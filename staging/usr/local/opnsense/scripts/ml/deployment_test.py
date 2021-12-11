import gym
import os
import sys
from locust import HttpUser, between, task, events

import common

# make sure the helper utilities are importable
sys.path.append(os.getcwd())

run, client = None, None


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--data-source", type=str, include_in_web_ui=True, default="", help="Data source to test")
    # Set `include_in_web_ui` to False if you want to hide from the web UI
    parser.add_argument("--serving-url", type=str, include_in_web_ui=True, default="", help="Serving url to test")


@events.test_start.add_listener
def _(environment, **kw):
    print("Custom argument supplied: data_source=%s" % environment.parsed_options.data_source)
    print("Custom argument supplied: serving_url=%s" % environment.parsed_options.serving_url)

    global run, client
    #run, client = common.init_experiment('anomaly_deployment_test')
    #client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_TEST_STATUS, value="Start")


@events.test_stop.add_listener
def _(environment, **kw):
    global run, client
    #client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_TEST_STATUS, value="Done")


class AnomalyDeploymentModelTest(HttpUser):
    wait_time = between(5, 15)

    def on_start(self):
        self.ml_run, self.ml_client = common.init_experiment('anomaly_deployment_test')
        self.ml_client.set_tag(run_id=self.ml_run.info.run_id, key=common.TAG_DEPLOYMENT_TEST_STATUS, value="Testing")

    def on_stop(self):
        self.ml_client.set_tag(run_id=self.ml_run.info.run_id, key=common.TAG_DEPLOYMENT_TEST_STATUS, value="Done")

    @task
    def anomaly(self):
        env = gym.make("CartPole-v0")
        obs = env.reset()
        print(f"-> Sending observation {obs}")
        resp = self.client.get("http://selks.ddns.net:6789/anomaly", json={"observation": obs.tolist()})
        print(f"<- Received response {resp.json() if resp.ok else resp}")

# if __name__ == "__main__":
#     locust

# Run: locust -f deployment_test.py
# Visit: http://0.0.0.0:8089/
