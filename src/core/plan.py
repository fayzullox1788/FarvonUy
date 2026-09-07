"""Haftalik / oylik reja va reja-fakt solishtiruvi.

TZ dagi talab: "Plan uchun pulni chiqarish uchun alohida narxi bilan
kiritilgan mahsulotlar bo'ladi, shu mahsulotlar belgilanib umumiyi
hisoblanadi. Haftalik umumiy rasxodlar hafta tugaganida qo'yilgan plan
bilan solishtiriladi."

Muhim qoida: reja tuzilganda narx SNAPSHOT qilinadi. Katalogdagi narx
keyin oshsa, o'tgan haftalarning rejasi o'zgarmaydi — aks holda tarix
har safar qayta yoziladi va solishtiruvning ma'nosi qolmaydi.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


# ────────────────────────────────────────────────────────── sana yordamchi

def hafta_boshi(kun: date | str | None = None) -> str:
    d = _kun(kun)
    return (d - timedelta(days=d.weekday())).isoformat()


def hafta_oxiri(kun: date | str | None = None) -> str:
    d = _kun(kun)
    return (d - timedelta(days=d.weekday()) + timedelta(days=6)).isoformat()


def oy_boshi(kun: date | str | None = None) -> str:
    return _kun(kun).replace(day=1).isoformat()


def oy_oxiri(kun: date | str | None = None) -> str:
    d = _kun(kun).replace(day=1)
    keyingi = (d.replace(year=d.year + 1, month=1) if d.month == 12
               else d.replace(month=d.month + 1))
    return (keyingi - timedelta(days=1)).isoformat()


def _kun(kun) -> date:
    if kun is None:
        return date.today()
    if isinstance(kun, str):
        return date.fromisoformat(kun[:10])
    if isinstance(kun, date):
        return kun
    raise TypeError(kun)


# ────────────────────────────────────────────────────────────── katalog

def itemlar(db, faqat_faol: bool = True) -> list:
    shart = " WHERE i.faol=1" if faqat_faol else ""
    return db.q(
        "SELECT i.*, t.nom turi_nom, t.belgi turi_belgi FROM item i"
        f" LEFT JOIN turi t ON t.id=i.turi_id{shart}"
        " ORDER BY t.tartib, i.nom")


def item_qosh(db, nom: str, narx: int, turi_id: int | None = None,
              birlik: str | None = None, cikl_kun: int | None = None) -> int:
    nom = nom.strip()
    if not nom:
        raise ValueError("Mahsulot nomi bo'sh")
    with db.amal(f"Katalog: {nom} qo'shildi"):
        return db.apply("item", "INSERT", {
            "nom": nom, "narx": int(narx), "turi_id": turi_id,
            "birlik": birlik or None, "cikl_kun": cikl_kun})


def item_tahrir(db, item_id: int, **maydonlar) -> None:
    with db.amal("Katalog tahrirlandi"):
        db.apply("item", "UPDATE", maydonlar, item_id)


def item_ochir(db, item_id: int) -> None:
    with db.amal("Katalogdan o'chirildi"):
        db.apply("item", "UPDATE", {"faol": 0}, item_id)


# ───────────────────────────────────────────────────────────────── reja

def reja_ol(db, boshi: str, tur: str = "haftalik"):
    return db.q1("SELECT * FROM reja WHERE tur=? AND boshi=?", tur, boshi)


def reja_yarat(db, boshi: str, tur: str = "haftalik",
               katalogdan: bool = True) -> int:
    """Reja yaratadi. `katalogdan` bo'lsa — sikli mos keladigan mahsulotlarni
    narx snapshoti bilan qo'shadi."""
    bor = reja_ol(db, boshi, tur)
    if bor:
        return bor["id"]

    oxiri = hafta_oxiri(boshi) if tur == "haftalik" else oy_oxiri(boshi)
    kunlar = 7 if tur == "haftalik" else 30

    with db.amal(f"Reja yaratildi: {boshi}"):
        rid = db.apply("reja", "INSERT", {
            "tur": tur, "boshi": boshi, "oxiri": oxiri})
        if katalogdan:
            for it in itemlar(db):
                cikl = it["cikl_kun"]
                if not cikl:
                    continue
                # sikl davr ichiga necha marta tushadi
                marta = max(1, round(kunlar / cikl))
                db.apply("reja_qator", "INSERT", {
                    "reja_id": rid, "item_id": it["id"], "nom": it["nom"],
                    "turi_id": it["turi_id"],
                    "summa": int(it["narx"]) * marta, "miqdor": marta})
        return rid


def qatorlar(db, reja_id: int) -> list:
    return db.q(
        "SELECT q.*, t.nom turi_nom, t.belgi turi_belgi FROM reja_qator q"
        " LEFT JOIN turi t ON t.id=q.turi_id"
        " WHERE q.reja_id=? AND q.ochirilgan=0 ORDER BY t.tartib, q.nom", reja_id)


def qator_qosh(db, reja_id: int, nom: str, summa: int,
               turi_id: int | None = None, miqdor: float = 1) -> int:
    with db.amal(f"Rejaga qo'shildi: {nom}"):
        return db.apply("reja_qator", "INSERT", {
            "reja_id": reja_id, "nom": nom, "summa": int(summa),
            "turi_id": turi_id, "miqdor": miqdor})


def qator_tahrir(db, qator_id: int, **maydonlar) -> None:
    with db.amal("Reja qatori tahrirlandi"):
        db.apply("reja_qator", "UPDATE", maydonlar, qator_id)


def qator_ochir(db, qator_id: int) -> None:
    with db.amal("Reja qatori o'chirildi"):
        db.apply("reja_qator", "DELETE", qator_id=qator_id)


def bor_belgila(db, qator_id: int, bor: bool) -> None:
    """"Uyda bor" — bu qator xarid ro'yxatidan chiqadi, lekin o'chmaydi."""
    with db.amal("Uyda bor belgilandi"):
        db.apply("reja_qator", "UPDATE", {"bor": 1 if bor else 0}, qator_id)


# ───────────────────────────────────────────────────────── reja vs fakt

@dataclass
class RejaFakt:
    reja_id: int
    boshi: str
    oxiri: str
    reja: int          # olinishi kerak bo'lgan (bor=0) qatorlar yig'indisi
    reja_hammasi: int  # "bor" belgilanganlari bilan birga
    fakt: int          # shu oraliqdagi haqiqiy umumiy rasxod
    farq: int          # fakt - reja  (musbat = oshib ketdi)
    foiz: float

    @property
    def oshdimi(self) -> bool:
        return self.farq > 0


def solishtir(db, reja_id: int) -> RejaFakt:
    r = db.q1("SELECT * FROM reja WHERE id=?", reja_id)
    if not r:
        raise ValueError("Reja topilmadi")
    reja = db.skalyar(
        "SELECT SUM(summa) FROM reja_qator"
        " WHERE reja_id=? AND ochirilgan=0 AND bor=0", reja_id)
    hammasi = db.skalyar(
        "SELECT SUM(summa) FROM reja_qator WHERE reja_id=? AND ochirilgan=0", reja_id)
    fakt = db.skalyar(
        "SELECT SUM(summa) FROM rasxod"
        " WHERE ochirilgan=0 AND umumiymi=1 AND sana BETWEEN ? AND ?",
        r["boshi"], r["oxiri"])
    budjet = r["budjet"] if r["budjet"] is not None else reja
    return RejaFakt(reja_id, r["boshi"], r["oxiri"], budjet, hammasi, fakt,
                    fakt - budjet, (fakt / budjet * 100) if budjet else 0.0)


def oxirgi_rejalar(db, soni: int = 12, tur: str = "haftalik") -> list[RejaFakt]:
    return [solishtir(db, r["id"]) for r in db.q(
        "SELECT id FROM reja WHERE tur=? ORDER BY boshi DESC LIMIT ?", tur, soni)]


# ──────────────────────────────────────────────────────── budjet nazorati

def turi_budjet(db, oy: str) -> list[dict]:
    """Kategoriya bo'yicha oylik budjet va haqiqiy sarf."""
    oxiri = oy_oxiri(oy + "-01")
    natija = []
    for t in db.q("SELECT * FROM turi WHERE faol=1 ORDER BY tartib"):
        b = db.q1("SELECT summa FROM budjet WHERE turi_id=? AND oy IN (?, '*')"
                  " ORDER BY oy DESC LIMIT 1", t["id"], oy)
        fakt = db.skalyar(
            "SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0 AND turi_id=?"
            " AND sana BETWEEN ? AND ?", t["id"], oy + "-01", oxiri)
        if not b and not fakt:
            continue
        budjet = b["summa"] if b else 0
        natija.append({
            "turi_id": t["id"], "nom": t["nom"], "belgi": t["belgi"],
            "budjet": budjet, "fakt": fakt, "farq": fakt - budjet,
            "foiz": (fakt / budjet * 100) if budjet else 0.0})
    return natija


def budjet_qoy(db, turi_id: int, oy: str, summa: int) -> None:
    bor = db.q1("SELECT id FROM budjet WHERE turi_id=? AND oy=?", turi_id, oy)
    with db.amal("Budjet o'zgartirildi"):
        if bor:
            db.apply("budjet", "UPDATE", {"summa": int(summa)}, bor["id"])
        else:
            db.apply("budjet", "INSERT",
                     {"turi_id": turi_id, "oy": oy, "summa": int(summa)})


# ─────────────────────────────────────────────────────────────── prognoz

def prognoz(db, kunlar: int = 30) -> dict:
    """Oxirgi `kunlar` kundagi tempda pul qancha vaqtga yetadi."""
    oxiri = date.today()
    boshi = oxiri - timedelta(days=kunlar)
    sarf = db.skalyar(
        "SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0 AND sana BETWEEN ? AND ?",
        boshi.isoformat(), oxiri.isoformat())
    kunlik = sarf / kunlar if kunlar else 0
    naqd = db.skalyar("SELECT SUM(naqd) FROM v_balans")
    return {
        "kunlik": int(round(kunlik)),
        "haftalik": int(round(kunlik * 7)),
        "oylik": int(round(kunlik * 30)),
        "naqd": naqd,
        "yetadi_kun": int(naqd / kunlik) if kunlik > 0 and naqd > 0 else None,
    }


# ─────────────────────────────────────────── kategoriya ichidagi mahsulot

def turi_itemlari(db, turi_id: int | None) -> list:
    """Shu kategoriyaga tegishli mahsulotlar — narxi bilan.

    Rasxod oynasida kategoriya tanlangach shu ro'yxat chiqadi: mahsulotni
    tanlasangiz narxi o'zi qo'yiladi, lekin uni qo'lda o'zgartirish ham
    mumkin (bozorda narx har doim bir xil emas).
    """
    if turi_id is None:
        return db.q("SELECT * FROM item WHERE faol=1 AND turi_id IS NULL"
                    " ORDER BY nom")
    return db.q("SELECT * FROM item WHERE faol=1 AND turi_id=? ORDER BY nom",
                turi_id)


def item_narx_yangila(db, item_id: int, narx: int) -> None:
    """Xarid paytida narx boshqacha chiqsa — katalogdagi narxni yangilaydi."""
    with db.amal("Mahsulot narxi yangilandi"):
        db.apply("item", "UPDATE", {"narx": int(narx)}, item_id)


def item_topib_qosh(db, nom: str, narx: int, turi_id: int | None) -> int:
    """Shu nomdagi mahsulot bo'lsa qaytaradi, bo'lmasa yaratadi."""
    nom = nom.strip()
    bor = db.q1("SELECT id FROM item WHERE faol=1 AND nom=? AND"
                " (turi_id IS ? OR turi_id=?)", nom, turi_id, turi_id)
    if bor:
        return bor["id"]
    return item_qosh(db, nom, narx, turi_id)
