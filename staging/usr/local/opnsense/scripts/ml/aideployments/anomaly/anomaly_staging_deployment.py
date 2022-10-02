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


@serve.deployment(name="AnomalyStagingDeployment",
                  num_replicas=1,
                  ray_actor_options={"num_cpus": 0.01, "num_gpus": 0.01})
class AnomalyStagingDeployment:

    def __init__(self) -> None:
        self.called = 0
        self.feature_num: int = 6
        self.batch_num: int = 1
        self.batch_size: int = 5
        self.cell_size: int = 32
        self.l = None
        self.h = np.zeros((self.batch_num, self.cell_size), dtype=np.float32)
        self.c = np.zeros((self.batch_num, self.cell_size), dtype=np.float32)

        self.run, self.client = common.init_tracking(name='anomaly-staging-deployment', run_name='anomaly-staging-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        self.model: Model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/staging')
        self.client.log_dict(run_id=self.run.info.run_id, dictionary=self.model.to_json(), artifact_file="model.json")

    async def __call__(self, request: Request):
        self.called += 1
        self.client.log_metric(run_id=self.run.info.run_id, key="called", value=self.called)

        obs: DataFrame = await self._process_request_data(request)
        obs_labeled = await self.predict(obs)
        res = await self._process_response_data(obs_labeled)

        # self.client.log_metric(run_id=self.run.info.run_id, key="predict_counter", value=float(self.model._predict_counter))
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": res}, artifact_file="last_action.json")

        return {'action': res}

    async def predict(self, df: DataFrame) -> DataFrame:
        x = df.to_numpy().reshape(self.batch_num, self.batch_size, self.feature_num)
        s = np.full(self.batch_num, fill_value=self.feature_num - 1, dtype=np.int32)
        self.l, y, self.h, self.c = self.model.predict(x=[x, s, self.h, self.c])
        df[LABEL] = pd.DataFrame(y.flatten('C'))
        return df

    async def _process_request_data(self, request: Request) -> DataFrame:
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, text=body.decode("utf-8"), artifact_file="last_request.json")

        data = json.loads(body)
        df = DataFrame.from_dict(data['obs'])
        df = df[[DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL]]
        return df

    async def _process_response_data(self, labeled_data: DataFrame) -> dict:
        return labeled_data.to_dict(orient="list")
