import pandas as pd
df = pd.read_parquet('data/raw_data.parquet')
with pd.option_context('display.max_columns', None):
    print(df)
