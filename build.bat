@echo off
setlocal
REM =====================================================================
REM  Farovon Hayot - INSTALLER YASASH
REM  Natija:  installer\FarvonUySetup.exe   <-- odamlarga SHU fayl beriladi
REM  Kerak:   Python 3.14 (py -3.14)  va  Inno Setup 6 (ISCC.exe)
REM =====================================================================
cd /d "%~dp0"

set "PY=py -3.14"
%PY% --version >nul 2>nul
if errorlevel 1 set "PY=python"

echo.
echo [1/6] Kutubxonalar tekshirilmoqda...
%PY% -m pip install -r requirements.txt pyinstaller Pillow
if errorlevel 1 goto :xato

echo.
echo [2/6] Testlar ishga tushirilmoqda...
REM Test yiqilsa build TO'XTAYDI. Buzilgan dasturni tarqatmaymiz.
%PY% src\tekshir.py
if errorlevel 1 goto :test_xato
%PY% src\ui_tekshir.py
if errorlevel 1 goto :test_xato

echo.
echo [3/6] Ikonka yasalmoqda...
%PY% packaging\make_icon.py
if errorlevel 1 goto :xato

echo.
echo [4/6] PyInstaller (onedir) bilan yig'ilmoqda...
%PY% -m PyInstaller --noconfirm --clean packaging\FarvonUy.spec
if errorlevel 1 goto :xato
if not exist "dist\FarvonUy\FarvonUy.exe" (
    echo XATO: dist\FarvonUy\FarvonUy.exe yasalmadi.
    goto :xato
)

echo.
echo [5/6] Inno Setup qidirilmoqda...
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo XATO: ISCC.exe topilmadi.
    echo Inno Setup 6 ni o'rnating: https://jrsoftware.org/isdl.php
    goto :xato
)
echo Topildi: %ISCC%

echo.
echo [6/6] Installer yasalmoqda...
"%ISCC%" packaging\FarvonUy.iss
if errorlevel 1 goto :xato
if not exist "installer\FarvonUySetup.exe" (
    echo XATO: installer\FarvonUySetup.exe yasalmadi.
    goto :xato
)

echo Oraliq fayllar tozalanmoqda...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo =====================================================================
echo  BUILD MUVAFFAQIYATLI.  Odamlarga SHU BITTA faylni bering:
echo    %CD%\installer\FarvonUySetup.exe
echo.
echo  Baza %%LOCALAPPDATA%%\FarvonUy ichida - qayta o'rnatsangiz ham
echo  ma'lumotlar o'chmaydi.
echo =====================================================================
if not defined FARVONUY_NOPAUSE pause
exit /b 0

:test_xato
echo.
echo *** TESTLAR YIQILDI - build to'xtatildi. ***
echo Buzilgan dasturni tarqatib bo'lmaydi. Avval xatoni tuzating.
if not defined FARVONUY_NOPAUSE pause
exit /b 1

:xato
echo.
echo *** BUILD YIQILDI - yuqoridagi xabarlarni o'qing. ***
if not defined FARVONUY_NOPAUSE pause
exit /b 1
