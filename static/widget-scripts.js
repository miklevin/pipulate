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
});

/**
 * Execute JavaScript code for a widget
 * 
 * @param {string} widgetId - ID of the widget container
 * @param {string} code - JavaScript code to execute
 * @param {string} targetId - ID of the DOM element to pass to the code
 */
function runJsWidget(widgetId, code, targetId) {
  try {
    // Create a function from the code string and execute it
    const functionBody = `
      "use strict";
      // Provide the targetId to the code
      const widget = document.getElementById('${widgetId}');
      ${code}
    `;
    const executeCode = new Function(functionBody);
    executeCode();
  } catch (error) {
    // Handle errors in the execution
    console.error('Error executing JavaScript widget:', error);
    const targetElement = document.getElementById(targetId);
    if (targetElement) {
      targetElement.innerHTML = `
        <div style="color: red; padding: 1rem;">
          <h4>JavaScript Error:</h4>
          <pre>${error.toString()}</pre>
        </div>
      `;
    }
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