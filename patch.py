# patch.py
patches = [
    {
        "file": "/home/mike/repos/pipulate/pipulate/core.py",
        "block_name": "wrap_with_inline_button",
        "new_code": """    def wrap_with_inline_button(self, input_element: Input, button_label: str = 'Next ▸', button_class: str = 'primary', show_new_key_button: bool = False, app_name: str = None, **kwargs) -> Div:
        \"\"\"Wrap an input element with an inline button in a flex container.

        Args:
            input_element: The input element to wrap
            button_label: Text to display on the button (default: 'Next ▸')
            button_class: CSS class for the button (default: 'primary')
            show_new_key_button: Whether to show the 🆕 new key button (default: False)
            app_name: App name for new key generation (required if show_new_key_button=True)
            **kwargs: Additional attributes for the button, prefixed with 'button_' (e.g., button_data_testid='my-id')

        Returns:
            Div: A flex container with the input and button(s)
        \"\"\"
        # Styles are now externalized to CSS classes for maintainability

        # Generate unique IDs for input-button association
        input_id = input_element.attrs.get('id') or f'input-{hash(str(input_element))}'
        button_id = f'btn-{input_id}'

        # Enhance input element with semantic attributes if not already present
        if 'aria_describedby' not in input_element.attrs:
            input_element.attrs['aria_describedby'] = button_id
        if 'id' not in input_element.attrs:
            input_element.attrs['id'] = input_id

        # Prepare button attributes with defaults
        button_attrs = {
            'type': 'submit',
            'cls': f'{button_class} inline-button-submit',
            'id': button_id,
            'aria_label': f'Submit {input_element.attrs.get("placeholder", "input")}',
            'title': f'Submit form ({button_label})'
        }

        # Process and merge kwargs, allowing overrides
        for key, value in kwargs.items():
            if key.startswith('button_'):
                # Convert button_data_testid to data-testid
                attr_name = key.replace('button_', '', 1).replace('_', '-')
                button_attrs[attr_name] = value

        # Create enhanced button with semantic attributes and pass through extra kwargs
        enhanced_button = Button(button_label, **button_attrs)

        # Prepare elements for container
        elements = [input_element, enhanced_button]

        # Add new key button if requested
        if show_new_key_button and app_name:
            ui_constants = CFG.UI_CONSTANTS
            # 🆕 New Key button styled via CSS class for maintainability
            new_key_button = Button(
                ui_constants['BUTTON_LABELS']['NEW_KEY'],
                type='button',  # Not a submit button
                cls='new-key-button',  # Externalized styling in styles.css
                id=f'new-key-{input_id}',
                hx_get=f'/generate-new-key/{app_name}',
                hx_target=f'#{input_id}',
                hx_swap='outerHTML',
                aria_label='Generate new pipeline key',
                title='Generate a new auto-incremented pipeline key'
            )
            elements.append(new_key_button)

        return Div(
            *elements,
            cls='inline-button-container',
            role='group',
            aria_label='Input with submit button' + (' and new key generator' if show_new_key_button else '')
        )"""
    }
]