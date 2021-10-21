from ray import tune
from ray.tune.integration.mlflow import mlflow_mixin

import mlflow

import common

common.init_node()

# Create the MlFlow expriment.
mlflow.create_experiment("my_experiment")


@mlflow_mixin
def train_fn(config):
    for i in range(10):
        loss = config["a"] + config["b"]
        mlflow.log_metric(key="loss", value=loss)
    tune.report(loss=loss, done=True)


tune.run(
    train_fn,
    config={
        # define search space here
        "a": tune.choice([1, 2, 3]),
        "b": tune.choice([4, 5, 6]),
        # mlflow configuration
        "mlflow": {
            "experiment_name": "my_experiment",
            "tracking_uri": mlflow.get_tracking_uri()
        }
    })
