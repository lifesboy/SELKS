import tensorflow as tf
a = tf.data.Dataset.from_tensor_slices([[['1'], ['1']], [['2'], ['2']], [['2'], ['1']], [['1'], ['1']]])
list(a.as_numpy_iterator())
list(a.flat_map(tf.data.Dataset.from_tensor_slices).as_numpy_iterator())
list(a.flat_map(tf.data.Dataset.from_tensor_slices).flat_map(tf.data.Dataset.from_tensor_slices).as_numpy_iterator())
list(a.flat_map(tf.data.Dataset.from_tensor_slices).flat_map(tf.data.Dataset.from_tensor_slices).unique().as_numpy_iterator())
labels = a.flat_map(tf.data.Dataset.from_tensor_slices).flat_map(tf.data.Dataset.from_tensor_slices).unique().as_numpy_iterator()

# list(a.flat_map(tf.data.Dataset.from_tensor_slices).map(lambda i: tf.unique(i)[0]).as_numpy_iterator())

# a.map(lambda i: tf.unique(i)[0]).reduce([''], lambda x, y: tf.unique(tf.concat(values=[x, y], axis=0))[0]).numpy().tolist()

au = a.unique()
al = list(au.as_numpy_iterator())

# ==========
x = ['', '1']
y = ['1', '2']
tf.concat(values=[x, y], axis=0)
tf.unique(tf.concat(values=[x, y], axis=0))[0]

b = tf.data.Dataset.from_tensor_slices([['', '1'], ['1', '2']])
b.reduce([''], lambda x, y: tf.unique(tf.concat(values=[x, y], axis=0))[0])