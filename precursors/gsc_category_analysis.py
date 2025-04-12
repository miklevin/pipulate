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

    # First, establish L1-L2 relationships based on keyword similarity
    l1_clusters = hierarchy.get(1, [])
    l2_clusters = hierarchy.get(2, [])
    l3_clusters = hierarchy.get(3, [])

    # Track which L2s are assigned to L1s
    assigned_l2_ids = set()

    # For each L1 cluster, find related L2s based on keyword overlap
    l1_children = defaultdict(list)
    for l1 in l1_clusters:
        l1_keywords = set(k.lower() for k in l1['keywords'])
        for l2 in l2_clusters:
            l2_keywords = set(k.lower() for k in l2['keywords'])
            # Calculate similarity score based on keyword overlap
            overlap = len(l1_keywords & l2_keywords)
            if overlap > 0:  # If there's any keyword overlap
                l1_children[l1['id']].append((l2, overlap))
                assigned_l2_ids.add(l2['id'])  # Track this L2 as assigned
    
    # Sort L2s by overlap score within each L1
    for l1_id in l1_children:
        l1_children[l1_id].sort(key=lambda x: x[1], reverse=True)

    # Print L1 clusters and their related L2s
    for i, l1 in enumerate(l1_clusters):
        is_last_l1 = (i == len(l1_clusters) - 1)
        l1_prefix = "└── " if is_last_l1 else "├── "
        l1_child_prefix = "    " if is_last_l1 else "│   "

        # Format L1 cluster name
        name = " & ".join(l1['keywords'][:2])
        name = name[:50] + "..." if len(name) > 50 else name
        
        print(f"{l1_prefix}[L1] {name} ({l1['size']} posts, {l1['impressions']:,} impressions)")

        # Print top posts under L1
        related_l2s = l1_children.get(l1['id'], [])
        l1_posts = [url for url in l1['urls'] if url not in 
                   [url for l2, _ in related_l2s for url in l2['urls']]]

        for j, url in enumerate(l1_posts[:3]):
            is_last_post = (j == len(l1_posts[:3]) - 1) and not related_l2s
            post_prefix = l1_child_prefix + ("└── " if is_last_post else "├── ")
            
            # Get post title and number
            title = posts_df[posts_df['url'] == url]['title'].iloc[0]
            title = title[:60] + "..." if len(title) > 60 else title
            post_num = post_numbers.get(url, '?')
            
            print(f"{post_prefix}#{post_num}: {title}")
            print(f"{l1_child_prefix}{'    '}{url}")

        # Print related L2 clusters
        for k, (l2, overlap) in enumerate(related_l2s):
            is_last_l2 = (k == len(related_l2s) - 1)
            l2_prefix = l1_child_prefix + ("└── " if is_last_l2 else "├── ")
            l2_child_prefix = l1_child_prefix + ("    " if is_last_l2 else "│   ")

            # Format L2 cluster name
            name = " & ".join(l2['keywords'][:2])
            name = name[:50] + "..." if len(name) > 50 else name
            
            print(f"{l2_prefix}[L2] {name} ({l2['size']} posts, {l2['impressions']:,} impressions)")

            # Print top posts under L2
            for m, url in enumerate(l2['urls'][:3]):
                is_last_post = (m == len(l2['urls'][:3]) - 1)
                post_prefix = l2_child_prefix + ("└── " if is_last_post else "├── ")
                
                # Get post title and number
                title = posts_df[posts_df['url'] == url]['title'].iloc[0]
                title = title[:60] + "..." if len(title) > 60 else title
                post_num = post_numbers.get(url, '?')
                
                print(f"{post_prefix}#{post_num}: {title}")
                print(f"{l2_child_prefix}{'    '}{url}")

    # Find orphaned L2s (those not assigned to any L1)
    orphaned_l2s = [l2 for l2 in l2_clusters if l2['id'] not in assigned_l2_ids]
    
    if orphaned_l2s:
        print("\n└── [Uncategorized L2s]")
        for i, l2 in enumerate(orphaned_l2s):
            is_last = (i == len(orphaned_l2s) - 1)
            prefix = "    └── " if is_last else "    ├── "
            name = " & ".join(l2['keywords'][:2])
            print(f"{prefix}{name} ({l2['size']} posts, {l2['impressions']:,} impressions)")

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