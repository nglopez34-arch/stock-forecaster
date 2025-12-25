'''
Fetches minute-level raw OHLCV data + trade count and VWAP from Alpaca. Stores it in "unprocessed_data.parquet"
'''

# !/usr/bin/env python3

import os
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# ==================== CONFIGURATION ====================
# Adjust all parameters here

# Symbols to fetch
SYMBOLS = ['NVDA','BEN']

# Date range
DAYS_OF_HISTORY = 30  # How many days back to fetch
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