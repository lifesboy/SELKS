import ray
import pandas as pd
import pyarrow as pa
from pyarrow.lib import Schema
from ray.data.aggregate import Count

a = ray.data.from_items([{"A": x % 3, "B": x} for x in range(100)])
ag = a.groupby('A')
ac = ag.aggregate(Count())
count_df: pd.DataFrame = ac.to_pandas()
count_df.loc[count_df['A'] == 0].sum()['count()']
count_df.sum()['count()']

schema: Schema = a.schema(fetch_if_missing=True)
print('schema=%s' % schema.names)