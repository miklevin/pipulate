#!/usr/bin/env python3
"""
🎨 LIVING README REVOLUTION - Parsable ASCII Art Dictionary System

BREAKTHROUGH: Transforms documentation from static text into dynamic source of truth
where ASCII art diagrams become parsable, distributable assets that maintain 
consistency across the entire project ecosystem.

PARSING STRATEGY - Structured format enables automatic extraction:
- Headline (### title) becomes the key/identifier
- Header = content between headline and first ``` fence
- Art = ASCII art content inside ``` fences  
- Footer = content between closing ``` and next section

DISTRIBUTION MAGIC:
• Source: README.md (clean, beautiful, GitHub-friendly)
• Destinations: Any .md/.mdc file with ASCII art markers
• Result: Single source of truth for all ASCII art across Pipulate

This creates "foolproof failsafe" documentation that writes itself!
"""

import re
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

def main():
    """Test the parser with README.md"""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    
    if not readme_path.exists():
        print(f"❌ README.md not found at {readme_path}")
        return
    
    print("🔍 Parsing README.md for ASCII art blocks...")
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = extract_ascii_art_blocks(content)
    
    print(f"\n📊 Found {len(blocks)} ASCII art blocks:")
    
    for slug, block in blocks.items():
        print(f"\n🎨 {slug}:")
        print(f"   Title: {block['title']}")
        print(f"   Header: {block['header'][:50]}..." if len(block['header']) > 50 else f"   Header: {block['header']}")
        print(f"   Art: {len(block['art'])} characters")
        print(f"   Footer: {block['footer'][:50]}..." if len(block['footer']) > 50 else f"   Footer: {block['footer']}")

if __name__ == "__main__":
    main() 