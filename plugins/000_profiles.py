from fasthtml.common import (
    Container, Grid, Div, Card, H2, Ul, Form, Group, Input, Button, Li, Span, A, Hr,
    Label, Details, Summary, Select, Option, Textarea, Script, Link, Meta, Title,
    HTTPException, HTMLResponse, to_xml
)
from server import (
    BaseCrud, DB_FILENAME, LIST_SUFFIX,
    PLACEHOLDER_ADDRESS, PLACEHOLDER_CODE, NOWRAP_STYLE,
    get_current_profile_id,
    db,
    logger,
    rt
)
import os
import re
import sys
import fastlite
import json
from typing import Optional, List, Dict, Any
from pipulate.server import (
    profiles, pipulate
)

# Constants
PLACEHOLDER_ADDRESS = "Address (optional)"
PLACEHOLDER_CODE = "Code (optional)"
NOWRAP_STYLE = "white-space: nowrap;"

ROLES = ['Core']

class PluginIdentityManager:
    """Plugin identity manager for profiles."""
    
    def __init__(self):
        """Initialize the plugin identity manager."""
        self.name = "profiles"
        self.display_name = "Profiles"
        self.description = "Manage user profiles"
        self.version = "1.0.0"
        self.author = "Pipulate Team"
        self.roles = ROLES
        self.table = None
        self.profile_app = None
        self.pipulate = None

    def initialize(self, table, pipulate_instance=None):
        """Initialize the plugin with a table and pipulate instance."""
        self.table = table
        self.pipulate = pipulate_instance
        self.profile_app = ProfileApp(table, pipulate_instance)
        return self

    def get_app(self):
        """Get the profile app instance."""
        return self.profile_app

    def register_plugin_routes(self):
        """Register plugin routes."""
        if not self.profile_app:
            logger.error("Profile app not initialized")
            return

        # Register the profile render route
        @rt(f"/{self.name}")
        async def profile_route(request):
            return await self.profile_app.profile_render()

        # Register the profile actions routes
        self.profile_app.register_routes(rt)

class CrudCustomizer(BaseCrud):
    """Custom CRUD operations for profiles."""
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.table = plugin.table
        self.pipulate = plugin.pipulate

    def render_item(self, item):
        """Render a profile item."""
        return render_profile(item, self)

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

    async def toggle_item(self, request):
        """Toggle profile active state."""
        try:
            profile_id = request.path_params.get('id')
            if not profile_id:
                raise ValueError("No profile ID provided")

            profile = self.table.get(profile_id)
            if not profile:
                raise ValueError(f"Profile not found: {profile_id}")

            # Toggle active state
            profile.active = not profile.active
            self.table.update(profile)

            # Return updated profile item
            return render_profile(profile, self)

        except Exception as e:
            logger.error(f"Error toggling profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

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
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided")
            return None

        # Get all records to calculate max priority
        records = self.table.all()
        max_priority = max([r.priority for r in records], default=0)

        insert_data = {
            'name': profile_name,
            'real_name': form.get('profile_real_name', '').strip(),
            'address': form.get('profile_address', '').strip(),
            'code': form.get('profile_code', '').strip(),
            'active': True,
            'priority': max_priority + 1
        }
        logger.debug(f"Prepared insert data: {insert_data}")
        return insert_data

    def prepare_update_data(self, form):
        """Prepare data for profile update."""
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided for update")
            return None

        update_data = {
            'name': profile_name,
            'real_name': form.get('profile_real_name', '').strip(),
            'address': form.get('profile_address', '').strip(),
            'code': form.get('profile_code', '').strip()
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data

    async def delete_item(self, request):
        """Delete a profile."""
        try:
            profile_id = request.path_params.get('id')
            if not profile_id:
                raise ValueError("No profile ID provided")

            profile = self.table.get(profile_id)
            if not profile:
                raise ValueError(f"Profile not found: {profile_id}")

            # Check if profile is in use
            records = self.pipulate.table()
            records_with_profile = [r for r in records if getattr(r, 'profile_id', None) == profile_id]
            if records_with_profile:
                raise ValueError(f"Cannot delete profile: {len(records_with_profile)} records are using it")

            # Delete the profile
            self.table.delete(profile_id)
            logger.info(f"Deleted profile: {profile_id}")

            # Return empty response for HTMX to remove the element
            return ""

        except ValueError as e:
            logger.error(f"Validation error deleting profile: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

def render_profile(profile, app_instance: CrudCustomizer):
    """Render a profile item with HTMX functionality."""
    # Construct HTMX URLs
    delete_url = f"{app_instance.plugin.endpoint_prefix}/delete/{profile.id}"
    toggle_url = f"{app_instance.plugin.endpoint_prefix}/toggle/{profile.id}"
    update_url = f"{app_instance.plugin.endpoint_prefix}/update/{profile.id}"

    # Create delete icon
    delete_icon = Span(
        _class="delete-icon",
        _style="cursor: pointer; color: red;",
        _hx_delete=delete_url,
        _hx_confirm="Are you sure you want to delete this profile?",
        _hx_target="closest li",
        _hx_swap="outerHTML",
        content="🗑️"
    )

    # Create active checkbox
    active_checkbox = Input(
        type="checkbox",
        name="active",
        checked=profile.active,
        _hx_post=toggle_url,
        _hx_target="closest li",
        _hx_swap="outerHTML"
    )

    # Create update form
    update_form = Form(
        _class="update-form",
        _style="display: none;",
        _hx_put=update_url,
        _hx_target="closest li",
        _hx_swap="outerHTML",
        content=[
            Input(
                type="text",
                name="profile_name",
                value=profile.name,
                placeholder="Profile Name",
                required=True
            ),
            Input(
                type="text",
                name="profile_real_name",
                value=profile.real_name or "",
                placeholder="Real Name (optional)"
            ),
            Input(
                type="text",
                name="profile_address",
                value=profile.address or "",
                placeholder=PLACEHOLDER_ADDRESS
            ),
            Input(
                type="text",
                name="profile_code",
                value=profile.code or "",
                placeholder=PLACEHOLDER_CODE
            ),
            Button(
                type="submit",
                content="Update"
            )
        ]
    )

    # Create profile info
    profile_info = Div(
        _class="profile-info",
        content=[
            Span(
                _class="profile-name",
                _style="cursor: pointer;",
                _onclick="this.parentElement.nextElementSibling.style.display = 'block'",
                content=profile.name
            ),
            Span(
                _class="profile-details",
                content=[
                    f"Real Name: {profile.real_name}" if profile.real_name else None,
                    f"Address: {profile.address}" if profile.address else None,
                    f"Code: {profile.code}" if profile.code else None
                ]
            )
        ]
    )

    # Create list item
    return Li(
        _class="profile-item",
        _style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem;",
        _data_priority=profile.priority,
        _data_active=str(profile.active).lower(),
        content=[
            delete_icon,
            active_checkbox,
            profile_info,
            update_form
        ]
    )

# class ProfileApp(BaseCrud):
#     """Profile management application."""
#     
#     def __init__(self, table, pipulate_instance=None):
#         """Initialize the profile app."""
#         super().__init__(
#             name="profiles",
#             table=table,
#             toggle_field="active",
#             sort_field="priority",
#             pipulate_instance=pipulate_instance
#         )
# 
#     async def profile_render(self):
#         """Render the profile list page."""
#         all_profiles = profiles()
#         logger.debug("Initial profile state:")
#         for profile in all_profiles:
#             logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")
# 
#         ordered_profiles = sorted(
#             all_profiles,
#             key=lambda p: p.priority if p.priority is not None else float('inf')
#         )
# 
#         logger.debug("Ordered profile list:")
#         for profile in ordered_profiles:
#             logger.debug(f"Profile {profile.id}: name = {profile.name}, priority = {profile.priority}")
# 
#         return Container(
#             Grid(
#                 Div(
#                     Card(
#                         H2(f"{self.name.capitalize()} {LIST_SUFFIX}"),
#                         Ul(
#                             *[self.render_item(profile) for profile in ordered_profiles],
#                             id='profile-list',
#                             cls='sortable',
#                             style="padding-left: 0;"
#                         ),
#                         header=Form(
#                             Group(
#                                 Input(
#                                     placeholder="Nickname",
#                                     name="profile_name",
#                                     id="profile-name-input",
#                                     autofocus=True
#                                 ),
#                                 Input(
#                                     placeholder=f"Real Name",
#                                     name="profile_menu_name",
#                                     id="profile-menu-name-input"
#                                 ),
#                                 Input(
#                                     placeholder=PLACEHOLDER_ADDRESS,
#                                     name="profile_address",
#                                     id="profile-address-input"
#                                 ),
#                                 Input(
#                                     placeholder=PLACEHOLDER_CODE,
#                                     name="profile_code",
#                                     id="profile-code-input"
#                                 ),
#                                 Button(
#                                     "Add",
#                                     type="submit",
#                                     id="add-profile-button"
#                                 ),
#                             ),
#                             hx_post=f"/{self.name}",
#                             hx_target="#profile-list",
#                             hx_swap="beforeend",
#                             hx_swap_oob="true",
#                             hx_on__after_request="this.reset(); document.getElementById('profile-name-input').focus();"
#                         ),
#                     ),
#                     id="content-container",
#                 ),
#             ),
#         )

    def render_item(self, profile):
        """Render a profile item."""
        return render_profile(profile, self)

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

    async def toggle_item(self, request):
        """Toggle profile active state."""
        try:
            profile_id = request.path_params.get('id')
            if not profile_id:
                raise ValueError("No profile ID provided")

            profile = self.table.get(profile_id)
            if not profile:
                raise ValueError(f"Profile not found: {profile_id}")

            # Toggle active state
            profile.active = not profile.active
            self.table.update(profile)

            # Return updated profile item
            return render_profile(profile, self)

        except Exception as e:
            logger.error(f"Error toggling profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

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
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided")
            return None

        # Get all records to calculate max priority
        records = self.table.all()
        max_priority = max([r.priority for r in records], default=0)

        insert_data = {
            'name': profile_name,
            'real_name': form.get('profile_real_name', '').strip(),
            'address': form.get('profile_address', '').strip(),
            'code': form.get('profile_code', '').strip(),
            'active': True,
            'priority': max_priority + 1
        }
        logger.debug(f"Prepared insert data: {insert_data}")
        return insert_data

    def prepare_update_data(self, form):
        """Prepare data for profile update."""
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided for update")
            return None

        update_data = {
            'name': profile_name,
            'real_name': form.get('profile_real_name', '').strip(),
            'address': form.get('profile_address', '').strip(),
            'code': form.get('profile_code', '').strip()
        }
        logger.debug(f"Prepared update data: {update_data}")
        return update_data

    async def delete_item(self, request):
        """Delete a profile."""
        try:
            profile_id = request.path_params.get('id')
            if not profile_id:
                raise ValueError("No profile ID provided")

            profile = self.table.get(profile_id)
            if not profile:
                raise ValueError(f"Profile not found: {profile_id}")

            # Check if profile is in use
            records = self.pipulate.table()
            records_with_profile = [r for r in records if getattr(r, 'profile_id', None) == profile_id]
            if records_with_profile:
                raise ValueError(f"Cannot delete profile: {len(records_with_profile)} records are using it")

            # Delete the profile
            self.table.delete(profile_id)
            logger.info(f"Deleted profile: {profile_id}")

            # Return empty response for HTMX to remove the element
            return ""

        except ValueError as e:
            logger.error(f"Validation error deleting profile: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 