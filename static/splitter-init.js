console.log('🔥 splitter-init.js script loaded and executing!');

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

console.log('✅ window.initializePipulateSplitter function defined!', typeof window.initializePipulateSplitter); 