#!/usr/bin/python3

import argparse
import glob
import os
import signal
import traceback

import ray
import requests
from pandas import DataFrame, Series
from pyarrow import csv
from ray import serve
from ray.data import Dataset, DatasetPipeline
from ray.data.datasource import FastFileMetadataProvider

import common
import lib.utils as utils
from lib.ciccsvdatasource import CicCSVDatasource
from lib.logger import log
from aideployments.anomaly.anomaly_staging_deployment import AnomalyStagingDeployment

batches_processed: int = 0
batches_success: int = 0
sources_fail: [] = []
invalid_rows: [] = []
sources_processed: int = 0
sources_success: int = 0

parser = argparse.ArgumentParser()
parser.add_argument(
    "--endpoint",
    type=str,
    default="/anomaly-staging",
    help="data source file path filter pattern")
parser.add_argument(
    "--data-source",
    type=str,
    default="*/*",
    help="data source file path filter pattern")
parser.add_argument(
    "--num-gpus",
    type=float,
    default=0.1,
    help="Number of GPUs to use.")
parser.add_argument(
    "--num-cpus",
    type=float,
    default=0.1,
    help="Number of CPUs to use.")
parser.add_argument(
    "--num-step",
    type=float,
    default=1,
    help="Number of time steps per batch.")
parser.add_argument(
    "--batch-size",
    type=int,
    default=500,
    help="Number of batch size to process.")
parser.add_argument(
    "--tag",
    type=str,
    default="train",
    help="run tag")


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def create_predict_pipe(data_files: [], batch_size: int, num_gpus: float, num_cpus: float):
    if not data_files or len(data_files) <= 0:
        return None

    if not utils.is_ray_gpu_ready():
        log.warning('create_predict_pipe restart ray failing ray: %s', data_files)
        utils.restart_ray_service()

    def skip_invalid_row(row):
        global run, client, invalid_rows
        log.warning('skip_invalid_row %s on %s', row, data_files)
        invalid_rows += [{'source': data_files, 'row': row}]
        client.log_dict(run_id=run.info.run_id, dictionary=invalid_rows, artifact_file='invalid_rows.json')
        return 'skip'

    parse_options = csv.ParseOptions(delimiter=",", invalid_row_handler=skip_invalid_row)

    pipe: DatasetPipeline = ray.data.read_datasource(
        CicCSVDatasource(),
        paths=data_files,
        meta_provider=FastFileMetadataProvider(),
        parse_options=parse_options,
    ).window(blocks_per_window=batch_size)

    return pipe


def predict(endpoint: str, batch: DataFrame, num_step: int, batch_size: int) -> DataFrame:
    global batches_processed
    batches_processed += num_step
    client.log_metric(run_id=run.info.run_id, key='batches_processed', value=batches_processed)

    url = f'http://{common.MODEL_STAGING_ADDRESS}:{common.MODEL_STAGING_PORT}{endpoint}'
    log.info(f'-> Sending {endpoint} observation {batch}')
    resp = requests.post(url, json={
        'obs': batch.to_dict(orient="list"),
        'num_step': num_step,
        'batch_size': batch_size,
    })

    if not resp.ok:
        raise Exception('predict fail {}'.format(resp))

    data = resp.json()
    log.info(f"<- Received {endpoint} response {data}")
    return DataFrame.from_dict(data['action'])


def infer_data(df: Series, endpoint: str, num_step: int, batch_size: int, num_gpus: float, num_cpus: float) -> bool:
    log.info('infer_data start %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])

    global run, client, sources_processed, batches_success, sources_success, sources_fail

    try:
        sources_processed += 1
        client.log_metric(run_id=run.info.run_id, key='sources_processed', value=sources_processed)

        df['pipe'] = create_predict_pipe(df['input_path'], num_step * batch_size, num_gpus, num_cpus)
        df['pipe'] = df['pipe'].map_batches(lambda i: predict(endpoint, i, num_step, batch_size), batch_format="pandas", compute="actors",
                                            batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)
        df['pipe'].write_csv(path=df['output_path'], try_create_dir=True)
        utils.marked_done(df['marked_done_path'])

        log.info('inferring done %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
        batches_success += num_step
        sources_success += len(df['input_path'])
        client.log_metric(run_id=run.info.run_id, key='batches_success', value=batches_success)
        client.log_metric(run_id=run.info.run_id, key='sources_success', value=sources_success)
    except Exception as e:
        log.error('infer_data tasks interrupted: %s', e)
        sources_fail += [{'source': df['input_path'], 'reason': traceback.format_exc()}]
        client.log_metric(run_id=run.info.run_id, key='sources_fail_num', value=len(sources_fail))
        client.log_dict(run_id=run.info.run_id,
                        dictionary=sources_fail,
                        artifact_file='sources_fail.json')
    finally:
        pass

    log.info('infer_data end %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
    return True


def main(args, course: str, unit: str, lesson):
    batch_size_source = 1
    endpoint = args.endpoint
    batch_size = args.batch_size
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    num_step = args.num_step
    data_source = args.data_source

    client.log_param(run_id=run.info.run_id, key='host', value=common.MODEL_STAGING_ADDRESS)
    client.log_param(run_id=run.info.run_id, key='port', value=common.MODEL_STAGING_PORT)
    client.log_param(run_id=run.info.run_id, key='endpoint', value=endpoint)
    client.log_param(run_id=run.info.run_id, key='batch_size_source', value=batch_size_source)
    client.log_param(run_id=run.info.run_id, key='batch_size', value=batch_size)
    client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)
    client.log_param(run_id=run.info.run_id, key='num_cpus', value=num_cpus)
    client.log_param(run_id=run.info.run_id, key='num_step', value=num_step)

    input_files = common.get_data_normalized_labeled_files_by_pattern(data_source)
    destination_dir = f"{common.DATA_TESTED_DIR}{course}/{unit}/"
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='test',
        batch_size=batch_size_source)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
    serve.start(http_options={'host': common.MODEL_STAGING_ADDRESS, 'port': common.MODEL_STAGING_PORT})

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyStagingDeployment.deploy')
    AnomalyStagingDeployment.options(name=endpoint[1:]).deploy()

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='Testing')

    try:
        log.info('start infer_data: pipe=%s', batch_df.count())
        batch_df.apply(lambda i: infer_data(i, endpoint, num_step, batch_size, num_gpus, num_cpus), axis=1)
        log.info('finish infer_data.')

        data_destination_files = glob.glob(destination_dir + '*')
        client.log_text(run_id=run.info.run_id, text=f'{data_destination_files}', artifact_file='data_destination_files.json')

        client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')
        client.set_terminated(run_id=run.info.run_id)
    except Exception as e:
        log.error('infer_data run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='run_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")


# command:locust
# parameters: --web-host * --web-port 8089 -f /usr/local/opnsense/scripts/ml/deployment_test.py --serving-url=%s --data-source=%s
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/testanomaly.py --data-source=cic2018/*.csv --tag=manual-test

if __name__ == "__main__":
    args = parser.parse_args()
    testing_course = f"{common.get_course()}-test"
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
