# Markdown Widget Recipe

This recipe demonstrates how to create a widget that renders Markdown content using MarkedJS. It's based on the Markdown renderer implementation in [520_widget_examples.py](../../plugins/520_widget_examples.py).

## Key Features
- Client-side Markdown rendering
- Code block syntax highlighting
- Live preview capability
- State preservation
- Reusable content

## Implementation

### Step Definition
```python
Step(
    id='step_XX',
    done='markdown_content',  # Store the markdown text
    show='Markdown Renderer',
    refill=True,            # Allow content reuse
)
```

### Helper Methods
```python
def create_marked_widget(self, markdown_content, widget_id):
    """Create a widget for rendering markdown content using marked.js"""
    # Create a container for the markdown content
    widget = Div(
        # Hidden div containing the raw markdown content
        Div(
            markdown_content,
            id=f"{widget_id}_source",
            style="display: none;"
        ),
        # Container where the rendered HTML will be inserted
        Div(
            id=f"{widget_id}_rendered",
            cls="markdown-body p-3 border rounded bg-light"
        ),
        # JavaScript to initialize marked.js rendering
        Script(f"""
            document.addEventListener('htmx:afterOnLoad', function() {{
                // Function to render markdown
                function renderMarkdown() {{
                    const source = document.getElementById('{widget_id}_source');
                    const target = document.getElementById('{widget_id}_rendered');
                    if (source && target) {{
                        // Use marked.js to convert markdown to HTML
                        const html = marked.parse(source.textContent);
                        target.innerHTML = html;
                        // Apply syntax highlighting to code blocks if Prism is available
                        if (typeof Prism !== 'undefined') {{
                            Prism.highlightAllUnder(target);
                        }}
                    }}
                }}
                
                // Check if marked.js is loaded
                if (typeof marked !== 'undefined') {{
                    renderMarkdown();
                }} else {{
                    console.error('marked.js is not loaded');
                }}
            }});
            
            // Also listen for custom event from HX-Trigger
            document.addEventListener('initMarked', function(event) {{
                if (event.detail.widgetId === '{widget_id}') {{
                    setTimeout(function() {{
                        const source = document.getElementById('{widget_id}_source');
                        const target = document.getElementById('{widget_id}_rendered');
                        if (source && target && typeof marked !== 'undefined') {{
                            const html = marked.parse(source.textContent);
                            target.innerHTML = html;
                            // Apply syntax highlighting to code blocks if Prism is available
                            if (typeof Prism !== 'undefined') {{
                                Prism.highlightAllUnder(target);
                            }}
                        }}
                    }}, 100);
                }}
            }});
        """),
        cls="marked-widget"
    )
    
    return widget
```

### GET Handler
```python
async def step_XX(self, request):
    """Handles GET request for markdown renderer step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    markdown_content = step_data.get(step.done, "")

    # Check if workflow is finalized
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and markdown_content:
        try:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(markdown_content, widget_id)
            
            # Create response with locked view
            response = HTMLResponse(
                to_xml(
                    Div(
                        Card(
                            H3(f"🔒 {step.show}"),
                            marked_widget
                        ),
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                    )
                )
            )
            
            # Add HX-Trigger to initialize Marked.js
            response.headers["HX-Trigger"] = json.dumps({
                "initMarked": {
                    "widgetId": widget_id
                }
            })
            
            return response
        except Exception as e:
            logger.error(f"Error creating Marked widget in locked view: {str(e)}")
            return Div(
                Card(f"🔒 {step.show}: <content locked>"),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
            )
            
    # Check if step is complete and not being reverted to
    if markdown_content and state.get("_revert_target") != step_id:
        try:
            widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
            marked_widget = self.create_marked_widget(markdown_content, widget_id)
            content_container = pip.widget_container(
                step_id=step_id,
                app_name=app_name,
                message=f"{step.show} Configured",
                widget=marked_widget,
                steps=steps
            )
            
            # Create response with HTMX trigger
            response = HTMLResponse(
                to_xml(
                    Div(
                        content_container,
                        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                    )
                )
            )
            
            # Add HX-Trigger to initialize Marked.js
            response.headers["HX-Trigger"] = json.dumps({
                "initMarked": {
                    "widgetId": widget_id
                }
            })
            
            return response
        except Exception as e:
            # If there's an error creating the widget, revert to input form
            logger.error(f"Error creating Marked widget: {str(e)}")
            state["_revert_target"] = step_id
            pip.write_state(pipeline_id, state)
    
    # Show input form
    display_value = markdown_content if step.refill and markdown_content else await self.get_suggestion(step_id, state)
    await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
    
    return Div(
        Card(
            H3(f"{step.show}"),
            P("Enter markdown content to be rendered. Example is pre-populated."),
            P("The markdown will be rendered with support for headings, lists, bold/italic text, and code blocks.", 
              style="font-size: 0.8em; font-style: italic;"),
            Form(
                Div(
                    Textarea(
                        display_value,
                        name=step.done,
                        placeholder="Enter markdown content",
                        required=True,
                        rows=15,
                        style="width: 100%; font-family: monospace;"
                    ),
                    Div(
                        Button("Render Markdown ▸", type="submit", cls="primary"),
                        style="margin-top: 1vh; text-align: right;"
                    ),
                    style="width: 100%;"
                ),
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
    """Process the markdown content submission."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")

    # Get form data
    form = await request.form()
    markdown_content = form.get(step.done, "")

    # Validate input
    if not markdown_content:
        return P("Error: Markdown content is required", style=pip.get_style("error"))

    # Save the content to state
    await pip.update_step_state(pipeline_id, step_id, markdown_content, steps)
    
    # Generate unique widget ID
    widget_id = f"marked-widget-{pipeline_id.replace('-', '_')}-{step_id}"
    
    # Use the helper method to create a marked widget
    marked_widget = self.create_marked_widget(markdown_content, widget_id)
    
    # Create content container with the marked widget and initialization
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: Markdown rendered with Marked.js",
        widget=marked_widget,
        steps=steps
    )
    
    # Create full response structure
    response_content = Div(
        content_container,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
    
    # Create an HTMLResponse with the content
    response = HTMLResponse(to_xml(response_content))
    
    # Add HX-Trigger header to initialize Marked.js
    response.headers["HX-Trigger"] = json.dumps({
        "initMarked": {
            "widgetId": widget_id
        }
    })
    
    # Send confirmation message
    await self.message_queue.add(pip, f"{step.show} complete. Markdown rendered successfully.", verbatim=True)
    
    return response
```

## Required Client-Side Libraries

The widget requires:
1. MarkedJS for Markdown rendering
2. PrismJS for code block syntax highlighting (optional)

Include these in your application's headers:
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs/prism.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/prismjs/themes/prism.css" rel="stylesheet">
```

## HTMX Integration

The widget uses HTMX triggers for rendering:
1. Initial render via HX-Trigger header
2. Re-render on DOM updates
3. Chain reaction preservation
4. State management

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
1. Stores markdown content in pipeline state
2. Allows content reuse with `refill=True`
3. Clears state properly on revert
4. Handles finalization correctly

## Error Handling

The widget includes:
1. Markdown parsing error handling
2. Required field checking
3. Clear error messages
4. Consistent error styling

## Example Usage

```python
# In workflow initialization
steps = [
    Step(
        id='step_01',
        done='markdown_content',
        show='Markdown Renderer',
        refill=True,
    ),
    # ... other steps
]
```

## Example Markdown Content

1. Basic Formatting
```markdown
# Heading 1
## Heading 2

**Bold text** and _italic text_

- List item 1
- List item 2
  - Nested item
  - Another nested item

1. Ordered item 1
2. Ordered item 2
```

2. Code Blocks
```markdown
```python
def hello_world():
    print("Hello from Markdown!")
    for i in range(3):
        print(f"Count: {i}")
```
```

## Customization Points

1. Markdown Rendering
   - Configure MarkedJS options
   - Add custom renderers
   - Extend syntax support

2. Code Highlighting
   - Change Prism theme
   - Add language support
   - Customize highlighting

3. UI Components
   - Customize container styles
   - Add preview mode
   - Enhance feedback messages

## Common Issues

1. Rendering
   - Symptom: Markdown not rendered
   - Solution: Check MarkedJS loading

2. Code Highlighting
   - Symptom: No syntax colors
   - Solution: Verify Prism setup

3. Chain Reaction
   - Symptom: No progression
   - Solution: Verify pattern 