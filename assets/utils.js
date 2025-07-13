/**
 * PIPULATE UTILITIES
 * 
 * Consolidated client-side utilities for Pipulate including:
 * - Widget functionality (JavaScript execution, Markdown/Mermaid rendering)
 * - Copy-to-clipboard functionality
 * - General utility functions
 */

console.log('🔧 Pipulate utilities loading');

// =============================================================================
// WIDGET FUNCTIONALITY
// =============================================================================

/**
 * Widget Scripts - JavaScript functions used by the Widget Examples workflow.
 * Provides functionality for executing JavaScript code and rendering Markdown.
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
 * @param {string} targetId - ID of the target element to display results
 */
function runJsWidget(widgetId, code, targetId) {
  console.log('Running JavaScript widget:', widgetId, targetId);
  
  // Clear the target element's content
  const targetElement = document.getElementById(targetId);
  if (targetElement) {
    targetElement.innerHTML = '';
  }
  
  try {
    // Create a scoped execution context for the widget
    const widget = {
      element: targetElement,
      id: targetId,
      log: function(message) {
        console.log(`[Widget ${widgetId}]:`, message);
        if (targetElement) {
          const logElement = document.createElement('div');
          logElement.className = 'widget-log';
          logElement.textContent = message;
          targetElement.appendChild(logElement);
        }
      },
      clear: function() {
        if (targetElement) {
          targetElement.innerHTML = '';
        }
      },
      append: function(content) {
        if (targetElement) {
          if (typeof content === 'string') {
            const div = document.createElement('div');
            div.innerHTML = content;
            targetElement.appendChild(div);
          } else if (content instanceof HTMLElement) {
            targetElement.appendChild(content);
          }
        }
      }
    };
    
    // Execute the code in the widget context
    const executeCode = new Function('widget', code);
    executeCode(widget);
    
  } catch (error) {
    console.error('Error executing JavaScript widget:', error);
    if (targetElement) {
      targetElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
  }
}

/**
 * Render Markdown content in a target element
 * 
 * @param {string} targetId - ID of the target element
 * @param {string} markdown - Markdown content to render
 */
function renderMarkdown(targetId, markdown) {
  console.log('Rendering Markdown in:', targetId);
  
  const targetElement = document.getElementById(targetId);
  if (!targetElement) {
    console.error('Target element not found:', targetId);
    return;
  }
  
  try {
    // Check if marked.js is available
    if (typeof marked === 'undefined') {
      console.error('marked.js is not loaded');
      targetElement.innerHTML = '<div class="error">marked.js is not loaded</div>';
      return;
    }
    
    // Render the markdown
    const renderedHtml = marked.parse(markdown);
    targetElement.innerHTML = renderedHtml;
    
    // Initialize Prism.js for code blocks if available
    if (typeof Prism !== 'undefined') {
      Prism.highlightAllUnder(targetElement);
    }
    
  } catch (error) {
    console.error('Error rendering Markdown:', error);
    targetElement.innerHTML = `<div class="error">Error rendering Markdown: ${error.message}</div>`;
  }
}

/**
 * Render Mermaid diagram in a target element
 * 
 * @param {string} targetId - ID of the target element
 * @param {string} diagram - Mermaid diagram content
 */
function renderMermaid(targetId, diagram) {
  console.log('Rendering Mermaid diagram in:', targetId);
  
  const targetElement = document.getElementById(targetId);
  if (!targetElement) {
    console.error('Target element not found:', targetId);
    return;
  }
  
  try {
    // Check if mermaid is available
    if (typeof mermaid === 'undefined') {
      console.error('mermaid.js is not loaded');
      targetElement.innerHTML = '<div class="error">mermaid.js is not loaded</div>';
      return;
    }
    
    // Clear the target element
    targetElement.innerHTML = '';
    
    // Create a unique ID for the diagram
    const diagramId = 'mermaid-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    // Create a div for the diagram
    const diagramDiv = document.createElement('div');
    diagramDiv.id = diagramId;
    diagramDiv.className = 'mermaid';
    targetElement.appendChild(diagramDiv);
    
    // Configure mermaid with dark theme
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      themeVariables: {
        primaryColor: '#ff6b6b',
        primaryTextColor: '#ffffff',
        primaryBorderColor: '#ff6b6b',
        lineColor: '#ffffff',
        secondaryColor: '#4ecdc4',
        tertiaryColor: '#ffe66d',
        background: '#2c3e50',
        mainBkg: '#34495e',
        secondBkg: '#2c3e50',
        tertiaryBkg: '#34495e'
      }
    });
    
    // Render the diagram
    mermaid.render(diagramId, diagram).then(({svg}) => {
      diagramDiv.innerHTML = svg;
    }).catch(error => {
      console.error('Error rendering Mermaid diagram:', error);
      diagramDiv.innerHTML = `<div class="error">Error rendering Mermaid diagram: ${error.message}</div>`;
    });
    
  } catch (error) {
    console.error('Error rendering Mermaid diagram:', error);
    targetElement.innerHTML = `<div class="error">Error rendering Mermaid diagram: ${error.message}</div>`;
  }
}

/**
 * Debounce function to limit rapid function calls
 * 
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
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
 * Scroll to bottom of the page
 */
function scrollToBottom() {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  });
}

// =============================================================================
// COPY FUNCTIONALITY
// =============================================================================

/**
 * Copy-to-clipboard functionality across Pipulate for:
 * - AI prompts (data-copy-text attribute)
 * - Inline code elements (click-to-copy)
 * - Custom copy buttons
 * 
 * Note: Code blocks use PrismJS built-in copy-to-clipboard plugin
 */

window.PipulateCopy = (function() {
    'use strict';

    // Initialize copy functionality when DOM is ready
    function initialize() {
        console.log('🔄 Initializing Pipulate copy functionality');
        
        // Handle copy buttons with data-copy-text attribute (for AI prompts)
        initializeDataCopyButtons();
        
        // Handle click-to-copy for inline code elements
        initializeInlineCodeCopy();
        
        console.log('✅ Pipulate copy functionality initialized');
    }

    function initializeDataCopyButtons() {
        document.querySelectorAll('button[data-copy-text]').forEach(function(button) {
            // Remove any existing listeners to prevent duplicates
            button.removeEventListener('click', handleDataCopyClick);
            button.addEventListener('click', handleDataCopyClick);
        });
    }

    function handleDataCopyClick(event) {
        const button = event.target;
        const textToCopy = button.getAttribute('data-copy-text');
        const originalText = button.textContent;
        
        if (!textToCopy) {
            console.warn('No data-copy-text attribute found on button');
            return;
        }
        
        copyToClipboard(textToCopy)
            .then(() => {
                // Success feedback
                button.textContent = '✅ Copied!';
                button.style.background = '#28a745';
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                }, 2000);
            })
            .catch(error => {
                console.error('Copy failed:', error);
                
                // Error feedback
                button.textContent = '❌ Copy failed';
                button.style.background = '#dc3545';
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                }, 2000);
            });
    }

    function initializeInlineCodeCopy() {
        document.querySelectorAll('code:not(.language-*):not([class*="language-"])').forEach(function(codeElement) {
            const text = codeElement.textContent.trim();
            
            // Only add click-to-copy for command-like text
            if (isCommandLike(text)) {
                codeElement.style.cursor = 'pointer';
                codeElement.title = 'Click to copy';
                codeElement.classList.add('clickable-code');
                
                // Remove any existing listeners to prevent duplicates
                codeElement.removeEventListener('click', handleInlineCodeClick);
                codeElement.addEventListener('click', handleInlineCodeClick);
            }
        });
    }

    function handleInlineCodeClick(event) {
        const codeElement = event.target;
        const textToCopy = codeElement.textContent.trim();
        
        copyToClipboard(textToCopy)
            .then(() => {
                // Success feedback
                const originalBg = codeElement.style.backgroundColor;
                codeElement.style.backgroundColor = '#28a745';
                codeElement.style.color = 'white';
                
                // Reset after 1 second
                setTimeout(() => {
                    codeElement.style.backgroundColor = originalBg;
                    codeElement.style.color = '';
                }, 1000);
            })
            .catch(error => {
                console.error('Copy failed:', error);
                
                // Error feedback
                const originalBg = codeElement.style.backgroundColor;
                codeElement.style.backgroundColor = '#dc3545';
                codeElement.style.color = 'white';
                
                // Reset after 1 second
                setTimeout(() => {
                    codeElement.style.backgroundColor = originalBg;
                    codeElement.style.color = '';
                }, 1000);
            });
    }

    function isCommandLike(text) {
        // Check for common command patterns
        const commandPatterns = [
            /^[a-z]+\s+/,  // starts with command word
            /^[A-Z_]+=/,   // environment variable
            /^[a-z]+\.[a-z]+/,  // file.extension
            /^\/[a-z\/]+/,  // file path
            /^[a-z-]+\s+--/,  // command with flags
            /^pip\s+install/,  // pip install
            /^npm\s+install/,  // npm install
            /^git\s+/,  // git command
            /^sudo\s+/,  // sudo command
            /^cd\s+/,  // cd command
            /^ls\s+/,  // ls command
            /^curl\s+/,  // curl command
        ];
        
        return commandPatterns.some(pattern => pattern.test(text));
    }

    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            return fallbackCopyToClipboard(text);
        }
    }

    function fallbackCopyToClipboard(text) {
        return new Promise((resolve, reject) => {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);
                
                if (successful) {
                    resolve();
                } else {
                    reject(new Error('Copy command failed'));
                }
            } catch (error) {
                document.body.removeChild(textArea);
                reject(error);
            }
        });
    }

    // Re-initialize copy functionality when new content is added
    function refresh() {
        console.log('🔄 Refreshing copy functionality');
        initialize();
    }

    // Public API
    return {
        initialize: initialize,
        refresh: refresh,
        copyToClipboard: copyToClipboard
    };
})();

// Initialize copy functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    PipulateCopy.initialize();
});

// Re-initialize copy functionality after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function() {
    PipulateCopy.refresh();
});

console.log('✅ Pipulate utilities loaded successfully'); 