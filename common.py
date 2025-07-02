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
from datetime import datetime
from fasthtml.common import HTMLResponse, Li, A, Input, to_xml
from loguru import logger

# 🎯 Import the durable backup system
try:
    from helpers.durable_backup_system import backup_manager
except ImportError:
    backup_manager = None
    logger.warning("⚠️ Durable backup system not available")


class BaseCrud:
    """
    CRUD base class for all Apps. The CRUD is DRY and the Workflows are WET!
    
    🎯 ENHANCED with Durable Backup Support:
    - Auto-triggers backups on data changes
    - Soft delete support (mark as deleted_at instead of hard delete)
    - Gantt field support for task management
    - Cross-platform data persistence
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None, pipulate_instance=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field  # Field to toggle (e.g., 'done', 'active')
        self.sort_field = sort_field or 'priority'
        self.item_name_field = 'name'
        self.sort_dict = sort_dict or {}
        self.pipulate_instance = pipulate_instance
        
        # 🎯 DURABLE BACKUP INTEGRATION
        self.backup_enabled = backup_manager is not None
        self.table_name = getattr(table, 'name', name.lower())
        
        # 🎯 SOFT DELETE CONFIGURATION
        self.soft_delete_enabled = True  # Enable soft deletes by default
        self.deleted_field = 'deleted_at'
        self.updated_field = 'updated_at'
        
        if self.backup_enabled:
            logger.info(f"🗃️ {name} CRUD initialized with durable backup support")
            self._ensure_backup_schema()
        
        # Existing pipeline_instance method wrapper
        def safe_send_message(message, verbatim=True):
            """Safely send message through pipulate without breaking if not available."""
            try:
                if self.pipulate_instance and hasattr(self.pipulate_instance, 'get_message_queue'):
                    queue = self.pipulate_instance.get_message_queue()
                    if hasattr(queue, 'add'):
                        asyncio.create_task(queue.add(self.pipulate_instance, message, verbatim=verbatim))
                    elif hasattr(self.pipulate_instance, 'stream'):
                        asyncio.create_task(self.pipulate_instance.stream(message, verbatim=verbatim))
                    else:
                        print(f"Message: {message}")
            except Exception as e:
                print(f"Failed to send message: {message} (Error: {e})")
        
        self.safe_send_message = safe_send_message

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
            item_name = getattr(item, self.item_name_field, f'Item {item_id}')
            
            # 🎯 ENHANCED: Use soft delete when enabled and supported
            soft_delete_attempted = False
            if self.soft_delete_enabled:
                soft_delete_attempted = self._soft_delete_item(item_id)
            
            if soft_delete_attempted:
                action_verb = "soft deleted"
            else:
                # Traditional hard delete as fallback
                self.table.delete(item_id)
                action_verb = "removed"
            
            # 🎯 TRIGGER BACKUP after successful delete
            self._trigger_backup()
            
            action_details = f"The {self.name} item '{item_name}' was {action_verb}."
            prompt = action_details
            self.safe_send_message(prompt, verbatim=True)
            if self.name == 'profiles':
                response = HTMLResponse('')
                response.headers['HX-Refresh'] = 'true'
                return response
            else:
                return HTMLResponse('')
        except Exception as e:
            error_msg = str(e)
            action_details = f'An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}'
            prompt = action_details
            self.safe_send_message(prompt, verbatim=True)
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
            self.safe_send_message(action_details, verbatim=True)
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
            self.safe_send_message(action_details, verbatim=True)
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
            self.safe_send_message(prompt, verbatim=True)
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
            self.safe_send_message(prompt, verbatim=True)
            return ('Invalid data format', 400)
        except Exception as e:
            error_msg = f'Error updating {self.name} order: {str(e)}'
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            action_details = f'An error occurred while sorting {self.name} items: {error_msg}'
            prompt = action_details
            self.safe_send_message(prompt, verbatim=True)
            return (str(e), 500)

    async def insert_item(self, request):
        try:
            form = await request.form()
            insert_data = self.prepare_insert_data(form)
            if insert_data is None:
                return HTMLResponse(f"<div style='color:red;'>Invalid {self.name} data</div>", status_code=400)
            
            # 🎯 ENHANCED: Add timestamp fields for backup tracking (only if table supports it)
            if self.backup_enabled and self._has_backup_fields():
                current_time = datetime.now().isoformat()
                insert_data[self.updated_field] = current_time
                # Don't set deleted_at on insert (should be NULL for active records)
            
            logger.debug(f'[DEBUG] Attempting to insert data into {self.name}: {insert_data}')
            new_item = self.table.insert(insert_data)
            logger.debug(f'[DEBUG] Successfully inserted item into {self.name}: {new_item}')
            
            # 🎯 TRIGGER BACKUP after successful insert
            self._trigger_backup()
            
            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            self.safe_send_message(action_details, verbatim=True)
            rendered_item_ft = self.render_item(new_item)
            logger.debug(f'[DEBUG] Rendered item type (insert_item for {self.name}): {type(rendered_item_ft)}')
            return rendered_item_ft
        except Exception as e:
            import traceback
            logger.exception(f'Detailed error inserting item in {self.name}:')
            error_msg = f'Error inserting {self.name}: {str(e)}'
            action_details = f'An error occurred while adding a new {self.name}: {error_msg}'
            self.safe_send_message(action_details, verbatim=True)
            return HTMLResponse(f"<div style='color:red;'>Error inserting {self.name}: {error_msg}</div>", status_code=500)

    async def update_item(self, request, item_id: int):
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if update_data is None:
                return HTMLResponse(f"<div style='color:red;'>Invalid {self.name} data</div>", status_code=400)
            
            # 🎯 ENHANCED: Add updated timestamp for backup tracking (only if table supports it)
            if self.backup_enabled and self._has_backup_fields():
                update_data[self.updated_field] = datetime.now().isoformat()
            
            original_item = self.table[item_id]
            old_values = {field: getattr(original_item, field, None) for field in update_data.keys()}
            
            # Update the item
            updated_item = self.table.update(item_id, **update_data)
            
            # 🎯 TRIGGER BACKUP after successful update
            self._trigger_backup()
            
            # Track changes for logging
            changes = {}
            for field, new_value in update_data.items():
                old_value = old_values.get(field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
            
            if changes:
                item_name_display = getattr(updated_item, self.item_name_field, f'Item {item_id}')
                changes_str = ', '.join([f"{field}: '{change['old']}' → '{change['new']}'" for field, change in changes.items()])
                
                if hasattr(self.pipulate_instance, 'fmt'):
                    formatted_changes = self.pipulate_instance.fmt(changes_str)
                else:
                    formatted_changes = changes_str
                    
                action_details = f"The {self.name} item '{item_name_display}' was updated. Changes: {formatted_changes}"
                self.safe_send_message(action_details, verbatim=True)
                logger.debug(f'Updated {self.name} item {item_id}. Changes: {changes_str}')
            
            rendered_item_ft = self.render_item(updated_item)
            return rendered_item_ft
            
        except Exception as e:
            import traceback
            logger.exception(f'Detailed error updating item {item_id} in {self.name}:')
            error_msg = f'Error updating {self.name}: {str(e)}'
            action_details = f'An error occurred while updating {self.name} (ID: {item_id}): {error_msg}'
            self.safe_send_message(action_details, verbatim=True)
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

    def _has_backup_fields(self) -> bool:
        """Check if the table has the required backup fields."""
        if not self.backup_enabled:
            return False
            
        try:
            # Check if the table has updated_at and deleted_at fields
            # For now, we'll assume tables don't have these fields by default
            # This can be enhanced later to actually check the table schema
            return False
        except Exception as e:
            logger.debug(f"Error checking backup fields for {self.table_name}: {e}")
            return False
    
    def _ensure_backup_schema(self):
        """Ensure table has the required fields for backup integration."""
        if not self.backup_enabled:
            return
            
        try:
            # For now, just log that we're checking the schema
            # Later we can add actual schema migration logic here
            has_fields = self._has_backup_fields()
            if has_fields:
                logger.debug(f"✅ Backup schema verified for {self.table_name}")
            else:
                logger.debug(f"ℹ️ Backup fields not present in {self.table_name} - backup disabled for this table")
                self.backup_enabled = False
        except Exception as e:
            logger.error(f"❌ Error ensuring backup schema for {self.table_name}: {e}")
            self.backup_enabled = False
    
    def _trigger_backup(self):
        """Trigger a backup operation for this table."""
        if not self.backup_enabled:
            return
            
        try:
            # Get the database path from the table or use default
            db_path = getattr(self.table, 'db_path', 'data/app.db')
            success = backup_manager.backup_table(db_path, self.table_name)
            if success:
                logger.debug(f"✅ Backup triggered for {self.table_name}")
            else:
                logger.warning(f"⚠️ Backup failed for {self.table_name}")
        except Exception as e:
            logger.error(f"❌ Error triggering backup for {self.table_name}: {e}")
    
    def _soft_delete_item(self, item_id: int):
        """Perform soft delete by setting deleted_at timestamp."""
        # Only do soft delete if table supports backup fields
        if not self.backup_enabled or not self._has_backup_fields():
            return False
            
        try:
            # Update the item with deleted_at timestamp
            update_data = {
                self.deleted_field: datetime.now().isoformat(),
                self.updated_field: datetime.now().isoformat()
            }
            
            # Update the database record
            item = self.table[item_id]
            for field, value in update_data.items():
                if hasattr(item, field):
                    setattr(item, field, value)
            
            # Save changes (FastLite should handle this automatically)
            logger.info(f"🗑️ Soft deleted {self.name} ID {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Soft delete failed for {self.name} ID {item_id}: {e}")
            return False 