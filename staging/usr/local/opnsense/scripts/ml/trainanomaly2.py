#!/usr/bin/python3

import argparse
import time
import traceback

import mlflow
import pandas as pd
import ray
from pandas import DataFrame
from pyarrow import csv

from ray import tune
from ray.data import Dataset
from ray.data.aggregate import Count
from ray.tune.integration.mlflow import MLflowLoggerCallback
from ray.tune.registry import register_env
from ray.tune.utils.log import Verbosity

import common
import lib.utils as utils
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel
from anomaly_normalization import LABEL
from lib.ciccsvdatasource import CicCSVDatasource
from lib.logger import log
from aienvs.anomaly.anomaly_env import AnomalyEnv
from aienvs.anomaly.anomaly_initial_obs_env import AnomalyInitialObsEnv
from aienvs.anomaly.anomaly_random_env import AnomalyRandomEnv
from aienvs.anomaly.anomaly_minibatch_env import AnomalyMinibatchEnv
from aimodels.anomaly.anomaly_model import AnomalyModel
from ray.rllib.examples.models.rnn_model import RNNModel
from ray.rllib.models import ModelCatalog
from ray.rllib.utils.test_utils import check_learning_achieved
from ray.rllib.utils.framework import try_import_tf

tf1, tf, tfv = try_import_tf()
invalid_rows = []

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
    type=bool,
    default=False,
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
    default=2,
    help="Number of GPUs to use.")
parser.add_argument(
    "--num-cpus",
    type=float,
    default=20,
    help="Number of CPUs to use.")
parser.add_argument(
    "--num-workers",
    type=int,
    default=1,
    help="Number of workers to train.")
parser.add_argument(
    "--batch-size",
    type=int,
    default=1000,
    help="Number of batch size to process.")
parser.add_argument(
    "--tag",
    type=str,
    default="train",
    help="run tag")

# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly2.py --stop-iters=100 --stop-episode-len=1000000 --stop-timesteps=1000000 --stop-reward=1000000 --tag=manual-train2-cic2018
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly2.py --stop-iters=1000 --stop-episode-len=1000 --stop-timesteps=1000 --stop-reward=1000 --tag=manual-train2-cic2018 --env=AnomalyInitialObsEnv
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly2.py --stop-iters=1000 --stop-episode-len=1000 --stop-timesteps=1000 --stop-reward=1000 --tag=manual-train2-cic2018 --env=AnomalyRandomEnv
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly2.py --stop-iters=100 --stop-episode-len=100 --stop-timesteps=100 --stop-reward=100 --tag=manual-train2-cic2018 --env=AnomalyMinibatchEnv


def main(args, sampling_id):
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    num_workers = args.num_workers
    data_source = args.data_source
    input_files = common.get_data_normalized_labeled_files_by_pattern(data_source)
    destination_dir = common.DATA_TRAINED_DIR
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='train',
        batch_size=1)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []
    data_source_sampling_dir = '%s%s/' % (common.DATA_SAMPLING_DIR, sampling_id)
    utils.create_sampling(data_source_sampling_dir, data_source_files)

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)

    # config = yaml.load(open('anomaly.yaml', 'r'), Loader=yaml.FullLoader)
    config = {
        "env": args.env,
        "env_config": {  # mlflow cannot log too long param, saving to "context_data" instead
            "episode_len": args.stop_episode_len,
            "batch_size": args.batch_size,
            "data_source_sampling_dir": data_source_sampling_dir,
        },
        "gamma": 0.9,
        # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
        # "num_cpus": num_cpus,
        "num_gpus": num_gpus,  # int(os.environ.get("RLLIB_NUM_GPUS", "0")),
        "num_workers": num_workers,  # https://github.com/ray-project/ray/issues/25012
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
    client.log_param(run_id=run.info.run_id, key='config', value=config)  # assert mlflow auto-log param too long error

    def skip_invalid_row(row):
        global invalid_rows, data_source_sampling_dir
        invalid_rows += [{'source': data_source_sampling_dir, 'row': row}]
        return 'skip'

    dataset_parallelism = max(int(0.5 * num_cpus), 1)  # using 50% CPU for dataset operations
    schema = CicFlowmeterNormModel.get_input_schema()
    convert_options = csv.ConvertOptions(column_types=schema)
    parse_options = csv.ParseOptions(delimiter=",", invalid_row_handler=skip_invalid_row)
    dataset: Dataset = ray.data.read_datasource(
        CicCSVDatasource(),
        parallelism=dataset_parallelism,  # using 50% CPU for dataset operations
        paths=[data_source_sampling_dir],
        parse_options=parse_options,
        convert_options=convert_options)

    dataset = dataset.fully_executed().repartition(num_blocks=dataset_parallelism)
    count_df: DataFrame = dataset.groupby(LABEL).aggregate(Count()).to_pandas()
    context_data: dict = {
        'max_episode_steps': args.stop_episode_len,
        'num_samples': 10,
        'anomaly_total': count_df.loc[count_df[LABEL] == 0].sum()['count()'],
        'dataset_size': count_df.sum()['count()'],
    }

    register_env("AnomalyEnv", lambda c: AnomalyEnv(dataset, context_data, c))
    register_env("AnomalyInitialObsEnv", lambda c: AnomalyInitialObsEnv(c))
    register_env("AnomalyRandomEnv", lambda c: AnomalyRandomEnv(c))
    register_env("AnomalyMinibatchEnv", lambda c: AnomalyMinibatchEnv(dataset, context_data, c))

    ModelCatalog.register_custom_model("rnn", RNNModel)
    ModelCatalog.register_custom_model("anomaly", AnomalyModel)

    client.log_param(run_id=run.info.run_id, key='context_data', value=context_data)
    client.log_param(run_id=run.info.run_id, key='stop', value=stop)
    client.log_text(run_id=run.info.run_id, text=dataset.stats(), artifact_file='dataset_stats.txt')

    # To run the Trainer without tune.run, using our RNN model and
    # manual state-in handling, do the following:

    try:
        # Example (use `config` from the above code):
        import numpy as np
        from ray.rllib.agents.ppo import PPOTrainer

        trainer = PPOTrainer(config)
        lstm_cell_size = config["model"]["custom_model_config"]["cell_size"]
        env = AnomalyMinibatchEnv(config)
        obs = env.reset()

        # range(2) b/c h- and c-states of the LSTM.
        init_state = state = [
            np.zeros([lstm_cell_size], np.float32) for _ in range(2)
        ]

        while True:
            try:
                a, state_out, _ = trainer.compute_single_action(obs, state)
                obs, reward, done, _ = env.step(a)
                if done:
                    obs = env.reset()
                    state = init_state
                else:
                    state = state_out
            except Exception as ex:
                log.error('trainer run error: %s', ex)

        # check_learning_achieved(results, args.stop_reward)

        client.set_terminated(run_id=run.info.run_id)
    except Exception as e:
        log.error('tune run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='tune_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')


if __name__ == "__main__":
    args = parser.parse_args()
    sampling_id = '%s-%s' % (args.tag, time.time())

    mlflow.autolog(log_models=True, log_model_signatures=True, exclusive=True, log_input_examples=True)
    # mlflow.tensorflow.autolog()
    # mlflow.keras.autolog()
    run, client = common.init_experiment(name="anomaly-train", run_name=sampling_id)

    try:
        main(args, sampling_id)
    except Exception as e:
        log.error('train run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='train_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
