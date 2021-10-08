#!/usr/bin/python3

import ray
from ray.data.dataset_pipeline import DatasetPipeline
from ray.data.impl.arrow_block import ArrowRow
from pyarrow import Table

import common
from anomaly_normalization import F1, F2, F3, F4, F5, F6
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS
import anomaly_normalization as norm


def preprocess(row: ArrowRow) -> ArrowRow:
    return ArrowRow(
        Table().from_pydict({
            F1: norm.norm_port(row[0][DST_PORT]),
            F2: norm.norm_protocol(row[0][PROTOCOL]),
            # F3: row[0][TIMESTAMP],
            F4: norm.norm_time_1h(row[0][FLOW_DURATION]),
            F5: norm.norm_size_1mb(row[0][TOT_FWD_PKTS]),
            F6: norm.norm_size_1mb(row[0][TOT_BWD_PKTS]),
        })
    )


pipe: DatasetPipeline = ray.data.read_csv([
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
]).pipeline(parallelism=4)

# Preprocess the data.
pipe = pipe.map(preprocess)

# Apply GPU batch inference to the data.
# pipe = pipe.map_batches(BatchInferModel, compute="actors", batch_size=256, num_gpus=1)

# Save the output.
pipe.write_json(common.TMP_DIR)
