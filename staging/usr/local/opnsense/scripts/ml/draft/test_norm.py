# /cic/dataset/featured_extracted/cic2018/Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv.1.csv

import ray
from ray.rllib.utils.framework import tf_function
from ray.rllib.utils.framework import try_import_tf
from pandas import DataFrame

tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

LABEL_VALUE_BENIGN = 'Benign'


def norm_port(port: int) -> float:
    return port / 65535


@tf_function(tf)
def norm_label(v: str) -> int:
    return 0 if tf.math.equal(v, '') or tf.math.equal(v, LABEL_VALUE_BENIGN) else 1


ray.init()

df = DataFrame.from_dict({
    'f1': [5, 3, 2, 1, 0],
    'label': ['', 'Benign', 'Benign', 'Brute Force -Web', 'Benign']
})
dst_port = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df['f1'])).map(norm_port)
label = tf.data.Dataset.from_tensor_slices(tf.convert_to_tensor(df['label'])).map(norm_label)

print(list(label.as_numpy_iterator()))
print(list(dst_port.as_numpy_iterator()))
