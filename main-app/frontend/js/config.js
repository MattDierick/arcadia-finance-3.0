/**
 * config.js – LLM configuration page for Arcadia Finance
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

  // Load current config
  async function loadConfig() {
    try {
      const cfg = await API.getConfig();
      document.getElementById("llm-url").value   = cfg.llm_url   || "";
      document.getElementById("llm-model").value = cfg.llm_model || "gpt-4o";
      document.getElementById("chatbot-system-prompt").value = cfg.chatbot_system_prompt || "";
      if (tokenMasked) {
        tokenMasked.textContent = cfg.llm_token_masked ? `Current token: ${cfg.llm_token_masked}` : "No token stored";
      }
      if (statusDot) {
        const configured = !!(cfg.llm_url && cfg.llm_token_masked);
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

    const payload = {
      llm_url:               document.getElementById("llm-url").value.trim(),
      llm_model:             document.getElementById("llm-model").value.trim(),
      chatbot_system_prompt: document.getElementById("chatbot-system-prompt").value.trim(),
    };
    const tokenInput = document.getElementById("llm-token").value.trim();
    if (tokenInput) payload.llm_token = tokenInput;

    try {
      await API.saveConfig(payload);
      resultEl.textContent = "✅ Configuration saved successfully!";
      resultEl.className   = "mt-md text-success";
      document.getElementById("llm-token").value = ""; // clear token field
      await loadConfig();
    } catch (err) {
      resultEl.textContent = `❌ ${err?.data?.error || "Save failed."}`;
      resultEl.className   = "mt-md text-error";
    } finally {
      btn.disabled = false;
      btn.textContent = "Save Configuration";
    }
  });

  // Logout already wired via inline handler above
  document.querySelectorAll(".user-initials").forEach(async el => {
    try { const u = await API.me(); el.textContent = (u.name[0]+u.surname[0]).toUpperCase(); } catch {}
  });
});
