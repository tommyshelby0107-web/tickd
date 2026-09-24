// The cover page: Coco working the tick factory, how it works, proof, edge cases, and the way into the app.
// Needs app.js (wordmark, theme, motion helpers) and coco.js (the rig, the curled cat, words and hearts).

// ---------------------------------------------------------------- the tick factory
// Invoices ride a belt through three gates (Read, Check, Decide). Coco, standing at the end, swats each one:
// the stamp lands, she reacts, and the invoice flies to its tray. At night she dozes between invoices.

const START_X = -96;                 // where an invoice enters (its left edge, stage px)
const STOP_X = 372;                  // where it stops, in front of Coco
const SPEED = 170;                   // belt speed in px/s (the belt stripes move at the same speed)
const GATE_X = [95, 210, 325];
const COCO = { x: 520, ground: 330, scale: 1.45 };
const LOOK = {
  approve: { sym: "✓", color: "var(--o-mint)", words: ["purr-fect!", "tick!", "approved!"] },
  review: { sym: "?", color: "var(--o-amber)", words: ["hmm, a person should look", "over to you, humans"] },
  reject: { sym: "✕", color: "var(--o-coral)", words: ["nope!", "not today!"] },
};
const JOBS = [
  { vendor: "Apex Fasteners", color: "#6a4cf5", amount: "$2,588.06", outcome: "approve", why: "matched PO-4501, every check passed" },
  { vendor: "Summit Electrical", color: "#ec8a0c", amount: "$15,000.00", outcome: "review", why: "PO-4503 would be 112.5% billed" },
  { vendor: "Coastal Packaging", color: "#2f76e0", amount: "$13,650.20", outcome: "approve", why: "within tolerance, 3 notes" },
  { vendor: "Redline Industrial", color: "#e0445c", amount: "$1,850.00", outcome: "reject", why: "vendor is blocked" },
  { vendor: "Northline Safety", color: "#23945f", amount: "$5,565.00", outcome: "review", why: "no PO printed, PO-4504 inferred" },
  { vendor: "Harbor Office", color: "#8b4fe0", amount: "$1,194.40", outcome: "approve", why: "matched PO-4480" },
  { vendor: "Brightpath Tools", color: "#2a2238", amount: "$2,180.00", outcome: "review", why: "bank details changed, call the vendor" },
  { vendor: "Apex Fasteners", color: "#6a4cf5", amount: "$2,588.06", outcome: "reject", why: "duplicate of INV-2026-0457" },
  { vendor: "Delta Pallet", color: "#ec8a0c", amount: "$4,676.25", outcome: "review", why: "120 pallets not received yet" },
];

const stage = document.getElementById("stage");
const counts = { approve: 0, review: 0, reject: 0 };
let watching = null;          // the invoice Coco is watching come down the belt
let dozing = false;
let dozeToken = 0;
const pick = (list) => list[Math.floor(Math.random() * list.length)];

function stagePoint(x, y) {
  const b = stage.getBoundingClientRect();
  return [b.left + x, b.top + y];
}

// Coco's head, in page coordinates.
function cocoHead() {
  return stagePoint(R.x + R.flip * R.scale * 34, R.ground - 58 * R.scale);
}

function say(text, dx = -40) {
  const [hx, hy] = cocoHead();
  floatWord(text, hx + dx, hy);
}

function hop(height = 14) {
  return tween(440, (k, raw) => {
    R.hop = -height * Math.sin(Math.PI * raw);
    R.squash = 1 + 0.07 * Math.sin(Math.PI * raw) - (raw > 0.85 ? 0.08 * Math.sin(Math.PI * (raw - 0.85) / 0.15) : 0);
  }, ease.linear).then(() => { R.hop = 0; R.squash = 1; });
}

function nod() {
  return tween(520, (k, raw) => { R.headDown = -9 * Math.sin(Math.PI * 2 * raw); }, ease.linear).then(() => { R.headDown = 0; });
}

function shakeHead() {
  return tween(480, (k, raw) => { R.shake = Math.sin(raw * Math.PI * 6) * 4 * (1 - raw); }, ease.linear).then(() => { R.shake = 0; });
}

async function doze() {
  if (dozing || theme() !== "night") return;
  dozing = true;
  const token = ++dozeToken;
  await tween(700, (k) => { R.sleep = k; R.headDown = 10 * k; });
  while (dozing && token === dozeToken) {             // little z's while she sleeps
    say("z", 12);
    await wait(1300);
  }
}

function wakeUp(startled = true) {
  if (!dozing) return;
  dozing = false;
  dozeToken++;
  tween(260, (k) => { R.sleep = 1 - k; R.headDown = 10 * (1 - k); });
  if (startled) say("!", 10);
}

function stampCard(card, outcome) {
  const s = card.querySelector(".stamp");
  s.textContent = LOOK[outcome].sym;
  s.className = `stamp ${outcome}`;
  void s.offsetWidth;
  s.classList.add("on");
  setTimeout(() => sparkle(s, 10), 80);
}

function react(outcome) {
  const [hx, hy] = cocoHead();
  say(pick(LOOK[outcome].words), outcome === "review" ? -150 : -60);
  if (outcome === "approve") { hop(); floatHearts(hx, hy, 2); }
  if (outcome === "review") nod();
  if (outcome === "reject") shakeHead();
}

function tick(job) {
  const t = document.getElementById("ticker");
  const look = LOOK[job.outcome];
  t.innerHTML = `<span class="msg"><i style="background:${look.color}">${look.sym}</i><b>${esc(job.vendor)}</b>
    <span class="muted">${esc(job.amount)} · ${esc(job.why)}</span></span>`;
}

async function flyToTray(card, outcome) {
  const tray = document.getElementById(`t-${outcome}`);
  const t = tray.getBoundingClientRect();
  const s = stage.getBoundingClientRect();
  const tx = t.left + t.width / 2 - s.left - 40;
  const ty = t.top + t.height / 2 - s.top - 226 - 52;
  const spin = outcome === "reject" ? 40 : -25;
  const frames = [
    { transform: `translate(${STOP_X}px, 0) rotate(0) scale(1)` },
    ...(outcome === "reject" ? [                     // a rejected invoice shudders first
      { transform: `translate(${STOP_X - 7}px, 0)`, offset: 0.08 }, { transform: `translate(${STOP_X + 7}px, 0)`, offset: 0.16 },
      { transform: `translate(${STOP_X - 5}px, 0)`, offset: 0.24 }, { transform: `translate(${STOP_X}px, 0)`, offset: 0.3 }] : []),
    { transform: `translate(${(STOP_X + tx) / 2}px, ${ty / 2 - 80}px) rotate(${spin / 2}deg) scale(0.7)`, offset: 0.62 },
    { transform: `translate(${tx}px, ${ty}px) rotate(${spin}deg) scale(0.16)`, opacity: 0.3 },
  ];
  await card.animate(frames, { duration: outcome === "reject" ? 1000 : 720, easing: "cubic-bezier(0.4, 0, 0.6, 1)", fill: "forwards" }).finished;
  card.remove();
  counts[outcome] += 1;
  countUp(tray.querySelector("b"), counts[outcome]);
  replay(tray, "bump");
}

async function runJob(job) {
  const card = document.createElement("div");
  card.className = "inv";
  card.innerHTML = `<span class="band" style="background:${job.color}">${esc(job.vendor)}</span>
    <i class="ln"></i><i class="ln s"></i><i class="ln"></i><b class="amt">${esc(job.amount)}</b><span class="stamp"></span>`;
  card.style.transform = `translateX(${START_X}px)`;
  document.getElementById("cards").appendChild(card);
  const belt = document.getElementById("belt");
  const ms = ((STOP_X - START_X) / SPEED) * 1000;
  const gates = [...stage.querySelectorAll(".gate")];
  belt.classList.add("moving");
  watching = card;
  GATE_X.forEach((gx, i) => {
    setTimeout(() => {                                // the gate lights as the invoice passes under it
      gates[i].style.setProperty("--lamp", i === 2 ? LOOK[job.outcome].color : "var(--o-mint)");
      gates[i].classList.add("lit");
      if (i === 0) replay(card, "scan");
      if (i === 1) card.classList.add("checked");
      setTimeout(() => gates[i].classList.remove("lit"), 700);
    }, ((gx - 40 - START_X) / SPEED) * 1000);
  });
  if (dozing) setTimeout(() => wakeUp(true), Math.max(0, ms - 1100));
  await card.animate([{ transform: `translateX(${START_X}px)` }, { transform: `translateX(${STOP_X}px)` }],
    { duration: ms, easing: "linear", fill: "forwards" }).finished;
  belt.classList.remove("moving");
  wakeUp(false);
  const [px, py] = stagePoint(STOP_X + 76, COCO.ground - 22);
  await rigBat(px, py, () => {
    stampCard(card, job.outcome);
    tapRing(px, py);
    card.animate([{ transform: `translateX(${STOP_X}px)` }, { transform: `translateX(${STOP_X - 3}px) scale(1.05, 0.95)` },
      { transform: `translateX(${STOP_X}px)` }], { duration: 260 });
  });
  watching = null;
  react(job.outcome);
  tick(job);
  await wait(450);
  await flyToTray(card, job.outcome);
  if (theme() === "night") doze();
}

// Her eyes follow the invoice coming down the belt, otherwise your cursor.
function lookAround() {
  let px = innerWidth / 2, py = innerHeight / 2;
  addEventListener("pointermove", (e) => { px = e.clientX; py = e.clientY; }, { passive: true });
  const step = () => {
    const [hx, hy] = cocoHead();
    let tx = px, ty = py;
    if (watching) { const r = watching.getBoundingClientRect(); tx = r.left + r.width / 2; ty = r.top + r.height / 2; }
    const dx = tx - hx, dy = ty - hy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 220) * 2.1;
    R.lookX = lerp(R.lookX, ((dx / d) * k) / Math.sign(R.flip * R.scale || 1), 0.18);
    R.lookY = lerp(R.lookY, (dy / d) * k * 0.8, 0.18);
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function factory() {
  const slot = document.getElementById("rig-slot");
  slot.insertAdjacentHTML("afterend", RIG_SVG);
  slot.remove();
  if (!stage.offsetParent) return;                    // hidden on small screens
  rigStart({ svg: stage.querySelector(".rig"), home: COCO.x, ground: COCO.ground, flip: -1, scale: COCO.scale, lie: 0 });
  if (!reducedMotion) lookAround();
  if (theme() === "night") doze();
  await wait(900);
  for (let n = 0; ; n++) {
    await runJob(JOBS[n % JOBS.length]);
    await wait(reducedMotion ? 2500 : 550);
  }
}

// Petting Coco on the stage.
document.getElementById("coco-hit").addEventListener("click", () => {
  const [hx, hy] = cocoHead();
  floatHearts(hx, hy, 4);
  if (dozing) { say("purrr… zzz", -40); return; }
  say(pick(["meow!", "purrr~", "hi there!"]), -40);
  hop(18);
});

// ---------------------------------------------------------------- the page around it

function setupNav() {
  const slot = document.getElementById("brand");
  slot.insertAdjacentHTML("afterend", wordmark());
  slot.remove();
  wireWordmark(document.querySelector(".wordmark"));
  const switchSlot = document.getElementById("switch-slot");
  switchSlot.innerHTML = themeSwitch();
  const toggle = switchSlot.querySelector(".theme-switch");
  toggle.addEventListener("click", () => {
    const next = theme() === "night" ? "day" : "night";
    setTheme(next, toggle.querySelector(".knob"));
    if (next === "night") setTimeout(() => { if (!watching) doze(); }, 900);
    else wakeUp(true);
  });
  document.querySelectorAll(".go").forEach((a) => { a.insertAdjacentHTML("beforeend", ` <span class="arrow">${icon("arrowRight", 18)}</span>`); });
  document.getElementById("arrow")?.remove();
  document.getElementById("trust").innerHTML = ["Python first, AI only when needed", "Every decision explained", "Doubt goes to a person"]
    .map((t) => `<span>${icon("check", 16)}${t}</span>`).join("");
}

// "Open the app": Coco cheers, a clay portal opens from the button, and the dashboard greets you.
function setupGo() {
  document.querySelectorAll(".go").forEach((a) => a.addEventListener("click", (e) => {
    try { sessionStorage.setItem("tickd-welcome", "1"); } catch { /* private mode */ }
    if (e.metaKey || e.ctrlKey || e.shiftKey || reducedMotion) return;
    e.preventDefault();
    if (stage.offsetParent) { wakeUp(false); say("let's go!", -50); hop(18); }
    const b = a.getBoundingClientRect();
    const x = b.left + b.width / 2, y = b.top + b.height / 2;
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const portal = document.createElement("div");
    portal.className = "portal";
    document.body.appendChild(portal);
    portal.animate([{ clipPath: `circle(0px at ${x}px ${y}px)` }, { clipPath: `circle(${r}px at ${x}px ${y}px)` }],
      { duration: 700, delay: 250, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "forwards" })
      .finished.then(() => { location.href = a.href; });
  }));
  const finalGo = document.getElementById("final-go");
  const cat = document.querySelector(".final-card .cat");
  finalGo.addEventListener("mouseenter", () => cat && cat.classList.add("hello"));
  finalGo.addEventListener("mouseleave", () => cat && cat.classList.remove("hello"));
}

// Sections rise into view; the proof numbers count up when they appear.
function setupReveal() {
  const targets = document.querySelectorAll(".l-title, .step, .proof-card, .marquee, .final-card, .live-line");
  targets.forEach((el) => el.classList.add("reveal"));
  const io = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    io.unobserve(entry.target);
    const el = entry.target;
    const siblings = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
    el.style.transitionDelay = `${Math.max(0, siblings.indexOf(el)) * 90}ms`;
    el.classList.add("in");
    el.querySelectorAll(".big").forEach((big) => {
      if (big.dataset.static) { big.animate([{ transform: "scale(0.5)" }, { transform: "scale(1.12)" }, { transform: "none" }], { duration: 700, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" }); return; }
      countUp(big, Number(big.dataset.count), (v) => `${Math.round(v)}${big.dataset.suffix || ""}`);
    });
  }), { threshold: 0.25 });
  targets.forEach((el) => io.observe(el));
}

const EDGES = [
  [["Bank details changed on a perfect invoice", "--o-coral"], ["Split PO billed to 112.5%", "--o-amber"],
   ["An old invoice re-sent as a scan", "--o-coral"], ["No PO printed, PO inferred from the lines", "--o-sky"],
   ["A credit note, not a bill", "--o-lilac"], ["Prices that already include sales tax", "--o-mint"], ["Billed for 300 pallets, 180 received", "--o-amber"]],
  [["Invoice in rupees, PO in dollars", "--o-amber"], ["Blocked vendor", "--o-coral"], ["Lookalike sender domain", "--o-coral"],
   ["WhatsApp photo, 42% OCR", "--o-sky"], ["Unknown vendor quoting our real PO", "--o-coral"], ["A line typed 609 instead of 690", "--o-lilac"],
   ["Free AI tier down: straight to a person", "--o-mint"]],
];

function setupEdges() {
  EDGES.forEach((row, i) => {
    const chips = row.map(([text, color]) => `<span class="edge" style="--c:var(${color})"><i></i>${esc(text)}</span>`).join("");
    document.getElementById(`edges-${i + 1}`).innerHTML = chips + chips;      // twice, for a seamless loop
  });
}

async function setupLive() {
  try {
    const m = await api("/api/metrics");
    if (!m.total) return;
    document.getElementById("live-line").innerHTML =
      `<i class="live-dot"></i>Live in this demo: ${m.total} invoice${m.total === 1 ? "" : "s"} processed so far`;
  } catch { /* optional */ }
}

renderBackdrop();
setupNav();
setupGo();
setupEdges();
setupReveal();
setupLive();
document.getElementById("final-cat").outerHTML = CAT;
if (!reducedMotion) trackEyes();
factory();
