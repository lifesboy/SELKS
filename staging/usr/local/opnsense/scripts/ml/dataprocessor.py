#!/usr/bin/python3
from typing import List

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

common.init_experiment('data-processor')


@mlflow_mixin
def preprocess(df: DataFrame) -> DataFrame:
    # print(df)
    data = DataFrame(data={
        DST_PORT: df[DST_PORT].apply(norm.norm_port).values,
        PROTOCOL: df[PROTOCOL].apply(norm.norm_protocol).values,
        FLOW_DURATION: df[FLOW_DURATION].apply(norm.norm_time_1h).values,
        TOT_FWD_PKTS: df[TOT_FWD_PKTS].apply(norm.norm_size_1mb).values,
        TOT_BWD_PKTS: df[TOT_BWD_PKTS].apply(norm.norm_size_1mb).values,
        LABEL: df[LABEL].apply(norm.norm_label).values,
    }, index=df[TIMESTAMP])
    # print(data)
    return data


# ray.init(local_mode=True)
# ray.init(num_cpus=8)

pipe: DatasetPipeline = ray.data.read_csv([
    common.TRAIN_DATA_DIR + 'demo.csv',
    # common.TRAIN_DATA_DIR + 'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv',
    # common.TRAIN_DATA_DIR + 'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv',
]).pipeline(parallelism=5)

mlflow.set_tags({
    common.TAG_DATASET_SIZE: pipe.count(),
    common.TAG_RUN_TYPE: 'preprocess'
})

pipe = pipe.map_batches(preprocess, batch_format="pandas", compute="actors",
                        batch_size=1024, num_gpus=0, num_cpus=0)

# tf.keras.layers.BatchNormalization

num_rows = 0
for row in pipe.iter_batches(batch_size=1024):
    num_rows += len(row)
    mlflow.log_metric(key="row", value=num_rows)

print("Total done rows: ", num_rows)

# Save the output.
pipe.write_csv(common.TMP_DIR)

# ray.shutdown()
