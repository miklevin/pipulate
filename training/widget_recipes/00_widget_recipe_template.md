# Widget Recipe Template

> ⚠️ **CRITICAL WARNING**: All widget implementations MUST preserve the chain reaction pattern:
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

This file serves as a template for creating new widget recipes. Follow this structure when documenting a new widget type.

## Format Overview

```markdown
# [Widget Name] Recipe

## Overview
Brief description of what the widget does and its key features.

## Core Concepts
- **Concept 1**: Brief explanation
- **Concept 2**: Brief explanation
- **Concept 3**: Brief explanation

## Implementation Phases

### Phase 1: [First Phase Name]
Code and explanation for the first implementation phase.

```python
# Code example
```

### Phase 2: [Second Phase Name]
Code and explanation for the second implementation phase.

```python
# Code example
```

### Phase 3: [Third Phase Name]
Code and explanation for the third implementation phase.

```python
# Code example
```

### Phase 4: [Optional Phases]
Additional phases as needed.

## Sample Data
Example data for testing, if applicable.

## Common Pitfalls
- **Pitfall 1**: How to avoid it
- **Pitfall 2**: How to avoid it
- **Pitfall 3**: How to avoid it

## Related Widget Recipes
- [Related Widget 1](path/to/widget1.md)
- [Related Widget 2](path/to/widget2.md)
```

## Implementation Guidelines

### 1. Customization Points

Always use the standard customization point markers:

```python
# CUSTOMIZE_STEP_DEFINITION
# CUSTOMIZE_VALUE_ACCESS
# CUSTOMIZE_DISPLAY
# CUSTOMIZE_COMPLETE
# CUSTOMIZE_FORM
# CUSTOMIZE_FORM_PROCESSING
# CUSTOMIZE_VALIDATION
# CUSTOMIZE_DATA_PROCESSING
# CUSTOMIZE_STATE_STORAGE
# CUSTOMIZE_WIDGET_DISPLAY
```

### 2. Critical Preservation Points

Always include and emphasize these preservation notes:

```python
# PRESERVE: Empty div for next step - DO NOT ADD hx_trigger HERE
# PRESERVE: Store state data
# PRESERVE: Return the revert control with chain reaction
```

### 3. Helper Methods

If the widget requires helper methods:
- Place them at the beginning of the recipe
- Provide clear documentation for each method
- Explain where to add them in the workflow class

### 4. State Management

Always document:
- What data is stored in state
- How to access it from other steps
- Any transformation applied before storage
- When to use `_preserve_completed` flag
- How to handle state during reverts

### 5. UI Components

Clearly identify:
- FastHTML components used
- Element IDs and classes
- Event handlers and HTMX attributes
- Mobile responsiveness considerations
- Accessibility features

### 6. Transform Functions

Document any transform functions:
```python
# Example transform function
transform=lambda prev_value: f"Processed: {prev_value}"
```
- Explain the input/output
- Document any side effects
- Note dependencies on other steps

### 7. Error Handling

Include patterns for:
- Input validation
- API error handling
- File operation errors
- State corruption recovery
- User feedback mechanisms

### 8. Mobile Responsiveness

Document:
- Layout considerations
- Touch interactions
- Screen size adaptations
- Loading states
- Error message display

### 9. Accessibility

Include:
- ARIA attributes
- Keyboard navigation
- Screen reader support
- Color contrast
- Focus management

## Recipe Categories

Organize recipes into these categories:

1. **Input Collection**
   - Text inputs
   - Selection widgets
   - File uploads
   - Multi-field forms

2. **Data Display**
   - Tables
   - Charts
   - Text formatting
   - Code display

3. **Operational**
   - API requests
   - File operations
   - Polling and progress
   - Authentication

4. **Specialized**
   - Integration with external libraries
   - Interactive visualizations
   - Custom data processing 

## State Management Patterns

### Basic State Storage
```python
# Store single value
await pip.update_step_state(pipeline_id, step_id, value, steps)

# Store complex data
state = pip.read_state(pipeline_id)
state[step_id] = {
    'value': value,
    'metadata': metadata,
    '_preserve_completed': True  # For download steps
}
pip.write_state(pipeline_id, state)
```

### State Access
```python
# Get step data
step_data = pip.get_step_data(pipeline_id, step_id, {})

# Get transformed data
transformed = step.transform(step_data.get(step.done)) if step.transform else step_data.get(step.done)
```

### State Preservation
```python
# For download steps
state[step_id]['_preserve_completed'] = True

# For revert handling
if state.get('_revert_target') == step_id:
    # Show input form
else:
    # Show completed state
```

## Error Recovery Patterns

### Input Validation
```python
if not value:
    return P("Error: Field is required", style=pip.get_style("error"))
```

### API Error Handling
```python
try:
    result = await api_call()
except Exception as e:
    return P(f"Error: {str(e)}", style=pip.get_style("error"))
```

### State Recovery
```python
if not pip.read_state(pipeline_id):
    return P("Error: Invalid state", style=pip.get_style("error"))
```

## Mobile Responsiveness Patterns

### Container Sizing
```python
Card(
    # Content
    style="max-width: 100%; overflow-x: auto;"
)
```

### Touch Interactions
```python
Button(
    "Submit",
    type="submit",
    cls="primary",
    style="min-height: 44px; min-width: 44px;"  # Touch target size
)
```

### Loading States
```python
Div(
    "Loading...",
    cls="loading-indicator",
    style="display: none;",
    _="on htmx:beforeRequest show me end on htmx:afterRequest hide me end"
)
```
