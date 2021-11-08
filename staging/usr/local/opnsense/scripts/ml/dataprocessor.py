#!/usr/bin/python3
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

num_rows = 0


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

# ray.init(local_mode=True)
# ray.init(num_cpus=8)

data_source = [
    # common.TRAIN_DATA_DIR + 'demo.csv',
    # common.TRAIN_DATA_DIR + 'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
    # common.TRAIN_DATA_DIR + 'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
]
batch_size = 10240
num_gpus = 0.2
num_cpus = 0.5
parallelism = 5

client.log_param(run_id=run.info.run_id, key='data_source', value=data_source)
client.log_param(run_id=run.info.run_id, key='batch_size', value=batch_size)
client.log_param(run_id=run.info.run_id, key='num_gpus', value=num_gpus)
client.log_param(run_id=run.info.run_id, key='num_cpus', value=num_cpus)
client.log_param(run_id=run.info.run_id, key='parallelism', value=parallelism)

pipe: DatasetPipeline = ray.data.read_csv(data_source).window(blocks_per_window=batch_size)

# client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_TYPE, value='preprocess')
client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='counting')
# client.set_tag(run_id=run.info.run_id, key=common.TAG_DATASET_SIZE, value=pipe.count())

client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='batching')
pipe = pipe.map_batches(BatchPreprocessor, batch_format="pandas", compute="actors",
                        batch_size=batch_size, num_gpus=num_gpus, num_cpus=num_cpus)

# tf.keras.layers.BatchNormalization

client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='saving')
pipe.write_csv(path=common.TMP_DIR + 'processed_data_' + common.get_train_id() + '/', try_create_dir=True)

mlflow.pyfunc.log_model(artifact_path=preprocessor_model_path,
                        python_model=preprocessor_model,
                        registered_model_name=preprocessor_reg_model_name,
                        conda_env=conda_env)
client.set_tag(run_id=run.info.run_id, key=common.TAG_RUN_STATUS, value='done')
