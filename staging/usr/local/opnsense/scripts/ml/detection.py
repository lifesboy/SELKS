import gym
from starlette.requests import Request
import requests
import random
import time

import ray.rllib.agents.ppo as ppo
from ray import serve

import common

for _ in range(1000):
    env = gym.make("CartPole-v0")
    obs = env.reset()
    print(f"-> Sending observation {obs}")
    resp = requests.get(common.MODEL_SERVE_DETECTION_URL, json={"observation": obs.tolist()})
    print(f"<- Received response {resp.json() if resp.ok else resp}")
    time.sleep(random.randint(1, 5))
