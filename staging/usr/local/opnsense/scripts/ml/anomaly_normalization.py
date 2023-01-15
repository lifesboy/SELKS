import socket
import struct
import sys

# Dst Port,Protocol,Timestamp,Flow Duration,Tot Fwd Pkts,Tot Bwd Pkts,TotLen Fwd Pkts,TotLen Bwd Pkts,Fwd Pkt Len Max,Fwd Pkt Len Min,Fwd Pkt Len Mean,Fwd Pkt Len Std,Bwd Pkt Len Max,Bwd Pkt Len Min,Bwd Pkt Len Mean,Bwd Pkt Len Std,Flow Byts/s,Flow Pkts/s,Flow IAT Mean,Flow IAT Std,Flow IAT Max,Flow IAT Min,Fwd IAT Tot,Fwd IAT Mean,Fwd IAT Std,Fwd IAT Max,Fwd IAT Min,Bwd IAT Tot,Bwd IAT Mean,Bwd IAT Std,Bwd IAT Max,Bwd IAT Min,Fwd PSH Flags,Bwd PSH Flags,Fwd URG Flags,Bwd URG Flags,Fwd Header Len,Bwd Header Len,Fwd Pkts/s,Bwd Pkts/s,Pkt Len Min,Pkt Len Max,Pkt Len Mean,Pkt Len Std,Pkt Len Var,FIN Flag Cnt,SYN Flag Cnt,RST Flag Cnt,PSH Flag Cnt,ACK Flag Cnt,URG Flag Cnt,CWE Flag Count,ECE Flag Cnt,Down/Up Ratio,Pkt Size Avg,Fwd Seg Size Avg,Bwd Seg Size Avg,Fwd Byts/b Avg,Fwd Pkts/b Avg,Fwd Blk Rate Avg,Bwd Byts/b Avg,Bwd Pkts/b Avg,Bwd Blk Rate Avg,Subflow Fwd Pkts,Subflow Fwd Byts,Subflow Bwd Pkts,Subflow Bwd Byts,Init Fwd Win Byts,Init Bwd Win Byts,Fwd Act Data Pkts,Fwd Seg Size Min,Active Mean,Active Std,Active Max,Active Min,Idle Mean,Idle Std,Idle Max,Idle Min,Label
# 443,6,02/03/2018 08:47:38,141385,9,7,553,3773,202,0,61.44444444,87.53443767,1460,0,539,655.4329358,30597.30523,113.1661775,9425.666667,19069.11685,73403,1,141385,17673.125,23965.32327,73403,22,51417,8569.5,13036.89082,31525,1,0,0,0,0,192,152,63.65597482,49.51020264,0,1460,254.4705882,474.7129551,225352.3897,0,0,1,1,0,0,0,1,0,270.375,61.44444444,539,0,0,0,0,0,0,9,553,7,3773,8192,119,4,20,0,0,0,0,0,0,0,0,Benign
# 49684,6,02/03/2018 08:47:38,281,2,1,38,0,38,0,19,26.87005769,0,0,0,0,135231.3167,10676.15658,140.5,174.655375,264,17,281,281,0,281,281,0,0,0,0,0,1,0,0,0,40,20,7117.437722,3558.718861,0,38,19,21.93931023,481.3333333,0,1,0,0,1,0,0,0,0,25.33333333,19,0,0,0,0,0,0,0,2,38,1,0,123,0,0,20,0,0,0,0,0,0,0,0,Benign
# 443,6,02/03/2018 08:47:40,279824,11,15,1086,10527,385,0,98.72727273,129.3924966,1460,0,701.8,636.3141856,41501.0864,92.91554692,11192.96,24379.44834,112589,1,279728,27972.8,36167.74032,112589,94,258924,18494.57143,36356.50372,133669,1,0,0,0,0,232,312,39.31042369,53.60512322,0,1460,430.1111111,566.234209,320621.1795,0,0,1,1,0,0,0,1,1,446.6538462,98.72727273,701.8,0,0,0,0,0,0,11,1086,15,10527,8192,1047,5,20,0,0,0,0,0,0,0,0,Benign
# 443,6,02/03/2018 08:47:40,132,2,0,0,0,0,0,0,0,0,0,0,0,0,15151.51515,132,0,132,132,132,132,0,132,132,0,0,0,0,0,0,0,0,0,40,0,15151.51515,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,256,-1,0,20,0,0,0,0,0,0,0,0,Benign
# 443,6,02/03/2018 08:47:41,274016,9,13,1285,6141,517,0,142.7777778,183.8877224,1460,0,472.3846154,611.1804887,27100.60726,80.28728249,13048.38095,26311.62703,114077,1,273946,34243.25,37996.56546,114077,201,252994,21082.83333,39075.73819,135611,1,0,0,0,0,192,272,32.84479738,47.44248511,0,1460,322.8695652,497.2547641,247262.3004,0,0,1,1,0,0,0,1,1,337.5454545,142.7777778,472.3846154,0,0,0,0,0,0,9,1285,13,6141,8192,1047,5,20,0,0,0,0,0,0,0,0,Benign
# 443,6,02/03/2018 08:47:41,250,2,0,0,0,0,0,0,0,0,0,0,0,0,8000,250,0,250,250,250,250,0,250,250,0,0,0,0,0,0,0,0,0,40,0,8000,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,251,-1,0,20,0,0,0,0,0,0,0,0,Benign
# 80,6,02/03/2018 08:47:41,5964033,3,1,0,0,0,0,0,0,0,0,0,0,0,0.6706871,1988011,3425209.65,5943084,19,5964033,2982016.5,4187581.818,5943084,20949,0,0,0,0,0,0,0,0,0,72,32,0.503015325,0.167671775,0,0,0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,3,0,1,0,8192,29200,0,20,0,0,0,0,0,0,0,0,Benign
# 49690,6,02/03/2018 08:47:46,144,2,0,0,0,0,0,0,0,0,0,0,0,0,13888.88889,144,0,144,144,144,144,0,144,144,0,0,0,0,0,0,0,0,0,40,0,13888.88889,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,913,-1,0,20,0,0,0,0,0,0,0,0,Benign
# 443,6,02/03/2018 08:48:17,90828,8,8,1748,3898,1078,0,218.5,363.7133879,1460,0,487.25,639.5062269,62161.44801,176.1571322,6055.2,9948.657879,23343,1,69438,9919.714286,11893.19116,23365,48,69553,9936.142857,12312.69524,23723,1,0,0,0,0,172,172,88.07856608,88.07856608,0,1460,332.1176471,512.0358731,262180.7353,0,0,1,1,0,0,0,1,1,352.875,218.5,487.25,0,0,0,0,0,0,8,1748,8,3898,8192,8192,5,20,0,0,0,0,0,0,0,0,Benign

# "Dst Port", "Protocol", "Timestamp", "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts",
# "TotLen Bwd Pkts", "Fwd Pkt Len Max", "Fwd Pkt Len Min", "Fwd Pkt Len Mean", "Fwd Pkt Len Std", "Bwd Pkt Len Max",
# "Bwd Pkt Len Min", "Bwd Pkt Len Mean", "Bwd Pkt Len Std", "Flow Byts/s", "Flow Pkts/s", "Flow IAT Mean",
# "Flow IAT Std", "Flow IAT Max", "Flow IAT Min", "Fwd IAT Tot", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max",
# "Fwd IAT Min", "Bwd IAT Tot", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags",
# "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "Fwd Header Len", "Bwd Header Len", "Fwd Pkts/s", "Bwd Pkts/s",
# "Pkt Len Min", "Pkt Len Max", "Pkt Len Mean", "Pkt Len Std", "Pkt Len Var", "FIN Flag Cnt", "SYN Flag Cnt",
# "RST Flag Cnt", "PSH Flag Cnt", "ACK Flag Cnt", "URG Flag Cnt", "CWE Flag Count", "ECE Flag Cnt", "Down/Up Ratio",
# "Pkt Size Avg", "Fwd Seg Size Avg", "Bwd Seg Size Avg", "Fwd Byts/b Avg", "Fwd Pkts/b Avg", "Fwd Blk Rate Avg",
# "Bwd Byts/b Avg", "Bwd Pkts/b Avg", "Bwd Blk Rate Avg", "Subflow Fwd Pkts", "Subflow Fwd Byts", "Subflow Bwd Pkts",
# "Subflow Bwd Byts", "Init Fwd Win Byts", "Init Bwd Win Byts", "Fwd Act Data Pkts", "Fwd Seg Size Min",
# "Active Mean", "Active Std", "Active Max", "Active Min", "Idle Mean", "Idle Std", "Idle Max", "Idle Min", "Label"
import numpy as np
from ray.rllib.utils.framework import tf_function
from ray.util.client import ray

from ray.rllib.utils.framework import try_import_tf
tf1, tf, tfv = try_import_tf()

FEATURE_NAMES = 'Flow ID,Src IP,Src Port,Dst IP,Dst Port,Protocol,Timestamp,Flow Duration,Tot Fwd Pkts,Tot Bwd Pkts,' \
                'TotLen Fwd Pkts,TotLen Bwd Pkts,Fwd Pkt Len Max,Fwd Pkt Len Min,Fwd Pkt Len Mean,Fwd Pkt Len Std,' \
                'Bwd Pkt Len Max,Bwd Pkt Len Min,Bwd Pkt Len Mean,Bwd Pkt Len Std,Flow Byts/s,Flow Pkts/s,' \
                'Flow IAT Mean,Flow IAT Std,Flow IAT Max,Flow IAT Min,Fwd IAT Tot,Fwd IAT Mean,Fwd IAT Std,' \
                'Fwd IAT Max,Fwd IAT Min,Bwd IAT Tot,Bwd IAT Mean,Bwd IAT Std,Bwd IAT Max,Bwd IAT Min,Fwd PSH Flags,' \
                'Bwd PSH Flags,Fwd URG Flags,Bwd URG Flags,Fwd Header Len,Bwd Header Len,Fwd Pkts/s,Bwd Pkts/s,' \
                'Pkt Len Min,Pkt Len Max,Pkt Len Mean,Pkt Len Std,Pkt Len Var,FIN Flag Cnt,SYN Flag Cnt,RST Flag Cnt,' \
                'PSH Flag Cnt,ACK Flag Cnt,URG Flag Cnt,CWE Flag Count,ECE Flag Cnt,Down/Up Ratio,Pkt Size Avg,' \
                'Fwd Seg Size Avg,Bwd Seg Size Avg,Fwd Byts/b Avg,Fwd Pkts/b Avg,Fwd Blk Rate Avg,Bwd Byts/b Avg,' \
                'Bwd Pkts/b Avg,Bwd Blk Rate Avg,Subflow Fwd Pkts,Subflow Fwd Byts,Subflow Bwd Pkts,Subflow Bwd Byts,' \
                'Init Fwd Win Byts,Init Bwd Win Byts,Fwd Act Data Pkts,Fwd Seg Size Min,Active Mean,Active Std,' \
                'Active Max,Active Min,Idle Mean,Idle Std,Idle Max,Idle Min,Label'.split(',')
FEATURE_NAMES_NORMED = list(map(lambda i: i.lower().replace(' ', '_').replace('/', '_'), FEATURE_NAMES))
#FEATURE_NAMES_NORMED = list(map(lambda i: "%s_CIC = '%s'" % (i.lower().replace(' ', '_').replace('/', '_').upper(), i), FEATURE_NAMES))
#print("\n".join(FEATURE_NAMES_NORMED))

FLOW_ID = 'flow_id'
SRC_IP = 'src_ip'
SRC_PORT = 'src_port'
SRC_MAC = 'src_mac'
DST_IP = 'dst_ip'
DST_PORT = 'dst_port'
DST_MAC = 'dst_mac'
PROTOCOL = 'protocol'
TIMESTAMP = 'timestamp'
FLOW_DURATION = 'flow_duration'
TOT_FWD_PKTS = 'tot_fwd_pkts'
TOT_BWD_PKTS = 'tot_bwd_pkts'

TOTLEN_FWD_PKTS = 'totlen_fwd_pkts'
TOTLEN_BWD_PKTS = 'totlen_bwd_pkts'
FWD_PKT_LEN_MAX = 'fwd_pkt_len_max'
FWD_PKT_LEN_MIN = 'fwd_pkt_len_min'
FWD_PKT_LEN_MEAN = 'fwd_pkt_len_mean'
FWD_PKT_LEN_STD = 'fwd_pkt_len_std'
BWD_PKT_LEN_MAX = 'bwd_pkt_len_max'
BWD_PKT_LEN_MIN = 'bwd_pkt_len_min'
BWD_PKT_LEN_MEAN = 'bwd_pkt_len_mean'
BWD_PKT_LEN_STD = 'bwd_pkt_len_std'
FLOW_BYTS_S = 'flow_byts_s'
FLOW_PKTS_S = 'flow_pkts_s'
FLOW_IAT_MEAN = 'flow_iat_mean'
FLOW_IAT_STD = 'flow_iat_std'
FLOW_IAT_MAX = 'flow_iat_max'
FLOW_IAT_MIN = 'flow_iat_min'
FWD_IAT_TOT = 'fwd_iat_tot'
FWD_IAT_MEAN = 'fwd_iat_mean'
FWD_IAT_STD = 'fwd_iat_std'
FWD_IAT_MAX = 'fwd_iat_max'
FWD_IAT_MIN = 'fwd_iat_min'
BWD_IAT_TOT = 'bwd_iat_tot'
BWD_IAT_MEAN = 'bwd_iat_mean'
BWD_IAT_STD = 'bwd_iat_std'
BWD_IAT_MAX = 'bwd_iat_max'
BWD_IAT_MIN = 'bwd_iat_min'
FWD_PSH_FLAGS = 'fwd_psh_flags'
BWD_PSH_FLAGS = 'bwd_psh_flags'
FWD_URG_FLAGS = 'fwd_urg_flags'
BWD_URG_FLAGS = 'bwd_urg_flags'
FWD_HEADER_LEN = 'fwd_header_len'
BWD_HEADER_LEN = 'bwd_header_len'
FWD_PKTS_S = 'fwd_pkts_s'
BWD_PKTS_S = 'bwd_pkts_s'
PKT_LEN_MIN = 'pkt_len_min'
PKT_LEN_MAX = 'pkt_len_max'
PKT_LEN_MEAN = 'pkt_len_mean'
PKT_LEN_STD = 'pkt_len_std'
PKT_LEN_VAR = 'pkt_len_var'
FIN_FLAG_CNT = 'fin_flag_cnt'
SYN_FLAG_CNT = 'syn_flag_cnt'
RST_FLAG_CNT = 'rst_flag_cnt'
PSH_FLAG_CNT = 'psh_flag_cnt'
ACK_FLAG_CNT = 'ack_flag_cnt'
URG_FLAG_CNT = 'urg_flag_cnt'
CWE_FLAG_COUNT = 'cwe_flag_count'
ECE_FLAG_CNT = 'ece_flag_cnt'
DOWN_UP_RATIO = 'down_up_ratio'
PKT_SIZE_AVG = 'pkt_size_avg'
FWD_SEG_SIZE_AVG = 'fwd_seg_size_avg'
BWD_SEG_SIZE_AVG = 'bwd_seg_size_avg'
FWD_BYTS_B_AVG = 'fwd_byts_b_avg'
FWD_PKTS_B_AVG = 'fwd_pkts_b_avg'
FWD_BLK_RATE_AVG = 'fwd_blk_rate_avg'
BWD_BYTS_B_AVG = 'bwd_byts_b_avg'
BWD_PKTS_B_AVG = 'bwd_pkts_b_avg'
BWD_BLK_RATE_AVG = 'bwd_blk_rate_avg'
SUBFLOW_FWD_PKTS = 'subflow_fwd_pkts'
SUBFLOW_FWD_BYTS = 'subflow_fwd_byts'
SUBFLOW_BWD_PKTS = 'subflow_bwd_pkts'
SUBFLOW_BWD_BYTS = 'subflow_bwd_byts'
INIT_FWD_WIN_BYTS = 'init_fwd_win_byts'
INIT_BWD_WIN_BYTS = 'init_bwd_win_byts'
FWD_ACT_DATA_PKTS = 'fwd_act_data_pkts'
FWD_SEG_SIZE_MIN = 'fwd_seg_size_min'
ACTIVE_MEAN = 'active_mean'
ACTIVE_STD = 'active_std'
ACTIVE_MAX = 'active_max'
ACTIVE_MIN = 'active_min'
IDLE_MEAN = 'idle_mean'
IDLE_STD = 'idle_std'
IDLE_MAX = 'idle_max'
IDLE_MIN = 'idle_min'
TTL = 'ttl'
LEN_PAYLOADS = 'len_payloads'
PS = 'p%s'
LABEL = 'label'

PAYLOAD_FEATURE_NUM = 256

ALL_PAYLOAD_FEATURES = [PS % i for i in range(0, PAYLOAD_FEATURE_NUM)]

ALL_FEATURES = [
    SRC_IP,
    SRC_PORT,
    SRC_MAC,
    DST_IP,
    DST_PORT,
    DST_MAC,
    PROTOCOL,
    TIMESTAMP,
    FLOW_DURATION,
    TOT_FWD_PKTS,
    TOT_BWD_PKTS,

    TOTLEN_FWD_PKTS,
    TOTLEN_BWD_PKTS,
    FWD_PKT_LEN_MAX,
    FWD_PKT_LEN_MIN,
    FWD_PKT_LEN_MEAN,
    FWD_PKT_LEN_STD,
    BWD_PKT_LEN_MAX,
    BWD_PKT_LEN_MIN,
    BWD_PKT_LEN_MEAN,
    BWD_PKT_LEN_STD,
    FLOW_BYTS_S,
    FLOW_PKTS_S,
    FLOW_IAT_MEAN,
    FLOW_IAT_STD,
    FLOW_IAT_MAX,
    FLOW_IAT_MIN,
    FWD_IAT_TOT,
    FWD_IAT_MEAN,
    FWD_IAT_STD,
    FWD_IAT_MAX,
    FWD_IAT_MIN,
    BWD_IAT_TOT,
    BWD_IAT_MEAN,
    BWD_IAT_STD,
    BWD_IAT_MAX,
    BWD_IAT_MIN,
    FWD_PSH_FLAGS,
    BWD_PSH_FLAGS,
    FWD_URG_FLAGS,
    BWD_URG_FLAGS,
    FWD_HEADER_LEN,
    BWD_HEADER_LEN,
    FWD_PKTS_S,
    BWD_PKTS_S,
    PKT_LEN_MIN,
    PKT_LEN_MAX,
    PKT_LEN_MEAN,
    PKT_LEN_STD,
    PKT_LEN_VAR,
    FIN_FLAG_CNT,
    SYN_FLAG_CNT,
    RST_FLAG_CNT,
    PSH_FLAG_CNT,
    ACK_FLAG_CNT,
    URG_FLAG_CNT,
    CWE_FLAG_COUNT,
    ECE_FLAG_CNT,
    DOWN_UP_RATIO,
    PKT_SIZE_AVG,
    FWD_SEG_SIZE_AVG,
    BWD_SEG_SIZE_AVG,
    FWD_BYTS_B_AVG,
    FWD_PKTS_B_AVG,
    FWD_BLK_RATE_AVG,
    BWD_BYTS_B_AVG,
    BWD_PKTS_B_AVG,
    BWD_BLK_RATE_AVG,
    SUBFLOW_FWD_PKTS,
    SUBFLOW_FWD_BYTS,
    SUBFLOW_BWD_PKTS,
    SUBFLOW_BWD_BYTS,
    INIT_FWD_WIN_BYTS,
    INIT_BWD_WIN_BYTS,
    FWD_ACT_DATA_PKTS,
    FWD_SEG_SIZE_MIN,
    ACTIVE_MEAN,
    ACTIVE_STD,
    ACTIVE_MAX,
    ACTIVE_MIN,
    IDLE_MEAN,
    IDLE_STD,
    IDLE_MAX,
    IDLE_MIN,
    TTL,
    LEN_PAYLOADS,
    *ALL_PAYLOAD_FEATURES
]

TIMESTAMP_FLOW = 'timestamp_flow'

FLOW_ID_CIC = 'Flow ID'
SRC_IP_CIC = 'Src IP'
SRC_PORT_CIC = 'Src Port'
SRC_MAC_CIC = 'Src Mac'
DST_IP_CIC = 'Dst IP'
DST_PORT_CIC = 'Dst Port'
DST_MAC_CIC = 'Dst Mac'
PROTOCOL_CIC = 'Protocol'
TIMESTAMP_CIC = 'Timestamp'
FLOW_DURATION_CIC = 'Flow Duration'
TOT_FWD_PKTS_CIC = 'Tot Fwd Pkts'
TOT_BWD_PKTS_CIC = 'Tot Bwd Pkts'
TOTLEN_FWD_PKTS_CIC = 'TotLen Fwd Pkts'
TOTLEN_BWD_PKTS_CIC = 'TotLen Bwd Pkts'
FWD_PKT_LEN_MAX_CIC = 'Fwd Pkt Len Max'
FWD_PKT_LEN_MIN_CIC = 'Fwd Pkt Len Min'
FWD_PKT_LEN_MEAN_CIC = 'Fwd Pkt Len Mean'
FWD_PKT_LEN_STD_CIC = 'Fwd Pkt Len Std'
BWD_PKT_LEN_MAX_CIC = 'Bwd Pkt Len Max'
BWD_PKT_LEN_MIN_CIC = 'Bwd Pkt Len Min'
BWD_PKT_LEN_MEAN_CIC = 'Bwd Pkt Len Mean'
BWD_PKT_LEN_STD_CIC = 'Bwd Pkt Len Std'
FLOW_BYTS_S_CIC = 'Flow Byts/s'
FLOW_PKTS_S_CIC = 'Flow Pkts/s'
FLOW_IAT_MEAN_CIC = 'Flow IAT Mean'
FLOW_IAT_STD_CIC = 'Flow IAT Std'
FLOW_IAT_MAX_CIC = 'Flow IAT Max'
FLOW_IAT_MIN_CIC = 'Flow IAT Min'
FWD_IAT_TOT_CIC = 'Fwd IAT Tot'
FWD_IAT_MEAN_CIC = 'Fwd IAT Mean'
FWD_IAT_STD_CIC = 'Fwd IAT Std'
FWD_IAT_MAX_CIC = 'Fwd IAT Max'
FWD_IAT_MIN_CIC = 'Fwd IAT Min'
BWD_IAT_TOT_CIC = 'Bwd IAT Tot'
BWD_IAT_MEAN_CIC = 'Bwd IAT Mean'
BWD_IAT_STD_CIC = 'Bwd IAT Std'
BWD_IAT_MAX_CIC = 'Bwd IAT Max'
BWD_IAT_MIN_CIC = 'Bwd IAT Min'
FWD_PSH_FLAGS_CIC = 'Fwd PSH Flags'
BWD_PSH_FLAGS_CIC = 'Bwd PSH Flags'
FWD_URG_FLAGS_CIC = 'Fwd URG Flags'
BWD_URG_FLAGS_CIC = 'Bwd URG Flags'
FWD_HEADER_LEN_CIC = 'Fwd Header Len'
BWD_HEADER_LEN_CIC = 'Bwd Header Len'
FWD_PKTS_S_CIC = 'Fwd Pkts/s'
BWD_PKTS_S_CIC = 'Bwd Pkts/s'
PKT_LEN_MIN_CIC = 'Pkt Len Min'
PKT_LEN_MAX_CIC = 'Pkt Len Max'
PKT_LEN_MEAN_CIC = 'Pkt Len Mean'
PKT_LEN_STD_CIC = 'Pkt Len Std'
PKT_LEN_VAR_CIC = 'Pkt Len Var'
FIN_FLAG_CNT_CIC = 'FIN Flag Cnt'
SYN_FLAG_CNT_CIC = 'SYN Flag Cnt'
RST_FLAG_CNT_CIC = 'RST Flag Cnt'
PSH_FLAG_CNT_CIC = 'PSH Flag Cnt'
ACK_FLAG_CNT_CIC = 'ACK Flag Cnt'
URG_FLAG_CNT_CIC = 'URG Flag Cnt'
CWE_FLAG_COUNT_CIC = 'CWE Flag Count'
ECE_FLAG_CNT_CIC = 'ECE Flag Cnt'
DOWN_UP_RATIO_CIC = 'Down/Up Ratio'
PKT_SIZE_AVG_CIC = 'Pkt Size Avg'
FWD_SEG_SIZE_AVG_CIC = 'Fwd Seg Size Avg'
BWD_SEG_SIZE_AVG_CIC = 'Bwd Seg Size Avg'
FWD_BYTS_B_AVG_CIC = 'Fwd Byts/b Avg'
FWD_PKTS_B_AVG_CIC = 'Fwd Pkts/b Avg'
FWD_BLK_RATE_AVG_CIC = 'Fwd Blk Rate Avg'
BWD_BYTS_B_AVG_CIC = 'Bwd Byts/b Avg'
BWD_PKTS_B_AVG_CIC = 'Bwd Pkts/b Avg'
BWD_BLK_RATE_AVG_CIC = 'Bwd Blk Rate Avg'
SUBFLOW_FWD_PKTS_CIC = 'Subflow Fwd Pkts'
SUBFLOW_FWD_BYTS_CIC = 'Subflow Fwd Byts'
SUBFLOW_BWD_PKTS_CIC = 'Subflow Bwd Pkts'
SUBFLOW_BWD_BYTS_CIC = 'Subflow Bwd Byts'
INIT_FWD_WIN_BYTS_CIC = 'Init Fwd Win Byts'
INIT_BWD_WIN_BYTS_CIC = 'Init Bwd Win Byts'
FWD_ACT_DATA_PKTS_CIC = 'Fwd Act Data Pkts'
FWD_SEG_SIZE_MIN_CIC = 'Fwd Seg Size Min'
ACTIVE_MEAN_CIC = 'Active Mean'
ACTIVE_STD_CIC = 'Active Std'
ACTIVE_MAX_CIC = 'Active Max'
ACTIVE_MIN_CIC = 'Active Min'
IDLE_MEAN_CIC = 'Idle Mean'
IDLE_STD_CIC = 'Idle Std'
IDLE_MAX_CIC = 'Idle Max'
IDLE_MIN_CIC = 'Idle Min'
LABEL_CIC = 'Label'

LABEL_VALUE_BENIGN = 'Benign'
LABEL_VALUE_ANOMALY = 'Anomaly'

SIZE_1B = 0xFF
SIZE_1KB = 1024
SIZE_1MB = 1024 * SIZE_1KB
SIZE_1GB = 1024 * SIZE_1MB

TIME_1S = 1000
TIME_1M = 60 * TIME_1S
TIME_1H = 60 * TIME_1M
TIME_1D = 24 * TIME_1H

F1 = 'F1'
F2 = 'F2'
F3 = 'F3'
F4 = 'F4'
F5 = 'F5'
F6 = 'F6'


# "Dst Port"
def norm_port(port: int) -> float:
    return port / 65535


# "Protocol"
def norm_protocol(p: int) -> float:
    return p / 100


def norm_flag(f: float) -> float:
    return f / 0xFF


# "Flow Duration"
def norm_max_int(v: int) -> float:
    return v / sys.maxsize


def norm_n_int(v: int, n: int = sys.maxsize) -> float:
    return v / n if v < n else n


@tf_function(tf)
def norm_min_1(x: float) -> float:
    return tf.math.minimum(x, 1.)


# https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8576553/
# Selected features for signal categorization, CIC-IDS2017 and CSE-CIC-IDS2018 datasets.
# CIC-IDS2017	                                            CSE-CIC-IDS2018
# Feature               Signal category FC (Fi)       Feature	        Signal category	FC (Fi)
# FwdPacketLengthMin    SS	0.6787	                   PktLenMax	    SS	0.6618
# FlowBytess            SS	0.3624	                   PktLenStd	    SS	0.0547
# FwdPacketLengthMax    SS	0.3296	                   FwdActDataPkts	SS	0.0118
# FwdURGFlags           SS	0.1520	                   BwdPSHFlags	    SS	0
# CWEFlagCount          SS	0.1520                     BwdURGFlags	    SS	0
# TotalBackwardPackets  DS	−1.6132	                   InitBwdWinByts	DS	−2.0298
# SubflowBwdPackets     DS	−1.6132	                   InitFwdWinByts	DS	−1.6018
# BwdHeaderLength       DS	−1.1659	                   FwdPktLenMax	    DS	−1.4341
# TotalFwdPackets       DS	−0.8473                    BwdHeaderLen	    DS	−1.1041
# SubflowFwdPackets     DS	−0.8473	                   PktSizeAvg	    DS	−0.9627
@tf_function(tf)
def norm_size_1mb(v: float) -> float:
    return tf.math.sign(v) * tf.math.minimum(tf.math.abs(v), SIZE_1MB) / SIZE_1MB


@tf_function(tf)
def norm_time_1h(v: int) -> float:
    return tf.math.sign(v) * tf.math.minimum(tf.math.abs(v), TIME_1H) / TIME_1H


@tf_function(tf)
def norm_size_1kb(v: float) -> float:
    return tf.math.sign(v) * tf.math.minimum(tf.math.abs(v), SIZE_1KB) / SIZE_1KB


@tf_function(tf)
def norm_time_1min(v: int) -> float:
    return tf.math.sign(v) * tf.math.minimum(tf.math.abs(v), TIME_1M) / TIME_1M

@tf_function(tf)
def norm_crop_1byte(v: int) -> float:
    return tf.math.sign(v) * tf.math.minimum(tf.math.abs(v), SIZE_1B)


def norm_ip(ip: str) -> int:
    return struct.unpack('!I', socket.inet_aton(ip))[0]


@tf_function(tf)
def norm_label(v: str) -> int:
    return 0 if tf.math.equal(v, '') or tf.math.equal(v, LABEL_VALUE_BENIGN) else 1

