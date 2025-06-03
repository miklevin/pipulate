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
    # Override this in subclasses to customize the emoji
    EMOJI = ''
    
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
        name = title_name(self.name)
        if self.EMOJI:
            return f"{self.EMOJI} {name} (Home)"
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
    # Override this to customize the emoji for this specific plugin
    EMOJI = '👥'
    
    # UI Configuration Constants
    UI_CONSTANTS = {
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
        'ROLE_COLORS': {
            # 🎨 SINGLE SOURCE OF TRUTH - Edit colors here, CSS generated automatically
            'menu-role-core': {
                'border': '#22c55e',            # GREEN
                'background': 'rgba(34, 197, 94, 0.1)',
                'background_light': 'rgba(34, 197, 94, 0.05)'
            },
            'menu-role-botify-employee': {
                'border': '#a855f7',            # PURPLE
                'background': 'rgba(168, 85, 247, 0.1)',
                'background_light': 'rgba(168, 85, 247, 0.05)'
            },
            'menu-role-tutorial': {
                'border': '#f97316',            # ORANGE
                'background': 'rgba(249, 115, 22, 0.1)',
                'background_light': 'rgba(249, 115, 22, 0.05)'
            },
            'menu-role-developer': {
                'border': '#3b82f6',            # BLUE
                'background': 'rgba(59, 130, 246, 0.1)',
                'background_light': 'rgba(59, 130, 246, 0.05)'
            },
            'menu-role-components': {
                'border': '#6b7280',            # GRAY
                'background': 'rgba(107, 114, 128, 0.1)',
                'background_light': 'rgba(107, 114, 128, 0.05)'
            },
            'menu-role-workshop': {
                'border': '#eab308',            # YELLOW
                'background': 'rgba(234, 179, 8, 0.1)',
                'background_light': 'rgba(234, 179, 8, 0.05)'
            }
        },
        'FALLBACK_COLORS': {
            'border': 'var(--pico-color-azure-500)',
            'background': 'var(--pico-card-background-color)'
        }
    }
    
    @classmethod 
    def generate_role_css(cls):
        """Generate CSS rules from ROLE_COLORS - single source of truth approach."""
        css_rules = []
        
        # Generate main role CSS with role-specific hover/focus states
        for role_class, colors in cls.UI_CONSTANTS['ROLE_COLORS'].items():
            # Extract RGB values from border color for darker hover state
            border_color = colors['border']
            if border_color.startswith('#'):
                # Convert hex to RGB for hover/focus calculations
                hex_color = border_color[1:]
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                # Create hover state with 20% background opacity
                hover_bg = f"rgba({r}, {g}, {b}, 0.2)"
                
                # Create focus/selected state with 25% background opacity 
                focus_bg = f"rgba({r}, {g}, {b}, 0.25)"
                
                css_rules.append(f"""
.{role_class} {{
    background-color: {colors['background']} !important;
    border-left: 3px solid {colors['border']} !important;
}}

.{role_class}:hover {{
    background-color: {hover_bg} !important;
}}

.{role_class}:focus,
.{role_class}:active,
.{role_class}[style*="background-color: var(--pico-primary-focus)"] {{
    background-color: {focus_bg} !important;
}}""")
        
        # Generate light theme adjustments with matching hover states
        for role_class, colors in cls.UI_CONSTANTS['ROLE_COLORS'].items():
            if role_class != 'menu-role-core':  # Core doesn't need light theme adjustment
                border_color = colors['border']
                if border_color.startswith('#'):
                    hex_color = border_color[1:]
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    
                    # Lighter hover for light theme (15% opacity)
                    light_hover_bg = f"rgba({r}, {g}, {b}, 0.15)"
                    light_focus_bg = f"rgba({r}, {g}, {b}, 0.2)"
                    
                    css_rules.append(f"""
[data-theme="light"] .{role_class} {{
    background-color: {colors['background_light']} !important;
}}

[data-theme="light"] .{role_class}:hover {{
    background-color: {light_hover_bg} !important;
}}

[data-theme="light"] .{role_class}:focus,
[data-theme="light"] .{role_class}:active,
[data-theme="light"] .{role_class}[style*="background-color: var(--pico-primary-focus)"] {{
    background-color: {light_focus_bg} !important;
}}""")
        
        return '\n'.join(css_rules)

    @property
    def ENDPOINT_MESSAGE(self):
        return f"Control which plugins appear in your APP menu by managing {self.DISPLAY_NAME.lower()}. Check roles that match your needs - Core plugins always show, while other roles add specialized plugin categories. Multiple roles can be combined to create custom plugin sets for different user types and workflows. Drag-to-reorder the APP menu."

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
            # Dynamic CSS injection - single source of truth for role colors
            Style(self.generate_role_css()),
            Card(
                H2(f"{self.DISPLAY_NAME}"),
                P(
                    "👇️ Check the sets-of-APPs (Roles) that match your needs to control which plugins appear in the ",
                    Strong("APP"), 
                    " dropdown menu. ",
                    Strong("Core"), 
                    " plugins always show, while other roles add specific plugin categories. You can select multiple roles to combine their plugin sets, and drag-to-reorder the APP menu.",
                    style=f"margin-bottom: {self.UI_CONSTANTS['SPACING']['LARGE_MARGIN']}; padding: {self.UI_CONSTANTS['SPACING']['DESCRIPTION_PADDING']}; background-color: var(--pico-muted-background-color); border-radius: {self.UI_CONSTANTS['SPACING']['BORDER_RADIUS']}; border-left: {self.UI_CONSTANTS['SPACING']['BORDER_WIDTH']} solid var(--pico-color-azure-500); color: var(--pico-muted-color); font-size: {self.UI_CONSTANTS['TYPOGRAPHY']['DESCRIPTION_TEXT']};"
                ),
                Ul(
                    *[self.app_instance.render_item(item) for item in items],
                    id=self.LIST_ID,
                    cls='sortable',
                    style="padding-left: 0;",
                    hx_post=f"{self.ENDPOINT_PREFIX}_sort",
                    hx_swap="none",
                    data_plugin_name=self.name
                )
            ),
            id=self.CONTAINER_ID,
            style="display: flex; flex-direction: column;"
        )

    async def render(self, render_items=None):
        """Fallback render method, currently just calls landing."""
        logger.debug(f"{self.DISPLAY_NAME}Plugin.render called, delegating to landing.")
        return await self.landing()


def get_role_css_class(role_name):
    """Convert role name to CSS class name that matches the menu styling."""
    # Convert to CSS class format (lowercase, spaces to hyphens)
    css_role = role_name.lower().replace(' ', '-')
    return f"menu-role-{css_role}"

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
        onclick="event.stopPropagation();" if not is_core else None,  # Prevent expand/contract when clicking checkbox
    )

    text_display = Span(
        item.text,
        id=f"{app_instance.name}-text-display-{item.id}",
        style="margin-left: 5px; font-weight: 500;"
    )

    # Create plugin visibility information
    plugin_info = create_plugin_visibility_table(item.text, app_instance.plugin.UI_CONSTANTS)

    # Get role-based CSS class for consistent coloring with menu
    role_css_class = get_role_css_class(item.text)
    base_classes = 'done' if item.done or is_core else ''
    combined_classes = f"{base_classes} {role_css_class}".strip()

    # Generate unique IDs for this item's details element
    details_id = f"details-{item_id}"
    
    return Li(
        # Main role item with checkbox and name
        Div(
            checkbox,
            text_display,
            style=f"display: flex; align-items: center; margin-bottom: {app_instance.plugin.UI_CONSTANTS['SPACING']['SECTION_MARGIN']};"
        ),
        # Plugin visibility information below
        plugin_info,
        id=item_id,
        cls=combined_classes,
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
    """Get plugins that would be shown for a given role using the same primary role logic as the APP menu."""
    # Import here to avoid circular imports
    import sys
    import os
    
    shown_plugins = []
    
    # Get the plugins directory
    plugins_dir = os.path.join(os.path.dirname(__file__))
    
    if os.path.isdir(plugins_dir):
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                # Skip experimental plugins
                if filename.lower().startswith('xx_') or '(' in filename:
                    continue
                
                # Extract numeric prefix and name
                match = re.match(r'^(\d+)_(.+)\.py$', filename)
                if match:
                    prefix = int(match.group(1))
                    base_name = match.group(2).replace('_', ' ').title()
                    plugin_endpoint_name = match.group(2)  # Keep original with underscores for endpoint
                    plugin_endpoint = f"/{plugin_endpoint_name}"
                    
                    # Get the module's ROLES and DISPLAY_NAME
                    try:
                        module_name = f"plugins.{filename[:-3]}"
                        if module_name in sys.modules:
                            module = sys.modules[module_name]
                            plugin_roles = getattr(module, 'ROLES', [])
                        else:
                            # Try to import the module
                            spec = importlib.util.spec_from_file_location(module_name, os.path.join(plugins_dir, filename))
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            plugin_roles = getattr(module, 'ROLES', [])
                        
                        # Try to get the actual DISPLAY_NAME from the plugin
                        display_name = base_name  # fallback
                        try:
                            # Look for plugin classes that might have DISPLAY_NAME
                            for name, obj in inspect.getmembers(module):
                                if inspect.isclass(obj) and hasattr(obj, 'DISPLAY_NAME'):
                                    try:
                                        if inspect.isdatadescriptor(obj.DISPLAY_NAME) or callable(obj.DISPLAY_NAME):
                                            # It's a property, need to use fallback logic
                                            if hasattr(obj, 'EMOJI'):
                                                emoji = getattr(obj, 'EMOJI', '')
                                                if emoji:
                                                    display_name = f"{base_name} {emoji}"
                                                else:
                                                    display_name = base_name
                                            else:
                                                display_name = base_name
                                        else:
                                            # It's a direct attribute, ensure it's a string
                                            attr_value = obj.DISPLAY_NAME
                                            if isinstance(attr_value, str):
                                                display_name = attr_value
                                            else:
                                                display_name = base_name
                                        break
                                    except Exception as inner_e:
                                        logger.debug(f"Error getting DISPLAY_NAME from {name}: {inner_e}")
                                        continue
                        except Exception as e:
                            logger.debug(f"Could not get display name for {filename}: {e}")
                            display_name = base_name
                        
                        # Use the same primary role logic as the APP menu
                        # Get the PRIMARY role (first role in the list)
                        if plugin_roles:
                            primary_role = plugin_roles[0]  # First role is primary (80/20 win/loss rule)
                            
                            # Only count this plugin if its PRIMARY role matches the requested role
                            if primary_role == role_name:
                                shown_plugins.append((prefix, display_name, plugin_endpoint))
                        # Only default to Core if ROLES variable is completely missing, not if it's empty
                        elif not hasattr(module, 'ROLES') and role_name == 'Core':
                            # Plugins with no ROLES variable (missing entirely) default to Core
                            shown_plugins.append((prefix, display_name, plugin_endpoint))
                        # Plugins with ROLES = [] are intentionally invisible and should not appear anywhere
                            
                    except Exception as e:
                        logger.warning(f"Could not check ROLES for {filename}: {e}")
                        continue
    
    return sorted(shown_plugins), [], f"Plugins available with {role_name} role"

def create_plugin_visibility_table(role_name, ui_constants=None):
    """Create a simple summary showing which plugins this role provides access to."""
    # Use default constants if none provided (for backward compatibility)
    if ui_constants is None:
        ui_constants = CrudUI.UI_CONSTANTS
    
    shown_plugins, hidden_plugins, description = get_affected_plugins(role_name)
    
    if not shown_plugins:
        return Small(f"📋 No plugins available", style=f"color: var(--pico-muted-color); font-style: italic; font-size: {ui_constants['TYPOGRAPHY']['TINY_TEXT']};")
    
    shown_count = len(shown_plugins)
    
    # Get role-based border color to match menu styling
    role_css_class = get_role_css_class(role_name)
    
    colors = ui_constants['ROLE_COLORS'].get(role_css_class, ui_constants['FALLBACK_COLORS'])
    border_color = colors['border']
    background_color = colors['background']
    
    # Create the plugin list vertically with clickable links using CSS counters
    def format_all_plugins_vertical(plugins):
        plugin_items = []
        for index, (prefix, display_name, endpoint) in enumerate(plugins, 1):
            plugin_items.append(
                Li(
                    Span(f"{index}. ", style=f"font-weight: bold; color: var(--pico-muted-color); font-size: {ui_constants['TYPOGRAPHY']['SMALL_TEXT']};"),
                    A(
                        display_name, 
                        href=endpoint,
                        style=f"color: var(--pico-color-azure-600); font-size: {ui_constants['TYPOGRAPHY']['SMALL_TEXT']}; line-height: {ui_constants['TYPOGRAPHY']['LINE_HEIGHT_COMPACT']}; text-decoration: none;",
                        onclick="event.stopPropagation();",  # Prevent triggering parent expand/contract
                        onmouseover="this.style.textDecoration='underline';",
                        onmouseout="this.style.textDecoration='none';"
                    ),
                    style=f"margin-bottom: {ui_constants['SPACING']['PLUGIN_ITEM_MARGIN']}; list-style: none;"
                )
            )
        return Ol(*plugin_items, style=f"padding-left: 1rem; margin: 0; list-style: none !important;")
    
    return Details(
        Summary(
            Small(
                f"📋 {shown_count} plugins available",
                style=f"color: var(--pico-muted-color); font-size: {ui_constants['TYPOGRAPHY']['SMALL_TEXT']}; cursor: pointer;"
            ),
            style="margin: 0; padding: 0; list-style: none;"
        ),
        Div(
            format_all_plugins_vertical(shown_plugins),
            style=f"padding: {ui_constants['SPACING']['CONTAINER_PADDING']}; background-color: {background_color}; border-radius: {ui_constants['SPACING']['BORDER_RADIUS']}; margin-top: {ui_constants['SPACING']['SECTION_MARGIN']}; border-left: {ui_constants['SPACING']['BORDER_WIDTH']} solid {border_color};"
        ),
        style="margin: 0;"
    )
