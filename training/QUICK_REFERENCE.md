# 🚨 Pipulate Quick Reference Card 🚨

## The 2 Patterns That Break Everything

1. **Empty Key Field**: Must return `HX-Refresh` response (not error message)
2. **Missing hx_trigger="load"**: Must include in completed views (Phases 1 & 2 only)

**If you remember nothing else, remember these two patterns.**

---

## Critical Pattern Checklist

### ✅ Auto-Key Generation (Priority 1)
```python
if not user_input:
    response = Response('')
    response.headers['HX-Refresh'] = 'true'
    return response
```

### ✅ Three-Phase Step Pattern (Priority 2)
```python
# Phase 1: Finalize Phase (Locked View)
if 'finalized' in finalize_data:
    return Div(
        Card(H3(f'🔒 {step.show}: {user_val}')),
        Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
        id=step_id
    )

# Phase 2: Revert Phase (Completed View)  
elif user_val and state.get('_revert_target') != step_id:
    return Div(
        pip.display_revert_header(step_id, app_name, f'{step.show}: {user_val}', steps),
        Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'),
        id=step_id
    )

# Phase 3: Input Phase (Form View)
else:
    return Div(
        Card(/* input form */),
        Div(id=next_step_id),  # Empty placeholder - NO hx_trigger here
        id=step_id
    )
```

### ✅ Chain Reaction Pattern (Priority 6)
```python
# ONLY in completed phases (1 & 2) - NOT in input phase (3)
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')
```

### ✅ Request Parameter (Priority 7)
```python
# ALL handlers MUST accept request parameter
async def step_01(self, request):  # Required
async def init(self, request):     # Required
async def landing(self, request):  # Required
```

---

## Debugging Checklist

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

## Common Mistakes

### ❌ WRONG Patterns
```python
# WRONG - Missing HX-Refresh for empty input
if not user_input:
    return P("Please enter a key")  # Should be HX-Refresh

# WRONG - Missing hx_trigger in completed phases
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}')

# WRONG - Adding hx_trigger to input forms
Div(id=next_step_id, hx_trigger='load')  # In input phase

# WRONG - Missing request parameter
async def step_01(self):  # Missing request

# WRONG - Wrong three-phase order
if user_val:  # Should check finalized first
```

### ✅ CORRECT Patterns
```python
# RIGHT - HX-Refresh for empty input
if not user_input:
    response = Response('')
    response.headers['HX-Refresh'] = 'true'
    return response

# RIGHT - hx_trigger in completed phases only
Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load')

# RIGHT - No hx_trigger in input phase
Div(id=next_step_id)  # Empty placeholder

# RIGHT - Request parameter required
async def step_01(self, request):

# RIGHT - Correct three-phase order
if 'finalized' in finalize_data:      # Phase 1
elif user_val and state.get('_revert_target') != step_id:  # Phase 2
else:                                 # Phase 3
```

---

## Essential Code Snippets

### Step Definition Template
```python
self.steps = [
    Step(id='step_01', done='field_name', show='Step Title', refill=True),
    Step(id='step_02', done='another_field', show='Another Step', refill=True),
    Step(id='finalize', done='finalized', show='Finalize', refill=False)  # REQUIRED
]
```

### Complete Step Handler Template
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
    
    # Three-phase pattern implementation here...
```

### Submit Handler Template
```python
async def step_01_submit(self, request):
    pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
    step_id = 'step_01'
    step_index = self.steps_indices[step_id]
    pipeline_id = db.get('pipeline_id', 'unknown')
    
    form = await request.form()
    user_input = form.get('field_name', '').strip()
    
    if not user_input:
        return P('Please enter a value.', style=pip.get_style('error'))
    
    await pip.set_step_data(pipeline_id, step_id, {'field_name': user_input}, steps)
    
    return pip.chain_reverter(step_id, step_index, steps, app_name, user_input)
```

---

## Development Tools

### Create New Workflow
```bash
python helpers/create_workflow.py 035_my_workflow.py MyWorkflow my_workflow "My Workflow" "Welcome message" "Training prompt"
```

### Add Step to Existing Workflow
```bash
python helpers/splice_workflow_step.py plugins/035_my_workflow.py step_02 "New Step" new_field --position bottom
```

### Use Development Assistant
1. Navigate to Development Assistant plugin (320_dev_assistant)
2. Select plugin file to analyze
3. Review pattern validation results
4. Follow debugging recommendations

---

## Resources

- **Ultimate Pipulate Guide Part 1**: Core patterns (Priorities 1-10)
- **Ultimate Pipulate Guide Part 2**: Advanced patterns (Priorities 11-20)
- **Ultimate Pipulate Guide Part 3**: Expert mastery (Priorities 21-25)
- **Development Assistant Plugin**: Interactive debugging tool
- **Workflow Genesis Plugin**: Interactive workflow creation
- **Helper Scripts**: create_workflow.py, splice_workflow_step.py

---

## Emergency Debug Commands

```python
# Enable debug mode in server.py
DEBUG_MODE = True
STATE_TABLES = True

# Add debug logging in workflows
from loguru import logger
logger.debug(f"Step {step_id} state: {step_data}")

# State inspection
pip.append_to_history(f"DEBUG: State = {state}", role='system')
```

**Remember**: Pipulate is fundamentally different from typical web frameworks. It prioritizes **local-first operation**, **explicit state management**, and **notebook-like linear progression** over traditional MVC patterns. 