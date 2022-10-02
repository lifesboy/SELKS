import ray
import numpy as np

a = ray.data.from_items([{"A": x % 3, "B": 1 + x, "C": 0.5 * x} for x in range(1)])
df = a.to_pandas()
print(df)

df = df[["B", "A"]]
print(df)

b = df.to_numpy(dtype=np.float64).flatten()
print(b)

token = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], np.float64)
print(token)
