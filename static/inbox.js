// Email inbox: connection status, "Check now", and every email received with the invoices it produced.

const SETUP = `
  <div class="section-label">Not connected yet</div>
  <h2 style="margin-top:4px">Connect a Gmail inbox in four steps</h2>
  <ol style="margin:8px 0 0;padding-left:20px;line-height:1.8">
    <li>Create a new Gmail account just for the demo, e.g. <b>meridian.ap.demo@gmail.com</b>. Never use a personal inbox.</li>
    <li>Google Account → Security → turn on <b>2-Step Verification</b>.</li>
    <li>Google Account → search <b>App passwords</b> → create one named "Invoice Agent" and copy the 16 characters.</li>
    <li>In <span class="mono">invoice-agent\\.env</span> set <span class="mono">EMAIL_ADDRESS</span>,
      <span class="mono">EMAIL_APP_PASSWORD</span> and (your own address) <span class="mono">EMAIL_TRUSTED_FORWARDERS</span>,
      then restart the app.</li>
  </ol>`;

async function load() {
  const s = await api("/api/email");
  document.getElementById("check").disabled = !s.enabled;
  if (s.enabled) {
    document.getElementById("lead").textContent =
      `Invoices emailed to ${s.address} are picked up automatically every ${s.poll_seconds} seconds.`;
  }
  const state = !s.enabled ? "" : s.last_error
    ? `<span class="pill reject">Error</span> <span class="muted">${esc(s.last_error)}</span>`
    : s.last_checked ? '<span class="pill approve">Connected</span>' : '<span class="pill running">Connecting…</span>';
  document.getElementById("status").innerHTML = !s.enabled ? SETUP : `
    <div class="headline" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      ${state}
      <span><b>${esc(s.address)}</b></span>
      <span class="muted">Last checked: ${s.last_checked ? timeAgo(s.last_checked) : "not yet"}</span>
      ${s.trusted_forwarders.length ? `<span class="muted">Trusted forwarders: ${esc(s.trusted_forwarders.join(", "))}</span>` : ""}
    </div>
    <div class="callout" style="margin-top:12px">Every emailed invoice also gets a sender check (VM-04): it should come from the
      vendor's own domain. A lookalike domain is held as high risk.</div>`;
  document.getElementById("count").textContent = `${s.emails.length} received`;
  document.getElementById("emails").innerHTML = s.emails.length ? s.emails.map((e) => `
    <tr>
      <td class="muted nowrap">${timeAgo(e.received_at || e.logged_at)}</td>
      <td><b>${esc(e.sender_name || e.sender)}</b><div class="quote">${esc(e.sender)}</div></td>
      <td>${esc(e.subject || "(no subject)")}</td>
      <td>${e.runs.length ? e.runs.map((r) => `<div style="margin-bottom:4px"><a href="/runs/${esc(r.run_id)}">${esc(r.file_name)}</a>
          ${decisionPill(r.decision, r.severity, r.status)}</div>`).join("") : '<span class="muted">none</span>'}</td>
      <td class="muted">${esc(e.ignored.join(", ") || "—")}</td>
    </tr>`).join("") : `<tr><td colspan="5" class="empty">${s.enabled ? "No emails yet. Send an invoice PDF to " + esc(s.address) + "." : "Connect an inbox to start receiving invoices by email."}</td></tr>`;
}

document.getElementById("check").addEventListener("click", async () => {
  const button = document.getElementById("check");
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    await api("/api/email/check", { method: "POST" });
    toast("Inbox checked");
  } catch (e) {
    toast(e.message);
  }
  button.textContent = "Check now";
  load();
});

renderSidebar("inbox");
load();
setInterval(load, 5000);
