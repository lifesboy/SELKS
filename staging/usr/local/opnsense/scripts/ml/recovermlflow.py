#!/usr/bin/python3

import argparse
import os
import signal
import traceback
import time

import pandas as pd
from mlflow.entities import Metric

import common
import lib.utils as utils
from lib.logger import log

parser = argparse.ArgumentParser()
# parser.add_argument(
#     "--data-source",
#     type=str,
#     default="/drl/mlruns/*/*/artifacts/metrics_*.csv",
#     help="data source file path filter pattern")

parser.add_argument(
    "--action",
    type=str,
    default="start",
    help="run action")
parser.add_argument(
    "--tag",
    type=str,
    default="save-metrics",
    help="run tag")


# /usr/bin/python3 /usr/local/opnsense/scripts/ml/recovermlflow.py --tag=manual-recover-mlflow

def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def main(args):
    data_source = '/drl/mlruns/*/*/artifacts/metrics_*.csv'  # args.data_source
    data_source_files = common.get_data_files_by_pattern(data_source)

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)

    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')

    step: int = 0
    file_processed: int = 0
    metric_processed: int = 0
    file_success: int = 0
    metric_success: int = 0
    for path in data_source_files:
        step += 1
        timestamp = int(time.time() * 1000)
        file_success += 1
        try:
            client.log_metric(run_id=run.info.run_id, key='file_processed', value=file_processed, timestamp=timestamp, step=step)

            metric_run_id = path.split('/')[3]
            df = pd.read_csv(path)
            metrics = df.apply(lambda x: Metric(key=x['key'], value=x['value'], timestamp=x['timestamp'], step=x['step']), axis=0)

            metric_processed += len(metrics)
            client.log_metric(run_id=run.info.run_id, key='metric_processed', value=metric_processed, timestamp=timestamp, step=step)

            client.log_batch(run_id=metric_run_id, metrics=metrics)
            metric_success += len(metrics)
            client.log_metric(run_id=run.info.run_id, key='metric_success', value=metric_success, timestamp=timestamp, step=step)
        except Exception as e:
            log.error('recover mlflow error: %s', e)
            client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='recover_error.txt')


if __name__ == "__main__":
    args = parser.parse_args()
    kill_exists_processing()

    run, client = common.init_experiment(name='recover-mlflow')

    client.log_param(run_id=run.info.run_id, key='action', value=args.action)
    if args.action == 'stop':
        exit(0)

    try:
        main(args)
    except Exception as e:
        log.error('recover mlflow run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='recover_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
