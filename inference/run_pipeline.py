"""
Orchestrates the data pipeline.
Starts right before trading, and simply collects raw data until a sufficent amount has been collected. (120 min?)
Once a sufficient amount has been collected, runs through the rest of the pipeline.
"""

import time
from datetime import datetime, timezone
from data.universe import companies
from fetch_data import update_raw_data
from gen_features import generate_features
from zoneinfo import ZoneInfo

import requests
import sys

API_KEY = "your_key"
API_SECRET = "your_secret"

# --- Market open check ---
clock = requests.get(
    "https://api.alpaca.markets/v1/clock",
    headers={"APCA-API-KEY-ID": API_KEY, "APCA-API-SECRET-KEY": API_SECRET}
).json()

if not clock["is_open"]:
    print(f"Market is closed today. Next open: {clock['next_open']}")
    sys.exit(0)

# --- Rest of your script ---