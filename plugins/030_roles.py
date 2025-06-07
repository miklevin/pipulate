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
        return f"Control which plugins appear in your APP menu by managing {self.DISPLAY_NAME.lower()}. Check roles that match your needs - Core plugins always show, while other roles add specialized plugin categories. Multiple roles can be combined to create custom plugin sets for different user types and workflows. Drag-to-reorder the APP menu."

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
        ]
        for path, handler, methods in routes:
            self.app.route(path, methods=methods)(handler)

    async def landing(self, request=None):
        """Render the main roles management interface."""
        items_query = self.table()
        roles_config = self.config.get('ROLES_CONFIG', {})
        items = sorted(items_query, key=lambda item: roles_config.get(item.text, {}).get('priority', 99))
        
        return Div(
            Style(self.generate_role_css()),
            Card(
                H2(f"{self.DISPLAY_NAME}"),
                P(self.ENDPOINT_MESSAGE),
                Ul(
                    *[self.app_instance.render_item(item) for item in items],
                    id=self.LIST_ID, cls='sortable', style="padding-left: 0;",
                    hx_post=f"{self.ENDPOINT_PREFIX}_sort", hx_swap="none",
                    data_plugin_name=self.name
                )
            ),
            id=self.CONTAINER_ID,
        )

    async def render(self, render_items=None):
        """Render method for compatibility."""
        return await self.landing()
    
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
    """Render a single role item with description and controls."""
    item_id = f'{app_instance.name}-{item.id}'
    toggle_url = f"{app_instance.plugin.ENDPOINT_PREFIX}/toggle/{item.id}"
    
    # Get role configuration from the injected config
    roles_config = app_instance.plugin.config.get('ROLES_CONFIG', {})
    role_info = roles_config.get(item.text, {})
    description = role_info.get('description', 'No description available.')
    emoji = role_info.get('emoji', '▫️')
    
    # Core role is always enabled and cannot be toggled
    is_core = item.text == "Core"
    checkbox = Input(
        type="checkbox", 
        checked=True if is_core else item.done, 
        disabled=is_core,
        hx_post=toggle_url if not is_core else None, 
        hx_swap="outerHTML", 
        hx_target=f"#{item_id}",
        cls="flex-shrink-0"
    )
    
    text_display = Span(
        f"{emoji} {item.text}", 
        style="margin-left: 5px; font-weight: 500;"
    )
    
    # Role description
    description_text = P(
        Strong("Description: "), 
        description, 
        style=f"font-size: {app_instance.plugin.UI_CONSTANTS['TYPOGRAPHY']['DESCRIPTION_TEXT']}; color: var(--pico-muted-color); margin-top: 0.5rem;"
    )

    return Li(
        Div(
            checkbox, 
            text_display, 
            cls='flex-row'
        ),
        description_text,
        id=item_id, 
        cls=f"card-container {get_role_css_class(item.text)}",
        style="list-style-type: none; cursor: grab; margin-bottom: 0.5rem;",
        data_id=item.id, 
        data_priority=item.priority or 0,
        data_plugin_item='true',
        data_list_target=app_instance.plugin.LIST_ID
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

def get_affected_plugins(role_name):
    """Get plugins that would be affected by toggling this role."""
    affected = []
    for plugin in get_plugin_list():
        if role_name in plugin['roles']:
            affected.append(plugin['display_name'])
    return affected

def create_plugin_visibility_table(role_name, ui_constants=None):
    """Create a table showing which plugins belong to this role."""
    affected_plugins = get_affected_plugins(role_name)
    
    if not affected_plugins:
        return P("No plugins assigned to this role.", style="font-style: italic; color: var(--pico-muted-color);")
    
    def format_all_plugins_vertical(plugins):
        """Format plugin list vertically with consistent styling."""
        if not plugins:
            return P("No plugins in this role.")
        
        plugin_items = []
        for plugin_name in plugins:
            plugin_items.append(
                Li(
                    plugin_name,
                    style="list-style-type: none; padding: 0.25rem 0; border-bottom: 1px solid var(--pico-muted-border-color);"
                )
            )
        
        return Div(
            P(f"Plugins in this role ({len(plugins)}):", style="font-weight: 500; margin-bottom: 0.5rem;"),
            Ul(*plugin_items, style="padding-left: 0; margin: 0;"),
            style="margin-top: 0.5rem;"
        )
    
    return format_all_plugins_vertical(affected_plugins)
