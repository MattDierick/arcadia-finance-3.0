/** dashboard-transfer.js – Transfer form & history helpers */

function setupTransferForm(fmt) {
  const transferForm   = document.getElementById("transfer-form");
  const transferResult = document.getElementById("transfer-result");
  const showMsg = (msg, type) => {
    if (!transferResult) return;
    transferResult.textContent = msg;
    transferResult.className = `mt-md ${type === "success" ? "text-success" : "text-error"}`;
  };

  transferForm?.addEventListener("submit", async e => {
    e.preventDefault();
    const from_account = document.getElementById("from-account").value;
    const to_account   = document.getElementById("to-account").value.trim();
    const amount       = parseFloat(document.getElementById("amount").value);
    const note         = document.getElementById("note").value.trim();
    if (!from_account || !to_account || !amount) { showMsg("Please fill all required fields.", "error"); return; }
    if (from_account === to_account) { showMsg("Source and destination must differ.", "error"); return; }
    const btn = transferForm.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "Processing…";
    try {
      const res = await API.transfer({ from_account, to_account, amount, note });
      showMsg(`✅ Transfer of ${fmt(amount)} completed! (ID: ${res.transfer_id})`, "success");
      transferForm.reset();
      // Trigger reload via custom event
      document.dispatchEvent(new CustomEvent("transfer:completed", { detail: { from_account } }));
    } catch (err) { showMsg(`❌ ${err?.data?.error || "Transfer failed."}`, "error"); }
    finally { btn.disabled = false; btn.textContent = "Send Transfer"; }
  });
}

async function loadTransfers(account, fmt) {
  const transfersTbody = document.getElementById("transfers-tbody");
  if (!transfersTbody) return;
  transfersTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px"><div class="spinner" style="margin:auto"></div></td></tr>`;
  try {
    const rows = await API.transfers(account);
    renderTransfers(rows, account, fmt, transfersTbody);
  } catch {
    transfersTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-secondary);padding:24px">Could not load history.</td></tr>`;
  }
}

function renderTransfers(rows, acct, fmt, tbody) {
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-secondary)">No transfers for this account.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(t => {
    const out = t.from_account === acct;
    return `<tr>
      <td style="font-family:monospace;font-size:0.8rem">#${t.id}</td>
      <td style="font-family:monospace;font-size:0.8rem">${t.from_account}</td>
      <td style="font-family:monospace;font-size:0.8rem">${t.to_account}</td>
      <td class="${out ? "text-error" : "text-success"}" style="font-weight:700">${out ? "-" : "+"}${fmt(Math.abs(t.amount))}</td>
      <td>${t.note || "<span style='color:var(--text-muted)'>—</span>"}</td>
      <td><span class="badge badge-success">${t.status}</span></td>
      <td style="color:var(--text-muted);font-size:0.8rem">${new Date(t.created_at).toLocaleDateString("fr-FR")}</td>
    </tr>`;
  }).join("");
}
