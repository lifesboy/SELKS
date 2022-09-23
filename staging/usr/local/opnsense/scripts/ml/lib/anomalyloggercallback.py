from typing import Dict

from ray.tune.integration.mlflow import MLflowLoggerCallback


class AnomalyLoggerCallback(MLflowLoggerCallback):

    def log_trial_result(self, iteration: int, trial: "Trial", result: Dict):
        super().log_trial_result(iteration=iteration, trial=trial, result=result)
        run_id = self._trial_runs[trial]
        if self.should_save_artifact:
            self.mlflow_util.save_artifacts(run_id=run_id, dir=trial.logdir)
