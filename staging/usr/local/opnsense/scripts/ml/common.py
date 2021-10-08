#!/usr/bin/python3

from pathlib import Path

DATA_DIR = '/cic/2018/'
TRAIN_DATA_DIR = DATA_DIR + 'Processed Traffic Data for ML Algorithms/'

TMP_DIR = '/drl/tmp/'
Path(TMP_DIR).mkdir(parents=True, exist_ok=True)
