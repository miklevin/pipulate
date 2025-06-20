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
    console.log('🔔 Setting up menu flash feedback system');
    
    // Add CSS for flash animation if not already present
    if (!document.getElementById('menu-flash-styles')) {
        const style = document.createElement('style');
        style.id = 'menu-flash-styles';
        style.textContent = `
            .menu-flash {
                animation: menuUpdateFlash 0.6s ease-out;
                transform-origin: center;
                position: relative;
                z-index: 10;
            }
            
            @keyframes menuUpdateFlash {
                0% { 
                    box-shadow: 0 0 0 0 rgba(74, 171, 247, 0.5);
                    transform: scale(1);
                }
                25% { 
                    box-shadow: 0 0 0 6px rgba(74, 171, 247, 0.3);
                    transform: scale(1.015);
                }
                50% { 
                    box-shadow: 0 0 0 10px rgba(74, 171, 247, 0.15);
                    transform: scale(1.01);
                }
                75% { 
                    box-shadow: 0 0 0 12px rgba(74, 171, 247, 0.08);
                    transform: scale(1.005);
                }
                100% { 
                    box-shadow: 0 0 0 0 rgba(74, 171, 247, 0);
                    transform: scale(1);
                }
            }
            
            /* Darker theme variant with cooler blue */
            [data-theme="dark"] .menu-flash {
                animation: menuUpdateFlashDark 0.6s ease-out;
            }
            
            @keyframes menuUpdateFlashDark {
                0% { 
                    box-shadow: 0 0 0 0 rgba(120, 220, 255, 0.4);
                    transform: scale(1);
                }
                25% { 
                    box-shadow: 0 0 0 6px rgba(120, 220, 255, 0.25);
                    transform: scale(1.015);
                }
                50% { 
                    box-shadow: 0 0 0 10px rgba(120, 220, 255, 0.12);
                    transform: scale(1.01);
                }
                75% { 
                    box-shadow: 0 0 0 12px rgba(120, 220, 255, 0.06);
                    transform: scale(1.005);
                }
                100% { 
                    box-shadow: 0 0 0 0 rgba(120, 220, 255, 0);
                    transform: scale(1);
                }
            }
            
            /* Respect reduced motion preferences for accessibility */
            @media (prefers-reduced-motion: reduce) {
                .menu-flash {
                    animation: menuUpdateFlashReduced 0.3s ease-out;
                }
                
                @keyframes menuUpdateFlashReduced {
                    0% { 
                        box-shadow: 0 0 0 0 rgba(74, 171, 247, 0.3);
                    }
                    50% { 
                        box-shadow: 0 0 0 4px rgba(74, 171, 247, 0.2);
                    }
                    100% { 
                        box-shadow: 0 0 0 0 rgba(74, 171, 247, 0);
                    }
                }
                
                [data-theme="dark"] .menu-flash {
                    animation: menuUpdateFlashReducedDark 0.3s ease-out;
                }
                
                @keyframes menuUpdateFlashReducedDark {
                    0% { 
                        box-shadow: 0 0 0 0 rgba(120, 220, 255, 0.25);
                    }
                    50% { 
                        box-shadow: 0 0 0 4px rgba(120, 220, 255, 0.15);
                    }
                    100% { 
                        box-shadow: 0 0 0 0 rgba(120, 220, 255, 0);
                    }
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Function to flash a menu element
    function flashMenuElement(elementId, menuType) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`🔔 Menu flash: Element ${elementId} not found`);
            return;
        }
        
        console.log(`🔔 Flashing ${menuType} menu (${elementId})`);
        
        // Remove any existing flash class
        element.classList.remove('menu-flash');
        
        // Force reflow to ensure the class removal takes effect
        element.offsetHeight;
        
        // Add flash class
        element.classList.add('menu-flash');
        
        // Determine animation duration based on reduced motion preference
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const animationDuration = prefersReducedMotion ? 300 : 600;
        
        // Remove the class after animation completes
        setTimeout(() => {
            element.classList.remove('menu-flash');
        }, animationDuration);
    }
    
    // Listen for HTMX afterSwap events to detect menu updates
    document.addEventListener('htmx:afterSwap', function(event) {
        const targetId = event.target.id;
        
        if (targetId === 'profile-dropdown-menu') {
            console.log('🔔 Profile menu updated via HTMX');
            flashMenuElement('profile-id', 'PROFILE');
        } else if (targetId === 'app-dropdown-menu') {
            console.log('🔔 App menu updated via HTMX');
            flashMenuElement('app-id', 'APP');
        }
    });
    
    // Listen for HX-Trigger events directly (more reliable than custom events)
    document.addEventListener('htmx:trigger', function(event) {
        if (event.detail && event.detail.refreshProfileMenu !== undefined) {
            console.log('🔔 Profile menu refresh trigger detected');
            // Small delay to ensure the HTMX swap happens first
            setTimeout(() => flashMenuElement('profile-id', 'PROFILE'), 25);
        }
        
        if (event.detail && event.detail.refreshAppMenu !== undefined) {
            console.log('🔔 App menu refresh trigger detected');
            // Small delay to ensure the HTMX swap happens first
            setTimeout(() => flashMenuElement('app-id', 'APP'), 25);
        }
    });
    
    // Also listen for custom events that might trigger menu updates (fallback)
    document.addEventListener('refreshProfileMenu', function() {
        console.log('🔔 Profile menu refresh event detected (custom event)');
        setTimeout(() => flashMenuElement('profile-id', 'PROFILE'), 25);
    });
    
    document.addEventListener('refreshAppMenu', function() {
        console.log('🔔 App menu refresh event detected (custom event)');
        setTimeout(() => flashMenuElement('app-id', 'APP'), 25);
    });
    
    console.log('🔔 Menu flash feedback system initialized with enhanced animations');
}