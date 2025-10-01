#!/usr/bin/env python3
# list_posts_chronologically_config.py
import os
import yaml
from datetime import datetime

# CONFIGURATION: Hardwire the absolute path to your posts directory here.
POSTS_DIRECTORY = "/home/mike/repos/MikeLev.in/_posts"

def get_post_order(posts_dir=POSTS_DIRECTORY):
    """
    Parses Jekyll posts from a specified directory, sorts them by date 
    and 'sort_order', and returns an ordered list of full absolute file paths.
    """
    posts_data = []
    
    # The script now uses the provided 'posts_dir' argument directly.
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

    sorted_posts = sorted(
        posts_data, 
        key=lambda p: (p['date'], p['sort_order']), 
        reverse=True
    )

    return [post['path'] for post in sorted_posts]

if __name__ == '__main__':
    # The function is called without arguments, so it uses the default
    # value from the POSTS_DIRECTORY configuration variable.
    ordered_files = get_post_order()
    print("Posts in intended chronological order (full paths):")
    for filename in ordered_files:
        print(filename)