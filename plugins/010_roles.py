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
    """Renders a single item as an LI element."""
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
        style="margin-left: 5px;"
    )

    return Li(
        checkbox,
        text_display,
        id=item_id,
        cls='done' if item.done or is_core else '',  # Always marked as done for Core
        style="list-style-type: none; display: flex; align-items: center; margin-bottom: 5px;",
        data_id=item.id,
        data_priority=item.priority,
        data_plugin_item="true",
        data_list_target=app_instance.plugin.LIST_ID,
        data_endpoint_prefix=app_instance.plugin.ENDPOINT_PREFIX
    )
