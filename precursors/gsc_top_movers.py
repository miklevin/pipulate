#!/usr/bin/env python
# coding: utf-8

"""
Finds the most recent date for which Google Search Console (GSC) data
is available for a specified site using a service account.

Required pip installs:
    pip install google-api-python-client google-auth
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
# IMPORTANT: Make sure the service account has access to this property!
SITE_URL = "sc-domain:mikelev.in"

# Path to your service account key JSON file
# Assumes the key file is in the same directory as the script. Adjust if needed.
SERVICE_ACCOUNT_KEY_FILE = os.path.join(os.path.dirname(__file__), 'service-account-key.json')

# Required Google API scopes
SCOPES = ['https://www.googleapis.com/auth/webmasters']

# GSC data typically has a delay. Start checking this many days before today.
START_OFFSET_DAYS = 2

# Maximum number of past days to check before giving up
MAX_DAYS_TO_CHECK = 10

# Delay between API checks (in seconds) to respect rate limits
API_CHECK_DELAY = 0.5

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
    """
    Checks if GSC has any performance data for the given site and date.

    Args:
        service: The authenticated GSC API service object.
        site_url (str): The GSC property URL.
        check_date (date): The date to check for data.

    Returns:
        bool: True if data exists for the date, False otherwise.
    """
    date_str = check_date.strftime('%Y-%m-%d')
    # Create a minimal query request for the specific date
    request_body = {
        'startDate': date_str,
        'endDate': date_str,
        'dimensions': ['query'],  # Using a minimal dimension
        'rowLimit': 1             # We only need 1 row to confirm data exists
    }

    try:
        # Execute the query via the searchanalytics endpoint
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request_body
        ).execute()

        # Check if the 'rows' key exists and contains any data
        return bool(response.get('rows'))  # More concise check

    except HttpError as e:
        # Handle common API errors gracefully
        print(f"\nAPI Error querying for date {date_str}: {e.resp.status} {e.resp.reason}")
        if e.resp.status == 403:
            print("   (This could be a permission issue or rate limiting.)")
        elif e.resp.status == 429:
            print("   (Rate limit exceeded. Consider increasing API_CHECK_DELAY.)")
        # Continue checking previous days despite error on this date
        return False
    except Exception as e:
        # Catch other potential exceptions
        print(f"\nUnexpected error querying for date {date_str}: {e}")
        return False


def find_most_recent_gsc_data_date(service, site_url):
    """
    Iterates backward from recent dates to find the latest date with GSC data.

    Args:
        service: The authenticated GSC API service object.
        site_url (str): The GSC property URL to check.

    Returns:
        date or None: The most recent date with data, or None if not found within limit.
    """
    most_recent_data_date = None
    days_checked = 0
    current_date = datetime.now().date() - timedelta(days=START_OFFSET_DAYS)

    print(f"\nFinding most recent data for site: {site_url}")
    print(f"Starting check from date: {current_date}")

    while days_checked < MAX_DAYS_TO_CHECK:
        print(f"Checking date {current_date}...", end=" ", flush=True)

        if check_date_has_data(service, site_url, current_date):
            print("✓ Data found!")
            most_recent_data_date = current_date
            break  # Exit loop once data is found
        else:
            print("✗ No data")
            current_date -= timedelta(days=1)
            days_checked += 1
            time.sleep(API_CHECK_DELAY)  # Pause before the next check

    return most_recent_data_date


def fetch_all_gsc_data(service, site_url, request_body):
    """
    Fetches all available data rows for a given GSC query, handling pagination.

    Args:
        service: The authenticated GSC API service object.
        site_url (str): The GSC property URL.
        request_body (dict): The initial query request body. Must include
                             'rowLimit' and 'startRow'.

    Returns:
        list: A list containing all the row data dictionaries fetched from GSC.
              Returns an empty list if an error occurs or no data is found.
    """
    all_rows = []
    start_row = request_body.get('startRow', 0)
    row_limit = request_body.get('rowLimit', 1000)  # Default GSC limit if not specified
    page_count = 0

    print(f"\nFetching data with dimensions: {request_body.get('dimensions', [])}")

    while True:
        page_count += 1
        request_body['startRow'] = start_row
        print(f"Fetching page {page_count} (starting row {start_row})...", end=" ", flush=True)

        try:
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()

            current_rows = response.get('rows', [])

            if not current_rows:
                if page_count == 1:
                    print("No data found for this query.")
                else:
                    print("✓ No more data.")
                break  # Exit loop if no rows are returned

            print(f"✓ Retrieved {len(current_rows)} rows.")
            all_rows.extend(current_rows)

            # GSC API max rowLimit is 25000, but let's use the requested rowLimit
            # If fewer rows than the limit are returned, it's the last page
            if len(current_rows) < row_limit:
                print("✓ Reached last page of results.")
                break  # Exit loop if last page is fetched

            start_row += len(current_rows)
            time.sleep(API_CHECK_DELAY)  # Be nice to the API between pages

        except HttpError as e:
            print(f"\nAPI Error during data fetch (page {page_count}): {e.resp.status} {e.resp.reason}")
            if e.resp.status in [403, 429]:
                print("   (Consider permissions, quotas, or increasing API_CHECK_DELAY.)")
            print("   Aborting data fetch for this request.")
            return []  # Return empty list on error
        except Exception as e:
            print(f"\nUnexpected error during data fetch (page {page_count}): {e}")
            print("   Aborting data fetch for this request.")
            return []  # Return empty list on error

    print(f"✓ Finished fetching. Total rows retrieved: {len(all_rows)}")
    return all_rows


def process_gsc_data_to_dataframe(gsc_data_list):
    """
    Converts the raw list of GSC data rows into a processed Pandas DataFrame.

    Args:
        gsc_data_list (list): A list of row data dictionaries from fetch_all_gsc_data.

    Returns:
        pandas.DataFrame: A DataFrame with processed GSC data, including separate
                          'query' and 'page' columns, and numeric metrics.
                          Returns an empty DataFrame if input is empty or invalid.
    """
    if not gsc_data_list:
        print("No data to process into DataFrame.")
        return pd.DataFrame()

    df = pd.DataFrame(gsc_data_list)

    # Split the 'keys' column (list) into separate dimension columns
    if 'keys' in df.columns and not df['keys'].empty:
        # Assuming dimensions are ['query', 'page'] as requested
        try:
            df['query'] = df['keys'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
            df['page'] = df['keys'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)
            df = df.drop('keys', axis=1)
            print("✓ Split 'keys' into 'query' and 'page' columns.")
        except Exception as e:
            print(f"Warning: Could not split 'keys' column reliably: {e}")
            # Keep the 'keys' column if splitting fails
            if 'query' in df.columns:
                df = df.drop('query', axis=1)
            if 'page' in df.columns:
                df = df.drop('page', axis=1)

    # Ensure standard metric columns exist and convert to numeric types
    metric_cols = ['clicks', 'impressions', 'ctr', 'position']
    for col in metric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')  # Coerce errors to NaN
            # Optional: Fill NaNs created by coercion if needed, e.g., df[col] = df[col].fillna(0)
        else:
            # Add the column with default value if missing (optional)
            # df[col] = 0
            print(f"Note: Metric column '{col}' not found in raw data.")

    # Optional: Convert CTR to percentage for display
    if 'ctr' in df.columns:
        df['ctr'] = df['ctr'] * 100
        print("✓ Converted 'ctr' to percentage.")

    print(f"✓ Processed data into DataFrame with {len(df)} rows and {len(df.columns)} columns.")
    return df


def main():
    """Main execution function."""
    # 1. Authenticate and get the GSC service object
    gsc_service = authenticate_gsc()

    # 2. Find the most recent date with data
    latest_date = find_most_recent_gsc_data_date(gsc_service, SITE_URL)

    # --- ADD THE FOLLOWING ---
    # 3. If a date was found, fetch and process the data for that day
    if latest_date:
        print(f"\nAttempting to download data for the most recent date: {latest_date.strftime('%Y-%m-%d')}")

        # Define the request for that single day
        single_day_request = {
            'startDate': latest_date.strftime('%Y-%m-%d'),
            'endDate': latest_date.strftime('%Y-%m-%d'),
            'dimensions': ['query', 'page'],
            'rowLimit': 25000,  # Use max row limit per page fetch
            'startRow': 0
        }

        # Fetch data using the pagination function
        raw_gsc_data = fetch_all_gsc_data(gsc_service, SITE_URL, single_day_request)

        # Process the raw data into a DataFrame
        df_gsc_data = process_gsc_data_to_dataframe(raw_gsc_data)

        # Display results if DataFrame is not empty
        if not df_gsc_data.empty:
            print("\n--- GSC Data DataFrame Preview (first 10 rows) ---")
            # Set display options for better preview
            pd.set_option('display.max_rows', 20)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 100)
            pd.set_option('display.max_colwidth', 50)
            print(df_gsc_data.head(10))

            print("\n--- DataFrame Info ---")
            df_gsc_data.info()

            print("\n--- Basic Stats ---")
            # Use describe() for numeric columns, handle potential missing columns
            numeric_cols = df_gsc_data.select_dtypes(include=['number']).columns
            if not numeric_cols.empty:
                print(df_gsc_data[numeric_cols].describe())
            else:
                print("No numeric columns found for describe().")

            # Example of accessing specific data
            # print(f"\nTotal Clicks: {df_gsc_data['clicks'].sum()}")
            # print(f"Total Impressions: {df_gsc_data['impressions'].sum()}")

        else:
            print("\nNo data was processed into the DataFrame.")
    # --- END OF ADDED SECTION ---
    else:
        # This part was already there: handle case where no date was found
        last_checked_date = datetime.now().date() - timedelta(days=START_OFFSET_DAYS + MAX_DAYS_TO_CHECK - 1)
        print(f"\nWarning: Could not find GSC data within the last {MAX_DAYS_TO_CHECK} checked days")
        print(f"         (Checked back to {last_checked_date.strftime('%Y-%m-%d')}).")
        print("         Cannot proceed with data download.")
        # Removed the previous permission/interface check message as it's less relevant here


# --- Ensure the final block still calls main() ---
if __name__ == "__main__":
    # Ensure SITE_URL is set (this check can be simplified or enhanced)
    if not SITE_URL or SITE_URL == "sc-domain:yourdomain.com":  # Added check for default placeholder
        print("Error: Please update the 'SITE_URL' variable in the script configuration.")
        sys.exit(1)
    main()
