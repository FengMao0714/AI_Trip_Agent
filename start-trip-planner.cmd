@echo off
setlocal

cd /d "%~dp0"
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1"

