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
        return bool(response.get('rows')) # More concise check

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
            time.sleep(API_CHECK_DELAY) # Pause before the next check

    return most_recent_data_date


def main():
    """Main execution function."""
    # 1. Authenticate and get the GSC service object
    gsc_service = authenticate_gsc()

    # 2. Find the most recent date with data
    latest_date = find_most_recent_gsc_data_date(gsc_service, SITE_URL)

    # 3. Report the result
    if latest_date:
        print(f"\nSuccess: Most recent GSC data available is for: {latest_date.strftime('%Y-%m-%d')}")
    else:
        last_checked_date = datetime.now().date() - timedelta(days=START_OFFSET_DAYS + MAX_DAYS_TO_CHECK -1)
        print(f"\nWarning: Could not find GSC data within the last {MAX_DAYS_TO_CHECK} checked days")
        print(f"         (Checked back to {last_checked_date.strftime('%Y-%m-%d')}).")
        print("         Please verify the service account has permissions for the site,")
        print("         and check the GSC interface for data availability.")


if __name__ == "__main__":
    # Ensure SITE_URL is set
    if not SITE_URL:
         print("Error: Please set the GSC_SITE_URL environment variable or update the 'SITE_URL' variable in the script.")
         print("Example usage: GSC_SITE_URL=\"sc-domain:example.com\" python precursors/gsc_movers_and_shakers.py")
         sys.exit(1)
    main()