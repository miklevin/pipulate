import os
import sys
import argparse
import tiktoken
import re
from typing import Dict, List, Optional, Union

# Hi there, Gemini! I case you're wondering, this is the script that I use to
# make this great big XML file you're looking at.
#
# NOTE: This script now includes the modular tools/ directory containing
# extracted MCP tools (botify_mcp_tools.py, advanced_automation_mcp_tools.py)
# for token optimization purposes.

# ============================================================================
# USER CONFIGURATION: Files to include in context
# ============================================================================
# Files are now configured in foo_files.py module.
# To update the file list:
#   1. Run: python generate_files_list.py (or python prompt_foo.py --files)
#   2. Edit foo_files.py to uncomment the files you want to include
#   3. Run prompt_foo.py as usual
#
# Note: When using a prompt file with --prompt flag, the script automatically
# selects Template 1 (Material Analysis Mode), which is designed to be more
# flexible and allows for various response types rather than strictly
# implementation-focused responses.

# FILES_TO_INCLUDE_RAW will be loaded from foo_files.py when needed
FILES_TO_INCLUDE_RAW = None

def load_files_to_include():
    """Load FILES_TO_INCLUDE_RAW from foo_files.py module."""
    global FILES_TO_INCLUDE_RAW
    if FILES_TO_INCLUDE_RAW is None:
        try:
            import foo_files
            FILES_TO_INCLUDE_RAW = foo_files.FILES_TO_INCLUDE_RAW
        except ImportError:
            print("ERROR: foo_files.py not found!")
            print("Run 'python generate_files_list.py' or 'python prompt_foo.py --files' to generate it.")
            sys.exit(1)
        except AttributeError:
            print("ERROR: foo_files.py exists but doesn't contain FILES_TO_INCLUDE_RAW!")
            print("Run 'python generate_files_list.py' or 'python prompt_foo.py --files' to regenerate it.")
            sys.exit(1)
    return FILES_TO_INCLUDE_RAW

# Now process the raw string into the list we'll use  
def get_files_to_include():
    """Get the processed list of files to include."""
    files_raw = load_files_to_include()
    files_list = files_raw.strip().splitlines()
    
    # Filter out any commented lines
    files_list = [line for line in files_list if not line.strip().startswith('#')]
    # Filter out blank lines
    files_list = [line for line in files_list if line.strip()]
    
    # Strip off any <-- comments and trailing # comments (handling variable whitespace)
    files_list = [re.sub(r'\s*#.*$', '', line.split('<--')[0]).rstrip() for line in files_list]
    
    # Remove duplicates while preserving order
    seen_files = set()
    deduplicated_files = []
    for file_path in files_list:
        if file_path and file_path not in seen_files:
            seen_files.add(file_path)
            deduplicated_files.append(file_path)
    
    return deduplicated_files

def get_files_with_comments():
    """Get the processed list of files with their comments preserved."""
    files_raw = load_files_to_include()
    files_list = files_raw.strip().splitlines()
    
    # Filter out any commented lines (starting with #)
    files_list = [line for line in files_list if not line.strip().startswith('#')]
    # Filter out blank lines
    files_list = [line for line in files_list if line.strip()]
    
    # Process each line to extract file path and comment
    seen_files = set()
    files_with_comments = []
    
    for line in files_list:
        line = line.strip()
        if not line:
            continue
            
        # Extract file path and comment
        file_path = line
        comment = ""
        
        # Handle <-- style comments first (takes priority over # comments)
        if '<--' in line:
            parts = line.split('<--', 1)
            file_path = parts[0].strip()
            comment = parts[1].strip()
            # Remove any trailing # from the file_path if it exists
            if file_path.endswith('#'):
                file_path = file_path.rstrip('#').strip()
        # Handle trailing # comments
        elif '#' in line:
            parts = line.split('#', 1)
            file_path = parts[0].strip()
            comment = parts[1].strip()
        else:
            file_path = line.strip()
            comment = ""
        
        # Remove duplicates while preserving order
        if file_path and file_path not in seen_files:
            seen_files.add(file_path)
            files_with_comments.append((file_path, comment))
    
    return files_with_comments

# ============================================================================
# MATERIAL ANALYSIS CONFIGURATION  
# ============================================================================
# Set these values to enable material analysis mode.
# When enabled, the script will include the specified material in the context
# and use specialized prompts for flexible analysis.

PROMPT_FILE = None  # Default prompt file is None

# ============================================================================
# END USER CONFIGURATION
# ============================================================================

# ============================================================================
# CONTENT SIZE REFERENCE SCALE
# ============================================================================
# Real-world comparisons for understanding token and word counts
CONTENT_SIZE_SCALE = {
    "words": [
        (500, "Short blog post"),
        (1000, "Long blog post or magazine article"),
        (2500, "Academic paper or white paper"),
        (5000, "Long-form journalism piece"),
        (7500, "Short story"),
        (10000, "College research paper"),
        (15000, "Novella or master's thesis chapter"),
        (25000, "Master's thesis"),
        (40000, "Doctoral dissertation chapter"),
        (60000, "Short non-fiction book"),
        (80000, "Standard novel"),
        (120000, "Long novel"),
        (200000, "Epic fantasy novel"),
    ],
    "tokens": [
        (1000, "Email or short memo"),
        (2500, "Blog post"),
        (5000, "Magazine article"),
        (10000, "Academic paper"),
        (25000, "Long-form article"),
        (50000, "Short story or report"),
        (75000, "Novella chapter"),
        (100000, "Technical documentation"),
        (150000, "Short book"),
        (250000, "Standard novel"),
        (400000, "Long novel"),
        (500000, "Technical manual"),
        (750000, "Epic novel"),
    ]
}

def get_size_comparison(count, count_type="words"):
    """Get a human-readable comparison for word or token counts."""
    scale = CONTENT_SIZE_SCALE.get(count_type, CONTENT_SIZE_SCALE["words"])
    
    for threshold, description in scale:
        if count <= threshold:
            return description
    
    # If larger than our biggest reference
    return f"Larger than {scale[-1][1]}"

def format_size_with_comparison(word_count, token_count):
    """Format size information with human-readable comparisons."""
    word_comparison = get_size_comparison(word_count, "words")
    token_comparison = get_size_comparison(token_count, "tokens")
    
    return {
        "words": f"{word_count:,} words ({word_comparison})",
        "tokens": f"{token_count:,} tokens ({token_comparison})",
        "word_comparison": word_comparison,
        "token_comparison": token_comparison
    }

# ============================================================================
# END CONTENT SIZE REFERENCE SCALE
# ============================================================================

def print_structured_output(manifest, pre_prompt, files, post_prompt, total_tokens, max_tokens, total_words=None):
    """Print a structured view of the prompt components in markdown format."""
    print("\n=== Prompt Structure ===\n")
    
    print("--- Pre-Prompt ---")
    # Handle pre-prompt content
    try:
        if '<context>' in pre_prompt:
            context_start = pre_prompt.find('<context>') + 8
            context_end = pre_prompt.find('</context>')
            if context_start > 7 and context_end > context_start:
                context_content = pre_prompt[context_start:context_end]
                
                # Extract system info
                if '<system_info>' in context_content:
                    sys_start = context_content.find('<system_info>') + 12
                    sys_end = context_content.find('</system_info>')
                    if sys_start > 11 and sys_end > sys_start:
                        print("System Information:")
                        sys_content = context_content[sys_start:sys_end].strip()
                        # Remove any remaining XML tags and clean up formatting
                        sys_content = re.sub(r'<[^>]+>', '', sys_content)
                        sys_content = sys_content.replace('>', '')  # Remove any remaining > characters
                        print(f"  {sys_content}")
                
                # Extract key points
                if '<key_points>' in context_content:
                    points_start = context_content.find('<key_points>') + 11
                    points_end = context_content.find('</key_points>')
                    if points_start > 10 and points_end > points_start:
                        points_content = context_content[points_start:points_end]
                        print("\nKey Points:")
                        for point in points_content.split('<point>'):
                            if point.strip():
                                point_end = point.find('</point>')
                                if point_end > -1:
                                    point_content = point[:point_end].strip()
                                    # Remove any remaining XML tags
                                    point_content = re.sub(r'<[^>]+>', '', point_content)
                                    print(f"  • {point_content}")
    except Exception as e:
        print("  [Error parsing pre-prompt content]")
    
    print("\n--- Files Included ---")
    # Parse the manifest to get token counts for each file
    token_counts = {}
    try:
        if '<token_usage>' in manifest:
            token_usage_start = manifest.find('<token_usage>') + 12
            token_usage_end = manifest.find('</token_usage>')
            token_usage = manifest[token_usage_start:token_usage_end]
            
            if '<files>' in token_usage:
                files_start = token_usage.find('<files>') + 7
                files_end = token_usage.find('</files>', files_start)
                files_section = token_usage[files_start:files_end]
                
                if '<content>' in files_section:
                    content_start = files_section.find('<content>') + 9
                    content_end = files_section.find('</content>')
                    content_section = files_section[content_start:content_end]
                    
                    # Extract file paths and token counts
                    file_pattern = r'<file>.*?<path>(.*?)</path>.*?<tokens>(.*?)</tokens>.*?</file>'
                    for match in re.finditer(file_pattern, content_section, re.DOTALL):
                        path, tokens = match.groups()
                        token_counts[path.strip()] = int(tokens.strip())
    except Exception as e:
        print(f"  [Error parsing token counts: {e}]")
    
    for file in files:
        tokens_str = f" ({token_counts.get(file, 0):,} tokens)" if file in token_counts else ""
        print(f"• {file}{tokens_str}")
    
    print("\n--- Post-Prompt ---")
    # Show the actual prompt content if it's a direct string
    if post_prompt and not os.path.exists(post_prompt):
        print("\nDirect String Prompt:")
        print(f"  {post_prompt}")
    elif post_prompt:
        print(f"\nPrompt File: {post_prompt}")
    
    print("\n--- Token Summary ---")
    print(f"Total tokens: {format_token_count(total_tokens)}")
    if total_words is not None:
        print(f"Total words: {format_word_count(total_words)}")
        
        # Add size comparisons
        size_info = format_size_with_comparison(total_words, total_tokens)
        print(f"\nSize Perspective:")
        print(f"📝 Content size: {size_info['word_comparison']}")
        print(f"🤖 Token size: {size_info['token_comparison']}")
        
        # Calculate and show token-to-word ratio
        ratio = total_tokens / total_words if total_words > 0 else 0
        print(f"📊 Token-to-word ratio: {ratio:.2f} (higher = more technical/structured content)")
    
    print("\n=== End Prompt Structure ===\n")

# -------------------------------------------------------------------------
# NOTE TO USERS:
# This script is obviously customized to my (Mike Levin's) specific purposes,
# but if you find this interesting, just go in and adjust the paths and the 
# prompts to taste. It's an effective way to put a lot of separate files into 
# one text-file or your OS's copy/paste buffer and do one-shot prompting with 
# spread out files as if they were a single file (reduce copy/paste tedium 
# and improve prompt injection consistency).
# -------------------------------------------------------------------------

# --- XML Support Functions ---
def wrap_in_xml(content: str, tag_name: str, attributes: Optional[Dict[str, str]] = None) -> str:
    """Wrap content in XML tags with optional attributes."""
    attrs = " ".join(f'{k}="{v}"' for k, v in (attributes or {}).items())
    return f"<{tag_name}{' ' + attrs if attrs else ''}>{content}</{tag_name}>"

def create_xml_element(tag_name: str, content: Union[str, List[str]], attributes: Optional[Dict[str, str]] = None) -> str:
    """Create an XML element with optional attributes and content."""
    if isinstance(content, list):
        content = "\n".join(content)
    content = content.replace('\n\n', '\n')  # Remove double newlines
    return wrap_in_xml(content, tag_name, attributes)

def create_xml_list(items: List[str], tag_name: str = "item") -> str:
    """Create an XML list from a list of items."""
    return "\n".join(f"<{tag_name}>{item}</{tag_name}>" for item in items)

# --- Configuration for context building ---
# Edit these values as needed
repo_root = "/home/mike/repos/pipulate"  # Path to your repository

# Token buffer for pre/post prompts and overhead
TOKEN_BUFFER = 10_000
MAX_TOKENS = 4_000_000  # Set to a high value since we're not chunking

# === Prompt Templates ===
# Define multiple prompt templates and select them by index
prompt_templates = [
    # Template 0: General Codebase Analysis
    {
        "name": "General Codebase Analysis",
        "pre_prompt": create_xml_element("context", [
            create_xml_element("system_info", """
This codebase uses a hybrid approach with Nix for system dependencies and virtualenv for Python packages.
"""),
        ]),
        "post_prompt": create_xml_element("analysis_request", [
            create_xml_element("introduction", """
Now that you've reviewed the codebase context, I'd love your insights and analysis!

Dear AI Assistant:
I've provided you with the core architecture of a Python web application that takes an interesting approach to modern web development. I'd appreciate your thoughtful analysis on any of these aspects:
"""),
            create_xml_element("analysis_areas", [
                create_xml_element("area", [
                    "<title>Technical Architecture Analysis</title>",
                    "<questions>",
                    "<question>How does this hybrid Nix+virtualenv approach compare to other deployment patterns?</question>",
                    "<question>What are the tradeoffs of using HTMX with server-side state vs traditional SPAs?</question>",
                    "<question>How does the plugin system architecture enable extensibility?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Pattern Recognition & Insights</title>",
                    "<questions>",
                    "<question>What patterns emerge from the codebase that surprise you?</question>",
                    "<question>How does this approach to web development differ from current trends?</question>",
                    "<question>What potential scaling challenges or opportunities do you see?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Forward-Looking Perspective</title>",
                    "<questions>",
                    "<question>How does this architecture align with or diverge from emerging web development patterns?</question>",
                    "<question>What suggestions would you make for future evolution of the system?</question>",
                    "<question>How might this approach need to adapt as web technologies advance?</question>",
                    "</questions>"
                ])
            ]),
            create_xml_element("focus_areas", [
                "<area>The interplay between modern and traditional web development approaches</area>",
                "<area>Architectural decisions that stand out as novel or counterintuitive</area>",
                "<area>Potential implications for developer experience and system maintenance</area>"
            ])
        ])
    },
    # Template 1: Material Analysis Mode
    {
        "name": "Material Analysis Mode",
        "pre_prompt": create_xml_element("context", [
            create_xml_element("system_info", """
You are about to review a codebase and related documentation. Please study and understand
the provided materials thoroughly before responding.
"""),
            create_xml_element("key_points", [
                "<point>Focus on understanding the architecture and patterns in the codebase</point>",
                "<point>Note how existing patterns could be leveraged in your response</point>",
                "<point>Consider both technical and conceptual aspects in your analysis</point>"
            ])
        ]),
        "post_prompt": create_xml_element("response_request", [
            create_xml_element("introduction", """
Now that you've reviewed the provided materials, please respond thoughtfully to the prompt.
Your response can include analysis, insights, implementation suggestions, or other relevant
observations based on what was requested.
"""),
            create_xml_element("response_areas", [
                create_xml_element("area", [
                    "<title>Material Analysis</title>",
                    "<questions>",
                    "<question>What are the key concepts, patterns, or architecture details in the provided materials?</question>",
                    "<question>What interesting aspects of the system stand out to you?</question>",
                    "<question>How would you characterize the approach taken in this codebase?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Strategic Considerations</title>",
                    "<questions>",
                    "<question>How might the content of the materials inform future development?</question>",
                    "<question>What patterns or conventions should be considered in any response?</question>",
                    "<question>What alignment exists between the provided materials and the prompt?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Concrete Response</title>",
                    "<questions>",
                    "<question>What specific actionable insights can be provided based on the prompt?</question>",
                    "<question>If implementation is requested, how might it be approached?</question>",
                    "<question>What recommendations or observations are most relevant to the prompt?</question>",
                    "</questions>"
                ])
            ]),
            create_xml_element("focus_areas", [
                "<area>Responding directly to the core request in the prompt</area>",
                "<area>Drawing connections between the materials and the prompt</area>",
                "<area>Providing value in the form requested (analysis, implementation, etc.)</area>"
            ])
        ])
    }
]

# file_list will be initialized when needed via get_files_to_include()

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def count_words(text: str) -> int:
    """Count the number of words in a text string."""
    # Simple word counting: split on whitespace and filter out empty strings
    words = text.split()
    return len(words)

def format_token_count(num: int) -> str:
    """Format a token count with commas."""
    return f"{num:,} tokens"

def format_word_count(num: int) -> str:
    """Format a word count with commas."""
    return f"{num:,} words"

def run_tree_command():
    """Run the tree command and return its output."""
    try:
        import subprocess
        result = subprocess.run(
            ['tree', '-I', '__pycache__|client|data|downloads|looking_at|*.csv|*.zip|*.pkl|*.png|*.svg|*.html'],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error running tree command: {result.stderr}"
    except Exception as e:
        return f"Error running tree command: {str(e)}"

# --- AI Assistant Manifest System ---
class AIAssistantManifest:
    """
    Manifest system for AI coding assistants to understand context before receiving files.
    
    This class generates a structured overview of what files and information 
    the assistant is about to receive, helping to:
    1. Set expectations about content length and complexity
    2. Provide a map of key components and their relationships
    3. Establish important conventions specific to this codebase
    4. Track token usage for each component and total context
    """
    
    def __init__(self, model="gpt-4"):
        self.files = []
        self.conventions = []
        self.environment_info = {}
        self.critical_patterns = []
        self.model = model
        self.token_counts = {
            "files": {
                "metadata": 0,  # For file descriptions and components
                "content": {}   # For actual file contents, keyed by filename
            },
            "environment": 0,
            "conventions": 0,
            "patterns": 0,
            "manifest_structure": 0,
            "total_content": 0  # Running total of file contents
        }
                    # Add XSD schema for XML structure understanding (front-load for LLM understanding)
        xsd_schema = self._load_xsd_schema()
        if xsd_schema:
            self.set_environment("XML Schema Definition", f"Below is the XSD schema that defines the structure of this XML context document:\n\n{xsd_schema}", description="schema")
        
        # Add tree output to environment info
        tree_output = run_tree_command()
        self.set_environment("Codebase Structure", f"Below is the output of 'tree -I \"__pycache__|client|data|*.csv|*.zip|*.pkl\"' showing the current state of the codebase:\n\n{tree_output}", description="tree")
    
    def add_file(self, path, description, key_components=None, content=None):
        """Register a file that will be provided to the assistant."""
        file_info = {
            "path": path,
            "description": description,
            "key_components": key_components or []
        }
        self.files.append(file_info)
        
        # Count tokens for this file's manifest entry (metadata)
        manifest_text = f"- `{path}`: {description}"
        if key_components:
            manifest_text += "\n  Key components:\n" + "\n".join(f"  - {comp}" for comp in key_components)
        self.token_counts["files"]["metadata"] += count_tokens(manifest_text, self.model)
        
        # If content is provided, count its tokens
        if content:
            content_tokens = count_tokens(content, self.model)
            self.token_counts["files"]["content"][path] = content_tokens
            self.token_counts["total_content"] += content_tokens
            
        return self
    
    def add_convention(self, name, description):
        """Add a coding convention specific to this project."""
        convention = {"name": name, "description": description}
        self.conventions.append(convention)
        self.token_counts["conventions"] += count_tokens(f"{name}: {description}", self.model)
        return self
    
    def set_environment(self, env_type, details, description=None):
        """Describe the execution environment."""
        self.environment_info[env_type] = {"details": details, "description": description}
        self.token_counts["environment"] += count_tokens(f"{env_type}: {details}", self.model)
        return self
    
    def add_critical_pattern(self, pattern, explanation):
        """Document a pattern that should never be modified."""
        pattern_info = {"pattern": pattern, "explanation": explanation}
        self.critical_patterns.append(pattern_info)
        self.token_counts["patterns"] += count_tokens(f"{pattern}: {explanation}", self.model)
        return self
    
    def generate_xml(self):
        """Generate the XML manifest for the AI assistant."""
        manifest = ['<manifest>']
        
        # Files section with token counts
        files_section = ['<files>']
        for file in self.files:
            path = file['path']
            content_tokens = self.token_counts["files"]["content"].get(path, 0)
            file_type = self._get_file_type(path)
            file_content = [
                f"<path>{path}</path>",
                f"<description>{file['description']}</description>"
            ]
            
            if file_type:
                file_content.append(f"<file_type>{file_type}</file_type>")
                
            if file['key_components']:
                file_content.append(create_xml_element("key_components", [
                    f"<component>{comp}</component>" for comp in file['key_components']
            ]))
                
            file_content.append(f"<tokens>{content_tokens}</tokens>")
            files_section.append(create_xml_element("file", file_content))
        
        files_section.append('</files>')
        manifest.append("\n".join(files_section))
        
        # Environment details as simple detail elements
        if self.environment_info:
            for env_type, env_data in self.environment_info.items():
                if isinstance(env_data, dict):
                    details = env_data["details"]
                    description = env_data.get("description")
                else:
                    # Handle backward compatibility for old format
                    details = env_data
                    description = None
                
                detail_attrs = {"description": description} if description else None
                manifest.append(create_xml_element("detail", details, detail_attrs))
        
        # Conventions section
        if self.conventions:
            conv_section = ['<conventions>']
            for convention in self.conventions:
                conv_section.append(create_xml_element("convention", [
                    f"<name>{convention['name']}</name>",
                    f"<description>{convention['description']}</description>"
                ]))
            conv_section.append('</conventions>')
            manifest.append("\n".join(conv_section))
        
        # Critical patterns section
        if self.critical_patterns:
            patterns_section = ['<critical_patterns>']
            for pattern in self.critical_patterns:
                patterns_section.append(create_xml_element("pattern", [
                    f"<pattern>{pattern['pattern']}</pattern>",
                    f"<explanation>{pattern['explanation']}</explanation>"
                ]))
            patterns_section.append('</critical_patterns>')
            manifest.append("\n".join(patterns_section))
        
        # Token usage summary
        token_section = ['<token_usage>']
        token_section.append(create_xml_element("files", [
            f"<metadata>{self.token_counts['files']['metadata']}</metadata>",
            create_xml_element("content", [
                create_xml_element("file", [
                    f"<path>{path}</path>",
                    f"<tokens>{tokens}</tokens>"
                ]) for path, tokens in self.token_counts["files"]["content"].items()
            ]),
            f"<total>{self.token_counts['total_content']}</total>"
        ]))
        token_section.append('</token_usage>')
        manifest.append("\n".join(token_section))
        
        manifest.append('</manifest>')
        result = "\n".join(manifest)
        # Clean up any remaining double newlines
        result = result.replace('\n\n', '\n')
        return result
    
    def _load_xsd_schema(self):
        """Load the XSD schema file for embedding in the manifest."""
        try:
            # Look for the XSD file in the helpers directory
            xsd_path = os.path.join(os.path.dirname(__file__), 'pipulate-context.xsd')
            if not os.path.exists(xsd_path):
                # Fallback: look relative to repo root
                xsd_path = os.path.join(repo_root, 'helpers', 'pipulate-context.xsd')
            
            if os.path.exists(xsd_path):
                with open(xsd_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Warning: XSD schema not found at {xsd_path}")
                return None
        except Exception as e:
            print(f"Warning: Could not load XSD schema: {e}")
            return None
    
    def _get_file_type(self, path):
        """Get file type based on extension for better LLM context"""
        ext = os.path.splitext(path)[1].lower()
        if ext:
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.md': 'markdown',
                '.json': 'json',
                '.nix': 'nix',
                '.sh': 'bash',
                '.txt': 'text'
            }
            return lang_map.get(ext, 'text')
        return None
    
    def generate(self):
        """Generate the manifest for the AI assistant (legacy format)."""
        return self.generate_xml()  # Default to XML format

def create_pipulate_manifest(file_paths_with_comments):
    """Create a manifest specific to the Pipulate project."""
    manifest = AIAssistantManifest()
    
    # Track total tokens and processed files to respect limit and avoid duplicates
    total_tokens = 0
    max_tokens = MAX_TOKENS - TOKEN_BUFFER
    processed_files = set()
    result_files = []
    
    # Define the environment
    # Combine Python/Nix environment details
    environment_details = "Python 3.12 in a Nix-managed virtualenv (.venv). Hybrid approach using Nix flakes for system dependencies + pip for Python packages."
    manifest.set_environment("Development Environment", environment_details, description="environment")
    # Add the raw FILES_TO_INCLUDE content for context
    manifest.set_environment("Files Selection", "Below is the raw FILES_TO_INCLUDE content before any processing:\n\n" + FILES_TO_INCLUDE_RAW, description="story")
    
    # Check for missing files and collect them
    missing_files = []
    for file_path, comment in file_paths_with_comments:
        file_path = file_path.strip()
        if not file_path:
            continue
            
        full_path = os.path.join(repo_root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path):
            missing_files.append(full_path)
    
    # If any files are missing, raise an exception with clear details
    if missing_files:
        error_message = "The following files were not found:\n"
        for missing_file in missing_files:
            error_message += f"  - {missing_file}\n"
        error_message += "\nPlease check the file paths in FILES_TO_INCLUDE variable."
        print(error_message)
        sys.exit(1)
    
    # Register key files with their contents and comments
    for file_path, comment in file_paths_with_comments:
        file_path = file_path.strip()
        if not file_path or file_path in processed_files:
            continue
            
        processed_files.add(file_path)
        result_files.append((file_path, comment))  # Store both path and comment
        full_path = os.path.join(repo_root, file_path) if not os.path.isabs(file_path) else file_path
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                content_tokens = count_tokens(content)
                
                # Check if adding this file would exceed token limit
                if total_tokens + content_tokens > max_tokens:
                    description = f"{os.path.basename(file_path)} [skipped: would exceed token limit]"
                    if comment:
                        description += f" - {comment}"
                    manifest.add_file(
                        file_path,
                        description
                    )
                    continue
                
                total_tokens += content_tokens
                description = f"{os.path.basename(file_path)} [loaded]"
                if comment:
                    description += f" - {comment}"
                
                # Add file to manifest
                manifest.add_file(
                    file_path,
                    description,
                    content=content
                )
                
        except UnicodeDecodeError as e:
            print(f"ERROR: Could not decode {full_path}: {e}")
            sys.exit(1)  # Exit with error code for encoding issues
        except Exception as e:
            print(f"ERROR: Could not read {full_path}: {e}")
            sys.exit(1)  # Exit with error code for any other exceptions
    
    # Add conventions and patterns only if we have room
    remaining_tokens = max_tokens - total_tokens
    if remaining_tokens > 1000:  # Arbitrary threshold for metadata
        manifest.add_convention(
            "FastHTML Rendering", 
            "All FastHTML objects must be converted with to_xml() before being returned in HTTP responses"
        )
        
        manifest.add_convention(
            "Environment Activation", 
            "Always run 'nix develop' in new terminals before any other commands"
        )
        
        manifest.add_convention(
            "Dependency Management",
            "System deps go in flake.nix, Python packages in requirements.txt"
        )
        
        manifest.add_critical_pattern(
            "to_xml(ft_object)",
            "Required to convert FastHTML objects to strings before HTTP responses"
        )
        
        manifest.add_critical_pattern(
            "HTMLResponse(str(to_xml(rendered_item)))",
            "Proper pattern for returning FastHTML content with HTMX triggers"
        )
    
    # Return the manifest content WITHOUT the outer <manifest> tags
    manifest_xml = manifest.generate()
    # Remove opening and closing manifest tags to prevent double wrapping
    if manifest_xml.startswith('<manifest>') and manifest_xml.endswith('</manifest>'):
        manifest_xml = manifest_xml[len('<manifest>'):-len('</manifest>')]
    
    return manifest_xml, result_files, total_tokens

# Add a function to copy text to clipboard
def copy_to_clipboard(text):
    """Copy text to system clipboard."""
    try:
        # For Linux
        import subprocess
        process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        return True
    except Exception as e:
        print(f"Warning: Could not copy to clipboard: {e}")
        print("Make sure xclip is installed (sudo apt-get install xclip)")
        return False

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate context file with selectable prompt templates and token limits.')
parser.add_argument('-t', '--template', type=int, default=0, help='Template index to use (default: 0)')
parser.add_argument('-l', '--list', action='store_true', help='List available templates')
parser.add_argument('-o', '--output', type=str, default="foo.txt", help='Output filename (default: foo.txt)')
parser.add_argument('-m', '--max-tokens', type=int, default=MAX_TOKENS - TOKEN_BUFFER, 
                    help=f'Maximum tokens to include (default: {MAX_TOKENS - TOKEN_BUFFER:,})')
parser.add_argument('-p', '--prompt', type=str, help='Path to a prompt file to use (default: prompt.md in current directory)')
parser.add_argument('--cat', action='store_true',
                    help='Shortcut for concat mode with blog posts, outputs a single file')
parser.add_argument('--concat-mode', action='store_true', 
                    help='Use concatenation mode similar to cat_foo.py')
parser.add_argument('-d', '--directory', type=str, default=".",
                    help='Target directory for concat mode (default: current directory)')
parser.add_argument('--chunk', type=int,
                    help='Process specific chunk number (default: process all chunks)')
parser.add_argument('--compress', action='store_true',
                    help='Compress output files using gzip')
parser.add_argument('--single', action='store_true',
                    help=f'Force single file output with {MAX_TOKENS - TOKEN_BUFFER:,} token limit')
parser.add_argument('--model', choices=['gemini15', 'gemini25', 'claude', 'gpt4'], default='claude',
                    help='Set target model (default: claude)')
parser.add_argument('--repo-root', type=str, default=repo_root,
                    help=f'Repository root directory (default: {repo_root})')
parser.add_argument('--no-clipboard', action='store_true', help='Disable copying output to clipboard')
parser.add_argument('--files', action='store_true', 
                    help='Generate FILES_TO_INCLUDE_RAW content by enumerating directories')

args = parser.parse_args()

# Update repo_root if specified via command line
if args.repo_root and args.repo_root != repo_root:
    repo_root = args.repo_root
    print(f"Repository root directory set to: {repo_root}")

# Generate files list if requested
if args.files:
    from generate_files_list import main as generate_main
    generate_main()
    sys.exit(0)

# List available templates if requested
if args.list:
    print("Available prompt templates:")
    for i, template in enumerate(prompt_templates):
        print(f"{i}: {template['name']}")
    sys.exit(0)

# Get the file list with comments
final_file_list = get_files_with_comments() if '--files' not in sys.argv else []  # Start with the default list

# Handle prompt file - now with default prompt.md behavior
prompt_path = args.prompt
prompt_content = None
direct_prompt = None  # New variable to store direct string prompts

if prompt_path:
    # Check if the prompt is a file path or direct string
    if os.path.exists(prompt_path):
        # It's a file path
        if not os.path.isabs(prompt_path):
            prompt_path = os.path.join(os.getcwd(), prompt_path)
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            print(f"Using prompt file: {prompt_path}")
        except Exception as e:
            print(f"Error reading prompt file {prompt_path}: {e}")
            sys.exit(1)
    else:
        # It's a direct string prompt
        direct_prompt = prompt_path  # Store the direct string
        prompt_content = prompt_path
        print("Using direct string prompt")
else:
    # If no prompt specified, look for prompt.md in current directory
    prompt_path = os.path.join(os.getcwd(), "prompt.md")
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            print(f"Using default prompt file: {prompt_path}")
        except Exception as e:
            print(f"Error reading default prompt file: {e}")
            sys.exit(1)
    else:
        print("No prompt file specified and prompt.md not found in current directory.")
        print("Running without a prompt file.")

if prompt_content:
    # Add prompt file to files list if not already present
    if prompt_path and os.path.exists(prompt_path):
        # Check if this file path is already in the list
        existing_paths = [file_path for file_path, comment in final_file_list]
        if prompt_path not in existing_paths:
            final_file_list.append((prompt_path, "User prompt file"))
    
    # Use article analysis template by default for prompt files
    args.template = 1  # Use the material analysis template

# If --cat is used, set concat mode and blog posts directory
if args.cat:
    args.concat_mode = True
    args.directory = "/home/mike/repos/MikeLev.in/_posts"  # Set blog posts directory
    if not args.output:  # Only set default if no output specified
        args.output = "foo.txt"  # Set default output for blog posts to .txt
    args.single = True  # Force single file output when using --cat

# Set the template index and output filename
template_index = args.template if 0 <= args.template < len(prompt_templates) else 0
output_filename = args.output

# Set the pre and post prompts from the selected template
pre_prompt = prompt_templates[template_index]["pre_prompt"]
post_prompt = prompt_templates[template_index]["post_prompt"]

# Override post_prompt with direct string if provided
if direct_prompt:
    post_prompt = direct_prompt

print(f"Using template {template_index}: {prompt_templates[template_index]['name']}")

# Remove verbose file checking messages
if args.concat_mode:
    print(f"Directory being searched for markdown files: {args.directory}")
    print("NOTE: Only .md files in this directory will be processed.")

# Create the manifest and incorporate user's pre_prompt
manifest_xml, processed_files, manifest_tokens = create_pipulate_manifest(final_file_list)
manifest = manifest_xml

# Add the pre-prompt and separator (without duplicating manifest)
lines = [pre_prompt]
lines.append("=" * 20 + " START CONTEXT " + "=" * 20)
total_tokens = count_tokens(pre_prompt, "gpt-4")

# Process each file in the manifest file list
for file_path, comment in processed_files:
    full_path = os.path.join(repo_root, file_path) if not os.path.isabs(file_path) else file_path
    
    # Original detailed mode with markers, now including comments
    comment_suffix = f" -- {comment}" if comment else ""
    start_marker = f"# <<< START FILE: {full_path}{comment_suffix} >>>"
    end_marker = f"# <<< END FILE: {full_path}{comment_suffix} >>>"
    
    lines.append(start_marker)
    try:
        with open(full_path, 'r', encoding='utf-8') as infile:
            file_content = infile.read()
            file_tokens = count_tokens(file_content, "gpt-4")
            token_info = f"\n# File token count: {format_token_count(file_tokens)}"
            if comment:
                token_info += f"\n# File purpose: {comment}"
            lines.append(file_content + token_info)
    except Exception as e:
        error_message = f"# --- ERROR: Could not read file {full_path}: {e} ---"
        print(f"ERROR: Could not read file {full_path}: {e}")
        sys.exit(1)  # Exit with error code
    
    lines.append(end_marker)

# Add a separator and the post-prompt
lines.append("=" * 20 + " END CONTEXT " + "=" * 20)
post_prompt_tokens = count_tokens(post_prompt, "gpt-4")
if total_tokens + post_prompt_tokens <= args.max_tokens:
    total_tokens += post_prompt_tokens
    lines.append(post_prompt)
else:
    print("Warning: Post-prompt skipped as it would exceed token limit")

# Calculate the final token count
def calculate_total_tokens(files_tokens, prompt_tokens):
    """Calculate total tokens and component breakdowns"""
    file_tokens = sum(files_tokens.values())
    total = file_tokens + prompt_tokens
    return {
        "files": file_tokens,
        "prompt": prompt_tokens,
        "total": total
    }

def calculate_total_words(files_words, prompt_words):
    """Calculate total words and component breakdowns"""
    file_words = sum(files_words.values())
    total = file_words + prompt_words
    return {
        "files": file_words,
        "prompt": prompt_words,
        "total": total
    }

# Calculate total tokens and words with proper accounting
files_tokens_dict = {}
files_words_dict = {}
for file_path, comment in processed_files:
    try:
        full_path = os.path.join(repo_root, file_path) if not os.path.isabs(file_path) else file_path
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        files_tokens_dict[file_path] = count_tokens(content, "gpt-4")
        files_words_dict[file_path] = count_words(content)
    except Exception as e:
        print(f"ERROR: Could not count tokens/words for {file_path}: {e}")
        sys.exit(1)  # Exit with error code

# Calculate prompt tokens and words
pre_prompt_tokens = count_tokens(pre_prompt, "gpt-4")
post_prompt_tokens = count_tokens(post_prompt, "gpt-4") 
prompt_tokens = pre_prompt_tokens + post_prompt_tokens

pre_prompt_words = count_words(pre_prompt)
post_prompt_words = count_words(post_prompt)
prompt_words = pre_prompt_words + post_prompt_words

# Calculate totals
token_counts = calculate_total_tokens(files_tokens_dict, prompt_tokens)
word_counts = calculate_total_words(files_words_dict, prompt_words)

# Update the token summary in the output
token_summary_content = [
    f"<total_context_size>{format_token_count(token_counts['total'])}</total_context_size>",
    f"<files_tokens>{format_token_count(token_counts['files'])}</files_tokens>",
    f"<prompt_tokens>{format_token_count(prompt_tokens)}</prompt_tokens>"
]

output_xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
              f'<context schema="pipulate-context" version="1.0">\n'
              f'{create_xml_element("manifest", manifest)}\n'
              f'{create_xml_element("pre_prompt", pre_prompt)}\n'
              f'{create_xml_element("content", chr(10).join(lines))}\n'
              f'{create_xml_element("post_prompt", post_prompt)}\n'
              f'{create_xml_element("token_summary", token_summary_content)}\n'
              f'</context>')

# Print concise output
file_paths_only = [file_path for file_path, comment in processed_files]
print("\n--- Files Included ---")
# Parse the manifest to get token counts for each file
token_counts_dict = {}
try:
    if '<token_usage>' in manifest:
        token_usage_start = manifest.find('<token_usage>') + 12
        token_usage_end = manifest.find('</token_usage>')
        token_usage = manifest[token_usage_start:token_usage_end]
        
        if '<files>' in token_usage:
            files_start = token_usage.find('<files>') + 7
            files_end = token_usage.find('</files>', files_start)
            files_section = token_usage[files_start:files_end]
            
            if '<content>' in files_section:
                content_start = files_section.find('<content>') + 9
                content_end = files_section.find('</content>')
                content_section = files_section[content_start:content_end]
                
                # Extract file paths and token counts
                file_pattern = r'<file>.*?<path>(.*?)</path>.*?<tokens>(.*?)</tokens>.*?</file>'
                for match in re.finditer(file_pattern, content_section, re.DOTALL):
                    path, tokens = match.groups()
                    token_counts_dict[path.strip()] = int(tokens.strip())
except Exception as e:
    pass  # If parsing fails, just show files without token counts

for file_path in file_paths_only:
    tokens_str = f" ({token_counts_dict.get(file_path, 0):,} tokens)" if file_path in token_counts_dict else ""
    print(f"• {file_path}{tokens_str}")

print("\n--- Token Summary ---")
print(f"Total tokens: {format_token_count(token_counts['total'])}")
if word_counts['total'] is not None:
    print(f"Total words: {format_word_count(word_counts['total'])}")
    
    # Add size comparisons
    size_info = format_size_with_comparison(word_counts['total'], token_counts['total'])
    print(f"\nSize Perspective:")
    print(f"📝 Content size: {size_info['word_comparison']}")
    print(f"🤖 Token size: {size_info['token_comparison']}")
    
    # Calculate and show token-to-word ratio
    ratio = token_counts['total'] / word_counts['total'] if word_counts['total'] > 0 else 0
    print(f"📊 Token-to-word ratio: {ratio:.2f} (higher = more technical/structured content)")

print()

# Write the complete XML output to the file
try:
    with open(args.output, 'w', encoding='utf-8') as outfile:
        outfile.write(output_xml)
    print(f"Output written to '{args.output}'")
except Exception as e:
    print(f"Error writing to '{args.output}': {e}")

# By default, copy the output to clipboard unless --no-clipboard is specified
if not args.no_clipboard:
    if copy_to_clipboard(output_xml):
        print("Output copied to clipboard")

print("\nScript finished.")

# When creating the final output, use direct_prompt if available
if direct_prompt:
    post_prompt = direct_prompt  # Use the direct string instead of template XML


