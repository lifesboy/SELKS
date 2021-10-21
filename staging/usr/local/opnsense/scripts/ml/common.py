#!/usr/bin/python3
import sys
from pathlib import Path

import mlflow
import ray

PATH_ML = '/usr/local/opnsense/scripts/ml'

RAY_HEAD_NODE_ADDRESS = '127.0.0.1:6379'
MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
# RAY_HEAD_NODE_ADDRESS = '123.16.153.97:6379'
# MLFLOW_TRACKING_URI = 'http://selks.ddns.net:5000'

DATA_DIR = '/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

TMP_DIR = '/drl/tmp/'
Path(TMP_DIR).mkdir(parents=True, exist_ok=True)


def init_node():
    ray.init(address=RAY_HEAD_NODE_ADDRESS)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
