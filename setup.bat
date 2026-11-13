@echo off
REM Lens2Mesh - one-click setup for Windows
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python 3.10+ is required: https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) & pause & exit /b 1)
if not exist .venv (
  echo Creating virtual environment...
  %PY% -m venv .venv || (echo Failed to create venv & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Dependency install failed & pause & exit /b 1)
where colmap >nul 2>nul || where COLMAP.bat >nul 2>nul || (
  echo.
  echo NOTE: COLMAP was not found on PATH. Photo reconstruction needs a configured engine.
  echo Download COLMAP-x.y-windows-cuda.zip from https://github.com/colmap/colmap/releases
  echo unzip to C:\COLMAP and add that folder to PATH ^(or set it in Project ^> Preferences^).
)
if not exist "%~dp0..\tools\glomap\bin\glomap.exe" if not exist "%~dp0tools\glomap\bin\glomap.exe" (
  echo.
  echo OPTIONAL: standalone GLOMAP is a fallback for compatible legacy COLMAP engines.
  echo Get a compatible build from https://github.com/colmap/glomap/releases
  echo Place it in tools\glomap ^(tools\glomap\bin\glomap.exe^).
  echo Modern COLMAP has an integrated global mapper; GLOMAP is not required.
)
echo.
echo Setup complete. Start the app with run.bat
pause
