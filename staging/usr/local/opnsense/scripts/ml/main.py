import ray
from ray import tune
import mlflow
from ray.tune.integration.mlflow import MLflowLoggerCallback

ray.init(address='127.0.0.1:6379')

mlflow.set_tracking_uri("http://127.0.0.1:5000")

tune.run(
    "PPO",
    stop={"episode_reward_mean": 200},
    config={
        "env": "CartPole-v0",
        "num_gpus": 0,
        "num_workers": 1,
        "lr": tune.grid_search([0.01, 0.001, 0.0001]),
    },
    callbacks=[MLflowLoggerCallback(
        experiment_name="experiment-main",
        save_artifact=True)]
)