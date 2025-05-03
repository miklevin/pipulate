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

### 5. UI Components

Clearly identify:
- FastHTML components used
- Element IDs and classes
- Event handlers and HTMX attributes

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
