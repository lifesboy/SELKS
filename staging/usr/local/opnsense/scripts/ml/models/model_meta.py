import mlflow


class ModelMeta(dict):
    artifact_path: str
    python_model: mlflow.pyfunc.PythonModel
    registered_model_name: str
    conda_env: dict

    def __init__(self, artifact_path: str, python_model: mlflow.pyfunc.PythonModel, registered_model_name: str, conda_env: dict):
        super().__init__()
        self.artifact_path = artifact_path
        self.python_model = python_model
        self.registered_model_name = registered_model_name
        self.conda_env = conda_env
