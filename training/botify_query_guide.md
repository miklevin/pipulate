# Botify Query Wizard: Complete AI Assistant Guide

This document provides instant context for AI assistants about Pipulate's advanced Botify API integration through MCP (Model Context Protocol) tools.

## 🚀 Core MCP Tools: Your Botify Superpowers

### 1. `botify_get_full_schema` - The Schema Discovery Engine

**Purpose**: Fetch the complete, real-time schema from Botify's official datamodel endpoints.

**Key Features**:
- Discovers all 4,449+ available fields from live API endpoints
- Intelligent 24-hour caching for instant repeated access
- Returns complete collections, dimensions, metrics, and filter capabilities
- `force_refresh` parameter to bypass cache when needed

**Usage Pattern**:
```json
{
  "tool_name": "botify_get_full_schema",
  "parameters": {
    "org": "uhnd-com",
    "project": "uhnd.com-demo-account", 
    "analysis": "20250616",
    "force_refresh": false
  }
}
```

**What You Get**: Complete schema including all available collections (URLs, Logs, Search Console), every possible dimension and metric, valid filter predicates, and data types.

### 2. `botify_list_available_analyses` - The Analysis Finder

**Purpose**: Find the correct `analysis_slug` without making API calls.

**Key Features**:
- Reads cached `analyses.json` files from local storage
- Sorts by date (most recent first) 
- Provides analysis metadata (URLs processed, completion status, etc.)
- Works with any cached Botify project data

**Usage Pattern**:
```json
{
  "tool_name": "botify_list_available_analyses", 
  "parameters": {
    "username": "uhnd-com",
    "project_name": "uhnd.com-demo-account"
  }
}
```

**What You Get**: List of all available analyses with slugs, completion dates, URL counts, and status information.

### 3. `botify_execute_custom_bql_query` - The Query Wizard

**Purpose**: Execute sophisticated BQL queries with complete customization.

**Key Features**:
- Full BQL v2 query construction (dimensions, metrics, filters, sorting)
- Built-in error handling and response parsing
- Automatic pagination awareness
- Comprehensive query logging for debugging

**Usage Pattern**:
```json
{
  "tool_name": "botify_execute_custom_bql_query",
  "parameters": {
    "org_slug": "uhnd-com",
    "project_slug": "uhnd.com-demo-account",
    "analysis_slug": "20250616",
    "query_json": {
      "dimensions": ["url", "segments.pagetype.value"],
      "metrics": [
        "nb_organic_visits_from_google",
        "nb_social_visits_from_facebook",
        "conversion_rate"
      ],
      "filters": {
        "field": "nb_visits",
        "predicate": "gte", 
        "value": 100
      },
      "sort": [{"nb_visits": {"order": "desc"}}],
      "size": 50
    }
  }
}
```

## 📊 GA4/Adobe Analytics Integration Points

While Botify doesn't have a dedicated "Google Analytics" table, GA4/Adobe Analytics data is deeply integrated throughout the schema:

### Traffic Source Attribution
- `nb_organic_visits_from_google` - Organic Google traffic
- `nb_organic_visits_from_bing` - Organic Bing traffic  
- `nb_social_visits_from_facebook` - Facebook social traffic
- `nb_social_visits_from_twitter` - Twitter social traffic
- `nb_social_visits_from_linkedin` - LinkedIn social traffic
- `visits_organic` / `visits_social` - General organic/social metrics

### Device & User Segmentation  
- `nb_active_users_desktop` / `nb_active_users_mobile` / `nb_active_users_tablet`
- `conversion_rate_per_device_category` 
- `sessions_per_device_type`

### Revenue & Goal Tracking
- Goal conversion rates by traffic source
- Revenue attribution with full source/medium chains
- Session quality metrics (bounce rate, time on page, conversion funnels)

## 🎯 Query Construction Workflow

### 1. Schema-First Approach (ALWAYS START HERE)
```markdown
If you're unsure about available fields, ALWAYS use `botify_get_full_schema` first:
- Confirms field names and data types
- Reveals valid filter predicates  
- Shows available collections and their structure
- Provides examples of metric functions
```

### 2. Find the Right Analysis
```markdown
Use `botify_list_available_analyses` to:
- Get the most recent analysis_slug
- Verify data freshness and completeness
- Understand analysis scope (URL count, completion status)
```

### 3. Build Custom Queries
```markdown
Construct BQL using `botify_execute_custom_bql_query`:
- Start with basic dimensions (url, http_code, title)
- Add relevant metrics based on user needs
- Apply filters to focus results
- Use sorting to prioritize insights
- Adjust size parameter for result volume
```

## 🔍 Advanced Query Examples

### Traffic Attribution Report
```json
{
  "dimensions": ["url", "segments.pagetype.value"],
  "metrics": [
    "nb_visits",
    "nb_organic_visits_from_google",
    "nb_organic_visits_from_bing", 
    "nb_social_visits_from_facebook",
    "conversion_rate"
  ],
  "filters": {
    "field": "nb_visits",
    "predicate": "gte",
    "value": 50
  },
  "sort": [{"nb_visits": {"order": "desc"}}]
}
```

### SEO Performance Analysis
```json
{
  "dimensions": ["url", "http_code", "metadata.title.content"],
  "metrics": [
    "nb_organic_visits_from_google",
    "search_console.period_0.count_impressions",
    "search_console.period_0.ctr",
    "search_console.period_0.avg_position"
  ],
  "filters": {
    "field": "http_code", 
    "predicate": "eq",
    "value": 200
  }
}
```

### Technical SEO Issues
```json
{
  "dimensions": ["url", "compliant.main_reason", "http_code"],
  "metrics": [
    {"function": "count", "args": ["url"]}
  ],
  "filters": {
    "field": "compliant.is_compliant",
    "predicate": "eq", 
    "value": false
  }
}
```

## ⚡ Dual BQL Version Reality

Botify has TWO coexisting BQL versions that MUST be used correctly:

### BQLv1 (Web Logs Only)
- **Endpoint**: `app.botify.com/api/v1/logs/...`
- **Date Format**: Dates at payload level
- **Use Case**: Web server log analysis
- **Structure**: Legacy format with simpler field structure

### BQLv2 (Crawl & GSC Data)  
- **Endpoint**: `api.botify.com/v1/projects/.../query`
- **Date Format**: Dates in periods array
- **Use Case**: Site crawl analysis and Search Console data
- **Structure**: Modern format with complex nested fields

**CRITICAL**: The MCP tools automatically handle BQLv2 format. For web logs, the Botify Trifecta workflow handles BQLv1 conversion.

## 🔧 Error Handling & Debugging

### Common Issues & Solutions

1. **Field Not Found**: Always use `botify_get_full_schema` to verify field names
2. **Invalid Filter Values**: Check schema for valid predicates (`eq`, `gte`, `in`, etc.)
3. **Empty Results**: Verify analysis completeness and filter logic
4. **Rate Limits**: Use appropriate `size` parameters and pagination

### Transparency Features

All MCP tool calls are logged with:
- Complete request/response data
- Execution timing
- Error details with context
- Generated Python code equivalents
- Cache hit/miss status

Check `logs/server.log` for detailed MCP execution traces using `FINDER_TOKEN: MCP_EXECUTION_START`.

## 🎯 AI Assistant Best Practices

1. **Always Schema First**: Call `botify_get_full_schema` when unsure about fields
2. **Cache Awareness**: Leverage 24-hour caching for repeated schema calls  
3. **Progressive Queries**: Start simple, add complexity based on results
4. **Validate Assumptions**: Use schema to confirm field availability before building queries
5. **Log Analysis**: Use transparency logs to debug and optimize queries
6. **Error Recovery**: Handle API errors gracefully with fallback strategies

## 📚 Integration with Pipulate Workflows

The MCP tools integrate seamlessly with Pipulate's workflow system:
- **Botify Trifecta**: Uses templates and MCP tools for multi-source data collection
- **Custom Workflows**: Build new workflows using MCP tools as building blocks
- **Real-time Analysis**: Query live data during workflow execution
- **Data Validation**: Verify workflow outputs against live API responses

This comprehensive tooling makes any AI assistant an instant "Botify API query wizard" capable of building sophisticated data analyses with full transparency and debugging capability. 