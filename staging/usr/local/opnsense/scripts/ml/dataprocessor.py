#!/usr/bin/python3
import argparse
import glob
from sys import version_info
import pandas
import ray
from ray.data.dataset_pipeline import DatasetPipeline
from ray.data.impl.arrow_block import ArrowRow
from pyarrow import Table
from ray.tune.integration.mlflow import mlflow_mixin

from pandas import DataFrame
import common
from anomaly_normalization import F1, F2, F3, F4, F5, F6
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL
import anomaly_normalization as norm

from datetime import date
import mlflow

PYTHON_VERSION = "{major}.{minor}.{micro}".format(major=version_info.major,
                                                  minor=version_info.minor,
                                                  micro=version_info.micro)
run, client = common.init_experiment('data-processor')


class BatchPreprocessor(mlflow.pyfunc.PythonModel):
    def __init__(self):
        super().__init__()
        global run
        self.processed_num = 0
        self.run, self.client = common.init_tracking('data-processor')
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=run.info.run_id)

    def __call__(self, batch: DataFrame) -> DataFrame:
        self.processed_num += len(batch.index)
        self.client.log_metric(run_id=self.run.info.run_id, key="row", value=self.processed_num)
        return self.preprocess(batch)

    @mlflow_mixin
    def preprocess(self, df: DataFrame) -> DataFrame:
        data = DataFrame(data={
            DST_PORT: df[DST_PORT].apply(norm.norm_port).values,
            PROTOCOL: df[PROTOCOL].apply(norm.norm_protocol).values,
            FLOW_DURATION: df[FLOW_DURATION].apply(norm.norm_time_1h).values,
            TOT_FWD_PKTS: df[TOT_FWD_PKTS].apply(norm.norm_size_1mb).values,
            TOT_BWD_PKTS: df[TOT_BWD_PKTS].apply(norm.norm_size_1mb).values,
            LABEL: df[LABEL].apply(norm.norm_label).values,
        }, index=df[TIMESTAMP])
        return data


preprocessor_model_path = "preprocessor"
preprocessor_reg_model_name = "BatchPreprocessor"
preprocessor_model = BatchPreprocessor()
conda_env = {
    'channels': ['defaults', 'conda-forge'],
    'dependencies': [
        'python={}'.format(PYTHON_VERSION),
        'pip'
    ],
    'pip': [
        'mlflow=={}'.format(mlflow.__version__),
        'pandas=={}'.format(pandas.__version__),
        'ray=={}'.format(ray.__version__)
    ],
    'name': 'mlflow-env'
}

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
        pipe = pipe.map_batches(BatchPreprocessor, batch_format="pandas", compute="actors",
                                batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)

        # tf.keras.layers.BatchNormalization

        client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='saving')
        pipe.write_csv(path=common.DATA_NORMALIZED_LABELED_DIR + data_destination + '/', try_create_dir=True)

        data_destination_file = glob.glob(common.DATA_NORMALIZED_LABELED_DIR + data_destination + '/*')
        client.log_param(run_id=run.info.run_id, key='data_destination_file', value=data_destination_file)

        mlflow.pyfunc.log_model(artifact_path=preprocessor_model_path,
                                python_model=preprocessor_model,
                                registered_model_name=preprocessor_reg_model_name,
                                conda_env=conda_env)

    client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')
