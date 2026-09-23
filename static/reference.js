// Reference data: POs with billed progress, vendor master, invoice registry, policy, and demo reset.

async function load() {
  const data = await api("/api/reference");
  const names = Object.fromEntries(data.vendors.map((v) => [v.vendor_id, v.name]));

  document.getElementById("pos").innerHTML = data.purchase_orders.map((po) => `
    <tr>
      <td class="mono"><b>${esc(po.po_number)}</b></td>
      <td>${esc(names[po.vendor_id] || po.vendor_id)}</td>
      <td>${esc(po.description)}</td>
      <td><span class="pill ${po.status === "Open" ? "approve" : "plain"}">${esc(po.status)}</span></td>
      <td>${esc(po.buyer)}</td>
      <td class="num">${money(po.value)}</td>
      <td class="num">${money(po.billed)}</td>
      <td><div class="progress ${po.billed_pct > 100 ? "over" : ""}"><div style="width:${Math.min(100, po.billed_pct)}%"></div></div>
        <div class="muted" style="font-size:12px">${po.billed_pct}% billed</div></td>
    </tr>`).join("");

  document.getElementById("vendors").innerHTML = data.vendors.map((v) => `
    <tr>
      <td class="mono">${esc(v.vendor_id)}</td>
      <td><b>${esc(v.name)}</b><div class="quote">${esc(v.address)}</div></td>
      <td><span class="pill ${v.status === "Active" ? "approve" : "reject"}">${esc(v.status)}</span></td>
      <td class="mono">${esc(v.tax_id)}</td>
      <td>${esc(v.bank_name)} <span class="mono">${esc(v.bank_account)}</span></td>
      <td>${esc(v.phone_on_file)}</td>
      <td class="num">${(v.expected_tax_rate * 100).toFixed(1)}%</td>
      <td>${esc(v.payment_terms)}</td>
    </tr>`).join("");

  document.getElementById("registry").innerHTML = data.registry.map((r) => `
    <tr>
      <td>${esc(names[r.vendor_id] || r.vendor_id)}</td>
      <td class="nowrap">${esc(r.invoice_number)}</td>
      <td class="mono">${esc(r.invoice_key)}</td>
      <td class="num">${money(r.total)}</td>
      <td>${esc(r.status)}${r.run_id ? ` · <a href="/runs/${esc(r.run_id)}">run</a>` : ""}</td>
    </tr>`).join("");

  document.getElementById("policy").innerHTML = Object.entries(data.policy).map(([k, v]) => `
    <tr><td class="mono">${esc(k)}</td><td class="num"><b>${esc(v)}</b></td></tr>`).join("");
}

document.getElementById("reset").addEventListener("click", async () => {
  if (!confirm("Reset all runs and reference data to the starting state?")) return;
  await api("/api/admin/reset", { method: "POST" });
  toast("Demo data reset");
  load();
  renderSidebar("reference");
});

renderSidebar("reference");
load();
