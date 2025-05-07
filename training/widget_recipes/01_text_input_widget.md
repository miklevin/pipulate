# Text Input Widget Recipe

> ⚠️ **CRITICAL WARNING**: This widget MUST preserve the chain reaction pattern:
> ```python
> Div(
>     Card(...), # Current step's content
>     # CRITICAL: This inner Div triggers loading of the next step
>     # DO NOT REMOVE OR MODIFY these attributes:
>     Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
>     id=step_id
> )
> ```
> See [Workflow Implementation Guide](../workflow_implementation_guide.md#the-chain-reaction-pattern) for details.

## Overview
This recipe transforms a placeholder step into a widget that collects text input with validation. This is the most basic form of user input and serves as a foundation for more complex input widgets.

## Core Concepts
- **Chain Reaction Pattern**: Maintains workflow progression through htmx triggers
- **State Management**: Properly tracks and updates step state
- **Validation**: Ensures input meets requirements before processing
- **Refill Support**: Allows users to modify previous inputs
- **Downstream Access**: Values are accessible in subsequent steps via `step_data.get(step.done)`
- **Mobile Responsiveness**: Adapts to different screen sizes and touch interactions
- **Accessibility**: Supports keyboard navigation and screen readers

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
    transform=lambda prev_value: prev_value.strip() if prev_value else ""  # Optional transform
),
```

### Phase 2: Update GET Handler
Only modify the marked sections:

```python
# CUSTOMIZE_VALUE_ACCESS:
text_value = step_data.get(step.done, "")  # Access the text value from state

# CUSTOMIZE_DISPLAY: Enhanced finalized state display with accessibility
return Div(
    Card(
        H3(f"🔒 {step.show}", id=f"{step_id}-title"),
        P(f"Input: {text_value}", id=f"{step_id}-value")
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id,
    role="region",
    aria-labelledby=f"{step_id}-title"
)

# CUSTOMIZE_COMPLETE: Enhanced completion display with accessibility
return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {text_value}", # Show value in revert control
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id,
    role="region",
    aria-live="polite"
)

# CUSTOMIZE_FORM: Replace with accessible text input form
display_value = text_value if (step.refill and text_value) else ""
return Div(
    Card(
        H3(f"{step.show}", id=f"{step_id}-form-title"),
        P("Enter text below:", id=f"{step_id}-form-instruction"),
        Form(
            Input(
                type="text", 
                name=step.done, 
                placeholder="Enter your text here", 
                value=display_value,  # Use refill value if available
                required=True,
                aria-required="true",
                aria-labelledby=f"{step_id}-form-title",
                aria-describedby=f"{step_id}-form-instruction",
                style="min-height: 44px;",  # Mobile touch target
                _="on keydown[key=='Enter'] halt the event then trigger click on <button[type='submit']/>"
            ),
            Div(
                Button(
                    "Submit", 
                    type="submit", 
                    cls="primary",
                    style="min-height: 44px; min-width: 44px;",  # Mobile touch target
                    aria-label="Submit text input"
                ),
                style="margin-top: 1vh; text-align: right;"
            ),
            hx_post=f"/{app_name}/{step_id}_submit", 
            hx_target=f"#{step_id}",
            _="on htmx:beforeRequest add .loading to <button[type='submit']/> end on htmx:afterRequest remove .loading from <button[type='submit']/> end"
        )
    ),
    Div(id=next_step_id),  # PRESERVE: Empty div for next step
    id=step_id,
    role="region",
    aria-labelledby=f"{step_id}-form-title"
)
```

### Phase 3: Update SUBMIT Handler
Only modify the marked sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Process form data with error handling
try:
form = await request.form()
text_input = form.get(step.done, "").strip()
except Exception as e:
    return P(f"Error processing form: {str(e)}", style=pip.get_style("error"))

# CUSTOMIZE_VALIDATION: Enhanced validation with specific error messages
if not text_input:
    return P("Error: Text input is required", style=pip.get_style("error"), role="alert")
if len(text_input) > 1000:  # Example length limit
    return P("Error: Text must be less than 1000 characters", style=pip.get_style("error"), role="alert")

# CUSTOMIZE_DATA_PROCESSING: Process the data with error handling
try:
processed_value = text_input  # Any transformations (e.g., title case, formatting)
except Exception as e:
    return P(f"Error processing input: {str(e)}", style=pip.get_style("error"), role="alert")

# CUSTOMIZE_STATE_STORAGE: Save to state with error handling
try:
await pip.update_step_state(pipeline_id, step_id, processed_value, steps)
await self.message_queue.add(pip, f"{step.show} complete: {processed_value}", verbatim=True)
except Exception as e:
    return P(f"Error saving state: {str(e)}", style=pip.get_style("error"), role="alert")

# Return standard revert control with chain reaction
return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {processed_value}", 
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id,
    role="region",
    aria-live="polite"
)
```

## Common Pitfalls
- Don't remove the chain reaction div with next_step_id
- Don't forget to validate input before saving
- Use `pip.update_step_state()` for proper state tracking
- Always handle finalized state in the GET handler
- Don't forget mobile touch target sizes (min 44px)
- Always include ARIA attributes for accessibility
- Handle keyboard navigation properly
- Include proper error handling and recovery

## Mobile Responsiveness
- Use appropriate touch target sizes (min 44px)
- Ensure text inputs are easily tappable
- Handle keyboard appearance properly
- Consider screen size constraints
- Use responsive layout patterns

## Accessibility Features
- ARIA labels and descriptions
- Keyboard navigation support
- Screen reader compatibility
- Error message announcements
- Focus management
- Color contrast compliance

## Related Widget Recipes
- [Dropdown Selection Widget](03_dropdown_selection_widget.md)
- [URL Input Widget](02_botify_url_widget.md) 

