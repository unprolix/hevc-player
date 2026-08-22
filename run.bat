@echo off
cd /d "%~dp0"
start "" "%LocalAppData%\Programs\Python\Python313\pythonw.exe" hevc_player.py %*
