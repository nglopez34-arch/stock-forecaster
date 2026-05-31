"""
Generate engineered features from raw data. This is essentially preprocessing step 1.
Each symbol is reindexed onto a complete 1-minute grid (every clock minute between its
first and last bar). Missing minutes are filled on the RAW series BEFORE features are
computed (price forward-filled, volume zero-filled), so the fill never peeks at future
bars. Features are then computed from the filled series.

Reads:  data/raw_data.parquet         (raw minute-bar OHLCV; one row per symbol + timestamp)
Writes: data/data_w_features.parquet  (symbol, timestamp, log_returns, ln_volume)

Run directly (e.g. from PyCharm) -- no CLI arguments needed.
"""
#TODO
# Add all of the other engineered features
# Also, you need to figure out how you are going to structure this thing.
# Some engineered features may need 60 minutes PRIOR TO THE MINUTE AT HAND.
# This means that you may need to add 60 minutes to the beginning! What are you going to do?
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count

import numpy as np
import pandas as pd

# --- Paths ---
PROJECT_ROOT  = Path(__file__).parent.parent
DATA_DIR      = PROJECT_ROOT / "data"
RAW_DATA      = DATA_DIR / "raw_data.parquet"
FEATURED_DATA = DATA_DIR / "data_w_features.parquet"

# --- Column names in raw_data.parquet ---
SYMBOL_COL    = "symbol"
TIMESTAMP_COL = "timestamp"
CLOSE_COL     = "close"      # price used for returns: r_t = ln(P_t) - ln(P_{t-1})
VOLUME_COL    = "volume"

# --- Compute config ---
N_PROCESSES   = max(1, cpu_count() - 1)   # leave one core free


# this script takes information from raw_data.parquet and uses it to create data_w_features.parquet
def _process_symbol(symbol_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features for a single symbol. Runs inside a worker process, so it must
    be a top-level (picklable) function. Expects rows for exactly one symbol.
    """
    df = symbol_df.sort_values(TIMESTAMP_COL).set_index(TIMESTAMP_COL)
    symbol = symbol_df[SYMBOL_COL].iloc[0]

    # guard against any accidental duplicate minutes (one bar per minute)
    df = df[~df.index.duplicated(keep="last")]

    # reindex onto a complete 1-minute grid so EVERY clock minute between the
    # symbol's first and last bar exists; missing minutes start out as NaN rows.
    full_index = pd.date_range(df.index.min(), df.index.max(), freq="1min")
    df = df.reindex(full_index)

    # --- fill the RAW series BEFORE computing any features ---
    # Price: forward-fill (last trade price). A no-trade minute didn't move, and
    # ffill uses only PAST bars -> no look-ahead (unlike linear interpolation,
    # which would pull in the post-gap price). It also keeps any future OHLC bars
    # internally consistent, since a filled bar is a verbatim copy of a real one.
    close = df[CLOSE_COL].ffill().to_numpy(dtype=float)
    # Volume: a no-trade minute genuinely transacted 0 shares.
    volume = df[VOLUME_COL].fillna(0.0).to_numpy(dtype=float)

    # --- engineered features, computed "by hand" from the filled series ---
    # log returns: r_t = ln(P_t) - ln(P_{t-1})  (0 across forward-filled minutes)
    safe_close = np.where(close > 0.0, close, np.nan)   # guard so ln() never blows up
    log_price  = np.log(safe_close)
    log_returns = np.full(log_price.shape, np.nan)      # first bar has no prior -> NaN
    log_returns[1:] = log_price[1:] - log_price[:-1]

    # ln(volume): use log1p so a 0-volume (no-trade) minute maps cleanly to 0
    # rather than -inf. For any real volume this is numerically identical to ln(volume).
    ln_volume = np.log1p(np.where(volume >= 0.0, volume, 0.0))

    out = pd.DataFrame({
        SYMBOL_COL:    symbol,
        TIMESTAMP_COL: full_index,
        "log_returns": log_returns,
        "ln_volume":   ln_volume,
    })

    return out


def generate_features():
    raw_data_df = pd.read_parquet(RAW_DATA)

    # figure out what minutes we will process
    # (timestamp is a column here; if it ever becomes the index, use raw_data_df.index instead)
    oldest_raw_timestamp = raw_data_df[TIMESTAMP_COL].min()
    newest_raw_timestamp = raw_data_df[TIMESTAMP_COL].max()

    # if data_w_features doesn't exist, start at the beginning
    if not FEATURED_DATA.exists():
        existing_df          = pd.DataFrame()
        oldest_ts_to_process = oldest_raw_timestamp
    # if data_w_features already exists, only (re)process the new tail
    else:
        existing_df          = pd.read_parquet(FEATURED_DATA)
        oldest_ts_to_process = existing_df[TIMESTAMP_COL].max()

    newest_ts_to_process = newest_raw_timestamp

    # nothing new to do -> leave the file as-is
    if existing_df.shape[0] and oldest_ts_to_process >= newest_ts_to_process:
        print(f"Already up to date (latest featured timestamp: {oldest_ts_to_process}).")
        return existing_df

    # now we know we must generate features between oldest_ts and newest_ts so the two parquets line up.
    # For the append case we deliberately KEEP the bar at oldest_ts_to_process because we need its
    # close as P_{t-1} for the first new return; those boundary rows get dropped before the concat.
    mask = (raw_data_df[TIMESTAMP_COL] >= oldest_ts_to_process) & \
           (raw_data_df[TIMESTAMP_COL] <= newest_ts_to_process)
    slice_df = raw_data_df.loc[mask]

    # split into one dataframe per symbol and build features in parallel
    symbol_groups = [g for _, g in slice_df.groupby(SYMBOL_COL, sort=False)]

    t0 = time.time()
    if N_PROCESSES > 1 and len(symbol_groups) > 1:
        with Pool(processes=N_PROCESSES) as pool:
            results = pool.map(_process_symbol, symbol_groups)
    else:
        results = [_process_symbol(g) for g in symbol_groups]
    new_features_df = pd.concat(results, ignore_index=True)
    print(f"Built features for {len(symbol_groups)} symbol(s) in {time.time() - t0:.1f}s")

    # either create a fresh df or append the missing minutes onto the existing one
    if existing_df.shape[0]:
        # drop the boundary rows we only kept to seed P_{t-1}
        new_features_df = new_features_df[new_features_df[TIMESTAMP_COL] > oldest_ts_to_process]
        data_w_features_df = pd.concat([existing_df, new_features_df], ignore_index=True)
    else:
        data_w_features_df = new_features_df

    data_w_features_df = (
        data_w_features_df
        .sort_values([SYMBOL_COL, TIMESTAMP_COL])
        .reset_index(drop=True)
    )

    # save the data_w_features.parquet when done
    data_w_features_df.to_parquet(FEATURED_DATA, index=False)
    print(f"Wrote {len(data_w_features_df):,} rows to {FEATURED_DATA}")
    return data_w_features_df


if __name__ == "__main__":
    generate_features()