import argparse
import os
import random
import signal
import time
import traceback

import gym
import requests
from pandas import DataFrame
from ray import serve

import common
import lib.utils as utils
from lib.logger import log
from aideployments.anomaly.anomaly_staging_deployment import AnomalyStagingDeployment

parser = argparse.ArgumentParser()
parser.add_argument(
    "--data-source",
    type=str,
    default="*/*",
    help="data source file path filter pattern")
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
    "--batch-size",
    type=int,
    default=1000,
    help="Number of batch size to process.")
parser.add_argument(
    "--tag",
    type=str,
    default="train",
    help="run tag")


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def main(args, course: str, unit: str, lesson):
    model = 'anomaly'
    training_name = common.get_training_name(args.run, model, args.env, unit)
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    num_workers = args.num_workers
    data_source = args.data_source
    input_files = common.get_data_normalized_labeled_files_by_pattern(data_source)
    destination_dir = f"{common.DATA_TESTED_DIR}{course}/{unit}/"
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='train',
        batch_size=1)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []
    data_source_sampling_dir = f"{common.DATA_SAMPLING_DIR}{course}/{unit}/"
    utils.create_sampling(data_source_sampling_dir, data_source_files)

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)
    client.set_tag(run_id=run.info.run_id, key='training_name', value=training_name)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
    serve.start(http_options={'host': common.MODEL_STAGING_ADDRESS, 'port': common.MODEL_STAGING_PORT})

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyStagingDeployment.deploy')
    AnomalyStagingDeployment.options(name='anomaly-staging').deploy()

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='Testing')

    for endpoint in ['anomaly-staging']:
        for _ in range(100):
            env = gym.make('CartPole-v0')
            obs = env.reset()
            print(f'-> Sending /{endpoint} observation {obs}')
            resp = requests.post(f'http://selks.ddns.net:6789/{endpoint}', json={'obs': obs.tolist()})
            print(f"<- Received /{endpoint} response {resp.json() if resp.ok else resp}")
            time.sleep(random.randint(1, 5))

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")


# command:locust
# parameters: --web-host * --web-port 8089 -f /usr/local/opnsense/scripts/ml/deployment_test.py --serving-url=%s --data-source=%s

if __name__ == "__main__":
    args = parser.parse_args()
    testing_course = f"test-{common.get_course()}"
    testing_unit = f"{common.get_course_unit()}"
    testing_lesson = '%s-%s' % (args.tag, common.get_second())  # testing 1 sample per week

    kill_exists_processing()
    run, client = common.init_experiment(name=testing_course, run_name=testing_lesson)
    client.log_param(run_id=run.info.run_id, key=common.TAG_TRAIN_UNIT, value=testing_unit)

    try:
        main(args, testing_course, testing_unit, testing_lesson)
    except Exception as e:
        log.error('test run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='test_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
