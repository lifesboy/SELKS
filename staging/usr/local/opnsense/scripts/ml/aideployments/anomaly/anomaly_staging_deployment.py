import mlflow
import time

from ray import serve

import common
from aimodels.anomaly.anomaly_model import AnomalyModel


@serve.deployment(name="AnomalyStagingDeployment",
                  num_replicas=10,
                  ray_actor_options={"num_cpus": 0.01, "num_gpus": 0.01})
class AnomalyStagingDeployment:

    def __init__(self) -> None:
        self.run, self.client = common.init_tracking(name='anomaly-staging-deployment', run_name='anomaly-staging-%s' % time.time())
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
        self.model = mlflow.keras.load_model(f'models:/{AnomalyModel.get_model_meta().registered_model_name}/staging')

    async def __call__(self, data):
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL, value='ServeAnomalyPPOModel')
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"obs": data}, artifact_file="data.json")

        action = self.model.predict(data)
        action = float(action)
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": action}, artifact_file="data.json")

        return {'action': action}


serve.start(http_options={"host": common.MODEL_SERVE_ADDRESS, "port": common.MODEL_SERVE_PORT})
