r"""Telegram xabarlarini yuboruvchi — dasturdan MUSTAQIL.

    py -3.14 src\xabarchi.py          # kerak bo'lsa yuboradi
    py -3.14 src\xabarchi.py --sinov  # hech narsa yubormaydi, ko'rsatadi

Windows «Vazifalar rejalashtiruvchisi» buni HAR DAQIQADA chaqiradi,
shuning uchun dastur oynasi ochiq bo'lmasa ham xabar boradi
(`packaging/xabarchi_reja.bat` reja yaratadi).

Har daqiqada, chunki skript ikki ish qiladi: kerakli xabarni yuboradi
VA guruhdagi tugma bosilishini qabul qiladi («Albatta!», menyu
tanlash). Tugma bosilib javob 5 daqiqa kutsa — odam ikkinchi marta
bosadi va tugma buzuq deb o'ylaydi.

Bir necha marta chaqirilishi XAVFSIZ: har xabar `yuborilgan` jadvalida
belgilanadi va ikkinchi marta yuborilmaydi; bosilishlar esa
`sozlama.tg_offset` bilan bir marta hisoblanadi.

UZUN SO'ROV. Reja amalda har 5 daqiqada ishga tushadi, rasxod boti esa
qadamma-qadam suhbat — har tugmaga daqiqalab javob kutib bo'lmaydi.
Shuning uchun skript darhol chiqib ketmaydi: `ISH_VAQTI` davomida
`getUpdates` ni uzun so'rov bilan tinglaydi (xabar kelishi bilan
javob beradi) va har daqiqada eslatmalarni tekshiradi. Reja
«IgnoreNew» — oldingisi ishlab turganda yangisi ishga tushmaydi,
ya'ni ikkita tinglovchi bo'lmaydi. `ISH_VAQTI` reja oralig'idan
(5 daqiqa) KICHIK: navbatdagi ishga tushish o'tkazib yuborilmasin.
"""
from __future__ import annotations

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
# qoladi. UTF-8 ga majburan o'tkazamiz.
for _oqim in (sys.stdout, sys.stderr):
    try:
        _oqim.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Soniya, JARAYON BOSHIDAN (tinglash boshidan emas). Reja har 5 daqiqada
# (300 s) ishga tushiradi va «IgnoreNew»: oldingisi hali ishlasa yangisi
# O'TKAZIB YUBORILADI — ya'ni 300 dan oshsa 5 daqiqalik bo'shliq bo'ladi.
# 270 bo'lganda har davrda ~30 s hech kim tinglamasdi va tugma «ishlamay
# qoldi» bo'lib ko'rinardi (2026-09-25). Boshlang'ich ish (dars sinxroni
# tarmoqqa chiqadi) necha soniya olsa ham, hisob jarayon boshidan.
ISH_VAQTI = 292
SOROV_VAQTI = 25       # bitta uzun so'rov (Telegram 50 gacha ruxsat beradi)
ESLATMA_ORALIQ = 60    # tinglash paytida eslatmalar shu oraliqda tekshiriladi
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


def _yubor(xabar, baza, sinov: bool) -> None:
    natija = xabar.yubor_kutilayotgan(baza, datetime.now(), sinov=sinov)
    for x in natija:
        bosh = x["matn"].splitlines()[0]
        print(f"[{'SINOV' if sinov else 'YUBORILDI'}] {x['turi']}: {bosh}")
    if natija and not sinov:
        xabar.eski_izlarni_tozala(baza)


def _tingla(xabar, baza, boshi: float | None = None) -> None:
    """Uzun so'rov: rasxod suhbati va tugmalarga soniyalarda javob.

    `boshi` — jarayon boshlangan payt (`time.monotonic()`); oyna shundan
    hisoblanadi.
    """
    if boshi is None:
        boshi = time.monotonic()
    oxirgi_eslatma = time.monotonic()
    while True:
        qoldi = ISH_VAQTI - (time.monotonic() - boshi)
        if qoldi < 3:
            return
        ishlar = xabar.tugmalarni_qayta_ishla(
            baza, kutish=int(min(SOROV_VAQTI, qoldi - 2)))
        for ish in ishlar:
            print(f"[TUGMA] {ish}")
        _jurnal(ishlar)
        if ishlar and all(i.startswith("Xato:") for i in ishlar):
            # Bitta tarmoq uzilishi («read operation timed out») butun
            # oynani yopmasin: 2026-09-25 da aynan shu bilan bot ~3 daqiqa
            # jim qolgan. Biroz kutib qayta urinamiz — oyna baribir
            # `ISH_VAQTI` da tugaydi.
            # Kamida 1 s: aks holda oxirgi soniyalarda tsikl bo'sh aylanardi.
            time.sleep(min(XATO_KUTISH, max(1.0, qoldi - 3)))
        if time.monotonic() - oxirgi_eslatma >= ESLATMA_ORALIQ:
            oxirgi_eslatma = time.monotonic()
            try:
                _yubor(xabar, baza, sinov=False)
            except Exception as x:
                print(f"[ESLATMA] xato: {x}")


def main() -> int:
    boshi = time.monotonic()
    sinov = "--sinov" in sys.argv

    import crashlog
    crashlog.ornat()

    import db as dbm
    from core import xabar

    # Zaxira olmaymiz: bu skript kuniga o'nlab marta ishga tushadi.
    baza = dbm.Db(zaxirasiz=True)
    try:
        # Takroriy vazifalar («har kuni namoz») ham Telegramdan
        # mustaqil: kalendar bot sozlanmagan bo'lsa ham to'lishi kerak.
        # Hech narsa yetishmasa hech narsa yozilmaydi.
        if not sinov:
            try:
                from core import vazifa as vz
                n = vz.takror_toldir(baza)
                if n:
                    print(f"[TAKROR] {n} ta kun qo'shildi")
            except Exception as x:
                print(f"[TAKROR] o'tkazib yuborildi: {x}")

        # Dars jadvali Telegramdan MUSTAQIL: kalendar bot sozlanmagan
        # bo'lsa ham to'ldirilishi kerak, shuning uchun tekshiruvdan
        # oldin turadi. Tarmoq yiqilsa xabarchi to'xtamaydi — jadval
        # kechikkanidan ko'ra eslatma kelmagani yomonroq.
        if not sinov:
            try:
                from core import dars
                o = dars.yangila(baza, datetime.now())
                if o and (o["qoshildi"] or o["yangilandi"] or o["ochirildi"]):
                    print(f"[DARS] {o['hafta']}: +{o['qoshildi']}"
                          f" ~{o['yangilandi']} -{o['ochirildi']}")
            except Exception as x:
                print(f"[DARS] o'tkazib yuborildi: {x}")

        if not sinov and not xabar.sozlangami(baza):
            print("Telegram sozlanmagan yoki o'chirilgan — hech narsa "
                  "yuborilmadi.")
            return 0
        # Avval tugmalar: odam «Albatta!» bosgan bo'lsa, vazifa
        # bajarilgan bo'ladi va unga eslatma yuborilmaydi.
        if not sinov:
            ishlar = xabar.tugmalarni_qayta_ishla(baza)
            for ish in ishlar:
                print(f"[TUGMA] {ish}")
            _jurnal(ishlar)

        _yubor(xabar, baza, sinov)
        if not sinov and "--bir-marta" not in sys.argv:
            _tingla(xabar, baza, boshi)
        return 0
    finally:
        baza.yop()


if __name__ == "__main__":
    sys.exit(main())
