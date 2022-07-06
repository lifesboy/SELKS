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
from ray.rllib.utils.framework import tf_function
from ray.util.client import ray

from ray.rllib.utils.framework import try_import_tf
tf1, tf, tfv = try_import_tf()

DST_PORT = 'dst_port'
PROTOCOL = 'protocol'
TIMESTAMP = 'timestamp'
FLOW_DURATION = 'flow_duration'
TOT_FWD_PKTS = 'tot_fwd_pkts'
TOT_BWD_PKTS = 'tot_bwd_pkts'
LABEL = 'label'
LABEL_VALUE_BENIGN = 'Benign'

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


# "Flow Duration"
def norm_max_int(v: int) -> float:
    return v / sys.maxsize


def norm_n_int(v: int, n: int = sys.maxsize) -> float:
    return v / n if v < n else n


@tf_function(tf)
def norm_size_1mb(v: float) -> float:
    return (v if v < SIZE_1MB else SIZE_1MB) / SIZE_1MB


@tf_function(tf)
def norm_time_1h(v: int) -> float:
    return (v if v < TIME_1H else TIME_1H) / SIZE_1MB


def norm_ip(ip: str) -> int:
    return struct.unpack('!I', socket.inet_aton(ip))[0]


@tf_function(tf)
def norm_label(v: str) -> int:
    return 0 if (not v) or (v == LABEL_VALUE_BENIGN) else 1
