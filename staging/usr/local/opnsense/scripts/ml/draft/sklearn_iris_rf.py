import pandas as pd
from sklearn import datasets
from sklearn.ensemble import RandomForestClassifier
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
import sys

sys.path.insert(0, '/usr/local/opnsense/scripts/ml')

import common

common.init_experiment('iris_rf')

iris = datasets.load_iris()
iris_train = pd.DataFrame(iris.data, columns=iris.feature_names)
clf = RandomForestClassifier(max_depth=7, random_state=0)
clf.fit(iris_train, iris.target)
signature = infer_signature(iris_train, clf.predict(iris_train))
mlflow.sklearn.log_model(clf, "iris_rf", signature=signature)