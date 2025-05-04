# Pipulate: Free & Open Source Local-First SEO *with & for* LLMs

![Pipulate Free & Open Source SEO with & for LLMs](/static/pipulate.svg)

> Workflows are WET (explicit & step-by-step). CRUD is DRY (uses BaseApp).  
> You do not need the Cloud because *no lock-in need apply!*  

## What is Pipulate?

Pipulate is a **local-first, single-tenant desktop app framework** featuring AI-assisted, step-by-step workflows. Designed to feel like an Electron app, it uniquely runs a full, reproducible Linux environment within a project folder using Nix, ensuring consistency across macOS, Linux, and Windows (via WSL).

Its primary goals are:
1.  **Empower End-Users (e.g., SEO Practitioners):** Enable non-programmers to run powerful, AI-guided workflows (often ported from Jupyter Notebooks) without needing to interact with Python code directly.
2.  **Serve Developers:** Provide a simple, reproducible environment for building these workflows, leveraging integrated tooling like Jupyter, local LLMs, and a streamlined web framework.

## Core Philosophy & Design

Pipulate is built on a distinct set of principles prioritizing user control, simplicity, and long-term viability:

* **Local-First & Single-Tenant:** Your data, your code, your hardware. The application runs entirely locally, ensuring privacy, maximizing performance by using local resources (CPU/GPU for LLMs, scraping), and eliminating cloud costs or vendor lock-in.
* **Simplicity & Observability ("Know EVERYTHING!"):** We intentionally avoid complex enterprise patterns (heavy ORMs, message queues, client-side state management like Redux/JWT, build steps). State is managed server-side via simple SQLite tables (using MiniDataAPI) and JSON blobs for workflows (using DictLikeDB). This transparency makes debugging intuitive – aiming for that "old-school webmaster feeling" on a modern stack.
* **Reproducibility:** Nix Flakes guarantee identical development and runtime environments across macOS, Linux, and Windows (WSL), solving the "works on my machine" problem.
* **Future-Proofing:** Relies on durable technologies: standard HTTP/HTML (via HTMX), Python (supercharged by AI), Nix (for universal environments), and local AI (Ollama). It aims to connect these "love-worthy" technologies.
* **WET Workflows, DRY CRUD:** Workflows often benefit from explicit, step-by-step code (**W**rite **E**verything **T**wice/Explicit), making them easy to port from notebooks and debug. Standard CRUD operations leverage a reusable `BaseCrud` class for efficiency (**D**on't **R**epeat **Y**ourself).

## Key Technologies Used

Pipulate integrates a carefully selected set of tools aligned with its philosophy:

* **FastHTML:** A Python web framework prioritizing simplicity. It generates HTML directly from Python objects (no template language like Jinja2) and minimizes JavaScript by design, working closely with HTMX. It's distinct from API-focused frameworks like FastAPI.
* **HTMX:** Enables dynamic, interactive UIs directly in HTML via attributes, minimizing the need for custom JavaScript. Pipulate uses it for server-rendered HTML updates.
* **MiniDataAPI:** A lightweight layer for interacting with SQLite. Uses Python dictionaries for schema definition, promoting type safety without the complexity of traditional ORMs.
* **Ollama:** Facilitates running LLMs locally, enabling in-app chat, workflow guidance, and future automation capabilities while ensuring privacy and avoiding API costs.
* **Nix Flakes:** Manages dependencies and creates reproducible environments, ensuring consistency across developers and operating systems, with optional CUDA support.
* **SQLite & Jupyter Notebooks:** Foundational tools for data persistence and the workflow development process (porting from notebooks to Pipulate workflows).

## Target Audience

* **End-Users (e.g., SEO Practitioners):** Individuals who want to use AI-assisted, structured workflows (derived from Python/Jupyter) without needing to write or see the underlying code.
* **Developers:** Those building these workflows, likely porting them from Jupyter Notebooks into the Pipulate framework. They benefit from the simple architecture, reproducibility, and integrated tooling.

---
*by [Mike Levin](https://mikelev.in/)*
---

## How to Install Pipulate

This guide shows you how to install Pipulate using two main commands in your terminal. This works on macOS or on Windows using WSL (Windows Subsystem for Linux) with an Ubuntu (or similar Linux) terminal.

1.  **Install Nix:**
    * Nix manages the underlying software dependencies and ensures a consistent environment.
    * Open your Terminal.
    * Copy and paste this command, then press Enter:
        ```shell
        curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
        ```
    * Follow any instructions on the screen (you might need to type "Yes").
    * **Important:** After the installation finishes, **close your Terminal window completely and open a new one.** This ensures Nix is correctly added to your system's PATH.

2.  **Install Pipulate:**
    * This command downloads Pipulate into `~/pipulate` (by default), sets up automatic updates via Git, and configures the Nix environment.
    * In the **new** Terminal window you just opened, copy and paste this command, then press Enter:
        ```shell
        curl -L https://pipulate.com/install.sh | sh
        ```
    * This might take some time the first time you run it as Nix downloads dependencies. It should automatically start the necessary services (JupyterLab and the Pipulate server) and open browser tabs when ready.

**That's it! Pipulate is installed.** You now have a self-contained, reproducible environment managed by Nix.

## How to Run Pipulate After Installation

Pipulate uses Nix Flakes to manage its environment. This means you activate the specific environment defined in the `flake.nix` file to run the application and its tools.

1.  Open a Terminal.
2.  Navigate to the Pipulate directory. If you used the default install script, type:
    ```shell
    cd ~/pipulate
    ```
    *(If it was installed elsewhere, change `~/pipulate` to the correct path)*
3.  Activate the Pipulate environment and start the services:
    ```shell
    nix develop
    ```
    * **What this command does:**
        * Checks for updates to the Pipulate code via `git pull`.
        * Enters the Nix environment defined in `flake.nix`, making all necessary tools (Python, system libraries, etc.) available.
        * Executes the `shellHook` defined in `flake.nix`, which:
            * Sets up the Python virtual environment (`.venv`).
            * Installs/updates Python packages from `requirements.txt` using `pip`.
            * Starts JupyterLab in the background (via `tmux`).
            * Starts the Pipulate server (`server.py`) in the foreground.
    * Your browser should open automatically to `http://localhost:5001` (Pipulate) and `http://localhost:8888` (JupyterLab).
    * Press `Ctrl+C` in the terminal to stop the Pipulate server (and the `nix develop` session). JupyterLab will continue running in the background.
    * To stop *all* services (including JupyterLab), you can run `pkill tmux` in a separate terminal.

## Developer Setup & Environment Notes

* **Nix Environment Activation:** Always run `nix develop` from the `~/pipulate` directory *before* running any project commands (`python server.py`, `pip install`, etc.) in a new terminal. This ensures you are using the correct dependencies defined in `flake.nix`.
* **Interactive vs. Quiet Shell:**
    * `nix develop` (or `nix develop .#default`): Standard interactive shell, runs the startup script (`run-script` defined in `flake.nix`) with welcome messages and service startup. Ideal for general use.
    * `nix develop .#quiet`: Activates the Nix environment *without* running the full startup script or launching services automatically. It only sets up paths and installs pip requirements. Use this for:
        * Running specific commands without starting the servers (e.g., `nix develop .#quiet --command python -c "import pandas"`).
        * Debugging or interacting with AI assistants where verbose startup output is undesirable.
        * Manually running `run-server` or `run-jupyter` (scripts placed in `.venv/bin` by the `shellHook`).
* **Dependencies:** System-level dependencies (Python version, libraries like `gcc`, `zlib`) are managed by `flake.nix`. Python package dependencies are managed by `pip` using `requirements.txt` within the Nix-provided environment.
* **Source of Truth:** The `flake.nix` file is the definitive source for the development environment setup.

---

## Architecture & Key Concepts

Pipulate features a distinct architecture designed for its local-first, simple, and observable nature.

### Architecture Overview Diagram

This diagram illustrates the high-level components and their interactions:

```
                 ┌─────────────┐ Like Electron, but full Linux subsystem 
                 │   Browser   │ in a folder for macOS and Windows (WSL)
                 └─────┬───────┘
                       │ HTTP/WS
                       ▼
    ┌───────────────────────────────────────┐
    │           Nix Flake Shell             │ - In-app LLM (where it belongs)
    │  ┌───────────────┐  ┌──────────────┐  │ - 100% reproducible
    │  │   FastHTML    │  │    Ollama    │  │ - 100% local
    │  │   HTMX App    │  │  Local LLM   │  │ - 100% multi-OS    
    │  └───────┬───────┘  └──────────────┘  │
    │          │                            │
    │    ┌─────▼─────┐     ┌────────────┐   │
    │    │MiniDataAPI│◄───►│ SQLite DB  │   │
    │    └───────────┘     └────────────┘   │
    └───────────────────────────────────────┘
```

### Integrated Data Science Environment

Jupyter Notebooks run alongside the FastHTML server, allowing developers to prototype workflows in a familiar environment before porting them to Pipulate's step-based interface for end-users. The same Python virtual environment (`.venv`) is shared, and ad-hoc package installation is supported.

```
      ┌──────────────────┐    ┌──────────────────┐
      │   Jupyter Lab    │    │    FastHTML      │
      │   Notebooks      │    │     Server       │
      │ ┌──────────┐     │    │  ┌──────────┐    │
      │ │ Cell 1   │     │    │  │ Step 1   │    │
      │ │          │     │--->│  │          │    │
      │ └──────────┘     │    │  └──────────┘    │
      │ ┌──────────┐     │    │  ┌──────────┐    │
      │ │ Cell 2   │     │    │  │ Step 2   │    │
      │ │          │     │--->│  │          │    │
      │ └──────────┘     │    │  └──────────┘    │
      │  localhost:8888  │    │  localhost:5001  │
      └──────────────────┘    └──────────────────┘
```

### Local-First & Single-Tenant Details

Pipulate manages all state server-side within the local environment, avoiding cloud dependencies. This approach offers:
* **Privacy & Control:** Data never leaves the user's machine.
* **Full Resource Access:** Utilize local CPU/GPU freely for intensive tasks (scraping, 24/7 AI processing) at minimal cost.
* **Simplicity:** Eliminates complexities associated with multi-tenancy, cloud deployment, and distributed state.
* **Observability:** State changes (via DictLikeDB/JSON) are transparent and easily logged.

```
      ┌───────────────────────────────┐ # Benefits of Local-First Simplicity
      │          Web Browser          │
      │                               │ - No mysterious client-side state
      │    ┌────────────────────┐     │ - No full-stack framework churn
      │    │   Server Console   │     │ - No complex ORM or SQL layers
      │    │     & Web Logs     │     │ - No external message queues
      │    └─────────┬──────────┘     │ - No build step required
      │              ▼                │ - Direct, observable state changes
      │    ┌─────────────────────┐    │
      │    │  Server-Side State  │    │ 
      │    │  DictLikeDB + JSON  │ ◄─── (Conceptually like server-side cookies)
      │    └─────────────────────┘    │ - Enables the "Know EVERYTHING!" philosophy
      └───────────────────────────────┘
```

### Server-Rendered UI (HTMX)

The UI is constructed primarily with server-rendered HTML fragments delivered via HTMX. This minimizes client-side JavaScript complexity.
* FastHTML generates HTML components directly from Python.
* HTMX handles partial page updates based on user interactions, requesting new HTML snippets from the server.
* WebSockets and Server-Sent Events (SSE) provide real-time updates (e.g., for chat, live development reloading).

```
                    HTMX+Python enables a world-class
                   Python front-end Web Development environment.
                             ┌─────────────────────┐
                             │    Navigation Bar   │  - No template language (like Jinja2)
                             ├─────────┬───────────┤  - HTML elements are Python functions
  Simple Python back-end     │  Main   │   Chat    │  - Minimal custom JavaScript
  HTMX "paints" HTML into    │  Area   │ Interface │  - No React/Vue/Angular overhead
  the DOM on demand──────►   │         │           │  - No virtual DOM, JSX, Redux, etc.
                             └─────────┴───────────┘
```

### Pipeline Workflows

Designed for porting notebook-style processes, workflows are sequences of steps where the state is managed explicitly at each stage and stored persistently (typically as a JSON blob in the `pipeline` table).
* **Resumable & Interrupt-Safe:** Because each step's completion is recorded, workflows can be stopped and resumed.
* **Explicit State Flow:** Data typically passes from one step's output (`done` field) to the next via the `transform` function, simplifying debugging.
* **Good Training Data:** The structured input/output of each step creates valuable data for potentially fine-tuning models.

```
  ┌─────────┐        ┌─────────┐        ┌─────────┐   - Fully customizable steps
  │ Step 01 │─piped─►│ Step 02 │─piped─►│ Step 03 │   - Interruption-safe & resumable
  └─────────┘        └─────────┘        └─────────┘   - Easily ported from Notebooks
       │                  │                  │        - One DB record per workflow run
       ▼                  ▼                  ▼
    State Saved        State Saved        Finalized?
```

### LLM Integration (Ollama)

Integration with a local Ollama instance provides AI capabilities without external API calls:
* **Privacy:** Prompts and responses stay local.
* **Cost-Effective:** No per-token charges; run continuously using local resources.
* **Streaming Support:** Real-time interaction via WebSockets.
* **Bounded Context:** Manages conversation history effectively.
* **Tool Calling:** Can interpret structured JSON from the LLM to execute functions.

```
                   ┌──────────────────┐
                   │   Local Ollama   │ - No API keys needed
                   │      Server      │ - Completely private processing
                   └────────┬─────────┘
                            │ Streaming via WebSocket
                            ▼
                   ┌──────────────────┐
                   │   Pipulate App   │ - Monitors WS for JSON/commands
                   │(WebSocket Client)│ - Parses responses in real-time
                   └────────┬─────────┘
                            │ In-memory or DB backed
                            ▼
                   ┌──────────────────┐
                   │     Bounded      │ - Manages context window (~128k)
                   │   Chat History   │ - Enables RAG / tool integration
                   └──────────────────┘
```

### Multi-OS & CUDA Support (Nix)

Nix Flakes ensure a consistent environment across Linux, macOS, and Windows (via WSL), optionally leveraging CUDA GPUs if detected.

```
                   ┌──────────────────┐
                   │  Linux / macOS   │ - Write code once, run anywhere
                   │  Windows (WSL)   │ - Consistent dev environment via Nix
                   └────────┬─────────┘
                            │ Nix manages dependencies
                            ▼
                   ┌──────────────────┐
                   │   CUDA Support   │ - Auto-detects NVIDIA GPU w/ CUDA
                   │   (if present)   │ - Uses GPU for LLM acceleration
                   └──────────────────┘   - Falls back to CPU if no CUDA
```

### UI Layout

The application interface is organized into distinct areas:

```
    ┌─────────────────────────────┐
    │        Navigation           │ (Profiles, Apps, Search)
    ├───────────────┬─────────────┤
    │               │             │
    │    Main Area  │    Chat     │ (Workflow/App UI)
    │   (Pipeline)  │  Interface  │ (LLM Interaction)
    │               │             │
    ├───────────────┴─────────────┤
    │        Poke Button          │ (Quick Action)
    └─────────────────────────────┘
```

<details>
<summary>UI Component Hierarchy (Click to Expand)</summary>

```
home (Root Component)
    |
    +-- create_outer_container
        |
        +-- create_nav_group
        |   |
        |   +-- create_nav_menu
        |       |
        |       +-- create_profile_menu
        |       +-- create_app_menu
        |
        +-- create_grid_left
            |
        +-- create_notebook_interface (Displays steps/cells)
                |
                +-- render_notebook_cells()
                    |
                    +-- render_notebook_cell(step_01)
                    +-- render_notebook_cell(step_02)
                    +-- ...
        |
        +-- create_chat_interface
            |
            +-- mk_chat_input_group
        |
        +-- create_poke_button
```

</details>

### Communication Channels

Pipulate uses standard web technologies for real-time updates:

* **WebSockets:** Bidirectional communication, primarily used for streaming LLM interactions (user-to-LLM prompts, LLM-to-user responses, potential tool calls).
* **Server-Sent Events (SSE):** Unidirectional (server-to-client) communication used for pushing UI updates triggered by server-side state changes or live reloading during development.

### File Structure

The project aims for a flat, understandable structure:

```plaintext
    .
    ├── .venv/                # Virtual environment (shared by server & Jupyter)
    ├── apps/                 # CRUD application plugins (e.g., profiles_app.py)
    ├── data/
    │   └── data.db           # SQLite database
    ├── downloads/            # Default location for workflow outputs (e.g., CSVs)
    ├── logs/
    │   └── server.log        # Server logs (useful for debugging / AI context)
    ├── static/               # JS, CSS, images
    ├── training/             # Markdown files for AI context/prompts
    ├── workflows/            # Workflow plugins (e.g., hello_flow.py)
    ├── .cursorrules          # Guidelines for AI code editing (if using Cursor)
    ├── flake.nix             # Nix flake definition for reproducibility
    ├── LICENSE
    ├── README.md             # This file
    ├── requirements.txt      # Python dependencies (managed by Nix)
    ├── server.py             # Main application entry point
    └── start/stop            # Scripts for managing Jupyter (if used)
```

-----

## Key Design Guidelines & Patterns

These "speedbumps" reinforce Pipulate's core philosophy:

  * **Local vs. Enterprise Mindset:** Embrace local-first simplicity. Avoid patterns designed for distributed, multi-tenant systems.
  * **JSON State Management (Workflows):** Keep workflow state in self-contained steps within a single JSON blob per run. Avoid complex state machines or external step tracking.
  * **Database (MiniDataAPI):** Use the simple schema definition and access patterns provided. Avoid heavy ORMs.
  * **Workflow Pattern:** Ensure workflows are linear and state is explicitly passed or saved at each step. Avoid complex async task chaining that obscures state.
  * **UI Rendering Pattern:** Generate HTML directly from Python components via FastHTML. Avoid template engines.
  * **WebSocket Pattern:** Use the dedicated `Chat` class for managing LLM interactions. Avoid raw WebSocket handling elsewhere.
  * **Workflow Progression Pattern:** Workflows use an explicit chain reaction pattern with `hx_trigger="load"` to manage step progression. This pattern must be preserved exactly as implemented. See the workflow documentation for details.

-----

## Core Concepts & Internal Components

Pipulate uses two main patterns for adding functionality:

1.  **CRUD Apps (`BaseCrud`):** For standard data management tasks (Create, Read, Update, Delete). Inherit from `BaseCrud` provided by the framework. Examples: `profiles_app.py`, `todo_app.py`.
2.  **Workflows (No Superclass):** For linear, step-by-step processes, often ported from Jupyter Notebooks. These are plain Python classes following a specific convention (steps list, `step_XX` / `step_XX_submit` methods). Example: `hello_flow.py`, `botify_export.py`.

New apps/workflows placed in the `plugins/` directory are automatically discovered and added to the UI navigation.

-----

## Understanding FastHTML & MiniDataAPI

These are key libraries underpinning Pipulate.

### FastHTML vs. FastAPI

FastHTML is chosen for its radical simplicity in building server-rendered UIs with HTMX, *not* for building high-performance JSON APIs like FastAPI. If your goal is a traditional API, FastAPI is likely a better choice. If your goal is a highly interactive, server-rendered UI with minimal JavaScript, FastHTML excels.

<details>
<summary>FastHTML Code Examples (Click to Expand)</summary>

### Minimal Example

```python
from fasthtml.common import *

app, rt = fast_app()

@rt('/')
def get():
    return HTML(
        Body(
            Main(
                H1("Welcome to FastHTML!"),
                P("Creating clean web pages with minimal Python code.")
            )
        )
    )

serve()
```

### HTMX Integration Example

```python
from fasthtml.common import *

app, rt = fast_app()

@rt('/')
def get():
    return HTML(
        Body(
            Main(
                H1("Interactive Example"),
                Input(
                    name="username", 
                    placeholder="Enter your name", 
                    hx_post="/welcome", 
                    hx_target="#welcome-msg", 
                    hx_swap="innerHTML"
                ),
                Div(id="welcome-msg")
            )
        )
    )

@rt('/welcome', methods=['POST'])
def welcome(username: str = ""):
    return P(f"Welcome {username}!")
```

### MiniDataAPI Example

```python
from fasthtml.common import *

# Create app with SQLite database
app, rt, users, User = fast_app('data.db', users={'username': str})

@rt('/')
def get():
    return HTML(
        Body(
            Main(
                H1("User List"),
                Form(
                    Input(name="username", placeholder="New user"),
                    Button("Add", type="submit"),
                    hx_post="/add-user",
                    hx_target="#user-list",
                    hx_swap="innerHTML"
                ),
                Ul(
                    id="user-list",
                    *[Li(user.username) for user in users()]
                )
            )
        )
    )

@rt('/add-user', methods=['POST'])
def add_user(username: str = ""):
    if username:
        users.insert(username=username)
    return Ul(*[Li(user.username) for user in users()])
```

</details>

### MiniDataAPI Spec

MiniDataAPI provides simple, dictionary-based interaction with SQLite tables.

  * **Philosophy:** Avoids ORM complexity.
  * **Operations:** `insert()`, `update()`, `delete()`, `.xtra()` (for filtering/ordering), `()` (for fetching).
  * **Type Safety:** Uses paired dataclasses (like `Task` for the `tasks` table object) generated by `fast_app`.

### The `fast_app` Helper

The `fast_app` function in FastHTML is a powerful (and unconventional) helper for setting up the application, router, and database connections.

```python
# Example unpacking from server.py
app, rt, (store, Store), (tasks, Task), (profiles, Profile), (pipeline, Pipeline) = fast_app(
    "data/data.db",  # DB file path
    # Other config like hdrs, live, exts...
    # Schema definitions as keyword arguments:
    store={'key': str, 'value': str, 'pk': 'key'},
    task={'id': int, 'name': str, 'done': bool, 'pk': 'id'},
    profile={'id': int, 'name': str, 'pk': 'id'},
    pipeline={'url': str, 'app_name': str, 'data': str, 'pk': 'url'}
)
```

**Unpacking Explained:**
`fast_app` returns a tuple. We use Python's tuple unpacking:

1.  `app`: The core application instance (like Flask/Starlette/FastAPI).
2.  `rt`: The route decorator (`@rt('/path')`).
3.  `(table_obj, TableClass)` pairs: For each keyword argument defining a table schema (like `task={...}`), `fast_app` returns a tuple containing:
      * The **table object** (e.g., `tasks`) for DB operations (`tasks.insert(...)`).
      * The **dataclass** (e.g., `Task`) representing a row (`Task(...)`).

The order of these pairs in the returned tuple matches the order of the keyword arguments defining the schemas. See the [FastHTML source for `fast_app`](https://github.com/AnswerDotAI/fasthtml/blob/main/fasthtml/fastapp.py) and [this blog post on unpacking](https://mikelev.in/futureproof/unpacking-fasthtml-databases/) for deeper dives.

-----

## Persistence & Monitoring

  * **Persistence:** State for workflows is stored in the `pipeline` table (managed by DictLikeDB), while CRUD apps use tables defined via MiniDataAPI (like `profile`, `task`). All data resides in the local `data/data.db` SQLite file.
  * **Monitoring:** A file system watchdog monitors code changes. Valid changes trigger an automatic, monitored server restart via Uvicorn, facilitating live development.

<!-- end list -->

```
        ┌─────────────┐         ┌──────────────┐
        │ File System │ Changes │  AST Syntax  │ Checks Code
        │  Watchdog   │ Detects │   Checker    │ Validity
        └──────┬──────┘         └───────┬──────┘
               │ Valid Change           │
               ▼                        ▼
 ┌───────────────────────────┐     ┌──────────┐
 │    Uvicorn Server         │◄─── │  Reload  │ Triggers Restart
 │ (Handles HTTP, WS, SSE)   │     │ Process  │
 └───────────────────────────┘     └──────────┘
```

-----

## Final Thoughts

Pipulate offers a unique approach to building local, AI-assisted applications, prioritizing simplicity, user control, and reproducibility over conventional scaling patterns. By understanding its core concepts and embracing its philosophy, developers can create powerful workflows, and end-users can benefit from AI guidance without cloud dependencies.

Remember the guiding principles:

1.  **Keep it simple.**
2.  **Stay local and single-user.**
3.  **Embrace the unconventional.**

-----

## Developer's Notes

### The Pipulate Workshop

The repository includes not only polished plugins but also experimental scripts and notebooks under development (e.g., in the root directory or marked with `xx_` prefix in plugin directories). These represent ongoing work and exploration.

### Plugin Development Conventions

#### Auto-Registration Behavior

  * **Numeric Prefixes:** Files like `workflows/10_hello_flow.py` are registered as `hello_flow` (number stripped for internal name, used for menu order).
  * **Parentheses Skip:** Files with `()` in the name (e.g., `hello_flow (Copy).py`) are skipped – useful for temporary copies during development.
  * **`xx_` Prefix Skip:** Files prefixed with `xx_` (e.g., `xx_experimental_flow.py`) are skipped – useful for keeping unfinished work in the plugin directories without activating it.

#### Workflow for Creating New Plugins

1.  **Copy:** Copy a template (e.g., `starter_flow.py`) to `my_flow (Copy).py`.
2.  **Modify:** Develop your workflow. It won't auto-register yet.
3.  **Test:** Rename to `xx_my_flow.py`. The server should auto-reload. Test thoroughly.
4.  **Deploy:** Rename to `##_my_flow.py` (e.g., `30_my_flow.py`) to assign menu order and activate.

#### Git History Considerations

Use `git mv` for simple renames (like `xx_` to numbered prefix) to preserve history. Document more complex renames in commit messages.

```bash
git mv workflows/xx_my_flow.py workflows/30_my_flow.py
git commit -m "Feat: Promote workflow xx_my_flow.py to 30_my_flow.py"
```

-----

## Roadmap

**Core & Workflow Enhancements:**

  * Dev, Test, and Prod database switching
  * Saving source HTML and rendered DOM of any URL
  * Botify data export CSV save (incorporating robust polling)
  * Full web form field support (textarea, dropdown, checkboxes, radio buttons)
  * Generic support for Anywidgets
  * Utility for deleting garbage tables from plugin experimentation

**AI / LLM Integration:**

  * LLM inspection of any local data object (RAG-style functionality)
  * Various memory types for LLM context (vector embedding, graph, key/val-store)
  * Enabling the local LLM to be an MCP Client

**Automation & External Interaction:**

  * MCP Server for automated web browsing and similar tasks

-----

## Contributing

Contributions are welcome\! Please adhere to the project's core philosophy:

  * Maintain Local-First Simplicity (No multi-tenant patterns, complex ORMs, heavy client-side state).
  * Respect Server-Side State (Use DictLikeDB/JSON for workflows, MiniDataAPI for CRUD).
  * Preserve the Workflow Pipeline Pattern (Keep steps linear, state explicit).
  * Honor Integrated Features (Don't disrupt core LLM/Jupyter integration unless enhancing local goals).

-----

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

