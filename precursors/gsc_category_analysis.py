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

# --- Configuration ---

# GSC Property URL (e.g., "sc-domain:example.com" or "https://www.example.com/")
SITE_URL = "sc-domain:mikelev.in"
# Base URL of your website (used to convert absolute GSC URLs to relative paths)
BASE_URL = "https://mikelev.in"

# --- Topology Parameters ---
# These parameters affect how the site hierarchy is structured

# Maximum number of L1 (top-level) categories
# Higher values create a flatter structure, lower values push more into L2
MAX_L1_CATEGORIES = 20

# Minimum impressions required for a cluster to be considered for L1
# Higher values push low-traffic topics into L2/L3
MIN_IMPRESSIONS_FOR_L1 = 50

# K-means clustering parameters
NUM_CLUSTERS = 20        # Initial number of clusters to create
MIN_CLUSTER_SIZE = 3     # Minimum posts required to form a cluster
MAX_KEYWORDS_PER_CLUSTER = 5  # Number of keywords to represent each cluster

# Keyword relationship thresholds
KEYWORD_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity to consider keywords related
MIN_KEYWORD_FREQUENCY = 2    # Minimum times a keyword must appear to be considered
MAX_KEYWORD_NGRAM = 3       # Maximum words in a keyword phrase

# Display parameters
MAX_TITLE_LENGTH = 60       # Truncate titles longer than this
INDENT_SPACES = 4           # Number of spaces for each tree level

# --- End Configuration ---

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
    """Suggest a hierarchical organization of clusters.
    
    Args:
        clusters_df: DataFrame with columns: id, urls, size, keywords, impressions
    
    Returns:
        Dictionary mapping level numbers to lists of cluster dictionaries
    """
    levels = defaultdict(list)
    
    # Sort clusters by impressions (descending)
    sorted_clusters = clusters_df.sort_values('impressions', ascending=False)
    
    # Assign clusters to levels based on impressions and size
    for _, cluster in sorted_clusters.iterrows():
        cluster_dict = cluster.to_dict()  # Convert Series to dict
        if cluster['impressions'] >= MIN_IMPRESSIONS_FOR_L1:
            if len(levels[1]) < MAX_L1_CATEGORIES:
                levels[1].append(cluster_dict)
            else:
                levels[2].append(cluster_dict)
        else:
            levels[2].append(cluster_dict)
    
    return levels

def print_post(url, prefix, indent, posts_df, post_numbers):
    """Helper to print a post with consistent indentation.
    
    Tree Formatting Rules:
    1. Regular list items use ├── for both title and URL lines
    2. For items that terminate a list:
       - The title line uses ├── to maintain the vertical line for the URL
       - The URL line uses └── to properly terminate the list
    3. Vertical lines (│) must be continuous throughout the tree
    4. Each level's indentation is 4 spaces
    5. URLs are indented 4 spaces after their tree character
    """
    matching_posts = posts_df[posts_df['url'] == url]
    if matching_posts.empty:
        return False
    
    title = matching_posts['title'].iloc[0]
    if title is None:
        title = "Untitled Post"
    else:
        title = str(title)[:MAX_TITLE_LENGTH] + "..." if len(str(title)) > MAX_TITLE_LENGTH else str(title)
    
    post_num = post_numbers.get(url, '?')
    
    # Tree Character Rules:
    # - If this is a list terminator (prefix ends with └──)
    #   - Title line gets ├── to maintain vertical line for URL
    #   - URL line keeps └── to terminate the list
    # - Otherwise, both lines use the same prefix (├── for continuation)
    if prefix.endswith("└── "):
        title_prefix = prefix.replace("└── ", "├── ")  # Keep vertical line for URL
        url_prefix = prefix  # Keep terminator for URL
    else:
        title_prefix = url_prefix = prefix  # Same prefix for both lines
    
    print(f"{title_prefix}#{post_num}: {title}")
    print(f"{url_prefix}    {url}")
    return True

def print_tree(hierarchy, posts_df):
    """Print hierarchy in tree format with proper nesting and article numbers.
    
    Tree Structure Rules:
    1. Each level is indented 4 spaces from its parent
    2. Vertical lines (│) must be continuous for all child items
    3. Last item in a list uses └── to terminate
    4. Penultimate items must use ├── to maintain vertical lines
    5. URLs are always children of their titles
    6. Missing/invalid posts are filtered out entirely
    """
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

    # Print L1 clusters and their hierarchy
    for l1_num, l1 in enumerate(l1_clusters, 1):
        is_last_l1 = (l1_num == len(l1_clusters))
        # Use ├── for last L1 since we have Uncategorized section after it
        l1_prefix = "├── "
        # Always use │ for child indentation
        l1_indent = "│   "

        # Print L1 cluster
        name = " & ".join(l1['keywords'][:2])
        name = name[:50] + "..." if len(name) > 50 else name
        print(f"{l1_prefix}[L1.{l1_num:02d}] {name} ({l1['size']} posts, {l1['impressions']:,} impressions)")

        # Get L2s for this L1
        l2_children = l1_to_l2.get(l1['id'], [])
        
        # Get L1's direct posts (not in any L2)
        l1_posts = [url for url in l1['urls'] if url not in 
                   [url for l2, _ in l2_children for url in l2['urls']]]

        # Print L1's direct posts
        valid_l1_posts = []
        for url in l1_posts:
            if url in posts_df['url'].values:
                valid_l1_posts.append(url)
        
        for j, url in enumerate(valid_l1_posts):
            is_last_post = (j == len(valid_l1_posts) - 1) and not l2_children
            post_prefix = l1_indent + ("└── " if is_last_post else "├── ")
            print_post(url, post_prefix, l1_indent + "    ", posts_df, post_numbers)

        # Print L2 clusters and their content
        for l2_num, (l2, _) in enumerate(l2_children, 1):
            is_last_l2 = (l2_num == len(l2_children))
            l2_prefix = l1_indent + ("└── " if is_last_l2 else "├── ")
            l2_indent = l1_indent + ("    " if is_last_l2 else "│   ")

            # Print L2 cluster
            name = " & ".join(l2['keywords'][:2])
            name = name[:50] + "..." if len(name) > 50 else name
            print(f"{l2_prefix}[L2.{l1_num:02d}.{l2_num:02d}] {name} ({l2['size']} posts, {l2['impressions']:,} impressions)")

            # Get L3s for this L2
            l3_children = l2_to_l3.get(l2['id'], [])
            
            # Get L2's direct posts (not in any L3)
            l2_posts = [url for url in l2['urls'] if url not in 
                       [url for l3, _ in l3_children for url in l3['urls']]]

            # Print L2's direct posts
            valid_l2_posts = []
            for url in l2_posts:
                if url in posts_df['url'].values:
                    valid_l2_posts.append(url)

            # Print L2's direct posts
            for m, url in enumerate(valid_l2_posts):
                is_last_post = (m == len(valid_l2_posts) - 1) and not l3_children
                post_prefix = l2_indent + ("└── " if is_last_post else "├── ")
                print_post(url, post_prefix, l2_indent + "    ", posts_df, post_numbers)

            # Print L3 clusters and their content
            for n, (l3, _) in enumerate(l3_children):
                is_last_l3 = (n == len(l3_children) - 1)
                l3_prefix = l2_indent + ("└── " if is_last_l3 else "├── ")
                l3_indent = l2_indent + ("    " if is_last_l3 else "│   ")

                # Print L3 cluster
                name = " & ".join(l3['keywords'][:2])
                name = name[:50] + "..." if len(name) > 50 else name
                print(f"{l3_prefix}[L3.{l1_num:02d}.{l2_num:02d}.{n+1:02d}] {name} ({l3['size']} posts, {l3['impressions']:,} impressions)")

                # Print L3's posts
                for p, url in enumerate(l3['urls']):  # Removed [:3] to show all posts
                    is_last_post = (p == len(l3['urls']) - 1)
                    post_prefix = l3_indent + ("└── " if is_last_post else "├── ")
                    print_post(url, post_prefix, l3_indent + "    ", posts_df, post_numbers)

    # Print orphaned clusters
    orphaned_l2s = [l2 for l2 in l2_clusters if l2['id'] not in assigned_l2_ids]
    orphaned_l3s = [l3 for l3 in l3_clusters if l3['id'] not in assigned_l3_ids]
    
    if orphaned_l2s or orphaned_l3s:
        print("└── [Uncategorized]")
        if orphaned_l2s:
            print("    └── [L2 Clusters]")
            for i, l2 in enumerate(orphaned_l2s):
                is_last = (i == len(orphaned_l2s) - 1)
                prefix = "        └── " if is_last else "        ├── "
                name = " & ".join(l2['keywords'][:2])
                print(f"{prefix}[L2.U.{i+1:02d}] {name} ({l2['size']} posts, {l2['impressions']:,} impressions)")
                
                # Print all posts for each orphaned L2 cluster
                valid_urls = []
                for url in l2['urls']:
                    if url in posts_df['url'].values:
                        valid_urls.append(url)
                
                for j, url in enumerate(valid_urls):
                    is_last_post = (j == len(valid_urls) - 1)
                    post_prefix = "        │   " if not is_last else "            "
                    if is_last_post:
                        post_prefix += "└── "  # Last post gets └── for both title and URL
                    else:
                        post_prefix += "├── "
                    print_post(url, post_prefix, post_prefix + "    ", posts_df, post_numbers)
        
        if orphaned_l3s:
            print("    └── [L3 Clusters]")
            for i, l3 in enumerate(orphaned_l3s):
                is_last = (i == len(orphaned_l3s) - 1)
                prefix = "        └── " if is_last else "        ├── "
                name = " & ".join(l3['keywords'][:2])
                print(f"{prefix}[L3.U.{i+1:02d}] {name} ({l3['size']} posts, {l3['impressions']:,} impressions)")
                
                # Print all posts for each orphaned L3 cluster
                for j, url in enumerate(l3['urls']):  # Removed [:3] to show all posts
                    is_last_post = (j == len(l3['urls']) - 1)
                    post_prefix = "        │   " if not is_last else "            "
                    if is_last_post:
                        post_prefix += "└── "  # Last post gets └── for both title and URL
                    else:
                        post_prefix += "├── "
                    print_post(url, post_prefix, post_prefix + "    ", posts_df, post_numbers)

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

def evaluate_topology(hierarchy, posts_df):
    """Score a topology based on key metrics.
    
    Scoring Criteria:
    1. Coverage: % of posts assigned to categories (-1 for each unassigned)
    2. Balance: Standard deviation of posts per category (lower is better)
    3. Coherence: Average keyword similarity within categories (higher is better)
    4. Depth: Ratio of L1 to L2 categories (prefer more L1s)
    5. Traffic: % of total impressions in L1 categories (higher is better)
    """
    total_posts = len(posts_df)
    total_impressions = sum(cluster['impressions'] for level in hierarchy.values() 
                          for cluster in level)
    
    # Coverage score (0-100)
    assigned_posts = len(set(url for level in hierarchy.values() 
                           for cluster in level for url in cluster['urls']))
    coverage_score = (assigned_posts / total_posts) * 100
    
    # Balance score (0-100)
    posts_per_category = [len(cluster['urls']) for level in hierarchy.values() 
                         for cluster in level]
    balance_score = 100 - (np.std(posts_per_category) * 10)  # Lower std = higher score
    
    # Coherence score (0-100)
    coherence_scores = []
    for level in hierarchy.values():
        for cluster in level:
            keywords = [k.lower() for k in cluster['keywords']]
            if len(keywords) > 1:
                similarities = []
                for i in range(len(keywords)):
                    for j in range(i + 1, len(keywords)):
                        similarity = len(set(keywords[i].split()) & 
                                      set(keywords[j].split())) / \
                                  len(set(keywords[i].split()) | 
                                      set(keywords[j].split()))
                        similarities.append(similarity)
                if similarities:
                    coherence_scores.append(np.mean(similarities))
    coherence_score = np.mean(coherence_scores) * 100 if coherence_scores else 0
    
    # Depth score (0-100)
    l1_count = len(hierarchy.get(1, []))
    l2_count = len(hierarchy.get(2, []))
    depth_score = (l1_count / (l1_count + l2_count)) * 100 if l1_count + l2_count > 0 else 0
    
    # Traffic score (0-100)
    l1_impressions = sum(cluster['impressions'] for cluster in hierarchy.get(1, []))
    traffic_score = (l1_impressions / total_impressions) * 100 if total_impressions > 0 else 0
    
    # Weighted total score (0-100)
    weights = {
        'coverage': 0.3,
        'balance': 0.2,
        'coherence': 0.2,
        'depth': 0.1,
        'traffic': 0.2
    }
    
    total_score = (
        coverage_score * weights['coverage'] +
        balance_score * weights['balance'] +
        coherence_score * weights['coherence'] +
        depth_score * weights['depth'] +
        traffic_score * weights['traffic']
    )
    
    return {
        'total_score': total_score,
        'coverage_score': coverage_score,
        'balance_score': balance_score,
        'coherence_score': coherence_score,
        'depth_score': depth_score,
        'traffic_score': traffic_score,
        'l1_count': l1_count,
        'l2_count': l2_count,
        'assigned_posts': assigned_posts,
        'total_posts': total_posts
    }

def optimize_parameters(posts_df, gsc_df):
    """Find optimal parameters through grid search."""
    param_ranges = {
        'MAX_L1_CATEGORIES': range(10, 31, 5),      # 10 to 30 step 5
        'MIN_IMPRESSIONS_FOR_L1': range(25, 76, 25), # 25 to 75 step 25
        'NUM_CLUSTERS': range(15, 31, 5),           # 15 to 30 step 5
        'KEYWORD_SIMILARITY_THRESHOLD': [0.2, 0.3, 0.4, 0.5]
    }
    
    best_score = 0
    best_params = None
    best_hierarchy = None
    results = []
    
    total_combinations = (
        len(param_ranges['MAX_L1_CATEGORIES']) *
        len(param_ranges['MIN_IMPRESSIONS_FOR_L1']) *
        len(param_ranges['NUM_CLUSTERS']) *
        len(param_ranges['KEYWORD_SIMILARITY_THRESHOLD'])
    )
    
    print(f"\nOptimizing parameters ({total_combinations} combinations)...")
    combination_count = 0
    
    for max_l1 in param_ranges['MAX_L1_CATEGORIES']:
        for min_imp in param_ranges['MIN_IMPRESSIONS_FOR_L1']:
            for num_clusters in param_ranges['NUM_CLUSTERS']:
                for sim_threshold in param_ranges['KEYWORD_SIMILARITY_THRESHOLD']:
                    combination_count += 1
                    print(f"\rTesting combination {combination_count}/{total_combinations}", end="")
                    
                    # Set parameters
                    global MAX_L1_CATEGORIES, MIN_IMPRESSIONS_FOR_L1, NUM_CLUSTERS, KEYWORD_SIMILARITY_THRESHOLD
                    MAX_L1_CATEGORIES = max_l1
                    MIN_IMPRESSIONS_FOR_L1 = min_imp
                    NUM_CLUSTERS = num_clusters
                    KEYWORD_SIMILARITY_THRESHOLD = sim_threshold
                    
                    # Generate and evaluate topology
                    clusters_df = cluster_content(posts_df, gsc_df)
                    hierarchy = suggest_hierarchy(clusters_df)
                    scores = evaluate_topology(hierarchy, posts_df)
                    
                    results.append({
                        'params': {
                            'MAX_L1_CATEGORIES': max_l1,
                            'MIN_IMPRESSIONS_FOR_L1': min_imp,
                            'NUM_CLUSTERS': num_clusters,
                            'KEYWORD_SIMILARITY_THRESHOLD': sim_threshold
                        },
                        'scores': scores
                    })
                    
                    if scores['total_score'] > best_score:
                        best_score = scores['total_score']
                        best_params = results[-1]['params']
                        best_hierarchy = hierarchy
    
    print("\n\nOptimization Results")
    print("===================")
    print("\nBest Parameters:")
    for param, value in best_params.items():
        print(f"{param}: {value}")
    
    print("\nBest Scores:")
    for metric, score in results[-1]['scores'].items():
        if isinstance(score, (int, float)):
            print(f"{metric}: {score:.1f}")
        else:
            print(f"{metric}: {score}")
    
    return best_params, best_hierarchy

def main():
    """Main execution function."""
    print("Loading GSC keyword data...")
    gsc_df = load_gsc_keywords()
    print(f"Loaded {len(gsc_df)} GSC keyword entries")
    
    print("\nExtracting YAML front matter...")
    posts_df = extract_yaml_front_matter()
    print(f"Processed {len(posts_df)} Jekyll posts")
    
    # Add parameter optimization
    print("\nOptimizing topology parameters...")
    best_params, best_hierarchy = optimize_parameters(posts_df, gsc_df)
    
    # Use best parameters for final output
    global MAX_L1_CATEGORIES, MIN_IMPRESSIONS_FOR_L1, NUM_CLUSTERS, KEYWORD_SIMILARITY_THRESHOLD
    MAX_L1_CATEGORIES = best_params['MAX_L1_CATEGORIES']
    MIN_IMPRESSIONS_FOR_L1 = best_params['MIN_IMPRESSIONS_FOR_L1']
    NUM_CLUSTERS = best_params['NUM_CLUSTERS']
    KEYWORD_SIMILARITY_THRESHOLD = best_params['KEYWORD_SIMILARITY_THRESHOLD']
    
    print("\nGenerating final topology with optimized parameters...")
    print_tree(best_hierarchy, posts_df)

if __name__ == "__main__":
    main() 