#!/usr/bin/env python3
"""
Analyzes GSC data and Jekyll post front matter to suggest optimal site categories.

This script:
1. Reads GSC data from both top keywords and top movers
2. Extracts YAML front matter from all Jekyll posts
3. Performs clustering analysis to suggest initial categories
4. Outputs recommended category structure with prioritized content placement

Required pip installs:
    pip install pyyaml pandas numpy scikit-learn
"""

import os
import sys
import json
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
JEKYLL_ROOT = os.path.join(os.path.dirname(__file__), '../../MikeLev.in')
POSTS_DIR = os.path.join(JEKYLL_ROOT, '_posts')
GSC_DATA_DIR = os.path.join(JEKYLL_ROOT, '_data')
GSC_KEYWORDS_FILE = os.path.join(GSC_DATA_DIR, 'gsc_top_keywords.json')

# Thresholds
TARGET_CLUSTERS = 20  # Initial target number of clusters
MIN_POSTS_PER_CATEGORY = 3  # Minimum posts to form a category
MAX_POSTS_PER_CATEGORY = 15  # Maximum posts before splitting
MIN_IMPRESSIONS_FOR_PRIORITY = 50  # Minimum impressions for Level 1

def load_gsc_keywords():
    """Load and process GSC keyword data."""
    with open(GSC_KEYWORDS_FILE) as f:
        data = json.load(f)
    
    # Convert to DataFrame for easier analysis
    rows = []
    for url, keywords in data.items():
        for kw in keywords:
            rows.append({
                'url': url,
                'query': kw['query'],
                'impressions': kw['impressions'],
                'clicks': kw['clicks']
            })
    return pd.DataFrame(rows)

def extract_yaml_front_matter():
    """Extract YAML front matter from all Jekyll posts."""
    front_matter = []
    for post in Path(POSTS_DIR).glob('*.md'):
        with open(post) as f:
            content = f.read()
            if content.startswith('---'):
                # Extract YAML between first two '---' markers
                yaml_text = content.split('---')[1]
                try:
                    data = yaml.safe_load(yaml_text)
                    data['file'] = post.name
                    data['url'] = data.get('permalink', '/' + post.stem + '/')
                    front_matter.append(data)
                except yaml.YAMLError as e:
                    print(f"Error parsing YAML in {post}: {e}")
    return pd.DataFrame(front_matter)

def combine_keywords(row):
    """Combine all keyword-related fields from YAML."""
    keywords = []
    for field in ['meta_keywords', 'keywords', 'tags']:
        if field in row and row[field]:
            if isinstance(row[field], str):
                keywords.extend(row[field].split(','))
            elif isinstance(row[field], list):
                keywords.extend(row[field])
    return ' '.join(k.strip() for k in keywords if k)

def cluster_content(posts_df, gsc_df):
    """Cluster content based on keywords and GSC data."""
    # Combine manual keywords and GSC queries
    content_keywords = defaultdict(list)
    
    # Add manual keywords
    for _, row in posts_df.iterrows():
        url = row['url']
        keywords = combine_keywords(row)
        if keywords:
            content_keywords[url].append(keywords)
    
    # Add GSC queries with weights based on impressions
    for _, row in gsc_df.iterrows():
        url = row['url']
        # Repeat query based on log of impressions to give weight
        weight = max(1, int(np.log2(row['impressions'] + 1)))
        content_keywords[url].extend([row['query']] * weight)
    
    # Create document vectors
    documents = [' '.join(kws) for kws in content_keywords.values()]
    urls = list(content_keywords.keys())
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', 
                               ngram_range=(1, 2),
                               max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # Determine optimal number of clusters
    n_clusters = min(TARGET_CLUSTERS, len(documents) // MIN_POSTS_PER_CATEGORY)
    n_clusters = max(n_clusters, len(documents) // MAX_POSTS_PER_CATEGORY)
    
    # Cluster using KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(tfidf_matrix)
    
    # Create cluster summary
    cluster_data = []
    for cluster_id in range(n_clusters):
        cluster_urls = [urls[i] for i, c in enumerate(clusters) if c == cluster_id]
        cluster_keywords = []
        cluster_impressions = 0
        
        # Get top GSC queries for cluster
        cluster_gsc = gsc_df[gsc_df['url'].isin(cluster_urls)]
        if not cluster_gsc.empty:
            top_queries = cluster_gsc.groupby('query')['impressions'].sum() \
                                   .sort_values(ascending=False)
            cluster_keywords.extend(top_queries.head().index)
            cluster_impressions = top_queries.sum()
        
        # Get manual keywords for cluster
        cluster_posts = posts_df[posts_df['url'].isin(cluster_urls)]
        manual_keywords = ' '.join(cluster_posts['meta_keywords'].dropna())
        if manual_keywords:
            cluster_keywords.extend(manual_keywords.split(',')[:5])
        
        # Get the centroid terms for this cluster
        if len(cluster_keywords) < 3:  # If we need more keywords
            centroid = kmeans.cluster_centers_[cluster_id]
            feature_names = vectorizer.get_feature_names_out()
            top_indices = centroid.argsort()[-5:][::-1]
            centroid_terms = [feature_names[i] for i in top_indices]
            cluster_keywords.extend(centroid_terms)
        
        cluster_data.append({
            'id': cluster_id,
            'urls': cluster_urls,
            'size': len(cluster_urls),
            'keywords': list(set(cluster_keywords)),
            'impressions': cluster_impressions
        })
    
    return pd.DataFrame(cluster_data)

def suggest_hierarchy(clusters_df):
    """Suggest hierarchical organization based on clusters."""
    # Sort clusters by impressions (descending)
    sorted_clusters = clusters_df.sort_values('impressions', ascending=False)
    
    # Initialize levels
    levels = {
        1: [],  # Top level categories
        2: [],  # Second level
        3: []   # Third level
    }
    
    # Assign clusters to levels based on size and impressions
    for _, cluster in sorted_clusters.iterrows():
        if cluster['impressions'] >= MIN_IMPRESSIONS_FOR_PRIORITY:
            if len(levels[1]) < 10:  # Keep top level limited
                levels[1].append(cluster)
            else:
                levels[2].append(cluster)
        else:
            if cluster['size'] >= MIN_POSTS_PER_CATEGORY:
                levels[2].append(cluster)
            else:
                levels[3].append(cluster)
    
    return levels

def print_tree(hierarchy, posts_df):
    """Print hierarchy in tree format with proper nesting and article numbers."""
    print("\nSite Hierarchy Tree")
    print("==================\n")
    print(".")  # Root node

    # Get master index order
    sorted_posts = posts_df.sort_values('date', ascending=False)
    post_numbers = {row['url']: idx + 1 for idx, row in sorted_posts.iterrows()}

    # Get clusters for each level
    l1_clusters = hierarchy.get(1, [])
    l2_clusters = hierarchy.get(2, [])
    l3_clusters = hierarchy.get(3, [])

    # Track assigned clusters
    assigned_l2_ids = set()
    assigned_l3_ids = set()

    # Build relationship maps based on keyword overlap
    def calculate_overlap(parent_keywords, child_keywords):
        parent_set = set(k.lower() for k in parent_keywords)
        child_set = set(k.lower() for k in child_keywords)
        return len(parent_set & child_set)

    # Map L1 to L2 relationships
    l1_to_l2 = defaultdict(list)
    for l1 in l1_clusters:
        for l2 in l2_clusters:
            overlap = calculate_overlap(l1['keywords'], l2['keywords'])
            if overlap > 0:
                l1_to_l2[l1['id']].append((l2, overlap))
                assigned_l2_ids.add(l2['id'])

    # Map L2 to L3 relationships
    l2_to_l3 = defaultdict(list)
    for l2 in l2_clusters:
        for l3 in l3_clusters:
            overlap = calculate_overlap(l2['keywords'], l3['keywords'])
            if overlap > 0:
                l2_to_l3[l2['id']].append((l3, overlap))
                assigned_l3_ids.add(l3['id'])

    # Sort relationships by overlap score
    for l1_id in l1_to_l2:
        l1_to_l2[l1_id].sort(key=lambda x: x[1], reverse=True)
    for l2_id in l2_to_l3:
        l2_to_l3[l2_id].sort(key=lambda x: x[1], reverse=True)

    def print_post(url, prefix, indent):
        """Helper to print a post with consistent indentation."""
        title = posts_df[posts_df['url'] == url]['title'].iloc[0]
        title = title[:60] + "..." if len(title) > 60 else title
        post_num = post_numbers.get(url, '?')
        print(f"{prefix}#{post_num}: {title}")
        # Keep the same tree structure for URL, just indent it more
        url_prefix = prefix.replace("└──", "└── ").replace("├──", "├── ")
        print(f"{url_prefix}    {url}")

    # Print L1 clusters and their hierarchy
    for i, l1 in enumerate(l1_clusters):
        is_last_l1 = (i == len(l1_clusters) - 1)
        l1_prefix = "└── " if is_last_l1 else "├── "
        l1_indent = "    " if is_last_l1 else "│   "

        # Print L1 cluster
        name = " & ".join(l1['keywords'][:2])
        name = name[:50] + "..." if len(name) > 50 else name
        print(f"{l1_prefix}[L1] {name} ({l1['size']} posts, {l1['impressions']:,} impressions)")

        # Get L2s for this L1
        l2_children = l1_to_l2.get(l1['id'], [])
        
        # Get L1's direct posts (not in any L2)
        l1_posts = [url for url in l1['urls'] if url not in 
                   [url for l2, _ in l2_children for url in l2['urls']]]

        # Print L1's direct posts
        for j, url in enumerate(l1_posts[:3]):
            is_last_post = (j == len(l1_posts[:3]) - 1) and not l2_children
            post_prefix = l1_indent + ("└── " if is_last_post else "├── ")
            print_post(url, post_prefix, l1_indent + "    ")

        # Print L2 clusters and their content
        for k, (l2, _) in enumerate(l2_children):
            is_last_l2 = (k == len(l2_children) - 1)
            l2_prefix = l1_indent + ("└── " if is_last_l2 else "├── ")
            l2_indent = l1_indent + ("    " if is_last_l2 else "│   ")

            # Print L2 cluster
            name = " & ".join(l2['keywords'][:2])
            name = name[:50] + "..." if len(name) > 50 else name
            print(f"{l2_prefix}[L2] {name} ({l2['size']} posts, {l2['impressions']:,} impressions)")

            # Get L3s for this L2
            l3_children = l2_to_l3.get(l2['id'], [])
            
            # Get L2's direct posts (not in any L3)
            l2_posts = [url for url in l2['urls'] if url not in 
                       [url for l3, _ in l3_children for url in l3['urls']]]

            # Print L2's direct posts
            for m, url in enumerate(l2_posts[:3]):
                is_last_post = (m == len(l2_posts[:3]) - 1) and not l3_children
                post_prefix = l2_indent + ("└── " if is_last_post else "├── ")
                print_post(url, post_prefix, l2_indent + "    ")

            # Print L3 clusters and their content
            for n, (l3, _) in enumerate(l3_children):
                is_last_l3 = (n == len(l3_children) - 1)
                l3_prefix = l2_indent + ("└── " if is_last_l3 else "├── ")
                l3_indent = l2_indent + ("    " if is_last_l3 else "│   ")

                # Print L3 cluster
                name = " & ".join(l3['keywords'][:2])
                name = name[:50] + "..." if len(name) > 50 else name
                print(f"{l3_prefix}[L3] {name} ({l3['size']} posts, {l3['impressions']:,} impressions)")

                # Print L3's posts
                for p, url in enumerate(l3['urls'][:3]):
                    is_last_post = (p == len(l3['urls'][:3]) - 1)
                    post_prefix = l3_indent + ("└── " if is_last_post else "├── ")
                    print_post(url, post_prefix, l3_indent + "    ")

    # Print orphaned clusters
    orphaned_l2s = [l2 for l2 in l2_clusters if l2['id'] not in assigned_l2_ids]
    orphaned_l3s = [l3 for l3 in l3_clusters if l3['id'] not in assigned_l3_ids]
    
    if orphaned_l2s or orphaned_l3s:
        print("\n└── [Uncategorized]")
        if orphaned_l2s:
            print("    ├── [L2 Clusters]")
            for i, l2 in enumerate(orphaned_l2s):
                is_last = (i == len(orphaned_l2s) - 1) and not orphaned_l3s
                prefix = "    │   └── " if is_last else "    │   ├── "
                name = " & ".join(l2['keywords'][:2])
                print(f"{prefix}{name} ({l2['size']} posts, {l2['impressions']:,} impressions)")
        
        if orphaned_l3s:
            print("    └── [L3 Clusters]")
            for i, l3 in enumerate(orphaned_l3s):
                is_last = (i == len(orphaned_l3s) - 1)
                prefix = "        └── " if is_last else "        ├── "
                name = " & ".join(l3['keywords'][:2])
                print(f"{prefix}{name} ({l3['size']} posts, {l3['impressions']:,} impressions)")

    # Print coverage statistics
    total_urls = set()
    for level in hierarchy.values():
        for cluster in level:
            total_urls.update(cluster['urls'])
    
    print("\nCoverage Statistics")
    print("==================")
    print(f"Total unique posts assigned: {len(total_urls)}")
    print(f"Total posts in master index: {len(posts_df)}")
    unassigned = len(posts_df) - len(total_urls)
    print(f"Unassigned posts: {unassigned} ({unassigned/len(posts_df)*100:.1f}%)")

def main():
    """Main execution function."""
    print("Loading GSC keyword data...")
    gsc_df = load_gsc_keywords()
    print(f"Loaded {len(gsc_df)} GSC keyword entries")
    
    print("\nExtracting YAML front matter...")
    posts_df = extract_yaml_front_matter()
    print(f"Processed {len(posts_df)} Jekyll posts")
    
    print("\nClustering content...")
    clusters_df = cluster_content(posts_df, gsc_df)
    print(f"Identified {len(clusters_df)} potential categories")
    
    print("\nSuggesting hierarchy...")
    hierarchy = suggest_hierarchy(clusters_df)
    
    # Print tree visualization
    print_tree(hierarchy, posts_df)
    
    # Print summary stats
    print("\nSummary Statistics")
    print("=================")
    total_impressions = sum(cluster['impressions'] for level in hierarchy.values() for cluster in level)
    print(f"Total Categories: {sum(len(clusters) for clusters in hierarchy.values())}")
    print(f"Total Posts: {len(posts_df)}")
    print(f"Total Impressions: {total_impressions:,}")
    for level, clusters in sorted(hierarchy.items()):
        level_impressions = sum(cluster['impressions'] for cluster in clusters)
        print(f"Level {level}: {len(clusters)} categories, {level_impressions:,} impressions " + 
              f"({level_impressions/total_impressions*100:.1f}% of total)")

if __name__ == "__main__":
    main() 