# Pipulate Workflow Implementation Guide

## Overview
This guide serves as the primary reference for building and modifying workflows within the Pipulate framework. It focuses on core patterns, step management, and maintaining the crucial HTMX chain reaction mechanism.

## Core Patterns Reference
Before implementing workflows, familiarize yourself with these essential patterns:

- [Atomic Steps Pattern](mdc:.cursor/rules/pattern-atomic-steps.mdc): How to design focused, purposeful workflow steps
- [Chain Reaction Pattern](mdc:.cursor/rules/pattern-chain-reaction.mdc): Critical HTMX progression mechanism
- [Placeholder Pattern](mdc:.cursor/rules/pattern-placeholder.mdc): Starting point for new steps
- [Widget Implementation](mdc:.cursor/rules/pattern-widget-implementation.mdc): UI component standards
- [Browser Integration](mdc:.cursor/rules/pattern-browser-integration.mdc): Working with web browsers

## Implementation Philosophy
Follow these established philosophies:

- [Core Philosophy](mdc:.cursor/rules/philosophy-core.mdc): Fundamental principles
- [Modern Simplicity](mdc:.cursor/rules/philosophy-simplicity.mdc): Design approach
- [Future-Proofing](mdc:.cursor/rules/philosophy-future-proofing.mdc): Long-term considerations

## Core Principles

### 1. State Management
- Widgets should never manage workflow state directly
- Use core workflow methods for state transitions
- Maintain widget state within workflow state
- Never manipulate state directly
- Use `pip.finalize_workflow()` for locking
- Use `pip.unfinalize_workflow()` for unlocking
- Use `pip.rebuild()` for UI updates

### 2. UI Construction
- Follow template patterns for widget UI
- Use standard components
- Maintain consistent structure
- Keep container hierarchy consistent
- Use proper HTMX triggers
- Follow template layout

### 3. Error Handling
- Use standard error patterns
- Provide clear error messages
- Handle edge cases gracefully
- Validate all inputs
- Use consistent error presentation
- Handle edge cases gracefully

## Critical Patterns

### 1. Chain Reaction Pattern
```python
# CRITICAL: This pattern is IMMUTABLE
return Div(
    Card(...), # Current step's content
    # CRITICAL: This inner Div triggers loading of the next step
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

### 2. Widget Container Pattern
```python
# Standard widget container structure
return Div(
    Card(
        H3(f"{step.show}"),
        Form(
            Input(...),
            Button(...),
            hx_post=f"/{app_name}/{step_id}_submit"
        )
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

### 3. State Management Pattern
```python
# Reading state
state = pip.read_state(pipeline_id)
step_data = pip.get_step_data(pipeline_id, step_id, {})

# Updating state
await pip.update_step_state(pipeline_id, step_id, value, steps)

# Finalizing state
await pip.finalize_workflow(pipeline_id)
return pip.rebuild(app_name, steps)
```

## Common Widget Patterns

### 1. Dropdown Widget
```python
async def step_01(self, request):
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_01"
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Get options using core methods
    options = await self.get_options(pipeline_id)
    
    # Format options using standard patterns
    formatted_options = [await self.format_option(opt) for opt in options]
    
    # Return using standard container structure
    return Div(
        Card(
            H3(f"{step.show}"),
            Form(
                Select(*formatted_options),
                Button("Submit", type="submit")
            )
        ),
        id=step_id
    )
```

### 2. Text Input Widget
```python
async def step_01(self, request):
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_01"
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Get current value using core methods
    current_value = pip.get_step_data(pipeline_id, step_id, {}).get(step.done, "")
    
    # Return using standard container structure
    return Div(
        Card(
            H3(f"{step.show}"),
            Form(
                Input(value=current_value),
                Button("Submit", type="submit")
            )
        ),
        id=step_id
    )
```

## Common Pitfalls

### 1. Direct State Manipulation
```python
# ❌ Broken Pattern
state = pip.read_state(pipeline_id)
state["widget_value"] = value
pip.write_state(pipeline_id, state)

# ✅ Correct Pattern
await pip.update_step_state(pipeline_id, step_id, value, steps)
```

### 2. Manual UI Construction
```python
# ❌ Broken Pattern
return Card(
    H3("Widget Title"),
    Form(
        Input(value=value),
        Button("Submit")
    )
)

# ✅ Correct Pattern
return Div(
    Card(
        H3(f"{step.show}"),
        Form(
            Input(value=value),
            Button("Submit", type="submit")
        )
    ),
    id=step_id
)
```

### 3. Inconsistent Container Structure
```python
# ❌ Broken Pattern
return Div(
    Card(...),
    id=step_id
)

# ✅ Correct Pattern
return Div(
    Card(...),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

## Recovery Process

### 1. Identify the Break
- Look for direct state manipulation
- Check for manual UI construction
- Verify container structure
- Check for missing chain reactions
- Verify state transitions

### 2. Apply the Fix
- Replace direct state updates with core methods
- Use standard rebuild patterns
- Restore container hierarchy
- Fix chain reactions
- Update state transitions

### 3. Verify the Recovery
- Check state transitions
- Validate UI structure
- Confirm workflow behavior
- Test revert functionality
- Verify error handling

## Prevention Guidelines

### 1. State Management
- Use core workflow methods
- Never manipulate state directly
- Maintain consistent state structure
- Use proper state transitions
- Handle finalization correctly

### 2. UI Construction
- Follow template patterns
- Use standard components
- Maintain consistent structure
- Keep container hierarchy
- Use proper HTMX triggers

### 3. Error Handling
- Use standard error patterns
- Provide clear error messages
- Handle edge cases gracefully
- Validate all inputs
- Use consistent error presentation

## Recovery Checklist

### 1. State Management
- [ ] Using core workflow methods
- [ ] No direct state manipulation
- [ ] Consistent state structure
- [ ] Proper state transitions
- [ ] Correct finalization

### 2. UI Construction
- [ ] Using standard components
- [ ] Following template patterns
- [ ] Proper container structure
- [ ] Correct chain reactions
- [ ] Proper HTMX triggers

### 3. Error Handling
- [ ] Using standard error patterns
- [ ] Clear error messages
- [ ] Edge case handling
- [ ] Input validation
- [ ] Error recovery

### 4. Container Structure
- [ ] Correct hierarchy
- [ ] Proper HTMX triggers
- [ ] Consistent layout
- [ ] Chain reaction intact
- [ ] Proper widget containers

## Implementation Steps

### 1. Widget Setup
1. Define widget configuration
2. Set unique APP_NAME
3. Set distinct DISPLAY_NAME
4. Configure widget options
5. Set up error handling

### 2. Core Implementation
1. Implement core methods
2. Handle state management
3. Construct UI elements
4. Handle form submission
5. Manage error cases

### 3. Testing and Validation
1. Test widget behavior
2. Verify state management
3. Check error handling
4. Test edge cases
5. Document implementation

## Advanced Patterns

### 1. Polling and Terminal Steps
```python
# Polling pattern
return Div(
    result_card,
    progress_indicator,
    cls="polling-status no-chain-reaction",
    hx_get=f"/{app_name}/check_status",
    hx_trigger="load, every 2s",
    hx_target=f"#{step_id}",
    id=step_id
)

# Terminal pattern
return Div(
    result_card,
    download_button,
    cls="terminal-response no-chain-reaction",
    id=step_id
)
```

### 2. Revert Control
```python
# Revert control pattern
return Div(
    pip.revert_control(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: {value}",
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

### 3. Message Queue
```python
# Message queue pattern
await self.message_queue.add(
    pip,
    message,
    verbatim=True,
    spaces_before=0,
    spaces_after=1
)
```

## Best Practices

### 1. Development
1. Start with placeholders
2. Add functionality incrementally
3. Test each phase
4. Maintain proper state
5. Keep LLM informed

### 2. Implementation
1. Follow template patterns
2. Use standard components
3. Maintain consistent structure
4. Handle errors properly
5. Test thoroughly

### 3. Deployment
1. Test configuration
2. Verify state management
3. Check error handling
4. Test edge cases
5. Document implementation

## Reference Examples

### 1. Basic Workflows
- [20_hello_workflow.py](mdc:pipulate/plugins/20_hello_workflow.py): Template
- [035_url_opener.py](mdc:pipulate/plugins/035_url_opener.py): URL handling

### 2. Complex Workflows
- [50_botify_export.py](mdc:pipulate/plugins/50_botify_export.py): Multi-step
- [60_widget_examples.py](mdc:pipulate/plugins/60_widget_examples.py): Widget patterns

## Additional Resources

### 1. Implementation Guides
- [HTMX Integration](mdc:.cursor/rules/implementation-htmx.mdc)
- [Error Handling](mdc:.cursor/rules/implementation-widget-error.mdc)
- [Mobile Support](mdc:.cursor/rules/implementation-widget-mobile.mdc)
- [Accessibility](mdc:.cursor/rules/implementation-widget-accessibility.mdc)

### 2. Architecture Guides
- [Core Architecture](mdc:.cursor/rules/architecture-core.mdc)
- [State Management](mdc:.cursor/rules/architecture-state.mdc)

Remember: Workflows are intentionally WET (Write Everything Twice) to allow maximum customization while maintaining consistent patterns. Follow the established patterns but feel free to adapt them to your specific needs.

# PIPULATE WORKFLOW PROGRESSION GUIDE

## 1. EMPTY WORKFLOW (LANDING → FINALIZE)
┌─────────────┐                  ┌───────────┐
│   landing   │                  │  finalize │
│  (method)   │ ---------------> │  (method) │
└─────────────┘                  └───────────┘

Key Code Connection:
```python
# In landing method return statement
return Div(
    Card(...),
    # Chain reaction initiator - NEVER REMOVE OR MODIFY THIS PATTERN
    Div(id="finalize", hx_get=f"/{app_name}/finalize", hx_trigger="load"),
    id="landing"
)
```

## 2. INSERTING STEP_01 (LANDING → STEP_01 → FINALIZE)
┌─────────────┐        ┌──────────────┐        ┌───────────┐
│   landing   │        │    step_01   │        │  finalize │
│  (method)   │ -----> │ (placeholder)│ -----> │  (method) │
└─────────────┘        └──────────────┘        └───────────┘

Changes Required:
1. Add step_01 to steps list in __init__
2. Create step_01 and step_01_submit methods
3. Modify landing chain reaction to point to step_01

```python
# Updated landing return statement 
return Div(
    Card(...),
    # Chain reaction now points to step_01 - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="step_01", hx_get=f"/{app_name}/step_01", hx_trigger="load"),
    id="landing"
)

# step_01 method 
return Div(
    Card(...),
    # Chain reaction to finalize - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="finalize", hx_get=f"/{app_name}/finalize", hx_trigger="load"),
    id="step_01"
)
```

## 3. ADDING STEP_02 (LANDING → STEP_01 → STEP_02 → FINALIZE)
┌─────────────┐        ┌──────────────┐        ┌──────────────┐        ┌───────────┐
│   landing   │        │    step_01   │        │    step_02   │        │  finalize │
│  (method)   │ -----> │ (placeholder)│ -----> │ (placeholder)│ -----> │  (method) │
└─────────────┘        └──────────────┘        └──────────────┘        └───────────┘

Changes Required:
1. Add step_02 to steps list in __init__
2. Create step_02 and step_02_submit methods
3. Modify step_01 chain reaction to point to step_02

```python
# Updated step_01 return statement
return Div(
    Card(...),
    # Chain reaction now points to step_02 - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="step_02", hx_get=f"/{app_name}/step_02", hx_trigger="load"),
    id="step_01"
)

# step_02 method
return Div(
    Card(...),
    # Chain reaction to finalize - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="finalize", hx_get=f"/{app_name}/finalize", hx_trigger="load"),
    id="step_02"
)
```

## 4. COMPLETE WORKFLOW WITH STEP_03 (LANDING → STEP_01 → STEP_02 → STEP_03 → FINALIZE)
┌─────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌───────────┐
│   landing   │        │    step_01   │        │    step_02   │        │    step_03   │        │  finalize │
│  (method)   │ -----> │ (placeholder)│ -----> │ (placeholder)│ -----> │ (placeholder)│ -----> │  (method) │
└─────────────┘        └──────────────┘        └──────────────┘        └──────────────┘        └───────────┘

Changes Required:
1. Add step_03 to steps list in __init__
2. Create step_03 and step_03_submit methods
3. Modify step_02 chain reaction to point to step_03

```python
# Updated step_02 return statement
return Div(
    Card(...),
    # Chain reaction now points to step_03 - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="step_03", hx_get=f"/{app_name}/step_03", hx_trigger="load"),
    id="step_02"
)

# step_03 method
return Div(
    Card(...),
    # Chain reaction to finalize - CRITICAL PATTERN, DO NOT MODIFY
    Div(id="finalize", hx_get=f"/{app_name}/finalize", hx_trigger="load"),
    id="step_03"
)
```

## 5. DYNAMIC CHAIN REACTION (GENERALIZED PATTERN)
For any step_XX in a workflow:

┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   step_prev  │        │    step_XX   │        │   step_next  │
│   (method)   │ -----> │  (your step) │ -----> │   (method)   │
└──────────────┘        └──────────────┘        └──────────────┘

Key Pattern Code:
```python
# Determine the next step dynamically
next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'

# Return with proper chain reaction
return Div(
    Card(...),
    # Dynamic chain reaction - CRITICAL PATTERN, DO NOT MODIFY
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

## 6. CRITICAL CHAIN REACTION ELEMENTS

┌───────────────────────────────────────────────────────────────────┐
│ CHAIN REACTION COMPONENT                                          │
├───────────────────────────────────────────────────────────────────┤
│ Div(id=next_step_id,                                              │
│     hx_get=f"/{app_name}/{next_step_id}",                         │
│     hx_trigger="load")                                            │
└───────────────────────────────────────────────────────────────────┘
   │
   │ Must preserve these three attributes
   ▼
┌───────────────────────────────────────────────────────────────────┐
│ id=next_step_id   : Container to be replaced with next step       │
│ hx_get=...        : URL to fetch next step content                │
│ hx_trigger="load" : Automatically triggers when this div appears  │
└───────────────────────────────────────────────────────────────────┘

## 7. STEP METHOD STRUCTURE AND CONNECTIONS

           ┌── Shared step_id = "step_XX"
           │
           │         ┌─ Common code pattern
           ▼         ▼
┌────────────────────────────────────────┐      ┌────────────────────────────────────────┐
│           step_XX (GET)                │      │          step_XX_submit (POST)         │
├────────────────────────────────────────┤      ├────────────────────────────────────────┤
│ 1. Get step metadata                   │      │ 1. Get step metadata                   │
│ 2. Get pipeline state                  │──┐   │ 2. Process form submission             │
│ 3. Display form with submit button     │  │   │ 3. Validate input                      │
│ 4. Include revert button               │  │   │ 4. Save state                          │
│ 5. Setup chain reaction to next step   │  │   │ 5. Update progress message             │
└────────────────────────────────────────┘  │   │ 6. Setup chain reaction to next step   │
                                            │   └────────────────────────────────────────┘
                                            │                      │
                                            │                      │
                                            ▼                      ▼
                               ┌────────────────────────────────────────────┐
                               │              hx_post                       │
                               │  Form(...                                  │
                               │    hx_post=f"/{app_name}/{step_id}_submit" │
                               │  )                                         │
                               └────────────────────────────────────────────┘


## 8. SPLICING IN NEW STEPS (BETWEEN STEP_01 AND STEP_02)
Before:
  step_01 → step_02

After:
  step_01 → new_step → step_02

Required Changes:
1. Add new_step to steps list between step_01 and step_02
2. Update step_indices in __init__
3. Create new_step and new_step_submit methods
4. Modify step_01's chain reaction to point to new_step
5. Set new_step's chain reaction to point to step_02


## 9. REFILL PARAMETER AND STATE FLOW BEHAVIOR

┌─────────────────────────────────────────────────────────────┐
│ REFILL=FALSE (Forward-Only Flow)                            │
├─────────────────────────────────────────────────────────────┤
│ 1. User completes steps: 01 → 02 → 03                       │
│ 2. User reverts to step_01                                  │
│ 3. Form shows with NO pre-filled values                     │
│ 4. Step_02 and step_03 data completely cleared              │
│ 5. Must fill each step again sequentially                   │
└─────────────────────────────────────────────────────────────┘
  vs.
┌─────────────────────────────────────────────────────────────┐
│ REFILL=TRUE (Iterative Flow)                                │
├─────────────────────────────────────────────────────────────┤
│ 1. User completes steps: 01 → 02 → 03                       │
│ 2. User reverts to step_01                                  │
│ 3. Form shows with PREVIOUS values pre-filled               │
│ 4. Step_02 and step_03 data still cleared                   │
│ 5. Previous inputs remembered but still must progress again │
└─────────────────────────────────────────────────────────────┘

For true "forward-only" workflows with strict dependencies between steps,
use `refill=False` to reinforce that reverting means starting over from that point.

## Important: The refill Parameter
- For strict forward-only workflows (where changing a previous step should completely invalidate
  subsequent steps), use `refill=False`
- For more flexible workflows where users might iterate and refine inputs, use `refill=True`
- This choice affects both the user experience and the conceptual integrity of the workflow

# CRITICAL PATTERN WARNING

When implementing workflows in Pipulate, one pattern is absolutely critical and must never be modified:

## The Chain Reaction Pattern

```python
# In step_XX or step_XX_submit return statement
return Div(
    Card(...), # Current step's content
    # CRITICAL: This inner Div triggers loading of the next step
    # DO NOT REMOVE OR MODIFY these attributes:
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
```

### Why This Pattern Is Essential

1. **Explicit Triggering**: The `hx_trigger="load"` attribute explicitly tells HTMX to load the next step immediately after this content is rendered
2. **Direct Initialization**: This approach eliminates race conditions and timing issues that may occur with event bubbling
3. **Reliable Implementation**: This pattern has been tested across the entire codebase and ensures consistent progression
4. **Documented Standard**: All workflow examples follow this pattern, and it should be considered immutable

### Dangerous Modifications to Avoid

- **DO NOT** remove `hx_trigger="load"` even if it seems redundant
- **DO NOT** attempt to replace explicit chain reaction with implicit event bubbling
- **DO NOT** implement alternative flow mechanisms without extensive testing

Such changes will appear to work in limited testing but will inevitably break more complex workflows.

### Breaking the Chain (Cautionary Pattern)
    The `no-chain-reaction` class should only be used in two specific scenarios:

    1. **Terminal responses** - For endpoints requiring explicit user action:
    ```python
    return Div(
        result_card,
        download_button,
        cls="terminal-response no-chain-reaction",
        id=step_id
    )
    ```

    2. **Polling states** - For continuous status checking without progression:
    ```python
    return Div(
        result_card,
        progress_indicator,
        cls="polling-status no-chain-reaction",
        hx_get=f"/{app_name}/check_status",
        hx_trigger="load, every 2s",
        hx_target=f"#{step_id}",
        id=step_id
    )
    ```

### Best Practices
    - Always maintain the chain reaction pattern unless absolutely necessary
    - When breaking the chain, provide clear UI indicators of what's happening
    - Resume the chain reaction as soon as the exceptional condition is complete
    - Document any use of `no-chain-reaction` with explicit comments explaining why

# PLACEHOLDER STEP PATTERN

## Overview
Placeholder steps are skeletal workflow steps that serve as preparation points for inserting fully-functional steps later. They maintain the standard workflow progression pattern while collecting minimal or no user data.

## When to Use Placeholder Steps
- When planning a workflow's structure before implementing detailed functionality
- When creating a step that will be replaced with more complex widgets later
- When needing a "confirmation" or "review" step between functional steps
- When creating a template for different widget types

## Implementation Pattern
To add a placeholder step to an existing workflow:

### 1. Add the Step Definition
    ```python
        Step(
    id='step_XX',            # Use proper sequential numbering
    done='placeholder',      # Simple state field name
    show='Placeholder Step', # Descriptive UI text
    refill=True,             # Usually True for consistency
),
```

### 2. Create the GET Handler Method
    ```python
    async def step_XX(self, request):
    """Handles GET request for placeholder step."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_XX"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get("pipeline_id", "unknown")
        state = pip.read_state(pipeline_id)
        
    # Simple form with just a proceed button
        return Div(
        Card(
            H4(f"{step.show}"),
            P("Click Proceed to continue to the next step."),
            Form(
                Button("Proceed", type="submit", cls="primary"),
                Button("Revert", type="button", cls="secondary",
                       hx_post=f"/{app_name}/handle_revert",
                       hx_vals=f'{{"step_id": "{step_id}"}}'),
                hx_post=f"/{app_name}/{step_id}_submit",
            ),
        ),
        # CRITICAL: Chain reaction to next step - DO NOT MODIFY OR REMOVE
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    ```

    2. **POST Handler Pattern**:
    ```python
    async def step_XX_submit(self, request):
        """Process the submission for Step XX."""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_XX"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        pipeline_id = db.get("pipeline_id", "unknown")
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        
        # Process form data
        form = await request.form()
        value = form.get("field_name", "")
        
        # Validate
        if not value:
            return P("Error: Field is required", style=pip.get_style("error"))
        
        # Store in state
        state = pip.read_state(pipeline_id)
        state[step.done] = value
        pip.write_state(pipeline_id, state)
        
        # Update progress and message
        await pip.update_step_state(pipeline_id, step_id, value, steps)
        await self.message_queue.add(pip, f"{step.show} complete: {value}", verbatim=True)
        
        # Return response with chain reaction
        return Div(
            Card(...),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    ```

    ## Adding or Inserting Steps
    To add a new step or insert one between existing steps:

    1. **Add to the steps list** in the correct position
    2. **Update step indices** in the steps_indices dictionary in __init__
    3. **Create both handler methods** following the patterns above
    4. **Verify chain reactions** in surrounding steps
    5. **Add suggestion text** in the get_suggestion method

    For placeholder steps, see the [placeholder-step-pattern](mdc:.cursor/rules/placeholder-step-pattern.mdc) rule.

    ## State Management
    - Use Pipulate helpers for state:
      - `pip.read_state(pipeline_id)`
      - `pip.get_step_data(pipeline_id, step_id, {})`
      - `pip.update_step_state(pipeline_id, step_id, val, steps)`
    - Handle finalization properly
    - Clear state appropriately on revert

    ## Message Queue Usage
    - Use ordered message delivery:
    ```python
    await self.message_queue.add(
        pip,
        message,
        verbatim=True,
        spaces_before=0,
        spaces_after=1
    )
    ```

    ## Error Handling
    - Validate all inputs
    - Use consistent error presentation
    - Provide clear user feedback
    - Handle edge cases gracefully
    - Example:
    ```python
    try:
        # Operation
    except Exception as e:
        return P(f"Error: {str(e)}", style=pip.get_style("error"))
    ```

    ## Advanced Features
    - Use transform functions for step data flow
    - Implement custom state preservation
    - Use advanced revert controls when needed
    - Track progress for long operations
    - Handle file operations safely

    ## Documentation
    - Provide clear docstrings
    - Document step dependencies
    - Explain state management
    - Detail UI/UX considerations
    - Document error handling

    ## Testing Considerations
    - Test step progression
    - Verify state management
    - Check revert functionality
    - Validate error handling
    - Test chain reactions

    ## Special Cases and Edge Case Handling
    1. **Terminal steps** may break the chain reaction pattern
    2. **Polling operations** require special HTMX handling
    3. **File downloads** use no-chain-reaction with manual continuation
    4. **Error recoveries** should guide users on how to proceed

    Remember: Workflows are intentionally WET (Write Everything Twice) to allow maximum customization while maintaining consistent patterns.

    Reference Examples:
    - [10_connect_with_botify.py](mdc:pipulate/plugins/10_connect_with_botify.py): Simple authentication workflow
    - [20_hello_workflow.py](mdc:pipulate/plugins/20_hello_workflow.py): Basic workflow template
    - [50_botify_export.py](mdc:pipulate/plugins/50_botify_export.py): Complex multi-step workflow
    - [60_widget_examples.py](mdc:pipulate/plugins/60_widget_examples.py): Visualizing data in workflow

These rules will make it easier to consistently add and modify steps in Pipulate workflows, ensuring proper chain reactions, state management, and UI patterns are preserved.

The key insight from our implementation was recognizing the importance of maintaining the HTMX chain reaction pattern and revert functionality, while creating a minimal step that can be expanded later with specific widget functionality.

---

Let me create a Cursor rule that documents the pattern for placeholder steps in Pipulate workflows:

```
# placeholder-step-pattern

## Overview
Placeholder steps are skeletal workflow steps that serve as preparation points for inserting fully-functional steps later. They maintain the standard workflow progression pattern while collecting minimal or no user data.

## When to Use Placeholder Steps
- When planning a workflow's structure before implementing detailed functionality
- When creating a step that will be replaced with more complex widgets later
- When needing a "confirmation" or "review" step between functional steps
- When creating a template for different widget types

## Implementation Pattern
To add a placeholder step to an existing workflow:

### 1. Add the Step Definition
```python
Step(
    id='step_XX',            # Use proper sequential numbering
    done='placeholder',      # Simple state field name
    show='Placeholder Step', # Descriptive UI text
    refill=True,             # Usually True for consistency
),
```

### 2. Create the GET Handler Method
```python
async def step_XX(self, request):
    """Handles GET request for placeholder step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    
    # Simple form with just a proceed button
        return Div(
        Card(
            H4(f"{step.show}"),
            P("Click Proceed to continue to the next step."),
                Form(
                    Button("Proceed", type="submit", cls="primary"),
                Button("Revert", type="button", cls="secondary",
                       hx_post=f"/{app_name}/handle_revert",
                       hx_vals=f'{{"step_id": "{step_id}"}}'),
                    hx_post=f"/{app_name}/{step_id}_submit", 
            ),
        ),
        # CRITICAL: Chain reaction to next step - DO NOT MODIFY OR REMOVE
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
```

### 3. Create the POST Handler Method
```python
async def step_XX_submit(self, request):
    """Process the submission for placeholder step."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    pipeline_id = db.get("pipeline_id", "unknown")
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    
    # Set a fixed completion value
    placeholder_value = "completed"
    
    # Update state and notify user
    await pip.update_step_state(pipeline_id, step_id, placeholder_value, steps)
    await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)
    
    # Return with revert control and chain reaction to next step
    return Div(
        pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
```

### 4. Add Suggestion for Step (Optional)
In the `get_suggestion` method, add a simple text for the placeholder:
```python
'... existing code ...

</rewritten_file> 
```

# ---
# ADDENDUM: ADVANCED WORKFLOW PATTERNS AND REAL-WORLD EXAMPLES
# ---

## Advanced Chain Reaction and HTMX Patterns

- **Polling and Terminal Steps:**
  - For steps that require polling (e.g., waiting for a background job), use:
    ```python
    return Div(
        result_card,
        Progress(),
        cls="polling-status no-chain-reaction",
        hx_get=f"/{app_name}/check_status",
        hx_trigger="load, every 2s",
        hx_target=f"#{step_id}",
        id=step_id
    )
    ```
  - For terminal steps (e.g., download complete):
    ```python
    return Div(
        Card(...),
        download_button,
        cls="terminal-response no-chain-reaction",
        id=step_id
    )
    ```
  - **Best Practice:** Always document and comment any break in the chain reaction.

## Revert Control and State Clearing

- **Pattern:**
  - Use `pip.revert_control(...)` in completed step views to allow users to revert to any previous step.
  - Example:
    ```python
    return Div(
        pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
    ```
- **State Clearing:**
  - On revert, always clear all state from the reverted step forward:
    ```python
    await pip.clear_steps_from(pipeline_id, step_id, steps)
    state = pip.read_state(pipeline_id)
    state["_revert_target"] = step_id
    pip.write_state(pipeline_id, state)
    ```
  - Then rebuild the UI from the reverted step.

## Widget Container Usage

- **Consistent UI:**
  - Always wrap widgets in `pip.widget_container(...)` for consistent styling and DOM structure.
  - Example:
    ```python
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: Configured",
        widget=custom_widget,
        steps=steps
    )
    return Div(
        content_container,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
    ```

## Message Queue and LLM Context

- **Pattern:**
  - Use `await self.message_queue.add(...)` to provide user feedback and keep the LLM context up to date.
  - Example:
    ```python
    await self.message_queue.add(pip, f"{step.show} complete: {value}", verbatim=True)
    pip.append_to_history(f"[WIDGET CONTENT] {step.show}: {value}")
    ```
  - Use `verbatim=True` for direct user messages, and LLM context for internal state.

## Advanced Widget and HTMX Integration

- **Prism.js, Mermaid, Marked.js:**
  - For widgets requiring client-side JS (syntax highlighting, diagrams, markdown), use unique widget IDs and HX-Trigger headers:
    ```python
    response.headers["HX-Trigger"] = json.dumps({
        "initializePrism": {"targetId": widget_id},
        "renderMermaid": {"targetId": f"{widget_id}_output", "diagram": diagram_syntax},
        "initMarked": {"widgetId": widget_id}
    })
    ```
  - See `520_widget_examples.py` for full patterns.

## Error Handling and User Feedback

- **Pattern:**
  - Always validate input and provide clear error messages:
    ```python
    if not value:
        return P("Error: Field is required", style=pip.get_style("error"))
    ```
  - For exceptions:
    ```python
    try:
        # ...
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        await self.message_queue.add(pip, error_msg, verbatim=True)
        return P(error_msg, style=pip.get_style("error"))
    ```

## File and Browser Automation Patterns

- **Selenium-wire and Download Structure:**
  - For browser automation and crawling, use `selenium-wire` to capture headers and save crawl data:
    ```python
    # Save headers, source, and DOM in a deterministic, reversible path
    save_dir = f"downloads/{app_name}/{hostname}/{date}/{encoded_path}/"
    with open(os.path.join(save_dir, "headers.json"), "w") as f:
        json.dump(headers, f, indent=2)
    with open(os.path.join(save_dir, "source.html"), "w") as f:
        f.write(page_source)
    with open(os.path.join(save_dir, "dom.html"), "w") as f:
        f.write(dom_html)
    ```
  - Always display the reconstructed URL and save path in the UI for verification.

## Cross-Referencing Real Plugin Files

- See these files for full, real-world patterns:
  - `pipulate/plugins/510_splice_workflow.py`: Multi-step, chain reaction, revert, and suggestion patterns
  - `pipulate/plugins/520_widget_examples.py`: Widget container, advanced JS widgets, and LLM context
  - `pipulate/plugins/040_parameter_buster.py`: Polling, file handling, and error recovery
  - `pipulate/plugins/550_browser_automation.py`: Browser automation, crawl/save, and error handling

## Common Advanced Patterns

- **Dynamic Step Insertion:**
  - Insert new steps by updating the steps list and indices, and ensure all chain reactions are updated.
- **Polling and Progress:**
  - Use polling patterns for background jobs, and break the chain reaction with clear UI cues.
- **Custom Widget Integration:**
  - Use unique IDs and HX-Trigger for client-side widget initialization.
- **Revert and State Flow:**
  - Always clear state forward from the reverted step, and use refill as appropriate.

## Troubleshooting and Debugging

- **Chain Reaction Not Progressing:**
  - Check for missing or incorrect `hx_trigger="load"` attributes.
  - Ensure next_step_id is calculated correctly.
- **Revert Not Working:**
  - Verify state clearing logic and UI rebuild after revert.
- **Widget Not Rendering:**
  - Check for missing widget_container or incorrect widget IDs.
  - Ensure HX-Trigger headers are set for JS widgets.
- **File/Browser Automation Issues:**
  - Check save paths, permissions, and error handling for browser steps.
- **User Feedback Not Appearing:**
  - Ensure all user-facing actions use `message_queue.add` and LLM context updates.

--- 