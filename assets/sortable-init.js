console.log('🔧 sortable-init.js script loaded and executing!');

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

console.log('✅ window.initializePipulateSortable function defined!', typeof window.initializePipulateSortable);
console.log('✅ window.setupSortable compatibility function defined!', typeof window.setupSortable); 