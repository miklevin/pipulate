/**
 * Initializes a draggable splitter between two elements.
 * It persists the user's chosen layout size in localStorage.
 *
 * @param {Array<string>} elements - An array of selectors for the elements to split.
 * @param {object} defaultOptions - Default options for Split.js.
 */
function initializeSplitter(elements, defaultOptions) {
  if (typeof Split === 'undefined') {
    console.error('Split.js is not loaded. Make sure it is included in your HTML.');
    return;
  }

  const storageKey = 'pipulate-split-sizes';
  let initialSizes;

  try {
    const savedSizes = localStorage.getItem(storageKey);
    initialSizes = savedSizes ? JSON.parse(savedSizes) : defaultOptions.sizes;
  } catch (e) {
    console.error('Error parsing saved split sizes, using default.', e);
    initialSizes = defaultOptions.sizes;
  }

  // Combine default options with persisted user settings
  const options = {
    ...defaultOptions,
    sizes: initialSizes,
    onDragEnd: function(sizes) {
      localStorage.setItem(storageKey, JSON.stringify(sizes));
      // Execute original onDragEnd if it was provided
      if (typeof defaultOptions.onDragEnd === 'function') {
        defaultOptions.onDragEnd(sizes);
      }
    }
  };

  console.log('Initializing splitter for:', elements, 'with options:', options);
  Split(elements, options);
} 