import numpy as np

a1 = np.array([1., 0., 1., 0.])  # expected
a2 = np.array([0., 0., 1., 1.])  # predicted
a3 = np.logical_xor(a1, a2)
a4 = np.logical_not(a3)
print(f"a1 = {a1}")
print(f"a2 = {a2}")
print(f"a3 = {a3.astype(float)}")
print(f"a4 = {a4.astype(float)}")

# expected 1 is detected
x1 = np.sum(np.prod([a1, a2], axis=0))
print(f"x1 = {x1}")

# expected 1 is mis-detected
x2 = np.sum(a1) - x1
print(f"x2 = {x2}")

# total detected
x3 = np.sum(a4)
print(f"x3 = {x3}")

# expected 0 is detected
x4 = x3 - x1
print(f"x4 = {x4}")

# expected 0 is mis-detected
x5 = np.sum(a3) - x2
print(f"x5 = {x5}")


