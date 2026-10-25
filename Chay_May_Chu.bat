@echo off
chcp 65001 >nul
title HỆ THỐNG THI SOẠN THẢO VĂN BẢN (NGHỊ ĐỊNH 30/2020)
cd /d "%~dp0\backend"
python server_lite.py
if %errorlevel% neq 0 (
    echo.
    echo Không thể chạy python server_lite.py. Kiểm tra xem máy đã cài Python chưa.
    pause
)
