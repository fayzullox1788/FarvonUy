"""Hisob-kitob: eng kam to'lov bilan hammani tenglashtirish.

Excel'da Otabek Fayzulloxonga 11 ta alohida qator bo'ylab qarzdor edi va
har birini qo'lda "Ha" qilish kerak edi. Bu yerda dastur o'zi hisoblaydi:
"Otabek Fayzulloxonga 547 667 so'm bersin — tamom, hamma tinch".

n kishi uchun ko'pi bilan n−1 ta to'lov chiqadi (3 kishi → 2 ta).
"""
from __future__ import annotations

from dataclasses import dataclass

import money
from core import entries, ledger


@dataclass
class Kochirma:
    kimdan_id: int
    kimga_id: int
    kimdan_nom: str
    kimga_nom: str
    summa: int

    def __str__(self) -> str:
        return f"{self.kimdan_nom} → {self.kimga_nom}: {money.fmt_som(self.summa)}"


def taklif(db) -> list[Kochirma]:
    """Hammani nolga keltiradigan eng kam to'lovlar ro'yxati.

    Ochko'z algoritm: eng katta qarzdorni eng katta kreditor bilan
    juftlaydi. Har qadamda kamida bitta odam nolga tushadi, shuning
    uchun natija hech qachon n−1 tadan oshmaydi.
    """
    qatorlar = ledger.balanslar(db)
    qarzdor = [[r["id"], r["nom"], -r["sof"]] for r in qatorlar if r["sof"] < 0]
    kreditor = [[r["id"], r["nom"], r["sof"]] for r in qatorlar if r["sof"] > 0]
    if not qarzdor or not kreditor:
        return []

    qarzdor.sort(key=lambda x: -x[2])
    kreditor.sort(key=lambda x: -x[2])

    natija: list[Kochirma] = []
    i = j = 0
    while i < len(qarzdor) and j < len(kreditor):
        s = min(qarzdor[i][2], kreditor[j][2])
        if s > 0:
            natija.append(Kochirma(qarzdor[i][0], kreditor[j][0],
                                   qarzdor[i][1], kreditor[j][1], s))
            qarzdor[i][2] -= s
            kreditor[j][2] -= s
        if qarzdor[i][2] == 0:
            i += 1
        if j < len(kreditor) and kreditor[j][2] == 0:
            j += 1
    return natija


def bajar(db, kochirmalar: list[Kochirma], sana: str,
          izoh: str = "Hisob-kitob") -> None:
    """Taklifni haqiqiy to'lovlarga aylantiradi — bitta undo qadami."""
    if not kochirmalar:
        return
    with db.amal(f"Hisob-kitob: {len(kochirmalar)} ta to'lov"):
        for k in kochirmalar:
            db.apply("hisob_kitob", "INSERT", {
                "sana": sana, "kim_toladi": k.kimdan_id, "kimga": k.kimga_id,
                "summa": k.summa, "izoh": izoh})


def juft_tolov(db, kimdan_id: int, kimga_id: int, summa: int, sana: str,
               izoh: str = "") -> int:
    """Qisman to'lov — masalan Otabek 200 000 berdi, hammasini emas."""
    return entries.hisob_kitob_qosh(db, sana, kimdan_id, kimga_id, summa,
                                    izoh or "Qisman to'lov")


# ══════════════════════════════════════════════ blok-blok hisob-kitob
#
# Hammasini bir yo'la yopish har doim ham to'g'ri kelmaydi: ko'pincha
# "mana shu bozorlikning pulini berdim" deyiladi, "hamma qarzimni
# yopdim" emas. Shuning uchun har bir ulushni ALOHIDA yopish mumkin —
# Excel'dagi qator yonidagi "Ha" belgisining o'rni aynan shu.


def ochiq_bloklar(db, qarzdor_id: int | None = None,
                  kreditor_id: int | None = None,
                  tolanganlar: bool = False) -> list:
    """To'lanmagan (yoki hammasi) bloklar ro'yxati, yangisidan eskisiga."""
    shart = ["1=1"]
    p: list = []
    if not tolanganlar:
        shart.append("tolandi=0")
    if qarzdor_id:
        shart.append("qarzdor_id=?")
        p.append(qarzdor_id)
    if kreditor_id:
        shart.append("kreditor_id=?")
        p.append(kreditor_id)
    return db.q(
        f"SELECT * FROM v_ochiq_ulush WHERE {' AND '.join(shart)}"
        f" ORDER BY tolandi, sana DESC, rasxod_id DESC", *p)


def blok_yop(db, ulush_id: int, sana: str | None = None) -> int:
    """Bitta blokni to'landi deb belgilaydi va shu summaga to'lov yozadi."""
    u = db.q1("SELECT * FROM v_ochiq_ulush WHERE ulush_id=?", ulush_id)
    if not u:
        raise ValueError("Blok topilmadi")
    if u["tolandi"]:
        return 0
    s = sana or u["sana"]
    with db.amal(f"To'landi: {u['nom'] or '—'} — {u['qarzdor']} → {u['kreditor']}"):
        hk = db.apply("hisob_kitob", "INSERT", {
            "sana": s, "kim_toladi": u["qarzdor_id"], "kimga": u["kreditor_id"],
            "summa": u["summa"], "ulush_id": ulush_id,
            "izoh": f"{u['nom'] or 'rasxod'} ({u['sana']}) uchun"})
        db.apply("ulush", "UPDATE",
                 {"tolandi": 1, "tolangan_sana": s}, ulush_id)
        return hk


def blok_och(db, ulush_id: int) -> None:
    """Blokni qayta ochadi va u bilan bog'liq to'lovni bekor qiladi."""
    u = db.q1("SELECT * FROM v_ochiq_ulush WHERE ulush_id=?", ulush_id)
    if not u or not u["tolandi"]:
        return
    with db.amal(f"Qayta ochildi: {u['nom'] or '—'}"):
        for h in db.q("SELECT id FROM hisob_kitob"
                      " WHERE ulush_id=? AND ochirilgan=0", ulush_id):
            db.apply("hisob_kitob", "DELETE", qator_id=h["id"])
        db.apply("ulush", "UPDATE",
                 {"tolandi": 0, "tolangan_sana": None}, ulush_id)


def bloklarni_yop(db, ulush_idlar: list[int], sana: str | None = None) -> int:
    """Bir nechta blokni bitta undo qadamida yopadi."""
    n = 0
    with db.amal(f"{len(ulush_idlar)} ta blok to'landi"):
        for i in ulush_idlar:
            if blok_yop(db, i, sana):
                n += 1
    return n
