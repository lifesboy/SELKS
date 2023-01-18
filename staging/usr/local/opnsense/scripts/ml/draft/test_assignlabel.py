from functools import reduce

from pandas import DataFrame

df_label = DataFrame.from_dict({
    'f1': [5, 3, 2, 1, 0],
    'f2': [5, 3, 2, 1, 0],
    'label': [0, 0, 0, 1, 0.1]
})

df = DataFrame.from_dict({
    'f1': [5, 3, 2, 1, 0, 1, 2, 3],
    'f2': [5, 3, 2, 1, 0, 1, 2, 3],
})

print(df)

merged_features = list(set(df_label.columns) - set(['label']))

x = df_label[:1]
f1 = merged_features[0]
a1 = df[f1] == x[f1][0]


f2 = merged_features[1]
a2 = df[f2] == x[f2][0]

a = a1 & a2

df_label.apply(lambda x: print(reduce(lambda a, f: a & (df[f] == x[f][0]), merged_features)), axis=1)

print(df)
