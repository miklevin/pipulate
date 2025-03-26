# plugins/competitor_plugin.py

import os
import inspect
from loguru import logger
from fasthtml.common import *
import fastlite

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import BaseApp, db as server_db, priority_key, LIST_SUFFIX, DB_FILENAME

# --- Define the App Logic Class (inherits from BaseApp) ---
class CompetitorApp(BaseApp):
    def __init__(self, table):
        # Initialize BaseApp with specific names and fields for competitors
        super().__init__(name='competitor', table=table, toggle_field='done', sort_field='priority')
        self.item_name_field = 'name'
        logger.debug(f"CompetitorApp initialized with table name: {table.name}")

    def render_item(self, competitor):
        # This method will call the specific rendering function for a competitor item
        logger.debug(f"CompetitorApp.render_item called for: {competitor}")
        # Pass 'self' (the CompetitorApp instance) to the render function
        return render_competitor(competitor, self)

    def prepare_insert_data(self, form):
        # Prepare data for inserting a new competitor
        name = form.get('competitor_name', form.get('name', '')).strip()
        if not name:
            logger.warning("Attempted to insert competitor with empty name.")
            return None

        current_profile_id = server_db.get("last_profile_id", 1)
        logger.debug(f"Using profile_id: {current_profile_id} for new competitor")

        # Query competitors for current profile using MiniDataAPI pattern
        competitors_for_profile = self.table("profile_id = ?", [current_profile_id])
        max_priority = max((c.priority or 0 for c in competitors_for_profile), default=-1) + 1
        priority = int(form.get('competitor_priority', max_priority))

        insert_data = {
            "name": name,
            "done": False,
            "priority": priority,
            "profile_id": current_profile_id,
        }
        logger.debug(f"Prepared insert data: {insert_data}")
        return insert_data

    def prepare_update_data(self, form):
        # Prepare data for updating an existing competitor
        name = form.get('competitor_name', form.get('name', '')).strip() # Allow updating name
        if not name:
             logger.warning("Attempted to update competitor with empty name.")
             return None # Don't allow empty name update

        # You might add other fields here if needed for updates
        update_data = {
            "name": name,
            # Example: Allow updating 'done' status if needed via form
            # "done": form.get('done', '').lower() == 'true',
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data

# --- Define the Rendering Function ---
def render_competitor(competitor, app_instance: CompetitorApp):
    """Renders a single competitor item as an LI element."""
    cid = f'competitor-{competitor.id}'
    logger.debug(f"Rendering competitor ID {competitor.id} with name '{competitor.name}'")

    # Use the app_instance passed in to generate correct URLs
    delete_url = app_instance.get_action_url('delete', competitor.id) # e.g., /competitor/delete/1
    toggle_url = app_instance.get_action_url('toggle', competitor.id) # e.g., /competitor/toggle/1
    update_url = f"/{app_instance.name}/{competitor.id}"             # e.g., /competitor/1

    checkbox = Input(
        type="checkbox",
        name="done_status" if competitor.done else None, # Use a unique name if needed
        checked=competitor.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{cid}",
    )

    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{cid}",
        style="cursor: pointer; display: inline; margin-left: 5px;", # Added margin
        cls="delete-icon"
    )

    # Use competitor_name_{id} for unique IDs if needed
    update_input_id = f"competitor_name_{competitor.id}"

    name_display = Span( # Changed A to Span for non-clickable display initially
        competitor.name,
        id=f"competitor-name-display-{competitor.id}", # Unique ID for display span
        style="margin-left: 5px; cursor: pointer;", # Make it look clickable
         # JS to hide display, show form
        onclick=(
            f"document.getElementById('competitor-name-display-{competitor.id}').style.display='none'; "
            f"document.getElementById('update-form-{competitor.id}').style.display='inline-flex'; "
            f"document.getElementById('{update_input_id}').focus();"
        )
    )

    update_form = Form(
        Group( # Using Group for inline layout
            Input(
                type="text",
                id=update_input_id,
                value=competitor.name,
                name="competitor_name", # Use the name expected by prepare_update_data
                style="flex-grow: 1; margin-right: 5px; margin-bottom: 0;", # Adjusted styles
            ),
            Button("Save", type="submit", style="margin-bottom: 0;"), # Adjusted styles
            Button("Cancel", type="button", style="margin-bottom: 0;", cls="secondary",
                   # JS to hide form, show display
                   onclick=(
                       f"document.getElementById('update-form-{competitor.id}').style.display='none'; "
                       f"document.getElementById('competitor-name-display-{competitor.id}').style.display='inline';"
                   )),
            style="align-items: center;" # Align items in the group
        ),
        style="display: none; margin-left: 5px;", # Hidden initially, inline-flex later
        id=f"update-form-{competitor.id}", # Unique ID for the form
        hx_post=update_url,
        hx_target=f"#{cid}",
        hx_swap="outerHTML",
    )

    return Li(
        checkbox,
        name_display, # Show the name span
        update_form,  # Include the hidden update form
        delete_icon,
        id=cid,
        cls='done' if competitor.done else '',
        style="list-style-type: none; display: flex; align-items: center; margin-bottom: 5px;", # Flex layout
        data_id=competitor.id,
        data_priority=competitor.priority
    )


# --- Define the Plugin Wrapper ---
class CompetitorPlugin:
    NAME = "competitor"
    DISPLAY_NAME = "Competitors"
    ENDPOINT_MESSAGE = "Manage your list of competitors here. Add, edit, sort, and toggle their status."

    def __init__(self, app, pipulate, pipeline, db_dictlike):
        """Initialize the Competitor Plugin."""
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike
        logger.debug(f"{self.DISPLAY_NAME} Plugin initializing...")

        # Use the same DB_FILENAME from server.py
        db_path = os.path.join(os.path.dirname(__file__), "..", DB_FILENAME)
        logger.debug(f"Using database path: {db_path}")

        self.plugin_db = fastlite.database(db_path)

        # --- REVISED TABLE CREATION using Schema Dict + .dataclass() call ---
        competitor_schema = {
            "id": int,
            "name": str,
            "done": bool,
            "priority": int,
            "profile_id": int,
            "pk": "id"  # Primary key definition
        }
        schema_fields = {k: v for k, v in competitor_schema.items() if k != 'pk'}
        primary_key = competitor_schema.get('pk')

        if not primary_key:
            logger.error("Primary key 'pk' must be defined in the schema dictionary!")
            raise ValueError("Schema dictionary must contain a 'pk' entry.")

        try:
            # 1. Get table handle via .t accessor
            competitor_table_handle = self.plugin_db.t.competitor # Use 'competitor' as table name
            logger.debug(f"Got potential table handle via .t accessor: {competitor_table_handle}")

            # 2. Create the table *ONLY IF IT DOES NOT EXIST* using the handle
            self.competitors_table = competitor_table_handle.create(
                **schema_fields,
                pk=primary_key,
                if_not_exists=True
            )
            logger.info(f"Fastlite 'competitor' table created or accessed via handle: {self.competitors_table}")

            # 3. *** ACTIVATE DATACLASS RETURNS for this handle ***
            # We don't need to store the result, just call it.
            self.competitors_table.dataclass()
            logger.info(f"Called .dataclass() on table handle to enable dataclass returns.")

        except Exception as e:
            logger.error(f"Error creating/accessing 'competitor' table: {e}")
            raise

        # Instantiate the actual CompetitorApp logic class, passing the table handle
        self.competitor_app_instance = CompetitorApp(table=self.competitors_table)
        logger.debug(f"CompetitorApp instance created.")

        self.register_plugin_routes()
        logger.debug(f"{self.DISPLAY_NAME} Plugin initialized successfully.")

    def register_plugin_routes(self):
        """Register routes manually using app.route, bypassing BaseApp's rt logic."""
        prefix = f"/{self.competitor_app_instance.name}" # /competitor

        # Determine the sort path based on the BaseApp pattern
        sort_path = f"/{self.competitor_app_instance.name}/sort" # e.g., /competitor_sort

        routes_to_register = [
            (f'{prefix}', self.competitor_app_instance.insert_item, ['POST']),
            (f'{prefix}/{{item_id:int}}', self.competitor_app_instance.update_item, ['POST']),
            (f'{prefix}/delete/{{item_id:int}}', self.competitor_app_instance.delete_item, ['DELETE']),
            (f'{prefix}/toggle/{{item_id:int}}', self.competitor_app_instance.toggle_item, ['POST']),
            (sort_path, self.competitor_app_instance.sort_items, ['POST']),
        ]

        logger.debug(f"Registering routes for {self.NAME} plugin:")
        for path, handler, methods in routes_to_register:
            func = handler
            self.app.route(path, methods=methods)(func)
            logger.debug(f"  Registered: {methods} {path} -> {handler.__name__}")

    async def landing(self, request=None):
        """Renders the main view for the Competitor plugin."""
        logger.debug(f"CompetitorPlugin.landing called")
        app_name = self.NAME
        current_profile_id = self.db_dictlike.get("last_profile_id", 1)
        logger.debug(f"Landing page using profile_id: {current_profile_id}")

        competitor_items_query = self.competitors_table(where=f"profile_id = {current_profile_id}")
        competitor_items = sorted(competitor_items_query, key=priority_key)
        logger.debug(f"Found {len(competitor_items)} competitors for profile {current_profile_id}")

        add_placeholder = f'Add new {self.DISPLAY_NAME[:-1]}'

        return Div(
            Card(
                H2(f"{self.DISPLAY_NAME} {LIST_SUFFIX}"),
                Ul(
                    *[self.competitor_app_instance.render_item(item) for item in competitor_items],
                    id=f'{app_name}-list',
                    cls='sortable',
                    style="padding-left: 0;"
                ),
                header=Form(
                    Group(
                        Input(
                            placeholder=add_placeholder,
                            id=f'{app_name}-name-input',
                            name='competitor_name',
                            autofocus=True
                        ),
                        Button("Add", type="submit")
                    ),
                    hx_post=f"/{app_name}",
                    hx_swap="beforeend",
                    hx_target=f"#{app_name}-list"
                )
            ),
            id=f"{app_name}-content-container",
            style="display: flex; flex-direction: column;"
        )

    async def render(self, render_items=None):
         """Fallback render method, currently just calls landing."""
         logger.debug(f"CompetitorPlugin.render called, delegating to landing.")
         # For workflows, render might be different, but for CRUD, landing is the main view
         return await self.landing()

# No registration needed here - server.py discovery will find CompetitorPlugin