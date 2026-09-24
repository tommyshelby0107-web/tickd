// Bulk run: pick a folder (or many PDFs), queue them all, and watch the batch progress live.

const batchId = location.pathname.startsWith("/bulk/") ? decodeURIComponent(location.pathname.split("/")[2]) : null;
let chosen = [];            // File objects picked in the browser
let folderName = "";

const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const isPdf = (f) => f.name.toLowerCase().endsWith(".pdf");

// ---------------------------------------------------------------- pick

async function showPick() {
  document.getElementById("pick").hidden = false;
  document.getElementById("folder-icon").innerHTML = icon("folder", 28);
  document.getElementById("files-icon").innerHTML = icon("upload", 28);
  const folderInput = document.getElementById("folder-input");
  const filesInput = document.getElementById("files-input");
  folderInput.addEventListener("change", () => {
    const files = [...folderInput.files];
    folderName = files[0] ? files[0].webkitRelativePath.split("/")[0] : "Folder";
    choose(files);
  });
  filesInput.addEventListener("change", () => { folderName = "Selected files"; choose([...filesInput.files]); });
  const zone = document.getElementById("files-zone");
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("over");
    folderName = "Dropped files";
    choose([...e.dataTransfer.files]);
  });
  document.getElementById("clear").addEventListener("click", () => choose([]));
  document.getElementById("start").addEventListener("click", startBatch);
  loadBatches();
}

function choose(files) {
  chosen = files.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
  const pdfs = chosen.filter(isPdf);
  const preview = document.getElementById("preview");
  preview.hidden = chosen.length === 0;
  document.getElementById("preview-title").textContent =
    `${folderName}: ${pdfs.length} PDF${pdfs.length === 1 ? "" : "s"}${chosen.length > pdfs.length ? `, ${chosen.length - pdfs.length} other file(s) skipped` : ""}`;
  const start = document.getElementById("start");
  start.textContent = `Process ${pdfs.length} invoice${pdfs.length === 1 ? "" : "s"}`;
  start.disabled = pdfs.length === 0;
  let n = 0;
  document.getElementById("preview-rows").innerHTML = chosen.map((f) => `
    <tr><td class="muted">${isPdf(f) ? ++n : ""}</td><td>${esc(f.webkitRelativePath || f.name)}</td>
      <td class="num">${kb(f.size)}</td>
      <td>${isPdf(f) ? '<span class="pill info">processed</span>' : '<span class="pill plain">skipped, not a PDF</span>'}</td></tr>`).join("");
}

async function startBatch() {
  const start = document.getElementById("start");
  start.disabled = true;
  start.textContent = "Uploading…";
  const form = new FormData();
  chosen.filter(isPdf).forEach((f) => form.append("files", f, f.name));
  form.append("name", folderName);
  try {
    const { batch_id } = await api("/api/batches", { method: "POST", body: form });
    location.href = `/bulk/${batch_id}`;
  } catch (e) {
    toast(e.message);
    start.disabled = false;
    choose(chosen);
  }
}

function tally(runs) {
  const count = (fn) => runs.filter(fn).length;
  return {
    done: count((r) => r.status === "done" || r.status === "resolved"),
    approve: count((r) => r.decision === "Approve"),
    review: count((r) => r.decision === "Review"),
    returned: count((r) => r.decision === "Return to vendor"),
    reject: count((r) => r.decision === "Reject"),
  };
}

async function loadBatches() {
  const list = await api("/api/batches");
  document.getElementById("batches").innerHTML = list.length ? list.map((b) => {
    const t = tally(b.runs);
    const pct = Math.round((100 * t.done) / Math.max(1, b.total));
    return `<tr class="clickable" onclick="location.href='/bulk/${esc(b.batch_id)}'">
      <td><b>${esc(b.name)}</b><div class="quote mono">${esc(b.batch_id)}</div></td>
      <td class="muted">${timeAgo(b.created_at)}</td><td class="num">${b.total}</td>
      <td><div class="progress"><div style="width:${pct}%"></div></div><div class="muted" style="font-size:12px">${t.done} of ${b.total}</div></td>
      <td class="num">${t.approve}</td><td class="num">${t.review}</td><td class="num">${t.returned}</td><td class="num">${t.reject}</td></tr>`;
  }).join("") : '<tr><td colspan="8" class="empty">No batches yet.</td></tr>';
}

// ---------------------------------------------------------------- watch

async function showWatch(id) {
  document.getElementById("watch").hidden = false;
  document.getElementById("batch-label").textContent = `Batch ${id}`;
  const tick = async () => {
    const b = await api(`/api/batches/${id}`);
    render(b);
    const finished = b.runs.every((r) => r.status === "done" || r.status === "resolved");
    if (!finished) setTimeout(tick, 1500);
  };
  tick();
}

function render(b) {
  const t = tally(b.runs);
  const pct = Math.round((100 * t.done) / Math.max(1, b.total));
  const finished = t.done === b.total;
  const started = new Date(b.created_at).getTime();
  const lastEnd = Math.max(...b.runs.map((r) => (r.started_at ? new Date(r.started_at).getTime() + 1000 * (r.seconds || 0) : 0)));
  const secs = ((finished ? lastEnd : Date.now()) - started) / 1000;
  document.getElementById("batch-title").textContent = b.name;
  document.getElementById("batch-sub").textContent = `${b.total} invoice(s) · started ${new Date(b.created_at).toLocaleString()}` +
    (b.skipped.length ? ` · skipped: ${b.skipped.join(", ")}` : "");
  document.getElementById("progress-text").textContent = finished
    ? `Done: ${b.total} invoices in ${secs.toFixed(0)}s · ${Math.round((100 * (t.approve + t.reject)) / b.total)}% decided automatically`
    : `Processing ${t.done} of ${b.total}…`;
  document.getElementById("elapsed").textContent = `${secs.toFixed(0)}s`;
  document.getElementById("progress-bar").style.width = `${pct}%`;
  document.getElementById("counts").innerHTML = [
    ["Approved", t.approve, "var(--green)"], ["Needs review", t.review, "var(--amber)"],
    ["Returned to vendor", t.returned, "var(--violet)"], ["Rejected", t.reject, "var(--red)"],
    ["Waiting", b.total - t.done, "var(--muted)"],
  ].map(([label, n, color]) => `<div class="card kpi" style="box-shadow:none">
      <div class="label">${label}</div><div class="value" style="color:${color}">${n}</div></div>`).join("");
  document.getElementById("batch-rows").innerHTML = b.runs.map((r, i) => {
    const status = r.status === "running" && r.current_stage
      ? `<span class="pill running">${esc(r.current_stage.stage)}</span>`
      : decisionPill(r.decision, r.severity, r.status);
    const why = (r.summary || "").replace(/^(Approved|Rejected|Returned to vendor|Held for [^.]+ review)\. /, "");
    return `<tr class="clickable" onclick="location.href='/runs/${esc(r.run_id)}'">
      <td class="muted">${i + 1}</td><td>${esc(r.file_name)}</td><td>${status}</td>
      <td>${esc(r.vendor_name || "—")}</td><td class="nowrap">${esc(r.invoice_number || "—")}</td>
      <td class="num">${money(r.total, r.currency)}</td>
      <td class="muted" style="max-width:360px;font-size:13px">${esc(why)}</td>
      <td class="num">${r.seconds ? `${r.seconds}s` : "—"}</td></tr>`;
  }).join("");
}

renderSidebar("bulk");
if (batchId) showWatch(batchId); else showPick();
