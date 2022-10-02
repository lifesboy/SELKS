import numpy as np
import pandas as pd

from gym import Space
from keras import Model
from ray.rllib.utils.framework import try_import_tf
from tensorflow.keras import layers

tf1, tf, tfv = try_import_tf()
print(f"tf={tf.__version__}")

cell_size = 32
hiddens_size = 256
num_outputs = 5
num_feature = 6
obs_space: Space = Space(shape=(num_feature, 10), dtype=np.float32)

input_layer = tf.keras.layers.Input(shape=(None, num_feature), name="inputs")
seq_in = tf.keras.layers.Input(shape=(), name="seq_in", dtype=tf.int32)
state_in_h = tf.keras.layers.Input(shape=(cell_size,), name="h")
state_in_c = tf.keras.layers.Input(shape=(cell_size,), name="c")

# Preprocess observation with a hidden layer and send to LSTM cell
dense1 = tf.keras.layers.Dense(hiddens_size, activation=tf.nn.relu, name="dense1")(input_layer)
lstm_out, state_h, state_c = tf.keras.layers.LSTM(cell_size, return_sequences=True, return_state=True, name="lstm")(
    inputs=dense1, mask=tf.sequence_mask(seq_in), initial_state=[state_in_h, state_in_c])

# Postprocess LSTM output with another hidden layer and compute values
logits = tf.keras.layers.Dense(num_outputs, activation=tf.keras.activations.linear, name="logits")(lstm_out)
values = tf.keras.layers.Dense(1, activation=None, name="values")(lstm_out)

# Create the RNN model
rnn_model: Model = Model(inputs=[input_layer, seq_in, state_in_h, state_in_c], outputs=[logits, values, state_h, state_c])
rnn_model.summary()
#rnn_model.compile(loss='mse', optimizer='adam')


batch = 1
batch_size = 5
#x = tf.keras.preprocessing.sequence.pad_sequences(x, padding="post")
#x = layers.Embedding(input_dim=5000, output_dim=num_feature, mask_zero=True)(x)
s = np.full((batch, 1), fill_value=num_feature, dtype=np.int32)
h = np.random.sample((batch, cell_size))
c = np.random.sample((batch, cell_size))
print('init-----------------')
print('h=%s' % h)
print('c=%s' % c)

for _ in range(0, 2):
    x = np.random.sample(batch * batch_size * num_feature).reshape(batch, batch_size, num_feature)
    print('predict-----------------')
    print(x)

    l, y, h, c = rnn_model.predict(x=[x, s, h, c])
    print(y)
    ydf = pd.DataFrame(x.reshape(batch * batch_size, num_feature)[:, 0].flatten('C'), columns=["f1"])
    ydf['label'] = pd.DataFrame(y.flatten('C'))
    print(ydf)

print(rnn_model.to_json())