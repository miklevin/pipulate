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

def cache_url_responses(job: str):
    """
    Iterates through URLs and caches the 'requests' response object, using a
    common browser user agent to avoid being blocked.
    """
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    # NEW: Define a standard browser header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"🔄 Caching web responses for {len(urls_to_process)} URLs...")
    with SqliteDict(CACHE_DB_FILE, autocommit=True) as cache:
        processed_count = len(cache)
        print(f"  -> Cache contains {processed_count} items.")
        for url in urls_to_process:
            if url in cache and isinstance(cache[url], requests.Response):
                continue
            try:
                print(f"  -> Fetching and caching {url}...")
                # MODIFIED: Pass the headers with the request
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                cache[url] = response
            except requests.exceptions.RequestException as e:
                print(f"❌ Failed to fetch {url}: {e}")
                cache[url] = str(e)
    print("✅ Caching complete.")

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


# START: test_advanced_scrape
async def test_advanced_scrape(job: str, headless: bool = False):
    """
    NEW (Optional Test): Scrapes the FIRST URL from the list using the advanced
    pip.scrape() browser automation to capture a full set of artifacts.
    """
    print("\n--- 🧪 Starting Advanced Scrape Test Flight ---")
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    if not urls_to_process:
        print("  -> No URLs found to test. Skipping.")
        return
    url_to_test = urls_to_process[0]
    print(f"  -> Target: {url_to_test}")
    print(f"  -> Headless Mode: {headless}")

    # This is the call to the powerful, Selenium-based scraper
    # exposed through the pipulate library, now with headless toggle.
    result = await pip.scrape(url=url_to_test, take_screenshot=True, headless=headless)

    if result.get('success'):
        print(f"  -> ✅ Success! Advanced scrape complete.")
        files_created = result.get('looking_at_files', {})
        print("  -> Artifacts captured in 'browser_cache/looking_at/':")
        for key, path in files_created.items():
            if path:
                print(f"       - {key}: {path}")
    else:
        print(f"  -> ❌ Failed: {result.get('error')}")
    print("--- 🧪 Test Flight Complete ---\n")
# END: test_advanced_scrape
