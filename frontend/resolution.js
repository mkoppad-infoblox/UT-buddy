// Multi-turn chat for error resolution
let resolutionMessages = [];

function renderResolutionChat() {
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';
    resolutionMessages.forEach(msg => {
        const div = document.createElement('div');
        div.className = 'message ' + msg.role;
        div.innerHTML = `<strong>${msg.role === 'user' ? 'You' : 'Assistant'}:</strong> ${msg.content}`;
        chatBox.appendChild(div);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendResolutionMessage() {
    const errorInput = document.getElementById('errorInput');
    const text = errorInput.value.trim();
    if (!text) return;

    resolutionMessages.push({ role: 'user', content: text });
    renderResolutionChat();
    errorInput.value = '';

    // Show loading
    resolutionMessages.push({ role: 'assistant', content: 'Thinking...' });
    renderResolutionChat();

    try {
        const response = await fetch('/resolve_error_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: resolutionMessages.filter(m => m.role !== 'assistant') })
        });
        const data = await response.json();
        // Remove loading
        resolutionMessages.pop();
        if (data.response) {
            resolutionMessages.push({ role: 'assistant', content: data.response });
        } else {
            resolutionMessages.push({ role: 'assistant', content: 'Error: ' + (data.error || 'Unknown error') });
        }
        renderResolutionChat();
    } catch (err) {
        resolutionMessages.pop();
        resolutionMessages.push({ role: 'assistant', content: 'Error: ' + err.message });
        renderResolutionChat();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('errorResolveBtn');
    if (btn) {
        btn.addEventListener('click', sendResolutionMessage);
    }
    renderResolutionChat();
});
