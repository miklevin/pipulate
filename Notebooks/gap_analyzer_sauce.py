# Drops pebble in pond

import os
import shutil
from pathlib import Path
import glob
from pipulate import pip # Import pip for persistence
import nbformat
import itertools


def extract_domains_and_print_urls(job: str, notebook_filename: str = "GAPalyzer.ipynb"):
    """
    Parses the specified notebook for competitor domains, stores them using pip.set,
    and prints the generated SEMrush URLs.

    Args:
        job (str): The current Pipulate job ID.
        notebook_filename (str): The name of the notebook file to parse.

    Returns:
        list: The list of extracted domains, or an empty list if none found/error.
    """
    domains = [] # Initialize domains to ensure it's always defined

    # --- Inner function to read notebook (kept internal to this step) ---
    def get_competitors_from_notebook(nb_file):
        """Parses the notebook to get the domain list from the 'url-list-input' cell."""
        try:
            notebook_path = Path(nb_file) # Use the passed filename
            if not notebook_path.exists():
                 print(f"❌ Error: Notebook file not found at '{notebook_path.resolve()}'")
                 return []
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)

            for cell in nb.cells:
                if "url-list-input" in cell.metadata.get("tags", []):
                    domains_raw = cell.source
                    # Ensure domains_raw is treated as a string before splitting lines
                    if isinstance(domains_raw, list):
                         domains_raw = "".join(domains_raw) # Join list elements if needed
                    elif not isinstance(domains_raw, str):
                         print(f"⚠️ Warning: Unexpected data type for domains_raw: {type(domains_raw)}. Trying to convert.")
                         domains_raw = str(domains_raw)

                    # Now splitlines should work reliably
                    extracted_domains = [
                        line.split('#')[0].strip()
                        for line in domains_raw.splitlines()
                        if line.strip() and not line.strip().startswith('#')
                    ]
                    return extracted_domains
            print("⚠️ Warning: Could not find a cell tagged with 'url-list-input'.")
            return []
        except Exception as e:
            print(f"❌ Error reading domains from notebook: {e}")
            return []

    # --- Main Logic ---
    print("🚀 Extracting domains and generating SEMrush URLs...")

    domains = get_competitors_from_notebook(notebook_filename)

    # --- Pipulate Scaffolding ---
    # Store the extracted domains list. This supports idempotency.
    # If the notebook restarts, subsequent steps can just pip.get('competitor_domains').
    pip.set(job, 'competitor_domains', domains)
    print(f"💾 Stored {len(domains)} domains in pip state for job '{job}'.")
    # ---------------------------

    url_template = "https://www.semrush.com/analytics/organic/positions/?db=us&q={domain}&searchType=domain"

    if not domains:
        print("🛑 No domains found or extracted. Please check the 'url-list-input' cell.")
    else:
        print(f"✅ Found {len(domains)} competitor domains. URLs to check:")
        print("-" * 30)
        for i, domain in enumerate(domains):
            full_url = url_template.format(domain=domain)
            # Keep the print logic here as it's primarily for user feedback in the notebook
            print(f"{i+1}. {domain}:\n   {full_url}\n")

    return domains # Return the list for potential immediate use


def collect_semrush_downloads(job: str, download_path_str: str, file_pattern_xlsx: str = "*-organic.Positions*.xlsx"):
    """
    Moves downloaded SEMRush files matching patterns from the user's download
    directory to a job-specific 'downloads/{job}/' folder, records the
    destination directory and file list in pip state.

    Args:
        job (str): The current job ID.
        download_path_str (str): The user's default browser download path (e.g., "~/Downloads").
        file_pattern_xlsx (str): The glob pattern for SEMRush XLSX files. CSV pattern is derived.

    Returns:
        tuple: (destination_dir_path: str, moved_files_list: list)
               Paths are returned as strings for compatibility. Returns (None, []) on failure or no files.
    """
    print("📦 Starting collection of new SEMRush downloads...")

    # 1. Define source and destination paths
    try:
        source_dir = Path(download_path_str).expanduser()
        if not source_dir.is_dir():
            print(f"❌ Error: Source download directory not found or is not a directory: '{source_dir}'")
            return None, []

        # Destination path relative to the current working directory (assumed Notebooks/)
        destination_dir = Path("downloads") / job
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_dir_str = str(destination_dir.resolve()) # Store resolved path as string
        print(f"Destination folder created/ensured: '{destination_dir_str}'")

    except Exception as e:
        print(f"❌ Error setting up paths: {e}")
        return None, []

    # 3. Find files in the source directory matching the patterns
    files_to_move = []
    moved_files_list = [] # List to store paths of successfully moved files

    try:
        # Check for .xlsx files
        xlsx_files = glob.glob(str(source_dir / file_pattern_xlsx))
        files_to_move.extend(xlsx_files)

        # Check for .csv files
        file_pattern_csv = file_pattern_xlsx.replace(".xlsx", ".csv")
        csv_files = glob.glob(str(source_dir / file_pattern_csv))
        files_to_move.extend(csv_files)

        if not files_to_move:
            print(f"⚠️ No new files matching patterns ('{file_pattern_xlsx}', '{file_pattern_csv}') found in '{source_dir}'. Skipping move.")
            # --- Pipulate Scaffolding ---
            pip.set(job, 'semrush_download_dir', str(destination_dir)) # Still record the dir path
            pip.set(job, 'collected_semrush_files', []) # Record empty list
            # ---------------------------
            return destination_dir_str, []

        # 4. Move the files
        move_count = 0
        print(f"🔍 Found {len(files_to_move)} potential files to move...")
        for source_file_path in files_to_move:
            source_file = Path(source_file_path)
            dest_file = destination_dir / source_file.name
            dest_file_str = str(dest_file.resolve()) # Store resolved path as string

            if dest_file.exists():
                # File already exists, add its path to the list but don't move
                if dest_file_str not in moved_files_list:
                     moved_files_list.append(dest_file_str)
                # print(f"  -> Skipping (already exists): {source_file.name}") # Optional: Reduce noise
                continue

            try:
                shutil.move(source_file, dest_file)
                print(f"  -> Moved: {source_file.name} to {dest_file}")
                moved_files_list.append(dest_file_str) # Add successfully moved file path
                move_count += 1
            except Exception as e:
                print(f"  -> ❌ Error moving {source_file.name}: {e}")

        print(f"✅ Collection complete. {move_count} new files moved to '{destination_dir}'. Total relevant files: {len(moved_files_list)}")

        # --- Pipulate Scaffolding ---
        pip.set(job, 'semrush_download_dir', destination_dir_str)
        pip.set(job, 'collected_semrush_files', moved_files_list)
        print(f"💾 Stored download directory and {len(moved_files_list)} file paths in pip state for job '{job}'.")
        # ---------------------------

        return destination_dir_str, moved_files_list

    except Exception as e:
        print(f"❌ An unexpected error occurred during file collection: {e}")
        # Attempt to store whatever state we have
        pip.set(job, 'semrush_download_dir', destination_dir_str)
        pip.set(job, 'collected_semrush_files', moved_files_list)
        return destination_dir_str, moved_files_list


def find_semrush_files_and_generate_summary(job: str, competitor_limit: int = None):
    """
    Finds SEMRush files, stores paths in pip state, and generates a Markdown summary.

    Args:
        job (str): The current Pipulate job ID.
        competitor_limit (int, optional): Max number of competitors to list in summary. Defaults to None (list all).


    Returns:
        str: A Markdown formatted string summarizing the found files, or a warning message.
    """
    print(f"🔍 Locating SEMRush files for job '{job}' and generating summary...")
    semrush_dir = Path("downloads") / job
    markdown_output_lines = [] # Initialize list to build Markdown output

    # Ensure the directory exists
    if not semrush_dir.is_dir():
         warning_msg = f"⚠️ **Warning:** Download directory `{semrush_dir.resolve()}` not found. Assuming no files collected yet."
         print(warning_msg.replace("**","")) # Print clean version to console
         pip.set(job, 'collected_semrush_files', [])
         return warning_msg # Return Markdown warning

    file_patterns = [
        "*-organic.Positions*.xlsx",
        "*-organic.Positions*.csv"
    ]

    try:
        all_downloaded_files = sorted(list(itertools.chain.from_iterable(
            semrush_dir.glob(pattern) for pattern in file_patterns
        )))
        all_downloaded_files_as_str = [str(p.resolve()) for p in all_downloaded_files]

        # --- Pipulate Scaffolding ---
        pip.set(job, 'collected_semrush_files', all_downloaded_files_as_str)
        # ---------------------------

        # --- Generate Markdown Output ---
        if all_downloaded_files:
            print(f"💾 Found {len(all_downloaded_files)} files and stored paths in pip state.")
            markdown_output_lines.append("## 💾 Found Downloaded Files")
            markdown_output_lines.append(f"✅ **{len(all_downloaded_files)} files** ready for processing in `{semrush_dir}/`\n")

            display_limit = competitor_limit if competitor_limit is not None else len(all_downloaded_files)
            if display_limit < len(all_downloaded_files):
                 markdown_output_lines.append(f"*(Displaying first {display_limit} based on COMPETITOR_LIMIT)*\n")

            for i, file in enumerate(all_downloaded_files[:display_limit]):
                try:
                    domain_name = file.name[:file.name.index("-organic.")].strip()
                except ValueError:
                    domain_name = file.name # Fallback
                markdown_output_lines.append(f"{i + 1}. **`{domain_name}`** ({file.suffix.upper()})")

        else:
            print(f"🤷 No files found matching patterns in '{semrush_dir}'. Stored empty list in pip state.")
            warning_msg = f"⚠️ **Warning:** No SEMRush files found in `{semrush_dir.resolve()}/`.\n(Looking for `*-organic.Positions*.xlsx` or `*.csv`)"
            markdown_output_lines.append(warning_msg)

        return "\n".join(markdown_output_lines)

    except Exception as e:
        error_msg = f"❌ An unexpected error occurred while listing SEMRush files: {e}"
        print(error_msg)
        pip.set(job, 'collected_semrush_files', []) # Store empty list on error
        return f"❌ **Error:** An error occurred during file listing. Check logs. ({e})"

# In Notebooks/gap_analyzer_sauce.py
import pandas as pd
from tldextract import extract
import itertools
from pathlib import Path
from pipulate import pip # Ensure pip is imported

# (Keep previously added functions)
# ...

def _extract_registered_domain(url: str) -> str:
    """Private helper to extract the registered domain (domain.suffix) from a URL/hostname."""
    try:
        extracted = extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        # Fallback for invalid inputs
        return url

def load_and_combine_semrush_data(job: str, client_domain: str, competitor_limit: int = None):
    """
    Loads all SEMRush files from pip state, combines them into a single master DataFrame,
    stores the result in pip state, and returns the DataFrame along with value counts for display.

    Args:
        job (str): The current Pipulate job ID.
        client_domain (str): The client's registered domain (e.g., 'example.com').
        competitor_limit (int, optional): Max number of competitor files to process.

    Returns:
        tuple: (master_df: pd.DataFrame, domain_counts: pd.Series)
               Returns the combined DataFrame and a Series of domain value counts.
               Returns (empty DataFrame, empty Series) on failure or no files.
    """
    semrush_lookup = _extract_registered_domain(client_domain)
    print(f"🛠️  Loading and combining SEMRush files for {semrush_lookup}...")

    # --- INPUT (from pip state) ---
    files_to_process_str = pip.get(job, 'collected_semrush_files', [])
    if not files_to_process_str:
        print("🤷 No collected SEMRush files found in pip state. Nothing to process.")
        return pd.DataFrame(), pd.Series(dtype='int64')

    # Convert string paths back to Path objects
    all_semrush_files = [Path(p) for p in files_to_process_str]
    
    # --- Refactoring Note: Apply COMPETITOR_LIMIT here ---
    # We add 1 to the limit to include the client file if it exists
    processing_limit = competitor_limit + 1 if competitor_limit is not None else None
    files_to_process = all_semrush_files[:processing_limit]
    if processing_limit and len(all_semrush_files) > processing_limit:
        print(f"🔪 Applying COMPETITOR_LIMIT: Processing first {processing_limit} of {len(all_semrush_files)} files.")


    # --- CORE LOGIC (Moved from Notebook) ---
    cdict = {}
    list_of_dfs = []
    print(f"Loading {len(files_to_process)} SEMRush files: ", end="", flush=True)

    for j, data_file in enumerate(files_to_process):
        read_func = pd.read_excel if data_file.suffix.lower() == '.xlsx' else pd.read_csv
        try:
            nend = data_file.stem.index("-organic")
            xlabel = data_file.stem[:nend].replace("_", "/").replace("///", "://").strip('.')
            just_domain = _extract_registered_domain(xlabel)
            cdict[just_domain] = xlabel

            df = read_func(data_file)
            df["Domain"] = xlabel # Use the full label (sub.domain.com) for the column
            df["Client URL"] = df.apply(lambda row: row["URL"] if row["Domain"] == semrush_lookup else None, axis=1)
            df["Competitor URL"] = df.apply(lambda row: row["URL"] if row["Domain"] != semrush_lookup else None, axis=1)
            list_of_dfs.append(df)
            print(f"{j + 1} ", end="", flush=True)

        except Exception as e:
            print(f"\n❌ Error processing file {data_file.name}: {e}")
            continue
    
    print("\n") # Newline after the loading count

    if not list_of_dfs:
        print("🛑 No DataFrames were created. Check for errors in file processing.")
        return pd.DataFrame(), pd.Series(dtype='int64')

    master_df = pd.concat(list_of_dfs, ignore_index=True)
    rows, columns = master_df.shape
    print(f"✅ Combined DataFrame created. Rows: {rows:,}, Columns: {columns:,}")
    
    domain_counts = master_df["Domain"].value_counts()

    # --- OUTPUT (to pip state) ---
    # Storing large DF as JSON is okay for now, per instructions.
    # Future distillation: Save to CSV/Parquet and store path instead.
    pip.set(job, 'semrush_master_df_json', master_df.to_json(orient='records'))
    pip.set(job, 'competitors_dict_json', cdict) # Store the competitor name mapping
    print(f"💾 Stored master DataFrame and competitor dictionary in pip state for job '{job}'.")
    # -----------------------------

    # --- RETURN VALUE ---
    return master_df, domain_counts
