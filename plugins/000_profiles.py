"""Profile management plugin for Pipulate."""

from typing import Optional, Dict, Any
import logging
import json
from pathlib import Path
from fasthtml.common import *
from server import BaseCrud, DB_FILENAME, LIST_SUFFIX
from loguru import logger
import os
import re
import sys
import fastlite
from pipulate.server import (
    Container, Grid, Div, Card, H2, Ul, Form, Group, Input, Button,
    Li, Span, LIST_SUFFIX, PLACEHOLDER_ADDRESS, PLACEHOLDER_CODE,
    get_current_profile_id, profiles, pipulate, logger, rt, BaseCrud
)

# Constants
PLACEHOLDER_ADDRESS = "Address (optional)"
PLACEHOLDER_CODE = "Code (optional)"

ROLES = ['Core']

class PluginIdentityManager:
    """Manages plugin identity and discovery."""
    
    def __init__(self):
        self.name = "profiles"
        self.description = "Profile management for Pipulate"
        self.version = "1.0.0"
        self.author = "Mike Levin"
        self.dependencies = []

class CrudCustomizer:
    """Customizes CRUD operations for profiles."""
    
    def __init__(self, table, pipulate_instance):
        self.table = table
        self.pipulate_instance = pipulate_instance
        self.db_filename = DB_FILENAME
        self.list_suffix = LIST_SUFFIX
        self.base_crud = BaseCrud(table, pipulate_instance)

    def render_item(self, item):
        """Render a profile item."""
        return render_profile(item)

    async def insert_item(self, request):
        """Insert a new profile."""
        form = await request.form()
        data = self.prepare_insert_data(form)
        
        # Set default values
        data['active'] = True
        data['priority'] = len(self.table)  # Add to end of list
        
        # Create the profile
        profile = await self.create_item(**data)
        
        # Return the rendered profile
        return self.render_item(profile)

    async def toggle_item(self, request, item_id: int):
        """Toggle a profile's active state."""
        profile = self.table[item_id]
        profile.active = not profile.active
        self.table[item_id] = profile
        return self.render_item(profile)

    async def update_item(self, request, item_id: int):
        """Update a profile."""
        form = await request.form()
        data = self.prepare_update_data(form)
        
        # Get the profile
        profile = self.table[item_id]
        
        # Update the profile
        for key, value in data.items():
            setattr(profile, key, value)
        
        # Save the profile
        self.table[item_id] = profile
        
        # Return the rendered profile
        return self.render_item(profile)

    def prepare_insert_data(self, form):
        """Prepare data for profile insertion."""
        return {
            'name': form.get('profile_name', ''),
            'menu_name': form.get('profile_menu_name', ''),
            'address': form.get('profile_address', ''),
            'code': form.get('profile_code', '')
        }

    def prepare_update_data(self, form):
        """Prepare data for profile update."""
        return {
            'name': form.get('profile_name', ''),
            'menu_name': form.get('profile_menu_name', ''),
            'address': form.get('profile_address', ''),
            'code': form.get('profile_code', '')
        }

def render_profile(profile):
    """Render a profile item in the list."""
    def count_records_with_xtra(table_handle, xtra_field, xtra_value):
        """Count records with a specific xtra field value."""
        count = 0
        for record in table_handle:
            if getattr(record, xtra_field, None) == xtra_value:
                count += 1
        return count

    # Get the current profile ID
    current_profile_id = get_current_profile_id()
    
    # Determine if this profile is selected
    is_selected = profile.id == current_profile_id
    
    # Count records with this profile
    record_count = count_records_with_xtra(pipulate.table(), 'profile_id', profile.id)
    
    # Create the profile item container
    profile_item = Li(
        # Profile selection form
        Form(
            # Selection button
            Button(
                "✓" if is_selected else "○",
                type="submit",
                name="profile_id",
                value=profile.id,
                cls="outline" if not is_selected else "primary",
                style="width: 40px; height: 40px; padding: 0; margin-right: 10px;"
            ),
            # Profile name display
            Span(
                profile.name,
                style="font-weight: bold; margin-right: 10px;"
            ),
            # Record count badge
            Span(
                f"{record_count} records",
                style="font-size: 0.8em; color: var(--pico-muted-color); margin-right: 10px;"
            ),
            # Profile menu name if different
            Span(
                f"({profile.menu_name})" if profile.menu_name and profile.menu_name != profile.name else "",
                style="font-size: 0.8em; color: var(--pico-muted-color);"
            ),
            # Form attributes
            hx_post="/select_profile",
            hx_target="body",
            hx_swap="outerHTML",
            style="display: flex; align-items: center; margin: 0;"
        ),
        # Profile actions container
        Div(
            # Edit button
            Button(
                "✎",
                type="button",
                cls="outline",
                style="width: 40px; height: 40px; padding: 0; margin-right: 5px;",
                onclick=f"editProfile({profile.id})"
            ),
            # Delete button
            Button(
                "×",
                type="button",
                cls="outline",
                style="width: 40px; height: 40px; padding: 0;",
                onclick=f"deleteProfile({profile.id})"
            ),
            style="display: flex; align-items: center; margin-left: auto;"
        ),
        style="display: flex; align-items: center; justify-content: space-between; padding: 10px; margin-bottom: 5px; border: 1px solid var(--pico-muted-border-color); border-radius: var(--pico-border-radius);"
    )
    
    return profile_item

class ProfileApp(BaseCrud):
    """Profile management application."""
    
    def __init__(self, table, pipulate_instance=None):
        """Initialize the profile app."""
        super().__init__(
            name="profiles",
            table=table,
            toggle_field="active",
            sort_field="priority",
            pipulate_instance=pipulate_instance
        )

    async def profile_render(self):
        """Render the profile list page."""
        all_profiles = profiles()
        logger.debug("Initial profile state:")
        for profile in all_profiles:
            logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

        ordered_profiles = sorted(
            all_profiles,
            key=lambda p: p.priority if p.priority is not None else float('inf')
        )

        logger.debug("Ordered profile list:")
        for profile in ordered_profiles:
            logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")

        return Container(
            Grid(
                Div(
                    Card(
                        H2(f"{self.name.capitalize()} {LIST_SUFFIX}"),
                        Ul(
                            *[self.render_item(profile) for profile in ordered_profiles],
                            id='profile-list',
                            cls='sortable',
                            style="padding-left: 0;"
                        ),
                        header=Form(
                            Group(
                                Input(
                                    placeholder="Nickname",
                                    name="profile_name",
                                    id="profile-name-input",
                                    autofocus=True
                                ),
                                Input(
                                    placeholder=f"Real Name",
                                    name="profile_menu_name",
                                    id="profile-menu-name-input"
                                ),
                                Input(
                                    placeholder=PLACEHOLDER_ADDRESS,
                                    name="profile_address",
                                    id="profile-address-input"
                                ),
                                Input(
                                    placeholder=PLACEHOLDER_CODE,
                                    name="profile_code",
                                    id="profile-code-input"
                                ),
                                Button(
                                    "Add",
                                    type="submit",
                                    id="add-profile-button"
                                ),
                            ),
                            hx_post=f"/{self.name}",
                            hx_target="#profile-list",
                            hx_swap="beforeend",
                            hx_swap_oob="true",
                            hx_on__after_request="this.reset(); document.getElementById('profile-name-input').focus();"
                        ),
                    ),
                    id="content-container",
                ),
            ),
        )

    def render_item(self, profile):
        """Render a profile item."""
        return render_profile(profile)

    async def insert_item(self, request):
        """Insert a new profile."""
        form = await request.form()
        data = self.prepare_insert_data(form)
        
        # Set default values
        data['active'] = True
        data['priority'] = len(self.table)  # Add to end of list
        
        # Create the profile
        profile = await self.create_item(**data)
        
        # Return the rendered profile
        return self.render_item(profile)

    async def toggle_item(self, request, item_id: int):
        """Toggle a profile's active state."""
        profile = self.table[item_id]
        profile.active = not profile.active
        self.table[item_id] = profile
        return self.render_item(profile)

    async def update_item(self, request, item_id: int):
        """Update a profile."""
        form = await request.form()
        data = self.prepare_update_data(form)
        
        # Get the profile
        profile = self.table[item_id]
        
        # Update the profile
        for key, value in data.items():
            setattr(profile, key, value)
        
        # Save the profile
        self.table[item_id] = profile
        
        # Return the rendered profile
        return self.render_item(profile)

    def prepare_insert_data(self, form):
        """Prepare data for profile insertion."""
        return {
            'name': form.get('profile_name', ''),
            'menu_name': form.get('profile_menu_name', ''),
            'address': form.get('profile_address', ''),
            'code': form.get('profile_code', '')
        }

    def prepare_update_data(self, form):
        """Prepare data for profile update."""
        return {
            'name': form.get('profile_name', ''),
            'menu_name': form.get('profile_menu_name', ''),
            'address': form.get('profile_address', ''),
            'code': form.get('profile_code', '')
        } 