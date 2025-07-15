# Vulture whitelist for server.py
# This file contains dummy definitions and usage to prevent false positives
# Usage: vulture server.py vulture_whitelist.py
# 
# Alternative commands:
# autopep8 --ignore E501,F405,F403,F541 --in-place server.py
# isort server.py
# vulture server.py vulture_whitelist.py
# pylint --disable=all --enable=redefined-outer-name server.py
# pylint --disable=all --enable=similarities .

# =============================================================================
# DUMMY DEFINITIONS FOR WHITELIST ITEMS
# =============================================================================

# Configuration variables used conditionally
DEEP_TESTING = True
BROWSER_TESTING = True
custom_theme = {}

# SVG constants used in templates
INFO_SVG = ""
EXTERNAL_LINK_SVG = ""
SETTINGS_SVG = ""

# Exception class for control flow
class GracefulRestartException:
    pass

# Functions used by framework
def monitor_conversation_efficiency():
    pass

def startup_event():
    pass

def generate_menu_style():
    pass

def demo_bookmark_check():
    pass

def prepare_local_llm_context():
    pass

# Pipulate class constants and methods
UNLOCK_BUTTON_LABEL = ""

def workflow():
    pass

def append_to_history():
    pass

def get_message_queue():
    pass

def get_ui_constants():
    pass

def get_config():
    pass

def get_button_border_radius():
    pass

def register_workflow_routes():
    pass

def log_api_call_details():
    pass

def create_folder_button():
    pass

def display_revert_widget():
    pass

def tree_display():
    pass

def create_standard_landing_page():
    pass

def parse_pipeline_key():
    pass

def validate_step_input():
    pass

def set_step_data():
    pass

def check_finalize_needed():
    pass

def chain_reverter():
    pass

def handle_finalized_step():
    pass

def finalize_workflow():
    pass

def unfinalize_workflow():
    pass

def make_singular():
    pass

# Message queue attributes
_current_step = None
_step_started = None
_step_complete = None
_workflow_context = None

def mark_step_complete():
    pass

def mark_step_started():
    pass

# Dynamic variables used in local scopes
is_bql = True
mcp_request_start = 0
existing_role_done_states = {}
role_priority = 0
current_url = ""
stash_result = None
conversation = []

# =============================================================================
# USAGE TO PREVENT VULTURE WARNINGS
# =============================================================================

# Use all the items defined above to prevent vulture from flagging them
_ = DEEP_TESTING
_ = BROWSER_TESTING
_ = custom_theme
_ = INFO_SVG
_ = EXTERNAL_LINK_SVG
_ = SETTINGS_SVG
_ = GracefulRestartException
_ = monitor_conversation_efficiency
_ = startup_event
_ = generate_menu_style
_ = demo_bookmark_check
_ = prepare_local_llm_context
_ = UNLOCK_BUTTON_LABEL
_ = workflow
_ = append_to_history
_ = get_message_queue
_ = get_ui_constants
_ = get_config
_ = get_button_border_radius
_ = register_workflow_routes
_ = log_api_call_details
_ = create_folder_button
_ = display_revert_widget
_ = tree_display
_ = create_standard_landing_page
_ = parse_pipeline_key
_ = validate_step_input
_ = set_step_data
_ = check_finalize_needed
_ = chain_reverter
_ = handle_finalized_step
_ = finalize_workflow
_ = unfinalize_workflow
_ = make_singular
_ = _current_step
_ = _step_started
_ = _step_complete
_ = _workflow_context
_ = mark_step_complete
_ = mark_step_started
_ = is_bql
_ = mcp_request_start
_ = existing_role_done_states
_ = role_priority
_ = current_url
_ = stash_result
_ = conversation 