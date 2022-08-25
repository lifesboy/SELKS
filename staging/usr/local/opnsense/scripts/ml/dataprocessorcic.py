#!/usr/bin/python3
import argparse
import glob
import os
import signal

import ray
from ray.data.dataset_pipeline import DatasetPipeline
from ray.data.datasource.file_meta_provider import FastFileMetadataProvider
from pandas import DataFrame, Series
from pyarrow import csv

import lib.utils as utils
from lib.logger import log

import common
from aimodels.preprocessing.cic2018_norm_model import Cic2018NormModel
import mlflow

from anomaly_normalization import DST_PORT_CIC

run, client = common.init_experiment('data-processor')
batches_processed: int = 0
batches_success: int = 0
sources_fail: [] = []
sources_success: int = 0

parser = argparse.ArgumentParser()
parser.add_argument(
    "--run-model",
    type=str,
    default="",
    help="model to run")
parser.add_argument(
    "--data-source",
    type=str,
    default="",
    help="data source file paths")
parser.add_argument(
    "--tag",
    type=str,
    default="dataprocessing",
    help="run tag")
parser.add_argument(
    "--batch-size",
    type=int,
    default=1,
    help="Number of batch size to process.")
parser.add_argument(
    "--batch-size-source",
    type=int,
    default=5,
    help="Number of batch size source to process.")
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
    "--data-destination",
    type=str,
    default='processed_data_' + common.get_train_id(),
    help="Number of CPUs to use.")


# data_source = [
# common.TRAIN_DATA_DIR + 'demo.csv',
# common.TRAIN_DATA_DIR + 'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
# common.TRAIN_DATA_DIR + 'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv',
# common.TRAIN_DATA_DIR + 'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
# ]


def create_processor_pipe(data_files: [], batch_size: int, num_gpus: float, num_cpus: float):
    if not data_files or len(data_files) <= 0:
        return None

    schema = Cic2018NormModel.get_input_schema()
    #read_options = csv.ReadOptions(column_names=list(schema.keys()), use_threads=False)
    convert_options = csv.ConvertOptions(column_types=schema)

    pipe: DatasetPipeline = ray.data.read_csv(
        data_files,
        meta_provider=FastFileMetadataProvider(),
        #read_options=read_options,
        convert_options=convert_options,
    ).window(blocks_per_window=batch_size)
    pipe = pipe.map_batches(Cic2018NormModel, batch_format="pandas", compute="actors",
                            batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)
    # tf.keras.layers.BatchNormalization

    return pipe


def process_data(df: Series, batch_size: int, num_gpus: float, num_cpus: float) -> bool:
    log.info('process_data start %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])

    global batches_processed, batches_success, sources_success, sources_fail

    try:
        batches_processed += 1
        client.log_metric(run_id=run.info.run_id, key='batches_processed', value=batches_processed)

        df['pipe'] = create_processor_pipe(df['input_path'], batch_size, num_gpus, num_cpus)
        df['pipe'].write_csv(path=df['output_path'], try_create_dir=True)

        utils.marked_done(df['marked_done_path'])
        log.info('sniffing done %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
        batches_success += 1
        sources_success += len(df['input_path'])
        client.log_metric(run_id=run.info.run_id, key='batches_success', value=batches_success)
        client.log_metric(run_id=run.info.run_id, key='sources_success', value=sources_success)
    except Exception as e:
        log.error('process_data tasks interrupted: %s', e)
        sources_fail += df['input_path']
        client.log_metric(run_id=run.info.run_id, key='sources_fail_num', value=len(sources_fail))
        for i, s in enumerate(sources_fail):
            client.set_tag(run_id=run.info.run_id, key='sources_fail_%s' % i, value=s)
    finally:
        pass

    log.info('process_data end %s to %s, marked at %s', df['input_path'], df['output_path'], df['marked_done_path'])
    return True


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)

def separate_csv_file(data_source: str):
    ldf = utils.lines_in_files_of(DST_PORT_CIC, data_source)
    ldf.apply(utils.separate_file_by_lines, axis=1)

# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/dataprocessor.py --data-source=nsm/*.csv --batch-size=500 --num-gpus=0.4 --num-cpus=0.1 --data-destination=nsm --tag=nsm
# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/dataprocessorcic.py --data-source=cic2018/*.csv --batch-size=500 --num-gpus=0.4 --num-cpus=0.1 --data-destination=cic2018 --tag=cic2018


if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.data_source
    tag = args.tag
    run_model = args.run_model
    batch_size = args.batch_size
    batch_size_source = args.batch_size_source
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    data_destination = args.data_destination
    destination_dir = common.DATA_NORMALIZED_LABELED_DIR + data_destination + '/'

    separate_csv_file(common.DATA_FEATURED_EXTRACTED_DIR + data_source)
    input_files = common.get_data_featured_extracted_files_by_pattern(data_source)
    # input_files = data_source.split(',')

    kill_exists_processing()

    batch_df: DataFrame = utils.get_processing_file_pattern(
        input_files=input_files,
        output=destination_dir,
        tag=tag,
        batch_size=batch_size_source)

    data_source_files = [i for j in batch_df['input_path'].values for i in j] if 'input_path' in batch_df else []

    client.log_param(run_id=run.info.run_id, key='run_model', value=run_model)
    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files', value=data_source_files)
    client.log_param(run_id=run.info.run_id, key='data_source_files_num', value=len(data_source_files))
    client.log_param(run_id=run.info.run_id, key='data_destination', value=data_destination)
    client.log_param(run_id=run.info.run_id, key='batch_size_source', value=batch_size_source)
    client.log_param(run_id=run.info.run_id, key='batch_size', value=batch_size)
    client.log_param(run_id=run.info.run_id, key='batches', value=batch_df.index.size)
    client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)
    client.log_param(run_id=run.info.run_id, key='num_cpus', value=num_cpus)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TAG, value=tag)

    # client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='batching')
    # batch_df['pipe'] = batch_df.apply(
    #    lambda i: create_processor_pipe(i.input_path, batch_size, num_gpus, num_cpus),
    #    axis=1)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='saving')
    log.info('start process_data: pipe=%s', batch_df.count())
    batch_df.apply(lambda i: process_data(i, batch_size, num_gpus, num_cpus), axis=1)
    log.info('finish process_data.')

    data_destination_file = glob.glob(destination_dir + '*')
    client.log_param(run_id=run.info.run_id, key='data_destination_file', value=data_destination_file)

    model_meta = Cic2018NormModel.get_model_meta()
    mlflow.pyfunc.log_model(artifact_path=model_meta.artifact_path,
                            python_model=model_meta.python_model,
                            registered_model_name=model_meta.registered_model_name,
                            conda_env=model_meta.conda_env)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')