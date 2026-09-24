// Shared helpers for every page: sidebar, API calls, formatting, status pills.

const ICONS = {
  dashboard: '<path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/>',
  run: '<path d="M12 5v14M5 12h14"/>',
  folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
  reference: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  alert: '<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  spinner: '<path d="M21 12a9 9 0 1 1-6.2-8.6"/>',
  minus: '<path d="M5 12h14"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
  logo: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4"/>',
};

function icon(name, size = 18) {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]}</svg>`;
}

// Escape anything that came from a PDF or the API before putting it in HTML.
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const money = (v) => (v === null || v === undefined || v === "" ? "—"
  : Number(v).toLocaleString("en-US", { style: "currency", currency: "USD" }));

function timeAgo(iso) {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

// Decision / status -> pill class and label.
const OUTCOME = {
  "Approve": ["approve", "Approved"],
  "Review": ["review", "Needs review"],
  "Return to vendor": ["return", "Returned to vendor"],
  "Reject": ["reject", "Rejected"],
};

function decisionPill(decision, severity, status) {
  if (status === "queued") return '<span class="pill">Queued</span>';
  if (status === "running" || !decision) return '<span class="pill running">Running</span>';
  if (decision === "Review" && severity === "high" && status !== "resolved")
    return '<span class="pill high">High-risk hold</span>';
  const [cls, label] = OUTCOME[decision] || ["", decision];
  const suffix = status === "resolved" ? " (by reviewer)" : "";
  return `<span class="pill ${cls}">${esc(label + suffix)}</span>`;
}

function toast(text) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

async function renderSidebar(active) {
  const aside = document.getElementById("sidebar");
  aside.innerHTML = `
    <div class="brand">
      <div class="brand-mark">${icon("logo", 18)}</div>
      <div><div class="brand-name">Invoice Agent</div><div class="brand-sub">Meridian · Accounts Payable</div></div>
    </div>
    <nav>
      <a href="/" class="${active === "dashboard" ? "active" : ""}">${icon("dashboard")} Dashboard
        <span class="nav-badge" id="nav-reviews" hidden></span></a>
      <a href="/run" class="${active === "run" ? "active" : ""}">${icon("run")} New run</a>
      <a href="/bulk" class="${active === "bulk" ? "active" : ""}">${icon("folder")} Bulk run</a>
      <a href="/reference" class="${active === "reference" ? "active" : ""}">${icon("reference")} Reference data</a>
    </nav>
    <div class="sidebar-foot" id="env"></div>`;
  try {
    const [cfg, m] = await Promise.all([api("/api/config"), api("/api/metrics")]);
    document.getElementById("env").innerHTML = `
      <div><b>Reader:</b> ${esc(cfg.llm_providers.join(" → ") || "no LLM key")}</div>
      <div><b>Mode:</b> ${esc(cfg.extraction_mode)} · <b>Policy</b> v${esc(cfg.policy_version)}</div>`;
    const badge = document.getElementById("nav-reviews");
    if (m.open_reviews) { badge.hidden = false; badge.textContent = `${m.open_reviews} to review`; }
  } catch (e) { /* sidebar info is optional */ }
}
