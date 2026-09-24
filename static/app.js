// Shared helpers for every page: sidebar, API calls, formatting, status pills, clay art and motion.

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
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6"/>',
  bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4M12 16h.01"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/>',
  external: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
};

function icon(name, size = 18) {
  // pathLength=100 lets CSS "draw" any icon stroke in the same time, whatever its real length
  const body = ICONS[name].replace(/<(path|circle|rect|ellipse) /g, '<$1 pathLength="100" ');
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor"
    stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}

// A puffy clay invoice with a badge: the brand mark, drop-zone art and empty-state illustration.
let artCount = 0;
const ART_BADGES = {
  doc: ["#8fe8bf", "#1f9d63", '<path d="M-8 0l5 5 10-10"/>'],
  upload: ["#b8adff", "#6c5ce7", '<path d="M0 8V-8M-7-1l7-7 7 7"/>'],
  folder: ["#ffd48a", "#e8940c", '<path d="M-9 7V-6h6l2 3h10V7z"/>'],
  mail: ["#9ccaff", "#2f7fea", '<rect x="-9" y="-6" width="18" height="13" rx="2"/><path d="M-9-5l9 7 9-7"/>'],
  empty: ["#d9c2ff", "#8a4de6", '<path d="M-7 0h14"/>'],
};

function clayArt(kind = "doc", size = 96) {
  const id = `ca${++artCount}`;
  const [light, dark, glyph] = ART_BADGES[kind] || ART_BADGES.doc;
  return `<svg class="clay-art" viewBox="0 0 120 120" width="${size}" height="${size}" aria-hidden="true">
    <defs>
      <linearGradient id="${id}p" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--paper-0)"/><stop offset="1" style="stop-color:var(--paper-1)"/></linearGradient>
      <radialGradient id="${id}h" cx="0.85" cy="0.95" r="0.8"><stop offset="0" stop-color="#6c5ce7" stop-opacity="0.35"/><stop offset="1" stop-color="#6c5ce7" stop-opacity="0"/></radialGradient>
      <radialGradient id="${id}b" cx="0.35" cy="0.3" r="0.85"><stop offset="0" stop-color="${light}"/><stop offset="1" stop-color="${dark}"/></radialGradient>
      <filter id="${id}s" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
    </defs>
    <ellipse cx="58" cy="112" rx="36" ry="5" fill="#5b4fd6" opacity="0.2" filter="url(#${id}s)"/>
    <g class="paper">
      <rect x="24" y="10" width="66" height="88" rx="20" fill="url(#${id}p)"/>
      <rect x="24" y="10" width="66" height="88" rx="20" fill="url(#${id}h)"/>
      <rect x="25.5" y="11.5" width="63" height="85" rx="18.5" fill="none" style="stroke:var(--paper-rim)" stroke-width="2.5" opacity="0.9"/>
      <rect x="37" y="30" width="30" height="8" rx="4" style="fill:var(--paper-line-1)"/>
      <rect x="37" y="45" width="40" height="8" rx="4" style="fill:var(--paper-line-2)"/>
      <rect x="37" y="60" width="24" height="8" rx="4" style="fill:var(--paper-line-2)"/>
      <ellipse cx="44" cy="19" rx="11" ry="3.5" style="fill:var(--paper-rim)"/>
    </g>
    <g transform="translate(86 86)">
      <g class="badge">
        <circle r="21" fill="url(#${id}b)"/>
        <ellipse cx="-7" cy="-10" rx="8" ry="4.5" fill="#fff" opacity="0.5"/>
        <g fill="none" stroke="#fff" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round">${glyph}</g>
      </g>
    </g>
  </svg>`;
}

function emptyState(text, kind = "empty") {
  return `<div class="empty">${clayArt(kind, 84)}${text}</div>`;
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

// Amounts are shown in the invoice's own currency, never converted (no currency printed = USD, our base currency).
const money = (v, currency) => {
  if (v === null || v === undefined || v === "") return "—";
  try {
    return Number(v).toLocaleString("en-US", { style: "currency", currency: currency || "USD" });
  } catch {
    return `${currency} ${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
};

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
  const suffix = status === "resolved" ? " · resolved" : "";
  return `<span class="pill ${cls}">${esc(label + suffix)}</span>`;
}

// ---------------------------------------------------------------- motion helpers

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Run after the browser has painted the current state, so a CSS transition has a "from" value.
function nextFrame(fn) { requestAnimationFrame(() => requestAnimationFrame(fn)); }

// Mark children to spring in one after another (first paint only, so refreshes don't flicker).
function stagger(parent, selector = ":scope > *") {
  parent.querySelectorAll(selector).forEach((el, i) => { el.classList.add("enter"); el.style.setProperty("--i", i); });
}

// Count a number up from its previous value.
function countUp(el, value, format = (v) => Math.round(v).toLocaleString()) {
  const to = Number(value) || 0;
  const from = el.dataset.v === undefined ? 0 : Number(el.dataset.v);
  el.dataset.v = to;
  if (reducedMotion || from === to) { el.textContent = format(to); return; }
  const start = performance.now();
  const duration = 900;
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    el.textContent = format(from + (to - from) * (1 - Math.pow(1 - t, 3)));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// A burst of clay confetti from an element (used when an invoice is approved live).
function confetti(fromEl, pieces = 42) {
  if (reducedMotion || !fromEl) return;
  const box = fromEl.getBoundingClientRect();
  const colors = ["#6fdcaa", "#a397ff", "#ffc766", "#8cc0ff", "#ff9a9a", "#cfa8ff"];
  for (let i = 0; i < pieces; i++) {
    const piece = document.createElement("span");
    piece.className = `confetti${i % 3 === 0 ? " round" : ""}`;
    piece.style.left = `${box.left + box.width / 2}px`;
    piece.style.top = `${box.top + box.height / 2}px`;
    piece.style.background = colors[i % colors.length];
    piece.style.setProperty("--dx", `${(Math.random() - 0.5) * 520}px`);
    piece.style.setProperty("--up", `${-120 - Math.random() * 180}px`);
    piece.style.setProperty("--dy", `${160 + Math.random() * 260}px`);
    piece.style.setProperty("--rot", `${(Math.random() - 0.5) * 900}deg`);
    piece.style.animationDelay = `${Math.random() * 120}ms`;
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 1900);
  }
}

// Restart a one-shot CSS animation class on an element.
function replay(el, cls) {
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
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
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 2400);
}

// ---------------------------------------------------------------- sidebar

const NAV = [
  ["dashboard", "/", "dashboard", "Dashboard"],
  ["run", "/run", "run", "New run"],
  ["bulk", "/bulk", "folder", "Bulk run"],
  ["inbox", "/inbox", "mail", "Email inbox"],
  ["reference", "/reference", "reference", "Reference data"],
];

// ---------------------------------------------------------------- brand: the tickd wordmark

const BRAND = "tickd";
const TICK_DOT = `<svg viewBox="0 0 24 24" aria-hidden="true">
  <defs><radialGradient id="tick-dot-fill" cx="0.35" cy="0.3" r="0.85">
    <stop offset="0" stop-color="#8fe8bf"/><stop offset="1" stop-color="#1f9d63"/></radialGradient></defs>
  <circle cx="12" cy="12" r="11" fill="url(#tick-dot-fill)"/>
  <ellipse cx="8.5" cy="7" rx="4.2" ry="2.3" fill="#fff" opacity="0.5"/>
  <path pathLength="100" d="M7 12.5l3.3 3.3L17 9" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

// Each letter is its own element so it can drop in, hop and change colour on its own beat.
// The i is a dotless ı: its dot is the tick badge, the logo inside the name.
function wordmark() {
  const letters = [...BRAND].map((ch, i) => `
    <span class="l" style="--i:${i}">${ch === "i" ? `<span class="in">ı</span><span class="tick-dot">${TICK_DOT}</span>` : `<span class="in">${ch}</span>`}</span>`).join("");
  return `<a class="wordmark" href="/" aria-label="${BRAND} home">${letters}
    <span class="tagline">every invoice, <b>ticked</b></span></a>`;
}

function wireWordmark(el) {
  let firstVisit = true;
  try { firstVisit = !sessionStorage.getItem("tickd-intro"); sessionStorage.setItem("tickd-intro", "1"); } catch { /* private mode */ }
  if (firstVisit && !reducedMotion) {          // the drop-in plays once per visit, not on every page change
    el.classList.add("intro");
    setTimeout(() => el.classList.remove("intro"), 2200);
  }
  let busy = false;
  el.addEventListener("mouseenter", () => {
    if (busy || reducedMotion) return;
    busy = true;
    el.classList.remove("party");
    void el.offsetWidth;
    el.classList.add("party");
    setTimeout(() => sparkle(el.querySelector(".tick-dot")), 600);     // at the top of the badge's leap
    setTimeout(() => { el.classList.remove("party"); busy = false; }, 1400);
  });
}

// A small radial burst of clay sparkles.
function sparkle(fromEl, pieces = 14) {
  if (reducedMotion || !fromEl) return;
  const box = fromEl.getBoundingClientRect();
  const colors = ["#6fdcaa", "#a397ff", "#ffc766", "#8cc0ff", "#ff9a9a", "#cfa8ff"];
  for (let i = 0; i < pieces; i++) {
    const s = document.createElement("span");
    s.className = `spark${i % 2 ? " round" : ""}`;
    const angle = (i / pieces) * Math.PI * 2 + Math.random() * 0.45;
    const distance = 28 + Math.random() * 36;
    s.style.left = `${box.left + box.width / 2}px`;
    s.style.top = `${box.top + box.height / 2}px`;
    s.style.background = colors[i % colors.length];
    s.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
    s.style.setProperty("--dy", `${Math.sin(angle) * distance}px`);
    document.body.appendChild(s);
    setTimeout(() => s.remove(), 850);
  }
}

// ---------------------------------------------------------------- day and night
// The theme is set before first paint by a one-line script in each page's <head>; this toggles and remembers it.

const theme = () => (document.documentElement.dataset.theme === "night" ? "night" : "day");

function themeSwitch() {
  return `<button class="theme-switch" role="switch" aria-checked="${theme() === "night"}" aria-label="Night mode" title="Night mode">
    <span class="track"><span class="night-sky"></span>
      <span class="stars"><i></i><i></i><i></i><i></i><i></i></span>
      <span class="clouds"><i></i><i></i></span></span>
    <span class="knob"><i></i><i></i><i></i></span>
  </button>`;
}

// Night spreads out from the switch as a growing circle (View Transitions), and the cat reacts.
function setTheme(next, origin) {
  const cat = document.querySelector(".cat");
  if (cat && !reducedMotion) {
    cat.classList.remove("waking", "dozing");
    void cat.getBoundingClientRect();
    cat.classList.add(next === "night" ? "dozing" : "waking");
    setTimeout(() => cat.classList.remove("waking", "dozing"), 1400);
    if (next === "day") setTimeout(() => sparkle(cat.querySelector(".cat-head"), 9), 330);
  }
  const apply = () => {
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("tickd-theme", next); } catch { /* private mode */ }
    document.querySelectorAll(".theme-switch").forEach((s) => s.setAttribute("aria-checked", String(next === "night")));
  };
  if (!document.startViewTransition || reducedMotion || !origin) { apply(); return; }
  const box = origin.getBoundingClientRect();
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const transition = document.startViewTransition(apply);
  transition.ready.then(() => {
    document.documentElement.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
      { duration: 800, easing: "cubic-bezier(0.65, 0, 0.35, 1)", pseudoElement: "::view-transition-new(root)" });
  }).catch(() => { /* a skipped transition still applies the theme */ });
  transition.finished.catch(() => {});
}

// The tickd cat: a ginger clay cat, curled up. Awake by day (blinks, swishes its tail, twitches an ear);
// at night its eyes close, its head droops onto its paws, its breathing slows and z's float up. Hover: a heart.
const CAT = `<svg class="cat" viewBox="0 0 120 84" width="100" height="70" role="img" aria-label="The tickd cat">
  <defs>
    <radialGradient id="cat-fur" cx="0.35" cy="0.28" r="0.95">
      <stop offset="0" stop-color="#ffdcae"/><stop offset="0.55" stop-color="#f6a458"/><stop offset="1" stop-color="#d9702c"/>
    </radialGradient>
    <linearGradient id="cat-tail-fur" x1="1" y1="0" x2="0" y2="0">
      <stop offset="0" stop-color="#e3813a"/><stop offset="1" stop-color="#f8b673"/>
    </linearGradient>
  </defs>
  <ellipse cx="64" cy="79.5" rx="46" ry="4.5" fill="#3a2230" opacity="0.14"/>
  <g class="cat-tail">
    <path d="M104 64 C118 76 98 82 74 81 C64 80.6 58 80 52 79" fill="none" stroke="url(#cat-tail-fur)" stroke-width="9" stroke-linecap="round"/>
    <circle cx="52" cy="79" r="4.6" fill="#fff1de"/>
  </g>
  <g class="cat-body">
    <path d="M28 70 C20 46 46 24 77 26 C103 28 117 46 111 64 C107 74 38 78 28 70 Z" fill="url(#cat-fur)"/>
    <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="4" stroke-linecap="round">
      <path d="M73 29 q5 7 1 14"/><path d="M87 31 q5 7 0 14"/><path d="M100 38 q4 7 -1 13"/>
    </g>
    <ellipse cx="66" cy="36" rx="17" ry="5" fill="#fff" opacity="0.4" transform="rotate(-8 66 36)"/>
  </g>
  <ellipse cx="30" cy="74.5" rx="7" ry="4.5" fill="#fff1de"/>
  <ellipse cx="43" cy="76.5" rx="7" ry="4.5" fill="#fff1de"/>
  <g class="cat-head">
    <g class="ear-l"><path d="M21 42 Q17 27 21 21 Q24 18 28 22 L37 32 Z" fill="url(#cat-fur)"/>
      <path d="M23.5 37 Q21.5 29 24 25 L32 32 Z" fill="#ff9fb3" opacity="0.8"/></g>
    <g class="ear-r"><path d="M39 32 L48 21 Q52 17 55 21 Q58 29 55 42 Z" fill="url(#cat-fur)"/>
      <path d="M43.5 31.5 L50 24.5 Q52 23 52.5 26 L52.5 37 Z" fill="#ff9fb3" opacity="0.8"/></g>
    <ellipse cx="38" cy="49" rx="20" ry="17" fill="url(#cat-fur)"/>
    <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="2.4" stroke-linecap="round">
      <path d="M34 34.5 v5"/><path d="M39 33.5 v6"/><path d="M44 34.5 v5"/></g>
    <ellipse cx="30" cy="39.5" rx="8" ry="3.4" fill="#fff" opacity="0.5"/>
    <ellipse cx="25" cy="54.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.35"/>
    <ellipse cx="51" cy="54.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.35"/>
    <ellipse cx="38" cy="56.5" rx="9" ry="6" fill="#fff3e3"/>
    <path d="M35.4 52.6 h5.2 l-2.6 3 z" fill="#ff8fa6" stroke="#ff8fa6" stroke-width="1" stroke-linejoin="round"/>
    <path d="M38 55.8 q-2 3 -4.5 1.6 M38 55.8 q2 3 4.5 1.6" fill="none" stroke="#6b4a3a" stroke-width="1.3" stroke-linecap="round"/>
    <g stroke="#8a6a5a" stroke-opacity="0.45" stroke-width="1" stroke-linecap="round">
      <path d="M29 57 l-12 -2.5"/><path d="M29 59 l-12 1.8"/><path d="M47 57 l12 -2.5"/><path d="M47 59 l12 1.8"/></g>
    <g class="eyes-open"><ellipse cx="30" cy="47" rx="2.8" ry="3.6" fill="#3a2a35"/><ellipse cx="46" cy="47" rx="2.8" ry="3.6" fill="#3a2a35"/>
      <circle cx="31" cy="45.6" r="1" fill="#fff"/><circle cx="47" cy="45.6" r="1" fill="#fff"/></g>
    <g class="eyes-closed" fill="none" stroke="#3a2a35" stroke-width="2" stroke-linecap="round">
      <path d="M26.5 47 q3.5 3 7 0"/><path d="M42.5 47 q3.5 3 7 0"/></g>
  </g>
  <g class="zzz" style="fill:var(--violet)" font-family="Nunito, sans-serif" font-weight="900">
    <text x="58" y="30" font-size="10">z</text><text x="66" y="19" font-size="13">z</text><text x="75" y="7" font-size="16">z</text>
  </g>
  <path class="heart" d="M62 26 C54 20 54 13 59 13 C61 13 62 15 62 16 C62 15 63 13 65 13 C70 13 70 20 62 26 Z" fill="#ff7a9a"/>
</svg>`;

async function renderSidebar(active) {
  if (!document.querySelector(".bg")) {
    const stars = Array.from({ length: 30 }, () => `<i class="${Math.random() < 0.2 ? "big" : ""}" style="left:${
      (Math.random() * 100).toFixed(1)}%;top:${(Math.random() * 100).toFixed(1)}%;animation-delay:${(Math.random() * 3.6).toFixed(2)}s"></i>`).join("");
    document.body.insertAdjacentHTML("afterbegin", `<div class="bg"><span></span><span></span><span></span>${stars}</div>`);
  }
  const aside = document.getElementById("sidebar");
  aside.innerHTML = `
    ${wordmark()}
    <nav>${NAV.map(([key, href, ico, label]) => `
      <a href="${href}" class="${active === key ? "active" : ""}">${icon(ico, 20)} ${label}
        ${key === "dashboard" ? '<span class="nav-badge" id="nav-reviews" title="Open reviews" hidden></span>' : ""}</a>`).join("")}
    </nav>
    <div class="sidebar-foot">${CAT}${themeSwitch()}</div>`;
  wireWordmark(aside.querySelector(".wordmark"));
  const toggle = aside.querySelector(".theme-switch");
  toggle.addEventListener("click", () => setTheme(theme() === "night" ? "day" : "night", toggle.querySelector(".knob")));
  try {
    const m = await api("/api/metrics");
    const badge = document.getElementById("nav-reviews");
    if (m.open_reviews) { badge.hidden = false; badge.textContent = m.open_reviews; }
  } catch (e) { /* the badge is optional */ }
}
