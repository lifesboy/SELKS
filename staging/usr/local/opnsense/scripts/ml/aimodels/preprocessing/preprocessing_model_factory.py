#!/usr/bin/python3
import mlflow

from cic2018_norm_model import Cic2018NormModel
from cicflowmeter_norm_model import CicFlowmeterNormModel


class PreProcessingModelFactory:

    @staticmethod
    def get_model(name: str) -> mlflow.pyfunc.PythonModel:
        return Cic2018NormModel if name == 'Cic2018NormModel' else CicFlowmeterNormModel
