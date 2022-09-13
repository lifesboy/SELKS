import time

import gym
from gym.spaces import Discrete
import random

import common


class AnomalyRandomEnv(gym.Env):
    """Env in which the initial observation has to be repeated all the time.

    Runs for n steps.
    r=1 if action correct, -1 otherwise (max. R=100).
    """

    def __init__(self, config: dict = None):
        config = config or {}

        self.observation_space = Discrete(2)
        self.action_space = Discrete(2)
        self.episode_len: int = config.get("episode_len", 100)
        self.current_obs: float = None
        self.current_step: int = 0
        self.reward_total: float = 0

        self._run, self._client = common.init_experiment(name='anomaly-random-env', run_name='env-tuning-%s' % time.time(),
                                                         skip_init_node=True)
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='env-tuning')

    def reset(self):
        self.current_obs = None
        self.current_step = 0
        self.reward_total = 0

        self._client.log_metric(run_id=self._run.info.run_id, key='reward_total', value=self.reward_total,
                                step=self.current_step)

        return self._next_obs()

    def step(self, action: float):
        self.current_step += 1
        reward = self._calculate_reward(action=action)
        self.reward_total += reward

        self._client.log_metric(run_id=self._run.info.run_id, key='action', value=action, step=self.current_step)
        self._client.log_metric(run_id=self._run.info.run_id, key='reward', value=reward, step=self.current_step)
        self._client.log_metric(run_id=self._run.info.run_id, key='reward_total', value=self.reward_total,
                                step=self.current_step)

        done = self.current_step > self.episode_len
        return self._next_obs(), reward, done, {}

    def _next_obs(self):
        token = random.choice([0, 1])
        self.current_obs = token

        return token

    def close(self):
        self._client.set_terminated(run_id=self._run.info.run_id)

    def _calculate_reward(self, action: float) -> float:
        if action == self.current_obs:
            return 1
        else:
            return -1
