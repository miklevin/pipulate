#!/usr/bin/env python3
"""
Extract Blog Posts from README
=============================

This script extracts keyed sections from README.md and converts them into 
standalone blog post drafts for Pipulate.com.

Usage:
    python extract_blog_posts.py --key universal-api-pattern
    python extract_blog_posts.py --key durable-vs-ephemeral  
    python extract_blog_posts.py --all
"""

import re
import argparse
from pathlib import Path
from datetime import datetime

def extract_keyed_section(content, key):
    """Extract a section based on its key comment."""
    # Pattern: <!-- key: section-name -->
    pattern = rf'<!-- key: {re.escape(key)} -->(.*?)(?=<!-- key: \w+|$)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        section_content = match.group(1).strip()
        return section_content
    return None

def find_all_keys(content):
    """Find all key comments in the content."""
    pattern = r'<!-- key: ([\w-]+) -->'
    matches = re.findall(pattern, content)
    return matches

def extract_title_from_section(section_content):
    """Extract the title from a section (first heading)."""
    lines = section_content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('###'):
            return line[3:].strip()
        elif line.startswith('##'):
            return line[2:].strip()
        elif line.startswith('#'):
            return line[1:].strip()
    return "Untitled"

def create_blog_post(key, section_content, output_dir):
    """Create a blog post file from a section."""
    title = extract_title_from_section(section_content)
    
    # Generate filename
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}-{key}.md"
    
    # Create blog post content
    blog_content = f"""---
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d')}
excerpt: "Extracted from Pipulate README philosophical framework"
tags: [pipulate, philosophy, architecture, local-first]
---

{section_content}

---

*This post is part of the Pipulate philosophical framework. See the [complete README](https://github.com/miklevin/pipulate) for full context.*
"""

    # Write to file
    output_path = output_dir / filename
    output_path.write_text(blog_content)
    print(f"Created: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Extract blog posts from README')
    parser.add_argument('--key', help='Extract specific key section')
    parser.add_argument('--all', action='store_true', help='Extract all keyed sections')
    parser.add_argument('--output', default='blog_drafts', help='Output directory')
    
    args = parser.parse_args()
    
    # Read README
    readme_path = Path(__file__).parent.parent.parent / 'README.md'
    if not readme_path.exists():
        print(f"README not found at {readme_path}")
        return
    
    content = readme_path.read_text()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    if args.all:
        # Extract all sections
        keys = find_all_keys(content)
        print(f"Found {len(keys)} keyed sections:")
        for key in keys:
            print(f"  - {key}")
            section = extract_keyed_section(content, key)
            if section:
                create_blog_post(key, section, output_dir)
    
    elif args.key:
        # Extract specific section
        section = extract_keyed_section(content, args.key)
        if section:
            create_blog_post(args.key, section, output_dir)
            print(f"Extracted section: {args.key}")
        else:
            print(f"Key not found: {args.key}")
            print("Available keys:")
            for key in find_all_keys(content):
                print(f"  - {key}")
    
    else:
        # List available keys
        keys = find_all_keys(content)
        print(f"Available keys ({len(keys)}):")
        for key in keys:
            print(f"  - {key}")

if __name__ == '__main__':
    main() 