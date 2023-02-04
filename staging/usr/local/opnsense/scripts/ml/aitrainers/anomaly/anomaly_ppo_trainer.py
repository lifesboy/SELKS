import os
from ray.rllib.agents.ppo import PPOTrainer


class AnomalyPPOTrainer(PPOTrainer):

    def save_checkpoint(self, checkpoint_dir: str) -> str:
        path = super().save_checkpoint(checkpoint_dir)
        self.export_policy_model(os.path.join(checkpoint_dir, "policy"))

        with self.get_policy().get_session().graph.as_default():
            with self.get_policy().get_session().as_default():
                self.get_policy().model.save_h5(checkpoint_dir)
                self.get_policy().model.save_mlflow()
                self.get_policy().model.mark_resumed_base_version()

        return path
