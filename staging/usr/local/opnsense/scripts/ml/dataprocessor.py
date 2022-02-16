#!/usr/bin/python3
import argparse
import glob
import ray
from ray.data.dataset_pipeline import DatasetPipeline

import common
from aimodels.preprocessing.cic2018_norm_model import Cic2018NormModel
import mlflow

run, client = common.init_experiment('data-processor')

parser = argparse.ArgumentParser()
parser.add_argument(
    "--data-source",
    type=str,
    default="",
    help="data source file paths")
parser.add_argument(
    "--batch-size",
    type=int,
    default=1,
    help="Number of batch size to process.")
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

if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.data_source
    batch_size = args.batch_size
    num_gpus = args.num_gpus
    num_cpus = args.num_cpus
    data_destination = args.data_destination
    #data_source_files = common.get_data_featured_extracted_files_by_pattern(data_source)
    data_source_files = data_source.split(',')

    client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
    client.log_param(run_id=run.info.run_id, key='data_source_files', value=data_source_files)
    client.log_param(run_id=run.info.run_id, key='data_destination', value=data_destination)
    client.log_param(run_id=run.info.run_id, key='batch_size', value=batch_size)
    client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)
    client.log_param(run_id=run.info.run_id, key='num_cpus', value=num_cpus)

    if data_source_files and len(data_source_files) > 0:
        pipe: DatasetPipeline = ray.data.read_csv(data_source_files).window(blocks_per_window=batch_size)

        # client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TYPE, value='preprocess')
        # client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='counting')
        # client.set_tag(run_id=run.info.run_id, key=common.TAG_DATASET_SIZE, value=pipe.count())

        client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='batching')
        pipe = pipe.map_batches(Cic2018NormModel, batch_format="pandas", compute="actors",
                                batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)

        # tf.keras.layers.BatchNormalization

        client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='saving')
        pipe.write_csv(path=common.DATA_NORMALIZED_LABELED_DIR + data_destination + '/', try_create_dir=True)

        data_destination_file = glob.glob(common.DATA_NORMALIZED_LABELED_DIR + data_destination + '/*')
        client.log_param(run_id=run.info.run_id, key='data_destination_file', value=data_destination_file)

        model_meta = Cic2018NormModel.get_model_meta()

        mlflow.pyfunc.log_model(artifact_path=model_meta.artifact_path,
                                python_model=model_meta.python_model,
                                registered_model_name=model_meta.registered_model_name,
                                conda_env=model_meta.conda_env)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')
