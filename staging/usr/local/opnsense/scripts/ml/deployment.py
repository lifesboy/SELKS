import gym
import requests
import random
import time

from ray import serve

import common
from aideployments.anomaly.anomaly_staging_deployment import AnomalyStagingDeployment

run, client = common.init_experiment(name='anomaly-deployment', run_name='deployment-deployment-%s' % time.time())

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")
serve.start(http_options={'host': common.MODEL_SERVE_ADDRESS, 'port': common.MODEL_SERVE_PORT})

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='AnomalyStagingDeployment.deploy')
AnomalyStagingDeployment.options(name='anomaly-staging').deploy()

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value='Testing')
for _ in range(100):
    env = gym.make('CartPole-v0')
    obs = env.reset()
    print(f'-> Sending observation {obs}')
    resp = requests.post('http://selks.ddns.net:6789/anomaly-staging', json={'observation': obs.tolist()})
    print(f"<- Received response {resp.json() if resp.ok else resp}")
    time.sleep(random.randint(1, 5))

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")
