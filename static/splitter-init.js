console.log('🔥 splitter-init.js script loaded and executing!');

// Global variable to track splitter instances by context
window.pipulateSplitterInstances = {};

/**
 * Safely destroys and reinitializes a splitter, preventing gutter accumulation.
 * 
 * @param {Array<string>} elements - An array of selectors for the elements to split.
 * @param {object} defaultOptions - Default options for Split.js, including context for localStorage key.
 */
window.initializePipulateSplitterSafe = function(elements, defaultOptions) {
  const context = defaultOptions.context || 'main';
  
  // Destroy existing splitter instance for this context
  if (window.pipulateSplitterInstances[context] && typeof window.pipulateSplitterInstances[context].destroy === 'function') {
    console.log(`🧹 Destroying existing ${context} splitter to prevent duplicate gutters`);
    window.pipulateSplitterInstances[context].destroy();
    window.pipulateSplitterInstances[context] = null;
  }
  
  // Clean up any orphaned gutter elements
  const orphanedGutters = document.querySelectorAll('.gutter.gutter-horizontal');
  if (orphanedGutters.length > 0) {
    console.log(`🧹 Removing ${orphanedGutters.length} orphaned gutter elements`);
    orphanedGutters.forEach(gutter => gutter.remove());
  }
  
  // Create new splitter instance and store it
  const splitterInstance = window.initializePipulateSplitter(elements, defaultOptions);
  window.pipulateSplitterInstances[context] = splitterInstance;
  
  return splitterInstance;
};

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
}

/**
 * Main splitter initialization function for the primary interface.
 * Moved from server.py to externalize JavaScript properly.
 */
function initMainSplitter() {
  if (window.initializePipulateSplitterSafe) {
    console.log('🔥 Initializing main interface splitter with localStorage persistence');
    const elements = ['#grid-left-content', '#chat-interface'];
    const options = {
      sizes: [65, 35],  // Default sizes - localStorage will override if available
      minSize: [400, 300],
      gutterSize: 10,
      cursor: 'col-resize',
      context: 'main'
    };
    initializePipulateSplitterSafe(elements, options);
  } else {
    // Retry if splitter-init.js hasn't loaded yet
    setTimeout(initMainSplitter, 50);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  initMainSplitter();
});

// Re-initialize after HTMX body swaps (like profile lock)
document.addEventListener('htmx:afterSettle', function(evt) {
  if (evt.target === document.body) {
    console.log('🔄 HTMX body swap detected, re-initializing splitter');
    // Add small delay to ensure DOM is fully settled
    setTimeout(initMainSplitter, 100);
  }
  // Also handle left panel content swaps (like profile navigation)
  else if (evt.target && evt.target.id === 'grid-left-content') {
    console.log('🔄 HTMX left panel swap detected, re-initializing splitter');
    // Add small delay to ensure DOM is fully settled
    setTimeout(initMainSplitter, 100);
  }
});

console.log('✅ window.initializePipulateSplitter function defined!', typeof window.initializePipulateSplitter); 