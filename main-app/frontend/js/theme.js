/**
 * theme.js – Dark / Light mode toggle for Arcadia Finance
 *
 * Strategy:
 *   - Theme is stored in localStorage under the key "arcadia_theme".
 *   - Applying a theme sets data-theme="light" on <html> (dark is the default,
 *     no attribute needed so existing CSS stays untouched).
 *   - The script is loaded as the very first <script> in each page so the
 *     correct theme is applied before first paint (no flash of wrong theme).
 */

(function () {
  const STORAGE_KEY = "arcadia_theme";
  const DARK  = "dark";
  const LIGHT = "light";

  /** Apply theme to <html> and update every toggle button on the page. */
  function applyTheme(theme) {
    if (theme === LIGHT) {
      document.documentElement.setAttribute("data-theme", LIGHT);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    // Update aria-label on all toggle buttons already in the DOM
    document.querySelectorAll(".theme-toggle").forEach(btn => {
      btn.setAttribute(
        "aria-label",
        theme === LIGHT ? "Switch to dark mode" : "Switch to light mode"
      );
      btn.setAttribute("title",
        theme === LIGHT ? "Switch to dark mode" : "Switch to light mode"
      );
    });
  }

  /** Read persisted preference, falling back to OS preference then dark. */
  function getStoredTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === LIGHT || stored === DARK) return stored;
    // Respect OS colour-scheme preference on first visit
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return LIGHT;
    }
    return DARK;
  }

  /** Toggle between dark and light and persist the choice. */
  function toggleTheme() {
    const current = localStorage.getItem(STORAGE_KEY) || getStoredTheme();
    const next    = current === LIGHT ? DARK : LIGHT;
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }

  // ── Apply immediately (before DOMContentLoaded) to avoid FOUC ──────────
  applyTheme(getStoredTheme());

  // ── Wire up toggle buttons once the DOM is ready ────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    // Apply again so aria-labels on buttons are set correctly
    applyTheme(getStoredTheme());

    document.querySelectorAll(".theme-toggle").forEach(btn => {
      btn.addEventListener("click", toggleTheme);
    });
  });

  // Expose helpers globally so other scripts can call them if needed
  window.ArcadiaTheme = { toggle: toggleTheme, apply: applyTheme, get: getStoredTheme };
})();
