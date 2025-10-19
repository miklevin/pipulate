# Drops pebble in pond

# In Notebooks/gap_analyzer_sauce.py
import nbformat
from pathlib import Path
from pipulate import pip # Import pip for persistence

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
