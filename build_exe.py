import PyInstaller.__main__
import os

BASE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    "main.py",
    "--name=FloatBar",
    "--noconsole",
    "--windowed",
    "--onefile",
    f"--add-data=ui{os.pathsep}ui",
    "--collect-all=webview",
    "--collect-all=pystray",
    "--collect-all=PIL",
    "--hidden-import=wmi",
    "--hidden-import=psutil",
])
print("Done: dist/FloatBar.exe")
