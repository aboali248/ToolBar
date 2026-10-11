/* UI state, smooth metrics, layout sizing, and pointer-driven native dragging. */
(() => {
  const $ = (id) => document.getElementById(id);
  const bar = $("bar");
  const panel = $("panel");
  const state = { layout: "h", mini: false, opacity: 85, ontop: true, startup: false };
  const activeTweens = new WeakMap();
  let fitFrame = 0;
  let fitTimer = 0;
  let lastSize = { width: 0, height: 0 };
  let opacitySaveTimer = 0;

  function showError(error) {
    const message = error instanceof Error ? error.message : String(error);
    $("app-status").textContent = message;
    console.error("FloatBar:", error);
  }

  function clearError() {
    $("app-status").textContent = "";
  }

  function persist(promise) {
    Promise.resolve(promise).catch(showError);
  }

  function clampPercent(value) {
    return Math.max(0, Math.min(100, Number(value) || 0));
  }

  function formatSpeed(bytesPerSecond) {
    if (bytesPerSecond >= 1_000_000) {
      return `${(bytesPerSecond / 1_000_000).toFixed(1)} MB/s`;
    }
    if (bytesPerSecond >= 1_000) {
      return `${(bytesPerSecond / 1_000).toFixed(0)} KB/s`;
    }
    return `${Math.round(bytesPerSecond)} B/s`;
  }

  function tweenNumber(element, target, formatter, duration = 760) {
    const previous = activeTweens.get(element);
    if (previous) {
      cancelAnimationFrame(previous.frame);
    }
    const from = previous ? previous.value : Number(element.dataset.value || 0);
    const started = performance.now();
    const end = Number.isFinite(Number(target)) ? Number(target) : 0;
    const animation = { value: from, frame: 0 };

    const draw = (now) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      animation.value = from + (end - from) * eased;
      element.textContent = formatter(animation.value);
      element.dataset.value = String(animation.value);
      if (progress < 1) {
        animation.frame = requestAnimationFrame(draw);
      } else {
        animation.value = end;
        element.dataset.value = String(end);
        element.textContent = formatter(end);
      }
    };

    animation.frame = requestAnimationFrame(draw);
    activeTweens.set(element, animation);
  }

  function setProgress(id, value) {
    $(id).style.width = `${clampPercent(value)}%`;
  }

  function applyOpacity(value, save = true) {
    const percentage = Math.max(10, Math.min(100, Math.round(Number(value) || 85)));
    state.opacity = percentage;
    $("opacity").value = String(percentage);
    $("opacity-value").value = `${percentage}%`;
    document.documentElement.style.setProperty("--widget-opacity", String(percentage / 100));
    if (save) {
      window.clearTimeout(opacitySaveTimer);
      opacitySaveTimer = window.setTimeout(() => persist(PyApi.saveOpacity(percentage)), 240);
    }
  }

  function fitWindow() {
    if (fitFrame) {
      cancelAnimationFrame(fitFrame);
    }
    fitFrame = requestAnimationFrame(() => {
      fitFrame = 0;
      const bounds = bar.getBoundingClientRect();
      const width = Math.ceil(bounds.width);
      const height = Math.ceil(bounds.height);
      if (Math.abs(width - lastSize.width) > 2 || Math.abs(height - lastSize.height) > 2) {
        lastSize = { width, height };
        persist(PyApi.fit(width + 2, height + 2));
      }
    });
  }

  function applyLayout(animate = false, save = true) {
    const update = () => {
      bar.classList.toggle("vertical", state.layout === "v");
      bar.classList.toggle("mini", state.mini);
      bar.classList.remove("switching");
      $("btn-orient").setAttribute("aria-pressed", String(state.layout === "v"));
      $("btn-fold").setAttribute("aria-pressed", String(state.mini));
      $("layout-label").textContent = state.layout === "h" ? "تخطيط عمودي" : "تخطيط أفقي";
      $("fold-label").textContent = state.mini ? "إلغاء الطي" : "وضع الطي";
      fitWindow();
    };

    if (animate) {
      bar.classList.add("switching");
      window.setTimeout(update, 140);
    } else {
      update();
    }
    if (save) {
      persist(PyApi.saveLayout(state.layout, state.mini));
    }
  }

  function openSettings() {
    if (!panel.hidden) {
      return;
    }
    panel.hidden = false;
    $("btn-settings").setAttribute("aria-expanded", "true");
    panel.animate(
      [
        { opacity: 0, transform: "translateY(-9px) scale(0.94)" },
        { opacity: 1, transform: "translateY(0) scale(1)" },
      ],
      { duration: 360, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
    );
    fitWindow();
  }

  function closeSettings() {
    if (panel.hidden) {
      return;
    }
    panel.hidden = true;
    $("btn-settings").setAttribute("aria-expanded", "false");
    fitWindow();
  }

  function restore() {
    bar.classList.remove("hiding");
    bar.animate(
      [
        { opacity: 0, transform: "translateY(-8px) scale(0.98)" },
        { opacity: state.opacity / 100, transform: "translateY(0) scale(1)" },
      ],
      { duration: 260, easing: "cubic-bezier(0.34, 1.2, 0.64, 1)" },
    );
  }

  function updateNetwork(stats) {
    const down = Math.max(0, Number(stats.down_bps) || 0);
    const up = Math.max(0, Number(stats.up_bps) || 0);
    tweenNumber($("down"), down, formatSpeed);
    tweenNumber($("up"), up, formatSpeed);
    const total = down + up;
    $("net-chip").dataset.load = total >= 5_000_000
      ? "heavy"
      : total >= 1_000_000 ? "moderate" : "idle";
  }

  function updateBattery(stats) {
    const chip = $("battery-chip");
    const label = $("battery");
    const fill = document.querySelector(".battery-fill");
    if (stats.battery === null || stats.battery === undefined) {
      label.textContent = "--";
      label.dataset.value = "0";
      $("battery-unit").textContent = "";
      chip.dataset.level = "unknown";
      chip.classList.remove("is-charging");
      fill.setAttribute("width", "0");
      return;
    }

    const percentage = clampPercent(stats.battery);
    tweenNumber(label, percentage, (value) => String(Math.round(value)));
    $("battery-unit").textContent = "%";
    chip.dataset.level = percentage < 20 ? "low" : percentage < 60 ? "medium" : "high";
    chip.classList.toggle("is-charging", Boolean(stats.plugged));
    fill.setAttribute("width", String(14 * percentage / 100));
  }

  function updateStats(stats) {
    updateNetwork(stats);
    tweenNumber($("cpu"), clampPercent(stats.cpu), Math.round);
    tweenNumber($("ram"), clampPercent(stats.ram), Math.round);
    setProgress("cpu-bar", stats.cpu);
    setProgress("ram-bar", stats.ram);

    const temperature = stats.temp;
    const temperatureMissing = temperature === null || temperature === undefined;
    $("temp").textContent = temperatureMissing ? "--" : String(Math.round(Number(temperature)));
    $("temp-chip").classList.toggle("sensor-missing", temperatureMissing);
    updateBattery(stats);
    if (!PyApi.preview) {
      clearError();
    }
  }

  async function pollStats() {
    const started = performance.now();
    try {
      updateStats(await PyApi.getStats());
    } catch (error) {
      showError(error);
    } finally {
      const delay = Math.max(0, 1000 - (performance.now() - started));
      window.setTimeout(pollStats, delay);
    }
  }

  async function initialize() {
    try {
      const config = await PyApi.getConfig();
      state.opacity = Math.max(10, Math.min(100, Number(config.opacity) || 85));
      state.layout = config.layout === "v" ? "v" : "h";
      state.mini = Boolean(config.mini);
      state.ontop = Boolean(config.ontop);
      state.startup = Boolean(config.startup);
      applyOpacity(state.opacity, false);
      $("ontop").checked = state.ontop;
      $("startup").checked = state.startup;
      applyLayout(false, false);
    } catch (error) {
      showError(error);
      applyOpacity(state.opacity, false);
      applyLayout(false, false);
    }
    pollStats();
    window.setTimeout(fitWindow, 100);
  }

  $("opacity").addEventListener("input", (event) => applyOpacity(event.target.value));
  $("opacity").addEventListener("change", () => {
    window.clearTimeout(opacitySaveTimer);
    persist(PyApi.saveOpacity(state.opacity));
  });

  $("btn-settings").addEventListener("click", () => {
    if (panel.hidden) {
      openSettings();
    } else {
      closeSettings();
    }
  });
  $("btn-panel-close").addEventListener("click", closeSettings);

  $("btn-orient").addEventListener("click", () => {
    state.layout = state.layout === "h" ? "v" : "h";
    applyLayout(true);
  });
  $("btn-fold").addEventListener("click", () => {
    state.mini = !state.mini;
    applyLayout(true);
  });

  $("ontop").addEventListener("change", (event) => {
    state.ontop = event.target.checked;
    persist(PyApi.setOnTop(state.ontop));
  });

  $("startup").addEventListener("change", async (event) => {
    const checkbox = event.target;
    const requested = checkbox.checked;
    checkbox.disabled = true;
    clearError();
    try {
      const result = await PyApi.setStartup(requested);
      state.startup = Boolean(result && result.enabled);
      checkbox.checked = state.startup;
    } catch (error) {
      checkbox.checked = state.startup;
      showError(error);
    } finally {
      checkbox.disabled = false;
    }
  });

  $("btn-test").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const result = $("speed-result");
    button.disabled = true;
    button.classList.add("is-loading");
    result.hidden = false;
    result.textContent = "جارٍ قياس سرعة التنزيل…";
    clearError();
    try {
      const measurement = await PyApi.speedtest();
      result.textContent = measurement.ok
        ? `سرعة التنزيل ${measurement.mbps} ميغابت/ث · ${measurement.mb} ميغابايت خلال ${measurement.seconds} ث`
        : `تعذر إكمال الاختبار: ${measurement.error}`;
    } catch (error) {
      result.textContent = error instanceof Error ? error.message : String(error);
      showError(error);
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
      fitWindow();
    }
  });

  $("btn-hide").addEventListener("click", () => {
    bar.classList.add("hiding");
    window.setTimeout(() => persist(PyApi.hide()), 150);
  });
  $("btn-close").addEventListener("click", () => {
    bar.classList.add("hiding");
    window.setTimeout(() => persist(PyApi.close()), 150);
  });

  $("drag-handle").addEventListener("pointerdown", (event) => {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    let pointerX = event.screenX;
    let pointerY = event.screenY;
    let queuedX = pointerX;
    let queuedY = pointerY;
    let frame = 0;
    let dragging = true;
    const pointerId = event.pointerId;
    bar.classList.add("dragging");
    event.currentTarget.setPointerCapture(pointerId);

    const move = (pointerEvent) => {
      if (!dragging || pointerEvent.pointerId !== pointerId) {
        return;
      }
      queuedX = pointerEvent.screenX;
      queuedY = pointerEvent.screenY;
      if (!frame) {
        frame = requestAnimationFrame(() => {
          frame = 0;
          const dx = queuedX - pointerX;
          const dy = queuedY - pointerY;
          pointerX = queuedX;
          pointerY = queuedY;
          if (dx || dy) {
            persist(PyApi.move(dx, dy));
          }
        });
      }
    };

    const end = (pointerEvent) => {
      if (pointerEvent.pointerId !== pointerId) {
        return;
      }
      dragging = false;
      if (frame) {
        cancelAnimationFrame(frame);
      }
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      bar.classList.remove("dragging");
      persist(PyApi.savePosition());
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  });

  try {
    new ResizeObserver(() => {
      window.clearTimeout(fitTimer);
      fitTimer = window.setTimeout(fitWindow, 60);
    }).observe(bar);
  } catch (error) {
    console.warn("FloatBar: ResizeObserver is unavailable; using initial sizing", error);
  }

  window.FloatBarApp = { openSettings, closeSettings, restore };
  initialize();
})();
