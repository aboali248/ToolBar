/* A small, typed-by-contract wrapper around pywebview's asynchronous bridge. */
(() => {
  const defaultConfig = {
    opacity: 85,
    ontop: true,
    layout: "h",
    mini: false,
    startup: false,
  };

  const PyApi = {
    available: false,
    preview: false,

    init() {
      const detectBridge = () => {
        this.available = Boolean(window.pywebview && window.pywebview.api);
      };
      detectBridge();
      document.addEventListener("pywebviewready", detectBridge);
      window.addEventListener("load", detectBridge, { once: true });
    },

    async bridge(timeoutMs = 7000) {
      const started = performance.now();
      while (performance.now() - started < timeoutMs) {
        if (window.pywebview && window.pywebview.api) {
          this.available = true;
          return window.pywebview.api;
        }
        if (typeof window.pywebview === "undefined") {
          this.preview = true;
          return null;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 40));
      }
      throw new Error("تعذر الاتصال بخدمة النظام");
    },

    async call(method, ...args) {
      const api = await this.bridge();
      if (!api) {
        return undefined;
      }
      const operation = api[method];
      if (typeof operation !== "function") {
        throw new Error(`واجهة النظام لا توفر العملية ${method}`);
      }
      return operation(...args);
    },

    async getConfig() {
      const result = await this.call("get_config");
      return result && typeof result === "object" ? result : { ...defaultConfig };
    },

    async getStats() {
      const api = await this.bridge();
      if (api) {
        return api.get_stats();
      }
      this.preview = true;
      return {
        down_bps: Math.random() * 1_500_000,
        up_bps: Math.random() * 350_000,
        cpu: Math.random() * 65,
        ram: 38 + Math.random() * 35,
        temp: 52 + Math.random() * 19,
        battery: 55 + Math.random() * 44,
        plugged: Math.random() > 0.78,
      };
    },

    async speedtest() {
      if (!(await this.bridge())) {
        throw new Error("اختبار السرعة متاح عند تشغيل التطبيق على سطح المكتب");
      }
      return this.call("run_speedtest");
    },

    move(dx, dy) {
      return this.call("move_window", dx, dy);
    },

    savePosition() {
      return this.call("save_position");
    },

    fit(width, height) {
      return this.call("fit", width, height);
    },

    saveLayout(layout, mini) {
      return this.call("save_layout", layout, mini);
    },

    hide() {
      return this.call("hide_to_tray");
    },

    close() {
      if (this.available) {
        return this.call("quit_app");
      }
      window.close();
      return Promise.resolve();
    },

    setOnTop(enabled) {
      return this.call("set_ontop", enabled);
    },

    setStartup(enabled) {
      return this.bridge().then((api) => {
        if (!api) {
          throw new Error("تشغيل التطبيق تلقائياً متاح عند تشغيل التطبيق على سطح المكتب");
        }
        return api.set_startup(enabled);
      });
    },

    saveOpacity(value) {
      return this.call("save_opacity", value);
    },

    openSettings() {
      if (window.FloatBarApp) {
        window.FloatBarApp.openSettings();
      }
    },
  };

  PyApi.init();
  window.PyApi = PyApi;
})();
