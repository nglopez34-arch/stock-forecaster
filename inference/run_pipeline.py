"""
Orchestrates the data pipeline.
Both this file and fetch_data.py live in:
  /home/graham/PycharmProjects/overnight/inference/
"""

import time
from datetime import datetime
from data.universe import companies
from fetch_data import update_raw_data

UPDATE_INTERVAL_SECONDS = 120

def run_once():
    print(f"\n[orchestrator] Update triggered at {datetime.now().strftime('%H:%M:%S')}")
    update_raw_data(companies)


def run_loop():
    print(f"[orchestrator] Starting live update loop (every {UPDATE_INTERVAL_SECONDS}s).")
    while True:
        run_once()
        print(f"[orchestrator] Sleeping {UPDATE_INTERVAL_SECONDS}s...")
        time.sleep(UPDATE_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_once()