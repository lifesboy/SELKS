#!/usr/bin/python3
from typing import Union, Type

import mlflow

from cic2018_norm_model import Cic2018NormModel
from cicflowmeter_norm_model import CicFlowmeterNormModel


class PreProcessingModelFactory:

    @staticmethod
    def get_model(name: str) -> Type[Union[Cic2018NormModel, CicFlowmeterNormModel]]:
        return Cic2018NormModel if name == 'Cic2018NormModel' else CicFlowmeterNormModel
