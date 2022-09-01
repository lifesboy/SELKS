import time
import gym
import ray
from gym.spaces import Discrete, Box
import numpy as np
import common


# @ray.remote
from ray.data import Dataset
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL


class AnomalyEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, config=None):
        self._run, self._client = common.init_experiment(name='anomaly-model', run_name='env-tuning-%s' % time.time())
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='env-tuning')
        config = config or {}
        self.data_source_sampling_dir = config.get("data_source_sampling_dir", [])
        self.data_set: Dataset = ray.data.read_csv(self.data_source_sampling_dir)

        self.iter = self.data_set.window(blocks_per_window=1024).iter_batches(batch_size=1)

        self.observation_space = Box(low=0., high=1., shape=(6,), dtype=np.float64)
        self.action_space = Discrete(2)

        self.episode_len = config.get("episode_len", 100)
        self.current_obs = None
        self.current_len = 0

    def reset(self):
        self.current_obs = None
        self.current_len = 0
        self.iter = self.data_set.window(blocks_per_window=1024).iter_batches(batch_size=1)
        return self._next_obs()

    def step(self, action):
        if (self.current_obs is None) or (action == self.current_obs[-1]):
            reward = 1
        else:
            reward = -1
        done = (self.current_len > self.episode_len) or (self.current_obs is None)
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
            np.float64) if i is not None else None
        self.current_obs = token
        self.current_len += 1
        return token
