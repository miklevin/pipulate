# JavaScript Widget Recipe

This recipe demonstrates how to create a widget that executes JavaScript code in HTMX-injected content. It's based on the JavaScript widget implementation in [520_widget_examples.py](../../plugins/520_widget_examples.py).

## Key Features
- Client-side code execution
- DOM manipulation
- Event handling
- State preservation
- Re-run capability

## Implementation

### Step Definition
```python
Step(
    id='step_XX',
    done='js_content',     # Store the JavaScript code
    show='JavaScript Widget',
    refill=True,          # Allow code reuse
)
```

### Helper Methods
None required. Uses HTMX triggers for JavaScript execution.

### GET Handler
```python
async def step_XX(self, request):
    """Handles GET request for JavaScript widget step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    js_code = step_data.get(step.done, "")

    # Generate unique widget ID
    widget_id = f"js-widget-{pipeline_id}-{step_id}".replace("-", "_")
    target_id = f"{widget_id}_target"

    # Check if workflow is finalized
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and js_code:
        # Create a JavaScript widget for locked view with re-run button
        js_widget = Div(
            P(
                "JavaScript will execute here...", 
                id=target_id, 
                style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
            ),
            Button(
                "Re-run JavaScript", 
                type="button", 
                _onclick=f"runJsWidget('{widget_id}', `{js_code.replace('`', '\\`')}`, '{target_id}')",
                style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
            ),
            id=widget_id
        )
        
        # Create response with content in locked view
        response = HTMLResponse(
            to_xml(
                Div(
                    Card(
                        H3(f"🔒 {step.show}"),
                        js_widget
                    ),
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            )
        )
        
        # Add HX-Trigger header to execute the JS code
        response.headers["HX-Trigger"] = json.dumps({
            "runJavaScript": {
                "widgetId": widget_id,
                "code": js_code,
                "targetId": target_id
            }
        })
        
        return response
        
    # Check if step is complete and not being reverted to
    if js_code and state.get("_revert_target") != step_id:
        # Create the JS widget from the existing code
        js_widget = Div(
            P(
                "JavaScript will execute here...", 
                id=target_id, 
                style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
            ),
            Button(
                "Re-run JavaScript", 
                type="button", 
                _onclick=f"runJsWidget('{widget_id}', `{js_code.replace('`', '\\`')}`, '{target_id}')",
                style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
            ),
            id=widget_id
        )
        
        # Create content container with the widget
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show} Configured",
            widget=js_widget,
            steps=steps
        )
        
        # Create response with HX-Trigger
        response = HTMLResponse(
            to_xml(
                Div(
                    content_container,
                    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
                )
            )
        )
        
        # Add HX-Trigger header to execute the JS code
        response.headers["HX-Trigger"] = json.dumps({
            "runJavaScript": {
                "widgetId": widget_id,
                "code": js_code,
                "targetId": target_id
            }
        })
        
        return response
    else:
        # Show code input form
        display_value = js_code if step.refill and js_code else await self.get_suggestion(step_id, state)
        await self.message_queue.add(pip, "Enter JavaScript code for the widget:", verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                P("Enter JavaScript code to execute. Use the 'widget' variable to access the container."),
                Form(
                    Div(
                        Textarea(
                            display_value,
                            name=step.done,
                            placeholder="Enter JavaScript code",
                            required=True,
                            rows=12,
                            style="width: 100%; font-family: monospace;"
                        ),
                        Div(
                            Button("Run JavaScript ▸", type="submit", cls="primary"),
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
    """Process the JavaScript code submission."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Get form data
    form = await request.form()
    js_code = form.get(step.done, "")

    # Validate input
    if not js_code:
        return P("Error: JavaScript code is required", style=pip.get_style("error"))

    # Save the code to state
    await pip.update_step_state(pipeline_id, step_id, js_code, steps)
    
    # Generate unique widget ID
    widget_id = f"js-widget-{pipeline_id}-{step_id}".replace("-", "_")
    target_id = f"{widget_id}_target"
    
    # Create a simple container with just the target element and re-run button
    js_widget = Div(
        P(
            "JavaScript will execute here...", 
            id=target_id, 
            style="padding: 1.5rem; background-color: var(--pico-card-background-color); border-radius: var(--pico-border-radius); min-height: 100px;"
        ),
        Button(
            "Re-run JavaScript", 
            type="button", 
            _onclick=f"runJsWidget('{widget_id}', `{js_code.replace('`', '\\`')}`, '{target_id}')",
            style="margin-top: 1rem; background-color: #9370DB; border-color: #9370DB;"
        ),
        id=widget_id
    )
    
    # Create content container with the widget
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: Interactive JavaScript example",
        widget=js_widget,
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
    
    # Add HX-Trigger header to execute the JS code
    response.headers["HX-Trigger"] = json.dumps({
        "runJavaScript": {
            "widgetId": widget_id,
            "code": js_code,
            "targetId": target_id
        }
    })
    
    # Send confirmation message
    await self.message_queue.add(pip, f"{step.show} complete. JavaScript executed.", verbatim=True)
    
    return response
```

## Required Client-Side Code

The widget requires this JavaScript function in your application:

```javascript
function runJsWidget(widgetId, code, targetId) {
    const widget = document.getElementById(widgetId);
    const target = document.getElementById(targetId);
    if (widget && target) {
        try {
            // Clear previous content
            target.innerHTML = '';
            // Execute the code with widget context
            eval(code);
        } catch (e) {
            target.innerHTML = `<div style="color: red;">Error: ${e.message}</div>`;
        }
    }
}
```

## HTMX Integration

The widget uses HTMX triggers for JavaScript execution:
1. Initial execution via HX-Trigger header
2. Re-run capability via onclick handler
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
1. Stores JavaScript code in pipeline state
2. Allows code reuse with `refill=True`
3. Clears state properly on revert
4. Handles finalization correctly

## Error Handling

The widget includes:
1. JavaScript execution error handling
2. Required field checking
3. Clear error messages
4. Consistent error styling

## Security Considerations

1. Code Execution
   - Executes in isolated context
   - Uses eval() safely
   - Handles errors gracefully

2. DOM Access
   - Limited to widget container
   - Prevents global DOM manipulation
   - Maintains widget isolation

## Example Usage

```python
# In workflow initialization
steps = [
    Step(
        id='step_01',
        done='js_content',
        show='JavaScript Widget',
        refill=True,
    ),
    # ... other steps
]
```

## Example JavaScript Code

1. Simple Counter
```javascript
let count = 0;
const countDisplay = document.createElement('div');
countDisplay.style.fontSize = '24px';
countDisplay.style.margin = '20px 0';
countDisplay.textContent = count;

const button = document.createElement('button');
button.textContent = 'Increment Count';
button.style.backgroundColor = '#9370DB';
button.style.borderColor = '#9370DB';
button.onclick = function() {
    count++;
    countDisplay.textContent = count;
};

widget.appendChild(countDisplay);
widget.appendChild(button);
```

2. Dynamic List
```javascript
const list = document.createElement('ul');
['Item 1', 'Item 2', 'Item 3'].forEach(text => {
    const item = document.createElement('li');
    item.textContent = text;
    list.appendChild(item);
});

const addButton = document.createElement('button');
addButton.textContent = 'Add Item';
addButton.onclick = function() {
    const item = document.createElement('li');
    item.textContent = `Item ${list.children.length + 1}`;
    list.appendChild(item);
};

widget.appendChild(list);
widget.appendChild(addButton);
```

## Customization Points

1. Code Execution
   - Add code validation
   - Implement sandboxing
   - Add execution limits

2. Widget Interface
   - Customize container styles
   - Add widget API methods
   - Enhance error display

3. UI Components
   - Customize button styles
   - Add code preview
   - Enhance feedback messages

## Common Issues

1. Code Execution
   - Symptom: JavaScript errors
   - Solution: Check browser console

2. DOM Updates
   - Symptom: No visual changes
   - Solution: Verify DOM manipulation

3. Chain Reaction
   - Symptom: No progression
   - Solution: Verify pattern 