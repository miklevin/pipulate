# secretsauce.py
# This module contains the implementation details for the Faquillizer workflow.

# All necessary imports are handled here, keeping the notebook clean.
from pipulate import pip
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import pandas as pd
import getpass
from io import StringIO

# These constants define the names for our data steps in the pipulate job.
API_KEY_STEP = "api_key"
URL_LIST_STEP = "url_list"
RAW_DATA_STEP = "raw_data"
AI_INSIGHTS_STEP = "ai_insights"
FINAL_DATAFRAME_STEP = "final_dataframe"
EXPORT_FILE_STEP = "export_file_path"

def setup_google_ai(job: str):
    """Handles getting, storing, and configuring the Google AI API key."""
    api_key = pip.get(job, API_KEY_STEP)
    if not api_key:
        try:
            api_key = getpass.getpass("Enter your Google AI API Key: ")
            pip.set(job, API_KEY_STEP, api_key)
            print("✅ API Key received and stored for this session.")
        except Exception as e:
            print(f"❌ Could not get API key: {e}")
            return
    if api_key:
        genai.configure(api_key=api_key)
        print("✅ Google AI configured successfully.")

def fetch_titles(job: str):
    """Fetches titles for all URLs in the job's list, skipping completed ones."""
    urls_to_process = pip.get(job, URL_LIST_STEP, [])
    processed_data = pip.get(job, RAW_DATA_STEP, [])
    processed_urls = {item.get('url') for item in processed_data}

    print(f"🔄 Fetching titles... {len(processed_urls)} of {len(urls_to_process)} URLs already complete.")
    for url in urls_to_process:
        if url in processed_urls:
            continue
        try:
            print(f"  -> Fetching {url}...")
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "No Title Found"
            processed_data.append({'url': url, 'title': title.strip()})
            pip.set(job, RAW_DATA_STEP, processed_data) # Save progress!
            processed_urls.add(url)
        except Exception as e:
            print(f"❌ Failed to process {url}: {e}")
    print("✅ Title fetching complete.")

def get_ai_insights(job: str):
    """Generates AI insights for each piece of raw data, skipping completed ones."""
    raw_data = pip.get(job, RAW_DATA_STEP, [])
    ai_insights = pip.get(job, AI_INSIGHTS_STEP, [])
    processed_titles = {item.get('title') for item in ai_insights}

    print(f"🧠 Generating AI insights... {len(processed_titles)} of {len(raw_data)} items already complete.")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # Updated model
        for item in raw_data:
            title = item.get('title')
            if title in processed_titles:
                continue
            try:
                print(f"  -> Analyzing title: '{title}'...")
                # This is where a user would customize their prompt!
                prompt = f"Based on the webpage title '{title}', what is the likely primary topic? Be concise and clear."
                response = model.generate_content(prompt)
                ai_insights.append({'title': title, 'topic': response.text.strip()})
                pip.set(job, AI_INSIGHTS_STEP, ai_insights) # Save progress!
                processed_titles.add(title)
            except Exception as e:
                print(f"❌ AI insight failed for '{title}': {e}")
    except Exception as e:
        print(f"❌ Could not initialize AI model. Is your API key correct? Error: {e}")
    print("✅ AI insights generated.")

def display_results(job: str):
    """Merges all data, styles it into a DataFrame, and displays it."""
    print("📊 Preparing final results table...")
    processed_data = pip.get(job, RAW_DATA_STEP, [])
    ai_insights = pip.get(job, AI_INSIGHTS_STEP, [])

    if not processed_data:
        print("No data to display. Please run the 'fetch_titles' step first.")
        return

    df_raw = pd.DataFrame(processed_data)
    df_final = df_raw

    if ai_insights:
        df_ai = pd.DataFrame(ai_insights)
        df_final = pd.merge(df_raw, df_ai, on="title", how="left")

    styled_df = df_final.style.set_properties(**{
        'text-align': 'left', 'white-space': 'pre-wrap',
    }).set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'left'), ('font-weight', 'bold')]},
    ]).hide(axis="index")

    display(styled_df)
    pip.set(job, FINAL_DATAFRAME_STEP, df_final.to_json(orient='records'))

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
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) if max_length < 80 else 80
                worksheet.column_dimensions[column_letter].width = adjusted_width
        pip.set(job, EXPORT_FILE_STEP, output_filename)
        print(f"✅ Success! Data exported to '{output_filename}'")
    except Exception as e:
        print(f"❌ Failed to export to Excel: {e}")
