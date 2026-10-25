@echo off
title He Thong Thi Soan Thao Van Ban (Nghi Dinh 30)

echo ========================================================
echo   HE THONG THI SOAN THAO VAN BAN (NGHI DINH 30/2020)
echo ========================================================
echo.
echo Dang mo trinh duyet phong thi tai: http://localhost:8000 ...
start http://localhost:8000

echo Dang khoi dong may chu phong thi...
cd /d "%~dp0backend"
python server_lite.py

pause
