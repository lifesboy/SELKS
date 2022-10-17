import numpy as np

a1 = [1., 0., 1., 0.]
a2 = [0., 0., 1., 1.]
print(f"a1 = {a1}")
print(f"a2 = {a2}")

x = np.sum(np.prod([a1, a2], axis=0))
print(f"sum(prod()) = {x}")

d = np.diff([a1, a2], axis=0)
print(f"diff() = {d}")

y = np.count_nonzero(d * np.pi / 180.)
print(f"count_nonzero(diff()) = {y}")

y = np.sin(d)
print(f"sin(diff(), x > 0) = {y}")
