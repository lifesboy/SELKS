import gym
from gym.spaces import Discrete
import random


class AnomalyInitialObsEnv(gym.Env):
    """Env in which the initial observation has to be repeated all the time.

    Runs for n steps.
    r=1 if action correct, -1 otherwise (max. R=100).
    """

    def __init__(self, config: dict = None):
        self.observation_space = Discrete(2)
        self.action_space = Discrete(2)
        self.token = None
        self.episode_len: int = config.get("episode_len", 100)
        self.num_steps = 0

    def reset(self):
        self.token = random.choice([0, 1])
        self.num_steps = 0
        return self.token

    def step(self, action):
        if action == self.token:
            reward = 1
        else:
            reward = -1
        self.num_steps += 1
        done = self.num_steps >= self.episode_len
        return 0, reward, done, {}
