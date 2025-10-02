#!/usr/bin/env python3
# list_posts_chronologically_config.py
import os
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
        print(f"Error: Could not find the configured directory at {posts_dir}")
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
            print(f"Could not process {filepath}: {e}")

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
    # Add the new reverse argument
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
    
    # Initialize a variable to keep the running total
    cumulative_tokens = 0

    for filepath in ordered_files:
        if args.token:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                token_count = count_tokens(content)
                # Add the current file's tokens to the cumulative total
                cumulative_tokens += token_count
                
                # Print the new format with both individual and cumulative counts
                print(f"{filepath}  # {token_count:,} tokens ({cumulative_tokens:,} total)")
            except Exception as e:
                print(f"{filepath}  # Error: Could not read file - {e}")
        else:
            print(filepath)