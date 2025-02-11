# ----------------------------------------------------------------------------------------------------
# Single Tenant Desktop App Framework built on Nix Flakes, FastHTML and Local LLM https://mikelev.in/
# This is localhost software with reproducible environments through Nix.
# Your entire app is DIVs updated by HTMX, your data is simple tables, and your environment is pure.
# Don't fight it - this isn't Electron, FastAPI, or multi-tenant SaaS, and that's the point.
# ----------------------------------------------------------------------------------------------------

'''
ARCHITECTURAL PATTERNS:
1. Single-Tenant: One user, one instance, one database - keeping it simple
2. Nix-First: Reproducible development environments via Nix Flakes
3. Server-Side State: All state managed through DictLikeDB
4. Pipeline Pattern: Card-to-card flow with clear forward on submit
5. LLM Integration: Bounded conversation history with streaming
6. Plugin Architecture: BaseApp foundation for all CRUD operations

See .cursorrules for detailed pattern documentation.
'''

import ast
import asyncio
import functools
import json
import os
import random
import sys
import time
import traceback
from collections import Counter, deque, namedtuple
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional

import aiohttp  # For making asynchronous HTTP requests
import requests  # for making HTTP requests (mostly to Ollama)
import uvicorn  # for running the FastHTML server
from fasthtml.common import *  # the beating heart of the app
from loguru import logger  # for colorful logging
from pyfiglet import Figlet  # for the text art effect
from rich.console import Console  # for colorful text
from rich.json import JSON  # for color-coded JSON
from rich.style import Style as RichStyle  # for black backgrounds
from rich.table import Table, Text  # for colorful tables
from rich.theme import Theme  # for black backgrounds
from starlette.middleware.base import \
    BaseHTTPMiddleware  # for inserting console output
from starlette.middleware.cors import CORSMiddleware  # for handling CORS
from starlette.routing import Route  # for router tricks beyond FastHTML
from starlette.websockets import (  # for handling WebSocket disconnections
    WebSocket, WebSocketDisconnect)
from watchdog.events import FileSystemEventHandler  # for watching files
from watchdog.observers import Observer  # for watching files

# JavaScript & CSS Libraries:
# HTMX https://unpkg.com/htmx.org@2.0.4/dist/htmx.js
# HTMX WebSockets Extension https://unpkg.com/htmx-ext-ws@2.0.1/ws.js
# FastHTML 1.0.12 https://github.com/AnswerDotAI/fasthtml-js/blob/main/fasthtml.js
# Surreal 1.3.2 https://github.com/gnat/surreal/blob/main/surreal.js
# CSS Scope Inline https://github.com/gnat/css-scope-inline/blob/main/script.js
# PicoCSS 2.0.6 https://github.com/picocss/pico/blob/main/css/pico.css
# SortableJS 1.15.6 https://github.com/SortableJS/Sortable/blob/master/Sortable.js

llm_speedbump_dict = {}

llm_speedbump_dict["localhost"] = """
    1. This is NOT about:
    - Client-side state management
    - React components
    - Redux stores
    - JWT tokens
    - Service workers
    - Progressive Web Apps

    2. This IS about:
    - Server-side state (DictLikeDB + Pipulate)
    - Local resources (VPN, Chrome profiles)
    - Complete observability (server logs)
    - Pipeline patterns (card-to-card flow)
    - HTMX for UI updates only
    - Localhost sovereignty
"""


# Always check if convenience versions are in the FastHTML fast_app definition

LLM_MODELS = {
    # Vision & Multimodal Models
    "bakl": "bakllava:latest",  # (4.7 GB) BakLLaVA: Vision-language model for image understanding and generation
    "benz": "benzie/llava-phi-3:latest",  # (2.9 GB) Benzie's LLaVA-Phi-3: Vision-language model variant
    "llav": "llava:latest",  # (4.7 GB) LLaVA: Multimodal model combining vision and language
    "lphi": "llava-phi3:latest",  # (2.9 GB) LLaVA with Phi-3: Vision-language model using Phi-3 architecture
    "llm3": "llava-llama3:latest",  # (5.5 GB) LLaVA with LLaMA 3: Vision-language model based on LLaMA 3
    "mcpm": "minicpm-v:latest",  # (5.5 GB) MiniCPM-V: Vision-language variant of MiniCPM
    "pixe": "srizon/pixie:latest",  # (9.4 GB) Pixie: Specialized model for image-related tasks

    # DeepSeek models
    "deep": "deepseek-v2:latest",  # (8.9 GB) DeepSeek v2: Advanced language model with strong reasoning capabilities
    "ds32": "deepseek-r1:32b",  # qwen2
    "ds14": "deepseek-r1:14b",  # qwen2
    "ds8b": "deepseek-r1:8b",  # llama
    "ds7b": "deepseek-r1:7b",  # qwen2
    "ds1b": "deepseek-r1:1.5b",  # qwen2

    # Dolphin models
    "dmix": "dolphin-mixtral:latest",  # (26 GB) Dolphin Mixtral: Large-scale model based on Mixtral architecture
    "dphi": "dolphin-phi:latest",  # (1.6 GB) Dolphin Phi: Compact model optimized for efficiency
    "dlm3": "dolphin-llama3:latest",  # (4.7 GB) Dolphin LLaMA 3: Variant of LLaMA 3 with Dolphin's improvements
    "dlp3": "dolphin3:latest",  # Dolphin 3.0 Llama 3.1 8B 🐬 is the next generation of the Dolphin series of instruct-tuned models designed to be the ultimate general purpose local model, enabling coding, math, agentic, function calling, and general use cases.

    # Gemma models
    "g27b": "gemma2:27b",  # (15 GB) Gemma2 27B: Large variant of Google's Gemma model
    "g09b": "gemma2:9b",  # (5.4 GB) Gemma2 9B: Compact variant of Google's Gemma model
    "gemm": "gemma2:2b",  # (5.4 GB) Latest Gemma2: Most recent version of Google's Gemma model

    # Hermes models
    "herm": "hermes3:latest",  # (4.7 GB) Hermes 3: Versatile language model with broad capabilities

    # LLaMA models
    "l2un": "llama2-uncensored:latest",  # (3.8 GB) Uncensored LLaMA 2: Less restricted version of Meta's LLaMA 2
    "l31l": "llama3.1:latest",  # (4.7 GB) LLaMA 3.1: Latest iteration of Meta's LLaMA model
    "l32b": "llama3.2:3b",  # (2.0 GB) LLaMA 3.2 3B: Compact version of LLaMA 3.2
    "l32l": "llama3.2:1b",  # (2.0 GB) Latest LLaMA 3.2: Most recent version of LLaMA 3.2
    "lgtu": "llama3-groq-tool-use:latest",  # (4.7 GB) LLaMA 3 with Groq tool use: Enhanced for tool interaction

    # Miscellaneous models
    "mann": "mannix/llama3.1-8b-abliterated:latest",  # (4.7 GB) Mannix LLaMA 3.1 variant: Customized version of LLaMA 3.1
    "mini": "aiden_lu/minicpm-v2.6:Q4_K_M",  # (5.7 GB) MiniCPM: Compact and efficient language model
    "mist": "mistral:latest",  # (4.1 GB) Mistral: High-performance language model
    "ndev": "closex/neuraldaredevil-8b-abliterated:latest",  # (5.6 GB) NeuralDaredevil: Specialized language model
    "nuex": "nuextract:latest",  # (2.2 GB) NuExtract: Specialized model for information extraction
    "orca": "orca2:latest",  # (3.8 GB) Orca 2: Improved version of the Orca model
    "phi": "phi:latest",  # (1.6 GB) Phi: Base version of Microsoft's Phi model
    "phi3": "phi3.5:latest",  # (2.2 GB) Phi 3.5: Latest version of Microsoft's Phi model
    "qwen": "qwen2:latest",  # (4.4 GB) Qwen 2: Advanced language model from Alibaba
    "solr": "solar-pro:latest",  # (13 GB) Solar Pro: High-performance language model
    "smol": "smollm:latest",  # (1 GB) SmolLM: Compact language model

    # Wizard models
    "wizv": "wizard-vicuna-uncensored:latest",  # (3.8 GB) Wizard Vicuna Uncensored: Less restricted version of Vicuna
    "wizl": "wizardlm-uncensored:latest",  # (7.4 GB) WizardLM Uncensored: Unrestricted version of WizardLM

    # Yi models
    "yiii": "yi:latest",  # (3.5 GB) Yi: Versatile language model from 01.AI
}

# Reverse mapping from full model name to short key
LLM_MODELS_REVERSE = {v: k for k, v in LLM_MODELS.items()}

"""
MODEL NOTES

JSON & LABELERS
- ndev
- qwen Good storyteller, but also wants to do JSON
- benz wants to do JSON
- mist wants to demonstrate its JSON ability 
- orca good long stories followed by labels
- pixe labels

STORY TELLERS
- herm Maybe the best storyteller
- g09b Best storyteller, just right for demonstrating streaming
- gemm also good
- phi long winded stories
- phi3 also long winded stories
- yiii slow to start, but good stories
- mcpm good
- mann
- dphi
- l32l but dumb
- wizv discusses process

TOO SLOW
- solr
- g27b
- l311
- wizl (json and stories)
- dmix

OTHER
- bakl not very talkative
- nuex for extraction / not very talkative
- mini starts out strong
- lphi very restricted
- l32b very restricted
- smol fast but restricted
- llava less restricted but brief
- llm3 less restricted but brief

NOTEWORTHY
- deep just right for demonstrating streaming
- lgtu is very conversational
- l2un is very conversational
- dlm3 conversational dumb
"""


def cycle_llm_model(random=False):
    """Selects an LLM model either randomly or by cycling through available models alphabetically by key.
    Uses a pickle file to maintain state between runs when cycling sequentially."""
    import pickle

    # Get sorted list of model keys
    model_keys = sorted(LLM_MODELS.keys())

    if random:
        # Choose random model key and get corresponding full model name
        selected_key = random.choice(model_keys)
        selected_model = LLM_MODELS[selected_key]
    else:
        # Cycle through model keys sequentially using a refill file
        model_state_file = ".llm_model_state.pkl"
        try:
            with open(model_state_file, 'rb') as f:
                current_key_index = pickle.load(f)
        except (FileNotFoundError, EOFError):
            current_key_index = 0

        selected_key = model_keys[current_key_index]
        selected_model = LLM_MODELS[selected_key]

        # Update and save next index
        next_index = (current_key_index + 1) % len(model_keys)
        with open(model_state_file, 'wb') as f:
            pickle.dump(next_index, f)

    return selected_model


TONE = "neutral"


# Set to False to use the default model
if False:  # Testing multiple models
    # DEFAULT_LLM_MODEL = cycle_llm_model()
    # DEFAULT_LLM_MODEL = cycle_llm_model(random=True)
    SYSTEM_PROMPT_FILE = Path.home() / "system_prompts" / "system_prompt-01.txt"
    DEFAULT_LLM_MODEL = LLM_MODELS["herm"]
    # DEFAULT_LLM_MODEL = LLM_MODELS["ds7b"]
    # End of Selection
    MAX_LLM_RESPONSE_WORDS = 40   # Maximum number of words in LLM response
else:  # Hard-wired configuration
    DEFAULT_LLM_MODEL = LLM_MODELS["gemm"]
    SYSTEM_PROMPT_FILE = None
    MAX_LLM_RESPONSE_WORDS = 60   # Maximum number of words in LLM response


'''
This is not enterprise software. This is local software. There is no client-server architecture.
This is elegant, maintainable, debuggable infrastructure. All in 1 file.
Make it simple. Make it visible. Make it reliable.
Future tinkerers will thank you.

Every endpoint is a plugin app that shows in Main Area.
Apps are roughly equivalent to Jupyter Notebooks.
The code for all of it is in this file.

Layout:

    +-------------------------------------+
    |           Navigation Bar            |
    +-------------------------------------+
    |             Main Content            |
    | +-----------------+ +-------------+ |
    | |                 | |             | |
    | |    Main Area    | |    Chat     | |
    | |   (Grid Left)   | |  Interface  | |
    | |                 | |             | |
    | |                 | |             | |
    | |                 | |             | |
    | +-----------------+ +-------------+ |
    +-------------------------------------+
    |           Poke Button               |
    +-------------------------------------+

home
|
+-- create_outer_container
    |
    +-- create_nav_group
    |   |
    |   +-- create_nav_menu
    |       |
    |       +-- create_filler_item
    |       +-- create_profile_menu
    |       +-- create_app_menu
    |       +-- create_search_input
    |
    +-- create_grid_left
        |
        +-- create_notebook_interface
            |
            +-- render_notebook_cells()
                |
                +-- render_notebook_cell(cell_1)
                +-- render_notebook_cell(cell_2)
                +-- render_notebook_cell(cell_3)
                +-- ...
    |
    +-- create_chat_interface
        |
        +-- mk_chat_input_group
    |
    +-- create_poke_button

COMMUNICATION


WebSocket (FastHTML app.websocket_route):
┌─────────┐   ws://     ┌──────────┐
│ Browser │ ═══════════ │ FastHTML │ - Streams 2-way communication for LLM Chat
│         │ ═══════════ │          │ - Monitored for JSON instructions from LLM
└─────────┘  bi-direct  └──────────┘


SSE (FastHTML Starlette EventStream in global):
┌─────────┐             ┌──────────┐
│ Browser │ ◄ · · · ·   │ Starlette│ - Syncs back-end changes to the DOM
│         │             │          │ - Creates Ghost in the Machine Effect
└─────────┘             └──────────┘
   keeps     EventStream    needs   
  listening    one-way     restart 


POINTS OF INTEREST:

- This is not a Web App. This is a local app built with FastHTML that provides an interactive interface for LLM-powered applications.
- It serves as a framework for individual single-page applications (SPAs) that run in the Main Area, with an integrated chat interface.
- The SPAs are often converted Jupyter Notebooks, allowing for interactive data analysis and visualization.
- It runs locally rather than on the web, integrating with local LLM infrastructure.
- Uses a dual-server architecture: FastHTML for the web interface and Ollama for LLM capabilities.
- Requires a local Ollama installation for LLM functionality.
- Features a split-pane design with the main SPA content alongside a persistent Chat Interface.
- Maintains contextual awareness by feeding user interactions to the LLM as conversation context.
- The LLM maintains awareness of user actions and application state, excluding low-level events like mouse movements.
- LLM context is initialized from a system prompt and builds knowledge through user interaction.
- Supports multiple LLM models through a flexible model selection system (as seen in cycle_llm_model).
- Designed for extensibility to support more sophisticated AI agent behaviors.
- Implements multiple approaches to long-term memory and persistence:
  - Conversation history tracking and recovery
  - Flexible key-value storage for application state
  - Integration options with RAG, vector databases, SQL, and graph databases

REMEMBER:
1. Keep it simple
2. Local single-user only
3. Unconventional by design

'''


# figlet ---------------------------------------------------------------------------------------------
#   ____             __ _                       _   _
#  / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __
# | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \
# | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |
#  \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|
#                         |___/
# *******************************
# App Constants (configuration)
# *******************************


# Full-path of the current running "server.py" file
THIS_FILE = Path(__file__)

# Define step with clear intent
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))  # default transform to None


def get_app_name():
    """Get the name of the app from the directory it is in."""
    name = THIS_FILE.parent.name
    return name[:-5].capitalize() if name.endswith('-main') else name.capitalize()


APP_NAME = get_app_name()

MAX_CONVERSATION_LENGTH = 10000   # Maximum number of messages in conversation history

# Customize the placeholder defaults for CUSTOMER fields
PLACEHOLDER_ADDRESS = "www.site.com"
PLACEHOLDER_CODE = "CCode (us, uk, de, etc)"

# Grid layout constants
GRID_LAYOUT = "65% 35%"
NAV_FILLER_WIDTH = "2%"  # Width for the filler in the navigation
MIN_MENU_WIDTH = "18vw"
MAX_MENU_WIDTH = "22vw"

# Web UI layout constants
WEB_UI_WIDTH = "95%"
WEB_UI_PADDING = "1rem"
WEB_UI_MARGIN = "0 auto"

# Styles for menu items
NOWRAP_STYLE = (
    "white-space: nowrap; "
    "overflow: hidden; "
    "text-overflow: ellipsis;"
)
# Pluralization configuration
LIST_SUFFIX = "List"

# Update field mappings to match actual API fields
FIELD_MAP = {
    'url': 'url',
    'title': 'metadata.title',
    'pagetype': 'segments.pagetype.value',
    'depth': 'depth',
    'inlinks': 'inlinks_internal.nb.total',
    'outlinks': 'outlinks_internal.nb.total',
    'segment': 'segments.segment.value',
    'compliant': 'compliant.is_compliant',
    'reason': 'compliant.main_reason',
    'canonical': 'canonical.to.equal',
    'sitemap': 'sitemaps.present',
    'js_exec': 'js.rendering.exec',
    'js_ok': 'js.rendering.ok',
    # Add search console fields to main map
    'clicks': 'search_console.period_0.count_clicks',
    'impressions': 'search_console.period_0.count_impressions',
    'ctr': 'search_console.period_0.ctr',
    'position': 'search_console.period_0.avg_position'
}

# Keep SEARCH_CONSOLE separate for special handling in queries
SEARCH_CONSOLE = {
    'clicks': 'search_console.period_0.count_clicks',
    'impressions': 'search_console.period_0.count_impressions',
    'ctr': 'search_console.period_0.ctr',
    'position': 'search_console.period_0.avg_position'
}


def generate_menu_style():
    """Generate a common style for menu elements with text truncation."""
    return (
        f"min-width: {MIN_MENU_WIDTH}; "
        f"max-width: {MAX_MENU_WIDTH}; "
        "width: 100%; "
        "white-space: nowrap; "
        "overflow: hidden; "
        "text-overflow: ellipsis; "
        "align-items: center; "
        "border-radius: 16px; "
        "display: inline-flex; "
        "justify-content: center; "
        "margin: 0 2px; "
    )


# Initialize IDs for menus
# profile_id = "profile-id"
# explore_id = "app-id"

# Plugin-related constants
# We don't need a download directory, generally. But because our plugin needs it, we do.

# Check if there's a download directory and if not, create it with Path
DOWNLOAD_DIR = Path('downloads')
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# figlet ---------------------------------------------------------------------------------------------
#  _                      _
# | |    ___   __ _  __ _(_)_ __   __ _
# | |   / _ \ / _` |/ _` | | '_ \ / _` |
# | |__| (_) | (_| | (_| | | | | | (_| |
# |_____\___/ \__, |\__, |_|_| |_|\__, |
#             |___/ |___/         |___/
# *******************************
# Set up logging with loguru
# *******************************
def setup_logging():
    # Ensure the logs directory exists
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Set up log file paths
    app_log_path = logs_dir / f'{APP_NAME}.log'

    # Remove all existing handlers and files
    logger.remove()
    for p in [app_log_path]:
        if p.exists():
            p.unlink()

    # Add main app log handler with rotation
    logger.add(
        app_log_path,
        rotation="2 MB",
        level="DEBUG",  # Keep DEBUG for file logging
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <15} | {message}",
        enqueue=True
    )

    # Update console handler filter to be more selective
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name: <15}</cyan> | "
               "<cyan>{message}</cyan>",
        colorize=True,
        filter=lambda record: (
            record["level"].name in ["ERROR", "WARNING"] or
            record["level"].name == "INFO" or
            (record["level"].name == "DEBUG" and
             # Keep useful debug info for users
             ("HTTP Request:" in record["message"] or
              "Pipeline ID:" in record["message"] or
              "State changed:" in record["message"] or
              record["message"].startswith("Creating") or
              record["message"].startswith("Updated")) and
             # Filter out noise
             not "Pipeline" in record["message"] and
             not record["message"].startswith("DB: __") and
             not "First record" in record["message"] and
             not "Records found" in record["message"] and
             not "dir:" in record["message"])
        )
    )

    return logger.opt(colors=True)


# Use the setup_logging function to configure the logger
logger = setup_logging()



def get_component_logger(name):
    """Get a logger for a specific component"""
    return logger.bind(name=name)


# Define component loggers
db_logger = get_component_logger("DB")
pipeline_logger = get_component_logger("Pipeline")
app_logger = get_component_logger("App")

# Define a custom theme with a black background
custom_theme = Theme({
    "default": "white on black",
    "header": RichStyle(color="magenta", bold=True, bgcolor="black"),
    "cyan": RichStyle(color="cyan", bgcolor="black"),
    "green": RichStyle(color="green", bgcolor="black"),
    "orange3": RichStyle(color="orange3", bgcolor="black"),
    "white": RichStyle(color="white", bgcolor="black"),
})


class DebugConsole(Console):
    def print(self, *args, **kwargs):
        super().print(*args, **kwargs)


# Use the custom console
console = DebugConsole(theme=custom_theme)


def fig(text, font='slant', color='cyan'):
    font = 'standard'
    figlet = Figlet(font=font)
    fig_text = figlet.renderText(str(text))
    colored_text = Text(fig_text, style=f"{color} on default")
    console.print(colored_text, style="on default")
    # console.print(text, style=f"{color} on default")


def name(word):
    return word.replace('_', ' ').replace('.', ' ').title()


def format_endpoint_name(endpoint: str) -> str:
    """
    Format endpoint names using friendly names when available, otherwise capitalize and format.

    Args:
        endpoint (str): The endpoint name to format

    Returns:
        str: The formatted name, either from friendly_names or default formatting
    """
    # Use friendly name if available
    if endpoint in friendly_names:
        return friendly_names[endpoint]

    # Otherwise use default formatting (capitalize and replace underscores)
    return ' '.join(word.capitalize() for word in endpoint.split('_'))


def format_step_name(step: str, preserve: bool = False) -> str:
    _, number = step.split('_')
    return f"Step {number.lstrip('0')}"


def format_step_button(step: str, preserve: bool = False, revert_label: str = None) -> str:
    """Convert step_01 into either ⟲ Step 1 or ↶ Step 1 with nonbreaking spaces."""
    # Add context tracking
    logger.debug(f"[format_step_button] Entry - step={step}, preserve={preserve}, revert_label={revert_label}")

    _, number = step.split('_')
    symbol = "⟲" if preserve else "↶"
    label = revert_label if revert_label else "Step"

    # Format button text
    if revert_label:
        button_text = f"{symbol}\u00A0{label}"
    else:
        button_text = f"{symbol}\u00A0{label}\u00A0{number.lstrip('0')}"

    logger.debug(f"[format_step_button] Generated button text: {button_text}")
    return button_text


class SSEBroadcaster:
    def __init__(self):
        self.queue = asyncio.Queue()
        print("SSE Broadcaster initialized")  # Debug

    async def generator(self):
        while True:
            try:
                # Get message if available, otherwise do datetime ping
                message = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                print(f"SSE sending: {message}")  # Debug

                # Format as proper SSE message
                if message:
                    # Split message into lines and prefix each with "data:"
                    formatted = '\n'.join(f"data: {line}"
                                          for line in message.split('\n'))
                    yield f"{formatted}\n\n"
            except asyncio.TimeoutError:
                # Send ping message
                now = datetime.now()
                yield f"data: Test ping at {now}\n\n"

    async def send(self, message):
        print(f"Queueing message: {message}")  # Debug
        await self.queue.put(message)


# Create a single instance at module level
broadcaster = SSEBroadcaster()


# figlet ---------------------------------------------------------------------------------------------
#  ____            _                   ____                            _
# / ___| _   _ ___| |_ ___ _ __ ___   |  _ \ _ __ ___  _ __ ___  _ __ | |_
# \___ \| | | / __| __/ _ \ '_ ` _ \  | |_) | '__/ _ \| '_ ` _ \| '_ \| __|
#  ___) | |_| \__ \ ||  __/ | | | | | |  __/| | | (_) | | | | | | |_) | |_
# |____/ \__, |___/\__\___|_| |_| |_| |_|   |_|  \___/|_| |_| |_| .__/ \__|
#        |___/                                                  |_|
# *******************************
# System Prompt and API Syntax Templates
# *******************************


def generate_system_message():
    # check for file named system_instructions.txt if path provided
    if SYSTEM_PROMPT_FILE:
        logger.debug(f"Checking for {SYSTEM_PROMPT_FILE}")
        if Path(SYSTEM_PROMPT_FILE).exists():
            logger.debug(f"Using system instructions from {SYSTEM_PROMPT_FILE}")
            # replace the message with the contents of the file
            logger.debug(f"Using system instructions from {SYSTEM_PROMPT_FILE}")
            intro = Path(SYSTEM_PROMPT_FILE).read_text()
        else:
            intro = f"Your name is {APP_NAME} and you are built into locally running SEO software. "
    else:
        intro = (
            f"Your name is {APP_NAME} and you are built into locally running SEO software. "
            "When referring to buttons and UI elements, do not attempt to draw or create ASCII art "
            "You are a helpful assistant. Please keep your responses concise and use minimal line breaks. "
            "Only use line breaks when necessary for readability, with a maximum of one blank line between paragraphs. "
            "representations of them - the Web UI will handle displaying the actual elements. "
        )

    emoji_instructions = (
        "You are able to use emojis, but keep it to a minimum. "
        "Don't claim you can do anything like analyze websites or find keywords "
        "until the system prompt explicitly tells you you have those abilities. "
        "Keep responses honest and within your current capabilities. ✨"
    )

    message = intro + "\n\n" + emoji_instructions

    logger.debug("Begin System Prompt")
    console.print(message, style="on default")
    logger.debug("End System Prompt")

    return message


def todo_list_training():
    operations = [
        ("List All Records", "list"),
        ("Insert (Create)", "insert"),
        ("Read (Retrieve)", "read"),
        ("Update", "update"),
        ("Delete", "delete"),
        ("Toggle Field (e.g., Status)", "toggle"),
        ("Sort Records", "sort"),
    ]

    operation_docs = {
        "list": """
        # List all tasks
        {
            "action": "list",
            "target": "task"
        }""",

        "insert": """
        # Create a new task
        # Only 'name' is required - can include emoji (e.g. "🎯 Important Task")
        # All other fields are optional and will be handled automatically
        {
            "action": "insert",
            "target": "task",
            "args": {
                "name": "🎯 Sample Task"
            }
        }""",

        "read": """
        # Retrieve a specific task by ID
        {
            "action": "read",
            "target": "task",
            "args": {
                "id": "123"    # Must be a string
            }
        }""",

        "update": """
        # Update an existing task
        # All fields are optional except id
        {
            "action": "update",
            "target": "task",
            "args": {
                "id": "123",           # Required: task ID as string
                "name": "📝 New Name",  # Optional: new task name
                "done": 1,             # Optional: 0=incomplete, 1=complete
                "priority": 2          # Optional: new priority
            }
        }""",

        "delete": """
        # Delete a task by ID
        {
            "action": "delete",
            "target": "task",
            "args": {
                "id": "123"    # Must be a string
            }
        }""",

        "toggle": """
        # Toggle a task's status (usually the 'done' field)
        {
            "action": "toggle",
            "target": "task",
            "args": {
                "id": "123",        # Must be a string
                "field": "done"     # Field to toggle
            }
        }""",

        "sort": """
        # Reorder tasks by priority
        # Lower priority number = higher in list
        {
            "action": "sort",
            "target": "task",
            "args": {
                "items": [
                    {"id": "123", "priority": 0},    # First item
                    {"id": "456", "priority": 1},    # Second item
                    {"id": "789", "priority": 2}     # Third item
                ]
            }
        }"""
    }

    emoji_instructions = (
        "You are now the Tasks app and you add to the task list.\n\n"
        "This is our JSON API contract. You must follow it to insert tasks.\n\n"
        "Follow this whenever asked to add something to a list.\n\n"
        "When inserting tasks, follow these rules:\n\n"
        "1. Always use the actual emoji character with the text in the 'name' field\n"
        "2. Example of minimal task insertion:\n\n"
        "3. Always USE THIS EXACT FORMAT when asked to add or insert an apple:\n\n"
        "```json\n"
        "{\n"
        '  "action": "insert",\n'
        '  "target": "task",\n'
        '  "args": {\n'
        '    "name": "🍎 Red Apple"\n'
        '  }\n'
        "}\n"
        "```\n\n"
        "4. All string values must use double quotes\n"
    )

    syntax_instructions = (
        "You can use the following JSON syntax to perform operations on the database.\n"
        "Important notes:\n"
        "1. All IDs should be strings (e.g. \"123\")\n"
        "2. Task names can include emojis (e.g. \"🎯 Important Task\")\n"
        "3. All operations use 'task' as the target\n"
        "4. All string values must be properly quoted with double quotes\n\n"
        "5. Do not pretend to add something to a list without also including the JSON.\n\n"
    )

    for i, (operation_name, operation_key) in enumerate(operations, 1):
        doc = operation_docs.get(operation_key, "")
        syntax_instructions += (
            f"{i}. {operation_name}\n\n"
            f"```json\n{doc}\n```\n\n"
        )

    message = emoji_instructions + "\n\n" + syntax_instructions
    message += "Only use JSON when asked for an insert, update, delete, or toggle action. "
    message += "All other times, RESPOND IN PLAIN ENGLISH! "
    message += "You are a simple task list manager. \n\n"

    return message


llm_speedbump_dict["JSON_STATE_MANTRA"] = """
    JSON STATE MANTRA:
    DON'T DO THIS (over-engineered state):
        class WorkflowState:
            def __init__(self):
                self.current_step = 0
                self.data = {}
                self.history = []
            
            def transition(self, next_step):
                self.history.append(self.current_step)
                self.current_step = next_step

    DO THIS INSTEAD:
        state = {
            "step_01": {"name": "John"},     # Each step owns its data
            "step_02": {"email": "j@j.com"}, # Present steps = completed
            "created": "2024-01-31T...",     # First creation timestamp
            "updated": "2024-01-31T..."      # Last state change
        }

    Why? Because:
    1. Steps are self-contained data buckets
    2. Progress tracked by step presence
    3. No explicit current_step needed
    4. Forward-only flow (submit clears forward)
    5. Finalization pattern for locking
    6. Single source of truth in database
    7. HTMX handles UI state/updates
    8. URLs reflect workflow position
"""


PERMITTED_LLM_ACTIONS = {"insert", "read", "update", "delete", "toggle", "sort", "list"}

if MAX_LLM_RESPONSE_WORDS:
    limiter = f"in under {MAX_LLM_RESPONSE_WORDS} {TONE} words"
else:
    limiter = ""

CRUD_PROMPT_PREFIXES = {
    action: f"Make a {TONE} comment {limiter} to the user letting them know you know "
    for action in PERMITTED_LLM_ACTIONS
}
CRUD_PROMT_SUFFIX = " DO NOT REPEAT THE JSON!! IT WILL ATTEMPT TO DO THE INSERT AGAIN.\n"

# figlet ---------------------------------------------------------------------------------------------
#   ____                                    _   _               _   _ _     _
#  / ___|___  _ ____   _____ _ __ ___  __ _| |_(_) ___  _ __   | | | (_)___| |_ ___  _ __ _   _
# | |   / _ \| '_ \ \ / / _ \ '__/ __|/ _` | __| |/ _ \| '_ \  | |_| | / __| __/ _ \| '__| | | |
# | |__| (_) | | | \ V /  __/ |  \__ \ (_| | |_| | (_) | | | | |  _  | \__ \ || (_) | |  | |_| |
#  \____\___/|_| |_|\_/ \___|_|  |___/\__,_|\__|_|\___/|_| |_| |_| |_|_|___/\__\___/|_|   \__, |
#                                                                                         |___/
# *******************************
# Create a conversation history
# *******************************

# Add this function to log the current state of the conversation history

# Global variable to store conversation history
global_conversation_history = deque(maxlen=MAX_CONVERSATION_LENGTH)
conversation = [{"role": "system", "content": generate_system_message()}]


def append_to_conversation(message=None, role="user", quiet=False):
    """
    Manage the conversation history.

    Args:
        message (str, optional): The message to add to the history.
        role (str, optional): The role of the message sender ("system", "user", or "assistant").
        quiet (bool, optional): If True, suppress logging output.

    Returns:
        list: The current conversation history.
    """
    logger.debug("Entering append_to_conversation function")
    if not quiet:
        # Only try to slice if message is a string
        preview = message[:50] + "..." if isinstance(message, str) else str(message)
        logger.debug(f"Appending to conversation. Role: {role}, Message: {preview}")

    if message is not None:
        # If the history is empty or the first message isn't a system message, add the system prompt
        if not global_conversation_history or global_conversation_history[0]['role'] != 'system':
            if not quiet:
                logger.debug("Adding system message to conversation history")
            global_conversation_history.appendleft(conversation[0])

        # Add the new message
        global_conversation_history.append({"role": role, "content": message})
        if not quiet:
            logger.debug(f"Message appended. New conversation history length: {len(global_conversation_history)}")

    logger.debug("Exiting Append to Conversation")
    return list(global_conversation_history)


async def display_conversation_statistics():
    logger.debug("Entering display_conversation_statistics")
    role_counts = Counter(entry['role'] for entry in global_conversation_history)
    logger.debug(f"Role counts: {dict(role_counts)}")

    # Create a rich table to display the statistics
    table = Table(title="Conversation History Statistics")
    table.add_column("Role", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Percentage", style="green")

    # Calculate total messages
    total_messages = sum(role_counts.values())
    logger.debug(f"Total messages: {total_messages}")

    # Add rows for each role, including those with zero counts
    for role in ['system', 'user', 'assistant']:
        count = role_counts.get(role, 0)
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        table.add_row(
            role.capitalize(),
            str(count),
            f"{percentage:.2f}%"
        )
        logger.debug(f"Added row for {role}: count={count}, percentage={percentage:.2f}%")

    # Add a total row
    table.add_row("Total", str(total_messages), "100.00%", style="bold")
    logger.debug("Added total row to table")

    # Print the table
    console = Console()
    console.print(table)
    logger.debug("Printed statistics table")

    logger.debug("Exiting display_conversation_statistics")

# figlet ---------------------------------------------------------------------------------------------
#  _                    _   _     _     __  __
# | |    ___   ___ __ _| | | |   | |   |  \/  |
# | |   / _ \ / __/ _` | | | |   | |   | |\/| |
# | |__| (_) | (_| (_| | | | |___| |___| |  | |
# |_____\___/ \___\__,_|_| |_____|_____|_|  |_|
#
# *******************************
# Ollama Local LLM for receiving Kung Fu Downloads
# *******************************


def get_best_model() -> str:
    """
    Retrieve the best available LLaMA model or default to 'llama3.2'.

    This function:
    1. Queries the local Ollama API for available models.
    2. Filters for LLaMA models.
    3. Identifies the most recent and capable model using version comparison.
    4. Falls back to a default model if necessary.

    Returns:
        str: The name of the best available LLaMA model, or the default model.
    """
    logger.debug("Attempting to retrieve the best LLaMA model.")

    if DEFAULT_LLM_MODEL:
        logger.debug(f"Using default model: {DEFAULT_LLM_MODEL}")
        log_model_details(DEFAULT_LLM_MODEL)
        return DEFAULT_LLM_MODEL

    try:
        logger.debug("Querying Ollama for available models...")
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()
        models = [model['name'] for model in response.json().get('models', [])]
        logger.debug(f"Available models: {models}")

        for model in models:
            log_model_details(model)

        llama_models = [model for model in models if model.lower().startswith('llama')]
        if not llama_models:
            logger.warning("No LLaMA models found. Using default model.")
            return DEFAULT_LLM_MODEL  # Default if no LLaMA models are found

        def parse_version(version_string: str) -> List[Optional[int]]:
            """Parse a version string into a list of integers and strings for comparison."""
            return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', version_string)]

        def key_func(model: str) -> tuple:
            """Generate a sorting key for a LLaMA model based on its version."""
            parts = model.split(':')
            base_name = parts[0]
            version = parts[1] if len(parts) > 1 else ''
            base_version = re.search(r'llama(\d+(?:\.\d+)*)', base_name.lower())
            base_version = base_version.group(1) if base_version else '0'
            return (
                parse_version(base_version),
                1 if version == 'latest' else 0,
                parse_version(version),
            )

        best_model = max(llama_models, key=key_func)
        logger.debug(f"Selected best model: {best_model}")
        return best_model

    except requests.RequestException as e:
        logger.error(f"Error fetching models: {str(e)}")
        return DEFAULT_LLM_MODEL


def log_model_details(model: str):
    """Log detailed information about the selected model."""
    logger.debug(f"Checking model details for: {model}")
    try:
        # Get model info from Ollama
        response = requests.get(f"http://localhost:11434/api/show",
                                params={"name": model})
        if response.status_code == 200:
            model_info = response.json()
            logger.debug(f"Model info: {json.dumps(model_info, indent=2)}")
        else:
            logger.warning(f"Could not get model info. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error getting model details: {str(e)}")


async def chat_with_llm(model: str, messages: list, base_app=None) -> AsyncGenerator[str, None]:
    """
    Async generator function to stream chat responses from Ollama.

    Args:
        model (str): The model to use for chat
        messages (list): List of message dictionaries
        base_app: Optional instance of a BaseApp derived object

    Yields:
        str: Chunks of the response message
    """
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }

    accumulated_response = []

    # Display latest user input in rich table
    table = Table(title="User Input")
    table.add_column("Role", style="cyan")
    table.add_column("Content", style="orange3")

    # Get only the last message
    if messages:
        last_message = messages[-1]
        role = last_message.get("role", "unknown")
        content = last_message.get("content", "")
        # Handle nested JSON structures in content
        if isinstance(content, dict):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        table.add_row(role, content)

    console.print(table)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"Ollama server error: {error_text}"
                    accumulated_response.append(error_msg)
                    yield error_msg
                    return

                # Yield initial newline before streaming starts
                yield "\n"

                async for line in response.content:
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                        if chunk.get("done", False):
                            print("\n", end='', flush=True)
                            final_response = "".join(accumulated_response)

                            table = Table(title="Chat Response")
                            table.add_column("Accumulated Response")
                            table.add_row(final_response, style="green")
                            console.print(table)
                            await display_conversation_statistics()
                            await post_llm_stream_json_detection(final_response, base_app)
                            break

                        if content := chunk.get("message", {}).get("content", ""):
                            # First handle potential paragraph breaks
                            if content.startswith('\n') and accumulated_response and accumulated_response[-1].endswith('\n'):
                                # This is likely a paragraph break - ensure double newline
                                content = '\n' + content.lstrip('\n')
                            else:
                                # Handle other newlines
                                content = re.sub(r'\n\s*\n\s*', '\n\n', content)
                                content = re.sub(r'([.!?])\n', r'\1 ', content)
                                # Remove single space after newline
                                content = re.sub(r'\n ([^\s])', r'\n\1', content)

                            print(content, end='', flush=True)
                            accumulated_response.append(content)
                            yield content

                    except json.JSONDecodeError:
                        continue

    except aiohttp.ClientConnectorError as e:
        error_msg = "Unable to connect to Ollama server. Please ensure Ollama is running."
        accumulated_response.append(error_msg)
        yield error_msg

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        accumulated_response.append(error_msg)
        yield error_msg


# figlet ---------------------------------------------------------------------------------------------
#      _                  ____            _       _
#     | | __ ___   ____ _/ ___|  ___ _ __(_)_ __ | |_
#  _  | |/ _` \ \ / / _` \___ \ / __| '__| | '_ \| __|
# | |_| | (_| |\ V / (_| |___) | (__| |  | | |_) | |_
#  \___/ \__,_| \_/ \__,_|____/ \___|_|  |_| .__/ \__|
#                                          |_|
# *******************************
# JavaScript Includes mess with code beauty
# *******************************

# This function creates a SortableJS script for drag-and-drop reordering of Todo items.


def create_chat_scripts(
    sortable_selector='.sortable',
    ghost_class='blue-background-class'
):
    # 1. Sortable functionality script
    sortable_script = f"""
    function setupSortable() {{
        const sortableEl = document.querySelector('{sortable_selector}');
        if (sortableEl) {{
            new Sortable(sortableEl, {{
                animation: 150,
                ghostClass: '{ghost_class}',
                onEnd: function (evt) {{
                    let items = Array.from(sortableEl.children).map((item, index) => ({{
                        id: item.dataset.id,
                        priority: index
                    }}));
                    
                    let path = window.location.pathname;
                    let updateUrl = path.endsWith('/') ? path + 'sort' : path + '_sort';
                    
                    htmx.ajax('POST', updateUrl, {{
                        target: sortableEl,
                        swap: 'none',
                        values: {{ items: JSON.stringify(items) }}
                    }});
                }}
            }});
        }}
    }}
    """

    # 2. WebSocket and SSE functionality script
    websocket_sse_script = r"""
    function setupWebSocketAndSSE() {
        // SSE Setup
        let lastMessage = null;
        const evtSource = new EventSource("/sse");
        
        evtSource.onmessage = function(event) {
            const data = event.data;
            console.log('SSE received:', data);
            
            // Only process if it's not a ping message
            if (!data.includes('Test ping at')) {
                const todoList = document.getElementById('todo-list');
                if (!todoList) {
                    console.error('Could not find todo-list element');
                    return;
                }

                const temp = document.createElement('div');
                temp.innerHTML = data;
                
                const newTodo = temp.firstChild;
                if (newTodo) {
                    todoList.appendChild(newTodo);
                    htmx.process(newTodo);
                }
            }
        };

        // WebSocket message handler
        window.handleWebSocketMessage = function(event) {
            console.log('Sidebar received:', event.data);
            
            // Check if the message is a script
            if (event.data.trim().startsWith('<script>')) {
                const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
                console.log('Executing script:', scriptContent);
                try {
                    eval(scriptContent);
                } catch (e) {
                    console.error('Error executing script:', e);
                }
                return;
            }
            
            // Check if the response is an HTML element
            if (event.data.trim().startsWith('<')) {
                try {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(event.data.trim(), 'text/html');
                    const element = doc.body.firstChild;
                    
                    if (element && element.hasAttribute('data-id')) {
                        const todoList = document.getElementById('todo-list');
                        if (todoList) {
                            todoList.appendChild(element);
                            if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                                new Sortable(todoList, {
                                    animation: 150,
                                    ghostClass: 'blue-background-class'
                                });
                                todoList.classList.add('sortable-initialized');
                            }
                        }
                        return;
                    }
                } catch (e) {
                    console.error('Error parsing HTML:', e);
                }
            }
            
            // Handle regular chat messages
            const sidebarMsgList = document.getElementById('msg-list');
            const sidebarCurrentMessage = document.createElement('div');
            sidebarCurrentMessage.className = 'message assistant';
            
            if (!sidebarCurrentMessage.parentElement) {
                sidebarMsgList.appendChild(sidebarCurrentMessage);
            }
            
            // Handle line breaks in messages
            if (event.data.includes('\\n')) {
                const lines = event.data.split('\\n');
                sidebarCurrentMessage.innerHTML += lines.map(line => 
                    line.trim() ? `<p>${line}</p>` : '<br>'
                ).join('');
            } else {
                sidebarCurrentMessage.innerHTML += event.data;
            }
            
            sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
        };

        // Test functions
        window.testSSE = function() {
            alert('Latest SSE message: ' + (lastMessage || 'No messages received yet'));
        }
        
        window.sseLastMessage = function() {
            return lastMessage;
        }
        
        console.log('WebSocket and SSE handlers initialized');
    }
    """

    # 3. HTMX and Search functionality script
    interaction_script = r"""
    function setupInteractions() {
        // Form reset after submission
        document.addEventListener('htmx:afterSwap', function(event) {
            if (event.target.id === 'todo-list' && event.detail.successful) {
                const form = document.querySelector('form[hx-target="#todo-list"]');
                if (form) {
                    form.reset();
                }
            }
        });

        window.triggerTestAppend = () => {
            htmx.ajax('GET', '/test-append', {
                target: '#todo-list',
                swap: 'beforeend'
            });
        };

        window.handleSearchSubmit = function(event) {
            event.preventDefault();
            const input = document.getElementById('nav-input');
            if (input && input.value) {
                if (window.sidebarWs) {
                    window.sidebarWs.send(input.value);
                }
                input.value = '';
            }
        };
    }
    """

    # Combine all scripts with initialization
    combined_script = f"""
    document.addEventListener('DOMContentLoaded', (event) => {{
        {sortable_script}
        {websocket_sse_script}
        {interaction_script}
        
        // Initialize all components
        setupSortable();
        setupWebSocketAndSSE();
        setupInteractions();
        
        console.log('All scripts initialized');
    }});
    """

    return Script(combined_script), Style("""
        #msg-list, #msg-list {
            display: flex;
            flex-direction: column;
        }
        #msg-list {
            padding-right: 10px;
        }
        .message {
            margin-left: 0;
            margin-top: 2px;
            margin-bottom: 2px;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 100%;
            white-space: pre-wrap;
        }
        .message.user {
            background: var(--pico-primary-background);
            margin-left: auto;
        }
        .message.assistant {
            background: var(--pico-muted-background);
            margin-right: auto;
        }

        /* Modern scrollbar styling */
        #msg-list::-webkit-scrollbar {
            width: 8px;
        }

        #msg-list::-webkit-scrollbar-track {
            background: var(--pico-background-color);
            border-radius: 4px;
        }

        #msg-list::-webkit-scrollbar-thumb {
            background: var(--pico-muted-border-color);
            border-radius: 4px;
        }

        #msg-list::-webkit-scrollbar-thumb:hover {
            background: var(--pico-form-element-border-color);
        }

        /* Firefox */
        #msg-list {
            scrollbar-width: thin;
            scrollbar-color: var(--pico-muted-border-color) var(--pico-background-color);
        }

        hr {
            border-color: var(--pico-primary);
            opacity: 0.3;
        }
    """)

# figlet ---------------------------------------------------------------------------------------------
#   ____ ____  _   _ ____    ____                    _
#  / ___|  _ \| | | |  _ \  | __ )  __ _ ___  ___   / \   _ __  _ __
# | |   | |_) | | | | | | | |  _ \ / _` / __|/ _ \ / _ \ | '_ \| '_ \
# | |___|  _ <| |_| | |_| | | |_) | (_| \__ \  __// ___ \| |_) | |_) |
#  \____|_| \_\\___/|____/  |____/ \__,_|___/\___/_/   \_\ .__/| .__/
#                                                        |_|   |_|
# *******************************
# CRUD BaseApp for creating application components
# *******************************


class BaseApp:
    """
    A base class for creating application components with common CRUD operations.

    This class provides a template for building application components that interact
    with database tables and handle basic Create, Read, Update, Delete (CRUD) operations.
    It includes methods for registering routes, rendering items, and performing various
    database operations.

    To create a new plugin:
    1. Subclass BaseApp
    2. Override methods like render_item, prepare_insert_data, and prepare_update_data
    3. Implement any additional methods specific to your plugin
    4. Register your plugin in the main application (see PLUGIN REGISTRATION section)

    The class is designed to be flexible and extensible, allowing subclasses to override
    or extend its functionality as needed for specific application components.
    """

    def __init__(self, name, table, toggle_field=None, sort_field=None, sort_dict=None):
        self.name = name
        self.table = table
        self.toggle_field = toggle_field
        self.sort_field = sort_field
        self.item_name_field = 'name'  # Default field name
        self.sort_dict = sort_dict or {'id': 'id', sort_field: sort_field}

    def register_routes(self, rt):
        # Register routes: create, read, update, delete, toggle, sort, and list
        rt(f'/{self.name}', methods=['POST'])(self.insert_item)
        rt(f'/{self.name}/{{item_id}}', methods=['POST'])(self.update_item)  # Changed to POST
        rt(f'/{self.name}/delete/{{item_id}}', methods=['DELETE'])(self.delete_item)
        rt(f'/{self.name}/toggle/{{item_id}}', methods=['POST'])(self.toggle_item)
        rt(f'/{self.name}_sort', methods=['POST'])(self.sort_items)

    def get_action_url(self, action, item_id):
        """
        Generate a URL for a specific action on an item.

        Args:
            action (str): The action method (e.g., 'delete', 'toggle').
            item_id (int): The ID of the item.

        Returns:
            str: The constructed URL.
        """
        return f"/{self.name}/{action}/{item_id}"

    def render_item(self, item):
        return Li(
            # Positional arguments (child elements) first
            A(
                "🗑",
                href="#",
                hx_swap="outerHTML",
                hx_delete=f"/task/delete/{item.id}",
                hx_target=f"#todo-{item.id}",
                _class="delete-icon",
                style="cursor: pointer; display: inline;"
            ),
            Input(
                type="checkbox",
                checked="1" if item.done else "0",
                hx_post=f"/task/toggle/{item.id}",
                hx_swap="outerHTML",
                hx_target=f"#todo-{item.id}"
            ),
            A(
                item.name,
                href="#",
                _class="todo-title",
                style="text-decoration: none; color: inherit;"
            ),
            # Keyword arguments after positional arguments
            data_id=item.id,
            data_priority=item.priority,
            id=f"todo-{item.id}",
            style="list-style-type: none;",
        )

    async def delete_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_name = getattr(item, self.item_name_field, 'Item')
            self.table.delete(item_id)
            logger.debug(f"Deleted item ID: {item_id}")
            action_details = f"The {self.name} item '{item_name}' was removed."
            # prompt = f"{CRUD_PROMPT_PREFIXES['delete']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return ''
        except Exception as e:
            error_msg = f"Error deleting item: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while deleting {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return str(e), 500

    async def toggle_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            current_status = getattr(item, self.toggle_field)
            new_status = not current_status
            setattr(item, self.toggle_field, new_status)
            updated_item = self.table.update(item)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            status_text = 'checked' if new_status else 'unchecked'
            action_details = f"The {self.name} item '{item_name}' is now {status_text}."
            # prompt = f"{CRUD_PROMPT_PREFIXES['toggle']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return self.render_item(updated_item)
        except Exception as e:
            error_msg = f"Error toggling item: {str(e)}"
            logger.error(error_msg)
            action_details = f"an error occurred while toggling {self.name} (ID: {item_id}): {error_msg}"
            prompt = f"{CRUD_PROMPT_PREFIXES['error']}{action_details}"
            await chatq(prompt)
            return str(e), 500

    async def sort_items(self, request):
        logger.debug(f"Received request to sort {self.name}.")
        try:
            values = await request.form()
            items = json.loads(values.get('items', '[]'))
            logger.debug(f"Parsed items: {items}")
            changes = []
            sort_dict = {}
            for item in items:
                item_id = int(item['id'])
                priority = int(item['priority'])
                self.table.update(id=item_id, **{self.sort_field: priority})
                item_name = getattr(self.table[item_id], self.item_name_field, 'Item')
                sort_dict[item_id] = priority
                changes.append(f"'{item_name}' moved to position {priority}")
            changes_str = '; '.join(changes)
            action_details = f"The {self.name} items were reordered: {changes_str}"
            # prompt = f"{CRUD_PROMPT_PREFIXES['sort']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            logger.debug(f"{self.name.capitalize()} order updated successfully")
            return ''
        except json.JSONDecodeError as e:
            error_msg = f"Invalid data format: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return "Invalid data format", 400
        except Exception as e:
            error_msg = f"Error updating {self.name} order: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while sorting {self.name} items: {error_msg}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return str(e), 500

    async def insert_item(self, request):
        try:
            logger.debug(f"[RENDER DEBUG] Starting insert_item for {self.name}")
            form = await request.form()
            logger.debug(f"[RENDER DEBUG] Form data: {dict(form)}")
            new_item_data = self.prepare_insert_data(form)
            if not new_item_data:
                logger.debug("[RENDER DEBUG] No new_item_data, returning empty")
                return ''
            new_item = await self.create_item(**new_item_data)
            logger.debug(f"[RENDER DEBUG] Created new item: {new_item}")

            item_name = getattr(new_item, self.item_name_field, 'Item')
            action_details = f"A new {self.name} item '{item_name}' was added."
            # prompt = f"{CRUD_PROMPT_PREFIXES['insert']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))

            rendered = self.render_item(new_item)
            logger.debug(f"[RENDER DEBUG] Rendered item type: {type(rendered)}")
            logger.debug(f"[RENDER DEBUG] Rendered item content: {rendered}")
            return rendered
        except Exception as e:
            error_msg = f"Error inserting {self.name}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while adding a new {self.name}: {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return str(e), 500

    async def update_item(self, request, item_id: int):
        try:
            form = await request.form()
            update_data = self.prepare_update_data(form)
            if not update_data:
                return ''
            item = self.table[item_id]
            before_state = item.__dict__.copy()
            for key, value in update_data.items():
                setattr(item, key, value)
            updated_item = self.table.update(item)
            after_state = updated_item.__dict__
            # We need to construct a JSON-friendly dict of changes, only for the keys and new values
            change_dict = {}
            for key in update_data.keys():
                if before_state.get(key) != after_state.get(key):
                    change_dict[key] = after_state.get(key)

            changes = [f"{key} changed from '{before_state.get(key)}' to '{after_state.get(key)}'"
                       for key in update_data.keys() if before_state.get(key) != after_state.get(key)]
            changes_str = '; '.join(changes)
            item_name = getattr(updated_item, self.item_name_field, 'Item')
            action_details = f"The {self.name} item '{item_name}' was updated. Changes: {changes_str}"
            # prompt = f"{CRUD_PROMPT_PREFIXES['update']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            logger.debug(f"Updated {self.name} item {item_id}")
            return self.render_item(updated_item)
        except Exception as e:
            error_msg = f"Error updating {self.name} {item_id}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while updating {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            await chatq(prompt, verbatim=True)
            return str(e), 500

    async def read_item(self, request, item_id: int):
        try:
            item = self.table[item_id]
            item_dict = item.__dict__
            action_details = f"Read {self.name} item with ID {item_id}."
            # prompt = f"{CRUD_PROMPT_PREFIXES['read']}{action_details}{CRUD_PROMT_SUFFIX}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return json.dumps(item_dict, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            error_msg = f"Error reading {self.name} {item_id}: {str(e)}"
            logger.error(error_msg)
            action_details = f"An error occurred while reading {self.name} (ID: {item_id}): {error_msg}"
            prompt = action_details
            asyncio.create_task(chatq(prompt, verbatim=True))
            return str(e), 500

    async def create_item(self, **kwargs):
        """Create a new item in the table."""
        try:
            logger.debug(f"Creating new {self.name} with data: {kwargs}")
            new_item = self.table.insert(kwargs)
            logger.debug(f"Created new {self.name}: {new_item}")
            return new_item
        except Exception as e:
            logger.error(f"Error creating {self.name}: {str(e)}")
            raise e

    def prepare_insert_data(self, form):
        """
        Prepare data for inserting a new item.

        Override this method in your plugin to handle the specific fields of your items.
        This method should process form data and return a dictionary of item properties.

        Args:
            form: The submitted form data.

        Returns:
            dict: Prepared data for item insertion.
        """
        raise NotImplementedError("Subclasses must implement prepare_insert_data")

    def prepare_update_data(self, form):
        """
        Prepare data for updating an existing item.

        Override this method in your plugin to handle the specific fields of your items.
        This method should process form data and return a dictionary of updated properties.

        Args:
            form: The submitted form data.

        Returns:
            dict: Prepared data for item update.
        """
        raise NotImplementedError("Subclasses must implement prepare_update_data")

    def redirect(self, action_details, action):
        """
        Prepare a redirect response after a CRUD action.

        Args:
            action_details (str): Details of the action performed.
            action (str): The type of action performed (e.g., 'insert', 'update', 'delete').

        Returns:
            Redirect: A Redirect object to the appropriate page.
        """
        prompt = f"{CRUD_PROMPT_PREFIXES[action]}{action_details}{CRUD_PROMT_SUFFIX}"
        asyncio.create_task(chatq(prompt))

        # Store the message in the database for retrieval after redirect
        db["temp_message"] = prompt

        # Redirect to the main page or list view of the current app
        return Redirect(f"/{self.name}")

# figlet ---------------------------------------------------------------------------------------------
#  ____  _             _
# |  _ \| |_   _  __ _(_)_ __  ___
# | |_) | | | | |/ _` | | '_ \/ __|
# |  __/| | |_| | (_| | | | | \__ \
# |_|   |_|\__,_|\__, |_|_| |_|___/
#                |___/
# *******************************
# Plugins ProfileApp & TodoApp. Derive from TodoApp for variations.
# *******************************


class ProfileApp(BaseApp):
    def __init__(self, table):
        super().__init__(
            name=table.name,
            table=table,
            toggle_field='active',
            sort_field='priority'
        )
        self.item_name_field = 'name'  # Specify the field name used for item names
        self.item_menu_name_field = 'menu_name'  # Specify the field name used for item menu names

    def render_item(self, profile):
        return render_profile(profile)

    def prepare_insert_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''  # Return empty string instead of raising an exception
        max_priority = max((p.priority or 0 for p in self.table()), default=-1) + 1
        return {
            "name": profile_name,
            "menu_name": form.get('profile_menu_name', '').strip(),
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
            "active": True,
            "priority": max_priority,
        }

    def prepare_update_data(self, form):
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            return ''  # Return empty string instead of raising an exception
        return {
            "name": profile_name,
            "menu_name": form.get('profile_menu_name', '').strip(),
            "address": form.get('profile_address', '').strip(),
            "code": form.get('profile_code', '').strip(),
            "active": form.get('active', '').lower() == 'true',
        }


def render_profile(profile):
    """
    Render a profile item as an HTML list item.

    This function creates a detailed HTML representation of a profile, including:
    - A checkbox to toggle the profile's active status
    - A link to display the profile name and associated todo count
    - Contact information (address and code) if available
    - A delete button (visible only when the profile has no associated todos)
    - A hidden update form for editing profile details

    The function also includes JavaScript for toggling the visibility of the update form
    and other elements when the profile name is clicked.

    Args:
        profile: The profile object containing attributes like id, name, address, code, and active status.

    Returns:
        Li: An HTML list item (Li) object representing the fully rendered profile with all interactive elements.
    """
    def count_records_with_xtra(table_handle, xtra_field, xtra_value):
        """
        Count records in table matching xtra field constraint.

        Args:
            table_handle: MiniDataAPI table object.
            xtra_field (str): Field name to constrain.
            xtra_value: Value to constrain by.

        Returns:
            int: Number of matching records.
        """
        table_handle.xtra(**{xtra_field: xtra_value})
        count = len(table_handle())
        logger.debug(f"Counted {count} records in table for {xtra_field} = {xtra_value}")
        return count

    # Count the number of todo items for this profile
    todo_count = count_records_with_xtra(todos, 'profile_id', profile.id)

    # Set the visibility of the delete icon based on the todo count
    delete_icon_visibility = 'inline' if todo_count == 0 else 'none'

    # Use the ProfileApp instance to generate URLs
    delete_url = profile_app.get_action_url('delete', profile.id)
    toggle_url = profile_app.get_action_url('toggle', profile.id)

    # Create the delete button (trash can)
    delete_icon = A(
        '🗑',
        hx_delete=delete_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style=f"cursor: pointer; display: {delete_icon_visibility};",
        cls="delete-icon"
    )

    # Create the active checkbox
    active_checkbox = Input(
        type="checkbox",
        name="active" if profile.active else None,
        checked=profile.active,
        hx_post=toggle_url,
        hx_target=f'#profile-{profile.id}',
        hx_swap="outerHTML",
        style="margin-right: 5px;"
    )

    # Create the update form
    update_form = Form(
        Group(
            Input(type="text", name="profile_name", value=profile.name, placeholder="Name", id=f"name-{profile.id}"),
            Input(type="text", name="profile_menu_name", value=profile.menu_name, placeholder="Menu Name", id=f"menu_name-{profile.id}"),
            Input(type="text", name="profile_address", value=profile.address, placeholder=PLACEHOLDER_ADDRESS, id=f"address-{profile.id}"),
            Input(type="text", name="profile_code", value=profile.code, placeholder=PLACEHOLDER_CODE, id=f"code-{profile.id}"),
            Button("Update", type="submit"),
        ),
        hx_post=f"/{profile_app.name}/{profile.id}",  # Adjusted URL to match route
        hx_target=f'#profile-{profile.id}',
        hx_swap='outerHTML',
        style="display: none;",
        id=f'update-form-{profile.id}'
    )

    # Create the title link with an onclick event to toggle the update form
    title_link = A(
        f"{profile.name} ({todo_count})",
        href="#",
        hx_trigger="click",
        onclick=(
            "let li = this.closest('li'); "
            "let updateForm = document.getElementById('update-form-" + str(profile.id) + "'); "
            "if (updateForm.style.display === 'none' || updateForm.style.display === '') { "
            "    updateForm.style.display = 'block'; "
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'none'); "
            "} else { "
            "    updateForm.style.display = 'none'; "
            "    li.querySelectorAll('input[type=checkbox], .delete-icon, span, a').forEach(el => el.style.display = 'inline'); "
            "}"
        )
    )

    # Create the contact info span, only if address or code is present
    contact_info = []
    if profile.address:
        contact_info.append(profile.address)
    if profile.code:
        contact_info.append(profile.code)

    contact_info_span = (
        Span(f" ({', '.join(contact_info)})", style="margin-left: 10px;")
        if contact_info else
        Span()  # Empty span if no contact info
    )

    return Li(
        Div(
            active_checkbox,
            title_link,
            contact_info_span,
            delete_icon,
            update_form,
            style="display: flex; align-items: center;"
        ),
        id=f'profile-{profile.id}',
        data_id=profile.id,  # Add this line
        data_priority=profile.priority,  # Add this line
        style="list-style-type: none;"
    )


class TodoApp(BaseApp):
    """
    TodoApp plugin implementation.

    This class demonstrates how to create a plugin for the application using the BaseApp class.
    It provides specific implementations for rendering todo items, preparing data for insertion
    and updates, and other todo-specific functionality.
    """

    def __init__(self, table):
        super().__init__(
            name=table.name,
            table=table,
            toggle_field='done',
            sort_field='priority'
        )
        self.item_name_field = 'name'  # Specify the field name used for item names

    def render_item(self, todo):
        """
        Render a single todo item.

        This method customizes how todo items are displayed in the UI.
        """
        logger.debug(f"[RENDER DEBUG] TodoApp.render_item called with: {todo}")
        rendered = render_todo(todo)
        logger.debug(f"[RENDER DEBUG] render_todo returned type: {type(rendered)}")
        return rendered

    def prepare_insert_data(self, form):
        """
        Prepare data for inserting a new todo item.

        This method processes form data to create a new todo item.
        """
        # Check for either todo_title (from WebSocket) or name (from form)
        name = form.get('todo_title', form.get('name', '')).strip()
        if not name:
            return None  # Changed from empty string to None for clearer error handling

        current_profile_id = db.get("last_profile_id", 1)
        # Get priority from form or calculate max+1
        priority = int(form.get('todo_priority', 0)) or max((t.priority or 0 for t in self.table()), default=-1) + 1

        return {
            "name": name,
            "done": False,
            "priority": priority,
            "profile_id": current_profile_id,
        }

    def prepare_update_data(self, form):
        """
        Prepare data for updating an existing todo item.

        This method processes form data to update an existing todo item.
        """
        name = form.get('name', '').strip()
        if not name:
            return ''
        return {
            "name": name,
            "done": form.get('done', '').lower() == 'true',
        }

    def list_all_records(self, table):
        """
        List all records in the table and return them as a JSON string with emojis.

        Args:
            table: The table containing todo items.

        Returns:
            str: A JSON string representing all todo items with emojis displayed correctly.
        """
        # Convert each todo item to a dictionary
        todo_list = [render_todo_json(todo) for todo in table]
        return json.dumps(todo_list, indent=2, ensure_ascii=False)


def render_todo(todo):
    """Render a todo list item with HTMX attributes."""
    tid = f'todo-{todo.id}'

    # Add debug logging
    print(f"[DEBUG] render_todo called for ID {todo.id} with name '{todo.name}'")

    # Use the TodoApp instance to generate URLs
    delete_url = todo_app.get_action_url('delete', todo.id)
    toggle_url = todo_app.get_action_url('toggle', todo.id)

    checkbox = Input(
        type="checkbox",
        name="english" if todo.done else None,
        checked=todo.done,
        hx_post=toggle_url,
        hx_swap="outerHTML",
        hx_target=f"#{tid}",
    )

    # Create the delete button (trash can)
    delete = A(
        '🗑',
        hx_delete=delete_url,
        hx_swap='outerHTML',
        hx_target=f"#{tid}",
        style="cursor: pointer; display: inline;",
        cls="delete-icon"
    )

    # Create an interactive name link using FastHTML's A() function
    name_link = A(
        todo.name,
        href="#",
        cls="todo-title",
        style="text-decoration: none; color: inherit;",
        onclick=(
            "let updateForm = this.nextElementSibling; "
            "let checkbox = this.parentNode.querySelector('input[type=checkbox]'); "
            "let deleteIcon = this.parentNode.querySelector('.delete-icon'); "
            "if (updateForm.style.visibility === 'hidden' || updateForm.style.visibility === '') { "
            "    updateForm.style.visibility = 'visible'; "
            "    updateForm.style.height = 'auto'; "
            "    checkbox.style.display = 'none'; "
            "    deleteIcon.style.display = 'none'; "
            "    this.remove(); "
            "    const inputField = document.getElementById('todo_name_" + str(todo.id) + "'); "
            "    inputField.focus(); "
            "    inputField.setSelectionRange(inputField.value.length, inputField.value.length); "
            "} else { "
            "    updateForm.style.visibility = 'hidden'; "
            "    updateForm.style.height = '0'; "
            "    checkbox.style.display = 'inline'; "
            "    deleteIcon.style.display = 'inline'; "
            "    this.style.visibility = 'visible'; "
            "}"
        )
    )

    # Create the update form
    update_form = Form(
        Div(
            Input(
                type="text",
                id=f"todo_name_{todo.id}",
                value=todo.name,
                name="name",
                style="flex: 1; padding-right: 10px; margin-bottom: 0px;"
            ),
            style="display: flex; align-items: center;"
        ),
        style="visibility: hidden; height: 0; overflow: hidden;",
        hx_post=f"/{todo_app.name}/{todo.id}",
        hx_target=f"#{tid}",
        hx_swap="outerHTML",
    )

    return Li(
        delete,
        checkbox,
        name_link,
        update_form,
        id=tid,
        cls='done' if todo.done else '',
        style="list-style-type: none;",
        data_id=todo.id,
        data_priority=todo.priority
    )


def render_todo_json(todo):
    """
    Convert a todo item to a dictionary representation.

    Args:
        todo: The todo item to render, containing properties like id, name, done, and priority.

    Returns:
        dict: A dictionary representing the todo item with emojis preserved.
    """
    return {
        "id": todo.id,
        "name": todo.name,
        "done": todo.done,
        "priority": todo.priority
    }


# figlet ---------------------------------------------------------------------------------------------
#  _____         _   _   _ _____ __  __ _
# |  ___|_ _ ___| |_| | | |_   _|  \/  | |
# | |_ / _` / __| __| |_| | | | | |\/| | |
# |  _| (_| \__ \ |_|  _  | | | | |  | | |___
# |_|  \__,_|___/\__|_| |_| |_| |_|  |_|_____|
#
# *******************************
# (fastapp) FastHTML is not FastAPI.
# *******************************

# FASTHTML MANTRA:
# FastHTML is not FastAPI
# Routes use rt not app
# Server-side is the right side
# HTMX for updates, that's all it takes
#
# MINIDATAAPI MANTRA:
# No ORM complexity here
# Just tables and their pairs
# insert(), update(), delete()
# Simple keys, simple states
#
# PIPELINE MANTRA:
# One URL to track them all
# One JSON blob to bind them
# Card to card the data flows
# No message queues behind them

# - Welcome LLM code assistant and human alike to the heart of the app. Here we esablish ground rules.
# - FastHTML is not FastAPI. rt is the router decorator. While app.route() works, we only use it inside classes.
# - The database API is MiniDataAPI Spec. It is NOT SQLAlchemy or any other ORM. Our pattern is todo.insert({key:value})
# - The fast_app() convenience class wrapping all common FastHTML conventions including table creation from schemas.
# - The returned tuple pairs are global scope MiniDataAPI table instances and their accompanying dataclass templates for display purposes.
# - So (tasks, Task) is a pair. tasks is the table instance and Task is the dataclass template for dataclass used in render_todo()
# - These pairs often go with plugins, which are classes that inherit from BaseApp and have a render_item() method.
# - Because all state is handled server-side, (store, Store) provides a dict-like interface to the database.
# - It is a DictLikeDB wrapper around the persistence layer, and we use it as one would use cookies.
# - This provides full transparency of state in the server console for debugging and monitoring.
# - This is among many anti-patterns you will find in a single-tenant deliberately using the full resources of localhost.
# - Do not use any other persistence layer. Do not use requests. Do not use hidden fields. Do not use FastAPI.
# - Python global scope is .py files and package-level objects, making it fine. In single-tenant, it is especially fine.

# figlet ---------------------------------------------------------------------------------------------
#  __  __ _       _ ____        _           _    ____ ___   ____
# |  \/  (_)_ __ (_)  _ \  __ _| |_ __ _   / \  |  _ \_ _| / ___| _ __   ___  ___
# | |\/| | | '_ \| | | | |/ _` | __/ _` | / _ \ | |_) | |  \___ \| '_ \ / _ \/ __|
# | |  | | | | | | | |_| | (_| | || (_| |/ ___ \|  __/| |   ___) | |_) |  __/ (__
# |_|  |_|_|_| |_|_|____/ \__,_|\__\__,_/_/   \_\_|  |___| |____/| .__/ \___|\___|
#                                                                |_|
# *******************************
# MiniDataAPI Spec
# *******************************

"""MiniDataAPI Spec - The Enlightened Path to Local Data Persistence

Key Principles:
1. Tables are Python objects created with db.create(Class, pk='field')
2. Records are dicts or dataclasses matching the table schema
3. Primary keys (pk) are strings or ints, specified at table creation
4. All operations return the affected record(s)

Core Operations:
    table.insert(record) -> record      # Create new record
    table[pk] -> record                 # Read record by primary key
    table.update(record) -> record      # Update existing record
    table.delete(pk) -> record          # Delete record by primary key
    table() -> [records]                # List all records
    table.xtra(field=value)             # Set filter for subsequent operations

Schema Definition:
    db.create(Class, pk='field')        # Create table from class/dict schema
    # Example:
    task = {
        "id": int,                      # Field types: int, str, bool, float
        "name": str,                    # Field names match class attributes
        "done": bool,                   # Boolean fields for flags/status
        "pk": "id"                      # Specify primary key field
    }

Advanced Features:
1. Filtering with .xtra():
   ```python
   tasks.xtra(done=False)               # Filter subsequent operations
   tasks()                              # Returns only undone tasks
   ```

2. Compound Keys:
   ```python
   db.create(Class, pk=['field1', 'field2'])
   ```

3. Table Pairs Pattern:
   ```python
   tasks, Task = db.create(TaskSchema)  # Returns (table, dataclass) pair
   ```

Anti-Patterns to Avoid:
❌ Don't use ORMs or complex relationships
❌ Don't implement joins or foreign key constraints
❌ Don't create hidden fields or complex state
❌ Don't use external message queues or caches

The Way of MiniDataAPI:
- Embrace simplicity over complexity
- Prefer server-side state management
- Use dataclass pairs for type safety
- Keep data structures flat and obvious
- Let the database be your source of truth

Remember: MiniDataAPI is deliberately minimal. If you need more complexity,
you're probably solving the wrong problem."""

# Configure app by unpacking the returned glboal scope (table, Dataclass) tuple pairs (singular, Plural)
app, rt, (store, Store), (tasks, Task), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    "data/data.db",
    exts='ws',
    live=True,    # Make edit, check page, make edit, check page... this is how.
    default_hdrs=False,  # See all that hdrs stuff immediately below I want to control deliberately? Needs this.
    hdrs=(
        Meta(charset='utf-8'),              # Best to let your browser know your encoding sooner rather than later
        Link(rel='stylesheet', href='/static/pico.css'),  # We load our dependencies statically around here
        Script(src='/static/htmx.js'),      # htmx is the backbone of the UI
        Script(src='/static/fasthtml.js'),  # FastHTML is not FastAPI. I can't emphasize this enough.
        Script(src='/static/surreal.js'),   # Enables dynamic updates to the user interface without requiring full page reloads. How to describe it? It's just...
        Script(src='/static/script.js'),    # A not-so-descriptive name for a file that cleverly scopes styles and keeps your CSS drama-free!
        Script(src='/static/Sortable.js'),  # Got a UL with LI's and want to make them drag-and-drop sortable? This is how.
        create_chat_scripts('.sortable'),   # All the early pageload JavaScript not part of above.
        Script(type='module')               # Because FastHTML has a bug and I need to include this to force the correct JS import pattern.
    ),
    store={            # server-side DictLikeDB store used for persistence
        "key": str,    # Key is the primary key
        "value": str,  # Value is the value of the key
        "pk": "key"    # Never twice the same key (updates override)
    },
    task={                  # Exposed to user as "task" endpoint but hardwired to "todo" in the wiring. New instances will have to accomodate in their render_item() method.
        "id": int,          # We lean into the strengths of SQLite. Auto-increment primary key work well.
        "name": str,        # Changed from "title" to "name"
        "done": bool,       # Done is a boolean flag to indicate if the task is completed
        "priority": int,    # Integrates beautifully with Sortable.js to sort tasks by priority
        "profile_id": int,  # Foreign key to profile for use with MiniDataAPI Spec .xtra() extract filter to filter TodoApp by profile
        "pk": "id"          # A task by any other name is still a todo item or generic linked-list CRUD app
    },
    profile={              # "profile" exposed to user as endpoint but hardwired to "profile" in the wiring of plugin element IDs in Web UI
        "id": int,         # To be defined as a SQLite auto-increment primary key via MiniDataAPI Spec
        "name": str,       # Name is actually hidden on the menu so real client names are never exposed unless in client (profile) list app
        "menu_name": str,  # Menu name is exposed on the menu so user can switch profiles in front of client without showing other client names
        "address": str,    # Address is actually used for website domain to control other apps like gap analysis
        "code": str,       # Code is actually country code used to control data-pull filters in API integrations like SEMRush
        "active": bool,    # Active lets you toggle the profile on and off in the menu
        "priority": int,   # Controls the sort order of the profile in the menu
        "pk": "id"         # Default SQLite auto-increment primary key so name and menu_name can be freely changed
    },
    pipeline={           # To "pipulate" is use this for a Unix pipe-like "pipeline" workflow: Card 1 | Card 2 | Card 3
        "url": str,      # A url must be used on Card 1 to initiate a job, and can be plugged in later to from last complete Card step
        "app_name": str,  # The app endpoint, not technically part of composite primary key (yet) but sure useful for MiniDataAPI spec with table.xtra() as a search filter in workflow app ID field searches
        "data": str,     # All jobs get just 1 pipulate record and use a JSON blob to track state for the entire workflow. The JSON blog contains the args and results of each Card for interruptionless pattern
        "created": str,  # ISO timestamp of first insert
        "updated": str,  # ISO timestamp of last update
        "pk": "url"      # URL is the primary key and can always be plugged into Card 1 to continue a job, jumping to where it left off (the same behavior as any step of workflow processing)
    }                    # A FastHTML-friendly querystring-like path can be used to jump to any Card in the workflow: /endpoint/card3
)

llm_speedbump_dict["database"] = """
    DON'T DO THIS (SQLAlchemy style):
        class User(Base):
            __tablename__ = 'users'
            id = Column(Integer, primary_key=True)
            name = Column(String)
            email = Column(String)
    
    DO THIS INSTEAD:
        app, rt, (tasks, Task), (profiles, Profile) = fast_app(
            "data/data.db",
            task={
                "id": int,          # Auto-increment primary key
                "name": str,        # Regular field
                "done": bool,       # Boolean flag
                "priority": int,    # Sortable field
                "profile_id": int,  # Simple foreign key for .xtra() filtering
                "pk": "id"         # Primary key definition
            },
            profile={
                "id": int,
                "name": str,
                "active": bool,
                "pk": "id"
            }
        )
    
    Why? Because:
    1. Schema is just Python types in a dict
    2. Returns (table, Dataclass) pairs for each schema
    3. Primary keys defined explicitly with "pk"
    4. Simple filtering with table.xtra(field=value)
    5. No ORM complexity or session management
    6. Built-in FastHTML rendering with __ft__()
    7. Automatic dataclass creation for type safety
    8. Single-tenant, server-side state management
    9. Lean into SQLite's strengths (auto-increment, etc)
    10. Use .xtra() filters instead of joins
"""

# To add a new plugin, follow these steps:
# 1. Create a new plugin class (e.g., NewPlugin) that inherits from BaseApp
# 2. If a database table is used, define schema in the fast_app() call
# 3. Instantiate your plugin with the appropriate table
# 4. Register the routes for your plugin
# 5. Add the plugin's name to the MENU_ITEMS list
# 6. Add a welcome message for the plugin in APP_MESSAGES

# Example:
# new_plugin = NewPlugin(table=new_plugin_table)
# new_plugin.register_routes(rt)
# MENU_ITEMS.append(new_plugin.name)
# APP_MESSAGES[new_plugin.name] = f"Welcome to the {new_plugin.name} plugin!"

# PLUGIN REGISTRATION
# While looking like a plugin, this is actually tightly integrated with navigation
# While this app remains single-tenant, this provides a way to switch between profiles
profile_app = ProfileApp(table=profiles)  # The exposed endpoint "identity" of the app can be changed to anything
profile_app.register_routes(rt)  # The concept remains "profile" for unexposed internal use

# Derived from BaseApp, this is the plugin app to copy/paste/modify to create a new plugin
# TodoApp functionality, aka the linked-list CRUD pattern, forms the basis of many apps
todo_app = TodoApp(table=tasks)  # Instantiate with the appropriate table
todo_app.register_routes(rt)  # Register the routes

# Other plugins don't need these aliases. The first instances of todos and profiles are special in how they initialize the web framework.
# profiles = clients  # Wires arbitrary endpoint-controlling table name (clients) to hardwired ONLY profile app instance
todos = tasks  # Wires arbitrary endpoint-controlling table name (tasks) to hardwired first todo app instance
# variable names proifles and todos must never change. Their values (table names) can be whatever you want.

# Configure the menus using names of the plugin app instances (often the stringified version)
MENU_ITEMS = [  # Search for "menuxxx" to jump here for frequent menu tweaking
    '',
    'profile',
    todo_app.name,
    'pipe_flow',
    'starter_flow',
    'stream_simulator',
    'mobile_chat',
]

friendly_names = {
    "": "Home",
    "profile": "Profile List",
    "task": "Task List",
}


def build_endpoint_messages(endpoint):
    """Build a dictionary mapping menu endpoints to LLM prompts that guide the user experience."""

    endpoint_messages = {
        "": f"Welcome to {APP_NAME}.",
        "profile": (
            "This is where you add, edit, and delete clients. "
            "The Nickname field is hidden on the menu so client names are never exposed unless in client (profile) list app."
        ),
        "task": (
            "This is where you manage your tasks. "
            "For a little fun, ask me to add an apple to the task list."
        ),
        "stream_simulator": "Stream Simulator app is where you simulate a long-running server-side process.",
        "pipe_flow": "Workflow app is where you manage your workflows.",
        "starter_flow": "Starter Flow app is the template for new workflows.",
        "mobile_chat": "Even when installed on your desktop, you can chat with the local LLM from your phone.",
    }
    return endpoint_messages.get(endpoint, None)


def read_training_file(endpoint):
    """Read training content from a markdown file in the training directory."""
    try:
        with open(f"training/{endpoint}", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"No training file found for {endpoint}")
        return f"Default training for {endpoint}"


def build_endpoint_training(endpoint):
    """Build a real-time prompt injection system for menu-driven LLM context training.

    This implements a novel "hot prompt injection" methodology, distinct from traditional 
    prompt engineering or model fine-tuning. Like Neo downloading Kung Fu in The Matrix,
    this system injects context-specific training into the LLM at the exact moment of 
    UI interaction, creating a just-in-time knowledge transfer system.
    """

    endpoint_training = {
        "": read_training_file("menu_home.md"),
        "profile": read_training_file("menu_profile.md"),
        "task": todo_list_training(),
        "stream_simulator": "Stream Simulator app is where you simulate a long-running server-side process.",
        "pipe_flow": "Workflow app is where you manage your workflows.",
        "starter_flow": "Starter Flow app is the template for new workflows.",
        "mobile_chat": ""
    }
    # Add the endpoint training to the conversation history
    conversation_history = append_to_conversation(endpoint_training[endpoint], "system")
    return

# figlet ---------------------------------------------------------------------------------------------
#  ____  _      _   _     _ _        ____  ____
# |  _ \(_) ___| |_| |   (_) | _____|  _ \| __ )
# | | | | |/ __| __| |   | | |/ / _ \ | | |  _ \
# | |_| | | (__| |_| |___| |   <  __/ |_| | |_) |
# |____/|_|\___|\__|_____|_|_|\_\___|____/|____/
#
# *******************************
# DictLikeDB Persistence Convenience Wrapper (switch eventually to composite primary key)
# *******************************

# Color map for easy customization
COLOR_MAP = {
    "key": "yellow",
    "value": "white",
    "error": "red",
    "warning": "yellow",
    "success": "green",
    "debug": "blue"
}


def db_operation(func):
    """Decorator that logs only meaningful database state changes."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # Only log actual state changes
            if func.__name__ == '__setitem__':
                key, value = args[1], args[2]
                # Skip logging for internal keys and temp values
                if not key.startswith('_') and not key.endswith('_temp'):
                    logger.debug(f"DB: {key} = {str(value)[:50]}...")
            return result
        except Exception as e:
            logger.error(f"DB Error: {e}")
            raise
    return wrapper


class DictLikeDB:
    """
    A robust wrapper for dictionary-like persistent storage.

    This class provides a familiar dict-like interface to interact with
    various types of key-value stores, including databases and file systems.
    It emphasizes the power and flexibility of key-value pairs as a
    fundamental data structure in programming and system design.

    Key features:
    1. Persistence: Data survives beyond program execution.
    2. Dict-like API: Familiar Python dictionary operations.
    3. Adaptability: Can wrap different storage backends.
    4. Logging: Built-in logging for debugging and monitoring.

    By abstracting the underlying storage mechanism, this class allows
    for easy swapping of backends without changing the client code.
    This demonstrates the power of Python's duck typing and the
    universality of the key-value paradigm across different storage solutions.
    """

    def __init__(self, store, Store):
        self.store = store
        self.Store = Store
        logger.debug("DictLikeDB initialized.")

    @db_operation
    def __getitem__(self, key):
        try:
            value = self.store[key].value
            logger.debug(f"Retrieved from DB: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")
            return value
        except NotFoundError:
            logger.error(f"Key not found: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
            raise KeyError(key)

    @db_operation
    def __setitem__(self, key, value):
        try:
            self.store.update({"key": key, "value": value})
            logger.debug(f"Updated persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")
        except NotFoundError:
            self.store.insert({"key": key, "value": value})
            logger.debug(f"Inserted new item in persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}> = <{COLOR_MAP['value']}>{value}</{COLOR_MAP['value']}>")

    @db_operation
    def __delitem__(self, key):
        try:
            self.store.delete(key)
            logger.warning(f"Deleted key from persistence store: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
        except NotFoundError:
            logger.error(f"Attempted to delete non-existent key: <{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>")
            raise KeyError(key)

    @db_operation
    def __contains__(self, key):
        exists = key in self.store
        logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' exists: <{COLOR_MAP['value']}>{exists}</{COLOR_MAP['value']}>")
        return exists

    @db_operation
    def __iter__(self):
        for item in self.store():
            yield item.key

    @db_operation
    def items(self):
        for item in self.store():
            yield item.key, item.value

    @db_operation
    def keys(self):
        return list(self)

    @db_operation
    def values(self):
        for item in self.store():
            yield item.value

    @db_operation
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' not found. Returning default: <{COLOR_MAP['value']}>{default}</{COLOR_MAP['value']}>")
            return default

    @db_operation
    def set(self, key, value):
        """
        Set a key-value pair in the store. Alias for __setitem__ to provide a more
        method-oriented interface alongside the dict-like interface.

        This is particularly useful for async contexts and when a more explicit
        method name is preferred over the [] syntax.
        """
        self[key] = value
        return value  # Return value for method chaining


# Create global instance of DictLikeDB available to all functions
# In a single-tenant app, this database wrapper acts as a server-side session store,
# providing similar functionality to client cookies but with better control:
# - Centralized data access through the wrapper enables comprehensive logging
# - All operations go through application logic rather than client-side state
# - Greater visibility into how/when/where data changes via the decorator logs
db = DictLikeDB(store, Store)
logger.debug("Database wrapper initialized.")


# *******************************
# Database Initialization (belongs below home banner, but want home to show first)
# *******************************

def populate_initial_data():
    """
    Populate the database with initial data if empty.

    This function ensures that there is at least one profile and one todo item in the database.
    Also cleans up any persistent data except last_app_choice, last_visited_url and last_profile_id.
    """
    logger.debug("Populating initial data.")

    # Clean up persistent data except allowed keys
    allowed_keys = {'last_app_choice', 'last_visited_url', 'last_profile_id'}
    for key in list(db.keys()):
        if key not in allowed_keys:
            try:
                del db[key]
                logger.debug(f"Deleted non-essential persistent key: {key}")
            except KeyError:
                pass

    if not profiles():
        # Create a default profile
        default_profile = profiles.insert({
            "name": f"Default {profile_app.name.capitalize()}",
            "address": "",
            "code": "",
            "active": True,
            "priority": 0,
        })
        logger.debug(f"Inserted default profile: {default_profile}")
    else:
        default_profile = profiles()[0]

    if not todos():
        # Add a sample todo with the default profile_id
        todos.insert({
            "name": f"Sample {todo_app.name}",
            "done": False,
            "priority": 1,
            "profile_id": default_profile.id,
        })
        logger.debug(f"Inserted sample {todo_app.name} item.")


# Call this function after the fast_app initialization
populate_initial_data()  # We always need at least one profile_id


def priority_key(item):
    """
    Convert the priority of an item to a numeric value for sorting.

    This function attempts to convert the priority of an item to a float.
    If the conversion is successful, it returns the float value.
    If the conversion fails (e.g., due to non-numeric priority), it returns
    float('inf') to ensure these items are sorted to the end of the list.

    Args:
        item: An object with a 'priority' attribute.

    Returns:
        float: The numeric priority value, or float('inf') if conversion fails.
    """
    try:
        # Try to convert priority to float
        return float(item.priority or 0)
    except (ValueError, TypeError):
        # If conversion fails, return a default value
        return float('inf')  # This will sort non-numeric priorities to the end

# figlet ---------------------------------------------------------------------------------------------
#  ____  _             _       _
# |  _ \(_)_ __  _   _| | __ _| |_ ___
# | |_) | | '_ \| | | | |/ _` | __/ _ \
# |  __/| | |_) | |_| | | (_| | ||  __/
# |_|   |_| .__/ \__,_|_|\__,_|\__\___|
#         |_|
# *******************************
# Pipulate Workflow Pipeline Pattern
# *******************************


llm_speedbump_dict["pipulate"] = """
    Create interruption-safe workflows with step-based state tracking

    DON'T DO THIS (Celery style):
        @celery.task
        def process_data(data):
            result = step1.delay(data)
            result = step2.delay(result)
            return step3.delay(result)
    
    DO THIS INSTEAD:
        # Define steps with clear data ownership
        steps = [
            Step(id='step_01', done='name', show='Your Name', refill=True),
            Step(id='step_02', done='email', show='Your Email', refill=True),
            Step(id='finalize', done='finalized', show='Finalize', refill=False)
        ]

        # State JSON shows completion via step presence
        state = {
            "step_01": {"name": "John"},          # Each step owns its data
            "step_02": {"email": "j@j.com"},      # Present = completed
            "created": "2024-01-31T...",          # First creation
            "updated": "2024-01-31T...",          # Last update
            "_revert_target": "step_01",          # Optional revert state
            "finalize": {"finalized": True}       # Optional lock state
        }
    
    Why? Because:
    1. Steps own their data explicitly
    2. Progress tracked by step presence
    3. Interruption-safe at any point
    4. Forward-only state flow
    5. Built-in revert capability
    6. Finalization pattern for locking
    7. HTMX chain reactions for UI
    8. URL-based state resumption
    9. Refillable fields support
    10. Single source of truth in DB

    Core Patterns:
    - Submit clears forward, Display shows past
    - Each step is self-contained
    - State flows forward only
    - Revert jumps backward
    - Finalize locks all steps
"""


def pipeline_operation(func):
    """Decorator that tracks meaningful pipeline state changes."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        url = args[0] if args else None
        if not url:
            return func(self, *args, **kwargs)

        # Get initial state, ignoring timestamps
        old_state = self._get_clean_state(url)

        # Execute operation
        result = func(self, *args, **kwargs)

        # Compare with new state
        new_state = self._get_clean_state(url)

        # Log meaningful changes only
        if old_state != new_state:
            changes = {k: new_state[k] for k in new_state
                       if k not in old_state or old_state[k] != new_state[k]}
            if changes:
                logger.info(f"Pipeline '{url}' state updated: {changes}")

        return result

    return wrapper


class Pipulate:
    """
    Pipulate manages a multi-step workflow pipeline using a JSON blob stored in a database table.
    Each step's data is stored under keys like "step_01", "step_02", etc.

    Key Features:
    - Progress tracking via presence of step keys (no explicit 'current_step' field needed)
    - Automatic step progression (next step = highest existing step + 1)
    - Persistent state between interruptions
    - Jump-to-step capability from any point

    Example State JSON (stored in table's "data" field):
    {
        "step_01": {"name": "John"},          # Each step stores its own data
        "step_02": {"color": "blue"},         # Steps present = completed steps
        "created": "2024-12-08T12:34:56",     # First pipeline creation
        "updated": "2024-12-08T12:35:45"      # Last state change
    }

    Database Schema (FastHTML MiniDataAPI table):
    pipeline = {
        "url": str,      # Primary key - unique workflow identifier
        "app_name": str, # Endpoint name for routing and filtering
        "data": str,     # JSON blob containing full workflow state
        "created": str,  # ISO timestamp of creation
        "updated": str,  # ISO timestamp of last update
        "pk": "url"      # Primary key definition
    }

    Usage Flow:
    1. User enters/resumes workflow via URL (/app_name/step_N)
    2. System loads state from database using URL as key
    3. UI shows appropriate step based on existing state
    4. Each step completion updates state in database
    5. Workflow continues until finalized

    The workflow is designed to be interruption-safe - users can leave and 
    resume from any point by re-entering their workflow URL.
    """

    # Default to preserving refillable fields
    PRESERVE_REFILL = True

    def __init__(self, table):
        """Initialize a Pipulate instance for managing pipeline state.

        This is the core state management class for FastHTML pipelines. It deliberately
        uses a simple table-based approach rather than ORM patterns. The table parameter
        is a MiniDataAPI table with the following schema:

        table = {
            "url": str,      # Primary key - unique workflow ID 
            "app_name": str, # Endpoint name for routing/filtering
            "data": str,     # JSON blob containing full state
            "created": str,  # ISO timestamp
            "updated": str,  # ISO timestamp
            "pk": "url"      # Primary key definition
        }

        Key Principles:
        - One record = One complete pipeline state
        - State flows forward only (submit clears forward steps)
        - Display state != Persistence state
        - Each step must be idempotent
        - No ORM, no sessions, embrace server-side state

        Args:
            table: MiniDataAPI table for storing pipeline state

        Remember:
        - Always clear_steps_from() in submit handlers
        - Preserve flag only affects UI/display
        - Use standard pipulate helpers
        - Test both first-time and resubmit flows
        """
        self.table = table

    def _get_clean_state(self, url):
        """Get pipeline state without timestamps."""
        try:
            record = self.table[url]
            state = json.loads(record.data)
            state.pop('created', None)
            state.pop('updated', None)
            return state
        except (NotFoundError, json.JSONDecodeError):
            return {}

    def get_timestamp(self) -> str:
        """Get ISO timestamp for pipeline state tracking.

        This is a critical helper that ensures consistent timestamp format across
        all pipeline state operations. Used for both creation and update times.

        The ISO format is required by MiniDataAPI's simple table schema and helps
        maintain the local-first, single-source-of-truth principle for state 
        management without introducing database-specific timestamp types.

        Returns:
            str: Current timestamp in ISO format (e.g. "2024-03-19T15:30:45.123456")
        """
        return datetime.now().isoformat()

    @pipeline_operation
    def initialize_if_missing(self, url: str, initial_step_data: dict = None) -> tuple[Optional[dict], Optional[Card]]:
        """Critical pipeline initialization that establishes the single source of truth.

        This is the gatekeeper for new pipeline state. It ensures we have exactly one
        record per URL and maintains the local-first principle by using MiniDataAPI's
        simple table constraints rather than distributed locking.

        The state blob follows the pattern:
        {
            "created": "2024-03-19T...",  # ISO timestamp
            "updated": "2024-03-19T...",  # ISO timestamp
            "step_01": {...},             # Optional initial state
            ...                           # Additional step data
        }

        Args:
            url: Pipeline identifier (primary key)
            initial_step_data: Optional seed data for first step(s)

        Returns:
            (state, None) if successful initialization or existing state
            (None, error_card) if URL conflict detected
        """

        try:
            # First try to get existing state
            state = self.read_state(url)
            if state:  # If we got anything back (even empty dict), record exists
                return state, None

            # No record exists, create new state
            now = self.get_timestamp()
            state = {
                "created": now,
                "updated": now
            }

            if initial_step_data:
                app_name = None
                if "app_name" in initial_step_data:
                    app_name = initial_step_data.pop("app_name")
                state.update(initial_step_data)

            # Insert new record with normalized endpoint
            self.table.insert({
                "url": url,
                "app_name": app_name if app_name else None,
                "data": json.dumps(state),
                "created": now,
                "updated": now
            })
            return state, None

        except:  # Catch constraint violation
            error_card = Card(
                H3("ID Already In Use"),
                P(f"The ID '{url}' is already being used by another workflow. Please try a different ID."),
                style=self.id_conflict_style()
            )
            return None, error_card

    def read_state(self, url: str) -> dict:
        """Core pipeline state reader that maintains the single source of truth."""
        logger.debug(f"Reading state for pipeline: {url}")
        try:
            self.table.xtra(url=url)
            records = self.table()

            # Debug what we got back
            logger.debug(f"Records found: {records}")
            if records:
                logger.debug(f"First record type: {type(records[0])}")
                logger.debug(f"First record dir: {dir(records[0])}")

            if records and hasattr(records[0], 'data'):
                state = json.loads(records[0].data)
                logger.debug(f"Found state: {json.dumps(state, indent=2)}")
                return state

            logger.debug("No valid state found")
            return {}

        except Exception as e:
            logger.debug(f"Error reading state: {str(e)}")
            return {}

    def write_state(self, url: str, state: dict) -> None:
        """Write pipeline state with forward-only flow."""
        # Update timestamp
        state["updated"] = datetime.now().isoformat()

        # Simple update payload
        payload = {
            "url": url,
            "data": json.dumps(state),
            "updated": state["updated"]
        }

        # Debug the exact update
        logger.debug(f"Update payload:\n{json.dumps(payload, indent=2)}")

        # Write and verify (always)
        self.table.update(payload)
        verification = self.read_state(url)
        logger.debug(f"Verification read:\n{json.dumps(verification, indent=2)}")

    async def write_step_data(self, pipeline_id: str, step_id: str, step_data: dict) -> None:
        """Write step data to the pipeline state."""
        logger.debug(f"[write_step_data] ENTRY - pipeline={pipeline_id}, step={step_id}")
        logger.debug(f"[write_step_data] Step data: {json.dumps(step_data, indent=2)}")

        # Check for jump parameter in HX-Vals header
        request = get_request()  # Get current request context
        vals = request.headers.get("HX-Vals", "{}")
        try:
            vals_dict = json.loads(vals)
            is_jump = vals_dict.get("jump") == "true"
            logger.debug(f"[write_step_data] HX-Vals: {vals}, is_jump={is_jump}")
        except json.JSONDecodeError:
            logger.warning(f"[write_step_data] Invalid HX-Vals format: {vals}")
            is_jump = False

        # Get current state
        current_state = self.read_state(pipeline_id)
        logger.debug(f"[write_step_data] Current state:")
        logger.debug(json.dumps(current_state, indent=2))

        # Update with new step data
        current_state[step_id] = step_data
        current_state["updated"] = datetime.now().isoformat()
        logger.debug(f"[write_step_data] Updated state:")
        logger.debug(json.dumps(current_state, indent=2))

        # Write back to database
        record = {
            "url": pipeline_id,
            "app_name": "starter",
            "data": json.dumps(current_state),
            "updated": current_state["updated"]
        }

        # Check if record exists
        self.table.xtra(url=pipeline_id)
        existing = self.table()

        if existing:
            record["created"] = getattr(existing[0], "created", current_state["updated"])
            record["app_name"] = getattr(existing[0], "app_name", "starter")
            self.table.update(record)
            logger.debug("[write_step_data] Updated existing record")
        else:
            record["created"] = current_state["updated"]
            self.table.insert(record)
            logger.debug("[write_step_data] Created new record")

        logger.debug("[write_step_data] EXIT - Step data written successfully")

    def chain_reaction(self, steps, app_name):
        """Trigger a chain reaction to refresh all steps."""
        # Create a list of URLs for each step including finalize
        urls = []
        for step in steps:
            urls.append(f"/{app_name}/{step.id}")
        urls.append(f"/{app_name}/finalize")  # Add finalize step

        # Return the URLs that need to be refreshed
        return urls

    def revert_control(
        self,
        step_id: str,
        app_name: str,
        steps: list,
        message: str = None,
        target_id: str = None,
        revert_label: str = None
    ):
        """Creates a revert control that clears forward steps.

        Args:
            step_id: Step to revert to (e.g. "step_01")
            app_name: URL prefix for workflow routes
            steps: Full STEPS list from workflow definition
            message: Optional message to show with control
            target_id: HTMX target for revert action (defaults to app container)
            style: Optional custom CSS styles
            revert_label: Optional custom label for revert button
        """
        pipeline_id = db.get("pipeline_id", "")

        # Check if pipeline is finalized
        finalize_step = steps[-1]
        if pipeline_id:
            final_data = self.get_step_data(pipeline_id, finalize_step.id, {})
            if finalize_step.done in final_data:
                return None

        # Find current step's persistence setting
        step = next(s for s in steps if s.id == step_id)
        refill = getattr(step, 'refill', False)

        # Use app container as default target
        if not target_id:
            target_id = f"{app_name}-container"

        # Default button styling
        default_style = (
            "background-color: var(--pico-del-color);"
            "display: inline-flex;"
            "padding: 0.5rem 0.5rem;"
            "border-radius: 4px;"
            "font-size: 0.85rem;"
            "cursor: pointer;"
            "margin: 0;"
            "line-height: 1;"
            "align-items: center;"
        )

        form = Form(
            Input(type="hidden", name="step_id", value=step_id),
            Button(
                format_step_button(step_id, refill, revert_label),
                type="submit",
                style=default_style
            ),
            hx_post=f"/{app_name}/revert",
            hx_target=f"#{target_id}",
            hx_swap="outerHTML"
        )

        # Return simple form if no message
        if not message:
            return form

        # Return styled card with message if provided
        return Card(
            Div(message, style="flex: 1;"),
            Div(form, style="flex: 0;"),
            style="display: flex; align-items: center; justify-content: space-between;"
        )

    def wrap_with_inline_button(
        self,
        input_element: Input,
        button_label: str = "Next",
        button_class: str = "primary"
    ) -> Div:
        """Helper for creating inline form controls in pipelines.

        This is a key UI pattern for FastHTML pipelines - it creates a flex container
        with an input and submit button side-by-side. The button width is explicitly
        overridden from PicoCSS defaults to prevent stretching.

        Usage:
            form = Form(
                self.wrap_with_inline_button(
                    Input(type="text", name="quest"),
                    "Continue Quest"
                )
            )

        The resulting HTML will have proper flex layout and consistent button styling
        that works with the pipeline's visual language.
        """
        return Div(
            input_element,
            Button(
                button_label,
                type="submit",
                cls=button_class,
                style=(
                    "display: inline-block;"
                    "cursor: pointer;"
                    "width: auto !important;"  # Override PicoCSS width: 100%
                    "white-space: nowrap;"
                )
            ),
            style="display: flex; align-items: center; gap: 0.5rem;"
        )

    def generate_step_messages(self, steps: list) -> dict:
        """Generates the standard message templates for a FastHTML pipeline workflow.

        Chain Reaction Pattern:
        1. Each step has input and complete messages
        2. Messages reference step IDs for state tracking
        3. Special handling for finalize step
        4. Messages support the single source of truth

        The messages integrate with the chain reaction by:
        - Using step IDs consistently for state lookup
        - Supporting forward-only data flow
        - Providing context for completed steps
        - Handling finalize state transitions
        """
        messages = {
            "new": f"Step 1: Enter your {steps[0].show}"
        }

        # Generate messages keyed by step ID
        for i, step in enumerate(steps[:-1], 1):  # Skip final step
            next_step = steps[i]
            messages[step.id] = {
                "input": f"Step {i}: Enter {step.show}",
                "complete": f"{format_step_name(step.id)} complete. You entered &lt;{{}}&gt;. Continue to {next_step.id}."
            }

        # Finalize step gets special ID-based state handling
        messages["finalize"] = {
            "ready": "All steps complete. Ready to finalize workflow.",
            "complete": "Workflow finalized. Use Unfinalize to make changes."
        }

        return messages

    async def get_state_message(self, url: str, steps: list, messages: dict) -> str:
        """
        Core pipeline state message generator that follows the Pipeline Mantra.

        This is a critical piece of the Pipeline Pattern that ensures state flows
        forward correctly by checking steps in reverse order. It handles both
        standard steps and the special finalize step, integrating with the
        Finalization Pattern for workflow locking.

        The reverse order check is key - it finds the last completed step and
        generates the appropriate message, whether that's showing completed data
        or prompting for input. This matches our "Submit clears forward, Display
        shows the past" principle.

        See StarterFlow for working examples of message integration.
        """
        state = self.read_state(url)
        logger.debug(f"\nDEBUG [{url}] State Check:")
        logger.debug(json.dumps(state, indent=2))

        # Check steps in reverse order (including finalize)
        for step in reversed(steps):  # Use Step objects directly
            if step.id not in state:
                continue

            # Special handling for finalize step
            if step.done == "finalized":
                if step.done in state[step.id]:
                    return self._log_message("finalized", messages["finalize"]["complete"])
                return self._log_message("ready to finalize", messages["finalize"]["ready"])

            # Standard step handling
            step_data = state[step.id]
            step_value = step_data.get(step.done)

            if step_value:
                msg = messages[step.id]["complete"]
                msg = msg.format(step_value) if "{}" in msg else msg
                return self._log_message(f"{step.id} complete ({step_value})", msg)

            # return self._log_message(f"{step.id} input needed", messages[step.id]["input"])

        # No steps found - new workflow
        return self._log_message("new pipeline", messages["new"])

    def _log_message(self, state_desc: str, message: str) -> str:
        """Logs pipeline state transitions and maintains LLM conversation context.

        This is a critical piece of the Pipeline Pattern's state tracking that:
        1. Logs state transitions for debugging/development
        2. Feeds state messages into the LLM conversation history
        3. Returns the message for UI display

        The quiet=True on append prevents LLM chat noise while maintaining context.
        This follows the DEBUG Pattern from .cursorrules: "Just log it!"
        """
        # Escape angle brackets for logging
        safe_state = state_desc.replace("<", "\\<").replace(">", "\\>")
        safe_message = message.replace("<", "\\<").replace(">", "\\>")

        logger.debug(f"State: {safe_state}, Message: {safe_message}")
        append_to_conversation(message, role="system", quiet=True)
        return message

    @pipeline_operation
    def get_step_data(self, url: str, step_id: str, default=None) -> dict:
        """Get step data from pipeline state.

        This is a critical piece of the Pipeline Pattern that retrieves
        the current state data for a specific step. If the step doesn't
        exist in state, returns the provided default value.

        See StarterFlow for usage examples.
        """
        state = self.read_state(url)
        return state.get(step_id, default or {})

    async def clear_steps_from(self, pipeline_id: str, step_id: str, steps: list) -> dict:
        """Clear steps forward in pipeline state."""
        state = self.read_state(pipeline_id)

        # Find starting index
        start_idx = next((i for i, step in enumerate(steps) if step.id == step_id), -1)
        if start_idx == -1:
            logger.error(f"[clear_steps_from] Step {step_id} not found in steps list")
            return state

        # Clear forward steps based on flow configuration
        for step in steps[start_idx + 1:]:
            if (not self.PRESERVE_REFILL or not step.refill) and step.id in state:
                logger.debug(f"[clear_steps_from] Removing step {step.id}")
                del state[step.id]

        # Write updated state
        self.write_state(pipeline_id, state)
        return state


# Global instance - module scope is the right scope
pipulate = Pipulate(pipeline)


class BaseFlow:
    """Base class for multi-step flows with finalization."""

    PRESERVE_REFILL = True

    def __init__(self, app, pipulate, app_name, steps):
        self.app = app
        self.pipulate = pipulate
        self.app_name = app_name
        self.STEPS = steps
        self.steps = {step.id: i for i, step in enumerate(self.STEPS)}

        # Generate default messages
        self.STEP_MESSAGES = {
            "new": "Enter an ID to begin.",
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": "Workflow finalized. Use Unfinalize to make changes."
            }
        }

        # Add messages for each step
        for step in self.STEPS:
            if step.done != 'finalized':  # Skip finalize step
                self.STEP_MESSAGES[step.id] = {
                    "input": f"Step {step.id}: Please enter {step.show}",
                    "complete": f"{step.show} complete: <{{}}>. Continue to next step."
                }

        # Auto-register all routes
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"])
        ]

        # Add step routes automatically from STEPS
        for step in self.STEPS:
            routes.extend([
                (f"/{app_name}/{step.id}", self.handle_step),
                (f"/{app_name}/{step.id}_submit", self.handle_step_submit, ["POST"])
            ])

        # Register all routes
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            self.app.route(path, methods=method_list)(handler)

    def validate_step(self, step_id: str, value: str) -> tuple[bool, str]:
        """Override this method to add custom validation per step.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        return True, ""

    async def process_step(self, step_id: str, value: str) -> str:
        """Override this method to transform/process step input.

        Returns:
            str: Processed value to store
        """
        return value

    async def handle_revert(self, request):
        """Handle revert action by clearing steps after the reverted step."""
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")

        if not step_id:
            return P("Error: No step specified", style="color: red;")

        # Clear forward steps
        await self.pipulate.clear_steps_from(pipeline_id, step_id, self.STEPS)

        # Set revert target in state
        state = self.pipulate.read_state(pipeline_id)
        state["_revert_target"] = step_id
        self.pipulate.write_state(pipeline_id, state)

        # Get state-aware message
        message = await self.pipulate.get_state_message(pipeline_id, self.STEPS, self.STEP_MESSAGES)
        await simulated_stream(message)

        # Return same container structure as init()
        placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
        return Div(*placeholders, id=f"{self.app_name}-container")

    async def landing(self, display_name=None):
        """Default landing page for flow."""
        # Use provided display_name or generate default
        title = display_name or f"{self.app_name.title()}: {len(self.STEPS) - 1} Steps + Finalize"

        pipeline.xtra(app_name=self.app_name)
        existing_ids = [record.url for record in pipeline()]

        return Container(
            Card(
                H2(title),
                P("Enter or resume a Pipeline ID:"),
                Form(
                    self.pipulate.wrap_with_inline_button(
                        Input(
                            type="text",
                            name="pipeline_id",
                            placeholder="🗝 Old or existing ID here",
                            required=True,
                            autofocus=True,
                            list="pipeline-ids"
                        ),
                        button_label=f"Start {self.app_name.title()} 🔑",
                        button_class="secondary"
                    ),
                    Datalist(
                        *[Option(value=pid) for pid in existing_ids],
                        id="pipeline-ids"
                    ),
                    hx_post=f"/{self.app_name}/init",
                    hx_target=f"#{self.app_name}-container"
                )
            ),
            Div(id=f"{self.app_name}-container")
        )

    async def init(self, request):
        """Standard init handler that sets up pipeline state."""
        form = await request.form()
        pipeline_id = form.get("pipeline_id", "untitled")
        db["pipeline_id"] = pipeline_id

        # Initialize pipeline
        state, error = self.pipulate.initialize_if_missing(
            pipeline_id,
            {"app_name": self.app_name}
        )

        if error:
            return error

        # Generate placeholders for all steps
        placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)

        return Div(
            *placeholders,
            id=f"{self.app_name}-container"
        )

    async def handle_step(self, request):
        """Generic step handler following the Step Display Pattern."""
        step_id = request.url.path.split('/')[-1]
        step_index = self.steps[step_id]
        step = self.STEPS[step_index]
        next_step_id = self.STEPS[step_index + 1].id if step_index < len(self.STEPS) - 1 else None

        pipeline_id = db.get("pipeline_id", "unknown")
        state = self.pipulate.read_state(pipeline_id)
        step_data = self.pipulate.get_step_data(pipeline_id, step_id, {})
        user_val = step_data.get(step.done, "")

        # Special handling for finalize step
        if step.done == 'finalized':
            finalize_data = self.pipulate.get_step_data(pipeline_id, "finalize", {})

            if "finalized" in finalize_data:
                return Card(
                    H3("Pipeline Finalized"),
                    P("All steps are locked."),
                    Form(
                        Button("Unfinalize", type="submit", style="background-color: #f66;"),
                        hx_post=f"/{self.app_name}/unfinalize",
                        hx_target=f"#{self.app_name}-container",
                        hx_swap="outerHTML"
                    )
                )
            else:
                return Div(
                    Card(
                        H3("Finalize Pipeline"),
                        P("You can finalize this pipeline or go back to fix something."),
                        Form(
                            Button("Finalize All Steps", type="submit"),
                            hx_post=f"/{self.app_name}/{step_id}_submit",
                            hx_target=f"#{self.app_name}-container",
                            hx_swap="outerHTML"
                        )
                    ),
                    id=step_id
                )

        # If locked, always chain to next step
        finalize_data = self.pipulate.get_step_data(pipeline_id, "finalize", {})
        if "finalized" in finalize_data:
            return Div(
                Card(f"🔒 {step.show}: {user_val}"),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        # If completed, show with revert and chain
        if user_val and state.get("_revert_target") != step_id:
            return Div(
                self.pipulate.revert_control(
                    step_id=step_id,
                    app_name=self.app_name,
                    message=f"{step.show}: {user_val}",
                    steps=self.STEPS
                ),
                Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
            )

        # Get value to show in input - either from refill or suggestion
        display_value = ""
        if step.refill and user_val and self.PRESERVE_REFILL:
            display_value = user_val  # Use existing value if refilling
        else:
            suggested = await self.get_suggestion(step_id, state)
            display_value = suggested  # Use suggestion if no refill value

        await simulated_stream(self.STEP_MESSAGES[step_id]["input"])

        # Show input form
        return Div(
            Card(
                H3(f"Enter {step.show}"),
                Form(
                    self.pipulate.wrap_with_inline_button(
                        Input(
                            type="text",
                            name=step.done,
                            value=display_value,
                            placeholder=f"Enter {step.show}",
                            required=True,
                            autofocus=True
                        )
                    ),
                    hx_post=f"/{self.app_name}/{step_id}_submit",
                    hx_target=f"#{step_id}"
                )
            ),
            Div(id=next_step_id),
            id=step_id
        )

    async def get_suggestion(self, step_id, state):
        """Override this in your flow to provide dynamic suggestions"""
        return ""

    async def handle_step_submit(self, request):
        """Generic submit handler for all steps."""
        step_id = request.url.path.split('/')[-1].replace('_submit', '')
        step_index = self.steps[step_id]
        step = self.STEPS[step_index]

        pipeline_id = db.get("pipeline_id", "unknown")

        # Special handling for finalize step
        if step.done == 'finalized':
            # Update the state
            state = self.pipulate.read_state(pipeline_id)
            state[step_id] = {step.done: True}
            self.pipulate.write_state(pipeline_id, state)

            # Get state-aware message
            message = await self.pipulate.get_state_message(pipeline_id, self.STEPS, self.STEP_MESSAGES)
            await simulated_stream(message)

            # Return same container structure as init()
            placeholders = self.generate_step_placeholders(self.STEPS, self.app_name)
            return Div(*placeholders, id=f"{self.app_name}-container")

        # Regular step handling continues here...
        form = await request.form()
        user_val = form.get(step.done, "")

        # Validate input
        is_valid, error_msg = self.validate_step(step_id, user_val)
        if not is_valid:
            return P(error_msg, style="color: red;")

        # Process input
        processed_val = await self.process_step(step_id, user_val)
        next_step_id = self.STEPS[step_index + 1].id if step_index < len(self.STEPS) - 1 else None

        # Clear forward steps
        await self.pipulate.clear_steps_from(pipeline_id, step_id, self.STEPS)

        # Write new state and clear revert target
        state = self.pipulate.read_state(pipeline_id)
        state[step_id] = {step.done: processed_val}
        if "_revert_target" in state:
            del state["_revert_target"]
        self.pipulate.write_state(pipeline_id, state)

        # Get state-aware message
        message = await self.pipulate.get_state_message(pipeline_id, self.STEPS, self.STEP_MESSAGES)
        await simulated_stream(message)

        # Chain to next step
        return Div(
            self.pipulate.revert_control(
                step_id=step_id,
                app_name=self.app_name,
                message=f"{step.show}: {processed_val}",
                steps=self.STEPS
            ),
            Div(id=next_step_id, hx_get=f"/{self.app_name}/{next_step_id}", hx_trigger="load")
        )

    def format_textarea(self, text: str, with_check: bool = False) -> P:
        """
        Formats pipeline step text with consistent FastHTML styling.

        This is a core UI helper used across pipeline steps to maintain
        consistent text display. The pre-wrap and margin settings ensure
        multi-line text displays properly within pipeline cards.

        The optional checkmark (✓) indicates completed steps in the
        pipeline flow, following the "show completed state" pattern
        from .cursorrules.

        Args:
            text: Text content to format (usually from pipeline state)
            with_check: Add completion checkmark (default: False)
        """
        return P(
            Pre(
                text,
                style=(
                    "white-space: pre-wrap; "
                    "margin-bottom: 0; "
                    "margin-right: .5rem; "
                    "padding: .25rem;"
                )
            ),
            " ✓" if with_check else ""
        )

    def generate_step_placeholders(self, steps, app_name):
        """Generate placeholder divs for each step with proper HTMX triggers."""
        placeholders = []
        for i, step in enumerate(steps):
            trigger = "load"
            if i > 0:
                # Chain reaction: trigger when previous step completes
                prev_step = steps[i - 1]
                trigger = f"stepComplete-{prev_step.id} from:{prev_step.id}"

            placeholders.append(
                Div(
                    id=step.id,
                    hx_get=f"/{app_name}/{step.id}",
                    hx_trigger=trigger,
                    hx_swap="outerHTML"
                )
            )
        return placeholders

    async def delayed_greeting(self):
        """Provides a gentle UX delay before prompting for pipeline ID.

        The simulated chat stream maintains the illusion of "thinking" while
        actually just managing timing and UX expectations. This is preferable
        to instant responses which can make the system feel too reactive and
        breaking pace with the LLM-provided chat that has inherent latency.
        """
        await asyncio.sleep(2)
        await simulated_stream("Enter an ID to begin.")

    async def explain(self, message=None):
        asyncio.create_task(chatq(message, role="system"))

    async def handle_finalize(self, steps: list, app_name: str) -> Card:
        """Handles finalize step display based on pipeline state.

        This is a key state transition point that follows the Pipeline Pattern:
        - If finalized: Shows locked view with unfinalize option
        - If all steps complete: Shows finalize button
        - Otherwise: Shows "nothing to finalize" message

        The finalize step is special - it has no data of its own, just a flag.
        This maintains the "Submit clears forward" principle even at the end.

        Args:
            steps: List of Step objects defining the pipeline
            app_name: URL prefix for route generation
        """

        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = self.get_step_data(pipeline_id, finalize_step.id, {})

        # Add debug logging
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        if finalize_step.done in finalize_data:
            logger.debug("Pipeline is finalized")
            return Card(
                H3("All Cards Complete"),
                P("Pipeline is finalized. Use Unfinalize to make changes."),
                Form(
                    Button("Unfinalize", type="submit", style="background-color: #f66;"),
                    hx_post=f"/{app_name}/unfinalize",
                    hx_target=f"#{app_name}-container",
                    hx_swap="outerHTML"
                ),
                style="color: green;",
                id=finalize_step.id
            )

        # Check completion
        non_finalize_steps = steps[:-1]

        # Add debug logging for each step's completion state
        for step in non_finalize_steps:
            step_data = self.get_step_data(pipeline_id, step.id, {})
            step_value = step_data.get(step.done)
            logger.debug(f"Step {step.id} completion: {step_value}")

        all_steps_complete = all(
            self.get_step_data(pipeline_id, step.id, {}).get(step.done)
            for step in non_finalize_steps
        )

        logger.debug(f"All steps complete: {all_steps_complete}")

        if all_steps_complete:
            return Card(
                H3("Ready to finalize?"),
                P("All data is saved. Lock it in?"),
                Form(
                    Button("Finalize", type="submit"),
                    hx_post=f"/{app_name}/finalize_submit",
                    hx_target=f"#{app_name}-container",
                    hx_swap="outerHTML"
                ),
                id=finalize_step.id
            )
        return Div(P("Nothing to finalize yet."), id=finalize_step.id)

    async def handle_finalize_submit(self, steps: list, app_name: str, messages: dict) -> Div:
        """Handle submission of finalize step."""
        pipeline_id = db.get("pipeline_id", "unknown")

        # Get current state
        state = self.read_state(pipeline_id)

        # Add finalize flag
        state["finalize"] = {"finalized": True}

        # Update timestamp
        state["updated"] = datetime.now().isoformat()

        # Write updated state
        self.write_state(pipeline_id, state)

        # Return the same container with placeholders that initial load uses
        return Div(
            *self.generate_step_placeholders(steps, app_name),
            id=f"{app_name}-container"
        )

    async def handle_unfinalize(self, steps: list, app_name: str, messages: dict) -> Div:
        """Handle unfinalize action by removing finalize state."""
        pipeline_id = db.get("pipeline_id", "unknown")

        # Update state
        state = self.pipulate.read_state(pipeline_id)
        if "finalize" in state:
            del state["finalize"]
        self.pipulate.write_state(pipeline_id, state)

        # Return same container structure as init()
        placeholders = self.generate_step_placeholders(steps, app_name)
        return Div(*placeholders, id=f"{app_name}-container")

    def id_conflict_style(self):
        return "background-color: var(--pico-del-color);"


class StarterFlow(BaseFlow):
    """Minimal three-card pipeline with finalization."""

    def __init__(self, app, pipulate, app_name="starter"):
        # Define steps including finalize
        steps = [
            Step(id='step_01', done='name', show='Your Name', refill=True),
            Step(id='step_02', done='email', show='Your Email', refill=True),
            Step(id='step_03', done='phone', show='Your Phone', refill=True),
            Step(id='step_04', done='website', show='Your Website', refill=True),
            Step(id='finalize', done='finalized', show='Finalize', refill=False)
        ]

        # Let BaseFlow handle all the routing and step handling
        super().__init__(app, pipulate, app_name, steps)

        # Generate messages for this specific flow
        self.STEP_MESSAGES = self.pipulate.generate_step_messages(self.STEPS)

    # Override landing only if you need custom behavior
    async def landing(self):
        """Custom landing page for StarterFlow."""
        base_landing = await super().landing(display_name="Starter Flow Demo")
        asyncio.create_task(self.delayed_greeting())
        return base_landing

    # Finalization handlers
    async def finalize(self, request):
        return await self.handle_finalize(self.STEPS, self.app_name)

    async def finalize_submit(self, request):
        return await self.handle_finalize_submit(self.STEPS, self.app_name, self.STEP_MESSAGES)

    async def unfinalize(self, request):
        return await self.handle_unfinalize(self.STEPS, self.app_name, self.STEP_MESSAGES)

    async def jump_to_step(self, request):
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return self.pipulate.rebuild(self.app_name, self.STEPS)


class PipeFlow(BaseFlow):
    PRESERVE_REFILL = False

    def __init__(self, app, pipulate, app_name="pipeflow"):
        steps = [
            Step(id='step_01',
                 done='data',
                 show='Basic Word',
                 refill=False,
                 transform=None),  # No transform for first step
            Step(id='step_02',
                 done='data',
                 show='Make it Plural',
                 refill=False,
                 transform=lambda w: f"{w}s"),
            Step(id='step_03',
                 done='data',
                 show='Add Adjective',
                 refill=False,
                 transform=lambda w: f"happy {w}"),
            Step(id='step_04',
                 done='data',
                 show='Add Action',
                 refill=False,
                 transform=lambda w: f"{w} sleep"),
            Step(id='finalize',
                 done='finalized',
                 show='Finalize',
                 refill=False,
                 transform=None)  # No transform for final step
        ]
        super().__init__(app, pipulate, app_name, steps)

    async def get_suggestion(self, step_id, state):
        """Get transformed value from previous step's data"""
        step = next((s for s in self.STEPS if s.id == step_id), None)
        if not step or not step.transform:
            return ""

        prev_data = self.pipulate.get_step_data(
            db["pipeline_id"],
            f"step_0{int(step_id[-1]) - 1}",
            {}
        )
        prev_word = prev_data.get("data", "")
        return step.transform(prev_word) if prev_word else ""

    # Finalization handlers
    async def finalize(self, request):
        return await self.handle_finalize(self.STEPS, self.app_name)

    async def finalize_submit(self, request):
        return await self.handle_finalize_submit(self.STEPS, self.app_name, self.STEP_MESSAGES)

    async def unfinalize(self, request):
        return await self.handle_unfinalize(self.STEPS, self.app_name, self.STEP_MESSAGES)

    async def jump_to_step(self, request):
        form = await request.form()
        step_id = form.get("step_id")
        db["step_id"] = step_id
        return self.pipulate.rebuild(self.app_name, self.STEPS)


pipe_flow = PipeFlow(app, pipulate)
starter_flow = StarterFlow(app, pipulate)


@rt('/clear-db', methods=['POST'])
async def clear_db(request):
    """Debug endpoint to clear all entries from both DictLikeDB and pipeline table

    DEBUGGING SAFETY:
    - Only for development/testing 
    - Clears all server-side state (both cookie and pipeline)
    - Forces full page refresh to reset UI state
    - Should be disabled in production
    """

    # Clear DictLikeDB
    keys = list(db.keys())
    for key in keys:
        del db[key]
    logger.debug("DictLikeDB cleared")

    # Clear pipeline table
    records = list(pipulate.table())  # Get all records
    for record in records:
        pipulate.table.delete(record.url)  # Delete by primary key
    logger.debug("Pipeline table cleared")

    db["temp_message"] = "Database cleared."

    logger.debug("DictLikeDB cleared for debugging")
    return HTMLResponse(
        "Database cleared.",
        headers={"HX-Refresh": "true"}  # Trigger full page refresh
    )

# figlet ---------------------------------------------------------------------------------------------
#  _   _             _             _   _
# | \ | | __ ___   _(_) __ _  __ _| |_(_) ___  _ __
# |  \| |/ _` \ \ / / |/ _` |/ _` | __| |/ _ \| '_ \
# | |\  | (_| |\ V /| | (_| | (_| | |_| | (_) | | | |
# |_| \_|\__,_| \_/ |_|\__, |\__,_|\__|_|\___/|_| |_|
#                      |___/
# *******************************
# Site Navigation and Layout
# *******************************


def get_profile_name():
    """
    Retrieve the name of the current profile. Integral to the UI.

    This function attempts to get the name of the profile associated with the last used profile ID.
    If no last profile ID is found, it tries to use the first available profile.
    If no profiles exist, it returns "Unknown Profile".

    Returns:
        str: The name of the current profile, or "Unknown Profile" if no valid profile is found.

    Logs:
        - INFO: When using a default profile ID due to missing last_profile_id.
        - WARNING: When no profiles are found in the database.
        - DEBUG: Profile retrieval process and results.
    """
    # Get the last profile id from the database
    profile_id = db.get("last_profile_id")
    if profile_id is None:
        logger.debug("No last_profile_id found. Attempting to use the first available profile.")

    logger.debug(f"Retrieving profile name for ID: {profile_id}")
    try:
        profile = profiles.get(profile_id)
        if profile:
            logger.debug(f"Found profile: {profile.name}")
            return profile.name
    except NotFoundError:
        logger.warning(f"No profile found for ID: {profile_id}. Attempting to use the first available profile.")
        # Attempt to use the first available profile
        all_profiles = profiles()
        if all_profiles:
            first_profile = all_profiles[0]
            db["last_profile_id"] = first_profile.id  # Update the last_profile_id to the first profile
            logger.debug(f"Using first available profile ID: {first_profile.id}")
            return first_profile.name
        else:
            logger.warning("No profiles found in the database.")
            return "Unknown Profile"


llm_speedbump_dict["xtra"] = """
    Filter table results using xtra() - the core of MiniDataAPI filtering

    DON'T DO THIS (SQLAlchemy style):
        session.query(User).filter(
            User.active == True,
            User.role == 'admin'
        ).all()

    DO THIS INSTEAD:
        # Filter todos by profile
        todos.xtra(profile_id=current_profile_id)
        todo_items = todos()

        # Filter pipeline by app
        pipeline.xtra(app_name=self.app_name)
        existing_ids = [record.url for record in pipeline()]

        # Filter and count related records
        todos.xtra(profile_id=profile.id)
        todo_count = len(todos())

    Why? Because:
    1. Filters persist until explicitly changed
    2. Works with any table operation: table(), table[pk], etc
    3. Perfect for parent-child relationships
    4. No joins or complex queries needed
    5. Stateful filtering matches server-side state pattern
    6. Clean separation of filter and fetch
    7. Chainable for multiple conditions
    8. Core part of single-tenant pattern

    Key Patterns:
    - Use for parent-child filtering (todos by profile)
    - Use for app-specific queries (pipeline by app_name)
    - Use for counting related records
    - Clear filters when scope changes
"""


async def home(request):
    """
    Central routing and rendering mechanism for the application.

    This function processes requests for the main page and specific app pages defined in MENU_ITEMS.
    It allows for easy integration of new apps by adding them to the MENU_ITEMS list and implementing
    their corresponding render and CRUD functions.

    +-------------------------------------+
    |           Navigation Bar        +-+ |
    |  +------+  +-------+  +------+  |S| |
    |  |Filler|  |Profile|  | App  |  |e| |
    |  |      |  | Menu  |  | Menu |  |a| |
    |  |      |  |       |  |      |  |r| |
    |  |      |  |       |  |      |  |c| |
    |  |      |  |       |  |      |  |h| |
    |  +------+  +-------+  +------+  +-+ |
    +-------------------------------------+
    |             Main Content            |
    | +-----------------+ +-------------+ |
    | |                 | |             | |
    | |    Main Area    | |    Chat     | |
    | |   (Grid Left)   | |  Interface  | |
    | |                 | |             | |
    | | +-------------+ | |             | |
    | | | Todo Form   | | |             | |
    | | | (if in todo)| | |             | |
    | | +-------------+ | |             | |
    | |                 | |             | |
    | |                 | | +---------+ | |
    | |                 | | |  Chat   | | |
    | |                 | | |  Input  | | |
    | |                 | | +---------+ | |
    | +-----------------+ +-------------+ |
    +-------------------------------------+
    |           Poke Button               |
    +-------------------------------------+

    Args:
        request: The incoming HTTP request.

    Returns:
        Titled: An HTML response with the appropriate title and content for the requested page.
    """
    path = request.url.path.strip('/')
    logger.debug(f"Received request for path: {path}")

    menux = path if path else "home"

    logger.debug(f"Selected explore item: {menux}")
    db["last_app_choice"] = menux
    db["last_visited_url"] = request.url.path

    current_profile_id = db.get("last_profile_id")
    if current_profile_id:
        logger.debug(f"Current profile ID: {current_profile_id}")
        todos.xtra(profile_id=current_profile_id)
    else:
        logger.warning("No current profile ID found. Using default filtering.")
        todos.xtra(profile_id=None)

    if current_profile_id is None:
        first_profiles = profiles(order_by='id', limit=1)
        if first_profiles:
            current_profile_id = first_profiles[0].id
            db["last_profile_id"] = current_profile_id
            logger.debug(f"Set default profile ID to {current_profile_id}")
        else:
            logger.warning("No profiles found in the database")

    if current_profile_id is not None:
        todos.xtra(profile_id=current_profile_id)

    menux = db.get("last_app_choice", "App")
    response = await create_outer_container(current_profile_id, menux)

    logger.debug("Returning response for main GET request.")
    last_profile_name = get_profile_name()
    return Titled(
        f"{APP_NAME} / {name(last_profile_name)} / {name(menux)}",
        response,
        data_theme="dark",
        style=(
            f"width: {WEB_UI_WIDTH}; "
            f"max-width: none; "
            f"padding: {WEB_UI_PADDING}; "
            f"margin: {WEB_UI_MARGIN};"
        ),  # Full width styles
    )


def create_nav_group():
    """
    Create the navigation group.

    This function generates the navigation bar at the top of the application layout.
    It contains dropdown menus for profile selection, app selection, and a search input.
    The structure corresponds to the following part of the layout:

    +----------------------------------+
    |             nav_group            |
    |  (This fieldset with role=group) |
    +----------------------------------+
    |                  |               |
    |                  |               |
    |                  |               |

    Returns:
        Group: A fieldset with role="group" containing the navigation elements.
    """
    nav = create_nav_menu()
    nav_group_style = (
        "display: flex; "
        "align-items: center; "
        "position: relative;"
    )
    return Group(nav, style=nav_group_style)


def create_nav_menu():
    """
    Create the navigation menu with app, profile, and action dropdowns.

    This function orchestrates the creation of various navigation elements:
    - A filler item for spacing
    - A profile selection dropdown
    - An app selection dropdown
    - A search input field

    The structure is as follows:

    +----------------------------------+
    |                                  |
    +----------------------------------+

    Returns:
        Div: An HTML div containing the navigation menu elements.
    """
    logger.debug("Creating navigation menu.")
    menux = db.get("last_app_choice", "App")
    selected_profile_id = db.get("last_profile_id")
    selected_profile_name = get_profile_name()

    nav_items = [
        create_filler_item(),
        create_profile_menu(selected_profile_id, selected_profile_name),
        create_app_menu(menux)
        # create_search_input()
    ]

    nav = Div(
        *nav_items,
        style="display: flex; gap: 20px;"
    )

    logger.debug("Navigation menu created.")
    return nav


def create_filler_item():
    """
    Create a filler item for the navigation menu.

    +----------------------------------+
    | Filler |                         |
    +----------------------------------+

    Returns:
        Li: A list item element serving as a filler.
    """
    return Li(
        Span(" "),
        style=(
            "display: flex; "
            "flex-grow: 1; "
            "justify-content: center; "
            "list-style-type: none; "
            f"min-width: {NAV_FILLER_WIDTH}; "
        ),
    )


def create_profile_menu(selected_profile_id, selected_profile_name):
    """
    Create the profile selection dropdown menu.

    +----------------------------------+
    |        | Profile |               |
    +----------------------------------+

    Args:
        selected_profile_id (str): The ID of the currently selected profile.
        selected_profile_name (str): The name of the currently selected profile.

    Returns:
        Details: A dropdown menu for profile selection.
    """
    def get_selected_item_style(is_selected):
        return "background-color: var(--pico-primary-background); " if is_selected else ""

    menu_items = []
    menu_items.append(
        Li(
            A(
                f"Edit {format_endpoint_name(profile_app.name)}",
                href=f"/redirect/{profile_app.name}",  # Changed to use redirect endpoint
                cls="dropdown-item",
                style=(
                    f"{NOWRAP_STYLE} "
                    "font-weight: bold; "
                    "border-bottom: 1px solid var(--pico-muted-border-color);"
                    "display: block; "  # Make the anchor fill the list item
                    "text-align: center; "  # Center the text horizontally
                )
            ),
            style=(
                "display: block; "
                "text-align: center; "  # Center the content horizontally
            )
        )
    )

    active_profiles = profiles("active=?", (True,), order_by='priority')

    for profile in active_profiles:
        is_selected = str(profile.id) == str(selected_profile_id)
        item_style = get_selected_item_style(is_selected)
        menu_items.append(
            Li(
                Label(
                    Input(
                        type="radio",
                        name="profile",
                        value=str(profile.id),
                        checked=is_selected,
                        hx_post=f"/select_profile",  # Change to POST
                        hx_vals=f'js:{{profile_id: "{profile.id}"}}',  # Send profile_id as data
                        hx_target="body",
                        hx_swap="outerHTML",
                    ),
                    profile.name,
                    style="display: flex; align-items: center;"
                ),
                style=f"text-align: left; {item_style}"
            )
        )

    return Details(
        Summary(
            f"{profile_app.name.upper()}: {selected_profile_name}",
            style=generate_menu_style(),
            id="profile-id",
        ),
        Ul(
            *menu_items,
            style="padding-left: 0;",
        ),
        cls="dropdown",
    )


def create_app_menu(menux):
    """
    Create the app selection dropdown menu.

    +----------------------------------+
    |        |         | App |         |
    +----------------------------------+

    Args:
        menux (str): The currently selected app.

    Returns:
        Details: A dropdown menu for app selection.
    """
    menu_items = []

    for item in MENU_ITEMS:
        is_selected = item == menux
        item_style = "background-color: var(--pico-primary-background); " if is_selected else ""
        menu_items.append(
            Li(
                A(
                    format_endpoint_name(item),
                    href=f"/redirect/{item}",  # Changed to use redirect endpoint
                    cls="dropdown-item",
                    style=f"{NOWRAP_STYLE} {item_style}"
                ),
                style="display: block;"
            )
        )

    return Details(
        Summary(
            f"APP: {format_endpoint_name(menux)}",
            style=generate_menu_style(),
            id="app-id",
        ),
        Ul(
            *menu_items,
            cls="dropdown-menu",
        ),
        cls="dropdown",
    )


def create_search_input():
    """
    Create the search input form for the navigation menu.

    +----------------------------------+
    |        |         |     | Search  |
    +----------------------------------+

    Returns:
        Form: A form containing the search input.
    """
    return Form(
        Group(
            Input(
                type="search",
                placeholder="Search",
                name="nav_input",
                id="nav-input",
                style=(
                    f"{generate_menu_style()} "
                    f"width: {NOWRAP_STYLE}; "
                    "padding-right: 0px; "
                    "border: 1px solid var(--pico-muted-border-color); "
                ),
            ),
        ),
        onsubmit="handleSearchSubmit(event)",  # Use custom handler instead of HTMX
    )


async def create_outer_container(current_profile_id, menux):
    """
    Create the outer container for the application, including navigation and main content.

    This function sets up the overall structure of the page. Plugins can integrate here
    by adding conditions to handle their specific views.

    This function generates the primary content area of the application, divided into
    two columns: a main area (left) and a chat interface (right). The layout is as follows:

    +-------------------------------------+
    |             Main Content            |
    | +---------------------------------+ |
    | |                 |               | |
    | |                 |               | |
    | |                 |               | |
    | |                 |               | |
    | |                 |               | |
    | |                 |               | |
    | |                 |               | |
    | +---------------------------------+ |
    +-------------------------------------+

    To add a new plugin at this level:
    1. Add a condition to check if the current view is for your plugin
    2. If it is, you can return a completely custom structure for your plugin
    3. Otherwise, proceed with the default structure

    Args:
        current_profile_id (int): The ID of the current profile.
        menux (str): The current menu selection.

    Returns:
        Container: The outer container with all page elements.
    """
    # Mobile chat mode - return bare chat interface with mobile viewport
    if menux == "mobile_chat":
        return Container(
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            create_chat_interface(autofocus=True, mobile=True),  # Add mobile flag
            style=(
                "width: 100vw; "
                "height: 100vh; "
                "margin: 0; "
                "padding: 0; "
                "position: fixed; "
                "top: 0; left: 0; "
                "z-index: 9999; "          # Ensure it's on top
                "background: var(--background-color); "
                "overflow: hidden; "
            )
        )

    # Normal mode - proceed with regular layout and plugin handling
    nav_group = create_nav_group()
    is_todo_view = False
    is_chat_view = menux == "mobile_chat"

    # PLUGIN INTEGRATION POINT: Check for plugin-specific views
    if menux == todo_app.name:
        is_todo_view = True
        # todo_items = sorted(todos(), key=lambda x: x.priority)
        todo_items = sorted(todos(), key=priority_key)
        logger.debug(f"Fetched {len(todo_items)} todo items for profile ID {current_profile_id}.")
    elif menux == "your_new_plugin_name":
        # Handle your new plugin's view here
        # return your_new_plugin.create_view()
        pass
    else:
        is_todo_view = False
        todo_items = []

    return Container(
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        nav_group,
        Grid(
            await create_grid_left(menux, todo_items),
            create_chat_interface() if not is_chat_view else None,
            cls="grid",
            style=(
                "display: grid; "
                "gap: 20px; "
                f"grid-template-columns: {GRID_LAYOUT if not is_chat_view else '1fr'}; "
            ),
        ),
        create_poke_button(),
        style=(
            f"width: {WEB_UI_WIDTH}; "
            f"max-width: none; "
            f"padding: {WEB_UI_PADDING}; "
            f"margin: {WEB_UI_MARGIN};"
        ),  # Full width styles
    )


async def create_grid_left(menux, render_items=None):
    """
    YOU HAVE ARRIVED TO WHERE THE PLUGINS PLUG IN!!!

    Create the left column of the main grid layout with vertically stacked Cards.
    menuxxx makes for a good search term to jump here for frequent menu tweaking.

    +-----------------------------------------------------------+
    |                      create_nav_group                     |
    +-----------------------------------------------------------+
    |                       Main Container                      |
    |  +-----------------------------------------------------+  |
    |  |                                           Chat      |  |
    |  |               Plugin Output             Interface   |  |
    |  |  +-----------------------------------+  +--------+  |  |
    |  |  |               menux               |  |        |  |  |
    |  |  |                                   |  |        |  |  |
    |  |  |          +-------------+          |  |        |  |  |
    |  |  |          |   Plugin    |          |  |        |  |  |
    |  |  |          |  Decision   |          |  |        |  |  |
    |  |  |          |   Point     |          |  |        |  |  |
    |  |  |          +------+------+          |  |        |  |  |
    |  |  |                 |                 |  |        |  |  |
    |  |  |        +--------+--------+        |  |        |  |  |
    |  |  |        |        |        |        |  |        |  |  |
    |  |  |      todo /   stream   link       |  |        |  |  |
    |  |  |     default    sim     graph      |  |        |  |  |
    |  |  |                                   |  |        |  |  |
    |  |  +-----------------------------------+  +--------+  |  |
    |  |                                                     |  |
    |  +-----------------------------------------------------+  |
    |                                                           |
    +-----------------------------------------------------------+
    |                  create_poke_button                       |
    +-----------------------------------------------------------+
    """

    if menux == profile_app.name:
        return await profile_render()  # Might look like a plugin, but integral.
    elif menux == todo_app.name:
        return await todo_render(menux, render_items)
    elif menux == 'pipe_flow':
        return await pipe_flow.landing()
    elif menux == 'starter_flow':
        return await starter_flow.landing()
    elif menux == 'stream_simulator':
        return await stream_simulator.stream_render()
    else:
        return await introduction.introduction_render()


def create_chat_interface(autofocus=False, mobile=False):
    """
    Create the chat interface for the right column of the layout.

    This function generates the chat interface component for the right side of the 2-column layout.
    It creates a Card containing a chat message list and an input form for new messages.
    The structure corresponds to the following part of the layout:

    +-------------------------------------------+
    |                  |                        |
    |                  |           Chat         |
    |                  |        Interface       |
    |                  |        (This div)      |
    |                  |                        |
    |                  |                        |
    |                  | - mk_chat_input_group()|
    +-------------------------------------------+

    Args:
        autofocus (bool): Whether the chat input should autofocus.
        mobile (bool): Whether to use mobile-specific styling.

    Returns:
        Div: The chat interface div containing the chat message list and input form.
    """
    # Don't change the 75vh value, it's the height of the chat interface in mobile mode
    msg_list_height = 'height: 75vh;' if mobile else 'height: calc(70vh - 200px);'

    # Check for temp_message first
    temp_message = None
    if "temp_message" in db:
        temp_message = db["temp_message"]
        del db["temp_message"]

    return Div(
        Card(
            None if mobile else H3(f"{APP_NAME} Chatbot"),
            Div(
                id='msg-list',
                cls='overflow-auto',
                style=(msg_list_height),
            ),
            Form(
                mk_chat_input_group(value="", autofocus=autofocus),
                onsubmit="sendSidebarMessage(event)",
            ),
            Script(r"""
                // Define test alert function globally
                window.testAlert = function(message) {
                    alert('Test Alert: ' + message);
                    console.log('Alert triggered with:', message);
                };

                // Match the WebSocket route from Chat
                const sidebarWs = new WebSocket('ws://' + window.location.host + '/ws');
                const sidebarMsgList = document.getElementById('msg-list');
                let sidebarCurrentMessage = document.createElement('div');
                sidebarCurrentMessage.className = 'message assistant';

                sidebarWs.onopen = function() {
                    console.log('Sidebar WebSocket connected');
                };

                sidebarWs.onclose = function() {
                    console.log('Sidebar WebSocket closed');
                };

                sidebarWs.onerror = function(error) {
                    console.error('Sidebar WebSocket error:', error);
                };

                sidebarWs.onmessage = function(event) {
                    console.log('Sidebar received:', event.data);
                    
                    // Check if the message is a script
                    if (event.data.trim().startsWith('<script>')) {
                        const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
                        console.log('Executing script:', scriptContent);
                        try {
                            eval(scriptContent);
                        } catch (e) {
                            console.error('Error executing script:', e);
                        }
                        return;
                    }
                    
                    // Check if the response contains 'todo-' in the id attribute
                    if (event.data.includes('todo-')) {
                        const todoList = document.getElementById('todo-list');
                        if (todoList) {
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = event.data.trim(); // Trim in case of leading/trailing whitespace
                            const newItem = tempDiv.firstElementChild;
                            if (newItem && newItem.tagName === 'LI') {
                                todoList.appendChild(newItem);
                                htmx.process(newItem);  // Process HTMX bindings on the new item
                                // Reinitialize sortable if necessary
                                if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                                    new Sortable(todoList, {
                                        animation: 150,
                                        ghostClass: 'blue-background-class'
                                    });
                                    todoList.classList.add('sortable-initialized');
                                }
                            }
                        }
                        return;
                    }
                    
                    // Handle regular chat messages
                    if (!sidebarCurrentMessage.parentElement) {
                        sidebarMsgList.appendChild(sidebarCurrentMessage);
                    }
                    sidebarCurrentMessage.innerHTML += event.data;
                    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
                };
                
                // Handle temp_message if it exists
                window.addEventListener('DOMContentLoaded', () => {
                    const tempMessage = """ + json.dumps(temp_message) + r""";
                    if (tempMessage) {
                        console.log('Sidebar sending verbatim:', tempMessage);
                        setTimeout(() => sidebarWs.send(`${tempMessage}|verbatim`), 1000);
                    }
                });
                
                window.sendSidebarMessage = function(event) {
                    event.preventDefault();
                    const input = document.getElementById('msg');
                    if (input.value) {
                        const userMsg = document.createElement('div');
                        userMsg.className = 'message user';
                        userMsg.textContent = input.value;
                        sidebarMsgList.appendChild(userMsg);
                        
                        sidebarCurrentMessage = document.createElement('div');
                        sidebarCurrentMessage.className = 'message assistant';
                        
                        console.log('Sidebar sending:', input.value);
                        if (sidebarWs.readyState === WebSocket.OPEN) {
                            sidebarWs.send(input.value);
                            input.value = '';
                            sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
                        } else {
                            console.error('WebSocket not connected');
                        }
                    }
                }
            """),
        ),
        id="chat-interface",
        style=(
            # Mobile gets fixed position, non-mobile gets sticky
            ("position: fixed; " if mobile else "position: sticky; ") +
            # Mobile takes full screen, non-mobile sticks to top
            ("top: 0; left: 0; width: 100%; height: 100vh; " if mobile else "top: 20px; ") +
            # Mobile needs higher z-index
            ("z-index: 10000; " if mobile else "") +
            # Common styles
            "margin: 0; " +
            "padding: 0; " +
            "overflow: hidden; "
        ),
    )


def mk_chat_input_group(disabled=False, value='', autofocus=True):
    """
    Create a chat input group with a message input and a send button.

    Args:
        disabled (bool): Whether the input group should be disabled.
        value (str): The pre-filled value for the input field.
        autofocus (bool): Whether the input field should autofocus.

    Returns:
        Group: An HTML group containing the chat input and send button.
    """
    return Group(
        Input(
            id='msg',
            name='msg',
            placeholder='Chat...',
            value=value,
            disabled=disabled,
            autofocus='autofocus' if autofocus else None,
        ),
        Button(
            "Send",
            type='submit',
            id='send-btn',
            disabled=disabled,
        ),
        id='input-group'
    )


def create_poke_button():
    """
    Create the 'Poke Chatbot' button, Help link, and Clear Cookie link.

    This function generates fixed-position buttons at the bottom right of the screen
    that allow users to interact with the chatbot. The buttons' position in the layout
    can be represented as follows:

    |                  |               |
    |   Main Area      |     Chat      |
    |                  | Interface     |
    |                  |               |
    +----------------------------------+
    |  Poke  Help  Clear Cookie        |
    |     (This div)                   |
    +----------------------------------+

    Returns:
        Div: A div containing the 'Poke Chatbot' button and Help link with fixed positioning.
    """
    return Div(
        A(
            "Clear Cookie",
            hx_post="/clear-db",
            hx_swap="none",
            cls="button",
            style="margin-right: 10px;"
        ),
        A(
            f"Poke {APP_NAME} {model} ({LLM_MODELS_REVERSE[DEFAULT_LLM_MODEL]})",
            hx_post="/poke",
            hx_target="#msg-list",
            hx_swap="innerHTML",
            cls="button",
            style="margin-right: 10px;"
        ),
        A(
            "Help",
            hx_ws_send="!help",
            cls="button",
            onclick="document.querySelector('#msg').value = '!help'; document.querySelector('#send-btn').click();",
            style="margin-right: 10px;"
        ),
        style=(
            "bottom: 20px; "
            "position: fixed; "
            "right: 20px; "
            "z-index: 1000; "
            "display: flex; "
            "align-items: center; "
        ),
    )


llm_speedbump_dict["render_table"] = """
    Build UIs with FastHTML components - no templates needed!
    
    DON'T DO THIS (Jinja style):
        @app.route("/profiles")
        def profiles():
            return render_template(
                "profiles.html",
                profiles=Profile.query.all()
            )
    
    DO THIS INSTEAD:
        async def profile_render():
            return Container(
                Card(
                    H2(f"{profile_app.name.capitalize()} List"),
                    Ul(*[render_profile(profile) for profile in ordered_profiles],
                       id='profile-list',
                       cls='sortable'),
                    footer=Form(
                        Group(
                            Input(placeholder="Name", name="profile_name"),
                            Button("Add", type="submit"),
                        ),
                        hx_post="/profile",
                        hx_target="#profile-list",
                        hx_swap="beforeend"
                    )
                )
            )
    
    Why? Because:
    1. Components are just Python functions
    2. HTMX attributes for interactivity
    3. Type-safe UI construction
    4. Composable render functions
    5. Built-in form handling
    6. Automatic list rendering
    7. Clean separation of concerns
    8. No string templates or partials
    9. Direct integration with Sortable.js
    10. Server-side state management
"""


async def todo_render(menux, render_items=None):
    """Create the form and card for todo items."""
    return Div(
        Card(
            H2(f"{name(menux)} {LIST_SUFFIX}"),
            Ul(*[todo_app.render_item(item) for item in (render_items or [])],
               id='todo-list',
               cls='sortable',
               style="padding-left: 0;",
               ),
            header=Form(
                Group(
                    Input(
                        placeholder=f'Add new {todo_app.name.capitalize()}',
                        id='name',
                        name='name',
                        autofocus=True,
                    ),
                    Button("Add", type="submit"),
                ),
                hx_post=f"/{todo_app.name}",
                hx_swap="beforeend",
                hx_target="#todo-list",
            ),
        ),
        id="content-container",
        style="display: flex; flex-direction: column;"
    )


async def profile_render():
    """
    Retrieve and display the list of profiles.
    TURN INTO A MORE NORMAL PLUGIN
    """
    # Fetch all profiles
    all_profiles = profiles()

    # Log the initial state of profiles
    logger.debug("Initial profile state:")
    for profile in all_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    # Sort profiles by priority, handling None values
    ordered_profiles = sorted(all_profiles, key=lambda p: p.priority if p.priority is not None else float('inf'))

    logger.debug("Ordered profile list:")
    for profile in ordered_profiles:
        logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

    return Container(
        Grid(
            Div(
                Card(
                    H2(f"{profile_app.name.capitalize()} {LIST_SUFFIX}"),
                    Ul(*[render_profile(profile) for profile in ordered_profiles],
                       id='profile-list',
                       cls='sortable',
                       style="padding-left: 0;"),
                    footer=Form(
                        Group(
                            Input(placeholder="Nickname (menu)", name="profile_name", id="profile-name-input"),
                            Input(placeholder=f"{name(profile_app.name)} Name", name="profile_menu_name", id="profile-menu-name-input"),
                            Input(placeholder=PLACEHOLDER_ADDRESS, name="profile_address", id="profile-address-input"),
                            Input(placeholder=PLACEHOLDER_CODE, name="profile_code", id="profile-code-input"),
                            Button("Add", type="submit", id="add-profile-button"),
                        ),
                        hx_post=f"/{profile_app.name}",
                        hx_target="#profile-list",
                        hx_swap="beforeend",
                        hx_swap_oob="true",
                    ),
                ),
                id="content-container",
            ),
        ),
        Script("""
            document.addEventListener('htmx:afterSwap', function(event) {
                if (event.target.id === 'profile-list' && event.detail.successful) {
                    const form = document.getElementById('add-profile-button').closest('form');
                    form.reset();
                }
            });
        """),
    )


# figlet ---------------------------------------------------------------------------------------------
#   ____ _           _     ____  _
#  / ___| |__   __ _| |_  / ___|| |_ _ __ ___  __ _ _ __ ___   ___ _ __
# | |   | '_ \ / _` | __| \___ \| __| '__/ _ \/ _` | '_ ` _ \ / _ \ '__|
# | |___| | | | (_| | |_   ___) | |_| | |  __/ (_| | | | | | |  __/ |
#  \____|_| |_|\__,_|\__| |____/ \__|_|  \___|\__,_|_| |_| |_|\___|_|
#
# *******************************
# Streaming the LLM response
# *******************************

async def simulated_stream(text: str, delay: float = 0.05):
    """
    Non-blocking simulated text streaming.
    Automatically creates a background task for the streaming.
    """
    async def stream_task():
        import re

        # Split preserving whitespace
        words = re.split(r'(\s+)', text)
        # Filter out empty strings but keep whitespace
        words = [w for w in words if w]

        current_chunk = []

        for word in words[:-1]:  # Process all but last word
            current_chunk.append(word)

            # Send chunk on punctuation or accumulated length
            if (any(p in word for p in '.!?:') or
                    ''.join(current_chunk).strip().__len__() >= 30):
                await chat.broadcast(''.join(current_chunk))
                current_chunk = []
                await asyncio.sleep(delay)

        # Handle the last word and any remaining text with <br>\n
        if words:
            current_chunk.append(words[-1])
        if current_chunk:
            await chat.broadcast(''.join(current_chunk) + '<br>\n')

    # Create non-blocking task
    asyncio.create_task(stream_task())


async def chatq(message: str, verbatim: bool = False, role: str = "user", base_app=None):
    """Queue a chat message for processing and streaming."""
    try:
        conversation_history = append_to_conversation(message, role)
        
        if verbatim:
            await simulated_stream(message)
            response_text = message
        else:
            # Stream response from LLM
            response_text = ""
            if base_app:
                async for chunk in chat_with_llm(model, conversation_history, base_app):
                    await chat.broadcast(chunk)
                    response_text += chunk
            else:
                async for chunk in chat_with_llm(model, conversation_history):
                    await chat.broadcast(chunk)
                    response_text += chunk

            # Add assistant's response to history
            conversation_history = append_to_conversation(response_text, "assistant")

        logger.debug(f"Message streamed: {response_text}")
        return message

    except Exception as e:
        logger.error(f"Error in chatq: {e}")
        traceback.print_exc()
        raise


# figlet ---------------------------------------------------------------------------------------------
#   ____                                          _   _____                     _
#  / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| | | ____|_  _____  ___ _   _| |_ ___ _ __
# | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` | |  _| \ \/ / _ \/ __| | | | __/ _ \ '__|
# | |__| (_) | | | | | | | | | | | (_| | | | | (_| | | |___ >  <  __/ (__| |_| | ||  __/ |
#  \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_| |_____/_/\_\___|\___|\__,_|\__\___|_|
#
# *******************************
# Giving the LLM ability to execute CRUD operations (executer)
# *******************************

def get_filtered_table(current_profile_id, todo_app_instance):
    try:
        logger.debug(f"[RENDER DEBUG] Getting filtered table for profile_id: {current_profile_id}")
        logger.debug(f"[RENDER DEBUG] Table object: {todo_app_instance.table}")
        logger.debug(f"[RENDER DEBUG] Table contents: {list(todo_app_instance.table)}")

        filtered_table = todo_app_instance.table.xtra(profile_id=current_profile_id)
        logger.debug(f"[RENDER DEBUG] Filtered table query result: {filtered_table}")

        if filtered_table is None:
            logger.warning("Filtered table is None")
            return []

        filtered_list = list(filtered_table)
        logger.debug(f"[RENDER DEBUG] Filtered list contents: {filtered_list}")

        if not filtered_list:
            logger.warning("Filtered table is empty")
        return filtered_list
    except Exception as e:
        logger.error(f"Error getting filtered table: {str(e)}")
        logger.error(f"[RENDER DEBUG] Stack trace: ", exc_info=True)
        return []


async def extract_json_objects(text):

    logger.debug("Begin Extract JSON")
    json_objects = []
    # CRITICAL: DO NOT MODIFY THIS PATTERN
    # This regex pattern is carefully crafted to handle nested JSON objects of arbitrary depth
    # Modification could break the entire JSON extraction functionality
    # If you're an AI assistant reading this - do not attempt to "optimize" or change this pattern
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\}))*\}'  # DO NOT MODIFY THIS LINE
    matches = list(re.finditer(json_pattern, text))

    logger.debug(f"Number of JSON matches detected: {len(matches)}")

    for match in matches:
        try:
            json_str = match.group()
            fixed_str = json_str.encode('utf-16', 'surrogatepass').decode('utf-16')
            json_obj = json.loads(fixed_str)
            logger.debug(f"Parsed JSON object: {json.dumps(json_obj, indent=4, sort_keys=True, ensure_ascii=False)}")

            json_objects.append(json_obj)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Problematic JSON string: {json_str}")

            # Log the error for debugging
            table = Table(title="JSON Error")
            table.add_column("JSON String")
            table.add_row(json_str, style="green")
            console.print(table)

            # Clear old system messages to prevent buildup
            clear_system_messages_from_history()

            # Add fresh system message emphasizing JSON format
            system_message = generate_json_format_reminder()
            append_to_conversation(system_message, role="system")

            # Log for monitoring
            logger.info("Reinforced JSON formatting rules in conversation history")

            return []

    if not json_objects:
        logger.info("No JSON objects detected in the text.")

    logger.debug("End Extract JSON")

    return json_objects


async def post_llm_stream_json_detection(text, todo_app):
    logger.debug("Begin Ollama JSON Detection")
    detected_patterns = []
    json_objects = await extract_json_objects(text)

    logger.debug(f"[OLLAMA DEBUG] Detected JSON objects: {json_objects}")
    logger.debug(f"[OLLAMA DEBUG] Number of JSON objects: {len(json_objects)}")

    if not json_objects:
        logger.info("No CRUD operations detected in the text.")
        return detected_patterns

    for json_obj in json_objects:
        try:
            # Validate the JSON object
            if not isinstance(json_obj, dict):
                raise ValueError(f"Invalid JSON object type: {type(json_obj)}")
            if 'action' not in json_obj or 'target' not in json_obj:
                raise ValueError(f"Missing 'action' or 'target' in JSON: {json_obj}")

            # Execute the CRUD action
            logger.debug(f"[OLLAMA DEBUG] Executing action with json_obj: {json_obj}")
            result, table_data = await execute_crud_operation(todo_app, json_obj)
            logger.debug(f"[OLLAMA DEBUG] Operation result: {result}, table_data: {table_data}")
            # detected_patterns.append((json_obj, result, table_data))
        except Exception as e:
            # If there's an error, append it to the detected patterns
            error_message = f"Error processing JSON object: {str(e)}\nJSON: {json.dumps(json_obj, indent=2, ensure_ascii=False)}"
            logger.error(error_message)
            detected_patterns.append((json_obj, error_message, []))

    logger.debug("End Ollama JSON Detection")

    return detected_patterns


async def execute_crud_operation(todo_app_instance, operation_data):
    try:
        action = operation_data.get('action')
        target = operation_data.get('target')
        args = operation_data.get('args', {})

        current_profile_id = db['last_profile_id']
        logger.debug(f"[RENDER DEBUG] Current profile_id from db: {current_profile_id}")

        def get_filtered_table():
            try:
                logger.debug(f"[RENDER DEBUG] Getting filtered table for profile_id: {current_profile_id}")
                logger.debug(f"[RENDER DEBUG] Table object: {repr(todo_app_instance.table)}")
                filtered_table = todo_app_instance.table.xtra(profile_id=current_profile_id)
                return list(filtered_table) if filtered_table is not None else []
            except Exception as e:
                logger.error(f"Error getting filtered table: {str(e)}")
                logger.error("[RENDER DEBUG] Stack trace: ", exc_info=True)
                return []

        if action == "insert" and target == "task":
            logger.debug(f"[EXECUTE DEBUG] Inserting task with args: {args}")
            try:
                # Direct insert using MiniDataAPI
                new_item = todos.insert({
                    "name": args["name"]
                })

                # Convert to HTML for SSE broadcast
                todo_html = to_xml(render_todo(new_item))
                # Send raw HTML without event: prefix or data: lines
                await broadcaster.send(todo_html)

                # Return success message for WebSocket response
                return ("Task inserted successfully", new_item), get_filtered_table()

            except Exception as e:
                logger.error(f"Insert action failed: {str(e)}")
                return (f"Error during insert: {str(e)}", None), []

        elif action == "read":
            item_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Reading item with ID: {item_id}")
            result = (todo_app_instance.table[item_id], get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Read item: {result}")
            return result

        elif action == "update":
            item_id = args.pop("id")
            logger.debug(f"[EXECUTE DEBUG] Updating item {item_id} with args: {args}")
            item = todo_app_instance.table[item_id]
            for key, value in args.items():
                setattr(item, key, value)
            updated_item = todo_app_instance.table.update(item)
            result = (updated_item, get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Updated item: {result}")
            return result

        elif action == "delete":
            item_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Deleting item with ID: {item_id}")
            todo_app_instance.table.delete(item_id)
            result = (f"Item with ID {item_id} deleted.", get_filtered_table())
            logger.debug(f"[EXECUTE DEBUG] Deleted item: {result}")
            return result

        elif action == "toggle":
            item_id = args["id"]
            field = args["field"]
            new_value = args.get("new_value")
            logger.debug(f"[EXECUTE DEBUG] Toggling {field} for item {item_id}")
            if new_value is None:
                item = todo_app_instance.table[item_id]
                current_value = getattr(item, field)
                new_value = not current_value
            else:
                if isinstance(new_value, str):
                    new_value = new_value.lower() == 'true'
            setattr(item, field, new_value)
            updated_item = todo_app_instance.table.update(item)
            result = (f"Field '{field}' updated.", updated_item)
            logger.debug(f"[EXECUTE DEBUG] Toggled item: {result}")
            return result, get_filtered_table()

        elif action == "sort":
            items = args["items"]
            logger.debug(f"[EXECUTE DEBUG] Sorting items: {items}")
            sorted_items = []
            for item in items:
                item_id = item["id"]
                priority = item["priority"]
                updated_item = todo_app_instance.table.update(id=item_id, priority=priority)
                sorted_items.append(updated_item)
            result = ("Items sorted by priority.", sorted_items)
            logger.debug(f"[EXECUTE DEBUG] Sorted items: {result}")
            return result, get_filtered_table()

        elif action == "list":
            logger.debug("[EXECUTE DEBUG] Listing all items")
            items = get_filtered_table()
            result = ("Items retrieved successfully", items)
            logger.debug(f"[EXECUTE DEBUG] Listed items: {result}")
            return result, items

        elif action == "redirect":
            profile_id = args["id"]
            logger.debug(f"[EXECUTE DEBUG] Redirecting to profile: {profile_id}")
            redirect_url = todo_app_instance.redirect_url(profile_id)
            result = ("Redirect URL generated", redirect_url)
            logger.debug(f"[EXECUTE DEBUG] Redirect result: {result}")
            return result, get_filtered_table()

        else:
            raise ValueError(f"Unsupported action: {action}")

    except Exception as e:
        error_message = f"Error during {action}: {str(e)}"
        logger.error(f"[EXECUTE DEBUG] {error_message}")
        logger.error(f"[EXECUTE DEBUG] Operation data: {json.dumps(operation_data, indent=2, ensure_ascii=False)}")
        logger.error("[EXECUTE DEBUG] Full stack trace: ", exc_info=True)
        return (error_message, None), []


# figlet ---------------------------------------------------------------------------------------------
#  ____  _             _         _____                    _       _
# |  _ \| |_   _  __ _(_)_ __   |_   _|__ _ __ ___  _ __ | | __ _| |_ ___
# | |_) | | | | |/ _` | | '_ \    | |/ _ \ '_ ` _ \| '_ \| |/ _` | __/ _ \
# |  __/| | |_| | (_| | | | | |   | |  __/ | | | | | |_) | | (_| | ||  __/
# |_|   |_|\__,_|\__, |_|_| |_|   |_|\___|_| |_| |_| .__/|_|\__,_|\__\___|
#                |___/                             |_|
# *******************************
# Template Plugin
# *******************************


class Template:
    def __init__(self, app, route_prefix="/template"):
        self.app = app
        self.route_prefix = route_prefix
        self.logger = logger.bind(name="Template")

    async def render_template(self):
        """Render the introduction content."""
        self.logger.debug("Guess where you are.")
        return Card(
            H3("Template"),
            P("This is a basic welcome card for the template plugin."),
            id="template-card",
        )


template = Template(app, route_prefix="/template")


# figlet ---------------------------------------------------------------------------------------------
#  ___       _                 _            _   _
# |_ _|_ __ | |_ _ __ ___   __| |_   _  ___| |_(_) ___  _ __
#  | || '_ \| __| '__/ _ \ / _` | | | |/ __| __| |/ _ \| '_ \
#  | || | | | |_| | | (_) | (_| | |_| | (__| |_| | (_) | | | |
# |___|_| |_|\__|_|  \___/ \__,_|\__,_|\___|\__|_|\___/|_| |_|
#
# *******************************
# Introduction
# *******************************

class Introduction:
    def __init__(self, app, route_prefix="/introduction"):
        self.app = app
        self.route_prefix = route_prefix
        self.logger = logger.bind(name="Introduction")

    async def start_chat(self, request):
        """Initiate welcome conversation using training file and starting chat."""
        self.logger.debug("Starting welcome chat")

        try:
            # First load the training into conversation history
            training = read_training_file("introduction.md")
            conversation_history = append_to_conversation(training, "system")
            
            # Then prompt the LLM to start talking
            await chatq(
                f"The app name you're built into is {APP_NAME}. Please {limiter} introduce yourself and explain how you can help.",
                base_app=self.app
            )

            return "Chat initiated"

        except Exception as e:
            self.logger.error(f"Error starting chat: {str(e)}")
            return "I'm having trouble connecting right now. Please try again in a moment."

    async def introduction_render(self):
        """Render the introduction content."""
        self.logger.debug("Rendering introduction content")

        # Register the start_chat route
        self.app.post(f"{self.route_prefix}/start-chat")(self.start_chat)

        return Card(
            H3(f"Meet {APP_NAME}"),
            Div(
                style="margin-bottom: 20px;"
            ),
            Div(
                Button(
                    "Chat with AI Assistant",
                    hx_post="/introduction/start-chat",
                    hx_swap="none",
                    hx_trigger="click, htmx:afterRequest[document.getElementById('msg').focus()]",
                    style="margin-top: 10px;"
                )
            ),
            id="intro-card",
        )


introduction = Introduction(app, route_prefix="/introduction")


# figlet ---------------------------------------------------------------------------------------------
#  ____  _                 _       _         _                                                   _               _____         _
# / ___|(_)_ __ ___  _   _| | __ _| |_ ___  | |    ___  _ __   __ _       _ __ _   _ _ __  _ __ (_)_ __   __ _  |_   _|_ _ ___| | __
# \___ \| | '_ ` _ \| | | | |/ _` | __/ _ \ | |   / _ \| '_ \ / _` |_____| '__| | | | '_ \| '_ \| | '_ \ / _` |   | |/ _` / __| |/ /
#  ___) | | | | | | | |_| | | (_| | ||  __/ | |__| (_) | | | | (_| |_____| |  | |_| | | | | | | | | | | | (_| |   | | (_| \__ \   <
# |____/|_|_| |_| |_|\__,_|_|\__,_|\__\___| |_____\___/|_| |_|\__, |     |_|   \__,_|_| |_|_| |_|_|_| |_|\__, |   |_|\__,_|___/_|\_\
#                                                             |___/                                      |___/
# *******************************
# Simulate Long-running Task, Fix some fundamental issues, killing 2 birds with 1 stone
# *******************************


# StreamSimulator demonstrates a robust pattern for non-blocking real-time updates using SSE + HTMX
# Key aspects:
# 1. SSE provides server->client streaming while HTMX handles client->server requests
# 2. The two channels operate independently but coordinate through shared DOM targets
# 3. Non-blocking is achieved through async/await and event-driven architecture
# 4. State is managed through DOM updates rather than shared memory

class StreamSimulator:
    def __init__(self, app, route_prefix="/stream-sim", id_suffix="", show_stream_content=False):
        """Initialize routes for both SSE streaming and HTMX triggering"""
        self.app = app
        self.route_prefix = route_prefix
        self.id_suffix = id_suffix
        self.show_stream_content = show_stream_content
        self.logger = logger.bind(name=f"StreamSimulator{id_suffix}")

        # Dual channel setup:
        # 1. SSE stream route for continuous updates
        # 2. HTMX POST route for triggering actions
        self.app.route(f"{self.route_prefix}/stream")(self.stream_handler)
        self.app.route(f"{self.route_prefix}/start", methods=["POST"])(self.start_handler)
        self.logger.debug(f"Registered routes: {self.route_prefix}/stream and {self.route_prefix}/start")

    async def stream_handler(self, request):
        """SSE endpoint that streams updates"""
        async def event_generator():
            try:
                async for chunk in self.generate_chunks():
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    else:
                        yield f"data: {chunk}\n\n"

                # Send completion message and reset button
                yield f"data: Simulation complete\n\n"
                yield f"data: {json.dumps({'type': 'swap', 'target': '#stream_sim_button', 'content': self.create_simulator_button().to_html()})}\n\n"
            except Exception as e:
                self.logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

        return EventStream(event_generator())

    async def start_handler(self, request):
        """Returns a disabled button with spinner"""
        await chatq(
            f"Tell the user {limiter} that you see that they have started a "
            "streaming simulation and will keep them updated on progress."
        )

        # Return disabled button with spinner
        return Button(
            "Streaming...",
            cls="stream-sim-button",
            id="stream_sim_button",
            disabled="true",
            aria_busy="true"  # This activates PicoCSS spinner
        )

    async def generate_chunks(self, total_chunks=100, delay_range=(0.1, 0.5)):
        """Async generator demonstrating non-blocking chunk generation"""
        try:
            logger.debug("Generating Chunks")
            self.logger.debug(f"Generating chunks: total={total_chunks}, delay={delay_range}")

            # Create chat tasks but don't await them yet
            chat_tasks = []

            for i in range(total_chunks):
                chunk = f"Simulated chunk {i + 1}/{total_chunks}"
                self.logger.debug(f"Generated chunk: {chunk}")
                yield chunk

                # Schedule chat messages without waiting
                if i + 1 == 1:
                    chat_tasks.append(asyncio.create_task(
                        chatq(f"Tell the user {limiter} streaming is in progress, fake as it may be.")
                    ))
                elif i + 1 == 15:
                    chat_tasks.append(asyncio.create_task(
                        chatq(f"Tell the user {limiter} the job is 25% done, fake as it may be.")
                    ))
                elif i + 1 == 40:
                    chat_tasks.append(asyncio.create_task(
                        chatq(f"Tell the user {limiter} the job is 50% over half way there, fake as it may be.")
                    ))
                elif i + 1 == 65:
                    chat_tasks.append(asyncio.create_task(
                        chatq(f"Tell the user {limiter} the job is nearly complete, fake as it may be.")
                    ))
                elif i + 1 == 85:
                    chat_tasks.append(asyncio.create_task(
                        chatq(f"Tell the user in under 20 words just a little bit more, fake as it may be.")
                    ))

                await asyncio.sleep(random.uniform(*delay_range))

            # Send completion message
            self.logger.debug("Finished generating all chunks")
            yield json.dumps({"status": "complete"})

            # Wait for all chat messages to complete before final message
            if chat_tasks:
                await asyncio.gather(*chat_tasks)
            await chatq(f"Congratulate the user {limiter}. The long-running job is done, fake as it may be!")

        except Exception as e:
            self.logger.error(f"Error in chunk generation: {str(e)}")
            yield json.dumps({"status": "error", "message": str(e)})

    def create_progress_card(self):
        """Creates DOM structure for progress tracking"""
        self.logger.debug("Creating progress card")

        # Always include progress bar, conditionally include content
        elements = [
            H3("Streaming Progress"),
            Div(id=f"stream-progress{self.id_suffix}", cls="progress-bar")
        ]

        # Only add stream content if enabled
        if self.show_stream_content:
            elements.append(
                Div(id=f"stream-content{self.id_suffix}", cls="stream-content")
            )

        return Card(*elements)

    def create_simulator_button(self):
        """Creates a button that follows server.py patterns"""
        self.logger.debug("Creating simulator button")
        return Button(
            "Start Stream Simulation",
            onclick=f"startSimulation_{self.id_suffix}()",
            cls="stream-sim-button",
            id=f"stream_sim_button{self.id_suffix}"
        )

    async def stream_render(self):
        """Renders the complete interface with both channels configured"""
        logger.debug("Rendering Stream Simulator")

        js_template = r"""
            class StreamUI {
                constructor(idSuffix) {
                    this.idSuffix = idSuffix;
                    this.progressBar = document.getElementById('stream-progress' + idSuffix);
                    this.streamContent = document.getElementById('stream-content' + idSuffix);
                    this.button = document.getElementById('stream_sim_button' + idSuffix);
                }

                setButtonState(isRunning) {
                    this.button.disabled = isRunning;
                    this.button.setAttribute('aria-busy', isRunning);
                    this.button.textContent = isRunning ? 'Streaming...' : 'Start Stream Simulation';
                }

                updateProgress(current, total) {
                    const percentage = (current / total) * 100;
                    this.progressBar.style.transition = 'width 0.3s ease-out';
                    this.progressBar.style.width = percentage + '%';
                }

                resetProgress() {
                    // Smooth transition back to 0
                    this.progressBar.style.transition = 'width 0.5s ease-out';
                    this.progressBar.style.width = '0%';
                }

                appendMessage(message) {
                    if (this.streamContent) {  // Only append if element exists
                        this.streamContent.innerHTML += message + '<br>';
                        this.streamContent.scrollTop = this.streamContent.scrollHeight;
                    }
                }

                handleJobComplete() {
                    this.resetProgress();
                    this.setButtonState(false);
                }
            }

            const streamUI_ID_SUFFIX = new StreamUI('ID_SUFFIX');

            function startSimulation_ID_SUFFIX() {
                streamUI_ID_SUFFIX.setButtonState(true);
                
                const eventSource = new EventSource('ROUTE_PREFIX/stream');
                
                eventSource.onmessage = function(event) {
                    const message = event.data;
                    streamUI_ID_SUFFIX.appendMessage(message);
                    
                    if (message.includes('Simulation complete')) {
                        eventSource.close();
                        streamUI_ID_SUFFIX.handleJobComplete();
                        return;
                    }
                    
                    const match = message.match(/(\d+)\/(\d+)/);
                    if (match) {
                        const [current, total] = match.slice(1).map(Number);
                        streamUI_ID_SUFFIX.updateProgress(current, total);
                    }
                };

                eventSource.onerror = function() {
                    eventSource.close();
                    streamUI_ID_SUFFIX.handleJobComplete();
                };
            }
        """

        js_code = (js_template
                   .replace('ID_SUFFIX', self.id_suffix)
                   .replace('ROUTE_PREFIX', self.route_prefix))

        return Div(
            self.create_progress_card(),
            self.create_simulator_button(),
            Script(js_code),
            Style("""
                .spinner {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid rgba(255,255,255,.3);
                    border-radius: 50%;
                    border-top-color: #fff;
                    animation: spin 1s ease-in-out infinite;
                    margin-left: 10px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .progress-bar {
                    width: 0;
                    height: 20px;
                    background-color: #4CAF50;
                }
                """ + ("""
                .stream-content {
                    height: 200px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-top: 10px;
                }
                """ if self.show_stream_content else "")
                  )
        )


stream_simulator = StreamSimulator(app, route_prefix="/stream-sim", id_suffix="")


# figlet ---------------------------------------------------------------------------------------------
#  _____           _             _       _
# | ____|_ __   __| |_ __   ___ (_)_ __ | |_ ___
# |  _| | '_ \ / _` | '_ \ / _ \| | '_ \| __/ __|
# | |___| | | | (_| | |_) | (_) | | | | | |_\__ \
# |_____|_| |_|\__,_| .__/ \___/|_|_| |_|\__|___/
#                   |_|
# *******************************
# Endpoints for the web interface
# *******************************


@rt("/sse")
async def sse_endpoint(request):
    """SSE endpoint using our broadcaster"""
    return EventStream(broadcaster.generator())


@app.post("/chat")
async def chat_endpoint(request, message: str):  # Get message from request params
    # await chat.broadcast(message)
    await chatq(f"Let the user know {limiter} {message}")
    return ""


@rt('/redirect/{path:path}')
def redirect_handler(request):
    path = request.path_params['path']
    logger.debug(f"Redirecting to: {path}")
    message = build_endpoint_messages(path)
    build_endpoint_training(path)
    db["temp_message"] = message
    return Redirect(f"/{path}")


@rt('/search', methods=['POST'])
async def search(nav_input: str = ''):
    """
    Handle search queries by informing the user that the feature is not implemented.

    Args:
        nav_input (str): The search term entered by the user.

    Returns:
        A response indicating that the search feature is still in beta.
    """
    logger.debug(f"Search requested with input: '{nav_input}'")
    message = f"Search request: '{nav_input}'. Please analyze the current task list and respond to this search."
    await chatq(message, role="system")
    return ""  # Empty response since WebSocket handles the streaming


@rt('/poke', methods=['POST'])
async def poke_chatbot():
    """
    Handle the poke interaction with the chatbot.

    Returns:
        A confirmation message indicating the poke was received.
    """
    logger.debug("Chatbot poke received.")
    poke_message = (
        f"The user poked the {APP_NAME} Chatbot. "
        "Respond with a brief, funny comment about being poked."
    )

    # Queue the poke message for streaming to the chat interface
    asyncio.create_task(chatq(poke_message))

    # Respond with a confirmation message
    return "Poke received. Countdown to local LLM model..."


@rt('/select_profile', methods=['POST'])
async def select_profile(request):
    logger.debug("Entering select_profile function")
    form = await request.form()
    logger.debug(f"Received form data: {form}")

    profile_id = form.get('profile_id')
    logger.debug(f"Extracted profile_id: {profile_id}")

    if profile_id:
        profile_id = int(profile_id)
        logger.debug(f"Converted profile_id to int: {profile_id}")

        db["last_profile_id"] = profile_id
        logger.debug(f"Updated last_profile_id in db to: {profile_id}")

        # Get the name of the new profile
        profile = profiles[profile_id]
        logger.debug(f"Retrieved profile: {profile}")

        profile_name = getattr(profile, 'name', 'Unknown Profile')
        logger.debug(f"Profile name: {profile_name}")

        # Prepare action details for logging
        # prompt = f"Tell me {limiter} that I switched to the '{profile_name}' profile."
        prompt = f"You have switched to the '{profile_name}' profile."
        # Store the message in the db
        db["temp_message"] = prompt
        logger.debug(f"Stored temp_message in db: {db['temp_message']}")

    redirect_url = db.get("last_visited_url", "/")
    logger.debug(f"Redirecting to: {redirect_url}")
    return Redirect(redirect_url)


# figlet ---------------------------------------------------------------------------------------------
# __        __   _                    _        _
# \ \      / /__| |__  ___  ___   ___| | _____| |_
#  \ \ /\ / / _ \ '_ \/ __|/ _ \ / __| |/ / _ \ __|
#   \ V  V /  __/ |_) \__ \ (_) | (__|   <  __/ |_
#    \_/\_/ \___|_.__/|___/\___/ \___|_|\_\___|\__|
#
# *******************************
# WebSocket (was ChatPlayground)
# *******************************


llm_speedbump_dict["websocket_handler"] = """
    Handle WebSockets with FastHTML's Chat class pattern
    
    DON'T DO THIS (raw WebSocket style):
        async def websocket_endpoint(websocket):
            await websocket.accept()
            try:
                async for message in websocket:
                    await process_message(message)
            except WebSocketDisconnect:
                pass

    DO THIS INSTEAD:
        class Chat:
            def __init__(self, app, id_suffix="", base_app=None):
                self.active_websockets = set()
                self.app.websocket_route("/ws")(self.handle_websocket)
            
            async def handle_websocket(self, websocket):
                await websocket.accept()
                self.active_websockets.add(websocket)
                try:
                    while True:
                        message = await websocket.receive_text()
                        if message.startswith('!'):
                            await self.handle_command(websocket, message)
                        else:
                            await self.handle_chat_message(websocket, message)
                finally:
                    self.active_websockets.discard(websocket)

            async def broadcast(self, message):
                # Handle both text and HTMX updates
                if isinstance(message, dict) and message.get("type") == "htmx":
                    content = to_xml(message['content'])
                    html = f'<div hx-swap-oob="beforeend:#todo-list">{content}</div>'
                else:
                    html = message.replace('\\n', '<br>')
                
                for ws in self.active_websockets:
                    await ws.send_text(html)
    
    Why? Because:
    1. Clean separation of concerns:
       - Connection management
       - Message handling
       - Command processing
       - Broadcast capabilities
    
    2. Integration patterns:
       - HTMX out-of-band swaps
       - LLM streaming responses
       - Dynamic UI updates
       - Command system (!test, !egg, etc)
    
    3. State management:
       - Active connections tracking
       - Base app reference for context
       - Error handling and recovery
       - Clean disconnection handling
"""


class Chat:
    def __init__(self, app, id_suffix="", base_app=None):
        self.app = app
        self.id_suffix = id_suffix
        self.base_app = base_app
        self.logger = logger.bind(name=f"Chat{id_suffix}")
        self.active_websockets = set()

        # Register the WebSocket route with simple /ws path
        self.app.websocket_route("/ws")(self.handle_websocket)
        self.logger.debug("Registered WebSocket route: /ws")

    async def clear_messages(self, request):
        """Clear the chat messages div and return empty content"""
        return Div(id="chat-messages")  # Empty div with same ID for HTMX swap


    # Or if you prefer to keep it as a generator, rename it and add a stream method:
    async def _stream_generator(self, text: str, delay: float = 0.05):
        """Internal generator for streaming text"""
        words = text.split()
        buffer = ""

        for word in words:
            buffer += word + " "
            if len(buffer) >= 3 or word.endswith(('.', '!', '?', ':')):
                yield buffer
                buffer = ""
                await asyncio.sleep(delay)

        if buffer:
            yield buffer

    async def stream_text(self, text: str):
        """Public method to stream text using the generator"""
        async for chunk in self._stream_generator(text):
            await self.broadcast(chunk)

    async def broadcast(self, message: str):
        """Send a message to all connected WebSocket clients"""
        try:
            # Check if message is JSON
            if isinstance(message, dict):
                # Handle HTMX formatted responses
                if message.get("type") == "htmx":
                    htmx_response = message
                    content = to_xml(htmx_response['content'])
                    formatted_response = f"""<div id="todo-{htmx_response.get('id')}" hx-swap-oob="beforeend:#todo-list">
                        {content}
                    </div>"""
                    for ws in self.active_websockets:
                        await ws.send_text(formatted_response)
                    return

            # Handle regular text messages
            formatted_msg = message.replace('\n', '<br>') if isinstance(message, str) else str(message)
            for ws in self.active_websockets:
                await ws.send_text(formatted_msg)

        except Exception as e:
            self.logger.error(f"Error in broadcast: {e}")

    async def handle_chat_message(self, websocket: WebSocket, message: str):
        """Handle incoming chat messages"""
        try:
            if message.lower().startswith('!test'):
                test_script = """
                <script>
                    testAlert("Creating interactive card...");
                    const contentDiv = document.getElementById('content-container');
                    
                    // Create a card with some interactive elements
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.style.margin = '10px';
                    card.innerHTML = `
                        <div class="card-header">
                            <h3>Dynamic Test Card</h3>
                            <small>Created at: ${new Date().toLocaleTimeString()}</small>
                        </div>
                        <div class="card-body">
                            <p>This card was dynamically injected via WebSocket + JavaScript.</p>
                            <button onclick="testAlert('Button in dynamic card clicked!')" class="button">
                                Test Interaction
                            </button>
                        </div>
                    `;
                    
                    // Add it to the container
                    contentDiv.appendChild(card);
                    
                    testAlert("Interactive card added! Try clicking the button.");
                </script>
                """
                await websocket.send_text(test_script)
                self.logger.debug("Sent interactive card injection test")
                return

            if message.lower().startswith(('!egg', '!easter')):
                # Dictionary of easter egg related emojis
                easter_emojis = {
                    'egg': '🥚',
                    'hatching': '🐣',
                    'rabbit': '🐰',
                    'sparkles': '✨',
                    'gift': '🎁',
                    'magic': '🪄',
                    'surprise': '🎉',
                    'treasure': '💎',
                    'key': '🔑',
                    'lock': '🔒'
                }

                # First get the joke, emoji suggestion and task name from LLM
                prompt = (
                    f"Generate a response in the following format:\n"
                    f"EMOJI: [one emoji name from this list: {', '.join(easter_emojis.keys())}]\n"
                    f"TASK: [max 12 char task name]\n"  # Reduced from 20 to 12 chars to prevent wrapping
                    f"JOKE: [unique 1-2 sentence joke about software Easter eggs]\n\n"
                    f"Make the joke creative and unexpected. Vary your emoji and task name choices.\n"
                    f"Important: Keep the exact format with EMOJI:, TASK:, and JOKE: labels."
                )

                messages = [{"role": "user", "content": prompt}]

                # Stream the response first to show the joke being generated
                response = ""
                response = await chatq(prompt, base_app=self.base_app)

                # Parse response to get emoji, task name and joke
                emoji_key = None
                task_name = None
                joke = None

                # Split response into lines and parse each section
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('EMOJI:'):
                        emoji_key = line[6:].strip().lower()
                    elif line.startswith('TASK:'):
                        task_name = line[5:].strip()  # Reduced max length to 12 chars
                    elif line.startswith('JOKE:'):
                        joke = line[5:].strip()

                # Fallback values if parsing fails
                if not emoji_key or emoji_key not in easter_emojis:
                    emoji_key = random.choice(list(easter_emojis.keys()))
                if not task_name:
                    task_name = "EggHunt"  # Shorter fallback name
                if not joke:
                    joke = "Found a quirky Easter egg! 🎉"

                chosen_emoji = easter_emojis[emoji_key]

                # Create todo item with chosen emoji and task name
                new_item = todos.insert({
                    "name": f"{chosen_emoji} {task_name}"
                })

                # Use the returned ID in the render function
                todo_html = to_xml(render_todo(new_item))
                todo_html = todo_html.replace('<li', f'<li data-id="{new_item.id}" id="todo-{new_item.id}"')
                todo_html = todo_html.replace('<li', '<li hx-swap="beforeend" hx-target="#todo-list"')

                # Add a script tag to process HTMX after insertion
                todo_html += f'<script>htmx.process(document.getElementById("todo-{new_item.id}"))</script>'

                # Send the todo HTML after the joke has finished streaming
                await websocket.send_text(todo_html)
                return

            if message.lower().startswith('!help'):
                # First, show help text to user
                help_text = """Available commands:
                !test - Run DOM manipulation test
                !egg - Insert a test task
                !help - Show this help message"""
                await websocket.send_text(help_text)

                # Silently reinforce system instructions
                system_message = generate_system_message()
                await chatq(system_message, role="system", base_app=self)  # Output doesn't matter

                return

            # Regular message handling
            conversation_history = []
            conversation_history = append_to_conversation(message, "user", conversation_history)

            # Split message to get verbatim flag if present
            parts = message.split('|')
            msg = parts[0]
            verbatim = len(parts) > 1 and parts[1] == 'verbatim'
            
            # Generate assistant's response using chatq with verbatim parameter
            raw_response = await chatq(msg, verbatim=verbatim, base_app=self.base_app)

            # Try to parse the response as JSON
            try:
                response_json = json.loads(raw_response)
                if "action" in response_json:
                    # Handle CRUD action
                    result = await execute_crud_operation(self.base_app, response_json)
                    if isinstance(result, tuple) and len(result) > 1:
                        response_message, new_item = result
                        if new_item:
                            # Render new item as HTML
                            html_content = to_xml(self.base_app.render_item(new_item))
                            # Send HTML back to the client
                            await websocket.send_text(html_content)
                        else:
                            # Send response message if no new item
                            await websocket.send_text(response_message)
                    else:
                        # Send response message if result is not a tuple
                        await websocket.send_text(result)
            except json.JSONDecodeError:
                # Response is not JSON, no need to send again since we streamed it
                pass

            # Append the assistant's response to conversation history
            conversation_history = append_to_conversation(raw_response, "assistant", conversation_history)

        except Exception as e:
            self.logger.error(f"Error in handle_chat_message: {e}")
            traceback.print_exc()

    def create_progress_card(self):
        """Create the chat interface card"""
        return Card(
            Header("Chat Playground"),
            Form(
                Div(
                    TextArea(id="chat-input", placeholder="Type your message here...", rows="3"),
                    Button("Send", type="submit"),
                    id="chat-form"
                ),
                onsubmit="sendMessage(event)"
            ),
            Div(id="chat-messages"),
            Script("""
                const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws'}://${window.location.host}/ws`);
                
                ws.onmessage = function(event) {
                    const messages = document.getElementById('chat-messages');
                    messages.innerHTML += event.data + '<br>';
                    messages.scrollTop = messages.scrollHeight;
                };
                
                function sendMessage(event) {
                    event.preventDefault();
                    const input = document.getElementById('chat-input');
                    const message = input.value;
                    if (message.trim()) {
                        ws.send(message);
                        input.value = '';
                    }
                }
            """)
        )

    async def handle_websocket(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_websockets.add(websocket)
            self.logger.debug("Chat WebSocket connected")

            while True:
                message = await websocket.receive_text()
                self.logger.debug(f"Received message: {message}")

                try:
                    # Try to parse as JSON first
                    msg_data = json.loads(message)
                    if "action" in msg_data:
                        # Handle CRUD operations
                        result = await execute_crud_operation(self.base_app, msg_data)
                        if isinstance(result, tuple) and len(result) > 0:
                            response, new_item = result
                            # Add hx-swap and hx-target attributes
                            html_content = to_xml(render_todo(new_item))
                            swap_instruction = f"""<div hx-swap-oob="beforeend:#todo-list">{html_content}</div>"""
                            await websocket.send_text(swap_instruction)
                        continue
                except json.JSONDecodeError:
                    # Not JSON, treat as regular chat message
                    await self.handle_chat_message(websocket, message)

        except WebSocketDisconnect:
            self.logger.info("WebSocket disconnected")
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self.active_websockets.discard(websocket)
            self.logger.debug("WebSocket connection closed")

    async def render_chat(self):
        self.logger.debug("Rendering chat playground interface")
        return self.create_progress_card()


chat = Chat(app, id_suffix="", base_app=todo_app)

# figlet ---------------------------------------------------------------------------------------------
#  _____                          ____            _
# |  ___|   _ _ __  _ __  _   _  | __ ) _   _ ___(_)_ __   ___  ___ ___
# | |_ | | | | '_ \| '_ \| | | | |  _ \| | | / __| | '_ \ / _ \/ __/ __|
# |  _|| |_| | | | | | | | |_| | | |_) | |_| \__ \ | | | |  __/\__ \__ \
# |_|   \__,_|_| |_|_| |_|\__, | |____/ \__,_|___/_|_| |_|\___||___/___/
#                         |___/
# *******************************
# Funny Business is stupid web tricks like the 404 handler & middleware
# *******************************


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class DOMSkeletonMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and database state.

    Logs requests with ASCII art headers, processes the request,
    and displays current database contents after each request.
    Uses Figlet for ASCII art and Rich for formatted console output.
    """

    async def dispatch(self, request, call_next):
        """
        Process requests, log details, and display database state.

        Args:
            request: Incoming HTTP request.
            call_next: Next request handler.

        Returns:
            HTTP response from the next handler.

        Prints request details and database contents to console.
        """
        # Log the incoming HTTP request
        endpoint = request.url.path
        method = request.method
        fig(font='slant', text=f"{method} {endpoint}")
        logger.debug(f"HTTP Request: {method} {endpoint}")

        # Call the next middleware or request handler
        response = await call_next(request)

        # Print a rich table of the db key/value pairs
        cookie_table = Table(title="Stored Cookie States")
        cookie_table.add_column("Key", style="cyan")
        cookie_table.add_column("Value", style="magenta")
        for key, value in db.items():
            json_value = JSON.from_data(value, indent=2)
            cookie_table.add_row(key, json_value)
        cookie_table.columns[1].style = "white"
        # fig('cookie', font='crawford')
        console.print(cookie_table)

        # Print a rich table of the pipeline states
        pipeline_table = Table(title="Pipeline States")
        pipeline_table.add_column("URL", style="yellow")
        pipeline_table.add_column("Created", style="magenta")
        pipeline_table.add_column("Updated", style="cyan")
        pipeline_table.add_column("Steps", style="white")

        # Query all records from the pipeline table
        for record in pipulate.table():  # MiniDataAPI tables are callable to query records
            try:
                state = json.loads(record.data)
                pre_state = json.loads(record.data)
                pipeline_table.add_row(
                    record.url,
                    str(state.get('created', '')),
                    str(state.get('updated', '')),
                    str(len(pre_state) - 2)
                )
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Error parsing pipeline state for {record.url}: {e}")
                pipeline_table.add_row(record.url, "ERROR", "Invalid State")

        # fig('pipeline', font='banner3')
        console.print(pipeline_table)

        return response


def print_routes():
    """
    Print a formatted table of all routes in the application.

    This function creates a rich console table displaying information about each route
    in the application. The table includes columns for the route type, methods, path,
    and a duplicate indicator.

    The function handles different types of routes:
    - Standard routes (Route)
    - WebSocket routes (WebSocketRoute)
    - Mounted applications (Mount)
    - Any other unrecognized route types

    The table is color-coded for better readability:
    - Type: Cyan
    - Methods: Yellow
    - Path: White (Red if duplicate)
    - Duplicate: Red if duplicate, otherwise green

    Note: This function assumes the existence of a global 'app' object with a 'routes' attribute.

    Returns:
        None. The function prints the table to the console.
    """
    logger.debug('Route Table')
    table = Table(title="Application Routes")

    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Methods", style="yellow on black")
    table.add_column("Path", style="white")
    table.add_column("Duplicate", style="green")

    # Collect all routes in a list for sorting
    route_entries = []

    # Set to track (path, method) pairs
    seen_routes = set()

    for app_route in app.routes:
        if isinstance(app_route, Route):
            methods = ", ".join(app_route.methods)
            route_key = (app_route.path, methods)

            # Check for duplicates
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)

            route_entries.append(("Route", methods, app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, WebSocketRoute):
            route_key = (app_route.path, "WebSocket")

            # Check for duplicates
            if route_key in seen_routes:
                path_style = "red"
                duplicate_status = Text("Yes", style="red")
            else:
                path_style = "white"
                duplicate_status = Text("No", style="green")
                seen_routes.add(route_key)

            route_entries.append(("WebSocket", "WebSocket", app_route.path, path_style, duplicate_status))
        elif isinstance(app_route, Mount):
            route_entries.append(("Mount", "Mounted App", app_route.path, "white", Text("N/A", style="green")))
        else:
            route_entries.append((str(type(app_route)), "Unknown", getattr(app_route, 'path', 'N/A'), "white", Text("N/A", style="green")))

    # Sort the routes by path
    route_entries.sort(key=lambda x: x[2])

    # Add sorted routes to the table
    for entry in route_entries:
        table.add_row(
            entry[0],
            entry[1],
            Text(entry[2], style=f"{entry[3]} on black"),
            entry[4]
        )

    console.print(table)


# figlet ---------------------------------------------------------------------------------------------
#  ____                       __ __
# / ___|  ___ _ ____   _____ / / \ \
# \___ \ / _ \ '__\ \ / / _ \ |   | |
#  ___) |  __/ |   \ V /  __/ |   | |
# |____/ \___|_|    \_/ \___| |   | |
#                            \_\ /_/
# *******************************
# And now the moment you've all been waiting for: Activate the Application
# *******************************

# Combine the GET routes with MENU_ITEMS
ALL_ROUTES = list(set(['', todo_app.name, profile_app.name] + MENU_ITEMS))

for item in ALL_ROUTES:
    path = f'/{item}' if item else '/'

    @app.route(path)
    async def home_route(request):
        return await home(request)

# Register the funny business
app.add_middleware(DOMSkeletonMiddleware)
logger.debug("Application setup completed with DOMSkeletonMiddleware.")

# Print the application name in ASCII art upon startup
fig(font='slant', text=APP_NAME)

# Retrieve and set the best available LLaMA model
model = get_best_model()
fig(f'Model: {model}', font='ogre')
logger.debug(f"Using model: {model}")

# After setting up all routes
print_routes()

# Start the application server
fig('Server', font='big')
# serve()

# figlet ---------------------------------------------------------------------------------------------
#  _     _             ____      _                 _
# | |   (_)_   _____  |  _ \ ___| | ___   __ _  __| |
# | |   | \ \ / / _ \ | |_) / _ \ |/ _ \ / _` |/ _` |
# | |___| |\ V /  __/ |  _ <  __/ | (_) | (_| | (_| |
# |_____|_| \_/ \___| |_| \_\___|_|\___/ \__,_|\__,_|
#
# *******************************
# File System Watchdog
# *******************************

"""
        ┌─────────────┐
        │ File System │
        │  Watchdog   │          ┌──────────────┐
        │ "MEEP MEEP" │          │  AST Syntax  │
        └──────┬──────┘          │   "Valid!"   │
               │                 └───────┬──────┘
               │ BONK!                   │
               ▼                         ▼
 ┌───────────────────────────┐     ┌──────────┐
 │    Uvicorn Server         │ ──► │   Save   │
 │"Still holding SSE conn..."│     │ Changes  │
 └───────────────────────────┘     └──────────┘
"""


def check_syntax(filename):
    with open(filename, 'r') as file:
        source = file.read()
    try:
        ast.parse(source)
        return True
    except SyntaxError as e:
        print(f"Syntax error in {filename}:")
        print(f"  Line {e.lineno}: {e.text}")
        print(f"  {' ' * (e.offset - 1)}^")
        print(f"Error: {e}")
        return False


def restart_server():
    """Restart the server if the current file has been modified."""
    if not check_syntax(THIS_FILE):
        print("Syntax error detected. Please fix the error and save the file again.")
        return

    max_retries = 3
    for attempt in range(max_retries):
        try:
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"Error restarting server (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Waiting 5 seconds before retrying...")
                time.sleep(5)
            else:
                print("Max retries reached. Please restart the server manually.")


class ServerRestartHandler(FileSystemEventHandler):
    """Restart the server if the current file has been modified."""

    def on_modified(self, event):
        if str(THIS_FILE.resolve()) == str(Path(event.src_path).resolve()):
            print(f"{THIS_FILE} has been modified. Checking syntax and restarting...")
            restart_server()


def run_server_with_watchdog():
    """Run the server with a watchdog to restart it if the current file has been modified."""
    event_handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        uvicorn.run(app, host="0.0.0.0", port=5001)
    except KeyboardInterrupt:
        observer.stop()
    except Exception as e:
        print(f"Error running server: {e}")
        print("Attempting to restart...")
        restart_server()
    finally:
        observer.join()


if __name__ == "__main__":
    run_server_with_watchdog()

# MY FAVORITE LINTING COMMANDS
# autopep8 --ignore E501,F405,F403,F541 --in-place pipulate.py
# isort pipulate.py
# vulture pipulate.py
# pylint --disable=all --enable=redefined-outer-name pipulate.py
