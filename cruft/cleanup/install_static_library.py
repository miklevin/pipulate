#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Downloads JavaScript libraries from specified URLs and saves them locally.

I need to figure out a way to make this look for all the latest versions and
harmlessly report them, giving the option to update each locally.

Currently it's just hardwired to the latest known versions of each at the last
time I ran it. Not that you want to just blindly update every local library
every time you run this. Such libraries being frozen locally is part of the
Pipulate advantage, so I need to think through under what conditions and for
what reasons local JavaScript (and CSS) libraries and dependencies get updated.

Also, certain things like Prism are handled differently because of their
download systems. Currently, the download selections for Prism are set to:

https://prismjs.com/download#themes=prism&languages=markup+css+clike+javascript+bash+diff+json+json5+jsonp+liquid+lua+markdown+markup-templating+mermaid+nix+python+regex+yaml&plugins=line-highlight+line-numbers+show-language+jsonp-highlight+toolbar+copy-to-clipboard+download-button+diff-highlight+treeview

"""

import requests
from pathlib import Path
import sys
from typing import List, Dict, Union, Optional

# Library definitions - URLs and file types
# List the CDN paths of each static library here.
LIBRARIES = {
    "prism-core": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js",
        "type": "js"
    },
    "prism-theme": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-okaidia.min.css",
        "type": "css"
    },
    "prism-copy": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/copy-to-clipboard/prism-copy-to-clipboard.min.js",
        "type": "js"
    },
    "prism-line-numbers": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js",
        "type": "js"
    },
    "prism-line-numbers-css": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.css",
        "type": "css"
    }
}

# Target directory to save the files
TARGET_DIR = Path("/home/mike/repos/pipulate/static")

def download_library(name: str, lib_info: Dict[str, str], save_dir: Path) -> Optional[Path]:
    """
    Downloads a file from the given URL and saves it into the specified directory.
    
    Args:
        name: The name of the library
        lib_info: Dictionary containing url and type
        save_dir: The directory where the file should be saved
    
    Returns:
        Path to the saved file or None if download failed
    """
    try:
        url = lib_info["url"]
        
        # Ensure the target directory exists, create if it doesn't
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract the filename from the URL
        filename = Path(url).name
        if not filename:
            print(f"Error: Could not determine filename from URL: {url}", file=sys.stderr)
            return None
        
        save_path = save_dir / filename
        print(f"Downloading '{name}' from {url}...")
        
        # Perform the GET request to download the file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Write the content to the local file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully saved to: {save_path}")
        return save_path
    
    except Exception as e:
        print(f"Error downloading {name}: {e}", file=sys.stderr)
        return None

def download_all_libraries(libraries: Dict[str, Dict[str, str]], save_dir: Path) -> List[Path]:
    """
    Downloads all libraries defined in the libraries dictionary.
    
    Args:
        libraries: Dictionary of library definitions
        save_dir: Directory to save files to
        
    Returns:
        List of paths to successfully downloaded files
    """
    successful_downloads = []
    
    for name, lib_info in libraries.items():
        result = download_library(name, lib_info, save_dir)
        if result:
            successful_downloads.append(result)
    
    return successful_downloads

if __name__ == "__main__":
    print("Starting JavaScript library download...")
    successful = download_all_libraries(LIBRARIES, TARGET_DIR)
    print(f"Download process finished. {len(successful)}/{len(LIBRARIES)} libraries downloaded successfully.")
