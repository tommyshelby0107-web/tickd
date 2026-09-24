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
  document.getElementById("upload-icon").innerHTML = icon("upload", 28);
  const samples = await api("/api/samples");
  const sets = [
    ["demo", "Demo scenarios", "The happy paths and edge cases the rules were designed around."],
    ["holdout", "Unseen test invoices", "Held out: new vendors and layouts that were never used to tune the rules."],
  ];
  const card = (s) => `
    <button class="sample" data-sample="${esc(s.scenario)}">
      <div class="top"><span class="chip">${esc(s.scenario)}</span>
        <span class="pill plain ${s.type === "digital" ? "info" : "review"}">${esc(s.type)}</span></div>
      <div class="title">${esc(s.title)}</div>
      <div class="muted" style="font-size:12.5px">${esc(s.file)}</div>
    </button>`;
  document.getElementById("sample-sets").innerHTML = sets.map(([key, heading, blurb]) => {
    const items = samples.filter((s) => s.set === key);
    return items.length ? `
      <h2 style="margin:26px 0 2px">${heading}</h2>
      <p class="muted" style="margin:0 0 12px">${blurb}</p>
      <div class="samples">${items.map(card).join("")}</div>` : "";
  }).join("");
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

let clientStart = 0;        // browser time when the first event arrived: drives the ticking timer
let timer = null;

async function showLive(id) {
  document.getElementById("live").hidden = false;
  document.getElementById("run-label").textContent = `Run ${id}`;
  document.getElementById("pdf-link").href = `/api/runs/${id}/pdf`;
  const cfg = await api("/api/config");
  document.getElementById("timeline").innerHTML = cfg.stages.map((s, i) => `
    <li class="stage pending" id="stage-${s.key}">
      <div class="dot">${icon("minus", 14)}</div>
      <div>
        <div class="name">${i + 1}. ${esc(s.label)} <span class="time"></span></div>
        <div class="summary">Waiting</div>
        <div class="detail"></div>
      </div>
    </li>`).join("");
  showDocument(id, 1);
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

  const stream = new EventSource(`/api/runs/${id}/events`);
  let first = true;
  stream.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    if (first) {
      clientStart = Date.now();
      timer = setInterval(tick, 100);
      first = false;
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
  if (event.status === "running") stageStart[event.stage] = at;
  li.className = `stage ${event.status}`;
  li.querySelector(".dot").innerHTML = icon(STATUS_ICON[event.status] || "info", 14);
  // The decide stage's full text is in the decision card; the timeline keeps its first sentence.
  const summary = event.stage === "decide" && event.status !== "running" ? event.summary.split(". ")[0] + "." : event.summary;
  li.querySelector(".summary").textContent = event.status === "running" ? `${summary}…` : summary;
  const took = ((at - (stageStart[event.stage] ?? at)) / 1000).toFixed(1);
  li.querySelector(".time").textContent = event.status === "running" ? "" : `${STATUS_WORD[event.status] || ""} · ${took}s`;
  const findings = event.data && event.data.findings;
  if (findings && findings.length) {
    const issues = findings.filter((f) => f.outcome !== "pass").length;
    li.querySelector(".detail").innerHTML = `
      <details ${issues ? "open" : ""}>
        <summary>${findings.length} check${findings.length > 1 ? "s" : ""}${issues ? ` · ${issues} flagged` : " · all passed"}</summary>
        <ul class="findings">${findings.map((f) => `
          <li class="finding ${esc(f.outcome)}"><span class="chip">${esc(f.rule)}</span><span>${esc(f.message)}</span></li>`).join("")}
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
    document.getElementById("run-sub").textContent =
      `Queued: ${ahead} invoice${ahead === 1 ? "" : "s"} ahead of this one. It starts automatically.`;
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
  document.getElementById("run-sub").textContent = [
    doc.type === "scanned" ? `Scanned PDF, OCR confidence ${Math.min(...conf).toFixed(0)}%` : "Digital PDF",
    ext.model ? `read by ${ext.model}${ext.seconds ? ` in ${ext.seconds}s` : ""}` : null,
    `decided in ${r.seconds}s`,
    `policy v${r.policy_version}`,
  ].filter(Boolean).join(" · ");
  renderDecision(run);
  renderFields(r);
  renderLines(r);
}

// ---------------------------------------------------------------- decision card and review

function renderDecision(run) {
  const r = run.result;
  const d = r.decision;
  const cls = d.severity === "high" ? "high" : (OUTCOME[d.outcome] || [""])[0];
  const el = document.getElementById("decision");
  el.className = `card decision show ${cls}`;
  const held = run.status === "done" && (d.outcome === "Review" || d.outcome === "Return to vendor");
  const candidates = r.po_inferred && r.po_candidates.length ? `
    <div class="callout" style="margin-top:12px">Suggested PO <b>${esc(r.po)}</b> — match score
      ${r.po_candidates.map((c) => `${esc(c.po_number)} ${c.score.toFixed(2)}`).join(", ")}.
      Inferred matches are never approved automatically.</div>` : "";
  const message = d.message ? `
    <details style="margin-top:12px">
      <summary style="cursor:pointer;font-weight:600">${icon("mail", 15)} Drafted message to ${esc(d.message.to)}</summary>
      <div class="message-box" id="draft">Subject: ${esc(d.message.subject)}\n\n${esc(d.message.body)}</div>
      <button class="btn btn-sm" style="margin-top:8px" onclick="copyDraft()">Copy</button>
    </details>` : "";
  // Approval needs a known vendor and a matched PO; without them the only safe choices are return or reject.
  const canApprove = Boolean(r.vendor && r.po);
  const reviewForm = held ? `
    <div style="margin-top:16px">
      <div style="font-weight:600;margin-bottom:6px">Resolve this invoice</div>
      <textarea id="reason" placeholder="Reason (required) — e.g. Confirmed PO-4504 with buyer Dana Whitfield"></textarea>
      <div class="actions">
        <button class="btn btn-primary" onclick="review('approve')" ${canApprove ? "" : "disabled"}
          title="${canApprove ? "" : "Needs a known vendor and a matched PO: onboard the vendor or fix the PO first"}">${icon("check", 16)} Approve</button>
        <button class="btn" onclick="review('return')">Return to vendor</button>
        <button class="btn btn-danger" onclick="review('reject')">${icon("x", 16)} Reject</button>
      </div>
      ${canApprove ? "" : '<div class="muted" style="font-size:12.5px;margin-top:6px">Approve is unavailable: there is no known vendor and matched PO to approve against.</div>'}
    </div>` : "";
  const resolved = run.review_actions.length ? `
    <div class="callout" style="margin-top:12px">${run.review_actions.map((a) =>
      `Resolved by ${esc(a.actor)}: <b>${esc(a.action)}</b> — “${esc(a.reason)}” (${esc(new Date(a.at).toLocaleString())})`).join("<br>")}</div>` : "";

  el.innerHTML = `
    <div class="headline">
      ${decisionPill(d.outcome, d.severity, "done")}
      ${d.owner ? `<span class="muted">Owner: <b style="color:var(--text)">${esc(d.owner)}</b></span>` : ""}
      ${d.reasons.map((x) => `<span class="chip">${esc(x)}</span>`).join(" ")}
    </div>
    <div class="summary">${esc(d.summary)}</div>
    <div class="next"><b>Next step:</b> ${esc(d.next_action)}</div>
    ${d.notes.length ? `<ul class="muted" style="margin:8px 0 0;padding-left:18px">${d.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
    ${candidates}${message}${resolved}${reviewForm}`;
}

function copyDraft() {
  navigator.clipboard.writeText(document.getElementById("draft").innerText).then(() => toast("Draft copied"));
}

async function review(action) {
  const reason = document.getElementById("reason").value.trim();
  if (!reason) { toast("Please give a reason"); return; }
  try {
    const run = await api(`/api/runs/${runId}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, reason }),
    });
    renderDecision(run);
    toast("Decision recorded");
  } catch (e) {
    toast(e.message);
  }
}

// ---------------------------------------------------------------- tabs

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  ["document", "fields", "lines"].forEach((n) => { document.getElementById(`tab-${n}`).hidden = n !== name; });
}

function showDocument(id, page) {
  document.getElementById("tab-document").innerHTML =
    `<img class="page-img" src="/api/runs/${esc(id)}/pages/${page}" alt="Invoice page ${page}">`;
}

function renderFields(r) {
  const x = r.extracted;
  if (!x) return;
  const v05 = r.findings.find((f) => f.rule === "V-05");
  const src = (s) => s && s.value
    ? `${esc(s.value)}${s.source_quote ? `<div class="quote">“${esc(s.source_quote)}”${s.page ? ` · page ${s.page}` : ""}</div>` : ""}`
    : '<span class="muted">not printed</span>';
  const plain = (v) => (v === null || v === undefined || v === "" ? '<span class="muted">—</span>' : esc(v));
  const rows = [
    ["Vendor", src(x.vendor_name)], ["Invoice number", src(x.invoice_number)], ["Invoice date", src(x.invoice_date)],
    ["Due date", src(x.due_date)], ["PO number", src(x.po_number)], ["Order reference", plain(x.po_hint)],
    ["Subtotal", plain(x.subtotal !== null ? money(x.subtotal) : null)],
    ["Tax", plain(x.tax_amount !== null ? `${money(x.tax_amount)}${x.tax_rate_pct !== null ? ` (${x.tax_rate_pct}%)` : ""}` : null)],
    ["Freight", plain(x.freight ? money(x.freight) : null)], ["Total", src(x.total)],
    ["Remit-to bank", plain(x.remit_bank_name)], ["Routing", src(x.remit_routing_number)],
    ["Account", src(x.remit_account_number)], ["Notes on invoice", plain(x.notes)],
  ];
  const ext = r.extraction || {};
  document.getElementById("tab-fields").innerHTML = `
    ${v05 ? `<div class="callout" style="margin-bottom:14px">
      <span class="${v05.outcome === "pass" ? "verified" : "unverified"}">${v05.outcome === "pass" ? "✓ Evidence verified" : "! Evidence not verified"}</span>
      — ${esc(v05.message)}</div>` : ""}
    <dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    <h2 style="margin:18px 0 8px">Lines on the invoice</h2>
    <table><thead><tr><th>SKU</th><th>Description</th><th class="num">Qty</th><th class="num">Unit price</th><th class="num">Amount</th></tr></thead>
    <tbody>${x.lines.map((l) => `<tr><td class="mono">${esc(l.sku || "—")}</td><td>${esc(l.description)}</td>
      <td class="num">${l.quantity}</td><td class="num">${money(l.unit_price)}</td><td class="num">${money(l.amount)}</td></tr>`).join("")}</tbody></table>
    <p class="muted" style="margin-top:12px;font-size:12.5px">Read by ${esc(ext.model || "—")}
      ${ext.input_tokens ? ` · ${ext.input_tokens} + ${ext.output_tokens} tokens` : ""}
      ${ext.fallbacks && ext.fallbacks.length ? ` · skipped: ${esc(ext.fallbacks.join("; "))}` : ""}</p>`;
}

function renderLines(r) {
  const el = document.getElementById("tab-lines");
  if (!r.po) {
    el.innerHTML = '<div class="empty">No purchase order was matched to this invoice.</div>';
    return;
  }
  const matches = r.line_matches || [];
  el.innerHTML = `
    <div style="margin-bottom:12px"><b>${esc(r.po)}</b>
      ${r.po_inferred ? '<span class="pill review" style="margin-left:6px">inferred</span>' : '<span class="pill info" style="margin-left:6px">printed on invoice</span>'}</div>
    <table><thead><tr><th>Line</th><th class="num">Qty</th><th class="num">Invoice price</th><th class="num">PO price</th>
      <th class="num">Variance</th><th class="num">Received</th><th class="num">Billed before</th></tr></thead>
    <tbody>${matches.map((m) => {
      const net = m.unit_price_net ?? m.unit_price;      // prices that include tax are compared net of it
      const pct = ((net - m.po_unit_price) / m.po_unit_price) * 100;
      const netNote = Math.abs(net - m.unit_price) > 0.001 ? `<div class="quote">${money(net)} net of tax</div>` : "";
      return `<tr><td>${esc(m.description)}<div class="quote mono">${esc(m.sku)} · PO line ${m.po_line_no}</div></td>
        <td class="num">${m.qty}</td><td class="num">${money(m.unit_price)}${netNote}</td><td class="num">${money(m.po_unit_price)}</td>
        <td class="num" style="color:${Math.abs(pct) > 0.001 ? "var(--amber)" : "var(--muted)"}">${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%</td>
        <td class="num">${m.qty_received} / ${m.qty_ordered}</td><td class="num">${m.qty_invoiced_before}</td></tr>`;
    }).join("") || '<tr><td colspan="7" class="empty">No lines matched</td></tr>'}</tbody></table>`;
}

// ---------------------------------------------------------------- init

renderSidebar("run");
if (runId) showLive(runId); else showNewRun();
