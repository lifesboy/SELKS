import time
import gym
from gym.spaces import Discrete, Box
import numpy as np
from mlflow.entities import Metric

import common
from aienvs.anomaly_spec import AnomalySpec
from lib.logger import log
from pandas import DataFrame

from typing import Iterator
# @ray.remote
from ray.data.dataset import Dataset, BatchType
from anomaly_normalization import DST_PORT, PROTOCOL, FLOW_DURATION, TOT_FWD_PKTS, TOT_BWD_PKTS, TOTLEN_FWD_PKTS, LABEL


class AnomalyMinibatchGlobalShuffleEnv(gym.Env):
    """Env in which the observation at timestep minus n must be repeated."""

    def __init__(self, dataset: Dataset, context_data: dict, config: dict = None):
        config = config or {}

        self.blocks_per_window: int = 1
        self.batch_size: int = config.get("batch_size", 1000)
        self.episode_len: int = config.get("episode_len", 100)
        self.current_batch: DataFrame = None
        self.current_obs = None
        self.current_action = None
        self.current_step: int = 0
        self.reward_total: float = 0
        self.anomaly_detected: int = 0
        self.anomaly_incorrect: int = 0
        self.clean_detected: int = 0
        self.clean_incorrect: int = 0

        self.metrics: [Metric] = []
        self._run, self._client = common.init_experiment(name='anomaly-env', run_name=f"{common.get_second()}",
                                                         skip_init_node=True)
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='env-tuning')
        self.spec: AnomalySpec = AnomalySpec(self._run.info.run_id, context_data)

        self.dataset: Dataset = dataset \
            .window(blocks_per_window=self.blocks_per_window)
        self.dataset_size: int = context_data.get("dataset_size")
        self.anomaly_total: float = context_data.get("anomaly_total")
        self.features: [] = context_data.get("features")
        self.iter: Iterator[BatchType] = None

        self.observation_space: Box = Box(low=-1., high=1., shape=(len(self.features),), dtype=np.float64)
        self.action_space: Discrete = Discrete(2)

        self._client.log_param(run_id=self._run.info.run_id, key='name', value=type(self).__name__)
        self._client.log_param(run_id=self._run.info.run_id, key='blocks_per_window', value=self.blocks_per_window)
        self._client.log_param(run_id=self._run.info.run_id, key='batch_size', value=self.batch_size)
        self._client.log_param(run_id=self._run.info.run_id, key='episode_len', value=self.episode_len)
        self._client.log_param(run_id=self._run.info.run_id, key='dataset_size', value=self.dataset_size)
        self._client.log_param(run_id=self._run.info.run_id, key='anomaly_total', value=self.anomaly_total)
        self._client.log_param(run_id=self._run.info.run_id, key='features_num', value=len(self.features))
        self._client.log_text(run_id=self._run.info.run_id, text=f'{self.features}', artifact_file='features.json')

    def reset(self) -> [np.float64]:
        self.current_obs = None
        self.current_step = 0
        self.reward_total = 0
        self.anomaly_detected = 0
        self.anomaly_incorrect = 0
        self.clean_detected = 0
        self.clean_incorrect = 0

        timestamp = int(time.time() * 1000)
        self.metrics += [
            Metric(key='reward_total', value=self.reward_total, timestamp=timestamp, step=self.current_step),
            Metric(key='anomaly_detected', value=self.anomaly_detected, timestamp=timestamp, step=self.current_step),
            Metric(key='anomaly_incorrect', value=self.anomaly_incorrect, timestamp=timestamp, step=self.current_step),
            Metric(key='clean_detected', value=self.clean_detected, timestamp=timestamp, step=self.current_step),
            Metric(key='clean_incorrect', value=self.clean_incorrect, timestamp=timestamp, step=self.current_step)
        ]

        self.iter: Iterator[BatchType] = self.dataset.random_shuffle() \
            .iter_batches(batch_size=self.batch_size, batch_format='pandas')
        return self._next_obs()

    def step(self, action: np.int32):
        self.current_step += 1
        reward = self._calculate_reward(action=action)
        self.reward_total += reward
        done = (self.current_step > self.episode_len) or (self.current_obs is None)

        timestamp = int(time.time() * 1000)
        self.metrics += [
            Metric(key='action_expected', value=self.current_action[0], timestamp=timestamp, step=self.current_step),
            Metric(key='action', value=action, timestamp=timestamp, step=self.current_step),
            Metric(key='reward', value=reward, timestamp=timestamp, step=self.current_step),
            Metric(key='reward_total', value=self.reward_total, timestamp=timestamp, step=self.current_step),
            Metric(key='anomaly_detected', value=self.anomaly_detected, timestamp=timestamp, step=self.current_step),
            Metric(key='anomaly_incorrect', value=self.anomaly_incorrect, timestamp=timestamp, step=self.current_step),
            Metric(key='clean_detected', value=self.clean_detected, timestamp=timestamp, step=self.current_step),
            Metric(key='clean_incorrect', value=self.clean_incorrect, timestamp=timestamp, step=self.current_step)
        ]

        if done or len(self.metrics) > 1000:
            self._log_metrics()

        return self._next_obs(), reward, done, {}

    def _next_obs(self) -> [np.float64]:
        self.current_batch: DataFrame = next(self.iter).fillna(0.)

        if self.current_batch is None or self.current_batch.empty:
            self.current_obs = None
            return None

        seq_len = self.current_batch.index.size
        token = self.current_batch[self.features].to_numpy(dtype=np.float64).reshape((seq_len, len(self.features)))
        self.current_obs = token
        self.current_action = self.current_batch[LABEL].to_numpy(dtype=np.int32).reshape((seq_len, 1))

        return token

    def close(self):
        self._log_metrics()
        self._client.set_terminated(run_id=self._run.info.run_id)

    def _calculate_reward(self, action: [np.int32]) -> float:
        if self.current_obs is None:
            return 0

        self.anomaly_detected += np.sum(np.prod([action, self.current_action], axis=0))
        reward = np.sum(np.logical_xor([action, self.current_action], axis=0))

        if action == self.current_action[0]:
            if action == 1:
                self.anomaly_detected += 1
            else:
                self.clean_detected += 1
            return 1

        if action == 1:
            self.clean_incorrect += 1
        else:
            self.anomaly_incorrect += 1
        return -1

    def _log_metrics(self):
        try:
            self._client.log_batch(run_id=self._run.info.run_id, metrics=self.metrics)
            self.metrics = []
        except Exception as e:
            log.error('_log_metrics error %s', e)
