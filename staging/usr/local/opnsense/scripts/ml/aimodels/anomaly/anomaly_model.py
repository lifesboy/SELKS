#!/usr/bin/python3
import os
import time
from pathlib import Path

import numpy as np
import mlflow
import pandas
import ray
from mlflow.types import Schema, ColSpec, DataType

import common

from gym import Space
from keras import Model
from mlflow.models.signature import ModelSignature
from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.tf.recurrent_net import RecurrentNetwork
from ray.rllib.utils.typing import ModelConfigDict

from ray.rllib.utils.framework import try_import_tf

from aimodels.model_meta import ModelMeta
from anomaly_normalization import LABEL

tf1, tf, tfv = try_import_tf()
from ray.rllib.utils.annotations import override


class AnomalyModel(RecurrentNetwork):

    @staticmethod
    def get_model_meta() -> ModelMeta:
        return ModelMeta(artifact_path=common.MODEL_ARTIFACT_PATH,
                         registered_model_name=common.MODEL_NAME,
                         python_model=None,  # AnomalyModel(),
                         conda_env={
                             'channels': ['defaults', 'conda-forge'],
                             'dependencies': [
                                 'python={}'.format(common.PYTHON_VERSION),
                                 'pip'
                             ],
                             'pip': [
                                 'mlflow=={}'.format(mlflow.__version__),
                                 'pandas=={}'.format(pandas.__version__),
                                 'ray=={}'.format(ray.__version__)
                             ],
                             'name': 'mlflow-env'
                         })

    def __init__(self,
                 obs_space: Space,
                 action_space: Space,
                 num_outputs: int,
                 model_config: ModelConfigDict,
                 name: str,
                 **kwargs):
        super(AnomalyModel, self).__init__(obs_space, action_space, num_outputs,
                                           model_config, name)
        # we have to pass features list to save model dynamic signature for each version,
        # so that we can detect to preprocess and infer data dynamically
        # Unfortunately, mlflow limit length of param to 5000 character,
        # it causes training process fail with mlflow.autolog
        # which unable to log model custom params inside training param in a single json
        # in order to go forward in this time, we have to disable mlflow.autolog
        #
        # mlflow.tensorflow.autolog()
        # # mlflow.keras.autolog()
        self.parent_run_id: str = kwargs.get('parent_run_id', '')
        self.lesson: str = kwargs.get('lesson', '%s-model-tuning' % time.time())

        self._run, self._client = common.init_experiment(name='anomaly-model', run_name=f"{self.lesson}-model")
        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_RUN_TAG, value='model-tuning')

        self.base_version: str = kwargs.get('base_version', '')
        self.base_version_dir: str = kwargs.get('base_version_dir', '')
        self.hidden_size: int = kwargs.get('hidden_size', 256)
        self.cell_size: int = kwargs.get('cell_size', 64)
        self.features: [str] = kwargs.get('features', [])

        self._client.set_tag(run_id=self._run.info.run_id, key=common.TAG_PARENT_RUN_UUID, value=self.parent_run_id)
        self._client.log_param(run_id=self._run.info.run_id, key='base_version', value=self.base_version)

        # Define input layers
        input_layer = tf.keras.layers.Input(shape=(None, obs_space.shape[0]), name="inputs")
        state_in_h = tf.keras.layers.Input(shape=(self.cell_size,), name="h")
        state_in_c = tf.keras.layers.Input(shape=(self.cell_size,), name="c")
        seq_in = tf.keras.layers.Input(shape=(), name="seq_in", dtype=tf.int32)

        # Preprocess observation with a hidden layer and send to LSTM cell
        dense1 = tf.keras.layers.Dense(self.hidden_size, activation=None, name="dense1")(input_layer)
        lstm_out, state_h, state_c = tf.keras.layers.LSTM(
            self.cell_size, return_sequences=True, return_state=True, name="lstm")(
            inputs=dense1,
            mask=tf.sequence_mask(seq_in),
            initial_state=[state_in_h, state_in_c]
        )

        # Postprocess LSTM output with another hidden layer and compute values
        logits = tf.keras.layers.Dense(
            self.num_outputs,
            activation=tf.keras.activations.sigmoid,
            name="logits")(lstm_out)
        values = tf.keras.layers.Dense(
            1, activation='sigmoid', name="values")(lstm_out)

        # Create the RNN model
        self.rnn_model: Model = Model(
            inputs=[input_layer, seq_in, state_in_h, state_in_c],
            outputs=[logits, values, state_h, state_c])

        if self.base_version and self.base_version not in ['', '0']:
            base_model: Model = mlflow.keras.load_model(f'models:/{common.MODEL_NAME}/{self.base_version}')
            self.rnn_model = base_model if base_model else self.rnn_model
            self._client.log_param(run_id=self._run.info.run_id, key='load_model', value=base_model.name if base_model else '')

        self.rnn_model.summary()

    @override(RecurrentNetwork)
    def forward_rnn(self, inputs, state, seq_lens):
        model_out, self._value_out, h, c = self.rnn_model([inputs, seq_lens] + state)

        # # Creating output tf.Variables to specify the output of the saved model.
        # feat_specifications = {
        #     "SepalLength": tf.Variable([], dtype=tf.float64, name="SepalLength"),
        #     "SepalWidth": tf.Variable([], dtype=tf.float64, name="SepalWidth"),
        #     "PetalLength": tf.Variable([], dtype=tf.float64, name="PetalLength"),
        #     "PetalWidth": tf.Variable([], dtype=tf.float64, name="PetalWidth"),
        # }
        # receiver_fn = tf.estimator.export.build_raw_serving_input_receiver_fn(feat_specifications)
        # # self.rnn_model.export_saved_model("/tmp/anomaly_model/", receiver_fn).decode("utf-8")
        # # tf.keras.experimental.export_saved_model(self.rnn_model, "/tmp/anomaly_model/")

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

    def save_h5(self, checkpoint_dir):
        h5_dir = os.path.join(checkpoint_dir, "h5")
        h5_path = os.path.join(h5_dir, "saved_model.h5")
        Path(h5_dir).mkdir(parents=True, exist_ok=True)
        self.rnn_model.save_weights(h5_path)
        self.rnn_model.save(h5_path)

    def save_mlflow(self):
        common.save_anomaly_model_to_mlflow(self.rnn_model, self.features)

    def mark_resumed_base_version(self):
        Path(self.base_version_dir).mkdir(parents=True, exist_ok=True)
