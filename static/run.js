// New run (upload or pick a scenario) and the live run view for /runs/{id}.

const runId = location.pathname.startsWith("/runs/") ? decodeURIComponent(location.pathname.split("/")[2]) : null;
const STATUS_ICON = {
  running: "spinner", pass: "check", approve: "check", note: "info", review: "alert",
  return: "alert", return_to_vendor: "alert", reject: "x", error: "x", skipped: "minus", pending: "minus",
};
const STATUS_WORD = {
  running: "Running", pass: "Passed", note: "Passed with notes", review: "Needs review", return: "Return",
  return_to_vendor: "Return to vendor", reject: "Reject", error: "Error", skipped: "Skipped", approve: "Approved",
};

// ---------------------------------------------------------------- new run

async function showNewRun() {
  document.getElementById("new-run").hidden = false;
  document.getElementById("upload-art").innerHTML = clayArt("upload", 112);
  const samples = await api("/api/samples");
  const sets = [["demo", "Demo scenarios"], ["holdout", "Unseen invoices"]];
  const card = (s) => `
    <button class="sample" data-sample="${esc(s.scenario)}">
      <div class="top"><span class="chip">${esc(s.scenario)}</span>
        <span class="pill plain ${s.type === "digital" ? "info" : "review"}">${esc(s.type)}</span></div>
      <div class="title">${esc(s.title)}</div>
    </button>`;
  const holder = document.getElementById("sample-sets");
  holder.innerHTML = sets.map(([key, heading]) => {
    const items = samples.filter((s) => s.set === key);
    return items.length ? `
      <div class="set-head"><h2>${heading}</h2><span class="tag">${items.length}</span></div>
      <div class="samples">${items.map(card).join("")}</div>` : "";
  }).join("");
  stagger(holder, ".set-head, .sample");
  document.querySelectorAll(".sample").forEach((b) =>
    b.addEventListener("click", () => start({ sample: b.dataset.sample })));

  const zone = document.getElementById("dropzone");
  const input = document.getElementById("file");
  input.addEventListener("change", () => input.files[0] && start({ file: input.files[0] }));
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("over");
    if (e.dataTransfer.files[0]) start({ file: e.dataTransfer.files[0] });
  });
}

async function start({ sample, file }) {
  const form = new FormData();
  if (sample) form.append("sample", sample);
  if (file) form.append("file", file);
  try {
    const { run_id } = await api("/api/runs", { method: "POST", body: form });
    location.href = `/runs/${run_id}`;
  } catch (e) {
    toast(e.message);
  }
}

// ---------------------------------------------------------------- live run

let clientStart = 0;        // browser time when the first event arrived: drives the ticking clock
let timer = null;
let celebrate = false;      // the decision arrived just now (not a replay of an old run): allow confetti

async function showLive(id) {
  document.getElementById("live").hidden = false;
  document.getElementById("pdf-link").innerHTML = `${icon("external", 16)} PDF`;
  document.getElementById("pdf-link").href = `/api/runs/${id}/pdf`;
  document.getElementById("again").innerHTML = `${icon("run", 16)} New run`;
  const cfg = await api("/api/config");
  document.getElementById("timeline").innerHTML = cfg.stages.map((s) => `
    <li class="stage pending" id="stage-${s.key}">
      <div class="dot">${icon("minus", 17)}</div>
      <div>
        <div class="name">${esc(s.label)} <span class="time"></span></div>
        <div class="summary"></div>
        <div class="detail"></div>
      </div>
    </li>`).join("");
  showDocument(id, 1);
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
  document.fonts.ready.then(moveThumb);
  addEventListener("resize", moveThumb);

  const stream = new EventSource(`/api/runs/${id}/events`);
  let first = true;
  stream.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    if (first) {
      clientStart = Date.now();
      timer = setInterval(tick, 100);
      first = false;
    }
    if (event.stage === "decide" && event.status !== "running") {
      celebrate = Date.now() - new Date(event.at).getTime() < 15000;
    }
    updateStage(event);
  };
  stream.addEventListener("end", () => { stream.close(); clearInterval(timer); loadResult(id); });
  stream.onerror = () => { stream.close(); clearInterval(timer); loadResult(id); };
  loadHeader(id);
}

function tick() {
  document.getElementById("elapsed").textContent = `${((Date.now() - clientStart) / 1000).toFixed(1)}s`;
}

const stageStart = {};

function updateStage(event) {
  const li = document.getElementById(`stage-${event.stage}`);
  if (!li) return;
  const at = new Date(event.at).getTime();
  const running = event.status === "running";
  if (running) stageStart[event.stage] = at;
  li.className = `stage ${event.status}${running ? "" : " done"}`;
  li.querySelector(".dot").innerHTML = icon(STATUS_ICON[event.status] || "info", 17);
  // The decide stage's full text is in the decision card; the timeline keeps its first sentence.
  const text = event.stage === "decide" && !running ? event.summary.split(". ")[0] + "." : event.summary;
  const summary = li.querySelector(".summary");
  summary.textContent = running ? `${text}…` : text;
  replay(summary, "flash");
  const took = ((at - (stageStart[event.stage] ?? at)) / 1000).toFixed(1);
  li.querySelector(".time").textContent = running ? "" : `${STATUS_WORD[event.status] || ""} · ${took}s`;
  const findings = event.data && event.data.findings;
  if (findings && findings.length) {
    const issues = findings.filter((f) => f.outcome !== "pass").length;
    li.querySelector(".detail").innerHTML = `
      <details ${issues ? "open" : ""}>
        <summary>${findings.length} check${findings.length > 1 ? "s" : ""}${issues ? ` · ${issues} flagged` : ""}</summary>
        <ul class="findings">${findings.map((f, i) => `
          <li class="finding ${esc(f.outcome)}" style="--i:${i}"><span class="chip">${esc(f.rule)}</span><span>${esc(f.message)}</span></li>`).join("")}
        </ul>
      </details>`;
  }
}

async function loadHeader(id) {
  const run = await api(`/api/runs/${id}`).catch(() => null);
  if (!run) return;
  document.getElementById("run-title").textContent = run.file_name;
  if (run.status === "queued") {
    const ahead = run.queue_position || 0;
    document.getElementById("run-meta").innerHTML = `<span class="pill">Queued · ${ahead} ahead</span>`;
  }
}

async function loadResult(id) {
  const run = await api(`/api/runs/${id}`);
  const r = run.result;
  document.getElementById("run-title").textContent = run.file_name;
  if (!r) return;
  document.getElementById("elapsed").textContent = `${r.seconds}s`;
  const doc = r.document || {};
  const ext = r.extraction || {};
  const conf = (doc.ocr_confidence || []).filter((c) => c !== null);
  const meta = [
    [icon("file", 14), doc.type === "scanned" ? `Scanned · OCR ${Math.min(...conf).toFixed(0)}%` : "Digital"],
    ext.model ? [icon("sparkle", 14), ext.model] : null,
    [icon("clock", 14), `${r.seconds}s`],
  ].filter(Boolean);
  const metaEl = document.getElementById("run-meta");
  metaEl.innerHTML = meta.map(([ico, text]) => `<span class="pill plain">${ico}${esc(text)}</span>`).join("");
  stagger(metaEl);
  renderDecision(run);
  renderFields(r);
  renderLines(r);
}

// ---------------------------------------------------------------- decision card and review

const DECISION_LOOK = {
  approve: ["mint", "check"], review: ["amber", "alert"], high: ["coral", "shield"],
  return: ["lilac", "mail"], reject: ["coral", "x"],
};

function renderDecision(run) {
  const r = run.result;
  const d = r.decision;
  const cls = d.severity === "high" ? "high" : (OUTCOME[d.outcome] || [""])[0];
  const [color, ico] = DECISION_LOOK[cls] || ["", "info"];
  const title = cls === "high" ? "High-risk hold" : (OUTCOME[d.outcome] || ["", d.outcome])[1];
  const el = document.getElementById("decision");
  el.className = `card decision ${cls}`;
  void el.offsetWidth;                      // restart the pop-in when the card is re-rendered
  el.classList.add("show");
  const held = run.status === "done" && (d.outcome === "Review" || d.outcome === "Return to vendor");
  const summary = d.summary.replace(/^(Approved|Rejected|Returned to vendor|Held for [^.]+ review)\. /, "");
  const candidates = r.po_inferred && r.po_candidates.length ? `
    <div class="callout" style="margin-top:12px">Suggested <b>${esc(r.po)}</b> ·
      ${r.po_candidates.map((c) => `${esc(c.po_number)} ${c.score.toFixed(2)}`).join(" · ")}</div>` : "";
  const message = d.message ? `
    <details class="draft" style="margin-top:14px">
      <summary>${icon("mail", 16)} Draft to ${esc(d.message.to)}</summary>
      <div class="message-box" id="draft">Subject: ${esc(d.message.subject)}\n\n${esc(d.message.body)}</div>
      <button class="btn btn-sm" style="margin-top:10px" onclick="copyDraft()">Copy</button>
    </details>` : "";
  // Approval needs a known vendor, a matched PO and the PO's currency; otherwise the only safe choices are return or reject.
  const blocker = !(r.vendor && r.po) ? "no known vendor and matched PO to approve against"
    : d.reasons.includes("V-07") ? `invoice is in ${r.invoice.currency}, a different currency from its PO`
    : null;
  const reviewForm = held ? `
    <div class="resolve-title">Resolve</div>
    <textarea id="reason" placeholder="Reason (required), e.g. Confirmed PO-4504 with buyer Dana Whitfield"></textarea>
    <div class="actions">
      <button class="btn btn-primary" onclick="review('approve')" ${blocker ? "disabled" : ""}
        title="${blocker ? `Approve is unavailable: ${esc(blocker)}` : ""}">${icon("check", 16)} Approve</button>
      <button class="btn" onclick="review('return')">${icon("mail", 16)} Return to vendor</button>
      <button class="btn btn-danger" onclick="review('reject')">${icon("x", 16)} Reject</button>
    </div>
    ${blocker ? `<div class="sub" style="margin-top:8px">Approve unavailable: ${esc(blocker)}.</div>` : ""}` : "";
  const resolved = run.review_actions.length ? `
    <div class="callout" style="margin-top:14px">${run.review_actions.map((a) =>
      `${icon("user", 14)} <b>${esc(a.action)}</b> by ${esc(a.actor)}: “${esc(a.reason)}” · ${esc(new Date(a.at).toLocaleString())}`).join("<br>")}</div>` : "";

  el.innerHTML = `
    <div class="d-top">
      <div class="blob ${color}">${icon(ico, 32)}</div>
      <div>
        <div class="d-title">${esc(title)}</div>
        <div class="d-tags">
          ${d.owner ? `<span class="pill plain">${icon("user", 14)}${esc(d.owner)}</span>` : ""}
          ${d.reasons.map((x) => `<span class="chip">${esc(x)}</span>`).join("")}
        </div>
      </div>
    </div>
    <div class="d-summary">${esc(summary)}</div>
    <div class="d-next">${icon("bolt")}<span>${esc(d.next_action)}</span></div>
    ${d.notes.length ? `<ul class="notes">${d.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
    ${candidates}${message}${resolved}${reviewForm}`;
  if (celebrate && d.outcome === "Approve") setTimeout(() => confetti(el.querySelector(".blob")), 350);
  celebrate = false;
}

function copyDraft() {
  navigator.clipboard.writeText(document.getElementById("draft").innerText).then(() => toast("Draft copied"));
}

async function review(action) {
  const reason = document.getElementById("reason").value.trim();
  if (!reason) {
    toast("Please give a reason");
    replay(document.getElementById("reason"), "shake-once");
    return;
  }
  try {
    const run = await api(`/api/runs/${runId}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, reason }),
    });
    renderDecision(run);
    if (action === "approve") confetti(document.querySelector("#decision .blob"));
    toast("Decision recorded");
  } catch (e) {
    toast(e.message);
  }
}

// ---------------------------------------------------------------- tabs

function moveThumb() {
  const active = document.querySelector(".tab.active");
  const thumb = document.querySelector(".tab-thumb");
  if (!active || !thumb) return;
  thumb.style.width = `${active.offsetWidth}px`;
  thumb.style.transform = `translateX(${active.offsetLeft}px)`;
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  ["document", "fields", "lines"].forEach((n) => { document.getElementById(`tab-${n}`).hidden = n !== name; });
  moveThumb();
}

function showDocument(id, page) {
  document.getElementById("tab-document").innerHTML =
    `<img class="page-img" src="/api/runs/${esc(id)}/pages/${page}" alt="Invoice page ${page}">`;
  document.getElementById("tab-fields").innerHTML = emptyState("Reading the invoice…", "doc");
  document.getElementById("tab-lines").innerHTML = emptyState("Matching the PO…", "folder");
}

function renderFields(r) {
  const x = r.extracted;
  if (!x) {
    document.getElementById("tab-fields").innerHTML = emptyState("The invoice could not be read automatically");
    return;
  }
  const v05 = r.findings.find((f) => f.rule === "V-05");
  const src = (s) => s && s.value
    ? `${esc(s.value)}${s.source_quote ? `<div class="quote">“${esc(s.source_quote)}”${s.page ? ` · p${s.page}` : ""}</div>` : ""}`
    : '<span class="muted">not printed</span>';
  const plain = (v) => (v === null || v === undefined || v === "" ? '<span class="muted">—</span>' : esc(v));
  const cur = (r.invoice && r.invoice.currency) || x.currency;
  const rows = [
    ["Vendor", src(x.vendor_name)], ["Invoice number", src(x.invoice_number)], ["Invoice date", src(x.invoice_date)],
    ["Due date", src(x.due_date)], ["PO number", src(x.po_number)], ["Order reference", plain(x.po_hint)],
    ["Currency", plain(x.currency ? `${x.currency} (as printed)` : cur ? `${cur} (none printed)` : null)],
    ["Subtotal", plain(x.subtotal !== null ? money(x.subtotal, cur) : null)],
    ["Tax", plain(x.tax_amount !== null ? `${money(x.tax_amount, cur)}${x.tax_rate_pct !== null ? ` (${x.tax_rate_pct}%)` : ""}` : null)],
    ["Freight", plain(x.freight ? money(x.freight, cur) : null)], ["Total", src(x.total)],
    ["Remit-to bank", plain(x.remit_bank_name)], ["Routing", src(x.remit_routing_number)],
    ["Account", src(x.remit_account_number)], ["Notes on invoice", plain(x.notes)],
  ];
  const ext = r.extraction || {};
  document.getElementById("tab-fields").innerHTML = `
    ${v05 ? `<div class="callout" style="margin-bottom:16px">
      <span class="${v05.outcome === "pass" ? "verified" : "unverified"}">${v05.outcome === "pass" ? "✓ Evidence verified" : "! Evidence not verified"}</span>
      · ${esc(v05.message)}</div>` : ""}
    <dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    <h2 style="margin:22px 0 8px">Lines</h2>
    <table><thead><tr><th>SKU</th><th>Description</th><th class="num">Qty</th><th class="num">Unit price</th><th class="num">Amount</th></tr></thead>
    <tbody>${x.lines.map((l) => `<tr><td class="mono">${esc(l.sku || "—")}</td><td>${esc(l.description)}</td>
      <td class="num">${l.quantity}</td><td class="num">${money(l.unit_price, cur)}</td><td class="num">${money(l.amount, cur)}</td></tr>`).join("")}</tbody></table>
    <p class="sub" style="margin-top:14px">Read by ${esc(ext.model || "—")}
      ${ext.fallbacks && ext.fallbacks.length ? ` · skipped: ${esc(ext.fallbacks.join("; "))}` : ""}</p>`;
}

function renderLines(r) {
  const el = document.getElementById("tab-lines");
  if (!r.po) {
    el.innerHTML = emptyState("No purchase order matched");
    return;
  }
  const matches = r.line_matches || [];
  el.innerHTML = `
    <div style="margin-bottom:14px;display:flex;gap:8px;align-items:center"><b style="font-size:16px">${esc(r.po)}</b>
      ${r.po_inferred ? '<span class="pill review">inferred</span>' : '<span class="pill info">printed on invoice</span>'}</div>
    <table><thead><tr><th>Line</th><th class="num">Qty</th><th class="num">Invoice price</th><th class="num">PO price</th>
      <th class="num">Variance</th><th class="num">Received</th><th class="num">Billed before</th></tr></thead>
    <tbody>${matches.map((m) => {
      const net = m.unit_price_net ?? m.unit_price;      // prices that include tax are compared net of it
      const pct = ((net - m.po_unit_price) / m.po_unit_price) * 100;
      const netNote = Math.abs(net - m.unit_price) > 0.001 ? `<div class="quote">${money(net)} net of tax</div>` : "";
      return `<tr><td>${esc(m.description)}<div class="quote mono">${esc(m.sku)} · line ${m.po_line_no}</div></td>
        <td class="num">${m.qty}</td><td class="num">${money(m.unit_price)}${netNote}</td><td class="num">${money(m.po_unit_price)}</td>
        <td class="num" style="font-weight:800;color:${Math.abs(pct) > 0.001 ? "var(--amber)" : "var(--mint)"}">${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%</td>
        <td class="num">${m.qty_received} / ${m.qty_ordered}</td><td class="num">${m.qty_invoiced_before}</td></tr>`;
    }).join("") || `<tr><td colspan="7">${emptyState("No lines matched")}</td></tr>`}</tbody></table>`;
}

// ---------------------------------------------------------------- init

renderSidebar("run");
if (runId) showLive(runId); else showNewRun();
