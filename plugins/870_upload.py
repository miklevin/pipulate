import asyncio
import json
import os
import shutil
from collections import namedtuple
from datetime import datetime
from pathlib import Path
import urllib.parse

from fasthtml.common import *
from loguru import logger
from starlette.responses import HTMLResponse

ROLES = ['Components']
'\nFile Upload Widget Workflow\n\nThis workflow demonstrates a widget that allows users to upload files to the server.\nFiles are saved in a designated directory with proper organization and tracking.\n'
Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


class FileUploadWidget:
    """
    File Upload Widget Workflow

    A focused environment for creating and testing file upload functionality.
    Users can select and upload multiple files, which are saved to a designated
    server directory with proper organization and tracking.
    """
    APP_NAME = 'file_upload_widget'
    DISPLAY_NAME = 'File Upload Widget'
    ENDPOINT_MESSAGE = 'This workflow demonstrates a file upload widget. Select one or more files to upload and save them to the server.'
    TRAINING_PROMPT = 'This workflow is for demonstrating and testing the file upload widget. The user will select files, which are then uploaded and saved to a designated server directory.'

    def __init__(self, app, pipulate, pipeline, db, app_name=APP_NAME):
        """
        Initialize the workflow, define steps, and register routes.
        """
        self.app = app
        self.app_name = app_name
        self.pipulate = pipulate
        self.pipeline = pipeline
        self.steps_indices = {}
        self.db = db
        pip = self.pipulate
        self.message_queue = pip.message_queue
        steps = [Step(id='step_01', done='file_summary', show='Upload Files', refill=True, transform=lambda prev_value: prev_value.strip() if prev_value else '')]
        routes = [(f'/{app_name}', self.landing), (f'/{app_name}/init', self.init, ['POST']), (f'/{app_name}/revert', self.handle_revert, ['POST']), (f'/{app_name}/finalize', self.finalize, ['GET', 'POST']), (f'/{app_name}/unfinalize', self.unfinalize, ['POST'])]
        self.steps = steps
        for step in steps:
            step_id = step.id
            routes.append((f'/{app_name}/{step_id}', getattr(self, step_id)))
            routes.append((f'/{app_name}/{step_id}_submit', getattr(self, f'{step_id}_submit'), ['POST']))
        for path, handler, *methods in routes:
            method_list = methods[0] if methods else ['GET']
            app.route(path, methods=method_list)(handler)
        self.step_messages = {'finalize': {'ready': 'All steps complete. Ready to finalize workflow.', 'complete': f'Workflow finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.'}, 'new': 'Please complete each step to explore the file upload widget.', 'step_01': {'input': 'Please select files to upload.', 'complete': 'Files uploaded successfully.'}}
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        self.steps_indices = {step.id: i for i, step in enumerate(steps)}

    async def landing(self, request):
        """ Renders the initial landing page with the key input form. """
        pip, pipeline, steps, app_name = (self.pipulate, self.pipeline, self.steps, self.app_name)
        context = pip.get_plugin_context(self)
        title = f'{self.DISPLAY_NAME or app_name.title()}'
        full_key, prefix, user_part = pip.generate_pipeline_key(self)
        default_value = full_key
        pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in pipeline() if record.pkey.startswith(prefix)]
        datalist_options = [f"{prefix}{record_key.replace(prefix, '')}" for record_key in matching_records]
        return Container(Card(H2(title), P(self.ENDPOINT_MESSAGE, cls='text-secondary'), Form(pip.wrap_with_inline_button(Input(placeholder='Existing or new 🗝 here (Enter for auto)', name='pipeline_id', list='pipeline-ids', type='search', required=False, autofocus=True, value=default_value, _onfocus='this.setSelectionRange(this.value.length, this.value.length)', cls='contrast'), button_label=f'Enter 🔑', button_class='secondary'), pip.update_datalist('pipeline-ids', options=datalist_options if datalist_options else None), hx_post=f'/{app_name}/init', hx_target=f'#{app_name}-container')), Div(id=f'{app_name}-container'))

    async def init(self, request):
        """ Initialize the workflow state and redirect to the first step. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        user_input = form.get('pipeline_id', '').strip()
        if not user_input:
            from starlette.responses import Response
            response = Response('')
            response.headers['HX-Refresh'] = 'true'
            return response
        context = pip.get_plugin_context(self)
        plugin_name = context['plugin_name'] or app_name
        profile_name = context['profile_name'] or 'default'
        profile_part = profile_name.replace(' ', '_')
        plugin_part = plugin_name.replace(' ', '_')
        expected_prefix = f'{profile_part}-{plugin_part}-'
        if user_input.startswith(expected_prefix):
            pipeline_id = user_input
        else:
            _, prefix, user_provided_id = pip.generate_pipeline_key(self, user_input)
            pipeline_id = f'{prefix}{user_provided_id}'
        db['pipeline_id'] = pipeline_id
        logger.debug(f'Using pipeline ID: {pipeline_id}')
        state, error = pip.initialize_if_missing(pipeline_id, {'app_name': app_name})
        if error:
            return error
        all_steps_complete = all((step.id in state and step.done in state[step.id] for step in steps[:-1]))
        is_finalized = 'finalize' in state and 'finalized' in state['finalize']
        await self.message_queue.add(pip, f'Workflow ID: {pipeline_id}', verbatim=True, spaces_before=0)
        await self.message_queue.add(pip, f"Return later by selecting '{pipeline_id}' from the dropdown.", verbatim=True, spaces_before=0)
        if all_steps_complete:
            status_msg = f'Workflow is complete and finalized. Use {pip.UNLOCK_BUTTON_LABEL} to make changes.' if is_finalized else 'Workflow is complete but not finalized. Press Finalize to lock your data.'
            await self.message_queue.add(pip, status_msg, verbatim=True)
        elif not any((step.id in state for step in self.steps)):
            await self.message_queue.add(pip, self.step_messages['new'], verbatim=True)
        parsed = pip.parse_pipeline_key(pipeline_id)
        prefix = f"{parsed['profile_part']}-{parsed['plugin_part']}-"
        self.pipeline.xtra(app_name=app_name)
        matching_records = [record.pkey for record in self.pipeline() if record.pkey.startswith(prefix)]
        if pipeline_id not in matching_records:
            matching_records.append(pipeline_id)
        updated_datalist = pip.update_datalist('pipeline-ids', options=matching_records)
        return pip.rebuild(app_name, steps)

    async def finalize(self, request):
        """ Handle GET/POST requests to finalize (lock) the workflow. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        finalize_step = steps[-1]
        finalize_data = pip.get_step_data(pipeline_id, finalize_step.id, {})
        if request.method == 'GET':
            if finalize_step.done in finalize_data:
                return Card(H3('Workflow is locked.'), Form(Button(pip.UNLOCK_BUTTON_LABEL, type='submit', cls='secondary outline'), hx_post=f'/{app_name}/unfinalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
            else:
                all_steps_complete = all((pip.get_step_data(pipeline_id, step.id, {}).get(step.done) for step in steps[:-1]))
                if all_steps_complete:
                    return Card(H3('All steps complete. Finalize?'), P('You can revert to any step and make changes.', cls='text-secondary'), Form(Button('Finalize 🔒', type='submit', cls='primary'), hx_post=f'/{app_name}/finalize', hx_target=f'#{app_name}-container', hx_swap='outerHTML'), id=finalize_step.id)
                else:
                    return Div(id=finalize_step.id)
        else:
            await pip.finalize_workflow(pipeline_id)
            await self.message_queue.add(pip, self.step_messages['finalize']['complete'], verbatim=True)
            return pip.rebuild(app_name, steps)

    async def unfinalize(self, request):
        """ Handle POST request to unlock the workflow. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        pipeline_id = db.get('pipeline_id', 'unknown')
        await pip.unfinalize_workflow(pipeline_id)
        await self.message_queue.add(pip, 'Workflow unfinalized! You can now revert to any step and make changes.', verbatim=True)
        return pip.rebuild(app_name, steps)

    async def get_suggestion(self, step_id, state):
        """ Gets a suggested input value for a step. """
        if step_id == 'step_01':
            return 'No pre-fill for file uploads. Please select files.'
        return ''

    async def handle_revert(self, request):
        """ Handle POST request to revert to a previous step. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        form = await request.form()
        step_id = form.get('step_id')
        pipeline_id = db.get('pipeline_id', 'unknown')
        if not step_id:
            return P('Error: No step specified', style=pip.get_style('error'))
        await pip.clear_steps_from(pipeline_id, step_id, steps)
        state = pip.read_state(pipeline_id)
        state['_revert_target'] = step_id
        pip.write_state(pipeline_id, state)
        message = await pip.get_state_message(pipeline_id, steps, self.step_messages)
        await self.message_queue.add(pip, message, verbatim=True)
        return pip.rebuild(app_name, steps)

    async def step_01(self, request):
        """ Handles GET request for file upload widget. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        state = pip.read_state(pipeline_id)
        step_data = pip.get_step_data(pipeline_id, step_id, {})
        file_summary = step_data.get(step.done, '')
        finalize_data = pip.get_step_data(pipeline_id, 'finalize', {})
        if 'finalized' in finalize_data and file_summary:
            try:
                save_directory = Path('downloads') / app_name / pipeline_id
                return Div(Card(H3(f'🔒 {step.show}'), P('Uploaded files summary:'), Pre(file_summary, style='white-space: pre-wrap; font-size: 0.9em; background-color: var(--pico-card-background-color); padding: 1em; border-radius: var(--pico-border-radius);'), P("Open folder: ", A("📂 View Files", href="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_get="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_swap="none"), style="margin-top: 1em;")), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
            except Exception as e:
                logger.error(f'Error creating file summary in locked view: {str(e)}')
                return Div(Card(f'🔒 {step.show}: <content locked>'), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        elif state.get('_finalized'):
            try:
                file_summary = pip.get_step_data(pipeline_id, step_id)
                save_directory = Path('downloads') / app_name / pipeline_id
                return Div(Card(f'🔒 {step.show}', P("Uploaded files summary:"), Pre(file_summary, style='white-space: pre-wrap; font-size: 0.9em; background-color: var(--pico-card-background-color); padding: 1em; border-radius: var(--pico-border-radius);'), P("Open folder: ", A("📂 View Files", href="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_get="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_swap="none"), style="margin-top: 1em;")), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
            except Exception as e:
                logger.error(f'Error creating file summary in locked view: {str(e)}')
                return Div(Card(f'🔒 {step.show}: <content locked>'), Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'))
        elif file_summary and state.get('_revert_target') != step_id:
            save_directory = Path('downloads') / app_name / pipeline_id
            content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Files previously uploaded', widget=Div(
                Pre(file_summary, style='white-space: pre-wrap; font-size: 0.9em; margin-top:1em; padding: 1em; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius);'),
                P("Open folder: ", A("📂 View Files", href="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_get="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_swap="none"), style="margin-top: 1em;")
            ), steps=steps)
            return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
        explanation = 'Select one or more files. They will be saved to the `downloads` directory in a subfolder named after this workflow and pipeline ID.'
        await self.message_queue.add(pip, self.step_messages[step_id]['input'], verbatim=True)
        await self.message_queue.add(pip, explanation, verbatim=True)
        return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P(explanation, style=pip.get_style('muted')), Form(Input(type='file', name='uploaded_files', multiple='true', required='true', cls='contrast'), Button('Upload Files ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}', enctype='multipart/form-data')), Div(id=next_step_id), id=step_id)

    async def step_01_submit(self, request):
        """ Process the submission for file upload widget. """
        pip, db, steps, app_name = (self.pipulate, self.db, self.steps, self.app_name)
        step_id = 'step_01'
        step_index = self.steps_indices[step_id]
        step = steps[step_index]
        next_step_id = steps[step_index + 1].id if step_index < len(steps) - 1 else 'finalize'
        pipeline_id = db.get('pipeline_id', 'unknown')
        form_data = await request.form()
        uploaded_files = form_data.getlist('uploaded_files')
        if not uploaded_files or not uploaded_files[0].filename:
            await self.message_queue.add(pip, 'No files selected. Please try again.', verbatim=True)
            explanation = 'Select one or more files. They will be saved to the `downloads` directory.'
            return Div(Card(H3(f'{pip.fmt(step_id)}: {step.show}'), P('No files were selected. Please try again.', style=pip.get_style('error')), P(explanation, style=pip.get_style('muted')), Form(Input(type='file', name='uploaded_files', multiple='true', required='true', cls='contrast'), Button('Upload Files ▸', type='submit', cls='primary'), hx_post=f'/{app_name}/{step_id}_submit', hx_target=f'#{step_id}', enctype='multipart/form-data')), Div(id=next_step_id), id=step_id)
        save_directory = Path('downloads') / app_name / pipeline_id
        try:
            save_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_msg = f'Error creating save directory {save_directory}: {str(e)}'
            logger.error(error_msg)
            await self.message_queue.add(pip, error_msg, verbatim=True)
            return P(f'Error creating save directory. Please check permissions or disk space. Details: {error_msg}', style=pip.get_style('error'))
        file_info_list = []
        total_size = 0
        for uploaded_file in uploaded_files:
            if not uploaded_file.filename:
                continue
            try:
                contents = await uploaded_file.read()
                file_size = len(contents)
                total_size += file_size
                file_save_path = save_directory / uploaded_file.filename
                with open(file_save_path, 'wb') as f:
                    f.write(contents)
                file_info_list.append(f'📄 {uploaded_file.filename} ({file_size:,} bytes) -> {file_save_path}')
            except Exception as e:
                error_msg = f'Error saving file {uploaded_file.filename}: {str(e)}'
                logger.error(error_msg)
                await self.message_queue.add(pip, error_msg, verbatim=True)
                return P(f'Error saving file {uploaded_file.filename}. Details: {error_msg}', style=pip.get_style('error'))
        file_summary = '\n'.join(file_info_list)
        file_summary += f'\n\nTotal: {len(file_info_list)} files, {total_size:,} bytes'
        file_summary += f'\nSaved to directory: {save_directory.resolve()}'
        await pip.set_step_data(pipeline_id, step_id, file_summary, steps)
        pip.append_to_history(f'[WIDGET CONTENT] {step.show}:\n{file_summary}')
        pip.append_to_history(f'[WIDGET STATE] {step.show}: Files saved')
        await self.message_queue.add(pip, f'Successfully saved {len(file_info_list)} files to {save_directory}', verbatim=True)
        content_container = pip.display_revert_widget(step_id=step_id, app_name=app_name, message=f'{step.show}: Files Uploaded Successfully!', widget=Div(
            Pre(file_summary, style='white-space: pre-wrap; font-size: 0.9em; margin-top:1em; padding: 1em; background-color: var(--pico-code-background); border-radius: var(--pico-border-radius);'),
            P("Open folder: ", A("📂 View Files", href="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_get="/open-folder?path=" + urllib.parse.quote(str(save_directory.resolve())), hx_swap="none"), style="margin-top: 1em;")
        ), steps=steps)
        return Div(content_container, Div(id=next_step_id, hx_get=f'/{app_name}/{next_step_id}', hx_trigger='load'), id=step_id)
