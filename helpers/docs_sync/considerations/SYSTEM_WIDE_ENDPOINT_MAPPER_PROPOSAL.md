# System-Wide Endpoint Mapper Proposal

## **Problem Statement**

The session hijacking URL mapping bug revealed a fundamental architectural issue: **multiple systems attempting the same app_name → endpoint mapping with different, brittle logic**.

**Current Pain Points:**
- String manipulation errors in filename → endpoint parsing
- Duplicate mapping logic across `server.py` and `mcp_tools.py`
- No centralized registry of plugin endpoints
- Fragile fallback logic when mappings fail

## **Proposed Solution: Plugin Endpoint Registry**

### **Core Architecture**

**1. Registration-Time Mapping Creation**
```python
class PluginEndpointRegistry:
    """
    Centralized registry populated during plugin discovery.
    Single source of truth for all app_name ↔ endpoint mappings.
    """
    
    def __init__(self):
        self._registry = {}  # app_name → endpoint_info
        
    def register_plugin(self, filename: str, app_name: str, instance):
        """Called during plugin discovery to build the registry"""
        # Extract endpoint from filename (once, correctly)
        endpoint = self._extract_endpoint_from_filename(filename)
        
        self._registry[app_name] = {
            'filename': filename,
            'endpoint': endpoint,
            'full_url': f"http://localhost:5001/{endpoint}",
            'instance': instance,
            'display_name': getattr(instance, 'DISPLAY_NAME', endpoint.title())
        }
    
    def get_endpoint_url(self, app_name: str) -> str:
        """Single method for all app_name → URL lookups"""
        if app_name in self._registry:
            return self._registry[app_name]['full_url']
        
        # Graceful fallback with logging
        logger.warning(f"Unknown app_name '{app_name}', using fallback mapping")
        return f"http://localhost:5001/{app_name}_workflow"
    
    def _extract_endpoint_from_filename(self, filename: str) -> str:
        """Centralized, tested filename → endpoint logic"""
        # Remove .py extension
        name = filename.replace('.py', '')
        
        # Remove numeric prefix if present
        parts = name.split('_')
        if parts[0].isdigit():
            parts = parts[1:]
            
        return '_'.join(parts)
```

**2. Global Registry Instance**
```python
# In server.py global scope
plugin_endpoint_registry = PluginEndpointRegistry()

# During plugin discovery
for filename, instance in plugin_instances.items():
    if hasattr(instance, 'APP_NAME'):
        plugin_endpoint_registry.register_plugin(
            filename=filename,
            app_name=instance.APP_NAME,
            instance=instance
        )
```

**3. Unified Usage Across Codebase**
```python
# Session hijacking (server.py)
def _determine_user_workflow_context():
    # ... extract app_name from pipeline_id ...
    workflow_endpoint = plugin_endpoint_registry.get_endpoint_url(app_name)
    return {"main_endpoint": workflow_endpoint, ...}

# Browser automation (mcp_tools.py)  
def _browser_automate_workflow_walkthrough():
    # ... get app_name from database ...
    plugin_url = plugin_endpoint_registry.get_endpoint_url(app_name)
    driver.get(plugin_url)

# Navigation menus
def create_plugin_menu_item():
    endpoint_url = plugin_endpoint_registry.get_endpoint_url(app_name)
    return A(display_name, href=endpoint_url)
```

### **Implementation Benefits**

**✅ Single Source of Truth**
- One place for filename → endpoint parsing logic
- All systems use the same mapping method
- Eliminates duplicate, divergent implementations

**✅ Error Resilience**  
- Centralized error handling and logging
- Graceful fallbacks when mappings fail
- Easy to debug mapping issues

**✅ Non-Breaking Migration**
- Registry can be introduced gradually
- Existing direct mapping calls still work
- Optional migration path for each system

**✅ Testing & Validation**
- Registry can validate all mappings on startup
- Unit tests for mapping logic in one place
- Easy to verify endpoint accessibility

**✅ Future Extensibility**
- Registry can hold additional metadata (roles, descriptions, etc.)
- Support for dynamic endpoint registration
- Plugin discovery improvements

### **Migration Strategy**

**Phase 1: Registry Introduction (Non-Breaking)**
```python
# Add registry alongside existing logic
plugin_endpoint_registry = PluginEndpointRegistry()

# Session hijacking - fallback to registry if plugin lookup fails
try:
    # ... existing complex plugin lookup ...
except:
    workflow_endpoint = plugin_endpoint_registry.get_endpoint_url(app_name)
```

**Phase 2: Gradual Migration**
- Replace session hijacking complex lookup with registry call
- Update browser automation to use registry
- Migrate navigation menu generation

**Phase 3: Registry-First Architecture**
- Remove all direct filename parsing
- Registry becomes the authoritative source
- Add validation and error reporting

### **Testing Scenarios**

```python
def test_endpoint_registry():
    registry = PluginEndpointRegistry()
    
    # Test normal case
    registry.register_plugin("040_hello_workflow.py", "hello", mock_instance)
    assert registry.get_endpoint_url("hello") == "http://localhost:5001/hello_workflow"
    
    # Test edge case - no numeric prefix
    registry.register_plugin("documentation.py", "docs", mock_instance)  
    assert registry.get_endpoint_url("docs") == "http://localhost:5001/documentation"
    
    # Test fallback
    assert registry.get_endpoint_url("unknown") == "http://localhost:5001/unknown_workflow"
```

## **Conclusion**

This registry pattern would:
1. **Prevent the bug we just fixed** from ever happening again
2. **Simplify the codebase** by centralizing mapping logic  
3. **Improve reliability** with better error handling
4. **Enable future improvements** to plugin discovery and routing

The migration can be **gradual and non-breaking**, making it a safe architectural improvement. 