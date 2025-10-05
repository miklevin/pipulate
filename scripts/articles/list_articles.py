#!/usr/bin/env python3
# list_posts_chronologically_config.py
import os
import sys
import yaml
import argparse
import tiktoken
from datetime import datetime

# NOTE: This script now requires 'tiktoken' and 'PyYAML'.
# Install them with: pip install tiktoken PyYAML

# --- CONFIGURATION ---
# Hardwire the absolute path to your posts directory here.
POSTS_DIRECTORY = "/home/mike/repos/MikeLev.in/_posts"

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Counts the number of tokens in a text string using the tiktoken library."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback for any tiktoken errors
        return 0

def get_post_order(posts_dir=POSTS_DIRECTORY, reverse_order=False):
    """
    Parses Jekyll posts from a specified directory, sorts them by date
    and 'sort_order', and returns an ordered list of full absolute file paths.
    """
    posts_data = []
    
    if not os.path.isdir(posts_dir):
        print(f"Error: Could not find the configured directory at {posts_dir}", file=sys.stderr)
        return []

    for filename in os.listdir(posts_dir):
        filepath = os.path.join(posts_dir, filename)
        
        if not os.path.isfile(filepath) or not filename.endswith(('.md', '.markdown')):
            continue

        try:
            date_str = filename[:10]
            post_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.startswith('---'):
                front_matter = {}
            else:
                parts = content.split('---', 2)
                front_matter = yaml.safe_load(parts[1]) or {}

            sort_order = int(front_matter.get('sort_order', 0))
            
            posts_data.append({
                'path': filepath,
                'date': post_date,
                'sort_order': sort_order
            })

        except (ValueError, yaml.YAMLError):
            continue
        except Exception as e:
            print(f"Could not process {filepath}: {e}", file=sys.stderr)

    # The 'reverse' flag of the sorted function is controlled by the new argument
    sorted_posts = sorted(
        posts_data, 
        key=lambda p: (p['date'], p['sort_order']), 
        reverse=not reverse_order
    )

    return [post['path'] for post in sorted_posts]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="List Jekyll posts in chronological order, optionally with token counts."
    )
    parser.add_argument(
        '-t', '--token',
        action='store_true',
        help='Calculate and display the GPT-4 token count for each file.'
    )
    parser.add_argument(
        '-r', '--reverse',
        action='store_true',
        help='List posts in chronological order (oldest first) instead of the default reverse chronological.'
    )
    args = parser.parse_args()

    # Pass the reverse flag to the function
    ordered_files = get_post_order(reverse_order=args.reverse)
    
    order_description = "chronological (oldest first)" if args.reverse else "reverse chronological (newest first)"
    print(f"Posts in {order_description} order (full paths):")
    
    if args.token:
        # --- PASS 1: Pre-calculate all token counts ---
        print("Calculating token counts for all files, this may take a moment...", file=sys.stderr)
        file_data = []
        for filepath in ordered_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                token_count = count_tokens(content)
                file_data.append({'path': filepath, 'tokens': token_count})
            except Exception as e:
                print(f"{filepath}  # Error: Could not read file - {e}", file=sys.stderr)
                # Add a record with 0 tokens to avoid breaking the logic
                file_data.append({'path': filepath, 'tokens': 0})
        
        grand_total_tokens = sum(item['tokens'] for item in file_data)
        print("", file=sys.stderr) # Add a newline after the status message

        # --- PASS 2: Print formatted output with dual cumulative counts ---
        ascending_total = 0
        descending_total = grand_total_tokens

        for item in file_data:
            filepath = item['path']
            token_count = item['tokens']
            
            ascending_total += token_count
            
            # Print the new format with individual, ascending, and descending counts
            print(f"{filepath}  # {token_count:,} tokens ({ascending_total:,} / {descending_total:,} total)")
            
            # Decrement the descending total for the next iteration
            descending_total -= token_count

    else:
        # If --token is not used, just print the file paths as before
        for filepath in ordered_files:
            print(filepath)