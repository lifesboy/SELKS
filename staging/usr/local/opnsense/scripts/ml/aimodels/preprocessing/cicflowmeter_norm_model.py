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
import pyarrow as pa

from pandas import DataFrame
from ray.rllib.utils.framework import try_import_tf
tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

import common
from anomaly_normalization import F1, F2, F3, F4, F5, F6
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS,\
    TOTLEN_FWD_PKTS, TOTLEN_BWD_PKTS, FWD_PKT_LEN_MAX, FWD_PKT_LEN_MIN, FWD_PKT_LEN_MEAN, FWD_PKT_LEN_STD,\
    BWD_PKT_LEN_MAX, BWD_PKT_LEN_MIN, BWD_PKT_LEN_MEAN, BWD_PKT_LEN_STD, PKT_LEN_MAX, PKT_LEN_MIN, PKT_LEN_MEAN,\
    PKT_LEN_STD, PKT_LEN_VAR, FWD_HEADER_LEN, BWD_HEADER_LEN, FWD_SEG_SIZE_MIN, FWD_ACT_DATA_PKTS,\
    ACTIVE_MEAN,\
    LABEL
import anomaly_normalization as norm

from datetime import date
import mlflow
from aimodels.model_meta import ModelMeta


class CicFlowmeterNormModel(mlflow.pyfunc.PythonModel):

    @staticmethod
    def get_model_meta() -> ModelMeta:
        return ModelMeta(artifact_path='preprocessor',
                         registered_model_name='CicFlowmeterNormModel',
                         python_model=CicFlowmeterNormModel(),
                         conda_env={
                             'channels': ['defaults', 'conda-forge'],
                             'dependencies': [
                                 'python={}'.format(common.PYTHON_VERSION),
                                 'pip'
                             ],
                             'pip': [
                                 'mlflow=={}'.format(mlflow.__version__),
                                 'pandas=={}'.format(pandas.__version__),
                                 'ray=={}'.format(ray.__version__)
                             ],
                             'name': 'mlflow-env'
                         })

    @staticmethod
    def get_input_schema() -> dict:
        schema = {
            DST_PORT: pa.int64(),
            PROTOCOL: pa.int32(),
            FLOW_DURATION: pa.int64(),
            TOT_FWD_PKTS: pa.float64(),
            TOT_BWD_PKTS: pa.float64(),

            TOTLEN_FWD_PKTS: pa.float64(),
            TOTLEN_BWD_PKTS: pa.float64(),
            FWD_PKT_LEN_MAX: pa.float64(),
            FWD_PKT_LEN_MIN: pa.float64(),
            FWD_PKT_LEN_MEAN: pa.float64(),
            FWD_PKT_LEN_STD: pa.float64(),
            BWD_PKT_LEN_MAX: pa.float64(),
            BWD_PKT_LEN_MIN: pa.float64(),
            BWD_PKT_LEN_MEAN: pa.float64(),
            BWD_PKT_LEN_STD: pa.float64(),
            PKT_LEN_MAX: pa.float64(),
            PKT_LEN_MIN: pa.float64(),
            PKT_LEN_MEAN: pa.float64(),
            PKT_LEN_STD: pa.float64(),
            PKT_LEN_VAR: pa.float64(),
            FWD_HEADER_LEN: pa.float64(),
            BWD_HEADER_LEN: pa.float64(),
            FWD_SEG_SIZE_MIN: pa.float64(),
            FWD_ACT_DATA_PKTS: pa.float64(),

            ACTIVE_MEAN: pa.float64(),

            LABEL: pa.string(),
        }

        return schema

    def __init__(self):
        super().__init__()
        # global run
        parent_run_id = ''  # run.info.run_id

        self.processed_num = 0
        self.row_normed_num = 0
        self.run, self.client = common.init_tracking('data-processor')
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=parent_run_id)

    def __call__(self, batch: DataFrame) -> DataFrame:
        self.processed_num += len(batch.index)
        self.client.log_metric(run_id=self.run.info.run_id, key="row", value=self.processed_num)
        self.client.log_metric(run_id=self.run.info.run_id, key='features_num', value=len(batch.columns))
        self.client.set_tag(run_id=self.run.info.run_id, key='features', value=batch.columns.tolist())

        preprocessed = self.preprocess(batch)

        self.row_normed_num += len(preprocessed.index)
        self.client.log_metric(run_id=self.run.info.run_id, key='row_normed_num', value=self.row_normed_num)
        self.client.log_metric(run_id=self.run.info.run_id, key='features_normed_num', value=len(preprocessed.columns))
        self.client.set_tag(run_id=self.run.info.run_id, key='features_normed', value=preprocessed.columns.tolist())
        return preprocessed

    @mlflow_mixin
    def preprocess(self, df: DataFrame) -> DataFrame:
        df.columns = df.columns.str.lower()
        df.columns = df.columns.str.replace(' ', '_')

        dst_port = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[DST_PORT])).map(norm.norm_port)
        protocol = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PROTOCOL])).map(norm.norm_protocol)
        flow_duration = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FLOW_DURATION])).map(norm.norm_time_1h)
        tot_fwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOT_FWD_PKTS])).map(norm.norm_size_1mb)
        tot_bwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOT_BWD_PKTS])).map(norm.norm_size_1mb)

        totlen_fwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOTLEN_FWD_PKTS])).map(norm.norm_size_1mb)
        totlen_bwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOTLEN_BWD_PKTS])).map(norm.norm_size_1mb)
        fwd_pkt_len_max = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_PKT_LEN_MAX])).map(norm.norm_size_1mb)
        fwd_pkt_len_min = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_PKT_LEN_MIN])).map(norm.norm_size_1mb)
        fwd_pkt_len_mean = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_PKT_LEN_MEAN])).map(norm.norm_size_1mb)
        fwd_pkt_len_std = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_PKT_LEN_STD])).map(norm.norm_size_1mb)
        bwd_pkt_len_max = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[BWD_PKT_LEN_MAX])).map(norm.norm_size_1mb)
        bwd_pkt_len_min = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[BWD_PKT_LEN_MIN])).map(norm.norm_size_1mb)
        bwd_pkt_len_mean = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[BWD_PKT_LEN_MEAN])).map(norm.norm_size_1mb)
        bwd_pkt_len_std = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[BWD_PKT_LEN_STD])).map(norm.norm_size_1mb)
        pkt_len_max = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PKT_LEN_MAX])).map(norm.norm_size_1mb)
        pkt_len_min = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PKT_LEN_MIN])).map(norm.norm_size_1mb)
        pkt_len_mean = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PKT_LEN_MEAN])).map(norm.norm_size_1mb)
        pkt_len_std = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PKT_LEN_STD])).map(norm.norm_size_1mb)
        pkt_len_var = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PKT_LEN_VAR])).map(norm.norm_size_1mb)
        fwd_header_len = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_HEADER_LEN])).map(norm.norm_size_1mb)
        bwd_header_len = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[BWD_HEADER_LEN])).map(norm.norm_size_1mb)
        fwd_seg_size_min = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_SEG_SIZE_MIN])).map(norm.norm_size_1mb)
        fwd_act_data_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FWD_ACT_DATA_PKTS])).map(norm.norm_size_1mb)

        data = DataFrame(data={
            DST_PORT: list(dst_port.as_numpy_iterator()),
            PROTOCOL: list(protocol.as_numpy_iterator()),
            FLOW_DURATION: list(flow_duration.as_numpy_iterator()),
            TOT_FWD_PKTS: list(tot_fwd_pkts.as_numpy_iterator()),
            TOT_BWD_PKTS: list(tot_bwd_pkts.as_numpy_iterator()),

            TOTLEN_FWD_PKTS: list(totlen_fwd_pkts.as_numpy_iterator()),
            TOTLEN_BWD_PKTS: list(totlen_bwd_pkts.as_numpy_iterator()),
            FWD_PKT_LEN_MAX: list(fwd_pkt_len_max.as_numpy_iterator()),
            FWD_PKT_LEN_MIN: list(fwd_pkt_len_min.as_numpy_iterator()),
            FWD_PKT_LEN_MEAN: list(fwd_pkt_len_mean.as_numpy_iterator()),
            FWD_PKT_LEN_STD: list(fwd_pkt_len_std.as_numpy_iterator()),
            BWD_PKT_LEN_MAX: list(bwd_pkt_len_max.as_numpy_iterator()),
            BWD_PKT_LEN_MIN: list(bwd_pkt_len_min.as_numpy_iterator()),
            BWD_PKT_LEN_MEAN: list(bwd_pkt_len_mean.as_numpy_iterator()),
            BWD_PKT_LEN_STD: list(bwd_pkt_len_std.as_numpy_iterator()),
            PKT_LEN_MAX: list(pkt_len_max.as_numpy_iterator()),
            PKT_LEN_MIN: list(pkt_len_min.as_numpy_iterator()),
            PKT_LEN_MEAN: list(pkt_len_mean.as_numpy_iterator()),
            PKT_LEN_STD: list(pkt_len_std.as_numpy_iterator()),
            PKT_LEN_VAR: list(pkt_len_var.as_numpy_iterator()),
            FWD_HEADER_LEN: list(fwd_header_len.as_numpy_iterator()),
            BWD_HEADER_LEN: list(bwd_header_len.as_numpy_iterator()),
            FWD_SEG_SIZE_MIN: list(fwd_seg_size_min.as_numpy_iterator()),
            FWD_ACT_DATA_PKTS: list(fwd_act_data_pkts.as_numpy_iterator()),
        }, index=df[TIMESTAMP])

        if LABEL in df.columns:
            label = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[LABEL])).map(norm.norm_label)
            data[LABEL] = list(label.as_numpy_iterator())
        else:
            data[LABEL] = ['' for i in range(len(data.index))]

        return data
