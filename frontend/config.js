// Replace this with your Railway URL after deploying.
// e.g. "https://pushing-daisies-production.up.railway.app"
window.API_BASE = "REPLACE_WITH_YOUR_RAILWAY_URL";

// Auto-fallback: if the placeholder wasn't replaced, use localhost in dev
if (!window.API_BASE || window.API_BASE.startsWith("REPLACE")) {
  window.API_BASE = "http://localhost:8000";
}
