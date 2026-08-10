/**
 * home.js – Login form logic for the Arcadia Finance home page
 */

document.addEventListener("DOMContentLoaded", () => {
  const form      = document.getElementById("login-form");
  const btnText   = document.getElementById("login-btn-text");
  const btnSpinner= document.getElementById("login-btn-spinner");
  const errorBox  = document.getElementById("login-error");

  // If a JWT token exists, verify it is still valid and redirect to dashboard.
  // Skipping the call entirely when no token is present avoids a pointless 401.
  if (localStorage.getItem("arcadia_jwt")) {
    API.me().then(() => { window.location.href = "/dashboard.html"; }).catch(() => {});
  }

  function setLoading(on) {
    btnText.textContent = on ? "Signing in…" : "Sign In";
    btnSpinner.classList.toggle("hidden", !on);
    form.querySelector("button[type=submit]").disabled = on;
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !password) { showError("Please enter your username and password."); return; }

    setLoading(true);
    try {
      const user = await API.login(username, password);
      // Store user info in sessionStorage for UI display
      // JWT is automatically stored in localStorage by API.login()
      sessionStorage.setItem("arcadia_user", JSON.stringify(user));
      window.location.href = "/dashboard.html";
    } catch (err) {
      const msg = err?.data?.error || "Login failed. Please check your credentials.";
      showError(msg);
    } finally {
      setLoading(false);
    }
  });

  // Demo user quick-fill
  document.querySelectorAll(".demo-user-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("username").value = btn.dataset.user;
      document.getElementById("password").value = btn.dataset.pass;
    });
  });
});
