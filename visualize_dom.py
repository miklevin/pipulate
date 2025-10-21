# visualize_dom.py
import argparse
import io
import sys
from pathlib import Path
from rich.console import Console
from bs4 import BeautifulSoup

# --- Need to add project root to sys.path to import dom_tools ---
# Determine the script's directory and add the project root
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))
# --- End path modification ---

try:
    # Now try importing the necessary classes from dom_tools
    # NOTE: Ensure these classes ONLY return the rich object and do NOT print.
    from tools.dom_tools import _DOMHierarchyVisualizer, _DOMBoxVisualizer
except ImportError as e:
    print(f"Error: Could not import visualization classes from tools.dom_tools. {e}", file=sys.stderr)
    print("Ensure visualize_dom.py is in the project root and tools/ exists.", file=sys.stderr)
    sys.exit(1)

def main(html_file_path: str):
    """
    Generates DOM hierarchy and box visualizations (.txt and .html)
    for a given HTML file. Saves output in the same directory.
    """
    input_path = Path(html_file_path).resolve()
    output_dir = input_path.parent

    if not input_path.exists() or not input_path.is_file():
        print(f"Error: Input HTML file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        html_content = input_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading HTML file {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    results = {}

    # --- Generate Hierarchy ---
    try:
        # Use the class that ONLY returns the object
        hierarchy_visualizer = _DOMHierarchyVisualizer()
        tree_object = hierarchy_visualizer.visualize_dom_content(html_content, source_name=str(input_path)) # Pass source_name

        # Capture Text silently
        string_buffer_txt_h = io.StringIO()
        record_console_txt_h = Console(record=True, width=180, file=string_buffer_txt_h)
        record_console_txt_h.print(tree_object)
        results['hierarchy_txt'] = record_console_txt_h.export_text()

        # Capture HTML silently
        string_buffer_html_h = io.StringIO()
        record_console_html_h = Console(record=True, width=180, file=string_buffer_html_h)
        record_console_html_h.print(tree_object)
        results['hierarchy_html'] = record_console_html_h.export_html(inline_styles=True)

    except Exception as e:
        print(f"Error generating hierarchy visualization for {input_path}: {e}", file=sys.stderr)
        results['hierarchy_txt'] = f"Error generating hierarchy: {e}"
        results['hierarchy_html'] = f"<h1>Error generating hierarchy</h1><p>{e}</p>"


    # --- Generate Boxes ---
    try:
        # Use the class that ONLY returns the object
        box_visualizer = _DOMBoxVisualizer()
        box_object = box_visualizer.visualize_dom_content(html_content, source_name=str(input_path)) # Pass source_name

        if box_object:
            # Capture Text silently
            string_buffer_txt_b = io.StringIO()
            record_console_txt_b = Console(record=True, width=180, file=string_buffer_txt_b)
            record_console_txt_b.print(box_object)
            results['boxes_txt'] = record_console_txt_b.export_text()

            # Capture HTML silently
            string_buffer_html_b = io.StringIO()
            record_console_html_b = Console(record=True, width=180, file=string_buffer_html_b)
            record_console_html_b.print(box_object)
            results['boxes_html'] = record_console_html_b.export_html(inline_styles=True)
        else:
            results['boxes_txt'] = "Error: Could not generate box layout object."
            results['boxes_html'] = "<h1>Error: Could not generate box layout object.</h1>"

    except Exception as e:
        print(f"Error generating box visualization for {input_path}: {e}", file=sys.stderr)
        results['boxes_txt'] = f"Error generating boxes: {e}"
        results['boxes_html'] = f"<h1>Error generating boxes</h1><p>{e}</p>"


    # --- Save Files ---
    try:
        (output_dir / "dom_hierarchy.txt").write_text(results.get('hierarchy_txt', ''), encoding='utf-8')
        (output_dir / "dom_hierarchy.html").write_text(results.get('hierarchy_html', ''), encoding='utf-8')
        (output_dir / "dom_layout_boxes.txt").write_text(results.get('boxes_txt', ''), encoding='utf-8')
        (output_dir / "dom_layout_boxes.html").write_text(results.get('boxes_html', ''), encoding='utf-8')
        print(f"Successfully generated visualizations for {input_path}") # Print success to stdout
    except Exception as e:
        print(f"Error writing visualization files for {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DOM visualizations from an HTML file.")
    parser.add_argument("html_file", help="Path to the input rendered_dom.html file.")
    args = parser.parse_args()
    main(args.html_file)