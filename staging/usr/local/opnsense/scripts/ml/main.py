import ray
from ray import tune

ray.init()
assert ray.is_initialized() == True

tune.run(
    "PPO",
    stop={"episode_reward_mean": 200},
    config={
        "env": "CartPole-v0",
        "num_gpus": 0,
        "num_workers": 1,
        "lr": tune.grid_search([0.01, 0.001, 0.0001]),
    },
)

ray.shutdown()
assert ray.is_initialized() == False
