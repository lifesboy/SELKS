#!/usr/bin/python3

from pathlib import Path

import mlflow
import ray

RAY_HEAD_NODE_ADDRESS = '127.0.0.1:6379'
MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'

DATA_DIR = '/Volumes/Extra/workstore/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

TMP_DIR = '/Volumes/Extra/workstore/drl/tmp/'
Path(TMP_DIR).mkdir(parents=True, exist_ok=True)


def init_node():
    ray.init(address=RAY_HEAD_NODE_ADDRESS)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
