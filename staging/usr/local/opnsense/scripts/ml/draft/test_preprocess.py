from functools import reduce

import numpy as np
from pandas import DataFrame

df = DataFrame.from_dict({
    'f1': [5, 3, np.inf, 1, 0],
    'f2': [5, -np.inf, 2, 1, np.inf],
    'label': [0, 0, 0, 1, 0.1]
})

df = df.fillna(0.).replace([np.inf, -np.inf], 0)

print(df)
