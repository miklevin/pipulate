# plugins/tasks.py

import os
import inspect
from loguru import logger
from fasthtml.common import *
import fastlite

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import BaseApp, db as server_db, priority_key, LIST_SUFFIX, DB_FILENAME

# --- Define the App Logic Class (inherits from BaseApp) ---
class TaskApp(BaseApp):
    def __init__(self, table):
        # Initialize BaseApp with specific names and fields for tasks
        super().__init__(name='task', table=table, toggle_field='done', sort_field='priority')
        self.item_name_field = 'text'
        logger.debug(f"TaskApp initialized with table name: {table.name}")

    def render_item(self, task):
        # This method will call the specific rendering function for a task item
        logger.debug(f"TaskApp.render_item called for: {task}")
        # Pass 'self' (the TaskApp instance) to the render function
        return render_task(task, self)

    def prepare_insert_data(self, form):
        # Prepare data for inserting a new task
        text = form.get('task_text', form.get('text', '')).strip()
        if not text:
            logger.warning("Attempted to insert task with empty text.")
            return None

        current_profile_id = server_db.get("last_profile_id", 1)
        logger.debug(f"Using profile_id: {current_profile_id} for new task")

        # Query tasks for current profile using MiniDataAPI pattern
        tasks_for_profile = self.table("profile_id = ?", [current_profile_id])
        max_priority = max((t.priority or 0 for t in tasks_for_profile), default=-1) + 1
        priority = int(form.get('task_priority', max_priority))

        insert_data = {
            "text": text,
            "done": False,
            "priority": priority,
            "profile_id": current_profile_id,
        }
        logger.debug(f"Prepared insert data: {insert_data}")
        return insert_data

    def prepare_update_data(self, form):
        # Prepare data for updating an existing task
        text = form.get('task_text', form.get('text', '')).strip()
        if not text:
            logger.warning("Attempted to update task with empty text.")
            return None

        update_data = {
            "text": text,
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data

# --- Define the Rendering Function ---
def render_task(task, app_instance: TaskApp):
    """Renders a single task item as an LI element."""
    tid = f'{app_instance.name}-{task.id}'
    logger.debug(f"Rendering task ID {task.id} with text '{task.text}'")

    delete_url = app_instance.get_action_url('delete', task.id)
    toggle_url = app_instance.get_action_url('toggle', task.id)
    update_url = f"/{app_instance.name}/{task.id}"

    checkbox = Input(
        type="checkbox",
        name="done_status" if task.done else None,
        checked=task.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )

    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
        style="cursor: pointer; display: inline; margin-left: 5px; text-decoration: none;",
        cls="delete-icon"
    )

    update_input_id = f"{app_instance.name}_text_{task.id}"

    text_display = Span(
        task.text,
        id=f"{app_instance.name}-text-display-{task.id}",
        style="margin-left: 5px; cursor: pointer;",
        onclick=(
            f"document.getElementById('{app_instance.name}-text-display-{task.id}').style.display='none'; "
            f"document.getElementById('update-form-{task.id}').style.display='inline-flex'; "
            f"document.getElementById('{tid}').style.alignItems='baseline'; "
            f"document.getElementById('{update_input_id}').focus();"
        )
    )

    update_form = Form(
        Group(
            Input(
                type="text",
                id=update_input_id,
                value=task.text,
                name="task_text",
                style="flex-grow: 1; margin-right: 5px; margin-bottom: 0;",
            ),
            Button("Save", type="submit", style="margin-bottom: 0;"),
            Button("Cancel", type="button", style="margin-bottom: 0;", cls="secondary",
                onclick=(
                    f"document.getElementById('update-form-{task.id}').style.display='none'; "
                    f"document.getElementById('{app_instance.name}-text-display-{task.id}').style.display='inline'; "
                    f"document.getElementById('{tid}').style.alignItems='center';"
                )),
            style="align-items: center;"
        ),
        style="display: none; margin-left: 5px;",
        id=f"update-form-{task.id}",
        hx_post=update_url,
        hx_target=f"#{tid}",
        hx_swap="outerHTML",
    )

    return Li(
        checkbox,
        text_display,
        update_form,
        delete_icon,
        id=tid,
        cls='done' if task.done else '',
        style="list-style-type: none; display: flex; align-items: center; margin-bottom: 5px;",
        data_id=task.id,
        data_priority=task.priority,
        data_plugin_item="true",
        data_list_target=f"{app_instance.name}-list"
    )

# --- Define the Plugin Wrapper ---
class TasksPlugin:
    NAME = os.path.splitext(os.path.basename(__file__))[0]  # Dynamically gets "tasks"
    DISPLAY_NAME = "Tasks"  # Human-readable name
    DB_TABLE_NAME = "task"  # Database table name
    ENDPOINT_MESSAGE = "Manage your task list here. Add, edit, sort, and mark tasks as complete."

    def __init__(self, app, pipulate, pipeline, db_dictlike):
        """Initialize the Tasks Plugin."""
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike
        
        # Generate consistent IDs based on NAME
        self.LIST_ID = f"{self.NAME}-list"
        self.CONTAINER_ID = f"{self.NAME}-content-container"
        self.INPUT_ID = f"{self.NAME}-name-input"
        
        logger.debug(f"{self.DISPLAY_NAME} Plugin initializing...")

        db_path = os.path.join(os.path.dirname(__file__), "..", DB_FILENAME)
        logger.debug(f"Using database path: {db_path}")

        self.plugin_db = fastlite.database(db_path)

        task_schema = {
            "id": int,
            "text": str,
            "done": bool,
            "priority": int,
            "profile_id": int,
            "pk": "id"
        }
        schema_fields = {k: v for k, v in task_schema.items() if k != 'pk'}
        primary_key = task_schema.get('pk')

        if not primary_key:
            logger.error("Primary key 'pk' must be defined in the schema dictionary!")
            raise ValueError("Schema dictionary must contain a 'pk' entry.")

        try:
            task_table_handle = self.plugin_db.t[self.DB_TABLE_NAME]
            logger.debug(f"Got potential table handle via .t accessor: {task_table_handle}")

            self.tasks_table = task_table_handle.create(
                **schema_fields,
                pk=primary_key,
                if_not_exists=True
            )
            logger.info(f"Fastlite '{self.DB_TABLE_NAME}' table created or accessed via handle: {self.tasks_table}")

            self.tasks_table.dataclass()
            logger.info(f"Called .dataclass() on table handle to enable dataclass returns.")

        except Exception as e:
            logger.error(f"Error creating/accessing '{self.DB_TABLE_NAME}' table: {e}")
            raise

        self.task_app_instance = TaskApp(table=self.tasks_table)
        logger.debug(f"TaskApp instance created.")

        self.register_plugin_routes()
        logger.debug(f"{self.DISPLAY_NAME} Plugin initialized successfully.")

    def register_plugin_routes(self):
        """Register routes manually using app.route."""
        prefix = f"/{self.NAME}"
        sort_path = f"{prefix}/sort"

        routes_to_register = [
            (f'{prefix}', self.task_app_instance.insert_item, ['POST']),
            (f'{prefix}/{{item_id:int}}', self.task_app_instance.update_item, ['POST']), 
            (f'{prefix}/delete/{{item_id:int}}', self.task_app_instance.delete_item, ['DELETE']),
            (f'{prefix}/toggle/{{item_id:int}}', self.task_app_instance.toggle_item, ['POST']),
            (sort_path, self.task_app_instance.sort_items, ['POST']),
        ]

        logger.debug(f"Registering routes for {self.NAME} plugin:")
        for path, handler, methods in routes_to_register:
            func = handler
            self.app.route(path, methods=methods)(func)
            logger.debug(f"  Registered: {methods} {path} -> {handler.__name__}")

    async def landing(self, request=None):
        """Renders the main view for the Tasks plugin."""
        logger.debug(f"TasksPlugin.landing called")
        current_profile_id = self.db_dictlike.get("last_profile_id", 1)
        logger.debug(f"Landing page using profile_id: {current_profile_id}")

        task_items_query = self.tasks_table(where=f"profile_id = {current_profile_id}")
        task_items = sorted(task_items_query, key=priority_key)
        logger.debug(f"Found {len(task_items)} tasks for profile {current_profile_id}")

        add_placeholder = f"Add new {self.DISPLAY_NAME[:-1].lower()}"

        return Div(
            Card(
                H2(f"{self.DISPLAY_NAME} {LIST_SUFFIX}"),
                Ul(
                    *[self.task_app_instance.render_item(item) for item in task_items],
                    id=self.LIST_ID,
                    cls='sortable',
                    style="padding-left: 0;"
                ),
                header=Form(
                    Group(
                        Input(
                            placeholder=add_placeholder,
                            id=self.INPUT_ID,
                            name='task_text',
                            autofocus=True
                        ),
                        Button("Add", type="submit")
                    ),
                    hx_post=f"/{self.NAME}",
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
        logger.debug(f"TasksPlugin.render called, delegating to landing.")
        return await self.landing()