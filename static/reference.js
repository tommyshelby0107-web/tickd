// Reference data: POs with billed progress, vendor master, invoice registry, policy, and demo reset.

async function load() {
  const data = await api("/api/reference");
  const names = Object.fromEntries(data.vendors.map((v) => [v.vendor_id, v.name]));

  countUp(document.getElementById("po-count"), data.purchase_orders.length);
  document.getElementById("pos").innerHTML = data.purchase_orders.map((po) => `
    <tr>
      <td class="mono"><b>${esc(po.po_number)}</b></td>
      <td>${esc(names[po.vendor_id] || po.vendor_id)}</td>
      <td>${esc(po.description)}</td>
      <td><span class="pill ${po.status === "Open" ? "approve" : "plain"}">${esc(po.status)}</span></td>
      <td class="nowrap">${esc(po.buyer)}</td>
      <td class="num">${money(po.value)}</td>
      <td class="num">${money(po.billed)}</td>
      <td><div class="progress ${po.billed_pct > 100 ? "over" : ""}"><div style="width:0%" data-w="${Math.min(100, po.billed_pct)}"></div></div>
        <div class="sub">${po.billed_pct}%</div></td>
    </tr>`).join("");

  countUp(document.getElementById("vendor-count"), data.vendors.length);
  document.getElementById("vendors").innerHTML = data.vendors.map((v) => `
    <tr>
      <td class="mono">${esc(v.vendor_id)}</td>
      <td><b>${esc(v.name)}</b><div class="sub">${esc(v.address)}</div></td>
      <td><span class="pill ${v.status === "Active" ? "approve" : "reject"}">${esc(v.status)}</span></td>
      <td class="mono">${esc(v.tax_id)}</td>
      <td>${esc(v.bank_name)} <span class="mono">${esc(v.bank_account)}</span></td>
      <td class="nowrap">${esc(v.phone_on_file)}</td>
      <td class="num">${(v.expected_tax_rate * 100).toFixed(1)}%</td>
      <td class="nowrap">${esc(v.payment_terms)}</td>
    </tr>`).join("");

  countUp(document.getElementById("registry-count"), data.registry.length);
  document.getElementById("registry").innerHTML = data.registry.map((r) => `
    <tr>
      <td>${esc(names[r.vendor_id] || r.vendor_id)}</td>
      <td class="nowrap"><b>${esc(r.invoice_number)}</b></td>
      <td class="mono">${esc(r.invoice_key)}</td>
      <td class="num">${money(r.total)}</td>
      <td>${esc(r.status)}${r.run_id ? ` · <a href="/runs/${esc(r.run_id)}">run</a>` : ""}</td>
    </tr>`).join("");

  document.getElementById("policy").innerHTML = Object.entries(data.policy).map(([k, v]) => `
    <tr><td class="mono">${esc(k)}</td><td class="num wrap"><b>${esc(Array.isArray(v) ? v.join(", ") : v)}</b></td></tr>`).join("");

  ["pos", "vendors", "registry", "policy"].forEach((id) => stagger(document.getElementById(id), "tr"));
  nextFrame(() => document.querySelectorAll("[data-w]").forEach((bar) => { bar.style.width = `${bar.dataset.w}%`; }));
}

const resetButton = document.getElementById("reset");
resetButton.innerHTML = `${icon("trash", 16)} Reset demo data`;
resetButton.addEventListener("click", async () => {
  if (!confirm("Reset all runs and reference data to the starting state?")) return;
  await api("/api/admin/reset", { method: "POST" });
  toast("Demo data reset");
  load();
  renderSidebar("reference");
});

renderSidebar("reference");
load();
