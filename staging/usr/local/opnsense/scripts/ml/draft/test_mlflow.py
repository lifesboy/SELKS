import mlflow

mlflow.set_tracking_uri('http://127.0.0.1:5000')
mlflow.keras.load_model('models:/AnomalyModel/staging')
client = mlflow.MlflowClient()
v = client.get_latest_versions(name='AnomalyModel', stages=['staging'])