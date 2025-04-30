# Botify URL Input Widget Recipe

## Overview
This recipe transforms a placeholder step into a widget that collects and validates Botify project URLs. It ensures the URL follows the Botify project pattern, always includes a trailing slash, and extracts key project information.

## Core Concepts
- **URL Validation**: Ensure input is a valid Botify project URL
- **URL Standardization**: Always ensure URLs end with a trailing slash
- **Pattern Matching**: Extract project ID and components from URL
- **Error Handling**: Clear validation feedback to users
- **Data Storage**: Store structured project data for downstream steps

## Implementation Phases

### Phase 1: Add Helper Method
First, add this helper method to your workflow class:

```python
def validate_botify_url(self, url):
    """Validate a Botify project URL and extract project information.
    
    Returns:
        tuple: (is_valid, message, extracted_data)
            - is_valid (bool): Whether the URL is valid
            - message (str): Validation message or error
            - extracted_data (dict): Extracted project information
    """
    # Trim whitespace
    url = url.strip()
    
    # Basic URL validation
    if not url:
        return False, "URL is required", {}
    
    try:
        # Use a more flexible pattern that matches Botify URLs
        if not url.startswith(("https://app.botify.com/", "https://analyze.botify.com/")):
            return False, "URL must be a Botify project URL (starting with https://app.botify.com/ or https://analyze.botify.com/)", {}
        
        # Ensure URL ends with a trailing slash
        if not url.endswith('/'):
            url = f"{url}/"
        
        # Extract the path components
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        path_parts = [p for p in parsed_url.path.split('/') if p]
        
        # Need at least two components
        if len(path_parts) < 2:
            return False, "Invalid Botify URL: must contain at least organization and project", {}
        
        # Extract organization and project
        username = path_parts[0]
        project_group = path_parts[1] if len(path_parts) > 2 else ""
        project_name = path_parts[-1]  # Use last path component as project name
        
        # Create project data
        project_data = {
            "url": url,  # Keep original URL with trailing slash
            "username": username,
            "project_group": project_group,
            "project_name": project_name,
            "project_id": f"{username}/{project_name}" if not project_group else f"{username}/{project_group}/{project_name}"
        }
        
        return True, f"Valid Botify project: {project_name}", project_data
    
    except Exception as e:
        return False, f"Error parsing URL: {str(e)}", {}
```

### Phase 2: Update Step Definition
```python
# CUSTOMIZE_STEP_DEFINITION
# Change from:
Step(
    id='step_XX',
    done='placeholder',
    show='Placeholder Step',
    refill=False,
),

# To:
Step(
    id='step_XX',
    done='botify_project',         # Field to store the project data
    show='Botify Project URL',     # User-friendly name
    refill=True,                   # Allow refilling for better UX
),
```

### Phase 3: Update GET Handler
Only modify the marked sections:

```python
# CUSTOMIZE_VALUE_ACCESS
project_data_str = step_data.get(step.done, "")
import json
project_data = json.loads(project_data_str) if project_data_str else {}
project_url = project_data.get("url", "")

# CUSTOMIZE_DISPLAY: Enhanced finalized state display
return Div(
    Card(
        H3(f"🔒 {step.show}"),
        Div(
            P(f"Project: {project_data.get('project_name', '')}"),
            P(f"Group: {project_data.get('project_group', '')}"),
            Small(project_url, style="word-break: break-all;"),
            style="padding: 10px; background: var(--pico-card-background-color); border-radius: 5px;"
        )
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# CUSTOMIZE_COMPLETE: Enhanced completion display
project_name = project_data.get('project_name', '')
project_group = project_data.get('project_group', '')
username = project_data.get('username', '')

project_info = Div(
    H4(f"Project: {project_name}"),
    P(f"Group: {project_group}"),
    P(f"Username: {username}"),
    Small(project_url, style="word-break: break-all;"),
    style="padding: 10px; background: #f8f9fa; border-radius: 5px;"
)

return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {project_url}",
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# CUSTOMIZE_FORM: Replace with URL input form
display_value = project_url if (step.refill and project_url) else ""
await self.message_queue.add(pip, self.step_messages[step_id]["input"], verbatim=True)

return Div(
    Card(
        H3(f"{step.show}"),
        P("Enter a Botify project URL:"),
        Form(
            Input(
                type="url", 
                name="botify_url", 
                placeholder="https://app.botify.com/username/group/project", 
                value=display_value,
                required=True,
                pattern="https://(app|analyze)\\.botify\\.com/[^/]+/[^/]+/[^/]+.*",
                style="width: 100%;"
            ),
            Small("Example: https://app.botify.com/username/group/project/", style="display: block; margin-bottom: 10px;"),
            Small("Note: A trailing slash will be added automatically if missing", style="display: block; color: #666; margin-bottom: 10px;"),
            Div(
                Button("Submit", type="submit", cls="primary"),
                style="margin-top: 1vh; text-align: right;"
            ),
            hx_post=f"/{app_name}/{step_id}_submit", 
            hx_target=f"#{step_id}"
        )
    ),
    Div(id=next_step_id),  # PRESERVE: Empty div for next step - DO NOT ADD hx_trigger HERE
    id=step_id
)
```

### Phase 4: Update SUBMIT Handler
Only modify the marked sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Process form data
form = await request.form()
botify_url = form.get("botify_url", "").strip()

# CUSTOMIZE_VALIDATION: Validate the Botify URL
is_valid, message, project_data = self.validate_botify_url(botify_url)

if not is_valid:
    return P(f"Error: {message}", style=pip.get_style("error"))

# CUSTOMIZE_DATA_PROCESSING: Convert to storable format 
import json
project_data_str = json.dumps(project_data)

# CUSTOMIZE_STATE_STORAGE: Save to state with JSON
await pip.update_step_state(pipeline_id, step_id, project_data_str, steps)
await self.message_queue.add(pip, f"{step.show} complete: {project_data['project_name']}", verbatim=True)

# CUSTOMIZE_WIDGET_DISPLAY: Create project info widget
project_name = project_data.get('project_name', '')
project_group = project_data.get('project_group', '') 
username = project_data.get('username', '')
project_url = project_data.get('url', '')

project_info = Div(
    H4(f"Project: {project_name}"),
    P(f"Group: {project_group}"),
    P(f"Username: {username}"),
    Small(project_url, style="word-break: break-all;"),
    style="padding: 10px; background: #f8f9fa; border-radius: 5px;"
)

# PRESERVE: Return the revert control with chain reaction to next step
return Div(
    pip.revert_control(
        step_id=step_id, 
        app_name=app_name, 
        message=f"{step.show}: {project_url}",
        steps=steps
    ),
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)
```

### Phase 5: Accessing in Downstream Steps
In downstream steps that need to use the project data:

```python
# Get data from previous step
prev_step_id = "step_XX"  # The step with the Botify URL
prev_step_data = pip.get_step_data(pipeline_id, prev_step_id, {})
prev_data_str = prev_step_data.get("botify_project", "")

import json
project_data = json.loads(prev_data_str) if prev_data_str else {}

# Access specific project components
project_name = project_data.get("project_name", "")
project_id = project_data.get("project_id", "")
username = project_data.get("username", "")
project_group = project_data.get("project_group", "")
project_url = project_data.get("url", "")  # Will always have trailing slash

# Use in API calls or other operations
```

## Common Pitfalls
- **URL Validation**: Always validate both format and accessibility
- **URL Standardization**: Always ensure URLs end with a trailing slash
- **JSON Serialization**: Remember to serialize/deserialize with JSON 
- **Error Messaging**: Provide clear feedback on validation errors
- **Pattern Matching**: Ensure regex patterns handle all valid URL formats
- **Default Values**: Always use get() with defaults when accessing data

## Related Widget Recipes
- [Text Input Widget](01_text_input_widget.md)
- [API Request Widget](07_api_request_widget.md) 