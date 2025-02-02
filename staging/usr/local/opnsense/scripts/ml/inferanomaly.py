#!/usr/bin/python3

import argparse
import base64
import glob
import json
import os
import signal
import time
import traceback

import ray
import requests
import numpy as np
from pandas import DataFrame, Series
from pyarrow import csv
from ray import serve
from ray.data import Dataset, DatasetPipeline
from ray.data.datasource import FastFileMetadataProvider

import common
import lib.utils as utils
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel
from anomaly_normalization import SRC_IP, DST_IP, DST_PORT, LABEL, LABEL_VALUE_BENIGN, LABEL_VALUE_ANOMALY
from lib.ciccsvdatasource import CicCSVDatasource
from lib.logger import log
from aideployments.anomaly.anomaly_production_deployment import AnomalyProductionDeployment
from lib.singlefileblockwritepathprovider import SingleFileBlockWritePathProvider

parallelism = common.TOTAL_CPUS_INFERRING_DATASET_OPERATION
anomaly_detected: int = 0
total_processed: int = 0
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
    default="/anomaly-production",
    help="data source file path filter pattern")
parser.add_argument(
    "--data-source",
    type=str,
    default="*/*",
    help="data source file path filter pattern")
parser.add_argument(
    "--num-gpus",
    type=float,
    default=0,
    help="Number of GPUs to use.")
parser.add_argument(
    "--num-cpus",
    type=float,
    default=2,
    help="Number of CPUs to use.")
parser.add_argument(
    "--num-step",
    type=float,
    default=1,
    help="Number of time steps per batch.")
parser.add_argument(
    "--batch-size",
    type=int,
    default=5000,
    help="Number of batch size to process.")
parser.add_argument(
    "--anomaly-threshold",
    type=float,
    default=0.5,
    help="Number of batch size to process.")
parser.add_argument(
    "--data-destination",
    type=str,
    default='inferred_data_' + common.get_course(),
    help="Number of CPUs to use.")
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


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def create_predict_pipe(data_files: [], batch_size: int, num_gpus: float, num_cpus: float):
    if not data_files or len(data_files) <= 0:
        return None

    # if not utils.is_ray_gpu_ready():
    #     log.warning('create_predict_pipe restart ray failing ray: %s', data_files)
    #     utils.restart_ray_service()

    def skip_invalid_row(row):
        global run, client, invalid_rows
        log.warning('skip_invalid_row %s on %s', row, data_files)
        invalid_rows += [{'source': data_files, 'row': row}]
        client.log_dict(run_id=run.info.run_id, dictionary=invalid_rows, artifact_file='invalid_rows.json')
        return 'skip'

    schema = CicFlowmeterNormModel.get_input_schema()
    parse_options = csv.ParseOptions(delimiter=",", invalid_row_handler=skip_invalid_row)
    convert_options = csv.ConvertOptions(column_types=schema)

    pipe: Dataset = ray.data.read_datasource(
        CicCSVDatasource(),
        paths=data_files,
        meta_provider=FastFileMetadataProvider(),
        parse_options=parse_options,
        convert_options=convert_options,
    )  # .window(blocks_per_window=batch_size)

    return pipe


def predict(endpoint: str, batch: DataFrame, num_step: int, batch_size: int, anomaly_threshold: float, tag: str) -> DataFrame:
    # global batches_processed, anomaly_detected, total_processed
    # batches_processed += num_step
    # client.log_metric(run_id=run.info.run_id, key='batches_processed', value=batches_processed)

    url = f'http://{common.MODEL_SERVE_ADDRESS}:{common.MODEL_SERVE_PORT}{endpoint}'
    log.info(f'-> Sending {endpoint} observation {batch}')
    resp = requests.post(url, json={
        'obs': batch.fillna(0).replace([np.inf, -np.inf], 0).to_dict(orient="list"),
        'num_step': num_step,
        'batch_size': batch_size,
        'anomaly_threshold': anomaly_threshold,
        'tag': tag,
    })

    if not resp.ok:
        raise Exception('predict fail {}'.format(resp))

    data = resp.json()
    log.info(f"<- Received {endpoint} response {data}")
    action_label = DataFrame.from_dict(data['action'])[LABEL]
    batch[LABEL] = action_label.map({0: LABEL_VALUE_BENIGN, 1: LABEL_VALUE_ANOMALY}).fillna(LABEL_VALUE_BENIGN)
    # anomaly_detected += action_label.sum()
    # total_processed += action_label.size
    # client.log_metric(run_id=run.info.run_id, key='anomaly_detected', value=int(anomaly_detected))
    # client.log_metric(run_id=run.info.run_id, key='total_processed', value=int(total_processed))

    return batch


def infer_data(df: Series, endpoint: str, num_step: int, batch_size: int, anomaly_threshold: float, num_gpus: float, num_cpus: float, tag: str) -> bool:
    log.info('infer_data start %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])

    global run, client, sources_processed, sources_success, sources_fail, anomaly_detected, total_processed

    try:
        sources_processed += 1
        client.log_metric(run_id=run.info.run_id, key='sources_processed', value=sources_processed)

        df['pipe'] = create_predict_pipe(df['input_path'], num_step * batch_size, num_gpus, num_cpus)
        df['pipe'] = df['pipe'].map_batches(lambda i: predict(endpoint, i, num_step, batch_size, anomaly_threshold, tag),
                                            batch_format="pandas", compute="actors",
                                            batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)
        # df['pipe'].write_csv(path=df['output_path'], try_create_dir=True, block_path_provider=SingleFileBlockWritePathProvider(df['output_name']))
        df_pipe: DataFrame = df['pipe'].to_pandas(limit=1000000000)
        df_anomaly: DataFrame = df_pipe[df_pipe[LABEL] == LABEL_VALUE_ANOMALY]

        add_anomaly_filter(tag, df_anomaly)
        os.system(f"mkdir -p \"{df['output_path']}\"")
        df_pipe.to_csv(f"{df['output_path']}{df['output_name']}.csv", index=False)
        utils.marked_done(df['marked_done_path'])

        log.info('inferring done %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
        # batches_success += num_step
        sources_success += len(df['input_path'])
        anomaly_detected += df_anomaly.index.size
        total_processed += df_pipe.index.size
        client.log_metric(run_id=run.info.run_id, key='anomaly_detected', value=int(anomaly_detected))
        client.log_metric(run_id=run.info.run_id, key='total_processed', value=int(total_processed))
        # client.log_metric(run_id=run.info.run_id, key='batches_success', value=batches_success)
        client.log_metric(run_id=run.info.run_id, key='sources_success', value=sources_success)
        client.log_text(run_id=run.info.run_id, text=f"{df['input_path']}", artifact_file='sources_success.txt')
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


def add_anomaly_filter(run_name: str, df: DataFrame):
    anomalies: DataFrame = df[[SRC_IP]].groupby(by=[SRC_IP]).first().reset_index()
    anomaly_filters = json.dumps({
        'run_name': run_name,
        'anomalies': json.loads(anomalies.to_json(orient='records'))
    })
    data = base64.b64encode(anomaly_filters.encode('utf-8')).decode("utf-8")
    os.system(f"configctl filter add_anomaly {data}")

    client.log_text(run_id=run.info.run_id, text=f"{data}\n{anomaly_filters}", artifact_file=f"run_filter_{int(time.time() * 1000)}.txt")
    return data


def main(args, course: str, unit: str, lesson):
    batch_size_source = 1
    endpoint = args.endpoint
    batch_size = args.batch_size
    anomaly_threshold = args.anomaly_threshold
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    num_step = args.num_step
    data_source = args.data_source
    data_destination = args.data_destination

    client.log_param(run_id=run.info.run_id, key='host', value=common.MODEL_SERVE_ADDRESS)
    client.log_param(run_id=run.info.run_id, key='port', value=common.MODEL_SERVE_PORT)
    client.log_param(run_id=run.info.run_id, key='endpoint', value=endpoint)
    client.log_param(run_id=run.info.run_id, key='batch_size_source', value=batch_size_source)
    client.log_param(run_id=run.info.run_id, key='batch_size', value=batch_size)
    client.log_param(run_id=run.info.run_id, key='anomaly_threshold', value=anomaly_threshold)
    client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)
    client.log_param(run_id=run.info.run_id, key='num_cpus', value=num_cpus)
    client.log_param(run_id=run.info.run_id, key='num_step', value=num_step)

    input_files = common.get_data_featured_extracted_files_by_pattern(data_source)
    destination_dir = f"{common.DATA_FEATURED_EXTRACTED_DIR}{data_destination}/"
    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='infer',
        batch_size=batch_size_source)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
    serve.start(http_options={'host': common.MODEL_SERVE_ADDRESS, 'port': common.MODEL_SERVE_PORT})

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyProductionDeployment.deploy')
    AnomalyProductionDeployment.options(name=endpoint[1:]).deploy()

    client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='Inferring')

    try:
        log.info('start infer_data: pipe=%s', batch_df.count())
        batch_df.apply(lambda i: infer_data(i, endpoint, num_step, batch_size, anomaly_threshold, num_gpus, num_cpus, lesson), axis=1)
        log.info('finish infer_data.')

        os.system(f"configctl filter reload gateway")  # apply generated rules

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
# /usr/bin/python3 /usr/local/opnsense/scripts/ml/inferanomaly.py --data-destination=nsm_anomaly --batch-size=500 --data-source=nsm/*.csv --num-cpus=2 --num-gpus=0 --tag=manual-infer

# a = json.dumps({
#     'run_name': 'INFER123',
#     'anomalies': [
#         {'src_ip': '123.123.123.1', 'dst_ip': '10.10.10.1', 'dst_port': 22},
#         {'src_ip': '123.123.123.2', 'dst_ip': '10.10.10.1', 'dst_port': 22},
#     ]
# })
# param = base64.b64encode(a.encode('utf-8')).decode("utf-8") # eyJydW5fbmFtZSI6ICJJTkZFUjEyMyIsICJhbm9tYWxpZXMiOiBbeyJzcmNfaXAiOiAiMTIzLjEyMy4xMjMuMSIsICJkc3RfaXAiOiAiMTAuMTAuMTAuMSIsICJkc3RfcG9ydCI6IDIyfSwgeyJzcmNfaXAiOiAiMTIzLjEyMy4xMjMuMiIsICJkc3RfaXAiOiAiMTAuMTAuMTAuMSIsICJkc3RfcG9ydCI6IDIyfV19
# os.system(f"configctl filter add_anomaly eyJydW5fbmFtZSI6ICJJTkZFUjEyMyIsICJhbm9tYWxpZXMiOiBbeyJzcmNfaXAiOiAiMTIzLjEyMy4xMjMuMSIsICJkc3RfaXAiOiAiMTAuMTAuMTAuMSIsICJkc3RfcG9ydCI6IDIyfSwgeyJzcmNfaXAiOiAiMTIzLjEyMy4xMjMuMiIsICJkc3RfaXAiOiAiMTAuMTAuMTAuMSIsICJkc3RfcG9ydCI6IDIyfV19")


if __name__ == "__main__":
    args = parser.parse_args()
    inferring_course = f"{common.get_course()}-infer"
    inferring_unit = f"{common.get_course_unit()}"
    inferring_lesson = common.get_second()  # inferring 1 sample per week

    kill_exists_processing()
    run, client = common.init_experiment(name=inferring_course, run_name=inferring_lesson)
    client.log_param(run_id=run.info.run_id, key=common.TAG_TRAIN_UNIT, value=inferring_unit)

    client.log_param(run_id=run.info.run_id, key='action', value=args.action)
    if args.action == 'stop':
        exit(0)

    try:
        main(args, inferring_course, inferring_unit, inferring_lesson)
    except Exception as e:
        log.error('infer run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='infer_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
