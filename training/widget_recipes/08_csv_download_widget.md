# CSV Download Widget Recipe

## Overview
This recipe transforms a placeholder step into a widget that initiates a CSV download operation, polls for completion status, and provides a download link when ready. This pattern is used for long-running operations that generate downloadable files.

## Core Concepts
- **Async Operation**: Start a download that runs in the background
- **Polling Pattern**: Check status periodically without blocking the UI
- **Chain Breaking**: Temporarily break the automatic chain reaction during polling
- **Terminal Response**: Provide a download link as a terminal response
- **Chain Reaction Preservation**: CRITICAL - Must maintain chain reaction pattern with proper `hx_trigger="load"` attributes

## Implementation Phases

### Phase 1: Add Helper Methods
Add these helper methods to your workflow class:

```python
async def initiate_csv_download(self, parameters):
    """Start an asynchronous CSV download process.
    
    This is a placeholder for your actual download logic.
    Should return a job_id or reference for status checking.
    """
    # Example implementation
    import uuid
    import asyncio
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Store job in class variable for demonstration
    # In a real implementation, you would store in a database
    if not hasattr(self, 'download_jobs'):
        self.download_jobs = {}
    
    # Start with 0% progress
    self.download_jobs[job_id] = {
        'progress': 0,
        'status': 'RUNNING',
        'parameters': parameters,
        'filepath': None
    }
    
    # Simulate starting an async task
    # In real implementation, you would use a proper async process
    asyncio.create_task(self._simulate_download_progress(job_id))
    
    return job_id

async def _simulate_download_progress(self, job_id):
    """Simulate a download process progressing from 0% to 100%.
    
    In a real implementation, this would be your actual download logic,
    periodically updating the job status.
    """
    import asyncio
    import os
    import random
    
    # Simulate download steps
    for progress in range(0, 101, 10):
        self.download_jobs[job_id]['progress'] = progress
        
        # Random sleep to simulate work
        await asyncio.sleep(random.uniform(1, 2))
    
    # Mark as complete when done
    self.download_jobs[job_id]['status'] = 'COMPLETED'
    
    # Create a dummy CSV file
    output_dir = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, f"{job_id}.csv")
    with open(filepath, 'w') as f:
        f.write("column1,column2,column3\n")
        f.write("value1,value2,value3\n")
        f.write("value4,value5,value6\n")
    
    # Store the filepath
    self.download_jobs[job_id]['filepath'] = filepath

async def check_download_status(self, job_id):
    """Check the status of an ongoing download job."""
    if not hasattr(self, 'download_jobs') or job_id not in self.download_jobs:
        return {'status': 'ERROR', 'message': 'Job not found'}
    
    job = self.download_jobs[job_id]
    return {
        'status': job['status'],
        'progress': job['progress'],
        'filepath': job['filepath']
    }
```

### Phase 2: Add Additional Route
Add a special route for status checking in your `__init__` method:

```python
# Add to the routes list in __init__
routes.append((f"/{app_name}/check_download_status", self.handle_download_status, ["GET"]))

# Later in __init__, make sure this route is registered
app.route(f"/{app_name}/check_download_status")(self.handle_download_status)
```

### Phase 3: Add Status Handler
Add this method to handle the status check requests:

```python
async def handle_download_status(self, request):
    """Handle requests to check download status."""
    from starlette.responses import JSONResponse
    
    # Get job_id from query parameters
    job_id = request.query_params.get('job_id')
    if not job_id:
        return JSONResponse({'status': 'ERROR', 'message': 'No job ID provided'})
    
    # Check the job status
    status = await self.check_download_status(job_id)
    
    # Generate appropriate response
    if status['status'] == 'COMPLETED':
        # If complete, return JSON with filepath
        return JSONResponse({
            'status': 'COMPLETED', 
            'filepath': status['filepath'],
            'download_url': f"/{self.app_name}/download_file?file={os.path.basename(status['filepath'])}"
        })
    elif status['status'] == 'RUNNING':
        # If still running, return progress
        return JSONResponse({
            'status': 'RUNNING',
            'progress': status['progress'],
            'message': f"Download {status['progress']}% complete"
        })
    else:
        # Error or unknown status
        return JSONResponse(status)
```

### Phase 4: Add Download Route
Add a route to serve the downloaded file:

```python
# Add to the routes list in __init__
routes.append((f"/{app_name}/download_file", self.serve_download_file, ["GET"]))

# Later in __init__, make sure this route is registered
app.route(f"/{app_name}/download_file")(self.serve_download_file)
```

```python
async def serve_download_file(self, request):
    """Serve a downloaded file."""
    from starlette.responses import FileResponse
    import os
    
    # Get filename from query parameter
    filename = request.query_params.get('file')
    if not filename:
        return HTMLResponse("Error: No file specified")
    
    # Construct full path
    filepath = os.path.join(os.getcwd(), 'downloads', filename)
    
    # Check if file exists
    if not os.path.exists(filepath):
        return HTMLResponse("Error: File not found")
    
    # Serve the file as a download
    return FileResponse(
        filepath,
        media_type='text/csv',
        filename=filename
    )
```

### Phase 5: Update Step Definition
```python
# CUSTOMIZE_STEP_DEFINITION
# Change from:
Step(
    id='step_XX',
    done='placeholder',
    show='Placeholder Step',
    refill=False,
),

# To:
Step(
    id='step_XX',
    done='download_job_id',      # Stores the download job ID
    show='CSV Download',         # User-friendly name
    refill=False,                # No refill needed for downloads
),
```

### Phase 6: Update GET Handler
Replace the key sections:

```python
# CUSTOMIZE_VALUE_ACCESS
job_id = step_data.get(step.done, "")  # Get saved job ID

# CUSTOMIZE_DISPLAY: Enhanced finalized state display
if "finalized" in finalize_data and job_id:
    # Check job status
    status = await self.check_download_status(job_id)
    
    if status['status'] == 'COMPLETED' and status.get('filepath'):
        # Show download link for completed job
        filename = os.path.basename(status['filepath'])
        download_link = A(
            "Download CSV File",
            href=f"/{app_name}/download_file?file={filename}",
            target="_blank",
            cls="button primary"
        )
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P("Download is ready:"),
                download_link
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    else:
        # Show status for unfinished job
        return Div(
            Card(
                H3(f"🔒 {step.show}"),
                P(f"Download status: {status.get('status', 'Unknown')}")
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )

# CUSTOMIZE_COMPLETE: Enhanced completion display with download status
if job_id and state.get("_revert_target") != step_id:
    # Check job status
    status = await self.check_download_status(job_id)
    
    if status['status'] == 'COMPLETED' and status.get('filepath'):
        # Show download link for completed job
        filename = os.path.basename(status['filepath'])
        download_widget = Div(
            P("Your CSV file is ready for download:"),
            A(
                "Download CSV File",
                href=f"/{app_name}/download_file?file={filename}",
                target="_blank",
                cls="button primary"
            )
        )
        
        content_container = pip.widget_container(
            step_id=step_id,
            app_name=app_name,
            message=f"{step.show}: Download ready",
            widget=download_widget,
            steps=steps
        )
        
        return Div(
            content_container,
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id
        )
    
    elif status['status'] == 'RUNNING':
        # Show progress indicator for running job
        progress_bar = Div(
            P(f"Downloading: {status['progress']}% complete"),
            Div(
                Div(
                    style=f"width: {status['progress']}%; height: 20px; background-color: #4CAF50;"
                ),
                style="width: 100%; background-color: #f1f1f1; border-radius: 5px;"
            ),
            # Key part: This creates a polling update
            cls="polling-status no-chain-reaction",
            hx_get=f"/{app_name}/check_download_status?job_id={job_id}",
            hx_trigger="load, every 2s",
            hx_target=f"#{step_id}-status"
        )
        
        return Div(
            Card(
                H3(f"{step.show}"),
                progress_bar
            ),
            Div(id=f"{step_id}-status"),  # Status update target
            id=step_id,
            cls="no-chain-reaction"  # Prevents chain reaction during polling
        )
    
    else:
        # Show error or unknown status
        return Div(
            Card(
                H3(f"{step.show}"),
                P(f"Download status: {status.get('status', 'Unknown')}"),
                P(f"Error: {status.get('message', 'Unknown error')}", style="color: red;")
            ),
            Div(id=next_step_id),
            id=step_id
        )

# CUSTOMIZE_FORM: Create download initiation form
await self.message_queue.add(pip, f"Initiate CSV download in {step.show}", verbatim=True)

return Div(
    Card(
        H3(f"{step.show}"),
        P("Configure and start your CSV download:"),
        Form(
            # Simple parameters for the download
            Div(
                Label("Rows:", fr=f"{step_id}-rows"),
                Input(
                    type="number",
                    id=f"{step_id}-rows",
                    name="rows",
                    value="100",
                    min="1",
                    max="1000",
                    required=True
                ),
                style="margin-bottom: 10px;"
            ),
            Div(
                Label("Format:", fr=f"{step_id}-format"),
                Select(
                    Option("CSV", value="csv", selected=True),
                    Option("TSV", value="tsv"),
                    id=f"{step_id}-format",
                    name="format"
                ),
                style="margin-bottom: 20px;"
            ),
            Div(
                Button("Start Download", type="submit", cls="primary"),
                style="margin-top: 1vh; text-align: right;"
            ),
            hx_post=f"/{app_name}/{step_id}_submit",
            hx_target=f"#{step_id}"
        )
    ),
    Div(id=next_step_id),
    id=step_id
)
```

### Phase 7: Update SUBMIT Handler
Replace the key sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Get download parameters
form = await request.form()
rows = form.get("rows", "100")
format_type = form.get("format", "csv")

# CUSTOMIZE_VALIDATION: Validate parameters
try:
    rows = int(rows)
    if rows < 1 or rows > 1000:
        raise ValueError("Rows must be between 1 and 1000")
except ValueError as e:
    return P(f"Error: {str(e)}", style=pip.get_style("error"))

# Validate format
if format_type not in ["csv", "tsv"]:
    return P("Error: Invalid format selected", style=pip.get_style("error"))

# CUSTOMIZE_DATA_PROCESSING: Start the download job
parameters = {
    "rows": rows,
    "format": format_type
}
job_id = await self.initiate_csv_download(parameters)

# CUSTOMIZE_STATE_STORAGE: Store job ID in state
await pip.update_step_state(pipeline_id, step_id, job_id, steps)
await self.message_queue.add(pip, f"{step.show} started. Download job ID: {job_id}", verbatim=True)

# Check initial status
status = await self.check_download_status(job_id)

# CUSTOMIZE_WIDGET_DISPLAY: Show progress indicator
progress_bar = Div(
    P(f"Downloading: {status['progress']}% complete"),
    Div(
        Div(
            style=f"width: {status['progress']}%; height: 20px; background-color: #4CAF50;"
        ),
        style="width: 100%; background-color: #f1f1f1; border-radius: 5px;"
    ),
    # Key part: This creates a polling update
    hx_get=f"/{app_name}/check_download_status?job_id={job_id}",
    hx_trigger="load, every 2s",
    hx_target=f"#{step_id}-status"
)

# Return with polling status instead of chain reaction
from starlette.responses import HTMLResponse
from fasthtml.xml import to_xml

response_content = Div(
    Card(
        H3(f"{step.show}"),
        progress_bar
    ),
    Div(id=f"{step_id}-status"),  # Status update target
    id=step_id,
    cls="no-chain-reaction"  # Prevents chain reaction during polling
)

return HTMLResponse(to_xml(response_content))
```

## Common Pitfalls
- **Chain Reaction Breaking**: Use `cls="no-chain-reaction"` only during polling, then restore the chain
- **HTMX Triggers**: Use `hx_trigger="load, every 2s"` for polling with a reasonable interval
- **Async Handling**: Ensure download processes run in the background and don't block the server
- **File Cleanup**: Implement file cleanup to remove old downloads eventually
- **Error Handling**: Provide clear error messages and recovery options

## Related Widget Recipes
- [Polling Status Widget](09_polling_status_widget.md)
- [File Upload Widget](10_file_upload_widget.md) 
