"""
=============================================================================
Botify CSV Export Workflow
=============================================================================

Core functionality for exporting Botify data to CSV files with:
- Project URL validation
- Analysis selection
- Depth calculation
- Field selection
- Export job management
- Download handling

The workflow is organized into these main sections:
1. Core Setup & Configuration
2. Step Handlers (step_01 through step_04)
3. Export Job Management
4. File & Directory Management
5. API Integration
6. UI Helper Functions
7. State Management
"""

# ============================================================================
# 1. IMPORTS & CONFIGURATION
# ============================================================================

import asyncio
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse
import httpx
from pathlib import Path
import json
import os

from fasthtml.common import *
from loguru import logger

# Core configuration
EXPORT_REGISTRY_FILE = Path("downloads/export_registry.json")
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))

# ============================================================================
# 2. CORE CLASS & INITIALIZATION
# ============================================================================

class BotifyExport:
    """
    Botify CSV Export Workflow
    
    This workflow helps users export data from Botify projects and download it as CSV files.
    It demonstrates usage of rich UI components like directory trees alongside standard
    form inputs and revert controls.
    
    Implementation Note on Tree Displays:
    ------------------------------------
    The tree display for file paths uses the standardized pip.revert_control_advanced method,
    which provides consistent styling and layout for displaying additional content below
    the standard revert controls. This ensures proper alignment with revert buttons 
    while maintaining visual grouping.
    
    Example usage:
    ```python
    tree_display = pip.tree_display(tree_path)
    content_container = pip.revert_control_advanced(
        step_id=step_id,
        app_name=app_name,
        message=display_msg,
        content=tree_display,
        steps=steps
    )
    ```
    
    This standardized pattern eliminates the need for workflow-specific spacing adjustments
    and ensures consistent styling across the application.
    """
    APP_NAME = "botify_csv"
    DISPLAY_NAME = "Botify CSV Export"
    ENDPOINT_MESSAGE = (
        "This workflow helps you export data from Botify projects. "
        "Press Enter to start a new workflow or enter an existing key to resume. "
    )
    TRAINING_PROMPT = "botify_export.md"
    PRESERVE_REFILL = True

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow.
        
        This method sets up the workflow by:
        1. Storing references to app, pipulate, pipeline, and database
        2. Defining the ordered sequence of workflow steps
        3. Registering routes for standard workflow methods
        4. Registering custom routes for each step
        5. Creating step messages for UI feedback
        6. Adding a finalize step to complete the workflow
        
        Args:
            app: The FastAPI application instance
            pipulate: The Pipulate helper instance
            pipeline: The pipeline database handler
            db: The request-scoped database dictionary
            app_name: Optional override for the workflow app name
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        # Create message queue for ordered streaming
        self.message_queue = pip.message_queue

        # Customize the steps, it's like one step per cell in the Notebook
        steps = [
            Step(id='step_01', done='url', show='Botify Project URL', refill=True),
            Step(id='step_02', done='analysis', show='Analysis Selection', refill=False),
            Step(id='step_03', done='depth', show='Maximum Click Depth', refill=False),
            Step(id='step_04', done='export_url', show='CSV Export', refill=False),
        ]

        # Defines routes for standard workflow method (do not change)
        routes = [
            (f"/{app_name}", self.landing),
            (f"/{app_name}/init", self.init, ["POST"]),
            (f"/{app_name}/jump_to_step", self.jump_to_step, ["POST"]),
            (f"/{app_name}/revert", self.handle_revert, ["POST"]),
            (f"/{app_name}/finalize", self.finalize, ["GET", "POST"]),
            (f"/{app_name}/unfinalize", self.unfinalize, ["POST"]),
        ]

        # Defines routes for each custom step (do not change)
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f"/{app_name}/{step_id}", getattr(self, step_id)))
            routes.append((f"/{app_name}/{step_id}_submit", getattr(self, f"{step_id}_submit"), ["POST"]))

        # Register the routes (do not change)
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ["GET"]
            app.route(path, methods=method_list)(handler)

        # Add routes for CSV export functionality
        app.route(f"/{app_name}/download_csv", methods=["POST"])(self.download_csv)
        app.route(f"/{app_name}/download_progress")(self.download_progress)
        app.route(f"/{app_name}/download_job_status")(self.download_job_status)
        app.route(f"/{app_name}/use_existing_export", methods=["POST"])(self.use_existing_export)
        app.route(f"/{app_name}/step_04/new")(self.step_04_new)
        app.route(f"/{app_name}/check_export_status", methods=["POST"])(self.check_export_status)
        app.route(f"/{app_name}/download_ready_export", methods=["POST"])(self.download_ready_export)

        # Define messages for finalize (you can change these)
        self.step_messages = {
            "finalize": {
                "ready": "All steps complete. Ready to finalize workflow.",
                "complete": f"Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes."
            }
        }

        # Creates a default message for each step (you can change these)
        for step in steps:
            self.step_messages[step.id] = {
                "input": f"{pip.fmt(step.id)}: Please enter {step.show}.",
                "complete": f"{step.show} complete. Continue to next step."
            }

        # Add a finalize step to the workflow (do not change)
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

# ============================================================================
# 3. WORKFLOW STEP HANDLERS
# ============================================================================

    # -----------------
    # Step 1: Project URL
    # -----------------
    async def step_01(self, request):
        """Handle project URL input"""
        # ... existing step_01 code ...

    async def step_01_submit(self, request):
        """Process project URL submission"""
        # ... existing step_01_submit code ...

    # -----------------
    # Step 2: Analysis Selection
    # -----------------
    async def step_02(self, request):
        """Handle analysis selection"""
        # ... existing step_02 code ...

    async def step_02_submit(self, request):
        """Process analysis selection submission"""
        # ... existing step_02_submit code ...

    # -----------------
    # Step 3: Maximum Click Depth
    # -----------------
    async def step_03(self, request):
        """Handle maximum click depth selection"""
        # ... existing step_03 code ...

    async def step_03_submit(self, request):
        """Process click depth submission"""
        # ... existing step_03_submit code ...

    # -----------------
    # Step 4: Export Configuration
    # -----------------
    async def step_04(self, request):
        """Handle export configuration"""
        # ... existing step_04 code ...

    async def step_04_submit(self, request):
        """Process export configuration submission"""
        # ... existing step_04_submit code ...

    async def step_04_new(self, request):
        """Handle new export creation"""
        # ... existing step_04_new code ...

    async def use_existing_export(self, request):
        """Handle using an existing export"""
        # ... existing use_existing_export code ...

# ============================================================================
# 4. EXPORT JOB MANAGEMENT
# ============================================================================

    def get_export_key(self, org, project, analysis, depth):
        """Generate unique export key"""
        return f"{org}_{project}_{analysis}_depth_{depth}"

    def load_export_registry(self):
        """Load the export registry from file"""
        try:
            if EXPORT_REGISTRY_FILE.exists():
                with open(EXPORT_REGISTRY_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading export registry: {e}")
            return {}

    def save_export_registry(self, registry):
        """Save the export registry to file"""
        try:
            # Create directory if it doesn't exist
            EXPORT_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(EXPORT_REGISTRY_FILE, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving export registry: {e}")

    def register_export_job(self, org, project, analysis, depth, job_url, job_id):
        """Register a new export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        
        # Check if this export already exists
        if export_key not in registry:
            registry[export_key] = []
        
        # Add the new job
        registry[export_key].append({
            'job_url': job_url,
            'job_id': job_id,
            'status': 'PROCESSING',
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'download_url': None,
            'local_file': None
        })
        
        self.save_export_registry(registry)
        return export_key

    def update_export_job(self, org, project, analysis, depth, job_id, updates):
        """Update an existing export job in the registry"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        
        if export_key not in registry:
            logger.error(f"Export key {export_key} not found in registry")
            return False
        
        for job in registry[export_key]:
            if job['job_id'] == job_id:
                job.update(updates)
                job['updated'] = datetime.now().isoformat()
                self.save_export_registry(registry)
                return True
        
        logger.error(f"Job ID {job_id} not found for export key {export_key}")
        return False

    def find_export_jobs(self, org, project, analysis, depth):
        """Find all export jobs for a specific configuration"""
        registry = self.load_export_registry()
        export_key = self.get_export_key(org, project, analysis, depth)
        return registry.get(export_key, [])

    def find_downloaded_analyses(self, org, project):
        """Find downloaded analyses for org/project"""
        registry = self.load_export_registry()
        downloaded_analyses = set()
        
        # Look for keys that match this org and project
        for key in registry.keys():
            if key.startswith(f"{org}_{project}_"):
                # Extract analysis name from the key (format: org_project_analysis_depth_X)
                parts = key.split('_')
                if len(parts) >= 3:
                    analysis = parts[2]
                    # Check if any job for this analysis has been downloaded
                    for job in registry[key]:
                        if job.get('status') == 'DONE' and job.get('local_file'):
                            downloaded_analyses.add(analysis)
                            break
        
        return list(downloaded_analyses)

# ============================================================================
# 5. FILE & DIRECTORY MANAGEMENT
# ============================================================================

    async def create_download_directory(self, org, project, analysis):
        """Create a nested directory structure for downloads"""
        download_path = Path("downloads") / org / project / analysis
        download_path.mkdir(parents=True, exist_ok=True)
        return download_path

    def format_path_as_tree(self, path_str):
        """
        Format a file path as a proper hierarchical ASCII tree with single path.
        
        This tree visualization is used in various places in the UI to show 
        download locations. The styling of the tree display is carefully tuned
        in each context where it appears.
        """
        path = Path(path_str)
            
        # Get the parts of the path
        parts = list(path.parts)
        
        # Build the tree visualization
        tree_lines = []
        
        # Root or first part
        if parts and parts[0] == '/':
            tree_lines.append('/')
            parts = parts[1:]
        elif len(parts) > 0:
            tree_lines.append(parts[0])
            parts = parts[1:]
        
        # Track the current level of indentation
        indent = ""
        
        # Add nested branches for each directory level
        for part in parts:
            tree_lines.append(f"{indent}└─{part}")
            # Increase indentation for next level, using spaces to align
            indent += "    "
            
        return '\n'.join(tree_lines)

    async def download_csv(self, request):
        """Handle CSV file download"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        
        if not pipeline_id:
            return P("Missing pipeline_id parameter", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Extract necessary information
        download_url = step_data.get('download_url')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        job_id = step_data.get('job_id', 'unknown')
        
        if not download_url:
            # Check if the job is complete and get the download URL
            try:
                job_url = step_data.get(step.done)
                if not job_url:
                    return P("No job URL found", style=pip.get_style("error"))
                    
                api_token = self.read_api_token()
                is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
                
                if not is_complete or not download_url:
                    return Div(
                        P("Export job is still processing. Please try again in a few minutes.", style="margin-bottom: 1rem;"),
                        Progress(value="60", max="100", style="width: 100%;"),
                        P(f"Error: {error}" if error else "", style=pip.get_style("error"))
                    )
                    
                # Update state with download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
            except Exception as e:
                return P(f"Error checking job status: {str(e)}", style=pip.get_style("error"))
        
        # Create the download directory
        try:
            download_dir = await self.create_download_directory(org, project, analysis)
            
            # Generate filename based on depth and fields included
            include_fields = step_data.get('include_fields', {})
            fields_suffix = "_".join(k for k, v in include_fields.items() if v)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv"
            
            local_file_path = download_dir / filename
            
            # Start downloading with progress feedback
            await self.message_queue.add(pip, f"Starting download from {download_url}", verbatim=True)
            
            # Show download progress
            return Div(
                Card(
                    H4("Downloading CSV File"),
                    P(f"Downloading export to {local_file_path}", style="margin-bottom: 1rem;"),
                    Progress(value="10", max="100", style="width: 100%;"),
                    P("Please wait, this may take a few minutes for large files...", 
                      style="font-size: 0.9em; color: #666;")
                ),
                hx_get=f"/{app_name}/download_progress",
                hx_trigger="load",
                hx_target=f"#{step_id}",
                hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}',
                id=step_id
            )
        except Exception as e:
            return P(f"Error preparing download: {str(e)}", style=pip.get_style("error"))

    async def download_progress(self, request):
        """Handle download progress tracking"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        
        # Get request data
        pipeline_id = request.query_params.get("pipeline_id")
        download_url = request.query_params.get("download_url")
        local_file = request.query_params.get("local_file")
        
        if not all([pipeline_id, download_url, local_file]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        local_file_path = Path(local_file)
        
        try:
            # Perform the actual download
            api_token = self.read_api_token()
            headers = {"Authorization": f"Token {api_token}"}
            
            # Create parent directories if they don't exist
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file using httpx with streaming
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", download_url, headers=headers, follow_redirects=True) as response:
                    response.raise_for_status()
                    
                    # Get content length if available
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # Open file for writing
                    with open(local_file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            # Check if file needs to be unzipped
            if local_file_path.suffix.lower() in ('.zip', '.gz'):
                await self.message_queue.add(pip, f"Extracting {local_file_path}", verbatim=True)
                
                extracted_path = None
                # Unzip the file (implementation depends on file type)
                if local_file_path.suffix.lower() == '.zip':
                    import zipfile
                    
                    with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                        # Get the first CSV file in the archive
                        csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
                        if not csv_files:
                            return P("No CSV files found in the downloaded ZIP archive", style=pip.get_style("error"))
                        
                        # Extract the CSV file
                        csv_file = csv_files[0]
                        extracted_path = local_file_path.parent / csv_file
                        zip_ref.extract(csv_file, local_file_path.parent)
                
                elif local_file_path.suffix.lower() == '.gz':
                    import gzip
                    import shutil
                    
                    # Assume it's a .csv.gz file and create a .csv file
                    extracted_path = local_file_path.with_suffix('')
                    with gzip.open(local_file_path, 'rb') as f_in:
                        with open(extracted_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                
                # Update the local file path to the extracted file if available
                if extracted_path:
                    local_file_path = extracted_path
            
            # Update state with local file path
            state = pip.read_state(pipeline_id)
            step_data = pip.get_step_data(pipeline_id, step_id, {})
            
            job_id = step_data.get('job_id')
            org = step_data.get('org')
            project = step_data.get('project')
            analysis = step_data.get('analysis')
            depth = step_data.get('depth')
            
            state[step_id]['local_file'] = str(local_file_path)
            pip.write_state(pipeline_id, state)
            
            # Update the registry if we have a job_id
            if job_id and all([org, project, analysis, depth]):
                self.update_export_job(
                    org, project, analysis, depth, job_id,
                    {'local_file': str(local_file_path)}
                )
            
            # Get file information
            file_size_bytes = local_file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # Send success message
            await self.message_queue.add(
                pip, 
                f"Successfully downloaded and prepared CSV file:\n"
                f"Path: {local_file_path}\n"
                f"Size: {file_size_mb:.2f} MB", 
                verbatim=True
            )
            
            # Return success UI with file information
            # Format the directory path
            dir_tree = self.format_path_as_tree(str(local_file_path.parent))
            # Add the filename to the tree
            tree_path = f"{dir_tree}\n{'    ' * len(local_file_path.parent.parts)}└─{local_file_path.name}"
            tree_display = pip.tree_display(tree_path)
            return Div(
                pip.revert_control_advanced(
                    step_id=step_id,
                    app_name=app_name,
                    message=f"{step.show}: CSV downloaded ({file_size_mb:.2f} MB)",
                    content=tree_display,
                    steps=steps
                ),
                Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
                id=step_id
            )
        
        except Exception as e:
            return Div(
                Card(
                    H4("Download Error"),
                    P(f"Error downloading CSV file: {str(e)}", style=pip.get_style("error")),
                    P(f"Download URL: {download_url}"),
                    P(f"Target file: {local_file_path}"),
                    Button("Try Again", type="button", cls="primary",
                           hx_post=f"/{app_name}/download_csv",
                           hx_target=f"#{step_id}",
                           hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}')
                ),
                id=step_id
            )

    async def download_ready_export(self, request):
        """Handle ready export download"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        job_id = form.get("job_id")
        download_url = form.get("download_url")
        
        if not all([pipeline_id, job_id, download_url]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Extract necessary information from state
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth', '0')
        
        # Update state with the download URL if it's not already set
        if step_id not in state:
            state[step_id] = {}
        
        state[step_id].update({
            'job_id': job_id,
            'download_url': download_url,
            'status': 'DONE',
            'org': org,
            'project': project,
            'analysis': analysis,
            'depth': depth
        })
        
        # Set a dummy job URL if none exists
        if step.done not in state[step_id]:
            state[step_id][step.done] = f"existing://{job_id}"
            
        pip.write_state(pipeline_id, state)
        
        # Show download progress UI
        try:
            # Create download directory
            download_dir = await self.create_download_directory(org, project, analysis)
            
            # Generate filename
            include_fields = step_data.get('include_fields', {})
            fields_suffix = "_".join(k for k, v in include_fields.items() if v) or "url_only"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{org}_{project}_{analysis}_depth_{depth}_{fields_suffix}_{timestamp}.csv"
            
            local_file_path = download_dir / filename
            
            # Start downloading with progress feedback
            await self.message_queue.add(pip, f"Starting download from {download_url}", verbatim=True)
            
            # Show download progress
            return Div(
                Card(
                    H4("Downloading CSV File"),
                    P(f"Downloading export to {local_file_path}", style="margin-bottom: 1rem;"),
                    Progress(value="10", max="100", style="width: 100%;"),
                    P("Please wait, this may take a few minutes for large files...", 
                      style="font-size: 0.9em; color: #666;")
                ),
                hx_get=f"/{app_name}/download_progress",
                hx_trigger="load",
                hx_target=f"#{step_id}",
                hx_vals=f'{{"pipeline_id": "{pipeline_id}", "download_url": "{download_url}", "local_file": "{local_file_path}"}}',
                id=step_id
            )
            
        except Exception as e:
            logger.error(f"Error preparing download: {str(e)}")
            return P(f"Error preparing download: {str(e)}", style=pip.get_style("error"))

# ============================================================================
# 6. API INTEGRATION
# ============================================================================

    def read_api_token(self):
        """Read Botify API token from local file."""
        try:
            token_file = Path("botify_token.txt")
            if not token_file.exists():
                raise FileNotFoundError("botify_token.txt not found")
            
            token = token_file.read_text().splitlines()[0].strip()
            return token
        except Exception as e:
            raise ValueError(f"Error reading API token: {e}")

    async def fetch_analyses(self, org, project, api_token):
        """Fetch analysis slugs for a given project from Botify API."""
        url = f"https://api.botify.com/v1/analyses/{org}/{project}/light"
        headers = {"Authorization": f"Token {api_token}"}
        slugs = []
        
        async with httpx.AsyncClient() as client:
            try:
                while url:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    slugs.extend(a['slug'] for a in data.get('results', []))
                    url = data.get('next')
                return slugs
            except httpx.RequestError as e:
                raise ValueError(f"Error fetching analyses: {e}")

    async def get_urls_by_depth(self, org, project, analysis, api_key):
        """
        Fetches URL counts aggregated by depth from the Botify API.
        Returns a dictionary {depth: count} or an empty {} on error.
        """
        api_url = f"https://api.botify.com/v1/projects/{org}/{project}/query"
        headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        payload = {
            "collections": [f"crawl.{analysis}"],
            "query": {
                "dimensions": [f"crawl.{analysis}.depth"],
                "metrics": [{"field": f"crawl.{analysis}.count_urls_crawl"}],
                "sort": [{"field": f"crawl.{analysis}.depth", "order": "asc"}]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=payload, timeout=120.0)
                response.raise_for_status()
                
                results = response.json().get("results", [])
                depth_distribution = {}
                
                for row in results:
                    if "dimensions" in row and len(row["dimensions"]) == 1 and \
                       "metrics" in row and len(row["metrics"]) == 1:
                        depth = row["dimensions"][0]
                        count = row["metrics"][0]
                        if isinstance(depth, int):
                            depth_distribution[depth] = count
                
                return depth_distribution
                
        except Exception as e:
            logger.error(f"Error fetching URL depths: {str(e)}")
            return {}

    async def calculate_max_safe_depth(self, org, project, analysis, api_key):
        """Calculate maximum depth that keeps cumulative URLs under 1M and return count details"""
        depth_distribution = await self.get_urls_by_depth(org, project, analysis, api_key)
        if not depth_distribution:
            return None, None, None
        
        cumulative_sum = 0
        sorted_depths = sorted(depth_distribution.keys())
        
        for i, depth in enumerate(sorted_depths):
            prev_sum = cumulative_sum
            cumulative_sum += depth_distribution[depth]
            if cumulative_sum >= 1_000_000:
                safe_depth = depth - 1
                safe_count = prev_sum
                next_depth_count = cumulative_sum
                return safe_depth, safe_count, next_depth_count
                
        # If we never hit 1M, return the max depth and its cumulative count
        return max(sorted_depths), cumulative_sum, None

    async def initiate_export_job(self, org, project, analysis, depth, include_fields, api_token):
        """
        Initiate a Botify export job with the specified parameters
        
        Args:
            org: Organization slug
            project: Project slug
            analysis: Analysis slug
            depth: Maximum depth to include
            include_fields: Dictionary of fields to include (title, meta_desc, h1)
            api_token: Botify API token
            
        Returns:
            Tuple of (job_url, error_message)
        """
        jobs_url = "https://api.botify.com/v1/jobs"
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
        
        # Define the query dimensions based on selected fields
        dimensions = [f"crawl.{analysis}.url"]
        
        if include_fields.get('title', False):
            dimensions.append(f"crawl.{analysis}.metadata.title.content")
        
        if include_fields.get('meta_desc', False):
            dimensions.append(f"crawl.{analysis}.metadata.description.content")
        
        if include_fields.get('h1', False):
            dimensions.append(f"crawl.{analysis}.metadata.h1.contents")
        
        # Build the BQL query with depth filter
        query = {
            "dimensions": dimensions,
            "metrics": [],
            "sort": [{"field": f"crawl.{analysis}.url", "order": "asc"}],
            "filters": {
                "field": f"crawl.{analysis}.depth",
                "predicate": "lte",
                "value": int(depth)
            }
        }
        
        # Construct the job payload
        export_payload = {
            "job_type": "export",
            "payload": {
                "username": org,
                "project": project,
                "connector": "direct_download",
                "formatter": "csv",
                "export_size": 1000000,
                "query": {
                    "collections": [f"crawl.{analysis}"],
                    "query": query
                }
            }
        }
        
        try:
            # Submit export job request
            async with httpx.AsyncClient() as client:
                response = await client.post(jobs_url, headers=headers, json=export_payload, timeout=60.0)
                response.raise_for_status()
                job_data = response.json()
                
                job_url_path = job_data.get('job_url')
                if not job_url_path:
                    return None, "Failed to get job URL from response"
                    
                full_job_url = f"https://api.botify.com{job_url_path}"
                return full_job_url, None
        
        except Exception as e:
            logger.error(f"Error initiating export job: {str(e)}")
            return None, f"Error initiating export job: {str(e)}"

    async def poll_job_status(self, job_url, api_token, max_attempts=12):
        """
        Poll the job status URL to check for completion
        
        Args:
            job_url: Full job URL to poll
            api_token: Botify API token
            max_attempts: Maximum number of polling attempts
            
        Returns:
            Tuple of (is_complete, download_url, error_message)
        """
        headers = {"Authorization": f"Token {api_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(job_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                status_data = response.json()
                
                job_status = status_data.get("job_status")
                
                if job_status == "DONE":
                    download_url = status_data.get("results", {}).get("download_url")
                    if download_url:
                        return True, download_url, None
                    else:
                        return False, None, "Job completed but no download URL found"
                elif job_status == "FAILED":
                    return False, None, f"Export job failed: {status_data.get('results')}"
                else:
                    # Not complete yet
                    return False, None, None
        
        except Exception as e:
            logger.error(f"Error polling job status: {str(e)}")
            return False, None, f"Error polling job status: {str(e)}"

# ============================================================================
# 7. UI HELPERS & UTILITIES
# ============================================================================

    def clean_job_id_for_display(self, job_id):
        """
        Clean and shorten a job ID for display in the UI.
        Removes the depth and field information to show only the project details.
        
        Args:
            job_id: The raw job ID, typically a filename
            
        Returns:
            str: A cleaned, possibly truncated job ID
        """
        if not job_id or job_id == "Unknown":
            return "Unknown"
            
        # Extract the part before "_depth_" which typically contains org/project info
        clean_id = job_id.split('_depth_')[0] if '_depth_' in job_id else job_id
        
        # Truncate if too long
        if len(clean_id) > 30:
            clean_id = clean_id[:27] + "..."
            
        return clean_id

    async def check_export_status(self, request):
        """Check and display export status"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else None
        
        # Get form data
        form = await request.form()
        pipeline_id = form.get("pipeline_id")
        job_url = form.get("job_url")
        job_id = form.get("job_id")
        
        if not all([pipeline_id, job_url, job_id]):
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Check if the job is complete
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
            
            if is_complete and download_url:
                # Update the state with the download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                
                # Update the registry
                org = step_data.get('org')
                project = step_data.get('project')
                analysis = step_data.get('analysis')
                depth = step_data.get('depth')
                
                if all([org, project, analysis, depth]):
                    self.update_export_job(
                        org, project, analysis, depth, job_id,
                        {'status': 'DONE', 'download_url': download_url}
                    )
                
                # Send success message
                await self.message_queue.add(
                    pip, 
                    f"Export job completed! Job ID: {job_id}\n"
                    f"The export is ready for download.", 
                    verbatim=True
                )
                
                # Return the download button - IMPORTANT: Break the HTMX chain reaction
                # No hx_get or other HTMX attributes on this DIV
                # This is a "terminal" response that won't trigger other steps
                return Div(
                    Card(
                        H4("Export Status: Complete ✅"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"The export is ready for download.", style="margin-bottom: 1rem;"),
                        Form(
                            Button("Download CSV", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/download_csv",
                            hx_target=f"#{step_id}",
                            hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                        )
                    ),
                    # Add class to indicate this is a terminal response
                    # This DIV won't load any other steps automatically
                    cls="terminal-response no-chain-reaction",
                    id=step_id
                )
            else:
                # Job is still processing
                created = step_data.get('created', state[step_id].get('created', 'Unknown'))
                try:
                    created_dt = datetime.fromisoformat(created)
                    created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    created_str = created
                
                # Send message about still processing
                await self.message_queue.add(
                    pip, 
                    f"Export job is still processing (Job ID: {job_id}).\n"
                    f"Status will update automatically.", 
                    verbatim=True
                )
                
                # Return the UI with automatic polling instead of "Check Status Again" button
                include_fields = step_data.get('include_fields', {})
                fields_list = ", ".join([k for k, v in include_fields.items() if v]) or "URL only"
                
                return Div(
                    Card(
                        H4("Export Status: Processing ⏳"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"Started: {created_str}", style="margin-bottom: 0.5rem;"),
                        Div(
                            Progress(),  # PicoCSS indeterminate progress bar
                            P("Checking status automatically...", style="color: #666;"),
                            id="progress-container"
                        )
                    ),
                    # Only these HTMX attributes to continue polling - nothing else
                    # This breaks the chain reaction by not having any next-step HTMX attributes
                    cls="polling-status no-chain-reaction",
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="every 2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}',
                    id=step_id
                )
                
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return P(f"Error checking export status: {str(e)}", style=pip.get_style("error"))

    async def download_job_status(self, request):
        """Handle job status updates"""
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        step_id = "step_04"
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        
        # Get query parameters from the GET request
        pipeline_id = request.query_params.get("pipeline_id")
        
        if not pipeline_id:
            return P("Missing required parameters", style=pip.get_style("error"))
        
        # Get state data
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        
        # Get job information from state
        job_url = step_data.get('job_url')
        job_id = step_data.get('job_id')
        org = step_data.get('org')
        project = step_data.get('project')
        analysis = step_data.get('analysis')
        depth = step_data.get('depth')
        
        if not all([job_url, job_id]):
            return P("Job information not found in state", style=pip.get_style("error"))
        
        # Check if the job is complete
        try:
            api_token = self.read_api_token()
            is_complete, download_url, error = await self.poll_job_status(job_url, api_token)
            
            if is_complete and download_url:
                # Update the state with the download URL
                state[step_id]['download_url'] = download_url
                state[step_id]['status'] = 'DONE'
                pip.write_state(pipeline_id, state)
                
                # Update the registry
                if all([org, project, analysis, depth]):
                    self.update_export_job(
                        org, project, analysis, depth, job_id,
                        {'status': 'DONE', 'download_url': download_url}
                    )
                
                # Send success message
                await self.message_queue.add(
                    pip, 
                    f"Export job completed! Job ID: {job_id}\n"
                    f"The export is ready for download.", 
                    verbatim=True
                )
                
                # Return the download button - IMPORTANT: Break the HTMX chain reaction
                # No hx_get or other HTMX attributes on this DIV
                # This is a "terminal" response that won't trigger other steps
                return Div(
                    Card(
                        H4("Export Status: Complete ✅"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"The export is ready for download.", style="margin-bottom: 1rem;"),
                        Form(
                            Button("Download CSV", type="submit", cls="primary"),
                            hx_post=f"/{app_name}/download_csv",
                            hx_target=f"#{step_id}",
                            hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}'
                        )
                    ),
                    # Add class to indicate this is a terminal response
                    # This DIV won't load any other steps automatically
                    cls="terminal-response no-chain-reaction",
                    id=step_id
                )
            else:
                # Job is still processing - show indeterminate progress bar with automatic polling
                include_fields = step_data.get('include_fields', {})
                fields_list = ", ".join([k for k, v in include_fields.items() if v]) or "URL only"
                
                return Div(
                    Card(
                        H4("Export Status: Processing ⏳"),
                        P(f"Job ID: {job_id}", style="margin-bottom: 0.5rem;"),
                        P(f"Exporting URLs up to depth {depth}", style="margin-bottom: 0.5rem;"),
                        P(f"Including fields: {fields_list}", style="margin-bottom: 1rem;"),
                        Div(
                            Progress(),  # PicoCSS indeterminate progress bar
                            P("Checking status...", style="color: #666;"),
                            id="progress-container"
                        )
                    ),
                    # Only these HTMX attributes to continue polling - nothing else
                    # This breaks the chain reaction by not having any next-step HTMX attributes
                    cls="polling-status no-chain-reaction",
                    hx_get=f"/{app_name}/download_job_status",
                    hx_trigger="every 2s",
                    hx_target=f"#{step_id}",
                    hx_swap="outerHTML",
                    hx_vals=f'{{"pipeline_id": "{pipeline_id}"}}',
                    id=step_id
                )
                
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return P(f"Error checking export status: {str(e)}", style=pip.get_style("error"))

# ============================================================================
# 8. STATE MANAGEMENT
# ============================================================================

    async def finalize(self, request):
        """
        Finalize the workflow, locking all steps from further changes.
        
        This method handles both GET requests (displaying finalization UI) and 
        POST requests (performing the actual finalization). The UI portions
        are intentionally kept WET to allow for full customization of the user
        experience, while core state management is handled by DRY helper methods.
        
        Customization Points:
        - GET response: The cards/UI shown before finalization
        - Confirmation message: What the user sees after finalizing
        - Any additional UI elements or messages
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components for either the finalization prompt or confirmation
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        logger.debug(f"Pipeline ID: {pipeline_id}")
        logger.debug(f"Finalize step: {finalize_step}")
        logger.debug(f"Finalize data: {finalize_data}")

        # ───────── GET REQUEST: FINALIZATION UI (INTENTIONALLY WET) ─────────
        if request.method == "GET":
            if finalize_step.done in finalize_data:
                logger.debug("Pipeline is already finalized")
                return Card(
                    H4("Workflow is locked."),
                    Form(
                        Button(pip.UNLOCK_BUTTON_LABEL, type="submit", cls="secondary outline"),
                        hx_post=f"/{app_name}/unfinalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )

            # Check if all previous steps are complete
            non_finalize_steps = steps[:-1]
            all_steps_complete = all(
                pip.get_step_data(pipeline_id, step.id, {}).get(step.done)
                for step in non_finalize_steps
            )
            logger.debug(f"All steps complete: {all_steps_complete}")

            if all_steps_complete:
                return Card(
                    H4("All steps complete. Finalize?"),
                    P("You can revert to any step and make changes.", style="font-size: 0.9em; color: #666;"),
                    Form(
                        Button("Finalize", type="submit", cls="primary"),
                        hx_post=f"/{app_name}/finalize",
                        hx_target=f"#{app_name}-container",
                        hx_swap="outerHTML"
                    ),
                    id=finalize_step.id
                )
            else:
                return Div(P("Nothing to finalize yet."), id=finalize_step.id)
        # ───────── END GET REQUEST ─────────
        else:
            # ───────── POST REQUEST: PERFORM FINALIZATION ─────────
            # Update state using DRY helper
            await pip.finalize_workflow(pipeline_id)
            
            # ───────── CUSTOM FINALIZATION UI (INTENTIONALLY WET) ─────────
            # Send a confirmation message 
            await self.message_queue.add(pip, "Workflow successfully finalized! Your data has been saved and locked.", verbatim=True)
            
            # Return the updated UI
            return pip.rebuild(app_name, steps)
            # ───────── END CUSTOM FINALIZATION UI ─────────

    async def unfinalize(self, request):
        """
        Unfinalize the workflow, allowing steps to be modified again.
        
        This method removes the finalization flag from the workflow state
        and displays a confirmation message to the user. The core state
        management is handled by a DRY helper method, while the UI generation
        is intentionally kept WET for customization.
        
        Customization Points:
        - Confirmation message: What the user sees after unfinalizing
        - Any additional UI elements or actions
        
        Args:
            request: The HTTP request object
            
        Returns:
            UI components showing the workflow is unlocked
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        pipeline_id = db.get("pipeline_id", "unknown")
        
        # Before unfinalizing, check if Step 4 is completed and preserve its state
        state = pip.read_state(pipeline_id)
        step_04_data = pip.get_step_data(pipeline_id, "step_04", {})
        step_04 = next((s for s in steps if s.id == "step_04"), None)
        
        if step_04 and step_04_data.get(step_04.done):
            # Add a flag to indicate Step 4 should stay in completed state
            state["step_04"]["_preserve_completed"] = True
            pip.write_state(pipeline_id, state)
        
        # Update state using DRY helper
        await pip.unfinalize_workflow(pipeline_id)
        
        # ───────── CUSTOM UNFINALIZATION UI (INTENTIONALLY WET) ─────────
        # Send a message informing them they can revert to any step
        await self.message_queue.add(pip, "Workflow unfinalized! You can now revert to any step and make changes.", verbatim=True)
        
        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)
        # ───────── END CUSTOM UNFINALIZATION UI ─────────

    async def handle_revert(self, request):
        """
        Handle reverting to a previous step in the workflow.
        
        This method clears state data from the specified step forward,
        marks the step as the revert target in the state, and rebuilds
        the workflow UI. It allows users to go back and modify their
        inputs at any point in the workflow process.
        
        Args:
            request: The HTTP request object containing the step_id
            
        Returns:
            FastHTML components representing the rebuilt workflow UI
        """
        pip, db, steps, app_name = self.pipulate, self.db, self.steps, self.app_name
        form = await request.form()
        step_id = form.get("step_id")
        pipeline_id = db.get("pipeline_id", "unknown")
        if not step_id:
            return P("Error: No step specified", style=pip.get_style("error"))
        
        # Clear steps from the specified step forward
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        
        # Update state with revert target
        state = pip.read_state(pipeline_id)
        state["_revert_target"] = step_id
        
        # When reverting to step_04 or any earlier step, clear the _preserve_completed flag
        # from step_04 to ensure it shows the interactive UI instead of the completed state
        if step_id == "step_04" or self.steps_indices.get(step_id, 0) < self.steps_indices.get("step_04", 99):
            if "step_04" in state and "_preserve_completed" in state["step_04"]:
                del state["step_04"]["_preserve_completed"]
        
        pip.write_state(pipeline_id, state)
        
        # Send a state message
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        
        # Return the rebuilt UI
        return pip.rebuild(app_name, steps)

# ============================================================================
# 9. UTILITY FUNCTIONS
# ============================================================================

def parse_botify_url(url: str) -> dict:
    """
    Parse and validate Botify URL.
    
    Args:
        url: The Botify project URL to parse
        
    Returns:
        dict: Contains url, org, and project information
        
    Raises:
        ValueError: If URL format is invalid
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        raise ValueError("Invalid Botify URL format")
    org = path_parts[0]
    project = path_parts[1]
    base_url = f"https://{parsed.netloc}/{org}/{project}/"
    return {"url": base_url, "org": org, "project": project} 