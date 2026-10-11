"""FloatBar — تول بار عائم زجاجي صغير (pywebview + HTML/CSS/JS)."""
import json
import os
import sys
import threading

import webview

BASE = os.path.dirname(os.path.abspath(__file__))


def res_path(rel):
    """مسار يعمل داخل الـ exe (PyInstaller) وخارجه."""
    try:
        base = sys._MEIPASS  # type: ignore
    except Exception:
        base = BASE
    return os.path.join(base, rel)


UI = res_path(os.path.join("ui", "index.html"))
CONFIG = os.path.join(BASE, "config.json")

from backend.monitor import get_stats, quick_speedtest

window: webview.Window | None = None
tray_icon = None


def load_config():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"opacity": 85, "ontop": True}


def save_config(patch: dict):
    cfg = load_config()
    cfg.update(patch)
    try:
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass


class Api:
    def get_stats(self):
        return get_stats()

    def run_speedtest(self):
        return quick_speedtest()

    _hwnd = None

    @classmethod
    def _find_hwnd(cls):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "FloatBar")
            if hwnd:
                cls._hwnd = hwnd
                return hwnd
        except Exception:
            pass
        return cls._hwnd

    def move_window(self, dx, dy):
        global window
        # الطريقة المباشرة عبر Win32 (لا تعتمد على window.x/y)
        try:
            import ctypes
            hwnd = self._hwnd or self._find_hwnd()
            if hwnd:
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w, h = rect.right - rect.left, rect.bottom - rect.top
                if w > 0 and h > 0:
                    ctypes.windll.user32.MoveWindow(
                        hwnd, rect.left + int(dx), rect.top + int(dy), w, h, True)
                    return
        except Exception:
            pass
        try:
            if window and window.x is not None and window.y is not None:
                window.move(window.x + int(dx), window.y + int(dy))
        except Exception:
            pass

    def set_ontop(self, v):
        global window
        try:
            if window:
                window.on_top = bool(v)
            save_config({"ontop": bool(v)})
        except Exception:
            pass

    def save_opacity(self, v):
        save_config({"opacity": int(v)})

    def save_layout(self, layout, mini):
        save_config({"layout": layout, "mini": bool(mini)})

    def fit(self, w, h):
        """تصغير النافذة على قد المحتوى (منع المساحة البيضاء)."""
        global window
        try:
            if window:
                window.resize(int(w), int(h))
        except Exception:
            pass

    def panel(self, open, base_h=58):
        """تكبير النافذة عند فتح الإعدادات فقط."""
        global window
        try:
            if window:
                w = window.width or 540
                try:
                    base_h = int(base_h)
                except Exception:
                    base_h = 58
                window.resize(int(w), base_h + 260 if open else base_h)
        except Exception:
            pass

    def hide_to_tray(self):
        """إخفاء في شريط المهام السفلي (Tray) بدل القفل."""
        global window
        try:
            if window:
                window.hide()
        except Exception:
            pass

    def show_window(self):
        global window
        try:
            if window:
                window.show()
        except Exception:
            pass

    def quit_app(self):
        global tray_icon
        try:
            if tray_icon:
                tray_icon.stop()
        except Exception:
            pass
        try:
            if window:
                window.destroy()
        except Exception:
            os._exit(0)


def _make_icon():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 20, 58, 44], radius=10, fill=(40, 120, 255, 255))
    d.ellipse([26, 8, 38, 20], fill=(80, 200, 255, 255))
    return img


def run_tray(api: Api):
    global tray_icon
    try:
        import pystray
        from pystray import MenuItem as Item, Menu
        menu = Menu(
            Item("إظهار", lambda: api.show_window(), default=True),
            Item("إخفاء", lambda: api.hide_to_tray()),
            Item("خروج", lambda: api.quit_app()),
        )
        tray_icon = pystray.Icon("FloatBar", _make_icon(), "FloatBar", menu)
        tray_icon.run()
    except Exception as e:
        print("Tray failed:", e)


def _force_true_transparency(title="FloatBar", timeout=15):
    """pywebview يجعل الـ WebView شفافاً لكن الفورم يرسم رمادياً.
    نجعل لون الفورم نفسه شفافاً عبر WS_EX_LAYERED + colorkey (لون الزوايا فعلاً)."""
    import ctypes
    import time
    from collections import Counter

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    LWA_COLORKEY = 0x1
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x80000

    def rgb(rgb_tuple):
        r, g, b = rgb_tuple[:3]
        return r | (g << 8) | (b << 16)

    t0 = time.time()
    hwnd = None
    while time.time() - t0 < timeout:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        print("transparency: window not found")
        return
    try:
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(2.5)  # استقرار الرسم والمقاس
    try:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        from PIL import ImageGrab
        key = (240, 240, 240)
        for _ in range(3):
            shot = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).convert("RGB")
            w, h = shot.size
            pts = []
            for x in range(2, max(w - 2, 3), 4):
                pts += [(x, 1), (x, h - 2)]
            for y in range(2, max(h - 2, 3), 4):
                pts += [(1, y), (w - 2, y)]
            colors = Counter(shot.getpixel(p) for p in pts if 0 <= p[0] < w and 0 <= p[1] < h)
            cand, count = colors.most_common(1)[0]
            # لون الفورم رمادي محايد؛ غير كده يعني النافذة متغطية — أعد المحاولة
            if count >= len(pts) * 0.3 and max(cand) - min(cand) <= 12 and 200 <= sum(cand) / 3 <= 252:
                key = cand
                break
            time.sleep(1.5)
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(hwnd, rgb(key), 0, LWA_COLORKEY)
        print(f"transparency: colorkey={key}")
    except Exception as e:
        print("transparency failed:", e)


def _single_instance():
    """لو فيه نسخة شغالة بالفعل، اظهرها واخرج (منع التكرار)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "FloatBar")
        if hwnd and user32.IsWindowVisible(hwnd):
            try:
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            print("FloatBar already running")
            return False
    except Exception:
        pass
    return True


def main():
    if not _single_instance():
        return
    cfg = load_config()
    api = Api()
    global window
    vertical = cfg.get("layout", "h") == "v"
    window = webview.create_window(
        "FloatBar",
        UI,
        js_api=api,
        width=150 if vertical else 540,
        height=340 if vertical else 58,
        min_size=(120, 50),
        frameless=True,
        on_top=bool(cfg.get("ontop", True)),
        transparent=True,
        background_color="#000000",
        resizable=False,
        shadow=False,
        focus=False,
        text_select=False,
    )
    # شغل الـ Tray في ثريد منفصل (الإخفاء في الأسفل)
    t = threading.Thread(target=run_tray, args=(api,), daemon=True)
    t.start()
    threading.Thread(target=_force_true_transparency, daemon=True).start()
    # إغلاق النافذة = إخفاء في الـ Tray مش خروج
    webview.start(debug=False)
    # لو خرج من الـ webview اقفل الـ tray
    try:
        if tray_icon:
            tray_icon.stop()
    except Exception:
        pass


if __name__ == "__main__":
    # إصلاح sys.prefix المكسور في بعض أجهزة ويندوز (Store install)
    main()
