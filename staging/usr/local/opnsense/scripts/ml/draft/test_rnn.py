import numpy as np

from gym import Space
from keras import Model
from ray.rllib.utils.framework import try_import_tf

tf1, tf, tfv = try_import_tf()
cell_size = 32
hiddens_size = 256
num_outputs = 5
obs_space: Space = Space(shape=(5, 10), dtype=np.float32)

input_layer = tf.keras.layers.Input(shape=(None, obs_space.shape[0]), name="inputs")
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
rnn_model.compile(loss='mse', optimizer='adam')


batch = 5
x = np.random.sample(25).reshape(batch, 1, 5)
s = np.ones((batch, 1), dtype=np.int32)
h = np.zeros((batch, cell_size), dtype=np.float32)
c = np.zeros((batch, cell_size), dtype=np.float32)

a = rnn_model.predict(x=[x, s, h, c])
print(a)
print(rnn_model.to_json())