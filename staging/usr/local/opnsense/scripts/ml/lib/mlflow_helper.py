from time import time
DATABASE_URI = ''

from mlflow.store.tracking.dbmodels.models import (
    SqlLatestMetric,
    SqlParam,
)
from mlflow.tracking.client import (
    MlflowClient,
)
from mlflow.tracking.context import (
    registry as context_registry,
)

mlflow_client = MlflowClient(
    tracking_uri=DATABASE_URI
)
experiment_name = "testing_mlflow"
try:
    experiment_id = str(
        mlflow_client.get_experiment_by_name(
            experiment_name
        ).experiment_id
    )
except AttributeError:
    experiment_id = mlflow_client.create_experiment(
        experiment_name
    )

run_name = "final_solution"
tags = context_registry.resolve_tags(
    {"mlflow.runName": run_name}
)
run = mlflow_client.create_run(
    experiment_id=experiment_id, tags=tags
)

metrics = {
    f"metric_{i}": 1 / (i + 1)
    for i in range(12)
}
params = {
    f"param_{i}": f"param_{i}"
    for i in range(3)
}
prep_metrics = [
    SqlLatestMetric(
        **{
            "key": key,
            "value": value,
            "run_uuid": run.info.run_id,
            "timestamp": int(time() * 1000),
            "step": 0,
            "is_nan": False,
        }
    )
    for key, value in metrics.items()
]
prep_params = [
    SqlParam(
        **{
            "key": key,
            "value": str(value),
            "run_uuid": run.info.run_id,
        }
    )
    for key, value in params.items()
]

start = time()
store = mlflow_client._tracking_client.store
with store.ManagedSessionMaker() as session:
    session.add_all(
        prep_params + prep_metrics
    )
mlflow_client.set_terminated(run.info.run_id)
print(f"Took {time()- start:.2f} seconds")