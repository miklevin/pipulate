#!/usr/bin/env python3
"""
Debug Sync Logic

Test the exact replacement logic used by sync_ascii_art.py to identify
why it's creating duplicate markers.
"""

import re

def test_sync_logic():
    print("🔍 TESTING SYNC REPLACEMENT LOGIC")
    print("=" * 50)
    
    # Test case 1: Simple placeholder
    print("\n📝 TEST 1: Simple placeholder")
    content1 = '''<!-- START_ASCII_ART: test -->
[Placeholder - run sync_ascii_art.py to populate]
<!-- END_ASCII_ART: test -->'''
    
    marker = 'test'
    new_content_block = '''### Test Block

ASCII ART HERE

Some description'''
    
    block_pattern = rf'<!-- START_ASCII_ART: {re.escape(marker)} -->.*?<!-- END_ASCII_ART: {re.escape(marker)} -->'
    replacement = f'<!-- START_ASCII_ART: {marker} -->\n{new_content_block}\n<!-- END_ASCII_ART: {marker} -->'
    
    print("BEFORE:")
    print(content1)
    print("\nREPLACEMENT:")
    print(replacement)
    print("\nAFTER:")
    new_content1 = re.sub(block_pattern, lambda m: replacement, content1, count=1, flags=re.DOTALL)
    print(new_content1)
    
    # Test case 2: Content with title line (like our actual case)
    print("\n" + "=" * 50)
    print("📝 TEST 2: Content with title line (real scenario)")
    content2 = '''<!-- START_ASCII_ART: plugin-discovery-system -->
### 5. Plugin Discovery System  <!-- key: plugin-discovery-system -->

<!-- START_ASCII_ART: plugin-discovery-system -->

EXISTING ASCII ART
CONTENT HERE

<!-- END_ASCII_ART: plugin-discovery-system -->

Some text after
<!-- END_ASCII_ART: plugin-discovery-system -->

More content'''
    
    marker2 = 'plugin-discovery-system'
    new_content_block2 = '''### 5. Plugin Discovery System  <!-- key: plugin-discovery-system -->

NEW ASCII ART
REPLACEMENT CONTENT

* Some bullet points
* More information'''
    
    block_pattern2 = rf'<!-- START_ASCII_ART: {re.escape(marker2)} -->.*?<!-- END_ASCII_ART: {re.escape(marker2)} -->'
    replacement2 = f'<!-- START_ASCII_ART: {marker2} -->\n{new_content_block2}\n<!-- END_ASCII_ART: {marker2} -->'
    
    print("BEFORE:")
    print(content2)
    print("\nREPLACEMENT:")
    print(replacement2)
    print("\nAFTER:")
    new_content2 = re.sub(block_pattern2, lambda m: replacement2, content2, count=1, flags=re.DOTALL)
    print(new_content2)
    
    # Test case 3: What happens on second run?
    print("\n" + "=" * 50)
    print("📝 TEST 3: Second sync run (idempotence test)")
    
    # Run the replacement again on the result
    print("RUNNING SYNC AGAIN ON RESULT:")
    new_content3 = re.sub(block_pattern2, lambda m: replacement2, new_content2, count=1, flags=re.DOTALL)
    print(new_content3)
    
    # Check if they're identical
    if new_content2 == new_content3:
        print("\n✅ IDEMPOTENT: Second run produced identical result")
    else:
        print("\n❌ NOT IDEMPOTENT: Second run changed the content")
        print("DIFFERENCES:")
        lines2 = new_content2.split('\n')
        lines3 = new_content3.split('\n')
        for i, (line2, line3) in enumerate(zip(lines2, lines3)):
            if line2 != line3:
                print(f"  Line {i+1}: '{line2}' → '{line3}'")

if __name__ == '__main__':
    test_sync_logic() 