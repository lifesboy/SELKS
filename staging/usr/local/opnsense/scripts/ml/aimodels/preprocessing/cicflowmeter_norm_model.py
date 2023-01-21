#!/usr/bin/python3

import time
import pandas
import ray
from mlflow.entities import Metric
from ray.tune.integration.mlflow import mlflow_mixin
import pyarrow as pa
import numpy as np

import pandas as pd
from pandas import DataFrame
from ray.rllib.utils.framework import try_import_tf

from lib.logger import log

tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

import common
from anomaly_normalization import FLOW_ID, SRC_IP, SRC_PORT, SRC_MAC, DST_IP, DST_PORT, DST_MAC, PROTOCOL, TIMESTAMP,\
 FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, TOTLEN_FWD_PKTS, TOTLEN_BWD_PKTS, FWD_PKT_LEN_MAX,\
 FWD_PKT_LEN_MIN, FWD_PKT_LEN_MEAN, FWD_PKT_LEN_STD, BWD_PKT_LEN_MAX, BWD_PKT_LEN_MIN, BWD_PKT_LEN_MEAN,\
 BWD_PKT_LEN_STD, FLOW_BYTS_S, FLOW_PKTS_S, FLOW_IAT_MEAN, FLOW_IAT_STD, FLOW_IAT_MAX, FLOW_IAT_MIN,\
 FWD_IAT_TOT, FWD_IAT_MEAN, FWD_IAT_STD, FWD_IAT_MAX, FWD_IAT_MIN, BWD_IAT_TOT, BWD_IAT_MEAN, BWD_IAT_STD,\
 BWD_IAT_MAX, BWD_IAT_MIN, FWD_PSH_FLAGS, BWD_PSH_FLAGS, FWD_URG_FLAGS, BWD_URG_FLAGS, FWD_HEADER_LEN,\
 BWD_HEADER_LEN, FWD_PKTS_S, BWD_PKTS_S, PKT_LEN_MIN, PKT_LEN_MAX, PKT_LEN_MEAN, PKT_LEN_STD, PKT_LEN_VAR,\
 FIN_FLAG_CNT, SYN_FLAG_CNT, RST_FLAG_CNT, PSH_FLAG_CNT, ACK_FLAG_CNT, URG_FLAG_CNT, CWE_FLAG_COUNT, ECE_FLAG_CNT,\
 DOWN_UP_RATIO, PKT_SIZE_AVG, FWD_SEG_SIZE_AVG, BWD_SEG_SIZE_AVG, FWD_BYTS_B_AVG, FWD_PKTS_B_AVG, FWD_BLK_RATE_AVG,\
 BWD_BYTS_B_AVG, BWD_PKTS_B_AVG, BWD_BLK_RATE_AVG, SUBFLOW_FWD_PKTS, SUBFLOW_FWD_BYTS, SUBFLOW_BWD_PKTS,\
 SUBFLOW_BWD_BYTS, INIT_FWD_WIN_BYTS, INIT_BWD_WIN_BYTS, FWD_ACT_DATA_PKTS, FWD_SEG_SIZE_MIN, ACTIVE_MEAN,\
 ACTIVE_STD, ACTIVE_MAX, ACTIVE_MIN, IDLE_MEAN, IDLE_STD, IDLE_MAX, IDLE_MIN, TTL, LEN_PAYLOADS, PS, LABEL,\
 PAYLOAD_FEATURE_NUM

import anomaly_normalization as norm
import lib.utils as utils

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
            FLOW_ID: pa.string(),
            SRC_IP: pa.string(),
            SRC_PORT: pa.float64(),
            SRC_MAC: pa.string(),
            DST_IP: pa.string(),
            DST_PORT: pa.float64(),
            DST_MAC: pa.string(),
            PROTOCOL: pa.float64(),
            TIMESTAMP: pa.string(),
            FLOW_DURATION: pa.float64(),
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
            FLOW_BYTS_S: pa.float64(),
            FLOW_PKTS_S: pa.float64(),
            FLOW_IAT_MEAN: pa.float64(),
            FLOW_IAT_STD: pa.float64(),
            FLOW_IAT_MAX: pa.float64(),
            FLOW_IAT_MIN: pa.float64(),
            FWD_IAT_TOT: pa.float64(),
            FWD_IAT_MEAN: pa.float64(),
            FWD_IAT_STD: pa.float64(),
            FWD_IAT_MAX: pa.float64(),
            FWD_IAT_MIN: pa.float64(),
            BWD_IAT_TOT: pa.float64(),
            BWD_IAT_MEAN: pa.float64(),
            BWD_IAT_STD: pa.float64(),
            BWD_IAT_MAX: pa.float64(),
            BWD_IAT_MIN: pa.float64(),
            FWD_PSH_FLAGS: pa.float64(),
            BWD_PSH_FLAGS: pa.float64(),
            FWD_URG_FLAGS: pa.float64(),
            BWD_URG_FLAGS: pa.float64(),
            FWD_HEADER_LEN: pa.float64(),
            BWD_HEADER_LEN: pa.float64(),
            FWD_PKTS_S: pa.float64(),
            BWD_PKTS_S: pa.float64(),
            PKT_LEN_MIN: pa.float64(),
            PKT_LEN_MAX: pa.float64(),
            PKT_LEN_MEAN: pa.float64(),
            PKT_LEN_STD: pa.float64(),
            PKT_LEN_VAR: pa.float64(),
            FIN_FLAG_CNT: pa.float64(),
            SYN_FLAG_CNT: pa.float64(),
            RST_FLAG_CNT: pa.float64(),
            PSH_FLAG_CNT: pa.float64(),
            ACK_FLAG_CNT: pa.float64(),
            URG_FLAG_CNT: pa.float64(),
            CWE_FLAG_COUNT: pa.float64(),
            ECE_FLAG_CNT: pa.float64(),
            DOWN_UP_RATIO: pa.float64(),
            PKT_SIZE_AVG: pa.float64(),
            FWD_SEG_SIZE_AVG: pa.float64(),
            BWD_SEG_SIZE_AVG: pa.float64(),
            FWD_BYTS_B_AVG: pa.float64(),
            FWD_PKTS_B_AVG: pa.float64(),
            FWD_BLK_RATE_AVG: pa.float64(),
            BWD_BYTS_B_AVG: pa.float64(),
            BWD_PKTS_B_AVG: pa.float64(),
            BWD_BLK_RATE_AVG: pa.float64(),
            SUBFLOW_FWD_PKTS: pa.float64(),
            SUBFLOW_FWD_BYTS: pa.float64(),
            SUBFLOW_BWD_PKTS: pa.float64(),
            SUBFLOW_BWD_BYTS: pa.float64(),
            INIT_FWD_WIN_BYTS: pa.float64(),
            INIT_BWD_WIN_BYTS: pa.float64(),
            FWD_ACT_DATA_PKTS: pa.float64(),
            FWD_SEG_SIZE_MIN: pa.float64(),
            ACTIVE_MEAN: pa.float64(),
            ACTIVE_STD: pa.float64(),
            ACTIVE_MAX: pa.float64(),
            ACTIVE_MIN: pa.float64(),
            IDLE_MEAN: pa.float64(),
            IDLE_STD: pa.float64(),
            IDLE_MAX: pa.float64(),
            IDLE_MIN: pa.float64(),
            TTL: pa.float64(),
            LEN_PAYLOADS: pa.float64(),
            LABEL: pa.string(),
        }

        for i in range(0, PAYLOAD_FEATURE_NUM):
            schema[PS % i] = pa.float64()

        return schema

    @staticmethod
    def get_feature_norm() -> dict:
        feature_norm = {
            # FLOW_ID: None,
            # SRC_IP: None,
            SRC_PORT: tf.keras.activations.tanh,
            # SRC_MAC: None,
            # DST_IP: None,
            DST_PORT: tf.keras.activations.tanh,
            # DST_MAC: None,
            PROTOCOL: tf.keras.activations.tanh,
            # TIMESTAMP: None,
            FLOW_DURATION: tf.keras.activations.tanh,
            TOT_FWD_PKTS: tf.keras.activations.tanh,
            TOT_BWD_PKTS: tf.keras.activations.tanh,
            TOTLEN_FWD_PKTS: tf.keras.activations.tanh,
            TOTLEN_BWD_PKTS: tf.keras.activations.tanh,
            FWD_PKT_LEN_MAX: tf.keras.activations.tanh,
            FWD_PKT_LEN_MIN: tf.keras.activations.tanh,
            FWD_PKT_LEN_MEAN: tf.keras.activations.tanh,
            FWD_PKT_LEN_STD: tf.keras.activations.tanh,
            BWD_PKT_LEN_MAX: tf.keras.activations.tanh,
            BWD_PKT_LEN_MIN: tf.keras.activations.tanh,
            BWD_PKT_LEN_MEAN: tf.keras.activations.tanh,
            BWD_PKT_LEN_STD: tf.keras.activations.tanh,
            FLOW_BYTS_S: tf.keras.activations.tanh,
            FLOW_PKTS_S: tf.keras.activations.tanh,
            FLOW_IAT_MEAN: tf.keras.activations.tanh,
            FLOW_IAT_STD: tf.keras.activations.tanh,
            FLOW_IAT_MAX: tf.keras.activations.tanh,
            FLOW_IAT_MIN: tf.keras.activations.tanh,
            FWD_IAT_TOT: tf.keras.activations.tanh,
            FWD_IAT_MEAN: tf.keras.activations.tanh,
            FWD_IAT_STD: tf.keras.activations.tanh,
            FWD_IAT_MAX: tf.keras.activations.tanh,
            FWD_IAT_MIN: tf.keras.activations.tanh,
            BWD_IAT_TOT: tf.keras.activations.tanh,
            BWD_IAT_MEAN: tf.keras.activations.tanh,
            BWD_IAT_STD: tf.keras.activations.tanh,
            BWD_IAT_MAX: tf.keras.activations.tanh,
            BWD_IAT_MIN: tf.keras.activations.tanh,
            FWD_PSH_FLAGS: tf.keras.activations.tanh,
            BWD_PSH_FLAGS: tf.keras.activations.tanh,
            FWD_URG_FLAGS: tf.keras.activations.tanh,
            BWD_URG_FLAGS: tf.keras.activations.tanh,
            FWD_HEADER_LEN: tf.keras.activations.tanh,
            BWD_HEADER_LEN: tf.keras.activations.tanh,
            FWD_PKTS_S: tf.keras.activations.tanh,
            BWD_PKTS_S: tf.keras.activations.tanh,
            PKT_LEN_MIN: tf.keras.activations.tanh,
            PKT_LEN_MAX: tf.keras.activations.tanh,
            PKT_LEN_MEAN: tf.keras.activations.tanh,
            PKT_LEN_STD: tf.keras.activations.tanh,
            PKT_LEN_VAR: tf.keras.activations.tanh,
            FIN_FLAG_CNT: tf.keras.activations.tanh,
            SYN_FLAG_CNT: tf.keras.activations.tanh,
            RST_FLAG_CNT: tf.keras.activations.tanh,
            PSH_FLAG_CNT: tf.keras.activations.tanh,
            ACK_FLAG_CNT: tf.keras.activations.tanh,
            URG_FLAG_CNT: tf.keras.activations.tanh,
            CWE_FLAG_COUNT: tf.keras.activations.tanh,
            ECE_FLAG_CNT: tf.keras.activations.tanh,
            DOWN_UP_RATIO: tf.keras.activations.tanh,
            PKT_SIZE_AVG: tf.keras.activations.tanh,
            FWD_SEG_SIZE_AVG: tf.keras.activations.tanh,
            BWD_SEG_SIZE_AVG: tf.keras.activations.tanh,
            FWD_BYTS_B_AVG: tf.keras.activations.tanh,
            FWD_PKTS_B_AVG: tf.keras.activations.tanh,
            FWD_BLK_RATE_AVG: tf.keras.activations.tanh,
            BWD_BYTS_B_AVG: tf.keras.activations.tanh,
            BWD_PKTS_B_AVG: tf.keras.activations.tanh,
            BWD_BLK_RATE_AVG: tf.keras.activations.tanh,
            SUBFLOW_FWD_PKTS: tf.keras.activations.tanh,
            SUBFLOW_FWD_BYTS: tf.keras.activations.tanh,
            SUBFLOW_BWD_PKTS: tf.keras.activations.tanh,
            SUBFLOW_BWD_BYTS: tf.keras.activations.tanh,
            INIT_FWD_WIN_BYTS: tf.keras.activations.tanh,
            INIT_BWD_WIN_BYTS: tf.keras.activations.tanh,
            FWD_ACT_DATA_PKTS: tf.keras.activations.tanh,
            FWD_SEG_SIZE_MIN: tf.keras.activations.tanh,
            ACTIVE_MEAN: tf.keras.activations.tanh,
            ACTIVE_STD: tf.keras.activations.tanh,
            ACTIVE_MAX: tf.keras.activations.tanh,
            ACTIVE_MIN: tf.keras.activations.tanh,
            IDLE_MEAN: tf.keras.activations.tanh,
            IDLE_STD: tf.keras.activations.tanh,
            IDLE_MAX: tf.keras.activations.tanh,
            IDLE_MIN: tf.keras.activations.tanh,
            TTL: tf.keras.activations.tanh,
            LEN_PAYLOADS: tf.keras.activations.tanh,
            LABEL: norm.norm_label,
        }

        for i in range(0, PAYLOAD_FEATURE_NUM):
            feature_norm[PS % i] = norm.norm_crop_1byte

        return feature_norm

    def __init__(self):
        super().__init__()
        # global run
        parent_run_id = ''  # run.info.run_id

        self.processed_num: int = 0
        self.row_normed_num: int = 0
        self.anomaly_total: float = 0

        self.current_step: int = 0
        self.metrics: [Metric] = []

        self.run, self.client = common.init_tracking(name='data-processor', run_name='sub-processing-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=parent_run_id)

    def __del__(self):
        self.client.set_terminated(run_id=self.run.info.run_id)
        super(CicFlowmeterNormModel, self).__del__()

    def __call__(self, batch: DataFrame) -> DataFrame:
        return self.predict({}, batch)

    def predict(self, context, batch: DataFrame) -> DataFrame:
        self.current_step += 1
        self.processed_num += len(batch.index)
        self.client.set_tag(run_id=self.run.info.run_id, key='features', value=batch.columns.tolist())

        preprocessed = self.preprocess(batch)

        self.row_normed_num += len(preprocessed.index)
        if LABEL in preprocessed.columns.tolist():
            self.anomaly_total += preprocessed[LABEL].sum()

        self.client.set_tag(run_id=self.run.info.run_id, key='features_normed', value=preprocessed.columns.tolist())
        timestamp = int(time.time() * 1000)
        self.metrics += [
            Metric(key='row', value=self.processed_num, timestamp=timestamp, step=self.current_step),
            Metric(key='features_num', value=len(batch.columns), timestamp=timestamp, step=self.current_step),
            Metric(key='row_normed_num', value=self.row_normed_num, timestamp=timestamp, step=self.current_step),
            Metric(key='features_normed_num', value=len(preprocessed.columns), timestamp=timestamp, step=self.current_step),
            Metric(key='anomaly_total', value=self.anomaly_total, timestamp=timestamp, step=self.current_step),
        ]

        if len(self.metrics) > 0:
            self._log_metrics()

        return preprocessed

    @mlflow_mixin
    def preprocess(self, df: DataFrame) -> DataFrame:
        df.columns = df.columns.str.lower()
        df.columns = df.columns.str.replace(' ', '_')

        feature_norm = CicFlowmeterNormModel.get_feature_norm()
        features = sorted(list(set(df.columns).intersection(feature_norm.keys())))
        df_norm = df[features]

        # if LABEL not in features:
        #     df_norm[LABEL] = ''

        @ray.remote(num_gpus=0.01)
        def preprocess_transform(name, ds, f):
            return (name, list(tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(ds))
                               .map(f)
                               .as_numpy_iterator()))

        pipes = map(lambda x: preprocess_transform.remote(x, df_norm[x], feature_norm[x]), features)
        data = DataFrame()
        for ps in np.array_split(list(pipes), 4):
            transformed = ray.get(ps)
            df_ps = DataFrame(data=dict(transformed))
            data = pd.concat([data, df_ps], axis=1, ignore_index=True)

        return data.fillna(0.).replace([np.inf, -np.inf], 0)

    def _log_metrics(self):
        try:
            self.client.log_batch(run_id=self.run.info.run_id, metrics=self.metrics)
            self.metrics = []
        except Exception as e:
            utils.write_failsafe_metrics(f"{self.run.info.artifact_uri}/metrics_{int(time.time() * 1000)}.csv", self.metrics)
            self.metrics = []
            log.error('_log_metrics error %s', e)
