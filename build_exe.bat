@echo off
REM Build FloatBar.exe — شغل من C:\ مع ضبط PYTHONHOME لو بايثون Store مكسور
set PYTHONHOME=C:\Users\el tieb pc\AppData\Local\Programs\Python\Python315
C:\Python315\python.exe -m pip install -r requirements.txt
C:\Python315\python.exe build_exe.py
pause
