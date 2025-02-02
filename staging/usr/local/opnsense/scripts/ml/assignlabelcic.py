#!/usr/bin/python3
import argparse
import os
import signal
from datetime import datetime, timedelta

import lib.utils as utils
from lib.logger import log

import common
import numpy as np
import pandas as pd

from anomaly_normalization import TIMESTAMP, FLOW_DURATION, SRC_IP, SRC_PORT, DST_IP, DST_PORT, PROTOCOL, \
    LABEL, TIMESTAMP_FLOW, OFFSET, LABEL_VALUE_BENIGN

parser = argparse.ArgumentParser()
parser.add_argument(
    "--data-source",
    type=str,
    default="",
    help="data source file paths")
parser.add_argument(
    "--label-source",
    type=str,
    default="",
    help="label file paths")
parser.add_argument(
    "--data-destination",
    type=str,
    default="",
    help="output labeled data directory path")


def kill_exists_processing():
    for pid in set(utils.get_process_ids(__file__)) - {os.getpid()}:
        os.kill(pid, signal.SIGTERM)


def assign_label_to_extracted_csv(label_source: str, data_source: str, data_destination: str):
    df_label = combine_label_csv(label_source)
    df = pd.DataFrame(common.get_data_featured_extracted_files_by_pattern(data_source), columns=['input'])
    df['output'] = df.apply(lambda x: common.DATA_FEATURED_EXTRACTED_DIR + '/'.join([
        data_destination,
        *(x['input'].split(common.DATA_FEATURED_EXTRACTED_DIR)[1].split('/')[1:])
    ]), axis=1)
    df['result'] = df.apply(lambda x: label_extracted_csv(df_label, x['input'], x['output']), axis=1)
    return df


def combine_label_csv(pattern: str):
    merge_features = [SRC_IP, SRC_PORT, DST_IP, DST_PORT, PROTOCOL, LABEL]
    combine = pd.DataFrame()
    for f in common.get_data_featured_extracted_files_by_pattern(pattern):
        df = pd.read_csv(f)
        missing_features = set(merge_features) - set(df.columns)
        if len(missing_features) > 0:
            log.warn(f"combine_label_csv {f}: {missing_features}")
        df[list(missing_features)] = np.nan  # protocol will not be tcp(6) or udp (17)
        df = df[merge_features]
        combine = pd.concat([combine, df], axis=0, ignore_index=True)

    log.info(f"combine_label_csv {pattern}: {combine.shape}")

    if TIMESTAMP in combine.columns:
        # Record the resolution for later matching
        combine.loc[combine[TIMESTAMP].str.count(":") == 1, OFFSET] = 60
        combine.loc[combine[TIMESTAMP].str.count(":") == 2, OFFSET] = 1

        combine[TIMESTAMP] = combine[TIMESTAMP].apply(
            lambda x: (datetime.strptime(x + " -0300", "%d/%m/%Y %H:%M %z"))
            if x.count(":") == 1
            else (datetime.strptime(x + " -0300", "%d/%m/%Y %H:%M:%S %z"))
        )

        # Timestamps are listed 3/7/2017 2:55, without AM/PM indicators, so any time between 1 and 7 AM ADT (4 and 11 AM UTC) are actually PM
        # Datetime was instantiated with timezone info, so .hour is already in the -0300 timezone
        combine[TIMESTAMP] = combine[TIMESTAMP].apply(
            lambda x: int((x + timedelta(hours=12)).timestamp()) if (x.hour >= 1) & (x.hour <= 7) else int(x.timestamp())
        )
        combine = combine.sort_values(by=TIMESTAMP)

    return combine


def label_extracted_csv(df_flow: pd.DataFrame, input_file, output_file) -> int:

    log.info("Reading extracted_csv %s ......" % input_file)
    df_pcap_csv = pd.read_csv(input_file, index_col=0)

    # Merge based on the shared columns keeping every payload and adding flow data for every matches
    # Merge duplicates the PCAP row for each matching df_flow row
    _FLOW = "_flow"
    combine1 = pd.merge(df_pcap_csv, df_flow, how="left",
                        on=[SRC_IP, DST_IP, DST_PORT, SRC_PORT, PROTOCOL],
                        suffixes=("", _FLOW))
    # Invert the dest/source to capture return traffic
    combine2 = pd.merge(
        df_pcap_csv,
        df_flow,
        how="left",
        left_on=[SRC_IP, DST_IP, DST_PORT, SRC_PORT, PROTOCOL],
        right_on=[DST_IP, SRC_IP, SRC_PORT, DST_PORT, PROTOCOL],
        suffixes=("", _FLOW),
    )
    combine = pd.concat([combine1, combine2])
    combine.drop_duplicates(inplace=True)

    if f"{TIMESTAMP}{_FLOW}" in combine.columns:
        # Drop any rows that are do not have matching times, i.e. keep only rows that the payload timestamp is after the flow started and before the flow ends
        # TIMESTAMP is measured in seconds
        # TIMESTAMP_FLOW has resolution of either 1 second or 60 seconds, recorded in offset
        # FLOW_DURATION is measured in microseconds
        combine = combine[
            (combine[f"{TIMESTAMP}{_FLOW}"] - combine[OFFSET] <= combine[TIMESTAMP])
            & (combine[TIMESTAMP] <= combine[f"{TIMESTAMP}{_FLOW}"] + combine[OFFSET] + combine[FLOW_DURATION] / 1e6)
        ]

    if f"{LABEL}{_FLOW}" in combine.columns:
        combine[LABEL] = combine[f"{LABEL}{_FLOW}"]

    combine.loc[combine[LABEL] == "", LABEL] = LABEL_VALUE_BENIGN

    columns = df_pcap_csv.columns if LABEL in df_pcap_csv.columns else [*df_pcap_csv.columns, LABEL]
    combine.to_csv(output_file, columns=columns, index=False)
    return combine.index.size


# ex: /usr/bin/python3 /usr/local/opnsense/scripts/ml/assignlabel.py --data-source=cic2018-payloads/*/*.csv --label-source=cic2018/*.csv --data-destination=cic2018-payloads-label

if __name__ == "__main__":
    args = parser.parse_args()
    data_source = args.data_source
    label_source = args.label_source
    data_destination = args.data_destination

    log.info('start dataprocessor_assignlabel: %s', data_source)
    kill_exists_processing()
    res = assign_label_to_extracted_csv(label_source, data_source, data_destination)
    log.info('finish dataprocessor_assignlabel: %s, %s', data_source, res['result'].tolist())
