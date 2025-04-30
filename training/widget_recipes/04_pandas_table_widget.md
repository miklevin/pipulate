# Pandas Table Widget Recipe

## Overview
This recipe transforms a placeholder step into a widget that:
1. Collects CSV text input from the user
2. Processes it into a Pandas DataFrame 
3. Displays it as a formatted HTML table

## Core Concepts
- **Data Collection**: TextArea for CSV input
- **State Storage**: Store both raw CSV and processed HTML
- **Widget Display**: Use `HTML()` component to render the table

## Implementation Phases

### Phase 1: Add Helper Method
First, add this helper method to your workflow class:

```python
def create_pandas_table(self, data_str):
    """Convert string data to a Pandas DataFrame and render as HTML table."""
    import pandas as pd
    import io
    
    try:
        # Try to parse the input as CSV
        df = pd.read_csv(io.StringIO(data_str))
        
        # Limit preview size for performance
        preview_df = df.head(10) if len(df) > 10 else df
        
        # Create a styled HTML table
        styled_table = preview_df.style.set_table_attributes('class="pandas-table"')
        html_table = styled_table.to_html()
        
        # Return the HTML wrapped in appropriate FastHTML components
        return Div(
            H4("DataFrame Preview:"),
            P(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns"),
            HTML(html_table),
            style="overflow-x: auto;"
        )
    except Exception as e:
        return P(f"Error creating table: {str(e)}", style="color: red;")
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
    done='csv_data',              # Stores the raw CSV input
    show='Pandas Table Widget',   # User-friendly name
    refill=True,                  # Allow refilling for iterative data exploration
),
```

### Phase 3: Update GET Handler
Replace the key sections:

```python
# CUSTOMIZE_VALUE_ACCESS
csv_data = step_data.get(step.done, "")  # Get saved CSV data

# CUSTOMIZE_DISPLAY: Enhanced finalized state display
if "finalized" in finalize_data and csv_data:
    table_widget = self.create_pandas_table(csv_data)
    return Div(
        Card(
            H3(f"🔒 {step.show}"),
            table_widget  # Show pandas table
        ),
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )

# CUSTOMIZE_COMPLETE: Enhanced completion display
if csv_data and state.get("_revert_target") != step_id:
    table_widget = self.create_pandas_table(csv_data)
    content_container = pip.widget_container(
        step_id=step_id,
        app_name=app_name,
        message=f"{step.show}: DataFrame created",
        widget=table_widget,
        steps=steps
    )
    return Div(
        content_container,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id
    )

# CUSTOMIZE_FORM: Create CSV input form
display_value = csv_data if (step.refill and csv_data) else ""
await self.message_queue.add(pip, f"Enter CSV data for {step.show}", verbatim=True)

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

### Phase 4: Update SUBMIT Handler
Replace the key sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Get CSV data
form = await request.form()
csv_data = form.get(step.done, "").strip()

# CUSTOMIZE_VALIDATION: Check if data is provided and valid
if not csv_data:
    return P("Error: CSV data is required", style=pip.get_style("error"))

# Validate CSV format
try:
    import pandas as pd
    import io
    pd.read_csv(io.StringIO(csv_data))
except Exception as e:
    return P(f"Error: Invalid CSV format - {str(e)}", style=pip.get_style("error"))

# CUSTOMIZE_STATE_STORAGE: Store raw CSV data
await pip.update_step_state(pipeline_id, step_id, csv_data, steps)
await self.message_queue.add(pip, f"{step.show} complete.", verbatim=True)

# CUSTOMIZE_WIDGET_DISPLAY: Create pandas table widget
table_widget = self.create_pandas_table(csv_data)
content_container = pip.widget_container(
    step_id=step_id,
    app_name=app_name,
    message=f"{step.show}: DataFrame created",
    widget=table_widget,
    steps=steps
)

# Create response with chain reaction to next step
response_content = Div(
    content_container,
    Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
    id=step_id
)

# Return HTMLResponse with the widget
from starlette.responses import HTMLResponse
from fasthtml.xml import to_xml
return HTMLResponse(to_xml(response_content))
```

## Sample CSV Data
For testing, you can use this sample CSV:

```
Name,Age,City
John,35,New York
Mary,28,San Francisco
Sam,42,Chicago
```

## Common Pitfalls
- **Memory Management**: Limit preview rows for large DataFrames
- **CSV Validation**: Always validate CSV format before processing
- **Error Handling**: Provide clear error messages for parsing issues
- **Styling**: Add overflow handling for wide tables
- **Dependencies**: Ensure Pandas is available in your environment

## Related Widget Recipes
- [Markdown Widget](05_markdown_widget.md)
- [Mermaid Diagram Widget](06_mermaid_diagram_widget.md) 