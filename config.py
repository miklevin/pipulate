"""
Centralized Configuration for the Pipulate Digital Workshop.

This module holds instance-specific settings, UI constants, and other
configurations that customize this particular Pipulate instance.
Externalizing this config allows for easier white-labeling, theming,
and management, and avoids circular dependencies between server.py,
common.py, and mcp_tools.py.
"""

# ================================================================
# INSTANCE-SPECIFIC CONFIGURATION - "The Crucible"
# ================================================================
# This dictionary holds settings that customize this particular Pipulate instance.
# Moving configuration here allows for easy white-labeling and configuration management.
# Over time, more instance-specific "slag" will be skimmed from plugins to here.

PCONFIG = {
    # UI & Navigation
    'HOME_MENU_ITEM': 'Roles️ 👥',
    'DEFAULT_ACTIVE_ROLES': {'Botify Employee', 'Core'},
    
    # Role System Configuration
    'ROLES_CONFIG': {
        'Botify Employee': {
            'priority': 0, 
            'description': 'Connect with Botify to use Parameter Buster and Link Graph Visualizer.',
            'emoji': '👔'
        },
        'Core': {
            'priority': 1, 
            'description': 'Essential plugins available to all users.',
            'emoji': '⚙️'
        },
        'Tutorial': {
            'priority': 2, 
            'description': 'Guided workflows and introductory examples for learning the system.',
            'emoji': '📚'
        },
        'Developer': {
            'priority': 3, 
            'description': 'Tools for creating, debugging, and managing workflows and plugins.',
            'emoji': '⚡'
        },
        'Workshop': {
            'priority': 4, 
            'description': 'This is where we put works in progress, proof of concepts and crazy stuff not ready for release. Consider it the sausage factory.',
            'emoji': '🔬'
        },
        'Components': {
            'priority': 5, 
            'description': 'UI and data widgets for building rich workflow interfaces.',
            'emoji': '🧩'
        }
    },
    
    # Role Color Configuration
    'ROLE_COLORS': {
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
    
    # Botify API Configuration
    'BOTIFY_API': {
        'MAX_EXPORT_SIZE': 1000000,  # Botify's maximum export size limit (1M rows)
        'DEFAULT_EXPORT_SIZE': 1000000,  # Conservative default for testing/development
        'GSC_EXPORT_SIZE': 1000000,  # GSC can handle full export size
        'WEBLOG_EXPORT_SIZE': 1000000,  # Web logs can handle full export size
        'CRAWL_EXPORT_SIZE': 1000000,  # Crawl exports can handle full export size
    },
    
    # Chat & Streaming Configuration
    'CHAT_CONFIG': {
        'TYPING_DELAY': 0.0125,  # Delay between words in typing simulation (seconds)
        'MAX_CONVERSATION_LENGTH': 100,  # Maximum number of conversation messages to keep
    },
    
    # UI Constants for Workflows - Centralized button labels, emojis, and styles
    'UI_CONSTANTS': {
        'BUTTON_LABELS': {
            'ENTER_KEY': '🔑 Enter Key',
            'NEW_KEY': '🆕',
            'NEXT_STEP': 'Next Step ▸',
            'FINALIZE': '🔒 Finalize',
            'UNLOCK': '🔓 Unlock',
            'PROCEED': 'Proceed ▸',
            'HIDE_SHOW_CODE': '🐍 Hide/Show Code',
            'VIEW_FOLDER': '📂 View Folder',
            'DOWNLOAD_CSV': '⬇️ Copy to Downloads',
            'VISUALIZE_GRAPH': '🌐 Visualize Graph',
            'SKIP_STEP': 'Skip️'
        },
        'BUTTON_STYLES': {
            'PRIMARY': 'primary',
            'SECONDARY': 'secondary',
            'OUTLINE': 'secondary outline',
            'STANDARD': 'secondary outline',
            'FLEX_CONTAINER': 'display: flex; gap: var(--pipulate-gap-sm); flex-wrap: wrap; align-items: center;',
            'BUTTON_ROW': 'display: flex; gap: var(--pipulate-gap-sm); align-items: center;',
            'SKIP_BUTTON': 'secondary outline',
            'SKIP_BUTTON_STYLE': 'padding: 0.5rem 1rem; width: 10%; min-width: 80px; white-space: nowrap;',
            'BORDER_RADIUS': 'var(--pico-border-radius)'  # Global button roundedness control
        },
        'EMOJIS': {
            # Process Status Indicators
            'KEY': '🔑',
            'SUCCESS': '🎯',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'COMPLETION': '✅',
            'LOCKED': '🔒',
            'UNLOCKED': '🔓',
            
            # Data Type Indicators  
            'USER_INPUT': '👤',
            'GREETING': '💬',
            'WORKFLOW': '🔄',
            'INPUT_FORM': '📝',
            
            # Code and Development Indicators
            'PYTHON_CODE': '🐍',           # Python code snippets and headers
            'CODE_SNIPPET': '✂️',         # Code snippet indicator
            'JUPYTER_NOTEBOOK': '📓',     # Jupyter notebook related
            'API_CALL': '🔌',             # API endpoint calls
            'DEBUG_CODE': '🐛',           # Debugging code sections
            
            # File and Data Operations
            'DOWNLOAD': '⬇️',             # Download operations
            'UPLOAD': '⬆️',               # Upload operations
            'FILE_FOLDER': '📂',          # File/folder operations
            'CSV_FILE': '📊',             # CSV and data files
            'JSON_DATA': '📄',            # JSON and structured data
            
            # Analysis and Processing
            'ANALYSIS': '🔍',             # Data analysis and discovery
            'PROCESSING': '⚙️',          # Background processing
            'OPTIMIZATION': '🎯',        # Optimization results
            'GRAPH_NETWORK': '🌐',       # Network/graph visualization
            'VISUALIZATION': '📈',       # Charts and visualizations
            
            # Search Console and SEO
            'SEARCH_CONSOLE': '🔍',      # Google Search Console
            'SEO_DATA': '📊',            # SEO metrics and data
            'CRAWL_DATA': '🕷️',         # Website crawling
            'WEB_LOGS': '📝',            # Web server logs
            
            # Workflow Status
            'STEP_COMPLETE': '✅',       # Step completion
            'STEP_PROGRESS': '🔄',      # Step in progress
            'STEP_ERROR': '❌',          # Step error
            'STEP_WARNING': '⚠️',       # Step warning
            'REVERT': '↩️',              # Revert action
            'FINALIZE': '🔒',           # Finalize workflow
            'UNFINALIZE': '🔓'          # Unfinalize workflow
        },
        'CONSOLE_MESSAGES': {
            # Server console log messages - centralized for consistency
            'PYTHON_SNIPPET_INTRO': '# {python_emoji} Python (httpx) Snippet BEGIN {snippet_emoji}:',
            'PYTHON_SNIPPET_END': '# {python_emoji} Python (httpx) Snippet END {snippet_emoji}',
            'API_CALL_LOG': 'API Call: {method} {url}',
            'FILE_GENERATED': 'Generated file: {filename}',
            'PROCESSING_COMPLETE': 'Processing complete for: {operation}',
            'ERROR_OCCURRED': 'Error in {context}: {error_message}'
        },
        'CODE_FORMATTING': {
            # Visual dividers and separators for generated code
            'COMMENT_DIVIDER': '# ============================================================================='
        },
        'MESSAGES': {
            'WORKFLOW_UNLOCKED': 'Workflow unfinalized! You can now revert to any step and make changes.',
            'ALL_STEPS_COMPLETE': 'All steps complete. Ready to finalize workflow.',
            'FINALIZE_QUESTION': 'All steps complete. Finalize?',
            'FINALIZE_HELP': 'You can revert to any step and make changes.',
            'WORKFLOW_LOCKED': 'Workflow is locked.'
        },
        'LANDING_PAGE': {
            'INPUT_PLACEHOLDER': 'Existing or new 🗝 here (Enter for auto)',
            'INIT_MESSAGE_WORKFLOW_ID': 'Workflow ID: {pipeline_id}',
            'INIT_MESSAGE_RETURN_HINT': "Return later by selecting '{pipeline_id}' from the dropdown."
        }
    },
    
    # SVG Icons - Centralized icon definitions
    'SVG_ICONS': {
        'INFO': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-info"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>''',
        'EXTERNAL_LINK': '''<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-external-link"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>''',
        'CLIPBOARD': '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-clipboard"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>''',
        'SETTINGS': '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'''
    }
} 