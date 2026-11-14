@echo off
setlocal
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONIOENCODING=utf-8"
set "PROJ_NETWORK=OFF"
set "InstallRoot=%~1"
if not defined InstallRoot set /p "InstallRoot=Enter the Lens2Mesh installation folder (contains app and python): "
if not defined InstallRoot exit /b 2
set "InstallRoot=%InstallRoot:"=%"
if not exist "%InstallRoot%\python\python.exe" (
  echo Python was not found. Select the installation folder containing app and python.
  pause
  exit /b 2
)
if not exist "%~dp0verify_survey_math.py" (
  echo Keep verify_survey_math.py beside this BAT, outside the installation folder.
  pause
  exit /b 2
)
"%InstallRoot%\python\python.exe" "%~dp0verify_survey_math.py" --app-dir "%InstallRoot%\app" --output "%~dp0reports\numerical-report"
set "CheckExit=%ERRORLEVEL%"
echo.
if "%CheckExit%"=="0" (echo Numerical checks passed.) else (echo Checks failed or could not finish. Read the report and messages above.)
echo Reports, when generated, are in the reports folder beside this BAT.
pause
exit /b %CheckExit%
