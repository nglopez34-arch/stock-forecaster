import pandas as pd
import matplotlib.pyplot as plt

# Load parquet
df = pd.read_parquet('raw_data.parquet')

# Calculate EWMA for each stock while preserving timestamps
ewma_df = df.copy()
ewma_df['close'] = df.groupby('symbol')['close'].transform(
    lambda x: x.ewm(span=20, adjust=False).mean()
)

print(df)
print(ewma_df)

# Plot for a single stock to visualize better
sample_symbol = df['symbol'].iloc[0]
mask_orig = df['symbol'] == sample_symbol
mask_ewma = ewma_df['symbol'] == sample_symbol

plt.plot(df[mask_orig]['timestamp'], df[mask_orig]['close'], label='Original', alpha=0.7)
plt.plot(ewma_df[mask_ewma]['timestamp'], ewma_df[mask_ewma]['close'], label='EWMA', alpha=0.7)
plt.legend()
plt.show()