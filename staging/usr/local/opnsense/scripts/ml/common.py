#!/usr/bin/python3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import mlflow
import ray
from mlflow.entities import Experiment, Run
from mlflow.tracking import MlflowClient
from mlflow.tracking.fluent import ActiveRun

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
TAG_RUN_UUID = 'run.uuid'
TAG_PARENT_RUN_UUID = 'run.parent.uuid'
TAG_RUN_TYPE = 'run.type'
TAG_RUN_STATUS = 'run.status'


def init_node():
    ray.init(address=RAY_HEAD_NODE_ADDRESS)


def init_tracking(name: str) -> (ActiveRun, MlflowClient):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(name)
    run = mlflow.active_run() if mlflow.active_run() else mlflow.start_run()
    client = MlflowClient()
    client.set_tag(run_id=run.info.run_id, key=TAG_RUN_UUID, value=run.info.run_id)
    return run, client


def init_experiment(name: str) -> (ActiveRun, MlflowClient):
    init_node()
    exp = name  # + datetime.now().strftime("-%Y%m%dT%H%M%S")
    return init_tracking(exp)


def get_train_id():
    return datetime.now().strftime("%Y%m%dT%H%M%S")
