@echo off
chcp 65001 >nul
title Phan mem Quan ly Hoa don dien tu
color 0A
echo ============================================================
echo    PHAN MEM QUAN LY HOA DON DIEN TU - DA CONG TY
echo ============================================================
echo.

REM ====== Tu dong do lenh Python: thu python, py, python3 ======
set PYEXE=
python --version >nul 2>&1
if not errorlevel 1 (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set PYEXE=python
)
if not defined PYEXE (
    py --version >nul 2>&1
    if not errorlevel 1 set PYEXE=py
)
if not defined PYEXE (
    python3 --version >nul 2>&1
    if not errorlevel 1 set PYEXE=python3
)

if not defined PYEXE (
    echo [LOI] Khong tim thay Python tren may.
    echo.
    echo Co the do 1 trong cac nguyen nhan:
    echo   1. Python chua duoc them vao PATH
    echo      -^> Cai lai Python va TICK vao "Add Python to PATH"
    echo   2. Windows dang chan bang App execution aliases
    echo      -^> Settings ^> Apps ^> Advanced app settings
    echo         ^> App execution aliases ^> TAT "python.exe" va "python3.exe"
    echo.
    echo Kiem tra: mo Command Prompt, go thu:  python --version
    echo                                  hoac:  py --version
    echo.
    pause
    exit /b
)

echo [OK] Da tim thay Python: %PYEXE%
%PYEXE% --version
echo.

REM ====== Tu dong cap nhat phan mem tu GitHub (neu co ban moi) ======
if exist "update.py" (
    echo [*] Dang kiem tra cap nhat phan mem...
    %PYEXE% update.py
    if errorlevel 10 (
        echo [*] Da cap nhat trinh khoi dong - khoi dong lai...
        start "" "%~f0"
        exit /b
    )
    echo.
)

REM ====== Tu dong cai lai neu requirements.txt thay doi ======
%PYEXE% -c "import os,sys; sys.exit(0 if os.path.exists('.installed') and os.path.getmtime('.installed')>=os.path.getmtime('requirements.txt') else 1)" >nul 2>&1
if errorlevel 1 (
    if exist ".installed" (
        echo [*] requirements.txt da thay doi - dang cap nhat thu vien...
        del .installed >nul 2>&1
    )
)

REM ====== Cai thu vien lan dau ======
if not exist ".installed" (
    echo [*] Lan dau chay - dang cai thu vien can thiet...
    echo     (Chi cham lan nay, cac lan sau se mo nhanh^)
    echo.
    %PYEXE% -m pip install --upgrade pip >nul 2>&1
    %PYEXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [LOI] Cai thu vien that bai. Kiem tra ket noi mang roi chay lai.
        pause
        exit /b
    )
    echo. > .installed
    echo.
    echo [OK] Da cai xong thu vien!
    echo.
)

echo [*] Dang khoi dong phan mem...
echo [*] Trinh duyet se tu mo tai: http://127.0.0.1:8686
echo.
echo  ====^> DE TAT PHAN MEM: dong cua so nay ^<====
echo.
%PYEXE% server.py
pause
