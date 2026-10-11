# Role & Task
You are an expert Full-Stack Python and Frontend Developer specializing in ultra-modern, high-performance Desktop Widgets. Your task is to build a complete, production-ready, and bug-free codebase for a small, floating desktop toolbar widget with a luxurious RTL Arabic UI.

The project must be strictly modular and split into:
- `main.py` (Python backend with psutil, wmi/pythoncom, pystray, pywebview, and a persistent configuration JSON)
- `index.html` (Semantic HTML5 layout optimized for RTL)
- `css/style.css` (Advanced CSS variables, Glassmorphism, animations, and custom scrollbars)
- `js/api.js` (Robust Pywebview bi-directional bridge handling stats data and window control)
- `js/app.js` (State management, SVG injection, real-time polling, and fluid UI animations)

---

## 1. Advanced Layout & Micro-Interactions (RTL Arabic UI)
- **Frameless Design:** Fully transparent, frameless window with NO static background panel. It must look like independent, organic pill-shaped elements floating on the desktop.
- **Dynamic Orientation:** Supports seamless toggling between a horizontal row and a vertical column. The window must dynamically auto-resize and snap to its content without visual flickering.
- **RTL Component Order (Right-to-Left):**
  1. **Drag-Grip:** Interactive matrix dots (handles window moving).
  2. **Live NET Chip:** Stacked Download/Upload speeds (e.g., `↓ 12.4 MB/s` / `↑ 2.1 MB/s`) with dynamic color changing based on network load (Green = Idle, Orange = Moderate, Red = Heavy).
  3. **CPU Temp Chip:** Show current °C. If sensors fail, display a pulsing `--` warning state.
  4. **CPU % Usage Chip:** Live number + an integrated ultra-sleek mini progress bar.
  5. **RAM % Usage Chip:** Live number + an integrated ultra-sleek mini progress bar.
  6. **Battery Status Chip:** Percentage + dynamic icon that changes based on level (Full, Medium, Low) and triggers a fluid electricity arc/bolt pulse animation when charging.
  7. **System Quick-Actions:** 3 distinct mini round buttons: Settings (⚙️), Minimize-to-Tray (➖), and Close (❌).
- **Icons Standard:** Zero emojis or external web fonts (like FontAwesome). Use ONLY highly detailed, raw inline SVG stroke icons (`stroke-width: 2`, `vector-effect: non-scaling-stroke`).

---

## 2. Elite Styling & Fluid Animations (The Core Visuals)
- **Luxury Glassmorphism Asset Styling:** Fully rounded pills (`border-radius: 999px`) using a dark frosted-glass aesthetics:
  - Background: Multi-layered semi-transparent dark radial gradient (`rgba(15,15,20,0.65)` to `rgba(5,5,5,0.85)`).
  - Highlights & Borders: A crisp 1px top white gloss highlight line (`rgba(255,255,255,0.15)`) transitioning into a dark bottom border, backed by a soft, diffuse multi-layered drop shadow.
  - Typography: Bold white premium sans-serif typography (`system-ui`) with a sharp, subtle 3D text shadow for perfect legibility against light or chaotic desktop wallpapers.
  - Performance: Explicitly do NOT use heavy CSS `backdrop-filter: blur` to prevent GPU lagging during drag-and-drop operations.
- **Advanced Animation System:**
  - **Entrance Event:** A dramatic yet smooth cinematic slide-in from the top-screen edge with a custom `cubic-bezier(0.34, 1.56, 0.64, 1)` spring overshoot effect on startup.
  - **Hover Micro-Interactions:** Hovering over any pill or button triggers an instantaneous soft lift (Y-axis translation) combined with a scale-up (`scale(1.05)`) and an inner glowing border accentuation.
  - **Data Tweening:** Numerical changes in network speed, CPU/RAM percentages, and battery cannot just "jump". Implement a highly smooth JavaScript RequestAnimationFrame (rAF) number-counter tweening effect.
  - **Liquid Progress Bars:** Progress bar fills must use CSS transitions with a custom fluid timing curve (`cubic-bezier(0.4, 0, 0.2, 1)`) to look like flowing liquid rather than robotic ticks.

---

## 3. High-Tier Extended Features
- **Data Lifecycle:** High-frequency data pulling happens exactly every 1000ms via the Pywebview bridge.
- **Interactive Chat-Style Settings Bubble:** Clicking the settings cog opens an exquisite popup container structured like an iOS chat bubble (rounded 20px corners with a precise directional tail arrow anchored directly to the cog icon). It enters using an organic spring pop-in scale animation and contains:
  - **Header Zone:** Live green pulsing status dot + Arabic Title ("إعدادات النظام") + Mini version badge pill ("v2.0.4-Pro") + Close button.
  - **Live Transparency Engine:** A custom-styled range slider adjusting widget opacity from 10-100% in real-time, accompanied by a dynamic live percentage chip tracker.
  - **Super-Utility Grid (3 Action Buttons with Smooth Toggles):**
    1. *Speed-Test:* Initiates an async network speed test using an animated loading spinner. The final metric appears as a stylized incoming chat bubble with a soft slide-up effect.
    2. *Layout Switcher:* Rotates the widget between horizontal and vertical forms with an elastic rotation animation on the icon itself.
    3. *Fold/Compact Mode:* Instantly collapses the bar, sliding all hardware chips inside the NET chip to save screen estate, leaving only network speeds visible.
  - **System Level Toggles:** iOS-style animated slide switches for "Always on Top" (فوق الجميع) and "Run on System Startup" (تشغيل تلقائي).
- **System Tray Architecture:** Minimizing smoothly fades out the widget and docks it into the Windows System Tray (`pystray`). The tray context menu must be fully localized in Arabic and feature:
  - إظهار اللوحة (Show Widget - restores with smooth fade-in)
  - إخفاء مؤقت (Hide Widget)
  - إعدادات المظهر (Quick access to open settings bubble)
  - خروج نهائي (Quit Application - cleanly terminates background loops)

---

## 4. Technical Specifications & Robust Backend
- **Python Architecture (3.10+):**
  - Use `psutil` cleanly avoiding resource leaks.
  - Leverage `wmi` with proper `pythoncom.CoInitialize()` wrapping to safely pull accurate CPU core temperatures on separate threads without locking the main thread.
  - Use a JSON-based local configuration file (`config.json`) to persist variables: opacity, orientation mode, fold state, window coordinates, and startup flag.
- **Native Pointer Dragging:** Window movement must be achieved via frontend `pointerdown`, `pointermove`, and `pointerup` event handling. It passes real-time delta coordinates to the Python backend to update the pywebview window position smoothly without hitching.
- **Production Compilation:** Code must be structured safely so that PyInstaller can easily compile it into a single standalone `.exe` using the `--add-data` flag for frontend assets, ensuring the app runs portably with zero external requirements.

---

## Output Requirement
Provide the complete, production-ready, beautifully commented code for all five files. Ensure all Arabic strings are correctly structured for Right-to-Left (RTL) reading and contain no encoding artifacts.
