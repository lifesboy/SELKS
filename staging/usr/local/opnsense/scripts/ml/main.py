import ray
from ray import tune
import mlflow
from ray.tune.integration.mlflow import MLflowLoggerCallback

import common

run, client = common.init_experiment("experiment-main")

tune.run(
    "PPO",
    stop={"episode_reward_mean": 200},
    config={
        "env": "CartPole-v0",
        "num_gpus": 1,
        "num_workers": 1,
        "lr": tune.grid_search([0.01, 0.001, 0.0001]),
    },
    callbacks=[MLflowLoggerCallback(
        experiment_name="experiment-main",
        save_artifact=True)]
)