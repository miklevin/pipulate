# Widget Recipe System

This directory contains recipes for transforming placeholder steps in Pipulate workflows into functional widgets. Each recipe provides detailed implementation instructions that maintain workflow patterns while adding specific functionality.

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

| Recipe | Description | Key Features |
|--------|-------------|-------------|
| [Text Input Widget](01_text_input_widget.md) | Basic text input with validation | Simple, reusable text input pattern |
| [Botify URL Widget](02_botify_url_widget.md) | Validates and extracts Botify project URLs | URL pattern validation, data extraction |
| [Dropdown Selection Widget](03_dropdown_selection_widget.md) | Selection widget with options | Dynamic options, preset selections |

### Data Display Widgets

| Recipe | Description | Key Features |
|--------|-------------|-------------|
| [Pandas Table Widget](04_pandas_table_widget.md) | Creates and displays DataFrame tables | CSV processing, HTML table rendering |
| [Markdown Widget](05_markdown_widget.md) | Renders Markdown content | Text formatting, code blocks |
| [Mermaid Diagram Widget](06_mermaid_diagram_widget.md) | Creates flowcharts and diagrams | Interactive diagrams, code generation |

### Operational Widgets

| Recipe | Description | Key Features |
|--------|-------------|-------------|
| [API Request Widget](07_api_request_widget.md) | Makes API calls to external services | Request configuration, response handling |
| [CSV Download Widget](08_csv_download_widget.md) | Manages file downloads with status | Progress tracking, async operations |
| [Polling Status Widget](09_polling_status_widget.md) | Polls for status of long-running operations | Automatic updates, completion detection |
| [File Upload Widget](10_file_upload_widget.md) | Handles file uploads | Validation, processing |

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

- Chain reaction mechanism with the next step
- Revert control functionality
- State management patterns for tracking completion
- Forward-only state clearing on revert
- Proper finalization handling

## Adding New Recipes

To add new widget recipes:

1. Copy the template from `00_widget_recipe_template.md`
2. Create a new file with an appropriate name, using the next available number
3. Implement the recipe following the standard format
4. Update this README to include your new recipe in the appropriate category
5. Test the recipe by implementing it in a real workflow 