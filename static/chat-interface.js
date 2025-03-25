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
    
    // Check if the response contains 'todo-' in the id attribute
    if (event.data.includes('todo-')) {
        const todoList = document.getElementById('todo-list');
        if (todoList) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = event.data.trim(); // Trim in case of leading/trailing whitespace
            const newItem = tempDiv.firstElementChild;
            if (newItem && newItem.tagName === 'LI') {
                todoList.appendChild(newItem);
                htmx.process(newItem);  // Process HTMX bindings on the new item
                // Reinitialize sortable if necessary
                if (window.Sortable && !todoList.classList.contains('sortable-initialized')) {
                    new Sortable(todoList, {
                        animation: 150,
                        ghostClass: 'blue-background-class'
                    });
                    todoList.classList.add('sortable-initialized');
                }
            }
        }
        return;
    }
    
    // Handle regular chat messages
    if (!sidebarCurrentMessage.parentElement) {
        sidebarMsgList.appendChild(sidebarCurrentMessage);
    }
    sidebarCurrentMessage.innerHTML += event.data;
    sidebarMsgList.scrollTop = sidebarMsgList.scrollHeight;
};

// Handle temp_message if it exists
window.addEventListener('DOMContentLoaded', () => {
    if (tempMessage) {
        console.log('Sidebar sending verbatim:', tempMessage);
        setTimeout(() => sidebarWs.send(`${tempMessage}|verbatim`), 1000);
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