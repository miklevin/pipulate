# Pipulate Configuration Module
# Centralized configuration to eliminate duplication between server.py and pipeline.py

# Temporary friendly_names to avoid circular imports - TODO: refactor into shared config
friendly_names = {
    'step_01': 'Step 1',
    'step_02': 'Step 2', 
    'step_03': 'Step 3',
    'step_04': 'Step 4',
    'step_05': 'Step 5',
    'step_06': 'Step 6',
    'step_07': 'Step 7',
    'step_08': 'Step 8',
    'step_09': 'Step 9',
    'step_10': 'Step 10',
    'step_analysis': 'Analysis',
    'step_visualization': 'Visualization',
    'step_configuration': 'Configuration',
    'step_download': 'Download',
    'step_processing': 'Processing'
}

# Default configuration values (will be overridden by server.py with instance-specific values)
DEFAULT_ACTIVE_ROLES = {'Core'}
HOME_MENU_ITEM = '👥 Roles (Home)'

# Complete centralized configuration - single source of truth
PCONFIG = {
    # UI & Navigation
    'HOME_MENU_ITEM': HOME_MENU_ITEM,
    'DEFAULT_ACTIVE_ROLES': DEFAULT_ACTIVE_ROLES,
    
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
            'STEP_COMPLETE': '✅', 
            'STEP_PROGRESS': '🔄',      # Step in progress
            'STEP_ERROR': '❌',          # Step error
            'STEP_WARNING': '⚠️',       # Step warning
            'REVERT': '↩️',              # Revert action
            'FINALIZE': '🔒',           # Finalize workflow
            'UNFINALIZE': '🔓'          # Unfinalize workflow
        },
        'CONSOLE_MESSAGES': {
            # Server console log messages - centralized for consistency
            'PYTHON_SNIPPET_INTRO': '{python_emoji} Python Snippet BEGIN {snippet_emoji}:',
            'PYTHON_SNIPPET_END': '{python_emoji} Python Snippet END {snippet_emoji}',
            'API_CALL_LOG': 'API Call: {method} {url}',
            'FILE_GENERATED': 'Generated file: {filename}',
            'PROCESSING_COMPLETE': 'Processing complete for: {operation}',
            'ERROR_OCCURRED': 'Error in {context}: {error_message}'
        },
        'CODE_FORMATTING': {
            # Visual dividers and separators for generated code
            'COMMENT_DIVIDER': '#' * 50
        },
        'MESSAGES': {
            'WORKFLOW_UNLOCKED': 'Workflow unfinalized! You can now revert to any step and make changes.',
            'ALL_STEPS_COMPLETE': 'All steps complete. Ready to finalize workflow.',
            'FINALIZE_QUESTION': 'All steps complete. Finalize?',
            'FINALIZE_HELP': 'You can revert to any step and make changes.',
            'WORKFLOW_LOCKED': 'Workflow is locked.',
            'STEP_COMPLETE': 'Step complete. Continue to next step.',
            'WORKFLOW_FINALIZED': 'Workflow finalized successfully.',
            'PROCESSING': 'Processing...',
            'PLEASE_WAIT': 'Please wait while processing...'
        },
        'LANDING_PAGE': {
            'INPUT_PLACEHOLDER': 'Existing or new 🗝 here (Enter for auto)',
            'INIT_MESSAGE_WORKFLOW_ID': 'Workflow ID: {pipeline_id}',
            'INIT_MESSAGE_RETURN_HINT': "Return later by selecting '{pipeline_id}' from the dropdown."
        }
    },
    
    # SVG Icons Configuration
    'SVG_ICONS': {
        'CLIPBOARD': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
    }
} 