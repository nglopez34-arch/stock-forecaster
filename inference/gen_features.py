"""
Generate engineered features from raw data. This is essentially preprocessing step 1.
Winsorize and interpolate at this step also.
"""
import pandas as pd
import numpy as np
import os
from multiprocessing import Pool, cpu_count
import time

def generate_features():
    pass

"""
Read raw_data.parquet and figure out what the oldest and newest time stamps are
read data_w_features.parquet and figure out what the oldest and newest time stamps are
generate data with features according to the gaps, thereby making it so that data_w_features.parquet is the same
"""
