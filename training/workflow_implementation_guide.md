# Guide and Primer On Pipulate Workflow Patterns

This serves as a comprehensive guide and primer on the fundamental patterns used for building
and modifying workflows within the Pipulate framework, particularly focusing on
step insertion and maintaining the crucial HTMX chain reaction mechanism. It
doesn't introduce new requirements *for* the codebase but rather documents *how*
the codebase works and how developers (or AI assistants) should interact with it
when adding or modifying workflow steps.

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
The placeholder step pattern is used to build the structure of a workflow with minimal functionality before implementing full step logic. It's ideal for scaffolding workflows and maintaining correct progression patterns.

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
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get("pipeline_id", "unknown")
    
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

## Critical Elements for Step Progression
- **Chain Reaction Pattern**: Using `hx_trigger="load"` to automatically load the next step
- **Proper Step Connections**: Each step must properly link to the next via the `next_step_id`
- **Finalization Flow**: All paths must eventually lead to the finalize step
- **Revert Controls**: Using `pip.revert_control()` consistently after step completion

## Benefits of Placeholder Steps
- Quickly build workflow structure with minimal implementation effort
- Test progression logic before implementing complex functionality
- Maintain consistent state management and navigation between steps
- Ensure proper revert and finalize capabilities from the beginning

## Common Pitfalls
- Missing `hx_trigger="load"` in the chain reaction div
- Forgetting to use `pip.revert_control()` for completed steps
- Not handling the finalization state properly
- Incorrect step indices in the steps_indices dictionary

## Implementation Strategy
When building workflows, consider starting with placeholder steps for all planned functionality, then incrementally replace each with full implementations while preserving the progression pattern.
```

---

This implementation plan focuses on how to **apply the principles outlined in the guide** when making changes, ensuring architectural integrity and adherence to existing patterns.

## 1. Core Patterns Recap (From Article & Codebase)

Before detailing changes, let's recap the essential patterns documented in the article and reflected in the codebase (`plugins/` files, `server.py`, `.cursorrules/`):

1.  **Workflow Structure:**
    * Workflows are Python classes within the `plugins/` directory.
    * They define metadata (`APP_NAME`, `DISPLAY_NAME`, `ENDPOINT_MESSAGE`, `TRAINING_PROMPT`).
    * Steps are defined sequentially in the `__init__` method using the `Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'])` structure.
    * Each step requires corresponding GET (`step_XX`) and POST (`step_XX_submit`) handler methods.
    * Core methods (`landing`, `init`, `finalize`, `unfinalize`, `handle_revert`, etc.) provide the workflow engine and should generally not be modified significantly.

2.  **HTMX Chain Reaction:**
    * This is the core mechanism for automatic step progression.
    * It relies on returning a specific `Div` structure from step handlers:
        ```python
        # In step_XX or step_XX_submit return statement
        return Div(
            Card(...), # Current step's content or completion view
            # CRITICAL: This inner Div triggers the loading of the next step
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id # Outer Div ID matches the current step
        )
        ```
    * The `hx_trigger="load"` on the inner `Div` causes HTMX to immediately fetch the content for the `next_step_id` as soon as the current step's content is swapped into the DOM.
    * Breaking this chain (using `no-chain-reaction` class) should only be done for specific cases like terminal responses or polling, as documented in `htmx-chain-reactions.mdc`.

3.  **State Management:**
    * Workflow state is stored per `pipeline_id` in the `pipeline` table (managed via `DictLikeDB` accessed through `self.pipeline` and `self.pipulate.table`).
    * The `pipulate` instance (`self.pipulate` or `pip`) provides helper methods for safe state interaction:
        * `pip.read_state(pipeline_id)`
        * `pip.get_step_data(pipeline_id, step_id, default={})`
        * `await pip.update_step_state(pipeline_id, step_id, value, steps)` (Recommended for saving primary step value)
        * `pip.write_state(pipeline_id, state)` (Use carefully for bulk updates)
        * `await pip.clear_steps_from(pipeline_id, step_id, steps)` (Used in `handle_revert`)
        * `await pip.finalize_workflow(pipeline_id)` / `await pip.unfinalize_workflow(pipeline_id)`

4.  **Placeholder Steps:**
    * As detailed in `placeholder-step-pattern.mdc` and the article, these are minimal steps used for scaffolding.
    * They implement the basic GET/POST handlers and maintain the chain reaction but collect no user data (usually just a "Proceed" button).
    * They use a simple `done='placeholder'` state field.

## 2. Required Changes (When Adding/Inserting Workflow Steps)

Based on the article's guidance and existing patterns, adding or inserting a new step (let's call it `step_new`) involves these specific changes:

1.  **Modify `__init__`:**
    * **Define the `Step`:** Add a new `Step(...)` definition for `step_new` into the `steps` list at the correct sequential position.
        ```python
        steps = [
            # ... existing steps before ...
            Step(id='step_new', done='new_field', show='New Step Label', refill=False, transform=None),
            # ... existing steps after ...
        ]
        ```
    * **Update Indices:** Regenerate `self.steps_indices` *after* defining the complete `steps` list to ensure correct mapping.
        ```python
        # Add this *after* the steps list definition
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}
        ```
    * **Register Routes:** Ensure the route registration loop runs *after* the `steps` list (including the new step) is finalized. This is already the standard structure, but verify.

2.  **Modify Adjacent Steps' Chain Reactions:**
    * **Preceding Step (`step_prev`):** Update the `Div` returned by `step_prev`'s GET and POST handlers. Its `id` should now be `step_new`, and `hx_get` should point to `/{app_name}/step_new`.
        ```python
        # In step_prev or step_prev_submit return statement
        return Div(
            Card(...), # step_prev content
            # Update this Div:
            Div(id="step_new", hx_get=f"/{app_name}/step_new", hx_trigger="load"),
            id="step_prev"
        )
        ```
    * **Subsequent Step (`step_next`):** No direct change needed here, but the new step must correctly point to it.

3.  **Create New Step Handlers:**
    * **`async def step_new(self, request):` (GET Handler)**
        * Follow the standard pattern: get `pip`, `db`, `steps`, `app_name`, `step_id`, `step_index`, `step`, `pipeline_id`, `state`, `step_data`.
        * Calculate `next_step_id` correctly (pointing to `step_next` or `'finalize'`).
        * Check for finalized state and return locked view if necessary.
        * Check for completion (`step.done` in `step_data`) and `_revert_target` to decide whether to show the completed view (using `pip.widget_container` or `pip.revert_control`) or the input form.
        * If showing the form, get `display_value` (using `step.refill` and `get_suggestion` if needed).
        * Add input prompt message using `self.message_queue.add(...)`.
        * Return the `Div` containing the `Card` with the form/widget, the critical chain reaction `Div` pointing to `next_step_id`, and the outer `id=step_id`.
    * **`async def step_new_submit(self, request):` (POST Handler)**
        * Follow the standard pattern: get context variables.
        * Process `await request.form()` to get `user_val`.
        * Perform validation using `pip.validate_step_input` and potentially custom checks. Return error component on failure.
        * Perform any necessary processing on `user_val` to get `processed_val`.
        * Save state using `await pip.update_step_state(pipeline_id, step_id, processed_val, steps)`.
        * Add completion message using `self.message_queue.add(...)`.
        * Check if finalize is needed (`pip.check_finalize_needed(...)`) and add appropriate message.
        * Return the navigation component using `pip.create_step_navigation(...)` which includes the revert control and the chain reaction `Div` for the next step.

4.  **Update `step_messages` (Optional but Recommended):**
    * Add entries for `step_new` in `self.step_messages` for clear UI feedback.

5.  **Update `get_suggestion` (Optional):**
    * If the new step's input can be derived from the previous step, update `get_suggestion` accordingly, potentially using the `transform` lambda defined in the `Step`.

## 3. Integration Strategy (Following Patterns)

Integrating new steps requires strict adherence to the established patterns documented in the article and codebase rules:

* **WET Workflow Convention:** Embrace the explicitness. Copy, paste, and modify the standard GET/POST handler structure for new steps. Avoid creating complex abstractions *within* a single workflow's step logic. Refer to `wet-workflows.mdc`.
* **HTMX Chain Reaction:** This is paramount. Double-check the `id`, `hx_get`, and `hx_trigger="load"` attributes in the returned `Div`s of *all* modified and new handlers. Ensure the `id` of the *inner* div matches the `next_step_id`, and the `hx_get` path is correct. Refer to `htmx-chain-reactions.mdc`.
* **Pipulate Helpers:** Consistently use `self.pipulate` (or `pip`) methods for state (`read_state`, `get_step_data`, `update_step_state`), UI generation (`revert_control`, `widget_container`, `create_step_navigation`, `fmt`), and validation (`validate_step_input`). This ensures integration with the core engine.
* **Placeholder Pattern:** For incremental development or complex steps, first implement a placeholder step following `placeholder-step-pattern.mdc`. This ensures the structure and connections are correct before adding complex logic or UI.
* **Message Queue:** Use `self.message_queue.add(pip, ...)` for all user-facing status updates in the chat sidebar to ensure messages appear in the correct order, especially during asynchronous operations.
* **Backward Compatibility:** Adhering to these patterns inherently maintains compatibility. The workflow engine relies on these structures. Deviations (like breaking the chain reaction incorrectly) are the primary risk to existing functionality. Modifying the *content* of steps is generally safe if the core patterns are preserved.

## 4. Implementation Plan (Guide for Adding a Step)

This plan outlines the recommended process for adding a new workflow step (`step_new`) between `step_prev` and `step_next`.

1.  **Backup:** Create a copy of the workflow file (e.g., `xx_my_flow (backup).py`) before starting.
2.  **Define Step:** Open the workflow file (e.g., `plugins/NN_my_flow.py`). Add the `Step(...)` definition for `step_new` in the `steps` list within `__init__` at the correct sequence.
3.  **Update Indices:** Immediately after the `steps` list, ensure `self.steps_indices = {step.id: i for i, step in enumerate(steps)}` is present to recalculate indices.
4.  **Update Preceding Step (`step_prev`):**
    * Locate the `return Div(...)` statement in both `async def step_prev(...)` and `async def step_prev_submit(...)`.
    * Find the inner chain reaction `Div`: `Div(id=step_next.id, hx_get=f"/{app_name}/{step_next.id}", hx_trigger="load")`.
    * Change its `id` and `hx_get` path to point to `step_new`: `Div(id="step_new", hx_get=f"/{app_name}/step_new", hx_trigger="load")`.
5.  **Create New GET Handler (`step_new`):**
    * Copy the structure from an existing GET handler (like `step_prev`).
    * Update `step_id = "step_new"`.
    * Ensure `next_step_id` is calculated correctly (should point to `step_next.id` or `'finalize'`).
    * Implement the logic for finalized, completed, and input states.
    * **Crucially:** Ensure the returned `Div` has the *outer* `id="step_new"` and the *inner* chain reaction `Div` points correctly to `next_step_id`.
    * *Checkpoint:* Run the workflow. Verify that after completing `step_prev`, `step_new`'s input form loads automatically. Check the HTML source for correct IDs and `hx_get` attributes.
6.  **Create New POST Handler (`step_new_submit`):**
    * Copy the structure from an existing POST handler.
    * Update `step_id = "step_new"`.
    * Implement form processing, validation, state saving (`update_step_state`), and user messages (`message_queue.add`).
    * Return the standard navigation component using `pip.create_step_navigation(...)`. This function correctly includes the chain reaction `Div` pointing to `next_step_id`.
    * *Checkpoint:* Run the workflow. Submit the `step_new` form. Verify the data is saved correctly (check logs/DB state). Verify the UI updates to the completed view for `step_new` and that `step_next` loads automatically.
7.  **Update Messages/Suggestions (Optional):**
    * Add entries to `self.step_messages` for `step_new`.
    * Update `get_suggestion` if applicable.
8.  **Testing:**
    * Test the full workflow sequence.
    * Test reverting *to* `step_new`.
    * Test reverting *from* `step_new` back to `step_prev`.
    * Test finalizing the workflow with `step_new` included.
    * Test unfinalizing and reverting again.
    * Test with invalid input in `step_new`.

### Potential Challenges & Risks

* **Broken Chain Reaction:** Forgetting `hx_trigger="load"` or having incorrect `id`/`hx_get` values. Mitigation: Carefully check the structure of returned `Div`s in logs or browser dev tools.
* **State Errors:** Incorrectly saving data (e.g., wrong key in `step.done`) or failing to clear state on revert. Mitigation: Use `pip.update_step_state` for primary values. Log state before/after updates for debugging. Test revert thoroughly.
* **Index Errors:** Forgetting to update `steps_indices` after modifying the `steps` list. Mitigation: Always place the index recalculation *after* the final `steps` list definition.
* **Syntax Errors:** Preventing server restart. Mitigation: Rely on the built-in `check_syntax` and manually run `python plugins/NN_my_flow.py` if needed.
* **UI Glitches:** Issues with client-side rendering (Mermaid, Prism, custom JS). Mitigation: Use unique IDs, employ `HX-Trigger` headers, use browser dev tools for JS debugging.

By carefully following the patterns established in the codebase and documented in the article and rules, you can reliably extend Pipulate workflows with new steps and widgets while maintaining the integrity of the system. Remember to leverage the placeholder pattern for complex additions.

# Critical Pattern Warning

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

# WIDGET RECIPE SYSTEM

This section introduces the widget recipe system - a collection of step-by-step guides for transforming placeholder steps into specific functional widgets while maintaining all critical workflow patterns.

## Overview of the Widget Recipe System

The widget recipe system provides standardized patterns for converting placeholder steps into various widget types, such as:

1. **Input Collection Widgets**:
   - Text input widgets
   - URL input widgets
   - Selection/dropdown widgets
   - Checkbox and radio button widgets

2. **Data Display Widgets**:
   - Pandas table widgets
   - Markdown rendering widgets
   - Mermaid diagram widgets
   - Code syntax highlighting widgets

3. **Operational Widgets**:
   - API request widgets
   - CSV download widgets
   - Polling status widgets
   - File upload widgets

## How to Use Widget Recipes

Widget recipes are designed to be applied to placeholder steps in your workflow. Each recipe follows this process:

1. **Locate the Customization Points**:
   Both placeholder GET and SUBMIT handlers contain clearly marked customization points:
   ```
   # CUSTOMIZE_STEP_DEFINITION
   # CUSTOMIZE_FORM
   # CUSTOMIZE_DISPLAY
   # CUSTOMIZE_COMPLETE
   # CUSTOMIZE_FORM_PROCESSING
   # CUSTOMIZE_DATA_PROCESSING
   # CUSTOMIZE_STATE_STORAGE
   # CUSTOMIZE_WIDGET_DISPLAY
   ```

2. **Apply the Recipe Changes**: 
   The recipe will provide specific code to insert at each customization point.

3. **Preserve Critical Patterns**:
   Each recipe maintains:
   - Chain reaction mechanism
   - Revert control functionality
   - State management patterns
   - Proper finalization handling

## Recipe Format

Each widget recipe follows a standard format:

I've analyzed the workflow implementation guide and have recommendations for enhancing it with a widget recipe system section that would fit well within the current structure. Here's how I would integrate it:

```markdown
# WIDGET RECIPE SYSTEM

This section introduces the widget recipe system - a collection of step-by-step guides for transforming placeholder steps into specific functional widgets while maintaining all critical workflow patterns.

## Overview of the Widget Recipe System

The widget recipe system provides standardized patterns for converting placeholder steps into various widget types, such as:

1. **Input Collection Widgets**:
   - Text input widgets
   - URL input widgets
   - Selection/dropdown widgets
   - Checkbox and radio button widgets

2. **Data Display Widgets**:
   - Pandas table widgets
   - Markdown rendering widgets
   - Mermaid diagram widgets
   - Code syntax highlighting widgets

3. **Operational Widgets**:
   - API request widgets
   - CSV download widgets
   - Polling status widgets
   - File upload widgets

## How to Use Widget Recipes

Widget recipes are designed to be applied to placeholder steps in your workflow. Each recipe follows this process:

1. **Locate the Customization Points**:
   Both placeholder GET and SUBMIT handlers contain clearly marked customization points:
   ```
   # CUSTOMIZE_STEP_DEFINITION
   # CUSTOMIZE_FORM
   # CUSTOMIZE_DISPLAY
   # CUSTOMIZE_COMPLETE
   # CUSTOMIZE_FORM_PROCESSING
   # CUSTOMIZE_DATA_PROCESSING
   # CUSTOMIZE_STATE_STORAGE
   # CUSTOMIZE_WIDGET_DISPLAY
   ```

2. **Apply the Recipe Changes**: 
   The recipe will provide specific code to insert at each customization point.

3. **Preserve Critical Patterns**:
   Each recipe maintains:
   - Chain reaction mechanism
   - Revert control functionality
   - State management patterns
   - Proper finalization handling

## Recipe Format

Each widget recipe follows a standard format:

```
# Widget Name Recipe

## Overview
Brief description of what the widget does.

## Implementation Phases
Step-by-step implementation instructions:

### Phase 1: Update Step Definition
Code changes for the Step namedtuple.

### Phase 2: Update GET Handler
Code changes for the GET handler.

### Phase 3: Update SUBMIT Handler
Code changes for the SUBMIT handler.

### Phase 4: Add Helper Methods (if needed)
Any additional helper methods required.

## Common Pitfalls
Things to watch out for.

## Related Widget Recipes
Links to related recipes.
```

## Widget Recipe Example: Basic Pandas Table Widget

Here's a snippet from the Pandas table widget recipe to illustrate the pattern:

```python
# CUSTOMIZE_FORM: Replace with CSV input form
return Div(
    Card(
        H3(f"{step.show}"),
        P("Enter CSV data below to create a Pandas DataFrame:"),
        Form(
            TextArea(
                display_value,
                name=step.done,
                placeholder="Paste CSV data here...",
                rows=8,
                required=True
            ),
            Div(
                Button("Create Table", type="submit", cls="primary"),
                style="margin-top: 1vh; text-align: right;"
            ),
            hx_post=f"/{app_name}/{step_id}_submit",
            hx_target=f"#{step_id}"
        )
    ),
    Div(id=next_step_id),
    id=step_id
)
```

For full recipes, refer to the individual widget recipe documents in the training folder.
```

