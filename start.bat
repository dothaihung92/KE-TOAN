@echo off
chcp 65001 >nul
title Phan mem Ke toan - HDDT + Fanpage AI
cd /d "%~dp0"

echo ============================================================
echo   PHAN MEM KE TOAN - Tra cuu hoa don dien tu + Fanpage AI
echo ============================================================
echo.

REM --- 1. Kiem tra da cai Python chua ------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay Python tren may.
    echo Vui long cai Python tai https://www.python.org/downloads/
    echo Nho tick chon "Add Python to PATH" khi cai dat, roi chay lai file nay.
    echo.
    pause
    exit /b 1
)

REM --- 2. Cap nhat ma nguon moi nhat (neu co Git va co mang) -------------
if exist ".git" (
    where git >nul 2>nul
    if not errorlevel 1 (
        echo Dang kiem tra cap nhat phan mem...
        git pull --ff-only
        if errorlevel 1 (
            echo [Canh bao] Khong the tu cap nhat ^(co the do offline hoac
            echo co thay doi cuc bo^). Bo qua buoc cap nhat, tiep tuc chay.
        )
        echo.
    )
)

REM --- 3. Tao moi truong ao lan dau chay --------------------------------
if not exist "venv" (
    echo Dang tao moi truong Python rieng cho phan mem ^(chi lam 1 lan^)...
    python -m venv venv
    echo.
)

call venv\Scripts\activate.bat

REM --- 4. Cai dat / cap nhat cac thu vien can thiet ----------------------
echo Dang kiem tra va cap nhat thu vien can thiet...
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo [LOI] Cai dat thu vien that bai. Kiem tra ket noi mang roi thu lai.
    pause
    exit /b 1
)
echo.

REM --- 5. Khoi chay phan mem ----------------------------------------------
echo Dang khoi chay phan mem, trinh duyet se tu mo...
echo Dong cua so nay ^(hoac nhan Ctrl+C^) de dung phan mem.
echo.
python run_web.py

pause
