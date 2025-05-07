# Browser Integration Widget Recipe

This recipe demonstrates how to create a widget that integrates with the user's default web browser using Python's `webbrowser` module. It's based on the implementation in [035_url_opener.py](../../plugins/035_url_opener.py).

## Key Features
- Opens URLs in the user's default browser
- Leverages existing browser profiles and logins
- Works cross-platform (WSL, macOS, Windows)
- Provides "Open Again" functionality
- Handles URL validation and formatting

## Implementation

### Step Definition
```python
Step(
    id='step_XX',
    done='url',           # Store the URL
    show='Open URL',      # Clear action description
    refill=True,         # Allow URL reuse
)
```

### Helper Methods
None required. Uses Python's built-in `webbrowser` module.

### GET Handler
```python
async def step_XX(self, request):
    """Handles GET request for URL opener step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    url_value = step_data.get(step.done, "")

    # Check if workflow is finalized
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and url_value:
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P(f"URL configured: ", B(url_value)),
                Button(
                    "Open URL Again ▸",
                    type="button",
                    _onclick=f"window.open('{url_value}', '_blank')",
                    cls="secondary"
                )
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
    # Check if step is complete and not being reverted to
    if url_value and state.get("_revert_target") != step_id:
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: {url_value}",
            widget=Div(
                P(f"URL configured: ", B(url_value)),
                Button(
                    "Open URL Again ▸",
                    type="button",
                    _onclick=f"window.open('{url_value}', '_blank')",
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
        # Show URL input form
        display_value = url_value if step.refill and url_value else "https://example.com"
        await self.message_queue.add(pip, "Enter the URL you want to open:", verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                Form(
                    Input(
                        type="url",
                        name="url",
                        placeholder="https://example.com",
                        required=True,
                        value=display_value,
                        cls="contrast"
                    ),
                    Button("Open URL ▸", type="submit", cls="primary"),
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
    """Process the URL submission and open the URL."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Get and validate URL
    form = await request.form()
    url = form.get("url", "").strip()
    
    if not url:
        return P("Error: URL is required", style=pip.get_style("error"))
    
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    # Store URL in state
    await pip.update_step_state(pipeline_id, step_id, url, steps)
    
    # Open URL immediately
    import webbrowser
    webbrowser.open(url)
    await self.message_queue.add(pip, f"Opening URL: {url}", verbatim=True)
    
    # Create widget with reopen button
    url_widget = Div(
        P(f"URL configured: ", B(url)),
        Button(
            "Open URL Again ▸",
            type="button",
            _onclick=f"window.open('{url}', '_blank')",
            cls="secondary"
        )
    )
    
    # Create content container
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: {url}",
        widget=url_widget,
        steps=steps
    )
    
    # Return with chain reaction to next step
    return Div(
        content_container,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
```

## Browser Profile Considerations

The widget uses Python's `webbrowser` module which:
1. Opens URLs in the user's default browser
2. Respects the active browser profile
3. Maintains access to saved passwords and logins
4. Works cross-platform through WSL/macOS/Windows

Important notes for users:
- The active browser profile determines available logins
- No direct access to browser data is needed
- URLs open in the last active browser window

## URL Handling

The widget includes several URL handling features:
1. Validates URL format
2. Adds HTTPS if protocol is missing
3. Provides immediate feedback
4. Allows reopening URLs later
5. Preserves URLs for reuse

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
1. Stores URLs in pipeline state
2. Allows URL reuse with `refill=True`
3. Clears state properly on revert
4. Handles finalization correctly

## Error Handling

The widget includes:
1. URL validation
2. Required field checking
3. Protocol validation
4. Clear error messages
5. Consistent error styling

## Security Considerations

1. URL Validation
   - Enforces HTTPS by default
   - Validates URL format
   - Prevents script injection

2. Browser Integration
   - No direct browser access
   - Uses system's default browser
   - Respects browser security settings

## Example Usage

```python
# In workflow initialization
steps = [
    Step(
        id='step_01',
        done='url',
        show='Open URL',
        refill=True,
    ),
    # ... other steps
]
```

## Customization Points

1. URL Validation
   - Modify protocol handling
   - Add domain restrictions
   - Implement custom validation

2. Browser Integration
   - Add browser detection
   - Implement profile selection
   - Add URL preprocessing

3. UI Components
   - Customize button labels
   - Add URL preview
   - Enhance feedback messages

## Common Issues

1. Browser Profile Mismatch
   - Symptom: Wrong profile opens URL
   - Solution: Switch to correct profile first

2. URL Format Issues
   - Symptom: Invalid URL errors
   - Solution: Check URL validation logic

3. Chain Reaction Breaks
   - Symptom: No progression after URL opens
   - Solution: Verify chain reaction pattern 