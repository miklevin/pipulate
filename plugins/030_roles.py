# Rename file to create a generic list plugin (e.g. tasks.py, competitors.py)

import importlib.util
import inspect
import os
import re
import sys
import fastlite
from fasthtml.common import *
from loguru import logger
from server import DB_FILENAME, BaseCrud, title_name

# ROLES constant is now used for discovery, not for defining the roles themselves.
ROLES = []

# Define the standard order of roles
ROLE_ORDER = {
    'Botify Employee': 0,
    'Core': 1,
    'Tutorial': 2,
    'Developer': 3,
    'Workshop': 4,
    'Components': 5,
}

# Plugin visibility is now determined by actual ROLES declarations in plugin files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class PluginIdentityManager:
    EMOJI = ''

    def __init__(self, filename=None):
        if not filename:
            filename = os.path.basename(__file__)
        self.original_name = filename.replace('.py', '')
        self.name = re.sub(r'^\d+_', '', self.original_name)
        self.ENDPOINT_PREFIX = f"/{self.name}"
        self.LIST_ID = f"{self.name}-list"
        self.ITEM_CLASS = f"{self.name}-item"
        self.FORM_FIELD_NAME = f"{self.name}-text"
        self.INPUT_ID = f"{self.name}-input"
        self.CONTAINER_ID = f"{self.name}-container"

    @property

    def DISPLAY_NAME(self):
        name = title_name(self.name)
        if self.EMOJI:
            return f"{self.EMOJI} {name}"
        return name

    @property

    def DB_TABLE_NAME(self):
        return self.name

    @property

    def TRAINING_PROMPT(self):
        return f"{self.name}.md"

class CrudCustomizer(BaseCrud):
    def __init__(self, table, plugin):
        self.plugin = plugin
        self.pipulate_instance = getattr(plugin, 'pipulate', None)
        super().__init__(
            name=plugin.name, table=table, toggle_field='done',
            sort_field='priority', pipulate_instance=self.pipulate_instance
        )
        self.item_name_field = 'text'

    def render_item(self, item):
        return render_item(item, self)

    def prepare_insert_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            return None

        roles_config = self.plugin.config.get('ROLES_CONFIG', {})
        if text in roles_config:
            priority = roles_config[text].get('priority', 99)
        else:
            all_items = self.table()
            max_priority = max((i.priority or 0 for i in all_items), default=len(roles_config)) + 1
            priority = int(form.get(f"{self.plugin.name}_priority", max_priority))

        default_active = self.plugin.config.get('DEFAULT_ACTIVE_ROLES', set())
        insert_data = { "text": text, "done": text in default_active, "priority": priority }
        return insert_data

    def prepare_update_data(self, form):
        text = form.get(self.plugin.FORM_FIELD_NAME, '').strip()
        if not text:
            return None
        return {"text": text}

class CrudUI(PluginIdentityManager):
    EMOJI = '👥'

    @property

    def ENDPOINT_MESSAGE(self):
        return f"Welcome! Check Roles to add to APP menu. Drag-to-reorder. Expand to see apps. Or try chatting."

    def __init__(self, app, pipulate, pipeline, db_dictlike, config):
        """Initialize the Roles Plugin with injected configuration."""
        super().__init__()
        self.app = app
        self.pipulate = pipulate
        self.pipeline_table = pipeline
        self.db_dictlike = db_dictlike
        self.config = config  # Store the passed-in config from server.py

        # Use the passed-in config for UI constants
        self.UI_CONSTANTS = {
            'TYPOGRAPHY': {
                'SMALL_TEXT': '0.75rem',
                'TINY_TEXT': '0.8rem',
                'DESCRIPTION_TEXT': '0.9rem',
                'LINE_HEIGHT_COMPACT': '1.2',
                'LINE_HEIGHT_NORMAL': '1.3',
            },
            'SPACING': {
                'PLUGIN_ITEM_MARGIN': '0.1rem',
                'SECTION_MARGIN': '0.25rem',
                'CARD_MARGIN': '0.5rem',
                'CONTAINER_PADDING': '0.5rem',
                'DESCRIPTION_PADDING': '0.75rem',
                'LARGE_MARGIN': '1rem',
                'BORDER_RADIUS': '0.25rem',
                'BORDER_WIDTH': '3px',
            },
            'ROLE_COLORS': self.config.get('ROLE_COLORS', {}),
            'FALLBACK_COLORS': {
                'border': 'var(--pico-color-azure-500)',
                'background': 'var(--pico-card-background-color)'
            }
        }

        logger.debug(f"{self.DISPLAY_NAME} Plugin initializing...")

        db_path = os.path.join(os.path.dirname(__file__), "..", DB_FILENAME)
        logger.debug(f"Using database path: {db_path}")

        self.plugin_db = fastlite.database(db_path)

        schema = {
            "id": int,
            "text": str,
            "done": bool,
            "priority": int,
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

        # CRITICAL: Roles are global - initialize once for all profiles
        self.ensure_roles_initialized()

    def get_app_name(self):
        """Get the app name from app_name.txt file."""
        try:
            app_name_path = os.path.join(os.path.dirname(__file__), "..", "app_name.txt")
            with open(app_name_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return "Pipulate"  # Fallback to default name

    def ensure_roles_initialized(self):
        """Ensure all roles from config are initialized in the database."""
        try:
            existing_roles = {role.text: role for role in self.table()}
            roles_config = self.config.get('ROLES_CONFIG', {})
            default_active = self.config.get('DEFAULT_ACTIVE_ROLES', set())

            logger.debug(f"ROLES: Found {len(existing_roles)} existing roles in database.")
            logger.debug(f"ROLES: Found {len(roles_config)} roles in configuration.")

            for role_name, config_data in roles_config.items():
                if role_name not in existing_roles:
                    logger.info(f"ROLES: Creating missing role '{role_name}' with priority {config_data['priority']}")
                    self.table.insert(
                        text=role_name,
                        done=(role_name in default_active),
                        priority=config_data['priority']
                    )
                else:
                    logger.debug(f"ROLES: Role '{role_name}' already exists in database.")

            logger.info(f"ROLES: Role initialization complete.")

        except Exception as e:
            logger.error(f"ROLES: Error during role initialization: {e}")

    def initialize_roles(self):
        """Legacy method name for backward compatibility."""
        return self.ensure_roles_initialized()

    def register_plugin_routes(self):
        """Register the routes for the roles plugin."""
        prefix = self.ENDPOINT_PREFIX
        routes = [
            (f'{prefix}/toggle/{{item_id:int}}', self.app_instance.toggle_item, ['POST']),
            (f"{prefix}_sort", self.app_instance.sort_items, ['POST']),
            (f"{prefix}/select_all", self.select_all_roles, ['POST']),
            (f"{prefix}/deselect_all", self.deselect_all_roles, ['POST']),
            (f"{prefix}/select_default", self.select_default_roles, ['POST']),
        ]
        for path, handler, methods in routes:
            self.app.route(path, methods=methods)(handler)

    async def landing(self, request=None):
        """Render the main roles management interface."""
        items_query = self.table()
        roles_config = self.config.get('ROLES_CONFIG', {})
        items = sorted(items_query, key=lambda item: item.priority or 99)

        return Div(
            Style(self.generate_role_css()),
            Card(
                H2(f"{self.DISPLAY_NAME}"),
                H3(self.ENDPOINT_MESSAGE),
                P(
                    f"New to {self.get_app_name()}? Start with the ",
                    A("Introduction", href="/redirect/introduction", 
                      style="color: var(--pico-primary-color); text-decoration: underline; font-weight: 500;",
                      onmouseover="this.style.color = 'var(--pico-primary-hover)';",
                      onmouseout="this.style.color = 'var(--pico-primary-color)';"),
                    " for a guided overview. Chat not working? Optionally install ",
                    A("Ollama", 
                      Img(src='/static/feather/external-link.svg', 
                          alt='External link', 
                          style='width: 14px; height: 14px; margin-left: 0.25rem; vertical-align: middle; filter: brightness(0) invert(1);'),
                      href="https://ollama.com/", target="_blank",
                      style="color: var(--pico-primary-color); text-decoration: underline; font-weight: 500;",
                      onmouseover="this.style.color = 'var(--pico-primary-hover)';",
                      onmouseout="this.style.color = 'var(--pico-primary-color)';"),
                    style="margin-bottom: 1rem; color: var(--pico-muted-color); font-size: 0.9em;"
                ),
                Div(
                    Button(Img(src='/static/feather/rewind.svg', 
                              alt='Reset', 
                              style='width: 14px; height: 14px; margin-right: 0.25rem; filter: brightness(0) invert(1);'),
                           "Default", 
                           hx_post=f"{self.ENDPOINT_PREFIX}/select_default",
                           cls="secondary",
                           style="font-size: 0.8rem; padding: 0.25rem 0.5rem; display: flex; align-items: center;"),
                    Button(Img(src='/static/feather/check-square.svg', 
                              alt='Select all', 
                              style='width: 14px; height: 14px; margin-right: 0.25rem; filter: brightness(0) invert(1);'),
                           "Select ALL", 
                           hx_post=f"{self.ENDPOINT_PREFIX}/select_all",
                           cls="secondary",
                           style="font-size: 0.8rem; padding: 0.25rem 0.5rem; display: flex; align-items: center;"),
                    Button(Img(src='/static/feather/square.svg', 
                              alt='Deselect all', 
                              style='width: 14px; height: 14px; margin-right: 0.25rem; filter: brightness(0) invert(1);'),
                           "Deselect ALL", 
                           hx_post=f"{self.ENDPOINT_PREFIX}/deselect_all",
                           cls="secondary outline",
                           style="font-size: 0.8rem; padding: 0.25rem 0.5rem; display: flex; align-items: center;"),
                    Button(Img(src='/static/feather/chevrons-down.svg', 
                              alt='Expand all', 
                              style='width: 14px; height: 14px; margin-right: 0.25rem; filter: brightness(0) invert(1);'),
                           "Expand ALL", 
                           onclick=f"document.querySelectorAll('#{self.CONTAINER_ID} details').forEach(function(details) {{ details.open = true; }});",
                           cls="secondary",
                           style="font-size: 0.8rem; padding: 0.25rem 0.5rem; display: flex; align-items: center;"),
                    Button(Img(src='/static/feather/chevrons-up.svg', 
                              alt='Collapse all', 
                              style='width: 14px; height: 14px; margin-right: 0.25rem; filter: brightness(0) invert(1);'),
                           "Collapse ALL", 
                           onclick=f"document.querySelectorAll('#{self.CONTAINER_ID} details').forEach(function(details) {{ details.open = false; }});",
                           cls="secondary outline",
                           style="font-size: 0.8rem; padding: 0.25rem 0.5rem; display: flex; align-items: center;"),
                    style="margin-bottom: 0.5rem; display: flex; gap: 0.25rem; flex-wrap: wrap; justify-content: center;"
                ),
                Ol(
                    *[self.app_instance.render_item(item) for item in items],
                    id=self.LIST_ID, cls='sortable', style="padding-left: 1.5rem;",
                    hx_post=f"{self.ENDPOINT_PREFIX}_sort", hx_swap="none",
                    data_plugin_name=self.name
                )
            ),
            id=self.CONTAINER_ID,
        )

    async def render(self, render_items=None):
        """Render method for compatibility."""
        return await self.landing()

    async def select_all_roles(self, request):
        """Select all roles except Core (which is always selected)."""
        try:
            # Get all roles except Core
            all_roles = self.table()
            for role in all_roles:
                if role.text != "Core" and not role.done:
                    # Update using proper fastlite syntax
                    role.done = True
                    self.table.update(role)
            
            # Return HX-Refresh header to trigger full page reload
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response
        except Exception as e:
            logger.error(f"Error in select_all_roles: {e}")
            # Even on error, trigger page refresh to show current state
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response

    async def deselect_all_roles(self, request):
        """Deselect all roles except Core (which stays selected)."""  
        try:
            # Get all roles except Core
            all_roles = self.table()
            for role in all_roles:
                if role.text != "Core" and role.done:
                    # Update using proper fastlite syntax
                    role.done = False
                    self.table.update(role)
            
            # Return HX-Refresh header to trigger full page reload
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response
        except Exception as e:
            logger.error(f"Error in deselect_all_roles: {e}")
            # Even on error, trigger page refresh to show current state
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response

    async def select_default_roles(self, request):
        """Reset roles to DEFAULT_ACTIVE_ROLES configuration."""
        try:
            # Get the default active roles from config
            default_active = self.config.get('DEFAULT_ACTIVE_ROLES', set())
            
            # Update all roles based on default configuration
            all_roles = self.table()
            for role in all_roles:
                should_be_active = role.text in default_active
                if role.done != should_be_active:
                    role.done = should_be_active
                    self.table.update(role)
            
            # Return HX-Refresh header to trigger full page reload
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response
        except Exception as e:
            logger.error(f"Error in select_default_roles: {e}")
            # Even on error, trigger page refresh to show current state
            from fasthtml.common import HTMLResponse
            response = HTMLResponse('')
            response.headers['HX-Refresh'] = 'true'
            return response



    async def render_roles_list(self):
        """Render just the roles list for HTMX updates."""
        items_query = self.table()
        roles_config = self.config.get('ROLES_CONFIG', {})
        items = sorted(items_query, key=lambda item: item.priority or 99)
        
        return Ol(
            *[self.app_instance.render_item(item) for item in items],
            id=self.LIST_ID, cls='sortable', style="padding-left: 1.5rem;",
            hx_post=f"{self.ENDPOINT_PREFIX}_sort", hx_swap="none",
            data_plugin_name=self.name
        )

    @classmethod

    def generate_role_css(cls):
        """Generate CSS rules from ROLE_COLORS - single source of truth approach.
        Note: This method will be updated to use instance config in future iterations."""
        # For now, return empty string as CSS is handled by server.py get_dynamic_role_css
        return ""

def get_role_css_class(role_name):
    """Generate CSS class name for a role."""
    return f"menu-role-{role_name.lower().replace(' ', '-')}"

def render_item(item, app_instance):
    """Render a single role item with clean, discrete presentation."""
    item_id = f'{app_instance.name}-{item.id}'
    toggle_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/toggle/{item.id}"

    # Get role configuration from the injected config
    roles_config = app_instance.plugin.config.get('ROLES_CONFIG', {})
    role_info = roles_config.get(item.text, {})
    description = role_info.get('description', 'No description available.')

    # Core role is always enabled and cannot be toggled
    is_core = item.text == "Core"
    checkbox = Input(
        type="checkbox",
        checked=True if is_core else item.done,
        disabled=is_core,
        hx_post=toggle_url if not is_core else None,
        hx_swap="outerHTML",
        hx_target=f"#{item_id}",
        cls="flex-shrink-0",
        style=f"margin-left: {app_instance.plugin.UI_CONSTANTS['SPACING']['SECTION_MARGIN']};"
    )

    # Bold title followed by colon and description - all on same line
    title_and_description = Div(
        Span(item.text, cls="role-title"),
        ": ",
        Span(description, cls="role-description"),
        style="flex: 1;"
    )

    # Create discrete expandable plugin list with real emojis
    plugin_info = create_plugin_visibility_table(item.text, app_instance.plugin.UI_CONSTANTS)

    return Li(
        # Main role item with checkbox and title:description - clickable to expand/collapse
        Div(
            checkbox,
            title_and_description,
            style=f"display: flex; align-items: center; margin-bottom: {app_instance.plugin.UI_CONSTANTS['SPACING']['SECTION_MARGIN']}; cursor: pointer;",
            onmousedown="this.parentElement._mouseDownPos = {x: event.clientX, y: event.clientY};",
            onclick=f"""
                // Only handle click if it wasn't a drag operation and wasn't on checkbox
                if (this.parentElement._mouseDownPos && event.target.type !== 'checkbox') {{
                    const dragThreshold = 5; // pixels
                    const dragDistance = Math.sqrt(
                        Math.pow(event.clientX - this.parentElement._mouseDownPos.x, 2) +
                        Math.pow(event.clientY - this.parentElement._mouseDownPos.y, 2)
                    );

                    // Only process as click if user didn't drag beyond threshold
                    if (dragDistance < dragThreshold) {{
                        const details = this.parentElement.querySelector('details');
                        if (details) {{
                            details.open = !details.open;
                        }}
                    }}
                    this.parentElement._mouseDownPos = null;
                }}
            """
        ),
        # Discrete expandable plugin list
        plugin_info,
        id=item_id,
        cls=f"card-container {get_role_css_class(item.text)}",
        style=f"list-style-type: none; margin-bottom: {app_instance.plugin.UI_CONSTANTS['SPACING']['CARD_MARGIN']}; padding: {app_instance.plugin.UI_CONSTANTS['SPACING']['SECTION_MARGIN']}; border-radius: {app_instance.plugin.UI_CONSTANTS['SPACING']['BORDER_RADIUS']}; background-color: var(--pico-card-background-color); cursor: pointer;",
        onmousedown="this._mouseDownPos = {x: event.clientX, y: event.clientY};",
        onclick=f"""
            // Only handle click if it wasn't a drag operation
            if (this._mouseDownPos) {{
                const dragThreshold = 5; // pixels
                const dragDistance = Math.sqrt(
                    Math.pow(event.clientX - this._mouseDownPos.x, 2) +
                    Math.pow(event.clientY - this._mouseDownPos.y, 2)
                );

                // Only process as click if user didn't drag beyond threshold
                if (dragDistance < dragThreshold && event.target.type !== 'checkbox' && !event.target.closest('a')) {{
                    const details = this.querySelector('details');
                    if (details) {{
                        details.open = !details.open;
                    }}
                }}
                this._mouseDownPos = null;
            }}
        """,
        data_id=item.id,
        data_priority=item.priority or 0,
        data_plugin_item='true',
        data_list_target=app_instance.plugin.LIST_ID,
        data_endpoint_prefix=app_instance.plugin.ENDPOINT_PREFIX
    )

# Supporting functions for plugin discovery and visibility
def get_plugin_list():
    """Get list of all available plugins with their roles."""
    plugin_dir = Path(__file__).parent
    plugins = []

    for file_path in plugin_dir.glob('*.py'):
        if file_path.name.startswith('__') or file_path.name.startswith('xx_'):
            continue

        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                plugin_roles = getattr(module, 'ROLES', [])
                
                # Look for DISPLAY_NAME in classes first (more common pattern)
                display_name = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and hasattr(obj, 'DISPLAY_NAME'):
                        display_name_attr = getattr(obj, 'DISPLAY_NAME', None)
                        # Handle both properties and direct attributes
                        if isinstance(display_name_attr, property):
                            # For CRUD apps with property-based DISPLAY_NAME, replicate the logic
                            try:
                                # Check if it's a PluginIdentityManager subclass
                                if hasattr(obj, 'EMOJI'):
                                    # Replicate the PluginIdentityManager.DISPLAY_NAME property logic
                                    # Get the module filename and process it like PluginIdentityManager does
                                    filename = file_path.name.replace('.py', '')
                                    name = re.sub(r'^\d+_', '', filename)  # Remove numeric prefix
                                    display_name = title_name(name)  # Use the same title_name function
                                    
                                    emoji = getattr(obj, 'EMOJI', '')
                                    if emoji:
                                        # Put emoji at the right for consistency with workflows
                                        display_name = f"{display_name} {emoji}"
                                    break
                            except:
                                continue
                        elif display_name_attr and isinstance(display_name_attr, str):
                            display_name = display_name_attr
                            break
                
                # Fallback to module-level DISPLAY_NAME or filename-based name
                if not display_name:
                    display_name = getattr(module, 'DISPLAY_NAME', file_path.stem.replace('_', ' ').title())

                plugins.append({
                    'filename': file_path.name,
                    'module_name': file_path.stem,
                    'display_name': display_name,
                    'roles': plugin_roles
                })
        except Exception as e:
            logger.debug(f"Could not inspect plugin {file_path.name}: {e}")
            continue

    return sorted(plugins, key=lambda x: x['filename'])



def get_plugin_emoji(module_name):
    """Get the real emoji for a plugin by importing and checking its EMOJI attribute."""
    try:
        plugin_path = Path(__file__).parent / f"{module_name}.py"
        if plugin_path.exists():
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check for EMOJI in classes first (more specific)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and hasattr(obj, 'EMOJI'):
                        emoji = getattr(obj, 'EMOJI', '')
                        if emoji.strip():
                            return emoji

                # Fallback to module-level EMOJI
                emoji = getattr(module, 'EMOJI', '')
                if emoji.strip():
                    return emoji
    except Exception:
        pass
    return '⚡'  # Default emoji

def create_plugin_visibility_table(role_name, ui_constants=None):
    """Create a discrete expandable accordion showing plugins with real emojis."""
    plugin_list = get_plugin_list()
    affected_plugins = [plugin for plugin in plugin_list if role_name in plugin['roles']]

    if not affected_plugins:
        return Details(
            Summary(f"{len(affected_plugins)} APPs", style="font-size: 0.75em; color: var(--pico-muted-color); opacity: 0.7; cursor: pointer;"),
            P("No plugins assigned to this role.", style="font-style: italic; color: var(--pico-muted-color); margin: 0.5rem 0;"),
            style="margin-top: 0.5rem;"
        )

    # Create discrete plugin links using display names as-is
    plugin_items = []
    for plugin in affected_plugins:
        module_name = plugin['module_name']
        display_name = plugin['display_name']

        # Create navigation link - strip numeric prefix for URL
        import re
        clean_module_name = re.sub(r'^\d+_', '', module_name)
        plugin_url = f"/redirect/{clean_module_name}"

        # Use display name as-is without adding extra emojis
        plugin_items.append(
                            Li(
                    A(
                        display_name,
                        href=plugin_url,
                        style="font-size: 0.8em; color: rgba(255, 255, 255, 0.9); text-decoration: none;",
                        onmouseover="this.style.color = 'var(--pico-primary)'; this.style.textDecoration = 'underline';",
                        onmouseout="this.style.color = 'rgba(255, 255, 255, 0.9)'; this.style.textDecoration = 'none';",
                        onclick="event.stopPropagation();"
                    ),
                    style="margin: 0; padding: 0; line-height: 1.2;",
                    title=f"Navigate to {display_name}"
                )
        )

    return Details(
        Summary(
            f"{len(affected_plugins)} APPs",
            cls="role-plugin-summary",
            style="font-size: 0.75em; color: var(--pico-muted-color); opacity: 0.7; cursor: pointer;"
        ),
        Ol(*plugin_items, cls="role-plugin-ordered-list", style="margin: 0.25rem 0; padding-left: 1.5rem;"),
        style="margin-top: 0.5rem;"
    )
