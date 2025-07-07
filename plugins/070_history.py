"""
Discussion History Viewer Plugin

A utility plugin for viewing and managing conversation history from the 
append-only conversation system. Provides a chronological view of all 
conversations with copy-to-clipboard functionality.

This plugin follows the "weird plugin" pattern - it's a utility app that
gets FastHTML navigation wrapping but doesn't follow the standard workflow structure.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from fasthtml.common import *

# Add helpers to path for conversation system access
helpers_dir = Path(__file__).parent.parent / 'helpers'
sys.path.insert(0, str(helpers_dir))

try:
    from append_only_conversation import get_conversation_system
    CONVERSATION_SYSTEM_AVAILABLE = True
except ImportError:
    CONVERSATION_SYSTEM_AVAILABLE = False

ROLES = ['Core', 'Developer']

logger = logging.getLogger(__name__)

class HistoryViewer:
    """
    Discussion History Viewer
    
    Provides a comprehensive view of conversation history using the append-only
    conversation system. Features include:
    - Chronological message display
    - Role-based filtering
    - Copy-to-clipboard functionality
    - Conversation statistics
    - Session tracking
    """
    
    APP_NAME = 'history'
    DISPLAY_NAME = 'Discussion History 💬'
    ENDPOINT_MESSAGE = """📜 Discussion History Viewer: Browse and manage your complete conversation history. View all messages chronologically, filter by role (user/assistant/system), copy individual messages or entire conversations to clipboard, and see conversation statistics. All data is preserved using the bulletproof append-only architecture."""
    
    # UI styling constants
    UI_CONSTANTS = {
        'COLORS': {
            'USER_MESSAGE': '#e3f2fd',      # Light blue for user messages
            'ASSISTANT_MESSAGE': '#f3e5f5', # Light purple for assistant messages  
            'SYSTEM_MESSAGE': '#e8f5e8',    # Light green for system messages
            'BORDER_COLOR': '#dee2e6',      # Light gray for borders
            'TIMESTAMP_COLOR': '#6c757d',   # Muted gray for timestamps
            'COPY_BUTTON': '#007bff',       # Blue for copy buttons
        },
        'SPACING': {
            'MESSAGE_MARGIN': '1rem 0',
            'MESSAGE_PADDING': '1rem',
            'BORDER_RADIUS': '8px',
        }
    }
    
    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"HistoryViewer initialized with NAME: {self.APP_NAME}")
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        
        # Register routes for the history viewer
        self.app.route(f'/{self.APP_NAME}', methods=['GET'])(self.landing)
        self.app.route(f'/{self.APP_NAME}/refresh', methods=['GET'])(self.refresh_history)
        self.app.route(f'/{self.APP_NAME}/filter', methods=['POST'])(self.filter_messages)
        self.app.route(f'/{self.APP_NAME}/copy', methods=['POST'])(self.copy_to_clipboard)
    
    async def landing(self, request):
        """Main history viewer page"""
        if not CONVERSATION_SYSTEM_AVAILABLE:
            return self.render_error_page("Conversation system not available")
        
        try:
            conv_system = get_conversation_system()
            stats = conv_system.get_conversation_stats()
            messages = conv_system.get_conversation_list()
            
            return self.render_history_page(messages, stats)
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return self.render_error_page(f"Error loading conversation history: {e}")
    
    async def refresh_history(self, request):
        """Refresh the history display"""
        return await self.landing(request)
    
    async def filter_messages(self, request):
        """Filter messages by role"""
        if not CONVERSATION_SYSTEM_AVAILABLE:
            return self.render_error_page("Conversation system not available")
        
        try:
            form = await request.form()
            role_filter = form.get('role_filter', 'all')
            
            conv_system = get_conversation_system()
            stats = conv_system.get_conversation_stats()
            all_messages = conv_system.get_conversation_list()
            
            if role_filter != 'all':
                filtered_messages = [msg for msg in all_messages if msg.get('role') == role_filter]
            else:
                filtered_messages = all_messages
            
            return self.render_messages_section(filtered_messages, stats, role_filter)
            
        except Exception as e:
            logger.error(f"Error filtering messages: {e}")
            return self.render_error_page(f"Error filtering messages: {e}")
    
    async def copy_to_clipboard(self, request):
        """Handle copy to clipboard requests"""
        form = await request.form()
        copy_type = form.get('copy_type', 'message')
        message_index = form.get('message_index', '')
        
        try:
            conv_system = get_conversation_system()
            messages = conv_system.get_conversation_list()
            
            if copy_type == 'message' and message_index.isdigit():
                # Copy single message
                idx = int(message_index)
                if 0 <= idx < len(messages):
                    message = messages[idx]
                    content = self.format_message_for_clipboard(message)
                    return self.render_copy_success(f"Message {idx + 1} copied to clipboard", content)
            
            elif copy_type == 'all':
                # Copy entire conversation
                content = self.format_conversation_for_clipboard(messages)
                return self.render_copy_success("Entire conversation copied to clipboard", content)
            
            return self.render_copy_error("Invalid copy request")
            
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return self.render_copy_error(f"Error: {e}")
    
    def render_history_page(self, messages, stats):
        """Render the complete history page"""
        return Div(
            H2(self.DISPLAY_NAME),
            P(self.ENDPOINT_MESSAGE, cls='text-secondary'),
            
            # Statistics section
            self.render_stats_section(stats),
            
            # Controls section  
            self.render_controls_section(),
            
            # Messages section (main content)
            Div(
                id='messages-container',
                hx_target='this',
                hx_swap='innerHTML'
            )(
                self.render_messages_section(messages, stats)
            ),
            
            # Copy functionality scripts
            self.render_copy_scripts(),
            
            id=f'{self.APP_NAME}-container'
        )
    
    def render_stats_section(self, stats):
        """Render conversation statistics"""
        role_distribution = stats.get('role_distribution', {})
        total_messages = stats.get('total_messages', 0)
        avg_length = stats.get('average_message_length', 0)
        
        return Card(
            H3("📊 Conversation Statistics"),
            Div(
                Div(f"📝 Total Messages: {total_messages}", cls='stat-item'),
                Div(f"👤 User: {role_distribution.get('user', 0)}", cls='stat-item'),
                Div(f"🤖 Assistant: {role_distribution.get('assistant', 0)}", cls='stat-item'),
                Div(f"⚙️ System: {role_distribution.get('system', 0)}", cls='stat-item'),
                Div(f"📏 Avg Length: {avg_length:.0f} chars", cls='stat-item'),
                style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 1rem;"
            ),
            cls='mb-3'
        )
    
    def render_controls_section(self):
        """Render filter and action controls"""
        return Card(
            H3("🔧 Controls"),
            Div(
                # Filter controls
                Form(
                    Label("Filter by Role:", _for='role_filter'),
                    Select(
                        Option("All Messages", value='all', selected=True),
                        Option("User Messages", value='user'),
                        Option("Assistant Messages", value='assistant'),
                        Option("System Messages", value='system'),
                        name='role_filter',
                        id='role_filter',
                        hx_post=f'/{self.APP_NAME}/filter',
                        hx_target='#messages-container',
                        hx_swap='innerHTML'
                    ),
                    cls='filter-form'
                ),
                
                # Action buttons
                Div(
                    Button(
                        "🔄 Refresh",
                        hx_get=f'/{self.APP_NAME}/refresh',
                        hx_target=f'#{self.APP_NAME}-container',
                        hx_swap='innerHTML',
                        cls='secondary'
                    ),
                    Button(
                        "📋 Copy All",
                        onclick="copyEntireConversation()",
                        cls='primary'
                    ),
                    style="display: flex; gap: 0.5rem; margin-top: 1rem;"
                ),
                
                style="display: flex; justify-content: space-between; align-items: flex-start;"
            ),
            cls='mb-3'
        )
    
    def render_messages_section(self, messages, stats, role_filter='all'):
        """Render the messages display section"""
        if not messages:
            return Div(
                H3("📭 No Messages Found"),
                P("No conversation history available yet."),
                cls='text-center'
            )
        
        message_elements = []
        for i, message in enumerate(messages):
            message_elements.append(self.render_single_message(message, i))
        
        filter_info = f"Showing {len(messages)} messages" + (f" (filtered by: {role_filter})" if role_filter != 'all' else "")
        
        return Div(
            P(filter_info, cls='text-secondary mb-2'),
            Div(*message_elements, cls='messages-list'),
            id='messages-display'
        )
    
    def render_single_message(self, message, index):
        """Render a single message with styling based on role"""
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            display_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            display_time = timestamp
        
        # Choose background color based on role
        bg_color = self.UI_CONSTANTS['COLORS'].get(f'{role.upper()}_MESSAGE', '#f8f9fa')
        
        # Role icon
        role_icons = {
            'user': '👤',
            'assistant': '🤖', 
            'system': '⚙️'
        }
        role_icon = role_icons.get(role, '❓')
        
        return Div(
            Div(
                # Message header
                Div(
                    Span(f"{role_icon} {role.title()}", style="font-weight: bold;"),
                    Span(display_time, style=f"color: {self.UI_CONSTANTS['COLORS']['TIMESTAMP_COLOR']}; font-size: 0.9em;"),
                    Button(
                        "📋",
                        onclick=f"copyMessage({index})",
                        title="Copy message to clipboard",
                        style=f"background: {self.UI_CONSTANTS['COLORS']['COPY_BUTTON']}; color: white; border: none; border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.8em;",
                        type='button'
                    ),
                    style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;"
                ),
                
                # Message content
                Div(
                    Pre(content, style="white-space: pre-wrap; margin: 0; font-family: inherit;"),
                    style="line-height: 1.5;"
                ),
                
                style=f"""
                    background-color: {bg_color};
                    border: 1px solid {self.UI_CONSTANTS['COLORS']['BORDER_COLOR']};
                    border-radius: {self.UI_CONSTANTS['SPACING']['BORDER_RADIUS']};
                    padding: {self.UI_CONSTANTS['SPACING']['MESSAGE_PADDING']};
                    margin: {self.UI_CONSTANTS['SPACING']['MESSAGE_MARGIN']};
                """
            ),
            data_message_index=str(index),
            data_message_content=content,
            data_message_role=role,
            data_message_timestamp=timestamp
        )
    
    def render_copy_scripts(self):
        """Render JavaScript for copy functionality"""
        return Script(f"""
            function copyMessage(index) {{
                const messageDiv = document.querySelector(`[data-message-index="${{index}}"]`);
                if (!messageDiv) return;
                
                const role = messageDiv.getAttribute('data-message-role');
                const timestamp = messageDiv.getAttribute('data-message-timestamp');
                const content = messageDiv.getAttribute('data-message-content');
                
                const formattedMessage = `${{role.toUpperCase()}} (${{timestamp}}):\\n${{content}}\\n`;
                
                navigator.clipboard.writeText(formattedMessage).then(() => {{
                    showCopySuccess(`Message ${{parseInt(index) + 1}} copied to clipboard`);
                }}).catch(() => {{
                    showCopyError('Failed to copy message');
                }});
            }}
            
            function copyEntireConversation() {{
                const messages = document.querySelectorAll('[data-message-index]');
                let conversation = '';
                
                messages.forEach((messageDiv, i) => {{
                    const role = messageDiv.getAttribute('data-message-role');
                    const timestamp = messageDiv.getAttribute('data-message-timestamp');
                    const content = messageDiv.getAttribute('data-message-content');
                    
                    conversation += `${{role.toUpperCase()}} (${{timestamp}}):\\n${{content}}\\n\\n`;
                }});
                
                navigator.clipboard.writeText(conversation).then(() => {{
                    showCopySuccess(`Entire conversation (${{messages.length}} messages) copied to clipboard`);
                }}).catch(() => {{
                    showCopyError('Failed to copy conversation');
                }});
            }}
            
            function showCopySuccess(message) {{
                const notification = document.createElement('div');
                notification.textContent = '✅ ' + message;
                notification.style.cssText = `
                    position: fixed; top: 20px; right: 20px; 
                    background: #28a745; color: white; 
                    padding: 1rem; border-radius: 4px; 
                    z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                `;
                document.body.appendChild(notification);
                setTimeout(() => notification.remove(), 3000);
            }}
            
            function showCopyError(message) {{
                const notification = document.createElement('div');
                notification.textContent = '❌ ' + message;
                notification.style.cssText = `
                    position: fixed; top: 20px; right: 20px; 
                    background: #dc3545; color: white; 
                    padding: 1rem; border-radius: 4px; 
                    z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                `;
                document.body.appendChild(notification);
                setTimeout(() => notification.remove(), 3000);
            }}
        """)
    
    def render_error_page(self, error_message):
        """Render error page when conversation system is unavailable"""
        return Div(
            H2(self.DISPLAY_NAME),
            Card(
                H3("❌ Error"),
                P(error_message),
                P("The conversation history feature requires the append-only conversation system to be available."),
                cls='error-card'
            ),
            id=f'{self.APP_NAME}-container'
        )
    
    def render_copy_success(self, message, content):
        """Render success response for copy operations"""
        return Div(
            P(f"✅ {message}", cls='text-success'),
            style="padding: 1rem; background: #d4edda; border-radius: 4px; margin: 1rem 0;"
        )
    
    def render_copy_error(self, message):
        """Render error response for copy operations"""
        return Div(
            P(f"❌ {message}", cls='text-danger'),
            style="padding: 1rem; background: #f8d7da; border-radius: 4px; margin: 1rem 0;"
        )
    
    def format_message_for_clipboard(self, message):
        """Format a single message for clipboard"""
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        return f"{role.upper()} ({timestamp}):\n{content}\n"
    
    def format_conversation_for_clipboard(self, messages):
        """Format entire conversation for clipboard"""
        formatted_messages = []
        for message in messages:
            formatted_messages.append(self.format_message_for_clipboard(message))
        
        return "\n".join(formatted_messages) 