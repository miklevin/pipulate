The user has just entered the "profile" app from the dropdown menu.

This is also sometimes known as the "client" app.

Profile is fundamental to the system in that as a single-tenant app, it allows
the user to maintain separate profiles for each client, with their own task list
or any other database data.

This is accomplished using the `.xtra()` (extract) method of the MiniDataAPI
spec built into FastHTML. The `id` field of this table:

```python
    profile={              # "profile" exposed to user as endpoint but hardwired to "profile" in the wiring of plugin element IDs in Web UI
        "id": int,         # To be defined as a SQLite auto-increment primary key via MiniDataAPI Spec
        "name": str,       # Name is actually hidden on the menu so real client names are never exposed unless in client (profile) list app
        "menu_name": str,  # Menu name is exposed on the menu so user can switch profiles in front of client without showing other client names
        "address": str,    # Address is actually used for website domain to control other apps like gap analysis
        "code": str,       # Code is actually country code used to control data-pull filters in API integrations like SEMRush
        "active": bool,    # Active lets you toggle the profile on and off in the menu
        "priority": int,   # Controls the sort order of the profile in the menu
        "pk": "id"         # Default SQLite auto-increment primary key so name and menu_name can be freely changed
    }
```

The key point here is that `menu_name` serves as a sort of profile or client
nickname so that the user can feel free to use this app in front of any client
without exposing the names of the other clients when operating the menus.

Going into the profile app itself using the `Edit Profile List` would show the
real client names, so tell them to be careful there if they ask.
