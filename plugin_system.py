
HOME_MENU_ITEM = 'Roles️ 👥'

HOME_MENU_ITEM = PCONFIG['HOME_MENU_ITEM']

def discover_plugin_files():
    """Discover and import all Python files in the plugins directory.

    This function scans the 'plugins' directory and imports each .py file
    as a module. It skips files:
    - Starting with '__' (like __init__.py)
    - Starting with 'xx_' or 'XX_' (indicating experimental/in-progress plugins)
    - Containing parentheses (like "tasks (Copy).py")

    Returns:
        dict: Mapping of module names to imported module objects
    """
    plugin_modules = {}
    plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
    logger.debug(f'Looking for plugins in: {plugins_dir}')
    if not os.path.isdir(plugins_dir):
        logger.warning(f'Plugins directory not found: {plugins_dir}')
        return plugin_modules

    def numeric_prefix_sort(filename):
        match = re.match('^(\\d+)_', filename)
        if match:
            return int(match.group(1))
        return float('inf')
    sorted_files = sorted(os.listdir(plugins_dir), key=numeric_prefix_sort)
    for filename in sorted_files:
        logger.debug(f'Checking file: {filename}')
        if '(' in filename or ')' in filename:
            logger.debug(f'Skipping file with parentheses: {filename}')
            continue
        if filename.lower().startswith('xx_'):
            logger.debug(f'Skipping experimental plugin: {filename}')
            continue
        if filename.endswith('.py') and (not filename.startswith('__')):
            base_name = filename[:-3]
            clean_name = re.sub('^\\d+_', '', base_name)
            original_name = base_name
            logger.debug(f'Module name: {clean_name} (from {original_name})')
            try:
                module = importlib.import_module(f'plugins.{original_name}')
                plugin_modules[clean_name] = module
                module._original_filename = original_name
                logger.debug(f'Successfully imported module: {clean_name} from {original_name}')
            except ImportError as e:
                logger.error(f'Error importing plugin module {original_name}: {str(e)}')
    logger.debug(f'Discovered plugin modules: {list(plugin_modules.keys())}')
    return plugin_modules

def find_plugin_classes(plugin_modules, discovered_modules):
    """Find all plugin classes in the given modules."""
    plugin_classes = []
    for module_or_name in plugin_modules:
        try:
            if isinstance(module_or_name, str):
                module_name = module_or_name
                original_name = getattr(discovered_modules[module_name], '_original_filename', module_name)
                module = importlib.import_module(f'plugins.{original_name}')
            else:
                module = module_or_name
                module_name = module.__name__.split('.')[-1]
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    logger.debug(f'Found member in {module_name}: {name}, type: {type(obj)}')
                    if hasattr(obj, 'landing'):
                        logger.debug(f'Class found: {module_name}.{name}')
                        if hasattr(obj, 'NAME') or hasattr(obj, 'APP_NAME') or hasattr(obj, 'DISPLAY_NAME'):
                            logger.debug(f'Found plugin: {module_name}.{name} (attribute-based, using NAME)')
                            plugin_classes.append((module_name, name, obj))
                        elif hasattr(obj, 'name') or hasattr(obj, 'app_name') or hasattr(obj, 'display_name'):
                            logger.debug(f'Found plugin: {module_name}.{name} (property-based)')
                            plugin_classes.append((module_name, name, obj))
                        else:
                            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{name} has landing method but missing required name attributes (NAME, APP_NAME, DISPLAY_NAME, name, app_name, display_name) - skipping')
                    else:
                        # Only log classes that look like they might be plugins (have common plugin attributes)
                        if any(hasattr(obj, attr) for attr in ['APP_NAME', 'DISPLAY_NAME', 'ROLES', 'steps']):
                            logger.warning(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Plugin class {module_name}.{name} appears to be a plugin (has APP_NAME/DISPLAY_NAME/ROLES/steps) but missing required landing method - skipping')
        except Exception as e:
            logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Error processing module {module_or_name}: {str(e)}')
            import traceback
            logger.error(f'FINDER_TOKEN: PLUGIN_REGISTRATION_FAILURE - Full traceback for {module_or_name}: {traceback.format_exc()}')
            continue
    logger.debug(f'Discovered plugin classes: {plugin_classes}')
    return plugin_classes

plugin_instances = {}

def register_plugin_endpoint(module_name: str, app_name: str) -> str:
    """
    Register a plugin's endpoint mapping during discovery.
    
    Args:
        module_name: Plugin filename (e.g., "040_hello_workflow")
        app_name: Plugin APP_NAME constant (e.g., "hello")
    
    Returns:
        The registered endpoint URL
    """
    # Extract endpoint from module filename (once, correctly)
    name = module_name.replace('.py', '')
    parts = name.split('_')
    if parts[0].isdigit():
        parts = parts[1:]  # Remove numeric prefix
    endpoint = '_'.join(parts)
    
    # Build full URL
    endpoint_url = f"http://localhost:5001/{endpoint}"
    
    # Register the mapping
    endpoint_registry[app_name] = {
        'module_name': module_name,
        'endpoint': endpoint,
        'url': endpoint_url
    }
    
    logger.debug(f"🎯 ENDPOINT_REGISTRY: Registered {app_name} → {endpoint_url}")
    return endpoint_url

base_menu_items = ['']

additional_menu_items = []

ordered_plugins = []

MENU_ITEMS = base_menu_items + ordered_plugins + additional_menu_items

def create_env_menu():
    """Create environment selection dropdown menu."""
    current_env = get_current_environment()
    display_env = 'DEV' if current_env == 'Development' else 'Prod'
    env_summary_classes = 'inline-nowrap'
    if current_env == 'Development':
        env_summary_classes += ' env-dev-style'
    menu_items = []
    is_dev = current_env == 'Development'
    dev_classes = 'menu-item-base menu-item-hover'
    if is_dev:
        dev_classes += ' menu-item-active'
    # Use external info SVG file for tooltips
    
    dev_item = Li(Label(
        Input(type='radio', name='env_radio_select', value='Development', checked=is_dev, hx_post='/switch_environment', hx_vals='{"environment": "Development"}', hx_target='#dev-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Development environment', data_testid='env-dev-radio'), 
        'DEV',
        Span(
            NotStr(INFO_SVG),
            data_tooltip='Development mode: Experiment and play! Freely reset database.',
            data_placement='left',
            aria_label='Development environment information',
            style='display: inline-block; margin-left: 12px;'
        ),
        cls='dropdown-menu-item'
    ), cls=dev_classes, id='dev-env-item', data_testid='env-dev-item')
    menu_items.append(dev_item)
    is_prod = current_env == 'Production'
    prod_classes = 'menu-item-base menu-item-hover'
    if is_prod:
        prod_classes += ' menu-item-active'
    prod_item = Li(Label(
        Input(type='radio', name='env_radio_select', value='Production', checked=is_prod, hx_post='/switch_environment', hx_vals='{"environment": "Production"}', hx_target='#prod-env-item', hx_swap='outerHTML', cls='ml-quarter', aria_label='Switch to Production environment', data_testid='env-prod-radio'), 
        'Prod',
        Span(
            NotStr(INFO_SVG),
            data_tooltip='Production mode: Automatically backs up Profile and Tasks data.',
            data_placement='left',
            aria_label='Production environment information',
            style='display: inline-block; margin-left: 12px;'
        ),
        cls='dropdown-menu-item'
    ), cls=prod_classes, id='prod-env-item', data_testid='env-prod-item')
    menu_items.append(prod_item)
    return Details(
        Summary(
            display_env, 
            cls=env_summary_classes, 
            id='env-id',
            aria_label='Environment selection menu',
            aria_expanded='false',
            aria_haspopup='menu'
        ), 
        Ul(
            *menu_items, 
            cls='dropdown-menu env-dropdown-menu',
            role='menu',
            aria_label='Environment options',
            aria_labelledby='env-id'
        ), 
        cls='dropdown', 
        id='env-dropdown-menu',
        aria_label='Environment management',
        data_testid='environment-dropdown-menu'
    )

def create_nav_menu():
    logger.debug('Creating navigation menu.')
    menux = db.get('last_app_choice', 'App')
    selected_profile_id = get_current_profile_id()
    selected_profile_name = get_profile_name()
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for menu creation")
        return Div(H1('Error: Profiles plugin not found', cls='text-invalid'), cls='nav-breadcrumb')
    home_link = A(APP_NAME, href='/redirect/', title=f'Go to {HOME_MENU_ITEM.lower()}', cls='nav-link-hover')
    separator = Span(' / ', cls='breadcrumb-separator')
    profile_text = Span(title_name(selected_profile_name))
    endpoint_text = Span(endpoint_name(menux) if menux else HOME_MENU_ITEM)
    breadcrumb = H1(home_link, separator, profile_text, separator, endpoint_text, role='banner', aria_label='Current location breadcrumb')
    # Create navigation poke button for the nav area
    # Use external SVG file for poke button settings icon
    nav_flyout_panel = Div(id='nav-flyout-panel', cls='nav-flyout-panel hidden')
    poke_section = Details(
        Summary(NotStr(SETTINGS_SVG), cls='inline-nowrap nav-poke-button', id='poke-summary', hx_get='/poke-flyout', hx_target='#nav-flyout-panel', hx_trigger='mouseenter', hx_swap='outerHTML'),
        nav_flyout_panel,
        cls='dropdown nav-poke-section',
        id='poke-dropdown-menu'
    )
    # Create navigation search field (positioned before PROFILE)
    # HTMX real-time search implementation with keyboard navigation
    # Search container with dropdown results
    search_results_dropdown = Div(id='search-results-dropdown', cls='search-dropdown', role='listbox', aria_label='Search results')
    
    nav_search_container = Div(
        Input(
            type='search',
            name='search',
            placeholder='Search plugins (Ctrl+K)',
            cls='nav-search nav-search-input',
            id='nav-plugin-search',
            hx_post='/search-plugins',
            hx_target='#search-results-dropdown',
            hx_trigger='input changed delay:300ms, keyup[key==\'Enter\'], focus',
            hx_swap='innerHTML',
            role='searchbox',
            aria_label='Search plugins',
            aria_describedby='search-results-dropdown',
            aria_autocomplete='list',
            aria_expanded='false'
            # Keyboard navigation now handled by external JavaScript in chat-interactions.js
        ),
        search_results_dropdown,
        cls='search-dropdown-container',
        role='search',
        aria_label='Plugin search'
    )
    
    menus = Div(nav_search_container, create_profile_menu(selected_profile_id, selected_profile_name), create_app_menu(menux), create_env_menu(), poke_section, cls='nav-menu-group')
    nav = Div(breadcrumb, menus, cls='nav-breadcrumb')
    logger.debug('Navigation menu created.')
    return nav

def create_profile_menu(selected_profile_id, selected_profile_name):
    """Create the profile dropdown menu."""
    menu_items = []
    profile_locked = db.get('profile_locked', '0') == '1'
    menu_items.append(Li(Label(Input(type='checkbox', name='profile_lock_switch', role='switch', checked=profile_locked, hx_post='/toggle_profile_lock', hx_target='body', hx_swap='outerHTML', aria_label='Lock or unlock profile editing'), 'Lock Profile',         Span(
            NotStr(INFO_SVG),
            data_tooltip='Prevent accidental profile changes. When locked, only selected profile is shown.',
            data_placement='left',
            aria_label='Profile lock information',
            cls='dropdown-tooltip'
        ), cls='dropdown-menu-item'), cls='profile-menu-item'))
    menu_items.append(Li(Hr(cls='profile-menu-separator'), cls='block'))
    profiles_plugin_inst = plugin_instances.get('profiles')
    if not profiles_plugin_inst:
        logger.error("Could not get 'profiles' plugin instance for profile menu creation")
        menu_items.append(Li(A('Error: Profiles link broken', href='#', cls='dropdown-item text-invalid')))
    else:
        plugin_display_name = getattr(profiles_plugin_inst, 'DISPLAY_NAME', 'Profiles')
        if not profile_locked:
            menu_items.append(Li(Label(
                f'Edit {plugin_display_name}',
                Span(
                    NotStr(INFO_SVG),
                    data_tooltip='Create, modify, and organize Customer profiles. Each profile has its own set of Tasks.',
                    data_placement='left',
                    aria_label='Edit profiles information',
                    cls='dropdown-tooltip'
                ),
                hx_post=f'/redirect/{profiles_plugin_inst.name}',
                hx_target='body',
                hx_swap='outerHTML',
                cls='dropdown-item menu-item-header dropdown-menu-item',
                style='cursor: pointer;'
            )))
    active_profiles_list = []
    if profiles:
        if profile_locked:
            if selected_profile_id:
                try:
                    selected_profile_obj = profiles.get(int(selected_profile_id))
                    if selected_profile_obj:
                        active_profiles_list = [selected_profile_obj]
                except Exception as e:
                    logger.error(f'Error fetching locked profile {selected_profile_id}: {e}')
        else:
            active_profiles_list = list(profiles(where='active = ?', where_args=(True,), order_by='priority'))
    else:
        logger.error("Global 'profiles' table object not available for create_profile_menu.")
    for profile_item in active_profiles_list:
        is_selected = str(profile_item.id) == str(selected_profile_id)
        radio_input = Input(type='radio', name='profile_radio_select', value=str(profile_item.id), checked=is_selected, hx_post='/select_profile', hx_vals=json.dumps({'profile_id': str(profile_item.id)}), hx_target='body', hx_swap='outerHTML', aria_label=f'Select {profile_item.name} profile')
        label_classes = 'dropdown-menu-item'
        if is_selected:
            label_classes += ' profile-menu-item-selected'
        profile_label = Label(radio_input, profile_item.name, cls=label_classes)
        menu_item_classes = 'menu-item-base menu-item-hover'
        if is_selected:
            menu_item_classes += ' menu-item-active'
        menu_items.append(Li(profile_label, cls=menu_item_classes))
    summary_profile_name_to_display = selected_profile_name
    if not summary_profile_name_to_display and selected_profile_id:
        try:
            profile_obj = profiles.get(int(selected_profile_id))
            if profile_obj:
                summary_profile_name_to_display = profile_obj.name
        except Exception:
            pass
    summary_profile_name_to_display = summary_profile_name_to_display or 'Select'
    return Details(Summary('👤 PROFILE', cls='inline-nowrap', id='profile-id', aria_label='Profile selection menu', aria_expanded='false', aria_haspopup='menu'), Ul(*menu_items, cls='dropdown-menu profile-dropdown-menu', role='menu', aria_label='Profile options', aria_labelledby='profile-id'), cls='dropdown', id='profile-dropdown-menu', aria_label='Profile management')

def normalize_menu_path(path):
    """Convert empty paths to empty string and return the path otherwise."""
    return '' if path == '' else path

def generate_menu_style():
    """Generate consistent menu styling for dropdown menus."""
    border_radius = PCONFIG['UI_CONSTANTS']['BUTTON_STYLES']['BORDER_RADIUS']
    return f'white-space: nowrap; display: inline-block; min-width: max-content; background-color: var(--pico-background-color); border: 1px solid var(--pico-muted-border-color); border-radius: {border_radius}; padding: 0.5rem 1rem; cursor: pointer; transition: background-color 0.2s;'

def create_app_menu(menux):
    """Create the App dropdown menu with hierarchical role-based sorting."""
    logger.debug(f"Creating App menu. Currently selected app (menux): '{menux}'")
    active_role_names = get_active_roles()
    menu_items = create_home_menu_item(menux)
    role_priorities = get_role_priorities()
    plugins_by_role = group_plugins_by_role(active_role_names)
    for role_name, role_priority in sorted(role_priorities.items(), key=lambda x: x[1]):
        if role_name in active_role_names:
            role_plugins = plugins_by_role.get(role_name, [])
            role_plugins.sort(key=lambda x: get_plugin_numeric_prefix(x))
            for plugin_key in role_plugins:
                menu_item = create_plugin_menu_item(plugin_key=plugin_key, menux=menux, active_role_names=active_role_names)
                if menu_item:
                    menu_items.append(menu_item)
    return create_menu_container(menu_items)

def group_plugins_by_role(active_role_names):
    """Group plugins by their primary role for hierarchical menu organization."""
    plugins_by_role = {}
    for plugin_key in ordered_plugins:
        instance = plugin_instances.get(plugin_key)
        if not instance:
            continue
        if plugin_key in ['profiles', 'roles']:
            continue
        if not should_include_plugin(instance, active_role_names):
            continue
        primary_role = get_plugin_primary_role(instance)
        if primary_role:
            role_name = primary_role.replace('-', ' ').title()
            if role_name not in plugins_by_role:
                plugins_by_role[role_name] = []
            plugins_by_role[role_name].append(plugin_key)
    logger.debug(f'Plugins grouped by role: {plugins_by_role}')
    return plugins_by_role

def get_plugin_numeric_prefix(plugin_key):
    """Extract numeric prefix from plugin filename for sorting within role groups."""
    if plugin_key in discovered_modules:
        original_filename = getattr(discovered_modules[plugin_key], '_original_filename', plugin_key)
        match = re.match('^(\\d+)_', original_filename)
        if match:
            return int(match.group(1))
    return 9999

def create_home_menu_item(menux):
    """Create menu items list starting with Home option."""
    menu_items = []
    is_home_selected = menux == ''
    home_radio = Input(type='radio', name='app_radio_select', value='', checked=is_home_selected, hx_post='/redirect/', hx_target='body', hx_swap='outerHTML', aria_label='Navigate to home page')
    home_css_classes = 'dropdown-item dropdown-menu-item'
    if is_home_selected:
        home_css_classes += ' app-menu-item-selected'
    home_label = Label(
        home_radio, 
        HOME_MENU_ITEM,
        Span(
            NotStr(INFO_SVG),
            data_tooltip='Customize by adding and sorting groups of Plugins (Roles)',
            data_placement='left',
            aria_label='Roles information',
            cls='dropdown-tooltip'
        ),
        cls=home_css_classes
    )
    menu_items.append(Li(home_label))
    return menu_items

def get_plugin_primary_role(instance):
    """Get the primary role for a plugin for UI styling purposes.
    
    Uses a simple 80/20 approach: if plugin has multiple roles, 
    we take the first one as primary. This creates a clean win/loss
    scenario for coloring without complex blending logic.
    
    Returns lowercase role name with spaces replaced by hyphens for CSS classes.
    """
    plugin_module_path = instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    if not plugin_defined_roles:
        return None
    primary_role = plugin_defined_roles[0]
    css_role = primary_role.lower().replace(' ', '-')
    logger.debug(f"Plugin '{instance.__class__.__name__}' primary role: '{primary_role}' -> CSS class: 'menu-role-{css_role}'")
    return css_role

def create_plugin_menu_item(plugin_key, menux, active_role_names):
    """Create menu item for a plugin if it should be included based on roles."""
    instance = plugin_instances.get(plugin_key)
    if not instance:
        logger.warning(f"Instance for plugin_key '{plugin_key}' not found. Skipping.")
        return None
    if plugin_key in ['profiles', 'roles']:
        return None

    if not should_include_plugin(instance, active_role_names):
        return None
    display_name = getattr(instance, 'DISPLAY_NAME', title_name(plugin_key))
    is_selected = menux == plugin_key
    redirect_url = f"/redirect/{(plugin_key if plugin_key else '')}"
    primary_role = get_plugin_primary_role(instance)
    role_class = f'menu-role-{primary_role}' if primary_role else ''
    css_classes = f'dropdown-item {role_class}'.strip()
    if is_selected:
        css_classes += ' app-menu-item-selected'
    radio_input = Input(type='radio', name='app_radio_select', value=plugin_key, checked=is_selected, hx_post=redirect_url, hx_target='body', hx_swap='outerHTML', aria_label=f'Navigate to {display_name}')
    return Li(Label(radio_input, display_name, cls=css_classes))

def should_include_plugin(instance, active_role_names):
    """Determine if plugin should be included based on its roles."""
    plugin_module_path = instance.__module__
    plugin_module = sys.modules.get(plugin_module_path)
    plugin_defined_roles = getattr(plugin_module, 'ROLES', []) if plugin_module else []
    is_core_plugin = 'Core' in plugin_defined_roles
    has_matching_active_role = any((p_role in active_role_names for p_role in plugin_defined_roles))
    should_include = is_core_plugin or has_matching_active_role
    logger.debug(f"Plugin '{instance.__class__.__name__}' (Roles: {plugin_defined_roles}). Core: {is_core_plugin}, Active Roles: {active_role_names}, Match: {has_matching_active_role}, Include: {should_include}")
    return should_include

def create_menu_container(menu_items):
    """Create the final menu container with all items."""
    return Details(Summary('⚡ APP', cls='inline-nowrap', id='app-id', aria_label='Application menu', aria_expanded='false', aria_haspopup='menu'), Ul(*menu_items, cls='dropdown-menu', role='menu', aria_label='Application options', aria_labelledby='app-id'), cls='dropdown', id='app-dropdown-menu', aria_label='Application selection')
