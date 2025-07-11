/**
 * GLOBAL CONFIG PATTERN: Reads window.PCONFIG set by Python
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
const config = window.PCONFIG || {};
const tempMessage = config.tempMessage;

// Flag to prevent duplicate temp message sending
let tempMessageSent = false;

// Match the WebSocket route from Chat
const sidebarWs = new WebSocket('ws://' + window.location.host + '/ws');
const sidebarMsgList = document.getElementById('msg-list');
let sidebarCurrentMessage = document.createElement('div');
sidebarCurrentMessage.className = 'message assistant';

// PERFORMANCE OPTIMIZATION: Throttle Markdown rendering to prevent exponential slowdown
let renderThrottleTimer = null;
const RENDER_THROTTLE_DELAY = config.CHAT_CONFIG?.RENDER_THROTTLE_DELAY || 15; // Configurable delay between renders (milliseconds)

sidebarWs.onopen = function() {
    console.log('Sidebar WebSocket connected');
    // If there's a temp message waiting and we just connected, send it immediately
    if (tempMessage && document.readyState === 'complete' && !tempMessageSent) {
        console.log('WebSocket opened, sending queued temp message:', tempMessage);
        const messageWithNewline = tempMessage + '';
        sidebarWs.send(`${messageWithNewline}|verbatim`);
        tempMessageSent = true;
    }
};

sidebarWs.onclose = function() {
    console.log('Sidebar WebSocket closed');
};

sidebarWs.onerror = function(error) {
    console.error('Sidebar WebSocket error:', error);
};

// Removed linkifyText function - no automatic URL linking

// Timer-based UI prediction removed - server now controls streaming state completely
sidebarWs.onmessage = function(event) {
    // Handle UI control messages first
    if (event.data === '%%STREAM_START%%') {
        updateStreamingUI(true);
        return; // Do not display this message
    }
    if (event.data === '%%STREAM_END%%') {
        updateStreamingUI(false);
        
        // PERFORMANCE OPTIMIZATION: Ensure final render happens and clear any pending renders
        if (renderThrottleTimer) {
            clearTimeout(renderThrottleTimer);
            renderThrottleTimer = null;
        }
        // Force final render of the complete message
        renderCurrentMessage();
        
        // Add clipboard functionality to the completed assistant message
        if (sidebarCurrentMessage && sidebarCurrentMessage.dataset.rawText) {
            addClipboardToAssistantMessage(sidebarCurrentMessage);
        }
        // Reset message buffer for next stream
        sidebarCurrentMessage = document.createElement('div');
        sidebarCurrentMessage.className = 'message assistant';
        return; // Do not display this message
    }

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
    
    // PERFORMANCE OPTIMIZATION: Throttle Markdown rendering to prevent exponential slowdown
    // Clear existing timer if one exists
    if (renderThrottleTimer) {
        clearTimeout(renderThrottleTimer);
    }
    
    // Schedule a throttled render
    renderThrottleTimer = setTimeout(() => {
        renderCurrentMessage();
        renderThrottleTimer = null;
    }, RENDER_THROTTLE_DELAY);
    
    // Keep the latest message in view
    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
};

// PERFORMANCE OPTIMIZATION: Dedicated function for rendering current message
function renderCurrentMessage() {
    // Render the accumulated Markdown with improved code fence detection
    if (typeof marked !== 'undefined') {
        try {
            const rawText = sidebarCurrentMessage.dataset.rawText;
            
            // Enhanced code fence detection - handle both ``` and ~~~ fences
            const codeFenceRegex = /^(```|~~~)/gm;
            const allFences = rawText.match(codeFenceRegex) || [];
            const hasIncompleteCodeFence = allFences.length % 2 !== 0;
            
            if (hasIncompleteCodeFence) {
                // Don't parse incomplete markdown - show as plain text for now
                // But preserve basic formatting for readability
                const lines = rawText.split('\n');
                const formattedLines = lines.map(line => {
                    // Basic HTML escaping for safety, but preserve <br> tags
                    return line.replace(/&/g, '&amp;')
                              .replace(/</g, '&lt;')
                              .replace(/>/g, '&gt;')
                              .replace(/&lt;br&gt;/g, '<br>'); // Convert escaped <br> back to actual breaks
                });
                sidebarCurrentMessage.innerHTML = formattedLines.join('<br>');
            } else {
                // Safe to parse complete markdown using pre-configured marked
                // PREPROCESSING: Clean up markdown to prevent extra spacing
                let cleanedText = rawText;
                
                // Remove extra whitespace between list items while preserving structure
                cleanedText = cleanedText
                    // Remove empty lines between list items in the same list
                    .replace(/(\n\s*[-*+]\s+[^\n]+)\n\s*\n(\s*[-*+]\s+)/g, '$1\n$2')
                    // Remove extra whitespace around nested lists
                    .replace(/(\n\s*[-*+]\s+[^\n]+)\n\s*\n(\s+[-*+]\s+)/g, '$1\n$2')
                    // Clean up multiple consecutive newlines (but preserve intentional paragraph breaks)
                    .replace(/\n\s*\n\s*\n/g, '\n\n')
                    // Remove trailing whitespace from lines
                    .replace(/[ \t]+$/gm, '')
                    // Normalize line endings
                    .replace(/\r\n/g, '\n');
                
                const renderedHtml = marked.parse(cleanedText);
                
                // POST-PROCESSING: Clean up HTML whitespace between elements
                let cleanedHtml = renderedHtml
                    // Remove whitespace between closing and opening list item tags
                    .replace(/(<\/li>)\s+(<li>)/g, '$1$2')
                    // Remove whitespace between closing list item and opening nested list
                    .replace(/(<\/li>)\s+(<ul>|<ol>)/g, '$1$2')
                    // Remove whitespace between closing nested list and opening list item
                    .replace(/(<\/ul>|<\/ol>)\s+(<li>)/g, '$1$2')
                    // Remove whitespace between opening list and first list item
                    .replace(/(<ul>|<ol>)\s+(<li>)/g, '$1$2')
                    // Remove whitespace between last list item and closing list
                    .replace(/(<\/li>)\s+(<\/ul>|<\/ol>)/g, '$1$2')
                    // Remove extra whitespace between paragraphs and lists
                    .replace(/(<\/p>)\s+(<ul>|<ol>)/g, '$1$2')
                    .replace(/(<\/ul>|<\/ol>)\s+(<p>)/g, '$1$2');
                
                sidebarCurrentMessage.innerHTML = cleanedHtml;
                
                // Apply syntax highlighting if Prism is available
                if (typeof Prism !== 'undefined') {
                    Prism.highlightAllUnder(sidebarCurrentMessage);
                }
            }
        } catch (e) {
            console.error('Error rendering Markdown:', e);
            // Fallback to safely formatted plain text
            const processedText = sidebarCurrentMessage.dataset.rawText
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/&lt;br&gt;/g, '<br>') // Convert escaped <br> back to actual breaks
                .replace(/\n/g, '<br>');
            sidebarCurrentMessage.innerHTML = processedText;
        }
    } else {
        // Fallback to plain text if marked.js is not available
        console.warn('marked.js is not available - using plain text');
        const processedText = sidebarCurrentMessage.dataset.rawText
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/&lt;br&gt;/g, '<br>') // Convert escaped <br> back to actual breaks
            .replace(/\n/g, '<br>');
        sidebarCurrentMessage.innerHTML = processedText;
    }
}

// --- Streaming state and UI control ---
let isStreaming = false;

function updateStreamingUI(streaming) {
    isStreaming = streaming;
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');
    const input = document.getElementById('msg');
    
    if (!sendBtn || !stopBtn || !input) return;
    
    if (isStreaming) {
        sendBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        input.disabled = true;
        input.placeholder = 'Streaming response...';
    } else {
        sendBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        input.disabled = false;
        input.placeholder = 'Chat...';
        input.focus();
    }
}

// Initialize chat interface icons and state
function initializeChatInterface() {
    updateStreamingUI(false);
}

// Copy message to clipboard with visual feedback
function copyMessageToClipboard(text, button) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showClipboardSuccess(button);
        }).catch(err => {
            console.error('Failed to copy message:', err);
            showClipboardError(button);
        });
    } else {
        // Fallback for older browsers
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
                showClipboardSuccess(button);
            } else {
                showClipboardError(button);
            }
        } catch (err) {
            document.body.removeChild(textArea);
            console.error('Fallback copy failed:', err);
            showClipboardError(button);
        }
    }
}

// Show success feedback for clipboard copy
function showClipboardSuccess(button) {
    const originalHTML = button.innerHTML;
    button.innerHTML = '✅';
    button.style.opacity = '1';
    button.style.backgroundColor = 'var(--pico-color-green-500)';
    
    setTimeout(() => {
        button.innerHTML = originalHTML;
        button.style.opacity = '0.6';
        button.style.backgroundColor = 'transparent';
    }, 2000);
}

// Show error feedback for clipboard copy
function showClipboardError(button) {
    const originalHTML = button.innerHTML;
    button.innerHTML = '❌';
    button.style.opacity = '1';
    button.style.backgroundColor = 'var(--pico-color-red-500)';
    
    setTimeout(() => {
        button.innerHTML = originalHTML;
        button.style.opacity = '0.6';
        button.style.backgroundColor = 'transparent';
    }, 2000);
}

// Add clipboard functionality to assistant messages
function addClipboardToAssistantMessage(messageElement) {
    // Check if clipboard button already exists
    if (messageElement.querySelector('.clipboard-button')) {
        return;
    }
    
    // Only add clipboard if message has content
    const messageText = messageElement.dataset.rawText;
    if (!messageText || messageText.trim() === '') {
        return;
    }
    
    // Create message container structure
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = messageElement.innerHTML;
    
    const clipboardButton = document.createElement('button');
    clipboardButton.className = 'clipboard-button';
    clipboardButton.innerHTML = window.PCONFIG.clipboardSVG;
    clipboardButton.title = 'Copy message to clipboard';
    clipboardButton.onclick = function(e) {
        e.preventDefault();
        e.stopPropagation();
        copyMessageToClipboard(messageText, clipboardButton);
    };
    
    messageContainer.appendChild(messageContent);
    messageContainer.appendChild(clipboardButton);
    
    // Replace the message element content
    messageElement.innerHTML = '';
    messageElement.appendChild(messageContainer);
}

window.stopSidebarStream = function() {
    if (isStreaming && sidebarWs.readyState === WebSocket.OPEN) {
        console.log('Sending stop command to server...');
        sidebarWs.send('%%STOP_STREAM%%');
        // The UI will be fully updated once the server sends back %%STREAM_END%%
        updateStreamingUI(false); // Optimistically update UI
    }
}

window.sendSidebarMessage = function(event) {
    event.preventDefault();
    const input = document.getElementById('msg');
    if (input.value && !isStreaming) { // Prevent sending while streaming
        const userMessageText = input.value;
        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        
        // Create message container with clipboard functionality
        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = userMessageText;
        
        const clipboardButton = document.createElement('button');
        clipboardButton.className = 'clipboard-button';
        clipboardButton.innerHTML = window.PCONFIG.clipboardSVG;
        clipboardButton.title = 'Copy message to clipboard';
        clipboardButton.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            copyMessageToClipboard(userMessageText, clipboardButton);
        };
        
        messageContainer.appendChild(messageContent);
        messageContainer.appendChild(clipboardButton);
        userMsg.appendChild(messageContainer);
        
        sidebarMsgList.appendChild(userMsg);
        
        sidebarCurrentMessage = document.createElement('div');
        sidebarCurrentMessage.className = 'message assistant';
        
        console.log('Sidebar sending:', userMessageText);
        if (sidebarWs.readyState === WebSocket.OPEN) {
            sidebarWs.send(userMessageText);
            input.value = '';
            // The server will now send %%STREAM_START%% to lock the UI
        } else {
            console.error('WebSocket not connected');
        }
    }
}

// Scroll utilities for the main grid
function scrollToTop() {
    const container = document.querySelector(".main-grid > div:first-child");
    if (container) {
        container.scrollTo({top: 0, behavior: "smooth"});
    }
}

function checkScrollHeight() {
    const container = document.querySelector('.main-grid > div:first-child');
    const scrollLink = document.getElementById('scroll-to-top-link');
    if (container && scrollLink) {
        const isScrollable = container.scrollHeight > container.clientHeight;
        scrollLink.style.display = isScrollable ? 'block' : 'none';
    }
}

function initializeScrollObserver() {
    // Check on load and when content changes
    window.addEventListener('load', checkScrollHeight);
    const observer = new MutationObserver(checkScrollHeight);
    const container = document.querySelector('.main-grid > div:first-child');
    if (container) {
        observer.observe(container, { childList: true, subtree: true });
    }
}

// Function to send temp message when WebSocket is ready
function sendTempMessageWhenReady() {
    if (!tempMessage || tempMessageSent) return;
    
    if (sidebarWs.readyState === WebSocket.OPEN) {
        console.log('Sidebar sending verbatim:', tempMessage);
        const messageWithNewline = tempMessage + '';
        sidebarWs.send(`${messageWithNewline}|verbatim`);
        tempMessageSent = true;
    } else {
        // Wait for connection and retry
        console.log('WebSocket not ready, waiting for connection...');
        setTimeout(sendTempMessageWhenReady, 100);
    }
}

// Global keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl+Shift+R: Restart server
    if (event.ctrlKey && event.shiftKey && event.key === 'R') {
        event.preventDefault();
        console.log('🔄 Server restart triggered via Ctrl+Shift+R');
        
        // Show immediate UI feedback
        showRestartSpinner();
        
        // Send restart command via WebSocket
        if (sidebarWs.readyState === WebSocket.OPEN) {
            sidebarWs.send('%%RESTART_SERVER%%');
            console.log('🔄 Restart command sent via WebSocket');
        } else {
            console.error('🔄 WebSocket not connected, cannot send restart command');
            hideRestartSpinner();
        }
    }
});

// Show Pico CSS restart spinner
function showRestartSpinner() {
    // Remove any existing restart overlay
    const existingOverlay = document.getElementById('restart-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    // Create restart overlay with Pico CSS spinner
    const overlay = document.createElement('div');
    overlay.id = 'restart-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.85);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        color: white;
        font-family: system-ui, sans-serif;
        backdrop-filter: blur(2px);
        font-size: 1.2rem;
    `;
    
    // Use Pico CSS aria-busy spinner
    overlay.innerHTML = '<span aria-busy="true">Restarting server...</span>';
    
    document.body.appendChild(overlay);
    console.log('🔄 Restart spinner displayed');
}

// Hide restart spinner (fallback)
function hideRestartSpinner() {
    const overlay = document.getElementById('restart-overlay');
    if (overlay) {
        overlay.remove();
        console.log('🔄 Restart spinner hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeChatInterface();
    initializeScrollObserver();
    
    // Send temp message when WebSocket is ready (with initial delay for page load)
    if (tempMessage && !tempMessageSent) {
        setTimeout(sendTempMessageWhenReady, 1000);
    }
}); 