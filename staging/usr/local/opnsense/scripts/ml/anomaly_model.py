"""Example of using a custom RNN keras model."""

import argparse
import os
import yaml

import ray
from ray import tune
from ray.tune.integration.mlflow import MLflowLoggerCallback
from ray.tune.registry import register_env

import common
from anomaly_env import AnomalyEnv
from anomaly_initial_obs_env import AnomalyInitialObsEnv
from ray.rllib.examples.models.rnn_model import RNNModel
from ray.rllib.models import ModelCatalog
from ray.rllib.utils.test_utils import check_learning_achieved

parser = argparse.ArgumentParser()
parser.add_argument(
    "--run",
    type=str,
    default="PPO",
    help="The RLlib-registered algorithm to use.")
parser.add_argument("--env", type=str, default="AnomalyEnv")
parser.add_argument("--num-cpus", type=int, default=0)
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

    run, client = common.init_experiment("anomaly-model")

    ModelCatalog.register_custom_model(
        "rnn", RNNModel)
    register_env("AnomalyEnv", lambda c: AnomalyEnv(c))
    register_env("AnomalyInitialObsEnv", lambda _: AnomalyInitialObsEnv())

    # config = yaml.load(open('anomaly.yaml', 'r'), Loader=yaml.FullLoader)
    config = {
        "env": args.env,
        "env_config": {
            "episode_len": args.stop_episode_len,
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
            "custom_model": "rnn",
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
