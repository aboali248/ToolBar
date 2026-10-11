/* api.js — طبقة التواصل مع بايثون (pywebview) */
const PyApi = {
  available: false,
  init() {
    // pywebview يحقن window.pywebview بعد التحميل
    const check = () => {
      if (window.pywebview && window.pywebview.api) {
        this.available = true;
      }
    };
    document.addEventListener("pywebviewready", check);
    // fallback: حاول بعد ثانية
    setTimeout(check, 1000);
  },
  async getStats() {
    if (this.available) return await window.pywebview.api.get_stats();
    // وضع تجريبي داخل المتصفح العادي
    return {
      down_str: (Math.random()*8).toFixed(1)+" Mb/s",
      up_str: (Math.random()*2).toFixed(1)+" Mb/s",
      cpu: Math.round(Math.random()*60),
      ram: Math.round(40+Math.random()*30),
      temp: 55+Math.round(Math.random()*10),
      battery: 80, plugged: false
    };
  },
  speedtest() { return this.available ? window.pywebview.api.run_speedtest() : Promise.resolve({ok:false}); },
  move(dx, dy) { if (this.available) window.pywebview.api.move_window(dx, dy); },
  fit(w, h) { if (this.available) window.pywebview.api.fit(w, h); },
  panel(open, baseH) { if (this.available) window.pywebview.api.panel(open, baseH); },
  saveLayout(layout, mini) { if (this.available) window.pywebview.api.save_layout(layout, mini); },
  hide() { if (this.available) window.pywebview.api.hide_to_tray(); },
  close() { if (this.available) window.pywebview.api.quit_app(); else window.close(); },
  setOnTop(v) { if (this.available) window.pywebview.api.set_ontop(v); },
  saveOpacity(v) { if (this.available) window.pywebview.api.save_opacity(v); },
};
PyApi.init();
