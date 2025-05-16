#!/usr/bin/env python3
"""
Generates a categories.md page from GSC category analysis results.
This creates a hierarchical category overview with:
- Category descriptions
- Post counts and impressions
- Top posts per category
- GSC performance metrics
"""

import os
import sys
from pathlib import Path
from gsc_category_analysis import (
    load_gsc_keywords,
    extract_yaml_front_matter,
    cluster_content,
    suggest_hierarchy,
    optimize_parameters
)
import pandas as pd

def format_category_description(keywords, posts_df, gsc_df):
    """Generate a category description from its keywords and content."""
    # Get unique keywords, removing duplicates and similar terms
    unique_keywords = list(set(keywords))
    
    # Get top performing posts for this category
    top_posts = []
    for url in posts_df['url']:
        if url in gsc_df['url'].values:
            # Group by URL and sum impressions
            url_impressions = gsc_df[gsc_df['url'] == url]['impressions'].sum()
            if pd.notna(url_impressions):  # Check for valid impression data
                title = posts_df[posts_df['url'] == url]['title'].iloc[0]
                if pd.notna(title):  # Check for valid title
                    top_posts.append((int(url_impressions), title, url))
    
    # Sort by impressions (first tuple element)
    top_posts.sort(key=lambda x: x[0], reverse=True)
    top_3_posts = top_posts[:3]
    
    # Format description
    desc = f"Articles about {', '.join(unique_keywords[:3])}"
    if len(unique_keywords) > 3:
        desc += f" and related topics"
    desc += "."
    
    return desc

def generate_categories_page(hierarchy, posts_df, gsc_df):
    """Generate the categories.md content."""
    content = []
    
    # Add YAML front matter
    content.extend([
        "---",
        "title: Site Categories",
        "permalink: /categories/",
        "description: Hierarchical overview of site content organized by topic and search performance.",
        "layout: page",
        "---",
        "",
        "# Site Categories",
        "",
        "_An AI-assisted categorization of site content based on topic clustering and search performance._",
        "",
        "## Top-Level Categories",
        ""
    ])
    
    # Add each L1 category
    for level, clusters in sorted(hierarchy.items()):
        if level == 1:  # Only process L1 categories
            for cluster in sorted(clusters, key=lambda x: x['impressions'], reverse=True):
                name = " & ".join(cluster['keywords'][:2])
                desc = format_category_description(cluster['keywords'], posts_df, gsc_df)
                
                content.extend([
                    f"### {name}",
                    "",
                    f"_{desc}_",
                    "",
                    f"**Posts:** {cluster['size']} • **Impressions:** {cluster['impressions']:,}",
                    "",
                    "Top Articles:",
                    ""
                ])
                
                # Add top 3 posts by impressions
                urls = cluster['urls']
                top_posts = []
                for url in urls:
                    if url in posts_df['url'].values and url in gsc_df['url'].values:
                        title = posts_df[posts_df['url'] == url]['title'].iloc[0]
                        if pd.notna(title):  # Check for valid title
                            impressions = gsc_df[gsc_df['url'] == url]['impressions'].sum()
                            if pd.notna(impressions):  # Check for valid impressions
                                top_posts.append((int(impressions), title, url))
                
                # Sort by impressions
                top_posts.sort(key=lambda x: x[0], reverse=True)
                for imp, title, url in top_posts[:3]:
                    content.append(f"- [{title}]({url}) _{imp:,} impressions_")
                content.append("")
                
                # Add any L2 subcategories
                l2_children = [c for c in hierarchy.get(2, []) 
                             if any(kw in c['keywords'] for kw in cluster['keywords'])]
                if l2_children:
                    content.append("Subcategories:")
                    content.append("")
                    for l2 in sorted(l2_children, key=lambda x: x['impressions'], reverse=True):
                        l2_name = " & ".join(l2['keywords'][:2])
                        content.append(f"- {l2_name} ({l2['size']} posts, {l2['impressions']:,} impressions)")
                    content.append("")
    
    # Add summary statistics
    total_impressions = sum(cluster['impressions'] for level in hierarchy.values() 
                          for cluster in level)
    total_categories = sum(len(clusters) for clusters in hierarchy.values())
    
    content.extend([
        "## Statistics",
        "",
        f"- **Total Categories:** {total_categories}",
        f"- **Total Posts:** {len(posts_df)}",
        f"- **Total Impressions:** {total_impressions:,}",
        "",
        "### Level Distribution",
        "",
        "| Level | Categories | Posts | Impressions | % of Traffic |",
        "|-------|------------|--------|-------------|--------------|"
    ])
    
    for level in sorted(hierarchy.keys()):
        clusters = hierarchy[level]
        level_posts = sum(len(c['urls']) for c in clusters)
        level_impressions = sum(c['impressions'] for c in clusters)
        traffic_percent = (level_impressions / total_impressions * 100) if total_impressions > 0 else 0
        content.append(f"| {level} | {len(clusters)} | {level_posts} | {level_impressions:,} | {traffic_percent:.1f}% |")
    
    content.extend([
        "",
        "_Categories are determined through AI clustering of content keywords and Google Search Console performance data._",
        "",
        "---",
        "",
        "_Generated on " + pd.Timestamp.now().strftime("%Y-%m-%d") + "_"
    ])
    
    return "\n".join(content)

def main():
    """Main execution function."""
    print("Loading GSC keyword data...")
    gsc_df = load_gsc_keywords()
    print(f"Loaded {len(gsc_df)} GSC keyword entries")
    
    print("\nExtracting YAML front matter...")
    posts_df = extract_yaml_front_matter()
    print(f"Processed {len(posts_df)} Jekyll posts")
    
    print("\nOptimizing topology parameters...")
    best_params, best_hierarchy = optimize_parameters(posts_df, gsc_df)
    
    print("\nGenerating categories.md...")
    content = generate_categories_page(best_hierarchy, posts_df, gsc_df)
    
    # Write to file
    output_path = os.path.join(os.path.dirname(__file__), '../../MikeLev.in/categories.md')
    with open(output_path, 'w') as f:
        f.write(content)
    print(f"\nCategories page written to: {output_path}")

if __name__ == "__main__":
    main() 