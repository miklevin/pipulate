#!/usr/bin/env python3
"""
Sync ASCII Art - One Command to Rule Them All

Updates all ASCII art blocks from pipulate/README.md to Pipulate.com
Walks through all markdown files and updates any markers it finds.

Usage: 
  python helpers/docs_sync/sync_ascii_art.py            # Normal sync
  python helpers/docs_sync/sync_ascii_art.py --candidates  # Include heuristic discovery
  python helpers/docs_sync/sync_ascii_art.py --verbose   # Include detailed line numbers and pattern matching info
"""

import os
import re
import sys
from pathlib import Path
from ascii_art_parser import extract_ascii_art_blocks

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

def main():
    """Main synchronization function with usage frequency and coverage analysis"""
    # Check for command-line arguments  
    verbose = "--verbose" in sys.argv
    prompt_mode = "--prompt" in sys.argv
    
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
                
                # Check if update is needed
                block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
                block_match = re.search(block_pattern, content, re.DOTALL)
                
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
                            new_content = re.sub(block_pattern, lambda m: replacement, content, flags=re.DOTALL)
                            
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
    
    # Unused blocks
    if unused_blocks:
        print(f"\n💤 UNUSED BLOCKS ({len(unused_blocks)}):")
        for i, marker in enumerate(sorted(unused_blocks.keys())):
            tree_connector = "└──" if i == len(unused_blocks) - 1 else "├──"
            print(f"   {tree_connector} ⚪ {marker}")
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

if __name__ == "__main__":
    main()
