# Botify Open API Swagger Examples

**Total Estimated Token Count**: `21,544` (using `cl100k_base`)

This document provides detailed information and Python code examples for every endpoint in the Botify API...
#### `GET /analyses/{username}/{project_slug}`

**Category:** `Project`

**Summary:** 

**Description:**
List all analyses for a project

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `only_success` | query | False | `boolean` | Return only successfully finished analyses |
| `fields` | query | False | `string` | Which fields to return (comma-separated) |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'only_success': 123,  # Type: boolean, Required: False
    'fields': 'example_value',  # Type: string, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/create/launch`

**Category:** `Analysis`

**Summary:** 

**Description:**
Create and launch an analysis for a project

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/create/launch"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/light`

**Category:** `Project`

**Summary:** 

**Description:**
List all analyses for a project (light)

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `only_success` | query | False | `boolean` | Return only successfully finished analyses |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/light"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'only_success': 123,  # Type: boolean, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Get an Analysis detail

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `previous_crawl` | query | False | `string` | Previous analysis identifier |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'previous_crawl': 'example_value',  # Type: string, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics`

**Category:** `Analysis`

**Summary:** 

**Description:**
Return global statistics for an analysis

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/time`

**Category:** `Analysis`

**Summary:** 

**Description:**
Return crawl statistics grouped by time frequency (1 min, 5 mins or 60 min) for an analysis

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `limit` | query | False | `integer` | max number of elements to retrieve |
| `frequency` | query | True | `string` | Aggregation frequency |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/time"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'limit': 123,  # Type: integer, Required: False
    'frequency': 'example_value',  # Type: string, Required: True
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/urls/{list_type}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Return a list of 1000 latest URLs crawled (all crawled URLs or only URLS with HTTP errors)

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
list_type = "YOUR_LIST_TYPE"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/crawl_statistics/urls/{list_type}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/ganalytics/orphan_urls/{medium}/{source}`

**Category:** `Analysis`

**Summary:** Legacy

**Description:**
Legacy    List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET Legacy
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
medium = "YOUR_MEDIUM"
source = "YOUR_SOURCE"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/ganalytics/orphan_urls/{medium}/{source}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/links/percentiles`

**Category:** `Analysis`

**Summary:** 

**Description:**
Get inlinks percentiles

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/links/percentiles"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/pagerank/lost`

**Category:** `Analysis`

**Summary:** 

**Description:**
Lost pagerank

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/pagerank/lost"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/scoring/summary`

**Category:** `Analysis`

**Summary:** 

**Description:**
Scoring summary

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/scoring/summary"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/search_console/stats`

**Category:** `Analysis`

**Summary:** 

**Description:**
List clicks and impressions per day

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/search_console/stats"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/report`

**Category:** `Analysis`

**Summary:** 

**Description:**
Get global information of the sitemaps found (sitemaps indexes, invalid sitemaps urls, etc.)

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/report"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/out_of_config`

**Category:** `Analysis`

**Summary:** 

**Description:**
Sample list of URLs which were found in your sitemaps but outside of the crawl perimeter defined for the project, for instance domain/subdomain or protocol (HTTP/HTTPS) not allowed in the crawl settings.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/out_of_config"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/sitemap_only`

**Category:** `Analysis`

**Summary:** 

**Description:**
Sample list of URLs which were found in your sitemaps, within the project allowed scope (allowed domains/subdomains/protocols), but not found by the Botify crawler.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/sitemaps/samples/sitemap_only"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/domains`

**Category:** `Analysis`

**Summary:** 

**Description:**
Top domains

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/domains"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/subdomains`

**Category:** `Analysis`

**Summary:** 

**Description:**
Top subddomains

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/top_domains/subdomains"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/features/visits/orphan_urls/{medium}/{source}`

**Category:** `Analysis`

**Summary:** 

**Description:**
List of Orphan URLs. URLs which generated visits from the selected source according to Google Analytics data, but were not crawled with by the Botify crawler (either because no links to them were found on the website, or because the crawler was not allowed to follow these links according to the project settings).   For a search engine (medium: origanic; sources: all, aol, ask, baidu, bing, google, naver, yahoo, yandex) or a social network (medium: social; sources: all, facebook, google+, linkedin, pinterest, reddit, tumblr, twitter)

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
medium = "YOUR_MEDIUM"
source = "YOUR_SOURCE"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/features/visits/orphan_urls/{medium}/{source}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/{analysis_slug}/pause`

**Category:** `Analysis`

**Summary:** 

**Description:**
Pause an analysis for a project

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/pause"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/{analysis_slug}/resume`

**Category:** `Analysis`

**Summary:** 

**Description:**
Resume an analysis for a project

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/resume"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/segments`

**Category:** `Analysis`

**Summary:** 

**Description:**
Get the segments feature public metadata of an analysis.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/segments"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes`

**Category:** `Analysis`

**Summary:** 

**Description:**
Return an object containing all robots.txt files found on the project's domains. The object is null for virtual robots.txt.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes/{robots_txt}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Return content of a robots.txt file.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
robots_txt = "YOUR_ROBOTS_TXT"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/staticfiles/robots-txt-indexes/{robots_txt}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/{analysis_slug}/urls`

**Category:** `Analysis`

**Summary:** 

**Description:**
Executes a query and returns a paginated response

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `Query` | body | False | `N/A` | Query |
| `area` | query | False | `string` | Analysis context |
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `previous_crawl` | query | False | `string` | Previous analysis identifier |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'previous_crawl': 'example_value',  # Type: string, Required: False
}
# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, params=query_params, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/{analysis_slug}/urls/aggs`

**Category:** `Analysis`

**Summary:** 

**Description:**
Query aggregator. It accepts multiple queries and dispatches them.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `AggsQueries` | body | False | `N/A` | AggsQueries |
| `area` | query | False | `string` | Analysis context |
| `previous_crawl` | query | False | `string` | Previous analysis identifier |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/aggs"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'previous_crawl': 'example_value',  # Type: string, Required: False
}
# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, params=query_params, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/ai/{url}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Gets AI suggestions of an URL for an analysis

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
url = "YOUR_URL"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/ai/{url}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/datamodel`

**Category:** `Analysis`

**Summary:** 

**Description:**
Gets an Analysis datamodel

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `area` | query | False | `string` | Analysis context |
| `previous_crawl` | query | False | `string` | Previous analysis identifier |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/datamodel"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'previous_crawl': 'example_value',  # Type: string, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/datasets`

**Category:** `Analysis`

**Summary:** 

**Description:**
Gets Analysis Datasets

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `area` | query | False | `string` | Analysis context |
| `previous_crawl` | query | False | `string` | Previous analysis identifier |
| `deprecated_fields` | query | False | `boolean` | Include deprecated fields |
| `sequenced` | query | False | `boolean` | Whether to use sequenced groups |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/datasets"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'previous_crawl': 'example_value',  # Type: string, Required: False
    'deprecated_fields': 123,  # Type: boolean, Required: False
    'sequenced': 123,  # Type: boolean, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/export`

**Category:** `Analysis`

**Summary:** 

**Description:**
A list of the CSV Exports requests and their current status

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/export"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /analyses/{username}/{project_slug}/{analysis_slug}/urls/export`

**Category:** `Analysis`

**Summary:** 

**Description:**
Creates a new UrlExport object and starts a task that will export the results into a csv. Returns the model id that manages the task

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `Query` | body | False | `N/A` | Query |
| `area` | query | False | `string` | Analysis context |
| `previous_crawl` | query | False | `string` | Previous analysis identifier |
| `export_size` | query | False | `integer` | Maximum size of the export (deprecated => size instead) |
| `size` | query | False | `integer` | Maximum size of the export |
| `compression` | query | False | `string` | Compressed file format |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/export"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'previous_crawl': 'example_value',  # Type: string, Required: False
    'export_size': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'compression': 'example_value',  # Type: string, Required: False
}
# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, params=query_params, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/export/{url_export_id}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Checks the status of an CSVUrlExportJob object. Returns json object with the status.

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
url_export_id = "YOUR_URL_EXPORT_ID"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/export/{url_export_id}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/html/{url}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Gets the HTML of an URL for an analysis

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
url = "YOUR_URL"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/html/{url}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /analyses/{username}/{project_slug}/{analysis_slug}/urls/{url}`

**Category:** `Analysis`

**Summary:** 

**Description:**
Gets the detail of an URL for an analysis

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `fields` | query | False | `array` | comma separated list of fields to return (c.f. URLs Datamodel) |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
analysis_slug = "YOUR_ANALYSIS_SLUG"
url = "YOUR_URL"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/analyses/{username}/{project_slug}/{analysis_slug}/urls/{url}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'fields': 123,  # Type: array, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /jobs`

**Category:** `Job`

**Summary:** 

**Description:**
List All jobs

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `job_type` | query | False | `string` | The job type |
| `project` | query | False | `string` | The project slug |
| `analysis` | query | False | `string` | The analysis slug |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/jobs"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'job_type': 'example_value',  # Type: string, Required: False
    'project': 'example_value',  # Type: string, Required: False
    'analysis': 'example_value',  # Type: string, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /jobs`

**Category:** `Job`

**Summary:** 

**Description:**
Creates a job instance of a class which depends on the "job_type" parameter you sent. Returns the model id that manages the task.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `JobCreate` | body | False | `N/A` | Job create |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/jobs"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /jobs/{job_id}`

**Category:** `Job`

**Summary:** 

**Description:**
Retrieve one job

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
job_id = "YOUR_JOB_ID"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/jobs/{job_id}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}`

**Category:** `User`

**Summary:** 

**Description:**
List all active projects for the user

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `name` | query | False | `string` | Project's name |
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'name': 'example_value',  # Type: string, Required: False
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/account_filters`

**Category:** `ProjectQuery`

**Summary:** 

**Description:**
List all the account saved filters

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `search` | query | False | `string` | Search query on the filter name |
| `disable_project` | query | False | `boolean` | Flag to return or not filters of this project |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/account_filters"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'search': 'example_value',  # Type: string, Required: False
    'disable_project': 123,  # Type: boolean, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/collections`

**Category:** `Collections`

**Summary:** 

**Description:**
List all collections for a project

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/collections"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/collections/{collection}`

**Category:** `Collections`

**Summary:** 

**Description:**
Get the detail of a collection

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `sequenced` | query | False | `boolean` | Whether to use sequenced groups |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
collection = "YOUR_COLLECTION"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/collections/{collection}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'sequenced': 123,  # Type: boolean, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/filters`

**Category:** `Project`

**Summary:** 

**Description:**
List all the project's saved filters (each filter's name, ID and filter value)

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |
| `search` | query | False | `string` | Search query on the filter name |

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/filters"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
    'search': 'example_value',  # Type: string, Required: False
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/filters/{identifier}`

**Category:** `Project`

**Summary:** 

**Description:**
Retrieve a specific project saved, account or recommended filter's name, ID and filter value

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"
identifier = "YOUR_IDENTIFIER"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/filters/{identifier}"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /projects/{username}/{project_slug}/query`

**Category:** `Project`

**Summary:** 

**Description:**
Query collections at a project level.

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `ProjectQuery` | body | False | `N/A` | Project Query |
| `page` | query | False | `integer` | Page Number |
| `size` | query | False | `integer` | Page Size |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/query"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'page': 123,  # Type: integer, Required: False
    'size': 123,  # Type: integer, Required: False
}
# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, params=query_params, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /projects/{username}/{project_slug}/saved_explorers`

**Category:** `Project`

**Summary:** 

**Description:**
List all the project's Saved Explorers.

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/saved_explorers"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /projects/{username}/{project_slug}/urls/aggs`

**Category:** `Project`

**Summary:** 

**Description:**
Project Query aggregator. It accepts multiple queries that will be executed on all completed analyses in the project

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `AggsQueries` | body | False | `N/A` | AggsQueries |
| `area` | query | False | `string` | Analyses context |
| `last_analysis_slug` | query | False | `string` | Last analysis on the trend |
| `nb_analyses` | query | False | `integer` | Max number of analysis to return |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/urls/aggs"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define query parameters
query_params = {
    'area': 'example_value',  # Type: string, Required: False
    'last_analysis_slug': 'example_value',  # Type: string, Required: False
    'nb_analyses': 123,  # Type: integer, Required: False
}
# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, params=query_params, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `POST /projects/{username}/{project_slug}/values_list/clone`

**Category:** `Project`

**Summary:** 

**Description:**
Clone all keyword groups of the current project to another one.  This endpoint is a little more general (for further use). That's why you will see a 'type' field (with a default value of: 'keywords').

**Parameters:**
| Name | Location (in) | Required | Type | Description |
|---|---|---|---|---|
| `ValuesListCloneRequestBody` | body | False | `N/A` | JSON body to use as request body for ValuesList clone operation |

**Python Example:**
```python
# Example: POST 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"
project_slug = "YOUR_PROJECT_SLUG"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/projects/{username}/{project_slug}/values_list/clone"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

# Define the JSON payload for the request body
json_payload = {
    'key': 'value'  # Replace with actual data
}

# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=json_payload)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /users/{username}/datasources_summary_by_projects`

**Category:** `Datasource`

**Summary:** 

**Description:**
Get the datasources details for all projects of a user

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/users/{username}/datasources_summary_by_projects"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```

--------------------------------------------------------------------------------

#### `GET /users/{username}/projects`

**Category:** `Project`

**Summary:** 

**Description:**
List all active projects for the user

**Python Example:**
```python
# Example: GET 
import httpx
import json

# Assumes your Botify API token is in a file named 'botify_token.txt'
try:
    with open('botify_token.txt') as f:
        token = f.read().split('\n')[0].strip()
except FileNotFoundError:
    print("Error: 'botify_token.txt' not found. Please create it.")
    token = 'YOUR_API_TOKEN'  # Fallback

# --- Define Path Parameters ---
username = "YOUR_USERNAME"

# --- Construct the Request ---
url = f"[https://api.botify.com/v1](https://api.botify.com/v1)/users/{username}/projects"
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}


# --- Send the Request ---
try:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        print('Success! Response:')
        print(json.dumps(response.json(), indent=2))
except httpx.HTTPStatusError as e:
    print(f'HTTP Error: {e.response.status_code} - {e.response.text}')
except httpx.RequestError as e:
    print(f'Request error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
```