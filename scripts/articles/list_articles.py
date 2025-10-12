#!/usr/bin/env python3
# list_posts_chronologically_config.py
import os
import sys
import yaml
import argparse
import tiktoken
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich import box

# NOTE: This script now requires 'tiktoken', 'PyYAML', and 'rich'.
# Install them with: pip install tiktoken PyYAML rich

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

    # This sort is crucial for both the main list and the contiguity analysis
    sorted_posts = sorted(
        posts_data,
        key=lambda p: (p['date'], p['sort_order']),
        reverse=False
    )

    for i, post in enumerate(sorted_posts):
        post['index'] = i

    if not chronological:
        # Reverse for display only after the canonical order is established
        return sorted_posts[::-1]

    return sorted_posts

def analyze_sort_order_contiguity(posts: list) -> list:
    """
    Analyzes the sort_order of posts grouped by day to find gaps, duplicates,
    and sequences not starting at 1.
    """
    anomalies = []
    posts_by_day = defaultdict(list)

    # Group posts by date
    for post in posts:
        posts_by_day[post['date']].append(post['sort_order'])

    for date, orders in sorted(posts_by_day.items()):
        # The list is already sorted by sort_order from get_post_order
        unique_orders = sorted(list(set(orders)))

        # Check for duplicates
        if len(orders) != len(unique_orders):
            dupes = sorted([o for o in unique_orders if orders.count(o) > 1])
            anomalies.append({
                "date": date,
                "type": "[bold red]Duplicate[/bold red]",
                "details": f"Duplicate value(s): {dupes}",
                "sequence": str(orders)
            })

        # Check if sequence starts with 1
        if unique_orders and unique_orders[0] != 1:
            anomalies.append({
                "date": date,
                "type": "[bold yellow]Starts Late[/bold yellow]",
                "details": f"Sequence starts at {unique_orders[0]} instead of 1.",
                "sequence": str(orders)
            })

        # Check for gaps
        if unique_orders:
            expected_sequence = set(range(1, unique_orders[-1] + 1))
            gaps = sorted(list(expected_sequence - set(unique_orders)))
            if gaps:
                anomalies.append({
                    "date": date,
                    "type": "[bold cyan]Gap[/bold cyan]",
                    "details": f"Missing value(s): {gaps}",
                    "sequence": str(orders)
                })

    return anomalies

def print_contiguity_report(anomalies: list):
    """Prints the sort_order contiguity report using rich.table."""
    console = Console()
    console.print("\n" + "="*50)
    console.print("[bold bright_blue]Sort Order Contiguity Report[/bold bright_blue]")
    console.print("="*50)

    if not anomalies:
        console.print("✅ [bold green]All Clear![/bold green] Sort order is contiguous and correct for all days.")
        return

    table = Table(title="Daily Sort Order Anomalies", box=box.ROUNDED, show_lines=True)
    table.add_column("Date", style="magenta", justify="left")
    table.add_column("Anomaly Type", style="cyan", justify="left")
    table.add_column("Details", style="white", justify="left")
    table.add_column("Observed Sequence", style="yellow", justify="left")

    for anomaly in anomalies:
        table.add_row(
            str(anomaly["date"]),
            anomaly["type"],
            anomaly["details"],
            anomaly["sequence"]
        )
    console.print(table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="List Jekyll posts. Default is chronological (oldest first) with tokens and meta descriptions."
    )
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

    # Get posts sorted canonically first for analysis
    canonical_posts = get_post_order(chronological=True)

    # Determine display order based on user flag
    display_posts = canonical_posts[::-1] if args.reverse else canonical_posts

    # Determine what to show based on flags
    show_tokens = args.tokens and not args.quiet
    show_meta = args.meta and not args.quiet

    order_description = "reverse chronological (newest first)" if args.reverse else "chronological (oldest first)"
    print(f"Posts in {order_description} order:")

    if show_tokens:
        print("Calculating token counts for all files, this may take a moment...", file=sys.stderr)
        file_data = []
        for post in display_posts: # Iterate over display order
            filepath = post['path']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                token_count = count_tokens(content)
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
            print(f"[{item['index']:>3}:{item['sort_order']}] {item['path']}  # {item['tokens']:,} tokens ({ascending_total:,} / {descending_total:,} total)")
            if show_meta and item['meta_description']:
                print(f"      └─ {item['meta_description']}")
            descending_total -= item['tokens']
    else: # Simple path output
        for post in display_posts:
            print(f"[{post['index']:>3}:{post['sort_order']}] {post['path']}")
            if show_meta and post['meta_description']:
                print(f"      └─ {post['meta_description']}")

    # --- NEW: Run and print the contiguity report ---
    # The analysis is always run on the canonical (chronological) order
    sort_order_anomalies = analyze_sort_order_contiguity(canonical_posts)
    print_contiguity_report(sort_order_anomalies)
