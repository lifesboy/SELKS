#!/usr/bin/python3
import argparse
import csv
import glob
import os
import signal
import time
import traceback
from datetime import datetime, timedelta
from functools import reduce
from pathlib import Path

import ray
from pandas import DataFrame, Series
from ray.data import DatasetPipeline
from ray.data.datasource import FastFileMetadataProvider

import lib.utils as utils
from lib.ciccsvdatasource import CicCSVDatasource
from lib.logger import log

import common
import numpy as np
import pandas as pd

from anomaly_normalization import TIMESTAMP, FLOW_DURATION, SRC_IP, SRC_PORT, DST_IP, DST_PORT, PROTOCOL, \
    LABEL, TIMESTAMP_FLOW, OFFSET, LABEL_VALUE_BENIGN, LABEL_VALUE_ANOMALY

batches_processed: int = 0
batches_success: int = 0
labeled_row: int = 0
labeled_source: int = 0
sources_fail: [] = []
invalid_rows: [] = []
sources_success: int = 0

parser = argparse.ArgumentParser()
parser.add_argument(
    "--data-destination",
    type=str,
    default="nsm-label",
    help="output labeled data directory path")
parser.add_argument(
    "--feature",
    type=str,
    default="src_ip",
    help="Matched values of this feature will be labeled")
parser.add_argument(
    "--values",
    type=str,
    default="192.168.66.190,192.168.66.191",
    help="Anomaly values to label (separate by comma)")
parser.add_argument(
    "--start-time",
    type=str,
    default="",
    help="Label matched data from this time (YYYY-MM-ddTHH-mm-ss). ex: 2023-01-14T23-08-25")
parser.add_argument(
    "--end-time",
    type=str,
    default="",
    help="Label matched data before this time (YYYY-MM-ddTHH-mm-ss). ex: 2023-01-14T23-08-25")
parser.add_argument(
    "--label",
    type=str,
    default=f"{LABEL_VALUE_ANOMALY}",
    help="Value to assign to label feature")
parser.add_argument(
    "--data-source",
    type=str,
    default="nsm/*.csv",
    help="Data to label")
parser.add_argument(
    "--action",
    type=str,
    default="start",
    help="run action")
parser.add_argument(
    "--tag",
    type=str,
    default="labeling-data",
    help="run tag")


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


@ray.remote
def create_assign_pipe(input_file: str, output_dir: str, label: str, feature: str, values: [str], start_time: str, end_time: str) -> int:
    df = pd.read_csv(input_file)

    if start_time:
        start = datetime.strptime(start_time + ' +0700', '%Y-%m-%dT%H-%M-%S %z')
        timestamp_start = datetime.strftime(start, '%Y-%m-%d %H:%M:%S')
        df = df[df[TIMESTAMP] >= timestamp_start]

    if end_time:
        end = datetime.strptime(start_time + ' +0700', '%Y-%m-%dT%H-%M-%S %z')
        timestamp_end = datetime.strftime(end, '%Y-%m-%d %H:%M:%S')
        df = df[df[TIMESTAMP] < timestamp_end]

    df.loc[df[feature].isin(values), LABEL] = label

    if df.index.size > 0:
        df.to_csv(f"{output_dir}/{input_file.split('/')[-1]}")
        return df.index.size

    return 0


def assign_data(df: Series, label: str, feature: str, values: [str], start_time: str, end_time: str) -> bool:
    log.info('assign_data start %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])

    global run, client, batches_processed, batches_success, sources_success, sources_fail, labeled_row, labeled_source

    try:
        batches_processed += 1
        client.log_metric(run_id=run.info.run_id, key='batches_processed', value=batches_processed)

        output_dir = df['output_path']
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        pipes = map(lambda x: create_assign_pipe.remote(x, output_dir, label, feature, values, start_time, end_time), df['input_path'])
        labeled_pipes = ray.get(list(pipes))
        done_rows = reduce(lambda s, x: s + x, labeled_pipes)
        done_sources = reduce(lambda s, x: s + (1 if x > 0 else 0), labeled_pipes)
        df['pipe_labeled'] = done_sources
        labeled_row += done_rows
        labeled_source += done_sources

        utils.marked_done(df['marked_done_path'])
        log.info('labeling done %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
        batches_success += 1
        sources_success += len(df['input_path'])
        client.log_metric(run_id=run.info.run_id, key='labeled_row', value=labeled_row)
        client.log_metric(run_id=run.info.run_id, key='labeled_source', value=labeled_source)
        client.log_metric(run_id=run.info.run_id, key='batches_success', value=batches_success)
        client.log_metric(run_id=run.info.run_id, key='sources_success', value=sources_success)
    except Exception as e:
        log.error('assign_data tasks interrupted: %s', e)
        sources_fail += [{'source': df['input_path'], 'reason': traceback.format_exc()}]
        client.log_metric(run_id=run.info.run_id, key='sources_fail_num', value=len(sources_fail))
        client.log_dict(run_id=run.info.run_id,
                        dictionary=sources_fail,
                        artifact_file='sources_fail.json')
    finally:
        pass

    log.info('assign_data end %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
    return True


# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/assignlabel.py --data-destination=nsm-label --feature=src_ip --values=192.168.66.190,192.168.66.191 --start-time=2023-01-14T23-08-25 --end-time=2023-01-15T23-08-25 --label=SSH-BruteForce --data-source=nsm/*.csv --tag=manual-labeling

if __name__ == "__main__":
    args = parser.parse_args()
    tag = args.tag
    data_source = args.data_source
    feature = args.feature
    values = args.values.strip().split(',')
    start_time = args.start_time
    end_time = args.end_time
    label = args.label
    data_destination = args.data_destination
    batch_size_source = 4
    destination_dir = common.DATA_FEATURED_EXTRACTED_DIR + data_destination + '/'

    input_files = common.get_data_featured_extracted_files_by_pattern(data_source)

    kill_exists_processing()
    run, client = common.init_experiment(name='labeling-data', run_name='%s-%s' % (tag, time.time()))

    client.log_param(run_id=run.info.run_id, key='action', value=args.action)
    if args.action == 'stop':
        exit(0)

    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag='labeling',
        batch_size=batch_size_source)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_text(run_id=run.info.run_id, text=f'{data_source_files}', artifact_file='data_source_files.json')

    client.log_param(run_id=run.info.run_id, key='feature', value=feature)
    client.log_param(run_id=run.info.run_id, key='values', value=values)
    client.log_param(run_id=run.info.run_id, key='start_time', value=start_time)
    client.log_param(run_id=run.info.run_id, key='end_time', value=end_time)
    client.log_param(run_id=run.info.run_id, key='label', value=label)
    client.log_param(run_id=run.info.run_id, key='data_destination', value=data_destination)
    client.log_param(run_id=run.info.run_id, key='batch_size_source', value=batch_size_source)
    client.log_param(run_id=run.info.run_id, key='batches', value=batch_df.index.size)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=tag)
    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='saving')

    try:
        log.info('start assign_data: pipe=%s', batch_df.count())
        batch_df.apply(lambda i: assign_data(i, label, feature, values, start_time, end_time), axis=1)
        log.info('finish assign_data.')

        data_destination_files = glob.glob(destination_dir + '*')
        client.log_text(run_id=run.info.run_id, text=f'{data_destination_files}',
                        artifact_file='data_destination_files.json')

        client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')
        client.set_terminated(run_id=run.info.run_id)
    except Exception as e:
        log.error('assignlabel run error: %s', e)
        client.log_text(run_id=run.info.run_id, text=traceback.format_exc(), artifact_file='run_error.txt')
        client.set_terminated(run_id=run.info.run_id, status='FAILED')
