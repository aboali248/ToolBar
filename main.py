"""FloatBar desktop widget: pywebview host, tray integration, and local settings."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

import webview

from backend.monitor import get_stats, quick_speedtest, shutdown_monitor

BASE = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
CONFIG = BASE / "config.json"
WINDOW_TITLE = "FloatBar"
DEFAULT_CONFIG: dict[str, Any] = {
    "opacity": 85,
    "ontop": True,
    "layout": "h",
    "mini": False,
    "startup": False,
    "x": None,
    "y": 16,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("floatbar")

window: webview.Window | None = None
tray_icon = None
_config_lock = threading.Lock()
_position_lock = threading.Lock()
_window_position: tuple[int, int] | None = None
_instance_mutex = None
_quitting = threading.Event()


def resource_path(relative_path: str) -> Path:
    """Resolve bundled assets both in development and in a PyInstaller build."""
    bundle_root = Path(getattr(sys, "_MEIPASS", BASE))
    return bundle_root / relative_path


def load_config() -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    try:
        with CONFIG.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)
        if not isinstance(loaded, dict):
            raise ValueError("The configuration root must be a JSON object")
        config.update(loaded)
    except FileNotFoundError:
        return config
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Unable to load %s; using safe defaults", CONFIG)
        return config

    try:
        config["opacity"] = max(10, min(100, int(config["opacity"])))
        config["layout"] = "v" if config["layout"] == "v" else "h"
        config["mini"] = bool(config["mini"])
        config["ontop"] = bool(config["ontop"])
        config["startup"] = bool(config["startup"])
        config["x"] = int(config["x"]) if config["x"] is not None else None
        config["y"] = int(config["y"]) if config["y"] is not None else 16
    except (TypeError, ValueError):
        logger.exception("Invalid values in %s; using safe defaults", CONFIG)
        return DEFAULT_CONFIG.copy()
    return config


def save_config(patch: dict[str, Any]) -> None:
    """Persist settings atomically so interruption cannot corrupt config.json."""
    with _config_lock:
        config = load_config()
        config.update(patch)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=CONFIG.parent,
                prefix=".config-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temp_name = temporary.name
                json.dump(config, temporary, ensure_ascii=False, indent=2)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temp_name, CONFIG)
        except OSError:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except OSError:
                    logger.exception("Unable to clean up temporary configuration file")
            logger.exception("Unable to save %s", CONFIG)
            raise


def _set_windows_startup(enabled: bool) -> None:
    """Register or remove the current application in the user's Run key."""
    if sys.platform != "win32":
        raise OSError("تشغيل التطبيق مع بدء النظام متاح على Windows فقط")
    import winreg

    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
    else:
        script = BASE / "main.py"
        command = f'"{sys.executable}" "{script}"'
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, "FloatBar", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "FloatBar")
            except FileNotFoundError:
                pass


class Api:
    """Methods exposed to the JavaScript UI through pywebview."""

    _hwnd: int | None = None

    def get_stats(self) -> dict[str, Any]:
        return get_stats()

    def get_config(self) -> dict[str, Any]:
        return load_config()

    def run_speedtest(self) -> dict[str, Any]:
        return quick_speedtest()

    @classmethod
    def _find_hwnd(cls) -> int | None:
        if cls._hwnd:
            return cls._hwnd
        if sys.platform != "win32":
            return None
        import ctypes

        handle = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        cls._hwnd = handle or None
        return cls._hwnd

    def move_window(self, dx: int, dy: int) -> None:
        """Move by pointer deltas; persist the final position separately."""
        global _window_position
        dx, dy = int(dx), int(dy)
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            handle = self._find_hwnd()
            if handle:
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect)):
                    flags = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE
                    with _position_lock:
                        current_x, current_y = _window_position or (rect.left, rect.top)
                        new_position = (current_x + dx, current_y + dy)
                        if ctypes.windll.user32.SetWindowPos(
                            handle, 0, new_position[0], new_position[1], 0, 0, flags
                        ):
                            _window_position = new_position
                            return
        if window:
            try:
                current_x = window.x if window.x is not None else 0
                current_y = window.y if window.y is not None else 0
                window.move(current_x + dx, current_y + dy)
                with _position_lock:
                    _window_position = (current_x + dx, current_y + dy)
            except (RuntimeError, AttributeError):
                logger.exception("Unable to move the FloatBar window")
                raise

    def save_position(self) -> None:
        with _position_lock:
            position = _window_position
        if position is None and window:
            position = (window.x or 0, window.y or 0)
        if position:
            save_config({"x": position[0], "y": position[1]})

    def set_ontop(self, enabled: bool) -> None:
        if window:
            window.on_top = bool(enabled)
        save_config({"ontop": bool(enabled)})

    def set_startup(self, enabled: bool) -> dict[str, bool]:
        enabled = bool(enabled)
        _set_windows_startup(enabled)
        save_config({"startup": enabled})
        return {"enabled": enabled}

    def save_opacity(self, value: int) -> None:
        save_config({"opacity": max(10, min(100, int(value)))})

    def save_layout(self, layout: str, mini: bool) -> None:
        if layout not in ("h", "v"):
            raise ValueError("layout must be 'h' or 'v'")
        save_config({"layout": layout, "mini": bool(mini)})

    def fit(self, width: int, height: int) -> None:
        if window:
            window.resize(max(100, int(width)), max(44, int(height)))

    def hide_to_tray(self) -> None:
        if window:
            window.hide()

    def show_window(self) -> None:
        if window:
            window.show()
            threading.Timer(0.2, self._restore_ui).start()

    @staticmethod
    def _restore_ui() -> None:
        if not window or _quitting.is_set():
            return
        try:
            window.evaluate_js(
                "window.FloatBarApp && window.FloatBarApp.restore()"
            )
        except Exception:
            logger.exception("Unable to restore the FloatBar interface")

    def open_settings(self) -> None:
        if not window:
            return
        window.show()

        def open_panel() -> None:
            if window and not _quitting.is_set():
                try:
                    window.evaluate_js(
                        "window.FloatBarApp && window.FloatBarApp.restore(); "
                        "window.FloatBarApp && window.FloatBarApp.openSettings()"
                    )
                except Exception:
                    logger.exception("Unable to open the settings panel")

        threading.Timer(0.25, open_panel).start()

    def quit_app(self) -> None:
        _quitting.set()
        if tray_icon:
            try:
                tray_icon.stop()
            except RuntimeError:
                logger.exception("Unable to stop the tray icon")
        shutdown_monitor()
        if window:
            window.destroy()


def _make_icon():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 18, 59, 46), radius=14, fill=(28, 190, 170, 255))
    draw.ellipse((15, 28, 21, 34), fill=(255, 255, 255, 255))
    draw.ellipse((29, 28, 35, 34), fill=(255, 255, 255, 255))
    draw.ellipse((43, 28, 49, 34), fill=(255, 255, 255, 255))
    return image


def run_tray(api: Api) -> None:
    global tray_icon
    try:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("إظهار اللوحة", lambda: api.show_window(), default=True),
            pystray.MenuItem("إخفاء مؤقت", lambda: api.hide_to_tray()),
            pystray.MenuItem("إعدادات المظهر", lambda: api.open_settings()),
            pystray.MenuItem("خروج نهائي", lambda: api.quit_app()),
        )
        tray_icon = pystray.Icon("FloatBar", _make_icon(), "FloatBar", menu)
        tray_icon.run()
    except Exception:
        logger.exception("The system tray icon stopped unexpectedly")


def _single_instance() -> bool:
    """Use a named mutex so hiding the window does not permit duplicate copies."""
    global _instance_mutex
    if sys.platform != "win32":
        return True
    import ctypes

    ctypes.set_last_error(0)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _instance_mutex = kernel32.CreateMutexW(None, False, "FloatBar.SingleInstance")
    if not _instance_mutex:
        raise ctypes.WinError()
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        handle = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if handle:
            ctypes.windll.user32.ShowWindow(handle, 5)
            ctypes.windll.user32.SetForegroundWindow(handle)
        return False
    return True


def _hide_on_window_close() -> bool:
    """Keep the process and tray icon alive when the window close control is used."""
    if not _quitting.is_set() and window:
        window.hide()
        return False
    return True


def main() -> None:
    global window, _window_position
    if not _single_instance():
        logger.info("Another FloatBar instance is already running")
        return

    config = load_config()
    x, y = config["x"], config["y"]
    if x is None:
        x = 30
    _window_position = (x, y)
    api = Api()
    window = webview.create_window(
        WINDOW_TITLE,
        str(resource_path(os.path.join("ui", "index.html"))),
        js_api=api,
        width=150 if config["layout"] == "v" else 540,
        height=340 if config["layout"] == "v" else 58,
        x=x,
        y=y,
        min_size=(100, 44),
        frameless=True,
        on_top=config["ontop"],
        transparent=True,
        background_color="#000000",
        resizable=False,
        shadow=False,
        focus=False,
        text_select=False,
    )
    window.events.closing += _hide_on_window_close
    threading.Thread(target=run_tray, args=(api,), name="FloatBarTray", daemon=True).start()
    try:
        webview.start(debug=False)
    finally:
        _quitting.set()
        shutdown_monitor()
        if tray_icon:
            try:
                tray_icon.stop()
            except RuntimeError:
                logger.exception("Unable to stop the tray icon")


if __name__ == "__main__":
    main()
