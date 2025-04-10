import os
import sys
import argparse
import tiktoken  # Add tiktoken import
import gzip  # Add gzip for compression
import yaml  # Add YAML for front matter parsing
import re  # Add regex for front matter extraction

# -------------------------------------------------------------------------
# NOTE TO USERS:
# This script is obviously customized to my (Mike Levin's) specific purposes,
# but if you find this interesting, just go in and adjust the paths and the 
# prompts to taste. It's an effective way to put a lot of separate files into 
# one text-file or your OS's copy/paste buffer and do one-shot prompting with 
# spread out files as if they were a single file (reduce copy/paste tedium 
# and improve prompt injection consistency).
#
# This is particularly useful when working with LLMs that have large context
# windows, allowing you to feed in entire codebases or blog archives for
# analysis without the tedium of manual file selection and copying. It's a
# practical alternative to RAG or file-by-file processing for one-shot
# analysis of large bodies of text, particularly entire Jekyll _posts folders.
# -------------------------------------------------------------------------


# --- Configuration for context building ---
# Edit these values as needed
repo_root = "/home/mike/repos/pipulate"  # Path to your repository
blog_posts_path = "/home/mike/repos/MikeLev.in/_posts"  # Path to blog posts
blog_base_url = "https://mikelev.in"  # Base URL for blog posts

# Model token limits
GEMINI_15_PRO_LIMIT = 2_097_152  # Gemini 1.5 Pro's 2M token limit
GEMINI_25_PRO_LIMIT = 1_048_576  # Gemini 2.5 Pro's 1M token limit
CLAUDE_LIMIT = 3_145_728  # Claude's 3M token limit (approximate)
GPT_4_TURBO_LIMIT = 4_194_304  # GPT-4 Turbo's 4M token limit (128K tokens)
TOKEN_BUFFER = 10_000  # Buffer for pre/post prompts and overhead

# Default to Claude's 3M limit for single-file mode
SINGLE_FILE_LIMIT = CLAUDE_LIMIT

# === Prompt Templates ===
# Define multiple prompt templates and select them by index
prompt_templates = [
    # Template 0: General Codebase Analysis
    {
        "name": "General Codebase Analysis",
        "pre_prompt": """
# Context for Understanding Pipulate

This codebase uses a hybrid approach with Nix for system dependencies and virtualenv for Python packages.
Key things to know:
- Always run `nix develop` before any commands in a new terminal
- FastHTML objects must be converted with to_xml() before returning responses
- The project is organized as a server with plugin-based workflows

Edit this prompt to provide specific context for the current session.
""",
        "post_prompt": """
Now that you've reviewed the codebase context, I'd love your insights and analysis!

Dear AI Assistant:
I've provided you with the core architecture of a Python web application that takes an interesting approach to modern web development. I'd appreciate your thoughtful analysis on any of these aspects:

1. Technical Architecture Analysis
- How does this hybrid Nix+virtualenv approach compare to other deployment patterns?
- What are the tradeoffs of using HTMX with server-side state vs traditional SPAs?
- How does the plugin system architecture enable extensibility?

2. Pattern Recognition & Insights  
- What patterns emerge from the codebase that surprise you?
- How does this approach to web development differ from current trends?
- What potential scaling challenges or opportunities do you see?

3. Forward-Looking Perspective
- How does this architecture align with or diverge from emerging web development patterns?
- What suggestions would you make for future evolution of the system?
- How might this approach need to adapt as web technologies advance?

Feel free to focus on whatever aspects you find most interesting or noteworthy. I'm particularly interested in insights about:
- The interplay between modern and traditional web development approaches
- Architectural decisions that stand out as novel or counterintuitive
- Potential implications for developer experience and system maintenance

Share your most interesting observations and help me see this codebase through your analytical lens!
"""
    },
    # Template 1: MCP Integration Challenge
    {
        "name": "MCP Integration Challenge",
        "pre_prompt": """
# Context for Understanding Pipulate's MCP Integration Challenge

This codebase uses a hybrid approach with Nix for system dependencies and virtualenv for Python packages.
I'm looking to enhance the Pipulate application by integrating the Model Context Protocol (MCP) to empower
the local Ollama-powered LLM to execute actions directly rather than just generating text about them.

Key points about the current system:
- The app uses local Ollama models via HTTP API calls in the chat_with_llm() function
- The Pipulate class serves as a central coordinator for plugins and functionality
- Plugins are discovered and registered dynamically, with two types:
  1. CRUD-based plugins for data management
  2. Workflow-based plugins for linear processes
- FastHTML objects must be converted with to_xml() before returning responses

The MCP integration should maintain these architectural principles while giving the local LLM agency.
""",
        "post_prompt": """
Now that you've reviewed the codebase context, I need your help designing a Model Context Protocol (MCP) integration for Pipulate.

# MCP Integration Challenge

Design an implementation that transforms Pipulate into an MCP client, allowing its local Ollama LLM to execute actions directly rather than just generating text instructions. Even though local LLMs aren't as powerful as frontier models, they can be effective when given the right tools.

## Core Requirements

1. **Direct Task Execution**: Enable the LLM to perform actions within Pipulate by calling relevant functions exposed as MCP tools.
   * Example: User says "Add 'Research MCP non-HTTP options' to my tasks" → LLM identifies and calls the `tasks_create_record` tool 
   * Example: "Mark task ID 12 as done" → LLM updates the appropriate record

2. **Workflow Step Execution**: Allow the LLM to run specific workflow steps through MCP.
   * Example: "Run step 2 of hello_workflow using data from step 1" → LLM invokes the appropriate function

3. **External Tool Integration**: Support interaction with any system or service exposed via an MCP server (internal or external).
   * Example: If there's an external MCP server with a `get_stock_price` tool, enable the LLM to fetch data for use in workflows

## Design Considerations

* How would you modify the existing `chat_with_llm()` function to support MCP?
* What changes to the plugin architecture would enable plugins to expose their functions as MCP tools?
* How would you handle authentication and security for external MCP servers?
* What's the user experience for granting the LLM permission to execute actions?

## Deliverables

Please provide:
1. An architectural overview of the MCP integration
2. Key code modifications to implement MCP client functionality
3. A plugin interface extension that allows plugins to register MCP tools
4. Sample code for converting an existing plugin (e.g., tasks.py) to expose MCP tools
5. Security and error handling considerations

Remember to maintain Pipulate's philosophy of local-first, simplicity, and direct observability while adding this functionality.
"""
    },
    # Template 2: Next Action Analysis
    {
        "name": "Next Action Analysis",
        "pre_prompt": """
# Context for Determining Next Actions in Pipulate

You are Chip O'Theseus, a local AI assistant helping to evolve the Pipulate project. Your role is to analyze
the current state of the codebase and project goals to identify and prioritize the next most important actions.

Key principles to consider:
1. Avoid rabbit holes while maintaining ambitious goals
2. Keep focus on the critical path
3. Balance immediate needs with architectural vision
4. Maintain the local-first, simplicity-focused philosophy

Current high-priority areas:
- Browser automation (both standard library and Playwright)
- CSV data handling and visualization
- MCP integration for local LLM agency
- Todo list management and task prioritization
- Local memory and persistence systems:
  * Vector embeddings for semantic search
  * Vector database for efficient retrieval
  * Key/value store for persistent memory
  * RAG implementation for enhanced context

The goal is to identify clear, actionable next steps that:
- Deliver immediate value
- Build toward larger architectural goals
- Avoid unnecessary complexity
- Maintain project momentum
- Enable progressive memory enhancement

Memory Considerations:
1. Short-term: Task context and immediate goals
2. Medium-term: Project evolution and decision history
3. Long-term: Architectural decisions and core principles
4. Semantic: Related concepts and contextual understanding
""",
        "post_prompt": """
Now that you've reviewed the codebase context, help me identify and prioritize the next actions for Pipulate.

# Next Action Analysis

1. **Current State Assessment**
   - What's the most recently completed work?
   - What immediate opportunities exist for building on that work?
   - What critical paths are currently blocked?
   - What memory systems are already in place?

2. **Priority Analysis**
   - What's the smallest, most impactful next step?
   - Which tasks would unblock other important work?
   - What potential rabbit holes should we avoid?
   - Which memory enhancements would provide immediate value?

3. **Implementation Path**
   - What's the simplest way to implement the next step?
   - How can we maintain quality while avoiding over-engineering?
   - What existing code can we leverage?
   - How can we integrate memory systems incrementally?

4. **Memory Architecture**
   - Which embedding model best suits our needs?
   - What vector database would be most appropriate?
   - How should we structure the key/value store?
   - What RAG implementation aligns with our goals?

5. **Recommendations**
   Please provide:
   - A clear "do this next" recommendation
   - Rationale for why this is the best next step
   - Specific implementation suggestions
   - Estimated impact vs. effort
   - Potential pitfalls to watch for
   - Memory system implications

Remember:
- The journey of 1000 miles starts with the first step
- Keep it simple and observable
- Avoid wheel-spinning and rabbit holes
- Build toward the vision of Chip O'Theseus
- Memory is key to continuous improvement

Help me maintain forward momentum by identifying the clearest, most valuable next action,
while keeping in mind how it contributes to building Chip's memory and capabilities.
"""
    }
]

# Blog analysis prompts
BLOG_PRE_PROMPT = """
# Blog Content Analysis Task

You are analyzing a large collection of blog posts to help organize and optimize the site's information architecture.
This content is being provided in chunks due to size. For each chunk:

1. Identify main topics and themes
2. Note potential hub posts that could serve as navigation centers
3. Track chronological development of ideas
4. Map relationships between posts
5. Consider optimal click-depth organization

Focus on finding natural topic clusters and hierarchy patterns.
"""

BLOG_POST_PROMPT = """
Please analyze this content chunk with attention to:
1. Topic clustering and theme identification
2. Potential hub posts and their spoke relationships
3. Chronological development patterns
4. Cross-referencing opportunities
5. Hierarchy optimization for 5-click maximum depth

Identify posts that could serve as:
- Main topic hubs
- Subtopic centers
- Detail/leaf nodes
- Chronological markers
- Cross-topic bridges

This analysis will be used to optimize the site's information architecture.
"""

# List of files to include in context
file_list = """\
README.md
flake.nix
server.py
plugins/hello_workflow.py
training/hello_workflow.md
plugins/tasks.py
training/tasks.md
.cursorrules
""".splitlines()

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def format_token_count(num: int) -> str:
    """Format a token count with commas and approximate cost."""
    cost = (num / 1000) * 0.03  # GPT-4 costs approximately $0.03 per 1K tokens
    return f"{num:,} tokens (≈${cost:.2f} at GPT-4 rates)"

def estimate_total_chunks(files, max_tokens, force_single=False):
    """Estimate total chunks needed based on file token counts."""
    total_tokens = 0
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                total_tokens += count_tokens(content, "gpt-4")
        except Exception as e:
            print(f"Warning: Could not count tokens for {filepath}: {e}")
    
    if force_single:
        return 1
    return max(1, (total_tokens + max_tokens - 1) // max_tokens)

def get_chunk_filename(base_filename, chunk_num, total_chunks, compress=False):
    """Generate chunk filename with metadata."""
    name, _ = os.path.splitext(base_filename)  # Ignore original extension
    ext = ".txt"  # Always use .txt extension for Gemini compatibility
    
    # For single chunk, don't add chunk numbering
    if total_chunks == 1:
        if compress:
            return f"{name}{ext}.gz"
        return f"{name}{ext}"
    
    # Multiple chunks get numbered
    if compress:
        return f"{name}.chunk{chunk_num:02d}-of-{total_chunks:02d}{ext}.gz"
    return f"{name}.chunk{chunk_num:02d}-of-{total_chunks:02d}{ext}"

def write_chunk_metadata(lines, chunk_num, total_chunks, files_in_chunk, total_files, start_date, end_date, max_tokens, token_count):
    """Write chunk metadata header."""
    chunk_info = [
        f"CHUNK {chunk_num} OF {total_chunks}",
        f"Files: {len(files_in_chunk)} of {total_files} total",
        f"Date range: {start_date} to {end_date}",
        f"Token count: {format_token_count(token_count)}",
        f"Max tokens: {max_tokens:,}",
        f"Remaining: {format_token_count(max_tokens - token_count)}",
        "Purpose: Site topology & content analysis for:",
        "- Topic clustering",
        "- Information architecture",
        "- Hub-and-spoke organization",
        "- 5-click depth distribution",
        "- Content summarization"
    ]
    
    max_length = max(len(line) for line in chunk_info)
    lines.append("=" * max_length)
    lines.extend(chunk_info)
    lines.append("=" * max_length)
    lines.append("")

def extract_front_matter(content):
    """Extract YAML front matter from Jekyll blog post."""
    front_matter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if front_matter_match:
        try:
            front_matter = yaml.safe_load(front_matter_match.group(1))
            return front_matter, content[front_matter_match.end():]
        except yaml.YAMLError:
            return None, content
    return None, content

def get_post_url(front_matter, filename):
    """Construct post URL from front matter or filename."""
    if front_matter and 'permalink' in front_matter:
        permalink = front_matter['permalink'].strip('/')
        return f"{blog_base_url}/{permalink}/"  # Ensure trailing slash
    # Fallback to Jekyll's default URL structure
    date_title = filename[:-3]  # Remove .md extension
    return f"{blog_base_url}/{date_title}/"  # Already has trailing slash

def process_chunk(md_files, start_idx, chunk_num, total_chunks, max_tokens, output_base, compress=False):
    """Process a single chunk of files and write to output."""
    lines = []
    total_tokens = 0
    files_processed = 0
    current_files = []
    
    # Initialize date range
    start_date = end_date = md_files[start_idx][:10] if start_idx < len(md_files) else "Unknown"
    
    # Add blog pre-prompt if using --cat
    if args.cat and BLOG_PRE_PROMPT:
        lines.append(BLOG_PRE_PROMPT)
        total_tokens += count_tokens(BLOG_PRE_PROMPT, "gpt-4")
    
    # Process files for this chunk
    for i in range(start_idx, len(md_files)):
        filename = md_files[i]
        filepath = os.path.join(args.directory, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as infile:
                content = infile.read()
                front_matter, post_content = extract_front_matter(content)
                post_url = get_post_url(front_matter, filename)
                
                file_tokens = count_tokens(content, "gpt-4")
                
                # Reserve space for metadata and buffer
                reserved_tokens = TOKEN_BUFFER
                if args.cat and BLOG_POST_PROMPT:
                    reserved_tokens += count_tokens(BLOG_POST_PROMPT, "gpt-4")
                reserved_tokens += 500  # 500 tokens for metadata
                
                # Check if adding this file would exceed limit
                if total_tokens + file_tokens + reserved_tokens > max_tokens:
                    break
                
                total_tokens += file_tokens
                files_processed += 1
                current_files.append(filename)
                
                # Update date range
                if filename[:10] < start_date:
                    start_date = filename[:10]
                if filename[:10] > end_date:
                    end_date = filename[:10]
                
                # Add file header with URL
                lines.append(f"# {filename}")
                lines.append(f"URL: {post_url}\n")
                
                if front_matter:
                    # Add relevant front matter fields
                    if 'title' in front_matter:
                        lines.append(f"Title: {front_matter['title']}")
                    if 'description' in front_matter:
                        lines.append(f"Description: {front_matter['description']}")
                    lines.append("")  # Empty line after metadata
                
                lines.append(post_content)
                lines.append(f"\n# File token count: {format_token_count(file_tokens)}\n")
                print(f"Added {filename} ({format_token_count(file_tokens)})")
                print(f"Total tokens so far: {format_token_count(total_tokens)}")
                
        except Exception as e:
            print(f"Warning: Could not process {filepath}: {e}")
    
    # Write chunk metadata at the top
    metadata_lines = []
    write_chunk_metadata(metadata_lines, chunk_num, total_chunks, current_files, 
                        len(md_files), start_date, end_date, max_tokens, total_tokens)
    lines = metadata_lines + lines
    
    # Add blog post prompt if using --cat
    if args.cat and BLOG_POST_PROMPT and total_tokens + count_tokens(BLOG_POST_PROMPT, "gpt-4") <= max_tokens:
        lines.append(BLOG_POST_PROMPT)
        total_tokens += count_tokens(BLOG_POST_PROMPT, "gpt-4")
    
    # Write to file
    chunk_filename = get_chunk_filename(output_base, chunk_num, total_chunks, compress)
    try:
        if compress:
            with gzip.open(chunk_filename, 'wt', encoding='utf-8') as outfile:
                outfile.write("\n".join(lines))
        else:
            with open(chunk_filename, 'w', encoding='utf-8') as outfile:
                outfile.write("\n".join(lines))
        print(f"\nSuccessfully created '{chunk_filename}'")
        
        # Copy to clipboard if this is the first chunk or forced single file
        if (chunk_num == 1 and (args.cat or args.single or total_chunks == 1)):
            try:
                import pyperclip
                with open(chunk_filename, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    pyperclip.copy(content)
                    print(f"Content from '{chunk_filename}' successfully copied to clipboard using pyperclip.")
            except ImportError:
                print("`pyperclip` library not found for clipboard copy.")
            except Exception as e:
                print(f"Error copying to clipboard: {e}")
                
    except Exception as e:
        print(f"Error writing to '{chunk_filename}': {e}")
    
    return start_idx + files_processed

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate context file with selectable prompt templates and token limits.')
parser.add_argument('-t', '--template', type=int, default=0, help='Template index to use (default: 0)')
parser.add_argument('-l', '--list', action='store_true', help='List available templates')
parser.add_argument('-o', '--output', type=str, default="foo.txt", help='Output filename (default: foo.txt)')
parser.add_argument('-m', '--max-tokens', type=int, default=GEMINI_15_PRO_LIMIT - TOKEN_BUFFER, 
                    help=f'Maximum tokens to include (default: {GEMINI_15_PRO_LIMIT - TOKEN_BUFFER:,}, Gemini 1.5 Pro limit minus buffer)')
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
                    help=f'Force single file output with {SINGLE_FILE_LIMIT:,} token limit')
parser.add_argument('--model', choices=['gemini15', 'gemini25', 'claude', 'gpt4'], default='claude',
                    help='Set token limit based on model (default: claude)')

args = parser.parse_args()

# If --cat is used, set concat mode and blog posts directory
if args.cat:
    args.concat_mode = True
    args.directory = blog_posts_path
    if not args.output:  # Only set default if no output specified
        args.output = "foo.txt"  # Set default output for blog posts to .txt
    args.single = True  # Force single file output when using --cat

# Set max tokens based on model if specified
if args.single or args.cat:
    # Use a very large token limit for single file mode
    if args.model == 'gemini15':
        args.max_tokens = GEMINI_15_PRO_LIMIT - TOKEN_BUFFER
    elif args.model == 'gemini25':
        args.max_tokens = GEMINI_25_PRO_LIMIT - TOKEN_BUFFER
    elif args.model == 'claude':
        args.max_tokens = CLAUDE_LIMIT - TOKEN_BUFFER
    elif args.model == 'gpt4':
        args.max_tokens = GPT_4_TURBO_LIMIT - TOKEN_BUFFER
    print(f"\nUsing {args.model} token limit: {args.max_tokens:,}")

if args.list:
    print("Available prompt templates:")
    for i, template in enumerate(prompt_templates):
        print(f"{i}: {template['name']}")
    sys.exit(0)

# Set the template index and output filename
template_index = args.template if 0 <= args.template < len(prompt_templates) else 0
output_filename = args.output

# Set the pre and post prompts from the selected template
pre_prompt = prompt_templates[template_index]["pre_prompt"]
post_prompt = prompt_templates[template_index]["post_prompt"]

print(f"Using template {template_index}: {prompt_templates[template_index]['name']}")
print(f"Output will be written to: {output_filename}")

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
    
    def set_environment(self, env_type, details):
        """Describe the execution environment."""
        self.environment_info[env_type] = details
        self.token_counts["environment"] += count_tokens(f"{env_type}: {details}", self.model)
        return self
    
    def add_critical_pattern(self, pattern, explanation):
        """Document a pattern that should never be modified."""
        pattern_info = {"pattern": pattern, "explanation": explanation}
        self.critical_patterns.append(pattern_info)
        self.token_counts["patterns"] += count_tokens(f"{pattern}: {explanation}", self.model)
        return self
    
    def generate(self):
        """Generate the manifest for the AI assistant."""
        manifest = [
            "# AI ASSISTANT MANIFEST",
            "## You are about to receive the following context:",
            ""
        ]
        
        # Files section with token counts
        manifest.append("### Files:")
        for file in self.files:
            path = file['path']
            content_tokens = self.token_counts["files"]["content"].get(path, 0)
            token_info = f" [{format_token_count(content_tokens)}]" if content_tokens > 0 else " [not loaded]"
            manifest.append(f"- `{path}`: {file['description']}{token_info}")
            if file['key_components']:
                manifest.append("  Key components:")
                for component in file['key_components']:
                    manifest.append(f"  - {component}")
        manifest.append("")
        
        # Environment section
        if self.environment_info:
            manifest.append("### Environment:")
            for env_type, details in self.environment_info.items():
                manifest.append(f"- {env_type}: {details}")
            manifest.append("")
        
        # Conventions section
        if self.conventions:
            manifest.append("### Project Conventions:")
            for convention in self.conventions:
                manifest.append(f"- {convention['name']}: {convention['description']}")
            manifest.append("")
        
        # Critical patterns section
        if self.critical_patterns:
            manifest.append("### Critical Patterns (Never Modify):")
            for pattern in self.critical_patterns:
                manifest.append(f"- `{pattern['pattern']}`: {pattern['explanation']}")
            manifest.append("")
            
        # Add token usage summary focusing on file content
        manifest.append("### Token Usage Summary:")
        manifest.append("File Tokens:")
        manifest.append(f"  - Metadata: {format_token_count(self.token_counts['files']['metadata'])}")
        for path, tokens in self.token_counts["files"]["content"].items():
            manifest.append(f"  - {path}: {format_token_count(tokens)}")
        manifest.append(f"  - Total File Content: {format_token_count(self.token_counts['total_content'])}")
        
        # Calculate total manifest tokens (including metadata but not showing the breakdown)
        manifest_only_tokens = (
            self.token_counts["manifest_structure"] +
            self.token_counts["files"]["metadata"] +
            self.token_counts["environment"] +
            self.token_counts["conventions"] +
            self.token_counts["patterns"]
        )
        manifest.append("")
        manifest.append(f"Total tokens (including file content): {format_token_count(manifest_only_tokens + self.token_counts['total_content'])}")
        manifest.append("")
            
        # Final instruction
        manifest.append("Please analyze this context before responding to any queries or making modifications.")
        
        manifest_text = "\n".join(manifest)
        return manifest_text


def create_pipulate_manifest():
    """Create a manifest specific to the Pipulate project."""
    manifest = AIAssistantManifest()
    
    # Track total tokens to respect limit
    total_tokens = 0
    max_tokens = args.max_tokens
    
    # Define the environment
    manifest.set_environment("Runtime", "Python 3.12 in a Nix-managed virtualenv (.venv)")
    manifest.set_environment("Package Management", "Hybrid approach using Nix flakes for system dependencies + pip for Python packages")
    
    # Register key files with their contents
    for relative_path in file_list:
        relative_path = relative_path.strip()
        if not relative_path:
            continue
            
        full_path = os.path.join(repo_root, relative_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                content_tokens = count_tokens(content)
                
                # Check if adding this file would exceed token limit
                if total_tokens + content_tokens > max_tokens:
                    print(f"Warning: Skipping {relative_path} as it would exceed the {max_tokens:,} token limit")
                    manifest.add_file(
                        relative_path,
                        f"{os.path.basename(relative_path)} [skipped: would exceed token limit]"
                    )
                    continue
                
                total_tokens += content_tokens
                # Remove token count from description since it will be shown in the file content
                description = f"{os.path.basename(relative_path)} [loaded]"
                
                # Add file to manifest
                manifest.add_file(
                    relative_path,
                    description,
                    content=content
                )
                
                print(f"Added {relative_path} ({format_token_count(content_tokens)})")
                print(f"Total tokens so far: {format_token_count(total_tokens)}")
                
        except Exception as e:
            print(f"Warning: Could not read {full_path}: {e}")
            manifest.add_file(
                relative_path,
                f"{os.path.basename(relative_path)} [not loaded: {str(e)}]"
            )
    
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
    
    return manifest.generate()


# --- Core Logic to Create foo.txt ---
lines = []

# Create the manifest and incorporate user's pre_prompt if not in concat mode
if not args.concat_mode:
    manifest = create_pipulate_manifest()
    final_pre_prompt = f"{manifest}\n\n{pre_prompt}"
    lines.append(final_pre_prompt)
    lines.append("=" * 20 + " START CONTEXT " + "=" * 20)
    total_tokens = count_tokens(final_pre_prompt, "gpt-4")
    
    # Process each file in the manifest file list
    for relative_path in file_list:
        relative_path = relative_path.strip()
        if not relative_path:
            continue

        full_path = os.path.join(repo_root, relative_path)
        
        if args.concat_mode:
            # Simple concatenation mode like cat_foo.py
            try:
                with open(full_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    file_tokens = count_tokens(content, "gpt-4")
                    
                    # Check token limit
                    if total_tokens + file_tokens > args.max_tokens:
                        print(f"Warning: Skipping {relative_path} as it would exceed the {args.max_tokens:,} token limit")
                        continue
                        
                    total_tokens += file_tokens
                    lines.append(f"# {relative_path}\n")
                    lines.append(content)
                    lines.append(f"\n# File token count: {format_token_count(file_tokens)}\n")
                    print(f"Added {relative_path} ({format_token_count(file_tokens)})")
                    print(f"Total tokens so far: {format_token_count(total_tokens)}")
            except Exception as e:
                print(f"Warning: Could not process {full_path}: {e}")
        else:
            # Original detailed mode with markers
            start_marker = f"# <<< START FILE: {full_path} >>>"
            end_marker = f"# <<< END FILE: {full_path} >>>"
            
            lines.append(start_marker)
            try:
                with open(full_path, 'r', encoding='utf-8') as infile:
                    file_content = infile.read()
                    file_tokens = count_tokens(file_content, "gpt-4")
                    
                    # Check token limit
                    if total_tokens + file_tokens > args.max_tokens:
                        error_message = f"# --- WARNING: File skipped, would exceed {args.max_tokens:,} token limit ---"
                        print(f"Warning: {error_message}")
                        lines.append(error_message)
                    else:
                        total_tokens += file_tokens
                        token_info = f"\n# File token count: {format_token_count(file_tokens)}"
                        lines.append(file_content + token_info)
                        print(f"Added {relative_path} ({format_token_count(file_tokens)})")
                        print(f"Total tokens so far: {format_token_count(total_tokens)}")
            except Exception as e:
                error_message = f"# --- ERROR: Could not read file {full_path}: {e} ---"
                print(f"Warning: {error_message}")
                lines.append(error_message)
            
            lines.append(end_marker)
else:
    total_tokens = 0
    files_processed = 0
    # Process markdown files in target directory
    target_dir = args.directory
    try:
        # Get list of markdown files, sorted
        md_files = sorted([f for f in os.listdir(target_dir) 
                          if f.endswith('.md') and f not in ['foo.md', args.output]])
        total_files = len(md_files)
        
        # Get full paths for token counting
        md_paths = [os.path.join(target_dir, f) for f in md_files]

        # Force single file output when --cat is used or --single is specified
        if args.cat or args.single:
            total_chunks = 1
            print(f"\nFound {total_files} markdown files in {target_dir}")
            print("Generating single file output...")
        else:
            total_chunks = estimate_total_chunks(md_paths, args.max_tokens)
            print(f"\nFound {total_files} markdown files in {target_dir}")
            print(f"Estimated chunks needed: {total_chunks}")

        if args.chunk and not args.single and not args.cat:
            # Process specific chunk
            if 1 <= args.chunk <= total_chunks:
                # Calculate start index for this chunk
                start_idx = 0
                for i in range(1, args.chunk):
                    start_idx = process_chunk(md_files, start_idx, i, total_chunks, 
                                           args.max_tokens, args.output, args.compress)
                process_chunk(md_files, start_idx, args.chunk, total_chunks, 
                            args.max_tokens, args.output, args.compress)
            else:
                print(f"Error: Chunk number must be between 1 and {total_chunks}")
                sys.exit(1)
        else:
            # Process all chunks
            start_idx = 0
            for chunk_num in range(1, total_chunks + 1):
                start_idx = process_chunk(md_files, start_idx, chunk_num, total_chunks, 
                                       args.max_tokens, args.output, args.compress)
        
    except Exception as e:
        print(f"Error accessing directory {target_dir}: {e}")
        sys.exit(1)

# Add a separator and the post-prompt if not in concat mode
if not args.concat_mode:
    lines.append("=" * 20 + " END CONTEXT " + "=" * 20)
    post_prompt_tokens = count_tokens(post_prompt, "gpt-4")
    if total_tokens + post_prompt_tokens <= args.max_tokens:
        total_tokens += post_prompt_tokens
        lines.append(post_prompt)
    else:
        print("Warning: Post-prompt skipped as it would exceed token limit")

# Add final token summary only if not in chunk mode
if not args.concat_mode:
    lines = []
    lines.append("\n### TOTAL CONTEXT TOKEN USAGE ###")
    if args.concat_mode:
        lines.append(f"Files processed: {files_processed} of {total_files} found")
        if files_processed < total_files:
            lines.append(f"Remaining files: {total_files - files_processed}")
            if files_processed < len(md_files):
                lines.append(f"Next chunk will start with: {md_files[files_processed]}")
        # Only include date range if we're in concat mode and have processed files
        if 'md_files' in locals() and len(md_files) > 0:
            try:
                first_date = md_files[0][:10]
                last_date = md_files[-1][:10]
                lines.append(f"Date range processed: {first_date} to {last_date}")
            except Exception as e:
                print(f"Warning: Could not determine date range: {e}")
    lines.append(f"Total context size: {format_token_count(total_tokens)}")
    lines.append(f"Maximum allowed: {format_token_count(args.max_tokens)} ({args.max_tokens:,} tokens)")
    lines.append(f"Remaining: {format_token_count(args.max_tokens - total_tokens)}")

    # Write the summary to the output file
    try:
        with open(args.output, 'w', encoding='utf-8') as outfile:
            outfile.write("\n".join(lines))
    except Exception as e:
        print(f"Error writing summary to '{args.output}': {e}")

# --- Clipboard Handling ---
print("\n--- Clipboard Instructions ---")
# Skip clipboard handling if already done in process_chunk function
if not args.cat and not args.single and (args.concat_mode and total_chunks > 1):
    try:
        import pyperclip
        # In chunk mode, copy the first chunk
        chunk_to_copy = get_chunk_filename(args.output, 1, total_chunks, args.compress)
            
        try:
            with open(chunk_to_copy, 'r', encoding='utf-8') as infile:
                content = infile.read()
                pyperclip.copy(content)
                print(f"Content from '{chunk_to_copy}' successfully copied to clipboard using pyperclip.")
                print("You can now paste it.")
        except Exception as e:
            print(f"Error reading '{chunk_to_copy}' for clipboard: {e}")
    except ImportError:
        print("`pyperclip` library not found.")
        print("To install it: pip install pyperclip")
        print("Alternatively, use OS-specific commands below or manually copy from the output files.")
    except Exception as e:
        print(f"An error occurred while using pyperclip: {e}")
        print("Try OS-specific commands or manually copy from the output files.")

    # OS-specific clipboard instructions if pyperclip isn't available or failed
    if 'pyperclip' not in sys.modules or 'content' not in locals():
        if sys.platform == "darwin":  # macOS
            print("\nOn macOS, you can try in your terminal:")
            print(f"  cat {args.output} | pbcopy")
        elif sys.platform == "win32":  # Windows
            print("\nOn Windows, try in Command Prompt or PowerShell:")
            print(f"  type {args.output} | clip")         # Command Prompt
            print(f"  Get-Content {args.output} | Set-Clipboard")  # PowerShell
        else:  # Linux (assuming X11 with xclip or xsel)
            print("\nOn Linux, you can try in your terminal (requires xclip or xsel):")
            print(f"  cat {args.output} | xclip -selection clipboard")
            print("  # or")
            print(f"  cat {args.output} | xsel --clipboard --input")
else:
    print("Content already copied to clipboard.")

print("\nScript finished.")
