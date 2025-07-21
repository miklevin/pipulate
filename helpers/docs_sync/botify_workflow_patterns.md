# 🌐 Botify Workflow Patterns

**Purpose**: Central documentation for Botify API workflows, replacing 150+ line docstrings duplicated across plugins.

---

## 🎯 Botify Workflow Types

### **400_botify_trifecta.py - Base Template**
Complete multi-export data collection workflow downloading:
- Crawl analysis data  
- Web logs data
- Search Console data
- Python code generation for Jupyter debugging

### **110_parameter_buster.py - Derivative**  
Template Config: `TEMPLATE_CONFIG = {'analysis': 'Not Compliant'}`
Focuses on parameter compliance analysis patterns.

### **120_link_graph.py - Derivative**
Template Config: `TEMPLATE_CONFIG = {'analysis': 'Link Graph Edges'}`  
Focuses on internal linking and graph analysis patterns.

---

## 🔥 Critical Botify API Evolution & Business Logic

### **The Painful Reality: Dual API Versions**
Botify's API evolved from BQLv1 to BQLv2, but **BOTH versions coexist** and are **required** for different data types:

- **Web Logs**: Uses BQLv1 with collections/periods structure (OUTER JOIN - all Googlebot visits)
- **Crawl/GSC**: Uses BQLv2 with standard endpoint (INNER JOIN - crawled/indexed URLs only)

### **Critical Business Logic**
Web logs require the **complete universe of URLs** that Googlebot discovered, including those never crawled. BQLv2 crawl collection only provides crawled URLs, fundamentally breaking web logs analysis value proposition (finding crawl gaps).

### **Painful Lessons Learned**
1. Web logs API uses different base URL (`app.botify.com` vs `api.botify.com`)
2. BQLv1 puts dates at payload level, BQLv2 puts them in periods array
3. Same job_type can have different payload structures (legacy vs modern)  
4. Missing dates = broken URLs = 404 errors
5. PrismJS syntax highlighting requires explicit language classes and manual triggers

---

## 🔄 Chain Reaction Pattern

### **Step Flow Implementation**
Each step follows this pattern for reliable chain reaction:

1. **GET handler** returns a div containing the step UI plus an empty div for the next step
2. **SUBMIT handler** returns a revert control plus explicit next step trigger:
   ```python
   Div(id=next_step_id, hx_get=f"/{app_name}/{next_step_id}", hx_trigger="load")
   ```

### **Key Implementation Notes**
- Background tasks use Script tags with htmx.ajax for better UX during long operations
- File paths are deterministic based on username/project/analysis to enable caching
- All API errors are handled with specific error messages for better troubleshooting
- Python code generation optimized for Jupyter Notebook debugging workflow
- Dual BQL version support (v1 for web logs, v2 for crawl/GSC) with proper conversion

---

## 🧩 Workflow Modularity & Flexibility

### **Required vs Optional Steps**

**REQUIRED STEP**: Only Step 2 (crawl data) is actually required because it:
- Establishes the analysis slug that Steps 3 & 4 depend on
- Provides the core site structure data that most analyses need

**OPTIONAL STEPS**: Steps 3 (Web Logs) and 4 (Search Console) are completely optional:
- Can be commented out or deleted without breaking the workflow
- The chain reaction pattern will automatically flow through uninterrupted
- Step 5 (finalize) will still work correctly with just crawl data

**PRACTICAL USAGE**: Many users only need crawl data, making this essentially a "Crawl Analysis Downloader" that can optionally become a full trifecta when needed.

---

## 🚨 HTMX Dynamic Menu Implementation - CRITICAL PATTERN

**⚠️ PRESERVATION WARNING**: This HTMX pattern is essential for dynamic button text and must be preserved during any refactoring. LLMs often strip this out during "creative" refactoring because they don't understand the pattern.

### **Core Components That Must Never Be Removed:**

**1. Route Registration (in __init__ method):**
```python
app.route(f'/{app_name}/update_button_text', methods=['POST'])(self.update_button_text)
```

**2. Form HTMX Attributes (in step templates):**
```python
Form(
    # ... form fields ...
    hx_post=f'/{app_name}/update_button_text',
    hx_target='#submit-button',
    hx_trigger='change',
    hx_include='closest form',
    hx_swap='outerHTML'
)
```

**3. Button ID Consistency:**
```python
# Initial button in form
Button("Process Data", id='submit-button', ...)

# Updated button in update_button_text method
return Button("Download Existing File", id='submit-button', ...)
```

**4. File Check Method (check_cached_file_for_button_text):**
```python
async def check_cached_file_for_button_text(self, username, project_name, analysis_slug, data_type):
    filepath = await self.get_deterministic_filepath(username, project_name, analysis_slug, data_type)
    exists, file_info = await self.check_file_exists(filepath)  # CRITICAL: Proper tuple unpacking
    return exists, file_info if exists else None
```

**5. Dynamic Button Text Method (update_button_text):**
```python
async def update_button_text(self, request):
    try:
        # Extract form data and determine file status
        # Return updated button with proper id='submit-button'
        return Button("Updated Text", id='submit-button', ...)
    except Exception as e:
        # Always return fallback button with proper ID
        return Button("Process Data", id='submit-button', ...)
```

### **How The Pattern Works:**
1. User changes any form field (hx_trigger='change')
2. HTMX sends POST to /update_button_text with full form data (hx_include='closest form')
3. Method checks if cached file exists for current form state
4. Returns updated button text: "Process Data" vs "Download Existing File"
5. Button gets swapped in place (hx_target='#submit-button', hx_swap='outerHTML')

### **Critical Implementation Details:**
- The `check_file_exists` method returns a tuple: `(exists: bool, file_info: dict|None)`
- Must unpack properly: `exists, file_info = await self.check_file_exists(filepath)`
- Button ID must be consistent: `id='submit-button'` in both initial and updated versions
- Template-aware: Button text considers current template selection for accurate filepath generation
- Error handling: Always return a valid button with proper ID, even on exceptions

### **Why LLMs Break This Pattern:**
1. They don't understand the HTMX request/response cycle
2. They see the route registration as "unused" and remove it
3. They "simplify" the button ID thinking it's redundant
4. They break the tuple unpacking in check_cached_file_for_button_text
5. They remove the try/except wrapper thinking it's unnecessary

**DO NOT REFACTOR THIS PATTERN WITHOUT UNDERSTANDING IT COMPLETELY**

---

## 🏗️ WET Inheritance Philosophy

These workflows implement **WET (Write Everything Twice)** for:
- **Radical transparency** - Every operation must be debuggable
- **Self-contained plugins** - No runtime dependencies between workflows
- **AI collaboration** - Complete code visibility for AI assistants
- **User customization** - Ability to modify individual workflows without affecting others

The template reconstruction system (`helpers/rebuild_trifecta_derivatives.sh`) uses AST-based surgical code manipulation to propagate improvements from the base template to derivatives while maintaining their unique configurations.

---

## 🎯 Usage Examples

### **Template Selection Pattern**
```python
# Base trifecta (comprehensive)
TEMPLATE_CONFIG = {}

# Parameter buster (compliance focused)  
TEMPLATE_CONFIG = {'analysis': 'Not Compliant'}

# Link graph (connectivity focused)
TEMPLATE_CONFIG = {'analysis': 'Link Graph Edges'}
```

### **BQL Version Selection**
```python
# Web logs (requires BQLv1)
payload = {
    "collections": [{"name": "web_logs"}],
    "date_range": {"start": start_date, "end": end_date}
}

# Crawl/GSC (can use BQLv2)
payload = {
    "query": "SELECT * FROM crawl", 
    "periods": [{"start": start_date, "end": end_date}]
}
```

This documentation provides complete context for understanding, maintaining, and extending Botify workflows without needing massive docstrings in every plugin file. 