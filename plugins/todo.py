# plugins/todo.py

import os
import inspect
from loguru import logger
from fasthtml.common import *
import fastlite

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import BaseApp, db as server_db, priority_key, LIST_SUFFIX, DB_FILENAME

# --- Define the App Logic Class (inherits from BaseApp) ---
class TodoApp(BaseApp):
    def __init__(self, table):
        # Initialize BaseApp with specific names and fields for todos
        super().__init__(name='todo', table=table, toggle_field='done', sort_field='priority')
        self.item_name_field = 'text'
        logger.debug(f"TodoApp initialized with table name: {table.name}")

    def render_item(self, todo):
        # This method will call the specific rendering function for a todo item
        logger.debug(f"TodoApp.render_item called for: {todo}")
        # Pass 'self' (the TodoApp instance) to the render function
        return render_todo(todo, self)

    def prepare_insert_data(self, form):
        # Prepare data for inserting a new todo
        text = form.get('task_text', form.get('text', '')).strip()
        if not text:
            logger.warning("Attempted to insert todo with empty text.")
            return None

        current_profile_id = server_db.get("last_profile_id", 1)
        logger.debug(f"Using profile_id: {current_profile_id} for new todo")

        # Query todos for current profile using MiniDataAPI pattern
        todos_for_profile = self.table("profile_id = ?", [current_profile_id])
        max_priority = max((t.priority or 0 for t in todos_for_profile), default=-1) + 1
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
        # Prepare data for updating an existing todo
        text = form.get('task_text', form.get('text', '')).strip()
        if not text:
            logger.warning("Attempted to update todo with empty text.")
            return None

        update_data = {
            "text": text,
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data

# --- Define the Rendering Function ---
def render_todo(todo, app_instance: TodoApp):
    """Renders a single todo item as an LI element."""
    tid = f'task-{todo.id}'
    logger.debug(f"Rendering todo ID {todo.id} with text '{todo.text}'")

    delete_url = app_instance.get_action_url('delete', todo.id)
    toggle_url = app_instance.get_action_url('toggle', todo.id)
    update_url = f"/{app_instance.name}/{todo.id}"

    checkbox = Input(
        type="checkbox",
        name="done_status" if todo.done else None,
        checked=todo.done,
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

    update_input_id = f"task_text_{todo.id}"

    text_display = Span(
        todo.text,
        id=f"task-text-display-{todo.id}",
        style="margin-left: 5px; cursor: pointer;",
        onclick=(
            f"document.getElementById('task-text-display-{todo.id}').style.display='none'; "
            f"document.getElementById('update-form-{todo.id}').style.display='inline-flex'; "
            f"document.getElementById('{tid}').style.alignItems='baseline'; "
            f"document.getElementById('{update_input_id}').focus();"
        )
    )

    update_form = Form(
        Group(
            Input(
                type="text",
                id=update_input_id,
                value=todo.text,
                name="task_text",
                style="flex-grow: 1; margin-right: 5px; margin-bottom: 0;",
            ),
            Button("Save", type="submit", style="margin-bottom: 0;"),
            Button("Cancel", type="button", style="margin-bottom: 0;", cls="secondary",
                onclick=(
                    f"document.getElementById('update-form-{todo.id}').style.display='none'; "
                    f"document.getElementById('task-text-display-{todo.id}').style.display='inline'; "
                    f"document.getElementById('{tid}').style.alignItems='center';"
                )),
            style="align-items: center;"
        ),
        style="display: none; margin-left: 5px;",
        id=f"update-form-{todo.id}",
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
        cls='done' if todo.done else '',
        style="list-style-type: none; display: flex; align-items: center; margin-bottom: 5px;",
        data_id=todo.id,
        data_priority=todo.priority
    )

# --- Define the Plugin Wrapper ---
class TodoPlugin:
    NAME = "todo"
    DISPLAY_NAME = "Tasks"
    ENDPOINT_MESSAGE = "Manage your todo list here. Add, edit, sort, and mark tasks as complete."

    def __init__(self, app, pipulate, pipeline, db_dictlike):
        """Initialize the Todo Plugin."""
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike
        logger.debug(f"{self.DISPLAY_NAME} Plugin initializing...")

        db_path = os.path.join(os.path.dirname(__file__), "..", DB_FILENAME)
        logger.debug(f"Using database path: {db_path}")

        self.plugin_db = fastlite.database(db_path)

        todo_schema = {
            "id": int,
            "text": str,
            "done": bool,
            "priority": int,
            "profile_id": int,
            "pk": "id"
        }
        schema_fields = {k: v for k, v in todo_schema.items() if k != 'pk'}
        primary_key = todo_schema.get('pk')

        if not primary_key:
            logger.error("Primary key 'pk' must be defined in the schema dictionary!")
            raise ValueError("Schema dictionary must contain a 'pk' entry.")

        try:
            task_table_handle = self.plugin_db.t.task
            logger.debug(f"Got potential table handle via .t accessor: {task_table_handle}")

            self.tasks_table = task_table_handle.create(
                **schema_fields,
                pk=primary_key,
                if_not_exists=True
            )
            logger.info(f"Fastlite 'task' table created or accessed via handle: {self.tasks_table}")

            self.tasks_table.dataclass()
            logger.info(f"Called .dataclass() on table handle to enable dataclass returns.")

        except Exception as e:
            logger.error(f"Error creating/accessing 'task' table: {e}")
            raise

        self.todo_app_instance = TodoApp(table=self.tasks_table)
        logger.debug(f"TodoApp instance created.")

        self.register_plugin_routes()
        logger.debug(f"{self.DISPLAY_NAME} Plugin initialized successfully.")

    def register_plugin_routes(self):
        """Register routes manually using app.route."""
        prefix = f"/{self.NAME}"  # Use self.NAME instead of self.todo_app_instance.name
        sort_path = f"{prefix}/sort"  # Consistent path construction

        routes_to_register = [
            (f'{prefix}', self.todo_app_instance.insert_item, ['POST']),
            (f'{prefix}/{{item_id:int}}', self.todo_app_instance.update_item, ['POST']), 
            (f'{prefix}/delete/{{item_id:int}}', self.todo_app_instance.delete_item, ['DELETE']),
            (f'{prefix}/toggle/{{item_id:int}}', self.todo_app_instance.toggle_item, ['POST']),
            (sort_path, self.todo_app_instance.sort_items, ['POST']),
        ]

        logger.debug(f"Registering routes for {self.NAME} plugin:")
        for path, handler, methods in routes_to_register:
            func = handler
            self.app.route(path, methods=methods)(func)
            logger.debug(f"  Registered: {methods} {path} -> {handler.__name__}")

    async def landing(self, request=None):
        """Renders the main view for the Todo plugin."""
        logger.debug(f"TodoPlugin.landing called")
        app_name = self.NAME
        current_profile_id = self.db_dictlike.get("last_profile_id", 1)
        logger.debug(f"Landing page using profile_id: {current_profile_id}")

        todo_items_query = self.tasks_table(where=f"profile_id = {current_profile_id}")
        todo_items = sorted(todo_items_query, key=priority_key)
        logger.debug(f"Found {len(todo_items)} todos for profile {current_profile_id}")

        add_placeholder = "Add new task"

        return Div(
            Card(
                H2(f"{self.DISPLAY_NAME} {LIST_SUFFIX}"),
                Ul(
                    *[self.todo_app_instance.render_item(item) for item in todo_items],
                    id=f'{app_name}-list',
                    cls='sortable',
                    style="padding-left: 0;"
                ),
                header=Form(
                    Group(
                        Input(
                            placeholder=add_placeholder,
                            id=f'{app_name}-name-input',
                            name='task_text',
                            autofocus=True
                        ),
                        Button("Add", type="submit")
                    ),
                    hx_post=f"/{app_name}",
                    hx_swap="beforeend",
                    hx_target=f"#{app_name}-list",
                    hx_on__after_request="this.reset()"
                )
            ),
            id=f"{app_name}-content-container",
            style="display: flex; flex-direction: column;"
        )

    async def render(self, render_items=None):
        """Fallback render method, currently just calls landing."""
        logger.debug(f"TodoPlugin.render called, delegating to landing.")
        return await self.landing()