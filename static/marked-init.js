/**
 * MARKED.JS CONFIGURATION
 * 
 * Configures marked.js for consistent Markdown rendering across the application.
 * Sets up GitHub Flavored Markdown (GFM) with line breaks and other options.
 * 
 * Usage: Include this script before any code that uses marked.parse()
 */

// Global marked configuration function
window.initializeMarked = function() {
    console.log('🔤 Initializing Marked.js configuration');
    
    if (typeof marked === 'undefined') {
        console.error('❌ marked.js is not available');
        return;
    }
    
    // Configure marked with GFM and sensible defaults for chat
    marked.use({
        // Enable GitHub Flavored Markdown line breaks
        // Single newlines become <br> tags instead of being collapsed
        breaks: true,
        
        // Enable GitHub Flavored Markdown features
        gfm: true,
        
        // Additional options for better chat experience
        headerIds: false,  // Don't generate header IDs (not needed in chat)
        mangle: false,     // Don't mangle email addresses
        
        // Custom renderer overrides for chat-specific behavior
        renderer: {
            // Ensure code blocks have proper classes for Prism.js
            code(code, language) {
                const lang = language || 'text';
                return `<pre><code class="language-${lang}">${code}</code></pre>`;
            },
            
            // Make links open in new tabs for external URLs
            link(href, title, text) {
                const titleAttr = title ? ` title="${title}"` : '';
                const external = href.startsWith('http') ? ' target="_blank" rel="noopener noreferrer"' : '';
                return `<a href="${href}"${titleAttr}${external}>${text}</a>`;
            }
        }
    });
    
    console.log('✅ Marked.js configured with GFM and breaks enabled');
};

// Auto-initialize if marked is already available
if (typeof marked !== 'undefined') {
    window.initializeMarked();
} else {
    // Wait for marked to be loaded
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof marked !== 'undefined') {
            window.initializeMarked();
        } else {
            console.warn('⚠️ marked.js still not available after DOM loaded');
        }
    });
} 