import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
df = pd.read_parquet('raw_data.parquet')
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)  # Set a wider total line width
pd.set_option("display.max_columns", None)
df = df.set_index("timestamp")
df = df.loc["2025-12-23 14:30:00":"2025-12-23 21:00:00"]

#convert to log returns
df['log_returns'] = np.log(df['close'])
df['log_returns'] = df['log_returns'].diff().fillna(0)
df['close'] = df['log_returns']

#Simple Moving Average
sma = []
close = df['close'].to_numpy()
window_size = 5
for i, row in enumerate(df.itertuples(index=False)):
    if i > window_size:
        window = close[i-window_size:i]
        new_val = window.mean()
    else:
        window = close[:i]
        new_val = window.mean() if len(window) > 0 else close[i]
    sma.append(new_val)
df["sma"] = sma

#whatever this is supposed to be
my_line = []
def func(x):
    return np.exp((np.log(0.5) / 5) * x)
for i, row in enumerate(df.itertuples(index=False)):
    if i > 0:
        weights = func(np.arange(i))
        weights = weights / np.sum(weights)
        weights = weights [::-1]
        my_line.append(np.sum(weights * close[:i]))
    else:
        my_line.append(close[i])
df["my_line"] = my_line

plt.plot(df.index,df['my_line'],label='my_line')
#plt.plot(df.index,df['sma'],label='sma')
plt.plot(df.index,df['close'])
plt.legend()
plt.show()
print(df)







