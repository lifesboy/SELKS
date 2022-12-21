import os

from ray.rllib.agents.ppo.ppo import PPOTrainer


class AnomalyPPOTrainer(PPOTrainer):

    def save_checkpoint(self, checkpoint_dir: str) -> str:
        path = super().save_checkpoint(checkpoint_dir)
        self.export_policy_model(os.path.join(checkpoint_dir, "policy"))
        return path
