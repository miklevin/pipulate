/**
 * HYBRID JAVASCRIPT PATTERN: Static File + Python Parameterization
 * 
 * This file is loaded statically but designed for Python configuration.
 * Python calls window.initializeChatScripts(config) with dynamic parameters.
 * 
 * Usage:
 * 1. Static: <script src="/static/sortable-parameterized-init.js"></script>
 * 2. Dynamic: <script>initializeChatScripts({sortableSelector: '.sortable'})</script>
 * 
 * Benefits: Static caching + Python configuration without templates
 */

// Global initialization function that accepts parameters
window.initializeChatScripts = function(config) {
    console.log('🚀 initializeChatScripts called with config:', config);
    
    // Prevent multiple initialization
    if (window._pipulateInitialized) {
        console.warn('⚠️ Scripts already initialized, skipping duplicate call');
        return;
    }
    
    // Note: Sortable functionality is now handled by dedicated sortable-init.js
    setupWebSocketAndSSE();
    setupInteractions();
    
    // Initialize search plugins keyboard navigation
    if (typeof window.initializeSearchPluginsKeyboardNav === 'function') {
        window.initializeSearchPluginsKeyboardNav();
    }
    
    window._pipulateInitialized = true;
    console.log('✅ Chat scripts initialized (sortable handled separately)');
};

// setupSortable function removed - now handled by dedicated sortable-init.js

function setupWebSocketAndSSE() {
    // SSE Setup
    let lastMessage = null;
    const evtSource = new EventSource("/sse");
    
    evtSource.onmessage = function(event) {
        const data = event.data;
        console.log('SSE received:', data);
        
        // Only process if it's not a ping message
        if (!data.includes('Test ping at')) {
            const todoList = document.getElementById('todo-list');
            if (!todoList) {
                console.error('Could not find todo-list element');
                return;
            }

            const temp = document.createElement('div');
            temp.innerHTML = data;
            
            const newTodo = temp.firstChild;
            if (newTodo) {
                todoList.appendChild(newTodo);
                htmx.process(newTodo);
            }
        }
    };

    // WebSocket message handler
    window.handleWebSocketMessage = function(event) {
        console.log('Sidebar received:', event.data);
        
        // Check if the message is a script
        if (event.data.trim().startsWith('<script>')) {
            const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
            console.log('Executing script:', scriptContent);
            try {
                eval(scriptContent);
            } catch (e) {
                console.error('Error executing script:', e);
            }
            return;
        }
        
        // Check if the response is an HTML element
        if (event.data.trim().startsWith('<')) {
            try {
                const parser = new DOMParser();
                const doc = parser.parseFromString(event.data.trim(), 'text/html');
                const element = doc.body.firstChild;
                
                if (element && element.hasAttribute('data-id')) {
                    const todoList = document.getElementById('todo-list');
                    if (todoList) {
                        todoList.appendChild(element);
                        if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                            new Sortable(todoList, {
                                animation: 150,
                                ghostClass: 'blue-background-class'
                            });
                            todoList.classList.add('sortable-initialized');
                        }
                    }
                    return;
                }
            } catch (e) {
                console.error('Error parsing HTML:', e);
            }
        }
        
        // Handle regular chat messages
        const sidebarMsgList = document.getElementById('msg-list');
        const sidebarCurrentMessage = document.createElement('div');
        sidebarCurrentMessage.className = 'message assistant';
        
        if (!sidebarCurrentMessage.parentElement) {
            sidebarMsgList.appendChild(sidebarCurrentMessage);
        }
        
        // Handle line breaks in messages
        if (event.data.includes('\\n')) {
            const lines = event.data.split('\\n');
            sidebarCurrentMessage.innerHTML += lines.map(line => {
                const linkedLine = linkifyText(line);
                return line.trim() ? `<p>${linkedLine}</p>` : '<br>';
            }).join('');
        } else {
            sidebarCurrentMessage.innerHTML += linkifyText(event.data);
        }
        
        sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
    };

    // Test functions
    window.testSSE = function() {
        alert('Latest SSE message: ' + (lastMessage || 'No messages received yet'));
    }
    
    window.sseLastMessage = function() {
        return lastMessage;
    }
    
    console.log('WebSocket and SSE handlers initialized');
}

function setupInteractions() {
    // Form reset after submission
    document.addEventListener('htmx:afterSwap', function(event) {
        // Handle both todo-list and competitor-list targets
        if ((event.target.id === 'todo-list' || event.target.id === 'competitor-list') && event.detail.successful) {
            const targetId = event.target.id;
            
            const form = document.querySelector(`form[hx-target="#${targetId}"]`);
            
            if (form) {
                form.reset();
            } else {
                // Try alternative selectors if the first one doesn't work
                const allForms = document.querySelectorAll('form[hx-target]');
                
                // Look for forms with matching target attributes
                allForms.forEach(f => {
                    if (f.getAttribute('hx-target') === `#${targetId}`) {
                        f.reset();
                    }
                });
            }
        }
    });

    // Add Enter/Shift+Enter handling for chat textarea
    const textarea = document.getElementById('msg');
    if (textarea) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                // Find the form and submit it
                var form = textarea.closest('form');
                if (form) {
                    form.requestSubmit ? form.requestSubmit() : form.submit();
                }
            }
            // else allow Shift+Enter for newline
        });
    }
}

/* ============================================================================
   SEARCH PLUGINS KEYBOARD NAVIGATION - Carson Gross HTMX Approach
   ============================================================================
   
   Keyboard navigation for search plugins dropdown following HTMX principles:
   • HTMX handles the heavy lifting (search API calls, DOM updates)
   • Minimal JavaScript for UI interaction (keyboard navigation)
   • Progressive enhancement - works without JavaScript
   • Clean separation of concerns
   
   🎯 FEATURES:
   • Arrow key navigation (up/down with wrapping)
   • Enter key selection and navigation
   • Escape key dismissal
   • Click-away dismissal with selection clearing
   • Mouse hover compatibility
   ============================================================================ */

// Global search plugins keyboard navigation functions
window.initializeSearchPluginsKeyboardNav = function() {
    console.log('🔍 Initializing Search Plugins keyboard navigation');
    
    const searchInput = document.getElementById('nav-plugin-search');
    const dropdown = document.getElementById('search-results-dropdown');
    
    if (!searchInput || !dropdown) {
        console.warn('⚠️ Search plugins elements not found, skipping keyboard nav setup');
        return;
    }
    
    let selectedIndex = -1;
    
    // Global Ctrl+K shortcut to activate search
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey && event.key === 'k') {
            event.preventDefault();
            searchInput.focus();
            searchInput.select(); // Select all text for easy replacement
            console.log('🔍 Search activated via Ctrl+K');
        }
    });
    
    // Keyboard navigation for search input
    searchInput.addEventListener('keydown', function(event) {
        const items = dropdown.querySelectorAll('.search-result-item');
        
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            if (dropdown.style.display === 'none' || items.length === 0) return;
            
            // Clear previous selection
            if (selectedIndex >= 0 && items[selectedIndex]) {
                items[selectedIndex].classList.remove('selected');
            }
            
            // Move to next item (wrap to first)
            selectedIndex = (selectedIndex + 1) % items.length;
            items[selectedIndex].classList.add('selected');
            
            // Scroll into view if needed
            items[selectedIndex].scrollIntoView({ block: 'nearest' });
            
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            if (dropdown.style.display === 'none' || items.length === 0) return;
            
            // Clear previous selection
            if (selectedIndex >= 0 && items[selectedIndex]) {
                items[selectedIndex].classList.remove('selected');
            }
            
            // Move to previous item (wrap to last)
            selectedIndex = selectedIndex <= 0 ? items.length - 1 : selectedIndex - 1;
            items[selectedIndex].classList.add('selected');
            
            // Scroll into view if needed
            items[selectedIndex].scrollIntoView({ block: 'nearest' });
            
        } else if (event.key === 'Enter') {
            event.preventDefault();
            if (selectedIndex >= 0 && items[selectedIndex]) {
                // Simulate click on selected item
                items[selectedIndex].click();
            } else if (items.length === 1) {
                // No manual selection but only one result - select it
                items[0].click();
                console.log('🎯 Enter pressed on single unselected result - navigating');
            }
            
        } else if (event.key === 'Escape') {
            // Hide dropdown and clear selection
            dropdown.style.display = 'none';
            clearSearchSelection();
            searchInput.blur();
        }
    });
    
    // Clear selection when new search results arrive
    function clearSearchSelection() {
        selectedIndex = -1;
        const items = dropdown.querySelectorAll('.search-result-item.selected');
        items.forEach(item => item.classList.remove('selected'));
    }
    
    // Reset selection when dropdown content changes (HTMX updates)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                clearSearchSelection();
                // Auto-select single result after content update
                autoSelectSingleResult();
            }
        });
    });
    
    observer.observe(dropdown, { childList: true, subtree: true });
    
    // Auto-select single result function
    function autoSelectSingleResult() {
        const items = dropdown.querySelectorAll('.search-result-item');
        
        // Only auto-select if there's exactly one result and it has the auto-select marker
        if (items.length === 1 && items[0].classList.contains('auto-select-single')) {
            selectedIndex = 0;
            items[0].classList.add('selected');
            console.log('🎯 Auto-selected single search result');
        }
    }
    
    // Make auto-select function globally available for server-triggered calls
    window.initializeSearchPluginsAutoSelect = autoSelectSingleResult;
    
    // Global click handler for click-away dismissal
    document.addEventListener('click', function(event) {
        if (!searchInput.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.style.display = 'none';
            clearSearchSelection();
        }
    });
    
    console.log('✅ Search Plugins keyboard navigation initialized');
};

function linkifyText(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return '<a href="' + url + '" target="_blank">' + url + '</a>';
    });
}

// Splitter initialization removed - now handled by dedicated splitter-init.js