r"""Telegram xabarchisi — dasturdan MUSTAQIL, DOIMIY ishlaydigan bitta jarayon.

    py -3.14 src\xabarchi.py             # doimiy: tinglaydi va yuboradi
    py -3.14 src\xabarchi.py --bir-marta # bir marta yuboradi va chiqadi
    py -3.14 src\xabarchi.py --sinov     # hech narsa yubormaydi, ko'rsatadi

DOIMIY JARAYON (2026-10-01, «bot juda sekin» shikoyatidan keyin). Avval
reja har 5 daqiqada ishga tushirar, skript ~292 s tinglab chiqib ketardi:
ishga tushish oralig'ida va noutbuk batareyada bo'lganda (reja
batareyada ishga tushmasdi) bot daqiqalab javob bermasdi. Endi:

  • skript chiqib KETMAYDI — `getUpdates` ni uzun so'rov bilan
    (`SOROV_VAQTI`) tinimsiz tinglaydi, har daqiqada eslatmalarni,
    har `DAVRIY_ORALIQ` da takroriy vazifa va dars jadvalini tekshiradi;
  • BITTA nusxa: `xabarchi.lock` fayl qulfi. Windows rejasi har daqiqada
    chaqiradi — qulf band bo'lsa yangi nusxa darhol chiqadi (nazoratchi);
    jarayon yiqilsa, ko'pi bilan bir daqiqada qayta ko'tariladi;
  • kod o'zgarsa (`src/**/*.py`) jarayon o'zi chiqadi — nazoratchi
    yangi kod bilan qayta ishga tushiradi. Shuning uchun bu fayllarni
    tahrirlagach darhol `py_compile` qiling (yarim fayl yangi jarayonni
    yiqitadi; nazoratchi baribir qayta urinadi).

Bir necha marta chaqirilishi XAVFSIZ: har xabar `yuborilgan` jadvalida
belgilanadi va ikkinchi marta yuborilmaydi; bosilishlar esa
`sozlama.tg_offset` bilan bir marta hisoblanadi.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Xabar matnlarida emoji bor (📅, 🍲, ...). Windows konsoli ko'pincha
# eski kodlashda (masalan cp1251) ishlaydi va bunday belgini chop etib
# bo'lmay, skript o'rtada yiqiladi — hech qanday xabar yuborilmay
# qoladi. UTF-8 ga majburan o'tkazamiz. (pyw da oqim yo'q — None.)
for _oqim in (sys.stdout, sys.stderr):
    try:
        _oqim.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Oynali rejim (`_tingla(..., ish_vaqti=N)`) — testlar va eski chaqiruv
# uchun; doimiy rejimda `ish_vaqti=None`.
ISH_VAQTI = 292
SOROV_VAQTI = 50       # bitta uzun so'rov — Telegram ruxsat beradigan eng ko'pi
ESLATMA_ORALIQ = 60    # eslatmalar shu oraliqda tekshiriladi, soniya
DAVRIY_ORALIQ = 600    # takroriy vazifa + dars jadvali, soniya
XATO_KUTISH = 5        # tarmoq xatosidan keyin qayta urinishgacha, soniya


JURNAL_MAX = 512 * 1024   # bayt — oshsa eskisi `.1` ga ko'chadi


def _jurnal(qatorlar) -> None:
    """Botning ishi `telegram.log` ga. Skript konsolsiz (pyw) ishlaydi —
    `print` hech qayerga chiqmaydi, xato esa jim yo'qolardi."""
    qatorlar = [q for q in qatorlar if q]
    if not qatorlar:
        return
    try:
        import config
        yol = config.DATA / "telegram.log"
        if yol.exists() and yol.stat().st_size > JURNAL_MAX:
            yol.replace(yol.with_suffix(".log.1"))
        vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(yol, "a", encoding="utf-8") as f:
            for q in qatorlar:
                f.write(f"{vaqt}  {q}\n")
    except Exception:
        pass


def _chiqar(matn: str) -> None:
    try:
        print(matn)
    except Exception:
        pass


# ───────────────────────────────────────────────────── bitta nusxa

def _qulfla(yol: Path | None = None):
    """Fayl qulfi: muvaffaqiyatli bo'lsa ochiq fayl (jarayon oxirigacha
    ushlab turiladi), band bo'lsa None — boshqa nusxa allaqachon ishlayapti.
    Jarayon o'lsa OS qulfni o'zi bo'shatadi. `yol` — testlar uchun."""
    if yol is None:
        import config
        yol = config.DATA / "xabarchi.lock"
    f = open(yol, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


# ───────────────────────────────────────────────────── kod o'zgardimi

def _kod_izi() -> float:
    """`src` dagi .py fayllarning eng so'nggi o'zgargan vaqti."""
    eng = 0.0
    for yol in SRC.rglob("*.py"):
        if "__pycache__" in yol.parts:
            continue
        try:
            eng = max(eng, yol.stat().st_mtime)
        except OSError:
            pass
    return eng


# ───────────────────────────────────────────────────── ishlar

def _yubor(xabar, baza, sinov: bool) -> None:
    natija = xabar.yubor_kutilayotgan(baza, datetime.now(), sinov=sinov)
    for x in natija:
        bosh = x["matn"].splitlines()[0]
        _chiqar(f"[{'SINOV' if sinov else 'YUBORILDI'}] {x['turi']}: {bosh}")
    if natija and not sinov:
        xabar.eski_izlarni_tozala(baza)


def _davriy(baza) -> None:
    """Takroriy vazifalar («har kuni namoz») va dars jadvali — Telegramdan
    MUSTAQIL: kalendar bot sozlanmagan bo'lsa ham to'lishi kerak. Hech
    narsa yetishmasa hech narsa yozilmaydi; dars o'zi soatiga bir marta
    tarmoqqa chiqadi. Yiqilsa xabarchi to'xtamaydi."""
    try:
        from core import vazifa as vz
        n = vz.takror_toldir(baza)
        if n:
            _chiqar(f"[TAKROR] {n} ta kun qo'shildi")
    except Exception as x:
        _chiqar(f"[TAKROR] o'tkazib yuborildi: {x}")
    try:
        from core import dars
        o = dars.yangila(baza, datetime.now())
        if o and (o["qoshildi"] or o["yangilandi"] or o["ochirildi"]):
            _chiqar(f"[DARS] {o['hafta']}: +{o['qoshildi']}"
                    f" ~{o['yangilandi']} -{o['ochirildi']}")
    except Exception as x:
        _chiqar(f"[DARS] o'tkazib yuborildi: {x}")


def _tingla(xabar, baza, boshi: float | None = None,
            ish_vaqti: float | None = ISH_VAQTI, toxta=None,
            davriy=None) -> str:
    """Uzun so'rov: rasxod suhbati va tugmalarga soniyalarda javob.

    `ish_vaqti` — `boshi` dan (`time.monotonic()`) shuncha soniyada
    tugaydi; None — cheksiz (doimiy rejim). `toxta()` True qaytarsa
    chiqadi (kod o'zgardi). `davriy(baza)` — `DAVRIY_ORALIQ` da bir marta.
    Qaytaradi: nega tugadi («vaqt» | «toxta»).
    """
    if boshi is None:
        boshi = time.monotonic()
    oxirgi_eslatma = time.monotonic()
    oxirgi_davriy = time.monotonic()
    while True:
        if toxta is not None and toxta():
            return "toxta"
        if ish_vaqti is None:
            kutish = SOROV_VAQTI
        else:
            qoldi = ish_vaqti - (time.monotonic() - boshi)
            if qoldi < 3:
                return "vaqt"
            kutish = int(min(SOROV_VAQTI, qoldi - 2))
        # Eslatma vaqti kelgan bo'lsa uzun so'rov uni kechiktirmasin.
        kutish = int(max(1, min(kutish, ESLATMA_ORALIQ
                                - (time.monotonic() - oxirgi_eslatma))))
        ishlar = xabar.tugmalarni_qayta_ishla(baza, kutish=kutish)
        for ish in ishlar:
            _chiqar(f"[TUGMA] {ish}")
        _jurnal(ishlar)
        if ishlar and all(i.startswith("Xato:") for i in ishlar):
            # Bitta tarmoq uzilishi («read operation timed out») tinglashni
            # to'xtatmasin — biroz kutib qayta urinamiz.
            dam = XATO_KUTISH if ish_vaqti is None else min(
                XATO_KUTISH, max(1.0, ish_vaqti - (time.monotonic() - boshi)
                                 - 3))
            time.sleep(dam)
        if time.monotonic() - oxirgi_eslatma >= ESLATMA_ORALIQ:
            oxirgi_eslatma = time.monotonic()
            try:
                _yubor(xabar, baza, sinov=False)
            except Exception as x:
                _chiqar(f"[ESLATMA] xato: {x}")
        if davriy is not None and \
                time.monotonic() - oxirgi_davriy >= DAVRIY_ORALIQ:
            oxirgi_davriy = time.monotonic()
            davriy(baza)


def main() -> int:
    boshi = time.monotonic()
    sinov = "--sinov" in sys.argv
    bir_marta = sinov or "--bir-marta" in sys.argv

    # Nazoratchi: boshqa nusxa ishlayotgan bo'lsa — darhol chiqamiz,
    # og'ir importlardan OLDIN (reja har daqiqada chaqiradi).
    qulf = None if bir_marta else _qulfla()
    if not bir_marta and qulf is None:
        return 0

    import crashlog
    crashlog.ornat()

    import config
    import db as dbm
    from core import xabar

    kod_izi = _kod_izi()
    # Zaxira olmaymiz: bu skript tez-tez ishga tushadi.
    # Har doim HAQIQIY baza: desktopda demo rejim yoqilgan bo'lsa ham
    # bot soxta ma'lumot bilan ishlamasin (`config.DEMO`).
    baza = dbm.Db(config.HAQIQIY_DB, zaxirasiz=True)
    try:
        if not sinov:
            _davriy(baza)
        if not sinov and not xabar.sozlangami(baza):
            _chiqar("Telegram sozlanmagan yoki o'chirilgan — hech narsa "
                    "yuborilmadi.")
            return 0
        # Avval tugmalar: odam «Albatta!» bosgan bo'lsa, vazifa
        # bajarilgan bo'ladi va unga eslatma yuborilmaydi.
        if not sinov:
            ishlar = xabar.tugmalarni_qayta_ishla(baza)
            for ish in ishlar:
                _chiqar(f"[TUGMA] {ish}")
            _jurnal(ishlar)

        _yubor(xabar, baza, sinov)
        if not bir_marta:
            _jurnal(["xabarchi: doimiy tinglash boshlandi"])
            sabab = _tingla(xabar, baza, boshi, ish_vaqti=None,
                            toxta=lambda: _kod_izi() != kod_izi,
                            davriy=_davriy)
            _jurnal([f"xabarchi: to'xtadi ({sabab}) — nazoratchi qayta "
                     f"ishga tushiradi"])
        return 0
    finally:
        baza.yop()
        if qulf is not None:
            qulf.close()


if __name__ == "__main__":
    sys.exit(main())
