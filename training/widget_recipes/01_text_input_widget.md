# Text Input Widget Recipe

## Overview
This recipe transforms a placeholder step into a widget that collects text input with validation. This is the most basic form of user input and serves as a foundation for more complex input widgets.

## Implementation Phases

### Phase 1: Update Step Definition
```python
# CUSTOMIZE_STEP_DEFINITION
# Change from:
Step(
    id='step_XX',
    done='placeholder',
    show='Placeholder Step',
    refill=False,
),

# To:
Step(
    id='step_XX',
    done='text_input',        # Field to store the input value
    show='Text Input Widget', # User-friendly name
    refill=True,              # Allow refilling for better UX
),
```

### Phase 2: Update GET Handler
Only modify the marked sections:

```python
# CUSTOMIZE_VALUE_ACCESS:
text_value = step_data.get(step.done, "")  # Access the text value from state

# CUSTOMIZE_DISPLAY: Enhanced finalized state display
return Div(
    Card(
        H3(f"🔒 {step.show}"),
        P(f"Input: {text_value}")  # Show the stored text value
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# CUSTOMIZE_COMPLETE: Enhanced completion display 
return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {text_value}", # Show value in revert control
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# CUSTOMIZE_FORM: Replace with text input form
display_value = text_value if (step.refill and text_value) else ""
return Div(
    Card(
        H3(f"{step.show}"),
        P("Enter text below:"),
        Form(
            Input(
                type="text", 
                name=step.done, 
                placeholder="Enter your text here", 
                value=display_value,  # Use refill value if available
                required=True
            ),
            Div(
                Button("Submit", type="submit", cls="primary"),
                style="margin-top: 1vh; text-align: right;"
            ),
            hx_post=f"/{app_name}/{step_id}_submit", 
            hx_target=f"#{step_id}"
        )
    ),
    Div(id=next_step_id),  # PRESERVE: Empty div for next step
    id=step_id
)
```

### Phase 3: Update SUBMIT Handler
Only modify the marked sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Process form data
form = await request.form()
text_input = form.get(step.done, "").strip()

# CUSTOMIZE_VALIDATION: Validate user input
if not text_input:
    return P("Error: Text input is required", style=pip.get_style("error"))

# CUSTOMIZE_DATA_PROCESSING: Process the data as needed
processed_value = text_input  # Any transformations (e.g., title case, formatting)

# CUSTOMIZE_STATE_STORAGE: Save to state 
await pip.update_step_state(pipeline_id, step_id, processed_value, steps)
await self.message_queue.add(pip, f"{step.show} complete: {processed_value}", verbatim=True)

# Return standard revert control with chain reaction
return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {processed_value}", 
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

## Common Pitfalls
- Don't remove the chain reaction div with next_step_id
- Don't forget to validate input before saving
- Use `pip.update_step_state()` for proper state tracking
- Always handle finalized state in the GET handler

## Related Widget Recipes
- [Dropdown Selection Widget](03_dropdown_selection_widget.md)
- [URL Input Widget](02_botify_url_widget.md) 