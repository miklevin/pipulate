console.log('🔥 splitter-init.js script loaded and executing!');

/**
 * Initializes a draggable splitter between two elements.
 * It uses sizes provided by the server and saves changes back to the server.
 *
 * @param {Array<string>} elements - An array of selectors for the elements to split.
 * @param {object} defaultOptions - Default options for Split.js, including initial sizes from the server.
 */
window.initializePipulateSplitter = function(elements, defaultOptions) {
  if (typeof Split === 'undefined') {
    console.error('Split.js is not loaded. Make sure it is included in your HTML.');
    return;
  }

  // The initial sizes are now passed directly in defaultOptions.sizes.
  // We modify onDragEnd to save back to the server instead of localStorage.
  const options = {
    sizes: defaultOptions.sizes || [65, 35],
    minSize: defaultOptions.minSize || [400, 300],
    gutterSize: defaultOptions.gutterSize || 10,
    cursor: defaultOptions.cursor || 'col-resize',
    onDragEnd: function(sizes) {
      // Check if HTMX is available
      if (typeof htmx === 'undefined') {
        console.error('❌ HTMX is not available! Cannot save split sizes.');
        return;
      }
      
      try {
        // Use HTMX to post the new sizes to the server endpoint.
        htmx.ajax('POST', '/save-split-sizes', {
          values: { sizes: JSON.stringify(sizes) },
          swap: 'none' // We don't need to swap any content from the response.
        });
      } catch (error) {
        console.error('Error saving split sizes:', error);
      }

      // Call original onDragEnd if it was provided (for future flexibility)
      if (typeof defaultOptions.onDragEnd === 'function') {
        defaultOptions.onDragEnd(sizes);
      }
    }
  };

  const splitInstance = Split(elements, options);
  return splitInstance;
}

console.log('✅ window.initializePipulateSplitter function defined!', typeof window.initializePipulateSplitter); 