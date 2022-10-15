from pandas import DataFrame

df = DataFrame.from_dict({
    'f1': [5, 3, 2, 1, 0],
    'label': [0, 0, 0, 1, 0.1]
})

df['label'] = df['label'].map({0: 'Benign', 1: 'Anomaly'}).fillna('Benign')

print(df)
