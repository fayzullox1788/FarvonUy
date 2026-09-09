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
"""
from __future__ import annotations

import sys
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


def main() -> int:
    sinov = "--sinov" in sys.argv

    import crashlog
    crashlog.ornat()

    import db as dbm
    from core import xabar

    # Zaxira olmaymiz: bu skript kuniga o'nlab marta ishga tushadi.
    baza = dbm.Db(zaxirasiz=True)
    try:
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
            for ish in xabar.tugmalarni_qayta_ishla(baza):
                print(f"[TUGMA] {ish}")

        natija = xabar.yubor_kutilayotgan(baza, datetime.now(), sinov=sinov)
        if not natija:
            print("Yuboriladigan xabar yo'q.")
            return 0
        for x in natija:
            bosh = x["matn"].splitlines()[0]
            print(f"[{'SINOV' if sinov else 'YUBORILDI'}] "
                  f"{x['turi']}: {bosh}")
        if not sinov:
            xabar.eski_izlarni_tozala(baza)
        return 0
    finally:
        baza.yop()


if __name__ == "__main__":
    sys.exit(main())
