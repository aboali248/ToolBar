"""Backend: monitor system stats (net speed, cpu, ram, temp, battery)."""
import time
import psutil

_last_net = None
_last_time = None


def _get_net_speed():
    """Return (down_kbps, up_kbps) based on diff since last call."""
    global _last_net, _last_time
    now = time.time()
    counters = psutil.net_io_counters()
    sent, recv = counters.bytes_sent, counters.bytes_recv
    if _last_net is None:
        _last_net = (sent, recv)
        _last_time = now
        return 0.0, 0.0
    dt = now - _last_time
    if dt <= 0:
        dt = 1.0
    old_sent, old_recv = _last_net
    up = max(0, (sent - old_sent) * 8 / dt / 1000)      # Kbps
    down = max(0, (recv - old_recv) * 8 / dt / 1000)    # Kbps
    _last_net = (sent, recv)
    _last_time = now
    return down, up


def _format_speed(kbps: float) -> str:
    if kbps >= 1000:
        return f"{kbps/1000:.1f} Mb/s"
    return f"{kbps:.0f} Kb/s"


def get_cpu_temp():
    """Try to read CPU/laptop temperature on Windows. Returns float or None."""
    # 1) psutil (works on Linux, usually empty on Windows)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for entries in temps.values():
                for e in entries:
                    if e.current and e.current > 0:
                        return round(float(e.current), 1)
    except Exception:
        pass

    # 2) WMI MSAcpi_ThermalZoneTemperature (Kelvin * 10)
    try:
        import wmi
        w = wmi.WMI(namespace=r"root\wmi")
        for t in w.MSAcpi_ThermalZoneTemperature():
            # CurrentTemperature is in tenths of Kelvin
            c = float(t.CurrentTemperature) / 10.0 - 273.15
            if 0 < c < 120:
                return round(c, 1)
    except Exception:
        pass

    # 3) LibreHardwareMonitor / OpenHardwareMonitor WMI
    for ns in (r"root\LibreHardwareMonitor", r"root\OpenHardwareMonitor"):
        try:
            import wmi
            w = wmi.WMI(namespace=ns)
            for s in w.Sensor():
                try:
                    if getattr(s, "SensorType", "") == "Temperature" and "cpu" in str(getattr(s, "Name", "")).lower():
                        v = float(s.Value)
                        if 0 < v < 120:
                            return round(v, 1)
                except Exception:
                    continue
        except Exception:
            continue
    return None


def get_stats():
    down_kbps, up_kbps = _get_net_speed()
    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = 0
    try:
        ram = psutil.virtual_memory().percent
    except Exception:
        ram = 0
    try:
        batt = psutil.sensors_battery()
        battery = int(batt.percent) if batt else None
        plugged = bool(batt.power_plugged) if batt else None
    except Exception:
        battery, plugged = None, None

    temp = get_cpu_temp()

    counters = psutil.net_io_counters()
    return {
        "down_kbps": round(down_kbps, 1),
        "up_kbps": round(up_kbps, 1),
        "down_str": _format_speed(down_kbps),
        "up_str": _format_speed(up_kbps),
        "cpu": round(float(cpu), 1),
        "ram": round(float(ram), 1),
        "temp": temp,  # None if no sensor
        "battery": battery,
        "plugged": plugged,
        "total_sent_mb": round(counters.bytes_sent / 1024 / 1024, 1),
        "total_recv_mb": round(counters.bytes_recv / 1024 / 1024, 1),
    }


def quick_speedtest(url="https://speed.cloudflare.com/__down?bytes=5000000", timeout=20):
    """Simple download speedtest (no extra dependency). Returns Mbps."""
    import urllib.request
    start = time.time()
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if time.time() - start > timeout:
                    break
    except Exception as e:
        return {"ok": False, "error": str(e)}
    dt = time.time() - start
    if dt <= 0 or total == 0:
        return {"ok": False, "error": "no data"}
    mbps = (total * 8) / dt / 1_000_000
    return {"ok": True, "mbps": round(mbps, 2), "mb": round(total / 1024 / 1024, 2), "seconds": round(dt, 2)}


if __name__ == "__main__":
    print(get_stats())
    time.sleep(1)
    print(get_stats())
