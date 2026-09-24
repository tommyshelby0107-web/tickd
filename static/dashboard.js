// Dashboard: KPIs, decision mix, exception reasons, review queue and run history. Refreshes every 5 s.

const RULE_NAMES = {
  "VM-03": "Bank details changed", "VM-04": "Sender not vendor's domain", "VM-02": "Blocked vendor",
  "VM-01": "Unknown vendor",
  "D-01": "Same file again", "D-02": "Duplicate invoice", "D-03": "Possible duplicate",
  "M-03": "PO over-billed", "M-01": "Price over tolerance", "M-04": "Subtotal over tolerance",
  "M-02": "Qty not received", "M-05": "Unplanned charges", "M-00": "Line not on PO",
  "P-01": "No PO found", "P-02": "PO of other vendor", "P-03": "PO closed", "P-04": "PO inferred",
  "V-01": "Missing data", "V-02": "Arithmetic", "V-03": "Date", "V-04": "Tax rate", "V-05": "Low confidence",
  "V-06": "Credit note / not a bill",
  "V-07": "Currency differs from PO",
  "X-00": "Could not process",
};

let painted = false;          // entrance animations run on the first paint only, not on every refresh
const lastHtml = {};          // skip re-rendering a table whose content has not changed

// Bars keep their elements between refreshes, so a changed count slides to its new width.
function bars(el, rows) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  const key = rows.map((r) => r[0]).join("|");
  if (el.dataset.key !== key) {
    el.dataset.key = key;
    el.innerHTML = rows.length ? rows.map(([label, , cls, chip], i) => `
      <div class="bar-row enter" style="--i:${i + 5}">
        <div class="bar-label">${chip ? `<span class="chip">${esc(chip)}</span>` : ""}<span>${esc(label)}</span></div>
        <div class="bar-track"><div class="bar-fill ${cls || ""}"></div></div>
        <div class="count">0</div>
      </div>`).join("") : emptyState("No exceptions yet");
  }
  nextFrame(() => rows.forEach(([, count], i) => {
    const row = el.children[i];
    if (!row || !row.querySelector(".bar-fill")) return;
    row.querySelector(".bar-fill").style.width = `${(100 * count) / max}%`;
    countUp(row.querySelector(".count"), count);
  }));
}

function setRows(id, html) {
  if (lastHtml[id] === html) return;
  lastHtml[id] = html;
  const body = document.getElementById(id);
  body.innerHTML = html;
  if (!painted) stagger(body, "tr");
}

async function load() {
  const [m, runs] = await Promise.all([api("/api/metrics"), api("/api/runs")]);
  countUp(document.getElementById("k-total"), m.total);
  countUp(document.getElementById("k-stp"), m.straight_through_pct, (v) => `${Math.round(v)}%`);
  countUp(document.getElementById("k-time"), m.avg_seconds, (v) => (m.avg_seconds ? `${v.toFixed(1)}s` : "—"));
  countUp(document.getElementById("k-open"), m.open_reviews);
  countUp(document.getElementById("k-high"), m.high_risk_open);

  bars(document.getElementById("by-outcome"), [
    ["Approved", m.by_outcome["Approve"], "approve"],
    ["Needs review", m.by_outcome["Review"], "review"],
    ["Returned to vendor", m.by_outcome["Return to vendor"], "return"],
    ["Rejected", m.by_outcome["Reject"], "reject"],
  ]);
  bars(document.getElementById("by-reason"), m.by_reason.map(([rule, n]) => [RULE_NAMES[rule] || rule, n, "", rule]));

  const queue = runs.filter((r) => r.status === "done" && r.decision === "Review");
  countUp(document.getElementById("queue-count"), queue.length);
  setRows("queue", queue.length ? queue.map((r) => `
    <tr class="clickable" onclick="location.href='/runs/${esc(r.run_id)}'">
      <td><b>${esc(r.invoice_number || "(no number)")}</b></td>
      <td>${esc(r.vendor_name || "—")}</td>
      <td class="num">${money(r.total, r.currency)}</td>
      <td>${decisionPill(r.decision, r.severity, r.status)}</td>
      <td>${esc(r.owner || "—")}</td>
      <td class="muted" style="max-width:420px"><div class="clamp" title="${esc(r.summary || "")}">${esc((r.summary || "").replace(/^Held for [^.]+ review\. /, ""))}</div></td>
      <td class="muted nowrap">${timeAgo(r.queued_at)}</td>
    </tr>`).join("") : `<tr><td colspan="7">${emptyState("All clear. Nothing is waiting for a person.", "doc")}</td></tr>`);

  countUp(document.getElementById("runs-count"), runs.length);
  setRows("runs", runs.length ? runs.map((r) => `
    <tr class="clickable" onclick="location.href='/runs/${esc(r.run_id)}'">
      <td><b>${esc(r.file_name)}</b></td>
      <td>${sourceCell(r)}</td>
      <td>${esc(r.vendor_name || "—")}</td>
      <td class="nowrap">${esc(r.invoice_number || "—")}</td>
      <td class="num">${money(r.total, r.currency)}</td>
      <td>${decisionPill(r.decision, r.severity, r.status)}</td>
      <td class="num">${r.seconds ? `${r.seconds}s` : "—"}</td>
      <td class="muted nowrap">${timeAgo(r.queued_at)}</td>
    </tr>`).join("") : `<tr><td colspan="8">${emptyState('No runs yet. <a href="/run">Process your first invoice</a>', "upload")}</td></tr>`);
  painted = true;
}

// Where the invoice came in: a prepared sample, an upload, a folder batch or an email.
function sourceCell(r) {
  const label = { sample: "Sample", upload: "Upload", folder: "Folder", email: "Email" }[r.source] || r.source || "—";
  const link = r.batch_id ? `<a href="/bulk/${esc(r.batch_id)}" onclick="event.stopPropagation()">${esc(r.source_detail || "batch")}</a>`
    : esc(r.source_detail || "");
  return `${esc(label)}${link ? `<div class="sub">${link}</div>` : ""}`;
}

document.getElementById("new-run").innerHTML = `${icon("run")} New run`;
document.querySelectorAll("[data-icon]").forEach((b) => { b.innerHTML = icon(b.dataset.icon, 24); });
stagger(document.getElementById("kpis"));
document.querySelectorAll("#charts > .card").forEach((c, i) => { c.classList.add("enter"); c.style.setProperty("--i", 5 + i); });
renderSidebar("dashboard");
load();
setInterval(load, 5000);
