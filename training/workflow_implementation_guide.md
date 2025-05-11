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

## Workflow Structure

### 1. Basic Workflow (Landing → Finalize)
```
┌─────────────┐                  ┌───────────┐
│   landing   │                  │  finalize │
│  (method)   │ ---------------> │  (method) │
└─────────────┘                  └───────────┘
```

Key Code Pattern:
```python
# In landing method return statement
return Div(
    Card(...),
    # Chain reaction initiator - NEVER REMOVE OR MODIFY THIS PATTERN
    Div(id="finalize", hx_get=f"/{app_name}/finalize", hx_trigger="load"),
    id="landing"
)
```

### 2. Adding Steps
Follow the [Atomic Steps Pattern](mdc:.cursor/rules/pattern-atomic-steps.mdc) when adding new steps:

```python
Step(
    id='step_01',
    done='result_key',
    show='User-Friendly Name',
    refill=True,  # Allow value reuse
)
```

### 3. Step Implementation
Each step requires:

1. GET Handler:
```python
async def step_XX(self, request):
    """Handles GET request for Step XX."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    
    # Follow Widget Implementation Pattern for UI components
    return Div(
        Card(...),
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
```

2. POST Handler:
```python
async def step_XX_submit(self, request):
    """Process the submission for Step XX."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    
    # Follow Error Handling Pattern
    try:
        # Process form data
        form = await request.form()
        value = form.get("field_name", "")
        
        if not value:
            return P("Error: Field is required", style=pip.get_style("error"))
        
        # Update state following State Management Pattern
        await pip.update_step_state(pipeline_id, step_id, value, steps)
        
        # Return with chain reaction
        return Div(
            pip.widget_container(...),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    except Exception as e:
        return P(f"Error: {str(e)}", style=pip.get_style("error"))
```

## Critical Patterns

### Chain Reaction
The chain reaction pattern is IMMUTABLE. Never modify these elements:
```python
Div(
    id=next_step_id,
    hx_get=f"/{app_name}/{next_step_id}",
    hx_trigger="load"
)
```

### Widget Structure
Follow the [Widget Implementation Pattern](mdc:.cursor/rules/pattern-widget-implementation.mdc):
```python
Card(
    H3(f"{step.show}"),
    Form(
        Input(...),
        Button(...),
        hx_post=f"/{app_name}/{step_id}_submit"
    )
)
```

### State Management
Use Pipulate's state management helpers:
```python
# Read state
state = pip.read_state(pipeline_id)
step_data = pip.get_step_data(pipeline_id, step_id, {})

# Update state
await pip.update_step_state(pipeline_id, step_id, value, steps)
```

## Development Workflow

1. Start with Placeholders
   - Use the [Placeholder Pattern](mdc:.cursor/rules/pattern-placeholder.mdc)
   - Maintain chain reaction
   - Plan step progression

2. Evolve to Widgets
   - Follow [Widget Implementation](mdc:.cursor/rules/pattern-widget-implementation.mdc)
   - Add form elements
   - Implement validation

3. Add Functionality
   - Follow [Browser Integration](mdc:.cursor/rules/pattern-browser-integration.mdc) if needed
   - Implement error handling
   - Add user feedback

## Testing and Validation

1. Chain Reaction
   - Verify progression works
   - Test revert functionality
   - Check finalization

2. State Management
   - Test state persistence
   - Verify revert behavior
   - Check refill functionality

3. Error Handling
   - Test validation
   - Check error messages
   - Verify recovery paths

## Common Pitfalls

1. Chain Reaction Breaks
   - Missing `hx_trigger="load"`
   - Incorrect next_step_id calculation
   - Broken progression chain

2. State Management Issues
   - Not clearing subsequent steps on revert
   - Missing state updates
   - Incorrect refill behavior

3. UI/UX Problems
   - Inconsistent button placement
   - Missing error feedback
   - Poor progression indicators

## Best Practices

1. Follow Atomic Design
   - One clear purpose per step
   - Combine related actions
   - Maintain user mental model

2. Preserve Patterns
   - Use established widget structures
   - Maintain chain reaction
   - Follow state management conventions

3. Error Handling
   - Validate all inputs
   - Provide clear feedback
   - Handle edge cases

## Reference Examples

1. Basic Workflows
   - [20_hello_workflow.py](mdc:pipulate/plugins/20_hello_workflow.py): Template
   - [035_url_opener.py](mdc:pipulate/plugins/035_url_opener.py): URL handling

2. Complex Workflows
   - [50_botify_export.py](mdc:pipulate/plugins/50_botify_export.py): Multi-step
   - [60_widget_examples.py](mdc:pipulate/plugins/60_widget_examples.py): Widget patterns

## Additional Resources

1. Implementation Guides
   - [HTMX Integration](mdc:.cursor/rules/implementation-htmx.mdc)
   - [Error Handling](mdc:.cursor/rules/implementation-widget-error.mdc)
   - [Mobile Support](mdc:.cursor/rules/implementation-widget-mobile.mdc)
   - [Accessibility](mdc:.cursor/rules/implementation-widget-accessibility.mdc)

2. Architecture Guides
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
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    placeholder_value = step_data.get(step.done, "")
    
    # Check workflow finalization
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and placeholder_value:
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P("Placeholder step completed")
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
    # Check completion status
    if placeholder_value and state.get("_revert_target") != step_id:
        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    else:
        # Show minimal UI with just a Proceed button
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                P("This is a placeholder step. Click Proceed to continue to the next step."),
                Form(
                    Button("Proceed", type="submit", cls="primary"),
                    hx_post=f"/{app_name}/{step_id}_submit", 
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),  # Note: No hx_trigger="load" here to prevent auto-progression
            id=step_id
        )
```

### 3. Create the POST Handler Method
```python
async def step_XX_submit(self, request):
    """Process the submission for placeholder Step XX."""
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
'step_XX': """Placeholder step - no user content needed.

This step serves as a placeholder for future functionality."""
```

## Critical Elements to Preserve
1. **Chain Reaction Pattern**: 
   ```python
   # CRITICAL - DO NOT MODIFY OR REMOVE
   Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
   ```
   - The `id=next_step_id` identifies the container for the next step
   - The `hx_get` attribute loads the next step's content
   - The `hx_trigger="load"` attribute is REQUIRED for automatic progression
   - NEVER remove `hx_trigger="load"` even if you think event bubbling would work
   - This explicit triggering pattern is the standard throughout the codebase

2. **Revert Button**: Always include for consistent user experience
3. **Step Numbering**: Maintain proper sequential numbering
4. **State Management**: Always store state even if minimal
5. **Message Queue Updates**: Always notify of step completion

## Common Implementation Pitfalls
- **SERIOUS ERROR**: Removing `hx_trigger="load"` from the chain reaction div will break progression
- **SERIOUS ERROR**: Using an empty div without the required attributes
- **SERIOUS ERROR**: Using event bubbling or implicit triggering instead of explicit triggers
- Using incorrect next_step_id calculation (especially for the last step)
- Forgetting to update steps_indices after adding new steps
- Not preserving the chain reaction pattern in both GET and POST handlers

## Placement Considerations
- **First Step**: If replacing the first step, ensure proper initialization
- **Middle Step**: Ensure proper next_step_id and previous step chain reaction
- **Last Step**: Properly handle transition to 'finalize' instead of next_step_id

## Example
See [60_widget_examples.py](mdc:pipulate/plugins/60_widget_examples.py) step_07 for a complete placeholder implementation.

## Upgrading Later
When ready to replace the placeholder with functional content:
1. Keep the same step_id and step definition
2. Add necessary form elements to collect data
3. Enhance the submit handler to process the collected data
4. Preserve the chain reaction pattern and revert functionality

## Workflow Step Progression at a Glance

```
Empty Workflow                              Workflow With Multiple Steps
┌───────────────┐                          ┌───────────────┐
│ Landing Page  │                          │ Landing Page  │
└───────┬───────┘                          └───────┬───────┘
        │                                          │
        ▼                                          ▼
┌───────────────┐                          ┌───────────────┐
│    Form UI    │                          │    Form UI    │
│ (pipeline_id) │                          │ (pipeline_id) │
└───────┬───────┘                          └───────┬───────┘
        │                                          │
        ▼                                          ▼
┌───────────────┐                          ┌───────────────┐
│ Init Response │                          │ Init Response │
│  with step_01 │                          │  with step_01 │
│ div(hx_trigger│                          │ div(hx_trigger│
│    ="load")   │                          │    ="load")   │
└───────┬───────┘                          └───────┬───────┘
        │                                          │
        │ Chain Reaction                           │ Chain Reaction
        ▼                                          ▼
┌───────────────┐                          ┌───────────────┐
│   step_01     │                          │   step_01     │
│   GET UI      │                          │   GET UI      │
└───────┬───────┘                          └───────┬───────┘
        │                                          │
        │ User Clicks "Proceed"                    │ User Clicks "Proceed"
        ▼                                          ▼
┌───────────────┐                          ┌───────────────┐
│   step_01     │                          │   step_01     │
│  Submit UI    │                          │  Submit UI    │
│  revert_ctrl  │                          │  revert_ctrl  │
│ next_step div │                          │ next_step div │
│(hx_trigger=   │                          │(hx_trigger=   │
│    "load")    │                          │    "load")    │
└───────┬───────┘                          └───────┬───────┘
        │                                          │
        │ Chain Reaction                           │ Chain Reaction
        ▼                                          ▼
┌───────────────┐                          ┌───────────────┐
│   finalize    │                          │   step_02     │
│      GET      │                          │     GET       │
└───────────────┘                          └───────┬───────┘
                                                   │
                                                   │ More steps...
                                                   ▼
                                           ┌───────────────┐
                                           │   finalize    │
                                           │      GET      │
                                           └───────────────┘
```

## Key Components of a Placeholder Step

1. **Step Definition**
```python
Step(
    id='step_XX',            # Use proper sequential numbering
    done='placeholder',      # Simple state field name
    show='Placeholder Step', # Descriptive UI text
    refill=False,            # Use False for strict forward-only flow, True for iterative workflows
),
```

2. **GET Handler**
```python
async def step_XX(self, request):
    """Handles GET request for placeholder Step XX."""
    pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
    step_id = "step_XX"
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    placeholder_value = step_data.get(step.done, "")
    
    # Check workflow finalization
    finalize_data = pip.get_step_data(pipeline_id, "finalize", {})
    if "finalized" in finalize_data and placeholder_value:
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P("Placeholder step completed")
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
        
    # Check completion status
    if placeholder_value and state.get("_revert_target") != step_id:
        return Div(
            pip.revert_control(step_id=step_id, app_name=app_name, message=f"{step.show}: Complete", steps=steps),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    else:
        # Show minimal UI with just a Proceed button
        await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)
        
        return Div(
            Card(
                H3(f"{step.show}"),
                P("This is a placeholder step. Click Proceed to continue to the next step."),
                Form(
                    Button("Proceed", type="submit", cls="primary"),
                    hx_post=f"/{app_name}/{step_id}_submit", 
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),  # Note: No hx_trigger="load" here to prevent auto-progression
            id=step_id
        )
```

3. **POST Handler**
```python
async def step_XX_submit(self, request):
    """Process the submission for placeholder Step XX."""
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

## Error Recovery and Resilience

### 1. Error States
```python
# In step handler
try:
    # Operation
except Exception as e:
    # Log error
    await self.message_queue.add(pip, f"Error in {step_id}: {str(e)}", verbatim=True)
    
    # Return error UI with retry option
    return Div(
        Card(
            H3("Error Occurred"),
            P(f"An error occurred: {str(e)}"),
            Form(
                Button("Retry", type="submit", cls="primary"),
                hx_post=f"/{app_name}/{step_id}_submit"
            )
        ),
        id=step_id
    )
```

### 2. State Recovery
```python
# After error recovery
state = pip.read_state(pipeline_id)
if state.get("_error_state"):
    # Restore from error state
    error_data = state["_error_state"]
    await pip.update_step_state(pipeline_id, step_id, error_data["value"], steps)
    state.pop("_error_state")
    pip.write_state(pipeline_id, state)
```

## Workflow Lifecycle Management

### 1. Initialization
```python
async def initialize_workflow(self, request):
    """Initialize workflow state and resources."""
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Clear any existing state
    pip.clear_state(pipeline_id)
    
    # Initialize step indices
    self.steps_indices = {step.id: i for i, step in enumerate(self.steps)}
    
    # Set initial state
    state = {
        "_workflow_start": datetime.now().isoformat(),
        "_current_step": "landing"
    }
    pip.write_state(pipeline_id, state)
```

### 2. Cleanup
```python
async def cleanup_workflow(self, request):
    """Clean up workflow resources."""
    pipeline_id = db.get("pipeline_id", "unknown")
    
    # Archive state if needed
    if self.should_archive_state():
        await self.archive_workflow_state(pipeline_id)
    
    # Clear state
    pip.clear_state(pipeline_id)
```

## State Persistence Patterns

### 1. Temporary State
```python
# For short-lived data
state["_temp_data"] = {
    "timestamp": datetime.now().isoformat(),
    "value": temporary_value
}
```

### 2. Persistent State
```python
# For data that should survive workflow restarts
state["persistent_data"] = {
    "created_at": datetime.now().isoformat(),
    "value": persistent_value,
    "version": "1.0"
}
```

### 3. State Versioning
```python
# When state structure changes
state["_state_version"] = "2.0"
if state.get("_state_version") != "2.0":
    state = self.migrate_state(state)
```

## Advanced Chain Reaction Patterns

### 1. Conditional Progression
```python
# Only progress if condition is met
if should_progress:
    return Div(
        Card(...),
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
else:
    return Div(
        Card(...),
        id=step_id
    )
```

### 2. Delayed Progression
```python
# Progress after delay
return Div(
    Card(...),
    Div(
        id=next_step_id,
        hx_get=f"/{app_name}/{next_step_id}",
        hx_trigger="load delay:2s"
    ),
    id=step_id
)
```

### 3. Parallel Progression
```python
# Load multiple steps in parallel
return Div(
    Card(...),
    Div(id="step_a", hx_get=f"/{app_name}/step_a", hx_trigger="load"),
    Div(id="step_b", hx_get=f"/{app_name}/step_b", hx_trigger="load"),
    id=step_id
)
```

## Performance Optimization

### 1. State Caching
```python
# Cache frequently accessed state
@cached_property
def workflow_state(self):
    pipeline_id = db.get("pipeline_id", "unknown")
    return pip.read_state(pipeline_id)
```

### 2. Lazy Loading
```python
# Load step data only when needed
async def get_step_data(self, step_id):
    if not hasattr(self, '_step_data_cache'):
        self._step_data_cache = {}
    if step_id not in self._step_data_cache:
        self._step_data_cache[step_id] = await self.load_step_data(step_id)
    return self._step_data_cache[step_id]
```

### 3. Batch Processing
```python
# Process multiple items in batches
async def process_batch(self, items, batch_size=10):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        await self.process_items(batch)
        await self.message_queue.add(pip, f"Processed {i + len(batch)} items", verbatim=True)
```

## Security Considerations

### 1. Input Validation
```python
# Validate all user inputs
def validate_input(self, value, validation_rules):
    for rule in validation_rules:
        if not rule.validate(value):
            raise ValidationError(f"Input failed validation: {rule.message}")
    return True
```

### 2. State Sanitization
```python
# Sanitize state before storage
def sanitize_state(self, state):
    sanitized = {}
    for key, value in state.items():
        if key.startswith('_'):
            sanitized[key] = value
        else:
            sanitized[key] = self.sanitize_value(value)
    return sanitized
```

### 3. Access Control
```python
# Check user permissions
async def check_permission(self, request, required_permission):
    user = await self.get_current_user(request)
    if not user.has_permission(required_permission):
        raise PermissionError(f"User lacks required permission: {required_permission}")
```

## Workflow Debugging

### 1. Debug Mode
```python
# Enable debug mode for a workflow
async def enable_debug_mode(self, request):
    """Enable debug mode for workflow development."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    state["_debug_mode"] = True
    state["_debug_log"] = []
    pip.write_state(pipeline_id, state)
```

### 2. Debug Logging
```python
# Log debug information
async def debug_log(self, message, data=None):
    """Log debug information if debug mode is enabled."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    if state.get("_debug_mode"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "data": data
        }
        state["_debug_log"].append(log_entry)
        pip.write_state(pipeline_id, state)
```

### 3. State Inspection
```python
# Inspect workflow state
async def inspect_state(self, request):
    """Return current workflow state for debugging."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    return Div(
        Card(
            H3("Workflow State"),
            Pre(json.dumps(state, indent=2)),
            Button("Close", type="button", cls="secondary",
                   hx_get=f"/{app_name}/close_debug")
        ),
        id="debug_panel"
    )
```

## Workflow Monitoring

### 1. Performance Metrics
```python
# Track step performance
async def track_step_performance(self, step_id, start_time):
    """Track performance metrics for a step."""
    duration = (datetime.now() - start_time).total_seconds()
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    
    if "_performance_metrics" not in state:
        state["_performance_metrics"] = {}
    
    if step_id not in state["_performance_metrics"]:
        state["_performance_metrics"][step_id] = []
    
    state["_performance_metrics"][step_id].append({
        "timestamp": datetime.now().isoformat(),
        "duration": duration
    })
    
    pip.write_state(pipeline_id, state)
```

### 2. Progress Tracking
```python
# Track workflow progress
async def track_progress(self, step_id, status):
    """Track progress of workflow steps."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    
    if "_progress" not in state:
        state["_progress"] = {}
    
    state["_progress"][step_id] = {
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    pip.write_state(pipeline_id, state)
```

### 3. Error Tracking
```python
# Track workflow errors
async def track_error(self, step_id, error):
    """Track errors that occur during workflow execution."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    
    if "_errors" not in state:
        state["_errors"] = []
    
    state["_errors"].append({
        "step_id": step_id,
        "error": str(error),
        "timestamp": datetime.now().isoformat()
    })
    
    pip.write_state(pipeline_id, state)
```

## Monitoring Dashboard

### 1. Performance Overview
```python
# Display performance metrics
async def show_performance_metrics(self, request):
    """Display performance metrics for the workflow."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    metrics = state.get("_performance_metrics", {})
    
    return Div(
        Card(
            H3("Performance Metrics"),
            Table(
                Tr(Th("Step"), Th("Avg Duration"), Th("Min"), Th("Max")),
                *[Tr(
                    Td(step_id),
                    Td(f"{sum(m['duration'] for m in step_metrics) / len(step_metrics):.2f}s"),
                    Td(f"{min(m['duration'] for m in step_metrics):.2f}s"),
                    Td(f"{max(m['duration'] for m in step_metrics):.2f}s")
                ) for step_id, step_metrics in metrics.items()]
            )
        ),
        id="performance_metrics"
    )
```

### 2. Progress Overview
```python
# Display workflow progress
async def show_progress(self, request):
    """Display current progress of the workflow."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    progress = state.get("_progress", {})
    
    return Div(
        Card(
            H3("Workflow Progress"),
            *[Div(
                H4(step_id),
                P(f"Status: {data['status']}"),
                P(f"Last Updated: {data['timestamp']}")
            ) for step_id, data in progress.items()]
        ),
        id="progress_overview"
    )
```

### 3. Error Overview
```python
# Display workflow errors
async def show_errors(self, request):
    """Display errors that occurred during workflow execution."""
    pipeline_id = db.get("pipeline_id", "unknown")
    state = pip.read_state(pipeline_id)
    errors = state.get("_errors", [])
    
    return Div(
        Card(
            H3("Workflow Errors"),
            *[Div(
                H4(error["step_id"]),
                P(f"Error: {error['error']}"),
                P(f"Time: {error['timestamp']}")
            ) for error in errors]
        ),
        id="error_overview"
    )
```
