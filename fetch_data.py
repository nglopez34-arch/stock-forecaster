"""
Fetches minute-level raw OHLCV data + trade count and VWAP from Alpaca. Stores it in "raw_data.parquet"
"""
#todo:
# Make it so that there is only data from when the market is open (not just hours, but also holidays)
# Remove symbols from universe that have too many holes in data

# !/usr/bin/env python3

import os
from datetime import datetime, timedelta, timezone
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from universe import companies
from tqdm import tqdm
import time


def fetch_symbol_data(client, symbol, start_date, end_date):
    """Fetch data for a single symbol with error handling"""
    try:
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start_date,
            end=end_date
        )
        bars = client.get_stock_bars(request)
        if bars.df.empty:
            return pd.DataFrame()

        df = bars.df.reset_index()
        return df
    except Exception as e:
        print(f"\nError fetching {symbol}: {e}")
        return pd.DataFrame()


def clean_dataframe(df):
    """Remove duplicates and sort the dataframe"""
    if df.empty:
        return df

    # Remove duplicate (symbol, timestamp) pairs, keeping the last occurrence
    df = df.drop_duplicates(subset=['symbol', 'timestamp'], keep='last')

    # Sort by symbol and timestamp for clean organization
    df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)

    return df


def main():
    symbols = [company[0] for company in companies]
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('KEY')
    secret_key = os.getenv('SECRET')

    if not api_key or not secret_key:
        raise ValueError("KEY and SECRET must be set in .env file")

    # Initialize Alpaca client
    client = StockHistoricalDataClient(api_key, secret_key)
    years_of_history = 0.5  # How long the parquet file will be

    if os.path.exists("raw_data.parquet"):
        print("Loading existing raw_data.parquet...")
        df = pd.read_parquet("raw_data.parquet")
        newest_ts = df['timestamp'].max()
        oldest_ts = df['timestamp'].min()

        # Fetch new data for each symbol
        new_data_list = []
        for symbol in tqdm(symbols, desc="Fetching symbols"):
            symbol_df = fetch_symbol_data(
                client,
                symbol,
                start_date=newest_ts,
                end_date=datetime.now(timezone.utc) - timedelta(minutes=15)
            )
            if not symbol_df.empty:
                # Filter out data that's not actually newer
                symbol_df = symbol_df[symbol_df['timestamp'] > newest_ts]
                if not symbol_df.empty:
                    new_data_list.append(symbol_df)
            time.sleep(1)

        # Combine new data
        if new_data_list:
            new_df = pd.concat(new_data_list, ignore_index=True)
            print(f"\nFetched {len(new_df)} new rows")

            # Combine with existing data
            df = pd.concat([df, new_df], ignore_index=True)
        else:
            print("\nNo new data to add")

        # Clean the dataframe (remove duplicates, sort)
        df = clean_dataframe(df)

        # Truncate old data
        newest_ts = df['timestamp'].max()
        rows_before_truncation = len(df)

        if oldest_ts < newest_ts - timedelta(days=years_of_history * 365):
            cutoff = newest_ts - timedelta(days=years_of_history * 365)
            cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
            df = df[df['timestamp'] >= cutoff]
            rows_after_truncation = len(df)
            print(f"Removed {rows_before_truncation - rows_after_truncation} old rows")

        # Save the cleaned data
        df.to_parquet("raw_data.parquet", index=False)
        print(f"\nFile contains data from {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Total rows: {len(df)}")
        print(f"Unique symbols: {df['symbol'].nunique()}")

    else:
        print("Raw data file does not exist. Creating new file...")
        start_date = datetime.now(timezone.utc)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date -= timedelta(days=years_of_history * 365)
        end_date = datetime.now(timezone.utc) - timedelta(minutes=15)

        print(f"\nFetching data from {start_date} to {end_date}...")

        # Fetch data for each symbol
        data_list = []
        for symbol in tqdm(symbols, desc="Fetching symbols"):
            symbol_df = fetch_symbol_data(client, symbol, start_date, end_date)
            if not symbol_df.empty:
                data_list.append(symbol_df)
            time.sleep(1)

        # Combine all data
        if data_list:
            df = pd.concat(data_list, ignore_index=True)

            # Clean the dataframe (remove duplicates, sort)
            df = clean_dataframe(df)

            # Save to parquet
            df.to_parquet("raw_data.parquet", index=False)
            print(f"\nCreated raw_data.parquet with {len(df)} rows")
            print(f"Data from {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"Unique symbols: {df['symbol'].nunique()}")
        else:
            print("\nNo data was fetched!")


if __name__ == '__main__':
    main()