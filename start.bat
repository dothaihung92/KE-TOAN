@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   PHAN MEM TRA CUU HOA DON DIEN TU - Khoi dong
echo ============================================================

where python >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python.
    echo Hay cai Python tai https://www.python.org/downloads/
    echo ^(nho tick vao o "Add Python to PATH" khi cai^), roi chay lai file nay.
    pause
    exit /b 1
)

echo.
echo [1/3] Dang cap nhat ma nguon moi nhat tu Git ^(neu co^)...
git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 (
    git pull
    if errorlevel 1 (
        echo   Khong cap nhat duoc ^(co the do mang hoac co thay doi chua luu^), tiep tuc chay ban hien tai.
    )
) else (
    echo   Bo qua ^(thu muc nay khong phai Git repo^).
)

echo.
echo [2/3] Dang cai dat / cap nhat thu vien can thiet...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [LOI] Cai dat thu vien that bai. Kiem tra ket noi mang roi chay lai file nay.
    pause
    exit /b 1
)

echo.
echo [3/3] Dang khoi dong phan mem...
echo ============================================================
python run_web.py

pause
