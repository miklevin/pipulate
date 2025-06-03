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
    
    const sortableSelector = config.sortableSelector || '.sortable';
    const ghostClass = config.ghostClass || 'blue-background-class';
    
    setupSortable(sortableSelector, ghostClass);
    setupWebSocketAndSSE();
    setupInteractions();
    
    window._pipulateInitialized = true;
    console.log('✅ All scripts initialized with config:', config);
};

function setupSortable(sortableSelector, ghostClass) {
    console.log('🔧 Setting up sortable with selector:', sortableSelector);
    const sortableEl = document.querySelector(sortableSelector);
    
    if (sortableEl) {
        console.log('✅ Found sortable element:', sortableEl);
        
        // Check if sortable is already initialized on this element
        if (sortableEl._sortable) {
            console.warn('⚠️ Sortable already initialized on this element, destroying previous instance');
            sortableEl._sortable.destroy();
        }
        
        // Track if user is actually dragging vs clicking to expand/collapse 
        let isDragging = false;
        let startPosition = null;
        let dragStartTime = null;
        
        const sortableInstance = new Sortable(sortableEl, {
            animation: 150,
            ghostClass: ghostClass,
            onStart: function (evt) {
                // Reset drag state and capture starting position
                isDragging = false;
                startPosition = { x: evt.originalEvent?.clientX || 0, y: evt.originalEvent?.clientY || 0 };
                dragStartTime = Date.now();
                console.log('🎯 Drag start detected:', {
                    oldIndex: evt.oldIndex,
                    startPosition: startPosition,
                    timestamp: dragStartTime
                });
            },
            onMove: function (evt, originalEvent) {
                // This is called when item is being moved - indicates actual dragging
                if (!isDragging) {
                    isDragging = true;
                    console.log('✅ Actual drag movement detected - will allow sort request');
                }
                // Let the drag continue (don't return false)
                return true;
            },
            onEnd: function (evt) {
                const dragEndTime = Date.now();
                const dragDuration = dragEndTime - (dragStartTime || dragEndTime);
                
                // EMERGENCY DEBUGGING: Capture stack trace to see what called this
                const stackTrace = new Error().stack;
                
                console.log('🔍 SortableJS onEnd triggered:', {
                    isDragging: isDragging,
                    oldIndex: evt.oldIndex,
                    newIndex: evt.newIndex,
                    dragDuration: dragDuration + 'ms',
                    wasActualDrag: isDragging && evt.oldIndex !== evt.newIndex,
                    item: evt.item?.id,
                    from: evt.from?.id,
                    to: evt.to?.id,
                    stackTrace: stackTrace
                });
                
                // CRITICAL DEBUG: Check if onStart was actually called
                if (dragStartTime === null) {
                    console.error('🚨 CRITICAL: onEnd called but onStart was never called!');
                    console.error('🚨 This suggests SortableJS is being triggered programmatically');
                    console.error('🚨 Stack trace:', stackTrace);
                    // Still don't send sort request for phantom events
                    return;
                }
                
                // SUPER STRICT: Only allow sort if we have clear evidence of dragging
                if (!isDragging || evt.oldIndex === evt.newIndex) {
                    console.log('🚫 Blocking sort request: isDragging=' + isDragging + ', same position=' + (evt.oldIndex === evt.newIndex));
                    return; 
                }
                
                console.log(`✅ Valid drag-and-drop completed: ${evt.oldIndex} → ${evt.newIndex} - sending sort request`);
                
                // Build items array for the current order
                let items = Array.from(sortableEl.children).map((item, index) => ({
                    id: item.dataset.id,
                    priority: index
                }));
                
                console.log('📦 Items to sort:', items);
                
                // Try to get plugin name from the sortable element's data attribute first
                let pluginName = sortableEl.dataset.pluginName;
                
                // Fallback to URL parsing if no data attribute
                if (!pluginName) {
                    let path = window.location.pathname;
                    let basePath = path;
                    
                    if (path.endsWith('/')) {
                        basePath = path.slice(0, -1);
                    }
                    
                    pluginName = basePath.split('/').pop();
                }
                
                // Use the hx-post attribute if available, otherwise construct URL
                let sortUrl = sortableEl.getAttribute('hx-post') || ('/' + pluginName + '_sort');
                
                console.log('🚀 Sending sort request to:', sortUrl);
                
                htmx.ajax('POST', sortUrl, {
                    target: sortableEl,
                    swap: 'none',
                    values: { items: JSON.stringify(items) }
                });
                
                // Reset tracking variables
                isDragging = false;
                startPosition = null;
                dragStartTime = null;
            }
        });
        
        // Store reference to prevent duplicate initialization
        sortableEl._sortable = sortableInstance;
        
        console.log('✅ Sortable initialized successfully');
    } else {
        console.warn('⚠️ Sortable element not found with selector:', sortableSelector);
    }
}

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
}

function linkifyText(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return '<a href="' + url + '" target="_blank">' + url + '</a>';
    });
} 