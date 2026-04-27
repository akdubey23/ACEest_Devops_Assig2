@echo off
setlocal EnableDelayedExpansion

REM Resolve Python for Jenkins on Windows when the service account has no user PATH.
REM Optional: set environment variable PYTHON_JENKINS to the full path of python.exe (Jenkins job or node).

set "ACTION=%~1"
if "%ACTION%"=="" (
  echo Usage: %~nx0 install ^| test
  exit /b 1
)

call :resolve_python
if errorlevel 1 (
  echo ERROR: Python 3 not found for this Jenkins agent.
  echo Tried: PYTHON_JENKINS env, %SystemRoot%\py.exe -3, python.org dirs, conda, then PATH.
  echo Fix: Install Python 3 from https://www.python.org/downloads/windows/ ^(include launcher^), or set PYTHON_JENKINS to python.exe.
  exit /b 1
)

if /i "%ACTION%"=="install" goto :install
if /i "%ACTION%"=="test" goto :test
echo Unknown action: %ACTION%
exit /b 1

:install
"%RESOLVED_PY%" -m pip install --upgrade pip || exit /b 1
"%RESOLVED_PY%" -m pip install -r requirements.txt
exit /b %ERRORLEVEL%

:test
if not exist test-results mkdir test-results
if not exist allure-results mkdir allure-results
"%RESOLVED_PY%" -m pytest tests/ -v --tb=short --junitxml=test-results/junit.xml --alluredir=allure-results --html=test-results/pytest-report.html --self-contained-html
set PYEXIT=%ERRORLEVEL%
"%RESOLVED_PY%" scripts\build_test_dashboard.py
exit /b %PYEXIT%

:resolve_python
set "RESOLVED_PY="

if defined PYTHON_JENKINS (
  if exist "%PYTHON_JENKINS%" (
    set "RESOLVED_PY=%PYTHON_JENKINS%"
    exit /b 0
  )
)

if exist "%SystemRoot%\py.exe" (
  for /f "delims=" %%i in ('"%SystemRoot%\py.exe" -3 -c "import sys; print(sys.executable)" 2^>nul') do set "RESOLVED_PY=%%i"
)
if defined RESOLVED_PY if exist "!RESOLVED_PY!" exit /b 0
set "RESOLVED_PY="

for %%V in (314 313 312 311 310 39) do (
  if exist "%ProgramFiles%\Python%%V\python.exe" (
    set "RESOLVED_PY=%ProgramFiles%\Python%%V\python.exe"
    exit /b 0
  )
  if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
    set "RESOLVED_PY=%LocalAppData%\Programs\Python\Python%%V\python.exe"
    exit /b 0
  )
)

REM Registry InstallPath (python.org installer) — often present when PATH is not set for LocalSystem
for %%V in (3.14 3.13 3.12 3.11 3.10 3.9) do (
  for /f "tokens=2*" %%A in ('reg query "HKLM\SOFTWARE\Python\PythonCore\%%V\InstallPath" /ve 2^>nul ^| findstr /i REG_SZ') do (
    set "PYDIR=%%B"
    if exist "!PYDIR!python.exe" (
      set "RESOLVED_PY=!PYDIR!python.exe"
      exit /b 0
    )
  )
  for /f "tokens=2*" %%A in ('reg query "HKLM\SOFTWARE\WOW6432Node\Python\PythonCore\%%V\InstallPath" /ve 2^>nul ^| findstr /i REG_SZ') do (
    set "PYDIR=%%B"
    if exist "!PYDIR!python.exe" (
      set "RESOLVED_PY=!PYDIR!python.exe"
      exit /b 0
    )
  )
)

for %%V in (314 313 312 311 310) do (
  if exist "C:\Python%%V\python.exe" (
    set "RESOLVED_PY=C:\Python%%V\python.exe"
    exit /b 0
  )
)
if exist "C:\Python39\python.exe" (
  set "RESOLVED_PY=C:\Python39\python.exe"
  exit /b 0
)

if exist "%ProgramData%\miniconda3\python.exe" (
  set "RESOLVED_PY=%ProgramData%\miniconda3\python.exe"
  exit /b 0
)
if exist "%ProgramData%\anaconda3\python.exe" (
  set "RESOLVED_PY=%ProgramData%\anaconda3\python.exe"
  exit /b 0
)

py -3 --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "RESOLVED_PY=%%i"
)
if defined RESOLVED_PY if exist "!RESOLVED_PY!" exit /b 0
set "RESOLVED_PY="

python --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%i in ('where python 2^>nul') do (
    set "RESOLVED_PY=%%i"
    if exist "!RESOLVED_PY!" exit /b 0
  )
)
set "RESOLVED_PY="

python3 --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%i in ('where python3 2^>nul') do (
    set "RESOLVED_PY=%%i"
    if exist "!RESOLVED_PY!" exit /b 0
  )
)

exit /b 1
