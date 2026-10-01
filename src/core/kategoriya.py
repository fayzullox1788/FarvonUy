"""Ikonkali rasxod kategoriyalari.

Ikonkalar `src/belgilar/` da (telefon skrinshotlaridan kesilgan,
`packaging/belgi_kes.py`). Ular NOMSIZ keladi — nomni foydalanuvchi
beradi, va nom berilgan ikonka `turi` jadvalida oddiy kategoriya bo'ladi
(`turi.rasm` = fayl nomi). Ya'ni butun balans va hisobot mantiqi
o'zgarishsiz ishlaydi: ular faqat `turi_id` ni ko'radi.

Nomi olib tashlangan kategoriya O'CHIRILMAYDI — `faol=0`. Unga
bog'langan eski rasxodlar kategoriyasini yo'qotmasin.
"""
from __future__ import annotations

from pathlib import Path

import config


def belgi_papkasi() -> Path:
    return config.resurs("belgilar")


# Foydalanuvchi ro'yxatdan olib tashlashni so'ragan ikonkalar (robot,
# xoch). Fayllar joyida qoladi — `belgi_kes.py` qayta kessa ham
# qaytib chiqmasin, shuning uchun o'chirish emas, shu ro'yxat.
YASHIRIN = {"education_08.png", "health_08.png"}


def belgilar() -> list[str]:
    """Hamma ikonka fayllari — skrinshot bo'yicha guruhlab, tartib bilan."""
    papka = belgi_papkasi()
    if not papka.is_dir():
        return []
    return sorted(p.name for p in papka.glob("*.png")
                  if p.name not in YASHIRIN)


# Skrinshotlardagi bo'lim nomlari (telefon ilovasidagi «Food»,
# «Personal» …) — o'zbekchaga o'girilgan. Bu IKONKA nomi emas, faqat
# sahifadagi guruh sarlavhasi: ikonkaga nomni foydalanuvchi o'zi beradi.
GURUH_NOMI = {
    "education": "Ta'lim",
    "entertainment": "Ko'ngilochar",
    "finance": "Moliya",
    "food": "Oziq-ovqat",
    "health": "Salomatlik",
    "life": "Turmush",
    "office": "Ofis",
    "others": "Boshqalar",
    "personal": "Shaxsiy",
    "shopping": "Xarid",
    "sports": "Sport",
    "transportation": "Transport",
    "travel": "Sayohat",
}


def guruh(fayl: str) -> str:
    """`food_03.png` → `food`. Kalit — ekranga `guruh_nomi()` chiqadi."""
    return fayl.rsplit("_", 1)[0]


def guruh_nomi(g: str) -> str:
    return GURUH_NOMI.get(g, g.capitalize())


def rasm_yoli(fayl: str | None) -> Path | None:
    if not fayl:
        return None
    yol = belgi_papkasi() / fayl
    return yol if yol.exists() else None


def nomlanganlar(db) -> dict[str, dict]:
    """ikonka fayli → faol kategoriya."""
    return {r["rasm"]: dict(r) for r in db.q(
        "SELECT id, nom, rasm FROM turi WHERE faol=1 AND rasm IS NOT NULL")}


def nom_ber(db, fayl: str, nom: str) -> int:
    """Ikonkaga nom beradi (yoki nomini o'zgartiradi). `turi.id` qaytaradi."""
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Nom bo'sh bo'lmasin")
    if fayl not in belgilar():
        raise ValueError("Bunday ikonka yo'q")

    joriy = nomlanganlar(db).get(fayl)
    band = db.q1("SELECT id, faol, rasm FROM turi WHERE nom=?", nom)

    if joriy:
        if band and band["id"] != joriy["id"]:
            raise ValueError(f"«{nom}» nomli kategoriya allaqachon bor")
        with db.amal(f"Kategoriya nomi: {nom}"):
            db.apply("turi", "UPDATE", {"nom": nom}, joriy["id"])
        return joriy["id"]

    if band:
        if band["faol"]:
            raise ValueError(f"«{nom}» nomli kategoriya allaqachon bor")
        # Oldin nomi olib tashlangan kategoriya — o'sha qatorni qayta
        # tiriltiramiz: eski rasxodlari yana shu nom ostida ko'rinadi.
        with db.amal(f"Kategoriya qaytdi: {nom}"):
            db.apply("turi", "UPDATE", {"faol": 1, "rasm": fayl}, band["id"])
        return band["id"]

    n = db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM turi")
    with db.amal(f"Yangi kategoriya: {nom}"):
        return db.apply("turi", "INSERT", {
            "nom": nom, "belgi": "", "rasm": fayl, "tartib": n})


def nomini_olib_tashla(db, fayl: str) -> None:
    """Ikonka yana nomsiz bo'ladi. Kategoriya o'chmaydi, faqat `faol=0`."""
    joriy = nomlanganlar(db).get(fayl)
    if not joriy:
        return
    with db.amal(f"Kategoriya olib tashlandi: {joriy['nom']}"):
        db.apply("turi", "UPDATE", {"faol": 0}, joriy["id"])
