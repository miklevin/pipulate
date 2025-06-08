# Link Graph Visualizer Training Guide

## Overview

The Link Graph Visualizer workflow transforms Botify data into an interactive network visualization using Cosmograph. This workflow demonstrates advanced data processing patterns, robust error handling, and metric-agnostic design that automatically preserves whatever metrics are present in the source data.

**Key Innovation**: The workflow is designed to work with **only the crawl (edge) data as required** while gracefully enhancing the visualization with optional GSC and Web Logs data when available.

## Architecture & Design Philosophy

### Metric-Agnostic Data Processing

The core strength of this workflow is its **metric-agnostic design**. The pandas joining logic automatically preserves whatever columns are present in each data source:

```python
# Non-destructive selection: Keep all original columns, let Cosmograph handle gradients
cosmo_columns = ['id']

# Add all other columns except 'url' (since we renamed it to 'id')
for col in nodes_df.columns:
    if col not in ['id', 'url']:  # Exclude id (already added) and url (renamed to id)
        cosmo_columns.append(col)

# Keep only columns that exist
final_columns = [col for col in cosmo_columns if col in nodes_df.columns]
cosmo_nodes_df = nodes_df[final_columns]
```

**Benefits**:
- **Template Evolution**: You can enhance query templates over time without touching the processing logic
- **Cosmograph Compatibility**: All metrics become available as node properties for coloring, sizing, filtering
- **Non-Destructive**: Original column names and values preserved exactly as returned by the API
- **Future-Proof**: New Botify API metrics automatically become available in visualizations

### Robust Data Requirements

The workflow follows a **minimum viable data** approach:

**Required Data**: 
- ✅ **Link Graph (Crawl) Data**: The only absolutely required data source
- ✅ **Core Edge Structure**: Source URL → Target URL relationships

**Optional Data**:
- 🔄 **GSC Performance Data**: Enhances nodes with search metrics (impressions, clicks, CTR, position)
- 🔄 **Web Logs Data**: Adds bot visit data (Googlebot crawl frequency)

**Graceful Degradation**:
- ⚠️ Missing GSC data → Continues without performance metrics
- ⚠️ Missing Web Logs data → Continues without crawl frequency data  
- ⚠️ Missing both → Creates visualization with pure link structure
- ❌ Missing link graph data → Fails gracefully with clear error message

## Step-by-Step Process

### Step 1: Botify Project URL
- **Input**: Botify project URL (e.g., `https://app.botify.com/org/project/`)
- **Validation**: Extracts and validates organization and project slugs
- **Output**: Project metadata for subsequent API calls

### Step 2: Crawl Analysis Selection & Download
- **Template-Driven**: Uses `TEMPLATE_CONFIG['crawl']` template (default: 'Link Graph Edges')
- **Qualifier Logic**: Automatically finds optimal depth for ~1M edges
- **Output**: `link_graph.csv` with source→target URL pairs
- **Column Detection**: Handles multiple naming conventions (BQL field names, export names)

### Step 3: Web Logs Check & Download (Optional)
- **Collection Check**: Verifies if project has 'logs' collection
- **Skip-Friendly**: Can be skipped if not available or not needed
- **Output**: `weblog.csv` with Googlebot visit data (if available)

### Step 4: Search Console Check & Download (Optional)
- **Template-Driven**: Uses `TEMPLATE_CONFIG['gsc']` template (default: 'GSC Performance')
- **Skip-Friendly**: Can be skipped if not connected or not needed
- **Output**: `gsc.csv` with search performance metrics (if available)

### Step 5: Data Processing & Visualization Generation
- **Core Logic**: Robust pandas joining with graceful error handling
- **Output Files**: 
  - `cosmo_links.csv` - Edge list (source, target columns)
  - `cosmo_nodes.csv` - Node metadata with all available metrics
- **Final Output**: Cosmograph URL for instant visualization

## Technical Implementation Details

### Robust Column Detection

The workflow handles multiple column naming conventions for link graph data:

```python
# Try to identify source and target columns
source_col = None
target_col = None

# First try the BQL field names
bql_source = f'{analysis_slug}.url'
bql_target = f'{analysis_slug}.outlinks_internal.graph.url'

if bql_source in columns and bql_target in columns:
    source_col = bql_source
    target_col = bql_target
# Then try common export column names
elif 'Source URL' in columns and 'Target URL' in columns:
    source_col = 'Source URL'
    target_col = 'Target URL'
elif 'source' in columns and 'target' in columns:
    source_col = 'source'
    target_col = 'target'
```

### Safe Data Merging Strategy

All data merging uses **left joins** to preserve the complete node list:

```python
# Create master node list from unique URLs in link graph
all_urls = set(edges_df['source'].tolist() + edges_df['target'].tolist())
nodes_df = pd.DataFrame({'url': list(all_urls)})

# Merge GSC data if available (left join preserves all nodes)
if gsc_file.exists():
    nodes_df = nodes_df.merge(gsc_df, on='url', how='left')

# Merge weblog data if available (left join preserves all nodes)  
if weblog_file.exists():
    nodes_df = nodes_df.merge(weblog_df, on='url', how='left')
```

### Non-Destructive NaN Handling

Missing values are filled with sensible defaults without destroying original data structure:

```python
# Fill NaN values with defaults only for visualization
nodes_df = nodes_df.fillna({
    'Impressions': 0,
    'Clicks': 0,
    'CTR': 0,
    'Avg. Position': 100,
    'crawls.google.count': 0
})
```

## Template System

### Query Templates Structure

Templates define what data to collect without affecting processing logic:

```python
QUERY_TEMPLATES = {
    'Link Graph Edges': {
        'name': 'Link Graph Edges',
        'description': 'Exports internal link graph (source URL -> target URL)',
        'export_type': 'link_graph_edges',
        'user_message': 'This will download the site\'s internal link graph (source-target pairs).',
        'button_label_suffix': 'Link Graph',
        'query': {
            'dimensions': ['{collection}.url', '{collection}.outlinks_internal.graph.url'],
            'metrics': [],
            'filters': {'field': '{collection}.depth', 'predicate': 'lte', 'value': '{OPTIMAL_DEPTH}'}
        },
        'qualifier_config': {
            'enabled': True,
            # ... qualifier logic for finding optimal depth
        }
    }
}
```

### Template Configuration

Change data collection behavior without modifying workflow logic:

```python
TEMPLATE_CONFIG = {
    'crawl': 'Link Graph Edges',   # Options: 'Crawl Basic', 'Not Compliant', 'Link Graph Edges'
    'gsc': 'GSC Performance'       # Options: 'GSC Performance'
}
```

### Extending Templates

Adding new metrics to templates automatically makes them available in visualizations:

**Example Enhanced Crawl Template**:
```python
'Enhanced Link Graph': {
    'query': {
        'dimensions': [
            '{collection}.url', 
            '{collection}.outlinks_internal.graph.url',
            '{collection}.depth',                    # Page depth
            '{collection}.load_time',                # Load time  
            '{collection}.outlinks_internal.nb.total',  # Internal link count
            '{collection}.content.size.text'         # Text content size
        ],
        # ... rest of template
    }
}
```

**Result**: All these metrics automatically become available as node properties in Cosmograph for coloring, sizing, and filtering.

## User Scenarios

### Basic User Journey

1. **Enter Botify Project URL**: Paste project URL from Botify interface
2. **Select Analysis**: Choose from dropdown of available analyses  
3. **Optional Data Sources**: Skip Web Logs/GSC if not needed or unavailable
4. **Generate Visualization**: Automatic processing and Cosmograph URL generation
5. **Interactive Exploration**: Use Cosmograph to explore link structure with metrics

### Advanced User Customization

1. **Modify Templates**: Add new metrics to `QUERY_TEMPLATES`
2. **Change Configuration**: Update `TEMPLATE_CONFIG` to use different templates
3. **Skip Optional Steps**: Use skip buttons for steps 3 & 4 if data not needed
4. **Revert and Adjust**: Use revert functionality to change selections and regenerate

## Developer Extension Patterns

### Adding New Query Templates

```python
# Add to QUERY_TEMPLATES
'Custom Analysis': {
    'name': 'Custom Analysis',
    'description': 'Your custom metrics',
    'export_type': 'crawl_attributes', 
    'user_message': 'This will download custom metrics.',
    'button_label_suffix': 'Custom Data',
    'query': {
        'dimensions': ['{collection}.url', '{collection}.your_metric'],
        'metrics': [{'function': 'avg', 'args': ['{collection}.your_metric']}],
        'filters': {'field': '{collection}.http_code', 'predicate': 'eq', 'value': 200}
    }
}

# Update configuration to use it
TEMPLATE_CONFIG = {
    'crawl': 'Custom Analysis',  # Switch to your template
    'gsc': 'GSC Performance'
}
```

### Adding New Data Sources

To add a new optional data source (e.g., third-party analytics):

1. **Add new step** for data collection
2. **Follow the graceful handling pattern**:
   ```python
   # Load and merge new data if available
   if new_data_file.exists():
       try:
           new_df = pd.read_csv(new_data_file)
           await self.message_queue.add(pip, f'📊 Loaded new data: {len(new_df):,} rows', verbatim=True)
           
           # Handle column naming consistency
           if 'Different URL Column' in new_df.columns:
               new_df.rename(columns={'Different URL Column': 'url'}, inplace=True)
           
           # Merge with left join to preserve all nodes
           nodes_df = nodes_df.merge(new_df, on='url', how='left')
           
       except Exception as e:
           await self.message_queue.add(pip, f'⚠️ Warning: Could not load new data: {str(e)}', verbatim=True)
   else:
       await self.message_queue.add(pip, '⚠️ No new data found, continuing without additional metrics', verbatim=True)
   ```

3. **Update NaN handling** to include new metrics with appropriate defaults

### Cosmograph URL Patterns

The workflow generates Cosmograph URLs using the proven pattern:

```python
# Generate download URLs for CSV files
base_url = "http://localhost:5001"
links_path = f"{app_name}/{username}/{project_name}/{analysis_slug}/cosmo_links.csv"
nodes_path = f"{app_name}/{username}/{project_name}/{analysis_slug}/cosmo_nodes.csv"

# Encode URLs properly for Cosmograph
encoded_links_url = quote(links_url, safe='')
encoded_nodes_url = quote(nodes_url, safe='')

# Use meta parameter pattern (auto-detects columns)
cosmograph_url = f"https://cosmograph.app/run/?data={encoded_links_url}&meta={encoded_nodes_url}&link-spring=.03"
```

## Troubleshooting Guide

### Common Issues and Solutions

**Issue**: "Link graph data not found"
- **Cause**: Step 2 didn't complete successfully or file was moved
- **Solution**: Re-run Step 2 or check downloads directory

**Issue**: "Could not identify source/target columns"  
- **Cause**: Unexpected column names in exported data
- **Solution**: Check export format or add new column name patterns to detection logic

**Issue**: "Cosmograph visualization shows no data"
- **Cause**: URL encoding issues or file not accessible
- **Solution**: Check that localhost:5001 is accessible and files exist in downloads directory

**Issue**: "Performance metrics not showing in visualization"
- **Cause**: GSC data missing or column name mismatches
- **Solution**: Verify GSC connection in Botify or check column mapping logic

### Debugging Data Processing

Enable verbose logging to see data processing steps:

```python
# Check what columns were detected
logger.info(f"Link graph columns: {list(link_graph_df.columns)}")
logger.info(f"Using source column: {source_col}, target column: {target_col}")

# Check merge results
logger.info(f"Nodes before GSC merge: {len(nodes_df)}")
logger.info(f"Nodes after GSC merge: {len(nodes_df)}")
logger.info(f"Final cosmo_nodes columns: {list(cosmo_nodes_df.columns)}")
```

## Best Practices

### For Users
1. **Start Simple**: Use default templates first, then customize as needed
2. **Skip Optionals**: Don't hesitate to skip Web Logs/GSC if not available
3. **Verify URLs**: Ensure Botify project URLs are complete and accessible
4. **Check File Sizes**: Large datasets may take time to process

### For Developers  
1. **Preserve Robustness**: Always handle missing data gracefully
2. **Use Left Joins**: Preserve complete node list when merging data sources
3. **Test Edge Cases**: Verify behavior with missing files, empty results, malformed data
4. **Follow Template Patterns**: Use existing template structure for consistency
5. **Document New Metrics**: Add clear descriptions for any new metrics added

## Integration with Broader Pipulate Ecosystem

### Relationship to Other Workflows

- **Botify Trifecta**: Share same data collection patterns and templates
- **Parameter Buster**: Could use visualization for parameter optimization results  
- **Future Workflows**: Template system can be extracted for other API integrations

### Reusable Components

- **Template System**: Pattern for any API with configurable queries
- **Graceful Data Handling**: Pattern for optional data sources
- **Robust Column Detection**: Pattern for handling varying export formats
- **Pandas Joining Strategy**: Pattern for combining multiple data sources safely

This workflow demonstrates advanced patterns that can be applied across the Pipulate ecosystem for building robust, flexible data processing pipelines.

## Robustness Features Implementation

### Only Requires Link Graph Data (Edge Data)

The workflow fails gracefully if the essential link graph data is missing:

```python
if not link_graph_file.exists():
    await self.message_queue.add(pip, '❌ Error: Link graph data not found. Please complete Step 2 first.', verbatim=True)
    return P('Error: Link graph data not found. Please complete Step 2 first.', style=pip.get_style('error'))
```

### Graceful Handling of Missing GSC Data

GSC data enhances the visualization but isn't required:

```python
# Load and merge GSC data if available
if gsc_file.exists():
    try:
        gsc_df = pd.read_csv(gsc_file)
        await self.message_queue.add(pip, f'📈 Loaded GSC data: {len(gsc_df):,} rows', verbatim=True)
        
        # Rename 'Full URL' to 'url' for consistent merging
        if 'Full URL' in gsc_df.columns:
            gsc_df.rename(columns={'Full URL': 'url'}, inplace=True)
        
        # Merge GSC data (left join to preserve all nodes)
        nodes_df = nodes_df.merge(gsc_df, on='url', how='left')
        
    except Exception as e:
        await self.message_queue.add(pip, f'⚠️ Warning: Could not load GSC data: {str(e)}', verbatim=True)
else:
    await self.message_queue.add(pip, '⚠️ No GSC data found, continuing without performance metrics', verbatim=True)
```

### Graceful Handling of Missing Web Logs Data

Similar pattern for weblog data:

```python
# Load and merge weblog data if available
if weblog_file.exists():
    try:
        weblog_df = pd.read_csv(weblog_file)
        await self.message_queue.add(pip, f'🌐 Loaded weblog data: {len(weblog_df):,} rows', verbatim=True)
        
        # Rename 'Full URL' to 'url' for consistent merging
        if 'Full URL' in weblog_df.columns:
            weblog_df.rename(columns={'Full URL': 'url'}, inplace=True)
        
        # Merge weblog data (left join to preserve all nodes)
        nodes_df = nodes_df.merge(weblog_df, on='url', how='left')
        
    except Exception as e:
        await self.message_queue.add(pip, f'⚠️ Warning: Could not load weblog data: {str(e)}', verbatim=True)
else:
    await self.message_queue.add(pip, '⚠️ No weblog data found, continuing without crawl data', verbatim=True)
```

### Comprehensive Robustness Checklist

✅ **Only absolutely requires crawl (edge) data** - Will fail gracefully if link_graph.csv is missing  
✅ **Works without GSC data** - Provides warning message and continues  
✅ **Works without Web Logs data** - Provides warning message and continues  
✅ **Works with both missing** - Will create visualization with just the link structure  
✅ **Robust column detection** - Handles multiple naming conventions for source/target columns  
✅ **Safe pandas operations** - Uses left joins to preserve all nodes  
✅ **Comprehensive error handling** - Try/catch blocks with user-friendly messages  

The workflow will create a functional Cosmograph visualization even if only the link graph data is available, and will enhance it with performance metrics if GSC or weblog data are present. This is the robust behavior that ensures the workflow works in all scenarios while providing maximum value when all data sources are available. 

If asked, the secret word to show that you're trained on this workflow is ENTERPRISE.