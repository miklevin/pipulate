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

    # Store minimal state data
    placeholder_value = "completed"
    state = pip.read_state(pipeline_id)
    state[step.done] = placeholder_value
    pip.write_state(pipeline_id, state)
    
    # Confirm completion and configure next step display
    await pip.update_step_state(pipeline_id, step_id, placeholder_value, steps)
    await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)
    
    # Return response with chain reaction to next step
    response = Div(
        Card(
            H4(f"{step.show} Complete"),
            P("Proceeding to next step..."),
        ),
        # CRITICAL: Chain reaction to next step - DO NOT MODIFY OR REMOVE
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )
    return response
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

## Individual Recipes

Individual widget recipes are available in the `pipulate/training/widget_recipes/` directory (planned for future implementation).

# IMPLEMENTATION PLAN FOR ADDING STEPS

This plan outlines the recommended process for adding a new workflow step (`step_new`) between `step_prev` and `step_next`.

1. **Backup:** Create a copy of the workflow file (e.g., `xx_my_flow (backup).py`) before starting.

2. **Define Step:** Open the workflow file (e.g., `plugins/NN_my_flow.py`). Add the `Step(...)` definition for `step_new` in the `steps` list within `__init__` at the correct sequence.
```python
steps = [
    # ... existing steps before ...
    Step(id='step_new', done='new_field', show='New Step Label', refill=False, transform=None),
    # ... existing steps after ...
]
```

3. **Update Indices:** Immediately after the `steps` list, ensure `self.steps_indices = {step.id: i for i, step in enumerate(steps)}` is present to recalculate indices.

4. **Update Preceding Step (`step_prev`):**
   * Locate the `return Div(...)` statement in both `async def step_prev(...)` and `async def step_prev_submit(...)`.
   * Find the inner chain reaction `Div`: `Div(id=step_next.id, hx_get=f"/{app_name}/{step_next.id}", hx_trigger="load")`.
   * Change its `id` and `hx_get` path to point to `step_new`: `Div(id="step_new", hx_get=f"/{app_name}/step_new", hx_trigger="load")`.

5. **Create New GET Handler (`step_new`):**
   * Copy the structure from an existing GET handler (like `step_prev`).
   * Update `step_id = "step_new"`.
   * Ensure `next_step_id` is calculated correctly (should point to `step_next.id` or `'finalize'`).
   * Implement the logic for finalized, completed, and input states.
   * **Crucially:** Ensure the returned `Div` has the *outer* `id="step_new"` and the *inner* chain reaction `Div` points correctly to `next_step_id`.
   * *Checkpoint:* Run the workflow. Verify that after completing `step_prev`, `step_new`'s input form loads automatically. Check the HTML source for correct IDs and `hx_get` attributes.

6. **Create New POST Handler (`step_new_submit`):**
   * Copy the structure from an existing POST handler.
   * Update `step_id = "step_new"`.
   * Implement form processing, validation, state saving (`update_step_state`), and user messages (`message_queue.add`).
   * Return the standard navigation component using `pip.create_step_navigation(...)`. This function correctly includes the chain reaction `Div` pointing to `next_step_id`.
   * *Checkpoint:* Run the workflow. Submit the `step_new` form. Verify the data is saved correctly (check logs/DB state). Verify the UI updates to the completed view for `step_new` and that `step_next` loads automatically.

7. **Update Messages/Suggestions (Optional):**
   * Add entries to `self.step_messages` for `step_new`.
   * Update `get_suggestion` if applicable.

8. **Testing:**
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

# WORKFLOW ARCHITECTURE IN PIPULATE

## Dual-Identity Pattern: Filename vs APP_NAME

Pipulate workflows maintain two separate identities:

### 1. Filename-based Endpoint Identity
- **Source**: The Python filename (minus numeric prefix and .py extension)
- **Example**: `110_parameter_buster_workflow.py` → `/parameter_buster_workflow` endpoint
- **Purpose**: Determines the URL path users will access in the browser
- **Navigation**: Controls what appears in the UI navigation menu
- **Flexibility**: Can be changed to improve user-facing URLs without breaking stored data

### 2. APP_NAME-based Storage Identity
- **Source**: The `APP_NAME` constant in the workflow class
- **Example**: `APP_NAME = "parameter_buster"` → Database keys use "parameter_buster"
- **Purpose**: Used for database keys and internal state management
- **Data Integrity**: Maintains connection to existing records in the database
- **Consistency**: Must remain stable to avoid orphaning existing workflow data

### Best Practices
- **Make Them Different**: Using different values for filename and APP_NAME provides maximum flexibility
- **Descriptive Filenames**: Use more descriptive filenames for better URL clarity
- **Simple APP_NAMEs**: Keep APP_NAMEs shorter and simpler for cleaner database keys
- **Version Transitions**: When creating a major revision, you can create a new file (e.g., `parameter_buster_v2_workflow.py`) while keeping the same APP_NAME to preserve all existing data

# CORE PRINCIPLES SUMMARY

1. **Explicit Chain Reaction**: Always maintain the `hx_trigger="load"` pattern - never attempt to use implicit event bubbling or remove this attribute.

2. **WET Workflows**: Workflows are intentionally Write Everything Twice (WET) to maintain clarity and ease of modification.

3. **Steps and State**: Each step has a clear `id`, `done` field, and defined progression path.

4. **Consistency in Patterns**: Use the same structure for all step handlers and submit methods.

5. **Careful Evolution**: When modifying existing workflows, preserve all critical connections and chain reactions.

By carefully following the patterns established in the codebase and documented in these guides, you can reliably extend Pipulate workflows with new steps and widgets while maintaining the integrity of the system. Remember to leverage the placeholder pattern for complex additions and to never modify the critical chain reaction pattern.
