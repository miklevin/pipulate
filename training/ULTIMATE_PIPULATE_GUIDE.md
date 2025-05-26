# 🚨 **THE ULTIMATE PIPULATE IMPLEMENTATION GUIDE FOR LLMs** 🚨

## **🔥 QUICK REFERENCE: The Two Patterns That Break Everything**

1. **Empty Key Field**: Must return `HX-Refresh` response (not error message)
2. **Missing hx_trigger="load"**: Must include in completed views (Phases 1 & 2 only)

**If you remember nothing else, remember these two patterns.**

---

## **PRIORITY 1: The Auto-Key Generation Pattern (MOST CRITICAL)**

### 🚨 **CRITICAL PATTERN ALERT** 🚨
**Question**: How does the auto-key generation work when a user hits Enter on an empty key field?

**Answer**: This is the most surprising pattern that will catch LLMs off-guard. When `user_input` is empty in the `init` method, you MUST return an `HX-Refresh` response:

```python
async def init(self, request):
    form = await request.form()
    user_input = form.get('pipeline_id', '').strip()
    
    # 🚨 CRITICAL: Empty input triggers page refresh for auto-key generation
    if not user_input:
        from starlette.responses import Response
        response = Response('')
        response.headers['HX-Refresh'] = 'true'
        return response
    
    # Continue with normal workflow initialization...
```

### **The Auto-Key Generation Flow:**
1. User hits Enter on empty field → `HX-Refresh` response
2. Page refreshes → JavaScript auto-generates key using `pip.generate_pipeline_key()`
3. Form auto-submits with generated key → Normal workflow initialization

### **❌ COMMON MISTAKE:**
```python
# WRONG - This breaks auto-key generation
if not user_input:
    return P("Please enter a key")  # Should be HX-Refresh instead
```

### **✅ CORRECT PATTERN:**
```python
# RIGHT - This enables auto-key generation
if not user_input:
    response = Response('')
    response.headers['HX-Refresh'] = 'true'
    return response
```

**This is NOT optional** - removing this breaks the core UX expectation that users can just hit Enter to start workflows.

---

## **PRIORITY 2: The Three-Phase Step Pattern (ARCHITECTURAL FOUNDATION)**

### 🚨 **CRITICAL PATTERN ALERT** 🚨
**Question**: What are the three phases every step handler must implement?

**Answer**: Every `step_XX` GET handler must handle these three distinct phases in this exact order:

### **Phase 1: Finalize Phase (Locked View)**
```python
if 'finalized' in finalize_data:
    return Div(
        Card(H3(f'🔒 {step.show}: {user_val}')),
        Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
        id=step_id
    )
```

### **Phase 2: Revert Phase (Completed View)**  
```python
elif user_val and state.get('_revert_target') != step_id:
    return Div(
        pip.display_revert_header(step_id, app_name, f'{step.show}: {user_val}', steps),
        Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
        id=step_id
    )
```

### **Phase 3: Input Phase (Form View)**
```python
else:
    return Div(
        Card(/* input form */),
        Div(id=next_step_id),  # Empty placeholder - NO hx_trigger here
        id=step_id
    )
```

### **🚨 CRITICAL RULES:**
- **Only Phases 1 & 2** include `hx_trigger="load"` - Phase 3 waits for form submission
- The `Div(id=next_step_id, hx_get=..., hx_trigger='load')` creates the "chain reaction"
- Each completed step automatically triggers the next step to load

### **❌ COMMON MISTAKES:**
```python
# WRONG - Missing hx_trigger in completed phases
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}')  # Missing hx_trigger

# WRONG - Adding hx_trigger to input forms
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')  # In input phase

# WRONG - Wrong phase order
if user_val:  # Should check finalized first
    # Phase logic
```

### **✅ COMPLETE CORRECT PATTERN:**
```python
async def step_01(self, request):
    pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
    step_id = 'step_01'
    step_index = self.steps_indices[step_id]
    step = steps[step_index]
    next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
    pipeline_id = db.get('pipeline_id', 'unknown')
    state = pip.read_state(pipeline_id)
    step_data = pip.get_step_data(pipeline_id, step_id, {})
    user_val = step_data.get(step.done, '')
    finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
    
    # Phase 1: Finalize Phase - Show locked view
    if 'finalized' in finalize_data:
        return Div(
            Card(H3(f'🔒 {step.show}: {user_val}')),
            Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
            id=step_id
        )
    
    # Phase 2: Revert Phase - Show completed view with revert option  
    elif user_val and state.get('_revert_target') != step_id:
        return Div(
            pip.display_revert_header(step_id, app_name, f'{step.show}: {user_val}', steps),
            Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
            id=step_id
        )
    
    # Phase 3: Input Phase - Show input form
    else:
        return Div(
            Card(
                H3(f'{step.show}'),
                Form(
                    Input(name=step.done, required=True, autofocus=True),
                    Button('Next ▸', type='submit'),
                    hx_post=f'/{app_name}/{step_id}_submit',
                    hx_target=f'#{step_id}'
                )
            ),
            Div(id=next_step_id),  # Empty placeholder for next step
            id=step_id
        )
```

---

## **PRIORITY 3: The Pipeline Key System (DATA INTEGRITY)**

**Question**: How do pipeline keys work and why are they critical?

**Answer**: Pipeline keys follow the format: `{profile_name}-{plugin_name}-{user_part}`

```python
def generate_pipeline_key(self, plugin_instance, user_input=None):
    # Auto-generates: "default-hello_workflow-01", "default-hello_workflow-02", etc.
    # Or uses user input: "default-hello_workflow-myproject"
    
    context = self.get_plugin_context(plugin_instance)
    profile_part = context['profile_name'].replace(' ', '_')
    plugin_part = context['plugin_name'].replace(' ', '_') 
    prefix = f'{profile_part}-{plugin_part}-'
    
    if user_input is None:
        # Auto-increment logic for next available number
        next_number = self._get_next_number(prefix)
        user_part = f'{next_number:02d}' if next_number < 100 else str(next_number)
    else:
        user_part = str(user_input)
    
    return (f'{prefix}{user_part}', prefix, user_part)
```

### **✅ VALID EXAMPLES:**
- `mike-hello_workflow-test123` ✅ Valid
- `default-browser_automation-01` ✅ Valid  
- `production-data_export-final` ✅ Valid

### **❌ INVALID EXAMPLES:**
- `mike-hello-workflow-test123` ❌ Invalid (hyphen in plugin name)
- `hello_workflow-test123` ❌ Invalid (missing profile)
- `mike_hello_workflow_test123` ❌ Invalid (missing separators)

**Critical**: These keys are the primary database identifiers. They enable:
- Resuming workflows across sessions
- Profile-based data isolation  
- Plugin-specific data organization
- User-friendly workflow identification

---

## **PRIORITY 4: The Step namedtuple Structure (WORKFLOW DEFINITION)**

**Question**: What does the Step namedtuple define and how is it used?

**Answer**: 

```python
from collections import namedtuple
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

steps = [
    Step(
        id='step_01',           # Route identifier: /{app_name}/step_01
        done='name',            # State key: state['step_01']['name'] = value
        show='Your Name',       # UI display label
        refill=True,           # Pre-fill form on revert?
        transform=None         # Optional: lambda to transform previous step's data
    ),
    Step(
        id='step_02', 
        done='greeting', 
        show='Hello Message', 
        refill=False,
        transform=lambda name: f'Hello {name}!'  # Uses previous step's output
    ),
    Step(id='finalize', done='finalized', show='Finalize', refill=False)  # REQUIRED
]
```

### **🚨 CRITICAL RULES:**
- `id` becomes the route: `/{app_name}/{step.id}` and `/{app_name}/{step.id}_submit`
- `done` is the state storage key: `state[step.id][step.done] = user_value`
- `transform` can process previous step's data for suggestions
- **ALWAYS** add `Step(id='finalize', done='finalized', show='Finalize', refill=False)` as the final step

### **❌ COMMON MISTAKES:**
```python
# WRONG - Missing finalize step
steps = [
    Step(id='step_01', done='name', show='Name'),
    # Missing finalize step breaks workflow
]

# WRONG - Invalid id format
Step(id='step-01', done='name', show='Name')  # Hyphens not allowed

# WRONG - Missing required fields
Step(id='step_01')  # Missing done, show
```

---

## **PRIORITY 5: State Management Patterns (DATA PERSISTENCE)**

**Question**: How is workflow state managed and persisted?

**Answer**: State is stored in the `pipeline` table with JSON blobs:

```python
# Reading state
state = pip.read_state(pipeline_id)  # Gets entire workflow state
step_data = pip.get_step_data(pipeline_id, step_id, {})  # Gets specific step
user_value = step_data.get(step.done, '')  # Gets the actual user input

# Writing state  
await pip.set_step_data(pipeline_id, step_id, user_value, steps)
# This automatically:
# 1. Stores: state[step_id][step.done] = user_value
# 2. Clears subsequent steps (optional)
# 3. Persists to database

# State structure example:
{
    'step_01': {'name': 'John'},
    'step_02': {'greeting': 'Hello John!'},
    'finalize': {'finalized': True},
    '_revert_target': 'step_01'  # Special flag for revert handling
}
```

### **🚨 CRITICAL RULES:**
- State persists across browser sessions
- Finalization locks the entire workflow
- Reverting clears all subsequent step data
- The `_revert_target` flag controls which step shows input form vs completed view

### **✅ CORRECT USAGE:**
```python
# Reading step data safely
step_data = pip.get_step_data(pipeline_id, step_id, {})
user_val = step_data.get(step.done, '')

# Writing step data properly
await pip.set_step_data(pipeline_id, step_id, user_value, steps)
```

### **❌ COMMON MISTAKES:**
```python
# WRONG - Direct state manipulation
state[step_id] = user_value  # Use pip.set_step_data instead

# WRONG - Not handling missing data
user_val = state[step_id][step.done]  # Can throw KeyError

# WRONG - Forgetting to await
pip.set_step_data(pipeline_id, step_id, user_value, steps)  # Missing await
```

---

## **PRIORITY 6: The Chain Reaction Pattern (UX FLOW)**

**Question**: How does the "Run All Cells" chain reaction work?

**Answer**: Each step must explicitly trigger the next step via HTMX:

```python
# In step GET handlers (phases 1 & 2):
return Div(
    Card(/* step content */),
    Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
    id=step_id
)

# In step POST handlers:
return pip.chain_reverter(step_id, step_index, steps, app_name, processed_val)
# This helper creates the revert header + next step trigger
```

### **🚨 CRITICAL RULES:**
- The `hx_trigger='load'` creates the automatic progression
- Missing this breaks the chain reaction
- `pip.chain_reverter()` is the preferred helper for POST handlers
- The chain stops at steps requiring user input (Input Phase)

### **✅ CORRECT CHAIN REACTION:**
```python
# Completed step with chain reaction
return Div(
    Card(H3(f'{step.show}: {user_val}')),
    Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
    id=step_id
)
```

### **❌ BREAKING THE CHAIN:**
```python
# WRONG - Missing hx_trigger
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}')

# WRONG - Wrong trigger
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='click')
```

---

## **PRIORITY 7: The Request Parameter Requirement (FRAMEWORK INTEGRATION)**

**Question**: Why do all route handlers require a `request` parameter and what happens if you forget it?

**Answer**: Every method that handles HTTP requests MUST accept a `request` parameter:

```python
# ✅ CORRECT - All these methods MUST have request parameter
async def landing(self, request):  # Required even if unused
async def init(self, request):
async def step_01(self, request):
async def step_01_submit(self, request):
async def finalize(self, request):
async def handle_revert(self, request):
```

### **❌ COMMON MISTAKE:**
```python
# WRONG - This will cause routing errors
async def step_01(self):  # Missing request parameter
async def init(self):     # Missing request parameter
```

### **✅ ACCESSING REQUEST DATA:**
```python
async def step_01_submit(self, request):
    form = await request.form()  # Form data
    user_input = form.get('field_name')
    query_params = request.query_params.get('param')
    headers = request.headers.get('header-name')
```

**Critical**: This is a FastHTML/Starlette requirement. The framework automatically passes the request object, and if your method signature doesn't accept it, you'll get routing errors.

---

## **PRIORITY 8: The DictLikeDB vs Pipeline Table Distinction (DATA ARCHITECTURE)**

**Question**: What's the difference between `self.db` and `self.pipeline` and when do you use each?

**Answer**: Two completely different storage systems:

```python
# self.db - DictLikeDB (global key-value store)
self.db['pipeline_id'] = 'default-hello-01'  # Current session state
self.db['last_user_choice'] = 'option_a'     # Global preferences
self.db.get('setting_name', 'default_value') # Dictionary-like access

# self.pipeline - MiniDataAPI (workflow state table)  
pip.read_state(pipeline_id)   # Get entire workflow JSON blob
pip.write_state(pipeline_id, state_dict)  # Save entire workflow state
pip.get_step_data(pipeline_id, step_id, {})  # Get specific step data
```

### **🚨 CRITICAL DISTINCTION:**
- `self.db` is for **global, session-level data** (current pipeline_id, user preferences)
- `self.pipeline` is for **workflow-specific state** (step values, completion status)
- `self.db` is simple key-value pairs
- `self.pipeline` stores complex JSON blobs per workflow instance

### **✅ CORRECT USAGE:**
```python
# Session data
pipeline_id = self.db.get('pipeline_id', 'unknown')

# Workflow data
state = pip.read_state(pipeline_id)
step_data = pip.get_step_data(pipeline_id, step_id, {})
```

---

## **PRIORITY 9: Workflow Registration and Discovery (PLUGIN SYSTEM)**

**Question**: How are workflows discovered and registered?

**Answer**: Workflows are auto-discovered from the `plugins/` directory:

```python
# File naming: {number}_{name}.py determines menu order and URL
# 500_hello_workflow.py → /hello_workflow endpoint, menu position 500

class HelloFlow:
    APP_NAME = 'hello_workflow'  # Internal identifier (stable)
    DISPLAY_NAME = 'Hello Workflow'  # Menu display name
    ENDPOINT_MESSAGE = 'Start a new Workflow...'  # Landing page text
    TRAINING_PROMPT = 'hello_workflow.md'  # LLM context file
    
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        # Register routes automatically
        routes = [
            (f'/{app_name}', self.landing),
            (f'/{app_name}/init', self.init, ['POST']),
            # ... step routes auto-generated from self.steps
        ]
```

### **🚨 CRITICAL RULES:**
- Filename determines URL and menu order
- `APP_NAME` must be unique and stable (data integrity)
- `DISPLAY_NAME` can change without breaking data
- Routes are registered in `__init__`

### **✅ FILE NAMING RULES:**
- `{number}_{name}.py` - Auto-registered, menu order by number
- `xx_{name}.py` or `XX_{name}.py` - Skipped (development)
- `{name} (Copy).py` - Skipped (contains parentheses)
- `__*.py` - Skipped (Python convention)

---

## **PRIORITY 10: The Message Queue System (LLM INTEGRATION)**

**Question**: How does the OrderedMessageQueue work and why is it critical?

**Answer**: The message queue synchronizes UI updates with LLM context:

```python
# In workflow methods
await self.message_queue.add(
    pip,                    # Pipulate instance
    "Step 1 complete",      # Message text
    verbatim=True,          # True: show as-is, False: send to LLM for response
    role='system'           # 'system', 'user', or 'assistant'
)
```

### **Context Markers Added:**
```
[WORKFLOW STATE: Step 1 completed]
[INFO] Step 1 complete
[USER INPUT] User entered: John
[RESPONSE] LLM's response to user
```

**Critical**: This keeps the LLM aware of what the user is seeing and doing. Without proper message queue usage, the LLM loses context about workflow state.

---

## **COMMON LLM MISTAKES TO AVOID**

### **❌ TOP 10 MISTAKES:**

1. **Missing HX-Refresh for empty input**
   ```python
   # WRONG
   if not user_input:
       return P("Please enter a key")
   ```

2. **Missing hx_trigger="load" in completed phases**
   ```python
   # WRONG
   Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}')
   ```

3. **Adding hx_trigger to input forms**
   ```python
   # WRONG - Skips user input
   Div(id=next_step_id, hx_trigger='load')  # In input phase
   ```

4. **Missing request parameter**
   ```python
   # WRONG
   async def step_01(self):  # Missing request
   ```

5. **Wrong three-phase order**
   ```python
   # WRONG - Should check finalized first
   if user_val:
       # Phase logic
   ```

6. **Direct state manipulation**
   ```python
   # WRONG
   state[step_id] = user_value  # Use pip.set_step_data
   ```

7. **Missing finalize step**
   ```python
   # WRONG - No finalize step in steps list
   ```

8. **Forgetting await on async methods**
   ```python
   # WRONG
   pip.set_step_data(...)  # Missing await
   ```

9. **Using wrong storage system**
   ```python
   # WRONG - Mixing db and pipeline usage
   self.db[pipeline_id] = state  # Should use pip.write_state
   ```

10. **Breaking chain reaction flow**
    ```python
    # WRONG - Missing next step div entirely
    return Card(H3("Done"))  # No chain continuation
    ```

---

## **DEBUGGING CHECKLIST**

When workflows don't work, check these in order:

1. **✅ Auto-key generation**: Empty input returns HX-Refresh?
2. **✅ Three-phase logic**: Correct order (finalized → revert → input)?
3. **✅ Chain reaction**: All completed phases have hx_trigger="load"?
4. **✅ Request parameters**: All handlers accept request?
5. **✅ State management**: Using pip.get_step_data/set_step_data?
6. **✅ Step definition**: Finalize step included in steps list?
7. **✅ Route registration**: All routes properly registered in __init__?
8. **✅ File naming**: Plugin file follows naming convention?

---

## **QUICK IMPLEMENTATION TEMPLATE**

```python
from collections import namedtuple
from fasthtml.common import *

Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

class MyWorkflow:
    APP_NAME = 'my_workflow'
    DISPLAY_NAME = 'My Workflow'
    
    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        self.pipulate, self.db = pipulate, db
        self.steps = [
            Step(id='step_01', done='my_field', show='My Step', refill=True),
            Step(id='finalize', done='finalized', show='Finalize', refill=False)
        ]
        self.steps_indices = {step.id: i for i, step in enumerate(self.steps)}
        
        # Register routes
        routes = [
            (f'/{app_name}', self.landing),
            (f'/{app_name}/init', self.init, ['POST']),
            (f'/{app_name}/step_01', self.step_01),
            (f'/{app_name}/step_01_submit', self.step_01_submit, ['POST']),
            (f'/{app_name}/finalize', self.finalize),
            (f'/{app_name}/handle_revert', self.handle_revert, ['POST']),
        ]
        for route in routes:
            app.route(*route)
    
    async def init(self, request):
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        
        # CRITICAL: Auto-key generation
        if not user_input:
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        
        # Continue with workflow...
    
    async def step_01(self, request):
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.APP_NAME)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        
        # Three-phase pattern
        if 'finalized' in finalize_data:
            return Div(
                Card(H3(f'🔒 {step.show}: {user_val}')),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        elif user_val and state.get('_revert_target') != step_id:
            return Div(
                pip.display_revert_header(step_id, app_name, f'{step.show}: {user_val}', steps),
                Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
                id=step_id
            )
        else:
            return Div(
                Card(
                    H3(f'{step.show}'),
                    Form(
                        Input(name=step.done, required=True, autofocus=True),
                        Button('Next ▸', type='submit'),
                        hx_post=f'/{app_name}/{step_id}_submit',
                        hx_target=f'#{step_id}'
                    )
                ),
                Div(id=next_step_id),
                id=step_id
            )
```

---

## **SUMMARY: The Patterns That Catch LLMs Off-Guard**

1. **"Why does empty input trigger HX-Refresh?"** → Auto-key generation pattern
2. **"What are the three phases in step handlers?"** → Finalize/Revert/Input pattern  
3. **"Why must all handlers accept request parameter?"** → FastHTML requirement
4. **"What's the difference between db and pipeline?"** → Global vs workflow-specific storage
5. **"How does the chain reaction work?"** → Explicit `hx_trigger='load'` pattern
6. **"Why WET instead of DRY for workflows?"** → Clarity over abstraction
7. **"How does state persistence work?"** → JSON blobs in pipeline table
8. **"What breaks the auto-key generation?"** → Missing HX-Refresh response
9. **"How does revert clear subsequent steps?"** → `clear_steps_from()` + `_revert_target`
10. **"Why does finalization lock everything?"** → Prevents accidental data loss

**Remember**: Pipulate is fundamentally different from typical web frameworks because it prioritizes **local-first operation**, **explicit state management**, and **notebook-like linear progression** over traditional MVC patterns. 