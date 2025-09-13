# 🎨 Widget Conversion Guide

**Purpose**: Convert widget templates into custom form components for Pipulate workflows.

---

## 🎯 Quick Conversion Process

### **1. Choose Your Widget Template**
- **Checkboxes**: `plugins/540_checkboxes.py`
- **Radio Buttons**: `plugins/550_radios.py` 
- **Text Input**: `plugins/510_text_field.py`
- **Dropdown**: `plugins/530_dropdown.py`
- **Range Slider**: `plugins/560_range.py`
- **Switch/Toggle**: `plugins/570_switch.py`
- **Text Area**: `plugins/520_text_area.py`
- **File Upload**: `plugins/580_upload.py`

### **2. Essential Conversion Points**

#### **CUSTOMIZE_STEP_DEFINITION**
```python
# Change 'done' field to your specific data field name
Step('step_01', 'user_selection', 'Select Options', False, None)
# Instead of generic: 'done'
```

#### **CUSTOMIZE_FORM**
```python
# Replace the generic Proceed button with your specific form elements
Fieldset(
    Legend("Your Custom Form"),
    # Add your checkboxes, inputs, etc. here
    Button("Submit Selection", type="submit")
)
```

#### **CUSTOMIZE_DISPLAY**
```python
# Update finalized state display for your widget
def show_final_result(self, selection_data):
    return Div(
        H3("Your Selection Results"),
        # Custom display of your data
    )
```

#### **CUSTOMIZE_COMPLETE**
```python
# Enhance completion state with your widget's specific display
return self.create_completion_view(
    step_data=step_data,
    display_widget=your_custom_widget,
    next_step_id=next_step_id
)
```

---

## 🔧 Critical Elements to Preserve

### **Chain Reaction Pattern**
```python
# ALWAYS include next step trigger
Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
```

### **Finalization State Handling**
```python
# Check if workflow is finalized
is_finalized = 'finalize' in state and 'finalized' in state['finalize']
if is_finalized:
    return self.show_finalized_view(state)
```

### **Revert Control Mechanism**
```python
# Include revert functionality
pip.display_revert_header(step_id, "Step Name")
```

### **Div Structure and ID Patterns**
```python
# Maintain consistent ID patterns
return Div(
    Card(...),  # Your content
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id  # CRITICAL: Must match step ID
)
```

---

## 🎨 Widget-Specific Patterns

### **Multi-Select Widgets (Checkboxes)**
```python
# Handle multiple selections
selected_items = form.getlist('items')  # Note: getlist for multiple
state[step_id] = {'selected_items': selected_items}
```

### **Single-Select Widgets (Radio, Dropdown)**
```python
# Handle single selection
selected_item = form.get('item')
state[step_id] = {'selected_item': selected_item}
```

### **Value Widgets (Range, Text)**
```python
# Handle numeric or text values
value = form.get('value')
state[step_id] = {'value': value}
```

### **File Widgets (Upload)**
```python
# Handle file uploads
uploaded_file = form.get('file')
if uploaded_file and uploaded_file.filename:
    # Process file
    state[step_id] = {'filename': uploaded_file.filename}
```

---

## 🚨 Common Pitfalls

### **1. Missing Chain Reaction**
```python
# ❌ WRONG: No next step trigger
return Card("Step complete")

# ✅ CORRECT: Includes chain reaction
return Div(
    Card("Step complete"),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

### **2. Incorrect Form Data Handling**
```python
# ❌ WRONG: Using get() for multi-select
selected = form.get('items')  # Only gets first item

# ✅ CORRECT: Using getlist() for multi-select
selected = form.getlist('items')  # Gets all selected items
```

### **3. Missing State Persistence**
```python
# ❌ WRONG: Not saving step data
# (Data lost on revert/revisit)

# ✅ CORRECT: Always save step data
state[step_id] = {step.done: form_data}
```

### **4. Broken Revert Functionality**
```python
# ❌ WRONG: No revert handling
if step_id in state:
    return "Already completed"

# ✅ CORRECT: Handle revert target
revert_target = state.get('_revert_target')
if revert_target == step_id:
    # Show input form for re-entry
```

---

## 🎯 Testing Your Widget

### **Essential Test Cases**
1. **Fresh Entry**: Widget works on first visit
2. **Data Persistence**: Data survives navigation away and back
3. **Revert Functionality**: Can revert and re-enter data
4. **Chain Reaction**: Automatically triggers next step
5. **Finalization**: Locked state when workflow finalized
6. **Edge Cases**: Empty submissions, invalid data

### **Quick Test Pattern**
```python
# 1. Complete the step normally
# 2. Navigate to next step
# 3. Use revert to go back
# 4. Verify data is preserved
# 5. Re-submit with different data
# 6. Verify update works correctly
```

---

## 🏆 Success Patterns

### **Clean Import Pattern**
```python
from modules.crud import WidgetImports, VALID_ROLES
from fasthtml.common import *
locals().update(WidgetImports.get_imports())
```

### **Consistent Role Definition**
```python
ROLES = ['Components']  # See config.AVAILABLE_ROLES for all valid roles
```

### **Embedded Documentation**
```python
# 📚 Widget conversion guide: helpers/docs_sync/widget_conversion_guide.md
```

This guide provides everything needed to convert widget templates into functional form components while maintaining Pipulate's chain reaction workflow patterns. 