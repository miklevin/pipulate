#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Downloads a JavaScript file from a specified URL and saves it locally.
"""

import requests
from pathlib import Path
import sys

# --- Configuration ---
# URL of the JavaScript file to download
JS_URL = "https://cdn.jsdelivr.net/npm/marked/marked.min.js"

# Target directory to save the file
# IMPORTANT: Adjust this path if it's different on your system
TARGET_DIR = Path("/home/mike/repos/pipulate/static")

# --- Main Script Logic ---
def download_js_library(url: str, save_dir: Path):
    """
    Downloads a file from the given URL and saves it into the specified directory.

    Args:
        url (str): The URL of the file to download.
        save_dir (Path): The directory where the file should be saved.
    """
    try:
        # Ensure the target directory exists, create if it doesn't
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"Target directory: {save_dir}")

        # Extract the filename from the URL
        filename = Path(url).name
        if not filename:
            print(f"Error: Could not determine filename from URL: {url}", file=sys.stderr)
            sys.exit(1)

        save_path = save_dir / filename
        print(f"Attempting to download '{filename}' from {url}...")

        # Perform the GET request to download the file
        response = requests.get(url, stream=True, timeout=30) # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Write the content to the local file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Successfully downloaded and saved to: {save_path}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error saving file to {save_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # --- Installation Note ---
    # Ensure you have the 'requests' library installed:
    # pip install requests
    # --- ---

    print("Starting JavaScript library download...")
    download_js_library(JS_URL, TARGET_DIR)
    print("Download process finished.")

