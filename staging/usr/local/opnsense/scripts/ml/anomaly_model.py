#!/usr/bin/python3
"""Example of using a custom RNN keras model."""

import argparse
import os

import numpy as np
import mlflow
import yaml

import ray
from gym import Space
from keras import Model
from ray import tune
from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.preprocessors import get_preprocessor
from ray.rllib.models.tf.recurrent_net import RecurrentNetwork
from ray.rllib.utils.typing import ModelConfigDict
from ray.tune.integration.mlflow import MLflowLoggerCallback
from ray.tune.registry import register_env

import common
from anomaly_env import AnomalyEnv
from anomaly_initial_obs_env import AnomalyInitialObsEnv
from ray.rllib.examples.models.rnn_model import RNNModel
from ray.rllib.models import ModelCatalog
from ray.rllib.utils.test_utils import check_learning_achieved
from ray.rllib.utils.framework import try_import_tf, try_import_torch

tf1, tf, tfv = try_import_tf()
from ray.rllib.utils.annotations import override


class AnomalyModel(RecurrentNetwork):

    def __init__(self,
                 obs_space: Space,
                 action_space: Space,
                 num_outputs: int,
                 model_config: ModelConfigDict,
                 name: str,
                 hiddens_size: int = 256,
                 cell_size: int = 64):
        super(AnomalyModel, self).__init__(obs_space, action_space, num_outputs,
                                           model_config, name)
        self.cell_size = cell_size

        # Define input layers
        input_layer = tf.keras.layers.Input(
            shape=(None, obs_space.shape[0]), name="inputs")
        state_in_h = tf.keras.layers.Input(shape=(cell_size,), name="h")
        state_in_c = tf.keras.layers.Input(shape=(cell_size,), name="c")
        seq_in = tf.keras.layers.Input(shape=(), name="seq_in", dtype=tf.int32)

        # Preprocess observation with a hidden layer and send to LSTM cell
        dense1 = tf.keras.layers.Dense(
            hiddens_size, activation=tf.nn.relu, name="dense1")(input_layer)
        lstm_out, state_h, state_c = tf.keras.layers.LSTM(
            cell_size, return_sequences=True, return_state=True, name="lstm")(
            inputs=dense1,
            mask=tf.sequence_mask(seq_in),
            initial_state=[state_in_h, state_in_c])

        # Postprocess LSTM output with another hidden layer and compute values
        logits = tf.keras.layers.Dense(
            self.num_outputs,
            activation=tf.keras.activations.linear,
            name="logits")(lstm_out)
        values = tf.keras.layers.Dense(
            1, activation=None, name="values")(lstm_out)

        # Create the RNN model
        self.rnn_model: Model = Model(
            inputs=[input_layer, seq_in, state_in_h, state_in_c],
            outputs=[logits, values, state_h, state_c])
        self.rnn_model.summary()

    @override(RecurrentNetwork)
    def forward_rnn(self, inputs, state, seq_lens):
        model_out, self._value_out, h, c = self.rnn_model([inputs, seq_lens] +
                                                          state)

        # Creating output tf.Variables to specify the output of the saved model.
        feat_specifications = {
            "SepalLength": tf.Variable([], dtype=tf.float64, name="SepalLength"),
            "SepalWidth": tf.Variable([], dtype=tf.float64, name="SepalWidth"),
            "PetalLength": tf.Variable([], dtype=tf.float64, name="PetalLength"),
            "PetalWidth": tf.Variable([], dtype=tf.float64, name="PetalWidth"),
        }
        receiver_fn = tf.estimator.export.build_raw_serving_input_receiver_fn(feat_specifications)
        # self.rnn_model.export_saved_model("/tmp/anomaly_model/", receiver_fn).decode("utf-8")
        # tf.keras.experimental.export_saved_model(self.rnn_model, "/tmp/anomaly_model/")
        mlflow.keras.log_model(self.rnn_model, "anomaly-model")

        return model_out, [h, c]

    @override(ModelV2)
    def get_initial_state(self):
        return [
            np.zeros(self.cell_size, np.float32),
            np.zeros(self.cell_size, np.float32),
        ]

    @override(ModelV2)
    def value_function(self):
        return tf.reshape(self._value_out, [-1])


parser = argparse.ArgumentParser()
parser.add_argument(
    "--run",
    type=str,
    default="PPO",
    help="The RLlib-registered algorithm to use.")
parser.add_argument("--env", type=str, default="AnomalyEnv")
parser.add_argument("--num-cpus", type=int, default=0)
parser.add_argument(
    "--data-source",
    type=str,
    default="*/*",
    help="data source file path filter pattern")
parser.add_argument(
    "--as-test",
    action="store_true",
    help="Whether this script should be run as a test: --stop-reward must "
         "be achieved within --stop-timesteps AND --stop-iters.")
parser.add_argument(
    "--stop-iters",
    type=int,
    default=100,
    help="Number of iterations to train.")
parser.add_argument(
    "--stop-timesteps",
    type=int,
    default=100000,
    help="Number of timesteps to train.")
parser.add_argument(
    "--stop-episode-len",
    type=int,
    default=1e4,
    help="Max length of episode to train.")
parser.add_argument(
    "--stop-reward",
    type=float,
    default=90.0,
    help="Reward at which we stop training.")

# python3 anomaly_model.py --stop-iters=1000000 --stop-episode-len=1000000 --stop-timesteps=1000000 --stop-reward=1000000

if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.episode_len
    data_source_files = common.get_data_normalized_labeled_files_by_pattern(data_source)

    mlflow.tensorflow.autolog()
    run, client = common.init_experiment("anomaly-model")

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files', value=data_source_files)

    ModelCatalog.register_custom_model("rnn", RNNModel)
    ModelCatalog.register_custom_model("anomaly", AnomalyModel)

    register_env("AnomalyEnv", lambda c: AnomalyEnv(c))
    register_env("AnomalyInitialObsEnv", lambda _: AnomalyInitialObsEnv())

    # config = yaml.load(open('anomaly.yaml', 'r'), Loader=yaml.FullLoader)
    config = {
        "env": args.env,
        "env_config": {
            "episode_len": args.stop_episode_len,
            "data_source_files": data_source_files,
        },
        "gamma": 0.9,
        # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
        "num_gpus": 0.1,  # int(os.environ.get("RLLIB_NUM_GPUS", "0")),
        "num_workers": 0,
        "num_envs_per_worker": 20,
        "entropy_coeff": 0.001,
        "num_sgd_iter": 5,
        "vf_loss_coeff": 1e-5,
        "vf_clip_param": 1000.0,
        "model": {
            "custom_model": "anomaly",
            "max_seq_len": 20,
            "custom_model_config": {
                "cell_size": 32,
            },
        },
        "framework": 'tf',
    }

    stop = {
        "training_iteration": args.stop_iters,
        "timesteps_total": args.stop_timesteps,
        "episode_reward_mean": args.stop_reward,
    }

    # To run the Trainer without tune.run, using our RNN model and
    # manual state-in handling, do the following:

    # Example (use `config` from the above code):
    # >> import numpy as np
    # >> from ray.rllib.agents.ppo import PPOTrainer
    # >>
    # >> trainer = PPOTrainer(config)
    # >> lstm_cell_size = config["model"]["custom_model_config"]["cell_size"]
    # >> env = AnomalyEnv({})
    # >> obs = env.reset()
    # >>
    # >> # range(2) b/c h- and c-states of the LSTM.
    # >> init_state = state = [
    # ..     np.zeros([lstm_cell_size], np.float32) for _ in range(2)
    # .. ]
    # >>
    # >> while True:
    # >>     a, state_out, _ = trainer.compute_single_action(obs, state)
    # >>     obs, reward, done, _ = env.step(a)
    # >>     if done:
    # >>         obs = env.reset()
    # >>         state = init_state
    # >>     else:
    # >>         state = state_out
    results = tune.run(args.run, config=config, stop=stop, verbose=1,
                       checkpoint_at_end=True,
                       callbacks=[MLflowLoggerCallback(
                           experiment_name="anomaly-model",
                           save_artifact=True)])

    if args.as_test:
        check_learning_achieved(results, args.stop_reward)
