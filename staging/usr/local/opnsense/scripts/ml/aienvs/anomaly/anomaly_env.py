import gym
import ray
from ray.data.datasource.file_meta_provider import FastFileMetadataProvider
from gym.spaces import Discrete, Box
import numpy as np


# @ray.remote
from ray.data import Dataset
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL


class AnomalyEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, config=None):
        config = config or {}
        self.data_source_files = config.get("data_source_files", [])
        self.data_set: Dataset = ray.data.read_csv(self.data_source_files, meta_provider=FastFileMetadataProvider())

        self.iter = self.data_set.window(blocks_per_window=1024).iter_batches(batch_size=1)

        self.observation_space = Box(low=0., high=1., shape=(6,), dtype=np.float32)
        self.action_space = Discrete(2)

        self.episode_len = config.get("episode_len", 100)
        self.history = []

    def reset(self):
        self.history = []
        self.iter = self.data_set.window(blocks_per_window=1024).iter_batches(batch_size=1)
        return self._next_obs()

    def step(self, action):
        if (self.history[-1] is None) or (action == self.history[-1][-1]):
            reward = 1
        else:
            reward = -1
        done = (len(self.history) > self.episode_len) or (self.history[-1] is None)
        return self._next_obs(), reward, done, {}

    def _next_obs(self):
        i = next(self.iter)
        token = np.array([
            i[DST_PORT].item(),
            i[PROTOCOL].item(),
            i[FLOW_DURATION].item(),
            i[TOT_FWD_PKTS].item(),
            i[TOT_BWD_PKTS].item(),
            i[LABEL].item()],
            np.float32) if i is not None else None
        self.history.append(token)
        return token
