/**
 * Pipulate Widget Scripts
 * 
 * This file contains JavaScript functions used by the Widget Examples workflow.
 * It provides functionality for executing JavaScript code and rendering Markdown.
 */

// Function to run JavaScript from an HTMX-triggered event
document.addEventListener('DOMContentLoaded', function() {
  // Set up HTMX event listener for running JavaScript
  htmx.on('runJavaScript', function(evt) {
    const data = evt.detail;
    runJsWidget(data.widgetId, data.code, data.targetId);
  });

  // Set up HTMX event listener for rendering Markdown
  htmx.on('renderMarkdown', function(evt) {
    const data = evt.detail;
    renderMarkdown(data.targetId, data.markdown);
  });
  
  // Set up HTMX event listener for rendering Mermaid diagrams
  htmx.on('renderMermaid', function(evt) {
    const data = evt.detail;
    renderMermaid(data.targetId, data.diagram);
  });

  // Initialize Prism.js for dynamically added content
  document.body.addEventListener('initializePrism', function(evt) {
    console.log('Prism initialization triggered');
    const targetId = evt.detail?.targetId;
    const targetElement = targetId ? document.getElementById(targetId) : document;
    
    if (targetElement && typeof Prism !== 'undefined') {
      // Use setTimeout to ensure DOM is fully updated
      setTimeout(() => {
        console.log('Highlighting code in:', targetId || 'document');
        Prism.highlightAllUnder(targetElement);
      }, 100);
    } else {
      console.error('Prism library not loaded or target element not found');
    }
  });
});

/**
 * Execute JavaScript code for a widget
 * 
 * @param {string} widgetId - ID of the widget container
 * @param {string} code - JavaScript code to execute
 * @param {string} targetId - ID of the DOM element to pass to the code
 */
function runJsWidget(widgetId, code, targetId) {
  console.log(`Running JS widget: ${widgetId}, target: ${targetId}`);
  
  // Get the target element where the JS will execute
  const targetElement = document.getElementById(targetId);
  if (!targetElement) {
    console.error(`Target element with ID '${targetId}' not found`);
    return;
  }
  
  // Clear the target element's content before execution
  targetElement.innerHTML = '';
  
  try {
    // Execute the code with the target element as the 'widget' variable
    // Using an IIFE to create a proper scope
    (function(widget) {
      try {
        // Use eval inside the function scope so 'widget' is properly bound
        eval(code);
        
        // After execution, find any buttons created and apply the purple styling
        // This ensures consistent button styling even if not in the user's code
        setTimeout(() => {
          const buttons = widget.querySelectorAll('button');
          buttons.forEach(button => {
            // Skip buttons that already have explicit styling
            if (!button.style.backgroundColor && !button.style.borderColor) {
              button.style.backgroundColor = '#9370DB'; // Light purple
              button.style.borderColor = '#9370DB';     // Light purple
            }
          });
        }, 0);
        
      } catch (innerError) {
        // Handle errors during execution
        console.error('Error in JS execution:', innerError);
        widget.innerHTML = `
          <div style="color: red; padding: 1rem;">
            <h4>JavaScript Error:</h4>
            <pre>${innerError.toString()}</pre>
          </div>
        `;
      }
    })(targetElement);
    
    console.log(`JS executed successfully for target ${targetId}`);
  } catch (error) {
    // Handle any outer errors
    console.error('Error executing JavaScript widget:', error);
    targetElement.innerHTML = `
      <div style="color: red; padding: 1rem;">
        <h4>JavaScript Error:</h4>
        <pre>${error.toString()}</pre>
      </div>
    `;
  }
}

/**
 * Render Markdown content using marked.js
 * 
 * @param {string} targetId - ID of the DOM element to render Markdown into
 * @param {string} markdown - Markdown content to render
 */
function renderMarkdown(targetId, markdown) {
  const targetElement = document.getElementById(targetId);
  if (!targetElement) {
    console.error(`Target element with ID '${targetId}' not found`);
    return;
  }

  try {
    // Check if marked is available
    if (typeof marked === 'undefined') {
      // Fallback if marked.js is not loaded
      targetElement.innerHTML = `
        <div style="color: red; padding: 1rem;">
          <h4>Error:</h4>
          <p>marked.js is not loaded. Please add it to the page's headers.</p>
        </div>
      `;
      return;
    }

    // Render the markdown
    targetElement.innerHTML = marked.parse(markdown);

    // Apply syntax highlighting if Prism is available
    if (typeof Prism !== 'undefined') {
      targetElement.querySelectorAll('pre code').forEach((block) => {
        Prism.highlightElement(block);
      });
    }
  } catch (error) {
    console.error('Error rendering Markdown:', error);
    targetElement.innerHTML = `
      <div style="color: red; padding: 1rem;">
        <h4>Markdown Error:</h4>
        <pre>${error.toString()}</pre>
      </div>
    `;
  }
}

/**
 * Render Mermaid diagram
 *
 * @param {string} targetId - ID of the DOM element containing the diagram
 * @param {string} diagram - Mermaid diagram syntax
 */
function renderMermaid(targetId, diagram) {
  console.log('Rendering Mermaid diagram in:', targetId);
  
  const targetElement = document.getElementById(targetId);
  if (!targetElement) {
    console.error(`Target element with ID '${targetId}' not found`);
    return;
  }

  try {
    // Check if mermaid is available
    if (typeof mermaid === 'undefined') {
      console.error('Mermaid library not loaded');
      targetElement.innerHTML = `
        <div style="color: red; padding: 1rem;">
          <h4>Error:</h4>
          <p>mermaid.min.js is not loaded. Please check the page headers.</p>
        </div>
      `;
      return;
    }

    // Find or create a div with the mermaid class
    let mermaidDiv = targetElement.querySelector('.mermaid');
    if (!mermaidDiv) {
      mermaidDiv = document.createElement('div');
      mermaidDiv.className = 'mermaid';
      targetElement.appendChild(mermaidDiv);
    }
    
    // Set the diagram content
    mermaidDiv.textContent = diagram;
    
    // Initialize Mermaid with configuration
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',        // Use dark theme for better visibility
      securityLevel: 'loose',
      flowchart: {
        htmlLabels: true
      }
    });
    
    // Run Mermaid rendering on the specific element
    try {
      // Different versions of Mermaid have different APIs
      if (typeof mermaid.run === 'function') {
        // Newer versions
        mermaid.run({ nodes: [mermaidDiv] });
      } else {
        // Older versions
        mermaid.init(undefined, mermaidDiv);
      }
    } catch (renderError) {
      console.error('Error during Mermaid rendering:', renderError);
      mermaidDiv.innerHTML = `
        <div style="color: red; padding: 1rem;">
          <h4>Mermaid Rendering Error:</h4>
          <pre>${renderError.toString()}</pre>
        </div>
      `;
    }
  } catch (error) {
    console.error('General error in Mermaid rendering:', error);
    targetElement.innerHTML = `
      <div style="color: red; padding: 1rem;">
        <h4>Mermaid Error:</h4>
        <pre>${error.toString()}</pre>
      </div>
    `;
  }
}

/**
 * Debounce utility - limits the rate at which a function can fire
 * 
 * @param {Function} func - The function to debounce
 * @param {number} wait - The time to wait in milliseconds
 * @returns {Function} - The debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Scroll to the bottom of the page smoothly
 */
function scrollToBottom() {
  console.log("Scrolling to bottom...");
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  });
}

// Create debounced version of the scroll function
const debouncedScrollToBottom = debounce(scrollToBottom, 300);

// Listen for HTMX settle events
document.addEventListener('DOMContentLoaded', function() {
  console.log("Setting up HTMX afterSettle listener for smooth scrolling");
  
  // Listen for the htmx:afterSettle event
  document.body.addEventListener('htmx:afterSettle', function(evt) {
    console.log('htmx:afterSettle triggered. Requesting debounced scroll.');
    debouncedScrollToBottom();
  });
}); 