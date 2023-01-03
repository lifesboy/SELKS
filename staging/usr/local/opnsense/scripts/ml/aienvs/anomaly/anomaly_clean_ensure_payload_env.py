import numpy as np
from aienvs.anomaly.anomaly_minibatch_payload_env import AnomalyMinibatchPayloadEnv


class AnomalyCleanEnsurePayloadEnv(AnomalyMinibatchPayloadEnv):

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
            return -2
        else:
            self.anomaly_incorrect += 1
            return -1
