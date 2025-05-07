# Search Query Widget Recipe

This recipe demonstrates how to create a widget that handles search queries and constructs search URLs. It's based on the Google Search implementation in [035_url_opener.py](../../plugins/035_url_opener.py).

## Key Features
- Handles search query input
- Constructs search URLs
- Opens searches in default browser
- Provides "Search Again" functionality
- Maintains query history

## Implementation

### Step Definition
```python
Step(
    id='step_XX',
    done='query',          # Store the search query
    show='Search Query',   # Clear action description
    refill=True,          # Allow query reuse
)
```

### Helper Methods
None required. Uses string formatting for URL construction.

### GET Handler
```python
async def step_XX(self, request):
    """Handles GET request for search query step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    query_value = step_data.get(step.done, "")

    # Check if workflow is finalized
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and query_value:
        search_url = f"https://www.google.com/search?q={query_value}"
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P(f"Search query: ", B(query_value)),
                Button(
                    "Search Again ▸",
                    type="button",
                    _onclick=f"window.open('{search_url}', '_blank')",
                    cls="secondary"
                )
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
    # Check if step is complete and not being reverted to
    if query_value and state.get("_revert_target") != step_id:
        search_url = f"https://www.google.com/search?q={query_value}"
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: {query_value}",
            widget=Div(
                P(f"Search query: ", B(query_value)),
                Button(
                    "Search Again ▸",
                    type="button",
                    _onclick=f"window.open('{search_url}', '_blank')",
                    cls="secondary"
                )
            ),
            steps=steps
        )
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    else:
        # Show query input form
        display_value = query_value if step.refill and query_value else "example search"
        await self.message_queue.add(pip, "Enter your search query:", verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                Form(
                    Input(
                        type="text",
                        name="query",
                        placeholder="Enter search query",
                        required=True,
                        value=display_value,
                        cls="contrast"
                    ),
                    Button("Search ▸", type="submit", cls="primary"),
                    hx_post=f"/{app_name}/{step_id}_submit", 
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )
```

### SUBMIT Handler
```python
async def step_XX_submit(self, request):
    """Process the search query submission and open search."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Get and validate query
    form = await request.form()
    query = form.get("query", "").strip()
    
    if not query:
        return P("Error: Search query is required", style=pip.get_style("error"))
    
    # Store query in state
    await pip.update_step_state(pipeline_id, step_id, query, steps)
    
    # Construct and open search URL
    search_url = f"https://www.google.com/search?q={query}"
    import webbrowser
    webbrowser.open(search_url)
    await self.message_queue.add(pip, f"Opening Google search: {query}", verbatim=True)
    
    # Create widget with search again button
    search_widget = Div(
        P(f"Search query: ", B(query)),
        Button(
            "Search Again ▸",
            type="button",
            _onclick=f"window.open('{search_url}', '_blank')",
            cls="secondary"
        )
    )
    
    # Create content container
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: {query}",
        widget=search_widget,
        steps=steps
    )
    
    # Return with chain reaction to next step
    return Div(
        content_container,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
```

## Query Handling

The widget handles search queries by:
1. Collecting user input
2. Validating query content
3. Constructing search URLs
4. Opening searches in browser
5. Maintaining query history

## URL Construction

Search URLs are constructed using:
1. Base URL: `https://www.google.com/search`
2. Query parameter: `?q=`
3. User's search term
4. No URL encoding needed (browser handles it)

## Chain Reaction Pattern

The widget maintains the critical chain reaction pattern:
```python
Div(
    content_container,
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

## State Management

The widget:
1. Stores queries in pipeline state
2. Allows query reuse with `refill=True`
3. Clears state properly on revert
4. Handles finalization correctly

## Error Handling

The widget includes:
1. Query validation
2. Required field checking
3. Clear error messages
4. Consistent error styling

## Browser Integration

The widget:
1. Uses system's default browser
2. Respects browser profiles
3. Handles search URLs properly
4. Provides immediate feedback

## Example Usage

```python
# In workflow initialization
steps = [
    Step(
        id='step_01',
        done='query',
        show='Google Search',
        refill=True,
    ),
    # ... other steps
]
```

## Customization Points

1. Search Engine
   - Change base URL
   - Add search parameters
   - Support multiple engines

2. Query Processing
   - Add query preprocessing
   - Implement validation rules
   - Add search suggestions

3. UI Components
   - Customize button labels
   - Add query preview
   - Enhance feedback messages

## Common Issues

1. Query Format
   - Symptom: Invalid query errors
   - Solution: Add query validation

2. URL Construction
   - Symptom: Search doesn't work
   - Solution: Check URL format

3. Chain Reaction
   - Symptom: No progression
   - Solution: Verify pattern

## Search Engine Options

The widget can be customized for different search engines:

1. Google
```python
search_url = f"https://www.google.com/search?q={query}"
```

2. Bing
```python
search_url = f"https://www.bing.com/search?q={query}"
```

3. DuckDuckGo
```python
search_url = f"https://duckduckgo.com/?q={query}"
```

## Advanced Features

1. Query History
   - Store previous queries
   - Add suggestions
   - Implement autocomplete

2. Search Options
   - Add search filters
   - Support advanced operators
   - Include search settings

3. Results Preview
   - Add result snippets
   - Show search metadata
   - Include related searches 