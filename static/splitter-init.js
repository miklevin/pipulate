console.log('🔥 splitter-init.js script loaded and executing!');

/**
 * Initializes a draggable splitter between two elements.
 * It uses sizes provided by the server and saves changes back to the server.
 *
 * @param {Array<string>} elements - An array of selectors for the elements to split.
 * @param {object} defaultOptions - Default options for Split.js, including initial sizes from the server.
 */
window.initializePipulateSplitter = function(elements, defaultOptions) {
  console.log('🟢 FUNCTION START - initializePipulateSplitter executing!');
  console.log('🟢 FUNCTION START - elements:', elements);
  console.log('🟢 FUNCTION START - defaultOptions:', defaultOptions);
  
  try {
    console.log('🔧 initializePipulateSplitter called with elements:', elements, 'and options:', defaultOptions);
    
    if (typeof Split === 'undefined') {
      console.error('Split.js is not loaded. Make sure it is included in your HTML.');
      alert('Split.js is not loaded!');
      return;
    }
    
    // Check if HTMX is available at initialization time
    console.log('🔍 HTMX available at init time:', typeof htmx !== 'undefined');

    // The initial sizes are now passed directly in defaultOptions.sizes.
    // We just need to modify onDragEnd to save back to the server instead of localStorage.

    console.log('🛠️ Building options object...');
    const options = {
      sizes: defaultOptions.sizes || [65, 35],
      minSize: defaultOptions.minSize || [400, 300],
      gutterSize: defaultOptions.gutterSize || 10,
      cursor: defaultOptions.cursor || 'col-resize',
      onStart: function(sizes) {
        console.log('🚀 Split onStart called with sizes:', sizes);
      },
      onDrag: function(sizes) {
        console.log('🔄 Split onDrag called with sizes:', sizes);
      },
      onDragEnd: function(sizes) {
        console.log('🎯 onDragEnd called with sizes:', sizes);
        
        // Add visible alert for testing
        alert('Drag ended! Sizes: ' + JSON.stringify(sizes));
        
        // Check if HTMX is available
        if (typeof htmx === 'undefined') {
          console.error('❌ HTMX is not available! Cannot save split sizes.');
          return;
        }
        
        console.log('✅ HTMX is available, sending POST request to /save-split-sizes');
        
        try {
          // Use HTMX to post the new sizes to the server endpoint.
          htmx.ajax('POST', '/save-split-sizes', {
            values: { sizes: JSON.stringify(sizes) },
            swap: 'none' // We don't need to swap any content from the response.
          });
          console.log('📤 HTMX request sent for sizes:', sizes);
        } catch (error) {
          console.error('💥 Error making HTMX request:', error);
        }

        // Call original onDragEnd if it was provided (for future flexibility)
        if (typeof defaultOptions.onDragEnd === 'function') {
          console.log('🔄 Calling original onDragEnd callback');
          defaultOptions.onDragEnd(sizes);
        }
      }
    };

    console.log('🚀 Creating Split.js instance with final options:', options);
    const splitInstance = Split(elements, options);
    console.log('✅ Split.js instance created:', splitInstance);
    
    return splitInstance;
    
  } catch (error) {
    console.error('💥 Error in initializePipulateSplitter:', error);
    console.error('💥 Error stack:', error.stack);
    alert('Error in initializePipulateSplitter: ' + error.message);
  }
}

console.log('✅ window.initializePipulateSplitter function defined!', typeof window.initializePipulateSplitter); 