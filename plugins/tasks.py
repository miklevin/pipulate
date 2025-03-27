# Rename file to create a generic list plugin (e.g. tasks.py, competitors.py)

import os
import inspect
from loguru import logger
from fasthtml.common import *
import fastlite

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import BaseApp, db as server_db, priority_key, LIST_SUFFIX, DB_FILENAME

class BasePlugin:
    """Base class providing dynamic naming for plugins."""
    def __init__(self, filename=None):
        # Get filename if not provided
        if not filename:
            filename = os.path.basename(__file__)
            
        # Strip .py extension to get the base name
        self.name = filename.replace('.py', '')
        
        # Use the name directly for all endpoints - no singular conversion
        self.ENDPOINT_PREFIX = f"/{self.name}"
        
        # Keep singular reference only for display/naming purposes if needed
        self.singular = self.name.rstrip('s')
        
        # Other naming constants
        self.LIST_ID = f"{self.name}-list"
        self.ITEM_CLASS = f"{self.singular}-item"  # Keep singular for CSS classes
        self.FORM_FIELD_NAME = f"{self.singular}-text"  # Keep singular for form fields
        self.INPUT_ID = f"{self.singular}-input"  # Keep singular for input IDs
        self.CONTAINER_ID = f"{self.name}-container"  # Use plural for container
        
    @property
    def DISPLAY_NAME(self):
        return self.name.title()
        
    @property
    def DISPLAY_NAME_SINGULAR(self):
        return self.singular.title()
        
    @property
    def DB_TABLE_NAME(self):
        return self.name

class AppLogic(BaseApp):
    def __init__(self, table, plugin):
        self.plugin = plugin
        super().__init__(
            name=plugin.name,
            table=table, 
            toggle_field='done',
            sort_field='priority'
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

        current_profile_id = server_db.get("last_profile_id", 1)
        logger.debug(f"Using profile_id: {current_profile_id} for new {self.plugin.name}")

        items_for_profile = self.table("profile_id = ?", [current_profile_id])
        max_priority = max((i.priority or 0 for i in items_for_profile), default=-1) + 1
        priority = int(form.get(f"{self.plugin.name}_priority", max_priority))

        insert_data = {
            "text": text,
            "done": False,
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

def render_item(item, app_instance):
    """Renders a single item as an LI element."""
    item_id = f'{app_instance.name}-{item.id}'
    logger.debug(f"Rendering {app_instance.plugin.name} ID {item.id} with text '{item.text}'")

    delete_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/delete/{item.id}"
    toggle_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/toggle/{item.id}"
    update_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/{item.id}"

    checkbox = Input(
        type="checkbox",
        name="done_status" if item.done else None,
        checked=item.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{item_id}",
    )

    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{item_id}",
        style="cursor: pointer; display: inline; margin-left: 5px; text-decoration: none;",
        cls="delete-icon"
    )

    update_input_id = f"{app_instance.name}_text_{item.id}"

    text_display = Span(
        item.text,
        id=f"{app_instance.name}-text-display-{item.id}",
        style="margin-left: 5px; cursor: pointer;",
        onclick=(
            f"document.getElementById('{app_instance.name}-text-display-{item.id}').style.display='none'; "
            f"document.getElementById('update-form-{item.id}').style.display='inline-flex'; "
            f"document.getElementById('{item_id}').style.alignItems='baseline'; "
            f"document.getElementById('{update_input_id}').focus();"
        )
    )

    update_form = Form(
        Group(
            Input(
                type="text",
                id=update_input_id,
                value=item.text,
                name=app_instance.plugin.FORM_FIELD_NAME,
                style="flex-grow: 1; margin-right: 5px; margin-bottom: 0;",
            ),
            Button("Save", type="submit", style="margin-bottom: 0;"),
            Button("Cancel", type="button", style="margin-bottom: 0;", cls="secondary",
                onclick=(
                    f"document.getElementById('update-form-{item.id}').style.display='none'; "
                    f"document.getElementById('{app_instance.name}-text-display-{item.id}').style.display='inline'; "
                    f"document.getElementById('{item_id}').style.alignItems='center';"
                )),
            style="align-items: center;"
        ),
        style="display: none; margin-left: 5px;",
        id=f"update-form-{item.id}",
        hx_post=update_url,
        hx_target=f"#{item_id}",
        hx_swap="outerHTML",
    )

    return Li(
        checkbox,
        text_display,
        update_form,
        delete_icon,
        id=item_id,
        cls='done' if item.done else '',
        style="list-style-type: none; display: flex; align-items: center; margin-bottom: 5px;",
        data_id=item.id,
        data_priority=item.priority,
        data_plugin_item="true",
        data_list_target=app_instance.plugin.LIST_ID,
        data_endpoint_prefix=app_instance.plugin.ENDPOINT_PREFIX
    )

class ListPlugin(BasePlugin):
    ENDPOINT_MESSAGE = "Manage your task list here. Add, edit, sort, and mark tasks as complete."

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

        self.app_instance = AppLogic(table=self.table, plugin=self)
        logger.debug(f"{self.DISPLAY_NAME}App instance created.")

        self.register_plugin_routes()
        logger.debug(f"{self.DISPLAY_NAME} Plugin initialized successfully.")

    def register_plugin_routes(self):
        """Register routes manually using app.route."""
        prefix = self.ENDPOINT_PREFIX
        sort_path = f"{prefix}/sort"

        routes_to_register = [
            (f'{prefix}', self.app_instance.insert_item, ['POST']),
            (f'{prefix}/{{item_id:int}}', self.app_instance.update_item, ['POST']), 
            (f'{prefix}/delete/{{item_id:int}}', self.app_instance.delete_item, ['DELETE']),
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
        items = sorted(items_query, key=priority_key)
        logger.debug(f"Found {len(items)} {self.name} for profile {current_profile_id}")

        add_placeholder = f"Add new {self.DISPLAY_NAME_SINGULAR.lower()}"

        return Div(
            Card(
                H2(f"{self.DISPLAY_NAME} {LIST_SUFFIX}"),
                Ul(
                    *[self.app_instance.render_item(item) for item in items],
                    id=self.LIST_ID,
                    cls='sortable',
                    style="padding-left: 0;"
                ),
                header=Form(
                    Group(
                        Input(
                            placeholder=add_placeholder,
                            id=self.INPUT_ID,
                            name=self.FORM_FIELD_NAME,
                            autofocus=True
                        ),
                        Button("Add", type="submit")
                    ),
                    hx_post=self.ENDPOINT_PREFIX,
                    hx_swap="beforeend",
                    hx_target=f"#{self.LIST_ID}",
                    hx_on__after_request="this.reset()"
                )
            ),
            id=self.CONTAINER_ID,
            style="display: flex; flex-direction: column;"
        )

    async def render(self, render_items=None):
        """Fallback render method, currently just calls landing."""
        logger.debug(f"{self.DISPLAY_NAME}Plugin.render called, delegating to landing.")
        return await self.landing()