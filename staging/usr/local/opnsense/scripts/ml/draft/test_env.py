import ray
import numpy as np

a = ray.data.from_items([{"A": x % 3, "B": x, "C": 0.5 * x} for x in range(1)])
df = a.to_pandas()
print(df)

df = df[["A", "B"]]
print(df)

b = df.to_numpy(dtype=np.float64).flatten()
print(b)
