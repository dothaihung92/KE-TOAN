@echo off
chcp 65001 >nul
title Phan mem Ke toan - HDDT + Fanpage AI
cd /d "%~dp0"

echo ============================================================
echo   PHAN MEM KE TOAN - Tra cuu hoa don dien tu + Fanpage AI
echo ============================================================
echo.

REM --- 1. Tim trinh thong dich Python -------------------------------------
set "PYEXE="
python --version >nul 2>nul
if not errorlevel 1 set "PYEXE=python"
if not defined PYEXE (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set "PYEXE=py -3"
)

if not defined PYEXE (
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

REM --- 3. Tao / kiem tra moi truong ao -------------------------------------
if not exist "venv\Scripts\python.exe" (
    if exist "venv" (
        echo Moi truong ao cu bi loi, dang xoa va tao lai...
        rmdir /s /q "venv"
    ) else (
        echo Dang tao moi truong Python rieng cho phan mem ^(chi lam 1 lan^)...
    )
    %PYEXE% -m venv venv
    echo.
)

set "VENV_PY=venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [Canh bao] Khong tao duoc moi truong ao rieng, se dung Python co san.
    set "VENV_PY=%PYEXE%"
)

REM --- 4. Cai dat / cap nhat cac thu vien can thiet ----------------------
echo Dang kiem tra va cap nhat thu vien can thiet...
%VENV_PY% -m pip install --upgrade pip >nul 2>nul
%VENV_PY% -m pip install -r requirements.txt --upgrade
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
%VENV_PY% run_web.py

pause
