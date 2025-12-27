import numpy as np
import matplotlib.pyplot as plt
x = np.arange(10)
def func(x):
    return np.exp((np.log(0.5) / 5) * x)
y = func(x)
y = y / np.sum(y)
print(np.sum(y))
print(y)