import inspect
import os
import re
import sys

import fastlite
from fasthtml.common import *
from loguru import logger
from server import DB_FILENAME
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
        db_path = os.path.join(os.path.dirname(__file__), '..', DB_FILENAME)
        logger.warning(f'TASKS INIT: Using database path: {db_path}')
        logger.warning(f'TASKS INIT: DB_FILENAME value: {DB_FILENAME}')
        self.plugin_db = fastlite.database(db_path)
        logger.warning(f'TASKS INIT: Plugin database instance: {self.plugin_db}')
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
        
        # Add profile navigation route
        @self.app.route(f'{prefix}/navigate/{{profile_id:int}}', methods=['POST'])
        async def navigate_to_profile(profile_id: int):
            """Navigate to tasks for a specific profile."""
            try:
                # Validate profile exists by checking if there's a profile record 
                profiles_table = self.plugin_db.t.profile
                profiles_table.dataclass()  # Enable dataclass returns
                profile = profiles_table.get(profile_id)
                if not profile:
                    logger.warning(f"Attempted to navigate to non-existent profile {profile_id}")
                    from fasthtml.common import HTTPException
                    raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
                
                # Switch to the profile 
                self.db_dictlike['last_profile_id'] = profile_id
                logger.info(f"📋 Navigated to tasks for profile {profile_id} ({profile.name})")
                
                # Return full page refresh to update everything
                from fasthtml.common import RedirectResponse
                return RedirectResponse(url=f'/{self.name}', status_code=303)
            except Exception as e:
                logger.error(f"Error navigating to profile {profile_id}: {e}")
                from fasthtml.common import HTTPException
                raise HTTPException(status_code=500, detail="Failed to navigate to profile")

    def get_all_profile_ids(self):
        """Get all profile IDs sorted by ID."""
        try:
            logger.warning(f"TASKS DEBUG: Accessing database: {self.plugin_db}")
            profiles_table = self.plugin_db.t.profile
            profiles_table.dataclass()  # Enable dataclass returns
            profiles = list(profiles_table())
            logger.warning(f"TASKS DEBUG: Found {len(profiles)} profiles: {[p.id for p in profiles]}")
            return sorted([p.id for p in profiles])
        except Exception as e:
            logger.error(f"Error getting profile IDs: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def create_profile_navigation(self, current_profile_id):
        """Create navigation arrows for switching between profiles."""
        logger.debug(f"Creating profile navigation for profile {current_profile_id}")
        
        # Check if profile is locked - hide navigation if locked
        profile_locked = self.db_dictlike.get('profile_locked', '0') == '1'
        logger.debug(f"Profile locked: {profile_locked}")
        if profile_locked:
            logger.debug("Profile is locked, hiding navigation")
            return None
        
        profile_ids = self.get_all_profile_ids()
        logger.debug(f"Retrieved profile IDs: {profile_ids}")
        if len(profile_ids) <= 1:
            logger.debug("Only one profile or less, no navigation needed")
            return None  # No navigation needed for single profile
        
        # Convert current_profile_id to int to match profile_ids list
        try:
            current_profile_id_int = int(current_profile_id)
            current_index = profile_ids.index(current_profile_id_int)
            logger.debug(f"Current profile index: {current_index}")
        except (ValueError, TypeError):
            logger.warning(f"Current profile {current_profile_id} (type: {type(current_profile_id)}) not found in profile list: {profile_ids}")
            return None
        
        # Previous profile
        prev_profile_id = profile_ids[current_index - 1] if current_index > 0 else None
        prev_button = Button(
            '◂ Previous',
            hx_post=f'{self.ENDPOINT_PREFIX}/navigate/{prev_profile_id}' if prev_profile_id else '#',
            hx_target='body',
            hx_swap='outerHTML',
            cls=f"{'primary outline' if not prev_profile_id else 'primary'} width-160",
            disabled=not prev_profile_id
        )
        
        # Next profile  
        next_profile_id = profile_ids[current_index + 1] if current_index < len(profile_ids) - 1 else None
        next_button = Button(
            'Next ▸',
            hx_post=f'{self.ENDPOINT_PREFIX}/navigate/{next_profile_id}' if next_profile_id else '#',
            hx_target='body', 
            hx_swap='outerHTML',
            cls=f"{'primary outline' if not next_profile_id else 'primary'} width-160",
            disabled=not next_profile_id
        )
        
        return Div(
            prev_button,
            next_button,
            cls='flex-center-gap'
        )

    async def landing(self, request=None):
        """Renders the main view for the plugin."""
        logger.debug(f'{self.DISPLAY_NAME}Plugin.landing called')
        current_profile_id = self.db_dictlike.get('last_profile_id', 1)
        logger.debug(f'Landing page using profile_id: {current_profile_id}')
        
        # Get current profile name for header
        profile_name = "Unknown Profile"
        try:
            profiles_table = self.plugin_db.t.profile
            profiles_table.dataclass()  # Enable dataclass returns
            profile = profiles_table.get(current_profile_id)
            if profile:
                profile_name = profile.name
        except Exception as e:
            logger.warning(f"Error getting profile name for {current_profile_id}: {e}")
        
        # Get tasks for current profile
        items_query = self.table(where=f'profile_id = {current_profile_id}')
        items = sorted(items_query, key=lambda item: float(item.priority or 0) if isinstance(item.priority, (int, float, str)) else float('inf'))
        logger.debug(f'Found {len(items)} {self.name} for profile {current_profile_id}')
        
        # Create profile navigation arrows (only if not locked)
        nav_arrows = self.create_profile_navigation(current_profile_id)
        
        add_placeholder = f'Add new {self.pipulate.make_singular(self.name.lower())}'
        
        # Build the content with optional navigation
        content_elements = [
            H2(f'{self.DISPLAY_NAME} List - {profile_name}'),
        ]
        
        # Add navigation arrows before the task list (if available)
        if nav_arrows:
            content_elements.append(nav_arrows)
        
        # Add the main task card
        content_elements.append(
            Card(
                Ul(*[self.app_instance.render_item(item) for item in items], id=self.LIST_ID, cls='sortable', style='padding-left: 0;'),
                header=Form(Group(Input(placeholder=add_placeholder, id=self.INPUT_ID, name=self.FORM_FIELD_NAME, autofocus=True), Button('Add', type='submit')), hx_post=self.ENDPOINT_PREFIX, hx_swap='beforeend', hx_target=f'#{self.LIST_ID}', hx_on__after_request="this.reset(); document.getElementById(this.querySelector('input').id).focus();")
            )
        )
        
        return Div(*content_elements, id=self.CONTAINER_ID, cls='flex-column')

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
