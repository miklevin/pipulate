import os
import sys
import argparse
import tiktoken  # Add tiktoken import
import gzip  # Add gzip for compression
import yaml  # Add YAML for front matter parsing
import re  # Add regex for front matter extraction
from typing import Dict, List, Optional, Union

# ============================================================================
# USER CONFIGURATION: Files to include in context
# ============================================================================
# Edit this list to specify which files should be included in the context.
# Each file will be processed and its content will be made available to the AI.
# Files are processed in order, and token counts are tracked to stay within limits.
#
# Simply add or remove file paths, one per line. The backslash at the start
# allows for clean multi-line string formatting.

FILES_TO_INCLUDE = """\
README.md
flake.nix
server.py
plugins/20_hello_workflow.py
training/hello_workflow.md
plugins/30_tasks.py
training/tasks.md
.cursorrules
""".splitlines()[:-1]  # Remove the last empty line

# ============================================================================
# ARTICLE MODE CONFIGURATION
# ============================================================================
# Set these values to enable article analysis mode.
# When enabled, the script will include the specified article in the context
# and use specialized prompts for article analysis.

ARTICLE_MODE = False  # Set to True to enable article analysis mode
ARTICLE_PATH = "/home/mike/repos/MikeLev.in/_posts/your-article.md"  # Path to the article

# ============================================================================
# END USER CONFIGURATION
# ============================================================================

def print_structured_output(manifest, pre_prompt, files, post_prompt, total_tokens, max_tokens):
    """Print a structured view of the prompt components in markdown format."""
    print("\n=== Prompt Structure ===")
    
    print("\n--- Manifest ---")
    # Convert XML manifest to markdown
    manifest_lines = manifest.split('\n')
    for line in manifest_lines:
        try:
            if '<file' in line:
                # Extract file info more flexibly
                path_start = line.find('path="') + 6
                path_end = line.find('"', path_start)
                if path_start > 5 and path_end > path_start:
                    path = line[path_start:path_end]
                    tokens = "0"
                    tokens_start = line.find('tokens="')
                    if tokens_start > -1:
                        tokens_end = line.find('"', tokens_start + 8)
                        if tokens_end > tokens_start:
                            tokens = line[tokens_start + 8:tokens_end]
                    print(f"- {path} ({format_token_count(int(tokens))})")
            elif '<convention>' in line:
                name_start = line.find('<name>') + 6
                name_end = line.find('</name>')
                desc_start = line.find('<description>') + 12
                desc_end = line.find('</description>')
                if all(pos > -1 for pos in [name_start, name_end, desc_start, desc_end]):
                    name = line[name_start:name_end]
                    desc = line[desc_start:desc_end]
                    print(f"  • Convention: {name} - {desc}")
            elif '<pattern>' in line:
                pattern_start = line.find('<pattern>') + 9
                pattern_end = line.find('</pattern>')
                if pattern_start > 8 and pattern_end > pattern_start:
                    pattern = line[pattern_start:pattern_end]
                    print(f"  • Critical Pattern: {pattern}")
        except Exception as e:
            continue  # Skip lines that can't be parsed
    
    print("\n--- Pre-Prompt ---")
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
    for file in files:
        print(f"• {file}")
    
    print("\n--- Post-Prompt ---")
    # Handle post-prompt content
    try:
        if '<analysis_request>' in post_prompt:
            analysis_start = post_prompt.find('<analysis_request>') + 17
            analysis_end = post_prompt.find('</analysis_request>')
            if analysis_start > 16 and analysis_end > analysis_start:
                analysis_content = post_prompt[analysis_start:analysis_end]
                
                # Extract introduction
                if '<introduction>' in analysis_content:
                    intro_start = analysis_content.find('<introduction>') + 13
                    intro_end = analysis_content.find('</introduction>')
                    if intro_start > 12 and intro_end > intro_start:
                        print("Introduction:")
                        intro_content = analysis_content[intro_start:intro_end].strip()
                        # Remove any remaining XML tags and clean up formatting
                        intro_content = re.sub(r'<[^>]+>', '', intro_content)
                        intro_content = intro_content.replace('>', '')  # Remove any remaining > characters
                        print(f"  {intro_content}")
                
                # Extract analysis areas
                if '<analysis_areas>' in analysis_content:
                    areas_start = analysis_content.find('<analysis_areas>') + 15
                    areas_end = analysis_content.find('</analysis_areas>')
                    if areas_start > 14 and areas_end > areas_start:
                        areas_content = analysis_content[areas_start:areas_end]
                        print("\nAnalysis Areas:")
                        for area in areas_content.split('<area>'):
                            if area.strip():
                                area_end = area.find('</area>')
                                if area_end > -1:
                                    area_content = area[:area_end]
                                    if '<title>' in area_content:
                                        title_start = area_content.find('<title>') + 7
                                        title_end = area_content.find('</title>')
                                        if title_start > 6 and title_end > title_start:
                                            title = area_content[title_start:title_end].strip()
                                            # Remove any remaining XML tags
                                            title = re.sub(r'<[^>]+>', '', title)
                                            print(f"  • {title}")
                
                # Extract focus areas
                if '<focus_areas>' in analysis_content:
                    focus_start = analysis_content.find('<focus_areas>') + 12
                    focus_end = analysis_content.find('</focus_areas>')
                    if focus_start > 11 and focus_end > focus_start:
                        focus_content = analysis_content[focus_start:focus_end]
                        print("\nFocus Areas:")
                        for area in focus_content.split('<area>'):
                            if area.strip():
                                area_end = area.find('</area>')
                                if area_end > -1:
                                    area_content = area[:area_end].strip()
                                    # Remove any remaining XML tags
                                    area_content = re.sub(r'<[^>]+>', '', area_content)
                                    print(f"  • {area_content}")
    except Exception as e:
        print("  [Error parsing post-prompt content]")
    
    print("\n--- Token Summary ---")
    print(f"Total tokens: {format_token_count(total_tokens)}")
    print(f"Maximum allowed: {format_token_count(max_tokens)}")
    print(f"Remaining: {format_token_count(max_tokens - total_tokens)}")
    print("\n=== End Prompt Structure ===\n")

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

# --- XML Support Functions ---
def wrap_in_xml(content: str, tag_name: str, attributes: Optional[Dict[str, str]] = None) -> str:
    """Wrap content in XML tags with optional attributes."""
    attrs = " ".join(f'{k}="{v}"' for k, v in (attributes or {}).items())
    return f"<{tag_name}{' ' + attrs if attrs else ''}>\n{content}\n</{tag_name}>"

def create_xml_element(tag_name: str, content: Union[str, List[str]], attributes: Optional[Dict[str, str]] = None) -> str:
    """Create an XML element with optional attributes and content."""
    if isinstance(content, list):
        content = "\n".join(content)
    return wrap_in_xml(content, tag_name, attributes)

def create_xml_list(items: List[str], tag_name: str = "item") -> str:
    """Create an XML list from a list of items."""
    return "\n".join(f"<{tag_name}>{item}</{tag_name}>" for item in items)

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
        "pre_prompt": create_xml_element("context", [
            create_xml_element("system_info", """
This codebase uses a hybrid approach with Nix for system dependencies and virtualenv for Python packages.
Key things to know:
- Always run `nix develop` before any commands in a new terminal
- FastHTML objects must be converted with to_xml() before returning responses
- The project is organized as a server with plugin-based workflows
"""),
            create_xml_element("key_points", [
                "<point>Always run `nix develop` before any commands in a new terminal</point>",
                "<point>FastHTML objects must be converted with to_xml() before returning responses</point>",
                "<point>The project is organized as a server with plugin-based workflows</point>"
            ])
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
    # Template 1: Article Analysis Mode
    {
        "name": "Article Analysis Mode",
        "pre_prompt": create_xml_element("context", [
            create_xml_element("system_info", """
You are about to review a codebase in preparation for implementing changes requested in an article.
Please study and understand the codebase thoroughly, as you will need this context
to provide meaningful implementation suggestions based on the article's requirements.

Key things to know about this codebase:
- It uses a hybrid approach with Nix for system dependencies and virtualenv for Python packages
- Always run `nix develop` before any commands in a new terminal
- FastHTML objects must be converted with to_xml() before returning responses
- The project is organized as a server with plugin-based workflows
"""),
            create_xml_element("key_points", [
                "<point>Focus on understanding how the codebase currently implements related functionality</point>",
                "<point>Note any existing patterns that could be leveraged for the requested changes</point>",
                "<point>Consider how the requested changes would integrate with the current architecture</point>"
            ])
        ]),
        "post_prompt": create_xml_element("implementation_request", [
            create_xml_element("introduction", """
Now that you understand the codebase, please review the article's requirements and provide
specific implementation suggestions. Focus on how to modify the codebase to meet these requirements
while maintaining its architectural integrity and existing patterns.
"""),
            create_xml_element("implementation_areas", [
                create_xml_element("area", [
                    "<title>Required Changes</title>",
                    "<questions>",
                    "<question>What specific code changes are needed to implement the article's requirements?</question>",
                    "<question>Which existing components need to be modified or extended?</question>",
                    "<question>What new components or patterns need to be introduced?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Integration Strategy</title>",
                    "<questions>",
                    "<question>How should these changes be integrated with existing functionality?</question>",
                    "<question>What existing patterns or conventions should be followed?</question>",
                    "<question>How can we ensure backward compatibility?</question>",
                    "</questions>"
                ]),
                create_xml_element("area", [
                    "<title>Implementation Plan</title>",
                    "<questions>",
                    "<question>What's the recommended order for implementing these changes?</question>",
                    "<question>What are the key milestones or checkpoints?</question>",
                    "<question>What potential challenges or risks need to be addressed?</question>",
                    "</questions>"
                ])
            ]),
            create_xml_element("focus_areas", [
                "<area>Practical implementation of the article's requirements</area>",
                "<area>Maintenance of codebase integrity and patterns</area>",
                "<area>Clear, actionable implementation steps</area>"
            ])
        ])
    }
]

# Blog analysis prompts
BLOG_PRE_PROMPT = create_xml_element("blog_analysis", [
    create_xml_element("task_description", """
You are analyzing a large collection of blog posts to help organize and optimize the site's information architecture.
This content is being provided in chunks due to size. For each chunk:
"""),
    create_xml_element("analysis_requirements", [
        "<requirement>Identify main topics and themes</requirement>",
        "<requirement>Note potential hub posts that could serve as navigation centers</requirement>",
        "<requirement>Track chronological development of ideas</requirement>",
        "<requirement>Map relationships between posts</requirement>",
        "<requirement>Consider optimal click-depth organization</requirement>"
    ]),
    create_xml_element("focus", "Focus on finding natural topic clusters and hierarchy patterns.")
])

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

# Replace the old file_list definition with the new FILES_TO_INCLUDE
file_list = FILES_TO_INCLUDE

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
                
                # Create XML structure for the file
                file_xml = create_xml_element("file", [
                    create_xml_element("metadata", [
                        f"<filename>{filename}</filename>",
                        f"<url>{post_url}</url>",
                        create_xml_element("front_matter", [
                            f"<title>{front_matter.get('title', '')}</title>",
                            f"<description>{front_matter.get('description', '')}</description>"
                        ]) if front_matter else "",
                        f"<tokens>{file_tokens}</tokens>"
                    ]),
                    create_xml_element("content", post_content)
                ])
                
                lines.append(file_xml)
                print(f"Added {filename} ({format_token_count(file_tokens)})")
                print(f"Total tokens so far: {format_token_count(total_tokens)}")
                
        except Exception as e:
            print(f"Warning: Could not process {filepath}: {e}")
    
    # Create XML structure for the chunk
    chunk_xml = create_xml_element("chunk", [
        create_xml_element("metadata", [
            f"<chunk_number>{chunk_num}</chunk_number>",
            f"<total_chunks>{total_chunks}</total_chunks>",
            f"<files_processed>{len(current_files)}</files_processed>",
            f"<total_files>{len(md_files)}</total_files>",
            f"<date_range>{start_date} to {end_date}</date_range>",
            f"<token_count>{total_tokens}</token_count>",
            f"<max_tokens>{max_tokens}</max_tokens>",
            f"<remaining_tokens>{max_tokens - total_tokens}</remaining_tokens>"
        ]),
        create_xml_element("purpose", [
            "<purpose>Site topology & content analysis for:</purpose>",
            "<item>Topic clustering</item>",
            "<item>Information architecture</item>",
            "<item>Hub-and-spoke organization</item>",
            "<item>5-click depth distribution</item>",
            "<item>Content summarization</item>"
        ]),
        create_xml_element("content", "\n".join(lines))
    ])
    
    # Add blog post prompt if using --cat
    if args.cat and BLOG_POST_PROMPT and total_tokens + count_tokens(BLOG_POST_PROMPT, "gpt-4") <= max_tokens:
        chunk_xml += "\n" + BLOG_POST_PROMPT
        total_tokens += count_tokens(BLOG_POST_PROMPT, "gpt-4")
    
    # Write to file
    chunk_filename = get_chunk_filename(output_base, chunk_num, total_chunks, compress)
    try:
        if compress:
            with gzip.open(chunk_filename, 'wt', encoding='utf-8') as outfile:
                outfile.write(chunk_xml)
        else:
            with open(chunk_filename, 'w', encoding='utf-8') as outfile:
                outfile.write(chunk_xml)
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
parser.add_argument('--article-mode', action='store_true', help='Enable article analysis mode')
parser.add_argument('--article-path', type=str, help='Path to the article for analysis')
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

# Handle article mode
if args.article_mode:
    if args.article_path:
        ARTICLE_PATH = args.article_path
    if not os.path.exists(ARTICLE_PATH):
        print(f"Error: Article file not found at {ARTICLE_PATH}")
        sys.exit(1)
    # Add article to files list
    FILES_TO_INCLUDE.append(ARTICLE_PATH)
    # Use article analysis template
    args.template = 1  # Use the article analysis template

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
    
    def generate_xml(self):
        """Generate the XML manifest for the AI assistant."""
        manifest = ['<manifest>']
        
        # Files section with token counts
        files_section = ['<files>']
        for file in self.files:
            path = file['path']
            content_tokens = self.token_counts["files"]["content"].get(path, 0)
            token_info = f" tokens='{content_tokens}'" if content_tokens > 0 else ""
            files_section.append(create_xml_element("file", [
                f"<path>{path}</path>",
                f"<description>{file['description']}</description>",
                create_xml_element("key_components", [
                    f"<component>{comp}</component>" for comp in file['key_components']
                ]) if file['key_components'] else ""
            ], {"tokens": str(content_tokens)} if content_tokens > 0 else None))
        files_section.append('</files>')
        manifest.append("\n".join(files_section))
        
        # Environment section
        if self.environment_info:
            env_section = ['<environment>']
            for env_type, details in self.environment_info.items():
                env_section.append(create_xml_element("setting", [
                    f"<type>{env_type}</type>",
                    f"<details>{details}</details>"
                ]))
            env_section.append('</environment>')
            manifest.append("\n".join(env_section))
        
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
        return "\n".join(manifest)
    
    def generate(self):
        """Generate the manifest for the AI assistant (legacy format)."""
        return self.generate_xml()  # Default to XML format


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
    # Create the manifest and incorporate user's pre_prompt if not in concat mode
    manifest = create_pipulate_manifest()
    final_pre_prompt = f"{manifest}\n\n{pre_prompt}"
    
    # Create XML structure for the entire output
    output_xml = create_xml_element("context", [
        create_xml_element("manifest", manifest),
        create_xml_element("pre_prompt", pre_prompt),
        create_xml_element("content", "\n".join(lines)),
        create_xml_element("post_prompt", post_prompt),
        create_xml_element("token_summary", [
            f"<total_context_size>{format_token_count(total_tokens)}</total_context_size>",
            f"<maximum_allowed>{format_token_count(args.max_tokens)} ({args.max_tokens:,} tokens)</maximum_allowed>",
            f"<remaining>{format_token_count(args.max_tokens - total_tokens)}</remaining>"
        ])
    ])
    
    # Print structured output
    print_structured_output(manifest, pre_prompt, file_list, post_prompt, total_tokens, args.max_tokens)
    
    # Write the complete XML output to the file
    try:
        with open(args.output, 'w', encoding='utf-8') as outfile:
            outfile.write(output_xml)
    except Exception as e:
        print(f"Error writing to '{args.output}': {e}")

# --- Clipboard Handling ---
print("\n--- Clipboard Instructions ---")
try:
    import pyperclip
    # Copy the complete XML content to clipboard
    pyperclip.copy(output_xml)
    print(f"Complete XML content successfully copied to clipboard using pyperclip.")
    print("You can now paste it.")
except ImportError:
    print("`pyperclip` library not found.")
    print("To install it: pip install pyperclip")
    print("Alternatively, use OS-specific commands below or manually copy from the output files.")
except Exception as e:
    print(f"An error occurred while using pyperclip: {e}")
    print("Try OS-specific commands or manually copy from the output files.")

# OS-specific clipboard instructions if pyperclip isn't available or failed
if 'pyperclip' not in sys.modules:
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

print("\nScript finished.")
