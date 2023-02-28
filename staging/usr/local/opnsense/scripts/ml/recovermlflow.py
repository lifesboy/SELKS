#!/usr/bin/python3

import argparse
import math
import os
import signal
import traceback
import time

import pandas as pd
from mlflow.entities import Metric
from mlflow.store.tracking.dbmodels.models import SqlMetric
from pandas import DataFrame, Series

import common
import lib.utils as utils
from lib.logger import log
from lib.mlflow_helper import log_batch_heavy

step: int = 0
file_processed: int = 0
metric_processed: int = 0
file_success: int = 0
metric_success: int = 0
metric_discarded: int = 0

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


def remove_duplicated_metric(batch: [Metric], err: Exception):
    # BAD_REQUEST: (raised as a result of Query-invoked autoflush; consider using a session.no_autoflush block if this flush is occurring prematurely)
    # (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "metric_pk"
    # DETAIL:  Key (key, "timestamp", step, run_uuid, value, is_nan)=(anomaly_detected, 1675736159441, 4254, 1b7e267a1cff44e79404b119c9dc03ee, 3, f) already exists.
    #
    # [SQL: INSERT INTO metrics (key, value, timestamp, step, is_nan, run_uuid) VALUES (%(key)s, %(value)s, %(timestamp)s, %(step)s, %(is_nan)s, %(run_uuid)s)]

    s = f"{err}".split('\n')
    if len(s) < 3 or 'duplicate key value violates unique constraint' not in s[1]:
        raise err

    keys = s[2].split(')=')[0].split('(')[1].split(', ')
    values = s[2].split('=(')[1].split(')')[0].split(', ')
    m = dict(map(lambda x: (keys[x], values[x]), range(0, len(keys))))
    return list(filter(lambda x: not (
            f"{x.key}" == m['key']
            and round(float(x.value), 4) == round(float(m['value']), 4)
            and int(x.timestamp) == int(m['"timestamp"'])
            and int(x.step) == int(m['step'])
    ), batch))


def recover_run_id(s: Series):
    global step, file_processed, metric_processed, file_success, metric_success, metric_discarded
    metric_run_id = s.name
    input_paths = s.input_path
    log.info(f"start recovering run_id={metric_run_id}: {len(input_paths)}")

    step += 1
    timestamp = int(time.time() * 1000)
    dfs = list(map(lambda x: pd.read_csv(x)[['key', 'value', 'timestamp', 'step']], input_paths))
    df = pd.concat(dfs, axis=0, ignore_index=True)
    df = df.groupby(by=['key', 'timestamp', 'step']).max().reset_index()

    file_processed += len(input_paths)
    client.log_metric(run_id=run.info.run_id, key='file_processed', value=file_processed, timestamp=timestamp, step=step)

    try:
        metrics = df.apply(lambda x: SqlMetric(
            run_uuid=metric_run_id,
            key=x['key'],
            value=x['value'],
            timestamp=x['timestamp'],
            step=x['step'],
            is_nan=False
        ), axis=1).to_list()

        batch_size = 1000
        for i in range(0, math.ceil(len(metrics) / batch_size)):
            batch = metrics[i * batch_size:(i + 1) * batch_size]
            metric_processed += len(batch)
            client.log_metric(run_id=run.info.run_id, key='metric_processed', value=metric_processed, timestamp=timestamp, step=step)
            while len(batch) > 0:
                try:
                    # client.log_batch(run_id=metric_run_id, metrics=batch)
                    log_batch_heavy(client, batch)

                    metric_success += len(batch)
                    batch = []
                except Exception as ex:
                    log.error('log_batch mlflow error: %s, try discard error metric from batch %s', ex, len(batch))
                    # batch = remove_duplicated_metric(batch, ex)
                    metric_discarded += len(batch)
                    batch = []

            client.log_metric(run_id=run.info.run_id, key='metric_success', value=metric_success, timestamp=timestamp, step=step)
            client.log_metric(run_id=run.info.run_id, key='metric_discarded', value=metric_discarded, timestamp=timestamp, step=step)

        file_success += len(input_paths)
        remove_pattern = '/'.join(input_paths[0].split('/')[:-1]) + 'metrics_*.csv'
        log.info(f"remove path {remove_pattern}")
        os.system(f"rm -rf {remove_pattern}")
        client.log_metric(run_id=run.info.run_id, key='file_success', value=file_success, timestamp=timestamp, step=step)
    except Exception as e:
        log.error('recover mlflow error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='recover_error.txt')


def main(args):
    data_source = '/drl/mlruns/*/*/artifacts/metrics_*.csv'  # args.data_source
    data_source_files = common.get_data_files_by_pattern(data_source)

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=args.tag)

    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')

    file_df: DataFrame = pd.DataFrame(data_source_files, columns=['input_path'])
    file_df = file_df.applymap(lambda x: [x])
    file_df['run_id'] = file_df['input_path'].apply(lambda x: x[0].split('/')[4])
    batch_df: DataFrame = file_df.groupby('run_id').sum()
    batch_df.apply(lambda x: recover_run_id(x), axis=1)


if __name__ == "__main__":
    args = parser.parse_args()
    kill_exists_processing()

    run, client = common.init_experiment(name='recover-mlflow')

    client.log_param(run_id=run.info.run_id, key='action', value=args.action)
    if args.action == 'stop':
        exit(0)

    try:
        older_than = 30
        client.log_param(run_id=run.info.run_id, key='auto-clean.older_than', value=f"{older_than}d")

        clean_result = utils.clean_mlflow(client, older_than)
        client.log_text(run_id=run.info.run_id, text=clean_result, artifact_file='clean_result.txt')

        main(args)
    except Exception as e:
        log.error('recover mlflow run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='recover_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
