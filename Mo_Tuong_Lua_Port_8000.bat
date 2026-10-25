@echo off
chcp 65001 >nul
echo ====================================================================
echo   TIỆN ÍCH MỞ TƯỜNG LỬA WINDOWS (FIREWALL) CHO CỔNG 8000
echo ====================================================================
echo.
echo Đang cấu hình Windows Defender Firewall để sinh viên có thể kết nối...

netsh advfirewall firewall delete rule name="Exam_Server_8000" >nul 2>&1
netsh advfirewall firewall add rule name="Exam_Server_8000" dir=in action=allow protocol=TCP localport=8000 profile=any

if %errorlevel% neq 0 (
    echo [!] LƯU Ý: Vui lòng click CHUỘT PHẢI vào file này và chọn:
    echo     "Run as administrator" (Chạy với quyền Quản trị viên)
    echo     để hệ điều hành cho phép mở tường lửa!
) else (
    echo.
    echo [V] THÀNH CÔNG! Đã mở thông cổng 8000 trên Windows Firewall.
    echo     Sinh viên bây giờ đã có thể truy cập mượt mà, không còn bị "wait".
)
echo.
echo ====================================================================
pause
