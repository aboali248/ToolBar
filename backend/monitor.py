"""Non-blocking system metrics for the FloatBar desktop widget."""

from __future__ import annotations

import logging
import threading
import time
import urllib.error
import urllib.request

import psutil

logger = logging.getLogger(__name__)

_net_lock = threading.Lock()
_last_net: tuple[int, int, float] | None = None
_temperature_lock = threading.Lock()
_temperature: float | None = None
_temperature_started = False
_temperature_stop = threading.Event()


def _format_speed(bytes_per_second: float) -> str:
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
    if bytes_per_second >= 1024:
        return f"{bytes_per_second / 1024:.0f} KB/s"
    return f"{bytes_per_second:.0f} B/s"


def _get_net_speed() -> tuple[float, float]:
    """Return download/upload bytes per second using process-wide counters."""
    global _last_net
    now = time.monotonic()
    counters = psutil.net_io_counters()
    if counters is None:
        raise RuntimeError("Network I/O counters are unavailable")
    sent, received = counters.bytes_sent, counters.bytes_recv
    with _net_lock:
        previous = _last_net
        _last_net = (sent, received, now)
    if previous is None:
        return 0.0, 0.0
    old_sent, old_received, old_time = previous
    elapsed = now - old_time
    if elapsed <= 0:
        return 0.0, 0.0
    return (
        max(0.0, (received - old_received) / elapsed),
        max(0.0, (sent - old_sent) / elapsed),
    )


def _read_temperature() -> float | None:
    """Read a CPU temperature where a supported hardware sensor is available."""
    try:
        temperatures = psutil.sensors_temperatures()
    except (AttributeError, OSError, RuntimeError):
        temperatures = {}
    for entries in temperatures.values():
        for entry in entries:
            if entry.current is not None and entry.current > 0:
                return round(float(entry.current), 1)

    try:
        import pythoncom
        import wmi
    except ImportError:
        logger.debug("WMI temperature support is unavailable on this system")
        return None

    pythoncom.CoInitialize()
    try:
        for namespace, query_name in (
            (r"root\wmi", "thermal"),
            (r"root\LibreHardwareMonitor", "sensor"),
            (r"root\OpenHardwareMonitor", "sensor"),
        ):
            try:
                client = wmi.WMI(namespace=namespace)
                if query_name == "thermal":
                    readings = client.MSAcpi_ThermalZoneTemperature()
                    for reading in readings:
                        value = float(reading.CurrentTemperature) / 10.0 - 273.15
                        if 0 < value < 120:
                            return round(value, 1)
                else:
                    for sensor in client.Sensor():
                        name = str(getattr(sensor, "Name", "")).lower()
                        if (
                            getattr(sensor, "SensorType", "") == "Temperature"
                            and "cpu" in name
                        ):
                            value = float(sensor.Value)
                            if 0 < value < 120:
                                return round(value, 1)
            except (AttributeError, OSError, TypeError, ValueError, wmi.x_wmi) as exc:
                logger.debug("Temperature sensor query failed for %s: %s", namespace, exc)
    finally:
        pythoncom.CoUninitialize()
    return None


def _temperature_worker() -> None:
    global _temperature
    while not _temperature_stop.is_set():
        try:
            value = _read_temperature()
            with _temperature_lock:
                _temperature = value
        except Exception:
            logger.exception("Unable to read CPU temperature")
        _temperature_stop.wait(5.0)


def _start_temperature_worker() -> None:
    global _temperature_started
    with _temperature_lock:
        if _temperature_started:
            return
        _temperature_started = True
    threading.Thread(
        target=_temperature_worker,
        name="FloatBarTemperature",
        daemon=True,
    ).start()


def shutdown_monitor() -> None:
    """Stop the background hardware-sensor loop during application shutdown."""
    _temperature_stop.set()


def get_stats() -> dict[str, float | int | bool | str | None]:
    """Collect a lightweight snapshot; hardware temperature is cached off-thread."""
    _start_temperature_worker()
    down_bps, up_bps = _get_net_speed()
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    try:
        battery_info = psutil.sensors_battery()
    except (AttributeError, OSError, RuntimeError) as exc:
        logger.warning("Unable to read battery status: %s", exc)
        battery_info = None
    battery = round(float(battery_info.percent)) if battery_info else None
    plugged = bool(battery_info.power_plugged) if battery_info else None
    counters = psutil.net_io_counters()
    with _temperature_lock:
        temperature = _temperature

    return {
        "down_bps": round(down_bps, 1),
        "up_bps": round(up_bps, 1),
        "down_str": _format_speed(down_bps),
        "up_str": _format_speed(up_bps),
        "cpu": round(float(cpu), 1),
        "ram": round(float(memory.percent), 1),
        "temp": temperature,
        "battery": battery,
        "plugged": plugged,
        "total_sent_mb": round(counters.bytes_sent / 1024 / 1024, 1) if counters else 0.0,
        "total_recv_mb": round(counters.bytes_recv / 1024 / 1024, 1) if counters else 0.0,
    }


def quick_speedtest(
    url: str = "https://speed.cloudflare.com/__down?bytes=5000000",
    timeout: float = 20.0,
) -> dict[str, float | bool | str]:
    """Measure a short download without adding a runtime dependency."""
    start = time.monotonic()
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if time.monotonic() - start >= timeout:
                    break
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        logger.warning("Network speed test failed: %s", exc)
        return {"ok": False, "error": str(exc)}

    elapsed = time.monotonic() - start
    if elapsed <= 0 or total == 0:
        return {"ok": False, "error": "لم يتم استلام بيانات"}
    return {
        "ok": True,
        "mbps": round(total * 8 / elapsed / 1_000_000, 2),
        "mb": round(total / 1024 / 1024, 2),
        "seconds": round(elapsed, 2),
    }
