// Email inbox: connection status, "Check now", and every email received with the invoices it produced.

const SETUP = `
  <div style="display:flex;gap:18px;align-items:center">
    ${clayArt("mail", 96)}
    <div>
      <h2 style="margin:0 0 6px">Connect a Gmail inbox</h2>
      <ol style="margin:0;padding-left:20px;line-height:1.9;font-weight:600">
        <li>Create a Gmail account just for the demo. Never use a personal inbox.</li>
        <li>Google Account → Security → turn on <b>2-Step Verification</b>.</li>
        <li>Search <b>App passwords</b>, create one and copy the 16 characters.</li>
        <li>Set <span class="mono">EMAIL_ADDRESS</span>, <span class="mono">EMAIL_APP_PASSWORD</span> and
          <span class="mono">EMAIL_TRUSTED_FORWARDERS</span> in <span class="mono">.env</span>, then restart.</li>
      </ol>
    </div>
  </div>`;

let painted = false;
let lastRows = "";

async function load() {
  const s = await api("/api/email");
  const check = document.getElementById("check");
  check.disabled = !s.enabled;
  document.getElementById("setup").hidden = s.enabled;
  if (!s.enabled) document.getElementById("setup").innerHTML = SETUP;
  const state = !s.enabled ? '<span class="pill">Not connected</span>' : s.last_error
    ? `<span class="pill reject" title="${esc(s.last_error)}">Connection error</span>`
    : s.last_checked ? '<span class="pill approve">Connected</span>' : '<span class="pill running">Connecting</span>';
  document.getElementById("status").innerHTML = state + (s.enabled ? `
    <span class="pill plain">${icon("mail", 14)}${esc(s.address)}</span>
    <span class="pill plain">${icon("refresh", 14)}${s.last_checked ? timeAgo(s.last_checked) : "not yet"}</span>` : "");
  countUp(document.getElementById("count"), s.emails.length);
  const html = s.emails.length ? s.emails.map((e) => `
    <tr>
      <td class="muted nowrap">${timeAgo(e.received_at || e.logged_at)}</td>
      <td><b>${esc(e.sender_name || e.sender)}</b><div class="sub">${esc(e.sender)}</div></td>
      <td>${esc(e.subject || "(no subject)")}</td>
      <td>${e.runs.length ? e.runs.map((r) => `<div style="margin-bottom:6px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <a href="/runs/${esc(r.run_id)}">${esc(r.file_name)}</a>${decisionPill(r.decision, r.severity, r.status)}</div>`).join("") : '<span class="muted">none</span>'}</td>
      <td class="muted">${esc(e.ignored.join(", ") || "—")}</td>
    </tr>`).join("")
    : `<tr><td colspan="5">${emptyState(s.enabled ? `No emails yet. Send an invoice PDF to ${esc(s.address)}` : "Connect an inbox to receive invoices by email", "mail")}</td></tr>`;
  if (html !== lastRows) {
    lastRows = html;
    const rows = document.getElementById("emails");
    rows.innerHTML = html;
    if (!painted) stagger(rows, "tr");
  }
  painted = true;
}

const checkButton = document.getElementById("check");
checkButton.innerHTML = `${icon("refresh", 16)} Check now`;
checkButton.addEventListener("click", async () => {
  checkButton.disabled = true;
  checkButton.innerHTML = `<span class="spin">${icon("refresh", 16)}</span> Checking`;
  try {
    await api("/api/email/check", { method: "POST" });
    toast("Inbox checked");
  } catch (e) {
    toast(e.message);
  }
  checkButton.innerHTML = `${icon("refresh", 16)} Check now`;
  load();
});

renderSidebar("inbox");
load();
setInterval(load, 5000);
