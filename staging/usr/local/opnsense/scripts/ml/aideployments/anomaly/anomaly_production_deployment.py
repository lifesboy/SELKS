import json

import mlflow
import time
import numpy as np
import pandas as pd
from keras.models import Model
from pandas import DataFrame

from ray import serve
from starlette.requests import Request

import common
from aimodels.anomaly.anomaly_model import AnomalyModel
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL


@serve.deployment(name="AnomalyProductionDeployment",
                  num_replicas=2,
                  ray_actor_options={"num_cpus": 0.01, "num_gpus": 1})
class AnomalyProductionDeployment:

    def __init__(self) -> None:
        self.called = 0
        self.feature_num: int = 6
        self.num_step: int = 1
        self.cell_size: int = 32
        self.l = None
        self.h = np.zeros((self.num_step, self.cell_size), dtype=np.float32)
        self.c = np.zeros((self.num_step, self.cell_size), dtype=np.float32)

        self.run, self.client = common.init_tracking(name='anomaly-production-deployment', run_name='anomaly-production-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        self.model: Model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/staging')
        self.client.log_dict(run_id=self.run.info.run_id, dictionary=self.model.to_json(), artifact_file="model.json")
        self.client.log_param(run_id=self.run.info.run_id, key='feature_num', value=self.feature_num)
        self.client.log_param(run_id=self.run.info.run_id, key='num_step', value=self.num_step)
        self.client.log_param(run_id=self.run.info.run_id, key='cell_size', value=self.cell_size)

    async def __call__(self, request: Request):
        self.called += 1
        obs, batch_size = await self._process_request_data(request)
        obs_labeled = await self.predict(obs, batch_size)
        res = await self._process_response_data(obs_labeled)

        self.client.log_metric(run_id=self.run.info.run_id, key="batch_size", value=batch_size)
        # self.client.log_metric(run_id=self.run.info.run_id, key="predict_counter", value=float(self.model._predict_counter))
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": res}, artifact_file="last_action.json")

        return {'action': res}

    async def predict(self, df: DataFrame, batch_size: int) -> DataFrame:
        x = df.to_numpy().reshape(self.num_step, batch_size, self.feature_num)
        s = np.full(self.num_step, fill_value=self.feature_num - 1, dtype=np.int32)
        self.l, y, self.h, self.c = self.model.predict(x=[x, s, self.h, self.c])
        df[LABEL] = pd.DataFrame(y.flatten('C'))
        return df

    async def _process_request_data(self, request: Request) -> (DataFrame, int):
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, text=body.decode("utf-8"), artifact_file="last_request.json")

        data = json.loads(body)
        batch_size = int(data['batch_size'])
        df = DataFrame.from_dict(data['obs'])
        df = df[[DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL]]
        return df, batch_size

    async def _process_response_data(self, labeled_data: DataFrame) -> dict:
        return labeled_data.to_dict(orient="list")
