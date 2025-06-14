# helpers/botify/object_explorer.py
import os
import json
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

# --- Configuration ---
TOKEN_FILE = 'botify_token.txt'
# Ensure the config file is in the same directory as this script for consistency
CONFIG_FILE = Path(__file__).parent / 'config.json'

# --- Fields to Explore ---
# A curated list of potentially useful fields for visualization enhancement.
FIELDS_TO_CHECK = {
    'Crawl & Indexing': [
        'compliant.is_compliant', 'compliant.main_reason', 'compliant.detailed_reason',
        'http_code', 'inlinks_internal.nb.total', 'depth', 'sitemaps.present'
    ],
    'Content & Performance': [
        'metadata.title.content', 'metadata.title.len', 'content.body.word_count',
        'performance.first_byte', 'performance.load_time'
    ],
    'Google Search Console': [
        'search_console.period_0.count_impressions',
        'search_console.period_0.count_clicks',
        'search_console.period_0.ctr',
        'search_console.period_0.avg_position'
    ]
}

def get_field_tester_query(collection: str, field: str, is_metric: bool = False) -> Dict[str, Any]:
    """Creates a minimal BQLv2 query to test the existence of a single field."""
    query = {"limit": 1}
    if is_metric:
        query["metrics"] = [field]
    else:
        query["dimensions"] = [field]
        
    return {"collections": [collection], "query": query}

async def check_field_availability(org: str, project: str, analysis: str, headers: Dict) -> Dict[str, Dict[str, List[str]]]:
    """Systematically checks which fields from FIELDS_TO_CHECK are available."""
    print("🕵️  Starting Botify API field exploration...")
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    crawl_collection = f"crawl.{analysis}"
    available = {'dimensions': [], 'metrics': []}

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n--- Checking Collection: {crawl_collection} ---")
        for field in FIELDS_TO_CHECK['Crawl & Indexing'] + FIELDS_TO_CHECK['Content & Performance']:
            # IMPORTANT FIX: Do NOT prepend collection name to field in the query object
            query = get_field_tester_query(crawl_collection, field)
            try:
                response = await client.post(url, headers=headers, json=query)
                if response.status_code == 200:
                    print(f"  ✅ {field}")
                    # Store the FULL field name for the final query
                    available['dimensions'].append(f"{crawl_collection}.{field}")
                else:
                    print(f"  ❌ {field} (status: {response.status_code})")
            except Exception as e:
                print(f"  ❓ {field} (Error: {e})")

        print("\n--- Checking Collection: search_console ---")
        try:
            analysis_date = datetime.strptime(analysis, '%Y%m%d')
            period_start = (analysis_date - timedelta(days=30)).strftime('%Y-%m-%d')
            period_end = analysis_date.strftime('%Y-%m-%d')
            
            # IMPORTANT FIX: use relative 'url' dimension for the crawl collection
            gsc_query = {
                "collections": [crawl_collection, "search_console"],
                "query": {"dimensions": ["url"], "metrics": FIELDS_TO_CHECK['Google Search Console'], "limit": 1},
                "periods": [[period_start, period_end]]
            }
            response = await client.post(url, headers=headers, json=gsc_query)
            if response.status_code == 200:
                print("  ✅ GSC Collection is available.")
                available['metrics'].extend(FIELDS_TO_CHECK['Google Search Console'])
            else:
                print(f"  ❌ GSC Collection not available (status: {response.status_code})")
        except Exception as e:
            print(f"  ❓ GSC Collection (Error: {e})")
            
    return available

async def generate_enhanced_node_attributes(org: str, project: str, analysis: str, available_fields: Dict[str, List[str]], headers: Dict):
    """Downloads a CSV of all available node attributes."""
    if not available_fields.get('dimensions'):
        print("\nNo available crawl dimensions found. Cannot generate node attributes file.")
        return

    print("\n💾 Generating enhanced node attributes CSV...")
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # Use the full field names that were verified
    dimensions = available_fields['dimensions']
    metrics = available_fields['metrics']
    
    collections = list(set([field.split('.')[0] for field in dimensions + metrics]))

    query_payload = {
        "collections": collections,
        "query": {
            "dimensions": dimensions,
            "metrics": metrics,
            "limit": 10000 
        }
    }
    
    if any(m.startswith("search_console") for m in metrics):
        analysis_date = datetime.strptime(analysis, '%Y%m%d')
        period_start = (analysis_date - timedelta(days=30)).strftime('%Y-%m-%d')
        period_end = analysis_date.strftime('%Y-%m-%d')
        query_payload["periods"] = [[period_start, period_end]]
        # Sort by the first available GSC metric
        query_payload["query"]["sort"] = [{"field": metrics[0], "order": "desc"}]

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=query_payload)
    
    if response.status_code != 200:
        print("❌ Data download failed.")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return

    data = response.json().get('results', [])
    
    records = []
    # Create column names from the last part of the field id
    dim_cols = [d.split('.')[-1] for d in dimensions]
    met_cols = [m.split('.')[-1] for m in metrics]
    
    for item in data:
        record = dict(zip(dim_cols, item.get('dimensions', [])))
        record.update(dict(zip(met_cols, item.get('metrics', []))))
        records.append(record)
    
    df = pd.DataFrame(records)
    
    output_dir = Path("helpers/botify/downloads")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{project}_{analysis}_enhanced_nodes.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Successfully saved enhanced node attributes to:\n   {output_file.resolve()}")
    print(f"\nDataFrame Preview:\n{df.head().to_markdown(index=False)}")

async def main():
    """Main function to run the data explorer."""
    try:
        api_key = open(TOKEN_FILE).read().strip().splitlines()[0]
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        org, project, analysis = config['org'], config['project'], config['analysis']
    except Exception as e:
        print(f"❌ Could not load config or token file: {e}")
        return
        
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    available_fields = await check_field_availability(org, project, analysis, headers)
    
    if any(available_fields.values()):
        await generate_enhanced_node_attributes(org, project, analysis, available_fields, headers)

if __name__ == "__main__":
    asyncio.run(main())