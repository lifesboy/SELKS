#!/usr/bin/python3

import argparse
import os
import signal
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
from ray.tune.logger import TBXLoggerCallback
from ray.tune.registry import register_env
from ray.tune.utils.log import Verbosity

import common
import lib.utils as utils
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel
from anomaly_normalization import ALL_FEATURES, LABEL
from lib.anomalyloggercallback import AnomalyLoggerCallback
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
parser.add_argument("--env", type=str, default="AnomalyMinibatchEnv")
parser.add_argument(
    "--data-source",
    type=str,
    default="*/*",
    help="data source file path filter pattern")
parser.add_argument(
    "--features",
    type=str,
    default="",
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
    "--action",
    type=str,
    default="start",
    help="run action")
parser.add_argument(
    "--tag",
    type=str,
    default="train",
    help="run tag")


# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=100 --stop-episode-len=1000000 --stop-timesteps=1000000 --stop-reward=1000000 --tag=manual-train-cic2018
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=1000 --stop-episode-len=1000 --stop-timesteps=1000 --stop-reward=1000 --tag=manual-train-cic2018 --env=AnomalyInitialObsEnv
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=1000 --stop-episode-len=1000 --stop-timesteps=1000 --stop-reward=1000 --tag=manual-train-cic2018 --env=AnomalyRandomEnv
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=1000000 --stop-episode-len=1000000 --stop-timesteps=1000000 --stop-reward=1000000 --tag=manual-train-cic2018 --env=AnomalyMinibatchEnv
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/trainanomaly.py --stop-iters=100 --stop-episode-len=100 --stop-timesteps=100 --stop-reward=100 --tag=manual-train-cic2018 --env=AnomalyEnv


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def main(args, course: str, unit: str, lesson):
    model = 'anomaly'
    training_name = common.get_training_name(args.run, model, args.env, unit)
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    num_workers = args.num_workers
    features_request = args.features.strip().split(',') if args.features.strip() != '' else ALL_FEATURES
    data_sources = args.data_source.strip().split(';')
    input_files = sum([common.get_data_normalized_labeled_files_by_pattern(i) for i in data_sources], [])
    destination_dir = f"{common.DATA_TRAINED_DIR}{course}/{unit}/"
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='train',
        batch_size=1)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []
    data_source_sampling_dir = f"{common.DATA_SAMPLING_DIR}{course}/{unit}/"
    utils.create_sampling(data_source_sampling_dir, data_source_files)
    data_sampling_files = common.get_data_files_by_pattern(f"{data_source_sampling_dir}*")

    client.log_param(run_id=run.info.run_id, key='data_source', value=args.data_source)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)
    client.set_tag(run_id=run.info.run_id, key='training_name', value=training_name)

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
            "custom_model": model,
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

    client.log_param(run_id=run.info.run_id, key='features_request_num', value=len(features_request))
    client.log_text(run_id=run.info.run_id, text=f'{features_request}', artifact_file='features_request.json')
    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')
    client.log_param(run_id=run.info.run_id, key='data_sampling_files_num', value=len(data_sampling_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_sampling_files}', artifact_file='data_sampling_files.json')
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
    features = list(set(features_request).intersection(dataset.schema(fetch_if_missing=True).names))
    context_data: dict = {
        'features': features,
        'max_episode_steps': args.stop_episode_len,
        'num_samples': 10,
        'anomaly_total': count_df.loc[count_df[LABEL] != '0'].sum()['count()'],
        'dataset_size': count_df.sum()['count()'],
        'dataset_label_count': count_df.to_json(),
    }

    register_env("AnomalyEnv", lambda c: AnomalyEnv(dataset, context_data, c))
    register_env("AnomalyInitialObsEnv", lambda c: AnomalyInitialObsEnv(c))
    register_env("AnomalyRandomEnv", lambda c: AnomalyRandomEnv(c))
    register_env("AnomalyMinibatchEnv", lambda c: AnomalyMinibatchEnv(dataset, context_data, c))

    ModelCatalog.register_custom_model("rnn", RNNModel)
    ModelCatalog.register_custom_model("anomaly", AnomalyModel)

    client.log_param(run_id=run.info.run_id, key='features_num', value=len(context_data['features']))
    client.log_text(run_id=run.info.run_id, text=f"{context_data['features']}", artifact_file='features.json')
    client.log_param(run_id=run.info.run_id, key='max_episode_steps', value=context_data['max_episode_steps'])
    client.log_param(run_id=run.info.run_id, key='num_samples', value=context_data['num_samples'])
    client.log_param(run_id=run.info.run_id, key='anomaly_total', value=context_data['anomaly_total'])
    client.log_param(run_id=run.info.run_id, key='dataset_size', value=context_data['dataset_size'])
    client.log_param(run_id=run.info.run_id, key='dataset_label_count', value=context_data['dataset_label_count'])
    client.log_param(run_id=run.info.run_id, key='stop', value=stop)
    client.log_text(run_id=run.info.run_id, text=dataset.stats(), artifact_file='dataset_stats.txt')

    def resume_tune(resume: str = 'AUTO'):
        # in case of error, sometime we're unable to recover an experiment
        # It should be switch to another unit, and assume agent is fail at error unit
        return tune.run(args.run, config=config, stop=stop, verbose=Verbosity.V3_TRIAL_DETAILS,
                        name=unit,
                        local_dir=f"/drl/ray_results/{course}",
                        trial_name_creator=lambda _: lesson,
                        trial_dirname_creator=lambda _: lesson,
                        # log_to_file=['stdout.txt', 'stderr.txt'],  #not use this, ray error I/O on closed stream
                        keep_checkpoints_num=20,
                        checkpoint_freq=1,
                        checkpoint_at_end=True,
                        resume=resume,
                        callbacks=[AnomalyLoggerCallback(
                            tracking_uri=common.MLFLOW_TRACKING_URI,
                            tags={
                                'training_name': training_name,
                                common.TAG_PARENT_RUN_UUID: run.info.run_id,
                                common.TAG_RUN_TAG: args.tag,
                            },
                            experiment_name="anomaly-model",
                            save_artifact=True), TBXLoggerCallback()])

    try:

        try:
            results = resume_tune(resume='AUTO')
        except Exception as e1:
            log.error('tune run error1: %s', e1)
            # https://github.com/ray-project/ray/issues/12389
            results = resume_tune(resume='ERRORED_ONLY')

        client.log_dict(run_id=run.info.run_id, dictionary=invalid_rows, artifact_file='invalid_rows.json')

        if args.as_test:
            check_learning_achieved(results, args.stop_reward)

        client.set_terminated(run_id=run.info.run_id)
    except Exception as e:
        log.error('tune run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='tune_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')


if __name__ == "__main__":
    args = parser.parse_args()
    training_course = f"{common.get_course()}-train"
    training_unit = f"{common.get_course_unit()}"
    training_lesson = '%s-%s' % (args.tag, common.get_second())  # learning 1 sample per week

    kill_exists_processing()
    mlflow.autolog(log_models=True, log_model_signatures=True, exclusive=True, log_input_examples=True)
    # mlflow.tensorflow.autolog()
    # mlflow.keras.autolog()
    run, client = common.init_experiment(name=training_course, run_name=training_lesson)
    client.log_param(run_id=run.info.run_id, key=common.TAG_TRAIN_UNIT, value=training_unit)

    client.log_param(run_id=run.info.run_id, key='action', value=args.action)
    if args.action == 'stop':
        exit(0)

    try:
        main(args, training_course, training_unit, training_lesson)
    except Exception as e:
        log.error('train run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='train_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
