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
    Parses Jekyll posts, sorts them by date and 'sort_order', and returns an
    ordered list of dictionaries, each containing post data.
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
            # Extract meta_description, default to an empty string if not found
            meta_description = front_matter.get('meta_description', '')

            posts_data.append({
                'path': filepath,
                'date': post_date,
                'sort_order': sort_order,
                'meta_description': meta_description # <-- New field added here
            })

        except (ValueError, yaml.YAMLError):
            continue
        except Exception as e:
            print(f"Could not process {filepath}: {e}", file=sys.stderr)

    sorted_posts = sorted(
        posts_data,
        key=lambda p: (p['date'], p['sort_order']),
        reverse=not reverse_order
    )
    # Return the full list of dictionaries now
    return sorted_posts

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="List Jekyll posts in chronological order, with optional token counts and meta descriptions."
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
    parser.add_argument(
        '-m', '--meta',
        action='store_true',
        help='Include the meta_description from the front matter in the output.'
    )
    args = parser.parse_args()

    ordered_posts = get_post_order(reverse_order=args.reverse)

    order_description = "chronological (oldest first)" if args.reverse else "reverse chronological (newest first)"
    print(f"Posts in {order_description} order:")

    if args.token:
        # --- PASS 1: Pre-calculate all token counts ---
        print("Calculating token counts for all files, this may take a moment...", file=sys.stderr)
        file_data = []
        for post in ordered_posts:
            filepath = post['path']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                token_count = count_tokens(content)
                # Carry the meta_description through
                file_data.append({'path': filepath, 'tokens': token_count, 'meta_description': post['meta_description']})
            except Exception as e:
                print(f"{filepath}  # Error: Could not read file - {e}", file=sys.stderr)
                file_data.append({'path': filepath, 'tokens': 0, 'meta_description': post['meta_description']})

        grand_total_tokens = sum(item['tokens'] for item in file_data)
        print("", file=sys.stderr)

        # --- PASS 2: Print formatted output ---
        ascending_total = 0
        descending_total = grand_total_tokens

        for item in file_data:
            ascending_total += item['tokens']
            print(f"{item['path']}  # {item['tokens']:,} tokens ({ascending_total:,} / {descending_total:,} total)")
            if args.meta and item['meta_description']:
                print(f"  └─ {item['meta_description']}") # Nicely formatted meta output
            descending_total -= item['tokens']

    else:
        # If --token is not used, just print the file paths and optionally meta
        for post in ordered_posts:
            print(post['path'])
            if args.meta and post['meta_description']:
                print(f"  └─ {post['meta_description']}") # Nicely formatted meta output