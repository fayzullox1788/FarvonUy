@echo off
REM =====================================================================
REM  Farovon Hayot - HAMMA TESTNI ISHGA TUSHIRISH
REM  1) yadro testlari (pul, bo'lish, undo, audit)
REM  2) UI testlari (hamma sahifa xatosiz quriladimi)
REM =====================================================================
cd /d "%~dp0"
set "PY=py -3.14"

echo.
echo === [1/2] Yadro testlari ===
%PY% src\tekshir.py
if errorlevel 1 goto :xato

echo.
echo === [2/2] UI testlari ===
%PY% src\ui_tekshir.py
if errorlevel 1 goto :xato

echo.
echo =====================================================
echo  HAMMASI JOYIDA.
echo =====================================================
pause
exit /b 0

:xato
echo.
echo *** TEST YIQILDI - yuqoridagi xabarlarni o'qing. ***
pause
exit /b 1
