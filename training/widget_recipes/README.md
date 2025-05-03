# Widget Recipe System

This directory contains recipes for transforming placeholder steps in Pipulate workflows into functional widgets. Each recipe provides detailed implementation instructions that maintain workflow patterns while adding specific functionality.

## Critical Patterns

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

## Using Widget Recipes

1. **Start with a placeholder step** created using the instructions in `widget_implementation_guide.md`.
2. **Choose a recipe** that matches your needs from the ones available below.
3. **Follow the implementation phases** described in the recipe, which typically include:
   - Adding helper methods to your workflow class
   - Updating the Step definition
   - Modifying the GET and SUBMIT handlers
   - Adding any additional routes or handlers needed

## Available Recipes

### Input Collection Widgets

| Recipe | Description | Key Features | Critical Notes |
|--------|-------------|-------------|----------------|
| [Text Input Widget](01_text_input_widget.md) | Basic text input with validation | Simple, reusable text input pattern | Preserves chain reaction |
| [Botify URL Widget](02_botify_url_widget.md) | Validates and extracts Botify project URLs | URL pattern validation, data extraction | Handles serialization |
| [Dropdown Selection Widget](03_dropdown_selection_widget.md) | Selection widget with options | Dynamic options, preset selections | Maintains state |

### Data Display Widgets

| Recipe | Description | Key Features | Critical Notes |
|--------|-------------|-------------|----------------|
| [Pandas Table Widget](04_pandas_table_widget.md) | Creates and displays DataFrame tables | CSV processing, HTML table rendering | Memory management |
| [Markdown Widget](05_markdown_widget.md) | Renders Markdown content | Text formatting, code blocks | Security aware |
| [Mermaid Diagram Widget](06_mermaid_diagram_widget.md) | Creates flowcharts and diagrams | Interactive diagrams, code generation | Client-side rendering |

### Operational Widgets

| Recipe | Description | Key Features | Critical Notes |
|--------|-------------|-------------|----------------|
| [API Request Widget](07_api_request_widget.md) | Makes API calls to external services | Request configuration, response handling | Error handling |
| [CSV Download Widget](08_csv_download_widget.md) | Manages file downloads with status | Progress tracking, async operations | Chain preservation |
| [Polling Status Widget](09_polling_status_widget.md) | Polls for status of long-running operations | Automatic updates, completion detection | State management |
| [File Upload Widget](10_file_upload_widget.md) | Handles file uploads | Validation, processing | Security focus |

## Widget Recipe Template

When creating new widget recipes, use the [Widget Recipe Template](00_widget_recipe_template.md) as a starting point to ensure consistency across all recipes.

## Customization Markers

All recipes use standardized markers for customization points:

- `CUSTOMIZE_STEP_DEFINITION`: Modify Step namedtuple parameters
- `CUSTOMIZE_VALUE_ACCESS`: Access saved state data
- `CUSTOMIZE_DISPLAY`: Update finalized state display
- `CUSTOMIZE_COMPLETE`: Enhance the completion state display
- `CUSTOMIZE_FORM`: Replace the form in the GET handler
- `CUSTOMIZE_FORM_PROCESSING`: Process form data in the SUBMIT handler
- `CUSTOMIZE_VALIDATION`: Add validation logic
- `CUSTOMIZE_DATA_PROCESSING`: Transform input data as needed
- `CUSTOMIZE_STATE_STORAGE`: Save data to pipeline state
- `CUSTOMIZE_WIDGET_DISPLAY`: Create widget for display in completion view

## Preservation Notes

Critical patterns that must be preserved in all widget implementations:

- Chain reaction mechanism with the next step (MOST CRITICAL)
- Revert control functionality
- State management patterns for tracking completion
- Forward-only state clearing on revert
- Proper finalization handling
- Consistent error handling using `pip.get_style("error")`

## Troubleshooting

Common integration issues and solutions:

1. **Chain Reaction Not Working**
   - Verify `hx_trigger="load"` is present
   - Check `id` and `hx_get` attributes match
   - Ensure proper nesting of Div elements

2. **State Management Issues**
   - Use `pip.update_step_state` for primary values
   - Log state before/after updates
   - Test revert functionality thoroughly

3. **Error Handling**
   - Use standardized error styling
   - Implement proper validation
   - Handle edge cases gracefully

## Adding New Recipes

To add new widget recipes:

1. Copy the template from `00_widget_recipe_template.md`
2. Create a new file with an appropriate name, using the next available number
3. Implement the recipe following the standard format
4. Update this README to include your new recipe in the appropriate category
5. Test the recipe by implementing it in a real workflow
6. Verify chain reaction pattern preservation
7. Document any special considerations or limitations