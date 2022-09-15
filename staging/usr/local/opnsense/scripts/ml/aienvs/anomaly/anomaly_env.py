import time
import gym
import ray
from gym.spaces import Discrete, Box
import numpy as np
from mlflow.entities import Metric

import common
import lib.utils as utils
from lib.ciccsvdatasource import CicCSVDatasource
from lib.logger import log

from pyarrow import csv
from typing import Iterator
# @ray.remote
from ray.data.dataset import Dataset, BatchType
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel


class AnomalyEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, dataset: Dataset, config: dict = None):
        config = config or {}

        self.blocks_per_window: int = config.get("batch_size", 1000)
        self.partition_num_blocks: int = 8
        self.batch_size: int = config.get("batch_size", 1000)
        self.episode_len: int = config.get("episode_len", 100)
        self.current_obs = None
        self.current_step: int = 0
        self.reward_total: float = 0
        self.anomaly_detected: float = 0

        self.metrics: [Metric] = []
        self._run, self._client = common.init_experiment(name='anomaly-env', run_name='env-tuning-%s' % time.time(),
                                                         skip_init_node=True)
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='env-tuning')

        self.dataset: Dataset = dataset
        self.anomaly_total: float = 0  # self.dataset.sum(LABEL)
        self.iter: Iterator[BatchType] = self.dataset\
            .repartition(num_blocks=self.partition_num_blocks)\
            .window(blocks_per_window=self.blocks_per_window)\
            .iter_batches(batch_size=self.batch_size, batch_format='pandas')

        self.observation_space: Box = Box(low=0., high=1., shape=(6,), dtype=np.float64)
        self.action_space: Discrete = Discrete(2)

        self._client.log_param(run_id=self._run.info.run_id, key='blocks_per_window', value=self.blocks_per_window)
        self._client.log_param(run_id=self._run.info.run_id, key='batch_size', value=self.batch_size)
        self._client.log_param(run_id=self._run.info.run_id, key='episode_len', value=self.episode_len)
        self._client.log_param(run_id=self._run.info.run_id, key='anomaly_total', value=self.anomaly_total)

    def reset(self):
        self.current_obs = None
        self.current_step = 0
        self.reward_total = 0
        self.anomaly_detected = 0
        self.iter = self.dataset.repartition(num_blocks=self.partition_num_blocks, shuffle=True).window(
            blocks_per_window=self.blocks_per_window).iter_batches(batch_size=self.batch_size)

        self.metrics += [
            Metric(key='reward_total', value=self.reward_total, timestamp=int(time.time() * 1000), step=self.current_step),
            Metric(key='anomaly_detected', value=self.anomaly_detected, timestamp=int(time.time() * 1000), step=self.current_step)
        ]

        return self._next_obs()

    def step(self, action: np.float64):
        self.current_step += 1
        reward = self._calculate_reward(action=action)
        self.reward_total += reward

        self.metrics += [
            Metric(key='action', value=action, timestamp=int(time.time() * 1000), step=self.current_step),
            Metric(key='reward', value=reward, timestamp=int(time.time() * 1000), step=self.current_step),
            Metric(key='reward_total', value=self.reward_total, timestamp=int(time.time() * 1000), step=self.current_step),
            Metric(key='anomaly_detected', value=self.anomaly_detected, timestamp=int(time.time() * 1000), step=self.current_step)
        ]

        if len(self.metrics) > 1000:
            self._log_metrics()

        done = (self.current_step > self.episode_len) or (self.current_obs is None)
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

        return token

    def close(self):
        self._log_metrics()
        self._client.set_terminated(run_id=self._run.info.run_id)

    def _calculate_reward(self, action: np.float64) -> float:
        if self.current_obs is None:
            return 0
        if action == self.current_obs[-1]:
            self.anomaly_detected += action
            return 1
        return -1

    def _log_metrics(self):
        try:
            self._client.log_batch(run_id=self._run.info.run_id, metrics=self.metrics)
            self.metrics = []
        except Exception as e:
            log.error('_log_metrics error %s', e)
