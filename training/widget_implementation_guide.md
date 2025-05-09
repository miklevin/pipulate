# Widget Implementation Guide

This guide provides patterns and best practices for implementing workflow widgets in Pipulate.

## Core Principles

1. Use the widget_container pattern for consistent styling and behavior
2. Follow the revert control pattern for step navigation
3. Implement proper HTMX triggers for dynamic updates
4. Use FastHTML components for DOM manipulation
5. Follow the Pipulate UI/UX guidelines

## Implementation Steps

1. Start with a placeholder step
2. Add the widget container
3. Implement the widget logic
4. Add revert controls
5. Test the workflow

## Best Practices

- Use consistent styling from Pipulate's style constants
- Implement proper error handling
- Follow the HTMX chain reaction pattern
- Use proper DOM targeting for updates
- Keep the UI responsive and user-friendly

## Common Patterns

### Widget Container
```python
def my_widget(step_id, app_name, steps):
    return pipulate.widget_container(
        step_id=step_id,
        app_name=app_name,
        steps=steps,
        message="Step message",
        widget=my_content
    )
```

### Revert Controls
```python
def my_step(step_id, app_name, steps):
    return pipulate.revert_control(
        step_id=step_id,
        app_name=app_name,
        steps=steps,
        message="Step message"
    )
```

### HTMX Updates
```python
def my_update():
    return Div(
        id="target-id",
        hx_post="/my-endpoint",
        hx_trigger="load",
        hx_swap="outerHTML"
    )
```

Remember to follow these patterns consistently across all workflow implementations. 