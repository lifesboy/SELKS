import json
import traceback

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
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, TOTLEN_FWD_PKTS, LABEL


@serve.deployment(name="AnomalyProductionDeployment",
                  num_replicas=2,
                  ray_actor_options={"num_cpus": 1, "num_gpus": 0.6})
class AnomalyProductionDeployment:

    def __init__(self) -> None:
        self.batches_processed: int = 0
        self.batches_success: int = 0
        self.feature_num: int = 6
        self.features: [] = [
            DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, TOTLEN_FWD_PKTS
        ]
        self.num_step: int = 1
        self.cell_size: int = 32
        self.l = None
        self.h = np.zeros((self.num_step, self.cell_size), dtype=np.float32)
        self.c = np.zeros((self.num_step, self.cell_size), dtype=np.float32)

        self.run, self.client = common.init_tracking(name='anomaly-production-deployment', run_name='anomaly-production-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="STARTED")
        self.model: Model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/production')
        self.client.log_dict(run_id=self.run.info.run_id, dictionary=self.model.to_json(), artifact_file="model.json")
        self.client.log_param(run_id=self.run.info.run_id, key='features_num', value=len(self.features))
        self.client.log_param(run_id=self.run.info.run_id, key='features', value=self.features)
        self.client.log_param(run_id=self.run.info.run_id, key='num_step', value=self.num_step)
        self.client.log_param(run_id=self.run.info.run_id, key='cell_size', value=self.cell_size)

    async def __call__(self, request: Request):
        self.batches_processed += 1
        self.client.log_metric(run_id=self.run.info.run_id, key="batches_processed", value=self.batches_processed)
        try:
            obs, batch_size = await self._process_request_data(request)
            obs_labeled = await self.predict(obs, batch_size)
            res = await self._process_response_data(obs_labeled)
            self.batches_success += 1

            self.client.log_metric(run_id=self.run.info.run_id, key="batch_size", value=batch_size)
            self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": res}, artifact_file="last_action.json")
            # self.client.log_metric(run_id=self.run.info.run_id, key="predict_counter", value=float(self.model._predict_counter))
            self.client.log_metric(run_id=self.run.info.run_id, key="batches_success", value=self.batches_success)
            return {'action': res}
        except Exception as e:
            self.client.log_text(run_id=self.run.info.run_id,
                                 text=traceback.format_exc(),
                                 artifact_file=f"predict_error_{time.time() * 1000}.txt")
            raise e

    async def predict(self, df: DataFrame, batch_size: int) -> DataFrame:
        features_num = len(self.features)
        batch_size_padding = max(5 - batch_size, 0)  # batch size should greater than or equal 5 to avoid error on GPU
        x_padding = np.full(batch_size_padding * features_num, fill_value=0).reshape((batch_size_padding, features_num))

        x = np.concatenate((df.to_numpy(), x_padding)).reshape((self.num_step, batch_size + batch_size_padding, features_num))
        s = np.full(self.num_step, fill_value=len(self.features) - 1, dtype=np.int32)
        self.l, y, self.h, self.c = self.model.predict(x=[x, s, self.h, self.c])

        df[LABEL] = pd.DataFrame(y[0:batch_size].flatten('C'))
        return df

    async def _process_request_data(self, request: Request) -> (DataFrame, int):
        body = await request.body()
        self.client.log_text(run_id=self.run.info.run_id, text=body.decode("utf-8"), artifact_file="last_request.json")

        data = json.loads(body)
        df = DataFrame.from_dict(data['obs'])
        # batch_size = int(data['batch_size'])
        batch_size = df.index.size
        df = df[self.features]
        return df, batch_size

    async def _process_response_data(self, labeled_data: DataFrame) -> dict:
        return labeled_data.to_dict(orient="list")
