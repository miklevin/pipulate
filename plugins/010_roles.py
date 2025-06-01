# Rename file to create a generic list plugin (e.g. tasks.py, competitors.py)

import inspect
import os
import re
import sys

import fastlite
from fasthtml.common import *
from loguru import logger
from server import DB_FILENAME, BaseCrud

ROLES = []

# Define the standard order of roles
ROLE_ORDER = {
    'Core': 0,
    'Botify Employee': 1,
    'Tutorial': 2,
    'Developer': 3,
    'Components': 4,
    'Workshop': 5,
}

# Plugin visibility mapping based on numeric prefixes
ROLE_PLUGIN_MAPPING = {
    'Core': {
        'show': [(0, 99)],  # Show plugins 000-099 (essential system)
        'description': 'Essential system plugins only'
    },
    'Botify Employee': {
        'show': [(0, 99), (500, 599)],  # Core + Botify workflows
        'description': 'Core system + Botify workflows'
    },
    'Tutorial': {
        'show': [(0, 99), (500, 599), (700, 799)],  # Core + Botify + Tutorial components
        'description': 'Core + Botify + Tutorial components'
    },
    'Developer': {
        'show': [(0, 99), (500, 599), (700, 799)],  # Same as Tutorial for now
        'description': 'Core + Botify + Development tools'
    },
    'Components': {
        'show': [(0, 999)],  # Show everything
        'description': 'All available plugins and components'
    },
    'Workshop': {
        'show': [(0, 999)],  # Show everything
        'description': 'Complete workshop access'
    }
}

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class PluginIdentityManager:
    def __init__(self, filename=None):
        # Get filename if not provided
        if not filename:
            filename = os.path.basename(__file__)

        # Strip .py extension to get the base name with potential numeric prefix
        self.original_name = filename.replace('.py', '')

        # Remove any numeric prefix (e.g., "01_tasks" -> "tasks")
        self.name = re.sub(r'^\d+_', '', self.original_name)

        # Use the name without prefix for all endpoints
        self.ENDPOINT_PREFIX = f"/{self.name}"

        # Other naming constants
        self.LIST_ID = f"{self.name}-list"
        self.ITEM_CLASS = f"{self.name}-item"
        self.FORM_FIELD_NAME = f"{self.name}-text"
        self.INPUT_ID = f"{self.name}-input"
        self.CONTAINER_ID = f"{self.name}-container"

    @property
    def DISPLAY_NAME(self):
        return self.name.title()

    @property
    def DB_TABLE_NAME(self):
        return self.name

    @property
    def TRAINING_PROMPT(self):
        return f"{self.name}.md"


class CrudCustomizer(BaseCrud):
    def __init__(self, table, plugin):
        self.plugin = plugin
        # Get pipulate_instance from plugin if it exists
        self.pipulate_instance = getattr(plugin, 'pipulate', None)

        super().__init__(
            name=plugin.name,
            table=table,
            toggle_field='done',
            sort_field='priority',
            pipulate_instance=self.pipulate_instance  # Pass it to BaseCrud
        )
        self.item_name_field = 'text'
        logger.debug(f"{self.plugin.DISPLAY_NAME}App initialized with table name: {table.name}")

    def render_item(self, item):
        logger.debug(f"{self.plugin.DISPLAY_NAME}App.render_item called for: {item}")
        return render_item(item, self)

    def prepare_insert_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            logger.warning(f"Attempted to insert {self.plugin.name} with empty text.")
            return None

        current_profile_id = self.plugin.db_dictlike.get("last_profile_id", 1)
        logger.debug(f"Using profile_id: {current_profile_id} for new {self.plugin.name}")

        # If this is one of our predefined roles, use its specific priority
        if text in ROLE_ORDER:
            priority = ROLE_ORDER[text]
        else:
            # For any other roles, add them after the predefined ones
            items_for_profile = self.table("profile_id = ?", [current_profile_id])
            max_priority = max((i.priority or 0 for i in items_for_profile), default=4) + 1
            priority = int(form.get(f"{self.plugin.name}_priority", max_priority))

        insert_data = {
            "text": text,
            "done": text in ["Core", "Botify Employee"],  # Set done=True for both Core and Botify Employee roles
            "priority": priority,
            "profile_id": current_profile_id,
        }
        logger.debug(f"Prepared insert data: {insert_data}")
        return insert_data

    def prepare_update_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            logger.warning(f"Attempted to update {self.plugin.name} with empty text.")
            return None

        update_data = {
            "text": text,
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data


class CrudUI(PluginIdentityManager):
    @property
    def ENDPOINT_MESSAGE(self):
        return f"Manage your {self.DISPLAY_NAME.lower()} list here. Add, edit, sort, and mark items as complete."

    def __init__(self, app, pipulate, pipeline, db_dictlike):
        """Initialize the List Plugin."""
        super().__init__()
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike

        logger.debug(f"{self.DISPLAY_NAME} Plugin initializing...")

        db_path = os.path.join(os.path.dirname(__file__), "..", DB_FILENAME)
        logger.debug(f"Using database path: {db_path}")

        self.plugin_db = fastlite.database(db_path)

        schema = {
            "id": int,
            "text": str,
            "done": bool,
            "priority": int,
            "profile_id": int,
            "pk": "id"
        }
        schema_fields = {k: v for k, v in schema.items() if k != 'pk'}
        primary_key = schema.get('pk')

        if not primary_key:
            logger.error("Primary key 'pk' must be defined in the schema dictionary!")
            raise ValueError("Schema dictionary must contain a 'pk' entry.")

        try:
            table_handle = self.plugin_db.t[self.DB_TABLE_NAME]
            logger.debug(f"Got potential table handle via .t accessor: {table_handle}")

            self.table = table_handle.create(
                **schema_fields,
                pk=primary_key,
                if_not_exists=True
            )
            logger.info(f"Fastlite '{self.DB_TABLE_NAME}' table created or accessed via handle: {self.table}")

            self.table.dataclass()
            logger.info(f"Called .dataclass() on table handle to enable dataclass returns.")

        except Exception as e:
            logger.error(f"Error creating/accessing '{self.DB_TABLE_NAME}' table: {e}")
            raise

        self.app_instance = CrudCustomizer(table=self.table, plugin=self)
        logger.debug(f"{self.DISPLAY_NAME}App instance created.")

        self.register_plugin_routes()
        logger.debug(f"{self.DISPLAY_NAME} Plugin initialized successfully.")

        # Check if roles need initialization for the current profile
        current_profile_id = self.db_dictlike.get("last_profile_id", 1)
        self.ensure_roles_initialized(current_profile_id)

    def ensure_roles_initialized(self, profile_id):
        """Check if roles exist for the profile and initialize if needed."""
        existing_roles = list(self.table("profile_id = ?", [profile_id]))
        
        # If no roles exist for this profile, initialize them
        if not existing_roles:
            self.initialize_roles(profile_id)
            return

        # Check if all predefined roles exist
        existing_role_names = {role.text for role in existing_roles}
        missing_roles = set(ROLE_ORDER.keys()) - existing_role_names

        # If any predefined roles are missing, initialize them
        if missing_roles:
            self.initialize_roles(profile_id)

    def initialize_roles(self, profile_id):
        """Initialize roles in the correct order, resetting states to defaults."""
        # Get existing roles and their states
        existing_roles = {role.text: role for role in self.table("profile_id = ?", [profile_id])}

        # Sort roles by their priority value to ensure correct insertion order
        sorted_roles = sorted(ROLE_ORDER.items(), key=lambda x: x[1])

        # Insert or update roles in the desired order
        for role_name, priority in sorted_roles:
            if role_name in existing_roles:
                # Update both priority and done state
                existing_role = existing_roles[role_name]
                existing_role.priority = priority
                existing_role.done = (role_name in ['Core', 'Botify Employee'])  # Reset done state to default
                self.table.update(existing_role)
            else:
                # Insert new role with default state
                self.table.insert(
                    text=role_name,
                    done=(role_name in ['Core', 'Botify Employee']),  # Set both Core and Botify Employee to done=True
                    priority=priority,
                    profile_id=profile_id
                )
        logger.debug(f"Initialized roles for profile {profile_id}")

    def register_plugin_routes(self):
        """Register routes manually using app.route."""
        prefix = self.ENDPOINT_PREFIX
        sort_path = f"{prefix}_sort"

        routes_to_register = [
            (f'{prefix}/toggle/{{item_id:int}}', self.app_instance.toggle_item, ['POST']),
            (sort_path, self.app_instance.sort_items, ['POST']),
        ]

        logger.debug(f"Registering routes for {self.name} plugin:")
        for path, handler, methods in routes_to_register:
            func = handler
            self.app.route(path, methods=methods)(func)
            logger.debug(f"  Registered: {methods} {path} -> {handler.__name__}")

    async def landing(self, request=None):
        """Renders the main view for the plugin."""
        logger.debug(f"{self.DISPLAY_NAME}Plugin.landing called")
        current_profile_id = self.db_dictlike.get("last_profile_id", 1)
        logger.debug(f"Landing page using profile_id: {current_profile_id}")

        items_query = self.table(where=f"profile_id = {current_profile_id}")
        # Sort items by their current priority, preserving user's custom order
        items = sorted(items_query, key=lambda item: float(item.priority or 0) if isinstance(item.priority, (int, float, str)) else float('inf'))
        logger.debug(f"Found {len(items)} {self.name} for profile {current_profile_id}")

        return Div(
            Card(
                H2(f"{self.DISPLAY_NAME} List"),
                Ul(
                    *[self.app_instance.render_item(item) for item in items],
                    id=self.LIST_ID,
                    cls='sortable',
                    style="padding-left: 0;"
                )
            ),
            id=self.CONTAINER_ID,
            style="display: flex; flex-direction: column;"
        )

    async def render(self, render_items=None):
        """Fallback render method, currently just calls landing."""
        logger.debug(f"{self.DISPLAY_NAME}Plugin.render called, delegating to landing.")
        return await self.landing()


def render_item(item, app_instance):
    """Renders a single item as an LI element with plugin visibility information."""
    item_id = f'{app_instance.name}-{item.id}'
    logger.debug(f"Rendering {app_instance.plugin.name} ID {item.id} with text '{item.text}'")

    toggle_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/toggle/{item.id}"

    # Special handling for "Core" item
    is_core = item.text == "Core"
    checkbox = Input(
        type="checkbox",
        name="done_status" if item.done else None,
        checked=True if is_core else item.done,  # Always checked for Core
        disabled=is_core,  # Disabled for Core
        hx_post=toggle_url if not is_core else None,  # No toggle for Core
        hx_swap="outerHTML",
        hx_target=f"#{item_id}",
    )

    text_display = Span(
        item.text,
        id=f"{app_instance.name}-text-display-{item.id}",
        style="margin-left: 5px; font-weight: 500;"
    )

    # Create plugin visibility information
    plugin_info = create_plugin_visibility_table(item.text)

    return Li(
        # Main role item with checkbox and name
        Div(
            checkbox,
            text_display,
            style="display: flex; align-items: center; margin-bottom: 0.25rem;"
        ),
        # Plugin visibility information below
        plugin_info,
        id=item_id,
        cls='done' if item.done or is_core else '',  # Always marked as done for Core
        style="list-style-type: none; margin-bottom: 0.5rem; padding: 0.25rem; border-radius: 0.25rem; background-color: var(--pico-card-background-color); border: 1px solid var(--pico-muted-border-color);",
        data_id=item.id,
        data_priority=item.priority,
        data_plugin_item="true",
        data_list_target=app_instance.plugin.LIST_ID,
        data_endpoint_prefix=app_instance.plugin.ENDPOINT_PREFIX
    )

def get_plugin_list():
    """Get list of all available plugins with their prefixes."""
    plugins_dir = os.path.join(os.path.dirname(__file__))
    plugins = []
    
    if os.path.isdir(plugins_dir):
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                # Skip experimental plugins
                if filename.lower().startswith('xx_') or '(' in filename:
                    continue
                    
                # Extract numeric prefix
                match = re.match(r'^(\d+)_(.+)\.py$', filename)
                if match:
                    prefix = int(match.group(1))
                    name = match.group(2).replace('_', ' ').title()
                    plugins.append((prefix, name))
                    
    return sorted(plugins)

def get_affected_plugins(role_name):
    """Get plugins that would be shown/hidden for a given role."""
    if role_name not in ROLE_PLUGIN_MAPPING:
        return [], [], "Unknown role"
    
    role_config = ROLE_PLUGIN_MAPPING[role_name]
    show_ranges = role_config['show']
    description = role_config['description']
    
    all_plugins = get_plugin_list()
    shown_plugins = []
    hidden_plugins = []
    
    for prefix, name in all_plugins:
        is_shown = False
        for start, end in show_ranges:
            if start <= prefix <= end:
                is_shown = True
                break
        
        if is_shown:
            shown_plugins.append((prefix, name))
        else:
            hidden_plugins.append((prefix, name))
    
    return shown_plugins, hidden_plugins, description

def create_plugin_visibility_table(role_name):
    """Create a simple summary showing which plugins this role provides access to."""
    shown_plugins, hidden_plugins, description = get_affected_plugins(role_name)
    
    if not shown_plugins:
        return Small(f"📋 No plugins available", style="color: var(--pico-muted-color); font-style: italic; font-size: 0.8rem;")
    
    shown_count = len(shown_plugins)
    
    # Create the plugin list
    def format_all_plugins(plugins):
        return ", ".join([f"{name}" for prefix, name in plugins])
    
    return Details(
        Summary(
            Small(
                f"📋 {shown_count} plugins available",
                style="color: var(--pico-muted-color); font-size: 0.75rem; cursor: pointer;"
            ),
            style="margin: 0; padding: 0; list-style: none;"
        ),
        Div(
            Small(format_all_plugins(shown_plugins), style="color: var(--pico-muted-color); font-size: 0.75rem; line-height: 1.3;"),
            style="padding: 0.5rem; background-color: var(--pico-card-background-color); border-radius: 0.25rem; margin-top: 0.25rem; border-left: 2px solid var(--pico-color-azure-500);"
        ),
        style="margin: 0;"
    )
