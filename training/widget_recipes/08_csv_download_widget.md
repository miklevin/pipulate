# CSV Download Widget Recipe

## Overview
This recipe transforms a placeholder step into a widget that initiates a CSV download operation, polls for completion status, and provides a download link when ready. This pattern is used for long-running operations that generate downloadable files.

## Core Concepts
- **Async Operation**: Start a download that runs in the background
- **Polling Pattern**: Check status periodically without blocking the UI
- **Chain Breaking**: Temporarily break the automatic chain reaction during polling
- **Terminal Response**: Provide a download link as a terminal response
- **Chain Reaction Preservation**: CRITICAL - Must maintain chain reaction pattern with proper `hx_trigger="load"` attributes
- **Mobile Responsiveness**: Adapts to different screen sizes and touch interactions
- **Accessibility**: Supports keyboard navigation and screen readers
- **Error Recovery**: Handles various failure scenarios gracefully

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
        'filepath': None,
        'error': None  # Track any errors
    }
    
    try:
        # Simulate starting an async task
        # In real implementation, you would use a proper async process
        asyncio.create_task(self._simulate_download_progress(job_id))
        return job_id
    except Exception as e:
        self.download_jobs[job_id]['status'] = 'ERROR'
        self.download_jobs[job_id]['error'] = str(e)
        raise

async def _simulate_download_progress(self, job_id):
    """Simulate a download process progressing from 0% to 100%.
    
    In a real implementation, this would be your actual download logic,
    periodically updating the job status.
    """
    import asyncio
    import os
    import random
    
    try:
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
    except Exception as e:
        self.download_jobs[job_id]['status'] = 'ERROR'
        self.download_jobs[job_id]['error'] = str(e)
        raise

async def check_download_status(self, job_id):
    """Check the status of an ongoing download job."""
    if not hasattr(self, 'download_jobs') or job_id not in self.download_jobs:
        return {'status': 'ERROR', 'message': 'Job not found'}
    
    job = self.download_jobs[job_id]
    return {
        'status': job['status'],
        'progress': job['progress'],
        'filepath': job['filepath'],
        'error': job.get('error')
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
    
    try:
        # Get job_id from query parameters
        job_id = request.query_params.get('job_id')
        if not job_id:
            return JSONResponse({
                'status': 'ERROR', 
                'message': 'No job ID provided'
            }, status_code=400)
        
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
        elif status['status'] == 'ERROR':
            # Handle error state
            return JSONResponse({
                'status': 'ERROR',
                'message': status.get('error', 'Unknown error occurred')
            }, status_code=500)
        else:
            # Unknown status
            return JSONResponse({
                'status': 'UNKNOWN',
                'message': 'Unknown job status'
            }, status_code=400)
    except Exception as e:
        return JSONResponse({
            'status': 'ERROR',
            'message': f"Error checking status: {str(e)}"
        }, status_code=500)
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
    from starlette.responses import FileResponse, HTMLResponse
    import os
    
    try:
        # Get filename from query parameter
        filename = request.query_params.get('file')
        if not filename:
            return HTMLResponse(
                "Error: No file specified", 
                status_code=400
            )
        
        # Construct full path
        filepath = os.path.join(os.getcwd(), 'downloads', filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return HTMLResponse(
                "Error: File not found", 
                status_code=404
            )
        
        # Serve the file as a download
        return FileResponse(
            filepath,
            media_type='text/csv',
            filename=filename,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        return HTMLResponse(
            f"Error serving file: {str(e)}", 
            status_code=500
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

# CUSTOMIZE_DISPLAY: Enhanced finalized state display with accessibility
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
            cls="button primary",
            style="min-height: 44px; min-width: 44px;",  # Mobile touch target
            aria-label="Download CSV file",
            role="button"
        )
        return Div(
            Card(
                H3(f"🔒 {step.show}", id=f"{step_id}-title"),
                P("Download is ready:", id=f"{step_id}-status"),
                download_link
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id,
            role="region",
            aria-labelledby=f"{step_id}-title"
        )
    else:
        # Show status for unfinished job
        return Div(
            Card(
                H3(f"🔒 {step.show}", id=f"{step_id}-title"),
                P(f"Download status: {status.get('status', 'Unknown')}", id=f"{step_id}-status")
            ),
            Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
            id=step_id,
            role="region",
            aria-labelledby=f"{step_id}-title"
        )

# CUSTOMIZE_COMPLETE: Enhanced completion display with download status
if job_id and state.get("_revert_target") != step_id:
    # Check job status
    status = await self.check_download_status(job_id)
    
    if status['status'] == 'COMPLETED' and status.get('filepath'):
        # Show download link for completed job
        filename = os.path.basename(status['filepath'])
        download_widget = Div(
            A(
                "Download CSV File",
                href=f"/{app_name}/download_file?file={filename}",
                target="_blank",
                cls="button primary",
                style="min-height: 44px; min-width: 44px;",  # Mobile touch target
                aria-label="Download CSV file",
                role="button"
            )
        )
    else:
        # Show status for unfinished job
        download_widget = P(f"Download status: {status.get('status', 'Unknown')}")
    
    return Div(
        pip.revert_control(
            step_id=step_id, 
            app_name=app_name, 
            message=f"{step.show}: {status.get('status', 'Unknown')}", 
            steps=steps
        ),
        download_widget,
        Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load"),
        id=step_id,
        role="region",
        aria-live="polite"
    )

# CUSTOMIZE_FORM: Replace with download initiation form
return Div(
    Card(
        H3(f"{step.show}", id=f"{step_id}-title"),
        P("Click Start to begin the download:", id=f"{step_id}-instruction"),
        Form(
            Button(
                "Start Download", 
                type="submit", 
                cls="primary",
                style="min-height: 44px; min-width: 44px;",  # Mobile touch target
                aria-label="Start CSV download"
            ),
            hx_post=f"/{app_name}/{step_id}_submit", 
            hx_target=f"#{step_id}",
            _="on htmx:beforeRequest add .loading to <button[type='submit']/> end on htmx:afterRequest remove .loading from <button[type='submit']/> end"
        )
    ),
    Div(id=next_step_id),  # PRESERVE: Empty div for next step
    id=step_id,
    role="region",
    aria-labelledby=f"{step_id}-title"
)
```

### Phase 7: Update SUBMIT Handler
Replace the key sections:

```python
# CUSTOMIZE_FORM_PROCESSING: Process form data with error handling
try:
    # Start the download process
    job_id = await self.initiate_csv_download({})  # Add any parameters needed
    
    # Store the job ID in state
    await pip.update_step_state(pipeline_id, step_id, job_id, steps)
    await self.message_queue.add(pip, f"{step.show} started", verbatim=True)
    
    # Return polling UI
    return Div(
        Card(
            H3(f"{step.show}", id=f"{step_id}-title"),
            P("Download in progress...", id=f"{step_id}-status"),
            Div(
                "0%",
                id=f"{step_id}-progress",
                style="width: 100%; height: 20px; background: #eee; border-radius: 4px; overflow: hidden;"
            ),
            Div(
                style="width: 0%; height: 100%; background: var(--accent); transition: width 0.3s ease;",
                _=f"on load set my.style.width to '0%' end on htmx:afterRequest set my.style.width to event.detail.xhr.response.progress + '%' end"
            )
        ),
        Div(
            id=next_step_id,
            hx_get=f"/{app_name}/check_download_status?job_id={job_id}",
            hx_trigger="load, every 2s",
            hx_swap="outerHTML"
        ),
        id=step_id,
        role="region",
        aria-live="polite"
    )
except Exception as e:
    return P(f"Error starting download: {str(e)}", style=pip.get_style("error"), role="alert")
```

## Common Pitfalls
- Don't remove the chain reaction div with next_step_id
- Don't forget to handle download errors
- Use proper error status codes
- Always clean up temporary files
- Handle mobile touch targets properly
- Include proper ARIA attributes
- Handle keyboard navigation
- Consider screen reader announcements

## Mobile Responsiveness
- Use appropriate touch target sizes (min 44px)
- Ensure download buttons are easily tappable
- Handle progress bar display on small screens
- Consider download size limitations
- Use responsive layout patterns

## Accessibility Features
- ARIA labels and descriptions
- Keyboard navigation support
- Screen reader compatibility
- Progress announcements
- Focus management
- Color contrast compliance

## Error Recovery
- Handle network failures
- Manage file system errors
- Clean up incomplete downloads
- Provide clear error messages
- Allow retry mechanisms

## Related Widget Recipes
- [File Upload Widget](path/to/file_upload_widget.md)
- [Progress Bar Widget](path/to/progress_bar_widget.md)