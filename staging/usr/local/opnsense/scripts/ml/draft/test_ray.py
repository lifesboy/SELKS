import ray
import pandas as pd
import pyarrow as pa

a = ray.data.from_items([{"A": x % 3, "B": x} for x in range(100)])
ag = a.groupby('A')
ac = ag.map_groups(lambda i: pd.DataFrame.from_dict({'A': [i['A'][0]], 'size': [i.index.size]}))
count_df: pd.DataFrame = ac.to_pandas()
count_df.loc[count_df['A'] == 0]['size'][0]
count_df.sum()['size']