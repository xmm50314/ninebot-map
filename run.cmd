@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
  call "scripts\setup.cmd"
  if errorlevel 1 exit /b 1
)

if not "%~1"=="" goto with_args

".venv\Scripts\python.exe" -m nbmap map
set "result=%errorlevel%"
if not "%result%"=="0" pause
exit /b %result%

:with_args
".venv\Scripts\python.exe" -m nbmap %*
exit /b %errorlevel%
