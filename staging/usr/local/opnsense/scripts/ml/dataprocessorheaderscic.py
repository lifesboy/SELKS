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
    ldf['result'] = ldf.apply(utils.separate_file_by_lines, axis=1)
    return ldf


def split_csv_file(data_source: str):
    ldf = utils.lines_of_files(data_source)
    ldf['result'] = ldf.apply(lambda i: utils.split_file_by_line_num(i, 100000), axis=1)
    return ldf


# mv Friday-02-03-2018_TrafficForML_CICFlowMeter.csv.bak Friday-02-03-2018_TrafficForML_CICFlowMeter.csv
# mv Friday-16-02-2018_TrafficForML_CICFlowMeter.csv.bak Friday-16-02-2018_TrafficForML_CICFlowMeter.csv
# mv Friday-23-02-2018_TrafficForML_CICFlowMeter.csv.bak Friday-23-02-2018_TrafficForML_CICFlowMeter.csv
# mv Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv.bak Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv
# mv Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv.bak Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv
# mv Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv.bak Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv
# mv Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv.bak Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv
# mv Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv.bak Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv
# mv Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv.bak Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv
# mv Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv.bak Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv

# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/dataprocessorheaderscic.py --data-source=cic2018/*.csv

if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.data_source

    log.info('start dataprocessorheaderscic: %s', data_source)
    kill_exists_processing()
    res = separate_csv_file(common.DATA_FEATURED_EXTRACTED_DIR + data_source)
    log.info('finish dataprocessorheaderscic: %s, %s', data_source, res['result'].tolist())

    log.info('start splitting: %s', data_source)
    res_split = split_csv_file(common.DATA_FEATURED_EXTRACTED_DIR + data_source)
    log.info('finish splitting: %s, %s', data_source, res_split['result'].tolist())
