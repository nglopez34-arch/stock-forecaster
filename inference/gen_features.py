"""
Generate engineered features from raw data. This is essentially preprocessing step 1.
Winsorize and interpolate at this step also.
"""
import pandas as pd
import numpy as np
import os
from multiprocessing import Pool, cpu_count
import time
from pathlib import Path




def generate_features():
    raw_data_df = pd.read_parquet("raw_data.parquet")

    #figure out what minutes we will process
    #syntax may need to be changed depending on whether the timestamp is a column or an index
    oldest_raw_timestamp = raw_data_df["timestamp"].min()
    newest_raw_timestamp = raw_data_df["timestamp"].max()

    featured_data_filepath = Path("data_w_features.parquet")

    #if data_w_features doesn't exist, start at the beginning
    if not featured_data_filepath.exists():
        oldest_ts_to_process = oldest_raw_timestamp
        newest_ts_to_process = newest_raw_timestamp
        data_w_features_df = pd.DataFrame()

    #if data_w_features already exists
    else:
        data_w_features_df = pd.read_parquet("data_w_features.parquet")
        oldest_ts_to_process = data_w_features_df["timestamp"].max()
        newest_ts_to_process = newest_raw_timestamp

    #now we know that we must generate features between oldest_ts and newest_ts so that the two parquets have the same time stamps
