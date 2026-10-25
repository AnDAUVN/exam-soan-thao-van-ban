[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:Path = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;" + $env:Path
Set-Location $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   HE THONG THI SOAN THAO VAN BAN (NGHI DINH 30/2020/ND-CP)" -ForegroundColor Cyan
Write-Host "   CONG CU DONG BO & CAP NHAT LEN WEB RENDER (1-CLICK)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Dang kiem tra ma nguon thay doi..." -ForegroundColor Yellow
git add -A

$diff = git status --porcelain
if ([string]::IsNullOrWhiteSpace($diff)) {
    Write-Host "[*] Khong co file nao thay doi so voi phien ban tren GitHub." -ForegroundColor Gray
} else {
    Write-Host "[*] Dang luu cac thay doi moi vao ban commit..." -ForegroundColor Yellow
    $timestamp = Get-Date -Format "dd/MM/yyyy HH:mm:ss"
    git commit -m "Cap nhat tu dong: $timestamp"
}

Write-Host ""
Write-Host "[2/3] Dang day du lieu len GitHub (Render se tu dong cap nhat)..." -ForegroundColor Yellow
Write-Host "(Luu y: Neu trinh duyet mo cua so GitHub, ban chi can bam Authorize/Sign in)" -ForegroundColor DarkGray
Write-Host ""

git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "   CAP NHAT THANH CONG LEN GITHUB & RENDER!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host " - Render dang tu dong nap ban moi (mat khoang 30 - 60 giay)." -ForegroundColor White
    Write-Host " - Cong Sinh Vien : https://exam-soan-thao-van-ban.onrender.com" -ForegroundColor Cyan
    Write-Host " - Cong Giang Vien: https://exam-soan-thao-van-ban.onrender.com/teacher" -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host " [!] Can xac thuc quyen day code len GitHub." -ForegroundColor Red
    Write-Host " Neu co cua so dang nhap GitHub hien ra, ban vui long bam Dang nhap." -ForegroundColor Yellow
    Write-Host "======================================================================" -ForegroundColor Red
}
