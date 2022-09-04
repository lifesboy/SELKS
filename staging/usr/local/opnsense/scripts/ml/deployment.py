import gym
import requests
import random
import time

from ray import serve

import common
from aideployments.anomaly.anomaly_staging_deployment import AnomalyStagingDeployment
from aideployments.anomaly.anomaly_production_deployment import AnomalyProductionDeployment

run, client = common.init_experiment(name='anomaly-deployment', run_name='deployment-deployment-%s' % time.time())

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
serve.start(http_options={'host': common.MODEL_SERVE_ADDRESS, 'port': common.MODEL_SERVE_PORT})

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyStagingDeployment.deploy')
AnomalyStagingDeployment.options(name='anomaly-staging').deploy()

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyProductionDeployment.deploy')
AnomalyProductionDeployment.options(name='anomaly-production').deploy()

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='Testing')
for endpoint in ['anomaly-staging', 'anomaly-production']:
    for _ in range(100):
        env = gym.make('CartPole-v0')
        obs = env.reset()
        print(f'-> Sending /{endpoint} observation {obs}')
        resp = requests.post(f'http://selks.ddns.net:6789/{endpoint}', json={'obs': obs.tolist()})
        print(f"<- Received /{endpoint} response {resp.json() if resp.ok else resp}")
        time.sleep(random.randint(1, 5))

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")
