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
2. **Choose a recipe** from the appropriate category below that matches your needs.
3. **Follow the implementation phases** described in the recipe, which typically include:
   - Adding helper methods to your workflow class
   - Updating the Step definition
   - Modifying the GET and SUBMIT handlers
   - Adding any additional routes or handlers needed

## Recipe Categories

### Input Widgets (`input/`)
Widgets for collecting user input:
- `text_input.md`: Basic text input with validation
- `url_input.md`: URL validation and processing
- `dropdown.md`: Selection widget with options

### Display Widgets (`display/`)
Widgets for presenting information:
- `table.md`: DataFrame and table rendering
- `markdown.md`: Markdown content display
- `mermaid.md`: Diagram generation and display

### Operation Widgets (`operation/`)
Widgets for performing actions:
- `file_download.md`: File download management
- `javascript.md`: Client-side code execution
- `api_request.md`: External API integration

### Integration Widgets (`integration/`)
Widgets for external system integration:
- `browser.md`: Browser automation integration
- `search.md`: Search engine integration

## Recipe Template

When creating new widget recipes, use the template in `_template/widget_recipe_template.md` as a starting point to ensure consistency across all recipes.

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

1. Copy the template from `_template/widget_recipe_template.md`
2. Create a new file in the appropriate category directory
3. Implement the recipe following the standard format
4. Update this README to include your new recipe
5. Test the recipe by implementing it in a real workflow
6. Verify chain reaction pattern preservation
7. Document any special considerations or limitations