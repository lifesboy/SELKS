from functools import reduce

from pandas import DataFrame

TIMESTAMP = 'timestamp'

df = DataFrame.from_dict({
    'f1': [5, 3, 2, 1, 0, 1, 2, 3],
    'f2': [5, 3, 2, 1, 0, 1, 2, 3],
    TIMESTAMP: [
        '2023-01-14 23:08:25',
        '2023-01-15 00:08:25',
        '2023-01-14 23:08:25',
        '2023-01-14 23:08:25',
        '2023-01-14 23:08:25',
        '2023-01-14 23:08:25',
        '2023-01-14 23:08:25',
        '2023-01-18 23:08:25'
    ],
})

print(df)

df_filter = df['f1'].isin([1, 3])
df_filter &= df[TIMESTAMP] >= '2023-01-14 23:09:25'
df_filter &= df[TIMESTAMP] < '2023-01-19 23:08:25'
df.loc[df_filter, 'label'] = 'Anomaly'
df.loc[df['label'].isna(), 'label'] = ''

print(df)