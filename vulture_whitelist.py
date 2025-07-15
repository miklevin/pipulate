# Whitelist for vulture to ignore functions used through FastHTML/HTMX routes and plugin system

# autopep8 --ignore E501,F405,F403,F541 --in-place server.py
# isort server.py
# vulture server.py
# pylint --disable=all --enable=redefined-outer-name server.py
# pylint --disable=all --enable=similarities .

from server import (  # noqa
    # Core classes used by plugins
    BaseCrud,  # Used by profiles, roles, tasks plugins
    Pipulate,  # Core coordinator class used throughout
    LogManager,  # Used for logging throughout
    Chat,  # Used for chat functionality
    
    # Functions used in plugin system
    startup_event,  # Used during server startup
    create_filler_item,  # Used in UI generation
    profile_render,  # Used in profile management
    step_name,  # Used in workflow steps
    get_button_style,  # Used in UI generation
)

# These functions are used through HTMX routes
@rt('/clear-pipeline', methods=['POST'])
async def clear_pipeline(request): ...  # noqa

@rt('/clear-db', methods=['POST'])
async def clear_db(request): ...  # noqa

@rt('/delete-pipeline', methods=['POST'])
async def delete_pipeline(request): ...  # noqa

@rt('/toggle_show_all', methods=['POST'])
async def toggle_show_all(request): ...  # noqa

@rt('/toggle_developer_plugins_visibility', methods=['POST'])
async def toggle_developer_plugins_visibility(request): ...  # noqa

@rt('/toggle_profile_lock', methods=['POST'])
async def toggle_profile_lock(request): ...  # noqa

@rt('/navigate_intro', methods=['POST'])
async def navigate_intro_page_endpoint(request): ...  # noqa

@rt('/poke-flyout', methods=['GET'])
async def poke_flyout(request): ...  # noqa

@rt('/poke-flyout-hide', methods=['GET'])
async def poke_flyout_hide(request): ...  # noqa

@rt('/redirect/{path:path}')
def redirect_handler(request): ...  # noqa

@rt('/poke', methods=['POST'])
async def poke_chatbot(): ...  # noqa

@rt('/select_profile', methods=['POST'])
async def select_profile(request): ...  # noqa

@rt('/refresh-profile-menu')
async def refresh_profile_menu(request): ...  # noqa

@rt('/switch_environment', methods=['POST'])
async def switch_environment(request): ...  # noqa

# These methods are used through the plugin system and dynamic routing
class Pipulate:  # noqa
    def workflow(self, message, details=None): ...  # noqa
    def append_to_history(self, message, role="system", quiet=True): ...  # noqa
    def mark_step_complete(self, step_num): ...  # noqa
    def mark_step_started(self, step_num): ...  # noqa
    def make_singular(self, word): ...  # noqa
    def set_chat(self, chat_instance): ...  # noqa
    def get_message_queue(self): ...  # noqa
    def widget_container(self, step_id, app_name, steps, message=None, widget=None, target_id=None, revert_label=None, widget_style=None): ...  # noqa
    def tree_display(self, content): ...  # noqa
    def finalized_content(self, message, content=None, heading_tag=H4, content_style=None): ...  # noqa
    def generate_pipeline_key(self, plugin_instance, user_input=None): ...  # noqa
    def parse_pipeline_key(self, pipeline_key): ...  # noqa
    def validate_step_input(self, value, step_show, custom_validator=None): ...  # noqa
    def set_step_data(self, pipeline_id, step_id, step_value, steps, clear_previous=True): ...  # noqa
    def check_finalize_needed(self, step_index, steps): ...  # noqa
    def create_step_navigation(self, step_id, step_index, steps, app_name, processed_val): ...  # noqa
    def handle_finalized_step(self, pipeline_id, step_id, steps, app_name, plugin_instance=None): ...  # noqa
    def finalize_workflow(self, pipeline_id, state_update=None): ...  # noqa
    def unfinalize_workflow(self, pipeline_id): ...  # noqa

class LogManager:  # noqa
    def send(self, message): ...  # noqa

class BaseCrud:  # noqa
    def get_action_url(self, action, item_id): ...  # noqa

class Chat:  # noqa
    def create_progress_card(self): ...  # noqa 