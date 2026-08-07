/**
 * chatbot.js – Aria chatbot widget for Arcadia Finance
 * Included on both index.html and dashboard.html
 */

document.addEventListener("DOMContentLoaded", () => {
  const fab      = document.getElementById("chatbot-fab");
  const panel    = document.getElementById("chatbot-panel");
  const closeBtn = document.getElementById("chatbot-close");
  const messages = document.getElementById("chatbot-messages");
  const input    = document.getElementById("chatbot-input");
  const sendBtn  = document.getElementById("chatbot-send");

  if (!fab) return; // widget not present on this page

  let history = []; // [{role, content}]
  let isOpen  = false;

  // ── Toggle panel ──────────────────────────────────────
  function togglePanel() {
    isOpen = !isOpen;
    panel.classList.toggle("hidden", !isOpen);
    if (isOpen && messages.children.length === 0) {
      appendMessage("bot", "👋 Hi! I'm **Aria**, your Arcadia Finance assistant. How can I help you today?");
    }
    if (isOpen) input.focus();
  }

  fab.addEventListener("click", togglePanel);
  closeBtn.addEventListener("click", () => { isOpen = false; panel.classList.add("hidden"); });

  // ── Render a message bubble ────────────────────────────
  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    // Simple markdown: **bold**
    div.innerHTML = text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function appendTyping() {
    const div = document.createElement("div");
    div.className = "chat-msg bot";
    div.id = "typing-indicator";
    div.innerHTML = '<span class="spinner"></span>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById("typing-indicator");
    if (t) t.remove();
  }

  // ── Send message ───────────────────────────────────────
  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    sendBtn.disabled = true;

    appendMessage("user", text);
    history.push({ role: "user", content: text });
    appendTyping();

    try {
      const res = await API.chat(history);
      removeTyping();

      if (res.error) {
        appendMessage("bot", `⚠️ Error: ${res.error}`);
      } else {
        appendMessage("bot", res.reply);
        history.push({ role: "assistant", content: res.reply });
      }
    } catch (err) {
      removeTyping();
      appendMessage("bot", "⚠️ Something went wrong. Please try again.");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
});
