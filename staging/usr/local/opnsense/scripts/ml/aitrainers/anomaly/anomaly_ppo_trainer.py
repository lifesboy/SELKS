import os
import mlflow
from mlflow.models import ModelSignature
from mlflow.types import Schema, ColSpec, DataType

from ray.rllib.agents.ppo import PPOTrainer

from aimodels.anomaly.anomaly_model import AnomalyModel
from anomaly_normalization import LABEL


class AnomalyPPOTrainer(PPOTrainer):

    def save_checkpoint(self, checkpoint_dir: str) -> str:
        path = super().save_checkpoint(checkpoint_dir)
        self.export_policy_model(os.path.join(checkpoint_dir, "policy"))

        h5_path = os.path.join(checkpoint_dir, "h5", "saved_model.h5")
        self.get_policy().model.base_model.save_weights(h5_path)
        self.get_policy().model.base_model.save(h5_path)

        model_meta = AnomalyModel.get_model_meta()
        features: [str] = self.config.get('features', [])
        input_schema = Schema([ColSpec(type=DataType.double, name=i) for i in features])
        output_schema = Schema([ColSpec(type=DataType.integer, name=LABEL)])
        signature = ModelSignature(inputs=input_schema, outputs=output_schema)
        mlflow.keras.log_model(keras_model=self.get_policy().model.base_model,
                               signature=signature,
                               artifact_path=model_meta.artifact_path,
                               registered_model_name=model_meta.registered_model_name)

        return path
