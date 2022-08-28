#!/usr/bin/python3

import numpy as np
import mlflow

from gym import Space
from keras import Model
from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.tf.recurrent_net import RecurrentNetwork
from ray.rllib.utils.typing import ModelConfigDict

from ray.rllib.utils.framework import try_import_tf

tf1, tf, tfv = try_import_tf()
from ray.rllib.utils.annotations import override


class AnomalyModel(RecurrentNetwork):

    def __init__(self,
                 obs_space: Space,
                 action_space: Space,
                 num_outputs: int,
                 model_config: ModelConfigDict,
                 name: str,
                 hiddens_size: int = 256,
                 cell_size: int = 64):
        super(AnomalyModel, self).__init__(obs_space, action_space, num_outputs,
                                           model_config, name)
        self.cell_size = cell_size

        # Define input layers
        input_layer = tf.keras.layers.Input(
            shape=(None, obs_space.shape[0]), name="inputs")
        state_in_h = tf.keras.layers.Input(shape=(cell_size,), name="h")
        state_in_c = tf.keras.layers.Input(shape=(cell_size,), name="c")
        seq_in = tf.keras.layers.Input(shape=(), name="seq_in", dtype=tf.int32)

        # Preprocess observation with a hidden layer and send to LSTM cell
        dense1 = tf.keras.layers.Dense(
            hiddens_size, activation=tf.nn.relu, name="dense1")(input_layer)
        lstm_out, state_h, state_c = tf.keras.layers.LSTM(
            cell_size, return_sequences=True, return_state=True, name="lstm")(
            inputs=dense1,
            mask=tf.sequence_mask(seq_in),
            initial_state=[state_in_h, state_in_c])

        # Postprocess LSTM output with another hidden layer and compute values
        logits = tf.keras.layers.Dense(
            self.num_outputs,
            activation=tf.keras.activations.linear,
            name="logits")(lstm_out)
        values = tf.keras.layers.Dense(
            1, activation=None, name="values")(lstm_out)

        # Create the RNN model
        self.rnn_model: Model = Model(
            inputs=[input_layer, seq_in, state_in_h, state_in_c],
            outputs=[logits, values, state_h, state_c])
        self.rnn_model.summary()

    @override(RecurrentNetwork)
    def forward_rnn(self, inputs, state, seq_lens):
        model_out, self._value_out, h, c = self.rnn_model([inputs, seq_lens] +
                                                          state)

        # Creating output tf.Variables to specify the output of the saved model.
        feat_specifications = {
            "SepalLength": tf.Variable([], dtype=tf.float64, name="SepalLength"),
            "SepalWidth": tf.Variable([], dtype=tf.float64, name="SepalWidth"),
            "PetalLength": tf.Variable([], dtype=tf.float64, name="PetalLength"),
            "PetalWidth": tf.Variable([], dtype=tf.float64, name="PetalWidth"),
        }
        receiver_fn = tf.estimator.export.build_raw_serving_input_receiver_fn(feat_specifications)
        # self.rnn_model.export_saved_model("/tmp/anomaly_model/", receiver_fn).decode("utf-8")
        # tf.keras.experimental.export_saved_model(self.rnn_model, "/tmp/anomaly_model/")
        mlflow.keras.log_model(self.rnn_model, "anomaly-model")

        return model_out, [h, c]

    @override(ModelV2)
    def get_initial_state(self):
        return [
            np.zeros(self.cell_size, np.float32),
            np.zeros(self.cell_size, np.float32),
        ]

    @override(ModelV2)
    def value_function(self):
        return tf.reshape(self._value_out, [-1])