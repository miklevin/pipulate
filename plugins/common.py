"""
Common classes and utilities for plugins.

This module contains shared classes that plugins can import without creating
circular dependencies with server.py.

Global UI constants can be accessed through the pipulate_instance when available:
- pipulate_instance.get_button_border_radius() - Global button roundedness setting
- pipulate_instance.get_ui_constants() - All UI constants
"""

import asyncio
import inspect
import json
import logging
from fasthtml.common import HTMLResponse, Li, A, Input, to_xml


class BaseCrud:
    """
    CRUD base class for all Apps. The CRUD is DRY and the Workflows are WET!
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None, pipulate_instance=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.item_name_field = 'name'
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}
        self.pipulate_instance = pipulate_instance

        def safe_send_message(message, verbatim=True):
            if not self.pipulate_instance:
                return
            try:
                stream_method = self.pipulate_instance.stream
                if inspect.iscoroutinefunction(stream_method):
                    return asyncio.create_task(stream_method(message, verbatim=verbatim, spaces_after=1))
                else:
                    return stream_method(message, verbatim=verbatim, spaces_after=1)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f'Error in send_message: {e}')
                return None
        self.send_message = safe_send_message

    def get_global_border_radius(self):
        """Get the global button border radius setting for consistent styling."""
        if self.pipulate_instance:
            return self.pipulate_instance.get_button_border_radius()
        return 'var(--pico-border-radius)'  # Fallback to PicoCSS default

    def register_routes(self, rt):
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        return f'/{self.name}/{action}/{item_id}'

    def render_item(self, item):
        item_name = getattr(item, self.item_name_field, 'Item')
        toggle_state = getattr(item, self.toggle_field, False) if self.toggle_field else False
        
        return Li(
            A('🗑', 
              href='#', 
              hx_swap='outerHTML', 
              hx_delete=f'/task/delete/{item.id}', 
              hx_target=f'#todo-{item.id}', 
              _class='delete-icon', 
              style=('cursor: pointer; ', 'display: inline'),
              role='button',
              aria_label=f'Delete {self.name} item: {item_name}',
              title=f'Delete {item_name}'
            ), 
            Input(
                type='checkbox', 
                checked='1' if toggle_state else '0', 
                hx_post=f'/task/toggle/{item.id}', 
                hx_swap='outerHTML', 
                hx_target=f'#todo-{item.id}',
                aria_label=f'Toggle {self.name} item: {item_name}',
                aria_describedby=f'todo-{item.id}-label'
            ), 
            A(item_name, 
              href='#', 
              _class='todo-title', 
              style=('color: inherit; ', 'text-decoration: none'),
              id=f'todo-{item.id}-label',
              aria_label=f'{self.name.capitalize()} item: {item_name}'
            ), 
            data_id=item.id, 
            data_priority=getattr(item, self.sort_field, 0) if self.sort_field else 0, 
            id=f'todo-{item.id}', 
            cls='list-style-none',
            role='listitem',
            aria_label=f'{self.name.capitalize()} item {item.id}: {item_name}'
        )

    async def delete_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_name = getattr(item, self.item_name_field, 'Item')
            self.table.delete(item_id)
            logger = logging.getLogger(__name__)
            logger.debug(f'Deleted item ID: {item_id}')
            action_details = f"The {self.name} item '{item_name}' was removed."
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            if self.name == 'profiles':
                response = HTMLResponse('')
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
                return response
            return HTMLResponse('')
        except Exception as e:
            error_msg = f'Error deleting item: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            action_details = f'An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return (str(e), 500)

    async def toggle_item(self, request, item_id: int):
        """Override the BaseCrud toggle_item to handle FastHTML objects properly"""
        try:
            item = self.table[item_id]
            current_status = getattr(item, self.toggle_field)
            new_status = not current_status
            setattr(item, self.toggle_field, new_status)
            updated_item = self.table.update(item)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            status_text = 'checked' if new_status else 'unchecked'
            action_details = f"The {self.name} item '{item_name}' is now {status_text}."
            self.send_message(action_details, verbatim=True)
            rendered_item_ft = self.render_item(updated_item)
            logger = logging.getLogger(__name__)
            logger.debug(f'[DEBUG] Rendered item type (toggle_item): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] HTML content (toggle_item): {html_content[:100]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles':
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to toggle_item on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            elif self.name == 'roles':
                logger.debug(f'Adding HX-Trigger for refreshAppMenu due to role toggle_item (item_id: {item_id})')
                response.headers['HX-Trigger'] = json.dumps({'refreshAppMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error toggling {self.name} item {item_id}: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            logger.exception(f'Detailed error toggling item {item_id} in {self.name}:')
            action_details = f'An error occurred while toggling {self.name} (ID: {item_id}): {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error: {error_msg}</div>", status_code=500)

    async def sort_items(self, request):
        """Override the BaseCrud sort_items to also refresh the profile menu"""
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f'Received request to sort {self.name}.')
            values = await request.form()
            items = json.loads(values.get('items', '[]'))
            logger.debug(f'Parsed items: {items}')
            
            # CRITICAL: Server-side validation to prevent meaningless sort requests
            current_order_changed = False
            for item in items:
                item_id = int(item['id'])
                new_priority = int(item['priority'])
                current_item = self.table[item_id]
                current_priority = getattr(current_item, self.sort_field)
                if current_priority != new_priority:
                    current_order_changed = True
                    break
            
            if not current_order_changed:
                logger.debug(f'🚫 SMART SORT BLOCKED: No actual changes detected for {self.name} - current order already matches requested order')
                return HTMLResponse('')  # Return empty response without triggers
            
            logger.debug(f'✅ SMART SORT ALLOWED: Actual changes detected for {self.name}')
            
            # Update all items and collect their names in new order
            updated_items = []
            for item in sorted(items, key=lambda x: int(x['priority'])):
                item_id = int(item['id'])
                priority = int(item['priority'])
                self.table.update(id=item_id, **{self.sort_field: priority})
                item_name = getattr(self.table[item_id], self.item_name_field, 'Item')
                updated_items.append(item_name)
            
            # Create a concise, human-friendly message showing the new order
            items_list = ', '.join(updated_items)
            action_details = f'Reordered {self.name}: {items_list}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            logger.debug(f'{self.name.capitalize()} order updated successfully')
            response = HTMLResponse('')
            triggers = {}
            if self.name == 'profiles':
                triggers['refreshProfileMenu'] = {}
            elif self.name == 'roles':
                triggers['refreshAppMenu'] = {}
            if triggers:
                response.headers['HX-Trigger'] = json.dumps(triggers)
            return response
        except json.JSONDecodeError as e:
            error_msg = f'Invalid data format: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            action_details = f'An error occurred while sorting {self.name} items: {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return ('Invalid data format', 400)
        except Exception as e:
            error_msg = f'Error updating {self.name} order: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            action_details = f'An error occurred while sorting {self.name} items: {error_msg}'
            prompt = action_details
            self.send_message(prompt, verbatim=True)
            return (str(e), 500)

    async def insert_item(self, request):
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f'[DEBUG] Starting BaseCrud insert_item for {self.name}')
            form = await request.form()
            logger.debug(f'[DEBUG] Form data for {self.name}: {dict(form)}')
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug(f'[DEBUG] No new_item_data for {self.name}, returning empty response for HTMX.')
                return HTMLResponse('')
            new_item = await self.create_item(**new_item_data)
            logger.debug(f'[DEBUG] Created new item for {self.name}: {new_item}')
            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            self.send_message(action_details, verbatim=True)
            rendered_item_ft = self.render_item(new_item)
            logger.debug(f'[DEBUG] Rendered item type (insert_item for {self.name}): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] Rendered item HTML (insert_item for {self.name}): {html_content[:150]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles':
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to insert_item on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error inserting {self.name}: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            logger.exception(f'Detailed error inserting item in {self.name}:')
            action_details = f'An error occurred while adding a new {self.name}: {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error inserting {self.name}: {error_msg}</div>", status_code=500)

    async def update_item(self, request, item_id: int):
        """Override the BaseCrud update_item to handle FastHTML objects properly"""
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:
                logger = logging.getLogger(__name__)
                logger.debug(f'Update for {self.name} item {item_id} aborted by prepare_update_data.')
                return HTMLResponse('')
            item = self.table[item_id]
            before_state = {k: getattr(item, k, None) for k in update_data.keys()}
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            after_state = {k: getattr(updated_item, k, None) for k in update_data.keys()}
            change_dict = {}
            changes_log_list = []
            for key in update_data.keys():
                if before_state.get(key) != after_state.get(key):
                    change_dict[key] = after_state.get(key)
                    changes_log_list.append(f"{key} changed from '{before_state.get(key)}' to '{after_state.get(key)}'")
            changes_str = '; '.join(changes_log_list)
            item_name_display = getattr(updated_item, self.item_name_field, 'Item')
            if changes_log_list:
                formatted_changes = self.pipulate_instance.fmt(changes_str) if hasattr(self.pipulate_instance, 'fmt') else changes_str
                action_details = f"The {self.name} item '{item_name_display}' was updated. Changes: {formatted_changes}"
                self.send_message(action_details, verbatim=True)
                logger = logging.getLogger(__name__)
                logger.debug(f'Updated {self.name} item {item_id}. Changes: {changes_str}')
            else:
                logger = logging.getLogger(__name__)
                logger.debug(f'No effective changes for {self.name} item {item_id}.')
            rendered_item_ft = self.render_item(updated_item)
            logger = logging.getLogger(__name__)
            logger.debug(f'[DEBUG] Rendered item type (update_item): {type(rendered_item_ft)}')
            html_content = to_xml(rendered_item_ft)
            logger.debug(f'[DEBUG] HTML content (update_item): {html_content[:100]}...')
            response = HTMLResponse(str(html_content))
            if self.name == 'profiles' and 'name' in change_dict:
                logger.debug(f"Adding HX-Trigger for refreshProfileMenu due to update_item (name change) on '{self.name}'")
                response.headers['HX-Trigger'] = json.dumps({'refreshProfileMenu': {}})
            return response
        except Exception as e:
            error_msg = f'Error updating {self.name} item {item_id}: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            logger.exception(f'Detailed error updating item {item_id} in {self.name}:')
            action_details = f'An error occurred while updating {self.name} (ID: {item_id}): {error_msg}'
            self.send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error: {error_msg}</div>", status_code=500)

    async def create_item(self, **kwargs):
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f'Creating new {self.name} with data: {kwargs}')
            new_item = self.table.insert(kwargs)
            logger.debug(f'Created new {self.name}: {new_item}')
            return new_item
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f'Error creating {self.name}: {str(e)}')
            raise e

    def prepare_insert_data(self, form):
        raise NotImplementedError('Subclasses must implement prepare_insert_data')

    def prepare_update_data(self, form):
        raise NotImplementedError('Subclasses must implement prepare_update_data') 