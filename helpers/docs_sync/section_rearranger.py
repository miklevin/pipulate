#!/usr/bin/env python3
"""
Deterministic Section Rearrangement Tool

This tool provides slice-and-join functionality for rearranging markdown sections
separated by 80-hyphen slicers. It ensures no content is lost during rearrangement
by using precise indexing operations.

Usage:
    python section_rearranger.py README.md --preview  # Show current sections
    python section_rearranger.py README.md --rearrange 1,3,2,4,5  # Reorder sections
"""
import argparse
import sys
from pathlib import Path
from typing import List, Tuple


class SectionRearranger:
    """Handles deterministic rearrangement of markdown sections."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.separator = "-" * 80
        self.sections = []
        self.load_sections()
    
    def load_sections(self):
        """Load and parse sections from the markdown file."""
        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        current_section = []
        section_start_line = 0
        
        for i, line in enumerate(lines):
            if line.strip() == self.separator:
                # Found separator - save current section
                if current_section:
                    self.sections.append({
                        'start_line': section_start_line,
                        'end_line': i - 1,
                        'content': '\n'.join(current_section),
                        'separator_line': i
                    })
                current_section = []
                section_start_line = i + 1
            else:
                current_section.append(line)
        
        # Add final section (after last separator or entire file if no separators)
        if current_section:
            self.sections.append({
                'start_line': section_start_line,
                'end_line': len(lines) - 1,
                'content': '\n'.join(current_section),
                'separator_line': None  # No separator after final section
            })
    
    def preview_sections(self) -> str:
        """Generate a preview of all sections with their first few lines."""
        preview = f"📄 File: {self.file_path}\n"
        preview += f"🔪 Found {len(self.sections)} sections separated by 80-hyphen slicers\n\n"
        
        for i, section in enumerate(self.sections, 1):
            lines = section['content'].strip().split('\n')
            first_line = lines[0] if lines else "(empty)"
            line_count = len(lines)
            
            preview += f"Section {i}: Lines {section['start_line']}-{section['end_line']} ({line_count} lines)\n"
            preview += f"  First line: {first_line[:80]}{'...' if len(first_line) > 80 else ''}\n"
            
            # Show first few content lines for context
            for j, line in enumerate(lines[:3]):
                if line.strip():
                    preview += f"  │ {line[:70]}{'...' if len(line) > 70 else ''}\n"
            if len(lines) > 3:
                preview += f"  │ ... ({len(lines) - 3} more lines)\n"
            preview += "\n"
        
        return preview
    
    def rearrange_sections(self, new_order: List[int]) -> str:
        """Rearrange sections according to the specified order (1-indexed)."""
        if len(new_order) != len(self.sections):
            raise ValueError(f"Order must specify all {len(self.sections)} sections")
        
        if set(new_order) != set(range(1, len(self.sections) + 1)):
            raise ValueError(f"Order must contain each section number 1-{len(self.sections)} exactly once")
        
        # Build new content by joining sections in new order
        new_content_parts = []
        
        for i, section_num in enumerate(new_order):
            section = self.sections[section_num - 1]  # Convert to 0-indexed
            
            # Add section content
            new_content_parts.append(section['content'])
            
            # Add separator after section (except for the last one)
            if i < len(new_order) - 1:
                new_content_parts.append(self.separator)
        
        return '\n'.join(new_content_parts)
    
    def write_rearranged(self, new_order: List[int], output_path: str = None):
        """Write rearranged content to file."""
        new_content = self.rearrange_sections(new_order)
        
        if output_path is None:
            output_path = self.file_path
        
        Path(output_path).write_text(new_content, encoding='utf-8')
        
        return f"✅ Sections rearranged and written to {output_path}"


def main():
    parser = argparse.ArgumentParser(description="Deterministic markdown section rearranger")
    parser.add_argument("file", help="Markdown file to process")
    parser.add_argument("--preview", action="store_true", help="Show section preview")
    parser.add_argument("--rearrange", help="New section order (e.g., '1,3,2,4,5')")
    parser.add_argument("--output", help="Output file (default: overwrite input)")
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    rearranger = SectionRearranger(args.file)
    
    if args.preview:
        print(rearranger.preview_sections())
    
    elif args.rearrange:
        try:
            # Parse the new order
            new_order = [int(x.strip()) for x in args.rearrange.split(',')]
            
            # Perform rearrangement
            result = rearranger.write_rearranged(new_order, args.output)
            print(result)
            
            # Show what was done
            print(f"\n📋 Rearrangement Summary:")
            print(f"   Original order: {list(range(1, len(rearranger.sections) + 1))}")
            print(f"   New order:      {new_order}")
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    
    else:
        print("Use --preview to see sections or --rearrange to reorder them")
        print(f"Example: python {sys.argv[0]} {args.file} --preview")
        print(f"Example: python {sys.argv[0]} {args.file} --rearrange 1,3,2,4,5")


if __name__ == "__main__":
    main() 