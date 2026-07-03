@echo off
setlocal
cd /d "%~dp0"

rem ==== Sua 2 dong duoi neu ban doi ten repo / doi nhanh (vi du sau khi ====
rem ==== gop vao "main" thi doi REPO_BRANCH thanh main).                 ====
set "REPO_URL=https://github.com/dothaihung92/KE-TOAN.git"
set "REPO_BRANCH=claude/vietnam-stock-analyzer-9vohi4"

echo ============================================================
echo   PHAN MEM TRA CUU HOA DON DIEN TU - Khoi dong
echo ============================================================

set "PYCMD="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYCMD=py -3"

if not defined PYCMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYCMD=python"
)

if not defined PYCMD (
    echo [LOI] Khong tim thay Python co the chay duoc tren may nay.
    echo Hay cai Python tai https://www.python.org/downloads/
    echo ^(nho tick vao o "Add python.exe to PATH" khi cai^), sau do
    echo DONG cua so nay va mo lai file start.bat.
    pause
    exit /b 1
)

echo   Dung: %PYCMD%

echo.
echo [1/3] Dang kiem tra cap nhat...
where git >nul 2>&1
if errorlevel 1 (
    echo   Chua cai Git nen khong the tu dong cap nhat. Cai tai
    echo   https://git-scm.com/downloads de bat tinh nang nay, hoac tai
    echo   thu cong ban moi nhat. Se chay voi ban hien co.
    goto :after_update
)

git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 (
    echo   Da ket noi Git, dang tai cap nhat moi nhat...
    git pull
    if errorlevel 1 (
        echo   Khong cap nhat duoc ^(co the do mang hoac co thay doi chua luu^), tiep tuc chay ban hien tai.
    )
    goto :after_update
)

echo   Thu muc nay chua duoc ket noi voi Git ^(vi du ban tai ve dang file zip^).
echo   Dang thiet lap ket noi lan dau de tu dong cap nhat tu lan sau...
git init -q
git remote add origin "%REPO_URL%" >nul 2>&1
git fetch --quiet origin %REPO_BRANCH%
if errorlevel 1 (
    echo   Khong ket noi duoc toi may chu cap nhat ^(kiem tra mang, hoac neu
    echo   repo la private thi can dang nhap Git voi tai khoan co quyen^).
    echo   Se chay voi ban hien co.
    goto :after_update
)

git reset --hard --quiet origin/%REPO_BRANCH%
git branch -q -M %REPO_BRANCH%
git branch -q --set-upstream-to=origin/%REPO_BRANCH% %REPO_BRANCH% >nul 2>&1
echo   Da ket noi thanh cong! Tu lan sau se tu dong cap nhat khi mo file nay.

:after_update

echo.
echo [2/3] Dang cai dat / cap nhat thu vien can thiet...
%PYCMD% -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [LOI] Cai dat thu vien that bai. Kiem tra ket noi mang roi chay lai file nay.
    pause
    exit /b 1
)

echo.
echo [3/3] Dang khoi dong phan mem...
echo ============================================================
%PYCMD% run_web.py

pause
