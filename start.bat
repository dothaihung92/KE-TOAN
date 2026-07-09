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

REM ====== Neu chua co Python -> TU DONG tai va cai dat tu python.org ======
if defined PYEXE goto :PYOK

echo [!] Khong tim thay Python tren may - dang TU DONG tai va cai dat Python.
echo     (Can ket noi Internet, vui long cho vai phut - khong can thao tac gi.)
echo.
REM Dung Python 3.11.9: on dinh, co san wheel cai dat nhanh cho tat ca thu vien
REM (ddddocr/onnxruntime/numpy...) nen cai xong chay ngay, khong phai build.
set "PYVER=3.11.9"
set "PYINST=%TEMP%\python-%PYVER%-amd64.exe"

echo [*] Dang tai Python %PYVER% tu python.org ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try{ Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe' -OutFile '%PYINST%' }catch{ exit 1 }"
if not exist "%PYINST%" (
    echo.
    echo [LOI] Tai Python that bai. Kiem tra ket noi mang roi chay lai start.bat,
    echo       hoac tai thu cong tai: https://www.python.org/downloads/
    echo       ^(nho TICK "Add Python to PATH" khi cai^).
    echo.
    pause
    exit /b
)

echo [*] Dang cai dat Python (im lang, khong can bam gi)...
REM Cai theo NGUOI DUNG hien tai (InstallAllUsers=0) -> KHONG can quyen Admin,
REM khong hien hop thoai UAC; PrependPath=1 tu them Python vao PATH cho lan sau.
"%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=0
del "%PYINST%" >nul 2>&1

REM ====== Do lai Python vua cai (PATH chua cap nhat trong phien CMD nay) ======
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
)
if not defined PYEXE (
    py --version >nul 2>&1
    if not errorlevel 1 set PYEXE=py
)
if not defined PYEXE (
    echo.
    echo [LOI] Da cai Python nhung chua nhan dien ngay duoc.
    echo       Vui long DONG cua so nay va mo lai start.bat mot lan nua
    echo       ^(hoac khoi dong lai may^) roi chay tiep - lan sau se chay binh thuong.
    echo.
    pause
    exit /b
)
echo [OK] Da cai dat Python xong!
echo.

:PYOK
echo [OK] Da tim thay Python: %PYEXE%
"%PYEXE%" --version
echo.

REM ====== Tu dong cap nhat phan mem tu GitHub (neu co ban moi) ======
if exist "update.py" (
    echo [*] Dang kiem tra cap nhat phan mem...
    "%PYEXE%" update.py
    if errorlevel 10 (
        echo [*] Da cap nhat trinh khoi dong - khoi dong lai...
        start "" "%~f0"
        exit /b
    )
    echo.
)

REM ====== Tu dong cai lai neu requirements.txt thay doi ======
"%PYEXE%" -c "import os,sys; sys.exit(0 if os.path.exists('.installed') and os.path.getmtime('.installed')>=os.path.getmtime('requirements.txt') else 1)" >nul 2>&1
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
    "%PYEXE%" -m pip install --upgrade pip >nul 2>&1
    "%PYEXE%" -m pip install -r requirements.txt
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
"%PYEXE%" server.py
pause
