"""
Fetches and appends the latest minute-level OHLCV data from Alpaca into raw_data.parquet.
No cleaning or processing — raw append only. File contains current trading day only.
"""
#TODO: make sure that there are no weird pre or post hours data. Like 8 am??

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from tqdm import tqdm

# ── Configuration ─────────────────────────────────────────────────────────────
PARQUET_PATH = "/home/graham/PycharmProjects/overnight/data/raw_data.parquet"
ALPACA_DELAY = 0.2
# ──────────────────────────────────────────────────────────────────────────────


def _get_client():
    load_dotenv()
    api_key = os.getenv("KEY")
    secret_key = os.getenv("SECRET")
    if not api_key or not secret_key:
        raise ValueError("KEY and SECRET must be set in .env file")
    return StockHistoricalDataClient(api_key, secret_key)


def _fetch_symbol(client, symbol, start, end):
    """Return a raw DataFrame for one symbol, or empty DataFrame on failure."""
    try:
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
        )
        bars = client.get_stock_bars(request)
        if bars.df.empty:
            return pd.DataFrame()
        return bars.df.reset_index()
    except Exception as e:
        print(f"  [fetcher] Error fetching {symbol}: {e}")
        return pd.DataFrame()


def update_raw_data(symbols):
    """
    Append the latest available Alpaca minute bars for every symbol in `symbols`
    to PARQUET_PATH. File contains current trading day only.
    No deduplication, no sorting, no truncation — raw append only.
    """
    client = _get_client()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.now(timezone.utc) - timedelta(minutes=15)

    # ── Seed run ──────────────────────────────────────────────────────────────
    if not os.path.exists(PARQUET_PATH):
        print("[fetcher] No parquet file found — seeding from today...")

        rows = []
        symbols = [company[0] for company in symbols]
        for symbol in tqdm(symbols, desc="[fetcher] Seeding"):
            df = _fetch_symbol(client, symbol, start=today_start, end=end)
            if not df.empty:
                rows.append(df)
            time.sleep(ALPACA_DELAY)

        if rows:
            pd.concat(rows, ignore_index=True).to_parquet(PARQUET_PATH, index=False)
            print(f"[fetcher] Seeded {PARQUET_PATH} with {sum(len(r) for r in rows)} rows.")
        else:
            print("[fetcher] No data returned — parquet file not created.")
        return

    # ── Incremental update ────────────────────────────────────────────────────
    existing = pd.read_parquet(PARQUET_PATH)

    # Drop any rows from previous days
    existing = existing[existing["timestamp"] >= today_start]

    if existing.empty:
        newest_ts = today_start
    else:
        newest_ts = existing["timestamp"].max()

    print(f"[fetcher] Existing data through {newest_ts}. Fetching newer bars...")

    rows = []
    for symbol in tqdm(symbols, desc="[fetcher] Updating"):
        df = _fetch_symbol(client, symbol, start=newest_ts, end=end)
        if not df.empty:
            new_rows = df[df["timestamp"] > newest_ts]
            if not new_rows.empty:
                rows.append(new_rows)
        time.sleep(ALPACA_DELAY)

    if rows:
        new_data = pd.concat(rows, ignore_index=True)
        updated = pd.concat([existing, new_data], ignore_index=True)
        updated.to_parquet(PARQUET_PATH, index=False)
        print(f"[fetcher] Appended {len(new_data)} new rows. Total: {len(updated)}.")
    else:
        print("[fetcher] No new data available.")