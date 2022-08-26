import argparse

from ray import tune
from ray.rllib.agents.ppo import PPOTrainer
from ray.rllib.examples.models.rnn_model import RNNModel
from ray.rllib.models import ModelCatalog
from ray.tune.integration.mlflow import MLflowLoggerCallback
from ray.tune.registry import register_env

import common
from aienvs.anomaly.anomaly_env import AnomalyEnv

parser = argparse.ArgumentParser()
parser.add_argument(
    "--run",
    type=str,
    default="PPO",
    help="The RLlib-registered algorithm to use.")
parser.add_argument("--env", type=str, default="AnomalyEnv")
parser.add_argument("--num-cpus", type=int, default=0)
parser.add_argument(
    "--as-test",
    action="store_true",
    help="Whether this script should be run as a test: --stop-reward must "
         "be achieved within --stop-timesteps AND --stop-iters.")
parser.add_argument(
    "--stop-iters",
    type=int,
    default=100,
    help="Number of iterations to train.")
parser.add_argument(
    "--stop-timesteps",
    type=int,
    default=100000,
    help="Number of timesteps to train.")
parser.add_argument(
    "--stop-episode-len",
    type=int,
    default=1e4,
    help="Max length of episode to train.")
parser.add_argument(
    "--stop-reward",
    type=float,
    default=90.0,
    help="Reward at which we stop training.")


class AnomalyExperiment():
    def __init__(self):
        args = parser.parse_args()
        self.args = args
        self.config = {
            "env": args.env,
            "env_config": {
                "episode_len": args.stop_episode_len,
            },
            "gamma": 0.9,
            # Use GPUs iff `RLLIB_NUM_GPUS` env var set to > 0.
            "num_gpus": 0.1,  # int(os.environ.get("RLLIB_NUM_GPUS", "0")),
            "num_workers": 0,
            "num_envs_per_worker": 20,
            "entropy_coeff": 0.001,
            "num_sgd_iter": 5,
            "vf_loss_coeff": 1e-5,
            "vf_clip_param": 1000.0,
            "model": {
                "custom_model": "rnn",
                "max_seq_len": 20,
                "custom_model_config": {
                    "cell_size": 32,
                },
            },
            "framework": 'tf',
        }

        self.stop = {
            "training_iteration": args.stop_iters,
            "timesteps_total": args.stop_timesteps,
            "episode_reward_mean": args.stop_reward,
        }

        self.run, self.client = common.init_experiment("anomaly_experiment")
        ModelCatalog.register_custom_model("rnn", RNNModel)
        register_env("AnomalyEnv", lambda c: AnomalyEnv(c))

    def train(self):
        results = tune.run(self.args.run, config=self.config, stop=self.stop, verbose=1,
                           checkpoint_at_end=True,
                           checkpoint_freq=1,
                           keep_checkpoints_num=10,
                           checkpoint_score_attr='training_iteration',
                           callbacks=[MLflowLoggerCallback(
                               experiment_name="anomaly-model",
                               save_artifact=True)])
        checkpoints = results.get_trial_checkpoints_paths(trial=results.get_best_trial(metric='episode_reward_mean',
                                                                                       mode='max'),
                                                          metric='episode_reward_mean')
        checkpoint_path = checkpoints[0][0]
        return checkpoint_path, results

    def load(self, path):
        self.agent = PPOTrainer(config=self.config, env=self.args.env)
        self.agent.restore(path)

    def test(self):
        # check_learning_achieved(results, self.args.stop_reward)

        env = getattr(anomaly_env, self.args.env)(self.config)
        # run until episode ends
        episode_reward = 0
        done = False
        obs = env.reset()

        self.client.log_metric(run_id=self.run.info.run_id, key="evaluation.episode_reward", value=episode_reward)
        while not done:
            action = self.agent.compute_action(obs)
            obs, reward, done, info = env.step(action)
            episode_reward += reward
            self.client.log_metric(run_id=self.run.info.run_id, key="evaluation.action", value=action)
            self.client.log_metric(run_id=self.run.info.run_id, key="evaluation.episode_reward", value=episode_reward)

        return episode_reward


if __name__ == "__main__":
    exp = AnomalyExperiment()
    # checkpoint_path, results = exp.train()
    # checkpoint_path = '/drl/ray_results/PPO/PPO_AnomalyEnv_6e374_00000_0_2021-11-17_16-00-05/checkpoint_000008/checkpoint-8'
    checkpoint_path = '/drl/artifacts/6/facfe1a0fb6c4ce38a97a21a90ac73a7/artifacts/checkpoint_000020/checkpoint-20'
    print("Checkpoint path:", checkpoint_path)
    exp.load(checkpoint_path)
    exp.test()
