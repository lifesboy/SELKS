import json

import mlflow
import time
import pandas as pd
from keras.models import Model
from pandas import DataFrame

from ray import serve
from starlette.requests import Request

import common
from aimodels.anomaly.anomaly_model import AnomalyModel
from anomaly_normalization import LABEL


@serve.deployment(name="AnomalyStagingDeployment",
                  num_replicas=1,
                  ray_actor_options={"num_cpus": 0.01, "num_gpus": 0.01})
class AnomalyStagingDeployment:

    def __init__(self) -> None:
        self.run, self.client = common.init_tracking(name='anomaly-staging-deployment', run_name='anomaly-staging-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        self.model: Model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/staging')

    async def __call__(self, request: Request):
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL, value='CALLED')

        obs: DataFrame = await self._process_request_data(request)
        obs_labeled = await self.predict(obs)
        res = await self._process_response_data(obs_labeled)

        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": res}, artifact_file="last_action.json")

        return {'action': res}

    async def predict(self, df: DataFrame) -> DataFrame:
        actions = self.model.predict(df)
        df[LABEL] = df.apply(lambda i: 1)
        return df

    async def _process_request_data(self, request: Request) -> DataFrame:
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, text=body.decode("utf-8"), artifact_file="last_request.json")

        data = json.loads(body)
        df = DataFrame.from_dict(data['obs'])
        return df

    async def _process_response_data(self, labeled_data: DataFrame) -> dict:
        return labeled_data.to_dict(orient="list")
