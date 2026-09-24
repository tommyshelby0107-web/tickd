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

// Standing Coco is a rig: drawn in her own coordinates (x = forward, y up is negative, ground at y = 0) and posed
// every frame by rigDraw(). Same fur, same face and collar as the curled Coco, so she visibly gets up.
const RIG_SVG = `<svg class="rig" aria-hidden="true">
  <defs>
    <radialGradient id="rig-fur" cx="0.35" cy="0.28" r="0.95">
      <stop offset="0" stop-color="#ffdcae"/><stop offset="0.55" stop-color="#f6a458"/><stop offset="1" stop-color="#d9702c"/>
    </radialGradient>
  </defs>
  <ellipse class="r-shadow" rx="32" ry="4" fill="#3a2230" opacity="0.15"/>
  <g class="r-root">
    <path class="r-leg" data-leg="hf" fill="none" stroke="#d27330" stroke-width="9.5" stroke-linecap="round" stroke-linejoin="round"/>
    <ellipse class="r-paw" data-leg="hf" rx="5.6" ry="3.3" fill="#f1d6ba"/>
    <path class="r-leg" data-leg="ff" fill="none" stroke="#d27330" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
    <ellipse class="r-paw" data-leg="ff" rx="5.4" ry="3.2" fill="#f1d6ba"/>
    <path class="r-tail" fill="none" stroke="#ea8a42" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>
    <path class="r-tail-hi" fill="none" stroke="#fbc088" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
    <circle class="r-tip" r="4.4" fill="#fff1de"/>
    <g class="r-body">
      <path d="M-35 -30 C-35 -47 -16 -51 3 -49 C23 -48 35 -45 35 -30 C35 -17 21 -14 0 -14 C-21 -14 -35 -16 -35 -30 Z" fill="url(#rig-fur)"/>
      <ellipse cx="-19" cy="-25" rx="12" ry="9" fill="#d9702c" opacity="0.28"/>
      <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="4" stroke-linecap="round">
        <path d="M-13 -48 q-3 7 0 12"/><path d="M-1 -49 q-3 7 0 13"/><path d="M11 -48 q-3 7 0 12"/></g>
      <ellipse cx="-4" cy="-42" rx="18" ry="4.5" fill="#fff" opacity="0.4"/>
    </g>
    <path class="r-leg" data-leg="hn" fill="none" stroke="#f09a52" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
    <ellipse class="r-paw" data-leg="hn" rx="6.2" ry="3.6" fill="#fff1de"/>
    <path class="r-leg" data-leg="fn" fill="none" stroke="#f09a52" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
    <ellipse class="r-paw" data-leg="fn" rx="6" ry="3.5" fill="#fff1de"/>
    <g class="r-head">
      <g class="r-ear-l"><path d="M-17 -7 Q-21 -22 -17 -28 Q-14 -31 -10 -27 L-1 -17 Z" fill="url(#rig-fur)"/>
        <path d="M-14.5 -12 Q-16.5 -20 -14 -24 L-6 -17 Z" fill="#ff9fb3" opacity="0.8"/></g>
      <g class="r-ear-r"><path d="M1 -17 L10 -28 Q14 -32 17 -28 Q20 -20 17 -7 Z" fill="url(#rig-fur)"/>
        <path d="M5.5 -17.5 L12 -24.5 Q14 -26 14.5 -23 L14.5 -12 Z" fill="#ff9fb3" opacity="0.8"/></g>
      <ellipse rx="20" ry="17" fill="url(#rig-fur)"/>
      <g fill="none" stroke="#c35f1e" stroke-opacity="0.45" stroke-width="2.4" stroke-linecap="round">
        <path d="M-4 -14.5 v5"/><path d="M1 -15.5 v6"/><path d="M6 -14.5 v5"/></g>
      <ellipse cx="-8" cy="-9.5" rx="8" ry="3.4" fill="#fff" opacity="0.5"/>
      <ellipse cx="-11" cy="5.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.4"/>
      <ellipse cx="15" cy="5.5" rx="4" ry="2.4" fill="#ff8fa6" opacity="0.4"/>
      <path d="M-13 12.5 Q1 21.5 15 12.5" fill="none" stroke="#6a4cf5" stroke-width="3.8" stroke-linecap="round"/>
      <g class="r-tag"><circle cx="1" cy="20.5" r="3.3" fill="#ffc94d" stroke="#e39a00" stroke-width="1"/></g>
      <ellipse cx="2" cy="7.5" rx="9" ry="6" fill="#fff3e3"/>
      <ellipse class="r-mouth" cx="2" cy="10.2" rx="3.2" ry="2.6" fill="#9b3a4f" opacity="0"/>
      <path d="M-0.6 3.6 h5.2 l-2.6 3 z" fill="#ff8fa6" stroke="#ff8fa6" stroke-width="1" stroke-linejoin="round"/>
      <path d="M2 6.8 q-2 3 -4.5 1.6 M2 6.8 q2 3 4.5 1.6" fill="none" stroke="#6b4a3a" stroke-width="1.3" stroke-linecap="round"/>
      <g stroke="#8a6a5a" stroke-opacity="0.45" stroke-width="1" stroke-linecap="round">
        <path d="M-7 8 l-12 -2.5"/><path d="M-7 10 l-12 1.8"/><path d="M11 8 l12 -2.5"/><path d="M11 10 l12 1.8"/></g>
      <g class="r-eyes"><ellipse cx="-5.5" cy="-2" rx="2.8" ry="3.6" fill="#3a2a35"/><ellipse cx="10.5" cy="-2" rx="2.8" ry="3.6" fill="#3a2a35"/>
        <circle cx="-4.5" cy="-3.4" r="1" fill="#fff"/><circle cx="11.5" cy="-3.4" r="1" fill="#fff"/></g>
      <g class="r-eyes-closed" fill="none" stroke="#3a2a35" stroke-width="2" stroke-linecap="round" opacity="0">
        <path d="M-9.5 -2 q3.5 3 7 0"/><path d="M6.5 -2 q3.5 3 7 0"/></g>
    </g>
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

// The curled cat and her buttons, plus the rig (standing Coco), which spans the whole sidebar foot so she can
// walk across it to the switch.
function cocoMarkup() {
  return `<div class="cat-corner">
    <div class="coco"><div class="bubble" aria-hidden="true"></div>${CAT}</div>
    <div class="cat-actions">
      <button class="cat-btn feed" title="Feed Coco">${FISH_ICON} Feed</button>
      <button class="cat-btn pet" title="Pet Coco">${HEART_ICON} Pet</button>
    </div>
  </div>${RIG_SVG}`;
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

// ---------------------------------------------------------------- the walking rig
// Procedural animation, the way game characters walk:
//   - four two-bone legs solved with inverse kinematics (hind legs bend back at the hock, front legs at the wrist)
//   - a lateral-sequence cat gait (left hind, left front, right hind, right front). Each foot plants and stays put
//     while the body passes over it, then lifts in an arc. The step phase follows distance walked, not time,
//     so planted feet never slide, however the speed eases in and out.
//   - secondary motion: the spine bobs on every footfall, the head stays steadier and nods, the tail waves as a
//     chain, the ears and collar tag bounce.
//   - poses are parameters on the same rig: lie (getting up / lying down), stretch (paws forward, rump up, yawn),
//     bat (a paw reaches out and taps the switch), turn (a quick hop-turn).

const GAIT = { stride: 15, duty: 0.6 };
const PIVOT = [-18, -24];                  // the spine pitches around the hips
const LEGS = [                             // hip, rest foot x, tucked foot x (lying), gait offset, bone lengths
  { id: "hf", hip: [-15, -25], rest: -15, tuck: -9, off: 0.5, a: 12.5, b: 13, lift: 5, bend: 1 },
  { id: "ff", hip: [19, -26], rest: 20, tuck: 27, off: 0.75, a: 12, b: 13.5, lift: 6, bend: -1 },
  { id: "hn", hip: [-19, -24], rest: -19, tuck: -12, off: 0, a: 12.5, b: 13, lift: 5, bend: 1 },
  { id: "fn", hip: [15, -25], rest: 16, tuck: 23, off: 0.25, a: 12, b: 13.5, lift: 6, bend: -1 },
];
const R = {};                              // the rig's state; tweens change it, rigDraw() renders it
let rigEls = null;
let rigRaf = 0;

const clamp01 = (v) => Math.max(0, Math.min(1, v));
const lerp = (a, b, k) => a + (b - a) * k;
const frac = (v) => v - Math.floor(v);
const ease = {
  linear: (k) => k,
  inOut: (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2),
  inOutSine: (k) => -(Math.cos(Math.PI * k) - 1) / 2,
  out: (k) => 1 - Math.pow(1 - k, 3),
  in: (k) => k * k * k,
  outBack: (k) => 1 + 2.2 * Math.pow(k - 1, 3) + 1.2 * Math.pow(k - 1, 2),
};

function tween(ms, fn, curve = ease.inOut) {
  return new Promise((resolve) => {
    const start = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - start) / ms);
      fn(curve(k), k);
      if (k < 1) requestAnimationFrame(step); else resolve();
    };
    requestAnimationFrame(step);
  });
}

// Two-bone IK: where the knee goes so the paw reaches (fx, fy). Out of reach: the leg points straight at it.
function ik(hx, hy, fx, fy, a, b, bend) {
  let dx = fx - hx, dy = fy - hy;
  let d = Math.hypot(dx, dy) || 0.001;
  const maxD = a + b - 0.05;
  if (d > maxD) { fx = hx + (dx / d) * maxD; fy = hy + (dy / d) * maxD; dx = fx - hx; dy = fy - hy; d = maxD; }
  d = Math.max(d, Math.abs(a - b) + 1);
  const alpha = Math.acos(Math.max(-1, Math.min(1, (a * a + d * d - b * b) / (2 * a * d))));
  const angle = Math.atan2(dy, dx) + bend * alpha;
  return { kx: hx + a * Math.cos(angle), ky: hy + a * Math.sin(angle), fx, fy };
}

// Where a foot is, relative to its rest spot, at a point of its step cycle.
function gaitOffset(p) {
  if (p < GAIT.duty) return { dx: GAIT.stride / 2 - (p / GAIT.duty) * GAIT.stride, lift: 0 };
  const q = (p - GAIT.duty) / (1 - GAIT.duty);
  return { dx: -GAIT.stride / 2 + q * q * (3 - 2 * q) * GAIT.stride, lift: Math.sin(Math.PI * q) };
}

function rigDraw(now) {
  const e = rigEls;
  const t = now / 1000;
  const phase = R.dist / (GAIT.stride / GAIT.duty);
  const bob = R.walk * 1.8 * (0.5 - 0.5 * Math.cos(4 * Math.PI * phase));
  const pitch = R.stretch * 13 + R.lean + R.shake;
  const dy = R.lie * 13 - bob - R.stretch * 1.5;
  const rad = (pitch * Math.PI) / 180, c = Math.cos(rad), s = Math.sin(rad);
  const T = (x, y) => {
    const px = x - PIVOT[0], py = y - PIVOT[1];
    return [PIVOT[0] + px * c - py * s, PIVOT[1] + px * s + py * c + dy];
  };
  e.root.setAttribute("transform", `translate(${R.x.toFixed(2)} ${(R.ground + R.hop).toFixed(2)}) scale(${R.flip.toFixed(3)} ${R.squash.toFixed(3)})`);
  e.body.setAttribute("transform", `translate(0 ${dy.toFixed(2)}) rotate(${pitch.toFixed(2)} ${PIVOT[0]} ${PIVOT[1]})`);
  e.shadow.setAttribute("cx", R.x.toFixed(2));
  e.shadow.setAttribute("cy", (R.ground + 1.5).toFixed(2));
  e.shadow.setAttribute("rx", (32 * (1 + R.hop / 40)).toFixed(2));

  const legAlpha = 1 - clamp01((R.lie - 0.45) / 0.5);          // legs fold away under her when she lies down
  for (const leg of LEGS) {
    const [hx, hy] = T(leg.hip[0], leg.hip[1]);
    const p = frac(phase + leg.off);
    const g = gaitOffset(p);
    let fx = leg.rest + R.walk * g.dx + (leg.id[0] === "f" ? 16 : -2) * R.stretch;
    let fy = -R.walk * g.lift * leg.lift;
    fx = lerp(fx, leg.tuck, clamp01(R.lie));
    fy = lerp(fy, 0, clamp01(R.lie));
    if (leg.id === "fn" && R.bat) [fx, fy] = R.bat;
    const k = ik(hx, hy, fx, fy, leg.a, leg.b, leg.bend);
    const el = e.legs[leg.id];
    el.leg.setAttribute("d", `M${hx.toFixed(2)} ${hy.toFixed(2)} L${k.kx.toFixed(2)} ${k.ky.toFixed(2)} L${k.fx.toFixed(2)} ${k.fy.toFixed(2)}`);
    el.leg.setAttribute("opacity", legAlpha.toFixed(2));
    el.paw.setAttribute("cx", (k.fx + 1.5).toFixed(2));
    el.paw.setAttribute("cy", (k.fy - 1.4).toFixed(2));
    // a paw print where each near foot touches down
    if (leg.id[1] === "n" && R.walk > 0.6 && leg.prev !== undefined && p < leg.prev) {
      pawPrintAt(R.x + R.flip * k.fx, R.ground, R.flip > 0 ? 90 : -90);
    }
    leg.prev = p;
  }

  // head: steadier than the body, with a small nod on each footfall
  const [nx, ny] = T(34, -50);
  const hx = nx + R.stretch * 4;
  const hy = ny + bob * 0.55 + R.stretch * 8 + R.lie * 2;
  const nod = R.walk * 2.2 * Math.sin(4 * Math.PI * phase + 0.9) + R.stretch * 9 + R.headDown;
  e.head.setAttribute("transform", `translate(${hx.toFixed(2)} ${hy.toFixed(2)}) rotate(${nod.toFixed(2)})`);
  const flick = R.walk * 5 * Math.sin(4 * Math.PI * phase - 0.6) + (t % 5.3 < 0.18 ? 12 : 0);
  e.earL.setAttribute("transform", `rotate(${(-flick * 0.6).toFixed(2)} -9 -17)`);
  e.earR.setAttribute("transform", `rotate(${flick.toFixed(2)} 9 -17)`);
  e.tag.setAttribute("transform", `rotate(${(R.walk * 18 * Math.sin(4 * Math.PI * phase - 1.4) + 3 * Math.sin(t * 2.3)).toFixed(2)} 1 17)`);
  const blink = t % 3.7 < 0.13;
  const closed = R.yawn > 0.5 || blink;
  e.eyes.setAttribute("opacity", closed ? 0 : 1);
  e.eyesClosed.setAttribute("opacity", closed ? 1 : 0);
  e.mouth.setAttribute("opacity", clamp01(R.yawn * 1.5).toFixed(2));

  // tail: a chain curled like a question mark, with a wave travelling to the tip
  let [px, py] = T(-31, -37);
  const pts = [[px, py]];
  const speed = R.walk > 0.1 ? 7 : 3.2;
  for (let i = 0; i < 8; i++) {
    const rest = -118 + i * 13, up = -96 + i * 2, down = -190 - i * 22;    // lying: curled down round her rump
    const a = lerp(lerp(rest, up, R.stretch), down, clamp01(R.lie))
      + (3 + i * 2.2) * Math.sin(t * speed - i * 0.55) * (1 - clamp01(R.lie) * 0.7);
    px += 5.2 * Math.cos((a * Math.PI) / 180);
    py += 5.2 * Math.sin((a * Math.PI) / 180);
    pts.push([px, py]);
  }
  let d = `M${pts[0][0].toFixed(2)} ${pts[0][1].toFixed(2)}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
    d += ` Q${pts[i][0].toFixed(2)} ${pts[i][1].toFixed(2)} ${mx.toFixed(2)} ${my.toFixed(2)}`;
  }
  const tip = pts[pts.length - 1];
  d += ` L${tip[0].toFixed(2)} ${tip[1].toFixed(2)}`;
  e.tail.setAttribute("d", d);
  e.tailHi.setAttribute("d", d);
  e.tip.setAttribute("cx", tip[0].toFixed(2));
  e.tip.setAttribute("cy", tip[1].toFixed(2));
}

function pawPrintAt(x, y, rotation) {
  const box = rigEls.svg.getBoundingClientRect();
  const p = document.createElement("span");
  p.className = "paw-print";
  p.innerHTML = PAW;
  p.style.left = `${box.left + x}px`;
  p.style.top = `${box.top + y + 1}px`;
  p.style.setProperty("--r", `${rotation}deg`);
  document.body.appendChild(p);
  setTimeout(() => p.remove(), 1500);
}

function rigLoop(now) {
  rigDraw(now);
  rigRaf = requestAnimationFrame(rigLoop);
}

// Swap the curled cat for the rig, lying in the same spot, facing the same way (left).
function rigStart() {
  const svg = document.querySelector(".rig");
  if (!rigEls) {
    const q = (sel) => svg.querySelector(sel);
    rigEls = {
      svg, root: q(".r-root"), body: q(".r-body"), head: q(".r-head"), shadow: q(".r-shadow"), earL: q(".r-ear-l"),
      earR: q(".r-ear-r"), tag: q(".r-tag"), eyes: q(".r-eyes"), eyesClosed: q(".r-eyes-closed"), mouth: q(".r-mouth"),
      tail: q(".r-tail"), tailHi: q(".r-tail-hi"), tip: q(".r-tip"), legs: {},
    };
    for (const leg of LEGS) rigEls.legs[leg.id] = { leg: q(`.r-leg[data-leg="${leg.id}"]`), paw: q(`.r-paw[data-leg="${leg.id}"]`) };
  }
  const box = svg.getBoundingClientRect();
  const cat = getCat().getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${box.width.toFixed(1)} ${box.height.toFixed(1)}`);
  Object.assign(R, {
    ground: cat.top + cat.height * 0.95 - box.top, home: cat.left + cat.width * 0.62 - box.left,
    flip: -1, hop: 0, squash: 1, dist: 0, walk: 0, lie: 1, stretch: 0, yawn: 0, lean: 0, shake: 0, headDown: 0, bat: null,
  });
  R.x = R.home;
  LEGS.forEach((leg) => { delete leg.prev; });
  rigDraw(performance.now());
  svg.classList.add("on");
  document.querySelector(".coco").classList.add("away");
  cancelAnimationFrame(rigRaf);
  rigRaf = requestAnimationFrame(rigLoop);
}

function rigStop() {
  rigEls.svg.classList.remove("on");
  document.querySelector(".coco").classList.remove("away");
  setTimeout(() => cancelAnimationFrame(rigRaf), 250);
}

async function rigTurn(dir) {
  const from = R.flip;
  await tween(300, (k, raw) => {
    R.hop = -9 * Math.sin(Math.PI * raw);
    const f = lerp(from, dir, k);
    R.flip = Math.abs(f) < 0.1 ? 0.1 * Math.sign(f || dir) : f;          // never exactly edge-on
    R.squash = 1 + 0.08 * Math.sin(Math.PI * raw);
  });
  R.flip = dir;
  R.hop = 0;
  await tween(150, (k, raw) => { R.squash = 1 - 0.1 * Math.sin(Math.PI * raw); }, ease.linear);
  R.squash = 1;
}

async function rigWalkTo(x) {
  const dir = x > R.x ? 1 : -1;
  if (R.flip !== dir) await rigTurn(dir);
  const x0 = R.x;
  const distance = Math.abs(x - x0);
  await tween(300 + distance * 10.5, (k, raw) => {
    const nx = x0 + (x - x0) * k;
    R.dist += Math.abs(nx - R.x);
    R.x = nx;
    R.walk = Math.min(1, raw / 0.16, (1 - raw) / 0.16);
  }, ease.inOutSine);
  R.walk = 0;
}

async function rigStretch() {
  await tween(460, (k) => { R.stretch = k; R.yawn = clamp01((k - 0.55) / 0.45); });
  await wait(380);
  await tween(400, (k) => { R.stretch = 1 - k; R.yawn = clamp01(1 - k * 2); });
  await tween(300, (k, raw) => { R.shake = Math.sin(raw * Math.PI * 6) * 3.5 * (1 - raw); }, ease.linear);
  R.shake = 0;
}

// A paw goes up, then comes down on the target (page coordinates); onHit fires on contact.
async function rigBat(targetX, targetY, onHit) {
  const box = rigEls.svg.getBoundingClientRect();
  const lx = (targetX - box.left - R.x) / R.flip;
  const ly = targetY - box.top - R.ground;
  const rest = [LEGS[3].rest, 0], up = [LEGS[3].rest + 9, -18], hit = [lx, ly];
  let fired = false;
  const mix = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k)];
  await tween(760, (k, raw) => {
    if (raw < 0.34) R.bat = mix(rest, up, ease.out(raw / 0.34));
    else if (raw < 0.47) R.bat = mix(up, hit, ease.in((raw - 0.34) / 0.13));
    else if (raw < 0.7) R.bat = hit;
    else R.bat = mix(hit, rest, ease.inOut((raw - 0.7) / 0.3));
    const bell = Math.sin(Math.PI * Math.min(1, raw / 0.88));
    R.lean = 11 * bell;
    R.headDown = 12 * bell;
    if (!fired && raw >= 0.47) { fired = true; onHit(); }
  }, ease.linear);
  R.bat = null;
  R.lean = 0;
  R.headDown = 0;
}

function tapRing(x, y) {
  const ring = document.createElement("span");
  ring.className = "tap-ring";
  ring.style.left = `${x}px`;
  ring.style.top = `${y}px`;
  document.body.appendChild(ring);
  setTimeout(() => ring.remove(), 700);
}

// Clicking the switch: Coco gets up, stretches with a yawn and a shake, hop-turns, walks over, bats the knob with
// her paw (that is what flips day and night), then walks home and lies back down.
async function cocoToggleTheme(toggle) {
  const knob = toggle.querySelector(".knob");
  const next = theme() === "night" ? "day" : "night";
  const cat = getCat();
  if (reducedMotion || catBusy || !cat || !cocoVisible() || !document.querySelector(".rig")) { setTheme(next, knob); return; }
  setCatBusy(true);
  toggle.disabled = true;
  hideBubble();
  try {
    cat.classList.remove("napping");
    if (theme() === "night") { cat.classList.add("alert"); await wait(420); }      // wake up first
    rigStart();
    await tween(520, (k) => { R.lie = 1 - k; }, ease.outBack);                     // get up
    await rigStretch();
    const k = knob.getBoundingClientRect();
    const box = rigEls.svg.getBoundingClientRect();
    await rigWalkTo(k.left + k.width / 2 - box.left - 22);
    await rigBat(k.left + k.width / 2, k.top + k.height / 2, () => {
      tapRing(k.left + k.width / 2, k.top + k.height / 2);
      setTheme(next, knob, { cat: false });
    });
    await wait(120);
    await rigWalkTo(R.home);                                                         // home, facing left again
    await tween(460, (k) => { R.lie = k; });                                         // lie back down
    cat.classList.remove("alert");
    rigStop();
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
