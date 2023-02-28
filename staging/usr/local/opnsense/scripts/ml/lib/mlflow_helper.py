from mlflow.store.tracking.dbmodels.models import SqlLatestMetric
from mlflow.tracking.client import MlflowClient


def log_batch_heavy(client: MlflowClient, metrics: [SqlLatestMetric]):
    store = client._tracking_client.store
    with store.ManagedSessionMaker() as session:
        session.bulk_save_objects(metrics)
