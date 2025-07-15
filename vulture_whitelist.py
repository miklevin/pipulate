# Whitelist for vulture to ignore functions used through FastHTML/HTMX routes and plugin system

# autopep8 --ignore E501,F405,F403,F541 --in-place server.py
# isort server.py
# vulture server.py
# pylint --disable=all --enable=redefined-outer-name server.py
# pylint --disable=all --enable=similarities .

# Configuration and testing variables used conditionally
DEEP_TESTING = True  # noqa - Testing mode flag used based on command line args
BROWSER_TESTING = True  # noqa - Browser testing flag used based on command line args

# Exception classes used for server control flow
class GracefulRestartException:  # noqa
    pass  # Used for graceful server restarts via watchdog

# UI constants and themes used in templates and dynamic contexts
custom_theme = {}  # noqa - Used by theming system
INFO_SVG = ""  # noqa - SVG icon used in templates
EXTERNAL_LINK_SVG = ""  # noqa - SVG icon used in templates  
SETTINGS_SVG = ""  # noqa - SVG icon used in templates
UNLOCK_BUTTON_LABEL = ""  # noqa - UI constant used in interface

# Conversation system variables used by LLM system
conversation = []  # noqa - Conversation history used by LLM
def monitor_conversation_efficiency(): pass  # noqa - Conversation monitoring function

# Menu and UI generation functions used dynamically
def generate_menu_style(): pass  # noqa - Used for dynamic menu styling

# Demo and development functions used conditionally  
async def demo_bookmark_check(): pass  # noqa - Used by demo system
async def prepare_local_llm_context(): pass  # noqa - Used for LLM context preparation

# FastHTML startup event used by framework
async def startup_event(): pass  # noqa - Used during server startup

# Variables used in debugging, logging, and dynamic contexts
is_bql = True  # noqa - Used for BQL query logging identification
mcp_request_start = 0.0  # noqa - Used for MCP timing measurements  
existing_role_done_states = {}  # noqa - Used in role synchronization
role_priority = 0  # noqa - Used in menu generation and sorting
current_url = ""  # noqa - Used in request processing and redirects
stash_result = None  # noqa - Used in git operations for update process

# These functions are used through HTMX routes but appear unused to vulture
async def clear_pipeline(request): ...  # noqa

async def clear_db(request): ...  # noqa

async def delete_pipeline(request): ...  # noqa

async def toggle_show_all(request): ...  # noqa

async def toggle_developer_plugins_visibility(request): ...  # noqa

async def toggle_profile_lock(request): ...  # noqa

async def navigate_intro_page_endpoint(request): ...  # noqa

async def poke_flyout(request): ...  # noqa

async def poke_flyout_hide(request): ...  # noqa

def redirect_handler(request): ...  # noqa

async def poke_chatbot(): ...  # noqa

async def select_profile(request): ...  # noqa

async def refresh_profile_menu(request): ...  # noqa

async def switch_environment(request): ...  # noqa

# These methods are used through the plugin system and dependency injection
class Pipulate:  # noqa
    def workflow(self, message, details=None): ...  # noqa
    def append_to_history(self, message, role="system", quiet=True): ...  # noqa
    def mark_step_complete(self, step_num): ...  # noqa
    def mark_step_started(self, step_num): ...  # noqa
    def make_singular(self, word): ...  # noqa
    def set_chat(self, chat_instance): ...  # noqa
    def get_message_queue(self): ...  # noqa
    def get_ui_constants(self): ...  # noqa
    def get_config(self): ...  # noqa
    def get_button_border_radius(self): ...  # noqa
    def register_workflow_routes(self, plugin_instance): ...  # noqa
    def log_api_call_details(self, pipeline_id, step_id, call_description, http_method, url, headers, **kwargs): ...  # noqa
    def create_folder_button(self, folder_path, icon="📁", text="Open Folder", title_prefix="Open folder"): ...  # noqa
    def display_revert_widget(self, step_id, app_name, steps, message=None, widget=None, target_id=None, revert_label=None, widget_style=None, finalized_content=None, next_step_id=None): ...  # noqa
    def tree_display(self, content): ...  # noqa
    def finalized_content(self, message, content=None, heading_tag=H4, content_style=None): ...  # noqa
    def create_standard_landing_page(self, plugin_instance): ...  # noqa
    def generate_pipeline_key(self, plugin_instance, user_input=None): ...  # noqa
    def parse_pipeline_key(self, pipeline_key): ...  # noqa
    def validate_step_input(self, value, step_show, custom_validator=None): ...  # noqa
    def set_step_data(self, pipeline_id, step_id, step_value, steps, clear_previous=True): ...  # noqa
    def check_finalize_needed(self, step_index, steps): ...  # noqa
    def chain_reverter(self, step_id, step_index, steps, app_name, processed_val): ...  # noqa
    def handle_finalized_step(self, pipeline_id, step_id, steps, app_name, plugin_instance=None): ...  # noqa
    def finalize_workflow(self, pipeline_id, state_update=None): ...  # noqa
    def unfinalize_workflow(self, pipeline_id): ...  # noqa
    
    # Workflow state attributes used by message queue system
    class OrderedMessageQueue:  # noqa
        _current_step = None  # noqa
        _step_started = False  # noqa  
        _step_complete = False  # noqa
        _workflow_context = None  # noqa

class LogManager:  # noqa
    def send(self, message): ...  # noqa

class BaseCrud:  # noqa
    def get_action_url(self, action, item_id): ...  # noqa

class Chat:  # noqa
    def create_progress_card(self): ...  # noqa 