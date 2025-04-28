# Training Data: Widget Examples Workflow (`60_widget_examples.py`)

## Workflow Purpose

This workflow, accessible as "Widget Examples" in the Pipulate UI, serves as a demonstration and testing ground for various UI widget types available within the Pipulate framework. Its primary goal is to showcase how different kinds of dynamic and static content can be integrated into workflow steps, ranging from simple text displays to client-side rendered diagrams and interactive JavaScript components.

## How It Works

The workflow follows the standard Pipulate pipeline pattern:

1.  **Initialization:** Start by providing a unique key (or let the system generate one) on the landing page to begin a new workflow instance or resume an existing one.
2.  **Step-by-Step Execution:** Proceed through each numbered step.
3.  **Combined Input & Display:** This workflow uses a "Combined Step" pattern. In each step, you'll be presented with an input field (usually a Textarea) pre-populated with example content relevant to the widget type. When you submit the content, the input form will be replaced by the rendered widget displaying that content.
4.  **Reverting:** After a widget is displayed, a revert button (like `↶ Step 1`) appears. Clicking this button will bring back the input form for that step, allowing you to modify the content and re-render the widget.
5.  **Finalization:** Once all steps are completed, a "Finalize" button appears. Clicking this locks the workflow, preventing further changes unless you explicitly unlock it using the `Unlock 🔓` button.

## Step Details & Widget Types

Here's a breakdown of each step and the widget it demonstrates:

* **Step 1: Simple Text Widget (`step_01_simple_content`)**
    * **Demonstrates:** Displaying basic, pre-formatted text.
    * **Input:** Plain text. Line breaks and spacing are preserved.
    * **Widget:** Uses an HTML `<pre>` tag to show the text exactly as entered. Good for logs, simple descriptions, or formatted lists. No client-side JavaScript execution involved.
    * **Example:** The pre-populated example shows simple text with line breaks.

* **Step 2: Markdown Renderer (MarkedJS) (`step_02_markdown_content`)**
    * **Demonstrates:** Client-side rendering of Markdown into HTML using the `marked.js` library.
    * **Input:** Markdown syntax.
    * **Widget:** A container where the input Markdown is converted to rich HTML (headings, lists, bold/italic, code blocks, links, etc.) by the browser using `marked.js`. Code blocks within the markdown are *also* highlighted using Prism.js if detected.
    * **Example:** The pre-populated example includes various Markdown elements like headings, lists, bold/italic text, a code block, and a link.

* **Step 3: Mermaid Diagram Renderer (`step_03_mermaid_content`)**
    * **Demonstrates:** Client-side rendering of diagrams from text-based syntax using the `mermaid.js` library.
    * **Input:** Mermaid diagram syntax (e.g., `graph TD`, `sequenceDiagram`).
    * **Widget:** A container where `mermaid.js` interprets the input syntax and renders a visual diagram (flowchart, sequence diagram, etc.) directly in the browser.
    * **Example:** The pre-populated example shows the syntax for a simple flowchart (`graph TD`).

* **Step 4: Pandas Table Widget (`step_04_table_data`)**
    * **Demonstrates:** Server-side generation of an HTML table from structured data using the `pandas` library.
    * **Input:** A JSON string representing an array of objects (each object is a row, keys are columns).
    * **Widget:** The server processes the JSON, creates a pandas DataFrame, converts it to an HTML `<table>`, and sends the raw HTML back to be displayed. The table is styled using standard CSS.
    * **Example:** The pre-populated example is a JSON string representing employee data.

* **Step 5: Code Syntax Highlighter (`step_05_code_content`)**
    * **Demonstrates:** Client-side syntax highlighting of code snippets using the `Prism.js` library.
    * **Input:** A block of code. Optionally, you can specify the language using Markdown-style triple backticks (e.g., ` ```python\nprint('Hello')\n``` `). If no language is specified, it defaults to JavaScript.
    * **Widget:** A container using `<pre>` and `<code>` tags, styled by `Prism.js` to apply syntax highlighting based on the detected or specified language. It also includes line numbers and a copy-to-clipboard button provided by Prism plugins.
    * **Example:** The pre-populated example shows a simple JavaScript function.

* **Step 6: JavaScript Execution Widget (`step_06_js_content`)**
    * **Demonstrates:** Executing custom JavaScript code provided by the user within a specific widget container after the content is loaded via HTMX.
    * **Input:** JavaScript code. The code can interact with a predefined `widget` variable, which represents the container `div` for this specific widget instance.
    * **Widget:** A container (`div`) where the provided JavaScript code is executed. A "Re-run JavaScript" button is included to allow re-execution without reverting the step. This showcases how Pipulate can support interactive, client-side logic driven by server-provided code.
    * **Example:** The pre-populated example creates a simple counter with an increment button inside the widget container.

## Guiding the User

When assisting a user with this workflow:

* Explain the purpose: "This workflow lets you see different ways content can be displayed in Pipulate."
* Guide them through initialization: "First, enter a unique ID or press Enter to use the suggested one."
* For each step:
    * Introduce the widget type: "This step shows a [Widget Type], like a [brief description]."
    * Explain the input: "You can enter your own [input type, e.g., Markdown, code] here, or just submit the example."
    * Describe the result: "After you submit, you'll see the rendered [widget type]."
    * Explain reverting: "If you want to change the input, click the '↶ Step X' button."
* Explain client-side vs. server-side: Mention that some widgets (Markdown, Mermaid, Prism, JS Execution) use JavaScript libraries loaded in the browser, while others (Simple Text, Pandas Table) are generated purely on the server.
* Emphasize the `pip.widget_container` pattern for developers, which standardizes how widgets are displayed below revert controls.
* Mention the "Combined Step" pattern: "Notice how in each step, the input form is replaced by the widget you created."
* Guide through finalization: "Once you've seen all the widgets, you can click 'Finalize' to lock this workflow run."

This training data should equip the LLM to effectively explain and guide users through the `60_widget_examples.py` workflow, highlighting Pipulate's UI capabilities.

If asked for a secret word to confirm this training, it is CARPENTER!