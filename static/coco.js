// Coco, Sid's digital cute pet: a ginger clay cat who lives in the sidebar.
//   By day she is awake (blinks, swishes her tail, her eyes follow the cursor); at night she sleeps.
//   She walks over and bats the day/night switch herself, says hello when hovered, can be fed and petted,
//   cheers when a file is uploaded, reacts to invoice decisions, and naps when the app is left alone.
// Needs app.js (icon helpers, theme(), setTheme(), sparkle(), confetti(), replay(), esc(), reducedMotion).

// ---------------------------------------------------------------- the two drawings

// Curled up (her resting pose), facing left.
const CAT = `<svg class="cat" viewBox="0 0 120 84" width="100" height="70" role="img" aria-label="Coco, Sid's digital cute pet">
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
    <ellipse class="blush" cx="25" cy="54.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.35"/>
    <ellipse class="blush" cx="51" cy="54.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.35"/>
    <path class="collar" d="M24 61.5 Q38 70.5 52 61.5" fill="none" stroke="#6a4cf5" stroke-width="3.8" stroke-linecap="round"/>
    <g class="tag"><circle cx="38" cy="69.5" r="3.3" fill="#ffc94d" stroke="#e39a00" stroke-width="1"/></g>
    <ellipse cx="38" cy="56.5" rx="9" ry="6" fill="#fff3e3"/>
    <ellipse class="mouth-open" cx="38" cy="59.2" rx="3.2" ry="2.6" fill="#9b3a4f"/>
    <path d="M35.4 52.6 h5.2 l-2.6 3 z" fill="#ff8fa6" stroke="#ff8fa6" stroke-width="1" stroke-linejoin="round"/>
    <path d="M38 55.8 q-2 3 -4.5 1.6 M38 55.8 q2 3 4.5 1.6" fill="none" stroke="#6b4a3a" stroke-width="1.3" stroke-linecap="round"/>
    <g stroke="#8a6a5a" stroke-opacity="0.45" stroke-width="1" stroke-linecap="round">
      <path d="M29 57 l-12 -2.5"/><path d="M29 59 l-12 1.8"/><path d="M47 57 l12 -2.5"/><path d="M47 59 l12 1.8"/></g>
    <g class="eyes-look"><g class="eyes-open"><ellipse cx="30" cy="47" rx="2.8" ry="3.6" fill="#3a2a35"/><ellipse cx="46" cy="47" rx="2.8" ry="3.6" fill="#3a2a35"/>
      <circle cx="31" cy="45.6" r="1" fill="#fff"/><circle cx="47" cy="45.6" r="1" fill="#fff"/></g></g>
    <g class="eyes-closed" fill="none" stroke="#3a2a35" stroke-width="2" stroke-linecap="round">
      <path d="M26.5 47 q3.5 3 7 0"/><path d="M42.5 47 q3.5 3 7 0"/></g>
    <g class="eyes-happy" fill="none" stroke="#3a2a35" stroke-width="2.2" stroke-linecap="round">
      <path d="M26.5 48.5 q3.5 -4.5 7 0"/><path d="M42.5 48.5 q3.5 -4.5 7 0"/></g>
  </g>
  <g class="zzz" style="fill:var(--violet)" font-family="Nunito, sans-serif" font-weight="900">
    <text x="58" y="30" font-size="10">z</text><text x="66" y="19" font-size="13">z</text><text x="75" y="7" font-size="16">z</text>
  </g>
</svg>`;

// Standing on four legs (for stretching, walking and batting the switch), facing right.
const WALKER = `<svg class="walker" viewBox="0 0 130 96" width="96" height="71" aria-hidden="true">
  <defs>
    <radialGradient id="w-fur" cx="0.4" cy="0.25" r="0.95">
      <stop offset="0" stop-color="#ffdcae"/><stop offset="0.55" stop-color="#f6a458"/><stop offset="1" stop-color="#d9702c"/>
    </radialGradient>
    <linearGradient id="w-leg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3a05a"/><stop offset="1" stop-color="#e2803c"/></linearGradient>
  </defs>
  <ellipse cx="64" cy="91" rx="42" ry="4" fill="#3a2230" opacity="0.14"/>
  <g class="w-tail"><path d="M26 48 C12 44 8 28 15 14" fill="none" stroke="#ec8c43" stroke-width="9" stroke-linecap="round"/>
    <circle cx="15" cy="14" r="4.6" fill="#fff1de"/></g>
  <g class="leg lb2"><rect x="42" y="56" width="9" height="31" rx="4.5" fill="#cf6a2a"/><ellipse cx="46.5" cy="87" rx="6" ry="3.4" fill="#f1d6ba"/></g>
  <g class="leg lf2"><rect x="80" y="56" width="9" height="31" rx="4.5" fill="#cf6a2a"/><ellipse cx="84.5" cy="87" rx="6" ry="3.4" fill="#f1d6ba"/></g>
  <g class="w-body">
    <path d="M22 52 C22 37 40 31 64 32 C88 33 104 39 104 53 C104 65 86 69 62 69 C40 69 22 66 22 52 Z" fill="url(#w-fur)"/>
    <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="4" stroke-linecap="round">
      <path d="M50 34 q-3 7 0 13"/><path d="M63 33 q-3 7 0 14"/><path d="M76 34 q-3 7 0 13"/></g>
    <ellipse cx="58" cy="40" rx="18" ry="4.5" fill="#fff" opacity="0.4"/>
  </g>
  <g class="leg lb"><rect x="30" y="56" width="10" height="32" rx="5" fill="url(#w-leg)"/><ellipse cx="35" cy="88" rx="6.5" ry="3.6" fill="#fff1de"/></g>
  <g class="leg lf"><rect x="88" y="56" width="10" height="32" rx="5" fill="url(#w-leg)"/><ellipse cx="93" cy="88" rx="6.5" ry="3.6" fill="#fff1de"/></g>
  <g class="w-head">
    <path d="M93 27 Q90 12 95 7 Q98 5 101 9 L108 21 Z" fill="url(#w-fur)"/>
    <path d="M96 22 Q94.5 14 97 11 L103 20 Z" fill="#ff9fb3" opacity="0.8"/>
    <path d="M110 20 L116 8 Q119 5 121 9 Q123 17 121 27 Z" fill="url(#w-fur)"/>
    <path d="M113 19 L117.5 11.5 Q119 10 119.5 12.5 L119 22 Z" fill="#ff9fb3" opacity="0.8"/>
    <ellipse cx="106" cy="35" rx="19" ry="16" fill="url(#w-fur)"/>
    <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="2.4" stroke-linecap="round">
      <path d="M103 21 v5"/><path d="M107 20.5 v6"/><path d="M111 21 v5"/></g>
    <ellipse cx="99" cy="26" rx="7" ry="3" fill="#fff" opacity="0.5"/>
    <ellipse cx="96" cy="41" rx="3.6" ry="2.2" fill="#ff8fa6" opacity="0.4"/><ellipse cx="118" cy="41" rx="3.6" ry="2.2" fill="#ff8fa6" opacity="0.4"/>
    <path d="M93 47 Q106 55 119 47" fill="none" stroke="#6a4cf5" stroke-width="3.6" stroke-linecap="round"/>
    <circle cx="106" cy="54.5" r="3.2" fill="#ffc94d" stroke="#e39a00" stroke-width="1"/>
    <ellipse cx="110" cy="43" rx="8.5" ry="5.8" fill="#fff3e3"/>
    <ellipse class="mouth-open" cx="110" cy="46" rx="3.4" ry="2.9" fill="#9b3a4f"/>
    <path d="M107.5 39.6 h5 l-2.5 2.8 z" fill="#ff8fa6" stroke="#ff8fa6" stroke-width="1" stroke-linejoin="round"/>
    <path d="M110 42.6 q-2 2.8 -4.3 1.5 M110 42.6 q2 2.8 4.3 1.5" fill="none" stroke="#6b4a3a" stroke-width="1.3" stroke-linecap="round"/>
    <g stroke="#8a6a5a" stroke-opacity="0.45" stroke-width="1" stroke-linecap="round">
      <path d="M102 44 l-11 -2"/><path d="M102 46 l-11 1.6"/><path d="M118 44 l10 -2"/><path d="M118 46 l10 1.6"/></g>
    <g class="eyes-open"><ellipse cx="101" cy="33.5" rx="2.7" ry="3.5" fill="#3a2a35"/><ellipse cx="115" cy="33.5" rx="2.7" ry="3.5" fill="#3a2a35"/>
      <circle cx="102" cy="32.2" r="1" fill="#fff"/><circle cx="116" cy="32.2" r="1" fill="#fff"/></g>
    <g class="eyes-closed" fill="none" stroke="#3a2a35" stroke-width="2" stroke-linecap="round">
      <path d="M97.5 33.5 q3.5 3 7 0"/><path d="M111.5 33.5 q3.5 3 7 0"/></g>
  </g>
</svg>`;

const FISH = `<svg viewBox="0 0 40 24" width="36" height="22" aria-hidden="true">
  <defs><radialGradient id="fish-fill" cx="0.35" cy="0.3" r="0.9">
    <stop offset="0" stop-color="#cfe8ff"/><stop offset="0.6" stop-color="#5aa2f5"/><stop offset="1" stop-color="#2f6fd6"/></radialGradient></defs>
  <path d="M27 12 L38 4.5 Q35.5 12 38 19.5 Z" fill="#4b8ff0"/>
  <path d="M3 12 C8 3 22 2 29 12 C22 22 8 21 3 12 Z" fill="url(#fish-fill)"/>
  <path d="M18 6.5 q2.4 5.5 0 11" fill="none" stroke="#2f6fd6" stroke-opacity="0.35" stroke-width="1.3"/>
  <ellipse cx="14" cy="8" rx="5.5" ry="1.8" fill="#fff" opacity="0.55"/>
  <circle cx="9.5" cy="11" r="1.9" fill="#1d2b4a"/><circle cx="10.1" cy="10.4" r="0.6" fill="#fff"/>
</svg>`;
const HAND = `<svg viewBox="0 0 48 46" width="50" height="48" aria-hidden="true">
  <defs><radialGradient id="hand-fill" cx="0.4" cy="0.3" r="0.95">
    <stop offset="0" stop-color="#ffe9dc"/><stop offset="0.6" stop-color="#f8c3a6"/><stop offset="1" stop-color="#e59b7c"/></radialGradient></defs>
  <rect x="9" y="17" width="8" height="21" rx="4" fill="url(#hand-fill)"/>
  <rect x="17" y="19" width="8" height="24" rx="4" fill="url(#hand-fill)"/>
  <rect x="25" y="18" width="8" height="23" rx="4" fill="url(#hand-fill)"/>
  <rect x="33" y="16" width="7.5" height="19" rx="3.75" fill="url(#hand-fill)"/>
  <rect x="2" y="12" width="9" height="16" rx="4.5" transform="rotate(-28 6.5 20)" fill="url(#hand-fill)"/>
  <rect x="8" y="5" width="33" height="23" rx="11" fill="url(#hand-fill)"/>
  <rect x="10" y="0" width="29" height="8" rx="4" fill="#a391ff"/>
  <ellipse cx="20" cy="12" rx="8" ry="3" fill="#fff" opacity="0.55"/>
</svg>`;
const HEART = '<svg viewBox="0 0 24 22" aria-hidden="true"><path d="M12 21C4 15 1 11 1 7a5.5 5.5 0 0 1 11-1 5.5 5.5 0 0 1 11 1c0 4-3 8-11 14z"/></svg>';
const PAW = '<svg viewBox="0 0 20 20" aria-hidden="true"><ellipse cx="10" cy="13.5" rx="5" ry="4.2"/><circle cx="4" cy="8" r="2.1"/><circle cx="8" cy="4.5" r="2.1"/><circle cx="12" cy="4.5" r="2.1"/><circle cx="16" cy="8" r="2.1"/></svg>';
const FISH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c3-5 10-6 14-2l5-4v12l-5-4c-4 4-11 3-14-2z"/><circle cx="7.5" cy="11" r="0.6" fill="currentColor"/></svg>';
const HEART_ICON = '<svg viewBox="0 0 24 22" fill="currentColor"><path d="M12 21C4 15 1 11 1 7a5.5 5.5 0 0 1 11-1 5.5 5.5 0 0 1 11 1c0 4-3 8-11 14z"/></svg>';

function cocoMarkup() {
  return `<div class="cat-corner">
    <div class="coco"><div class="bubble" aria-hidden="true"></div>${CAT}${WALKER}</div>
    <div class="cat-actions">
      <button class="cat-btn feed" title="Feed Coco">${FISH_ICON} Feed</button>
      <button class="cat-btn pet" title="Pet Coco">${HEART_ICON} Pet</button>
    </div>
  </div>`;
}

// ---------------------------------------------------------------- small helpers

let catBusy = false;
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const getCat = () => document.querySelector(".cat");
const cocoVisible = () => { const c = document.querySelector(".coco"); return !!(c && c.offsetParent); };

// A point in the curled cat's drawing (viewBox 120 x 84) in page coordinates.
function catPoint(cat, x, y) {
  const b = cat.getBoundingClientRect();
  return [b.left + (x / 120) * b.width, b.top + (y / 84) * b.height];
}

function flyer(html) {
  const el = document.createElement("div");
  el.className = "flyer";
  el.innerHTML = html;
  document.body.appendChild(el);
  return el;
}

function floatHearts(x, y, count = 3) {
  for (let i = 0; i < count; i++) {
    const h = document.createElement("span");
    h.className = "love";
    h.innerHTML = HEART;
    h.style.left = `${x + (Math.random() - 0.5) * 22}px`;
    h.style.top = `${y}px`;
    h.style.setProperty("--dx", `${(Math.random() - 0.5) * 56}px`);
    h.style.setProperty("--s", (0.7 + Math.random() * 0.6).toFixed(2));
    h.style.animationDelay = `${i * 130}ms`;
    document.body.appendChild(h);
    setTimeout(() => h.remove(), 2000);
  }
}

// Coco speaks in Sid's handwriting.
function floatWord(text, x, y) {
  const w = document.createElement("span");
  w.className = "cat-word";
  w.textContent = text;
  w.style.left = `${x}px`;
  w.style.top = `${y - 30}px`;
  document.body.appendChild(w);
  setTimeout(() => w.remove(), 2000);
}

function crumbs(x, y) {
  const colors = ["#ffd48a", "#f6a458", "#8cc0ff", "#fff1de", "#5aa2f5"];
  for (let i = 0; i < 12; i++) {
    const c = document.createElement("span");
    c.className = "confetti round crumb";
    c.style.left = `${x}px`;
    c.style.top = `${y}px`;
    c.style.background = colors[i % colors.length];
    c.style.setProperty("--dx", `${(Math.random() - 0.5) * 80}px`);
    c.style.setProperty("--up", `${-8 - Math.random() * 28}px`);
    c.style.setProperty("--dy", `${24 + Math.random() * 40}px`);
    c.style.setProperty("--rot", `${Math.random() * 360}deg`);
    document.body.appendChild(c);
    setTimeout(() => c.remove(), 1000);
  }
}

function setCatBusy(busy) {
  catBusy = busy;
  document.querySelectorAll(".cat-btn").forEach((b) => { b.disabled = busy; });
}

// Add a class for a while (restarting its animation if it is already there).
function pulseClass(el, cls, ms) {
  el.classList.remove(cls);
  void el.getBoundingClientRect();
  el.classList.add(cls);
  clearTimeout(el[`_${cls}`]);
  el[`_${cls}`] = setTimeout(() => el.classList.remove(cls), ms);
}

// ---------------------------------------------------------------- feed and pet

// Feed: a fish is tossed in a spinning arc; her eyes go wide, she catches it, chomps three times, gets a happy face
// and a round belly. At night she wakes for a midnight snack, then dozes straight back off.
function feedCat(button) {
  const cat = getCat();
  if (!cat || catBusy || !cocoVisible()) return;
  setCatBusy(true);
  hideBubble();
  const night = theme() === "night";
  cat.classList.remove("napping");
  cat.classList.add("alert");
  const [ex, ey] = catPoint(cat, 38, 57);
  const [hx, hy] = catPoint(cat, 44, 28);
  const eat = () => {
    cat.classList.add("eating");
    crumbs(ex, ey);
    setTimeout(() => {
      cat.classList.remove("eating");
      cat.classList.add("happy", "full");
      floatHearts(hx, hy, 4);
      floatWord(night ? "midnight snack!" : "nom nom!", hx + 18, hy);
    }, 950);
    setTimeout(() => { cat.classList.remove("happy", "full", "alert"); setCatBusy(false); }, 2700);
  };
  if (reducedMotion) { eat(); return; }
  const b = button.getBoundingClientRect();
  const sx = b.left + 14, sy = b.top + b.height / 2;
  const cx = (sx + ex) / 2 + 10, cy = Math.min(sy, ey) - 80;       // the top of the throw
  const fish = flyer(FISH);
  const frames = Array.from({ length: 21 }, (_, k) => {
    const t = k / 20, u = 1 - t;
    const x = u * u * sx + 2 * u * t * cx + t * t * ex;
    const y = u * u * sy + 2 * u * t * cy + t * t * ey;
    return { transform: `translate(${x - 18}px, ${y - 11}px) rotate(${-t * 400}deg) scale(${0.55 + Math.sin(t * Math.PI) * 0.55})`,
             opacity: t < 0.08 ? t / 0.08 : 1 };
  });
  fish.animate(frames, { duration: 900, easing: "cubic-bezier(0.3, 0.1, 0.55, 1)", fill: "forwards" }).finished
    .then(() => { fish.remove(); eat(); });
}

// Pet: a clay hand strokes her back twice; she leans in, squints happily, purrs and her tail curls.
// At night she is petted in her sleep: she smiles and keeps snoring.
function petCat() {
  const cat = getCat();
  if (!cat || catBusy || !cocoVisible()) return;
  setCatBusy(true);
  hideBubble();
  const night = theme() === "night";
  cat.classList.remove("napping");
  cat.classList.add("petted", "happy");
  const [hx, hy] = catPoint(cat, 44, 28);
  [350, 950, 1550].forEach((t) => setTimeout(() => floatHearts(hx, hy, 2), t));
  setTimeout(() => floatWord(night ? "purrr… zzz" : "purrr~", hx + 22, hy), 550);
  setTimeout(() => { cat.classList.remove("petted", "happy"); setCatBusy(false); }, 2400);
  if (reducedMotion) return;
  const [right, back] = catPoint(cat, 100, 33);
  const [left] = catPoint(cat, 64, 33);
  const at = (x, y, r = 0, s = 1) => `translate(${x - 25}px, ${y - 36}px) rotate(${r}deg) scale(${s})`;
  const hand = flyer(HAND);
  hand.animate([            // opacity on every frame: otherwise it would fade across the whole stroke
    { transform: at(right + 24, back - 60, 16, 0.8), opacity: 0 },
    { transform: at(right, back, 6), opacity: 1, offset: 0.16 },
    { transform: at(left, back + 3, -8), opacity: 1, offset: 0.36 },
    { transform: at(right, back, 6), opacity: 1, offset: 0.56 },
    { transform: at(left, back + 3, -8), opacity: 1, offset: 0.76 },
    { transform: at(left + 4, back - 6, -4), opacity: 1, offset: 0.84 },
    { transform: at(left + 10, back - 46, 10, 0.85), opacity: 0 },
  ], { duration: 2200, easing: "ease-in-out", fill: "forwards" }).finished.then(() => hand.remove());
}

// ---------------------------------------------------------------- "Hi, I'm Coco!"

// Letters bounce in one by one. At night she is asleep, so it is a dreamy thought bubble instead.
function cocoSay() {
  const coco = document.querySelector(".coco");
  const bubble = coco && coco.querySelector(".bubble");
  const cat = getCat();
  if (!bubble || catBusy || coco.classList.contains("away")) return;
  const night = theme() === "night";
  const parts = night
    ? [[["zzz… I'm ", ""], ["Coco", "name"], ["…", ""]], [["Sid's digital cute pet… zzz", ""]]]
    : [[["Hi, I'm ", ""], ["Coco", "name"], ["!", ""]], [["Sid's digital cute pet", ""]]];
  let i = 0;
  const line = (segments) => segments.map(([text, cls]) => [...text].map((ch) =>
    `<span class="ch ${cls}" style="--i:${i++}">${ch === " " ? "&nbsp;" : esc(ch)}</span>`).join("")).join("");
  bubble.className = `bubble${night ? " dream" : ""}`;
  bubble.innerHTML = `<div class="b-title">${line(parts[0])}</div><div class="b-sub">${line(parts[1])}</div>`;
  void bubble.offsetWidth;
  bubble.classList.add("show");
  cat.classList.remove("napping");
  cat.classList.add(night ? "dreaming" : "hello");
  if (!night) setTimeout(() => bubble.classList.contains("show") && sparkle(bubble.querySelector(".name"), 8), 420);
}

function hideBubble() {
  const bubble = document.querySelector(".coco .bubble");
  if (bubble) bubble.classList.remove("show");
  const cat = getCat();
  if (cat) cat.classList.remove("hello", "dreaming");
}

// ---------------------------------------------------------------- the walk to the switch

const PAW_REACH = 0.875;       // where her batting paw lands, as a fraction of the walker's width

function pawPrints(walker, facing) {
  const id = setInterval(() => {
    const foot = walker.querySelector(".lb").getBoundingClientRect();
    const p = document.createElement("span");
    p.className = "paw-print";
    p.innerHTML = PAW;
    p.style.left = `${foot.left + foot.width / 2}px`;
    p.style.top = `${foot.bottom - 3}px`;
    p.style.setProperty("--r", facing === "right" ? "90deg" : "-90deg");
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 1400);
  }, 230);
  return () => clearInterval(id);
}

function walk(walker, from, to, flipped) {
  const flip = flipped ? " scaleX(-1)" : "";
  walker.classList.add("walking");
  const stop = pawPrints(walker, flipped ? "left" : "right");
  return walker.animate(
    [{ transform: `translateX(${from}px)${flip}` }, { transform: `translateX(${to}px)${flip}` }],
    { duration: Math.max(500, Math.abs(to - from) * 8), easing: "cubic-bezier(0.45, 0.05, 0.55, 0.95)", fill: "forwards" },
  ).finished.then(() => { walker.classList.remove("walking"); stop(); });
}

function tapRing(x, y) {
  const ring = document.createElement("span");
  ring.className = "tap-ring";
  ring.style.left = `${x}px`;
  ring.style.top = `${y}px`;
  document.body.appendChild(ring);
  setTimeout(() => ring.remove(), 700);
}

// Clicking the switch: Coco wakes, stretches with a yawn, walks over leaving paw prints, bats the switch
// (that is what flips day and night), then walks home and curls up again.
async function cocoToggleTheme(toggle) {
  const knob = toggle.querySelector(".knob");
  const next = theme() === "night" ? "day" : "night";
  const coco = document.querySelector(".coco");
  const cat = getCat();
  const walker = coco && coco.querySelector(".walker");
  if (reducedMotion || catBusy || !walker || !cocoVisible()) { setTheme(next, knob); return; }
  setCatBusy(true);
  toggle.disabled = true;
  hideBubble();
  try {
    cat.classList.remove("napping");
    if (theme() === "night") { cat.classList.add("alert"); await wait(450); }     // wake up first
    coco.classList.add("away");
    walker.classList.add("on", "stretching");
    await wait(1250);
    walker.classList.remove("stretching");
    const k = knob.getBoundingClientRect();
    const w = walker.getBoundingClientRect();
    const dx = Math.round(k.left + k.width / 2 - (w.left + w.width * PAW_REACH));
    await walk(walker, 0, dx, false);
    walker.classList.add("tapping");
    await wait(300);                                   // the paw comes down on the knob
    tapRing(k.left + k.width / 2, k.top + k.height / 2);
    setTheme(next, knob, { cat: false });
    await wait(450);
    walker.classList.remove("tapping");
    await walker.animate(
      [{ transform: `translateX(${dx}px)` }, { transform: `translateX(${dx}px) scaleX(-1)` }],
      { duration: 280, easing: "ease-in-out", fill: "forwards" }).finished;           // turn around
    await walk(walker, dx, 0, true);
    walker.classList.remove("on");
    await wait(160);
    walker.getAnimations().forEach((a) => a.cancel());
    cat.classList.remove("alert");
    coco.classList.remove("away");
    pulseClass(cat, next === "night" ? "dozing" : "waking", 1400);
  } finally {
    toggle.disabled = false;
    setCatBusy(false);
  }
}

// ---------------------------------------------------------------- moods: uploads and decisions

function mood(cls, text, { hearts = 0, party = false, ms = 1600 } = {}) {
  const cat = getCat();
  if (!cat || !cocoVisible() || catBusy) return;
  hideBubble();
  cat.classList.remove("napping");
  cat.classList.add("alert");                 // she wakes up for news, even at night
  pulseClass(cat, cls, ms);
  if (party) pulseClass(cat, "jump", 950);
  const [hx, hy] = catPoint(cat, 44, 26);
  setTimeout(() => {
    if (hearts) floatHearts(hx, hy, hearts);
    if (text) floatWord(text, hx + 20, hy);
    if (party) confetti(cat, 18);
  }, 220);
  clearTimeout(cat._alert);
  cat._alert = setTimeout(() => cat.classList.remove("alert"), ms);
}

const coco = {
  celebrate: (text) => mood("happy", text, { hearts: 5, party: true }),
  curious(on) {
    const cat = getCat();
    if (!cat || !cocoVisible() || catBusy) return;
    if (on && !cat.classList.contains("tilt")) mood("tilt", "ooh, a file?", { ms: 60000 });
    if (!on) { cat.classList.remove("tilt", "alert"); }
  },
  react(outcome) {
    if (outcome === "Approve") return mood("happy", "purr-fect!", { hearts: 4, party: true });
    if (outcome === "Review") return mood("tilt", "hmm, take a look?");
    if (outcome === "Return to vendor") return mood("tilt", "back to sender!");
    if (outcome === "Reject") return mood("grumpy", "nope!");
  },
};

// Wait for a short celebration before leaving the page (uploads navigate away immediately otherwise).
function cocoParty(text) {
  if (reducedMotion || !cocoVisible()) return Promise.resolve();
  coco.celebrate(text);
  return wait(1150);
}

// ---------------------------------------------------------------- always-on life

// Her eyes follow the cursor.
function trackEyes() {
  let raf = 0, mx = 0, my = 0;
  addEventListener("pointermove", (e) => {
    mx = e.clientX; my = e.clientY;
    if (!raf) raf = requestAnimationFrame(() => {
      raf = 0;
      const cat = getCat();
      const look = cat && cat.querySelector(".eyes-look");
      if (!look) return;
      const [ex, ey] = catPoint(cat, 38, 47);
      const dx = mx - ex, dy = my - ey, d = Math.hypot(dx, dy) || 1;
      const k = Math.min(1, d / 160) * 1.9;
      look.style.transform = `translate(${((dx / d) * k).toFixed(2)}px, ${((dy / d) * k * 0.8).toFixed(2)}px)`;
    });
  }, { passive: true });
}

// Left alone for 45 s, she naps (even by day); any movement startles her awake.
function napWhenIdle() {
  let timer;
  const poke = () => {
    const cat = getCat();
    if (cat && cat.classList.contains("napping")) {
      cat.classList.remove("napping");
      pulseClass(cat, "waking", 900);
      const [hx, hy] = catPoint(cat, 44, 26);
      floatWord("!", hx + 10, hy);
    }
    clearTimeout(timer);
    timer = setTimeout(() => {
      const c = getCat();
      if (c && theme() === "day" && !catBusy && cocoVisible()) { hideBubble(); c.classList.add("napping"); }
    }, 45000);
  };
  ["pointermove", "pointerdown", "keydown", "wheel"].forEach((ev) => addEventListener(ev, poke, { passive: true }));
  poke();
}

// Dragging a file anywhere makes her curious.
function watchDrags() {
  let depth = 0;
  const hasFiles = (e) => e.dataTransfer && [...(e.dataTransfer.types || [])].includes("Files");
  addEventListener("dragenter", (e) => { if (hasFiles(e)) { depth++; coco.curious(true); } });
  addEventListener("dragleave", (e) => { if (hasFiles(e)) { depth = Math.max(0, depth - 1); if (!depth) coco.curious(false); } });
  addEventListener("drop", () => { depth = 0; coco.curious(false); });
}

let cocoAlive = false;

function wireCoco(aside, firstVisit) {
  const toggle = aside.querySelector(".theme-switch");
  toggle.addEventListener("click", () => cocoToggleTheme(toggle));
  const feed = aside.querySelector(".cat-btn.feed");
  feed.addEventListener("click", () => feedCat(feed));
  aside.querySelector(".cat-btn.pet").addEventListener("click", petCat);
  const cat = aside.querySelector(".cat");
  cat.addEventListener("mouseenter", cocoSay);
  cat.addEventListener("mouseleave", hideBubble);
  if (!cocoAlive) {                     // page-wide listeners, once
    cocoAlive = true;
    if (!reducedMotion) trackEyes();
    napWhenIdle();
    watchDrags();
  }
  if (firstVisit && !reducedMotion) {    // she introduces herself on the first visit
    setTimeout(() => { if (!cat.matches(":hover")) { cocoSay(); setTimeout(() => { if (!cat.matches(":hover")) hideBubble(); }, 3200); } }, 2600);
  }
}
