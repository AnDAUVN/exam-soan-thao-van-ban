@echo off
chcp 65001 >nul
echo ====================================================================
echo   KIỂM TRA ĐỊA CHỈ IP WI-FI THẬT CỦA MÁY TÍNH
echo ====================================================================
echo.
echo Dưới đây là danh sách các card mạng trên máy tính:
echo (Hãy tìm mục 'Wireless LAN adapter Wi-Fi' hoặc 'Ethernet', 
echo  xem dòng 'IPv4 Address' dạng 192.168.x.x hoặc 10.x.x.x)
echo.
ipconfig | findstr /i "adapter IPv4"
echo.
echo ====================================================================
echo LƯU Ý: Tuyệt đối KHÔNG dùng IP của 'vEthernet' hoặc 'WSL' (thường là 172.x.x.x)!
echo ====================================================================
pause
