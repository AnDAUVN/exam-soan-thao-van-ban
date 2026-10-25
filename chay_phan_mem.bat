@echo off
chcp 65001 > nul
title Hệ Thống Thi Môn Soạn Thảo Văn Bản (Nghị Định 30)

echo ========================================================
echo   HỆ THỐNG THI SOẠN THẢO VĂN BẢN (NGHỊ ĐỊNH 30/2020)
echo ========================================================
echo.
echo [1/2] Đang kiểm tra và cài đặt các thư viện (fastapi, uvicorn)...
python -m pip install fastapi uvicorn python-multipart

echo.
echo [2/2] Đang khởi động máy chủ phòng thi...
echo.
echo Máy chủ đang chạy tại: http://localhost:8000
echo Nhấn Ctrl + C để dừng máy chủ khi kết thúc ca thi.
echo ========================================================
echo.

start http://localhost:8000
cd backend
python main.py

pause
