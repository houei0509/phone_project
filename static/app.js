// Client: goi API cua server Flask bang fetch() va ve giao dien.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const NO_SEP = new Set(["Year", "Cluster", "Rank"]);          // cot khong dung dau phay ngan cach hang nghin
const fmt = (v, col) => v === null || v === undefined ? "N/a" : typeof v === "number"
  ? (NO_SEP.has(col) ? String(v) : v.toLocaleString("en-US", { maximumFractionDigits: 2 })) : esc(v);
// Ten hien thi than thien cho cac cot (ten goc van dung trong API/du lieu). Sua cho dung y nhom neu muon.
const LABELS = {
  Name: "Tên máy", Brand: "Hãng", Year: "Năm ra mắt", Cluster: "Cụm", So_may: "Số máy", Rank: "Hạng", Value: "Giá trị",
  Median: "Trung vị", Mean: "Trung bình", Std: "Độ lệch chuẩn",
  Weight_g: "Cân nặng (g)", Length_mm: "Chiều dài (mm)", Width_mm: "Chiều rộng (mm)", Thickness_mm: "Độ dày (mm)",
  Display_inch: "Kích thước màn hình (inch)", ScreenToBody_pct: "Tỉ lệ màn hình/thân máy (%)",
  Res_W: "Độ phân giải ngang (px)", Res_H: "Độ phân giải dọc (px)", PPI: "Mật độ điểm ảnh (PPI)",
  Refresh_Hz: "Tần số quét (Hz)", Peak_nits: "Độ sáng tối đa (nits)",
  Chipset_nm: "Tiến trình chip (nm)", CPU_cores: "Số nhân CPU",
  RAM_GB: "RAM tối đa (GB)", Storage_GB: "Bộ nhớ trong tối đa (GB)", SD_slot: "Khe thẻ nhớ (1 = có)",
  Battery_mAh: "Dung lượng pin (mAh)", Charge_W: "Công suất sạc có dây (W)", Wireless_W: "Công suất sạc không dây (W)",
  MainCam_MP: "Camera chính (MP)", MainCam_lenses: "Số ống kính camera sau", SelfieCam_MP: "Camera selfie (MP)",
  NFC: "NFC (1 = có)", Jack_3_5mm: "Jack tai nghe 3.5mm (1 = có)", IP_rating: "Chuẩn chống nước/bụi (số IP)",
  Bluetooth_ver: "Phiên bản Bluetooth", AnTuTu: "Điểm AnTuTu", GeekBench: "Điểm GeekBench", Price_EUR: "Giá GSMArena (EUR)", Price_VND: "Giá CellphoneS (VND)",
};
const L = (c) => LABELS[c] || c;
const COLORS = ["#2f6fed", "#f5821f", "#2ca58d", "#d6336c", "#8e6bd8", "#9aa0a6", "#c8a400", "#17a2b8"];
let meta = null, phones = [], sortKey = null, sortAsc = true;
const loaded = {};

async function api(url, opts) {
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (e) { /* khong phai JSON */ }
  if (!res.ok) throw new Error(data.error || `Loi ${res.status}`);
  return data;
}
function say(text) { const m = $("msg"); m.hidden = !text; m.textContent = text || ""; }
function table(cols, rows, labels) {
  const head = cols.map((c, i) => `<th class="${typeof rows[0]?.[c] === "number" ? "num" : ""}">${esc(labels ? labels[i] : L(c))}</th>`).join("");
  const body = rows.map((r) => "<tr>" + cols.map((c) => `<td class="${typeof r[c] === "number" ? "num" : ""}">${fmt(r[c], c)}</td>`).join("") + "</tr>").join("");
  return `<table><tr>${head}</tr>${body}</table>`;
}
const wrap = (html) => `<div class="scroll">${html}</div>`;

// ---------- Tab 1: bang du lieu ----------
function renderPhones() {
  const q = $("q").value.trim().toLowerCase(), b = $("brandFilter").value;
  let rows = phones.filter((r) => (!b || r.Brand === b) && (!q || r.Name.toLowerCase().includes(q)));
  if (sortKey) rows = [...rows].sort((x, y) => {
    const a = x[sortKey], c = y[sortKey];
    if (a === null) return 1; if (c === null) return -1;           // N/a luon o cuoi
    return (a < c ? -1 : a > c ? 1 : 0) * (sortAsc ? 1 : -1);
  });
  $("count").textContent = `${rows.length}/${phones.length} máy`;
  const cols = meta.table_cols;
  $("phoneTable").innerHTML = "<tr>" + cols.map((c) => `<th data-k="${c}" class="${c === "Name" || c === "Brand" ? "" : "num"}">${esc(L(c))}${sortKey === c ? (sortAsc ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>"
    + rows.map((r) => "<tr>" + cols.map((c) => `<td class="${typeof r[c] === "number" ? "num" : ""}">${fmt(r[c], c)}</td>`).join("") + "</tr>").join("");
  $("phoneTable").querySelectorAll("th").forEach((th) => th.onclick = () => {
    sortAsc = sortKey === th.dataset.k ? !sortAsc : true; sortKey = th.dataset.k; renderPhones();
  });
}
async function initData() {
  phones = await api("/api/phones");
  meta.brands.forEach((b) => $("brandFilter").insertAdjacentHTML("beforeend", `<option>${esc(b)}</option>`));
  $("q").oninput = $("brandFilter").onchange = renderPhones;
  renderPhones();
}

// ---------- Tab 2: thong ke ----------
async function loadStats() {
  say("");
  try {
    const d = await api("/api/stats?attr=" + encodeURIComponent($("attrSelect").value));
    const tops = (rows) => table(["Rank", "Name", "Brand", "Value"], rows);
    $("statsBody").innerHTML =
      (d.best ? `<p><b>Hãng tốt nhất:</b> ${esc(d.best.BestBrand)} (trung bình ${fmt(d.best.MeanValue)}, tiêu chí: ${d.best.Rule === "lowest" ? "thấp nhất" : "cao nhất"})</p>` : `<p class="muted">Thống kê này không có tiêu chí "tốt hơn" rõ ràng.</p>`)
      + "<h3>Median / Mean / Std</h3>" + wrap(table(["Brand", "Median", "Mean", "Std"], d.summary))
      + `<div class="grid2"><div><h3>3 máy cao nhất</h3>${tops(d.highest)}</div><div><h3>3 máy thấp nhất</h3>${tops(d.lowest)}</div></div>`
      + "<h3>Histogram</h3><div class='grid2'>"
      + (d.hist_all ? `<img class="plot" src="${d.hist_all}" alt="histogram toàn bộ">` : "")
      + (d.hist_brand ? `<img class="plot" src="${d.hist_brand}" alt="histogram theo hãng">` : "") + "</div>";
  } catch (e) { $("statsBody").innerHTML = ""; say(e.message); }
}
async function initStats() {
  if (!meta.stats_attrs.length) { say("Chưa có kết quả phần II. Chạy: python backend/stats.py"); return; }
  $("attrSelect").innerHTML = [...meta.stats_attrs].sort((a, b) => L(a).localeCompare(L(b), "vi")).map((a) => `<option value="${esc(a)}">${esc(L(a))}</option>`).join("");
  $("attrSelect").onchange = loadStats;
  loadStats();
}

// ---------- Tab 3: phan cum ----------
async function initClusters() {
  try {
    const d = await api("/api/clusters");
    $("clusterBody").innerHTML =
      `<p>K-means chia thành <b>${d.k}</b> cụm (dữ liệu đã chuẩn hóa), giảm xuống 2 chiều bằng PCA để vẽ. Rê chuột lên điểm để xem tên máy.</p>`
      + `<div class="chartbox"><canvas id="pcaChart"></canvas></div>`
      + "<h3>Đặc điểm trung bình từng cụm</h3>" + wrap(table(Object.keys(d.profile[0]), d.profile))
      + "<h3>Số máy theo cụm và hãng</h3>" + wrap(table(Object.keys(d.by_brand[0]), d.by_brand))
      + (d.elbow ? `<h3>Chọn số cụm k (Elbow và Silhouette)</h3><img class="plot" src="${d.elbow}" alt="elbow">` : "");
    if (typeof Chart === "undefined") {                 // khong tai duoc Chart.js (mat mang): dung anh PNG
      $("pcaChart").parentElement.innerHTML = d.pca_img ? `<img class="plot" src="${d.pca_img}" alt="PCA">` : "<p class='muted'>Không tải được thư viện biểu đồ.</p>";
      return;
    }
    const ids = [...new Set(d.points.map((p) => p.Cluster))].sort();
    new Chart($("pcaChart"), {
      type: "scatter",
      data: { datasets: ids.map((c, i) => ({
        label: "Cụm " + c, backgroundColor: COLORS[i % COLORS.length] + "cc", pointRadius: 4,
        data: d.points.filter((p) => p.Cluster === c).map((p) => ({ x: p.PC1, y: p.PC2, name: p.Name, brand: p.Brand })) })) },
      options: { maintainAspectRatio: false,
        scales: { x: { title: { display: true, text: "PC1" } }, y: { title: { display: true, text: "PC2" } } },
        plugins: { tooltip: { callbacks: { label: (c) => `${c.raw.name} (${c.raw.brand})` } } } },
    });
  } catch (e) { say(e.message); }
}

// ---------- Tab 4: radar ----------
function initRadar() {
  $("names").innerHTML = meta.names.map((n) => `<option value="${esc(n)}">`).join("");
  const defaults = ["RAM_GB", "Battery_mAh", "MainCam_MP", "Charge_W", "Weight_g"];
  $("attrChecks").innerHTML = meta.attrs.map((a) => `<label><input type="checkbox" value="${esc(a)}" ${defaults.includes(a) ? "checked" : ""}> ${esc(L(a))}</label>`).join("");
  $("radarBtn").onclick = async () => {
    say("");
    const attrs = [...document.querySelectorAll("#attrChecks input:checked")].map((i) => i.value);
    const qs = new URLSearchParams({ p1: $("p1").value, p2: $("p2").value, attrs: attrs.join(",") });
    try {
      const d = await api("/api/radar?" + qs);
      $("radarOut").innerHTML = `<div class="grid2"><img class="plot" src="${d.image}?t=${Date.now()}" alt="radar">`
        + `<div>${wrap(table(["attr", "v1", "v2"], d.rows.map((r) => ({ ...r, attr: L(r.attr) })), ["Thuộc tính", d.names[0], d.names[1]]))}`
        + `<p class="muted">Biểu đồ chuẩn hóa mỗi trục về 0–100% (thấp nhất–cao nhất trong toàn bộ máy). Với cân nặng, giá trị cao nghĩa là nặng hơn, không phải tốt hơn.</p></div></div>`;
    } catch (e) { $("radarOut").innerHTML = ""; say(e.message); }
  };
}

// ---------- Tab 5: du doan gia ----------
function initPrice() {
  const p = meta.predict;
  if (!p) { say("Chưa có mô hình giá. Chạy: python backend/price_model.py"); return; }
  $("priceForm").innerHTML = `<label>Hãng<select id="pBrand">${p.brands.map((b) => `<option>${esc(b)}</option>`).join("")}</select></label>`
    + p.fields.map((f) => `<label>${esc(L(f.name))}<input type="number" step="any" data-f="${esc(f.name)}" value="${f.default}" min="${f.min}" max="${f.max}"></label>`).join("")
    + `<label>&nbsp;<button id="predictBtn">Ước lượng giá</button></label>`;
  $("predictBtn").onclick = async () => {
    say("");
    const specs = {};
    document.querySelectorAll("#priceForm input[data-f]").forEach((i) => { specs[i.dataset.f] = i.value; });
    try {
      const d = await api("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand: $("pBrand").value, specs }) });
      $("priceOut").innerHTML = `<div class="result"><div class="big">≈ ${d.eur.toLocaleString("en-US")} €</div>`
        + (d.low ? `<p>Khoảng ${d.low.toLocaleString("en-US")} – ${d.high.toLocaleString("en-US")} € (sai số trung vị của mô hình ≈ ${d.ape}%)</p>` : "")
        + (d.vnd ? `<p>Quy đổi tham khảo: ≈ ${d.vnd.toLocaleString("en-US")} đ (tỉ lệ giữa hai nguồn giá: ${Math.round(d.ratio).toLocaleString("en-US")} đ/€, không phải tỉ giá)</p>` : "")
        + `<p class="muted">Mô hình: ${esc(d.model || "")}. Ước lượng chỉ mang tính tham khảo, không phản ánh khuyến mãi hay định vị thương hiệu.</p></div>`;
    } catch (e) { $("priceOut").innerHTML = ""; say(e.message); }
  };
}

// ---------- Khoi dong ----------
const inits = { data: initData, stats: initStats, clusters: initClusters, radar: initRadar, price: initPrice };
async function open(tab) {
  say("");
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === "tab-" + tab));
  if (!loaded[tab]) { loaded[tab] = true; try { await inits[tab](); } catch (e) { say(e.message); } }
}
(async () => {
  try {
    meta = await api("/api/meta");
    $("subtitle").textContent += ` · ${meta.n_phones} điện thoại`;
  } catch (e) { say("Không tải được dữ liệu: " + e.message); return; }
  document.querySelectorAll(".tabs button").forEach((b) => b.onclick = () => open(b.dataset.tab));
  open("data");
})();