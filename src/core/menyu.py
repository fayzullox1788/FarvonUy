"""Menyu — guruhda oshpaz tanlaydigan taomlar ro'yxati.

Pulga TEGMAYDI, shuning uchun `ledger.audit()` bu jadvalni ko'rmaydi.
Qt ni ham bilmaydi: ro'yxatni `xabar.py` ham, `ui/` ham shu yerdan
oladi.

Taom `vazifa.menyu` ga NOM bilan yoziladi, `menyu.id` bilan emas:
foydalanuvchi taomni ro'yxatdan olib tashlasa ham «o'sha kuni nima
pishirilgan» degan yozuv joyida qolishi kerak.
"""
from __future__ import annotations


def royxat(db) -> list:
    return db.q("SELECT * FROM menyu WHERE ochirilgan=0"
                " ORDER BY tartib, id")


def bitta(db, menyu_id: int):
    return db.q1("SELECT * FROM menyu WHERE id=? AND ochirilgan=0", menyu_id)


def nomlar(db) -> list[str]:
    return [r["nom"] for r in royxat(db)]


def qosh(db, nom: str) -> int:
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Taom nomi bo'sh bo'lishi mumkin emas")
    # `nom` UNIQUE — o'chirilgani bor bo'lsa INSERT yiqiladi, shuning
    # uchun uni tiriltiramiz (`vazifa.tur_qosh()` bilan bir xil).
    eski = db.q1("SELECT id, ochirilgan FROM menyu WHERE nom=?", nom)
    if eski and eski["ochirilgan"]:
        with db.amal(f"Menyuga qaytarildi: {nom}"):
            db.apply("menyu", "UPDATE", {"ochirilgan": 0}, eski["id"])
        return eski["id"]
    if eski:
        raise ValueError(f"«{nom}» menyuda bor")
    tartib = db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM menyu")
    with db.amal(f"Menyuga qo'shildi: {nom}"):
        return db.apply("menyu", "INSERT", {"nom": nom, "tartib": tartib})


def ochir(db, menyu_id: int) -> None:
    t = bitta(db, menyu_id)
    if not t:
        raise ValueError("Taom topilmadi")
    with db.amal(f"Menyudan olindi: {t['nom']}"):
        db.apply("menyu", "DELETE", qator_id=menyu_id)
