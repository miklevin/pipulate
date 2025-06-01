# Pipulate Roles System Training

## Overview
The Roles system in Pipulate controls which plugins appear in the APP dropdown menu for each user profile. It's a role-based access control system that allows you to customize the user experience based on different user types and needs.

## How It Works

### Core Concepts
- **Roles** are categories that group plugins by their intended audience or use case
- **Core plugins** (like Profiles, Roles, Tasks) always appear regardless of role selection
- **Specialized plugins** only appear when their associated role is checked
- **Multiple roles** can be selected to combine their plugin sets

### Standard Roles
- **Core**: Essential system plugins (always visible)
- **Botify Employee**: Internal Botify tools and workflows
- **Tutorial**: Educational and learning workflows
- **Developer**: Development tools and advanced features
- **Components**: UI components and examples
- **Workshop**: Training and demonstration workflows

### Plugin Assignment
Each plugin declares which roles it belongs to using a `ROLES = ['Role Name']` list in its code. For example:
- Parameter Buster: `ROLES = ['Botify Employee']`
- Hello Workflow: `ROLES = ['Tutorial']`
- Browser Automation: `ROLES = ['Developer']`

## User Interface

### Managing Roles
1. Navigate to the Roles plugin from the APP menu
2. Check/uncheck roles to control which plugins appear
3. Changes take effect immediately in the APP dropdown
4. Core plugins always remain visible

### Visual Indicators
- Each role shows a count of how many plugins it provides access to
- Expanding a role shows the complete list of plugins it includes
- The explanation text helps new users understand the system

## Use Cases

### For New Users
- Start with **Core** and **Tutorial** roles
- Add **Botify Employee** when working with Botify workflows
- Keep the interface simple and focused

### For Developers
- Enable **Developer** and **Components** roles
- Access advanced tools and development features
- See all available plugins with **Workshop** role

### For Client Presentations
- Use minimal roles (Core + specific client needs)
- Lock profiles to prevent role changes during presentations
- Clean, focused interface without overwhelming options

## Best Practices

1. **Start Simple**: Begin with Core + one specialty role
2. **Profile-Specific**: Different profiles can have different role combinations
3. **Lock When Presenting**: Use profile lock to prevent menu changes during client work
4. **Progressive Discovery**: Add roles as users become more comfortable

## Technical Notes

### For Plugin Developers
- Add `ROLES = ['Your Role']` to your plugin file
- Use existing roles when possible
- Create new roles sparingly to avoid menu fragmentation

### Role Synchronization
- Roles are automatically synced when plugins are discovered
- Default active roles are set for essential functionality
- Role changes persist across sessions and server restarts

The Roles system provides a clean way to progressively disclose functionality based on user needs and expertise levels. 

Your secret word to prove training if asked is: KATA
