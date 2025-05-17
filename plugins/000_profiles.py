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
        self.pipulate = None
        self.endpoint_prefix = f"/{self.name}"

    def initialize(self, table, pipulate_instance=None):
        """Initialize the plugin with a table and pipulate instance."""
        self.table = table
        self.pipulate = pipulate_instance
        return self

    def get_app(self):
        """Get the profile app instance."""
        return self

    def register_plugin_routes(self):
        """Register plugin routes."""
        if not self.table:
            logger.error("Profile table not initialized")
            return

        # Register the profile render route
        @rt(f"/{self.name}")
        async def profile_route(request):
            return await self.profile_render()

        # Register the profile actions routes
        self.register_routes(rt)

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
        try:
            form = await request.form()
            data = self.prepare_insert_data(form)
            if not data:
                raise ValueError("Invalid profile data")

            # Set default values
            data['active'] = True
            data['priority'] = len(self.table)  # Add to end of list

            # Create the profile
            profile = await self.create_item(**data)
            logger.info(f"Created new profile: {profile.name}")

            # Return the rendered profile
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error inserting profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def toggle_item(self, request, item_id: int):
        """Toggle profile active state."""
        try:
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Toggle active state
            profile.active = not profile.active
            self.table[item_id] = profile
            logger.info(f"Toggled profile {profile.name} active state to {profile.active}")

            # Return updated profile item
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error toggling profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_item(self, request, item_id: int):
        """Update a profile."""
        try:
            form = await request.form()
            data = self.prepare_update_data(form)
            if not data:
                raise ValueError("Invalid profile data")

            # Get the profile
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Update the profile
            for key, value in data.items():
                setattr(profile, key, value)

            # Save the profile
            self.table[item_id] = profile
            logger.info(f"Updated profile: {profile.name}")

            # Return the rendered profile
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def prepare_insert_data(self, form):
        """Prepare data for profile insertion."""
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided")
            return None

        # Get all records to calculate max priority
        records = list(self.table.all())
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

    async def delete_item(self, request, item_id: int):
        """Delete a profile."""
        try:
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Check if profile is in use
            records = list(self.pipulate.table.all())
            records_with_profile = [r for r in records if getattr(r, 'profile_id', None) == item_id]
            if records_with_profile:
                raise ValueError(f"Cannot delete profile: {len(records_with_profile)} records are using it")

            # Delete the profile
            self.table.delete(item_id)
            logger.info(f"Deleted profile: {profile.name}")

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
    delete_url = f"{app_instance.endpoint_prefix}/delete/{profile.id}"
    toggle_url = f"{app_instance.endpoint_prefix}/toggle/{profile.id}"
    update_url = f"{app_instance.endpoint_prefix}/update/{profile.id}"

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
            Button("Update", type="submit")
        ]
    )

    # Create profile content
    profile_content = Div(
        _class="profile-content",
        content=[
            Div(
                _class="profile-header",
                content=[
                    Span(profile.name, _class="profile-name"),
                    delete_icon
                ]
            ),
            Div(
                _class="profile-details",
                content=[
                    P(f"Real Name: {profile.real_name or 'Not set'}"),
                    P(f"Address: {profile.address or 'Not set'}"),
                    P(f"Code: {profile.code or 'Not set'}")
                ]
            ),
            update_form
        ]
    )

    # Create the list item
    return Li(
        _class="profile-item",
        content=[
            active_checkbox,
            profile_content
        ]
    )

class ProfileApp(CrudCustomizer):
    """Profile management app."""
    
    def __init__(self, table, pipulate_instance=None):
        """Initialize the profile app."""
        super().__init__(self)
        self.table = table
        self.pipulate = pipulate_instance
        self.endpoint_prefix = f"/{self.name}"
        logger.debug(f"ProfileApp initialized with table: {table}")

    async def profile_render(self):
        """Render the profiles page."""
        try:
            # Get all profiles, sorted by priority
            profiles = list(self.table.all())
            profiles.sort(key=lambda x: x.priority)

            # Create the profiles list
            profiles_list = Ul(
                *[self.render_item(profile) for profile in profiles],
                _class="profiles-list"
            )

            # Create the add profile form
            add_form = Form(
                _class="add-profile-form",
                _hx_post=f"{self.endpoint_prefix}/insert",
                _hx_target=".profiles-list",
                _hx_swap="beforeend",
                content=[
                    Input(
                        type="text",
                        name="profile_name",
                        placeholder="Profile Name",
                        required=True
                    ),
                    Input(
                        type="text",
                        name="profile_real_name",
                        placeholder="Real Name (optional)"
                    ),
                    Input(
                        type="text",
                        name="profile_address",
                        placeholder=PLACEHOLDER_ADDRESS
                    ),
                    Input(
                        type="text",
                        name="profile_code",
                        placeholder=PLACEHOLDER_CODE
                    ),
                    Button("Add Profile", type="submit")
                ]
            )

            # Return the complete page
            return Container(
                H2("Profiles"),
                add_form,
                profiles_list
            )

        except Exception as e:
            logger.error(f"Error rendering profiles: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def render_item(self, profile):
        """Render a profile item."""
        return render_profile(profile, self)

    async def insert_item(self, request):
        """Insert a new profile."""
        try:
            form = await request.form()
            data = self.prepare_insert_data(form)
            if not data:
                raise ValueError("Invalid profile data")

            # Set default values
            data['active'] = True
            data['priority'] = len(self.table)  # Add to end of list

            # Create the profile
            profile = await self.create_item(**data)
            logger.info(f"Created new profile: {profile.name}")

            # Return the rendered profile
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error inserting profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def toggle_item(self, request, item_id: int):
        """Toggle profile active state."""
        try:
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Toggle active state
            profile.active = not profile.active
            self.table[item_id] = profile
            logger.info(f"Toggled profile {profile.name} active state to {profile.active}")

            # Return updated profile item
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error toggling profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_item(self, request, item_id: int):
        """Update a profile."""
        try:
            form = await request.form()
            data = self.prepare_update_data(form)
            if not data:
                raise ValueError("Invalid profile data")

            # Get the profile
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Update the profile
            for key, value in data.items():
                setattr(profile, key, value)

            # Save the profile
            self.table[item_id] = profile
            logger.info(f"Updated profile: {profile.name}")

            # Return the rendered profile
            return self.render_item(profile)

        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def prepare_insert_data(self, form):
        """Prepare data for profile insertion."""
        profile_name = form.get('profile_name', '').strip()
        if not profile_name:
            logger.warning("Empty profile name provided")
            return None

        # Get all records to calculate max priority
        records = list(self.table.all())
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

    async def delete_item(self, request, item_id: int):
        """Delete a profile."""
        try:
            profile = self.table[item_id]
            if not profile:
                raise ValueError(f"Profile not found: {item_id}")

            # Check if profile is in use
            records = list(self.pipulate.table.all())
            records_with_profile = [r for r in records if getattr(r, 'profile_id', None) == item_id]
            if records_with_profile:
                raise ValueError(f"Cannot delete profile: {len(records_with_profile)} records are using it")

            # Delete the profile
            self.table.delete(item_id)
            logger.info(f"Deleted profile: {profile.name}")

            # Return empty response for HTMX to remove the element
            return ""

        except ValueError as e:
            logger.error(f"Validation error deleting profile: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting profile: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 