# FloatBar

شريط مراقبة خفيف لسطح مكتب Windows، بواجهة عربية RTL شفافة ومؤشرات مباشرة للمعالج والذاكرة والشبكة والحرارة والبطارية.

## المتطلبات

- Windows 10 أو أحدث، وPython 3.10+ ‏(64-bit).
- WebView2 Runtime لعرض واجهة pywebview.
- تثبيت الاعتماديات من مجلد المشروع:

```powershell
python -m pip install -r requirements.txt
```

## التشغيل

```powershell
python main.py
```

تُحفظ الإعدادات في `config.json`. قراءة حرارة المعالج تعتمد على توفر مستشعر يدعمه النظام أو WMI/LibreHardwareMonitor؛ عند غياب المستشعر تعرض الواجهة `--` دون إيقاف بقية المؤشرات.

## إنشاء ملف تنفيذي

```powershell
python build_exe.py
```

ينشئ PyInstaller ملف `dist/FloatBar.exe` ويضمّن مجلد `ui` واعتماديات الواجهة وWMI. عند التوزيع، يلزم توفر WebView2 Runtime على الجهاز الهدف. تبقى `config.json` بجوار الملف التنفيذي لتسهيل النسخ الاحتياطي والنقل.

## الواجهة

- `ui/index.html`: بنية RTL وعناصر SVG المضمنة.
- `ui/css/style.css`: الأنماط والحركات دون `backdrop-filter`.
- `ui/js/api.js`: واجهة اتصال pywebview ووضع معاينة المتصفح.
- `ui/js/app.js`: الحالة، الاستطلاع كل ثانية، تحريك القيم، تغيير القياس والسحب.
- `backend/monitor.py`: قراءات psutil، قياس الشبكة، ومستشعر الحرارة في خيط خلفي مهيأ لـ COM.
