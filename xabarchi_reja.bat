@echo off
REM =====================================================================
REM  Farvon Uy - Telegram xabarchisi uchun REJA o'rnatadi.
REM
REM  Ikki marta bosing. Shundan keyin Windows har daqiqada
REM  `src\xabarchi.py` ni ishga tushiradi va kerak bo'lsa guruhga
REM  xabar yuboradi - dastur oynasi ochiq bo'lmasa ham.
REM
REM  DIQQAT: kompyuter YONIQ bo'lishi kerak. O'chirilgan kompyuterdan
REM  xabar ketmaydi; yoqilganda o'sha kunning o'tkazib yuborilganlari
REM  yuboriladi (eskilari emas).
REM
REM  O'chirish uchun:  xabarchi_reja.bat /o
REM =====================================================================
setlocal
cd /d "%~dp0"
set REJA=FarvonUy_Telegram

if /i "%~1"=="/o" goto ochir

REM pyw - konsol oynasisiz ishga tushiradi
for /f "delims=" %%P in ('where pyw 2^>nul') do set PYW=%%P
if not defined PYW (
  echo [XATO] `pyw` topilmadi. Python 3.14 o'rnatilganini tekshiring.
  pause
  exit /b 1
)

schtasks /Create /TN "%REJA%" /SC MINUTE /MO 1 /F ^
  /TR "\"%PYW%\" -3.14 \"%~dp0src\xabarchi.py\""
if errorlevel 1 (
  echo.
  echo [XATO] Reja yaratilmadi.
  pause
  exit /b 1
)

echo.
echo Reja o'rnatildi: har daqiqada tekshiriladi.
echo Tekshirish:  schtasks /Query /TN "%REJA%"
echo O'chirish:   xabarchi_reja.bat /o
echo.
pause
exit /b 0

:ochir
schtasks /Delete /TN "%REJA%" /F
echo Reja o'chirildi.
pause
exit /b 0
