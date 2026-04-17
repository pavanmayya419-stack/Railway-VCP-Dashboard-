@echo off
echo Creating desktop shortcut...

set SCRIPT="%USERPROFILE%\Desktop\VCP Dashboard.bat"
echo @echo off > %SCRIPT%
echo cd /d "%~dp0" >> %SCRIPT%
echo powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" >> %SCRIPT%

echo.
echo Desktop shortcut created!
echo.
echo Double-click "VCP Dashboard" on your desktop to run.
pause
