#!/usr/bin/env python3
import csv
import urllib.parse
import os
import sys
import json
import argparse
from pathlib import Path
import common

def get_active_permalinks(navgraph_path):
    """Recursively extracts all active permalinks from the knowledge graph."""
    active = set()
    if not navgraph_path.exists():
        print(f"⚠️ Warning: {navgraph_path} not found. Proceeding without collision check.")
        return active
        
    with open(navgraph_path, 'r', encoding='utf-8') as f:
        nav = json.load(f)
        
    def traverse(node):
        if 'permalink' in node:
            active.add(node['permalink'])
            active.add(node['permalink'].rstrip('/'))
        for child in node.get('children_hubs', []): traverse(child)
        for child in node.get('children_articles', []):
            if 'permalink' in child:
                active.add(child['permalink'])
                active.add(child['permalink'].rstrip('/'))
                
    traverse(nav)
    return active

def build_nginx_map(csv_input_path, map_output_path, navgraph_path):
    print(f"🛠️ Forging Nginx map from {csv_input_path.name}...")
    
    if not csv_input_path.exists():
        print(f"❌ Error: {csv_input_path} not found.")
        return

    active_permalinks = get_active_permalinks(navgraph_path)
    valid_rows = []
    
    # Pass 1: Read, Clean, and Filter the CSV
    with open(csv_input_path, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        for row in reader:
            if len(row) != 2:
                continue # Skip hallucinated or malformed rows
                
            old_url = row[0].strip()
            new_url = row[1].strip()

            # THE BOUNCER: Collision Filter (Protect living hubs/articles)
            check_url = old_url if old_url.endswith('/') else old_url + '/'
            if check_url in active_permalinks or old_url in active_permalinks:
                print(f"🛡️ Active Collision Avoided (Pruning): {old_url}")
                continue # Drop the row entirely, it will be deleted from the CSV

            # THE BOUNCER: 80/20 Encoding Filter
            if '%' in old_url or '%' in new_url:
                print(f"⚠️ Dropping encoded URL: {old_url[:30]}...")
                continue

            # THE BOUNCER: Artifact Filter
            if 'attachment' in old_url.lower():
                print(f"⚠️ Dropping artifact URL: {old_url[:30]}...")
                continue
                
            # THE BOUNCER: Asset & Parameter Filter
            if '?' in old_url or old_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
                print(f"⚠️ Dropping asset/parameter URL: {old_url[:30]}...")
                continue
                
            # Deterministic sanitization
            safe_old_url = urllib.parse.quote(old_url, safe='/%')

            # THE BOUNCER: Preserve Nginx default map_hash_bucket_size
            if len(safe_old_url) > 120 or len(new_url) > 120:
                print(f"⚠️ Dropping oversized URL (>{len(safe_old_url)} chars): {safe_old_url[:30]}...")
                continue
                
            # Keep it in our valid ledger memory
            valid_rows.append([old_url, new_url])

    # Pass 2: Rewrite the CSV Ledger (Self-Pruning, No Blank Lines)
    with open(csv_input_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(valid_rows)
    print(f"🧹 Pruned and synchronized raw CSV ledger.")

    # Pass 3: Hardened Nginx Map Compilation with built-in Linter
    print("🛡️  Linting and compiling pure hash ledger...")
    
    corrupted_lines = 0
    external_noise = 0
    
    with open(map_output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("# PURE HASH LEDGER: /dead-path /living-path\n")
        
        seen_keys = set()
        for old_url, new_url in valid_rows:
            # 1. THE RIGOROUS GATEKEEPER (The grep -E '[;~^]' test)
            # If these characters exist, the line is a threat to the service.
            if any(char in old_url or char in new_url for char in [';', '~', '^']):
                print(f"❌ Corrupted data blocked: {old_url}")
                corrupted_lines += 1
                continue

            # 2. DOMAIN ISOLATION (The YouTube/External Filter)
            # Purge hallucinations or external URLs that bleed into the CSV.
            if "http" in old_url or "www." in old_url:
                print(f"🚫 External domain blocked: {old_url}")
                external_noise += 1
                continue

            # 3. NORMALIZE FOR NGINX $uri
            # Ensure keys and values are clean absolute paths.
            key = old_url.strip().rstrip('/')
            if not key.startswith('/'): key = '/' + key
            
            val = new_url.strip()
            if not val.startswith('/'): val = '/' + val
            
            # 4. DUPLICATE & CIRCULAR PROTECTION
            if key in seen_keys:
                continue 
            if key == val:
                print(f"⚠️  Circular skip: {key}")
                continue

            # 5. THE PURE WRITE
            # Exactly one space, no semicolon, no regex.
            outfile.write(f"{key} {val}\n")
            seen_keys.add(key)

    if corrupted_lines or external_noise:
        print(f"🧹 Cleanup complete: {corrupted_lines} corrupted and {external_noise} external entries purged.")

    print(f"✅ Nginx map forged successfully at {map_output_path.name}")

def main():
    parser = argparse.ArgumentParser(description="Generate Nginx Redirect Map")
    common.add_target_argument(parser)
    args = parser.parse_args()

    # Dynamically resolve target repository paths
    posts_dir = common.get_target_path(args)
    repo_root = posts_dir.parent
    
    csv_input_path = repo_root / '_raw_map.csv'
    map_output_path = repo_root / '_redirects.map'
    navgraph_path = repo_root / 'navgraph.json'

    build_nginx_map(csv_input_path, map_output_path, navgraph_path)

if __name__ == "__main__":
    main()
