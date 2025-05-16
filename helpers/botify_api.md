---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.17.1
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# What is Botify?

Botify is an enterprise SEO platform that crawls websites and provides detailed analytics about their technical SEO health. The Botify API allows you to:

- Access crawl data and site metrics
- Generate custom reports and analyses 
- Build automated SEO workflows
- Track site performance over time

## Authentication: Getting Started with the API

Before running any queries, you'll need to:

1. Get your API token from [Botify Account Settings](https://app.botify.com/account/)
2. Store it securely (we'll show you how)
3. Test the connection with a basic API call

## Secure Token Storage

**⚠️ SECURITY WARNING**: API tokens provide full access to your Botify account. Never:
- Commit tokens to version control
- Share notebooks with tokens
- Run token-using code on public platforms

For local development:

1. Create a `.gitignore` file if you don't have one
2. Add these lines:
```
botify_token.txt
config.json
.ipynb_checkpoints/
__pycache__/
```

3. If using Cursor IDE, also create a `.cursorignore` file with:
```
botify_token.txt
```

<!-- #region -->
# Introduction to BQL (Botify Query Language)

BQL is a specialized query language for accessing and analyzing website crawl data through the Botify API. This guide will help you understand how to effectively use BQL for website analysis and SEO insights.

## Core Capabilities
- **Data Extraction**: Query and analyze large-scale crawl datasets
- **Query Filtering**: Target specific page segments or URL attributes
- **Metric Creation**: Define and calculate custom analytics metrics
- **Site Segmentation**: Organize and categorize URLs by structural patterns

## Technical Requirements
Required dependencies:
- `httpx` library for API communication
- `pandas` for data manipulation
- Authentication files:
  - `botify_token.txt` for API authentication
  - `config.json` for project configuration

## Key Operations
- Execute API queries against crawl data
- Generate customized analytical reports
- Create data pipelines for site analysis
- Convert crawl data into actionable insights

## Query Structure
Every BQL query consists of four main components:
1. **Collections**: Source datasets for analysis
2. **Dimensions**: Data segmentation parameters
3. **Metrics**: Measurement criteria
4. **Sorting**: Result organization rules

### Example BQL Query

This example retrieves URL counts by page type:

```python
import httpx

# Define API variables
org = "your_organization_slug"
project = "your_project_slug"
collection = "your_collection_name"
api_key = "your_api_key_here"
url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

# BQL query payload
payload = {
    "collections": [collection],
    "query": {
        "dimensions": [{"field": "segments.pagetype.value"}],
        "metrics": [{"field": f"{collection}.count_urls_crawl"}],
        "sort": [
            {"type": "metrics", "index": 0, "order": "desc"},
            {"type": "dimensions", "index": 0, "order": "asc"}
        ]
    }
}

# Send POST request
response = httpx.post(url, headers=headers, json=payload)
response.raise_for_status()
print(response.json())
```
<!-- #endregion -->

```python
import httpx
from getpass import getpass

def validate_token(token):
    """Check if the Botify API token is valid and return the username if successful."""
    url = "https://api.botify.com/v1/authentication/profile"
    headers = {"Authorization": f"Token {token}"}
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        # Extract username if the token is valid
        user_data = response.json()
        username = user_data["data"]["username"]
        return username
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("Authentication failed: Invalid or expired token")
        else:
            print(f"API request failed: {e}")
        return None
    except httpx.RequestError as e:
        print(f"Request error: {e}")
        return None

# Define token file
token_file = "botify_token.txt"

# Attempt to read the token from the file
try:
    with open(token_file) as f:
        token = f.read().strip()
    username = validate_token(token)
    if username:
        print(f"Using saved token. Welcome, {username}!")
    else:
        print("Invalid saved token. Please provide a new token.")
        token = None
except FileNotFoundError:
    token = None
    print(f"No token file found at {token_file}")

# If no valid token, prompt once
if not token:
    print("\nTo get your API token, visit: https://app.botify.com/account")
    token = getpass("Enter your API token: ").strip()
    
    if token:
        username = validate_token(token)
        if username:
            with open(token_file, 'w') as f:
                f.write(token)
            print(f"API Token validated and saved. Welcome, {username}!")
        else:
            print("Token validation failed. Please try again later.")
    else:
        print("No token provided.")

print("Done. And remember, never let your browser save this token!")
```

**Sample Output**:

    Enter your API token or hit 'Esc 00' & Restart to quit (it's a Jupyter thing):  ········
    Invalid token, please try again.
    Enter your API token or hit 'Esc 00' & Restart to quit (it's a Jupyter thing):  ········
    API Token validated and saved. Welcome, michael.levin!
    Done. And remember, never let your browser save this token!

**Rationale**: Botify API-calls need access to your Botify API Token. We therefore retreive it smack it right down in the same folder where your script runs. This way, we can open it with a Python 1-liner, dump it into a global-scope `api_key` variable your functons can use anywhere. There's so much wrong with this except for the fact that it works every time. Don't deploy to production. Now go away or I shall taunt you a second time.


# Use API: How To Have Your First Initial Success With Botify API By Getting Username

```python
import httpx

api_key = open('botify_token.txt').read().strip()

headers = {"Authorization": f"Token {api_key}"}
user_data = httpx.get("https://api.botify.com/v1/authentication/profile", headers=headers).json()

username = user_data["data"]["username"]
print(username)
```

**Sample Output**: 

    first.last

**Rationale**: To create a first successful experience connecting to the Botify API. If you run this and see your name, congratulations! You're a Botify employee. Also, you're successfully connecting to the API.


# List Orgs: How To Get the List of Projects And Their Orgs Given Username

```python
import httpx

# Load API key
api_key = open('botify_token.txt').read().strip()
headers = {"Authorization": f"Token {api_key}"}

def get_username():
    """Fetch the username associated with the API key."""
    try:
        response = httpx.get("https://api.botify.com/v1/authentication/profile", headers=headers)
        response.raise_for_status()
        return response.json()["data"]["username"]
    except httpx.RequestError as e:
        print(f"Error fetching username: {e}")

def fetch_projects(username):
    """Fetch all projects for a given username from Botify API."""
    url = f"https://api.botify.com/v1/projects/{username}"
    projects = []
    try:
        while url:
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            projects.extend(
                (p['name'], p['slug'], p['user']['login']) for p in data.get('results', [])
            )
            url = data.get('next')
        return sorted(projects)
    except httpx.RequestError as e:
        print(f"Error fetching projects for {username}: {e}")
        return []

username = get_username()
if username:
    projects = fetch_projects(username)
    print(f"{'Project Name':<30} {'Project Slug':<35} {'User or Org':<15}")
    print("=" * 80)
    for name, slug, user in projects:
        print(f"{name:<30} {slug:<35} {user:<15}")
else:
    print("Failed to retrieve username or projects.")
```

**Sample Output**:

```
Username: first.last
Project Name                   Project Slug                        User or Org    
================================================================================
Foo Test                       foo.com                             first.last       
Bar Test                       bar.com                             bar-org       
Baz Test                       baz.com                             baz-org       
```

**Rationale**: You need an Organization slug (**org**) for these exercises. It goes in your **config.json** to get started. Your personal login username will usually be used for one Project, but then an offical ***org slug*** (aka group) will usually appear on the others. By convention, these values often end with `-org`.


# List Projects: How To Get the List of Projects Given an Organization

Note: 
- If you're running this in VSCode or Cursor IDE, the `config.json` file should be in the root directory of your project.
- If you're running this in Jupyter Notebook, the `config.json` file should be in the same directory as this notebook.

Your config.json should look like:
```json
{
    "org": "org_name",
    "project": "project_name"
}
```

```python
import json
import httpx

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']

def fetch_projects(org):
    """Fetch all projects for a given organization from Botify API."""
    url = f"https://api.botify.com/v1/projects/{org}"
    headers = {"Authorization": f"Token {api_key}"}
    projects = []
    
    try:
        while url:
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            projects.extend((p['name'], p['slug'], p['user']['login']) for p in data.get('results', []))
            url = data.get('next')
        return sorted(projects)
    except httpx.RequestError as e:
        print(f"Error fetching projects: {e}")
        return []

projects = fetch_projects(org)

print(f"{'Project Name':<30} {'Project Slug':<35} {'Login':<15}")
print("=" * 80)
for name, slug, user in projects:
    print(f"{name:<30} {slug:<35} {user:<15}")

print("\nDone")
```

**Sample Output**:

```
Organization: foo-bar
Project Name                   Project Slug                        Login     
================================================================================
Legendary Product Vault        legendary-product-vault             foo-org       
Hidden Content Cove            hidden-content-cove                 foo-org       
Fabled Catalog of Curiosities  fabled-catalog-of-curiosities       foo-org       
```

**Rationale**: Next, you need Project slugs for these exercises.


# List Analyses: How To Get the List of Analysis Slugs Given a Project


```python
import json
import httpx

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org, project = config['org'], config['project']

def fetch_analyses(org, project):
    """Fetch analysis slugs for a given project from Botify API."""
    url = f"https://api.botify.com/v1/analyses/{org}/{project}/light"
    headers = {"Authorization": f"Token {api_key}"}
    slugs = []
    
    try:
        while url:
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            slugs.extend(a['slug'] for a in data.get('results', []))
            url = data.get('next')
        return slugs
    except httpx.RequestError as e:
        print(f"Error fetching analyses: {e}")
        return []

# Output analysis slugs
for slug in fetch_analyses(org, project):
    print(slug)
print("\nDone")
```

**Sample Output**:

```
20240301
20240201
20240101-2
20240101
20231201
20231101
```

**Rationale**: Analysis slugs are dates in YYYYMMDD format but sometimes get incremeted with `-n` extensions starting with `-2`. They're the third thing you typically need in **config.json** for these exercises.


# List URLs: How To Get a List of the First 500 URLs

**Important**: For this step to work, you need to have an `analysis` value set in your `config.json` file. 

Your `config.json` should include:
```json
{
    "org": "your-organization",
    "project": "your-project-slug",
    "analysis": "your-analysis-slug"
}
```

The analysis slug is typically a date in YYYYMMDD format (like "20240301") as shown in the sample output below. Without this value in your config file, you'll encounter a KeyError.

```python
import json
import httpx
import pandas as pd

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']


def get_bqlv2_data(org, project, analysis, api_key):
    """Fetch data based on BQLv2 query for a specific Botify analysis."""
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # BQLv2 query payload
    data_payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url"
            ],
            "metrics": []  # Don't come crying to me when you delete this and it stops working.
        }
    }

    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

    # Send the request
    response = httpx.post(url, headers=headers, json=data_payload, timeout=60.0)
    response.raise_for_status()  # Check for errors
    
    return response.json()

# Run the query and load results
data = get_bqlv2_data(org, project, analysis, api_key)

list_of_urls = [url['dimensions'][0] for url in data['results']]

for i, url in enumerate(list_of_urls):
    print(i + 1, url)
    if i >= 9:
        break
```

**Sample Output**:

```
1 https://example.com/page1
2 https://example.com/page2
3 https://example.com/page3
4 https://example.com/page4
5 https://example.com/page5
6 https://example.com/page6
7 https://example.com/page7
8 https://example.com/page8
9 https://example.com/page9
10 https://example.com/page10
```

**Rationale**: To explicitly tell you that you have to leave the `metrics": []` field in this example even though it's empty. Don't believe me? Try it. Ugh! Also, I'm not here to teach you Python, but it's worth noting:

- `enumerate()` exposes the internal counter index.
- Python uses zero-based indexes, thus the `+1` for humans and `>= 9` to cut off at 10.
- The `print()` function takes multiple (un-labeled) inputs—counter & url in this case.
- The other way to use the counter & url together is ***f-strings***: `f"{i+1} {url}"`, which would also work.

You're welcome.


# List SEO Fields: How To Get a List of the First 500 URLs, Titles, Meta Descriptions and H1s

```python
import json
import httpx
import pandas as pd

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']

def get_bqlv2_data(org, project, analysis, api_key):
    """Fetch data for URLs with title, meta description, and H1 fields."""
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # BQLv2 query payload
    data_payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url",
                f"crawl.{analysis}.metadata.title.content",
                f"crawl.{analysis}.metadata.description.content",
                f"crawl.{analysis}.metadata.h1.contents"
            ],
            "metrics": []
        }
    }

    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

    # Send the request with a timeout of 60 seconds
    response = httpx.post(url, headers=headers, json=data_payload, timeout=60)
    response.raise_for_status()  # Check for errors
    
    return response.json()

# Run the query and load results
data = get_bqlv2_data(org, project, analysis, api_key)

# Flatten the data into a DataFrame
columns = ["url", "title", "meta_description", "h1"]
df = pd.DataFrame([item['dimensions'] for item in data['results']], columns=columns)

# Display the first 500 URLs
df.head(500).to_csv("first_500_urls.csv", index=False)
print("Data saved to first_500_urls.csv")

# Show a preview
df.head()
```

<!-- #region -->
**Sample Output**:


| url                              | title               | meta_description                           | h1                 |
|----------------------------------|---------------------|--------------------------------------------|---------------------|
| https://example.com/foo          | Foo Title          | This is a description of Foo.              | Foo Heading        |
| https://example.com/bar          | Bar Overview       | Bar is a collection of great resources.    | Bar Insights       |
| https://example.com/baz          | Baz Guide          | Learn all about Baz and its applications.  | Baz Essentials     |

...

*Data saved to `first_500_urls.csv`*

**Rationale**: To show you the main endpoint for listing 500 lines at a time, paging and quick aggregate queries. To show you how `org` and `project` are in the url (so you notice them disappearing later when we export csv downloads). To introduce the infinitely popular and useful `pandas` data library for manipulating ***row & column*** data.
<!-- #endregion -->

```python
import json
import httpx
import pandas as pd

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']

def format_analysis_date(analysis_slug):
    """Convert analysis slug (e.g. '20241108' or '20241108-2') to YYYY-MM-DD format."""
    # Strip any suffix after hyphen
    base_date = analysis_slug.split('-')[0]
    
    # Insert hyphens for YYYY-MM-DD format
    return f"{base_date[:4]}-{base_date[4:6]}-{base_date[6:8]}"

def get_previous_analysis(org, project, current_analysis, api_key):
    """Get the analysis slug immediately prior to the given one."""
    url = f"https://api.botify.com/v1/analyses/{org}/{project}/light"
    headers = {"Authorization": f"Token {api_key}"}
    
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        analyses = response.json().get('results', [])
        
        # Get base date without suffix
        current_base = current_analysis.split('-')[0]
        
        # Find the first analysis that's before our current one
        for analysis in analyses:
            slug = analysis['slug']
            base_slug = slug.split('-')[0]
            if base_slug < current_base:
                return slug
                
    except httpx.RequestError as e:
        print(f"Error fetching analyses: {e}")
        return None

def get_bqlv2_data(org, project, analysis, api_key):
    """Fetch data for URLs with titles and search console metrics, sorted by impressions."""
    # Get date range for search console data
    end_date = format_analysis_date(analysis)
    prev_analysis = get_previous_analysis(org, project, analysis, api_key)
    if prev_analysis:
        start_date = format_analysis_date(prev_analysis)
    else:
        # Fallback to 7 days before if no previous analysis found
        start_date = end_date  # You may want to subtract 7 days here
    
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    data_payload = {
        "collections": [
            f"crawl.{analysis}",
            "search_console"
        ],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url",
                f"crawl.{analysis}.metadata.title.content"
            ],
            "metrics": [
                "search_console.period_0.count_impressions",
                "search_console.period_0.count_clicks"
            ],
            "sort": [
                {
                    "field": "search_console.period_0.count_impressions",
                    "order": "desc"
                }
            ]
        },
        "periods": [
            [start_date, end_date]
        ]
    }
    
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    response = httpx.post(url, headers=headers, json=data_payload, timeout=60.0)
    response.raise_for_status()
    
    return response.json()

# Run the query and load results
data = get_bqlv2_data(org, project, analysis, api_key)

# Flatten the data into a DataFrame with URL, title, and search console metrics
columns = ["url", "title", "impressions", "clicks"]
df = pd.DataFrame([
    item['dimensions'] + item['metrics'] 
    for item in data['results']
], columns=columns)

# Display the first 500 URLs and titles
df.head(500).to_csv("first_500_urls_titles.csv", index=False)
print("Data saved to first_500_urls_titles.csv")

# Show a preview
df.head()
```

<!-- #region -->
**Sample Output**:

| | url                               | title              | impressions | clicks |
|-|-----------------------------------|--------------------|-------------|--------|
|0| https://example.com/foo           | Foo Page Title    | 1200        | 35     |
|1| https://example.com/bar           | Bar Page Title    | 1150        | 40     |
|2| https://example.com/baz           | Baz Page Title    | 980         | 25     |


**Rationale**: So that I can jump up and down screaming that BQL is not SQL and tell the LLMs to stop showing me SQL examples for BQL. Surely SQL is down there somewhere, but it's ***API-wrapped***. Though this does not spare us from some SQL methodology. For example, table-joins across Collections are a thing—demonstrated here as `search_console` joined with `crawl.YYMMDD`, left-outer if I'm reading it correctly (I may have to amend that). If you really wanna know, Collections are table aliases that help with the API-wrapping.
<!-- #endregion -->

# # Query Segments: How to Get Pagetype Segment Data for a Project With URL Counts

This query requires the "collection" field in your config.json file, in addition to "org", "project", and "analysis".
Example config.json:
```json
{
    "org": "org_name",
    "project": "project_name",
    "analysis": "20241230",
    "collection": "crawl.20241230"
}
```



```python
import httpx
import json

# Load configuration values from config.json
with open("config.json") as config_file:
    config = json.load(config_file)

# Extract configuration details
org = config["org"]
project = config["project"]
analysis = config["analysis"]
collection = config["collection"]

# Load the API key from botify_token.txt
api_key = open('botify_token.txt').read().strip()

# Define the URL for the API request
url = f"https://api.botify.com/v1/projects/{org}/{project}/query"

# Set headers for authorization and content type
headers = {
    "Authorization": f"Token {api_key}",
    "Content-Type": "application/json"
}

# Define the payload for the API query
payload = {
    "collections": [collection],
    "query": {
        "dimensions": [{"field": "segments.pagetype.value"}],
        "metrics": [{"field": f"{collection}.count_urls_crawl"}],
        "sort": [
            {"type": "metrics", "index": 0, "order": "desc"},
            {"type": "dimensions", "index": 0, "order": "asc"}
        ]
    }
}

# Send the POST request to the API
response = httpx.post(url, headers=headers, json=payload, timeout=60)
response.raise_for_status()  # Raise an error if the request fails

# Get the results from the response JSON
results = response.json()

# Use json.dumps with separators and indent for compact pretty printing
print(json.dumps(results, indent=4, separators=(',', ': ')))
```

**Sample Output**:

```json
{
    "results": [
        {
            "dimensions": ["pdp"],
            "metrics": [82150]
        },
        {
            "dimensions": ["plp"],
            "metrics": [53400]
        },
        {
            "dimensions": ["category"],
            "metrics": [44420]
        },
        [...]
    ],
    "previous": null,
    "next": "https://api.botify.com/v1/org/project/query?page=1",
    "page": 1,
    "size": 10
}
```

**Rationale**: To give you an example that uses dimensions, metrics and sorting all at once. Also to show you the `page` parameter on the querystring making you think it's the **GET method**, `org` & `project` arguments posing as folders, and finally a JSON `payload` showing you it's actually using the **POST method**. Ahhh, *gotta love the Botify API*.


# List Collections: How To Get the List of Collections Given a Project

```python
# Get List of Collections Given a Project

import json
import httpx

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']

def fetch_collections(org, project, api_key):
    """Fetch collection IDs for a given project from the Botify API."""
    collections_url = f"https://api.botify.com/v1/projects/{org}/{project}/collections"
    headers = {"Authorization": f"Token {api_key}"}
    
    try:
        response = httpx.get(collections_url, headers=headers)
        response.raise_for_status()
        collections_data = response.json()
        return [
            (collection['id'], collection['name']) for collection in collections_data
        ]
    except httpx.RequestError as e:
        print(f"Error fetching collections for project '{project}': {e}")
        return []


# Fetch collections
collections = fetch_collections(org, project, api_key)
for collection_id, collection_name in collections:
    print(f"ID: {collection_id}, Name: {collection_name}")
```

**Sample Output**:

```
ID: crawl.20240917, Name: 2024 Sept. 17th
ID: actionboard_ml.20240917, Name: ActionBoard ML
ID: crawl.20240715, Name: 2024 July 15th
ID: search_engines_orphans.20240715, Name: Search Engines Orphans
```

**Rationale**: To let you know how tough Collections are once you start digging in. The first challenge is simply knowing what collections you have and what you can do with them—though 9 out of 10 times it's `crawl.YYYYMMDD` and `search_console`. If not, come talk to me, I wanna pick your brain.


# List Fields: How To Get The List of Fields Given a Collection

```python
# Get List of Fields Given a Collection

import json
import httpx

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
collection = config['collection']

def fetch_fields(org, project, collection, api_key):
    """Fetch available fields for a given collection from the Botify API."""
    fields_url = f"https://api.botify.com/v1/projects/{org}/{project}/collections/{collection}"
    headers = {"Authorization": f"Token {api_key}"}
    
    try:
        response = httpx.get(fields_url, headers=headers)
        response.raise_for_status()
        fields_data = response.json()
        return [
            (field['id'], field['name'])
            for dataset in fields_data.get('datasets', [])
            for field in dataset.get('fields', [])
        ]
    except httpx.RequestError as e:
        print(f"Error fetching fields for collection '{collection}' in project '{project}': {e}")
        return []

# Fetch and print fields
fields = fetch_fields(org, project, collection, api_key)
print(f"Fields for collection '{collection}':")
for field_id, field_name in fields:
    print(f"ID: {field_id}, Name: {field_name}")
```

**Sample Output**:

```
Fields for collection 'crawl.20241101':
ID: field_of_vision, Name: Survey the Landscape
ID: field_of_dreams, Name: The Mind's Eye
ID: straying_far_afield, Name: Go Home Spiderman
ID: afield_a_complaint, Name: Red Swingline
```

**Rationale**: So you've got a collection and have no idea what to do with it? Well, you can always start by listing its fields. Yeah, let's list the fields.


# Get Pagetypes: How To Get the Unfiltered URL Counts by Pagetype for a Specific Analysis

```python
import json
import httpx
import pandas as pd

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
website = config['project']  # Assuming 'project' here refers to the website
analysis_date = config['analysis']  # Date of analysis, formatted as 'YYYYMMDD'

def get_first_page_pagetype_url_counts(org, website, analysis_date, api_key, size=5000):
    """Fetch pagetype segmentation counts for the first page only, sorted by URL count in descending order."""
    url = f"https://app.botify.com/api/v1/projects/{org}/{website}/query?size={size}"
    
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
        "x-botify-client": "spa",
    }
    
    # Payload to retrieve pagetype segmentation counts, ordered by URL count
    data_payload = {
        "collections": [f"crawl.{analysis_date}"],
        "query": {
            "dimensions": [{"field": "segments.pagetype.value"}],
            "metrics": [{"field": f"crawl.{analysis_date}.count_urls_crawl"}],
            "sort": [
                {"type": "metrics", "index": 0, "order": "desc"},
                {"type": "dimensions", "index": 0, "order": "asc"}
            ]
        }
    }

    try:
        # Make a single request for the first page of results
        response = httpx.post(url, headers=headers, json=data_payload)
        response.raise_for_status()
        data = response.json()

        # Process the first page of results
        results = []
        for item in data.get("results", []):
            pagetype = item["dimensions"][0] if item["dimensions"] else "Unknown"
            count = item["metrics"][0] if item["metrics"] else 0
            results.append({"Pagetype": pagetype, "URL Count": count})
    
    except httpx.RequestError as e:
        print(f"Error fetching pagetype URL counts: {e}")
        return []
    
    return results

# Fetch pagetype URL counts for the first page only
results = get_first_page_pagetype_url_counts(org, website, analysis_date, api_key)

# Convert results to a DataFrame and save
df = pd.DataFrame(results)
df.to_csv("pagetype_url_counts.csv", index=False)
print("Data saved to pagetype_url_counts.csv")

# Display a preview
print(df)
```

**Sample Output**:

```
Data saved to pagetype_url_counts.csv
                 Pagetype  URL Count
0                    pdp     250000
1                    plp      50000
2                    hub       5000
3                   blog       2500
4                    faq        500
```

**Rationale**: Do you ever get the feeling a website's folder-structure can tell you something about how it's organized? Yeah, me too. Thankfully, we here at Botify do the ***Regular Expressions*** so you don't have to. And it makes really great great color-coding in the link-graph visualizations. Psst! Wanna see the Death Star?


# Get Short Titles: How To Get the First 500 URLs With Short Titles Given Pagetype

```python
# Get the First 500 URLs With Short Titles Given Pagetype

import json
import httpx
import pandas as pd

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']


def get_bqlv2_data(org, project, analysis, api_key):
    """Fetch data based on BQLv2 query for a specific Botify analysis."""
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # BQLv2 query payload
    data_payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url",
                f"crawl.{analysis}.metadata.title.len",
                f"crawl.{analysis}.metadata.title.content",
                f"crawl.{analysis}.metadata.title.quality",
                f"crawl.{analysis}.metadata.description.content",
                f"crawl.{analysis}.metadata.structured.breadcrumb.tree",
                f"crawl.{analysis}.metadata.h1.contents",
                f"crawl.{analysis}.metadata.h2.contents"
            ],
            "metrics": [],
            "filters": {
                "and": [
                    {
                        "field": f"crawl.{analysis}.scoring.issues.title_len",
                        "predicate": "eq",
                        "value": True
                    },
                    {
                        "field": f"crawl.{analysis}.segments.pagetype.depth_1",
                        "value": "pdp"
                    }
                ]
            },
            "sort": [
                {
                    "field": f"crawl.{analysis}.metadata.title.len",
                    "order": "asc"
                }
            ]
        }
    }

    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

    # Send the request
    # Allow up to a minute for the API to respond
    response = httpx.post(url, headers=headers, json=data_payload, timeout=60.0)
    response.raise_for_status()  # Check for errors
    
    return response.json()

# Run the query and load results
data = get_bqlv2_data(org, project, analysis, api_key)

# Flatten the data into a DataFrame
# Define column names for each dimension in the data
columns = [
    "url", "title_len", "title_content", "title_quality",
    "description_content", "breadcrumb_tree", "h1_contents", "h2_contents"
]
df = pd.DataFrame([item['dimensions'] for item in data['results']], columns=columns)

print("Data saved to titles_too_short.csv")

# Display all columns
pd.set_option('display.max_columns', None)

# Display all rows 
pd.set_option('display.max_rows', None)

# Increase column width to avoid truncation
pd.set_option('display.max_colwidth', None)

df.head(10)
```

**Sample Output**:

**Data saved to titles_too_short.csv**

| url                                      | title_len | title_content     | title_quality | description_content                                              | breadcrumb_tree                                       | h1_contents                     | h2_contents                             |
|------------------------------------------|-----------|-------------------|---------------|------------------------------------------------------------------|--------------------------------------------------------|----------------------------------|-----------------------------------------|
| https://www.example.com/site/socks/12345 | 8         | Sock Store        | unique        | Best socks for every season, unbeatable comfort and style.      | Example Store/Footwear/Accessories/Socks               | [Our Socks]                     | [Features, Sizes, Related Items]        |
| https://www.example.com/site/hats/98765  | 9         | Top Hats Here!    | duplicate     | Stylish hats available year-round with exclusive discounts.     | Example Store/Apparel/Accessories/Hats                 | [Hat Selection]                 | [Details, Reviews, Top Picks]           |
| https://www.example.com/site/shirts/54321| 10        | - Shirt Emporium  | duplicate     | Discover comfortable and stylish shirts at great prices.        | Example Store/Apparel/Topwear/Shirts                   | [Shirt Central]                 | [Sizing, Similar Styles, Reviews]       |

...

**Rationale**: Ahh, ***title tags***. They show in browser bookmarks, tabs and SERPs—the only relevancy factor that will remain standing after SEO Armageddon. You could ditch every other factor but ***anchor text***, set your uber-crawler go off-site, use a click-depth of 4—and harvest yourself a pretty good link-graph of the entire Internet... were it not for spammers.


# Count Short Titles: How To Count Number of URLs Having Short Titles

```python
import json
import httpx

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']

def count_short_titles(org, project, analysis, api_key):
    """Count URLs with short titles for a specific Botify analysis."""
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }

    # Data payload for the count of URLs with short titles
    data_payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [],  # No dimensions needed, as we only need a count
            "metrics": [
                {
                    "function": "count",
                    "args": [f"crawl.{analysis}.url"]
                }
            ],
            "filters": {
                "field": f"crawl.{analysis}.scoring.issues.title_len",
                "predicate": "eq",
                "value": True
            }
        }
    }

    try:
        # Send the request
        response = httpx.post(url, headers=headers, json=data_payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Extract the count of URLs with short titles
        short_title_count = data["results"][0]["metrics"][0]
        return short_title_count
    except httpx.RequestError as e:
        print(f"Error fetching short title count for analysis '{analysis}' in project '{project}': {e}")
        return None

# Run the count query and display the result
short_title_count = count_short_titles(org, project, analysis, api_key)

if short_title_count is not None:
    print(f"Number of URLs with short titles: {short_title_count:,}")
else:
    print("Failed to retrieve the count of URLs with short titles.")

```

**Sample Output**:

    Number of URLs with short titles: 675,080

**Rationale**: Sometimes ya gotta count what you're trying to get before you go try and download it. Plus, learn ***filtering*** in the Botify API! But I think really I just wanted to show you how easy it is to format `f"{big_numbers:,}"` with commas using ***f-strings*** (I'm talking to you humans—because the LLMs *already know*).


# Download CSV: How To Download Up to 10K URLs Having Short Titles As a CSV

```python
import json
import httpx
import time
import gzip
import shutil

config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']


def start_export_job_for_short_titles(org, project, analysis, api_key):
    """Start an export job for URLs with short titles, downloading key metadata fields."""
    url = "https://api.botify.com/v1/jobs"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }

    # Data payload for the export job with necessary fields
    data_payload = {
        "job_type": "export",
        "payload": {
            "username": org,
            "project": project,
            "connector": "direct_download",
            "formatter": "csv",
            "export_size": 10000,  # Adjust as needed
            "query": {
                "collections": [f"crawl.{analysis}"],
                "query": {
                    "dimensions": [
                        f"crawl.{analysis}.url",
                        f"crawl.{analysis}.metadata.title.len",
                        f"crawl.{analysis}.metadata.title.content",
                        f"crawl.{analysis}.metadata.title.quality",
                        f"crawl.{analysis}.metadata.description.content",
                        f"crawl.{analysis}.metadata.h1.contents"
                    ],
                    "metrics": [],
                    "filters": {
                        "field": f"crawl.{analysis}.scoring.issues.title_len",
                        "predicate": "eq",
                        "value": True
                    },
                    "sort": [
                        {
                            "field": f"crawl.{analysis}.metadata.title.len",
                            "order": "asc"
                        }
                    ]
                }
            }
        }
    }

    try:
        print("Starting export job for short titles...")
        # Use a longer timeout to prevent ReadTimeout errors
        response = httpx.post(url, headers=headers, json=data_payload, timeout=300.0)
        response.raise_for_status()
        export_job_details = response.json()
        
        # Extract job URL for polling
        job_url = f"https://api.botify.com{export_job_details.get('job_url')}"
        
        # Polling for job completion
        print("Polling for job completion:", end=" ")
        while True:
            time.sleep(5)
            # Use a longer timeout for polling requests as well
            poll_response = httpx.get(job_url, headers=headers, timeout=120.0)
            poll_response.raise_for_status()
            job_status_details = poll_response.json()
            
            if job_status_details["job_status"] == "DONE":
                download_url = job_status_details["results"]["download_url"]
                print("\nDownload URL:", download_url)
                return download_url
            elif job_status_details["job_status"] == "FAILED":
                print("\nJob failed. Error details:", job_status_details)
                return None
            print(".", end="", flush=True)
        
    except httpx.ReadTimeout as e:
        print(f"\nTimeout error during export job: {e}")
        print("The API request timed out. Consider increasing the timeout value or try again later.")
        return None
    except httpx.RequestError as e:
        print(f"\nError starting or polling export job: {e}")
        return None


# Start export job and get download URL
download_url = start_export_job_for_short_titles(org, project, analysis, api_key)

# Download and decompress the file if the download URL is available
if download_url:
    gz_filename = "short_titles_export.csv.gz"
    csv_filename = "short_titles_export.csv"
    
    try:
        # Step 1: Download the gzipped CSV file with increased timeout
        response = httpx.get(download_url, timeout=300.0)
        with open(gz_filename, "wb") as gz_file:
            gz_file.write(response.content)
        print(f"File downloaded as '{gz_filename}'")
        
        # Step 2: Decompress the .gz file to .csv
        with gzip.open(gz_filename, "rb") as f_in:
            with open(csv_filename, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"File decompressed and saved as '{csv_filename}'")
    except httpx.ReadTimeout as e:
        print(f"Timeout error during file download: {e}")
        print("The download request timed out. Try again later or download manually from the URL.")
    except Exception as e:
        print(f"Error during file download or decompression: {e}")
else:
    print("Failed to retrieve the download URL.")
```

**Sample Output**:

    Starting export job for short titles...  
    Polling for job completion: .  
    Download URL: https://cdn.example.com/export_data/abc/def/ghi/xyz1234567890/funfetti-2024-11-08.csv.gz  
    File downloaded as 'short_titles_export.csv.gz'  
    File decompressed and saved as 'short_titles_export.csv'  

**Rationale**: Is it pulling or pooling? I could never remember. In either case, exporting and downloading csv-files is not as straightforward as you think. First, you make the request. Then you look for ***where*** to check progress, then keep re-checking until done. Then you sacrifice a chicken to help you debug useless errors. Lastly, you notice how your endpoint has changed to`https://api.botify.com/v1/jobs` with `org` and `project` moved into the JSON payload. Or is that firstly? Yeah, definitely firstly.


# Get Total Count: How To Get Aggregate Count of All URLs Crawled During Analysis

```python
import json
import httpx

# --- 1. Configuration ---
# Load necessary details from files (adjust paths if needed)
# Basic error handling for loading is good practice even in tutorials
try:
    config = json.load(open("config.json"))
    api_key = open('botify_token.txt').read().strip()
    # Get specific config values needed
    ORG_SLUG = config['org']
    PROJECT_SLUG = config['project']
    ANALYSIS_SLUG = config['analysis']
except FileNotFoundError:
    print("Error: 'config.json' or 'botify_token.txt' not found.")
    exit()
except KeyError as e:
    print(f"Error: Key '{e}' not found in 'config.json'.")
    exit()
except Exception as e:
    print(f"Error loading configuration: {e}")
    exit()

# TARGET_MAX_DEPTH is no longer needed for this calculation

# --- 2. Function to Get URL Counts Per Depth ---
def get_all_urls_by_depth(org, project, analysis, key):
    """
    Fetches URL counts for ALL depths from the Botify API.
    Returns a dictionary {depth: count} or None on error.
    """
    api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}

    # This payload asks for counts grouped by depth, for the entire crawl
    payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [f"crawl.{analysis}.depth"],
            "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
            "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
        }
    }

    try:
        print("Requesting total URL count of site from Botify API...")
        response = httpx.post(api_url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status() # Check for HTTP errors (like 4xx, 5xx)
        print("Data received successfully.")

        # Convert the response list into a more usable {depth: count} dictionary
        results = response.json().get("results", [])
        depth_counts = {
            row["dimensions"][0]: row["metrics"][0]
            for row in results
            if "dimensions" in row and len(row["dimensions"]) > 0 and \
               "metrics" in row and len(row["metrics"]) > 0 and \
               isinstance(row["dimensions"][0], int) # Ensure depth is an int
        }
        return depth_counts

    except httpx.HTTPStatusError as e:
        print(f"API Error: {e.response.status_code} - {e.response.text}")
        return None # Indicate failure
    except Exception as e:
        print(f"An error occurred during API call or processing: {e}")
        return None # Indicate failure

# --- 3. Main Calculation (Grand Total) ---
# Get the depth data using the function
all_depth_data = get_all_urls_by_depth(ORG_SLUG, PROJECT_SLUG, ANALYSIS_SLUG, api_key)

# Proceed only if we got data back
if all_depth_data is not None:
    # Calculate the grand total by summing all counts
    grand_total_urls = 0
    print(f"\nCalculating the grand total number of URLs from all depths...")

    # Loop through all counts returned in the dictionary values and add them up
    for count in all_depth_data.values():
        grand_total_urls += count

    # --- Alternatively, you could use the sum() function directly: ---
    # grand_total_urls = sum(all_depth_data.values())
    # ----------------------------------------------------------------

    # Print the final result
    print(f"\nResult: Grand Total URLs in Crawl = {grand_total_urls:,}")
else:
    print("\nCould not calculate total because API data retrieval failed.")
```

**Sample Output**:

Requesting total URL count of site from Botify API...
Data received successfully.

Calculating the grand total number of URLs from all depths...

Result: Grand Total URLs in Crawl = 3,000,000

**Rationale**: Before doing a download of a CSV it is often worth checking if the number of rows returned will be under the 1-million row API limit.


# Get Depth Count: How To Get Aggregate Count of URLs at Particular Click Depth

```python
import json
import httpx

# --- 1. Configuration ---
# Load necessary details from files (adjust paths if needed)
# Basic error handling for loading is good practice even in tutorials
try:
    config = json.load(open("config.json"))
    api_key = open('botify_token.txt').read().strip()
    # Get specific config values needed
    ORG_SLUG = config['org']
    PROJECT_SLUG = config['project']
    ANALYSIS_SLUG = config['analysis']
except FileNotFoundError:
    print("Error: 'config.json' or 'botify_token.txt' not found.")
    exit()
except KeyError as e:
    print(f"Error: Key '{e}' not found in 'config.json'.")
    exit()
except Exception as e:
    print(f"Error loading configuration: {e}")
    exit()

# Define the maximum depth for our calculation
TARGET_MAX_DEPTH = 5

# --- 2. Function to Get URL Counts Per Depth ---
def get_all_urls_by_depth(org, project, analysis, key):
    """
    Fetches URL counts for ALL depths from the Botify API.
    Returns a dictionary {depth: count} or None on error.
    """
    api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}

    # This payload asks for counts grouped by depth, for the entire crawl
    payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [f"crawl.{analysis}.depth"],
            "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
            "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
        }
    }

    try:
        print("Requesting data from Botify API...")
        response = httpx.post(api_url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status() # Check for HTTP errors (like 4xx, 5xx)
        print("Data received successfully.")

        # Convert the response list into a more usable {depth: count} dictionary
        results = response.json().get("results", [])
        depth_counts = {
            row["dimensions"][0]: row["metrics"][0]
            for row in results
            if "dimensions" in row and len(row["dimensions"]) > 0 and \
               "metrics" in row and len(row["metrics"]) > 0 and \
               isinstance(row["dimensions"][0], int) # Ensure depth is an int
        }
        return depth_counts

    except httpx.HTTPStatusError as e:
        print(f"API Error: {e.response.status_code} - {e.response.text}")
        return None # Indicate failure
    except Exception as e:
        print(f"An error occurred during API call or processing: {e}")
        return None # Indicate failure

# --- 3. Main Calculation ---
# Get the depth data using the function
all_depth_data = get_all_urls_by_depth(ORG_SLUG, PROJECT_SLUG, ANALYSIS_SLUG, api_key)

# Proceed only if we got data back
if all_depth_data is not None:
    total_count_at_or_below_depth = 0
    print(f"\nCalculating total for depth <= {TARGET_MAX_DEPTH}...")

    # Loop through the dictionary and sum counts for relevant depths
    for depth, count in all_depth_data.items():
        if depth <= TARGET_MAX_DEPTH:
            total_count_at_or_below_depth += count

    # Print the final result
    print(f"\nResult: Total URLs at depth {TARGET_MAX_DEPTH} or less = {total_count_at_or_below_depth:,}")
else:
    print("\nCould not calculate total because API data retrieval failed.")
```

**Sample Output**:

Attempting to get full URL distribution by depth...

Calculating total URLs for depth <= 5 from received data...

Total URLs at depth 5 or less: 1,500,000

**Rationale**: Before doing a download of a CSV it is often worth checking if the number of rows returned will be under the 1-million row API limit. By using a depth filter, we now have the foundation for reducing depth until we get a downloadable number.


# Get Aggregates: How To Get Map of Click-Depths Aggregates Given Analysis Slug

```python
import json
import httpx
import pprint # Keep pprint for the final output as in the original

# --- 1. Configuration ---
# Load necessary details from files (adjust paths if needed)
try:
    config = json.load(open("config.json"))
    api_key = open('botify_token.txt').read().strip()
    # Get specific config values needed
    ORG_SLUG = config['org']
    PROJECT_SLUG = config['project']
    ANALYSIS_SLUG = config['analysis']
    print("Configuration loaded successfully.")
except FileNotFoundError:
    print("Error: 'config.json' or 'botify_token.txt' not found.")
    exit(1)
except KeyError as e:
    print(f"Error: Key '{e}' not found in 'config.json'.")
    exit(1)
except Exception as e:
    print(f"Error loading configuration: {e}")
    exit(1)

# --- 2. Function to Get URL Counts Per Depth ---
# (Kept original function name)
def get_urls_by_depth(org, project, analysis, key):
    """
    Fetches URL counts aggregated by depth from the Botify API.
    Returns a dictionary {depth: count} or an empty {} on error.
    (Matches original functionality return type on error)
    """
    # Use clearer variable name for URL
    api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}

    # Use clearer variable name for payload
    payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [f"crawl.{analysis}.depth"],
            "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
            "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
        }
    }

    try:
        print("Requesting URL counts per depth from Botify API...")
        # Use a longer timeout (e.g., 120 seconds)
        response = httpx.post(api_url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status() # Check for HTTP errors (like 4xx, 5xx)
        print("Data received successfully.")

        # Convert the response list into a more usable {depth: count} dictionary
        # Add validation during processing
        response_data = response.json()
        results = response_data.get("results", [])

        depth_distribution = {}
        print("Processing API response...")
        for row in results:
             # Validate structure before accessing keys/indices
             if "dimensions" in row and len(row["dimensions"]) == 1 and \
                "metrics" in row and len(row["metrics"]) == 1:
                 depth = row["dimensions"][0]
                 count = row["metrics"][0]
                 # Ensure depth is an integer
                 if isinstance(depth, int):
                     depth_distribution[depth] = count
                 else:
                     print(f"Warning: Skipping row with non-integer depth: {row}")
             else:
                 print(f"Warning: Skipping row with unexpected structure: {row}")

        print("Processing complete.")
        return depth_distribution # Return the dictionary with results

    # Adopt more specific error handling from the target style
    except httpx.ReadTimeout:
        print("Request timed out after 120 seconds.")
        return {} # Return empty dict per original functionality
    except httpx.HTTPStatusError as e:
        print(f"API Error: {e.response.status_code} - {e.response.reason_phrase}")
        try:
            # Attempt to show detailed API error message
            error_details = e.response.json()
            print(f"Error details: {error_details}")
        except json.JSONDecodeError:
            # Fallback if response is not JSON
            print(f"Response content: {e.response.text}")
        return {} # Return empty dict per original functionality
    except httpx.RequestError as e:
        # Handles other request errors like connection issues
        print(f"An error occurred during the request: {e}")
        return {} # Return empty dict per original functionality
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
         # Catch issues during JSON processing or accessing expected keys/indices
         print(f"Error processing API response: {e}")
         if 'response' in locals(): # Log raw response if available
              print(f"Response Text: {response.text}")
         return {} # Return empty dict per original functionality
    except Exception as e:
        # Catch-all for any other unexpected errors in this function
        print(f"An unexpected error occurred in get_urls_by_depth: {e}")
        return {} # Return empty dict per original functionality


# --- 3. Main Execution ---
print("\nStarting script execution to get URL distribution by depth...")
try:
    # Call the function using loaded config variables
    depth_distribution_result = get_urls_by_depth(
        ORG_SLUG, PROJECT_SLUG, ANALYSIS_SLUG, api_key
    )

    # Check if the result is not an empty dictionary
    # An empty dict signifies an error occurred in the function OR no data found
    if depth_distribution_result: # A non-empty dict evaluates to True
        print("\n--- URL Distribution by Depth ---")
        # Use pprint for formatted output as in the original script
        pprint.pprint(depth_distribution_result, width=1)
        print("---------------------------------")
    else:
        # This message prints if the function returned {}
        print("\nRetrieved empty distribution. This could be due to an error (check logs above) or no URLs found.")

except Exception as e:
    # Catch any unexpected errors during the main execution sequence
    print(f"An unexpected error occurred during the main execution: {e}")
```

**Sample Output**:

```plaintext
Configuration loaded successfully.

Starting script execution to get URL distribution by depth...
Requesting URL counts per depth from Botify API...
Data received successfully.
Processing API response...
Processing complete.

--- URL Distribution by Depth (Scaled Generic Example) ---
{ 0: 10,        # Start pages (kept small)
  1: 550,
  2: 28000,     # Rounded 5k * 5.5
  3: 275000,    # 50k * 5.5
  4: 825000,    # Peak (150k * 5.5)
  5: 660000,    # Starting decline (120k * 5.5)
  6: 440000,    # 80k * 5.5
  7: 275000,    # 50k * 5.5
  8: 165000,    # 30k * 5.5
  9: 110000,    # 20k * 5.5
 10: 55000,     # 10k * 5.5
 11: 44000,     # 8k * 5.5
 12: 33000,     # 6k * 5.5
 13: 28000,     # Rounded 5k * 5.5
 14: 22000,     # 4k * 5.5
 15: 17000,     # Rounded 3k * 5.5
 16: 11000,     # 2k * 5.5
 17: 6000,      # Rounded 1k * 5.5
 18: 3000,      # Rounded 500 * 5.5
 19: 1100,      # 200 * 5.5
 20: 550 }      # 100 * 5.5
--------------------------------------------------------
```

**Rationale**: This depth distribution shows how many URLs exist at each click depth level from the homepage (hompage = depth 0). A healthy site typically has most content within 3 or 4 clicks of the homepage. Much more, and it may as well not exist. Such reports help identify potential deep crawl issues, spider-traps, and why (in addition to the infinite spam-cannon of generative AI content), brute-force crawls that *"make a copy of the Internet"* are all but dead. And did I mention that excessively crawl-able faceted search makes your site's link-graph look like the Death Star? Yeah, I think I did.


# Get Aggregates: How To Get Map of CUMULATIVE Click-Depths Aggregates Given Analysis Slug

```python
import json
import httpx
import pprint # Keep pprint for the final output

# --- 1. Configuration ---
# Load necessary details from files (adjust paths if needed)
try:
    config = json.load(open("config.json"))
    api_key = open('botify_token.txt').read().strip()
    # Get specific config values needed
    ORG_SLUG = config['org']
    PROJECT_SLUG = config['project']
    ANALYSIS_SLUG = config['analysis']
    print("Configuration loaded successfully.")
except FileNotFoundError:
    print("Error: 'config.json' or 'botify_token.txt' not found.")
    exit(1)
except KeyError as e:
    print(f"Error: Key '{e}' not found in 'config.json'.")
    exit(1)
except Exception as e:
    print(f"Error loading configuration: {e}")
    exit(1)

# --- 2. Function to Get URL Counts Per Depth ---
# (This function remains unchanged as it fetches the base data needed)
def get_urls_by_depth(org, project, analysis, key):
    """
    Fetches URL counts aggregated by depth from the Botify API.
    Returns a dictionary {depth: count} or an empty {} on error.
    """
    api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
    payload = {
        "collections": [f"crawl.{analysis}"],
        "query": {
            "dimensions": [f"crawl.{analysis}.depth"],
            "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
            "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
        }
    }
    try:
        print("Requesting URL counts per depth from Botify API...")
        response = httpx.post(api_url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status()
        print("Data received successfully.")
        response_data = response.json()
        results = response_data.get("results", [])
        depth_distribution = {}
        print("Processing API response...")
        for row in results:
             if "dimensions" in row and len(row["dimensions"]) == 1 and \
                "metrics" in row and len(row["metrics"]) == 1:
                 depth = row["dimensions"][0]
                 count = row["metrics"][0]
                 if isinstance(depth, int):
                     depth_distribution[depth] = count
                 else:
                     print(f"Warning: Skipping row with non-integer depth: {row}")
             else:
                 print(f"Warning: Skipping row with unexpected structure: {row}")
        print("Processing complete.")
        return depth_distribution
    except httpx.ReadTimeout:
        print("Request timed out after 120 seconds.")
        return {}
    except httpx.HTTPStatusError as e:
        print(f"API Error: {e.response.status_code} - {e.response.reason_phrase}")
        try:
            error_details = e.response.json()
            print(f"Error details: {error_details}")
        except json.JSONDecodeError:
            print(f"Response content: {e.response.text}")
        return {}
    except httpx.RequestError as e:
        print(f"An error occurred during the request: {e}")
        return {}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
         print(f"Error processing API response: {e}")
         if 'response' in locals():
              print(f"Response Text: {response.text}")
         return {}
    except Exception as e:
        print(f"An unexpected error occurred in get_urls_by_depth: {e}")
        return {}


# --- 3. Main Execution ---
print("\nStarting script execution...")
try:
    # Call the function to get the dictionary {depth: count_at_depth}
    depth_distribution_result = get_urls_by_depth(
        ORG_SLUG, PROJECT_SLUG, ANALYSIS_SLUG, api_key
    )

    # Check if the result is not an empty dictionary (which indicates an error)
    if depth_distribution_result: # A non-empty dict evaluates to True
        print("\nCalculating cumulative URL counts by depth...")

        # --- Calculate Cumulative Distribution ---
        cumulative_depth_distribution = {}
        current_cumulative_sum = 0
        # Get the depths present and sort them to process in order (0, 1, 2...)
        # Handle case where result might be empty just in case, though checked above
        sorted_depths = sorted(depth_distribution_result.keys())
        max_depth_found = sorted_depths[-1] if sorted_depths else -1

        # Iterate from depth 0 up to the maximum depth found in the results
        for depth_level in range(max_depth_found + 1):
            # Get the count for this specific depth_level from the original results.
            # Use .get(depth, 0) in case a depth level has no URLs (e.g., depth 0 might be missing if start page redirected)
            count_at_this_level = depth_distribution_result.get(depth_level, 0)

            # Add this level's count to the running cumulative sum
            current_cumulative_sum += count_at_this_level

            # Store the *cumulative* sum in the new dictionary for this depth level
            cumulative_depth_distribution[depth_level] = current_cumulative_sum
        # --- End Calculation ---

        print("\n--- Cumulative URL Distribution by Depth (URLs <= Depth) ---")
        # Use pprint for formatted output of the NEW cumulative dictionary
        pprint.pprint(cumulative_depth_distribution, width=1)
        print("----------------------------------------------------------")

    else:
        # This message prints if the function returned {}
        print("\nRetrieved empty distribution. Cannot calculate cumulative counts.")

except Exception as e:
    # Catch any unexpected errors during the main execution sequence
    print(f"An unexpected error occurred during the main execution: {e}")
```

**Sample Output**:

```plaintext
Configuration loaded successfully.

Starting script execution...
Requesting URL counts per depth from Botify API...
Data received successfully.
Processing API response...
Processing complete.

Calculating cumulative URL counts by depth...

--- Cumulative URL Distribution by Depth (Scaled Generic Example) ---
{ 0: 10,
  1: 560,          # (10 + 550)
  2: 28560,        # (560 + 28000)
  3: 303560,       # (28560 + 275000)
  4: 1128560,      # (303560 + 825000) <-- Reaches 1M+
  5: 1788560,      # (1128560 + 660000)
  6: 2228560,      # (1788560 + 440000) <-- Reaches 2M+
  7: 2503560,      # (2228560 + 275000)
  8: 2668560,      # (2503560 + 165000)
  9: 2778560,      # (2668560 + 110000)
 10: 2833560,      # (2778560 + 55000) <-- Growth significantly slower now
 11: 2877560,      # (2833560 + 44000)
 12: 2910560,      # (2877560 + 33000)
 13: 2938560,      # (2910560 + 28000)
 14: 2960560,      # (2938560 + 22000)
 15: 2977560,      # (2960560 + 17000)
 16: 2988560,      # (2977560 + 11000)
 17: 2994560,      # (2988560 + 6000)
 18: 2997560,      # (2994560 + 3000)
 19: 2998660,      # (2997560 + 1100)
 20: 2999210 }      # (2998660 + 550) <-- Final cumulative total ~3M
------------------------------------------------------------------
```

**Rationale**: This depth distribution shows how many URLs exist at each click depth level from the homepage (hompage = depth 0). A healthy site typically has most content within 3 or 4 clicks of the homepage. Much more, and it may as well not exist. Such reports help identify potential deep crawl issues, spider-traps, and why (in addition to the infinite spam-cannon of generative AI content), brute-force crawls that *"make a copy of the Internet"* are all but dead. And did I mention that excessively crawl-able faceted search makes your site's link-graph look like the Death Star? Yeah, I think I did.


# Download Link Graph: How to Download a Link Graph for a Specified Organization, Project, and Analysis For Website Visualization.

```python
import os
import time
import json
from pathlib import Path
import httpx
import pandas as pd

# Load configuration and API key
config = json.load(open("config.json"))
api_key = open('botify_token.txt').read().strip()
org = config['org']
project = config['project']
analysis = config['analysis']

# Define API headers
headers = {
    "Authorization": f"Token {api_key}",
    "Content-Type": "application/json"
}

# Determine optimal click depth for link graph export
def find_optimal_depth(org, project, analysis, max_edges=1000000):
    """
    Determine the highest depth for which the number of edges does not exceed max_edges.
    """
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    # httpx doesn't have Session, use Client instead
    client = httpx.Client()
    previous_edges = 0

    for depth in range(1, 10):
        data_payload = {
            "collections": [f"crawl.{analysis}"],
            "query": {
                "dimensions": [],
                "metrics": [{"function": "sum", "args": [f"crawl.{analysis}.outlinks_internal.nb.total"]}],
                "filters": {"field": f"crawl.{analysis}.depth", "predicate": "lte", "value": depth},
            },
        }

        response = client.post(url, headers=headers, json=data_payload)
        data = response.json()
        edges = data["results"][0]["metrics"][0]

        print(f"Depth {depth}: {edges:,} edges")

        if edges > max_edges or edges == previous_edges:
            return depth - 1 if depth > 1 else depth, previous_edges

        previous_edges = edges

    return depth, previous_edges

# Export link graph to CSV
def export_link_graph(org, project, analysis, chosen_depth, save_path="downloads"):
    """
    Export link graph up to the chosen depth level and save as a CSV.
    """
    url = "https://api.botify.com/v1/jobs"
    data_payload = {
        "job_type": "export",
        "payload": {
            "username": org,
            "project": project,
            "connector": "direct_download",
            "formatter": "csv",
            "export_size": 1000000,
            "query": {
                "collections": [f"crawl.{analysis}"],
                "query": {
                    "dimensions": [
                        "url",
                        f"crawl.{analysis}.outlinks_internal.graph.url",
                    ],
                    "metrics": [],
                    "filters": {"field": f"crawl.{analysis}.depth", "predicate": "lte", "value": chosen_depth},
                },
            },
        }
    }

    response = httpx.post(url, headers=headers, json=data_payload)
    export_job_details = response.json()
    job_url = f"https://api.botify.com{export_job_details.get('job_url')}"

    # Polling for job completion
    attempts = 300
    delay = 3
    while attempts > 0:
        time.sleep(delay)
        response_poll = httpx.get(job_url, headers=headers)
        job_status_details = response_poll.json()
        if job_status_details["job_status"] == "DONE":
            download_url = job_status_details["results"]["download_url"]
            save_as_filename = Path(save_path) / f"{org}_{project}_{analysis}_linkgraph_depth-{chosen_depth}.csv"
            download_file(download_url, save_as_filename)
            return save_as_filename
        elif job_status_details["job_status"] == "FAILED":
            print("Export job failed.")
            return None
        print(".", end="", flush=True)
        attempts -= 1

    print("Unable to complete download attempts successfully.")
    return None

# Download file function
def download_file(url, save_path):
    """
    Download a file from a URL to a specified local path.
    """
    # Fix: httpx.get() doesn't support 'stream' parameter directly
    with httpx.Client() as client:
        with client.stream("GET", url) as response:
            with open(save_path, "wb") as file:
                for chunk in response.iter_bytes(chunk_size=8192):
                    file.write(chunk)
    print(f"\nFile downloaded as '{save_path}'")

# Main execution
print("Determining optimal depth for link graph export...")
chosen_depth, final_edges = find_optimal_depth(org, project, analysis)
print(f"Using depth {chosen_depth} with {final_edges:,} edges for export.")

# Make sure the downloads folder exists
downloads_folder = Path("downloads")
downloads_folder.mkdir(parents=True, exist_ok=True)

print("Starting link graph export...")
link_graph_path = export_link_graph(org, project, analysis, chosen_depth, save_path="downloads")

if link_graph_path:
    print(f"Link graph saved to: {link_graph_path}")
else:
    print("Link graph export failed.")
```

**Sample Output**:
```
Determining optimal depth for link graph export...
Depth 1: 50,000 edges
Depth 2: 120,000 edges
Depth 3: 500,000 edges
Depth 4: 1,200,000 edges
Using depth 3 with 500,000 edges for export.
Starting link graph export...
Polling for job completion: ...
Download URL: https://botify-export-url.com/file.csv
File downloaded as 'downloads/org_project_analysis_linkgraph_depth-3.csv'
Link graph saved to: downloads/org_project_analysis_linkgraph_depth-3.csv
```

**Rationale**: And now, the moment you’ve all been waiting for—the elusive, hard-to-visualize link-graph of your website. Think Admiral Ackbar scrutinizing a hologram of the Death Star, examining every strength and vulnerability, now superimposed with Google Search Console Clicks and Impressions. The Rebels lean in, studying surprise hot spots and patches of dead wood. Every faceted search site ends up looking like the Death Star. But if you’ve done it right, with solid topical clustering, you’ll have something that resembles broccoli or cauliflower... are those called nodules? Florets? Either way, it’s a good look.


# Check Link-Graph Enhancements: How To Check What Data is Available to Enhance Link-Graph Visualization.

```python
import os
import json
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Load configuration and API key
headers = {
    "Authorization": f"Token {open('botify_token.txt').read().strip()}",
    "Content-Type": "application/json"
}

def preview_data(org, project, analysis, depth=1):
    """Preview data availability before committing to full download"""
    # Get analysis date from the slug (assuming YYYYMMDD format)
    analysis_date = datetime.strptime(analysis, '%Y%m%d')
    # Calculate period start (7 days before analysis date)
    period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
    period_end = analysis_date.strftime('%Y-%m-%d')
    
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    data_payload = {
        "collections": [
            f"crawl.{analysis}",
            "search_console"
        ],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url"
            ],
            "metrics": [
                "search_console.period_0.count_impressions",
                "search_console.period_0.count_clicks"
            ],
            "filters": {
                "field": f"crawl.{analysis}.depth",
                "predicate": "lte",
                "value": depth
            },
            "sort": [
                {
                    "field": "search_console.period_0.count_impressions",
                    "order": "desc"
                }
            ]
        },
        "periods": [
            [
                period_start,
                period_end
            ]
        ]
    }

    print(f"\n🔍 Sampling data for {org}/{project}/{analysis}")
    print("=" * 50)

    response = httpx.post(url, headers=headers, json=data_payload)
    if response.status_code != 200:
        print("❌ Preview failed:", response.status_code)
        return False
        
    data = response.json()
    if not data.get('results'):
        print("⚠️  No preview data available")
        return False
        
    print("\n📊 Data Sample Analysis")
    print("-" * 30)
    metrics_found = 0
    for result in data['results'][:3]:  # Show just top 3 for cleaner output
        url = result['dimensions'][0]
        impressions = result['metrics'][0]
        clicks = result['metrics'][1]
        metrics_found += bool(impressions or clicks)
        print(f"• URL: {url[:60]}...")
        print(f"  └─ Performance: {impressions:,} impressions, {clicks:,} clicks")
    
    print("\n🎯 Data Quality Check")
    print("-" * 30)
    print(f"✓ URLs found: {len(data['results'])}")
    print(f"✓ Search metrics: {'Available' if metrics_found else 'Not found'}")
    print(f"✓ Depth limit: {depth}")
    
    return True

def get_bqlv2_data(org, project, analysis):
    """Fetch data based on BQLv2 query for a specific Botify analysis."""
    collection = f"crawl.{analysis}"
    
    # Calculate dates
    analysis_date = datetime.strptime(analysis, '%Y%m%d')
    period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
    period_end = analysis_date.strftime('%Y-%m-%d')
    
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # Base dimensions that should always be available in crawl
    base_dimensions = [
        f"{collection}.url",
        f"{collection}.depth",
    ]
    
    # Optional dimensions that might not be available
    optional_dimensions = [
        f"{collection}.segments.pagetype.value",
        f"{collection}.compliant.is_compliant",
        f"{collection}.compliant.main_reason",
        f"{collection}.canonical.to.equal",
        f"{collection}.sitemaps.present",
        f"{collection}.js.rendering.exec",
        f"{collection}.js.rendering.ok"
    ]
    
    # Optional metrics from other collections
    optional_metrics = [
        "search_console.period_0.count_impressions",
        "search_console.period_0.count_clicks"
    ]
    
    # First, let's check which collections are available
    collections = [collection]  # Using full collection name
    try:
        # We could add an API call here to check available collections
        # For now, let's assume search_console might be available
        collections.append("search_console")
    except Exception as e:
        print(f"Search Console data not available: {e}")
    
    data_payload = {
        "collections": collections,
        "query": {
            "dimensions": base_dimensions + optional_dimensions,
            "metrics": optional_metrics if "search_console" in collections else [],
            "filters": {
                "field": f"{collection}.depth",
                "predicate": "lte",
                "value": 2
            },
            "sort": [
                {
                    "field": "search_console.period_0.count_impressions" if "search_console" in collections else f"{collection}.depth",
                    "order": "desc" if "search_console" in collections else "asc"
                }
            ]
        },
        "periods": [[period_start, period_end]] if "search_console" in collections else None
    }

    print(f"Query payload: {json.dumps(data_payload, indent=2)}")
    response = httpx.post(url, headers=headers, json=data_payload)
    
    if response.status_code != 200:
        print(f"Error response: {response.text}")
        response.raise_for_status()
    
    data = response.json()
    
    # Define all possible columns
    all_columns = ['url', 'depth', 'pagetype', 'compliant', 'reason', 'canonical', 
                  'sitemap', 'js_exec', 'js_ok', 'impressions', 'clicks']
    
    # Create DataFrame with available data
    results = []
    for item in data['results']:
        # Fill missing dimensions/metrics with None
        row = item['dimensions']
        if 'metrics' in item:
            row.extend(item['metrics'])
        while len(row) < len(all_columns):
            row.append(None)
        results.append(row)
    
    df = pd.DataFrame(results, columns=all_columns)
    
    return df

def fetch_fields(org: str, project: str, collection: str) -> List[str]:
    """
    Fetch available fields for a given collection from the Botify API.
    
    Args:
        org: Organization slug
        project: Project slug  
        collection: Collection name (e.g. 'crawl.20241108')
        
    Returns:
        List of field IDs available in the collection
    """
    fields_url = f"https://api.botify.com/v1/projects/{org}/{project}/collections/{collection}"
    
    try:
        response = httpx.get(fields_url, headers=headers)
        response.raise_for_status()
        fields_data = response.json()
        return [
            field['id'] 
            for dataset in fields_data.get('datasets', [])
            for field in dataset.get('fields', [])
        ]
    except httpx.RequestError as e:
        print(f"Error fetching fields for collection '{collection}': {e}")
        return []

def check_compliance_fields(org, project, analysis):
    """Check available compliance fields in a more structured way."""
    collection = f"crawl.{analysis}"
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # Group compliance fields by category
    compliance_categories = {
        'Basic Compliance': [
            'compliant.is_compliant',
            'compliant.main_reason',
            'compliant.reason.http_code',
            'compliant.reason.content_type',
            'compliant.reason.canonical',
            'compliant.reason.noindex',
            'compliant.detailed_reason'
        ],
        'Performance': [
            'scoring.issues.slow_first_to_last_byte_compliant',
            'scoring.issues.slow_render_time_compliant',
            'scoring.issues.slow_server_time_compliant',
            'scoring.issues.slow_load_time_compliant'
        ],
        'SEO': [
            'scoring.issues.duplicate_query_kvs_compliant'
        ],
        'Outlinks': [
            'outlinks_errors.non_compliant.nb.follow.unique',
            'outlinks_errors.non_compliant.nb.follow.total',
            'outlinks_errors.non_compliant.urls'
        ]
    }
    
    print("\n🔍 Field Availability Analysis")
    print("=" * 50)
    available_count = 0
    total_count = sum(len(fields) for fields in compliance_categories.values())
    
    available_fields = []
    for category, fields in compliance_categories.items():
        available_in_category = 0
        print(f"\n📑 {category}")
        print("-" * 30)
        for field in fields:
            full_field = f"{collection}.{field}"
            # Test field availability with a minimal query
            test_query = {
                "collections": [collection],
                "query": {
                    "dimensions": [full_field],
                    "filters": {"field": f"{collection}.depth", "predicate": "eq", "value": 0}
                }
            }
            
            try:
                response = httpx.post(url, headers=headers, json=test_query, timeout=60)
                if response.status_code == 200:
                    available_in_category += 1
                    available_count += 1
                    print(f"✓ {field.split('.')[-1]}")
                    available_fields.append(field)
                else:
                    print(f"× {field.split('.')[-1]}")
            except Exception as e:
                print(f"? {field.split('.')[-1]} (error checking)")
    
    coverage = (available_count / total_count) * 100
    print(f"\n📊 Field Coverage: {coverage:.1f}%")
    return available_fields

def main():
    """Main execution logic"""
    try:
        with open('config.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json file not found")
        return
    except json.JSONDecodeError:
        print("Error: config.json is not valid JSON")
        return
    
    org = config.get('org')
    project = config.get('project')
    analysis = config.get('analysis')
    
    if not all([org, project, analysis]):
        print("Error: Missing required fields in config.json (org, project, analysis)")
        return
    
    print("Previewing data availability...")
    if preview_data(org, project, analysis, depth=2):
        print("Data preview successful. Proceeding with full export...")
        print("Fetching BQLv2 data...")
        df = get_bqlv2_data(org, project, analysis)
        print("\nData Preview:")
        print(df.head())

        # Save to CSV
        Path("downloads").mkdir(parents=True, exist_ok=True)
        output_file = f"downloads/{org}_{project}_{analysis}_metadata.csv"
        df.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")
        
        # Use check_compliance_fields
        check_compliance_fields(org, project, analysis)
    else:
        print("Data preview failed. Please check configuration and try again.")

if __name__ == "__main__":
    main()
```

**Sample Output**:

    Previewing data availability...
    
    🔍 Sampling data for example/retail-division/20241108
    ==================================================
    
    📊 Data Sample Analysis
    ------------------------------
    • URL: https://www.example.com/...
      └─ Performance: 123,456 impressions, 12,345 clicks
    • URL: https://www.example.com/site/retail/seasonal-sale/pcmcat...
      └─ Performance: 98,765 impressions, 8,765 clicks
    • URL: https://www.example.com/site/misc/daily-deals/pcmcat2480...
      └─ Performance: 54,321 impressions, 4,321 clicks
    
    🎯 Data Quality Check
    ------------------------------
    ✓ URLs found: 404
    ✓ Search metrics: Available
    ✓ Depth limit: 2
    Data preview successful. Proceeding with full export...
    Fetching BQLv2 data...
    Query payload: {
      "collections": [
        "crawl.20241108",
        "search_console"
      ],
      "query": {
        "dimensions": [
          "crawl.20241108.url",
          "crawl.20241108.depth",
          "crawl.20241108.segments.pagetype.value",
          "crawl.20241108.compliant.is_compliant",
          "crawl.20241108.compliant.main_reason",
          "crawl.20241108.canonical.to.equal",
          "crawl.20241108.sitemaps.present",
          "crawl.20241108.js.rendering.exec",
          "crawl.20241108.js.rendering.ok"
        ],
        "metrics": [
          "search_console.period_0.count_impressions",
          "search_console.period_0.count_clicks"
        ],
        "filters": {
          "field": "crawl.20241108.depth",
          "predicate": "lte",
          "value": 2
        },
        "sort": [
          {
            "field": "search_console.period_0.count_impressions",
            "order": "desc"
          }
        ]
      },
      "periods": [
        [
          "2024-11-01",
          "2024-11-08"
        ]
      ]
    }
    
    Data Preview:
                                                                                                                            url  \
    0  https://www.example.com/realm/shops/merchants-quarter/enchanted-items/
    1  https://www.example.com/realm/elven-moonlight-potion-azure/
    2  https://www.example.com/realm/dwarven-decorative-runes-sapphire/   
    3  https://www.example.com/realm/legendary-artifacts/master-crafted-items/   
    4  ttps://www.example.com/realm/orcish-war-drums-obsidian/    
    
       depth       pagetype  compliant     reason canonical  sitemap  js_exec  \
    0      0           home       True  Indexable      True    False     True   
    1      2            pdp       True  Indexable      True    False     True   
    2      1            plp       True  Indexable      True    False     True   
    3      1       category       True  Indexable      True    False     True   
    4      1           main       True  Indexable      True    False     True   
    
       js_ok  impressions  clicks  
    0  False       123456   12345  
    1  False        98765    8765  
    2  False        54321    4321  
    3  False        11111    1111  
    4  False        12345    1234  
    
    Data saved to downloads/example_retail-division_20241108_metadata.csv

**Rationale**: Just because you happen to work at an enterprise SEO company and possess this peculiar intersection of skills—like crafting prompts that give LLMs instant deep-knowledge (think Neo suddenly knowing kung fu)—doesn't mean you actually understand BQL. In fact, needing to write this prompt rather proves the opposite... wait, did I just create a paradox? Anyway, there's a very subtle chicken-and-egg problem that this file in general and this example in particular helps address: ***validation of collection fields*** so you can template automations without them being too fragile.


# Color-Code Link-Graphs: How To Download Data to Enhance Website Link-Graph Visualization.

```python
import os
import json
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import gzip
import shutil
import time

# Load configuration and API key
headers = {
    "Authorization": f"Token {open('botify_token.txt').read().strip()}",
    "Content-Type": "application/json"
}

def preview_data(org, project, analysis, depth=1):
    """Preview data availability before committing to full download"""
    # Get analysis date from the slug (assuming YYYYMMDD format)
    analysis_date = datetime.strptime(analysis, '%Y%m%d')
    # Calculate period start (7 days before analysis date)
    period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
    period_end = analysis_date.strftime('%Y-%m-%d')
    
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    data_payload = {
        "collections": [
            f"crawl.{analysis}",
            "search_console"
        ],
        "query": {
            "dimensions": [
                f"crawl.{analysis}.url"
            ],
            "metrics": [
                "search_console.period_0.count_impressions",
                "search_console.period_0.count_clicks"
            ],
            "filters": {
                "field": f"crawl.{analysis}.depth",
                "predicate": "lte",
                "value": depth
            },
            "sort": [
                {
                    "field": "search_console.period_0.count_impressions",
                    "order": "desc"
                }
            ]
        },
        "periods": [
            [
                period_start,
                period_end
            ]
        ]
    }

    print(f"\n🔍 Sampling data for {org}/{project}/{analysis}")
    print("=" * 50)

    response = httpx.post(url, headers=headers, json=data_payload)
    if response.status_code != 200:
        print("❌ Preview failed:", response.status_code)
        return False
        
    data = response.json()
    if not data.get('results'):
        print("⚠️  No preview data available")
        return False
        
    print("\n📊 Data Sample Analysis")
    print("-" * 30)
    metrics_found = 0
    for result in data['results'][:3]:  # Show just top 3 for cleaner output
        url = result['dimensions'][0]
        impressions = result['metrics'][0]
        clicks = result['metrics'][1]
        metrics_found += bool(impressions or clicks)
        print(f"• URL: {url[:60]}...")
        print(f"  └─ Performance: {impressions:,} impressions, {clicks:,} clicks")
    
    print("\n🎯 Data Quality Check")
    print("-" * 30)
    print(f"✓ URLs found: {len(data['results'])}")
    print(f"✓ Search metrics: {'Available' if metrics_found else 'Not found'}")
    print(f"✓ Depth limit: {depth}")
    
    return True

def get_bqlv2_data(org, project, analysis):
    """Fetch BQLv2 data using jobs endpoint"""
    # Calculate periods
    analysis_date = datetime.strptime(analysis, '%Y%m%d')
    period_start = (analysis_date - timedelta(days=7)).strftime('%Y-%m-%d')
    period_end = analysis_date.strftime('%Y-%m-%d')
    
    url = "https://api.botify.com/v1/jobs"
    
    data_payload = {
        "job_type": "export",
        "payload": {
            "username": org,
            "project": project,
            "connector": "direct_download",
            "formatter": "csv",
            "export_size": 1000000,
            "query": {
                "collections": [
                    f"crawl.{analysis}",
                    "search_console"
                ],
                "periods": [[period_start, period_end]],
                "query": {
                    "dimensions": [
                        f"crawl.{analysis}.url", 
                        f"crawl.{analysis}.depth",
                        f"crawl.{analysis}.segments.pagetype.value",
                        f"crawl.{analysis}.compliant.is_compliant",
                        f"crawl.{analysis}.compliant.main_reason",
                        f"crawl.{analysis}.canonical.to.equal",
                        f"crawl.{analysis}.sitemaps.present",
                        f"crawl.{analysis}.js.rendering.exec",
                        f"crawl.{analysis}.js.rendering.ok"
                    ],
                    "metrics": [
                        "search_console.period_0.count_impressions",
                        "search_console.period_0.count_clicks"
                    ],
                    "filters": {
                        "field": f"crawl.{analysis}.depth",
                        "predicate": "lte",
                        "value": 2
                    }
                }
            }
        }
    }

    print("\nStarting export job...")
    response = httpx.post(url, json=data_payload, headers=headers)
    job_data = response.json()
    job_url = f"https://api.botify.com{job_data['job_url']}"
    print(f"Job created successfully (ID: {job_data['job_id']})")
    
    print("\nPolling for job completion: ", end="", flush=True)
    while True:
        time.sleep(5)  # Poll every 5 seconds
        status = httpx.get(job_url, headers=headers).json()
        print(f"\nCurrent status: {status['job_status']}")
        
        if status['job_status'] in ['COMPLETE', 'DONE']:
            download_url = status['results']['download_url']
            print(f"\nDownload URL: {download_url}")
            
            # Download and process the file
            gz_filename = "export.csv.gz"
            csv_filename = "export.csv"
            
            # Download gzipped file
            response = httpx.get(download_url)
            with open(gz_filename, "wb") as gz_file:
                gz_file.write(response.content)
            print(f"File downloaded as '{gz_filename}'")
            
            # Decompress and read into DataFrame
            with gzip.open(gz_filename, "rb") as f_in:
                with open(csv_filename, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print(f"File decompressed as '{csv_filename}'")
            
            # Read CSV into DataFrame
            df = pd.read_csv(csv_filename, names=[
                'url', 'depth', 'pagetype', 'compliant', 'reason', 
                'canonical', 'sitemap', 'js_exec', 'js_ok',
                'impressions', 'clicks'
            ])
            
            # Cleanup temporary files
            os.remove(gz_filename)
            os.remove(csv_filename)
            
            return df
            
        elif status['job_status'] == 'FAILED':
            print(f"\nJob failed. Error details: {status}")
            raise Exception("Export job failed")
            
        elif status['job_status'] in ['CREATED', 'PROCESSING']:
            print(".", end="", flush=True)
            continue
            
        else:
            print(f"\nUnexpected status: {status}")
            raise Exception(f"Unexpected job status: {status['job_status']}")

def fetch_fields(org: str, project: str, collection: str) -> List[str]:
    """
    Fetch available fields for a given collection from the Botify API.
    
    Args:
        org: Organization slug
        project: Project slug  
        collection: Collection name (e.g. 'crawl.20241108')
        
    Returns:
        List of field IDs available in the collection
    """
    fields_url = f"https://api.botify.com/v1/projects/{org}/{project}/collections/{collection}"
    
    try:
        response = httpx.get(fields_url, headers=headers)
        response.raise_for_status()
        fields_data = response.json()
        return [
            field['id'] 
            for dataset in fields_data.get('datasets', [])
            for field in dataset.get('fields', [])
        ]
    except httpx.RequestError as e:
        print(f"Error fetching fields for collection '{collection}': {e}")
        return []

def check_compliance_fields(org, project, analysis):
    """Check available compliance fields in a more structured way."""
    collection = f"crawl.{analysis}"
    url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
    
    # Group compliance fields by category
    compliance_categories = {
        'Basic Compliance': [
            'compliant.is_compliant',
            'compliant.main_reason',
            'compliant.reason.http_code',
            'compliant.reason.content_type',
            'compliant.reason.canonical',
            'compliant.reason.noindex',
            'compliant.detailed_reason'
        ],
        'Performance': [
            'scoring.issues.slow_first_to_last_byte_compliant',
            'scoring.issues.slow_render_time_compliant',
            'scoring.issues.slow_server_time_compliant',
            'scoring.issues.slow_load_time_compliant'
        ],
        'SEO': [
            'scoring.issues.duplicate_query_kvs_compliant'
        ],
        'Outlinks': [
            'outlinks_errors.non_compliant.nb.follow.unique',
            'outlinks_errors.non_compliant.nb.follow.total',
            'outlinks_errors.non_compliant.urls'
        ]
    }
    
    print("\n🔍 Field Availability Analysis")
    print("=" * 50)
    available_count = 0
    total_count = sum(len(fields) for fields in compliance_categories.values())
    
    available_fields = []
    for category, fields in compliance_categories.items():
        available_in_category = 0
        print(f"\n📑 {category}")
        print("-" * 30)
        for field in fields:
            full_field = f"{collection}.{field}"
            # Test field availability with a minimal query
            test_query = {
                "collections": [collection],
                "query": {
                    "dimensions": [full_field],
                    "filters": {"field": f"{collection}.depth", "predicate": "eq", "value": 0}
                }
            }
            
            try:
                response = httpx.post(url, headers=headers, json=test_query)
                if response.status_code == 200:
                    available_in_category += 1
                    available_count += 1
                    print(f"✓ {field.split('.')[-1]}")
                    available_fields.append(field)
                else:
                    print(f"× {field.split('.')[-1]}")
            except Exception as e:
                print(f"? {field.split('.')[-1]} (error checking)")
    
    coverage = (available_count / total_count) * 100
    print(f"\n📊 Field Coverage: {coverage:.1f}%")
    return available_fields

def download_and_process_csv(download_url, output_filename):
    """Download and decompress CSV from Botify API."""
    gz_filename = f"{output_filename}.gz"
    
    # Download gzipped file
    response = httpx.get(download_url)
    with open(gz_filename, "wb") as gz_file:
        gz_file.write(response.content)
    print(f"Downloaded: {gz_filename}")
    
    # Decompress to CSV
    with gzip.open(gz_filename, "rb") as f_in:
        with open(output_filename, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f"Decompressed to: {output_filename}")
    
    # Cleanup
    os.remove(gz_filename)
    return True

def main():
    """Main execution logic"""
    try:
        with open('config.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json file not found")
        return
    except json.JSONDecodeError:
        print("Error: config.json is not valid JSON")
        return
    
    org = config.get('org')
    project = config.get('project')
    analysis = config.get('analysis')
    
    if not all([org, project, analysis]):
        print("Error: Missing required fields in config.json (org, project, analysis)")
        return
    
    print("Previewing data availability...")
    if preview_data(org, project, analysis, depth=2):
        print("Data preview successful. Proceeding with full export...")
        print("Fetching BQLv2 data...")
        df = get_bqlv2_data(org, project, analysis)
        print("\nData Preview:")
        print(df.head())

        # Save to CSV
        Path("downloads").mkdir(parents=True, exist_ok=True)
        output_file = f"downloads/{org}_{project}_{analysis}_metadata.csv"
        df.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")
        
        # Use check_compliance_fields
        check_compliance_fields(org, project, analysis)
    else:
        print("Data preview failed. Please check configuration and try again.")

if __name__ == "__main__":
    main()
```

**Sample Output**:

    Previewing data availability...
    
    🔍 Sampling data for example/retail-division/20241108
    ==================================================
    
    📊 Data Sample Analysis
    ------------------------------
    • URL: https://www.example.com/...
      └─ Performance: 123,456 impressions, 12,345 clicks
    • URL: https://www.example.com/site/retail/seasonal-sale/pcmcat...
      └─ Performance: 98,765 impressions, 8,765 clicks
    • URL: https://www.example.com/site/misc/daily-deals/pcmcat2480...
      └─ Performance: 54,321 impressions, 4,321 clicks
    
    🎯 Data Quality Check
    ------------------------------
    ✓ URLs found: 404
    ✓ Search metrics: Available
    ✓ Depth limit: 2
    Data preview successful. Proceeding with full export...
    Fetching BQLv2 data...
    
    Starting export job...
    Job created successfully (ID: 12345)
    
    Polling for job completion: 
    Current status: CREATED
    .
    Current status: PROCESSING
    .
    Current status: DONE
    
    Download URL: https://example.cloudfront.net/exports/a/b/c/abc123def456/example-2024-11-10.csv.gz
    File downloaded as 'export.csv.gz'
    File decompressed as 'export.csv'
    
    Data Preview:
                                                                                                                            url  \
    0  https://www.example.com/realm/shops/merchants-quarter/enchanted-items/
    1  https://www.example.com/realm/elven-moonlight-potion-azure/
    2  https://www.example.com/realm/dwarven-decorative-runes-sapphire/   
    3  https://www.example.com/realm/legendary-artifacts/master-crafted-items/   
    4  ttps://www.example.com/realm/orcish-war-drums-obsidian/  
    
       depth             pagetype  compliant     reason canonical  sitemap  \
    0      2             category       True  Indexable      True    False   
    1      2                  pdp       True  Indexable      True     True   
    2      2                  plp       True  Indexable      True     True   
    3      2               review       True  Indexable      True    False   
    4      2                 main       True  Indexable      True     True   
    
       js_exec  js_ok  impressions  clicks  
    0     True  False       12345     123   
    1     True  False        9876      98   
    2     True  False        5432      54   
    3     True  False        1111      11   
    4     True  False         987       9   
    
    Data saved to downloads/example_retail-division_20241108_metadata.csv

**Rationale**: BQL and enterprise SEO diagnostics provide powerful tools for comprehensive website analysis. This code transforms link structures into detailed visualizations of your site's SEO health, presenting search signals and performance metrics in a multi-dimensional view. Similar to how diagnostic imaging reveals underlying conditions, these analyses expose strengths, vulnerabilities, and technical issues within your site architecture. Prepare your site for the increasing number of AI crawlers by optimizing your content and structure. Ensure your schema.org structured data is properly implemented to support real-time crawls that evaluate product availability and other critical information.
 
Next-generation SEO requires adapting to these AI-driven changes. Now, let's examine the process of converting from BQLv1 to the collection-based BQLv2 format...

<!-- #region -->
# Migrating from BQLv1 to BQLv2

This guide explains how to convert BQLv1 queries to BQLv2 format, with practical examples and validation helpers.

## Core Concepts

### API Endpoint Changes

- **BQLv1**: `/v1/analyses/{username}/{website}/{analysis}/urls`
- **BQLv2**: `/v1/projects/{username}/{website}/query`

### Key Structural Changes

1. Collections replace URL parameters
2. Fields become dimensions
3. All fields require collection prefixes
4. Areas are replaced with explicit filters

## Query Conversion Examples

### 1. Basic URL Query

```json
// BQLv1 (/v1/analyses/user/site/20210801/urls?area=current&previous_crawl=20210715)
{
  "fields": [
    "url",
    "http_code",
    "previous.http_code"
  ],
  "filters": {
    "field": "indexable.is_indexable",
    "predicate": "eq",
    "value": true
  }
}

// BQLv2 (/v1/projects/user/site/query)
{
  "collections": [
    "crawl.20210801",
    "crawl.20210715"
  ],
  "query": {
    "dimensions": [
      "crawl.20210801.url",
      "crawl.20210801.http_code",
      "crawl.20210715.http_code"
    ],
    "metrics": [],
    "filters": {
      "field": "crawl.20210801.indexable.is_indexable",
      "predicate": "eq",
      "value": true
    }
  }
}
```

### 2. Aggregation Query

```json
// BQLv1 (/v1/analyses/user/site/20210801/urls/aggs)
[
  {
    "aggs": [
      {
        "metrics": ["count"],
        "group_by": [
          {
            "distinct": {
              "field": "segments.pagetype.depth_1",
              "order": {"value": "asc"},
              "size": 300
            }
          }
        ]
      }
    ]
  }
]

// BQLv2
{
  "collections": ["crawl.20210801"],
  "query": {
    "dimensions": [
      "crawl.20210801.segments.pagetype.depth_1"
    ],
    "metrics": [
      "crawl.20210801.count_urls_crawl"
    ],
    "sort": [0]
  }
}
```

### 3. Area Filters

BQLv1's area parameter is replaced with explicit filters in BQLv2:

#### New URLs Filter
```json
{
  "and": [
    {
      "field": "crawl.20210801.url_exists_crawl",
      "value": true
    },
    {
      "field": "crawl.20210715.url_exists_crawl",
      "value": false
    }
  ]
}
```

#### Disappeared URLs Filter
```json
{
  "and": [
    {
      "field": "crawl.20210801.url_exists_crawl",
      "value": false
    },
    {
      "field": "crawl.20210715.url_exists_crawl",
      "value": true
    }
  ]
}
```

## Conversion Helper Functions

```python
def validate_bql_v2(query):
    """Validate BQLv2 query structure"""
    required_keys = {'collections', 'query'}
    query_keys = {'dimensions', 'metrics', 'filters'}
    
    if not all(key in query for key in required_keys):
        raise ValueError(f"Missing required keys: {required_keys}")
    if not any(key in query['query'] for key in query_keys):
        raise ValueError(f"Query must contain one of: {query_keys}")
    for collection in query['collections']:
        if not collection.startswith('crawl.'):
            raise ValueError(f"Invalid collection format: {collection}")
    return True

def convert_url_query(query_v1, current_analysis, previous_analysis=None):
    """Convert BQLv1 URL query to BQLv2"""
    collections = [f"crawl.{current_analysis}"]
    if previous_analysis:
        collections.append(f"crawl.{previous_analysis}")
    
    # Convert fields to dimensions
    dimensions = []
    for field in query_v1.get('fields', []):
        if field.startswith('previous.'):
            if not previous_analysis:
                raise ValueError("Previous analysis required for previous fields")
            field = field.replace('previous.', '')
            dimensions.append(f"crawl.{previous_analysis}.{field}")
        else:
            dimensions.append(f"crawl.{current_analysis}.{field}")
    
    # Convert filters
    filters = None
    if 'filters' in query_v1:
        filters = {
            "field": f"crawl.{current_analysis}.{query_v1['filters']['field']}",
            "predicate": query_v1['filters']['predicate'],
            "value": query_v1['filters']['value']
        }
    
    query_v2 = {
        "collections": collections,
        "query": {
            "dimensions": dimensions,
            "metrics": [],
            "filters": filters
        }
    }
    
    validate_bql_v2(query_v2)
    return query_v2
```

## Key Conversion Rules

1. **Collections**
   - Add `collections` array with `crawl.{analysis}` format
   - Include both analyses for comparison queries

2. **Fields to Dimensions**
   - Prefix fields with `crawl.{analysis}.`
   - Replace `previous.` prefix with `crawl.{previous_analysis}.`

3. **Metrics**
   - Convert aggregation metrics to appropriate BQLv2 metric fields
   - Use empty array when no metrics needed

4. **Filters**
   - Prefix filter fields with collection name
   - Replace area parameters with explicit URL existence filters
<!-- #endregion -->

# All Botify API Endpoints: How Do You Generate a Python Code Example for Every Botify Endpoint Given Their OpenAPI Swagger

Botify OpenAPI Swagger File: [https://api.botify.com/v1/swagger.json](https://api.botify.com/v1/swagger.json)

```python
# Everything From Botify OpenAPI Swagger File: https://api.botify.com/v1/swagger.json
import httpx
import json
from pathlib import Path
from typing import Dict, Any

def generate_python_example(method: str, path: str, params: Dict, config: Dict, description: str = "", show_config: bool = False) -> str:
    """Craft a Python invocation example for a given API endpoint"""
    docstring = f'    """{description}"""\n' if description else ""
    
    lines = [
        "```python",
        "# Summon the necessary artifacts",
        "import httpx",
        "import json",
        "",
        "def example_request():",
        "\n",
        docstring
    ]
    
    if show_config:
        lines.extend([
            "# Your configuration sigil should contain:",
            "#   - token: Your API token",
            "#   - org: Your organization ID",
            "#   - project: Your project ID",
            "#   - analysis: Your analysis ID",
            "#   - collection: Your collection ID",
            "",
            "# Load token from secure storage",
            'with open("botify_token.txt") as f:',
            '    token = f.read().strip()',
            ''
        ])
    
    # Format the URL and parameters
    url = f"url = f'https://api.botify.com/v1{path}'"
    lines.extend([
        "# Craft the invocation URL",
        url,
        "",
        "# Prepare the headers for your spell",
        'headers = {',
        '    "Authorization": f"Token {token}",',
        '    "Content-Type": "application/json"',
        '}',
        ''
    ])
    
    # Add method-specific code
    if method.lower() in ['post', 'put', 'patch']:
        lines.extend([
            "# Define the payload for your invocation",
            "data = {",
            '    # Add your request parameters here',
            "}",
            "",
            "# Cast the spell",
            f"response = httpx.{method.lower()}(url, headers=headers, json=data)",
            ""
        ])
    else:
        lines.extend([
            "# Cast the spell",
            f"response = httpx.{method.lower()}(url, headers=headers)",
            ""
        ])
    
    lines.extend([
        "# Interpret the response",
        "if response.status_code == 200:",
        "    result = response.json()",
        "    print(json.dumps(result, indent=2))",
        "else:",
        "    print(f'Error: {response.status_code}')",
        "    print(response.text)"
    ])
    
    lines.append("```")
    return "\n".join(line for line in lines if line)

def generate_markdown(spec: Dict[str, Any], config: Dict[str, str]) -> str:
    md_lines = [
        "## Everything From Botify OpenAPI Swagger File: https://api.botify.com/v1/swagger.json",
        "",
        "Having mastered the arts of BQL, we now document the full spectrum of API invocations.",
        "Each endpoint is presented with its purpose, capabilities, and Python implementation.",
        "",
        "### Endpoint Categories",
        ""
    ]
    
    endpoints_by_tag = {}
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            if method == 'parameters':
                continue
            tag = details.get('tags', ['Untagged'])[0]
            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []
            endpoints_by_tag[tag].append((method, path, details))
    
    first_example = True
    for tag in sorted(endpoints_by_tag.keys()):
        md_lines.extend([
            f"#### {tag} Invocations",
            "",
            f"These endpoints allow you to manipulate {tag.lower()} aspects of your digital realm.",
            ""
        ])
        
        for method, path, details in sorted(endpoints_by_tag[tag]):
            description = details.get('description', '')
            summary = details.get('summary', '')
            parameters = details.get('parameters', [])
            responses = details.get('responses', {})
            
            # Create a semantic block for LLMs
            md_lines.extend([
                f"##### {method.upper()} {path}",
                "",
                "**Purpose:**",
                summary or "No summary provided.",
                "",
                "**Detailed Description:**",
                description or "No detailed description available.",
                "",
                "**Parameters Required:**",
                "```",
                "\n".join(f"- {p.get('name')}: {p.get('description', 'No description')}" 
                         for p in parameters) if parameters else "No parameters required",
                "```",
                "",
                "**Expected Responses:**",
                "```",
                "\n".join(f"- {code}: {details.get('description', 'No description')}" 
                         for code, details in responses.items()),
                "```",
                "",
                "**Example Implementation:**",
                generate_python_example(method, path, details, config, 
                                     description=description, show_config=first_example),
                "",
                "---",
                ""
            ])
            first_example = False
    
    # Add a section specifically for LLM understanding
    md_lines.extend([
        "### LLM Guidance",
        "",
        "When deciding which endpoint to use:",
        "1. Consider the category (tag) that matches your task",
        "2. Review the Purpose and Description to ensure alignment",
        "3. Check the required parameters match your available data",
        "4. Verify the expected responses meet your needs",
        "",
        "Example prompt format:",
        '```',
        'I need to [task description]. I have access to [available data].',
        'Which endpoint would be most appropriate?',
        '```',
        ""
    ])
    
    return "\n".join(md_lines)

# First, ensure we have our token
if not Path("botify_token.txt").exists():
    print("Please run the authentication cell first to create your token file.")
else:
    # Load token
    with open("botify_token.txt") as f:
        token = f.read().strip()
    
    # Use existing configuration from earlier cells
    config = {
        "token": token,
        # These will be used as placeholders in examples
        "org": "{org_id}",
        "project": "{project_id}",
        "analysis": "{analysis_id}",
        "collection": "{collection_id}"
    }
    
    # Fetch the API specification
    try:
        response = httpx.get("https://api.botify.com/v1/swagger.json", 
                              headers={"Authorization": f"Token {token}"})
        spec = response.json()
        
        # Generate and display the markdown
        markdown_content = generate_markdown(spec, config)
        print("API documentation generated successfully!")
        
        # The markdown content will be rendered in the next cell
    except Exception as e:
        print(f"Error fetching API specification: {e}")
print(markdown_content)
```

<!-- #region -->
API documentation generated successfully!
## Everything From Botify OpenAPI Swagger File: https://api.botify.com/v1/swagger.json

Having mastered the arts of BQL, we now document the full spectrum of API invocations.
Each endpoint is presented with its purpose, capabilities, and Python implementation.

### Endpoint Categories

#### Analysis Invocations

These endpoints allow you to manipulate analysis aspects of your digital realm.

##### GET /analyses/{username}/{project_slug}/{analysis_slug}

**Purpose:**
No summary provided.

**Detailed Description:**
Get an Analysis detail

**Parameters Required:**
```
- previous_crawl: Previous analysis identifier
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get an Analysis detail"""

# Your configuration sigil should contain:
#   - token: Your API token
#   - org: Your organization ID
#   - project: Your project ID
#   - analysis: Your analysis ID
#   - collection: Your collection ID
# Load token from secure storage
with open("botify_token.txt") as f:
    token = f.read().strip()
# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics

**Purpose:**
No summary provided.

**Detailed Description:**
Return global statistics for an analysis

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Return global statistics for an analysis"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/time

**Purpose:**
No summary provided.

**Detailed Description:**
Return crawl statistics grouped by time frequency (1 min, 5 mins or 60 min) for an analysis

**Parameters Required:**
```
- limit: max number of elements to retrieve
- frequency: Aggregation frequency
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Return crawl statistics grouped by time frequency (1 min, 5 mins or 60 min) for an analysis"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/time'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/urls/{list_type}

**Purpose:**
No summary provided.

**Detailed Description:**
Return a list of 1000 latest URLs crawled (all crawled URLs or only URLS with HTTP errors)

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Return a list of 1000 latest URLs crawled (all crawled URLs or only URLS with HTTP errors)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/urls/{list_type}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/ganalytics/orphan_urls/{medium}/{source}

**Purpose:**
Legacy

**Detailed Description:**
Legacy    List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Legacy    List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/ganalytics/orphan_urls/{medium}/{source}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/links/percentiles

**Purpose:**
No summary provided.

**Detailed Description:**
Get inlinks percentiles

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get inlinks percentiles"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/links/percentiles'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/pagerank/lost

**Purpose:**
No summary provided.

**Detailed Description:**
Lost pagerank

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Lost pagerank"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/pagerank/lost'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/scoring/summary

**Purpose:**
No summary provided.

**Detailed Description:**
Scoring summary

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Scoring summary"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/scoring/summary'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/search_console/stats

**Purpose:**
No summary provided.

**Detailed Description:**
List clicks and impressions per day

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List clicks and impressions per day"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/search_console/stats'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/report

**Purpose:**
No summary provided.

**Detailed Description:**
Get global information of the sitemaps found (sitemaps indexes, invalid sitemaps urls, etc.)

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get global information of the sitemaps found (sitemaps indexes, invalid sitemaps urls, etc.)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/report'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/out_of_config

**Purpose:**
No summary provided.

**Detailed Description:**
Sample list of URLs which were found in your sitemaps but outside of the crawl perimeter defined for the project, for instance domain/subdomain or protocol (HTTP/HTTPS) not allowed in the crawl settings.

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Sample list of URLs which were found in your sitemaps but outside of the crawl perimeter defined for the project, for instance domain/subdomain or protocol (HTTP/HTTPS) not allowed in the crawl settings."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/out_of_config'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/sitemap_only

**Purpose:**
No summary provided.

**Detailed Description:**
Sample list of URLs which were found in your sitemaps, within the project allowed scope (allowed domains/subdomains/protocols), but not found by the Botify crawler.

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Sample list of URLs which were found in your sitemaps, within the project allowed scope (allowed domains/subdomains/protocols), but not found by the Botify crawler."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/sitemap_only'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/domains

**Purpose:**
No summary provided.

**Detailed Description:**
Top domains

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Top domains"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/domains'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/subdomains

**Purpose:**
No summary provided.

**Detailed Description:**
Top subddomains

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Top subddomains"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/subdomains'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/features/visits/orphan_urls/{medium}/{source}

**Purpose:**
No summary provided.

**Detailed Description:**
List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/features/visits/orphan_urls/{medium}/{source}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/segments

**Purpose:**
No summary provided.

**Detailed Description:**
Get the segments feature public metadata of an analysis.

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get the segments feature public metadata of an analysis."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/segments'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes

**Purpose:**
No summary provided.

**Detailed Description:**
Return an object containing all robots.txt files found on the project's domains. The object is null for virtual robots.txt.

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Return an object containing all robots.txt files found on the project's domains. The object is null for virtual robots.txt."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes/{robots_txt}

**Purpose:**
No summary provided.

**Detailed Description:**
Return content of a robots.txt file.

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Return content of a robots.txt file."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes/{robots_txt}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/ai/{url}

**Purpose:**
No summary provided.

**Detailed Description:**
Gets AI suggestions of an URL for an analysis

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Gets AI suggestions of an URL for an analysis"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/ai/{url}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/datamodel

**Purpose:**
No summary provided.

**Detailed Description:**
Gets an Analysis datamodel

**Parameters Required:**
```
- area: Analysis context
- previous_crawl: Previous analysis identifier
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Gets an Analysis datamodel"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/datamodel'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/datasets

**Purpose:**
No summary provided.

**Detailed Description:**
Gets Analysis Datasets

**Parameters Required:**
```
- area: Analysis context
- previous_crawl: Previous analysis identifier
- deprecated_fields: Include deprecated fields
- sequenced: Whether to use sequenced groups
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Gets Analysis Datasets"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/datasets'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/export

**Purpose:**
No summary provided.

**Detailed Description:**
A list of the CSV Exports requests and their current status

**Parameters Required:**
```
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """A list of the CSV Exports requests and their current status"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/export'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/export/{url_export_id}

**Purpose:**
No summary provided.

**Detailed Description:**
Checks the status of an CSVUrlExportJob object. Returns json object with the status.

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Checks the status of an CSVUrlExportJob object. Returns json object with the status."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/export/{url_export_id}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/html/{url}

**Purpose:**
No summary provided.

**Detailed Description:**
Gets the HTML of an URL for an analysis

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Gets the HTML of an URL for an analysis"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/html/{url}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/{url}

**Purpose:**
No summary provided.

**Detailed Description:**
Gets the detail of an URL for an analysis

**Parameters Required:**
```
- fields: comma separated list of fields to return (c.f. URLs Datamodel)
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Gets the detail of an URL for an analysis"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/{url}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/create/launch

**Purpose:**
No summary provided.

**Detailed Description:**
Create and launch an analysis for a project

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Create and launch an analysis for a project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/create/launch'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/{analysis_slug}/pause

**Purpose:**
No summary provided.

**Detailed Description:**
Pause an analysis for a project

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Pause an analysis for a project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/pause'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/{analysis_slug}/resume

**Purpose:**
No summary provided.

**Detailed Description:**
Resume an analysis for a project

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Resume an analysis for a project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/resume'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/{analysis_slug}/urls

**Purpose:**
No summary provided.

**Detailed Description:**
Executes a query and returns a paginated response

**Parameters Required:**
```
- Query: Query
- area: Analysis context
- page: Page Number
- size: Page Size
- previous_crawl: Previous analysis identifier
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Executes a query and returns a paginated response"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/{analysis_slug}/urls/aggs

**Purpose:**
No summary provided.

**Detailed Description:**
Query aggregator. It accepts multiple queries and dispatches them.

**Parameters Required:**
```
- AggsQueries: AggsQueries
- area: Analysis context
- previous_crawl: Previous analysis identifier
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Query aggregator. It accepts multiple queries and dispatches them."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/aggs'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /analyses/{username}/{project_slug}/{analysis_slug}/urls/export

**Purpose:**
No summary provided.

**Detailed Description:**
Creates a new UrlExport object and starts a task that will export the results into a csv. Returns the model id that manages the task

**Parameters Required:**
```
- Query: Query
- area: Analysis context
- previous_crawl: Previous analysis identifier
- export_size: Maximum size of the export (deprecated => size instead)
- size: Maximum size of the export
- compression: Compressed file format
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Creates a new UrlExport object and starts a task that will export the results into a csv. Returns the model id that manages the task"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/{analysis_slug}/urls/export'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### Collections Invocations

These endpoints allow you to manipulate collections aspects of your digital realm.

##### GET /projects/{username}/{project_slug}/collections

**Purpose:**
No summary provided.

**Detailed Description:**
List all collections for a project

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all collections for a project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/collections'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /projects/{username}/{project_slug}/collections/{collection}

**Purpose:**
No summary provided.

**Detailed Description:**
Get the detail of a collection

**Parameters Required:**
```
- sequenced: Whether to use sequenced groups
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get the detail of a collection"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/collections/{collection}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### Datasource Invocations

These endpoints allow you to manipulate datasource aspects of your digital realm.

##### GET /users/{username}/datasources_summary_by_projects

**Purpose:**
No summary provided.

**Detailed Description:**
Get the datasources details for all projects of a user

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Get the datasources details for all projects of a user"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/users/{username}/datasources_summary_by_projects'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### Job Invocations

These endpoints allow you to manipulate job aspects of your digital realm.

##### GET /jobs

**Purpose:**
No summary provided.

**Detailed Description:**
List All jobs

**Parameters Required:**
```
- page: Page Number
- size: Page Size
- job_type: The job type
- project: The project slug
- analysis: The analysis slug
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List All jobs"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/jobs'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /jobs/{job_id}

**Purpose:**
No summary provided.

**Detailed Description:**
Retrieve one job

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Retrieve one job"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/jobs/{job_id}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /jobs

**Purpose:**
No summary provided.

**Detailed Description:**
Creates a job instance of a class which depends on the "job_type" parameter you sent. Returns the model id that manages the task.

**Parameters Required:**
```
- JobCreate: Job create
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Creates a job instance of a class which depends on the "job_type" parameter you sent. Returns the model id that manages the task."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/jobs'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### Project Invocations

These endpoints allow you to manipulate project aspects of your digital realm.

##### GET /analyses/{username}/{project_slug}

**Purpose:**
No summary provided.

**Detailed Description:**
List all analyses for a project

**Parameters Required:**
```
- page: Page Number
- size: Page Size
- only_success: Return only successfully finished analyses
- fields: Which fields to return (comma-separated)
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all analyses for a project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /analyses/{username}/{project_slug}/light

**Purpose:**
No summary provided.

**Detailed Description:**
List all analyses for a project (light)

**Parameters Required:**
```
- page: Page Number
- size: Page Size
- only_success: Return only successfully finished analyses
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all analyses for a project (light)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/analyses/{username}/{project_slug}/light'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /projects/{username}/{project_slug}/filters

**Purpose:**
No summary provided.

**Detailed Description:**
List all the project's saved filters (each filter's name, ID and filter value)

**Parameters Required:**
```
- page: Page Number
- size: Page Size
- search: Search query on the filter name
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all the project's saved filters (each filter's name, ID and filter value)"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/filters'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /projects/{username}/{project_slug}/filters/{identifier}

**Purpose:**
No summary provided.

**Detailed Description:**
Retrieve a specific project saved, account or recommended filter's name, ID and filter value

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Retrieve a specific project saved, account or recommended filter's name, ID and filter value"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/filters/{identifier}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /projects/{username}/{project_slug}/saved_explorers

**Purpose:**
No summary provided.

**Detailed Description:**
List all the project's Saved Explorers.

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all the project's Saved Explorers."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/saved_explorers'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### GET /users/{username}/projects

**Purpose:**
No summary provided.

**Detailed Description:**
List all active projects for the user

**Parameters Required:**
```
No parameters required
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all active projects for the user"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/users/{username}/projects'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /projects/{username}/{project_slug}/query

**Purpose:**
No summary provided.

**Detailed Description:**
Query collections at a project level.

**Parameters Required:**
```
- ProjectQuery: Project Query
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Query collections at a project level."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/query'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /projects/{username}/{project_slug}/urls/aggs

**Purpose:**
No summary provided.

**Detailed Description:**
Project Query aggregator. It accepts multiple queries that will be executed on all completed analyses in the project

**Parameters Required:**
```
- AggsQueries: AggsQueries
- area: Analyses context
- last_analysis_slug: Last analysis on the trend
- nb_analyses: Max number of analysis to return
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Project Query aggregator. It accepts multiple queries that will be executed on all completed analyses in the project"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/urls/aggs'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

##### POST /projects/{username}/{project_slug}/values_list/clone

**Purpose:**
No summary provided.

**Detailed Description:**
Clone all keyword groups of the current project to another one.  This endpoint is a little more general (for further use). That's why you will see a 'type' field (with a default value of: 'keywords').

**Parameters Required:**
```
- ValuesListCloneRequestBody: JSON body to use as request body for ValuesList clone operation
```

**Expected Responses:**
```
- default: error payload
- 201: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """Clone all keyword groups of the current project to another one.  This endpoint is a little more general (for further use). That's why you will see a 'type' field (with a default value of: 'keywords')."""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/values_list/clone'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Define the payload for your invocation
data = {
    # Add your request parameters here
}
# Cast the spell
response = httpx.post(url, headers=headers, json=data)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### ProjectQuery Invocations

These endpoints allow you to manipulate projectquery aspects of your digital realm.

##### GET /projects/{username}/{project_slug}/account_filters

**Purpose:**
No summary provided.

**Detailed Description:**
List all the account saved filters

**Parameters Required:**
```
- page: Page Number
- size: Page Size
- search: Search query on the filter name
- disable_project: Flag to return or not filters of this project
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all the account saved filters"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}/{project_slug}/account_filters'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

#### User Invocations

These endpoints allow you to manipulate user aspects of your digital realm.

##### GET /projects/{username}

**Purpose:**
No summary provided.

**Detailed Description:**
List all active projects for the user

**Parameters Required:**
```
- name: Project's name
- page: Page Number
- size: Page Size
```

**Expected Responses:**
```
- default: error payload
- 200: Successful operation
```

**Example Implementation:**
```python
# Summon the necessary artifacts
import httpx
import json
def example_request():


    """List all active projects for the user"""

# Craft the invocation URL
url = f'https://api.botify.com/v1/projects/{username}'
# Prepare the headers for your spell
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}
# Cast the spell
response = httpx.get(url, headers=headers)
# Interpret the response
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.status_code}')
    print(response.text)
```

---

### LLM Guidance

When deciding which endpoint to use:
1. Consider the category (tag) that matches your task
2. Review the Purpose and Description to ensure alignment
3. Check the required parameters match your available data
4. Verify the expected responses meet your needs

Example prompt format:
```
I need to [task description]. I have access to [available data].
Which endpoint would be most appropriate?
```

<!-- #endregion -->
