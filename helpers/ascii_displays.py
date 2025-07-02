# ASCII Art and Visual Display Functions
# Externalized from server.py to reduce token count while preserving functionality

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
import pyfiglet
import logging

logger = logging.getLogger(__name__)

def falling_alice(console_output=True):
    """Display falling Alice ASCII art for Pipulate startup"""
    alice_art = '''
    
        🕳️ Down the Rabbit Hole We Go... 🕳️
    
                    .-""""""-.
                  .'          '.
                 /   O      O   \\
                :           `    :
                |                |
                :    .------.    :
                 \\  '        '  /
                  '.          .'
                    '-.......-'
                        
            🚀 Pipulate: Local-First AI SEO Software
            
                "We're all mad here..." 
                    - Cheshire Cat
    '''
    
    if console_output:
        console = Console()
        panel = Panel(
            Align.center(alice_art),
            title="🎭 Welcome to Wonderland",
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(panel)
    
    logger.info(f"🎭 NARRATOR: {alice_art}")
    return alice_art


def white_rabbit(console_output=True):
    """Display White Rabbit ASCII art for time-sensitive operations"""
    rabbit_art = '''
    
        🐰 "I'm Late! I'm Late! For a Very Important Date!" 🐰
    
                    (\   /)
                   ( ._.)
                  o_(")(")
                
            ⏰ Time to Optimize Your SEO Workflows!
            
                "The hurrier I go, the behinder I get"
                    - White Rabbit
    '''
    
    if console_output:
        console = Console()
        panel = Panel(
            Align.center(rabbit_art),
            title="⏰ Time is Ticking",
            border_style="bright_white",
            padding=(1, 2)
        )
        console.print(panel)
    
    logger.info(f"🐰 NARRATOR: {rabbit_art}")
    return rabbit_art


def system_diagram(console_output=True):
    """Display system architecture diagram"""
    diagram = '''
    
        🏗️ Pipulate Architecture Overview 🏗️
    
        Browser ←→ FastHTML Server ←→ Local AI
            ↓           ↓              ↓
        HTMX/JS    Plugin System    Ollama LLM
            ↓           ↓              ↓
        User UI     Workflows      WebSocket Chat
            ↓           ↓              ↓
        Data Flow   SQLite DB      Context Sync
        
            🎯 Local-First • Privacy-Preserving • AI-Enhanced
    '''
    
    if console_output:
        console = Console()
        panel = Panel(
            Align.center(diagram),
            title="🏗️ System Architecture",
            border_style="bright_green",
            padding=(1, 2)
        )
        console.print(panel)
    
    logger.info(f"🏗️ DIAGRAM: {diagram}")
    return diagram


def figlet_banner(text, subtitle=None, font='slant', color=None, box_style=None, console_output=True):
    """Generate figlet ASCII art banner"""
    try:
        figlet_text = pyfiglet.figlet_format(text, font=font)
    except:
        figlet_text = f"=== {text.upper()} ==="
    
    banner_content = figlet_text
    if subtitle:
        banner_content += f"\n\n{subtitle}"
    
    if console_output:
        console = Console()
        if box_style:
            panel = Panel(
                Align.center(banner_content),
                border_style=box_style or "bright_blue",
                padding=(1, 2)
            )
            console.print(panel)
        else:
            console.print(Align.center(banner_content))
    
    logger.info(f"🎨 FIGLET_BANNER: {text} (font: {font}) - {subtitle or 'No subtitle'}")
    return banner_content


def ascii_banner(title, subtitle=None, style=None, box_style=None):
    """Create a simple ASCII banner"""
    banner = f"\n{'=' * 60}\n"
    banner += f"  {title.upper()}\n"
    if subtitle:
        banner += f"  {subtitle}\n"
    banner += f"{'=' * 60}\n"
    
    console = Console()
    if box_style:
        panel = Panel(
            Align.center(banner),
            border_style=box_style,
            padding=(1, 2)
        )
        console.print(panel)
    else:
        console.print(banner)
    
    return banner


def radical_transparency_banner(console_output=True):
    """Display radical transparency mission statement"""
    transparency_art = '''
    
        🔍 RADICAL TRANSPARENCY ACTIVATED 🔍
    
            "In this house, we practice radical transparency.
             Every operation is observable.
             Every state change is logged.
             Every decision is traceable."
             
                - The Pipulate Philosophy
                
        🎯 FINDER_TOKENs guide the way to truth
        📊 Complete system observability enabled
        🔧 Zero black boxes, maximum insight
    '''
    
    if console_output:
        console = Console()
        panel = Panel(
            Align.center(transparency_art),
            title="🔍 Radical Transparency",
            border_style="bright_yellow",
            padding=(1, 2)
        )
        console.print(panel)
    
    logger.info(f"🔍 TRANSPARENCY: Radical transparency banner displayed")
    return transparency_art


def status_banner(mcp_count, plugin_count, env="Development"):
    """Display current system status banner"""
    status_art = f'''
    
        🚀 PIPULATE STATUS
        Local First AI SEO Software
        
        🌐 Server: http://localhost:5001
        🔧 MCP Tools: {mcp_count} active
        📦 Plugins: {plugin_count} registered  
        🏡 Environment: {env}
        🔍 Transparency: Full visibility enabled
    '''
    
    console = Console()
    panel = Panel(
        Align.center(status_art),
        title="⚡ System Status",
        border_style="bright_cyan",
        padding=(1, 2)
    )
    console.print(panel)
    
    logger.info(f"📊 STATUS_BANNER: MCP:{mcp_count}, Plugins:{plugin_count}, Env:{env}")
    return status_art


def fig(text, font='slant', color=None, width=200):
    """Quick figlet generation"""
    try:
        return pyfiglet.figlet_format(text, font=font, width=width)
    except:
        return f"=== {text.upper()} ==="


def chip_says(message, style=None, prefix="💬 Chip O'Theseus"):
    """Display a message from Chip O'Theseus narrator"""
    full_message = f"{prefix}: {message}"
    console = Console()
    console.print(full_message, style=style)
    logger.info(f"🎭 NARRATOR: {full_message}")
    return full_message


def story_moment(title, details=None, color=None):
    """Create a narrative story moment"""
    console = Console()
    text = Text(f"📖 {title}", style=f"bold {color or 'bright_blue'}")
    
    if details:
        text.append(f"\n   {details}")
    
    panel = Panel(
        text,
        border_style=color or "bright_blue",
        padding=(0, 1)
    )
    console.print(panel)
    
    logger.info(f"📖 STORY: {title} - {details or 'No details'}")
    return f"{title}: {details}" if details else title


def server_whisper(message, emoji="🤫"):
    """Display a quiet server message"""
    full_message = f"{emoji} {message}"
    console = Console()
    console.print(full_message, style="dim")
    return full_message


def section_header(icon, title, description=None, color=None):
    """Create a section header with consistent formatting"""
    header_text = f"{icon}  {title}"
    if description:
        header_text += f"\n{description}"
        
    separator = "─" * 60
    
    console = Console()
    panel = Panel(
        Align.center(f"{header_text}\n{separator}"),
        border_style=color or "bright_blue",
        padding=(1, 2)
    )
    console.print(panel)
    
    logger.info(f"📋 SECTION: {icon} {title} - {description or 'No description'}")
    return f"{header_text}\n{separator}" 