#!/usr/bin/python3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import mlflow
import ray
from mlflow.entities import Experiment, Run
from mlflow.tracking import MlflowClient

PATH_ML = '/usr/local/opnsense/scripts/ml'

RAY_HEAD_NODE_ADDRESS = '127.0.0.1:6379'
MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
# RAY_HEAD_NODE_ADDRESS = '123.16.153.97:6379'
# MLFLOW_TRACKING_URI = 'http://selks.ddns.net:5000'

DATA_DIR = '/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

TMP_DIR = '/drl/tmp/'
Path(TMP_DIR).mkdir(parents=True, exist_ok=True)

TAG_DATASET_SIZE = 'dataset.size'
TAG_DATASET_MIN = 'dataset.min'
TAG_DATASET_MAX = 'dataset.max'
TAG_RUN_TYPE = 'run.type'


def init_node():
    ray.init(address=RAY_HEAD_NODE_ADDRESS)


def init_tracking(name: str) -> (Run, MlflowClient):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(name)
    client = MlflowClient()
    return client.create_run(experiment_id=mlflow.get_experiment_by_name(name).experiment_id), client


def init_experiment(name: str) -> (Run, MlflowClient):
    init_node()
    exp = name  # + datetime.now().strftime("-%Y%m%dT%H%M%S")
    return init_tracking(exp)
