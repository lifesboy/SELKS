#!/usr/bin/python3

import time
import pandas
import ray
from mlflow.entities import Metric
from ray.tune.integration.mlflow import mlflow_mixin
import pyarrow as pa

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
 ACTIVE_STD, ACTIVE_MAX, ACTIVE_MIN, IDLE_MEAN, IDLE_STD, IDLE_MAX, IDLE_MIN, LABEL
from anomaly_normalization import FLOW_ID_CIC, SRC_IP_CIC, SRC_PORT_CIC, SRC_MAC_CIC, DST_IP_CIC, DST_PORT_CIC, DST_MAC_CIC, PROTOCOL_CIC, TIMESTAMP_CIC,\
 FLOW_DURATION_CIC, TOT_FWD_PKTS_CIC, TOT_BWD_PKTS_CIC, TOTLEN_FWD_PKTS_CIC, TOTLEN_BWD_PKTS_CIC, FWD_PKT_LEN_MAX_CIC,\
 FWD_PKT_LEN_MIN_CIC, FWD_PKT_LEN_MEAN_CIC, FWD_PKT_LEN_STD_CIC, BWD_PKT_LEN_MAX_CIC, BWD_PKT_LEN_MIN_CIC, BWD_PKT_LEN_MEAN_CIC,\
 BWD_PKT_LEN_STD_CIC, FLOW_BYTS_S_CIC, FLOW_PKTS_S_CIC, FLOW_IAT_MEAN_CIC, FLOW_IAT_STD_CIC, FLOW_IAT_MAX_CIC, FLOW_IAT_MIN_CIC,\
 FWD_IAT_TOT_CIC, FWD_IAT_MEAN_CIC, FWD_IAT_STD_CIC, FWD_IAT_MAX_CIC, FWD_IAT_MIN_CIC, BWD_IAT_TOT_CIC, BWD_IAT_MEAN_CIC, BWD_IAT_STD_CIC,\
 BWD_IAT_MAX_CIC, BWD_IAT_MIN_CIC, FWD_PSH_FLAGS_CIC, BWD_PSH_FLAGS_CIC, FWD_URG_FLAGS_CIC, BWD_URG_FLAGS_CIC, FWD_HEADER_LEN_CIC,\
 BWD_HEADER_LEN_CIC, FWD_PKTS_S_CIC, BWD_PKTS_S_CIC, PKT_LEN_MIN_CIC, PKT_LEN_MAX_CIC, PKT_LEN_MEAN_CIC, PKT_LEN_STD_CIC, PKT_LEN_VAR_CIC,\
 FIN_FLAG_CNT_CIC, SYN_FLAG_CNT_CIC, RST_FLAG_CNT_CIC, PSH_FLAG_CNT_CIC, ACK_FLAG_CNT_CIC, URG_FLAG_CNT_CIC, CWE_FLAG_COUNT_CIC, ECE_FLAG_CNT_CIC,\
 DOWN_UP_RATIO_CIC, PKT_SIZE_AVG_CIC, FWD_SEG_SIZE_AVG_CIC, BWD_SEG_SIZE_AVG_CIC, FWD_BYTS_B_AVG_CIC, FWD_PKTS_B_AVG_CIC, FWD_BLK_RATE_AVG_CIC,\
 BWD_BYTS_B_AVG_CIC, BWD_PKTS_B_AVG_CIC, BWD_BLK_RATE_AVG_CIC, SUBFLOW_FWD_PKTS_CIC, SUBFLOW_FWD_BYTS_CIC, SUBFLOW_BWD_PKTS_CIC,\
 SUBFLOW_BWD_BYTS_CIC, INIT_FWD_WIN_BYTS_CIC, INIT_BWD_WIN_BYTS_CIC, FWD_ACT_DATA_PKTS_CIC, FWD_SEG_SIZE_MIN_CIC, ACTIVE_MEAN_CIC,\
 ACTIVE_STD_CIC, ACTIVE_MAX_CIC, ACTIVE_MIN_CIC, IDLE_MEAN_CIC, IDLE_STD_CIC, IDLE_MAX_CIC, IDLE_MIN_CIC, LABEL_CIC

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
            LABEL: pa.string(),
        }

        return schema

    @staticmethod
    def get_feature_norm() -> dict:
        feature_norm = {
            # FLOW_ID: None,
            # SRC_IP: None,
            SRC_PORT: norm.norm_port,
            # SRC_MAC: None,
            # DST_IP: None,
            DST_PORT: norm.norm_port,
            # DST_MAC: None,
            PROTOCOL: norm.norm_protocol,
            # TIMESTAMP: None,
            FLOW_DURATION: norm.norm_time_1h,
            TOT_FWD_PKTS: norm.norm_size_1mb,
            TOT_BWD_PKTS: norm.norm_size_1mb,
            TOTLEN_FWD_PKTS: norm.norm_size_1mb,
            TOTLEN_BWD_PKTS: norm.norm_size_1mb,
            FWD_PKT_LEN_MAX: norm.norm_size_1mb,
            FWD_PKT_LEN_MIN: norm.norm_size_1mb,
            FWD_PKT_LEN_MEAN: norm.norm_size_1mb,
            FWD_PKT_LEN_STD: norm.norm_size_1mb,
            BWD_PKT_LEN_MAX: norm.norm_size_1mb,
            BWD_PKT_LEN_MIN: norm.norm_size_1mb,
            BWD_PKT_LEN_MEAN: norm.norm_size_1mb,
            BWD_PKT_LEN_STD: norm.norm_size_1mb,
            FLOW_BYTS_S: norm.norm_size_1mb,
            FLOW_PKTS_S: norm.norm_size_1mb,
            FLOW_IAT_MEAN: norm.norm_size_1mb,
            FLOW_IAT_STD: norm.norm_size_1mb,
            FLOW_IAT_MAX: norm.norm_size_1mb,
            FLOW_IAT_MIN: norm.norm_size_1mb,
            FWD_IAT_TOT: norm.norm_size_1mb,
            FWD_IAT_MEAN: norm.norm_size_1mb,
            FWD_IAT_STD: norm.norm_size_1mb,
            FWD_IAT_MAX: norm.norm_size_1mb,
            FWD_IAT_MIN: norm.norm_size_1mb,
            BWD_IAT_TOT: norm.norm_size_1mb,
            BWD_IAT_MEAN: norm.norm_size_1mb,
            BWD_IAT_STD: norm.norm_size_1mb,
            BWD_IAT_MAX: norm.norm_size_1mb,
            BWD_IAT_MIN: norm.norm_size_1mb,
            FWD_PSH_FLAGS: norm.norm_flag,
            BWD_PSH_FLAGS: norm.norm_flag,
            FWD_URG_FLAGS: norm.norm_flag,
            BWD_URG_FLAGS: norm.norm_flag,
            FWD_HEADER_LEN: norm.norm_size_1mb,
            BWD_HEADER_LEN: norm.norm_size_1mb,
            FWD_PKTS_S: norm.norm_size_1mb,
            BWD_PKTS_S: norm.norm_size_1mb,
            PKT_LEN_MIN: norm.norm_size_1mb,
            PKT_LEN_MAX: norm.norm_size_1mb,
            PKT_LEN_MEAN: norm.norm_size_1mb,
            PKT_LEN_STD: norm.norm_size_1mb,
            PKT_LEN_VAR: norm.norm_size_1mb,
            FIN_FLAG_CNT: norm.norm_flag,
            SYN_FLAG_CNT: norm.norm_flag,
            RST_FLAG_CNT: norm.norm_flag,
            PSH_FLAG_CNT: norm.norm_flag,
            ACK_FLAG_CNT: norm.norm_flag,
            URG_FLAG_CNT: norm.norm_flag,
            CWE_FLAG_COUNT: norm.norm_flag,
            ECE_FLAG_CNT: norm.norm_flag,
            DOWN_UP_RATIO: norm.norm_min_1,
            PKT_SIZE_AVG: norm.norm_size_1mb,
            FWD_SEG_SIZE_AVG: norm.norm_size_1mb,
            BWD_SEG_SIZE_AVG: norm.norm_size_1mb,
            FWD_BYTS_B_AVG: norm.norm_size_1mb,
            FWD_PKTS_B_AVG: norm.norm_size_1mb,
            FWD_BLK_RATE_AVG: norm.norm_size_1mb,
            BWD_BYTS_B_AVG: norm.norm_size_1mb,
            BWD_PKTS_B_AVG: norm.norm_size_1mb,
            BWD_BLK_RATE_AVG: norm.norm_size_1mb,
            SUBFLOW_FWD_PKTS: norm.norm_size_1mb,
            SUBFLOW_FWD_BYTS: norm.norm_size_1mb,
            SUBFLOW_BWD_PKTS: norm.norm_size_1mb,
            SUBFLOW_BWD_BYTS: norm.norm_size_1mb,
            INIT_FWD_WIN_BYTS: norm.norm_size_1mb,
            INIT_BWD_WIN_BYTS: norm.norm_size_1mb,
            FWD_ACT_DATA_PKTS: norm.norm_size_1mb,
            FWD_SEG_SIZE_MIN: norm.norm_size_1mb,
            ACTIVE_MEAN: norm.norm_time_1h,
            ACTIVE_STD: norm.norm_time_1h,
            ACTIVE_MAX: norm.norm_time_1h,
            ACTIVE_MIN: norm.norm_time_1h,
            IDLE_MEAN: norm.norm_time_1h,
            IDLE_STD: norm.norm_time_1h,
            IDLE_MAX: norm.norm_time_1h,
            IDLE_MIN: norm.norm_time_1h,
            LABEL: norm.norm_label,
        }

        return feature_norm

    def __init__(self):
        super().__init__()
        # global run
        parent_run_id = ''  # run.info.run_id

        self.processed_num = 0
        self.row_normed_num = 0
        self.anomaly_total = 0

        self.current_step: int = 0
        self.metrics: [Metric] = []

        self.run, self.client = common.init_tracking(name='data-processor', run_name='sub-processing-cic2018-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=parent_run_id)

    def __del__(self):
        self.client.set_terminated(run_id=self.run.info.run_id)
        super(Cic2018NormModel, self).__del__()

    def __call__(self, batch: DataFrame) -> DataFrame:
        return self.predict({}, batch)

    def predict(self, context, batch: DataFrame) -> DataFrame:
        self.current_step += 1
        self.processed_num += len(batch.index)
        self.client.set_tag(run_id=self.run.info.run_id, key='features', value=batch.columns.tolist())

        preprocessed = self.preprocess(batch)

        self.row_normed_num += len(preprocessed.index)
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

        feature_norm = Cic2018NormModel.get_feature_norm()
        features = set(df.columns).intersection(feature_norm.keys())
        df_norm = df[features]

        # if LABEL not in features:
        #     df_norm[LABEL] = ''

        data = DataFrame(data={
            i: list(tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df_norm[i]))
                    .map(feature_norm[i])
                    .as_numpy_iterator())
            for i in features
        })

        return data.fillna(0.)

    def _log_metrics(self):
        try:
            self.client.log_batch(run_id=self.run.info.run_id, metrics=self.metrics)
            self.metrics = []
        except Exception as e:
            log.error('_log_metrics error %s', e)
