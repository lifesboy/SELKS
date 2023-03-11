import json
import traceback

import mlflow
import time
import numpy as np
import pandas as pd
from keras.models import Model
from mlflow.entities import Metric
from mlflow.pyfunc import PyFuncModel
from mlflow.types import Schema
from pandas import DataFrame

from ray import serve
from starlette.requests import Request

import common
import lib.utils as utils
from aimodels.anomaly.anomaly_model import AnomalyModel
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, TOTLEN_FWD_PKTS, LABEL
from lib.logger import log


@serve.deployment(name="AnomalyProductionDeployment",
                  num_replicas=1,
                  ray_actor_options={"num_cpus": 2, "num_gpus": 2})
class AnomalyProductionDeployment:

    def __init__(self) -> None:
        self.anomaly_detected: int = 0
        self.batches_processed: int = 0
        self.batches_success: int = 0
        self.num_step: int = 1
        self.cell_size: int = 320
        self.l = None
        self.h = np.zeros((self.num_step, self.cell_size), dtype=np.float32)
        self.c = np.zeros((self.num_step, self.cell_size), dtype=np.float32)

        self.current_step: int = 0
        self.metrics: [Metric] = []

        self.run, self.client = common.init_tracking(name='anomaly-production-deployment',
                                                     run_name='anomaly-production-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        norm_model_name = CicFlowmeterNormModel.get_model_meta().registered_model_name
        model_name = AnomalyModel.get_model_meta().registered_model_name
        stage = 'production'
        norm_model_versions = self.client.get_latest_versions(name=norm_model_name, stages=[stage])
        model_versions = self.client.get_latest_versions(name=model_name, stages=[stage])
        if len(norm_model_versions) < 1:
            raise RuntimeError(f'model not found: {norm_model_name}/{stage}')
        if len(model_versions) < 1:
            raise RuntimeError(f'model not found: {model_name}/{stage}')

        self.norm_model: PyFuncModel = mlflow.pyfunc.load_model(f'models:/{norm_model_name}/{stage}')
        self.model: Model = mlflow.keras.load_model(f'models:/{model_name}/{stage}')
        model: PyFuncModel = mlflow.pyfunc.load_model(f'models:/{model_name}/{stage}')
        input_schema: Schema = model.metadata.signature.inputs
        output_schema: Schema = model.metadata.signature.outputs
        self.features: [str] = input_schema.input_names()

        self.client.log_param(run_id=self.run.info.run_id, key='norm_model_name', value=norm_model_versions[0].name)
        self.client.log_param(run_id=self.run.info.run_id, key='norm_model_version', value=norm_model_versions[0].version)

        self.client.log_param(run_id=self.run.info.run_id, key='model_name', value=model_versions[0].name)
        self.client.log_param(run_id=self.run.info.run_id, key='model_version', value=model_versions[0].version)
        self.client.log_text(run_id=self.run.info.run_id, text=f"{input_schema}", artifact_file="input_schema.json")
        self.client.log_text(run_id=self.run.info.run_id, text=f"{output_schema}", artifact_file="output_schema.json")

        self.client.log_dict(run_id=self.run.info.run_id, dictionary=self.model.to_json(), artifact_file="model.json")
        self.client.log_param(run_id=self.run.info.run_id, key='features_num', value=len(self.features))
        self.client.log_text(run_id=self.run.info.run_id, text=f'{self.features}', artifact_file='features.json')
        self.client.log_param(run_id=self.run.info.run_id, key='num_step', value=self.num_step)
        self.client.log_param(run_id=self.run.info.run_id, key='cell_size', value=self.cell_size)

    async def __call__(self, request: Request):
        timestamp = int(time.time() * 1000)
        self.current_step += 1
        self.batches_processed += 1
        self.metrics += [
            Metric(key='batches_processed', value=self.batches_processed, timestamp=timestamp, step=self.current_step),
        ]

        try:
            obs, batch_size, anomaly_threshold, tag = await self._process_request_data(request)
            self.metrics += [
                Metric(key=f'batch_size_{tag}', value=batch_size, timestamp=timestamp, step=self.current_step),
                Metric(key=f'anomaly_threshold_{tag}', value=anomaly_threshold, timestamp=timestamp, step=self.current_step),
            ]

            obs_labeled = await self.predict(obs, batch_size, anomaly_threshold, tag)
            res = await self._process_response_data(obs_labeled)
            anomaly_detected = obs_labeled[LABEL].sum()
            self.batches_success += 1
            self.anomaly_detected += anomaly_detected
            self.metrics += [
                Metric(key='anomaly_detected', value=int(self.anomaly_detected), timestamp=timestamp, step=self.current_step),
                Metric(key='batches_success', value=self.batches_success, timestamp=timestamp, step=self.current_step),
                Metric(key=f'anomaly_detected_{tag}', value=int(self.anomaly_detected), timestamp=timestamp, step=self.current_step),
            ]

            self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": res}, artifact_file="last_action.json")
            if len(self.metrics) > 0:
                self._log_metrics()

            return {'action': res}
        except Exception as e:
            self.client.log_text(run_id=self.run.info.run_id,
                                 text=traceback.format_exc(),
                                 artifact_file=f"predict_error_{time.time() * 1000}.txt")
            if len(self.metrics) > 0:
                self._log_metrics()
            raise e

    async def predict(self, df: DataFrame, batch_size: int, anomaly_threshold: float = 0.5, tag: str = 'anonymous') -> DataFrame:
        df_norm = self.norm_model.predict(df)
        padding_features = set(self.features) - set(df_norm.columns)
        for f in padding_features:
            df_norm[f] = 0.

        df_norm = df_norm[self.features]

        features_num = len(self.features)
        batch_size_padding = max(5 - batch_size, 0)  # batch size should greater than or equal 5 to avoid error on GPU
        x_padding = np.full(batch_size_padding * features_num, fill_value=0).reshape((batch_size_padding, features_num))

        seq_len = batch_size + batch_size_padding
        timestamp = int(time.time() * 1000)
        self.metrics += [
            Metric(key=f'padding_len_{tag}', value=len(padding_features), timestamp=timestamp, step=self.current_step),
            Metric(key=f'seq_len_{tag}', value=seq_len, timestamp=timestamp, step=self.current_step),
        ]

        x = np.concatenate((df_norm.to_numpy(), x_padding)).reshape((self.num_step, seq_len, features_num))

        # BLAST gpu errors, or invalid access element at [index] errors might occur for invalid seq_len shape
        s = np.full(self.num_step, fill_value=seq_len, dtype=np.int32)
        self.l, y, self.h, self.c = self.model.predict(x=[x, s, self.h, self.c])

        df[LABEL] = pd.DataFrame(y[0:batch_size].flatten('C')).apply(lambda i: 1 if i.item() > anomaly_threshold else 0, axis=1)
        return df

    async def _process_request_data(self, request: Request) -> (DataFrame, int, float, str):
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, text=body.decode("utf-8"), artifact_file="last_request.json")

        data = json.loads(body)
        tag = str(data['tag']) if data['tag'] else 'anonymous'
        anomaly_threshold = float(data['anomaly_threshold']) if data['anomaly_threshold'] else 0.5
        df = DataFrame.from_dict(data['obs'])
        # batch_size = int(data['batch_size'])
        batch_size = df.index.size
        df = df[self.features]

        self.client.set_tag(run_id=self.run.info.run_id, key='infer', value=tag)

        return df, batch_size, anomaly_threshold, tag

    async def _process_response_data(self, labeled_data: DataFrame) -> dict:
        return labeled_data[[LABEL]].to_dict(orient="list")

    def _log_metrics(self):
        try:
            self.client.log_batch(run_id=self.run.info.run_id, metrics=self.metrics)
            self.metrics = []
        except Exception as e:
            utils.write_failsafe_metrics(f"{self.run.info.artifact_uri}/metrics_{int(time.time() * 1000)}.csv", self.metrics)
            self.metrics = []
            log.error('_log_metrics error %s', e)
