#!/usr/bin/python3

import argparse
import time

import mlflow
import pandas as pd
from pandas import DataFrame

from ray import tune
from ray.tune.integration.mlflow import MLflowLoggerCallback
from ray.tune.registry import register_env

import common
import lib.utils as utils
from aienvs.anomaly.anomaly_env import AnomalyEnv
from aienvs.anomaly.anomaly_initial_obs_env import AnomalyInitialObsEnv
from aimodels.anomaly.anomaly_model import AnomalyModel
from ray.rllib.examples.models.rnn_model import RNNModel
from ray.rllib.models import ModelCatalog
from ray.rllib.utils.test_utils import check_learning_achieved
from ray.rllib.utils.framework import try_import_tf

tf1, tf, tfv = try_import_tf()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--run",
    type=str,
    default="PPO",
    help="The RLlib-registered algorithm to use.")
parser.add_argument("--env", type=str, default="AnomalyEnv")
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
parser.add_argument(
    "--num-gpus",
    type=float,
    default=0.1,
    help="Number of GPUs to use.")
parser.add_argument(
    "--num-cpus",
    type=float,
    default=0,
    help="Number of CPUs to use.")
parser.add_argument(
    "--tag",
    type=str,
    default="train",
    help="run tag")

# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=100 --stop-episode-len=1000000 --stop-timesteps=1000000 --stop-reward=1000000 --tag=manual-train-cic2018

if __name__ == "__main__":
    args = parser.parse_args()
    tag = args.tag
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    data_source = args.data_source
    input_files = common.get_data_normalized_labeled_files_by_pattern(data_source)
    destination_dir = common.DATA_TRAINED_DIR
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='train',
        batch_size=1)
    sampling_id = '%s-%s' % (tag, time.time())

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []
    data_source_sampling_dir = '%s%s/' % (common.DATA_SAMPLING_DIR, sampling_id)
    utils.create_sampling(data_source_sampling_dir, data_source_files)

    mlflow.tensorflow.autolog()
    # mlflow.keras.autolog()
    run, client = common.init_experiment(name="anomaly-model", run_name=sampling_id)

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    # client.log_param(run_id=run.info.run_id, key='data_source_files', value=data_source_files)
    # client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=tag)

    ModelCatalog.register_custom_model("rnn", RNNModel)
    ModelCatalog.register_custom_model("anomaly", AnomalyModel)

    register_env("AnomalyEnv", lambda c: AnomalyEnv(c))
    register_env("AnomalyInitialObsEnv", lambda _: AnomalyInitialObsEnv())

    # config = yaml.load(open('anomaly.yaml', 'r'), Loader=yaml.FullLoader)
    config = {
        "env": args.env,
        "env_config": {
            "episode_len": args.stop_episode_len,
            "data_source_sampling_dir": data_source_sampling_dir,
        },
        "gamma": 0.9,
        # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
        # "num_cpus": num_cpus,
        "num_gpus": num_gpus,  # int(os.environ.get("RLLIB_NUM_GPUS", "0")),
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

    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')

    config_df = pd.json_normalize([{'config': config}])
    config_df.apply(lambda i: i.reset_index().apply(
        lambda k: client.log_param(run_id=run.info.run_id, key=(k['index']), value=k[0]), axis=1), axis=1)

    stop_df = pd.json_normalize([{'stop': stop}])
    stop_df.apply(lambda i: i.reset_index().apply(
        lambda k: client.log_param(run_id=run.info.run_id, key=(k['index']), value=k[0]), axis=1), axis=1)

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
                       name=sampling_id,
                       checkpoint_at_end=True,
                       callbacks=[MLflowLoggerCallback(
                           experiment_name="anomaly-model",
                           save_artifact=True)])

    if args.as_test:
        check_learning_achieved(results, args.stop_reward)
