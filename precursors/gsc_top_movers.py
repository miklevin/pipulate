#!/usr/bin/env python
# coding: utf-8

"""
Fetches Google Search Console (GSC) data for the 4 most recent days available
for a specified site using a service account. Saves each day to a CSV file.

Required pip installs:
    pip install google-api-python-client google-auth pandas
"""

import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---

# Set your GSC Property URL here (e.g., "sc-domain:example.com" or "https://www.example.com/")
SITE_URL = "sc-domain:mikelev.in"

# Path to your service account key JSON file
# Assumes the key file is in the same directory as the script. Adjust if needed.
SCRIPT_DIR = os.path.dirname(__file__)
SERVICE_ACCOUNT_KEY_FILE = os.path.join(SCRIPT_DIR, 'service-account-key.json')

# Required Google API scopes
SCOPES = ['https://www.googleapis.com/auth/webmasters']

# GSC data typically has a delay. Start checking this many days before today.
START_OFFSET_DAYS = 2

# Maximum number of past days to check before giving up
MAX_DAYS_TO_CHECK = 10

# Delay between API checks (in seconds) to respect rate limits
API_CHECK_DELAY = 0.5

# Number of consecutive days of data to fetch (ending on the most recent date)
NUM_DAYS_TO_FETCH = 4

# Directory to store/load cached daily GSC data CSV files
CACHE_DIR = os.path.join(SCRIPT_DIR, 'gsc_cache')

# --- End Configuration ---


def authenticate_gsc():
    """Authenticates with Google API using service account credentials."""
    if not os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
        print(f"Error: Service account key file not found at: {SERVICE_ACCOUNT_KEY_FILE}")
        print("Please ensure the file exists and the path is correct.")
        sys.exit(1)

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES)
        webmasters_service = build('webmasters', 'v3', credentials=credentials)
        print("✓ Successfully authenticated with Google Search Console API.")
        return webmasters_service
    except Exception as e:
        print(f"Error during GSC authentication: {e}")
        sys.exit(1)


def check_date_has_data(service, site_url, check_date):
    """Checks if GSC has any performance data for the given site and date."""
    date_str = check_date.strftime('%Y-%m-%d')
    request_body = {
        'startDate': date_str, 'endDate': date_str,
        'dimensions': ['query'], 'rowLimit': 1
    }
    try:
        response = service.searchanalytics().query(
            siteUrl=site_url, body=request_body).execute()
        return bool(response.get('rows'))
    except HttpError as e:
        print(f"\nAPI Error checking date {date_str}: {e.resp.status} {e.resp.reason}")
        return False
    except Exception as e:
        print(f"\nUnexpected error checking date {date_str}: {e}")
        return False


def find_most_recent_gsc_data_date(service, site_url):
    """Iterates backward to find the latest date with GSC data."""
    most_recent_data_date = None
    days_checked = 0
    current_date = datetime.now().date() - timedelta(days=START_OFFSET_DAYS)
    print(f"\nFinding most recent data date for site: {site_url}")
    print(f"Starting check from date: {current_date}")
    while days_checked < MAX_DAYS_TO_CHECK:
        print(f"Checking date {current_date}...", end=" ", flush=True)
        if check_date_has_data(service, site_url, current_date):
            print("✓ Data found!")
            most_recent_data_date = current_date
            break
        else:
            print("✗ No data")
            current_date -= timedelta(days=1)
            days_checked += 1
            time.sleep(API_CHECK_DELAY)
    if not most_recent_data_date:
        last_checked_date = current_date + timedelta(days=1) # Date where check stopped
        print(f"\nWarning: Could not find data within {MAX_DAYS_TO_CHECK} checked days (back to {last_checked_date}).")
    return most_recent_data_date


def fetch_all_gsc_data(service, site_url, request_body):
    """Fetches all available data rows for a given GSC query, handling pagination."""
    all_rows = []
    start_row = request_body.get('startRow', 0)
    row_limit = request_body.get('rowLimit', 25000) # Use max GSC limit
    page_count = 0
    print(f"\nFetching data with dimensions: {request_body.get('dimensions', [])} for {request_body.get('startDate')}")
    while True:
        page_count += 1
        request_body['startRow'] = start_row
        print(f"Fetching page {page_count} (starting row {start_row})...", end=" ", flush=True)
        try:
            response = service.searchanalytics().query(
                siteUrl=site_url, body=request_body).execute()
            current_rows = response.get('rows', [])
            if not current_rows:
                if page_count == 1: print("No data found for this query.")
                else: print("✓ No more data.")
                break
            print(f"✓ Retrieved {len(current_rows)} rows.")
            all_rows.extend(current_rows)
            if len(current_rows) < row_limit:
                print("✓ Reached last page of results.")
                break
            start_row += len(current_rows)
            time.sleep(API_CHECK_DELAY)
        except HttpError as e:
            print(f"\nAPI Error fetching page {page_count}: {e.resp.status} {e.resp.reason}")
            return [] # Return empty list on error
        except Exception as e:
            print(f"\nUnexpected error fetching page {page_count}: {e}")
            return []
    print(f"✓ Finished fetching {request_body.get('startDate')}. Total rows: {len(all_rows)}")
    return all_rows


def process_gsc_data_to_dataframe(gsc_data_list, data_date):
    """Converts raw GSC data list into a processed Pandas DataFrame."""
    if not gsc_data_list:
        print(f"No data to process into DataFrame for {data_date}.")
        return pd.DataFrame()
    df = pd.DataFrame(gsc_data_list)
    if 'keys' in df.columns and not df['keys'].empty:
        try:
            df['query'] = df['keys'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
            df['page'] = df['keys'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)
            df = df.drop('keys', axis=1)
        except Exception as e:
            print(f"Warning: Could not split 'keys' column for {data_date}: {e}")
    metric_cols = ['clicks', 'impressions', 'ctr', 'position']
    for col in metric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            print(f"Note: Metric column '{col}' not found for {data_date}.")
    if 'ctr' in df.columns: df['ctr'] = df['ctr'] * 100
    print(f"✓ Processed data for {data_date} into DataFrame ({len(df)} rows).")
    return df


def get_gsc_data_for_day(service, site_url, data_date):
    """
    Fetches GSC data for a specific day, using cache if available.

    Args:
        service: Authenticated GSC service object.
        site_url (str): Target GSC property URL.
        data_date (date): The specific date to fetch data for.

    Returns:
        pandas.DataFrame: DataFrame containing data for the specified date.
                          Returns an empty DataFrame if fetching fails or no data.
    """
    date_str = data_date.strftime('%Y-%m-%d')
    cache_filename = os.path.join(CACHE_DIR, f"gsc_data_{date_str}.csv")

    # Check cache first
    if os.path.exists(cache_filename):
        try:
            print(f"✓ Loading data for {date_str} from cache: {cache_filename}")
            # Specify dtypes to avoid warnings and ensure consistency
            df = pd.read_csv(cache_filename, dtype={
                'clicks': 'Int64', # Use nullable integer type
                'impressions': 'Int64',
                'ctr': 'float64',
                'position': 'float64',
                'query': 'object',
                'page': 'object'
            }, parse_dates=False) # Dates handled separately
            # Ensure CTR is percentage if loaded from CSV
            if 'ctr' in df.columns and df['ctr'].max() <= 1.0:
                 df['ctr'] = df['ctr'] * 100
            return df
        except Exception as e:
            print(f"Warning: Could not load cache file {cache_filename}. Error: {e}. Re-fetching.")

    # If not in cache or cache fails, fetch from API
    print(f"Fetching data for {date_str} from GSC API...")
    request = {
        'startDate': date_str, 'endDate': date_str,
        'dimensions': ['query', 'page'],
        'rowLimit': 25000, 'startRow': 0
    }
    raw_data = fetch_all_gsc_data(service, site_url, request)
    df = process_gsc_data_to_dataframe(raw_data, date_str)

    # Save to cache if data was fetched successfully and is not empty
    if not df.empty:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True) # Ensure cache directory exists
            df.to_csv(cache_filename, index=False)
            print(f"✓ Saved data for {date_str} to cache: {cache_filename}")
        except Exception as e:
            print(f"Warning: Could not save data for {date_str} to cache. Error: {e}")

    return df


def main():
    """Main execution function."""
    # 1. Authenticate and get the GSC service object
    gsc_service = authenticate_gsc()

    # 2. Find the most recent date with data
    latest_date = find_most_recent_gsc_data_date(gsc_service, SITE_URL)

    if not latest_date:
        print("\nCannot proceed without a valid recent date.")
        sys.exit(1)

    print(f"\nSuccess: Most recent GSC data available is for: {latest_date.strftime('%Y-%m-%d')}")

    # 3. Determine the date range (last NUM_DAYS_TO_FETCH days)
    dates_to_fetch = [latest_date - timedelta(days=i) for i in range(NUM_DAYS_TO_FETCH)][::-1] # Reverse to get oldest first
    print(f"\nPreparing to fetch/load data for {NUM_DAYS_TO_FETCH} days:")
    for d in dates_to_fetch:
        print(f"  - {d.strftime('%Y-%m-%d')}")

    # 4. Fetch/load data for each day into a dictionary of DataFrames
    daily_dataframes = {}
    all_data_fetched = True
    for target_date in dates_to_fetch:
        df_day = get_gsc_data_for_day(gsc_service, SITE_URL, target_date)
        if df_day.empty and not os.path.exists(os.path.join(CACHE_DIR, f"gsc_data_{target_date.strftime('%Y-%m-%d')}.csv")):
             # Check if the file exists even if df is empty, maybe it was an empty day
             print(f"Warning: Failed to fetch or load data for {target_date.strftime('%Y-%m-%d')}. Trend analysis might be incomplete.")
             all_data_fetched = False
        daily_dataframes[target_date] = df_day

    # 5. Confirmation and next steps preview
    if all_data_fetched:
        print(f"\n✓ Successfully fetched/loaded data for all {len(daily_dataframes)} target days.")
        # Optionally display info about one of the DataFrames
        if latest_date in daily_dataframes and not daily_dataframes[latest_date].empty:
            print(f"\n--- Preview of data for the latest date ({latest_date.strftime('%Y-%m-%d')}): ---")
            print(daily_dataframes[latest_date].head())
            print(f"(Total rows for {latest_date.strftime('%Y-%m-%d')}: {len(daily_dataframes[latest_date])})")
        print("\nDataFrames are stored in the 'daily_dataframes' dictionary, keyed by date.")
        print("Next step: Combine these DataFrames and perform trend analysis.")
    else:
        print("\nWarning: Data fetching/loading was incomplete for one or more days.")
        print("Proceeding with available data, but trend analysis might be affected.")
        # Still print available data info
        print(f"\nAvailable DataFrames ({len(daily_dataframes)}): {list(daily_dataframes.keys())}")

    # The script now ends here. The next logical step (trend analysis)
    # would follow, using the 'daily_dataframes' dictionary.


if __name__ == "__main__":
    if not SITE_URL or SITE_URL == "sc-domain:yourdomain.com":
        print("Error: Please update the 'SITE_URL' variable in the script configuration.")
        sys.exit(1)
    main()