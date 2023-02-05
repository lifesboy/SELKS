import numpy as np
from aienvs.anomaly.anomaly_minibatch_env import AnomalyMinibatchEnv


class AnomalyBalanceOnTrainEnsureEnv(AnomalyMinibatchEnv):

    def _calculate_reward(self, action: np.int32) -> float:
        if self.current_obs is None:
            return 0

        # positive
        if action == self.current_action[0]:
            if action == 1:
                self.anomaly_detected += 1
            else:
                self.clean_detected += 1
            return 1

        # negative
        if action == 1:
            self.clean_incorrect += 1
            return -self.dataset_size / (1 + self.dataset_size - self.anomaly_total)
        else:
            self.anomaly_incorrect += 1
            return -self.dataset_size / (1 + self.anomaly_total)
