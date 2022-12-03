#!/usr/bin/python3
import glob
import os
import sys
import time
from sys import version_info
from datetime import datetime
from pathlib import Path
from typing import Optional

import mlflow
import ray
from ray.rllib import _register_all
from mlflow.entities import Experiment, Run
from mlflow.tracking import MlflowClient
from mlflow.tracking.fluent import ActiveRun
from ray.runtime_env import RuntimeEnv

import lib.utils as utils

PYTHON_VERSION = "{major}.{minor}.{micro}".format(major=version_info.major,
                                                  minor=version_info.minor,
                                                  micro=version_info.micro)

PATH_ML = '/usr/local/opnsense/scripts/ml'

RAY_HEAD_NODE_ADDRESS = os.getenv('RAY_REDIS_ADDRESS', '127.0.0.1:6379')
MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
# RAY_HEAD_NODE_ADDRESS = '123.16.153.97:6379'
# MLFLOW_TRACKING_URI = 'http://ngfw.h05:5000'

MODEL_STAGING_ADDRESS = '0.0.0.0'
MODEL_STAGING_PORT = 6689

MODEL_SERVE_ADDRESS = '0.0.0.0'
MODEL_SERVE_PORT = 6789

MODEL_SERVE_DETECTION_URL = 'http://ngfw.h05:6789/anomaly'

DATA_DIR = '/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

DATA_FEATURED_EXTRACTED_DIR = '/cic/dataset/featured_extracted/'
# DATA_NORMALIZED_DIR = '/cic/dataset/normalized/'
DATA_NORMALIZED_LABELED_DIR = '/cic/dataset/normalized_labeled/'
DATA_SAMPLING_DIR = '/cic/dataset/sampling/'
DATA_TRAINED_DIR = '/cic/dataset/trained/'
DATA_TESTED_DIR = '/cic/dataset/tested/'
# DATA_INFERRED_DIR = '/cic/dataset/inferred/'
TMP_DIR = '/drl/tmp/'

Path(TMP_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_FEATURED_EXTRACTED_DIR).mkdir(parents=True, exist_ok=True)
# Path(DATA_NORMALIZED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_NORMALIZED_LABELED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_SAMPLING_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_TRAINED_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_TESTED_DIR).mkdir(parents=True, exist_ok=True)
# Path(DATA_INFERRED_DIR).mkdir(parents=True, exist_ok=True)

TAG_DATASET_SIZE = 'dataset.size'
TAG_DATASET_MIN = 'dataset.min'
TAG_DATASET_MAX = 'dataset.max'
TAG_RUN_UUID = 'run.uuid'
TAG_PARENT_RUN_UUID = 'run.parent.uuid'
TAG_RUN_TYPE = 'run.type'
TAG_RUN_STATUS = 'run.status'
TAG_RUN_TAG = 'run.tag'
TAG_TRAIN_UNIT = 'unit'

TAG_DEPLOYMENT_STATUS = 'deployment.status'

TAG_DEPLOYMENT_RUN_MODEL = 'deployment.run.model'
TAG_DEPLOYMENT_RUN_OBS = 'deployment.run.obs'
TAG_DEPLOYMENT_RUN_ACTION = 'deployment.run.action'

TAG_DEPLOYMENT_TEST_STATUS = 'deployment.test.status'

TOTAL_CPUS = 40
TOTAL_CPUS_TRAINING_OPERATION = 10
TOTAL_CPUS_TRAINING_DATASET_OPERATION: int = 10
TOTAL_CPUS_CACHING_DATASET_OPERATION: int = 5
TOTAL_CPUS_PREPROCESSING_DATASET_OPERATION: int = 10
TOTAL_CPUS_INFERRING_DATASET_OPERATION: int = 4

TOTAL_GPUS = 4

TRAINING_COURSE_LENGTH = 4  # 4 years per course, to archive same university grade of best trained hackers


def init_node():
    if not utils.is_ray_gpu_ready():
        utils.restart_ray_service()
        time.sleep(60)

    if not ray.is_initialized():
        # runtime_env = RuntimeEnv(pip={
        #     "packages": ["tensorflow==2.7.0", "numpy==1.21.4", "six==1.16.0", "numba==0.56.0", "pyarrow==9.0.0"],
        #     "pip_check": False,
        #     "pip_version": "==22.2.2;python_version=='3.7.3'"})
        # ray.init(address=RAY_HEAD_NODE_ADDRESS, runtime_env=runtime_env)
        ray.init(address=RAY_HEAD_NODE_ADDRESS)

    # https://github.com/ray-project/ray/issues/8205
    _register_all()


def init_tracking(name: str, run_name: Optional[str] = None) -> (ActiveRun, MlflowClient):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(name)
    run = mlflow.active_run() if mlflow.active_run() else mlflow.start_run(run_name=run_name)
    client = MlflowClient()
    client.set_tag(run_id=run.info.run_id, key=TAG_RUN_UUID, value=run.info.run_id)

    # timeline_file = f'{TMP_DIR}{name}_{run_name}_timeline.json'
    # ray.timeline(filename=timeline_file)
    # client.log_artifact(run_id=run.info.run_id, local_path=timeline_file, artifact_path='profiling')
    return run, client


def init_experiment(name: str, run_name: Optional[str] = None,
                    skip_init_node: Optional[bool] = False) -> (ActiveRun, MlflowClient):
    if not skip_init_node:
        init_node()

    exp = name  # + datetime.now().strftime("-%Y%m%dT%H%M%S")
    return init_tracking(exp, run_name)


def get_second() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def get_week() -> str:
    return datetime.now().strftime("%YW%V")


def get_month() -> str:
    return datetime.now().strftime("%Y%m")


def get_course() -> str:
    year = datetime.now().year
    start = year - year % TRAINING_COURSE_LENGTH
    end = start + TRAINING_COURSE_LENGTH
    return f"{start}T{end}"


def get_course_unit() -> str:
    return f"{get_week()}"  # training 1 unit per week


def get_training_name(run: str, model: str, env: str, unit: str) -> str:
    return f"{run}_{model}_{env}_{unit}"  # learn by unit


def get_data_featured_extracted_files_by_pattern(pattern: str) -> [str]:
    return glob.glob(DATA_FEATURED_EXTRACTED_DIR + pattern)


# def get_data_normalized_files_by_pattern(pattern: str):
#     return glob.glob(DATA_NORMALIZED_DIR + pattern)


def get_data_normalized_labeled_files_by_pattern(pattern: str) -> [str]:
    return glob.glob(DATA_NORMALIZED_LABELED_DIR + pattern)


def get_data_files_by_pattern(pattern: str) -> [str]:
    return glob.glob(pattern)
