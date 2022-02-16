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
from aimodels.model_meta import ModelMeta


class Cic2018NormModel(mlflow.pyfunc.PythonModel):

    @staticmethod
    def get_model_meta() -> ModelMeta:
        return ModelMeta(artifact_path='preprocessor',
                         registered_model_name='Cic2018NormModel',
                         python_model=Cic2018NormModel(),
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
        data = DataFrame(data={
            DST_PORT: df[DST_PORT].apply(norm.norm_port).values,
            PROTOCOL: df[PROTOCOL].apply(norm.norm_protocol).values,
            FLOW_DURATION: df[FLOW_DURATION].apply(norm.norm_time_1h).values,
            TOT_FWD_PKTS: df[TOT_FWD_PKTS].apply(norm.norm_size_1mb).values,
            TOT_BWD_PKTS: df[TOT_BWD_PKTS].apply(norm.norm_size_1mb).values,
            LABEL: df[LABEL].apply(norm.norm_label).values,
        }, index=df[TIMESTAMP])
        return data
