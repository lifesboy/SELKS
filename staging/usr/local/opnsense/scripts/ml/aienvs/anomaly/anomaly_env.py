import time
import gym
import ray
from gym.spaces import Discrete, Box
import numpy as np
import common
import lib.utils as utils
from lib.logger import log

from pyarrow import csv
from typing import Iterator
# @ray.remote
from ray.data.dataset import Dataset, BatchType
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, LABEL
from aimodels.preprocessing.cicflowmeter_norm_model import CicFlowmeterNormModel


class AnomalyEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, config: dict = None):
        config = config or {}

        self.blocks_per_window: int = 1024
        self.batch_size: int = 1
        self.episode_len: int = config.get("episode_len", 100)
        self.current_obs = None
        self.current_step: int = 0
        self.reward_total: float = 0
        self.anomaly_detected: float = 0
        self.data_source_sampling_dir: str = config.get("data_source_sampling_dir", '')

        if not utils.is_ray_gpu_ready():
            log.warning('init anomaly env restart ray failing ray: %s', self.data_source_sampling_dir)
            utils.restart_ray_service()

        self._run, self._client = common.init_experiment(name='anomaly-model', run_name='env-tuning-%s' % time.time())
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='env-tuning')

        schema = CicFlowmeterNormModel.get_input_schema()
        convert_options = csv.ConvertOptions(column_types=schema)
        self.data_set: Dataset = ray.data.read_csv(self.data_source_sampling_dir, convert_options=convert_options)

        self.anomaly_total: float = self.data_set.sum(LABEL)
        self.iter: Iterator[BatchType] = self.data_set.window(
            blocks_per_window=self.blocks_per_window).iter_batches(batch_size=self.batch_size)

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
        self.iter = self.data_set.random_shuffle().window(
            blocks_per_window=self.blocks_per_window).iter_batches(batch_size=self.batch_size)

        self._client.log_metric(run_id=self._run.info.run_id, key='reward_total', value=self.reward_total, step=self.current_step)
        self._client.log_metric(run_id=self._run.info.run_id, key='anomaly_detected', value=self.anomaly_detected, step=self.current_step)

        return self._next_obs()

    def step(self, action: np.float64):
        reward = self._calculate_reward(action=action)

        self.reward_total += reward
        self._client.log_metric(run_id=self._run.info.run_id, key='action', value=action, step=self.current_step)
        self._client.log_metric(run_id=self._run.info.run_id, key='reward', value=reward, step=self.current_step)
        self._client.log_metric(run_id=self._run.info.run_id, key='reward_total', value=self.reward_total, step=self.current_step)

        done = (self.anomaly_total == self.anomaly_detected) or (self.current_step > self.episode_len) or (self.current_obs is None)
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
        self.current_step += 1

        return token

    def close(self):
        self._client.set_terminated(run_id=self._run.info.run_id)

    def _calculate_reward(self, action: np.float64) -> float:
        if self.current_obs is None:
            return 0
        if action == self.current_obs[-1]:
            self.anomaly_detected += action
            return 1
        return -1
