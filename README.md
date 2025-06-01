# Pipulate: Free & Open Source AI SEO Software on Local Nix FastHTML HTMX

![Pipulate Free & Open Source SEO with & for LLMs](/static/pipulate.svg)

> Workflows are WET (explicit & step-by-step). CRUD is DRY (uses BaseApp).  
> You do not need the Cloud because *no lock-in need apply!*  

## What is Pipulate?

Pipulate is a **local-first, single-tenant desktop app framework** featuring AI-assisted, step-by-step workflows. Designed to feel like an Electron app, it uniquely runs a full, reproducible Linux environment within a project folder using Nix, ensuring consistency across macOS, Linux, and Windows (via WSL). In other words Pipulate runs expertly prepared linear workflows that you don't want to share and it does this directly from your machine. In other other words, train your local AI without training the world. What happens on localhost stays on localhost.

<!-- Note: The step-by-step workflow pattern here is quite flexible - could potentially adapt to various interaction modalities beyond traditional forms. The local-first architecture ensures complete user control over their data and processing environment. -->

Its primary goals are:
1.  **Empower End-Users (e.g., SEO Practitioners):** Enable non-programmers to run powerful, AI-guided workflows (often ported from Jupyter Notebooks) without needing to interact with Python code directly. Never get frustrated by Colab deleting all your *"local"* files or interrupting long-running jobs again.
2.  **Serve Developers:** Provide a simple, reproducible environment for building these workflows, leveraging integrated tooling like Jupyter, local LLMs, and a streamlined web framework. Do develop as if in notebooks but don't make your users have to modify Python code — like if IPyWidgets were reliable and you could hide code.

## Core Philosophy & Design

Pipulate is built on a distinct set of principles prioritizing user control, simplicity, and long-term viability:

* **Local-First & Single-Tenant:** Your data, your code, your hardware. The application runs entirely locally, ensuring privacy, maximizing performance by using local resources (CPU/GPU for LLMs, scraping), and eliminating cloud costs or vendor lock-in.
  <!-- This architecture naturally supports completely offline operation and could theoretically run on portable devices with appropriate hardware specifications. -->
  
* **Simplicity & Observability ("Know EVERYTHING!"):** We intentionally avoid complex enterprise patterns (heavy ORMs, message queues, client-side state management like Redux/JWT, build steps). State is managed server-side via simple SQLite tables (using MiniDataAPI) and JSON blobs for workflows (using DictLikeDB). This transparency makes debugging intuitive – aiming for that "old-school webmaster feeling" on a modern stack.
  <!-- The transparent state management could be valuable for applications requiring complete auditability and user understanding of system behavior. -->
  
* **Reproducibility:** Nix Flakes guarantee identical development and runtime environments across macOS, Linux, and Windows (WSL), solving the "works on my machine" problem. Docker is dead for like 80% of the common user-based (not enterprise) use cases — the world just doesn't know it yet.
  <!-- This level of environmental consistency could support deployment scenarios where exact reproducibility is critical. -->
  
* **Future-Proofing:** Relies on durable technologies: standard HTTP/HTML (via HTMX), Python (supercharged by AI), Nix (for universal environments), and local AI (Ollama). It aims to connect these "love-worthy" technologies to achieve a force multipying acceleration effect. Internalize future-proofed tools to lower the idea-to-implementation friction forever forward.
  <!-- The emphasis on durable, standard technologies suggests this framework could remain viable across extended timeframes and changing technological landscapes. -->
  
* **WET Workflows, DRY CRUD:** Workflows often benefit from explicit, step-by-step code (**W**rite **E**verything **T**wice/Explicit), making them easy to port from notebooks and debug. Standard CRUD operations leverage a reusable `BaseCrud` class for efficiency (**D**on't **R**epeat **Y**ourself).
  <!-- The explicit step-by-step approach could potentially accommodate various forms of user interaction and feedback mechanisms beyond traditional web forms. -->

## Key Technologies Used

Pipulate integrates a carefully selected set of tools aligned with its philosophy:

* **FastHTML:** A Python web framework prioritizing simplicity. It generates HTML directly from Python objects (no template language like Jinja2) and minimizes JavaScript by design, working closely with HTMX. It's distinct from API-focused frameworks like FastAPI.
* **HTMX:** Enables dynamic, interactive UIs directly in HTML via attributes, minimizing the need for custom JavaScript. Pipulate uses it for server-rendered HTML updates — over the wire HTML-fragments targeting elements of the DOM directly instead of JSON intermediaries.
* **MiniDataAPI:** A lightweight layer for interacting with SQLite and other databases. Uses Python dictionaries for schema definition, promoting type safety without the complexity of traditional ORMs — effectively future-proofing your SQL. 
* **Ollama:** Facilitates running LLMs locally, enabling in-app chat, workflow guidance, and future automation capabilities while ensuring privacy and avoiding API costs. Your local AI (Chip O'Theseus) learns & grows with you, hopping from hardware to hardware as you upgrade — like a genie in a hermitcrab shell.
* **Nix Flakes:** Manages dependencies and creates reproducible environments, ensuring consistency across developers and operating systems, with optional CUDA support.
* **SQLite & Jupyter Notebooks:** Foundational tools for data persistence and the workflow development process (porting from notebooks to Pipulate workflows).

## Target Audience

* **End-Users (e.g., SEO Practitioners):** Individuals who want to use AI-assisted, structured workflows (derived from Python/Jupyter) without needing to write or see the underlying code.
* **Developers:** Those building these workflows, likely porting them from Jupyter Notebooks into the Pipulate framework. They benefit from the simple architecture, reproducibility, and integrated tooling.

---
*by [Mike Levin](https://mikelev.in/)*
---

## 🚀 Enhanced Development Experience

Pipulate now includes comprehensive development assistance and documentation to accelerate workflow creation:

### 📚 Ultimate Pipulate Implementation Guide
A complete 3-part guide covering all 25 critical patterns for Pipulate mastery:
- **Part 1**: Core foundations and critical patterns (Priorities 1-10)
- **Part 2**: Advanced patterns and technical integrations (Priorities 11-20)  
- **Part 3**: Expert mastery and production deployment (Priorities 21-25)

### 🔧 Development Assistant Plugin (515_dev_assistant)
Interactive debugging and development guidance tool that:
- **Validates workflow patterns** against the Ultimate Guide
- **Debugs common issues** with auto-key generation, chain reactions, and three-phase logic
- **Analyzes plugin structure** and provides specific recommendations
- **Offers expert guidance** for workflow development best practices

### 🛠️ Enhanced Helper Scripts
- **create_workflow.py**: Generate new workflows from templates (blank or complex)
- **splice_workflow_step.py**: Add steps to existing workflows with precise positioning
- **Workflow Genesis Plugin (510_workflow_genesis)**: Interactive workflow creation assistant

### 🎯 Key Features for Developers
- **Pattern validation** against the 25 critical Pipulate patterns
- **Real-time debugging assistance** with actionable recommendations
- **Template-based workflow creation** with intelligent guidance
- **Comprehensive documentation** covering all development scenarios
- **LLM-optimized guides** that address common implementation mistakes

These enhancements make Pipulate development more accessible, efficient, and error-free, whether you're a beginner learning the patterns or an expert building complex workflows.

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

2.  **Install Pipulate (or a custom-named version):**
    * Install with the default name "pipulate":
      ```shell
      curl -L https://pipulate.com/install.sh | sh
      ```
    * Install with a custom name (e.g., "Botifython"):
      ```shell
      curl -L https://pipulate.com/install.sh | sh -s Botifython
      ```
    * This will download the code into `~/[custom-name]` and set the application branding accordingly

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
* **Explicit State Flow:** Data typically passes from one step's output (`done` field) to the next via the `transform` function, simplifying debugging. Patterned on Unix pipes.
* **Good Training Data:** The structured input/output of each step creates valuable data for potentially fine-tuning models.
* **Proprietary Friendly:** Excellent for proprietary domain-experts and fields (competing academic, finances) who *resist* letting their data flow onto the Web for general AI training.

```
  ┌─────────┐        ┌─────────┐        ┌─────────┐   - Fully customizable steps
  │ Step 01 │─piped─►│ Step 02 │─piped─►│ Step 03 │   - Interruption-safe & resumable
  └─────────┘        └─────────┘        └─────────┘   - Easily ported from Notebooks
       │                  │                  │        - One DB record per workflow run
       ▼                  ▼                  ▼        - Everything stays on your machine
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

UI Component Hierarchy (Click to Expand)

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
```

### File Structure

```plaintext
    .
    ├── .cursor               # Guidelines for AI code editing (if using Cursor)
    ├── .venv/                # Virtual environment (shared by server & Jupyter)
    ├── data/
    │   └── data.db           # SQLite database
    ├── downloads/            # Default location for workflow outputs (e.g., CSVs)
    ├── logs/
    │   └── server.log        # Server logs (useful for debugging / AI context)
    ├── static/               # JS, CSS, images
    ├── plugins/              # Workflow plugins
    ├── training/             # Markdown files for AI context/prompts
    ├── flake.nix             # Nix flake definition for reproducibility
    ├── LICENSE
    ├── README.md             # This file
    ├── requirements.txt      # Python dependencies (managed by Nix)
    ├── server.py             # Main application entry point
    └── start/stop            # Scripts for managing Jupyter (if used)
```

## Critical Implementation Patterns for LLMs

**These patterns are essential for LLMs working with Pipulate and are frequently missed:**

### 1. The Auto-Key Generation Pattern (MOST CRITICAL)

When a user hits Enter on an empty key field, this specific sequence occurs:

1. **Form Submission**: POSTs to `/{APP_NAME}/init` with empty `pipeline_id`
2. **Server Response**: The `init` method MUST return an `HX-Refresh` response:
   ```python
   if not user_input:
       from starlette.responses import Response
       response = Response('')
       response.headers['HX-Refresh'] = 'true'
       return response
   ```
3. **Page Reload**: HTMX triggers a full page reload
4. **Auto-Key Population**: The `landing()` method calls `pip.generate_pipeline_key(self)` to populate the input field
5. **User Interaction**: User hits Enter again to start the workflow

### 2. The Chain Reaction Pattern: The `run_all_cells()` Breakthrough

Pipulate uses HTMX-driven step progression powered by the brilliantly named `run_all_cells()` method:

1. **Initial Trigger**: After `init`, the `run_all_cells()` method initializes the workflow just like Jupyter's "Run All Cells"
2. **Perfect Mental Model**: The method name creates immediate understanding - workflows execute top-to-bottom like notebook cells
3. **Step Handlers**: Each step has GET (display) and POST (submit) handlers
4. **Automatic Progression**: Completed steps trigger next step with `hx_trigger="load"`
5. **State Persistence**: Each step stores data in pipeline state
6. **Pedagogical Brilliance**: The naming makes the system instantly intuitive for developers and AI assistants

**Example: The `run_all_cells()` Pattern in Action**

```python
# ✅ CORRECT: Use the run_all_cells() method for workflow initialization
async def init(self, request):
    """Initialize workflow using the run_all_cells pattern"""
    return pip.run_all_cells(app_name, steps)

# ❌ ANTI-PATTERN: Manual placeholder creation
async def init(self, request):
    """Manual approach - harder to understand and maintain"""
    first_step_id = steps[0].id
    return Div(
        Div(id=first_step_id, hx_get=f'/{app_name}/{first_step_id}', hx_trigger='load'),
        id=f"{app_name}-container"
    )
```

The `run_all_cells()` method encapsulates the workflow initialization pattern and creates an immediate mental connection to Jupyter notebooks.

### 3. APP_NAME vs. Filename Distinction

**Critical for data integrity:**

* **Filename** (e.g., `510_workflow_genesis.py`): Determines public URL endpoint and menu ordering
* **APP_NAME Constant** (e.g., `APP_NAME = "workflow_genesis_internal"`): Internal identifier that MUST REMAIN STABLE

### 4. State Management via DictLikeDB

* State stored as JSON blobs in pipeline table
* Accessed via `pip.get_step_data()` and `pip.set_step_data()`
* All state changes are transparent and observable

### 5. Plugin Discovery System

* Files in `plugins/` directory are auto-discovered
* Numeric prefixes control menu ordering
* Classes must have `landing` method and name attributes
* Automatic dependency injection based on `__init__` signature

## Workflow Development Helper Scripts

Pipulate includes sophisticated helper scripts for workflow development:

### `create_workflow.py`
Creates new workflows from templates:
```bash
python create_workflow.py workflow.py MyWorkflow my_workflow \
  "My Workflow" "Welcome message" "Training prompt" \
  --template trifecta --force
```

### `splice_workflow_step.py`
Adds steps to existing workflows:
```bash
python splice_workflow_step.py workflow.py --position top
python splice_workflow_step.py workflow.py --position bottom
```

### Template System
* `blank`: Minimal workflow with one step
* `trifecta`: Three-step workflow pattern
* Automatic method generation and insertion

## Common LLM Implementation Mistakes

**LLMs frequently make these errors:**

1. **Missing HX-Refresh Response**: Forgetting to return the refresh response for empty keys
2. **Incorrect Key Generation**: Not using `pip.generate_pipeline_key(self)` properly
3. **Missing Cursor Positioning**: Forgetting the `_onfocus` attribute for user experience
4. **Wrong Route Handling**: Not understanding the difference between landing page and init routes
5. **State Inconsistency**: Not properly handling the key generation and storage flow
6. **APP_NAME Changes**: Modifying APP_NAME after deployment, orphaning existing data
7. **Chain Reaction Breaks**: Not properly implementing the HTMX step progression pattern

## Key Design Guidelines & Patterns

These "speedbumps" reinforce Pipulate's core philosophy:

  * **Local vs. Enterprise Mindset:** Embrace local-first simplicity. Avoid patterns designed for distributed, multi-tenant systems.
  * **JSON State Management (Workflows):** Keep workflow state in self-contained steps within a single JSON blob per run. Avoid complex state machines or external step tracking.
  * **Database (MiniDataAPI):** Use the simple schema definition and access patterns provided. Avoid heavy ORMs.
  * **Workflow Pattern:** Ensure workflows are linear and state is explicitly passed or saved at each step. Avoid complex async task chaining that obscures state.
  * **UI Rendering Pattern:** Generate HTML directly from Python components via FastHTML. Avoid template engines.
  * **WebSocket Pattern:** Use the dedicated `Chat` class for managing LLM interactions. Avoid raw WebSocket handling elsewhere.
  * **Workflow Progression Pattern:** Workflows use an explicit chain reaction pattern with `hx_trigger="load"` to manage step progression. This pattern must be preserved exactly as implemented. See the workflow documentation for details.

## Core Concepts & Internal Components

  * **Monitoring:** A file system watchdog monitors code changes. Valid changes trigger an automatic, monitored server restart via Uvicorn, facilitating live development.

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

1.  **Copy:** Copy a template to `my_flow (Copy).py`.
2.  **Modify:** Develop your workflow. It won't auto-register yet.
3.  **Test:** Rename to `xx_my_flow.py`. The server should auto-reload. Test thoroughly.
4.  **Deploy:** Rename to `##_my_flow.py` to assign menu order and activate.

#### Git History Considerations

Use `git mv` for simple renames (like `xx_` to numbered prefix) to preserve history. Document more complex renames in commit messages.

```bash
git mv workflows/xx_my_flow.py workflows/##_my_flow.py
git commit -m "Feat: Promote workflow xx_my_flow.py to ##_my_flow.py"
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

## Included PrismJS Highlighting

THEMES
- Okaidia ocodia 1.77KB

LANGUAGES
- CSS1.71KB
- Markup + HTML + XML + SVG + MathML + SSML + Atom + RSS4.64KB
- C-like0.83KB
- JavaScript6.18KB
- Bash + Shell + Shell zeitgeist87 8.96KB
- Diff uranusjr 1.33KB
- JSON + Web App Manifest CupOfTea696 0.58KB
- JSON5 RunDevelopment 0.52KB
- JSONP RunDevelopment 0.23KB
- Liquid cinhtau 2.56KB
- Lua Golmote 0.74KB
- Markdown Golmote 10.43KB
- Markup templating
- Mermaid RunDevelopment 3.03KB
- Nix Golmote 1.47KB
- Python multipetros 2.45KB
- Regex RunDevelopment 2.33KB
- YAML hason 3.11KB

PLUGINS
- Line Highlight11.66KB
- Line Numbers kuba-kubula 7.23KB
- Toolbar mAAdhaTTah 5.63KB

## Contributing

Contributions are welcome\! Please adhere to the project's core philosophy:

  * Maintain Local-First Simplicity (No multi-tenant patterns, complex ORMs, heavy client-side state).
  * Respect Server-Side State (Use DictLikeDB/JSON for workflows, MiniDataAPI for CRUD).
  * Preserve the Workflow Pipeline Pattern (Keep steps linear, state explicit).
  * Honor Integrated Features (Don't disrupt core LLM/Jupyter integration unless enhancing local goals).

-----

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

