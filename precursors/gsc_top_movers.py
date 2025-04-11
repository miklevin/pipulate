#!/usr/bin/env python
# coding: utf-8

"""
Fetches Google Search Console (GSC) data for the 4 most recent days available,
calculates trend slopes for impressions, clicks, and position for each
page/query combination, and identifies top movers. Saves daily data to CSV cache.

Required pip installs:
    pip install google-api-python-client google-auth pandas numpy scipy
"""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# Need scipy for linregress OR numpy for polyfit - we'll use polyfit here
# from scipy.stats import linregress

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


# --- Functions from previous steps (authenticate_gsc, check_date_has_data, find_most_recent_gsc_data_date, fetch_all_gsc_data, process_gsc_data_to_dataframe, get_gsc_data_for_day) ---
# Include the full definitions of these functions here from the previous code block...

def authenticate_gsc():
    """Authenticates with Google API using service account credentials."""
    if not os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
        print(f"Error: Service account key file not found at: {SERVICE_ACCOUNT_KEY_FILE}")
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
        # Keep this print statement for clarity during processing
        # print(f"No data to process into DataFrame for {data_date}.")
        return pd.DataFrame() # Return empty DF if no raw data
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
        # else: # No need to print this repeatedly if a metric is consistently missing
            # print(f"Note: Metric column '{col}' not found for {data_date}.")
    if 'ctr' in df.columns: df['ctr'] = df['ctr'] * 100
    # Don't print success here, wait until after combining DFs if needed
    # print(f"✓ Processed data for {data_date} into DataFrame ({len(df)} rows).")
    return df

def get_gsc_data_for_day(service, site_url, data_date):
    """Fetches GSC data for a specific day, using cache if available."""
    date_str = data_date.strftime('%Y-%m-%d')
    cache_filename = os.path.join(CACHE_DIR, f"gsc_data_{date_str}.csv")
    if os.path.exists(cache_filename):
        try:
            print(f"✓ Loading data for {date_str} from cache: {cache_filename}")
            df = pd.read_csv(cache_filename, dtype={
                'clicks': 'Int64', 'impressions': 'Int64', 'ctr': 'float64',
                'position': 'float64', 'query': 'object', 'page': 'object'
            }, parse_dates=False)
            if 'ctr' in df.columns and not df['ctr'].empty and df['ctr'].max() <= 1.0:
                 df['ctr'] = df['ctr'] * 100
            return df
        except Exception as e:
            print(f"Warning: Could not load cache file {cache_filename}. Error: {e}. Re-fetching.")
    print(f"Fetching data for {date_str} from GSC API...")
    request = {
        'startDate': date_str, 'endDate': date_str,
        'dimensions': ['query', 'page'],
        'rowLimit': 25000, 'startRow': 0
    }
    raw_data = fetch_all_gsc_data(service, site_url, request)
    df = process_gsc_data_to_dataframe(raw_data, date_str)
    if not df.empty:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            df.to_csv(cache_filename, index=False)
            print(f"✓ Saved data for {date_str} to cache: {cache_filename}")
        except Exception as e:
            print(f"Warning: Could not save data for {date_str} to cache. Error: {e}")
    return df

# --- New Function for Trend Analysis ---

def analyze_trends(daily_dataframes_dict):
    """
    Combines daily DataFrames and calculates trend slopes and time series.

    Args:
        daily_dataframes_dict (dict): Dict mapping date obj to daily GSC DataFrame.

    Returns:
        pandas.DataFrame: DataFrame with page, query, slopes, and time series lists.
                          Returns empty DataFrame if input is invalid or processing fails.
    """
    if not daily_dataframes_dict or len(daily_dataframes_dict) < 2:
        print("Error: Need at least 2 days of data for trend analysis.")
        return pd.DataFrame()

    # Get sorted dates from the dictionary keys
    dates = sorted(daily_dataframes_dict.keys())
    num_days = len(dates)

    # Prepare list of dataframes to concatenate, adding date column
    dfs_to_concat = []
    for date, df in daily_dataframes_dict.items():
        if not df.empty:
            df_copy = df.copy() # Work on a copy
            df_copy['date'] = pd.to_datetime(date) # Ensure date is datetime object
            dfs_to_concat.append(df_copy)

    if not dfs_to_concat:
        print("Error: No valid DataFrames found to combine for trend analysis.")
        return pd.DataFrame()

    # Combine DataFrames
    combined_df = pd.concat(dfs_to_concat, ignore_index=True)
    print(f"\n✓ Combined data for {len(dates)} days into a single DataFrame ({len(combined_df)} rows total).")

    # Add Day Index for regression
    date_to_index = {pd.to_datetime(date): i for i, date in enumerate(dates)}
    combined_df['day_index'] = combined_df['date'].map(date_to_index)

    # Define metrics for trend analysis
    metrics = ['impressions', 'clicks', 'position']

    # --- Inner function to process each page/query group ---
    def analyze_single_group(group):
        # Convert the groupby result to a DataFrame if it's a Series
        if isinstance(group, pd.Series):
            group = group.to_frame().T
        
        # Ensure date is in datetime format
        if 'date' in group.columns:
            group['date'] = pd.to_datetime(group['date'])
            group = group.set_index('date')
        
        # Create a complete date range
        full_date_index = pd.to_datetime(dates)
        
        # Create empty results dictionary
        results = {}
        
        # Handle each metric
        for metric in metrics:
            # Default values in case metric is missing
            results[f'{metric}_ts'] = [0] * num_days  # Default time series
            results[f'{metric}_slope'] = np.nan       # Default slope
            
            # Skip processing if metric is not in the group's columns
            if metric not in group.columns:
                continue
                
            # Get metric values for each date (align with date index)
            metric_by_date = {}
            for _, row in group.reset_index().iterrows():
                if 'date' in row and pd.notnull(row['date']) and metric in row and pd.notnull(row[metric]):
                    dt = pd.to_datetime(row['date'])
                    metric_by_date[dt] = row[metric]
            
            # Create time series array aligned with full date range
            ts_values = []
            for dt in full_date_index:
                if dt in metric_by_date:
                    value = metric_by_date[dt]
                    # Handle impressions and clicks as integers (filled with 0)
                    if metric in ['impressions', 'clicks']:
                        ts_values.append(int(value) if pd.notnull(value) else 0)
                    # Handle position as float (can be NaN)
                    else:
                        ts_values.append(round(float(value), 1) if pd.notnull(value) else np.nan)
                else:
                    # For missing dates: 0 for counts, NaN for position
                    ts_values.append(0 if metric in ['impressions', 'clicks'] else np.nan)
            
            results[f'{metric}_ts'] = ts_values
            
            # Calculate regression slope if we have enough valid data points
            x = np.arange(num_days)
            y = np.array(ts_values)
            valid_mask = ~np.isnan(y)
            valid_count = np.sum(valid_mask)
            
            if valid_count >= 2:  # Need at least two points for regression
                try:
                    # Extract valid x and y values
                    x_valid = x[valid_mask]
                    y_valid = y[valid_mask]
                    # Calculate slope using numpy's polyfit
                    coeffs = np.polyfit(x_valid, y_valid, 1)
                    results[f'{metric}_slope'] = coeffs[0]
                except (np.linalg.LinAlgError, ValueError, TypeError) as e:
                    # Handle computation errors
                    print(f"Warning: Slope calculation error for metric {metric}: {e}")
                    results[f'{metric}_slope'] = np.nan
        
        return pd.Series(results)
    # --- End of inner function ---

    print("✓ Starting trend analysis by grouping page/query combinations...")
    # Apply the analysis function to each group
    # Handle potential errors during apply (e.g., unexpected data types)
    try:
        # Using include_groups=False to avoid deprecation warning
        analysis_results = combined_df.groupby(['page', 'query'], observed=True, dropna=False).apply(
            analyze_single_group, include_groups=False).reset_index()
        print(f"✓ Trend analysis complete. Found {len(analysis_results)} unique page/query combinations.")
    except Exception as e:
        print(f"Error during groupby/apply operation for trend analysis: {e}")
        return pd.DataFrame() # Return empty DF on error

    # Optional: Round slopes for cleaner display
    for metric in metrics:
        col_name = f'{metric}_slope'
        if col_name in analysis_results.columns:
             analysis_results[col_name] = analysis_results[col_name].round(2)

    return analysis_results


# --- Modify the main() function ---

def main():
    """Main execution function."""
    # 1. Authenticate
    gsc_service = authenticate_gsc()

    # 2. Find most recent date
    latest_date = find_most_recent_gsc_data_date(gsc_service, SITE_URL)
    if not latest_date:
        print("\nCannot proceed without a valid recent date.")
        sys.exit(1)
    print(f"\nSuccess: Most recent GSC data available is for: {latest_date.strftime('%Y-%m-%d')}")

    # 3. Determine dates to fetch
    dates_to_fetch = [latest_date - timedelta(days=i) for i in range(NUM_DAYS_TO_FETCH)][::-1]
    print(f"\nPreparing to fetch/load data for {NUM_DAYS_TO_FETCH} days:")
    print(f"  Dates: {[d.strftime('%Y-%m-%d') for d in dates_to_fetch]}")

    # 4. Fetch/load daily data
    daily_dataframes = {}
    all_data_loaded = True
    for target_date in dates_to_fetch:
        df_day = get_gsc_data_for_day(gsc_service, SITE_URL, target_date)
        # Even if df_day is empty, store it to represent the day
        daily_dataframes[target_date] = df_day
        # Check if loading/fetching failed *and* cache doesn't exist
        if df_day.empty and not os.path.exists(os.path.join(CACHE_DIR, f"gsc_data_{target_date.strftime('%Y-%m-%d')}.csv")):
             print(f"Warning: Data could not be fetched or loaded for {target_date.strftime('%Y-%m-%d')}. Trend analysis might be incomplete.")
             all_data_loaded = False

    if not all_data_loaded:
         print("\nWarning: Data loading was incomplete. Proceeding with available data.")

    # --- ADD TREND ANALYSIS STEP ---
    # 5. Perform Trend Analysis
    trend_results_df = analyze_trends(daily_dataframes)

    # 6. Display Trend Analysis Results
    if not trend_results_df.empty:
        # Configure pandas display settings for better table formatting
        pd.set_option('display.max_rows', 30)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('display.max_colwidth', None)
        
        # Create a simplified display dataframe with cleaner formatting
        display_df = trend_results_df.copy()
        
        # Process the dataframe for display
        # 1. Extract page path from full URL
        if 'page' in display_df.columns:
            display_df['page'] = display_df['page'].str.replace(r'https://mikelev.in/futureproof/', '', regex=True)
            # Further trim endings
            display_df['page'] = display_df['page'].str.replace(r'/$', '', regex=True)
            
        # 2. Convert time series lists to more compact string representations
        for col in ['impressions_ts', 'clicks_ts', 'position_ts']:
            if col in display_df.columns:
                # Format time series values more compactly
                display_df[col] = display_df[col].apply(
                    lambda x: '[' + ','.join([str(int(i)) if isinstance(i, (int, float)) and not pd.isna(i) else '-' for i in x]) + ']'
                )
                
        # 3. Format slope values to 1 decimal place
        for col in ['impressions_slope', 'clicks_slope', 'position_slope']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"{x:.1f}" if pd.notnull(x) else "-"
                )
                
        print("\n--- Top 15 by Impression Increase ---")
        top_impressions = display_df.sort_values('impressions_slope', ascending=False, na_position='last').head(15)
        print(top_impressions.to_string(index=False))

        print("\n--- Top 15 by Position Improvement (Lower is Better) ---")
        # Ensure we're working with original numeric values for sorting
        numeric_df = trend_results_df.copy()
        numeric_df = numeric_df.dropna(subset=['position_slope'])
        # Sort by position_slope (lowest/most negative is best improvement) 
        top_positions_idx = numeric_df.sort_values('position_slope', ascending=True).head(15).index
        # Display using the formatted display dataframe
        print(display_df.loc[top_positions_idx].to_string(index=False))

        print("\n--- DataFrame Info ---")
        trend_results_df.info()

        # Save the final trend analysis results using the original dataframe (with full URLs)
        final_output_filename = os.path.join(SCRIPT_DIR, f"gsc_trend_analysis_{dates_to_fetch[0].strftime('%Y%m%d')}_to_{dates_to_fetch[-1].strftime('%Y%m%d')}.csv")
        try:
            trend_results_df.to_csv(final_output_filename, index=False)
            print(f"\n✓ Saved final trend analysis to: {final_output_filename}")
        except Exception as e:
            print(f"\nWarning: Failed to save final trend analysis results. Error: {e}")

    else:
        print("\nTrend analysis could not be completed.")

    print("\nScript finished.")


if __name__ == "__main__":
    if not SITE_URL or SITE_URL == "sc-domain:yourdomain.com":
        print("Error: Please update the 'SITE_URL' variable in the script configuration.")
        sys.exit(1)
    main()