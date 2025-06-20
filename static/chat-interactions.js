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
    setupMenuFlashFeedback();
    
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

    // Test functions
    window.testSSE = function() {
        alert('Latest SSE message: ' + (lastMessage || 'No messages received yet'));
    }
    
    window.sseLastMessage = function() {
        return lastMessage;
    }
    
    console.log('SSE handlers initialized (WebSocket handled by websocket-config.js)');
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

function setupMenuFlashFeedback() {
    console.log('🔔 Setting up simplified menu flash feedback system');
    
    // Simple debouncing to prevent multiple rapid fires
    let profileFlashTimeout = null;
    let appFlashTimeout = null;
    
    // Add minimal CSS for flash animation
    if (!document.getElementById('menu-flash-styles')) {
        const style = document.createElement('style');
        style.id = 'menu-flash-styles';
        style.textContent = `
            .menu-flash {
                animation: menuFlash 0.4s ease-out;
                position: relative;
                z-index: 10;
            }
            
            @keyframes menuFlash {
                0% { box-shadow: 0 0 0 0 rgba(74, 171, 247, 0.9); }
                50% { box-shadow: 0 0 0 10px rgba(74, 171, 247, 0.6); }
                100% { box-shadow: 0 0 0 0 rgba(74, 171, 247, 0); }
            }
            
            [data-theme="dark"] .menu-flash {
                animation: menuFlashDark 0.4s ease-out;
            }
            
            @keyframes menuFlashDark {
                0% { box-shadow: 0 0 0 0 rgba(120, 220, 255, 0.8); }
                50% { box-shadow: 0 0 0 10px rgba(120, 220, 255, 0.5); }
                100% { box-shadow: 0 0 0 0 rgba(120, 220, 255, 0); }
            }
            
            @media (prefers-reduced-motion: reduce) {
                .menu-flash { animation: none; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Simple flash function with debouncing
    function flashMenu(elementId, menuType) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Clear any existing timeout and class
        if (menuType === 'PROFILE') {
            clearTimeout(profileFlashTimeout);
        } else {
            clearTimeout(appFlashTimeout);
        }
        
        element.classList.remove('menu-flash');
        element.offsetHeight; // Force reflow
        element.classList.add('menu-flash');
        
        // Set timeout to remove class
        const timeout = setTimeout(() => {
            element.classList.remove('menu-flash');
        }, 400);
        
        if (menuType === 'PROFILE') {
            profileFlashTimeout = timeout;
        } else {
            appFlashTimeout = timeout;
        }
        
        console.log(`🔔 ${menuType} menu flashed`);
    }
    
    // Only listen to the most reliable event - HTMX afterSwap on the menu containers
    document.addEventListener('htmx:afterSwap', function(event) {
        const targetId = event.target.id;
        
        if (targetId === 'profile-dropdown-menu') {
            flashMenu('profile-id', 'PROFILE');
        } else if (targetId === 'app-dropdown-menu') {
            flashMenu('app-id', 'APP');
        }
    });
    
    // Listen for HTMX requests that will trigger page refresh (Select All/Deselect All/Default)
    document.addEventListener('htmx:beforeRequest', function(event) {
        const target = event.target;
        if (target && target.getAttribute) {
            const hxPost = target.getAttribute('hx-post');
            if (hxPost && (hxPost.includes('select_all') || hxPost.includes('deselect_all') || hxPost.includes('select_default'))) {
                // Store flag that we just triggered a roles bulk action
                sessionStorage.setItem('pipulate_roles_bulk_action', 'true');
                console.log('🔔 Roles bulk action detected, will flash menu after refresh');
            }
        }
    });
    
    // Flash app menu after page load if we just did a roles bulk action
    if (sessionStorage.getItem('pipulate_roles_bulk_action') === 'true') {
        sessionStorage.removeItem('pipulate_roles_bulk_action');
        // Small delay to ensure DOM is ready
        setTimeout(() => {
            flashMenu('app-id', 'APP');
            console.log('🔔 APP menu flashed after roles bulk action');
        }, 150);
    }
    
    console.log('🔔 Simplified menu flash system initialized');
}