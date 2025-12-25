'''
Fetches minute-level raw OHLCV data + trade count and VWAP from Alpaca. Stores it in "unprocessed_data.parquet"
'''







'''
Checks to see if there exists raw_data.parquet
if it does exist:
    Download all data that exists since the latest timestamp
    Truncate raw_data.parquet so that it is the proper length
if it doesn't exist:
    Download data to create raw_data.parquet
    
Every minute, fetch the latest bars for all stocks in universe
'''




# !/usr/bin/env python3

import os
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from universe import companies

SYMBOLS = [company[0] for company in companies]
#todo: remove
SYMBOLS = ["NVDA"]
DAYS_OF_HISTORY = 2  # How long the parquet file will be
print(companies)
print(SYMBOLS)
if os.path.exists("raw_data.parquet"):
    print("File exists!")
else:
    print("File does not exist.")
END_DATE = datetime.now()  # End date (default: now)
START_DATE = END_DATE - timedelta(days=DAYS_OF_HISTORY)

# Data granularity
TIMEFRAME = TimeFrame.Minute  # Options: Minute, Hour, Day, Week, Month

# Output settings

output_path = 'raw_data.parquet'


# API settings (will be loaded from .env)
# Required in .env: KEY, SECRET

# ==================== END CONFIGURATION ====================


def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('KEY')
    secret_key = os.getenv('SECRET')

    if not api_key or not secret_key:
        raise ValueError("KEY and SECRET must be set in .env file")

    # Initialize Alpaca client
    client = StockHistoricalDataClient(api_key, secret_key)

    print(f"Fetching {DAYS_OF_HISTORY} days of {TIMEFRAME} data for {len(SYMBOLS)} symbols")
    print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")

    # Create request
    request = StockBarsRequest(
        symbol_or_symbols=SYMBOLS,
        timeframe=TIMEFRAME,
        start=START_DATE,
        end=END_DATE
    )

    # Fetch data
    print("\nFetching data from Alpaca...")
    bars = client.get_stock_bars(request)

    # Convert to DataFrame
    print("Converting to DataFrame...")
    df = bars.df

    if df.empty:
        print("No data returned from API")
        return

    # Reset index to make symbol and timestamp columns
    df = df.reset_index()

    print(f"\nFetched {len(df)} total bars")
    print(f"Symbols: {df['symbol'].unique().tolist()}")
    print(f"\nData shape: {df.shape}")
    print(f"Date range in data: {df['timestamp'].min()} to {df['timestamp'].max()}")


    # Save to parquet
    print(f"\nSaving to {output_path}...")
    df.to_parquet(output_path, index=False, compression='snappy')

    # Show sample data
    print("\nSample data:")
    print(df.head())

    print(f"\n✓ Complete! Data saved to {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")


if __name__ == '__main__':
    main()