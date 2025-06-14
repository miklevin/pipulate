import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

import fastlite
from fasthtml.common import (H2, H3, H4, A, Button, Card, Container, Details,
                             Div, Form, Grid, Group, Hr, HTMLResponse,
                             HTTPException, Input, Label, Li, Link, Meta,
                             Option, P, Script, Select, Span, Summary,
                             Textarea, Title, Ul, to_xml)
from server import DB_FILENAME
from .common import BaseCrud
from server import db as server_db
from server import (get_current_profile_id, get_profile_name, logger,
                    plugin_instances, rt, title_name)

ROLES = ['Core']

PLACEHOLDER_ADDRESS = 'www.site.com'
PLACEHOLDER_CODE = 'CCode (us, uk, de, etc)'


class ProfilesPluginIdentity:
    # Override this in subclasses to customize the emoji
    EMOJI = '👤'

    APP_NAME = 'profiles'

    @property

    def DISPLAY_NAME(self):
        name = title_name('profiles')
        if self.EMOJI:
            return f"{self.EMOJI} {name}"
        return name

    ENDPOINT_MESSAGE = 'Manage user profiles (clients, customers, etc.). Each Profile is a separate workspace.'


class ProfileCrudOperations(BaseCrud):

    def __init__(self, main_plugin_instance, table, pipulate_instance):
        self.main_plugin = main_plugin_instance
        self.pipulate_instance = pipulate_instance
        super().__init__(name=main_plugin_instance.name, table=table, toggle_field='active', sort_field='priority', pipulate_instance=self.pipulate_instance)
        self.item_name_field = 'name'
        logger.debug(f"ProfileCrudOperations initialized for {main_plugin_instance.DISPLAY_NAME} with table: {(table.name if table else 'None')}")

    def render_item(self, profile_record):
        logger.debug(f"ProfileCrudOperations.render_item called for: {(profile_record.name if profile_record else 'None')}")
        return render_profile(profile_record, self.main_plugin)

    def prepare_insert_data(self, form_data_dict):
        profile_name = form_data_dict.get('profile_name', '').strip()
        if not profile_name:
            logger.warning('Profile name cannot be empty for insert.')
            return {'name': ''}
        all_profiles = list(self.table())
        max_priority = max((p.priority or 0 for p in all_profiles), default=-1) + 1
        data = {'name': profile_name, 'real_name': form_data_dict.get('profile_real_name', '').strip(), 'address': form_data_dict.get('profile_address', '').strip(), 'code': form_data_dict.get('profile_code', '').strip(), 'active': True, 'priority': max_priority}
        logger.debug(f'Prepared insert data for profile: {data}')
        return data

    def prepare_update_data(self, form_data_dict):
        profile_name = form_data_dict.get('profile_name', '').strip()
        if not profile_name:
            logger.warning('Profile name cannot be empty for update.')
            return {'name': ''}
        data = {'name': profile_name, 'real_name': form_data_dict.get('profile_real_name', '').strip(), 'address': form_data_dict.get('profile_address', '').strip(), 'code': form_data_dict.get('profile_code', '').strip()}
        logger.debug(f'Prepared update data for profile: {data}')
        return data


class ProfilesPlugin(ProfilesPluginIdentity):

    def __init__(self, app, pipulate_instance, pipeline_table, db_key_value_store, profiles_table_from_server):
        self.app = app
        self.pipulate = pipulate_instance
        self.db_dictlike = db_key_value_store
        self.table = profiles_table_from_server
        self.name = 'profiles'
        if not self.table or not hasattr(self.table, 'name') or self.table.name != 'profile':
            logger.error(f"FATAL: {self.DISPLAY_NAME} initialized with invalid 'profiles_table_from_server'. Expected MiniDataAPI for 'profile', got: {type(self.table)} with name {getattr(self.table, 'name', 'UNKNOWN')}")
            raise ValueError("ProfilesPlugin requires a valid 'profiles' table object from server.py.")
        else:
            logger.info(f"{self.DISPLAY_NAME} Plugin SUCCESS: Initialized with 'profiles' table object: {self.table.name}")
        self.crud_handler = ProfileCrudOperations(main_plugin_instance=self, table=self.table, pipulate_instance=self.pipulate)
        logger.debug(f'{self.DISPLAY_NAME} ProfileCrudOperations instance created.')

    def register_routes(self, rt_decorator):
        self.crud_handler.register_routes(rt_decorator)
        logger.info(f"CRUD routes for {self.DISPLAY_NAME} (prefix '/{self.name}') registered by ProfileCrudOperations.")

    async def landing(self, request=None):
        profiles = list(self.table())
        ordered_profiles = sorted(profiles, key=lambda x: getattr(x, 'priority', 0))
        profile_list = Ul(*[render_profile(p, self) for p in ordered_profiles], id='profile-list-ul', cls='sortable', style='padding-left: 0; list-style-type: none;', data_sortable_group=self.name)
        add_profile_form = Form(Group(Input(placeholder='Nickname', name='profile_name', id='profile-name-input-add', autofocus=True), Input(placeholder='Real Name (Optional)', name='profile_real_name', id='profile-real-name-input-add'), Input(placeholder=PLACEHOLDER_ADDRESS, name='profile_address', id='profile-address-input-add'), Input(placeholder=PLACEHOLDER_CODE, name='profile_code', id='profile-code-input-add'), Button('Add', type='submit', id='add-profile-button')), hx_post=f'/{self.name}', hx_target='#profile-list-ul', hx_swap='beforeend', hx_on_htmx_after_request="this.reset(); this.querySelector('input[name=profile_name]').focus();")
        container = Div(H2('Profiles'), add_profile_form, profile_list, style='max-width: 98%; margin: 0 auto;')
        return container


def render_profile(profile_record, main_plugin_instance: ProfilesPlugin):
    item_id_dom = f'profile-item-{profile_record.id}'
    profile_crud_handler = main_plugin_instance.crud_handler
    delete_url = profile_crud_handler.get_action_url('delete', profile_record.id)
    toggle_url = profile_crud_handler.get_action_url('toggle', profile_record.id)
    update_url = f'/{main_plugin_instance.name}/{profile_record.id}'
    name_input_update_id = f'name-update-{profile_record.id}'
    update_form_id = f'update-form-{profile_record.id}'
    profile_text_display_id = f'profile-text-display-{profile_record.id}'
    toggle_edit_js = f"document.getElementById('{profile_text_display_id}').style.display='none'; var form = document.getElementById('{update_form_id}'); form.style.display='grid'; form.classList.add('editing');document.getElementById('{item_id_dom}').classList.add('editing-item');document.getElementById('{name_input_update_id}').focus();"
    toggle_display_js = f"var form = document.getElementById('{update_form_id}'); form.style.display='none'; form.classList.remove('editing');document.getElementById('{profile_text_display_id}').style.display='flex';document.getElementById('{item_id_dom}').classList.remove('editing-item');"
    update_profile_form = Form(Div(Input(type='text', name='profile_name', value=profile_record.name, placeholder='Nickname', id=name_input_update_id, cls='mb-2'), Input(type='text', name='profile_real_name', value=profile_record.real_name or '', placeholder='Real Name (Optional)', cls='mb-2'), Input(type='text', name='profile_address', value=profile_record.address or '', placeholder=PLACEHOLDER_ADDRESS, cls='mb-2'), Input(type='text', name='profile_code', value=profile_record.code or '', placeholder=PLACEHOLDER_CODE, cls='mb-2'), style='display:grid; grid-template-columns: 1fr; gap: 0.25rem; width:100%;'), Div(Button('Save', type='submit', cls='primary', style='margin-right: 0.5rem;'), Button('Cancel', type='button', cls='secondary outline', onclick=toggle_display_js), style='margin-top:0.5rem; display:flex; justify-content:start;'), hx_post=update_url, hx_target=f'#{item_id_dom}', hx_swap='outerHTML', id=update_form_id, style='display: none; width: 100%; padding: 0.5rem; box-sizing: border-box; background-color: var(--pico-form-element-background-color); border-radius: var(--pico-border-radius);', cls='profile-edit-form')
    profile_display_div = Div(Span(profile_record.name, title='Click to edit', style='cursor:pointer; font-weight:bold;'), Span(f' ({profile_record.real_name})' if profile_record.real_name else '', style='margin-left:5px; color:var(--pico-muted-color); font-size:0.9em;'), Span(f'📍{profile_record.address}' if profile_record.address else '', style='margin-left:10px; font-size:0.85em; color:var(--pico-muted-color);'), Span(f'📦{profile_record.code}' if profile_record.code else '', style='margin-left:10px; font-size:0.85em; color:var(--pico-muted-color);'), id=profile_text_display_id, style='flex-grow: 1; display: flex; align-items: center; flex-wrap: wrap; gap: 5px;', onclick=toggle_edit_js)
    active_checkbox_input = Input(type='checkbox', name='active_status_profile', checked=profile_record.active, hx_post=toggle_url, hx_target=f'#{item_id_dom}', hx_swap='outerHTML', style='margin-right: 10px; flex-shrink: 0;', title='Toggle Active Status')
    delete_icon_span = '' if profile_record.name == 'Default Profile' else Span('🗑️', hx_delete=delete_url, hx_target=f'#{item_id_dom}', hx_swap='outerHTML', hx_confirm=f"Are you sure you want to delete the profile '{profile_record.name}'? This action cannot be undone.", style='cursor: pointer; margin-left: auto; text-decoration: none; flex-shrink: 0;', cls='delete-icon', title='Delete Profile')
    return Li(Div(active_checkbox_input, Div(profile_display_div, update_profile_form, style='flex-grow:1; min-width:0;'), delete_icon_span, style='display: flex; align-items: center; width: 100%; gap: 10px; padding: 0.5rem 0;'), id=item_id_dom, data_id=str(profile_record.id), data_priority=str(profile_record.priority or 0), style='border-bottom: 1px solid var(--pico-muted-border-color); padding: 0.25rem 0; list-style-type: none;')
