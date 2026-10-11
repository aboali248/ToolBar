/* app.js — نعومة عالية + طولي/عرضي + طي + سحب Pointer */
const $ = (id) => document.getElementById(id);
const bar = $("bar");
let lastW = 0, lastH = 0, fitTimer = 0;
function on(id, ev, fn) {
  const el = $(id);
  if (el) el.addEventListener(ev, fn);
  return el;
}
let layout = "h", mini = false;
try {
  layout = localStorage.getItem("floatbar_layout") || "h";
  mini = localStorage.getItem("floatbar_mini") === "1";
} catch (_) {}
function saveLocal(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }

// --- tween ناعم للأرقام ---
const shown = { cpu: 0, ram: 0 };
function tween(el, from, to, dur = 700) {
  const t0 = performance.now();
  function frame(t) {
    const p = Math.min(1, (t - t0) / dur);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * e);
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
function setBar(el, v) {
  if (el) el.style.width = Math.max(0, Math.min(100, v)) + "%";
}

// --- الشفافية ---
function applyOpacity(pct) {
  const alpha = Math.min(1, Math.max(0, pct / 100)) * 0.55;
  document.documentElement.style.setProperty("--chip-alpha", alpha.toFixed(2));
  $("op-val").textContent = pct + "%";
  saveLocal("floatbar_opacity", pct);
  PyApi.saveOpacity(pct);
}
const opEl = on("opacity", "input", (e) => applyOpacity(+e.target.value));
(function initOpacity(){
  let saved = 85;
  try { saved = +(localStorage.getItem("floatbar_opacity") || 85); } catch (_) {}
  $("opacity").value = saved;
  applyOpacity(saved);
})();

// --- طولي / عرضي + طي ---
function applyLayout(animate = false) {
  const doApply = () => {
    bar.classList.toggle("vertical", layout === "v");
    bar.classList.toggle("mini", mini);
    bar.classList.remove("switching");
    fitWindow();
  };
  if (animate) {
    bar.classList.add("switching");
    setTimeout(doApply, 160);
  } else doApply();
  saveLocal("floatbar_layout", layout);
  saveLocal("floatbar_mini", mini ? "1" : "0");
  PyApi.saveLayout(layout, mini);
}
on("btn-orient", "click", () => { layout = (layout === "h" ? "v" : "h"); applyLayout(true); });
on("btn-fold", "click", () => { mini = !mini; applyLayout(true); });
applyLayout(false);

// --- بانل ---
function baseHeight() {
  return Math.ceil(bar.getBoundingClientRect().height) + 8;
}
function popIn(el) {
  try {
    el.animate(
      [{ opacity: 0, transform: "translateY(-10px) scale(.96)" },
       { opacity: 1, transform: "none" }],
      { duration: 320, easing: "cubic-bezier(.34,1.4,.64,1)" });
  } catch (_) {}
}
function openPanel() {
  const p = $("panel");
  if (!p || !p.classList.contains("hidden")) return;
  p.classList.remove("hidden");
  popIn(p);
  // المقاس يتظبط تلقائياً عبر fit (النافذة تكبر لاستيعاب البانل)
}
function closePanel() {
  const p = $("panel");
  if (!p || p.classList.contains("hidden")) return;
  p.classList.add("hidden");
}
on("btn-settings", "click", () => {
  const p = $("panel");
  if (!p) return;
  if (p.classList.contains("hidden")) openPanel(); else closePanel();
});
on("btn-panel-close", "click", closePanel);

// --- أزرار ---
on("btn-hide", "click", () => PyApi.hide());
on("btn-close", "click", () => PyApi.close());
on("ontop", "change", (e) => PyApi.setOnTop(e.target.checked));
on("btn-test", "click", async () => {
  $("test-res").textContent = "جارٍ قياس السرعة...";
  const r = await PyApi.speedtest();
  $("test-res").textContent = r.ok
    ? `السرعة: ${r.mbps} Mb/s (${r.mb}MB في ${r.seconds}s)`
    : "فشل الاختبار: " + (r.error || "");
});

// --- تحديث ناعم كل ثانية ---
window.__m1 = 1; // كل المعالجات اتسجلت
async function tick() {
  try {
    const s = await PyApi.getStats();
    $("down").textContent = s.down_str;
    $("up").textContent = s.up_str;
    tween($("cpu"), shown.cpu, s.cpu); shown.cpu = s.cpu;
    tween($("ram"), shown.ram, s.ram); shown.ram = s.ram;
    setBar($("cpu-bar"), s.cpu);
    setBar($("ram-bar"), s.ram);
    $("temp").textContent = (s.temp == null ? "--" : s.temp);
    $("batt").textContent = (s.battery == null ? "--" : s.battery + "%" + (s.plugged ? " ⚡" : ""));
  } catch (e) {}
}
setInterval(tick, 1000);
tick();

// --- مقاس النافذة على قد المحتوى (بدون زنقة وبدون اهتزاز) ---
function fitWindow(force = false) {
  // ملحوظة: لا نستخدم scrollWidth/scrollHeight لأنها تشمل البانل المطلق (absolute)
  const r = bar.getBoundingClientRect();
  const w = Math.ceil(r.width) + 12;
  const h = Math.ceil(r.height) + 12;
  if (force || Math.abs(w - lastW) > 6 || Math.abs(h - lastH) > 6) {
    lastW = w; lastH = h;
    PyApi.fit(w, h);
  }
}
function scheduleFit() {
  clearTimeout(fitTimer);
  fitTimer = setTimeout(() => fitWindow(false), 300);
}
try {
  new ResizeObserver(scheduleFit).observe(bar);
} catch (_) {}
setTimeout(() => fitWindow(true), 400);
setTimeout(() => fitWindow(true), 1200);

// --- سحب ناعم (Pointer Events + دمج الفريمات) ---
(function enableDrag(){
  const handle = $("drag-handle");
  let sx = 0, sy = 0, lx = 0, ly = 0, dragging = false, raf = 0, pid = null;
  const flush = () => {
    raf = 0;
    if (!dragging) return;
    const dx = lx - sx, dy = ly - sy;
    if (dx || dy) { PyApi.move(dx, dy); sx = lx; sy = ly; }
  };
  const queue = (x, y) => { lx = x; ly = y; if (!raf) raf = requestAnimationFrame(flush); };
  const targets = [bar];
  targets.forEach((el) => {
    el.addEventListener("pointerdown", (e) => {
      if (e.target.closest("button") || e.target.closest("#panel") || e.target.closest("input")) return;
      dragging = true; pid = e.pointerId;
      sx = e.screenX; sy = e.screenY; lx = sx; ly = sy;
      bar.classList.add("dragging");
      try { el.setPointerCapture(e.pointerId); } catch (_) {}
    });
  });
  window.addEventListener("pointermove", (e) => {
    if (dragging && (pid === null || e.pointerId === pid)) queue(e.screenX, e.screenY);
  });
  const end = () => { dragging = false; pid = null; bar.classList.remove("dragging"); if (raf) { cancelAnimationFrame(raf); raf = 0; } };
  window.addEventListener("pointerup", end);
  window.addEventListener("pointercancel", end);
})();
window.__ready = "ok";
