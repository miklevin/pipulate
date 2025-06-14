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

def get_bulk_field_tester_query(collection: str, fields: List[str]) -> Dict[str, Any]:
    """Creates a BQLv2 query to test multiple fields at once with proper collection prefixes."""
    # Add collection prefix to each field for the query
    dimensions = [f"{collection}.{field}" for field in fields if not field.startswith('search_console')]
    
    # Correct BQL structure - no 'limit' field allowed
    query = {
        "collections": [collection],
        "query": {
            "dimensions": dimensions,
            "metrics": []  # Empty metrics array is required
        }
    }
    
    return query

async def check_field_availability(org: str, project: str, analysis: str, headers: Dict) -> Dict[str, List[str]]:
    """Checks which fields from FIELDS_TO_CHECK are available using bulk queries."""
    print("🕵️  Starting Botify API field exploration...")
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    crawl_collection = f"crawl.{analysis}"
    available_fields = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n--- Testing Crawl Collection: {crawl_collection} ---")
        
        # Test all crawl fields together in batches to avoid overwhelming the API
        all_crawl_fields = FIELDS_TO_CHECK['Crawl & Indexing'] + FIELDS_TO_CHECK['Content & Performance']
        
        # Try smaller batches to identify which fields work
        batch_size = 3
        for i in range(0, len(all_crawl_fields), batch_size):
            batch_fields = all_crawl_fields[i:i+batch_size]
            query = get_bulk_field_tester_query(crawl_collection, batch_fields)
            
            try:
                print(f"  Testing batch: {batch_fields}")
                response = await client.post(url, headers=headers, json=query)
                if response.status_code == 200:
                    print(f"  ✅ Batch successful")
                    # Add the successful fields with full collection prefix
                    for field in batch_fields:
                        available_fields.append(f"{crawl_collection}.{field}")
                else:
                    print(f"  ❌ Batch failed (status: {response.status_code})")
                    # Try individual fields in this batch
                    for field in batch_fields:
                        individual_query = get_bulk_field_tester_query(crawl_collection, [field])
                        try:
                            individual_response = await client.post(url, headers=headers, json=individual_query)
                            if individual_response.status_code == 200:
                                print(f"    ✅ {field}")
                                available_fields.append(f"{crawl_collection}.{field}")
                            else:
                                print(f"    ❌ {field} (status: {individual_response.status_code})")
                        except Exception as e:
                            print(f"    ❓ {field} (Error: {e})")
                            
            except Exception as e:
                print(f"  ❓ Batch error: {e}")

        print("\n--- Testing Search Console Integration ---")
        try:
            analysis_date = datetime.strptime(analysis, '%Y%m%d')
            period_start = (analysis_date - timedelta(days=30)).strftime('%Y-%m-%d')
            period_end = analysis_date.strftime('%Y-%m-%d')
            
            # Test GSC with a minimal query structure
            gsc_query = {
                "collections": [crawl_collection, "search_console"],
                "query": {
                    "dimensions": [f"{crawl_collection}.url"],
                    "metrics": FIELDS_TO_CHECK['Google Search Console']
                },
                "periods": [[period_start, period_end]]
            }
            response = await client.post(url, headers=headers, json=gsc_query)
            if response.status_code == 200:
                print("  ✅ GSC Collection is available.")
                available_fields.extend(FIELDS_TO_CHECK['Google Search Console'])
            else:
                print(f"  ❌ GSC Collection not available (status: {response.status_code})")
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  ❓ GSC Collection (Error: {e})")
            
    return {"dimensions": available_fields}

async def generate_enhanced_node_attributes(org: str, project: str, analysis: str, available_fields: Dict[str, List[str]], headers: Dict):
    """Downloads a CSV of all available node attributes."""
    all_fields = available_fields.get('dimensions', [])
    if not all_fields:
        print("\nNo available dimensions found. Cannot generate node attributes file.")
        return

    print(f"\n💾 Generating enhanced node attributes CSV with {len(all_fields)} fields...")
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # Separate dimensions and metrics based on field names
    dimensions = [field for field in all_fields if not any(gsc in field for gsc in ['impressions', 'clicks', 'ctr', 'position'])]
    metrics = [field for field in all_fields if any(gsc in field for gsc in ['impressions', 'clicks', 'ctr', 'position'])]
    
    # Build collections list from the field prefixes
    collections = list(set([field.split('.')[0] + '.' + field.split('.')[1] for field in dimensions]))
    if metrics:
        collections.append("search_console")

    query_payload = {
        "collections": collections,
        "query": {
            "dimensions": dimensions,
            "metrics": metrics
        }
    }
    
    # Add periods if we have GSC metrics
    if metrics:
        analysis_date = datetime.strptime(analysis, '%Y%m%d')
        period_start = (analysis_date - timedelta(days=30)).strftime('%Y-%m-%d')
        period_end = analysis_date.strftime('%Y-%m-%d')
        query_payload["periods"] = [[period_start, period_end]]
        # Sort by the first available GSC metric
        query_payload["query"]["sort"] = [{"field": metrics[0], "order": "desc"}]

    print(f"Query payload: {json.dumps(query_payload, indent=2)}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=query_payload)
    
    if response.status_code != 200:
        print("❌ Data download failed.")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return

    data = response.json().get('results', [])
    
    if not data:
        print("⚠️  No data returned from query.")
        return
    
    records = []
    # Create simplified column names from the field names
    dim_cols = [field.split('.')[-1] for field in dimensions]
    met_cols = [field.split('.')[-1] for field in metrics]
    
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
    print(f"\nDataFrame Info:")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")
    print(f"\nColumn Names: {list(df.columns)}")
    if len(df) > 0:
        print(f"\nFirst few rows:\n{df.head(3).to_string()}")

async def main():
    """Main function to run the data explorer."""
    try:
        api_key = open(TOKEN_FILE).read().strip().splitlines()[0]
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        org, project, analysis = config['org'], config['project'], config['analysis']
        print(f"🔍 Exploring fields for: {org}/{project}/{analysis}")
    except Exception as e:
        print(f"❌ Could not load config or token file: {e}")
        return
        
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    available_fields = await check_field_availability(org, project, analysis, headers)
    
    if available_fields.get('dimensions'):
        await generate_enhanced_node_attributes(org, project, analysis, available_fields, headers)
    else:
        print("\n❌ No fields were found to be available. This might indicate:")
        print("  - Token permissions issue")
        print("  - Incorrect project/analysis configuration") 
        print("  - API endpoint or field naming changes")

if __name__ == "__main__":
    asyncio.run(main())