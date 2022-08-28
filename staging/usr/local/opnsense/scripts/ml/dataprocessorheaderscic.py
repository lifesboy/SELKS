#!/usr/bin/python3
import argparse
import os
import signal

import lib.utils as utils
from lib.logger import log

import common

from anomaly_normalization import DST_PORT_CIC

parser = argparse.ArgumentParser()
parser.add_argument(
    "--data-source",
    type=str,
    default="",
    help="data source file paths")


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def separate_csv_file(data_source: str):
    ldf = utils.lines_in_files_of(DST_PORT_CIC, data_source)
    ldf.apply(utils.separate_file_by_lines, axis=1)


# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/dataprocessorheaderscic.py --data-source=cic2018/*.csv

if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.data_source

    log.info('start dataprocessorheaderscic: %s', data_source)
    kill_exists_processing()
    separate_csv_file(common.DATA_FEATURED_EXTRACTED_DIR + data_source)
    log.info('finish dataprocessorheaderscic: %s, %s', data_source)
