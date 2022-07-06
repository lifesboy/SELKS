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
from ray.rllib.utils.framework import try_import_tf
tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

import common
from anomaly_normalization import F1, F2, F3, F4, F5, F6
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL
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

    def __init__(self):
        super().__init__()
        # global run
        parent_run_id = ''  # run.info.run_id

        self.processed_num = 0
        self.run, self.client = common.init_tracking('data-processor')
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=parent_run_id)

    def __call__(self, batch: DataFrame) -> DataFrame:
        self.processed_num += len(batch.index)
        self.client.log_metric(run_id=self.run.info.run_id, key="row", value=self.processed_num)
        return self.preprocess(batch)

    @mlflow_mixin
    def preprocess(self, df: DataFrame) -> DataFrame:
        dst_port = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[DST_PORT])).map(norm.norm_port)
        protocol = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[PROTOCOL])).map(norm.norm_protocol)
        flow_duration = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[FLOW_DURATION])).map(norm.norm_time_1h)
        tot_fwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOT_FWD_PKTS])).map(norm.norm_size_1mb)
        tot_bwd_pkts = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[TOT_BWD_PKTS])).map(norm.norm_size_1mb)

        data = DataFrame(data={
            DST_PORT: list(dst_port.as_numpy_iterator()),
            PROTOCOL: list(protocol.as_numpy_iterator()),
            FLOW_DURATION: list(flow_duration.as_numpy_iterator()),
            TOT_FWD_PKTS: list(tot_fwd_pkts.as_numpy_iterator()),
            TOT_BWD_PKTS: list(tot_bwd_pkts.as_numpy_iterator()),
        }, index=df[TIMESTAMP])

        if LABEL in df.columns:
            label = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df[LABEL])).map(norm.norm_label)
            data[LABEL] = list(label.as_numpy_iterator())
        else:
            data[LABEL] = ['' for i in range(len(data.index))]

        return data
