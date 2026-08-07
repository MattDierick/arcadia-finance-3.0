/** dashboard.js – Arcadia Finance */
document.addEventListener("DOMContentLoaded", async () => {
  let currentUser = null;
  try { currentUser = await API.me(); } catch { window.location.href = "/"; return; }

  const initials = (currentUser.name[0] + currentUser.surname[0]).toUpperCase();
  document.querySelectorAll(".user-initials").forEach(el => el.textContent = initials);
  document.querySelectorAll(".user-fullname").forEach(el => el.textContent = `${currentUser.name} ${currentUser.surname}`);
  document.querySelectorAll(".user-email").forEach(el => el.textContent = currentUser.email);

  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    // API.logout() clears the server session AND the localStorage JWT automatically
    await API.logout();
    sessionStorage.removeItem("arcadia_user");
    window.location.href = "/";
  });

  let accounts = [];
  const accountsGrid   = document.getElementById("accounts-grid");
  const totalBalanceEl = document.getElementById("total-balance");
  const chartCanvas    = document.getElementById("balance-chart");
  const fmt = (n, c = "EUR") => new Intl.NumberFormat("fr-FR", { style: "currency", currency: c }).format(n);
  const icon = t => ({ checking: "💳", savings: "🏦", investment: "📈" }[t] || "💰");

  async function loadAccounts() {
    accountsGrid.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Loading…</p></div>`;
    try { accounts = await API.accounts(); renderAccounts(); renderChart(); }
    catch { accountsGrid.innerHTML = `<div class="empty-state"><p>Could not load accounts.</p></div>`; }
  }

  function renderAccounts() {
    if (!accounts.length) { accountsGrid.innerHTML = `<div class="empty-state"><p>No accounts found.</p></div>`; return; }
    if (totalBalanceEl) totalBalanceEl.textContent = fmt(accounts.reduce((s, a) => s + a.balance, 0), accounts[0]?.currency);
    accountsGrid.innerHTML = accounts.map(a => `
      <div class="account-card" data-account="${a.account_number}" onclick="selectAccount('${a.account_number}')">
        <div class="flex-between mb-md">
          <div class="flex gap-sm" style="align-items:center">
            <div class="account-type-icon account-type-${a.type}">${icon(a.type)}</div>
            <div>
              <div style="font-weight:600;font-size:0.9rem;text-transform:capitalize">${a.type}</div>
              <div style="font-size:0.75rem;color:var(--text-muted);font-family:monospace">${a.account_number}</div>
            </div>
          </div>
          <span class="badge badge-success">Active</span>
        </div>
        <div class="balance-amount">${fmt(a.balance, a.currency)}</div>
        <div class="balance-currency">${a.currency}</div>
      </div>`).join("");
  }

  let chartInst = null;
  function renderChart() {
    if (!chartCanvas || !accounts.length) return;
    if (chartInst) chartInst.destroy();
    const colorMap = { checking:"rgba(59,130,246,0.8)", savings:"rgba(16,185,129,0.8)", investment:"rgba(245,158,11,0.8)" };
    chartInst = new Chart(chartCanvas, {
      type: "bar",
      data: {
        labels: accounts.map(a => `${a.type.charAt(0).toUpperCase()+a.type.slice(1)} …${a.account_number.slice(-4)}`),
        datasets: [{ label:"Balance", data: accounts.map(a => a.balance), backgroundColor: accounts.map(a => colorMap[a.type]||"rgba(228,0,43,0.8)"), borderRadius:8, borderSkipped:false }],
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{display:false}, tooltip:{callbacks:{label:c=>fmt(c.parsed.y)}} },
        scales:{
          x:{grid:{color:"rgba(255,255,255,0.05)"},ticks:{color:"#94A3B8"}},
          y:{grid:{color:"rgba(255,255,255,0.05)"},ticks:{color:"#94A3B8",callback:v=>fmt(v)}},
        },
      },
    });
  }

  async function populateFromSelect() {
    const sel = document.getElementById("from-account"); if (!sel) return;
    const list = await API.accounts().catch(() => []);
    sel.innerHTML = list.map(a => `<option value="${a.account_number}">${a.type.charAt(0).toUpperCase()+a.type.slice(1)} — ${a.account_number} (${fmt(a.balance,a.currency)})</option>`).join("");
  }

  const fmt2 = fmt; // alias for closure
  setupTransferForm(fmt);

  // Listen for completed transfers to reload
  document.addEventListener("transfer:completed", async ev => {
    await loadAccounts(); await populateFromSelect();
    if (ev.detail?.from_account) loadTransfers(ev.detail.from_account, fmt2);
  });

  window.selectAccount = function(num) {
    document.querySelectorAll(".account-card").forEach(el => el.classList.toggle("selected", el.dataset.account === num));
    const s = document.getElementById("from-account"); if (s) s.value = num;
    loadTransfers(num, fmt2);
  };

  await loadAccounts();
  await populateFromSelect();
  if (accounts.length) selectAccount(accounts[0].account_number);
});
