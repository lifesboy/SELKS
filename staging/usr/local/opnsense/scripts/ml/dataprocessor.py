#!/usr/bin/python3
from typing import List

import ray
from ray.data.dataset_pipeline import DatasetPipeline
from ray.data.impl.arrow_block import ArrowRow
from pyarrow import Table
from ray.tune.integration.mlflow import mlflow_mixin

import common
from anomaly_normalization import F1, F2, F3, F4, F5, F6
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS
import anomaly_normalization as norm

import mlflow

ray.init(address='127.0.0.1:6379')

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.create_experiment("data-processor")

@mlflow_mixin
def preprocess(row: List[ArrowRow]) -> List[ArrowRow]:
    # print (row)
    mlflow.autolog()
    return row
    # data = ray.data.from_items([{
    #     F1: i[DST_PORT],
    #     F2: '1',  # [str(norm.norm_protocol(i[PROTOCOL]))],
    #     # F3: [row[0][TIMESTAMP]],
    #     F4: '1',  # [str(norm.norm_time_1h(i[FLOW_DURATION]))],
    #     F5: '1',  # [str(norm.norm_size_1mb(i[TOT_FWD_PKTS]))],
    #     F6: '1',  # [str(norm.norm_size_1mb(i[TOT_BWD_PKTS]))],
    # } for i in row])
    # print(data)
    # return data.take()


# ray.init(local_mode=True)
# ray.init(num_cpus=8)

pipe: DatasetPipeline = ray.data.read_csv([
    # common.TRAIN_DATA_DIR + 'demo.csv',
    common.TRAIN_DATA_DIR + 'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv',
    common.TRAIN_DATA_DIR + 'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv',
]).pipeline(parallelism=5)

# Preprocess the data.
# pipe = pipe.map(preprocess)

# Apply GPU batch inference to the data.
pipe = pipe.map_batches(preprocess, compute="actors", batch_size=256, num_gpus=1, num_cpus=0)

# tf.keras.layers.BatchNormalization

num_rows = 0
for row in pipe.iter_rows():
    mlflow.log_metric(key="row", value=num_rows)
    num_rows += 1

print("Total num rows", num_rows)

# Save the output.
pipe.write_json(common.TMP_DIR)

# ray.shutdown()
