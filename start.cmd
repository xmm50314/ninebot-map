@echo off
setlocal
chcp 65001 >nul
call "%~dp0run.cmd" start
set "result=%errorlevel%"

if "%result%"=="2" (
  echo.
  echo Available data was saved; the completeness report contains gaps or items to verify.
) else if not "%result%"=="0" (
  echo.
  echo The operation did not complete fully. Review the messages above.
)

pause >nul
exit /b %result%
