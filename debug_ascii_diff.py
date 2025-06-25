import re
from pathlib import Path

# Read README.md
with open('README.md', 'r') as f:
    readme_content = f.read()

# Read install.md  
with open('../Pipulate.com/install.md', 'r') as f:
    install_content = f.read()

# Extract the specific ASCII block from both
pattern = r'<!-- START_ASCII_ART: not-on-my-machine-problem-fixed -->.*?```\n(.*?)\n```.*?<!-- END_ASCII_ART: not-on-my-machine-problem-fixed -->'

readme_match = re.search(pattern, readme_content, re.DOTALL)
install_match = re.search(pattern, install_content, re.DOTALL)

if readme_match and install_match:
    readme_art = readme_match.group(1)
    install_art = install_match.group(1)
    
    print('README art length:', len(readme_art))
    print('Install art length:', len(install_art))
    print('Are they equal?', readme_art == install_art)
    print()
    
    # Show the problematic lines
    readme_lines = readme_art.split('\n')
    install_lines = install_art.split('\n')
    
    for i, (r_line, i_line) in enumerate(zip(readme_lines, install_lines)):
        if r_line != i_line:
            print(f'Line {i+1} differs:')
            print(f'  README : {repr(r_line)}')
            print(f'  Install: {repr(i_line)}')
            print()
else:
    print('Could not find ASCII art blocks in one or both files')
    if readme_match:
        print('Found in README')
    if install_match:
        print('Found in install.md')
