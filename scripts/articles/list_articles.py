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

def get_post_order(posts_dir=POSTS_DIRECTORY, chronological=True):
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
            meta_description = front_matter.get('meta_description', '')

            posts_data.append({
                'path': filepath,
                'date': post_date,
                'sort_order': sort_order,
                'meta_description': meta_description
            })

        except (ValueError, yaml.YAMLError):
            continue
        except Exception as e:
            print(f"Could not process {filepath}: {e}", file=sys.stderr)

    sorted_posts = sorted(
        posts_data,
        key=lambda p: (p['date'], p['sort_order']),
        reverse=False
    )

    for i, post in enumerate(sorted_posts):
        post['index'] = i

    if not chronological:
        sorted_posts.reverse()

    return sorted_posts

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="List Jekyll posts. Default is chronological (oldest first) with tokens and meta descriptions."
    )
    # --- CHANGE: Reinstated flags but changed their behavior ---
    parser.add_argument(
        '-t', '--no-tokens',
        action='store_false',
        dest='tokens',
        help='Do not calculate and display token counts.'
    )
    parser.add_argument(
        '-m', '--no-meta',
        action='store_false',
        dest='meta',
        help='Do not display meta descriptions.'
    )
    parser.add_argument(
        '-r', '--reverse',
        action='store_true',
        help='List in reverse chronological order (newest first).'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Only display file paths (implies --no-tokens and --no-meta).'
    )
    parser.set_defaults(tokens=True, meta=True)
    args = parser.parse_args()

    is_chronological = not args.reverse
    ordered_posts = get_post_order(chronological=is_chronological)

    # Determine what to show based on flags
    show_tokens = args.tokens
    show_meta = args.meta
    if args.quiet:
        show_tokens = False
        show_meta = False

    order_description = "chronological (oldest first)" if is_chronological else "reverse chronological (newest first)"
    print(f"Posts in {order_description} order:")

    if show_tokens:
        print("Calculating token counts for all files, this may take a moment...", file=sys.stderr)
        file_data = []
        for post in ordered_posts:
            filepath = post['path']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                token_count = count_tokens(content)
                # --- CHANGE 1: Add sort_order to the dictionary ---
                file_data.append({'path': filepath, 'tokens': token_count, 'meta_description': post['meta_description'], 'index': post['index'], 'sort_order': post['sort_order']})
            except Exception as e:
                print(f"[{post.get('index', ''):>3}:{post.get('sort_order', '')}] {filepath}  # Error: Could not read file - {e}", file=sys.stderr)
                file_data.append({'path': filepath, 'tokens': 0, 'meta_description': post['meta_description'], 'index': post['index'], 'sort_order': post['sort_order']})

        grand_total_tokens = sum(item['tokens'] for item in file_data)
        print("", file=sys.stderr)

        ascending_total = 0
        descending_total = grand_total_tokens

        for item in file_data:
            ascending_total += item['tokens']
            # --- CHANGE 2: Update the print format to include sort_order ---
            print(f"[{item['index']:>3}:{item['sort_order']}] {item['path']}  # {item['tokens']:,} tokens ({ascending_total:,} / {descending_total:,} total)")
            if show_meta and item['meta_description']:
                print(f"      └─ {item['meta_description']}")
            descending_total -= item['tokens']
    else: # Simple path output (quiet mode, or if --no-tokens is used)
        for post in ordered_posts:
            # --- CHANGE 3: Update the print format to include sort_order ---
            print(f"[{post['index']:>3}:{post['sort_order']}] {post['path']}")
            if show_meta and post['meta_description']:
                print(f"      └─ {post['meta_description']}")