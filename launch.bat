@echo off
rem Urea Plant OTS V1.1 - launcher.
rem
rem Double-click to start the simulator on this machine: the start-up intro, then the engine
rem and its console, as python run.py does; the plant starts when 100% LOAD is pressed.
rem Any arguments are passed to run.py unchanged, for example
rem     launch.bat --port 8766
rem     launch.bat --no-intro

setlocal
title Urea Plant OTS V1.1
cd /d "%~dp0"

rem The interpreter: the Python launcher if present, otherwise python on the PATH.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python was not found. Install Python 3.11 or newer from https://www.python.org
    goto :fail
)

rem The version run.py needs.
%PY% -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 or newer is required. Found:
    %PY% --version
    goto :fail
)

rem The runtime dependencies, named in requirements.txt.
%PY% -c "import PyQt6.QtWidgets, pyqtgraph, numpy" >nul 2>nul
if errorlevel 1 (
    echo The simulator's dependencies are not installed. Install them with:
    echo     %PY% -m pip install -r requirements.txt
    goto :fail
)

%PY% run.py %*
if errorlevel 1 goto :fail
endlocal
exit /b 0

:fail
echo.
echo The simulator did not start. See the messages above.
pause
endlocal
exit /b 1
