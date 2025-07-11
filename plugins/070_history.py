"""
Discussion History Plugin

Provides a comprehensive view of conversation history using the append-only
conversation system. Features include:
- Chronological message display with proper site navigation
- Role-based filtering (user/assistant/system)
- Copy-to-clipboard functionality
- Conversation statistics
- Session tracking
- PicoCSS-consistent color scheme
"""

import logging
import asyncio
from datetime import datetime
from fasthtml.common import *
from pathlib import Path

ROLES = ['Core']

logger = logging.getLogger(__name__)

# Import the append-only conversation system
try:
    from helpers.append_only_conversation import (
        get_conversation_history, 
        get_conversation_stats
    )
    CONVERSATION_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Append-only conversation system not available: {e}")
    CONVERSATION_SYSTEM_AVAILABLE = False

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
    
    # PicoCSS-consistent UI styling constants
    UI_CONSTANTS = {
        'user_color': 'var(--pico-primary-background)',
        'assistant_color': 'var(--pico-secondary-background)', 
        'system_color': 'var(--pico-color)',
        'background_color': 'var(--pico-background-color)',
        'border_color': 'var(--pico-border-color)',
        'text_color': 'var(--pico-color)',
        'muted_color': 'var(--pico-muted-color)',
        'border_radius': 'var(--pico-border-radius)',
        'spacing': 'var(--pico-spacing)',
        'card_background': 'var(--pico-card-background-color)',
        'card_border': 'var(--pico-card-border-color)'
    }

    def __init__(self, app, pipulate, pipeline, db):
        logger.debug(f"HistoryViewer initialized with APP_NAME: {self.APP_NAME}")
        self.app = app
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.db = db
        
        # Register HTMX interaction routes (utility plugin pattern)
        app.route('/history/refresh', methods=['GET'])(self.refresh_history)
        app.route('/history/filter', methods=['POST'])(self.filter_messages)
        app.route('/history/copy', methods=['POST'])(self.copy_to_clipboard)

    async def landing(self, request):
        """
        Main landing page with proper navigation integration.
        This method ensures the history viewer gets the standard site navigation.
        """
        try:
            # Get conversation data
            messages = []
            stats = {'total_messages': 0, 'role_distribution': {}, 'avg_length': 0}
            
            logger.debug(f"Conversation system available: {CONVERSATION_SYSTEM_AVAILABLE}")
            
            if CONVERSATION_SYSTEM_AVAILABLE:
                messages = await get_conversation_history()
                stats = await get_conversation_stats()
                logger.debug(f"Retrieved {len(messages)} messages from conversation system")
                logger.debug(f"Stats: {stats}")
            else:
                logger.warning("Conversation system not available")
            
            # Create the main content
            content = self.render_history_page(messages, stats)
            return content
            
        except Exception as e:
            logger.error(f"Error in history landing: {e}")
            return self.render_error_page(f"Error loading history: {str(e)}")



    async def refresh_history(self, request):
        """Refresh the history display"""
        return await self.landing(request)

    async def filter_messages(self, request):
        """Filter messages by role"""
        try:
            form_data = await request.form()
            role_filter = form_data.get('role', 'all')
            
            if not CONVERSATION_SYSTEM_AVAILABLE:
                return self.render_error_page("Conversation system not available")
            
            messages = await get_conversation_history()
            stats = await get_conversation_stats()
            
            # Filter messages if needed
            if role_filter != 'all':
                messages = [msg for msg in messages if msg.get('role') == role_filter]
            
            return self.render_messages_section(messages, stats, role_filter)
            
        except Exception as e:
            logger.error(f"Error filtering messages: {e}")
            return self.render_error_page(f"Error filtering messages: {str(e)}")

    async def copy_to_clipboard(self, request):
        """Handle copy to clipboard requests"""
        try:
            form_data = await request.form()
            copy_type = form_data.get('type', 'message')
            
            if copy_type == 'conversation':
                if not CONVERSATION_SYSTEM_AVAILABLE:
                    return self.render_copy_error("Conversation system not available")
                
                messages = await get_conversation_history()
                content = self.format_conversation_for_clipboard(messages)
                return self.render_copy_success("Entire conversation copied to clipboard!", content)
            
            elif copy_type == 'message':
                message_index = int(form_data.get('index', 0))
                if not CONVERSATION_SYSTEM_AVAILABLE:
                    return self.render_copy_error("Conversation system not available")
                
                messages = await get_conversation_history()
                if 0 <= message_index < len(messages):
                    message = messages[message_index]
                    content = self.format_message_for_clipboard(message)
                    return self.render_copy_success(f"Message {message_index + 1} copied to clipboard!", content)
                else:
                    return self.render_copy_error("Message not found")
            
            return self.render_copy_error("Invalid copy request")
            
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return self.render_copy_error(f"Error: {str(e)}")

    def render_history_page(self, messages, stats):
        """Render the complete history page"""
        return Div(
            self.render_stats_section(stats),
            self.render_controls_section(),
            self.render_messages_section(messages, stats),
            self.render_copy_scripts(),
            id="history-container",
            style=f"""
                padding: {self.UI_CONSTANTS['spacing']};
                background-color: {self.UI_CONSTANTS['background_color']};
                color: {self.UI_CONSTANTS['text_color']};
                min-height: 100vh;
            """
        )

    def render_stats_section(self, stats):
        """Render the statistics section"""
        role_badges = []
        for role, count in stats.get('role_distribution', {}).items():
            icon = {'user': '👤', 'assistant': '🤖', 'system': '⚙️'}.get(role, '❓')
            role_badges.append(
                Span(
                    f"{icon} {role.title()}: {count}",
                    style=f"""
                        display: inline-block;
                        margin-right: {self.UI_CONSTANTS['spacing']};
                        padding: 0.25rem 0.5rem;
                        background-color: {self.UI_CONSTANTS['card_background']};
                        border: 1px solid {self.UI_CONSTANTS['border_color']};
                        border-radius: {self.UI_CONSTANTS['border_radius']};
                        font-size: 0.85rem;
                    """
                )
            )
        
        return Card(
            H3("📊 Conversation Statistics", style=f"color: {self.UI_CONSTANTS['text_color']}; margin-bottom: 1rem;"),
            Div(
                Div(f"📈 Total Messages: {stats.get('total_messages', 0)}", style="margin-bottom: 0.5rem;"),
                Div(f"📏 Average Length: {stats.get('avg_length', 0):.0f} characters", style="margin-bottom: 0.5rem;"),
                Div(*role_badges, style="margin-top: 1rem;"),
                style=f"color: {self.UI_CONSTANTS['text_color']};"
            ),
            style=f"""
                background-color: {self.UI_CONSTANTS['card_background']};
                border: 1px solid {self.UI_CONSTANTS['card_border']};
                margin-bottom: 1rem;
            """
        )

    def render_controls_section(self):
        """Render the filter and action controls"""
        return Card(
            H4("🎛️ Controls", style=f"color: {self.UI_CONSTANTS['text_color']}; margin-bottom: 1rem;"),
            Div(
                # Filter controls
                Div(
                    Label("Filter by Role:", style=f"color: {self.UI_CONSTANTS['text_color']}; margin-right: 0.5rem;"),
                    Select(
                        Option("All Messages", value="all"),
                        Option("👤 User Messages", value="user"),
                        Option("🤖 Assistant Messages", value="assistant"),
                        Option("⚙️ System Messages", value="system"),
                        name="role",
                        hx_post="/history/filter",
                        hx_target="#messages-container",
                        hx_swap="outerHTML",
                        style=f"""
                            margin-right: 1rem;
                            background-color: {self.UI_CONSTANTS['card_background']};
                            border: 1px solid {self.UI_CONSTANTS['border_color']};
                            color: {self.UI_CONSTANTS['text_color']};
                        """
                    ),
                    style="display: inline-block; margin-right: 1rem;"
                ),
                # Action buttons
                Div(
                    Button(
                        "🔄 Refresh",
                        hx_get="/history/refresh",
                        hx_target="#history-container",
                        hx_swap="outerHTML",
                        style=f"""
                            margin-right: 0.5rem;
                            background-color: {self.UI_CONSTANTS['user_color']};
                            border: 1px solid {self.UI_CONSTANTS['border_color']};
                            color: white;
                        """
                    ),
                    Button(
                        "📋 Copy All",
                        onclick="copyConversation()",
                        style=f"""
                            background-color: {self.UI_CONSTANTS['assistant_color']};
                            border: 1px solid {self.UI_CONSTANTS['border_color']};
                            color: white;
                        """
                    ),
                    style="display: inline-block;"
                ),
                style="display: flex; align-items: center; gap: 1rem;"
            ),
            style=f"""
                background-color: {self.UI_CONSTANTS['card_background']};
                border: 1px solid {self.UI_CONSTANTS['card_border']};
                margin-bottom: 1rem;
            """
        )

    def render_messages_section(self, messages, stats, role_filter='all'):
        """Render the messages section"""
        if not messages:
            return Div(
                Card(
                    H4("📭 No Messages", style=f"color: {self.UI_CONSTANTS['text_color']};"),
                    P("No conversation history found.", style=f"color: {self.UI_CONSTANTS['muted_color']};"),
                    style=f"""
                        background-color: {self.UI_CONSTANTS['card_background']};
                        border: 1px solid {self.UI_CONSTANTS['card_border']};
                        text-align: center;
                    """
                ),
                id="messages-container"
            )
        
        message_elements = []
        for i, message in enumerate(messages):
            message_elements.append(self.render_single_message(message, i))
        
        return Div(
            H4(f"💬 Messages ({len(messages)})", style=f"color: {self.UI_CONSTANTS['text_color']}; margin-bottom: 1rem;"),
            Div(*message_elements, style="display: flex; flex-direction: column; gap: 0.5rem;"),
            id="messages-container"
        )

    def render_single_message(self, message, index):
        """Render a single message"""
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        # Role-specific styling
        role_styles = {
            'user': {
                'icon': '👤',
                'color': self.UI_CONSTANTS['user_color'],
                'border_color': self.UI_CONSTANTS['user_color']
            },
            'assistant': {
                'icon': '🤖', 
                'color': self.UI_CONSTANTS['assistant_color'],
                'border_color': self.UI_CONSTANTS['assistant_color']
            },
            'system': {
                'icon': '⚙️',
                'color': self.UI_CONSTANTS['system_color'],
                'border_color': self.UI_CONSTANTS['border_color']
            }
        }
        
        role_style = role_styles.get(role, role_styles['system'])
        
        # Format timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = 'Unknown time'
        except:
            formatted_time = str(timestamp)
        
        # Truncate very long messages for display
        display_content = content
        if len(content) > 500:
            display_content = content[:500] + "..."
        
        return Div(
            Div(
                Div(
                    Span(f"{role_style['icon']} {role.title()}", style=f"font-weight: bold; color: {role_style['color']};"),
                    Span(formatted_time, style=f"font-size: 0.8rem; color: {self.UI_CONSTANTS['muted_color']};"),
                    style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;"
                ),
                Pre(
                    display_content,
                    style=f"""
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        padding: 0.75rem;
                        background-color: {self.UI_CONSTANTS['background_color']};
                        border: 1px solid {self.UI_CONSTANTS['border_color']};
                        border-radius: {self.UI_CONSTANTS['border_radius']};
                        color: {self.UI_CONSTANTS['text_color']};
                        font-family: var(--pico-font-family);
                        font-size: 0.9rem;
                        line-height: 1.4;
                    """
                ),
                Button(
                    "📋 Copy",
                    onclick=f"copyMessage({index})",
                    style=f"""
                        margin-top: 0.5rem;
                        padding: 0.25rem 0.5rem;
                        font-size: 0.8rem;
                        background-color: {role_style['color']};
                        border: 1px solid {role_style['border_color']};
                        color: white;
                        border-radius: {self.UI_CONSTANTS['border_radius']};
                    """
                ),
                style=f"""
                    padding: 1rem;
                    background-color: {self.UI_CONSTANTS['card_background']};
                    border: 1px solid {self.UI_CONSTANTS['card_border']};
                    border-left: 4px solid {role_style['color']};
                    border-radius: {self.UI_CONSTANTS['border_radius']};
                """
            ),
            data_message_index=str(index),
            data_message_content=content,  # Store full content for copying
            style="margin-bottom: 0.5rem;"
        )

    def render_copy_scripts(self):
        """Render JavaScript for copy functionality"""
        return Script(f"""
            // Copy individual message
            function copyMessage(index) {{
                const messageDiv = document.querySelector(`[data-message-index="${{index}}"]`);
                if (messageDiv) {{
                    const content = messageDiv.getAttribute('data-message-content');
                    if (content) {{
                        navigator.clipboard.writeText(content).then(() => {{
                            showNotification('Message copied to clipboard!', 'success');
                        }}).catch(err => {{
                            console.error('Failed to copy message:', err);
                            showNotification('Failed to copy message', 'error');
                        }});
                    }}
                }}
            }}
            
            // Copy entire conversation
            function copyConversation() {{
                fetch('/history/copy', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }},
                    body: 'type=conversation'
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success && data.content) {{
                        navigator.clipboard.writeText(data.content).then(() => {{
                            showNotification('Entire conversation copied to clipboard!', 'success');
                        }}).catch(err => {{
                            console.error('Failed to copy conversation:', err);
                            showNotification('Failed to copy conversation', 'error');
                        }});
                    }} else {{
                        showNotification('Failed to copy conversation', 'error');
                    }}
                }})
                .catch(err => {{
                    console.error('Error copying conversation:', err);
                    showNotification('Error copying conversation', 'error');
                }});
            }}
            
            // Show notification
            function showNotification(message, type) {{
                const notification = document.createElement('div');
                notification.textContent = message;
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 1rem;
                    border-radius: {self.UI_CONSTANTS['border_radius']};
                    color: white;
                    font-weight: bold;
                    z-index: 1000;
                    transition: opacity 0.3s ease;
                    background-color: ${{type === 'success' ? '{self.UI_CONSTANTS['user_color']}' : 'var(--pico-del-color)'}};
                `;
                
                document.body.appendChild(notification);
                
                setTimeout(() => {{
                    notification.style.opacity = '0';
                    setTimeout(() => {{
                        document.body.removeChild(notification);
                    }}, 300);
                }}, 3000);
            }}
        """)

    def render_error_page(self, error_message):
        """Render an error page"""
        return Card(
            H3("❌ Error", style=f"color: var(--pico-del-color);"),
            P(error_message, style=f"color: {self.UI_CONSTANTS['text_color']};"),
            P("This may happen if the conversation system is not available.", style=f"color: {self.UI_CONSTANTS['muted_color']};"),
            style=f"""
                background-color: {self.UI_CONSTANTS['card_background']};
                border: 1px solid var(--pico-del-color);
                text-align: center;
                margin: 2rem auto;
                max-width: 500px;
            """
        )

    def render_copy_success(self, message, content):
        """Render copy success response"""
        return {"success": True, "message": message, "content": content}

    def render_copy_error(self, message):
        """Render copy error response"""
        return {"success": False, "message": message}

    def format_message_for_clipboard(self, message):
        """Format a single message for clipboard"""
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        return f"[{role.upper()}] {timestamp}\n{content}\n"

    def format_conversation_for_clipboard(self, messages):
        """Format the entire conversation for clipboard"""
        formatted_messages = []
        for message in messages:
            formatted_messages.append(self.format_message_for_clipboard(message))
        
        return "\n" + "="*50 + "\n".join(formatted_messages) + "="*50 + "\n" 