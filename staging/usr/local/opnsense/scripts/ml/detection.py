import argparse
import glob
import pandas as pd
from pandas import DataFrame

import gym
from starlette.requests import Request
import requests
import random
import time

import ray.rllib.agents.ppo as ppo
from ray import serve

import common

for _ in range(1000):
    env = gym.make("CartPole-v0")
    obs = env.reset()
    print(f"-> Sending observation {obs}")
    resp = requests.get(common.MODEL_SERVE_DETECTION_URL, json={"observation": obs.tolist()})
    print(f"<- Received response {resp.json() if resp.ok else resp}")
    time.sleep(random.randint(1, 5))


def main():
    parser = argparse.ArgumentParser()

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-f",
        "--file",
        action="store",
        dest="input_file",
        help="capture offline data from INPUT_FILE pattern",
    )

    batch_group = parser.add_mutually_exclusive_group(required=False)
    batch_group.add_argument(
        "-b",
        "--batch",
        type=int,
        action="store",
        dest="batch",
        default=100,
        help="number of files to sniff per session (default=100)",
    )

    cpu_num_group = parser.add_mutually_exclusive_group(required=False)
    cpu_num_group.add_argument(
        "-cpu",
        "--cpu-num",
        type=int,
        action="store",
        dest="cpu_num",
        default=1,
        help="number of cpus to sniff (default=1)",
    )

    output_group = parser.add_mutually_exclusive_group(required=False)
    output_group.add_argument(
        "-c",
        "--csv",
        "--flow",
        action="store_const",
        const="flow",
        dest="output_mode",
        help="output flows as csv",
    )

    url_model = parser.add_mutually_exclusive_group(required=False)
    url_model.add_argument(
        "-u",
        "--url",
        action="store",
        dest="url_model",
        help="URL endpoint for send to Machine Learning Model. e.g http://0.0.0.0:80/prediction",
    )

    parser.add_argument(
        "output",
        help="output directory",
    )

    args = parser.parse_args()
    batch_size = args.batch
    cpu_num = args.cpu_num
    input_interface = args.input_interface
    output_mode = args.output_mode
    output = args.output
    url_model = args.url_model

    if args.input_file is not None:
        input_files = glob.glob(args.input_file)
        file_df: DataFrame = pd.DataFrame(input_files, columns=['input_path'])
        file_df['input_name'] = file_df.apply(lambda i: os.path.split(i.input_path)[-1], axis=1)
        file_df['marked_done_name'] = file_df.apply(lambda i: utils.get_marked_done_file_name(i.input_path), axis=1)
        file_df['marked_done_path'] = file_df.apply(lambda i: os.path.join(output, i.marked_done_name), axis=1)
        file_df['marked_done_existed'] = file_df.apply(lambda i: os.path.exists(i.marked_done_path), axis=1)

        file_df = file_df.loc[file_df['marked_done_existed'] == False]
        file_df = file_df.sort_values(by='input_name')
        file_df = file_df.filter(['input_path', 'input_name', 'marked_done_path']).applymap(lambda i: [i])
        file_df['batch'] = file_df.apply(lambda i: i.name // batch_size, axis=1)

        batch_df: DataFrame = file_df.groupby('batch').sum()
        batch_df['output_name'] = batch_df.apply(lambda i: utils.get_output_file_of_batch(i.input_name), axis=1)
        batch_df['output_path'] = batch_df.apply(lambda i: os.path.join(output, i.output_name), axis=1)
        batch_df['sniffer'] = batch_df.apply(lambda i: create_sniffer(
            i.input_path, None, output_mode, i.output_path, url_model), axis=1)
    else:
        sniffers = [create_sniffer(None, input_interface, output_mode, output, url_model)]
        batch_df = pd.DataFrame(sniffers, columns=['sniffer'])

    batch_df['episode'] = batch_df.apply(lambda i: i.name // cpu_num, axis=1)
    episode_gr = batch_df.groupby(['episode'])

    log.info('start sniffing: episode=%s', episode_gr.count())
    episode_gr.apply(sniff)
    log.info('finish sniffing.')


if __name__ == "__main__":
    main()
