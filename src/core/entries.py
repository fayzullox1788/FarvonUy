"""Yozuvlar: kirim, rasxod, qarz, hisob-kitob.

Har bir funksiya `db.amal()` ichida ishlaydi — ya'ni rasxod va uning
ulushlari BITTA Ctrl+Z qadami bo'ladi. UI shu funksiyalardan boshqa
hech narsa chaqirmaydi.
"""
from __future__ import annotations

import money
from core import splitting

# "berilmagan" ni "None qilib qo'y" dan ajratish uchun.
# kim_uchun=None — "endi boshqa uchun emas" degani, shuning uchun
# oddiy None ni "tegmasin" deb talqin qilib bo'lmaydi.
_TEGMA = object()


# ────────────────────────────────────────────────────────────── kirim

def kirim_qosh(db, sana: str, odam_id: int, summa: int,
               sabab: str | None = None) -> int:
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Kirim summasi musbat bo'lishi kerak")
    nom = _odam_nom(db, odam_id)
    with db.amal(f"Kirim: {nom} +{money.fmt(summa)}"):
        return db.apply("kirim", "INSERT", {
            "sana": sana, "odam_id": odam_id, "summa": summa,
            "sabab": sabab or None})


def kirim_tahrir(db, kirim_id: int, **maydonlar) -> None:
    with db.amal("Kirim tahrirlandi"):
        db.apply("kirim", "UPDATE", maydonlar, kirim_id)


def kirim_ochir(db, kirim_id: int) -> None:
    with db.amal("Kirim o'chirildi"):
        db.apply("kirim", "DELETE", qator_id=kirim_id)


# ───────────────────────────────────────────────────────────── rasxod

def rasxod_qosh(db, sana: str, nom: str, summa: int, kim_toladi: int,
                umumiymi: bool = True, turi_id: int | None = None,
                usul: str = money.USUL_TENG,
                parametrlar: dict[int, float] | None = None,
                izoh: str | None = None, item_id: int | None = None,
                reja_id: int | None = None, takror_id: int | None = None,
                kim_uchun: int | None = None) -> int:
    """Rasxod + (umumiy bo'lsa) ulushlar. Bitta undo qadami.

    `kim_uchun` berilsa — bu BOSHQA ODAM UCHUN qilingan xarid:
    pulni `kim_toladi` chiqaradi, lekin rasxod butunlay `kim_uchun`
    niki bo'ladi va u shu summaga qarzdor bo'ladi.

    Bu KIRIM emas. Pul o'sha odamning qo'liga tegmagan, shuning uchun
    uning `naqd` (real balans) raqami umuman o'zgarmaydi — faqat qarzi
    ortadi. Aynan shu narsa "pul berib, keyin uni sarfladi" deb
    yozishdan farq qiladi.
    """
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Rasxod summasi musbat bo'lishi kerak")

    if kim_uchun is not None:
        # 100% bitta odamga — bo'lish shart emas, qoldiq ham yo'q.
        umumiymi = True
        usul = money.USUL_ANIQ
        parametrlar = {kim_uchun: summa}

    ulushlar = []
    if umumiymi:
        ulushlar = splitting.hisobla(db, summa, sana, usul, parametrlar)

    kim = _odam_nom(db, kim_toladi)
    if kim_uchun is not None:
        tur = f"{_odam_nom(db, kim_uchun)} uchun"
    else:
        tur = "Umumiy" if umumiymi else "Shaxsiy"
    with db.amal(f"{tur} rasxod: {nom or '—'} {money.fmt(summa)} ({kim})"):
        rid = db.apply("rasxod", "INSERT", {
            "sana": sana, "nom": nom or "", "turi_id": turi_id, "summa": summa,
            "kim_toladi": kim_toladi, "umumiymi": 1 if umumiymi else 0,
            "bolish_usul": usul, "item_id": item_id, "reja_id": reja_id,
            "takror_id": takror_id, "kim_uchun": kim_uchun,
            "izoh": izoh or None})
        for u in ulushlar:
            db.apply("ulush", "INSERT", {
                "rasxod_id": rid, "odam_id": u.odam_id,
                "summa": u.summa, "yaxlitlash": u.yaxlitlash})
        return rid


def rasxod_tahrir(db, rasxod_id: int, *, sana=None, nom=None, summa=None,
                  kim_toladi=None, umumiymi=None, turi_id=None,
                  usul=None, parametrlar=None, izoh=None,
                  kim_uchun=_TEGMA) -> None:
    """Rasxodni o'zgartiradi va kerak bo'lsa ulushlarni QAYTA hisoblaydi."""
    eski = db.q1("SELECT * FROM rasxod WHERE id=?", rasxod_id)
    if not eski:
        raise ValueError("Rasxod topilmadi")

    yangi = {
        "sana": sana if sana is not None else eski["sana"],
        "nom": nom if nom is not None else eski["nom"],
        "summa": int(summa) if summa is not None else eski["summa"],
        "kim_toladi": kim_toladi if kim_toladi is not None else eski["kim_toladi"],
        "umumiymi": (1 if umumiymi else 0) if umumiymi is not None else eski["umumiymi"],
        "turi_id": turi_id if turi_id is not None else eski["turi_id"],
        "bolish_usul": usul if usul is not None else eski["bolish_usul"],
        "izoh": izoh if izoh is not None else eski["izoh"],
        "kim_uchun": (eski["kim_uchun"] if kim_uchun is _TEGMA else kim_uchun),
    }
    if yangi["summa"] <= 0:
        raise ValueError("Rasxod summasi musbat bo'lishi kerak")

    # "Boshqa uchun" rasxod har doim 100% bitta odamga tegishli.
    if yangi["kim_uchun"] is not None:
        yangi["umumiymi"] = 1
        yangi["bolish_usul"] = money.USUL_ANIQ
        parametrlar = {yangi["kim_uchun"]: yangi["summa"]}

    # ulushlarni qayta hisoblash kerakmi?
    qayta = yangi["umumiymi"] == 1 and (
        yangi["summa"] != eski["summa"] or yangi["sana"] != eski["sana"]
        or yangi["umumiymi"] != eski["umumiymi"]
        or yangi["bolish_usul"] != eski["bolish_usul"]
        or yangi["kim_uchun"] != eski["kim_uchun"] or parametrlar is not None)

    with db.amal(f"Rasxod tahrirlandi: {yangi['nom'] or '—'}"):
        db.apply("rasxod", "UPDATE", yangi, rasxod_id)
        if yangi["umumiymi"] == 0:
            for r in db.q("SELECT id FROM ulush WHERE rasxod_id=?", rasxod_id):
                db.apply("ulush", "DELETE", qator_id=r["id"])
        elif qayta:
            for r in db.q("SELECT id FROM ulush WHERE rasxod_id=?", rasxod_id):
                db.apply("ulush", "DELETE", qator_id=r["id"])
            for u in splitting.hisobla(db, yangi["summa"], yangi["sana"],
                                       yangi["bolish_usul"], parametrlar):
                db.apply("ulush", "INSERT", {
                    "rasxod_id": rasxod_id, "odam_id": u.odam_id,
                    "summa": u.summa, "yaxlitlash": u.yaxlitlash})


def rasxod_ochir(db, rasxod_id: int) -> None:
    r = db.q1("SELECT nom, summa FROM rasxod WHERE id=?", rasxod_id)
    nom = (r["nom"] if r else "") or "—"
    with db.amal(f"Rasxod o'chirildi: {nom}"):
        db.apply("rasxod", "DELETE", qator_id=rasxod_id)


# ─────────────────────────────────────────────────────────────── qarz

def qarz_qosh(db, sana: str, kim_berdi: int, kimga: int, summa: int,
              sabab: str | None = None) -> int:
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Qarz summasi musbat bo'lishi kerak")
    if kim_berdi == kimga:
        raise ValueError("O'ziga o'zi qarz bera olmaydi")
    a, b = _odam_nom(db, kim_berdi), _odam_nom(db, kimga)
    with db.amal(f"Qarz: {a} → {b} {money.fmt(summa)}"):
        return db.apply("qarz", "INSERT", {
            "sana": sana, "kim_berdi": kim_berdi, "kimga": kimga,
            "summa": summa, "sabab": sabab or None})


def qarz_ochir(db, qarz_id: int) -> None:
    with db.amal("Qarz o'chirildi"):
        db.apply("qarz", "DELETE", qator_id=qarz_id)


# ────────────────────────────────────────────────────────── hisob-kitob

def hisob_kitob_qosh(db, sana: str, kim_toladi: int, kimga: int, summa: int,
                     izoh: str | None = None) -> int:
    """Qarzni yopish uchun haqiqiy to'lov."""
    summa = int(summa)
    if summa <= 0:
        raise ValueError("To'lov summasi musbat bo'lishi kerak")
    if kim_toladi == kimga:
        raise ValueError("O'ziga o'zi to'lay olmaydi")
    a, b = _odam_nom(db, kim_toladi), _odam_nom(db, kimga)
    with db.amal(f"Hisob-kitob: {a} → {b} {money.fmt(summa)}"):
        return db.apply("hisob_kitob", "INSERT", {
            "sana": sana, "kim_toladi": kim_toladi, "kimga": kimga,
            "summa": summa, "izoh": izoh or None})


def hisob_kitob_ochir(db, hk_id: int) -> None:
    with db.amal("Hisob-kitob o'chirildi"):
        db.apply("hisob_kitob", "DELETE", qator_id=hk_id)


# ────────────────────────────────────────────────────────────── odamlar

def odam_qosh(db, nom: str, rang: str = "#6b7fd7") -> int:
    nom = nom.strip()
    if not nom:
        raise ValueError("Ism bo'sh bo'lmasin")
    if db.q1("SELECT 1 FROM odam WHERE nom=? AND faol=1", nom):
        raise ValueError(f"{nom} allaqachon bor")
    n = db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM odam")
    with db.amal(f"Odam qo'shildi: {nom}"):
        return db.apply("odam", "INSERT", {"nom": nom, "rang": rang, "tartib": n})


def _odam_nom(db, odam_id: int) -> str:
    r = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    return r["nom"] if r else "?"


def odam_ochir(db, odam_id: int) -> None:
    """Odamni ro'yxatdan olib tashlaydi (nofaol qiladi).

    Yozuvlari HECH QAYERGA yo'qolmaydi — o'tgan rasxodlar, ulushlar va
    qarzlar joyida qoladi, aks holda kitob teng bo'lmay qolardi. Odam
    faqat yangi rasxodlarda ko'rinmaydi.
    """
    o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    if not o:
        raise ValueError("Odam topilmadi")
    if db.skalyar("SELECT COUNT(*) FROM odam WHERE faol=1") <= 1:
        raise ValueError("Oxirgi odamni o'chirib bo'lmaydi")

    b = db.q1("SELECT sof FROM v_balans WHERE id=?", odam_id)
    if b and b["sof"] != 0:
        yon = "qarzdor" if b["sof"] < 0 else "unga qarzdorlar"
        raise ValueError(
            f"{o['nom']} hali {money.fmt(abs(b['sof']))} so'mga {yon}.\n\n"
            f"Avval hisob-kitob qiling — qarz ochiq turganda odamni "
            f"ro'yxatdan olib tashlash hisobni chalkashtiradi.")

    with db.amal(f"Odam ro'yxatdan olindi: {o['nom']}"):
        db.apply("odam", "UPDATE", {"faol": 0}, odam_id)


def odam_qaytar(db, odam_id: int) -> None:
    o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    with db.amal(f"Odam qaytarildi: {o['nom'] if o else '?'}"):
        db.apply("odam", "UPDATE", {"faol": 1}, odam_id)


def odam_nomi_ozgartir(db, odam_id: int, yangi: str) -> None:
    yangi = yangi.strip()
    if not yangi:
        raise ValueError("Ism bo'sh bo'lmasin")
    if db.q1("SELECT 1 FROM odam WHERE nom=? AND id<>?", yangi, odam_id):
        raise ValueError(f"{yangi} allaqachon bor")
    with db.amal(f"Ism o'zgartirildi: {yangi}"):
        db.apply("odam", "UPDATE", {"nom": yangi}, odam_id)
