@echo off
REM Startet das Studien-Dashboard unter Windows.
REM Beim ersten Start wird eine virtuelle Umgebung angelegt und Matplotlib installiert.
cd /d "%~dp0"

set PY=python
where py >nul 2>nul && set PY=py -3

if not exist .venv\Scripts\python.exe (
    echo Einmalige Einrichtung, das kann kurz dauern ...
    %PY% -m venv .venv || goto fehler
    .venv\Scripts\python -m pip install -r requirements.txt || goto fehler
)
start "" .venv\Scripts\pythonw.exe main.py
exit /b 0

:fehler
echo.
echo Einrichtung fehlgeschlagen. Ist Python 3 von python.org installiert?
if exist .venv rmdir /s /q .venv
pause
exit /b 1
