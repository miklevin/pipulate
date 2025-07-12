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

// Global demo mode tracking
let demoModeActive = false;
let currentDemoScript = null;
let currentDemoStepIndex = 0;

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
    
    // Ctrl+Shift+D: Start demo/regression prevention sequence
    if (event.ctrlKey && event.shiftKey && event.key === 'D') {
        event.preventDefault();
        console.log('🎯 Demo sequence triggered via Ctrl+Shift+D');
        
        // Load and execute the demo script sequence
        loadDemoScript();
    }
});

// Function to simulate user input for demo/regression prevention sequences
function simulateUserInput(message) {
    console.log('🎯 Simulating user input:', message);
    
    // Find the message input textarea
    const msgTextarea = document.getElementById('msg');
    if (!msgTextarea) {
        console.error('🎯 Could not find message input textarea');
        return;
    }
    
    // Set the message text
    msgTextarea.value = message;
    
    // Find the form and submit it (simulating user pressing Enter)
    const form = msgTextarea.closest('form');
    if (form) {
        console.log('🎯 Submitting simulated user message');
        form.requestSubmit ? form.requestSubmit() : form.submit();
    } else {
        console.error('🎯 Could not find form to submit');
    }
}

// Function to load and execute demo script sequence
async function loadDemoScript() {
    try {
        console.log('🎯 Loading demo script configuration...');
        
        // Load the demo script configuration
        const response = await fetch('/demo_script_config.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const config = await response.json();
        const demoScript = config.demo_script;
        
        console.log('🎯 Demo script loaded:', demoScript.name);
        
        // Activate demo mode - this prevents real LLM submissions
        demoModeActive = true;
        currentDemoScript = demoScript;
        currentDemoStepIndex = 0;
        
        console.log('🎯 Demo mode ACTIVATED - Form submissions will be intercepted');
        
        // Execute the demo sequence
        await executeDemoSequence(demoScript);
        
    } catch (error) {
        console.error('🎯 Error loading demo script:', error);
        
        // Fallback to simple user input
        simulateUserInput('What is this?');
    }
}

// Function to execute a demo sequence with timing and MCP tool calls
async function executeDemoSequence(demoScript) {
    console.log('🎯 Executing demo sequence:', demoScript.name);
    
    for (const step of demoScript.steps) {
        console.log(`🎯 Executing step: ${step.step_id}`);
        
        // Wait for delay before step
        if (step.timing && step.timing.delay_before) {
            await new Promise(resolve => setTimeout(resolve, step.timing.delay_before));
        }
        
        switch (step.type) {
            case 'user_input':
                await executeUserInputStep(step);
                break;
                
            case 'system_reply':
                await executeSystemReplyStep(step);
                break;
                
            case 'mcp_tool_call':
                await executeMcpToolCallStep(step);
                break;
                
            default:
                console.warn('🎯 Unknown step type:', step.type);
        }
        
        // Small delay between steps for natural flow
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    console.log('🎯 Demo sequence completed!');
}

// Execute user input step with typing simulation
async function executeUserInputStep(step) {
    console.log('🎯 Executing user input step:', step.message);
    
    const msgTextarea = document.getElementById('msg');
    if (!msgTextarea) {
        console.error('🎯 Could not find message input textarea');
        return;
    }
    
    // Simulate typing if typing_speed is specified
    if (step.timing && step.timing.typing_speed) {
        await simulateTyping(msgTextarea, step.message, step.timing.typing_speed);
    } else {
        msgTextarea.value = step.message;
    }
    
    // In demo mode, we'll intercept the submission and trigger the next step
    // Submit the form (will be intercepted by our demo mode interceptor)
    const form = msgTextarea.closest('form');
    if (form) {
        form.requestSubmit ? form.requestSubmit() : form.submit();
    }
}

// Execute system reply step (verbatim, not LLM generated)
async function executeSystemReplyStep(step) {
    console.log('🎯 Executing system reply step');
    
    // Send verbatim system message via WebSocket
    if (sidebarWs.readyState === WebSocket.OPEN) {
        const systemMessage = {
            type: 'system_reply',
            message: step.message,
            verbatim: step.verbatim || false,
            timing: step.timing || {}
        };
        
        sidebarWs.send('%%DEMO_SYSTEM_REPLY%%:' + JSON.stringify(systemMessage));
        console.log('🎯 Sent system reply via WebSocket');
    } else {
        console.error('🎯 WebSocket not connected, cannot send system reply');
    }
}

// Execute MCP tool call step
async function executeMcpToolCallStep(step) {
    console.log('🎯 Executing MCP tool call:', step.tool_name);
    
    // Send MCP tool call via WebSocket
    if (sidebarWs.readyState === WebSocket.OPEN) {
        const mcpCall = {
            type: 'mcp_tool_call',
            tool_name: step.tool_name,
            tool_args: step.tool_args || {},
            description: step.description || ''
        };
        
        sidebarWs.send('%%DEMO_MCP_CALL%%:' + JSON.stringify(mcpCall));
        console.log('🎯 Sent MCP tool call via WebSocket');
    } else {
        console.error('🎯 WebSocket not connected, cannot send MCP tool call');
    }
}

// Simulate typing animation
async function simulateTyping(textarea, message, speed) {
    textarea.value = '';
    
    for (let i = 0; i < message.length; i++) {
        textarea.value += message[i];
        await new Promise(resolve => setTimeout(resolve, speed));
    }
}

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

// Form submission interceptor for demo mode
function interceptFormSubmission() {
    // Find all forms and add submission interceptors
    document.addEventListener('submit', function(event) {
        if (demoModeActive) {
            console.log('🎯 INTERCEPTED: Form submission blocked due to demo mode');
            event.preventDefault();
            event.stopPropagation();
            
            // Get the message that was typed
            const msgTextarea = document.getElementById('msg');
            const userMessage = msgTextarea ? msgTextarea.value : '';
            
            console.log('🎯 Intercepted user message:', userMessage);
            
            // Display the user message in the chat (phantom user message)
            if (userMessage.trim()) {
                displayPhantomUserMessage(userMessage);
            }
            
            // Clear the textarea to simulate normal submission
            if (msgTextarea) {
                msgTextarea.value = '';
            }
            
            // Trigger the next step in our demo script (the phantom LLM response)
            triggerNextDemoStep();
        }
    });
    
    // Also intercept the Enter key submission in chat
    document.addEventListener('keydown', function(event) {
        if (demoModeActive && event.key === 'Enter' && !event.shiftKey) {
            const msgTextarea = document.getElementById('msg');
            if (msgTextarea && event.target === msgTextarea) {
                console.log('🎯 INTERCEPTED: Enter key submission blocked due to demo mode');
                event.preventDefault();
                event.stopPropagation();
                
                const userMessage = msgTextarea.value;
                console.log('🎯 Intercepted user message (Enter key):', userMessage);
                
                // Display the user message in the chat (phantom user message)
                if (userMessage.trim()) {
                    displayPhantomUserMessage(userMessage);
                }
                
                // Clear the textarea
                msgTextarea.value = '';
                
                // Trigger the next step in our demo script
                triggerNextDemoStep();
            }
        }
    });
}

// Function to trigger the next step in the demo script
function triggerNextDemoStep() {
    if (!demoModeActive || !currentDemoScript) {
        console.log('🎯 No demo script active, cannot trigger next step');
        return;
    }
    
    // Find the next step that should be executed as a response
    const nextStepIndex = currentDemoStepIndex + 1;
    if (nextStepIndex >= currentDemoScript.steps.length) {
        console.log('🎯 Demo script completed, deactivating demo mode');
        demoModeActive = false;
        currentDemoScript = null;
        currentDemoStepIndex = 0;
        return;
    }
    
    const nextStep = currentDemoScript.steps[nextStepIndex];
    console.log(`🎯 Triggering next demo step: ${nextStep.step_id}`);
    
    currentDemoStepIndex = nextStepIndex;
    
    // Execute the next step (usually a system reply)
    setTimeout(async () => {
        await executeIndividualDemoStep(nextStep);
    }, nextStep.timing?.delay_before || 500);
}

// Function to execute an individual demo step
async function executeIndividualDemoStep(step) {
    console.log(`🎯 Executing individual step: ${step.step_id}`);
    
    switch (step.type) {
        case 'system_reply':
            await executePhantomLLMResponse(step);
            break;
            
        case 'mcp_tool_call':
            await executeMcpToolCallStep(step);
            break;
            
        default:
            console.warn('🎯 Unexpected step type in response:', step.type);
    }
}

// Function to simulate phantom LLM response with typing
async function executePhantomLLMResponse(step) {
    console.log('🎯 Executing phantom LLM response with typing simulation');
    
    // Show the typing indicator
    showLLMTypingIndicator();
    
    // Wait for the typing simulation
    await simulatePhantomLLMTyping(step.message, step.timing?.display_speed || 30);
    
    // Hide the typing indicator and show the final message
    hideLLMTypingIndicator();
    displayPhantomLLMMessage(step.message);
}

// Function to show LLM typing indicator
function showLLMTypingIndicator() {
    // Add a typing indicator to the chat
    const msgList = document.getElementById('msg-list');
    if (msgList) {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'phantom-typing-indicator';
        typingDiv.innerHTML = '🤖 <em>AI is typing...</em>';
        typingDiv.style.cssText = 'opacity: 0.7; font-style: italic; padding: 10px;';
        msgList.appendChild(typingDiv);
        msgList.scrollTop = msgList.scrollHeight;
    }
}

// Function to hide LLM typing indicator
function hideLLMTypingIndicator() {
    const typingIndicator = document.getElementById('phantom-typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Function to simulate phantom LLM typing
async function simulatePhantomLLMTyping(message, speed) {
    // Just wait for the appropriate time to simulate typing
    const typingTime = message.length * speed;
    await new Promise(resolve => setTimeout(resolve, typingTime));
}

// Function to display phantom LLM message
function displayPhantomLLMMessage(message) {
    const msgList = document.getElementById('msg-list');
    if (msgList) {
        const messageDiv = document.createElement('div');
        messageDiv.innerHTML = `<div class="assistant-message">${message}</div>`;
        messageDiv.style.cssText = 'padding: 10px; margin: 5px 0; background: #f0f8ff; border-radius: 8px;';
        msgList.appendChild(messageDiv);
        msgList.scrollTop = msgList.scrollHeight;
    }
}

// Function to display phantom user message
function displayPhantomUserMessage(message) {
    const msgList = document.getElementById('msg-list');
    if (msgList) {
        const messageDiv = document.createElement('div');
        messageDiv.innerHTML = `<div class="user-message">${message}</div>`;
        messageDiv.style.cssText = 'padding: 10px; margin: 5px 0; background: #e8f5e8; border-radius: 8px; text-align: right;';
        msgList.appendChild(messageDiv);
        msgList.scrollTop = msgList.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeChatInterface();
    initializeScrollObserver();
    
    // Initialize form submission interceptor
    interceptFormSubmission();
    
    // Send temp message when WebSocket is ready (with initial delay for page load)
    if (tempMessage && !tempMessageSent) {
        setTimeout(sendTempMessageWhenReady, 1000);
    }
}); 