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
                const renderedHtml = marked.parse(rawText);
                sidebarCurrentMessage.innerHTML = renderedHtml;
                
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
    
    // Keep the latest message in view
    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
};

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

document.addEventListener('DOMContentLoaded', () => {
    initializeChatInterface();
    initializeScrollObserver();
    
    // Send temp message when WebSocket is ready (with initial delay for page load)
    if (tempMessage && !tempMessageSent) {
        setTimeout(sendTempMessageWhenReady, 1000);
    }
}); 