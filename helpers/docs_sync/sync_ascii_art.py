#!/usr/bin/env python3
"""
Sync ASCII Art - One Command to Rule Them All

Updates all ASCII art blocks from pipulate/README.md to Pipulate.com
Walks through all markdown files and updates any markers it finds.

🚨 FEYNMAN SAFEGUARD: Built-in pollution detection prevents sync operations
when corrupted markers are detected, preventing exponential multiplication.

📋 README.md AUTO-COPY: Source documentation automatically synced to website
preserving original content exactly (no YAML headers, no transformations).

Usage: 
  python helpers/docs_sync/sync_ascii_art.py                    # Normal sync + README copy with pollution protection
  python helpers/docs_sync/sync_ascii_art.py --dry-run          # Preview changes without modifying files
  python helpers/docs_sync/sync_ascii_art.py --prompt           # Analysis mode for AI assistants
  python helpers/docs_sync/sync_ascii_art.py --verbose          # Include detailed pattern matching info
  python helpers/docs_sync/sync_ascii_art.py --force-pollution-override  # 🚨 Emergency bypass (dangerous!)

Safety Features:
  • Global pollution scan before any operations
  • Detects multiple START/END markers for same block
  • Detects orphaned, consecutive, or nested markers
  • Hard stop with detailed recovery instructions
  • Emergency override for advanced users only
"""

import os
import re
import sys
from pathlib import Path


def extract_key_from_headline(headline):
    """Extract key from headline, preferring comment-key if present"""
    # Check for comment-key first: <!-- key: some-key-name -->
    comment_key_match = re.search(r'<!--\s*key:\s*([^>]+)\s*-->', headline)
    if comment_key_match:
        return comment_key_match.group(1).strip()
    
    # Fallback to slugify if no comment-key found
    return slugify(headline)

def slugify(text):
    """Convert title to URL-friendly slug"""
    # Remove ### prefix and clean up
    text = re.sub(r'^#+\s*', '', text)
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    return re.sub(r'[\s-]+', '-', text)

def clean_footer_delimiters(footer):
    """Remove common section delimiters from footer content"""
    if not footer:
        return footer
    
    # Common delimiters that mark section boundaries
    delimiters = [
        r'^-{50,}$',           # 50+ hyphens (like --------------------------------------------------------------------------------)
        r'^={50,}$',           # 50+ equals signs
        r'^#{1,6}\s+.+$',      # Next markdown headline (### Title)
        r'^\*{50,}$',          # 50+ asterisks
        r'^---+$',             # 3+ hyphens (markdown horizontal rule)
        r'^===+$',             # 3+ equals (another horizontal rule style)
    ]
    
    lines = footer.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check if this line matches any delimiter pattern
        is_delimiter = False
        for delimiter_pattern in delimiters:
            if re.match(delimiter_pattern, line_stripped, re.MULTILINE):
                is_delimiter = True
                break
        
        # If we hit a delimiter, stop processing (exclude this line and everything after)
        if is_delimiter:
            break
            
        cleaned_lines.append(line)
    
    # Join back and strip any trailing whitespace
    cleaned_footer = '\n'.join(cleaned_lines).rstrip()
    return cleaned_footer

def extract_ascii_art_blocks(readme_content):
    """
    Extract ASCII art blocks from README.md content
    
    Returns dict with structure:
    {
        "title-slug": {
            "title": "Original Title",
            "header": "Content before ```",
            "art": "ASCII art content", 
            "footer": "Content after ```"
        }
    }
    """
    blocks = {}
    
    # Split content into sections by headlines
    sections = re.split(r'^(#{1,6}\s+.+)$', readme_content, flags=re.MULTILINE)
    
    for i in range(1, len(sections), 2):  # Process headline + content pairs
        if i + 1 >= len(sections):
            break
            
        headline = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        
        # Look for ``` code blocks in this section
        code_blocks = re.findall(r'```\n(.*?)\n```', content, re.DOTALL)
        
        if code_blocks:
            # Found ASCII art! Extract the components
            title = headline  # Preserve original markdown headline with ### level
            slug = extract_key_from_headline(headline)  # Use comment-key if present, otherwise slugify
            
            # Split content around the first code block
            pattern = r'```\n.*?\n```'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                header = content[:match.start()].strip()
                footer = content[match.end():].strip()
            else:
                header = content
                footer = ""
            
            # Clean up header (remove trailing colons, etc.)
            header = re.sub(r':$', '', header).strip()
            
            # Clean up footer - remove common delimiters that mark section boundaries
            footer = clean_footer_delimiters(footer)
            
            blocks[slug] = {
                "title": title,
                "header": header,
                "art": code_blocks[0],  # DON'T strip() - preserves leading/trailing whitespace
                "footer": footer
            }
    
    return blocks

def find_line_number(content, text):
    """Find the line number where text appears"""
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if text in line:
            return i
    return None

def show_pattern_match_details(content, marker, verbose=False):
    """Show detailed pattern matching information"""
    details = {}
    
    # Find START marker
    start_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->'
    start_match = re.search(start_pattern, content)
    if start_match:
        start_line = find_line_number(content, start_match.group(0))
        details['start_line'] = start_line
        details['start_match'] = start_match.group(0)
    
    # Find END marker  
    end_pattern = rf'<!-- END_ASCII_ART: {re.escape(marker)} -->'
    end_match = re.search(end_pattern, content)
    if end_match:
        end_line = find_line_number(content, end_match.group(0))
        details['end_line'] = end_line
        details['end_match'] = end_match.group(0)
    
    # Find the full block
    block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
    block_match = re.search(block_pattern, content, re.DOTALL)
    if block_match:
        details['block_found'] = True
        block_content = block_match.group(0)
        
        # Extract ASCII content
        art_pattern = r'```\n(.*?)\n```'
        art_match = re.search(art_pattern, block_content, re.DOTALL)
        if art_match:
            details['ascii_content'] = art_match.group(1)
            details['ascii_lines'] = len(art_match.group(1).split('\n'))
        else:
            details['ascii_content'] = None
            details['ascii_lines'] = 0
    else:
        details['block_found'] = False
    
    return details

def is_likely_ascii_art(content):
    """Check if content looks like ASCII art - now with more discriminating criteria"""
    if not content or len(content.strip()) < 20:
        return False
    
    lines = content.split('\n')
    if len(lines) < 3:
        return False
    
    # Look for ASCII art characters
    ascii_art_chars = ['│', '├', '└', '╔', '╗', '╚', '╝', '║', '═', '┌', '┐', '┘', '└', '─', '┼', 
                       '|', '+', '-', '/', '\\', '*', '#', '@', '═', '━', '┃', '┏', '┓', '┗', '┛']
    
    has_art_chars = any(char in content for char in ascii_art_chars)
    
    # Look for emoji patterns (strong indicator of modern ASCII art)
    emoji_pattern = r'[🎯🚀✨🔥💡📊🎨🏆⚡📝📄⚪❌✅🔄🌟💬🌐🍶📈🔍💤❓⚠️]'
    has_emojis = bool(re.search(emoji_pattern, content))
    
    # Look for visual structure but be more discriminating
    indent_levels = set(len(line) - len(line.lstrip()) for line in lines if line.strip())
    has_visual_structure = len(indent_levels) > 2  # Require more than 2 indent levels
    
    # Count ASCII art character occurrences (more chars = more likely to be ASCII art)
    art_char_count = sum(1 for char in content if char in ascii_art_chars)
    has_many_art_chars = art_char_count >= 10  # Require significant presence
    
    # MUCH MORE RESTRICTIVE: Require ASCII art chars AND (emojis OR structure OR many chars)
    # This eliminates most false positives while keeping real ASCII art
    return has_art_chars and (has_emojis or has_visual_structure or has_many_art_chars)

def find_heuristic_ascii_candidates(content, filename, known_ascii_blocks=None):
    """Find potential ASCII art in naked fenced code blocks using improved regex"""
    candidates = []
    
    # Create set of ASCII content that should be excluded
    managed_ascii_contents = set()
    
    # Add ASCII art blocks that are already managed in this file
    # Updated pattern to handle content between markers (title, description, etc.)
    ascii_marker_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->(.*?)<!-- END_ASCII_ART: [^>]+ -->'
    managed_matches = re.finditer(ascii_marker_pattern, content, re.DOTALL)
    for managed_match in managed_matches:
        # Extract all code blocks within the managed section
        managed_section = managed_match.group(2)
        code_blocks = re.findall(r'```\n(.*?)\n```', managed_section, re.DOTALL)
        for code_block in code_blocks:
            managed_ascii_contents.add(code_block.strip())
    
    # Also exclude ASCII art from our known synchronized blocks
    if known_ascii_blocks:
        for ascii_content in known_ascii_blocks.values():
            managed_ascii_contents.add(ascii_content.strip())
    
    # Improved regex pattern for naked fenced code blocks (no language identifier)
    # (?m): Multiline mode so ^ and $ match line boundaries
    # ^```(?![a-zA-Z0-9\-_]): Opening ``` at line start, negative lookahead excludes language identifiers
    # \s*$: Optional whitespace then end of line (no language specifier)
    # ([\s\S]*?): Capture content (lazy match for everything including newlines)
    # ^```\s*$: Closing ``` at line start with optional trailing whitespace
    pattern = r'(?m)^```(?![a-zA-Z0-9\-_])\s*$\n([\s\S]*?)\n^```\s*$'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        ascii_content_raw = match.group(1)  # Don't strip() - preserves leading/trailing whitespace  
        ascii_content_stripped = ascii_content_raw.strip()  # Use stripped version for comparisons
        
        # Skip if this ASCII art is already managed by markers
        if ascii_content_stripped in managed_ascii_contents:
            continue
        
        # Additional filtering: exclude blocks that contain programming language patterns
        if contains_programming_code(ascii_content_stripped):
            continue
            
        if is_likely_ascii_art(ascii_content_stripped):
            # Find line number where this block starts
            start_line = find_line_number(content, match.group(0))
            candidates.append({
                'content': ascii_content_raw,  # Store original with preserved whitespace
                'filename': filename,
                'start_line': start_line,
                'context': f"Found in naked fenced code block in {filename} (improved regex)"
            })
    
    return candidates

def detect_consecutive_markers(content, filename):
    """
    DEFENSIVE MEASURE #1: Detect consecutive ASCII art markers without content between them.
    
    This prevents silent failures where AI inserts markers like:
    <!-- START_ASCII_ART: block-name -->
    <!-- END_ASCII_ART: block-name -->
    
    With no placeholder content, sync_ascii_art.py cannot populate the block.
    """
    issues = []
    
    # Pattern to find consecutive START/END markers with only whitespace between
    consecutive_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->\s*\n\s*<!-- END_ASCII_ART: [^>]+ -->'
    
    matches = re.finditer(consecutive_pattern, content, re.MULTILINE)
    for match in matches:
        marker_name = match.group(1)
        start_line = find_line_number(content, match.group(0))
        
        issue = f"File {filename}, line {start_line}: Marker '{marker_name}' has no placeholder content between START/END markers"
        issues.append(issue)
    
    return issues

def detect_marker_pollution(content, filename):
    """
    🚨 FEYNMAN SAFEGUARD: "What if this valve fails?"
    
    COMPREHENSIVE MARKER POLLUTION DETECTION - The Choke-Point Defense
    
    This function detects ALL types of marker pollution that cause multiplication:
    1. Multiple START markers for the same block
    2. Multiple END markers for the same block  
    3. Consecutive markers without content
    4. Nested or overlapping markers
    5. Orphaned markers (START without END or vice versa)
    
    Returns: (is_polluted: bool, pollution_details: list)
    """
    pollution_issues = []
    
    # 1. DETECT MULTIPLE START MARKERS FOR SAME BLOCK
    start_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
    start_matches = re.findall(start_pattern, content)
    start_counts = {}
    for marker in start_matches:
        start_counts[marker] = start_counts.get(marker, 0) + 1
    
    for marker, count in start_counts.items():
        if count > 1:
            pollution_issues.append(f"POLLUTION: Multiple START markers for '{marker}' ({count} instances) in {filename}")
    
    # 2. DETECT MULTIPLE END MARKERS FOR SAME BLOCK
    end_pattern = r'<!-- END_ASCII_ART: ([^>]+) -->'
    end_matches = re.findall(end_pattern, content)
    end_counts = {}
    for marker in end_matches:
        end_counts[marker] = end_counts.get(marker, 0) + 1
    
    for marker, count in end_counts.items():
        if count > 1:
            pollution_issues.append(f"POLLUTION: Multiple END markers for '{marker}' ({count} instances) in {filename}")
    
    # 3. DETECT ORPHANED MARKERS (START without matching END or vice versa)
    all_start_markers = set(start_matches)
    all_end_markers = set(end_matches)
    
    orphaned_starts = all_start_markers - all_end_markers
    orphaned_ends = all_end_markers - all_start_markers
    
    for marker in orphaned_starts:
        pollution_issues.append(f"POLLUTION: Orphaned START marker for '{marker}' (no matching END) in {filename}")
    
    for marker in orphaned_ends:
        pollution_issues.append(f"POLLUTION: Orphaned END marker for '{marker}' (no matching START) in {filename}")
    
    # 4. DETECT CONSECUTIVE MARKERS (using existing function)
    consecutive_issues = detect_consecutive_markers(content, filename)
    for issue in consecutive_issues:
        pollution_issues.append(f"POLLUTION: {issue}")
    
    # 5. DETECT NESTED/OVERLAPPING MARKERS
    # Find all marker positions to check for overlaps
    all_markers = []
    
    for match in re.finditer(start_pattern, content):
        all_markers.append({
            'type': 'START',
            'marker': match.group(1),
            'position': match.start(),
            'text': match.group(0)
        })
    
    for match in re.finditer(end_pattern, content):
        all_markers.append({
            'type': 'END',
            'marker': match.group(1),
            'position': match.start(),
            'text': match.group(0)
        })
    
    # Sort by position to check for proper nesting
    all_markers.sort(key=lambda x: x['position'])
    
    # Stack-based validation for proper nesting
    marker_stack = []
    for marker_info in all_markers:
        if marker_info['type'] == 'START':
            marker_stack.append(marker_info['marker'])
        elif marker_info['type'] == 'END':
            if not marker_stack:
                pollution_issues.append(f"POLLUTION: Unexpected END marker for '{marker_info['marker']}' (no open START) in {filename}")
            elif marker_stack[-1] != marker_info['marker']:
                pollution_issues.append(f"POLLUTION: Mismatched markers - expected END for '{marker_stack[-1]}' but found '{marker_info['marker']}' in {filename}")
            else:
                marker_stack.pop()
    
    # Check for unclosed START markers
    for unclosed_marker in marker_stack:
        pollution_issues.append(f"POLLUTION: Unclosed START marker for '{unclosed_marker}' in {filename}")
    
    # Return pollution status
    is_polluted = len(pollution_issues) > 0
    return is_polluted, pollution_issues

def run_global_pollution_scan(markdown_files):
    """
    🚨 GLOBAL POLLUTION SCAN - The System-Wide Safety Check
    
    Scans ALL markdown files for marker pollution before allowing sync to proceed.
    This is the master choke-point that prevents sync when corruption is detected.
    
    Returns: (is_system_polluted: bool, all_pollution_issues: list, polluted_files: list)
    """
    all_pollution_issues = []
    polluted_files = []
    
    print("🔍 RUNNING GLOBAL POLLUTION SCAN (Feynman Safety Check)...")
    
    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = md_file.relative_to(md_file.parent.parent)
            is_polluted, pollution_issues = detect_marker_pollution(content, str(relative_path))
            
            if is_polluted:
                polluted_files.append(str(relative_path))
                all_pollution_issues.extend(pollution_issues)
                
        except Exception as e:
            pollution_issues = [f"ERROR: Could not scan {md_file}: {e}"]
            all_pollution_issues.extend(pollution_issues)
            polluted_files.append(str(md_file))
    
    is_system_polluted = len(all_pollution_issues) > 0
    
    if is_system_polluted:
        print(f"🚨 POLLUTION DETECTED: {len(polluted_files)} files have marker corruption")
    else:
        print("✅ POLLUTION SCAN CLEAN: No marker corruption detected")
    
    return is_system_polluted, all_pollution_issues, polluted_files

def contains_programming_code(content):
    """Check if content contains programming language patterns that indicate it's code, not ASCII art"""
    if not content:
        return False
    
    # Programming language indicators
    code_patterns = [
        # Language identifiers in nested code blocks
        r'```(python|javascript|js|typescript|ts|bash|shell|sh|java|c|cpp|go|rust|ruby|php|sql|html|css|xml|json|yaml|yml)',
        # Python-specific patterns
        r'\bdef\s+\w+\s*\(',  # function definitions
        r'\bclass\s+\w+',     # class definitions  
        r'\bimport\s+\w+',    # import statements
        r'\bfrom\s+\w+\s+import',  # from imports
        r'\breturn\s+',       # return statements
        r'\bif\s+.*:',        # if statements
        r'\bfor\s+.*\s+in\s+.*:',  # for loops
        r'\bwhile\s+.*:',     # while loops
        r'\btry\s*:',         # try blocks
        r'\bexcept\s*.*:',    # except blocks
        # JavaScript/TypeScript patterns
        r'\bfunction\s+\w+\s*\(',  # function declarations
        r'\bconst\s+\w+\s*=',      # const declarations
        r'\blet\s+\w+\s*=',        # let declarations
        r'\bvar\s+\w+\s*=',        # var declarations
        r'=>',                     # arrow functions
        # General programming patterns
        r'\w+\s*=\s*\w+\(',   # function calls
        r'\w+\.\w+\(',        # method calls
        r'#\s*[A-Z][A-Z_]+',  # comments (but allow # in ASCII art)
        r'//',                # comment lines
        r'<!--.*-->',         # HTML comments
        # Common programming constructs
        r'\{\s*$',            # opening braces at end of line
        r'^\s*\}',            # closing braces at start of line
        r';\s*$',             # semicolons at end of line
    ]
    
    # Check for multiple code indicators (reduces false positives)
    code_indicator_count = 0
    for pattern in code_patterns:
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            code_indicator_count += 1
            # If we find multiple strong code indicators, it's definitely code
            if code_indicator_count >= 2:
                return True
    
    # Single strong indicators that are definitive
    strong_indicators = [
        r'```(python|javascript|js|typescript|ts|bash|shell|sh|java|c|cpp|go|rust|ruby|php|sql)',
        r'\bdef\s+\w+\s*\(',
        r'\bclass\s+\w+\s*\(',
        r'\bfunction\s+\w+\s*\(',
        r'\bimport\s+\w+',
        r'\bfrom\s+\w+\s+import',
    ]
    
    for pattern in strong_indicators:
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            return True
    
    return False

def analyze_ascii_art_quality(ascii_content):
    """Analyze ASCII art to determine if it's worth promoting upstream"""
    if not ascii_content:
        return False, "No content"
    
    lines = ascii_content.split('\n')
    
    # Quality heuristics
    min_lines = 3
    min_width = 20
    has_ascii_art_chars = any(char in ascii_content for char in ['│', '├', '└', '╔', '╗', '╚', '╝', '║', '═', '┌', '┐', '┘', '└', '─', '┼', '|', '+', '-', '/', '\\', '*', '#', '@'])
    
    reasons = []
    score = 0
    
    if len(lines) >= min_lines:
        score += 2
        reasons.append(f"Good height ({len(lines)} lines)")
    
    if any(len(line.strip()) >= min_width for line in lines):
        score += 2 
        reasons.append(f"Good width (max {max(len(line.strip()) for line in lines)} chars)")
    
    if has_ascii_art_chars:
        score += 3
        reasons.append("Contains ASCII art characters")
    
    # Check for visual structure (indentation, alignment)
    indent_variety = len(set(len(line) - len(line.lstrip()) for line in lines if line.strip()))
    if indent_variety > 1:
        score += 1
        reasons.append("Has visual structure/indentation")
    
    # Check for emojis or unicode (modern ASCII art)
    emoji_pattern = r'[🎯🚀✨🔥💡📊🎨🏆⚡📝📄⚪❌✅🔄🌟💬🌐🍶📈🔍💤❓⚠️]'
    if re.search(emoji_pattern, ascii_content):
        score += 2
        reasons.append("Contains emojis/modern elements")
    
    # Quality threshold
    is_quality = score >= 4
    
    return is_quality, reasons

def suggest_placement_for_unused_blocks(unused_blocks, markdown_files, ascii_block_data):
    """Analyze content and suggest specific placements for unused ASCII art blocks"""
    placement_suggestions = {}
    
    # Define semantic keywords for each unused block to match against content
    block_keywords = {
        'breaking-free-framework-churn': [
            'framework', 'hamster wheel', 'churn', 'sovereignty', 'philosophy', 'approach', 'revolution',
            'freedom', 'empire', 'craftsmanship', 'rat race', 'sleep well', 'build tools that last',
            'choice', 'durable', 'lovable', 'tech stack', 'philosophy', 'why pipulate'
        ],
        'desktop-app-architecture-comparison': [
            'electron', 'desktop', 'application', 'architecture', 'browser', 'native', 'comparison',
            'vs', 'versus', 'install', 'how it works', 'technical', 'approach', 'nix', 'local',
            'single tenant', 'runs', 'environment'
        ],
        'the-lens-stack': [
            'lens', 'stack', 'architecture', 'technology', 'choices', 'aligned', 'focus', 'nix',
            'http', 'html', 'htmx', 'python', 'git', 'technical', 'framework', 'simple',
            'development', 'tools', 'grinding', 'burrs', 'focused'
        ],
        'ui-component-hierarchy': [
            'ui', 'component', 'hierarchy', 'interface', 'user interface', 'layout', 'design',
            'development', 'frontend', 'components', 'structure', 'web', 'html', 'workflow',
            'steps', 'form', 'button'
        ]
    }
    
    # Score each file for each unused block
    for block_key in unused_blocks:
        if block_key not in block_keywords:
            continue
            
        keywords = block_keywords[block_key]
        file_scores = []
        
        for md_file in markdown_files:
            relative_path = md_file.relative_to(md_file.parent.parent)
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                # Score based on keyword matches
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword.lower() in content:
                        score += 1
                        matched_keywords.append(keyword)
                
                # Bonus for specific high-value files
                if 'about.md' in str(relative_path):
                    score += 3  # About page is high-value for philosophy content
                elif 'index.md' in str(relative_path):
                    score += 2  # Homepage is high-value for key concepts
                elif 'development.md' in str(relative_path):
                    score += 2  # Development page for technical content
                elif 'install.md' in str(relative_path):
                    score += 1  # Install page for comparison content
                
                # Bonus for thematic matches in guide articles
                if '_guide/' in str(relative_path):
                    if 'local-first' in str(relative_path) and block_key == 'breaking-free-framework-churn':
                        score += 3
                    elif 'future-is-simple' in str(relative_path) and block_key == 'the-lens-stack':
                        score += 3
                    elif any(tech in str(relative_path) for tech in ['architecture', 'workflow']) and block_key == 'ui-component-hierarchy':
                        score += 2
                
                if score > 0:
                    file_scores.append({
                        'file': str(relative_path),
                        'score': score,
                        'matched_keywords': matched_keywords,
                        'reasons': []
                    })
                    
            except Exception as e:
                continue
        
        # Sort by score and take top suggestions
        file_scores.sort(key=lambda x: x['score'], reverse=True)
        top_suggestions = file_scores[:3]  # Top 3 suggestions per block
        
        # Add contextual reasons
        for suggestion in top_suggestions:
            reasons = []
            file_path = suggestion['file']
            
            if suggestion['score'] >= 5:
                reasons.append("Excellent thematic match")
            elif suggestion['score'] >= 3:
                reasons.append("Good content alignment")
            else:
                reasons.append("Moderate keyword match")
                
            if 'about.md' in file_path:
                reasons.append("High-impact about page")
            elif 'index.md' in file_path:
                reasons.append("Homepage visibility")
            elif 'development.md' in file_path:
                reasons.append("Technical documentation hub")
                
            if len(suggestion['matched_keywords']) >= 3:
                reasons.append(f"Multiple keyword matches ({len(suggestion['matched_keywords'])})")
                
            suggestion['reasons'] = reasons
        
        if top_suggestions:
            placement_suggestions[block_key] = top_suggestions
    
    return placement_suggestions

def main():
    """Main synchronization function with usage frequency and coverage analysis"""
    # Check for command-line arguments  
    verbose = "--verbose" in sys.argv
    prompt_mode = "--prompt" in sys.argv
    dry_run = "--dry-run" in sys.argv
    force_override = "--force-pollution-override" in sys.argv  # Emergency bypass
    
    if not prompt_mode:
        print("🚀 Syncing ASCII art from pipulate/README.md to Pipulate.com (with heuristic discovery)...")
    
    # Get ASCII blocks from README.md (adjusted for docs_sync subfolder)
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    ascii_block_data = extract_ascii_art_blocks(readme_content)
    
    # Build complete content blocks (title + header + art + footer)
    ascii_blocks = {}
    for key, data in ascii_block_data.items():
        # Reconstruct complete content block
        complete_content = []
        
        # Add title (preserve original markdown headline)
        if data['title']:
            complete_content.append(data['title'])
        
        # Add header content if present
        if data['header']:
            complete_content.append('')  # Empty line after title
            complete_content.append(data['header'])
        
        # Add ASCII art in code fences
        complete_content.append('')  # Empty line before code block
        complete_content.append('```')
        complete_content.append(data['art'])
        complete_content.append('```')
        
        # Add footer content if present
        if data['footer']:
            complete_content.append('')  # Empty line after code block
            complete_content.append(data['footer'])
        
        # Join with newlines and store
        ascii_blocks[key] = '\n'.join(complete_content)
    
    # Show extraction details with line numbers (skip in prompt mode)
    if not prompt_mode:
        for key, data in ascii_block_data.items():
            title = data['title']
            print(f"✅ Extracted: {title} -> {key}")
        
        print(f"✅ Found {len(ascii_blocks)} ASCII blocks in README.md")
    
    # Find Pipulate.com path (adjusted for docs_sync subfolder)
    pipulate_com_path = Path(__file__).parent.parent.parent / ".." / "Pipulate.com"
    
    # Find all markdown files
    markdown_files = []
    skip_dirs = {'.git', '_site', '.bundle', 'node_modules', '.gem', '.jekyll-cache'}
    
    for root, dirs, files in os.walk(pipulate_com_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(Path(root) / file)
    
    if not prompt_mode:
        print(f"🔍 Found {len(markdown_files)} markdown files")
    
    # 🚨 FEYNMAN SAFEGUARD: Run global pollution scan BEFORE any sync operations
    is_system_polluted, all_pollution_issues, polluted_files = run_global_pollution_scan(markdown_files)
    
    if is_system_polluted and not prompt_mode and not force_override:
        print(f"\n{'='*80}")
        print("🚨 SYNC OPERATION ABORTED - MARKER POLLUTION DETECTED")
        print(f"{'='*80}")
        print()
        print("🛑 CRITICAL SAFETY STOP: The sync process has been halted to prevent")
        print("   exponential content multiplication caused by corrupted ASCII art markers.")
        print()
        print(f"📊 POLLUTION SUMMARY:")
        print(f"   • Corrupted files: {len(polluted_files)}")
        print(f"   • Total issues: {len(all_pollution_issues)}")
        print()
        print(f"🔍 DETAILED POLLUTION REPORT:")
        for issue in all_pollution_issues:
            print(f"   ❌ {issue}")
        print()
        print(f"💡 RECOMMENDED RECOVERY ACTIONS:")
        print(f"   1. 🔄 ROLLBACK STRATEGY:")
        print(f"      cd /home/mike/repos/Pipulate.com")
        print(f"      git log --oneline -10  # Find clean commit before corruption")
        print(f"      git reset --hard <clean-commit-hash>")
        print(f"      git push --force-with-lease")
        print()
        print(f"   2. 🧹 MANUAL CLEANUP (Advanced):")
        print(f"      • Edit corrupted files to remove duplicate markers")
        print(f"      • Ensure each marker has exactly one START and one END")
        print(f"      • Add placeholder content between consecutive markers")
        print()
        print(f"   3. ✅ VERIFICATION:")
        print(f"      python helpers/docs_sync/sync_ascii_art.py --dry-run")
        print()
        print(f"   4. 🚨 EMERGENCY OVERRIDE (Use with extreme caution):")
        print(f"      python helpers/docs_sync/sync_ascii_art.py --force-pollution-override")
        print()
        print(f"🚀 Once pollution is cleared, normal sync operations will resume.")
        print(f"{'='*80}")
        
        # Exit with error code to prevent any further processing
        sys.exit(1)
    
    # Show override warning if pollution detected but overridden
    if is_system_polluted and force_override and not prompt_mode:
        print(f"\n⚠️  POLLUTION OVERRIDE ACTIVE - PROCEEDING WITH CAUTION")
        print(f"   🚨 {len(all_pollution_issues)} pollution issues detected but bypassed")
        print(f"   🎯 This may cause exponential content multiplication!")
        print(f"   📋 Use --dry-run first to assess potential damage")
        print()
    
    # Handle pollution reporting in prompt mode (don't exit, just report)
    if is_system_polluted and prompt_mode:
        print(f"\n🚨 MARKER POLLUTION DETECTED IN SYSTEM:")
        print(f"   • Corrupted files: {len(polluted_files)}")
        print(f"   • Total issues: {len(all_pollution_issues)}")
        for issue in all_pollution_issues[:5]:  # Show first 5 issues
            print(f"   ❌ {issue}")
        if len(all_pollution_issues) > 5:
            print(f"   ... and {len(all_pollution_issues) - 5} more issues")
        print(f"")
        print(f"⚠️  WARNING: Sync operations would be blocked due to pollution.")
        print(f"   Use rollback strategy or manual cleanup before attempting sync.")
        print(f"")
    
    if not prompt_mode:
        print("\n📁 Processing files:")
    
    total_updates = 0
    files_updated = 0
    heuristic_candidates = []  # Store heuristic ASCII art discoveries
    
    # Initialize frequency tracking
    usage_frequency = {marker: [] for marker in ascii_blocks.keys()}
    all_found_markers = set()
    unknown_marker_content = {}  # Store actual ASCII content for unknown markers
    
    # Process each file
    for md_file in sorted(markdown_files):
        relative_path = md_file.relative_to(pipulate_com_path)
        
        # Find ASCII markers in the file
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Scan for heuristic ASCII art candidates (always enabled)
        candidates = find_heuristic_ascii_candidates(content, str(relative_path), ascii_blocks)
        heuristic_candidates.extend(candidates)
        
        # Find all markers (corrected regex) - NEEDED FOR BOTH MODES
        marker_pattern = r'<!-- START_ASCII_ART: ([^>]+) -->'
        markers = re.findall(marker_pattern, content)
        
        # DEFENSIVE MEASURE #1: Detect consecutive markers without content
        consecutive_marker_issues = detect_consecutive_markers(content, str(relative_path))
        if consecutive_marker_issues and not prompt_mode:
            for issue in consecutive_marker_issues:
                print(f"🚨 CONSECUTIVE MARKER WARNING: {issue}")
        
        # Add to global tracking for prompt mode reporting
        if consecutive_marker_issues:
            if not hasattr(detect_consecutive_markers, 'global_issues'):
                detect_consecutive_markers.global_issues = []
            detect_consecutive_markers.global_issues.extend(consecutive_marker_issues)
        
        # Track usage frequency in BOTH modes (needed for coverage statistics)
        for marker in markers:
            all_found_markers.add(marker)
            if marker in ascii_blocks:
                usage_frequency[marker].append(str(relative_path))
        
        # Skip sync work in prompt mode - only collect candidates and usage stats
        if prompt_mode:
            continue
        
        if not markers:
            continue
        print(f"\n├── 📄 {relative_path}")
        file_had_updates = False
        
        for i, marker in enumerate(markers):
            # Use tree-style connectors
            is_last_marker = (i == len(markers) - 1)
            tree_connector = "└──" if is_last_marker else "├──"
            
            if marker in ascii_blocks:
                
                # Get detailed pattern matching info
                match_details = show_pattern_match_details(content, marker, verbose)
                
                # CRITICAL FIX: Clean up any existing duplicates FIRST
                block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
                
                # Find all instances of this block
                all_matches = list(re.finditer(block_pattern, content, re.DOTALL))
                
                if len(all_matches) > 1:
                    # DEDUPLICATION: Remove all but the first instance
                    print(f"    {tree_connector} 🧹 Deduplicating: {marker} (found {len(all_matches)} instances, keeping first)")
                    
                    # Sort matches by position (reverse order to avoid position shifts during removal)
                    sorted_matches = sorted(all_matches, key=lambda m: m.start(), reverse=True)
                    
                    # Remove all instances except the first (last in reverse-sorted list)
                    for match_to_remove in sorted_matches[:-1]:
                        content = content[:match_to_remove.start()] + content[match_to_remove.end():]
                    
                    # Re-find the remaining single block
                    block_match = re.search(block_pattern, content, re.DOTALL)
                    file_had_updates = True  # Mark file as needing update due to deduplication
                elif len(all_matches) == 1:
                    block_match = all_matches[0]
                else:
                    block_match = None
                
                if block_match:
                    current_block = block_match.group(0)
                    
                    # Extract current content between markers (excluding the markers themselves)
                    content_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->\n(.*?)\n<!-- END_ASCII_ART: {re.escape(marker)} -->'
                    content_match = re.search(content_pattern, current_block, re.DOTALL)
                    
                    if content_match:
                        current_content = content_match.group(1).strip()
                        new_content_block = ascii_blocks[marker]
                        
                        if current_content != new_content_block:
                            # Update needed!
                            replacement = f'<!-- START_ASCII_ART: {marker} -->\n{new_content_block}\n<!-- END_ASCII_ART: {marker} -->'
                            # Use lambda to avoid regex interpretation of backslashes in replacement
                            # CRITICAL FIX: count=1 prevents duplication multiplication when there are existing duplicates
                            new_content = re.sub(block_pattern, lambda m: replacement, content, count=1, flags=re.DOTALL)
                            
                            # Write the updated file
                            with open(md_file, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            if verbose and match_details['start_line']:
                                print(f"    {tree_connector} ✅ Updated: {marker} (lines {match_details['start_line']}-{match_details['end_line']})")
                            else:
                                print(f"    {tree_connector} ✅ Updated: {marker}")
                            total_updates += 1
                            file_had_updates = True
                            content = new_content  # Update content for next marker in same file
                        else:
                            if verbose and match_details['start_line']:
                                print(f"    {tree_connector} ⚪ No change: {marker} (lines {match_details['start_line']}-{match_details['end_line']}, {match_details['ascii_lines']} art lines)")
                            else:
                                print(f"    {tree_connector} ⚪ No change: {marker}")
                    else:
                        print(f"    {tree_connector} ⚠️  Malformed block: {marker} (no ASCII content found)")
                else:
                    print(f"    {tree_connector} ❌ Pattern match failed: {marker}")
            else:
                # Extract ASCII content from unknown markers for upstream analysis
                match_details = show_pattern_match_details(content, marker, verbose)
                
                ascii_content = match_details.get('ascii_content')
                if ascii_content:
                    unknown_marker_content[marker] = {
                        'content': ascii_content,
                        'file': str(relative_path),
                        'line_range': f"{match_details.get('start_line', '?')}-{match_details.get('end_line', '?')}",
                        'first_found': marker not in unknown_marker_content
                    }
                    
                if verbose and match_details.get('start_line'):
                    print(f"    {tree_connector} ❌ Block not found in README.md: {marker} (lines {match_details['start_line']}-{match_details['end_line']})")
                else:
                    print(f"    {tree_connector} ❌ Block not found in README.md: {marker}")
        
        if file_had_updates:
            files_updated += 1
    
    # Calculate coverage statistics (needed for both modes)
    used_blocks = {marker: files for marker, files in usage_frequency.items() if files}
    unused_blocks = {marker: files for marker, files in usage_frequency.items() if not files}
    unknown_markers = all_found_markers - set(ascii_blocks.keys())
    
    # Skip sync results in prompt mode
    if not prompt_mode:
        print(f"\n🎉 Sync complete!")
        print(f"   📊 Files updated: {files_updated}")
        print(f"   🔄 Total blocks updated: {total_updates}")
        
        if total_updates == 0:
            print("   ✨ All ASCII art was already up to date!")
        
        # 📋 COPY SOURCE README.md TO PIPULATE.COM ROOT
        readme_target_path = pipulate_com_path / "README.md"
        
        try:
            # Prepare cleaned content for comparison (strip ASCII art markers)
            cleaned_content = re.sub(
                r'<!-- START_ASCII_ART:.*?-->\n',
                '', 
                readme_content, 
                flags=re.MULTILINE
            )
            cleaned_content = re.sub(
                r'<!-- END_ASCII_ART:.*?-->\n',
                '', 
                cleaned_content, 
                flags=re.MULTILINE
            )
            
            # Check if update is needed
            readme_needs_update = True
            if readme_target_path.exists():
                with open(readme_target_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                readme_needs_update = (existing_content != cleaned_content)
            
            if readme_needs_update:
                if not dry_run:
                    # Copy README.md with ASCII art markers stripped to prevent duplication
                    with open(readme_target_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    print(f"   📋 Updated: README.md copied to Pipulate.com root (markers stripped)")
                else:
                    print(f"   📋 Would update: README.md copy to Pipulate.com root (markers stripped)")
            else:
                print(f"   📋 No change: README.md already up to date in Pipulate.com root")
                
        except Exception as e:
            print(f"   ⚠️  Warning: Could not copy README.md - {e}")
        
        # ASCII Art Usage Frequency & Coverage Analysis
        print(f"\n{'='*60}")
        print("📈 ASCII ART USAGE FREQUENCY & COVERAGE ANALYSIS")
        print(f"{'='*60}")
    
    total_usages = sum(len(files) for files in usage_frequency.values())
    coverage_percentage = (len(used_blocks) / len(ascii_blocks)) * 100 if ascii_blocks else 0
    
    print(f"\n📊 COVERAGE SUMMARY:")
    print(f"   🎯 Available blocks:  {len(ascii_blocks)}")
    print(f"   ✅ Used blocks:      {len(used_blocks)} ({coverage_percentage:.1f}%)")
    print(f"   ❌ Unused blocks:    {len(unused_blocks)}")
    print(f"   ⚠️  Unknown markers: {len(unknown_markers)}")
    print(f"   🔄 Total usages:     {total_usages}")
    
    # Most frequently used blocks
    if used_blocks:
        print(f"\n🏆 MOST FREQUENTLY USED BLOCKS:")
        sorted_usage = sorted(used_blocks.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (marker, files) in enumerate(sorted_usage, 1):
            print(f"   {i}. {marker} ({len(files)} uses)")
            for j, file_path in enumerate(files):
                tree_connector = "└──" if j == len(files) - 1 else "├──"
                print(f"      {tree_connector} 📝 {file_path}")
    
    # Detailed usage breakdown
    if used_blocks:
        print(f"\n📋 DETAILED USAGE BREAKDOWN:")
        for marker in sorted(used_blocks.keys()):
            files = usage_frequency[marker]
            print(f"\n   🎨 {marker} ({len(files)} {'use' if len(files) == 1 else 'uses'}):")
            for j, file_path in enumerate(files):
                tree_connector = "└──" if j == len(files) - 1 else "├──"
                print(f"      {tree_connector} 📄 {file_path}")
    
    # Unused blocks with strategic placement suggestions
    if unused_blocks:
        print(f"\n💤 UNUSED BLOCKS ({len(unused_blocks)}):")
        for i, marker in enumerate(sorted(unused_blocks.keys())):
            tree_connector = "└──" if i == len(unused_blocks) - 1 else "├──"
            print(f"   {tree_connector} ⚪ {marker}")
        
        # Generate strategic placement suggestions
        placement_suggestions = suggest_placement_for_unused_blocks(unused_blocks.keys(), markdown_files, ascii_block_data)
        
        if placement_suggestions:
            print(f"\n🎯 STRATEGIC PLACEMENT SUGGESTIONS:")
            print(f"\n   Found optimal placements for {len(placement_suggestions)} unused blocks:")
            
            for i, (block_key, suggestions) in enumerate(placement_suggestions.items(), 1):
                is_last_block = (i == len(placement_suggestions))
                block_connector = "└──" if is_last_block else "├──"
                
                print(f"\n   {block_connector} 🎨 {block_key}")
                
                # Get ASCII art title for context
                block_title = "Unknown"
                if block_key in ascii_block_data:
                    block_title = ascii_block_data[block_key]['title'].replace('###', '').replace('##', '').replace('#', '').strip()
                
                print(f"   {'   ' if is_last_block else '│  '} ├── 📝 Content: {block_title}")
                print(f"   {'   ' if is_last_block else '│  '} └── 🎯 Recommended placements:")
                
                for j, suggestion in enumerate(suggestions):
                    is_last_suggestion = (j == len(suggestions) - 1)
                    suggestion_connector = "└──" if is_last_suggestion else "├──"
                    indent = "      " if is_last_block else "│     "
                    
                    file_path = suggestion['file']
                    score = suggestion['score']
                    reasons = suggestion['reasons']
                    keywords = suggestion['matched_keywords']
                    
                    print(f"   {indent} {suggestion_connector} 📄 {file_path} (score: {score})")
                    
                    # Show reasons
                    reason_indent = "         " if is_last_block else "│        "
                    if is_last_suggestion:
                        reason_indent = "         " if is_last_block else "│        "
                    
                    for k, reason in enumerate(reasons):
                        reason_connector = "└──" if k == len(reasons) - 1 else "├──"
                        print(f"   {reason_indent} {reason_connector} ✨ {reason}")
                    
                    # Show top matched keywords
                    if keywords:
                        top_keywords = keywords[:3]  # Show first 3 keywords
                        keyword_text = ", ".join(top_keywords)
                        if len(keywords) > 3:
                            keyword_text += f" (+{len(keywords)-3} more)"
                        print(f"   {reason_indent} └── 🔤 Keywords: {keyword_text}")
            
            print(f"\n   💡 TO IMPLEMENT THESE SUGGESTIONS:")
            print(f"\n   1️⃣  Choose the highest-scoring placement for each block")
            print(f"   2️⃣  Add markers to the target file:")
            print(f"       <!-- START_ASCII_ART: block-name -->")
            print(f"       [PLACEHOLDER CONTENT REQUIRED]")
            print(f"       <!-- END_ASCII_ART: block-name -->")
            print(f"\n   🚨 CRITICAL: Include placeholder content between markers!")
            print(f"       ❌ WRONG: Consecutive markers (silent failure)")
            print(f"       ✅ CORRECT: Content or placeholder between markers")
            print(f"\n   3️⃣  Run the sync script to populate content:")
            print(f"       python helpers/docs_sync/sync_ascii_art.py")
            print(f"\n   ✨ This will strategically place unused ASCII art where it adds the most value!")
            
        else:
            print(f"   💡 Consider removing unused blocks or finding places to use them")
    
    # Enhanced unknown markers analysis with upstream promotion suggestions
    if unknown_markers:
        print(f"\n⚠️  UNKNOWN MARKERS FOUND ({len(unknown_markers)}):")
        
        # Analyze quality of unknown ASCII art
        promotion_candidates = []
        for marker in sorted(unknown_markers):
            if marker in unknown_marker_content:
                content_info = unknown_marker_content[marker]
                ascii_content = content_info['content']
                file_location = content_info['file']
                line_range = content_info['line_range']
                
                is_quality, reasons = analyze_ascii_art_quality(ascii_content)
                
                if is_quality:
                    promotion_candidates.append({
                        'marker': marker,
                        'content': ascii_content,
                        'file': file_location,
                        'line_range': line_range,
                        'reasons': reasons
                    })
                    if verbose:
                        print(f"   ├── 🌟 {marker} (PROMOTION CANDIDATE)")
                        print(f"   │   ├── 📄 Found in: {file_location} (lines {line_range})")
                        print(f"   │   └── ✨ Quality: {', '.join(reasons)}")
                    else:
                        print(f"   ├── 🌟 {marker} (PROMOTION CANDIDATE)")
                        print(f"   │   ├── 📄 Found in: {file_location}")
                        print(f"   │   └── ✨ Quality: {', '.join(reasons)}")
                else:
                    if verbose:
                        print(f"   ├── ❓ {marker}")
                        print(f"   │   └── 📄 Found in: {file_location} (lines {line_range})")
                    else:
                        print(f"   ├── ❓ {marker}")
                        print(f"   │   └── 📄 Found in: {file_location}")
            else:
                print(f"   └── ❓ {marker} (no content extracted)")
        
        # Upstream Promotion Suggestions
        if promotion_candidates:
            print(f"\n🚀 UPSTREAM PROMOTION SUGGESTIONS:")
            print(f"\n   Found {len(promotion_candidates)} high-quality ASCII art blocks that could be added to README.md:")
            
            for i, candidate in enumerate(promotion_candidates, 1):
                marker = candidate['marker']
                content = candidate['content']
                file_location = candidate['file']
                line_range = candidate.get('line_range', 'unknown')
                reasons = candidate['reasons']
                
                is_last = (i == len(promotion_candidates))
                tree_connector = "└──" if is_last else "├──"
                
                print(f"\n   {tree_connector} 🎨 {marker}")
                if verbose:
                    print(f"   {'   ' if is_last else '│  '} ├── 📍 Currently in: {file_location} (lines {line_range})")
                else:
                    print(f"   {'   ' if is_last else '│  '} ├── 📍 Currently in: {file_location}")
                print(f"   {'   ' if is_last else '│  '} ├── ⭐ Quality factors: {', '.join(reasons)}")
                print(f"   {'   ' if is_last else '│  '} └── 📝 Full ASCII art content:")
                
                all_lines = content.split('\n')
                for j, line in enumerate(all_lines):
                    is_last_line = (j == len(all_lines) - 1)
                    line_connector = "└──" if is_last_line else "├──"
                    indent = "      " if is_last else "│     "
                    print(f"   {indent} {line_connector} {line}")
            
            print(f"\n   💡 TO PROMOTE THESE TO README.md:")
            print(f"\n   1️⃣  Copy the ASCII content from the source file")
            print(f"   2️⃣  Add to pipulate/README.md in the ASCII art section:")
            print(f"       <!-- START_ASCII_ART: marker-name -->")
            print(f"       ```")
            print(f"       [ASCII content here]")
            print(f"       ```")
            print(f"       <!-- END_ASCII_ART: marker-name -->")
            print(f"\n   3️⃣  Run sync script again to propagate to all files:")
            print(f"       python helpers/docs_sync/sync_ascii_art.py")
            print(f"\n   ✨ This will make the ASCII art available system-wide!")
            
        else:
            print(f"   💡 No high-quality ASCII art found for promotion")
    
    # Heuristic ASCII Art Discovery (improved regex-based naked fenced code block detection)
    if heuristic_candidates:
        if prompt_mode:
            # Special AI-friendly prompt format with debugging instructions
            print("# ASCII Art Promotion Task")
            print("\nYou are an expert content curator for the Pipulate project. Your task is to analyze and promote high-quality ASCII art candidates that have been discovered in the documentation.")
            
            # Add debugging instructions for false positive scenarios
            print(f"\n⚠️  **CRITICAL: CHECK FOR FALSE POSITIVES FIRST!**")
            print(f"Current coverage shows {len(used_blocks)}/{len(ascii_blocks)} blocks used ({coverage_percentage:.1f}%).")
            print(f"If coverage is unexpectedly low (< 50%), investigate these potential issues BEFORE promoting new ASCII art:")
            print(f"")
            print(f"🔍 **DEBUGGING CHECKLIST:**")
            print(f"1. **Key disassociation**: ASCII art exists but markers have changed/moved")
            print(f"2. **Content drift**: ASCII art content changed upstream without sync")
            print(f"3. **File restructuring**: Markdown files reorganized breaking existing links")
            print(f"4. **Marker corruption**: START/END markers damaged or malformed")
            print(f"")
            print(f"📋 **FIX UPSTREAM FIRST:**")
            print(f"• Run full sync without --prompt: `python sync_ascii_art.py`")
            print(f"• Check if existing ASCII art blocks are properly linked")
            print(f"• Verify README.md ASCII art sections are intact")
            print(f"• Look for 'Unknown markers' in output")
            print(f"")
            print(f"✅ **ONLY AFTER** upstream issues are resolved, proceed with new ASCII art promotion.")
            print(f"")
            print("\nBased on the candidates below, please:")
            print("1. Select the BEST ASCII art candidates for promotion")
            print("2. Choose appropriate marker names that reflect their semantic meaning")
            print("3. Add them to pipulate/README.md in the appropriate ASCII art section")
            print("4. Replace the naked fenced code blocks in the source files with proper markers")
            print("5. Run the sync script to propagate the changes")
            print("\n## Discovered ASCII Art Candidates:")
        else:
            print(f"\n🔍 HEURISTIC ASCII ART DISCOVERY (improved regex):")
        
        print(f"\n   Found {len(heuristic_candidates)} potential ASCII art blocks in naked fenced code blocks:")
        
        # Analyze quality of heuristic candidates
        quality_candidates = []
        for candidate in heuristic_candidates:
            ascii_content = candidate['content']
            filename = candidate['filename']
            start_line = candidate.get('start_line', 'unknown')
            
            is_quality, reasons = analyze_ascii_art_quality(ascii_content)
            
            if is_quality:
                quality_candidates.append({
                    'content': ascii_content,
                    'file': filename,
                    'start_line': start_line,
                    'reasons': reasons,
                    'suggested_marker': filename.replace('.md', '').replace('_', '-').replace('/', '-')
                })
        
        if quality_candidates:
            if prompt_mode:
                print(f"\n### HIGH-QUALITY CANDIDATES ({len(quality_candidates)}):")
            else:
                print(f"\n   🌟 HIGH-QUALITY CANDIDATES ({len(quality_candidates)}):")
            
            for i, candidate in enumerate(quality_candidates, 1):
                content = candidate['content']
                file_location = candidate['file']
                start_line = candidate.get('start_line', 'unknown')
                reasons = candidate['reasons']
                suggested_marker = candidate['suggested_marker']
                
                is_last = (i == len(quality_candidates))
                tree_connector = "└──" if is_last else "├──"
                
                if prompt_mode:
                    print(f"\n#### Candidate {i}: {file_location}")
                    print(f"- **Quality factors**: {', '.join(reasons)}")
                    if start_line != 'unknown':
                        print(f"- **Location**: line {start_line}")
                    print(f"- **Suggested marker**: `{suggested_marker}`")
                    print(f"- **ASCII Art Content**:")
                    print("```")
                    print(content)
                    print("```")
                else:
                    print(f"\n   {tree_connector} 🎨 Found in: {file_location}")
                    print(f"   {'   ' if is_last else '│  '} ├── ⭐ Quality factors: {', '.join(reasons)}")
                    if verbose and start_line != 'unknown':
                        print(f"   {'   ' if is_last else '│  '} ├── 📍 Location: line {start_line}")
                    print(f"   {'   ' if is_last else '│  '} ├── 🏷️  Suggested marker: {suggested_marker}")
                    print(f"   {'   ' if is_last else '│  '} └── 📝 Full ASCII art content:")
                    
                    all_lines = content.split('\n')
                    for j, line in enumerate(all_lines):
                        is_last_line = (j == len(all_lines) - 1)
                        line_connector = "└──" if is_last_line else "├──"
                        indent = "      " if is_last else "│     "
                        print(f"   {indent} {line_connector} {line}")
            
            if prompt_mode:
                print("\n## Your Task:")
                print("\nFor each candidate you choose to promote:")
                print("\n1. **Choose a meaningful marker name** - Use semantic names like `local-first-benefits-diagram` instead of generic ones")
                print("2. **Add to pipulate/README.md** - Insert in the ASCII art section with proper markers")
                print("3. **Update source files** - Replace naked fenced code blocks with marker references")
                print("4. **Test the sync** - Run `python helpers/docs_sync/sync_ascii_art.py` to verify")
                print("\n### Example workflow:")
                print("```markdown")
                print("<!-- In pipulate/README.md, add: -->")
                print("<!-- START_ASCII_ART: your-chosen-marker-name -->")
                print("```")
                print("[Copy the ASCII content from above]")
                print("```")
                print("<!-- END_ASCII_ART: your-chosen-marker-name -->")
                print()
                print("<!-- In the source file, replace the naked code block with: -->")
                print("<!-- START_ASCII_ART: your-chosen-marker-name -->")
                print("<!-- END_ASCII_ART: your-chosen-marker-name -->")
                print("```")
            else:
                print(f"\n   💡 TO PROMOTE HEURISTIC DISCOVERIES:")
                print(f"\n   1️⃣  Choose a meaningful marker name for the ASCII art")
                print(f"   2️⃣  Add to pipulate/README.md in the ASCII art section:")
                print(f"       <!-- START_ASCII_ART: your-marker-name -->")
                print(f"       ```")
                print(f"       [Copy the ASCII content from the plain code block]")
                print(f"       ```")
                print(f"       <!-- END_ASCII_ART: your-marker-name -->")
                print(f"\n   3️⃣  Replace the naked fenced code block in the source file with:")
                print(f"       <!-- START_ASCII_ART: your-marker-name -->")
                print(f"       <!-- END_ASCII_ART: your-marker-name -->")
                print(f"\n   4️⃣  Run sync script to propagate:")
                print(f"       python helpers/docs_sync/sync_ascii_art.py")
                print(f"\n   ✨ This converts isolated ASCII art into reusable, managed content!")
        else:
            if prompt_mode:
                print("\n### No high-quality candidates found")
                print("All discovered ASCII art failed to meet quality thresholds.")
            else:
                print(f"   📝 Found candidates but none met quality thresholds")

    # Skip documentation sections in prompt mode
    if not prompt_mode:
        # How to use ASCII art markers documentation
        print(f"\n📖 HOW TO USE ASCII ART MARKERS:")
        print(f"\n   🎯 To insert any ASCII art block in your markdown files:")
        print(f"\n   1️⃣  Add the opening marker:")
        print(f"       <!-- START_ASCII_ART: block-name -->")
        print(f"\n   2️⃣  Add the closing marker:")
        print(f"       <!-- END_ASCII_ART: block-name -->")
        print(f"\n   3️⃣  Run the sync script:")
        print(f"       python helpers/docs_sync/sync_ascii_art.py")
        
        if 'unused_blocks' in locals() and unused_blocks:
            # Show example with first unused block
            first_unused = sorted(unused_blocks.keys())[0]
            print(f"\n   📝 Example usage for unused block '{first_unused}':")
            print(f"       ")
            print(f"       Here's how this feature works:")
            print(f"       ")
            print(f"       <!-- START_ASCII_ART: {first_unused} -->")
            print(f"       <!-- END_ASCII_ART: {first_unused} -->")
            print(f"       ")
            print(f"       This will provide detailed technical insights...")
        
        print(f"\n   ✨ The ASCII art content will be automatically inserted between the markers!")
        print(f"   🔄 Any changes to the source (README.md) will sync to all files using that marker.")

        if verbose:
            print(f"\n🔧 PATTERN MATCHING VERIFICATION:")
            print(f"   📋 Use --verbose flag to see:")
            print(f"   • Exact line numbers for all markers")
            print(f"   • Pattern matching success/failure details")
            print(f"   • ASCII content line counts")
            print(f"   • File location ranges for unknown markers")

        print(f"\n{'='*60}")
        print("✨ Analysis complete! ASCII art ecosystem status reported.")
        print(f"{'='*60}")
    
    # Report consecutive marker issues in BOTH modes
    if hasattr(detect_consecutive_markers, 'global_issues') and detect_consecutive_markers.global_issues:
        print(f"\n🚨 CONSECUTIVE MARKER ISSUES DETECTED:")
        print(f"   Found {len(detect_consecutive_markers.global_issues)} malformed marker pairs:")
        for issue in detect_consecutive_markers.global_issues:
            print(f"   ⚠️  {issue}")
        print(f"\n   💡 FIX: Add placeholder content between START/END markers:")
        print(f"       ❌ WRONG: <!-- START_ASCII_ART: name -->")
        print(f"                 <!-- END_ASCII_ART: name -->")
        print(f"       ✅ CORRECT: <!-- START_ASCII_ART: name -->")
        print(f"                   [placeholder content here]")
        print(f"                   <!-- END_ASCII_ART: name -->")
        print(f"\n   🔧 Without placeholder content, sync_ascii_art.py cannot populate the blocks!")

if __name__ == "__main__":
    main()
