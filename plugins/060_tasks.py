import inspect
import os
import re
import sys

import fastlite
from fasthtml.common import *
from loguru import logger
from server import get_db_filename
from common import BaseCrud

ROLES = ['Core']
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class PluginIdentityManager:
    # Override this in subclasses to customize the emoji
    EMOJI = ''

    def __init__(self, filename=None):
        if not filename:
            filename = os.path.basename(__file__)
        self.original_name = filename.replace('.py', '')
        self.name = re.sub('^\\d+_', '', self.original_name)
        self.ENDPOINT_PREFIX = f'/{self.name}'
        self.LIST_ID = f'{self.name}-list'
        self.ITEM_CLASS = f'{self.name}-item'
        self.FORM_FIELD_NAME = f'{self.name}-text'
        self.INPUT_ID = f'{self.name}-input'
        self.CONTAINER_ID = f'{self.name}-container'

    @property

    def DISPLAY_NAME(self):
        base_name = self.name.title()
        if self.EMOJI:
            return f'{base_name} {self.EMOJI}'
        return base_name

    @property

    def DB_TABLE_NAME(self):
        return self.name

    @property

    def TRAINING_PROMPT(self):
        return f'{self.name}.md'


class CrudCustomizer(BaseCrud):

    def __init__(self, table, plugin):
        self.plugin = plugin
        self.pipulate_instance = getattr(plugin, 'pipulate', None)
        super().__init__(name=plugin.name, table=table, toggle_field='done', sort_field='priority', pipulate_instance=self.pipulate_instance)
        self.item_name_field = 'text'
        logger.debug(f'{self.plugin.DISPLAY_NAME}App initialized with table name: {table.name}')

    def render_item(self, item):
        logger.debug(f'{self.plugin.DISPLAY_NAME}App.render_item called for: {item}')
        return render_item(item, self)

    def prepare_insert_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            logger.warning(f'Attempted to insert {self.plugin.name} with empty text.')
            return None
        current_profile_id = self.plugin.db_dictlike.get('last_profile_id', 1)
        logger.debug(f'Using profile_id: {current_profile_id} for new {self.plugin.name}')
        items_for_profile = self.table('profile_id = ?', [current_profile_id])
        max_priority = max((i.priority or 0 for i in items_for_profile), default=-1) + 1
        priority = int(form.get(f'{self.plugin.name}_priority', max_priority))
        insert_data = {'text': text, 'done': False, 'priority': priority, 'profile_id': current_profile_id}
        logger.debug(f'Prepared insert data: {insert_data}')
        return insert_data

    def prepare_update_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            logger.warning(f'Attempted to update {self.plugin.name} with empty text.')
            return None
        update_data = {'text': text}
        logger.debug(f'Prepared update data: {update_data}')
        return update_data

    async def insert_item(self, request):
        """Override to add FINDER_TOKEN logging for task creation."""
        response = await super().insert_item(request)
        
        # Add greppable logging after successful insert
        try:
            # Get current profile info for context
            current_profile_id = self.plugin.db_dictlike.get('last_profile_id', 1)
            profile_name = "Unknown Profile"
            try:
                profiles_table = self.plugin.plugin_db.t.profile
                profiles_table.dataclass()
                profile = profiles_table.get(current_profile_id)
                if profile:
                    profile_name = profile.name
            except Exception:
                pass
                
            # Get the most recent task for this profile (should be the one just created)
            recent_tasks = list(self.table('profile_id = ? ORDER BY id DESC LIMIT 1', [current_profile_id]))
            if recent_tasks:
                task = recent_tasks[0]
                logger.info(f"🔍 FINDER_TOKEN: TASK_CREATED - Task '{task.text}' created for profile '{profile_name}' (ID: {current_profile_id}) - Priority: {task.priority}")
                
        except Exception as e:
            logger.error(f"Error logging task creation: {e}")
            
        return response

    async def update_item(self, request, item_id: int):
        """Override to add FINDER_TOKEN logging for task updates."""
        # Get task info before update for comparison
        old_task = None
        try:
            old_task = self.table[item_id]
        except Exception:
            pass
            
        response = await super().update_item(request, item_id)
        
        # Add greppable logging after successful update
        try:
            updated_task = self.table[item_id]
            profile_name = "Unknown Profile"
            try:
                profiles_table = self.plugin.plugin_db.t.profile
                profiles_table.dataclass()
                profile = profiles_table.get(updated_task.profile_id)
                if profile:
                    profile_name = profile.name
            except Exception:
                pass
                
            old_text = old_task.text if old_task else "Unknown"
            logger.info(f"🔍 FINDER_TOKEN: TASK_UPDATED - Task ID {item_id} updated from '{old_text}' to '{updated_task.text}' for profile '{profile_name}' (ID: {updated_task.profile_id})")
                
        except Exception as e:
            logger.error(f"Error logging task update: {e}")
            
        return response

    async def toggle_item(self, request, item_id: int):
        """Override to add FINDER_TOKEN logging for task completion status changes."""
        # Get task info before toggle
        old_task = None
        try:
            old_task = self.table[item_id]
        except Exception:
            pass
            
        response = await super().toggle_item(request, item_id)
        
        # Add greppable logging after successful toggle
        try:
            updated_task = self.table[item_id]
            profile_name = "Unknown Profile"
            try:
                profiles_table = self.plugin.plugin_db.t.profile
                profiles_table.dataclass()
                profile = profiles_table.get(updated_task.profile_id)
                if profile:
                    profile_name = profile.name
            except Exception:
                pass
                
            status_change = "completed" if updated_task.done else "reopened"
            logger.info(f"🔍 FINDER_TOKEN: TASK_TOGGLED - Task '{updated_task.text}' {status_change} for profile '{profile_name}' (ID: {updated_task.profile_id}) - Priority: {updated_task.priority}")
                
        except Exception as e:
            logger.error(f"Error logging task toggle: {e}")
            
        return response

    async def delete_item(self, request, item_id: int):
        """Override to add FINDER_TOKEN logging for task deletion."""
        # Get task info before deletion
        deleted_task = None
        profile_name = "Unknown Profile"
        try:
            deleted_task = self.table[item_id]
            profiles_table = self.plugin.plugin_db.t.profile
            profiles_table.dataclass()
            profile = profiles_table.get(deleted_task.profile_id)
            if profile:
                profile_name = profile.name
        except Exception:
            pass
            
        response = await super().delete_item(request, item_id)
        
        # Add greppable logging after successful deletion
        if deleted_task:
            try:
                status_desc = "completed" if deleted_task.done else "pending"
                logger.info(f"🔍 FINDER_TOKEN: TASK_DELETED - Task '{deleted_task.text}' ({status_desc}) deleted from profile '{profile_name}' (ID: {deleted_task.profile_id}) - Priority: {deleted_task.priority}")
            except Exception as e:
                logger.error(f"Error logging task deletion: {e}")
                
        return response


class CrudUI(PluginIdentityManager):
    # Override this to customize the emoji for this specific plugin
    EMOJI = '✔️'

    @property

    def ENDPOINT_MESSAGE(self):
        return f'Manage your {self.DISPLAY_NAME.lower()} list here. Add, edit, sort, and mark items as complete. Each list is kept separate for each Profile.'

    def __init__(self, app, pipulate, pipeline, db_dictlike):
        """Initialize the List Plugin."""
        super().__init__()
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike
        logger.debug(f'{self.DISPLAY_NAME} Plugin initializing...')
        db_path = os.path.join(os.path.dirname(__file__), '..', get_db_filename())  # 🚨 CRITICAL FIX: Use dynamic database resolution
        logger.debug(f'Using database path: {db_path}')
        self.plugin_db = fastlite.database(db_path)
        schema = {'id': int, 'text': str, 'done': bool, 'priority': int, 'profile_id': int, 'pk': 'id'}
        schema_fields = {k: v for k, v in schema.items() if k != 'pk'}
        primary_key = schema.get('pk')
        if not primary_key:
            logger.error("Primary key 'pk' must be defined in the schema dictionary!")
            raise ValueError("Schema dictionary must contain a 'pk' entry.")
        try:
            table_handle = self.plugin_db.t[self.DB_TABLE_NAME]
            logger.debug(f'Got potential table handle via .t accessor: {table_handle}')
            self.table = table_handle.create(**schema_fields, pk=primary_key, if_not_exists=True)
            logger.info(f"Fastlite '{self.DB_TABLE_NAME}' table created or accessed via handle: {self.table}")
            self.table.dataclass()
            logger.info(f'Called .dataclass() on table handle to enable dataclass returns.')
        except Exception as e:
            logger.error(f"Error creating/accessing '{self.DB_TABLE_NAME}' table: {e}")
            raise
        self.app_instance = CrudCustomizer(table=self.table, plugin=self)
        logger.debug(f'{self.DISPLAY_NAME}App instance created.')
        self.register_plugin_routes()
        logger.debug(f'{self.DISPLAY_NAME} Plugin initialized successfully.')
        current_profile_id = self.db_dictlike.get('last_profile_id', 1)
        
        # STARTUP TASK ENUMERATION: Log all pending tasks for AI assistant discovery
        self.log_startup_task_baseline()

    def log_startup_task_baseline(self):
        """
        🔧 STARTUP TASK BASELINE: Log all pending tasks on server startup for AI assistant discovery.
        Creates a reliable control/reference point that LLMs can grep to understand current task state.
        """
        try:
            # Get all tasks from all profiles
            all_tasks = list(self.table())
            
            # Get all profiles for name lookup
            profiles_table = self.plugin_db.t.profile
            profiles_table.dataclass()
            all_profiles = list(profiles_table())
            profile_lookup = {p.id: p.name for p in all_profiles}
            
            # Filter for pending tasks only (done=False or done=0)
            pending_tasks = [task for task in all_tasks if not getattr(task, 'done', False)]
            
            if not pending_tasks:
                logger.info(f"🔍 FINDER_TOKEN: STARTUP_TASKS_BASELINE - No pending tasks found across all profiles")
                return
            
            # Group pending tasks by profile for organized logging
            tasks_by_profile = {}
            total_pending = len(pending_tasks)
            
            for task in pending_tasks:
                profile_id = getattr(task, 'profile_id', None)
                profile_name = profile_lookup.get(profile_id, f'Unknown Profile {profile_id}')
                
                if profile_name not in tasks_by_profile:
                    tasks_by_profile[profile_name] = []
                
                tasks_by_profile[profile_name].append({
                    'id': task.id,
                    'text': task.text,
                    'priority': getattr(task, 'priority', 0),
                    'profile_id': profile_id
                })
            
            # Log summary first
            summary_lines = [
                f"📋 Total pending tasks: {total_pending}",
                f"👥 Profiles with pending tasks: {len(tasks_by_profile)}"
            ]
            
            profile_summary = []
            for profile_name, tasks in tasks_by_profile.items():
                profile_summary.append(f"{profile_name}({len(tasks)})")
            
            if profile_summary:
                summary_lines.append(f"📊 Pending tasks by profile: {', '.join(profile_summary)}")
            
            summary = '\\n    '.join(summary_lines)
            logger.info(f"🔍 FINDER_TOKEN: STARTUP_TASKS_BASELINE - Task Control Established:\\n    {summary}")
            
            # Log detailed breakdown for each profile with pending tasks
            for profile_name, tasks in tasks_by_profile.items():
                # Sort tasks by priority for consistent ordering
                sorted_tasks = sorted(tasks, key=lambda t: t['priority'] if t['priority'] is not None else 999)
                
                task_details = []
                for task in sorted_tasks:
                    task_details.append(f"ID:{task['id']} '{task['text']}' (Priority:{task['priority']})")
                
                task_list = ', '.join(task_details)
                logger.info(f"🔍 FINDER_TOKEN: STARTUP_TASKS_PENDING - Profile '{profile_name}' (ID:{sorted_tasks[0]['profile_id']}) has {len(tasks)} pending: {task_list}")
            
        except Exception as e:
            logger.error(f"❌ FINDER_TOKEN: STARTUP_TASKS_BASELINE_ERROR - Failed to enumerate startup tasks: {e}")

    def register_plugin_routes(self):
        """Register routes manually using app.route."""
        prefix = self.ENDPOINT_PREFIX
        sort_path = f'{prefix}_sort'
        routes_to_register = [(f'{prefix}', self.app_instance.insert_item, ['POST']), (f'{prefix}/{{item_id:int}}', self.app_instance.update_item, ['POST']), (f'{prefix}/delete/{{item_id:int}}', self.app_instance.delete_item, ['DELETE']), (f'{prefix}/toggle/{{item_id:int}}', self.app_instance.toggle_item, ['POST']), (sort_path, self.app_instance.sort_items, ['POST'])]
        logger.debug(f'Registering routes for {self.name} plugin:')
        for path, handler, methods in routes_to_register:
            func = handler
            self.app.route(path, methods=methods)(func)
            logger.debug(f'  Registered: {methods} {path} -> {handler.__name__}')

    async def landing(self, request=None):
        """Renders the main view for the plugin."""
        logger.debug(f'{self.DISPLAY_NAME}Plugin.landing called')
        current_profile_id = self.db_dictlike.get('last_profile_id', 1)
        logger.debug(f'Landing page using profile_id: {current_profile_id}')
        items_query = self.table(where=f'profile_id = {current_profile_id}')
        items = sorted(items_query, key=lambda item: float(item.priority or 0) if isinstance(item.priority, (int, float, str)) else float('inf'))
        logger.debug(f'Found {len(items)} {self.name} for profile {current_profile_id}')
        add_placeholder = f'Add new {self.pipulate.make_singular(self.name.lower())}'
        return Div(Card(H2(f'{self.DISPLAY_NAME} List'), Ul(*[self.app_instance.render_item(item) for item in items], id=self.LIST_ID, cls='sortable', style='padding-left: 0;'), header=Form(Group(Input(placeholder=add_placeholder, id=self.INPUT_ID, name=self.FORM_FIELD_NAME, autofocus=True), Button('Add', type='submit')), hx_post=self.ENDPOINT_PREFIX, hx_swap='beforeend', hx_target=f'#{self.LIST_ID}', hx_on__after_request="this.reset(); document.getElementById(this.querySelector('input').id).focus();")), id=self.CONTAINER_ID, cls='flex-column')

    async def render(self, render_items=None):
        """Fallback render method, currently just calls landing."""
        logger.debug(f'{self.DISPLAY_NAME}Plugin.render called, delegating to landing.')
        return await self.landing()


def render_item(item, app_instance):
    """Renders a single item as an LI element."""
    item_id = f'{app_instance.name}-{item.id}'
    logger.debug(f"Rendering {app_instance.plugin.name} ID {item.id} with text '{item.text}'")
    delete_url = f'{app_instance.plugin.ENDPOINT_PREFIX}/delete/{item.id}'
    toggle_url = f'{app_instance.plugin.ENDPOINT_PREFIX}/toggle/{item.id}'
    update_url = f'{app_instance.plugin.ENDPOINT_PREFIX}/{item.id}'
    checkbox = Input(type='checkbox', name='done_status' if item.done else None, checked=item.done, hx_post=toggle_url, hx_swap='outerHTML', hx_target=f'#{item_id}')
    delete_icon = A('🗑', hx_delete=delete_url, hx_swap='outerHTML', hx_target=f'#{item_id}', cls='task-delete-icon delete-icon')
    update_input_id = f'{app_instance.name}_text_{item.id}'
    text_display = Span(item.text, id=f'{app_instance.name}-text-display-{item.id}', cls='task-text-display', onclick=f"document.getElementById('{app_instance.name}-text-display-{item.id}').style.display='none'; document.getElementById('update-form-{item.id}').style.display='inline-flex'; document.getElementById('{item_id}').style.alignItems='baseline'; document.getElementById('{update_input_id}').focus();")
    update_form = Form(Group(Input(type='text', id=update_input_id, value=item.text, name=app_instance.plugin.FORM_FIELD_NAME, style='flex-grow: 1; margin-right: 5px; margin-bottom: 0;'), Button('Save', type='submit', style='margin-bottom: 0;'), Button('Cancel', type='button', style='margin-bottom: 0;', cls='secondary', onclick=f"document.getElementById('update-form-{item.id}').style.display='none'; document.getElementById('{app_instance.name}-text-display-{item.id}').style.display='inline'; document.getElementById('{item_id}').style.alignItems='center';"), cls='items-center'), cls='task-update-form', id=f'update-form-{item.id}', hx_post=update_url, hx_target=f'#{item_id}', hx_swap='outerHTML')
    return Li(checkbox, text_display, update_form, delete_icon, id=item_id, cls=f"{'done' if item.done else ''} task-item".strip(), data_id=item.id, data_priority=item.priority, data_plugin_item='true', data_list_target=app_instance.plugin.LIST_ID, data_endpoint_prefix=app_instance.plugin.ENDPOINT_PREFIX)
