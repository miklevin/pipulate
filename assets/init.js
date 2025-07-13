/**
 * PIPULATE INITIALIZATION SYSTEM
 * 
 * Consolidated initialization for all third-party library configurations.
 * Each section is self-contained and checks for its dependencies.
 */

console.log('🚀 Pipulate initialization system loading');

// =============================================================================
// MARKED.JS CONFIGURATION
// =============================================================================

/**
 * Configures marked.js for consistent Markdown rendering across the application.
 * Sets up GitHub Flavored Markdown (GFM) with line breaks and other options.
 * 
 * Usage: Include this script before any code that uses marked.parse()
 */
window.initializeMarked = function() {
    console.log('🔤 Initializing Marked.js configuration');
    
    if (typeof marked === 'undefined') {
        console.error('❌ marked.js is not available');
        return;
    }
    
    // Configure marked with GFM and sensible defaults for chat
    marked.use({
        // Disable automatic line breaks within paragraphs
        // Two spaces + newline OR double newline for line breaks/paragraphs
        breaks: false, // Keep this as false for standard markdown paragraph/line break handling
        
        // Enable GitHub Flavored Markdown features
        gfm: true,
        
        // Additional options for better chat experience
        headerIds: false,  // Don't generate header IDs (not needed in chat)
        mangle: false,     // Don't mangle email addresses
        
        // Custom renderer overrides for chat-specific behavior
        renderer: {
            // Ensure code blocks have proper classes for Prism.js
            code(code, language) {
                const lang = language || 'text';
                return `<pre><code class="language-${lang}">${code}</code></pre>`;
            },
            
            // Disable automatic URL linking - return just the text
            link(href, title, text) {
                return text;
            }
        }
    });
    
    console.log('✅ Marked.js configured with GFM and breaks disabled');
};

// Auto-initialize if marked is already available
if (typeof marked !== 'undefined') {
    window.initializeMarked();
} else {
    // Wait for marked to be loaded
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof marked !== 'undefined') {
            window.initializeMarked();
        } else {
            console.warn('⚠️ marked.js still not available after DOM loaded');
        }
    });
}

// =============================================================================
// SORTABLEJS CONFIGURATION
// =============================================================================

/**
 * Initializes SortableJS drag-and-drop functionality on specified elements.
 * Handles automatic persistence via HTMX and provides clean drag detection.
 *
 * @param {string} selector - CSS selector for sortable elements (default: '.sortable')
 * @param {object} options - Configuration options
 */
window.initializePipulateSortable = function(selector = '.sortable', options = {}) {
    if (typeof Sortable === 'undefined') {
        console.error('SortableJS is not loaded. Make sure it is included in your HTML.');
        return;
    }

    const sortableSelector = selector;
    const ghostClass = options.ghostClass || 'blue-background-class';
    const animation = options.animation || 150;
    const dragThreshold = options.dragThreshold || 5; // pixels
    const minDragDuration = options.minDragDuration || 50; // milliseconds

    console.log('🔧 Setting up sortable with selector:', sortableSelector);
    const sortableEl = document.querySelector(sortableSelector);
    
    if (!sortableEl) {
        console.warn('⚠️ Sortable element not found with selector:', sortableSelector);
        return null;
    }

    console.log('✅ Found sortable element:', sortableEl);
    
    // Check if sortable is already initialized on this element
    if (sortableEl._sortable) {
        console.log('🔄 Sortable already initialized, destroying previous instance');
        sortableEl._sortable.destroy();
    }
    
    // Track actual dragging vs click/touch events
    let isDragging = false;
    let startPosition = null;
    let dragStartTime = null;
    
    const sortableInstance = new Sortable(sortableEl, {
        animation: animation,
        ghostClass: ghostClass,
        
        onStart: function (evt) {
            // Reset drag state and capture starting position
            isDragging = false;
            startPosition = { 
                x: evt.originalEvent?.clientX || 0, 
                y: evt.originalEvent?.clientY || 0 
            };
            dragStartTime = Date.now();
            
            console.log('🎯 Drag start detected:', {
                oldIndex: evt.oldIndex,
                item: evt.item?.id,
                startPosition: startPosition
            });
        },
        
        onMove: function (evt, originalEvent) {
            // Calculate drag distance to determine if this is actual dragging
            if (!isDragging && startPosition) {
                const currentX = originalEvent?.clientX || 0;
                const currentY = originalEvent?.clientY || 0;
                const dragDistance = Math.sqrt(
                    Math.pow(currentX - startPosition.x, 2) + 
                    Math.pow(currentY - startPosition.y, 2)
                );
                
                if (dragDistance > dragThreshold) {
                    isDragging = true;
                    console.log('✅ Actual drag movement detected (distance: ' + dragDistance.toFixed(1) + 'px)');
                }
            }
            
            return true; // Allow the drag to continue
        },
        
        onEnd: function (evt) {
            const dragEndTime = Date.now();
            const dragDuration = dragEndTime - (dragStartTime || dragEndTime);
            
            console.log('🔍 SortableJS onEnd triggered:', {
                isDragging: isDragging,
                oldIndex: evt.oldIndex,
                newIndex: evt.newIndex,
                dragDuration: dragDuration + 'ms',
                item: evt.item?.id
            });
            
            // Only process if we have clear evidence of dragging
            if (!isDragging || 
                evt.oldIndex === evt.newIndex || 
                dragDuration < minDragDuration ||
                dragStartTime === null) {
                console.log('🚫 Blocking sort request - not a valid drag operation');
                return;
            }
            
            console.log(`✅ Valid drag completed: ${evt.oldIndex} → ${evt.newIndex}`);
            
            // Build items array for the current order
            const items = Array.from(sortableEl.children).map((item, index) => ({
                id: item.dataset.id,
                priority: index
            }));
            
            // Get sort endpoint from element attributes or construct from plugin name
            let sortUrl = sortableEl.getAttribute('hx-post');
            if (!sortUrl) {
                const pluginName = sortableEl.dataset.pluginName || 
                                window.location.pathname.split('/').pop();
                sortUrl = '/' + pluginName + '_sort';
            }
            
            console.log('🚀 Sending sort request to:', sortUrl, 'with items:', items);
            
            // Check if HTMX is available
            if (typeof htmx === 'undefined') {
                console.error('❌ HTMX is not available! Cannot save sort order.');
                return;
            }
            
            try {
                // Send sort request via HTMX
                htmx.ajax('POST', sortUrl, {
                    target: sortableEl,
                    swap: 'none',
                    values: { items: JSON.stringify(items) }
                });
            } catch (error) {
                console.error('Error sending sort request:', error);
            }
            
            // Reset tracking variables
            isDragging = false;
            startPosition = null;
            dragStartTime = null;
            
            // Call original onEnd callback if provided
            if (typeof options.onEnd === 'function') {
                options.onEnd(evt);
            }
        }
    });
    
    // Store reference to prevent duplicate initialization and allow manual destruction
    sortableEl._sortable = sortableInstance;
    
    console.log('✅ Sortable initialized successfully on:', sortableSelector);
    return sortableInstance;
};

/**
 * Convenience function that matches the existing setupSortable signature
 * for backward compatibility with existing HTMX callbacks
 */
window.setupSortable = function(selector, ghostClass) {
    return window.initializePipulateSortable(selector, { ghostClass: ghostClass });
};

console.log('✅ Sortable functions defined:', {
    initializePipulateSortable: typeof window.initializePipulateSortable,
    setupSortable: typeof window.setupSortable
});

// =============================================================================
// SPLIT.JS CONFIGURATION  
// =============================================================================

/**
 * Initializes a draggable splitter between two elements.
 * It uses sizes from localStorage with context-specific keys for persistence.
 *
 * @param {Array<string>} elements - An array of selectors for the elements to split.
 * @param {object} defaultOptions - Default options for Split.js, including context for localStorage key.
 */
window.initializePipulateSplitter = function(elements, defaultOptions) {
    if (typeof Split === 'undefined') {
        console.error('Split.js is not loaded. Make sure it is included in your HTML.');
        return;
    }

    // Determine the localStorage key based on context
    const context = defaultOptions.context || 'main';
    const localStorageKey = `pipulate-split-sizes-${context}`;
    
    // Try to load sizes from localStorage first, fallback to defaultOptions.sizes
    let savedSizes = defaultOptions.sizes || [65, 35];
    try {
        const storedSizes = localStorage.getItem(localStorageKey);
        if (storedSizes) {
            const parsedSizes = JSON.parse(storedSizes);
            if (Array.isArray(parsedSizes) && parsedSizes.length === elements.length) {
                savedSizes = parsedSizes;
                console.log(`✅ Loaded ${context} split sizes from localStorage:`, savedSizes);
            }
        }
    } catch (error) {
        console.warn(`Warning: Could not load split sizes from localStorage for ${context}:`, error);
    }
    
    const options = {
        sizes: savedSizes,
        minSize: defaultOptions.minSize || [400, 300],
        gutterSize: defaultOptions.gutterSize || 10,
        cursor: defaultOptions.cursor || 'col-resize',
        onDragEnd: function(sizes) {
            try {
                // Save to localStorage with context-specific key
                localStorage.setItem(localStorageKey, JSON.stringify(sizes));
                console.log(`💾 Saved ${context} split sizes to localStorage:`, sizes);
            } catch (error) {
                console.error(`Error saving ${context} split sizes to localStorage:`, error);
            }

            // Call original onDragEnd if it was provided (for future flexibility)
            if (typeof defaultOptions.onDragEnd === 'function') {
                defaultOptions.onDragEnd(sizes);
            }
        }
    };

    const splitInstance = Split(elements, options);
    console.log(`🔧 Initialized ${context} splitter with sizes:`, savedSizes);
    return splitInstance;
};

console.log('✅ Splitter function defined:', typeof window.initializePipulateSplitter);

// =============================================================================
// INITIALIZATION COMPLETE
// =============================================================================

console.log('✅ Pipulate initialization system ready!'); 