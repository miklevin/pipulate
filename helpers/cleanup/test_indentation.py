#!/usr/bin/env python3
"""
Test script to verify indentation detection logic
"""

def test_indentation_detection():
    # Sample landing method with 4-space indentation
    sample_method = """    async def landing(self, request):
        \"\"\" Renders the initial landing page with the key input form. \"\"\"
        pip = self.pipulate
        return Container(...)"""
    
    print("Original method:")
    print(repr(sample_method))
    print()
    
    # Detect indentation
    lines = sample_method.split('\n')
    method_line = lines[0]
    print(f"Method line: {repr(method_line)}")
    
    base_indent = len(method_line) - len(method_line.lstrip())
    print(f"Base indent: {base_indent}")
    
    method_indent = ' ' * base_indent
    body_indent = ' ' * (base_indent + 4)
    print(f"Method indent: {repr(method_indent)}")
    print(f"Body indent: {repr(body_indent)}")
    
    # Create replacement
    standardized_method = f'''{method_indent}async def landing(self, request):
{body_indent}"""Generate the landing page using the standardized helper while maintaining WET explicitness."""
{body_indent}pip = self.pipulate
{body_indent}
{body_indent}# Use centralized landing page helper - maintains WET principle by explicit call
{body_indent}return pip.create_standard_landing_page(self)'''
    
    print("\nStandardized method:")
    print(repr(standardized_method))
    print()
    print("Formatted view:")
    print(standardized_method)

if __name__ == '__main__':
    test_indentation_detection() 