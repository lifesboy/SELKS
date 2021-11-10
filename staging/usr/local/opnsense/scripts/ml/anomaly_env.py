import gym
import ray
from gym.spaces import Discrete
import random


# @ray.remote
from ray.data.dataset_pipeline import DatasetPipeline

import common
from anomaly_normalization import DST_PORT, PROTOCOL, TIMESTAMP, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL


class AnomalyEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, config=None):
        config = config or {}
        batch_size = 10240
        num_gpus = 0.2
        num_cpus = 0.5
        parallelism = 5
        data_source = [
            # common.TRAIN_DATA_DIR + 'demo.csv',
            # common.TRAIN_DATA_DIR + 'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
            # common.TRAIN_DATA_DIR + 'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
            # common.TRAIN_DATA_DIR + 'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
            common.TMP_DIR + 'processed_data_20211108T142556/c5ba958bdad34eab855d2dabe385814a_000000_000000.csv',
            # common.TRAIN_DATA_DIR + 'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv', # error value Dst Port
        ]
        pipe: DatasetPipeline = ray.data.read_csv(data_source).window(blocks_per_window=batch_size)
        self.observation_space = pipe
        self.action_space = Discrete(2)
        # Note: Set `repeat_delay` to 0 for simply repeating the seen
        # observation (no delay).
        self.delay = config.get("repeat_delay", 1)
        self.episode_len = config.get("episode_len", 100)
        self.history = []

    def reset(self):
        self.history = [0] * self.delay
        return self._next_obs()

    def step(self, action):
        if action == self.history[-(1 + self.delay)]:
            reward = 1
        else:
            reward = -1
        done = len(self.history) > self.episode_len
        return self._next_obs(), reward, done, {}

    def _next_obs(self):
        token = self.observation_space.take(1)[LABEL]
        self.history.append(token)
        return token
