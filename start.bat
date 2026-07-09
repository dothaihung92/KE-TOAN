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

REM ====== Kiem tra thu vien da cai DAY DU chua ======
REM Kiem tra bang cach THU TIM tung module (find_spec) - tin cay hon file
REM .installed vi .installed co the bi COPY theo khi mang thu muc sang may khac,
REM khien may moi tuong da cai roi nhung thuc te CHUA co thu vien -> loi
REM "ModuleNotFoundError: No module named 'requests'".
set NEEDINSTALL=
"%PYEXE%" -c "import importlib.util as u,sys; m=['requests','fastapi','uvicorn','openpyxl','multipart','ddddocr','PIL','svglib','reportlab','curl_cffi','selenium']; sys.exit(0 if all(u.find_spec(x) for x in m) else 1)" >nul 2>&1
if errorlevel 1 set NEEDINSTALL=1

REM requirements.txt moi hon .installed -> co the co thu vien moi -> cai lai
if not defined NEEDINSTALL (
    "%PYEXE%" -c "import os,sys; sys.exit(0 if os.path.exists('.installed') and os.path.getmtime('.installed')>=os.path.getmtime('requirements.txt') else 1)" >nul 2>&1
    if errorlevel 1 set NEEDINSTALL=1
)

if defined NEEDINSTALL (
    echo [*] Dang cai/cap nhat thu vien can thiet...
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

REM ====== Kiem tra bo giai captcha (ddddocr) co CHAY duoc khong ======
REM ddddocr dung onnxruntime -> can 'Microsoft Visual C++ Redistributable'.
REM May moi thuong THIEU goi nay -> ddddocr khong nap duoc -> tu dang nhap
REM (OCR) that bai voi mã rong. Neu phat hien loi -> tu tai & cai VC++ Redist.
REM Chi kiem tra khi VUA cai thu vien (may moi) - tranh cham moi lan khoi dong.
if not defined NEEDINSTALL goto :OCROK
"%PYEXE%" -c "import ddddocr; ddddocr.DdddOcr(show_ad=False)" >nul 2>&1
if not errorlevel 1 goto :OCROK
echo [!] Bo giai captcha chua chay duoc - co the may thieu Visual C++ Redistributable.
echo [*] Dang tai va cai 'Microsoft Visual C++ Redistributable (x64)' ...
set "VCINST=%TEMP%\vc_redist.x64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try{ Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%VCINST%' }catch{ exit 1 }"
if exist "%VCINST%" (
    "%VCINST%" /install /quiet /norestart
    del "%VCINST%" >nul 2>&1
    REM do lai
    "%PYEXE%" -c "import ddddocr; ddddocr.DdddOcr(show_ad=False)" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Da cai VC++ Redistributable - bo giai captcha da chay duoc!
    ) else (
        echo [!] Van chua chay duoc. Vui long cai tay 'Microsoft Visual C++ Redistributable x64'
        echo     tai: https://aka.ms/vs/17/release/vc_redist.x64.exe  roi mo lai phan mem.
        echo     ^(Van co the dung nut "Lay ma" de nhap captcha bang TAY.^)
    )
) else (
    echo [!] Khong tai duoc VC++ Redistributable ^(kiem tra mang^). Ban co the:
    echo     - Cai tay tai: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo     - Hoac dung nut "Lay ma" de nhap captcha bang TAY.
)
echo.
:OCROK

echo [*] Dang khoi dong phan mem...
echo [*] Trinh duyet se tu mo tai: http://127.0.0.1:8686
echo.
echo  ====^> DE TAT PHAN MEM: dong cua so nay ^<====
echo.
"%PYEXE%" server.py
pause
