from mlflow.store.tracking.dbmodels.models import SqlLatestMetric
from mlflow.tracking.client import MlflowClient

DATABASE_URI = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'


def log_batch_heavy(metrics: [SqlLatestMetric]):
    client = MlflowClient(tracking_uri=DATABASE_URI)
    store = client._tracking_client.store
    with store.ManagedSessionMaker() as session:
        session.bulk_save_objects(metrics)
