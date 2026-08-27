/**
 * config.js – LLM configuration page for Arcadia Finance
 *
 * LLM token storage model:
 *  - The LLM API token is stored exclusively in the browser (localStorage key
 *    "arcadia_llm_token") via API.saveLlmToken().
 *  - It is NEVER sent to or persisted on the app server or database.
 *  - The masked hint shown in the UI is computed locally from localStorage.
 */
document.addEventListener("DOMContentLoaded", async () => {
  // Auth guard
  try { await API.me(); } catch { window.location.href = "/"; return; }

  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    await API.logout(); window.location.href = "/";
  });

  const form        = document.getElementById("config-form");
  const resultEl    = document.getElementById("config-result");
  const tokenMasked = document.getElementById("token-masked");
  const statusDot   = document.getElementById("llm-status");

  /** Render a masked hint for the token stored in localStorage. */
  function _maskLocalToken() {
    const tok = API.getLlmToken();
    if (!tok) return "";
    return tok.length > 12 ? tok.slice(0, 6) + "..." + tok.slice(-4) : "****";
  }

  // Load current config — non-secret fields come from the server; token is local-only.
  async function loadConfig() {
    try {
      const cfg = await API.getConfig();
      document.getElementById("llm-url").value   = cfg.llm_url   || "";
      document.getElementById("llm-model").value = cfg.llm_model || "gpt-4o";
      document.getElementById("chatbot-system-prompt").value = cfg.chatbot_system_prompt || "";

      // Token status is derived entirely from localStorage — no server round-trip.
      const masked = _maskLocalToken();
      if (tokenMasked) {
        tokenMasked.textContent = masked
          ? `Current token: ${masked} (stored in browser)`
          : "No token stored in browser";
      }
      if (statusDot) {
        const configured = !!(cfg.llm_url && masked);
        statusDot.textContent = configured ? "🟢 LLM Configured" : "🔴 Not Configured";
      }
    } catch { /* ignore */ }
  }

  await loadConfig();

  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving…";

    // Non-secret settings are persisted on the server as before.
    const payload = {
      llm_url:               document.getElementById("llm-url").value.trim(),
      llm_model:             document.getElementById("llm-model").value.trim(),
      chatbot_system_prompt: document.getElementById("chatbot-system-prompt").value.trim(),
    };

    // The token is saved to browser localStorage only — never included in the server payload.
    const tokenInput = document.getElementById("llm-token").value.trim();
    if (tokenInput) {
      API.saveLlmToken(tokenInput);
    }

    try {
      await API.saveConfig(payload);
      resultEl.textContent = "✅ Configuration saved successfully!";
      resultEl.className   = "mt-md text-success";
      document.getElementById("llm-token").value = ""; // clear token field after saving
      await loadConfig();
    } catch (err) {
      resultEl.textContent = `❌ ${err?.data?.error || "Save failed."}`;
      resultEl.className   = "mt-md text-error";
    } finally {
      btn.disabled = false;
      btn.textContent = "Save Configuration";
    }
  });

  document.querySelectorAll(".user-initials").forEach(async el => {
    try { const u = await API.me(); el.textContent = (u.name[0]+u.surname[0]).toUpperCase(); } catch {}
  });
});
