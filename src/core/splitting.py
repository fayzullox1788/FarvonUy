"""Kim qatnashadi va ulush qanday bo'linadi.

Ikkita savolga javob beradi:
  1. Shu sanadagi umumiy rasxodda kim qatnashadi? (uyda yo'q odam qatnashmaydi)
  2. Ortiqcha so'm kimga tushishi kerak? (shu paytgacha eng kam olganga)
"""
from __future__ import annotations

import money


def qatnashchilar(db, sana: str) -> list[int]:
    """Shu sanada uyda bo'lgan faol odamlar.

    Hech kim qolmasa — hamma qaytariladi (yo'qlik yozuvi xato deb hisoblanadi,
    rasxodni yo'qotgandan ko'ra hammaga bo'lgan yaxshi).
    """
    hamma = [r["id"] for r in db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib,id")]
    yoq = {r["odam_id"] for r in db.q(
        "SELECT DISTINCT odam_id FROM yoq_kun"
        " WHERE ochirilgan=0 AND boshi<=? AND oxiri>=?", sana, sana)}
    qolgan = [i for i in hamma if i not in yoq]
    return qolgan or hamma


def yoq_odamlar(db, sana: str) -> list[str]:
    return [r["nom"] for r in db.q(
        "SELECT DISTINCT o.nom FROM yoq_kun y JOIN odam o ON o.id=y.odam_id"
        " WHERE y.ochirilgan=0 AND y.boshi<=? AND y.oxiri>=? ORDER BY o.tartib",
        sana, sana)]


def yaxlitlash_tarixi(db) -> dict[int, int]:
    """{odam_id: shu paytgacha olgan ortiqcha so'm}."""
    return {r["id"]: r["ortiqcha"] for r in db.q("SELECT id, ortiqcha FROM v_yaxlitlash")}


def hisobla(db, summa: int, sana: str, usul: str = money.USUL_TENG,
            parametrlar: dict[int, float] | None = None) -> list[money.Ulush]:
    """Rasxod ulushlarini hisoblaydi. Yig'indi ANIQ `summa` ga teng."""
    if parametrlar:
        p = dict(parametrlar)
    else:
        p = {i: 1.0 for i in qatnashchilar(db, sana)}
    if not p:
        raise ValueError("bo'linadigan odam yo'q")
    return money.bol(summa, usul, p, yaxlitlash_tarixi(db))
