/**
 * PIPULATE COPY FUNCTIONALITY
 * 
 * Handles copy-to-clipboard functionality across Pipulate for:
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
                button.disabled = true;
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '#0066cc';
                    button.disabled = false;
                }, 3000);
            })
            .catch((err) => {
                console.error('Failed to copy text:', err);
                
                // Error feedback
                button.textContent = '❌ Error';
                button.style.background = '#dc3545';
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '#0066cc';
                }, 3000);
            });
    }

    function initializeInlineCodeCopy() {
        // Add click-to-copy for inline code elements that look like commands
        document.querySelectorAll('code:not([class*="language-"]):not(.copy-handled)').forEach(function(code) {
            const text = code.textContent;
            
            // Only add to code elements that look like commands
            if (isCommandLike(text)) {
                code.style.cursor = 'pointer';
                code.title = 'Click to copy';
                code.classList.add('copy-handled'); // Prevent duplicate handling
                
                code.addEventListener('click', function() {
                    copyToClipboard(text)
                        .then(() => {
                            // Success feedback
                            const originalBg = code.style.backgroundColor;
                            const originalColor = code.style.color;
                            
                            code.style.backgroundColor = '#28a745';
                            code.style.color = 'white';
                            
                            setTimeout(() => {
                                code.style.backgroundColor = originalBg;
                                code.style.color = originalColor;
                            }, 1000);
                        })
                        .catch((err) => {
                            console.error('Failed to copy inline code:', err);
                            
                            // Error feedback
                            const originalBg = code.style.backgroundColor;
                            const originalColor = code.style.color;
                            
                            code.style.backgroundColor = '#dc3545';
                            code.style.color = 'white';
                            
                            setTimeout(() => {
                                code.style.backgroundColor = originalBg;
                                code.style.color = originalColor;
                            }, 1000);
                        });
                });
            }
        });
    }

    function isCommandLike(text) {
        // Determine if text looks like a command worth copying
        return text.includes(' ') || 
               text.includes('python') || 
               text.includes('--') || 
               text.includes('npm') ||
               text.includes('git') ||
               text.includes('curl') ||
               text.includes('cd ') ||
               text.includes('mkdir') ||
               text.includes('pip ') ||
               text.length > 20; // Long text might be worth copying
    }

    function copyToClipboard(text) {
        // Modern clipboard API with fallback
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers or non-secure contexts
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
            
            try {
                textArea.focus();
                textArea.select();
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);
                
                if (successful) {
                    resolve();
                } else {
                    reject(new Error('Copy command failed'));
                }
            } catch (err) {
                document.body.removeChild(textArea);
                reject(err);
            }
        });
    }

    // Public API
    return {
        initialize: initialize,
        initializeDataCopyButtons: initializeDataCopyButtons,
        initializeInlineCodeCopy: initializeInlineCodeCopy,
        copyToClipboard: copyToClipboard
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', PipulateCopy.initialize);
} else {
    PipulateCopy.initialize();
}

// Re-initialize when HTMX swaps content
document.addEventListener('htmx:afterSwap', function(event) {
    // Re-initialize copy functionality for new content
    setTimeout(() => {
        PipulateCopy.initializeDataCopyButtons();
        PipulateCopy.initializeInlineCodeCopy();
    }, 100);
});

// Make globally available for manual initialization if needed
window.PipulateCopy = PipulateCopy; 