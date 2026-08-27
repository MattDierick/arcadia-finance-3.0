/**
 * config.js – LLM + F5 AI Security configuration page for Arcadia Finance
 *
 * Token storage model (applied to BOTH the LLM token and the F5 AI Security token):
 *  - Secrets are stored exclusively in the browser (localStorage) via API.saveLlmToken()
 *    / API.saveF5AiSecToken(). They are NEVER sent to or persisted on the app server.
 *  - Non-secret fields (URLs, model, system prompt, calypso_enabled toggle) are saved
 *    server-side in app_config as before.
 *  - Masked hints shown in the UI are computed locally from localStorage.
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

  const f5Form          = document.getElementById("f5aisec-form");
  const f5ResultEl      = document.getElementById("f5aisec-result");
  const f5TokenMasked   = document.getElementById("calypso-token-masked");

  /** Return a masked hint string for any token (first 6 + last 4), or "" if absent. */
  function _mask(tok) {
    if (!tok) return "";
    return tok.length > 12 ? tok.slice(0, 6) + "..." + tok.slice(-4) : "****";
  }

  // Load current config — non-secret fields come from the server; tokens are local-only.
  async function loadConfig() {
    try {
      const cfg = await API.getConfig();

      // ── LLM section ───────────────────────────────────────────────────────
      document.getElementById("llm-url").value   = cfg.llm_url   || "";
      document.getElementById("llm-model").value = cfg.llm_model || "gpt-4o";
      document.getElementById("chatbot-system-prompt").value = cfg.chatbot_system_prompt || "";

      const llmMasked = _mask(API.getLlmToken());
      if (tokenMasked) {
        tokenMasked.textContent = llmMasked
          ? `Current token: ${llmMasked} (stored in browser)`
          : "No token stored in browser";
      }
      if (statusDot) {
        const configured = !!(cfg.llm_url && llmMasked);
        statusDot.textContent = configured ? "🟢 LLM Configured" : "🔴 Not Configured";
      }

      // ── F5 AI Security section ────────────────────────────────────────────
      const calypsoEnabledEl = document.getElementById("calypso-enabled");
      const calypsoUrlEl     = document.getElementById("calypso-url");

      if (calypsoEnabledEl) calypsoEnabledEl.checked = !!cfg.calypso_enabled;
      if (calypsoUrlEl)     calypsoUrlEl.value        = cfg.calypso_url || "https://www.us1.calypsoai.app";

      const f5Masked = _mask(API.getF5AiSecToken());
      if (f5TokenMasked) {
        f5TokenMasked.textContent = f5Masked
          ? `Current token: ${f5Masked} (stored in browser)`
          : "No token stored in browser";
      }
    } catch { /* ignore */ }
  }

  await loadConfig();

  // ── LLM config form ───────────────────────────────────────────────────────
  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving…";

    // Non-secret settings persisted server-side.
    const payload = {
      llm_url:               document.getElementById("llm-url").value.trim(),
      llm_model:             document.getElementById("llm-model").value.trim(),
      chatbot_system_prompt: document.getElementById("chatbot-system-prompt").value.trim(),
    };

    // LLM token — browser localStorage only, never in the server payload.
    const llmTokenInput = document.getElementById("llm-token").value.trim();
    if (llmTokenInput) API.saveLlmToken(llmTokenInput);

    try {
      await API.saveConfig(payload);
      resultEl.textContent = "✅ Configuration saved successfully!";
      resultEl.className   = "mt-md text-success";
      document.getElementById("llm-token").value = "";
      await loadConfig();
    } catch (err) {
      resultEl.textContent = `❌ ${err?.data?.error || "Save failed."}`;
      resultEl.className   = "mt-md text-error";
    } finally {
      btn.disabled = false;
      btn.textContent = "Save Configuration";
    }
  });

  // ── F5 AI Security form ───────────────────────────────────────────────────
  f5Form?.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = f5Form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving…";

    // Non-secret settings (toggle + URL) persisted server-side.
    const payload = {
      calypso_enabled: document.getElementById("calypso-enabled").checked,
      calypso_url:     document.getElementById("calypso-url").value.trim(),
    };

    // F5 AI Security token — browser localStorage only, never in the server payload.
    const f5TokenInput = document.getElementById("calypso-token").value.trim();
    if (f5TokenInput) API.saveF5AiSecToken(f5TokenInput);

    try {
      await API.saveConfig(payload);
      f5ResultEl.textContent = "✅ F5 AI Security settings saved!";
      f5ResultEl.className   = "mt-md text-success";
      document.getElementById("calypso-token").value = "";
      await loadConfig();
    } catch (err) {
      f5ResultEl.textContent = `❌ ${err?.data?.error || "Save failed."}`;
      f5ResultEl.className   = "mt-md text-error";
    } finally {
      btn.disabled = false;
      btn.textContent = "Save F5 AI Security Settings";
    }
  });

  document.querySelectorAll(".user-initials").forEach(async el => {
    try { const u = await API.me(); el.textContent = (u.name[0]+u.surname[0]).toUpperCase(); } catch {}
  });
});
