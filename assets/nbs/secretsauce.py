# secretsauce.py (version 2.3 - Full Transparency)
# This module contains the implementation details for a 1-to-many AI enrichment workflow.

from pipulate import pip
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import json
from sqlitedict import SqliteDict
import asyncio

# --- CONFIGURATION ---
CACHE_DB_FILE = "url_cache.sqlite"
EXTRACTED_DATA_CSV = "_step_extract_output.csv"
AI_LOG_CSV = "_step_ai_log_output.csv" # NEW: Filename for the AI output log
PROMPT_TEMPLATE_FILE = "prompt.txt"

# Pipulate step names
API_KEY_STEP = "api_key"
URL_LIST_STEP = "url_list"
EXTRACTED_DATA_STEP = "extracted_data"
FAQ_DATA_STEP = "faq_data"
FINAL_DATAFRAME_STEP = "final_dataframe"
EXPORT_FILE_STEP = "export_file_path"

# --- WORKFLOW FUNCTIONS ---
# cache_url_responses, and extract_webpage_data remain unchanged.
# In Notebooks/secretsauce.py
async def scrape_and_extract(job: str, headless: bool = True, verbose: bool = False):
    """
    Scrapes each URL using pip.scrape() and immediately parses the HTML
    to extract key SEO data. Verbosity is now controllable.
    """
    print("🚀 Starting browser-based scraping and extraction...")
    
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    extracted_data = []

    for i, url in enumerate(urls_to_process):
        # This line now prints for every URL, regardless of the verbose setting.
        print(f"  -> 👁️  [{i+1}/{len(urls_to_process)}] Processing: {url}")
        
        try:
            scrape_result = await pip.scrape(
                url=url,
                take_screenshot=True,
                headless=headless,
                verbose=verbose
            )

            if not scrape_result.get("success"):
                if verbose:
                    print(f"  -> ❌ Scrape failed: {scrape_result.get('error')}")
                continue

            dom_path = scrape_result.get("looking_at_files", {}).get("rendered_dom")
            if not dom_path:
                if verbose:
                    print(f"  -> ⚠️ Scrape succeeded, but no DOM file was found.")
                continue

            with open(dom_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title Found"
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc_tag['content'].strip() if meta_desc_tag else ""
            h1s = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
            h2s = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
            
            extracted_data.append({
                'url': url, 'title': title, 'meta_description': meta_description,
                'h1s': h1s, 'h2s': h2s
            })
            if verbose:
                print(f"  -> ✅ Scraped and Extracted.")

        except Exception as e:
            # Always show critical errors for the specific URL that failed.
            print(f"  -> ❌ A critical error occurred while processing {url}: {e}")

    pip.set(job, EXTRACTED_DATA_STEP, extracted_data)
    print(f"✅ Scraping and extraction complete for {len(extracted_data)} URLs.")


async def scrape_all_urls(job: str, headless: bool = True):
    """
    Iterates through the URL list from the pip state, scraping each one
    using the advanced pip.scrape() browser automation.
    """
    print("🚀 Starting browser automation scrape for all URLs...")
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    
    scraped_data_paths = {}
    for url in urls_to_process:
        print(f"  -> 👁️  Scraping: {url}")
        try:
            # Call the core scrape method for each URL
            result = await pip.scrape(
                url=url,
                take_screenshot=True,
                headless=headless
            )
            if result.get("success"):
                scraped_data_paths[url] = result.get("looking_at_files", {})
                print(f"  -> ✅ Success! Artifacts saved.")
            else:
                print(f"  -> ❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"  -> ❌ A critical error occurred while scraping {url}: {e}")
    
    # For now, we'll just confirm completion. The next step will be to use this data.
    print("\n--- ✅ Browser automation complete! ---")
    # We can store the paths to the results for the next step, though we won't use it yet.
    pip.set(job, "scraped_data_paths", scraped_data_paths)


def extract_webpage_data(job: str):
    """Reads from cache, extracts key SEO elements, and saves to CSV."""
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    extracted_data = []
    print(f"🔍 Extracting SEO elements for {len(urls_to_process)} URLs...")
    with SqliteDict(CACHE_DB_FILE) as cache:
        for url in urls_to_process:
            response = cache.get(url)
            if not response or not isinstance(response, requests.Response):
                print(f"  -> ⏭️ Skipping {url} (no valid cache entry).")
                continue
            print(f"  -> Parsing {url}...")
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title Found"
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc_tag['content'].strip() if meta_desc_tag else ""
            h1s = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
            h2s = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
            extracted_data.append({
                'url': url, 'title': title, 'meta_description': meta_description,
                'h1s': h1s, 'h2s': h2s
            })
    pip.set(job, EXTRACTED_DATA_STEP, extracted_data)
    try:
        df = pd.DataFrame(extracted_data)
        df.to_csv(EXTRACTED_DATA_CSV, index=False)
        print(f"✅ Extraction complete. Intermediate data saved to '{EXTRACTED_DATA_CSV}'")
    except Exception as e:
        print(f"⚠️ Could not save intermediate CSV: {e}")


def generate_faqs(job: str):
    """Generates 5 FAQs for each URL using a dynamic prompt template."""
    extracted_data = pip.get(job, EXTRACTED_DATA_STEP, [])
    faq_data = pip.get(job, FAQ_DATA_STEP, [])
    processed_urls = {item.get('url') for item in faq_data}

    print(f"🧠 Generating FAQs... {len(processed_urls)} of {len(extracted_data)} URLs already complete.")

    try:
        with open(PROMPT_TEMPLATE_FILE, 'r') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Prompt file '{PROMPT_TEMPLATE_FILE}' not found. Please create it.")
        return

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        for item in extracted_data:
            url = item.get('url')
            if url in processed_urls:
                continue

            print(f"  -> Generating FAQs for {url}...")
            
            webpage_data_str = json.dumps(item, indent=2)
            full_prompt = prompt_template.replace("{webpage_data}", webpage_data_str)
            
            try:
                ai_response = model.generate_content(full_prompt)
                response_text = ai_response.text.strip().replace("```json", "").replace("```", "")
                faq_json = json.loads(response_text)
                
                for faq in faq_json['faqs']:
                    flat_record = {
                        'url': item.get('url'),
                        'title': item.get('title'),
                        'priority': faq.get('priority'),
                        'question': faq.get('question'),
                        'target_intent': faq.get('target_intent'),
                        'justification': faq.get('justification')
                    }
                    faq_data.append(flat_record)
                
                processed_urls.add(url)
                pip.set(job, FAQ_DATA_STEP, faq_data)
                print(f"  -> ✅ Successfully generated 5 FAQs for {url}")

            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"❌ AI processing or parsing failed for '{url}': {e}")

    except Exception as e:
        print(f"❌ Could not initialize AI model. Is your API key correct? Error: {e}")
    print("✅ FAQ generation complete.")


def display_results_log(job: str):
    """
    MODIFIED: Displays the FAQ log AND saves it to an intermediate CSV.
    """
    print("📊 Displaying raw FAQ log...")
    faq_data = pip.get(job, FAQ_DATA_STEP, [])
    if not faq_data:
        print("No FAQ data to display. Please run the previous steps.")
        return
    
    df = pd.DataFrame(faq_data)
    
    # NEW: Save the second "factory floor" file for transparency.
    try:
        df.to_csv(AI_LOG_CSV, index=False)
        print(f"  -> Intermediate AI log saved to '{AI_LOG_CSV}'")
    except Exception as e:
        print(f"⚠️ Could not save AI log CSV: {e}")

    pip.set(job, FINAL_DATAFRAME_STEP, df.to_json(orient='records'))
    with pd.option_context('display.max_rows', None, 'display.max_colwidth', 80):
        display(df)

def export_to_excel(job: str):
    """Exports the final DataFrame to a formatted Excel file."""
    print("📄 Exporting data to Excel...")
    final_json = pip.get(job, FINAL_DATAFRAME_STEP)
    if not final_json:
        print("❌ No final data found to export. Please run the 'display_results' step first.")
        return
    df_final = pd.read_json(StringIO(final_json))
    output_filename = f"{job}_output.xlsx"
    try:
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Faquillizer_Data')
            worksheet = writer.sheets['Faquillizer_Data']
            for column in worksheet.columns:
                max_length = max((df_final[column[0].value].astype(str).map(len).max(), len(str(column[0].value))))
                adjusted_width = (max_length + 2) if max_length < 80 else 80
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        pip.set(job, EXPORT_FILE_STEP, output_filename)
        print(f"✅ Success! Data exported to '{output_filename}'")
    except Exception as e:
        print(f"❌ Failed to export to Excel: {e}")


