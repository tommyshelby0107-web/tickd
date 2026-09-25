// Reference data: POs with billed progress, vendor master, invoice registry, policy, adding vendors and POs,
// and demo reset.

let data = null;

async function load(highlight) {
  data = await api("/api/reference");
  const names = Object.fromEntries(data.vendors.map((v) => [v.vendor_id, v.name]));

  countUp(document.getElementById("po-count"), data.purchase_orders.length);
  document.getElementById("pos").innerHTML = data.purchase_orders.map((po) => `
    <tr data-key="${esc(po.po_number)}">
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
    <tr data-key="${esc(v.vendor_id)}">
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
  if (highlight) {                     // the row just added: bring it into view and let it glow
    const row = document.querySelector(`tr[data-key="${CSS.escape(highlight)}"]`);
    if (row) { row.scrollIntoView({ block: "center", behavior: "smooth" }); setTimeout(() => replay(row, "flash"), 350); }
  }
}

// ---------------------------------------------------------------- the add forms (one clay dialog)

const modal = document.getElementById("modal");

function field(id, label, { required = false, type = "text", placeholder = "", hint = "", span = false, value = "", attrs = "" } = {}) {
  return `<div class="field${span ? " span-2" : ""}">
    <label for="${id}">${label}${required ? " <b>*</b>" : ""}</label>
    <input class="input" id="${id}" type="${type}" placeholder="${esc(placeholder)}" value="${esc(value)}" ${required ? "required" : ""} ${attrs}>
    ${hint ? `<span class="hint">${hint}</span>` : ""}</div>`;
}

function select(id, label, options, { required = false, span = false } = {}) {
  return `<div class="field${span ? " span-2" : ""}">
    <label for="${id}">${label}${required ? " <b>*</b>" : ""}</label>
    <select class="input" id="${id}" ${required ? "required" : ""}>${options.map(([value, text]) =>
      `<option value="${esc(value)}">${esc(text)}</option>`).join("")}</select></div>`;
}

function openSheet(title, subtitle, body, submitLabel, onSubmit) {
  modal.innerHTML = `
    <form class="sheet" novalidate>
      <div class="sheet-head">
        <div><h2 id="modal-title">${title}</h2><p class="sub" style="margin:4px 0 0">${subtitle}</p></div>
        <button type="button" class="btn btn-sm" data-close aria-label="Close">${icon("x", 16)}</button>
      </div>
      ${body}
      <div class="form-error" hidden></div>
      <div class="sheet-actions">
        <button type="button" class="btn" data-close>Cancel</button>
        <button type="submit" class="btn btn-primary">${icon("check", 16)} ${submitLabel}</button>
      </div>
    </form>`;
  const form = modal.querySelector("form");
  modal.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => modal.close()));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = form.querySelector(".form-error");
    const missing = [...form.querySelectorAll("[required]")].find((el) => !el.value.trim());
    if (missing) { showError(error, `Please fill in ${form.querySelector(`label[for="${missing.id}"]`)?.textContent.replace("*", "").trim() || "the required fields"}.`); missing.focus(); return; }
    const submit = form.querySelector("[type=submit]");
    submit.disabled = true;
    try {
      await onSubmit(form);
      modal.close();
    } catch (err) {
      showError(error, err.message);
    } finally {
      submit.disabled = false;
    }
  });
  modal.showModal();
  setTimeout(() => form.querySelector("input, select")?.focus(), 60);
}

function showError(el, message) {
  el.textContent = message;
  el.hidden = false;
  replay(el, "shake-once");
}

// close when the backdrop (outside the sheet) is clicked
modal.addEventListener("click", (e) => { if (e.target === modal) modal.close(); });

const val = (id) => document.getElementById(id).value.trim();
const num = (id) => Number(document.getElementById(id).value || 0);

function openVendorForm() {
  openSheet("Add a vendor", "Invoices from this vendor are matched by name, alias or tax ID.", `
    <div class="form-grid">
      ${field("v-name", "Vendor name", { required: true, span: true, placeholder: "Northgate Industrial Solutions LLC" })}
      ${field("v-aliases", "Also known as", { span: true, placeholder: "Northgate Industrial, Northgate", hint: "Other names it prints on invoices, separated by commas" })}
      ${field("v-tax", "Tax ID", { placeholder: "83-5519024" })}
      ${select("v-status", "Status", [["Active", "Active"], ["Blocked", "Blocked: never pay"]])}
      ${field("v-address", "Address", { span: true, placeholder: "700 Mill Road, Akron, OH 44308" })}
      ${field("v-phone", "Phone on file", { placeholder: "(330) 555-0114", hint: "Called to verify a bank-detail change" })}
      ${field("v-email", "Billing email", { type: "email", placeholder: "ar@northgate.example", hint: "Emailed invoices should come from this domain" })}
      ${field("v-bank", "Bank name", { placeholder: "Liberty Harbor Bank" })}
      ${field("v-account", "Account number", { required: true, placeholder: "440187723309", attrs: 'inputmode="numeric"', hint: "An invoice quoting any other account is held" })}
      ${field("v-routing", "Routing number", { placeholder: "021214891", attrs: 'inputmode="numeric"' })}
      ${field("v-rate", "Sales tax rate (%)", { type: "number", value: "0", attrs: 'min="0" max="30" step="0.25"' })}
      ${field("v-terms", "Payment terms", { value: "Net 30" })}
    </div>`, "Add vendor", async () => {
    const vendor = await api("/api/vendors", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: val("v-name"), aliases: val("v-aliases").split(",").map((a) => a.trim()).filter(Boolean), tax_id: val("v-tax"),
        status: val("v-status"), address: val("v-address"), phone_on_file: val("v-phone"), email: val("v-email"),
        bank_name: val("v-bank"), bank_account: val("v-account"), bank_routing: val("v-routing"),
        tax_rate_pct: num("v-rate"), payment_terms: val("v-terms"),
      }),
    });
    toast(`${vendor.name} added as ${vendor.vendor_id}`);
    coco.celebrate("a new friend!");
    await load(vendor.vendor_id);
  });
}

function lineRow() {
  return `<tr class="po-line">
    <td><input class="input" data-k="sku" placeholder="NG-GLV-NTR"></td>
    <td><input class="input" data-k="description" placeholder="Nitrile gloves, box of 100"></td>
    <td><input class="input num" data-k="qty_ordered" type="number" min="0" step="any" placeholder="50"></td>
    <td><input class="input num" data-k="unit_price" type="number" min="0" step="any" placeholder="11.80"></td>
    <td><input class="input num" data-k="qty_received" type="number" min="0" step="any" placeholder="0"></td>
    <td><button type="button" class="btn btn-sm remove-line" aria-label="Remove line">${icon("x", 14)}</button></td>
  </tr>`;
}

function openPOForm() {
  const vendors = [...data.vendors].sort((a, b) => a.name.localeCompare(b.name))
    .map((v) => [v.vendor_id, `${v.name} (${v.vendor_id})${v.status === "Blocked" ? ", blocked" : ""}`]);
  openSheet("Add a purchase order", "Invoices are matched against these lines: prices, quantities and what was received.", `
    <div class="form-grid">
      ${select("p-vendor", "Vendor", vendors, { required: true, span: true })}
      ${field("p-number", "PO number", { placeholder: data.next_po_number, hint: `Leave blank for ${esc(data.next_po_number)}` })}
      ${field("p-buyer", "Buyer", { placeholder: "Dana Whitfield" })}
      ${field("p-desc", "Description", { placeholder: "Safety consumables" })}
      ${select("p-status", "Status", [["Open", "Open"], ["Closed", "Closed"]])}
    </div>
    <div class="lines-head"><h3>Lines</h3><span class="sub" id="p-total"></span></div>
    <div class="lines-wrap"><table class="lines-table">
      <thead><tr><th>SKU</th><th>Description <b>*</b></th><th class="num">Ordered <b>*</b></th><th class="num">Unit price <b>*</b></th><th class="num">Received</th><th></th></tr></thead>
      <tbody id="p-lines">${lineRow()}</tbody></table></div>
    <button type="button" class="btn btn-sm" id="p-add-line" style="margin-top:10px">${icon("run", 14)} Add line</button>`,
  "Add PO", async () => {
    const lines = [...document.querySelectorAll(".po-line")].map((row) => {
      const get = (k) => row.querySelector(`[data-k="${k}"]`).value.trim();
      return { sku: get("sku"), description: get("description"), qty_ordered: Number(get("qty_ordered") || 0),
               unit_price: Number(get("unit_price") || 0), qty_received: Number(get("qty_received") || 0) };
    }).filter((l) => l.sku || l.description || l.qty_ordered || l.unit_price);
    if (!lines.length) throw new Error("Add at least one line.");
    const po = await api("/api/purchase_orders", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vendor_id: val("p-vendor"), po_number: val("p-number"), buyer: val("p-buyer"),
                             description: val("p-desc"), status: val("p-status"), lines }),
    });
    toast(`${po.po_number} added with ${po.lines.length} line${po.lines.length === 1 ? "" : "s"}`);
    coco.celebrate("ooh, a new PO!");
    await load(po.po_number);
  });
  const body = document.getElementById("p-lines");
  const total = () => {
    const sum = [...body.querySelectorAll(".po-line")].reduce((s, row) =>
      s + Number(row.querySelector('[data-k="qty_ordered"]').value || 0) * Number(row.querySelector('[data-k="unit_price"]').value || 0), 0);
    document.getElementById("p-total").textContent = sum ? `PO value ${money(sum)}` : "";
  };
  document.getElementById("p-add-line").addEventListener("click", () => {
    body.insertAdjacentHTML("beforeend", lineRow());
    body.lastElementChild.querySelector("input").focus();
  });
  body.addEventListener("click", (e) => {
    const remove = e.target.closest(".remove-line");
    if (remove && body.children.length > 1) { remove.closest("tr").remove(); total(); }
  });
  body.addEventListener("input", total);
}

document.getElementById("add-vendor").innerHTML = `${icon("run", 16)} Add vendor`;
document.getElementById("add-po").innerHTML = `${icon("run", 16)} Add PO`;
document.getElementById("add-vendor").addEventListener("click", openVendorForm);
document.getElementById("add-po").addEventListener("click", openPOForm);

const resetButton = document.getElementById("reset");
resetButton.innerHTML = `${icon("trash", 16)} Reset demo data`;
resetButton.addEventListener("click", async () => {
  if (!confirm("Reset all runs and reference data to the starting state? Vendors and POs you added are removed too.")) return;
  await api("/api/admin/reset", { method: "POST" });
  toast("Demo data reset");
  load();
  renderSidebar("reference");
});

renderSidebar("reference");
load();
