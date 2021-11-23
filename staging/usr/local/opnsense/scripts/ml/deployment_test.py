import gym
from locust import HttpUser, between, task

import common

run, client = common.init_experiment('anomaly_deployment_test')
client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Start")


class AnomalyDeploymentModelTest(HttpUser):
    wait_time = between(5, 15)

    def on_start(self):
        client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Testing")

    @task
    def anomaly(self):
        env = gym.make("CartPole-v0")
        obs = env.reset()
        print(f"-> Sending observation {obs}")
        resp = self.client.get("http://selks.ddns.net:8989/anomaly", json={"observation": obs.tolist()})
        print(f"<- Received response {resp.json() if resp.ok else resp}")

# if __name__ == "__main__":
#     locust

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")

# Run: locust -f deployment_test.py
# Visit: http://0.0.0.0:8089/