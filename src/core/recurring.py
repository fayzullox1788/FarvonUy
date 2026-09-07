"""Takroriy rasxodlar — ijara, internet, kommunal.

Dastur ochilganda muddati kelganlarini topadi va foydalanuvchidan
tasdiq so'raydi. HECH QACHON o'zi yozib qo'ymaydi: pul haqidagi
yozuvni odam ko'rmasdan turib kiritish — ishonchni yo'qotishning eng
tez yo'li.
"""
from __future__ import annotations

from datetime import date, timedelta

from core import entries

DAVRIYLIK = {"kunlik": "Har kuni", "haftalik": "Har hafta", "oylik": "Har oy"}
HAFTA_KUN = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba",
             "Juma", "Shanba", "Yakshanba"]


def hammasi(db) -> list:
    return db.q(
        "SELECT tk.*, o.nom odam_nom, t.nom turi_nom, t.belgi turi_belgi"
        " FROM takror tk"
        " LEFT JOIN odam o ON o.id=tk.kim_toladi"
        " LEFT JOIN turi t ON t.id=tk.turi_id"
        " WHERE tk.ochirilgan=0 ORDER BY tk.keyingi_sana")


def qosh(db, nom: str, summa: int, kim_toladi: int, davriylik: str = "oylik",
         kun: int = 1, turi_id: int | None = None, umumiymi: bool = True,
         boshlanish: str | None = None) -> int:
    keyingi = boshlanish or keyingi_sana_hisobla(davriylik, kun, date.today())
    with db.amal(f"Takroriy rasxod: {nom}"):
        return db.apply("takror", "INSERT", {
            "nom": nom, "summa": int(summa), "kim_toladi": kim_toladi,
            "davriylik": davriylik, "kun": int(kun), "turi_id": turi_id,
            "umumiymi": 1 if umumiymi else 0, "keyingi_sana": keyingi})


def tahrir(db, takror_id: int, **maydonlar) -> None:
    with db.amal("Takroriy rasxod tahrirlandi"):
        db.apply("takror", "UPDATE", maydonlar, takror_id)


def ochir(db, takror_id: int) -> None:
    with db.amal("Takroriy rasxod o'chirildi"):
        db.apply("takror", "DELETE", qator_id=takror_id)


def keyingi_sana_hisobla(davriylik: str, kun: int, dan: date) -> str:
    """`dan` kunidan KEYINGI birinchi mos sana."""
    if davriylik == "kunlik":
        return (dan + timedelta(days=1)).isoformat()

    if davriylik == "haftalik":
        nishon = max(1, min(7, int(kun))) - 1        # 0=Dushanba
        farq = (nishon - dan.weekday()) % 7 or 7
        return (dan + timedelta(days=farq)).isoformat()

    # oylik
    k = max(1, min(28, int(kun)))
    if dan.day < k:
        return dan.replace(day=k).isoformat()
    y, m = (dan.year + 1, 1) if dan.month == 12 else (dan.year, dan.month + 1)
    return date(y, m, k).isoformat()


def kutilayotgan(db, sanagacha: str | None = None) -> list[dict]:
    """Muddati kelgan, lekin hali yozilmagan takroriy rasxodlar."""
    chegara = sanagacha or date.today().isoformat()
    natija = []
    for t in db.q(
            "SELECT tk.*, o.nom odam_nom FROM takror tk"
            " LEFT JOIN odam o ON o.id=tk.kim_toladi"
            " WHERE tk.ochirilgan=0 AND tk.faol=1 AND tk.keyingi_sana<=?"
            " ORDER BY tk.keyingi_sana", chegara):
        natija.append({
            "id": t["id"], "nom": t["nom"], "summa": t["summa"],
            "sana": t["keyingi_sana"], "kim_toladi": t["kim_toladi"],
            "odam_nom": t["odam_nom"], "umumiymi": t["umumiymi"],
            "turi_id": t["turi_id"]})
    return natija


def yoz(db, takror_id: int, sana: str | None = None,
        summa: int | None = None) -> int:
    """Takroriy rasxodni haqiqiy rasxodga aylantiradi va muddatni suradi."""
    t = db.q1("SELECT * FROM takror WHERE id=?", takror_id)
    if not t:
        raise ValueError("Takroriy rasxod topilmadi")
    s = sana or t["keyingi_sana"]
    keyingi = keyingi_sana_hisobla(t["davriylik"], t["kun"],
                                   date.fromisoformat(s))
    with db.amal(f"Takroriy rasxod yozildi: {t['nom']}"):
        rid = entries.rasxod_qosh(
            db, s, t["nom"], int(summa if summa is not None else t["summa"]),
            t["kim_toladi"], umumiymi=bool(t["umumiymi"]),
            turi_id=t["turi_id"], takror_id=takror_id)
        db.apply("takror", "UPDATE", {"keyingi_sana": keyingi}, takror_id)
        return rid


def otkaz(db, takror_id: int) -> None:
    """Bu safar yozmaymiz — shunchaki keyingi muddatga o'tamiz."""
    t = db.q1("SELECT * FROM takror WHERE id=?", takror_id)
    if not t:
        return
    keyingi = keyingi_sana_hisobla(
        t["davriylik"], t["kun"], date.fromisoformat(t["keyingi_sana"]))
    with db.amal(f"Takroriy rasxod o'tkazildi: {t['nom']}"):
        db.apply("takror", "UPDATE", {"keyingi_sana": keyingi}, takror_id)
