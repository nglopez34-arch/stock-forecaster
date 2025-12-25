import pandas as pd
df = pd.read_parquet('raw_data.parquet')
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)  # Set a wider total line width
pd.set_option("display.max_columns", None)

print(df)