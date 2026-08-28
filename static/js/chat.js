/**
 * Companio - Real-Time Chat Simulator
 * Simulates Django Channels WebSocket interaction for live assistance chat
 */

document.addEventListener('DOMContentLoaded', () => {
  initChatEngine();
});

function initChatEngine() {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const chatMessages = document.getElementById('chat-messages');

  if (chatForm && chatInput && chatMessages) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const messageText = chatInput.value.trim();
      if (!messageText) return;

      // Render sent message
      appendMessage(messageText, 'sent');
      chatInput.value = '';

      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;

      // Simulate automated volunteer reply after 1.2 seconds
      setTimeout(() => {
        const automatedReplies = [
          "Hello! I'd be happy to assist you with your request today.",
          "I will be arriving at your location in about 15 minutes.",
          "Thank you for sharing the details! Is there anything specific I should prepare?",
          "No problem at all. Your convenience and comfort are my top priority."
        ];
        const reply = automatedReplies[Math.floor(Math.random() * automatedReplies.length)];
        appendMessage(reply, 'received');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        if (typeof showToast === 'function') {
          showToast('New message received', 'info');
        }
      }, 1200);
    });
  }
}

function appendMessage(text, direction) {
  const chatMessages = document.getElementById('chat-messages');
  if (!chatMessages) return;

  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const messageHtml = `
    <div class="message-bubble message-${direction}">
      <div>${escapeHtml(text)}</div>
      <div class="text-end mt-1" style="font-size: 0.75rem; opacity: 0.8;">${timeStr}</div>
    </div>
  `;

  chatMessages.insertAdjacentHTML('beforeend', messageHtml);
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
