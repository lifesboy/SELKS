import json

import mlflow
import time
import pandas as pd

from ray import serve
from starlette.requests import Request

import common
from aimodels.anomaly.anomaly_model import AnomalyModel


@serve.deployment(name="AnomalyProductionDeployment",
                  num_replicas=2,
                  ray_actor_options={"num_cpus": 0.01, "num_gpus": 0.01})
class AnomalyProductionDeployment:

    def __init__(self) -> None:
        self.run, self.client = common.init_tracking(name='anomaly-production-deployment', run_name='anomaly-production-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        self.model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/production')

    async def __call__(self, request: Request):
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL, value='CALLED')

        obs = await self._process_request_data(request)
        action = self.model.predict(obs).to_json(orient="records")

        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": action}, artifact_file="last_action.json")

        return {'action': action}

    async def predict(self, df):
        return self.model.predict(df).to_json(orient="records")

    async def _process_request_data(self, request: Request):
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, dictionary=body, artifact_file="last_request.json")

        data = json.loads(body)
        return data['obs']
