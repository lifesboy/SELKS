#!/usr/bin/python3
import glob
import sys
from sys import version_info
from datetime import datetime
from pathlib import Path
from typing import Optional

import mlflow
import ray
from mlflow.entities import Experiment, Run
from mlflow.tracking import MlflowClient
from mlflow.tracking.fluent import ActiveRun
import lib.utils as utils


PYTHON_VERSION = "{major}.{minor}.{micro}".format(major=version_info.major,
                                                  minor=version_info.minor,
                                                  micro=version_info.micro)

PATH_ML = '/usr/local/opnsense/scripts/ml'

RAY_HEAD_NODE_ADDRESS = '127.0.0.1:6379'
MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
# RAY_HEAD_NODE_ADDRESS = '123.16.153.97:6379'
# MLFLOW_TRACKING_URI = 'http://selks.ddns.net:5000'

MODEL_SERVE_ADDRESS = '0.0.0.0'
MODEL_SERVE_PORT = 6789

MODEL_SERVE_DETECTION_URL = 'http://selks.ddns.net:6789/anomaly'

DATA_DIR = '/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

DATA_FEATURED_EXTRACTED_DIR = '/cic/dataset/featured_extracted/'
DATA_NORMALIZED_DIR = '/cic/dataset/normalized/'
DATA_NORMALIZED_LABELED_DIR = '/cic/dataset/normalized_labeled/'
DATA_TRAINED_DIR = '/cic/dataset/trained/'
TMP_DIR = '/drl/tmp/'

Path(TMP_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_FEATURED_EXTRACTED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_NORMALIZED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_NORMALIZED_LABELED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_TRAINED_DIR).mkdir(parents=True, exist_ok=True)

TAG_DATASET_SIZE = 'dataset.size'
TAG_DATASET_MIN = 'dataset.min'
TAG_DATASET_MAX = 'dataset.max'
TAG_RUN_UUID = 'run.uuid'
TAG_PARENT_RUN_UUID = 'run.parent.uuid'
TAG_RUN_TYPE = 'run.type'
TAG_RUN_STATUS = 'run.status'
TAG_RUN_TAG = 'run.tag'

TAG_DEPLOYMENT_STATUS = 'deployment.status'

TAG_DEPLOYMENT_RUN_MODEL = 'deployment.run.model'
TAG_DEPLOYMENT_RUN_OBS = 'deployment.run.obs'
TAG_DEPLOYMENT_RUN_ACTION = 'deployment.run.action'

TAG_DEPLOYMENT_TEST_STATUS = 'deployment.test.status'


def init_node():
    if not utils.is_ray_gpu_ready():
        utils.restart_ray_service()

    if not ray.is_initialized():
        ray.init(address=RAY_HEAD_NODE_ADDRESS)


def init_tracking(name: str, run_name: Optional[str] = None) -> (ActiveRun, MlflowClient):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(name)
    run = mlflow.active_run() if mlflow.active_run() else mlflow.start_run(run_name=run_name)
    client = MlflowClient()
    client.set_tag(run_id=run.info.run_id, key=TAG_RUN_UUID, value=run.info.run_id)
    return run, client


def init_experiment(name: str, run_name: Optional[str] = None) -> (ActiveRun, MlflowClient):
    init_node()
    exp = name  # + datetime.now().strftime("-%Y%m%dT%H%M%S")
    return init_tracking(exp, run_name)


def get_train_id():
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def get_data_featured_extracted_files_by_pattern(pattern: str):
    return glob.glob(DATA_FEATURED_EXTRACTED_DIR + pattern)


def get_data_normalized_labeled_files_by_pattern(pattern: str):
    return glob.glob(DATA_NORMALIZED_LABELED_DIR + pattern)


def get_data_files_by_pattern(pattern: str):
    return glob.glob(pattern)
