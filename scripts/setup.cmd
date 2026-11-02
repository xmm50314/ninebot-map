@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PYTHONUTF8=1"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv was not found. Install it from https://docs.astral.sh/uv/getting-started/installation/
  exit /b 1
)

uv sync --frozen --python 3.12
if errorlevel 1 exit /b %errorlevel%

".venv\Scripts\python.exe" -m nbmap doctor
exit /b %errorlevel%
