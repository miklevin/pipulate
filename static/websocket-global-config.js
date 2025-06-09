/**
 * GLOBAL CONFIG PATTERN: Reads window.PIPULATE_CONFIG set by Python
 * 
 * This file automatically reads configuration from global variables.
 * No initialization call needed - Python sets config before loading.
 * 
 * Pattern: Static JS file that reads Python-generated global configuration
 */

// Define test alert function globally
window.testAlert = function(message) {
    alert('Test Alert: ' + message);
    console.log('Alert triggered with:', message);
};

// Get configuration from the global variable
const config = window.PIPULATE_CONFIG || {};
const tempMessage = config.tempMessage;

// Match the WebSocket route from Chat
const sidebarWs = new WebSocket('ws://' + window.location.host + '/ws');
const sidebarMsgList = document.getElementById('msg-list');
let sidebarCurrentMessage = document.createElement('div');
sidebarCurrentMessage.className = 'message assistant';

sidebarWs.onopen = function() {
    console.log('Sidebar WebSocket connected');
};

sidebarWs.onclose = function() {
    console.log('Sidebar WebSocket closed');
};

sidebarWs.onerror = function(error) {
    console.error('Sidebar WebSocket error:', error);
};

// Add this function at the top of the file
function linkifyText(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return '<a href="' + url + '" target="_blank">' + url + '</a>';
    });
}

sidebarWs.onmessage = function(event) {
    console.log('Sidebar received:', event.data);
    
    // Check if the message is a script
    if (event.data.trim().startsWith('<script>')) {
        const scriptContent = event.data.replace(/<\/?script>/g, '').trim();
        console.log('Executing script:', scriptContent);
        try {
            eval(scriptContent);
        } catch (e) {
            console.error('Error executing script:', e);
        }
        return;
    }
    
    // Check if the response contains a plugin list item
    if (event.data.includes('data-plugin-item="true"')) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = event.data.trim();
        const newItem = tempDiv.firstElementChild;
        
        if (newItem && newItem.hasAttribute('data-list-target')) {
            const listId = newItem.getAttribute('data-list-target');
            const targetList = document.getElementById(listId);
            
            if (targetList) {
                targetList.appendChild(newItem);
                htmx.process(newItem);
                
                // Initialize sortable if needed
                if (window.Sortable && !targetList.classList.contains('sortable-initialized')) {
                    new Sortable(targetList, {
                        animation: 150,
                        ghostClass: 'blue-background-class'
                    });
                    targetList.classList.add('sortable-initialized');
                }
            }
        }
        return;
    }
    
    // Handle regular chat messages
    if (!sidebarCurrentMessage.parentElement) {
        sidebarMsgList.appendChild(sidebarCurrentMessage);
    }
    
    // Initialize or update the raw text buffer
    if (!sidebarCurrentMessage.dataset.rawText) {
        sidebarCurrentMessage.dataset.rawText = '';
    }
    sidebarCurrentMessage.dataset.rawText += event.data;
    
    // Debug logging for marked.js
    console.log('marked.js available:', typeof marked !== 'undefined');
    if (typeof marked !== 'undefined') {
        console.log('marked.parse available:', typeof marked.parse === 'function');
        console.log('Current raw text:', sidebarCurrentMessage.dataset.rawText);
    }
    
    // Render the accumulated Markdown
    if (typeof marked !== 'undefined') {
        try {
            // Use marked.parse() to render the accumulated markdown
            const renderedHtml = marked.parse(sidebarCurrentMessage.dataset.rawText);
            console.log('Rendered HTML:', renderedHtml);
            sidebarCurrentMessage.innerHTML = renderedHtml;
            
            // Apply syntax highlighting if Prism is available
            if (typeof Prism !== 'undefined') {
                Prism.highlightAllUnder(sidebarCurrentMessage);
            }
        } catch (e) {
            console.error('Error rendering Markdown:', e);
            // Fallback to plain text if Markdown rendering fails
            sidebarCurrentMessage.textContent = sidebarCurrentMessage.dataset.rawText;
        }
    } else {
        // Fallback to plain text if marked.js is not available
        console.error('marked.js is not available');
        sidebarCurrentMessage.textContent = sidebarCurrentMessage.dataset.rawText;
    }
    
    // Keep the latest message in view
    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
};

// Handle temp_message if it exists
window.addEventListener('DOMContentLoaded', () => {
    if (tempMessage) {
        console.log('Sidebar sending verbatim:', tempMessage);
        const messageWithNewline = tempMessage + '';  // put \n if needed
        setTimeout(() => sidebarWs.send(`${messageWithNewline}|verbatim`), 1000);
    }
});

window.sendSidebarMessage = function(event) {
    event.preventDefault();
    const input = document.getElementById('msg');
    if (input.value) {
        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        userMsg.textContent = input.value;
        sidebarMsgList.appendChild(userMsg);
        
        sidebarCurrentMessage = document.createElement('div');
        sidebarCurrentMessage.className = 'message assistant';
        
        console.log('Sidebar sending:', input.value);
        if (sidebarWs.readyState === WebSocket.OPEN) {
            sidebarWs.send(input.value);
            input.value = '';
            sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
        } else {
            console.error('WebSocket not connected');
        }
    }
}

// Add CSS to reduce vertical spacing in messages
const style = document.createElement('style');
style.textContent = `
    .message {
        margin: 0.5em 0;
    }
    .message p {
        margin: 0 !important;
        padding: 0 !important;
    }
    .message ul, .message ol {
        margin: 0.2em 0 !important;
        padding-left: 1.5em !important;
    }
    .message li {
        margin: 0 !important;
        padding: 0 !important;
    }
    .message li + li {
        margin-top: 0.1em !important;
    }
    .message h1, .message h2, .message h3, .message h4, .message h5, .message h6 {
        margin: 0.5em 0 0.2em 0 !important;
    }
    .message pre {
        margin: 0.2em 0 !important;
    }
    .message blockquote {
        margin: 0.2em 0 !important;
        padding-left: 1em !important;
        border-left: 3px solid var(--pico-muted-border-color);
    }
    .message strong {
        font-weight: bold;
    }
    .message em {
        font-style: italic;
    }
    .message code {
        background: var(--pico-muted-background);
        padding: 0.1em 0.3em;
        border-radius: 3px;
    }
`;
document.head.appendChild(style); 