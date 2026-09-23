// Dashboard: KPIs, decision mix, exception reasons, review queue and run history. Refreshes every 5 s.

const RULE_NAMES = {
  "VM-03": "Bank details changed", "VM-02": "Blocked vendor", "VM-01": "Unknown vendor",
  "D-01": "Same file again", "D-02": "Duplicate invoice", "D-03": "Possible duplicate",
  "M-03": "PO over-billed", "M-01": "Price over tolerance", "M-04": "Subtotal over tolerance",
  "M-02": "Qty not received", "M-05": "Unplanned charges", "M-00": "Line not on PO",
  "P-01": "No PO found", "P-02": "PO of other vendor", "P-03": "PO closed", "P-04": "PO inferred",
  "V-01": "Missing data", "V-02": "Arithmetic", "V-03": "Date", "V-04": "Tax rate", "V-05": "Low confidence",
  "V-06": "Credit note / not a bill",
  "X-00": "Could not process",
};

function bars(el, rows, cls) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  el.innerHTML = rows.length ? rows.map(([label, count, c]) => `
    <div class="bar-row">
      <div>${esc(label)}</div>
      <div class="bar-track"><div class="bar-fill ${c || cls || ""}" style="width:${(100 * count) / max}%"></div></div>
      <div class="count">${count}</div>
    </div>`).join("") : '<div class="empty">No runs yet</div>';
}

async function load() {
  const [m, runs] = await Promise.all([api("/api/metrics"), api("/api/runs")]);
  document.getElementById("k-total").textContent = m.total;
  document.getElementById("k-stp").textContent = `${m.straight_through_pct}%`;
  document.getElementById("k-stp-hint").textContent = `${m.straight_through} of ${m.total} with no human touch`;
  document.getElementById("k-time").textContent = m.avg_seconds ? `${m.avg_seconds}s` : "—";
  document.getElementById("k-open").textContent = m.open_reviews;
  document.getElementById("k-high").textContent = m.high_risk_open;

  bars(document.getElementById("by-outcome"), [
    ["Approved", m.by_outcome["Approve"], "approve"],
    ["Needs review", m.by_outcome["Review"], "review"],
    ["Returned to vendor", m.by_outcome["Return to vendor"], "return"],
    ["Rejected", m.by_outcome["Reject"], "reject"],
  ]);
  bars(document.getElementById("by-reason"),
    m.by_reason.map(([rule, n]) => [`${rule} · ${RULE_NAMES[rule] || ""}`, n]));

  const queue = runs.filter((r) => r.status === "done" && r.decision === "Review");
  document.getElementById("queue-count").textContent = `${queue.length} open`;
  document.getElementById("queue").innerHTML = queue.length ? queue.map((r) => `
    <tr class="clickable" onclick="location.href='/runs/${esc(r.run_id)}'">
      <td><b>${esc(r.invoice_number || "(no number)")}</b></td>
      <td>${esc(r.vendor_name || "—")}</td>
      <td class="num">${money(r.total)}</td>
      <td>${decisionPill(r.decision, r.severity, r.status)}</td>
      <td>${esc(r.owner || "—")}</td>
      <td class="muted" style="max-width:420px">${esc((r.summary || "").replace(/^Held for [^.]+ review\. /, ""))}</td>
      <td class="muted">${timeAgo(r.started_at)}</td>
    </tr>`).join("") : '<tr><td colspan="7" class="empty">Nothing waiting. Every processed invoice was decided automatically or has been resolved.</td></tr>';

  document.getElementById("runs-count").textContent = `${runs.length} total`;
  document.getElementById("runs").innerHTML = runs.length ? runs.map((r) => `
    <tr class="clickable" onclick="location.href='/runs/${esc(r.run_id)}'">
      <td class="mono">${esc(r.run_id)}</td>
      <td>${esc(r.file_name)}</td>
      <td>${esc(r.vendor_name || "—")}</td>
      <td>${esc(r.invoice_number || "—")}</td>
      <td class="num">${money(r.total)}</td>
      <td>${decisionPill(r.decision, r.severity, r.status)}</td>
      <td class="num">${r.seconds ? `${r.seconds}s` : "—"}</td>
      <td class="muted">${timeAgo(r.started_at)}</td>
    </tr>`).join("") : '<tr><td colspan="8" class="empty">No runs yet. <a href="/run">Process your first invoice</a>.</td></tr>';
}

renderSidebar("dashboard");
load();
setInterval(load, 5000);
