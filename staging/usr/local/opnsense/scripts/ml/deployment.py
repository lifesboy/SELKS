import gym
from starlette.requests import Request
import requests

import ray.rllib.agents.ppo as ppo
from ray import serve

import common

run, client = common.init_experiment('anomaly_deployment')
client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="serve.start")

serve.start(http_options={"host": "0.0.0.0", "port": 8989})


# Our pipeline will be structured as follows:
# - Input comes in, the composed model sends it to model_one
# - model_one outputs a random number between 0 and 1, if the value is
#   greater than 0.5, then the data is sent to model_two
# - otherwise, the data is returned to the user.

# Let's define two models that just print out the data they received.


@serve.deployment
class ServeAnomalyPPOModel:
    def __init__(self, checkpoint_path) -> None:
        # self.run, self.client = common.init_experiment("anomaly_deployment")
        self.run, self.client = run, client
        self.trainer = ppo.PPOTrainer(
            config={
                "framework": "tf",
                # only 1 "local" worker with an env (not really used here).
                "num_workers": 0,
            },
            env="CartPole-v0")
        self.trainer.restore(checkpoint_path)

    async def __call__(self, data):
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL,
                            value='ServeAnomalyPPOModel')

        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"obs": data}, artifact_file="data.json")

        action = self.trainer.compute_action(data)
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": action}, artifact_file="data.json")

        return {"action": int(action)}


@serve.deployment
def model_two(data):
    # run2, client2 = common.init_experiment('anomaly_deployment')
    run2, client2 = run, client

    client2.set_tag(run_id=run2.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL, value='model_two')
    print("Model 2 called with data ", data)
    client2.log_dict(run_id=run2.info.run_id, dictionary={"obs": data}, artifact_file="data.json")
    client2.log_dict(run_id=run2.info.run_id, dictionary={"action": data}, artifact_file="data.json")
    return data


# max_concurrent_queries is optional. By default, if you pass in an async
# function, Ray Serve sets the limit to a high number.
@serve.deployment(max_concurrent_queries=10, route_prefix="/anomaly")
class ComposedModel:
    def __init__(self):
        # self.run, self.client = common.init_experiment("anomaly_deployment")
        self.run, self.client = run, client

        self.model_one = ServeAnomalyPPOModel.get_handle()
        self.model_two = model_two.get_handle()

    # This method can be called concurrently!
    async def __call__(self, starlette_request):
        self.client.set_tag(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_MODEL, value='ComposedModel')

        data = await starlette_request.json()
        observation = data["observation"]
        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"obs": observation}, artifact_file="data.json")

        score = await self.model_one.remote(data=observation)
        if not score:
            result = await self.model_two.remote(data=observation)
            result = {"model_used": 2, "score": result}
        else:
            result = {"model_used": 1, "score": score}

        self.client.log_dict(run_id=self.run.info.run_id, dictionary={"action": result}, artifact_file="data.json")
        # self.client.log_metric(run_id=self.run.info.run_id, key=common.TAG_DEPLOYMENT_RUN_ACTION, value=result)

        return result


client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="ServeAnomalyPPOModel.deploy")
ServeAnomalyPPOModel.deploy("/tmp/rllib_checkpoint/checkpoint_000001/checkpoint-1")

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="model_two.deploy")
model_two.deploy()

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="ComposedModel.deploy")
ComposedModel.deploy()

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Testing")
for _ in range(10):
    env = gym.make("CartPole-v0")
    obs = env.reset()
    print(f"-> Sending observation {obs}")
    resp = requests.get("http://0.0.0.0:8989/anomaly", json={"observation": obs.tolist()})
    print(f"<- Received response {resp.json()}")

client.set_tag(run_id=run.info.run_id, key=common.TAG_DEPLOYMENT_STATUS, value="Done")
