from typing import Dict

from ray.tune.integration.mlflow import MLflowLoggerCallback


class AnomalyLoggerCallback(MLflowLoggerCallback):

    def log_trial_start(self, trial: "Trial"):
        # Create run if not already exists.
        if trial not in self._trial_runs:
            # Set trial name in tags
            tags = self.tags.copy()
            tags["trial_name"] = str(trial)

            run = self.mlflow_util.start_run(tags=tags, run_name=str(trial))
            self._trial_runs[trial] = run.info.run_id

        run_id = self._trial_runs[trial]

        # Log the config parameters.
        config = trial.config
        # self.mlflow_util.log_params(run_id=run_id, params_to_log=config)

    def log_trial_result(self, iteration: int, trial: "Trial", result: Dict):
        super().log_trial_result(iteration=iteration, trial=trial, result=result)
        run_id = self._trial_runs[trial]
        if self.should_save_artifact:
            self.mlflow_util.save_artifacts(run_id=run_id, dir=trial.logdir)
