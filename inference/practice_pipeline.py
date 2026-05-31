"""
This is just scaffolding to help us build the project.
It is used to simulate certain parts of run_pipeline.py
Things will be commented out
"""
import os
import time
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from pathlib import Path

from data.universe import companies
from fetch_data import update_raw_data
from gen_features import generate_features
from normalize import normalize_data
from forecast import generate_forecasts

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest

# --- Config ---
load_dotenv()
API_KEY = os.getenv("KEY")
API_SECRET = os.getenv("SECRET")
PAPER = False

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
ARCHIVE_DIR  = DATA_DIR / "forecast_archive"
FORECASTS    = DATA_DIR / "forecasts.parquet"

ET = ZoneInfo("America/New_York")
normal_open = "09:30"      # skip the day unless hours are exactly these (excludes half days)
normal_close = "16:00"
phase1_minutes = 90 # phase 1 runs this long after the open. How many minutes of data for inference?
wind_down_minutes = 60     # phase 2 stops this long before the close. How far out are the forecasts made for?
interval = timedelta(minutes=3)
poll = 30                  # max seconds to sleep at once (accurate across suspend/clock changes)


def main():
    #archive_and_clean()
    client = TradingClient(API_KEY, API_SECRET, paper=PAPER)

    # hours = todays_hours(client)
    # if hours is None:
    #     print("Market closed today — exiting.")
    #     return
    # market_open, market_close = hours
    #
    # if (market_open.strftime("%H:%M"), market_close.strftime("%H:%M")) != (normal_open, normal_close):
    #     print(f"Abnormal hours today ({market_open:%H:%M}–{market_close:%H:%M} ET) — exiting.")
    #     return
    #
    # print(f"Open {market_open:%H:%M}, close {market_close:%H:%M} ET. Waiting for open…")
    # sleep_until(market_open)
    # print("The Market has maybe opened!")




    # #Do nothing but collect raw data for a while...
    # print("Now collecting raw data...")
    # end = market_open + timedelta(minutes=phase1_minutes)
    # while datetime.now(ET) < end:
    #     start = datetime.now(ET)
    #     update_raw_data(companies)
    #     print("Raw data updated.")
    #     sleep_until(min(start + interval, end))



    #continue to collect raw data, but now process it and generate forecasts also
    print("Now generating forecasts!")
    #end = market_close - timedelta(minutes=wind_down_minutes)
    #while datetime.now(ET) < end:
    while True:
        start = datetime.now(ET)
        #update_raw_data(companies)
        generate_features()
        #normalize_data()
        #generate_forecasts()
        #sleep_until((start + interval))
    print("Done generating forecasts for today!")


def todays_hours(client):
    """Return (open, close) as tz-aware datetimes, or None if the market is closed today."""
    today = datetime.now(ET).date()
    cal = client.get_calendar(GetCalendarRequest(start=today, end=today))
    if not cal or cal[0].date != today:
        return None
    day = cal[0]
    return (datetime.combine(today, day.open, ET), datetime.combine(today, day.close, ET))


def sleep_until(target):
    """Block until an absolute tz-aware time, polling so we never oversleep."""
    while (remaining := (target - datetime.now(ET)).total_seconds()) > 0:
        print(f"Now sleeping for {min(remaining, poll)} seconds.")
        time.sleep(min(remaining, poll))


def archive_and_clean():
    """Archive forecasts.parquet (if it exists) and delete all remaining parquets in data/."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if FORECASTS.exists():
        today_str = date.today().strftime("%Y-%m-%d")
        dest = ARCHIVE_DIR / f"forecasts_{today_str}.parquet"
        FORECASTS.rename(dest)
        print(f"Archived: forecasts.parquet → {dest.name}")
    else:
        print("No forecasts.parquet found to archive — skipping.")

    stale = list(DATA_DIR.glob("*.parquet"))
    if stale:
        for f in stale:
            f.unlink()
            print(f"Deleted stale parquet: {f.name}")
    else:
        print("No stale parquet files to clean up.")



if __name__ == "__main__":
    main()