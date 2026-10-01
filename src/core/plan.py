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

import money
from core import ledger


# ────────────────────────────────────────────────────────── sana yordamchi

def hafta_boshi(kun: date | str | None = None) -> str:
    d = _kun(kun)
    return (d - timedelta(days=d.weekday())).isoformat()


def hafta_oxiri(kun: date | str | None = None) -> str:
    d = _kun(kun)
    return (d - timedelta(days=d.weekday()) + timedelta(days=6)).isoformat()


def oy_boshi(kun: date | str | None = None) -> str:
    return _kun(kun).replace(day=1).isoformat()


def oy_bugungacha(kun: date | str | None = None) -> tuple[str, str]:
    """Joriy oyning 1-kunidan BUGUNGACHA. 1-noyabrda — faqat 1-noyabr."""
    d = _kun(kun)
    return d.replace(day=1).isoformat(), d.isoformat()


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
    shart = " WHERE i.ochirilgan=0" + (" AND i.faol=1" if faqat_faol else "")
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
        # Ichki kategoriyalardagi rasxod ham otasining budjetiga kiradi.
        fakt = db.skalyar(
            "WITH RECURSIVE a(id) AS (SELECT ?"
            " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)"
            " SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0"
            " AND turi_id IN (SELECT id FROM a)"
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


# ─────────────────────────────────────────────────── reja va fakt (oylik)
#
# «Analitika → Reja va fakt» shu yerdan o'qiydi. Yangi jadval YO'Q:
#   • umumiy oylik reja — `reja` qatori (tur='oylik', boshi=oyning 1-kuni),
#     summasi `reja.budjet` da. Haftalik rejalar bilan bir jadvalda, lekin
#     `tur` bilan ajralgan.
#   • kategoriya rejasi — eski `budjet` jadvali (oy yoki '*' — har oy).
# Fakt — shu oydagi HAMMA rasxod (umumiy ham, shaxsiy ham), ichki
# kategoriya otasiga qo'shilgan (`ledger.turi_boyicha`). Foiz butun son,
# 100 dan oshishi mumkin — oshib ketgan reja yashirilmaydi.

YAQIN_FOIZ = 80        # shundan boshlab «limitga yaqin»


def oy_kaliti(kun: date | str | None = None) -> str:
    """'2026-09-25' → '2026-09'."""
    return _kun(kun).isoformat()[:7]


def oy_sur(oy: str, qadam: int) -> str:
    """'2026-09' + 1 → '2026-10'."""
    y, m = int(oy[:4]), int(oy[5:7]) - 1 + qadam
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def oylik_reja(db, oy: str) -> int | None:
    """Umumiy oylik reja yoki None (qo'yilmagan)."""
    r = reja_ol(db, oy + "-01", "oylik")
    return r["budjet"] if r and r["budjet"] else None


def limit_reja(db, oy: str) -> dict[int, int]:
    """{turi_id: limit} — «Umumiy reja va limitlar» oynasidagi kategoriya
    summalari (`budjet` jadvali), faqat asosiy kategoriyalar, faqat > 0.

    Oyning o'z qatori '*' (har oy) dan ustun: shu oy uchun 0 qo'yilsa
    '*' dagi reja shu oyda o'chadi.
    """
    natija = {}
    for r in db.q("SELECT b.turi_id, b.summa FROM budjet b"
                  " JOIN turi t ON t.id=b.turi_id"
                  " WHERE t.ota_id IS NULL AND b.oy IN (?, '*')"
                  " ORDER BY b.oy='*' DESC", oy):
        natija[r["turi_id"]] = r["summa"]      # oyniki '*' ni bosadi
    return {k: v for k, v in natija.items() if v > 0}


# Reja ikki doirada (2026-10-01, foydalanuvchi so'ragan): UMUMIY — uyniki
# (`odam_id=None`), SHAXSIY — bitta odamniki (`odam_id=<id>`). Yozuv
# `reja_qator.umumiymi/odam_id` da. Umumiy oylik summa va kategoriya
# limitlari (`budjet`) faqat UMUMIY. Fakt ham shunga mos: umumiy —
# umumiy rasxodlarning butun summasi, shaxsiy — odamning shaxsiy
# rasxodi (+ uning uchun olingani), `ledger._manba` qoidasi.

def _doira_sharti(odam_id: int | None) -> tuple[str, tuple]:
    if odam_id is None:
        return " AND q.umumiymi=1", ()
    return " AND q.umumiymi=0 AND q.odam_id=?", (odam_id,)


def yozuv_reja(db, oy: str, odam_id: int | None = None) -> dict[int, int]:
    """{asosiy turi_id: summa} — rasxod kabi kiritilgan reja yozuvlari,
    ichki kategoriyasi otasiga qo'shilgan (`turi_boyicha` qoidasi).
    `odam_id` None — umumiy yozuvlar, aks holda o'sha odamning shaxsiysi."""
    shart, args = _doira_sharti(odam_id)
    return {r["ildiz"]: r["jami"] for r in db.q(
        "WITH RECURSIVE y(id, ildiz) AS ("
        "  SELECT id, id FROM turi WHERE ota_id IS NULL"
        "  UNION ALL SELECT t.id, y.ildiz FROM turi t JOIN y ON t.ota_id=y.id)"
        " SELECT y.ildiz, SUM(q.summa) jami FROM reja_qator q"
        " JOIN reja r ON r.id=q.reja_id JOIN y ON y.id=q.turi_id"
        " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0" + shart +
        " GROUP BY y.ildiz", oy + "-01", *args) if r["jami"]}


def turi_reja(db, oy: str, odam_id: int | None = None) -> dict[int, int]:
    """{turi_id: reja} — faqat asosiy kategoriyalar, faqat > 0.

    Umumiy: kiritilgan umumiy reja yozuvlari + kategoriya limiti
    (`limit_reja`). Shaxsiy (`odam_id`): faqat o'sha odamning yozuvlari.
    """
    natija = dict(limit_reja(db, oy)) if odam_id is None else {}
    for tid, summa in yozuv_reja(db, oy, odam_id).items():
        natija[tid] = natija.get(tid, 0) + summa
    return {k: v for k, v in natija.items() if v > 0}


def reja_saqla(db, oy: str, umumiy: int | None,
               turlar: dict[int, int]) -> None:
    """Oy rejasini BITTA undo qadamida saqlaydi.

    `umumiy` None/0 — umumiy reja olib tashlanadi (qator qoladi,
    `budjet` NULL). `turlar` — {turi_id: summa}; faqat o'zgarganlari
    yoziladi, 0 — shu oyda reja yo'q.
    """
    eski = limit_reja(db, oy)
    with db.amal(f"Oylik reja: {oy}"):
        r = reja_ol(db, oy + "-01", "oylik")
        yangi = int(umumiy) if umumiy and umumiy > 0 else None
        if r is None and yangi is not None:
            rid = reja_yarat(db, oy + "-01", "oylik", katalogdan=False)
            db.apply("reja", "UPDATE", {"budjet": yangi}, rid)
        elif r is not None and r["budjet"] != yangi:
            db.apply("reja", "UPDATE", {"budjet": yangi}, r["id"])
        for tid, summa in turlar.items():
            summa = max(0, int(summa or 0))
            if summa != eski.get(tid, 0):
                budjet_qoy(db, tid, oy, summa)


HAMMASI = "hammasi"


def reja_bormi(db, oy: str, odam_id=HAMMASI) -> bool:
    """Shu oyda reja bormi. Birlamchi — HAR QANDAY (umumiy yoki biror
    odamning shaxsiysi); `None` — faqat umumiy, `<id>` — o'sha odamniki."""
    if odam_id == HAMMASI:
        return reja_bormi(db, oy, None) or bool(db.skalyar(
            "SELECT COUNT(*) FROM reja_qator q JOIN reja r ON r.id=q.reja_id"
            " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0"
            " AND q.umumiymi=0", oy + "-01"))
    if odam_id is None and oylik_reja(db, oy) is not None:
        return True
    return bool(turi_reja(db, oy, odam_id))


def reja_kategoriyalari(db, oy: str) -> list[dict]:
    """Limit oynasi uchun: har asosiy kategoriya — limiti va shu oydagi
    fakti bilan. Nofaol kategoriya faqat limiti yoki fakti bo'lsa.
    `reja` — faqat LIMIT (oynada tahrirlanadigan qism), kiritilgan reja
    yozuvlari `yozuv` da alohida."""
    rejalar = limit_reja(db, oy)
    yozuvlar = yozuv_reja(db, oy)
    fakt = {t["turi_id"]: t["summa"] for t in ledger.turi_boyicha(
        db, oy + "-01", oy_oxiri(oy + "-01"), qism="umumiy")}
    natija = []
    for t in db.q("SELECT id, nom, belgi, rasm, faol FROM turi"
                  " WHERE ota_id IS NULL ORDER BY tartib, id"):
        r, f = rejalar.get(t["id"], 0), fakt.get(t["id"], 0)
        if t["faol"] or r or f:
            natija.append({"turi_id": t["id"], "nom": t["nom"],
                           "belgi": t["belgi"], "rasm": t["rasm"],
                           "reja": r, "fakt": f,
                           "yozuv": yozuvlar.get(t["id"], 0)})
    return natija


def reja_kochir(db, dan: str, ga: str) -> bool:
    """`dan` oyning rejasini `ga` oyga ko'chiradi (bitta undo): umumiy
    summa, limitlar va reja yozuvlari (mahsulotlari bilan, sanasi o'sha
    kunga). `dan` da reja bo'lmasa hech narsa yozilmaydi — False."""
    if not reja_bormi(db, dan):
        return False
    with db.amal(f"Reja ko'chirildi: {dan} → {ga}"):
        reja_saqla(db, ga, oylik_reja(db, dan), limit_reja(db, dan))
        oxirgi = int(oy_oxiri(ga + "-01")[8:10])
        for y in reja_yozuvlari(db, dan):
            kun = min(int((y["sana"] or dan + "-01")[8:10]), oxirgi)
            reja_yozuv_saqla(
                db, f"{ga}-{kun:02d}", y["nom"], y["turi_id"], y["summa"],
                reja_yozuv_mahsulotlari(db, y["id"]), majburiy=False,
                umumiymi=bool(y["umumiymi"]), odam_id=y["odam_id"])
    return True


# ─────────────────────────────────────── reja yozuvlari (rasxod kabi)
#
# Reja rasxod kabi qo'shiladi (2026-10-01, foydalanuvchi so'ragan): sana,
# kategoriya, ichida bir nechta mahsulot, sabab va summa. Yozuv — oylik
# rejaning (`reja`, tur='oylik') `reja_qator` qatori; mahsulotlari
# `reja_mahsulot` da. Sana qaysi oyga tushsa, o'sha oyning rejasiga
# yoziladi. Pulga tegmaydi — bu faqat reja, `v_balans` uni o'qimaydi.

def reja_yozuv_saqla(db, sana: str, nom: str, turi_id: int | None,
                     summa: int, mahsulotlar: list[dict] | None = None,
                     qator_id: int | None = None,
                     majburiy: bool = True, umumiymi: bool = True,
                     odam_id: int | None = None) -> int:
    """Yangi reja yozuvi yoki mavjudini tahrirlash — bitta undo.

    Qoida rasxodniki bilan bir xil: sabab va faol kategoriya majburiy,
    mahsulotlar bo'lsa summa — ularning yig'indisi. Shaxsiy reja
    (`umumiymi=False`) kimniki ekani bilan — `odam_id` majburiy.
    """
    if umumiymi:
        odam_id = None
    elif odam_id is None or (majburiy and not db.q1(
            "SELECT 1 FROM odam WHERE id=? AND faol=1", odam_id)):
        raise ValueError("Shaxsiy reja kimniki ekanini tanlang.")
    from core import entries
    from core import rasxod_kirit as rk
    sana = _kun(sana).isoformat()
    nom = (nom or "").strip()
    qatorlar = rk.mahsulot_qatorlari(db, mahsulotlar)
    summa = int(summa or 0)
    if qatorlar and rk.qatorlar_jami(qatorlar) != summa:
        raise ValueError(
            f"Summa mahsulotlar yig'indisiga teng emas "
            f"({money.fmt_som(rk.qatorlar_jami(qatorlar))}).")
    if summa <= 0:
        raise ValueError("Summa kiritilmagan.")
    if majburiy:
        entries.rasxod_majburiy(db, nom, turi_id)
    oy = oy_kaliti(sana)
    maydonlar = {"nom": nom, "turi_id": turi_id, "summa": summa,
                 "sana": sana, "miqdor": 1,
                 "umumiymi": 1 if umumiymi else 0, "odam_id": odam_id}
    with db.amal(f"Reja: {nom or '—'} {money.fmt(summa)}"):
        rk.yangi_mahsulotlarni_qosh(db, qatorlar, turi_id)
        maydonlar["item_id"] = (qatorlar[0]["item_id"]
                                if len(qatorlar) == 1 else None)
        r = reja_ol(db, oy + "-01", "oylik")
        maydonlar["reja_id"] = (r["id"] if r else
                                reja_yarat(db, oy + "-01", "oylik",
                                           katalogdan=False))
        if qator_id is None:
            qator_id = db.apply("reja_qator", "INSERT", maydonlar)
        else:
            db.apply("reja_qator", "UPDATE", maydonlar, qator_id)
        rk.qatorlarni_yoz(db, "reja_mahsulot", "qator_id", qator_id, qatorlar)
    return qator_id


def reja_yozuv_nusxa(db, qator_id: int, sana: str | None = None) -> int:
    """Reja ro'yxatidan nusxa — oddiy yangi ro'yxat (bitta undo): nomi,
    kategoriyasi, umumiy/shaxsiyligi va mahsulotlari bilan. «Aslida
    to'landi» va bog'langan rasxod KO'CHMAYDI — nusxa hali olinmagan.
    Sana berilmasa — keyingi kun, lekin o'sha oydan chiqmaydi."""
    y = db.q1("SELECT * FROM reja_qator WHERE id=? AND ochirilgan=0",
              qator_id)
    if not y:
        raise ValueError("Reja ro'yxati topilmadi.")
    if sana is None:
        asl = _kun(y["sana"] or date.today())
        keyingi = asl + timedelta(days=1)
        sana = (keyingi if keyingi.month == asl.month else asl).isoformat()
    return reja_yozuv_saqla(
        db, sana, y["nom"], y["turi_id"], y["summa"],
        reja_yozuv_mahsulotlari(db, qator_id), majburiy=False,
        umumiymi=bool(y["umumiymi"]), odam_id=y["odam_id"])


def reja_yozuv_ochir(db, qator_id: int) -> None:
    r = db.q1("SELECT nom FROM reja_qator WHERE id=?", qator_id)
    with db.amal(f"Reja o'chirildi: {(r['nom'] if r else '') or '—'}"):
        db.apply("reja_qator", "DELETE", qator_id=qator_id)


def reja_yozuvlari(db, oy: str, odam_id=HAMMASI) -> list:
    """Oyning reja yozuvlari — kategoriya, kimniki va mahsulotlar soni
    bilan. `odam_id`: HAMMASI | None (umumiy) | <id> (shaxsiy)."""
    shart, args = ("", ()) if odam_id == HAMMASI else _doira_sharti(odam_id)
    return db.q(
        "SELECT q.*, t.nom turi_nom, t.belgi turi_belgi, t.rasm turi_rasm,"
        " o.nom odam_nom,"
        " (SELECT COUNT(*) FROM reja_mahsulot m WHERE m.qator_id=q.id"
        "  AND m.ochirilgan=0) mahsulot_soni"
        " FROM reja_qator q JOIN reja r ON r.id=q.reja_id"
        " LEFT JOIN turi t ON t.id=q.turi_id"
        " LEFT JOIN odam o ON o.id=q.odam_id"
        " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0" + shart +
        " ORDER BY COALESCE(q.sana, r.boshi), q.id", oy + "-01", *args)


def kategoriya_reja_yozuvlari(db, oy: str, turi_id: int,
                              odam_id: int | None = None) -> list[dict]:
    """«Reja va fakt» dagi toifa ICHI: shu asosiy kategoriyaning (ichkilari
    bilan) reja yozuvlari, sana bo'yicha, har biri mahsulotlari va
    «aslida to'landi» summalari bilan. Doira — `reja_va_fakt` niki."""
    idlar = {r["id"] for r in db.q(
        "WITH RECURSIVE a(id) AS (SELECT ?"
        " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)"
        " SELECT id FROM a", turi_id)}
    natija = []
    for y in reja_yozuvlari(db, oy, odam_id):
        if y["turi_id"] not in idlar:
            continue
        natija.append(_toliq(db, y))
    return natija


def _toliq(db, y) -> dict:
    x = dict(y)
    x["mahsulotlar"] = [dict(m) for m in db.q(
        "SELECT id, item_id, nom, miqdor, summa, tolangan"
        " FROM reja_mahsulot WHERE qator_id=? AND ochirilgan=0"
        " ORDER BY tartib, id", y["id"])]
    r = (db.q1("SELECT id, sana, kim_toladi, summa FROM rasxod"
               " WHERE id=? AND ochirilgan=0", y["rasxod_id"])
         if y["rasxod_id"] else None)
    x["rasxod"] = dict(r) if r else None
    return x


def limitni_royxatga(db, oy: str, turi_id: int) -> int:
    """Kategoriya LIMITI («Umumiy reja va limitlar») ni oddiy reja
    ro'yxatiga aylantiradi — toifa ichida ochib «aslida to'landi» yozish
    uchun. Bitta undo: ro'yxat (nomi — kategoriya, summasi — limit,
    sanasi — oy ichida bugun yoki oyning 1-kuni) + shu oy limiti 0.
    Kategoriya rejasi summasi o'zgarmaydi."""
    limit = limit_reja(db, oy).get(turi_id, 0)
    if limit <= 0:
        raise ValueError("Bu kategoriyada limit yo'q.")
    nom = db.skalyar("SELECT nom FROM turi WHERE id=?", turi_id,
                     birlamchi="Reja")
    bugun = date.today().isoformat()
    sana = bugun if bugun[:7] == oy else oy + "-01"
    with db.amal(f"Limit ro'yxatga aylantirildi: {nom}"):
        qid = reja_yozuv_saqla(db, sana, nom, turi_id, limit,
                               majburiy=False)
        budjet_qoy(db, turi_id, oy, 0)
    return qid


def kun_reja_yozuvlari(db, sana: str | None = None) -> list[dict]:
    """Shu KUNGA rejalangan ro'yxatlar — umumiy ham, hammaning shaxsiysi
    ham («Bugun» sahifasidagi «Bugunga rejalangan» kartasi)."""
    sana = _kun(sana).isoformat()
    return [_toliq(db, y) for y in db.q(
        "SELECT q.*, t.nom turi_nom, t.belgi turi_belgi, o.nom odam_nom"
        " FROM reja_qator q JOIN reja r ON r.id=q.reja_id"
        " LEFT JOIN turi t ON t.id=q.turi_id"
        " LEFT JOIN odam o ON o.id=q.odam_id"
        " WHERE r.tur='oylik' AND q.ochirilgan=0 AND q.sana=?"
        " ORDER BY q.umumiymi DESC, q.id", sana)]


# Reja — kategoriyaga ajratilgan pul (2026-10-01, foydalanuvchi so'ragan):
# ro'yxatdagi mahsulotlar faqat TAFSILOT. Shu kategoriyadan qilingan HAR
# QANDAY rasxod (ro'yxatga bog'langan-bog'lanmaganidan qat'i nazar) o'sha
# kategoriya rejasidan ayiriladi — kun bo'yicha ham, oy bo'yicha ham.
# Fakt `reja_va_fakt` dagi bilan BITTA manbadan (`ledger._manba`) o'qiladi.

def _ildiz(db, turi_id: int | None) -> int | None:
    while turi_id is not None:
        r = db.q1("SELECT ota_id FROM turi WHERE id=?", turi_id)
        if not r or r["ota_id"] is None:
            return turi_id
        turi_id = r["ota_id"]
    return None


def _kun_fakt(db, turi_id: int | None, boshi: str, oxiri: str,
              odam_id: int | None) -> dict[str, int]:
    """{sana: summa} — asosiy kategoriyaning (ichkilari bilan) rasxodi,
    `reja_va_fakt` doirasida: umumiy yoki o'sha odamning shaxsiysi."""
    kunlar: dict[str, int] = {}
    for r in ledger.kategoriya_rasxodlari(
            db, [turi_id], boshi, oxiri, odam_id,
            "shaxsiy" if odam_id else "umumiy"):
        kunlar[r["sana"][:10]] = kunlar.get(r["sana"][:10], 0) + r["summa"]
    return kunlar


def kategoriya_kunlari(db, oy: str, turi_id: int | None,
                       odam_id: int | None = None) -> dict:
    """Toifa ichi, KUN bo'yicha: har kunning rejasi (o'sha kungi
    ro'yxatlar), shu kategoriyadan o'sha kuni qilingan HAMMA rasxod va
    qolgani. Limit (sanasiz) faqat oy jamiga qo'shiladi.

    Qaytadi: {reja, fakt, qolgan, limit,
              kunlar: [{sana, reja, fakt, qolgan, royxatlar: [nom]}]}
    `reja`/`fakt` — `reja_va_fakt` dagi shu toifa qatori bilan AYNAN teng.
    """
    boshi, oxiri = oy + "-01", oy_oxiri(oy + "-01")
    kunlar: dict[str, dict] = {}

    def _k(sana):
        return kunlar.setdefault(sana, {"sana": sana, "reja": 0, "fakt": 0,
                                        "royxatlar": []})
    for y in kategoriya_reja_yozuvlari(db, oy, turi_id, odam_id):
        k = _k((y["sana"] or boshi)[:10])
        k["reja"] += y["summa"]
        k["royxatlar"].append(y["nom"] or "—")
    for sana, summa in _kun_fakt(db, turi_id, boshi, oxiri, odam_id).items():
        _k(sana)["fakt"] += summa
    qatorlar = sorted(kunlar.values(), key=lambda k: k["sana"])
    for k in qatorlar:
        k["qolgan"] = k["reja"] - k["fakt"]
    limit = (limit_reja(db, oy).get(turi_id, 0)
             if odam_id is None and turi_id is not None else 0)
    reja = sum(k["reja"] for k in qatorlar) + limit
    fakt = sum(k["fakt"] for k in qatorlar)
    return {"reja": reja, "fakt": fakt, "qolgan": reja - fakt,
            "limit": limit, "kunlar": qatorlar}


def kun_kategoriyalari(db, sana: str | None = None) -> list[dict]:
    """«Bugun» kartasi: shu kunga reja qo'yilgan har bir kategoriya
    (doirasi bilan — umumiy yoki kimningdir shaxsiysi): bugungi reja,
    shu kategoriyadan bugun qilingan HAMMA rasxod, qolgani va oy
    bo'yicha qolgani. Ro'yxat nomlari — tafsilot."""
    sana = _kun(sana).isoformat()
    oy = oy_kaliti(sana)
    guruh: dict[tuple, dict] = {}
    for y in kun_reja_yozuvlari(db, sana):
        odam = None if y["umumiymi"] else y["odam_id"]
        ildiz = _ildiz(db, y["turi_id"])
        g = guruh.get((odam, ildiz))
        if g is None:
            t = (db.q1("SELECT nom, belgi FROM turi WHERE id=?", ildiz)
                 if ildiz is not None else None)
            g = guruh[(odam, ildiz)] = {
                "turi_id": ildiz, "odam_id": odam,
                "odam_nom": y["odam_nom"] if odam else None,
                "nom": t["nom"] if t else "Kategoriyasiz",
                "belgi": (t["belgi"] or "") if t else "",
                "reja": 0, "royxatlar": []}
        g["reja"] += y["summa"]
        g["royxatlar"].append(y["nom"] or "—")
    natija = []
    for g in guruh.values():
        g["fakt"] = _kun_fakt(db, g["turi_id"], sana, sana,
                              g["odam_id"]).get(sana, 0)
        g["qolgan"] = g["reja"] - g["fakt"]
        g["oy_qolgan"] = kategoriya_kunlari(db, oy, g["turi_id"],
                                            g["odam_id"])["qolgan"]
        natija.append(g)
    return natija


def kun_holati(reja: int, fakt: int) -> str:
    """Kun/kategoriya qatoridagi «Holat»: reja − fakt."""
    if not fakt:
        return "sarflanmagan" if reja else "—"
    if not reja:
        return "rejasiz"
    farq = reja - fakt
    return ("rejadagidek" if not farq else
            f"{money.fmt(farq)} qoldi" if farq > 0 else
            f"{money.fmt(-farq)} oshdi")


def royxat_holati(reja: int, tolandi: int) -> str:
    """Ro'yxat qatoridagi «Holat» — toifa oynasi va «Bugun» da bir xil."""
    if not tolandi:
        return "olinmagan"
    farq = tolandi - reja
    return ("rejadagidek" if not farq else
            f"+{money.fmt(farq)} ortiq" if farq > 0 else
            f"{money.fmt(-farq)} tejaldi")


def reja_yozuv_toliq(db, qator_id: int) -> dict | None:
    """Bitta reja ro'yxati — mahsulotlari va bog'langan rasxodi bilan."""
    y = db.q1("SELECT q.*, t.nom turi_nom, o.nom odam_nom FROM reja_qator q"
              " LEFT JOIN turi t ON t.id=q.turi_id"
              " LEFT JOIN odam o ON o.id=q.odam_id"
              " WHERE q.id=? AND q.ochirilgan=0", qator_id)
    return _toliq(db, y) if y else None


def reja_bajar(db, qator_id: int, tolanganlar: dict, kim_toladi: int,
               sana: str | None = None) -> int | None:
    """Rejadagi yozuvga «aslida qancha to'landi» ni yozadi — bitta undo.

    `tolanganlar`: {reja_mahsulot.id: summa}; mahsulotsiz yozuvda
    {None: summa}. 0/bo'sh — hali olinmagan. To'langanlardan HAQIQIY
    rasxod yoziladi (yoki bog'langani yangilanadi) — fakt rasxoddan
    hisoblanadi, shuning uchun bu yerda alohida fakt saqlanmaydi.
    Umumiy reja — umumiy rasxod (uydagilarga teng); shaxsiy reja —
    o'sha odamniki (boshqa to'lasa «uning uchun»). Hammasi 0 bo'lsa
    bog'langan rasxod o'chiriladi. Qaytaradi: rasxod id yoki None.
    """
    from core import entries
    from core import rasxod_kirit as rk
    y = db.q1("SELECT * FROM reja_qator WHERE id=? AND ochirilgan=0",
              qator_id)
    if not y:
        raise ValueError("Reja yozuvi topilmadi.")
    qatorlar = db.q("SELECT * FROM reja_mahsulot WHERE qator_id=?"
                    " AND ochirilgan=0 ORDER BY tartib, id", qator_id)
    sana = _kun(sana or y["sana"] or date.today()).isoformat()

    def _son(v) -> int:
        v = int(v or 0)
        if v < 0:
            raise ValueError("To'langan summa manfiy bo'lmaydi.")
        return v

    if qatorlar:
        yangi = {q["id"]: _son(tolanganlar.get(q["id"])) for q in qatorlar}
        mahsulotlar = [{"item_id": q["item_id"], "nom": q["nom"],
                        "miqdor": q["miqdor"], "summa": yangi[q["id"]]}
                       for q in qatorlar if yangi[q["id"]]]
        jami = sum(yangi.values())
    else:
        yangi, mahsulotlar = {}, []
        jami = _son(tolanganlar.get(None))

    umumiy = bool(y["umumiymi"])
    if umumiy:
        tur, kim_uchun = rk.UMUMIY, None
    elif kim_toladi == y["odam_id"]:
        tur, kim_uchun = rk.SHAXSIY, None
    else:
        tur, kim_uchun = rk.UCHUN, y["odam_id"]
    bor = (db.q1("SELECT id FROM rasxod WHERE id=? AND ochirilgan=0",
                 y["rasxod_id"]) if y["rasxod_id"] else None)

    with db.amal(f"Reja bajarildi: {y['nom']} {money.fmt(jami)}"):
        for q in qatorlar:
            v = yangi[q["id"]] or None
            if q["tolangan"] != v:
                db.apply("reja_mahsulot", "UPDATE", {"tolangan": v}, q["id"])
        if not qatorlar and y["tolangan"] != (jami or None):
            db.apply("reja_qator", "UPDATE", {"tolangan": jami or None},
                     qator_id)
        rid = bor["id"] if bor else None
        if jami <= 0:
            if bor:
                entries.rasxod_ochir(db, bor["id"])
                db.apply("reja_qator", "UPDATE", {"rasxod_id": None}, qator_id)
            return None
        q = rk.Qoralama(sana=sana, kim_toladi=kim_toladi,
                        turi_id=y["turi_id"], nom=y["nom"], summa=jami,
                        tur=tur, kim_uchun=kim_uchun,
                        mahsulotlar=mahsulotlar,
                        item_id=y["item_id"] if not qatorlar else None)
        if bor:
            rk.tahrirla(db, bor["id"], q)
        else:
            rid = rk.saqla(db, q)
            db.apply("reja_qator", "UPDATE", {"rasxod_id": rid}, qator_id)
        return rid


def reja_yozuv_mahsulotlari(db, qator_id: int) -> list[dict]:
    from core import rasxod_kirit as rk
    return rk.qatorlarni_ol(db, "reja_mahsulot", "qator_id", qator_id)


def _holat(reja: int, fakt: int) -> str:
    """oshdi | yaqin | yaxshi | rejasiz — `theme` rangi shundan."""
    if reja <= 0:
        return "rejasiz"
    if fakt > reja:
        return "oshdi"
    if money.foiz(fakt, reja) >= YAQIN_FOIZ:
        return "yaqin"
    return "yaxshi"


def reja_va_fakt(db, oy: str, odam_id: int | None = None) -> dict:
    """Bitta oy: reja, fakt, qolgan va kategoriyalar — bitta DOIRADA.

    `odam_id` None — UMUMIY: umumiy reja (summa, limit, umumiy yozuvlar)
    va umumiy rasxodlarning butun summasi. `<id>` — o'sha odamning
    SHAXSIY rejasi va shaxsiy rasxodi (unga olingani bilan).

    Qaytadi::

        {oy, boshi, oxiri, reja_bor, umumiy_qoyilgan,
         reja, fakt, qolgan, foiz, holat,      # umumiy
         turi_reja_jami,                       # kategoriya rejalari yig'indisi
         qatorlar: [{turi_id, nom, belgi, rasm, reja, fakt, qolgan,
                     foiz, holat}],
         diqqat: qator | None}                 # eng xavflisi

    `reja` — umumiy qo'yilgan bo'lsa o'sha, aks holda kategoriya
    rejalari yig'indisi. `qolgan` manfiy bo'lsa — shuncha oshib ketgan.
    """
    boshi, oxiri = oy + "-01", oy_oxiri(oy + "-01")
    rejalar = turi_reja(db, oy, odam_id)
    fakt = {t["turi_id"]: t["summa"]
            for t in ledger.turi_boyicha(db, boshi, oxiri, odam_id,
                                         "shaxsiy" if odam_id else "umumiy")}

    qatorlar = []
    for t in db.q("SELECT id, nom, belgi, rasm, faol FROM turi"
                  " WHERE ota_id IS NULL ORDER BY tartib, id"):
        r, f = rejalar.get(t["id"], 0), fakt.get(t["id"], 0)
        if not r and not f:
            continue
        qatorlar.append({"turi_id": t["id"], "nom": t["nom"],
                         "belgi": t["belgi"], "rasm": t["rasm"],
                         "reja": r, "fakt": f})
    # Rejasi borlari yuqorida (tartib bo'yicha), rejasizlari — fakt
    # bo'yicha kattadan; «Kategoriyasiz» eng oxirida.
    qatorlar.sort(key=lambda q: (not q["reja"], -q["fakt"] if not q["reja"] else 0))
    if fakt.get(None):
        qatorlar.append({"turi_id": None, "nom": "Kategoriyasiz", "belgi": "",
                         "rasm": None, "reja": 0, "fakt": fakt[None]})
    for q in qatorlar:
        q["qolgan"] = q["reja"] - q["fakt"]
        q["foiz"] = money.foiz(q["fakt"], q["reja"])
        q["holat"] = _holat(q["reja"], q["fakt"])

    umumiy = oylik_reja(db, oy) if odam_id is None else None
    turi_jami = sum(rejalar.values())
    reja = umumiy if umumiy is not None else turi_jami
    jami_fakt = sum(fakt.values())

    # Diqqat: avval eng ko'p oshib ketgani, yo'q bo'lsa eng yuqori foizli
    # «yaqin» — pastdagi bitta kartada shu turadi.
    oshgan = [q for q in qatorlar if q["holat"] == "oshdi"]
    yaqin = [q for q in qatorlar if q["holat"] == "yaqin"]
    diqqat = (min(oshgan, key=lambda q: q["qolgan"]) if oshgan else
              max(yaqin, key=lambda q: q["foiz"]) if yaqin else None)

    return {"oy": oy, "boshi": boshi, "oxiri": oxiri, "odam_id": odam_id,
            "reja_bor": bool(umumiy) or bool(rejalar),
            "umumiy_qoyilgan": umumiy is not None,
            "reja": reja, "fakt": jami_fakt, "qolgan": reja - jami_fakt,
            "foiz": money.foiz(jami_fakt, reja),
            "holat": _holat(reja, jami_fakt),
            "turi_reja_jami": turi_jami,
            "qatorlar": qatorlar, "diqqat": diqqat}


# Rejaga band pul — reja tuzilgach, oyning hali sarflanmagan rejasi
# (`reja − fakt`, manfiy bo'lsa 0) faol odamlarga TENG bo'linib, har
# birining qo'lidagi puldan «band» deb ayiriladi (2026-10-01,
# foydalanuvchi so'ragan). Faqat KO'RSATISH uchun: `v_balans`, audit va
# qarz hisobiga tegmaydi — pul hali hech kimga o'tmagan.

def band_pul(db, kun: date | str | None = None) -> dict[int, int]:
    """{odam_id: band summa} — joriy oy rejasidan. Reja yo'q bo'lsa {}.

    Umumiy rejaning sarflanmagani hammaga TENG bo'linadi; shaxsiy
    rejaning sarflanmagani esa butunlay o'sha odamdan band.
    """
    oy = oy_kaliti(kun)
    idlar = [r["id"] for r in db.q(
        "SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id")]
    natija: dict[int, int] = {}
    rf = reja_va_fakt(db, oy)
    qolgan = max(0, rf["qolgan"]) if rf["reja_bor"] else 0
    if qolgan and idlar:
        for u in money.bol_teng(qolgan, idlar):
            natija[u.odam_id] = u.summa
    for oid in idlar:
        rs = reja_va_fakt(db, oy, oid)
        if rs["reja_bor"] and rs["qolgan"] > 0:
            natija[oid] = natija.get(oid, 0) + rs["qolgan"]
    return {k: v for k, v in natija.items() if v}


def asosiy_odam(db) -> int | None:
    """Yon paneldagi «qo'ldagi pul» kimniki: `sozlama.asosiy_odam`, yo'q
    bo'lsa birinchi faol odam (tartib bo'yicha — uyda bu Fayzulloxon)."""
    r = db.q1("SELECT qiymat FROM sozlama WHERE kalit='asosiy_odam'")
    if r and r["qiymat"] and db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1",
                                   int(r["qiymat"])):
        return int(r["qiymat"])
    return db.skalyar("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id",
                      birlamchi=None)


def band_hisob(db, kun: date | str | None = None) -> dict[int, dict]:
    """Rejaga band pul HAQIQATDA kimning qo'lidan ayiriladi (2026-10-01,
    foydalanuvchi qoidasi): hech kimdan qo'lidagi puldan (naqd, manfiy
    bo'lsa 0) ortiq ayirilmaydi — balans rejadan minusga TUSHMAYDI.

    Yetmagan qismi — QARZ: asosiy odam (`asosiy_odam`) qoplaydi, o'zining
    puli yetganicha. {odam_id: {band, ayirildi, qarz, qoplaydi}}:
      band      — `band_pul` dagi ulushi;
      ayirildi  — qo'lidagi puldan shu oy ayirilgani (≤ naqd);
      qarz      — hisobida yo'q, qarz bo'lib yozilgani (band − o'zidan
                  ayirilgani; asosiy odamda — hech kim qoplamagani);
      qoplaydi  — asosiy odam boshqalar o'rniga qoplagani.
    Faqat KO'RSATISH: `v_balans` ga tegmaydi.
    """
    band = band_pul(db, kun)
    if not band:
        return {}
    asosiy = asosiy_odam(db)
    naqd = {r["id"]: max(0, int(r["naqd"])) for r in db.q(
        "SELECT id, naqd FROM v_balans")}
    natija = {}
    boshqalar_qarzi = 0
    for oid, b in band.items():
        if oid == asosiy:
            continue
        ayir = min(b, naqd.get(oid, 0))
        natija[oid] = {"band": b, "ayirildi": ayir, "qarz": b - ayir,
                       "qoplaydi": 0}
        boshqalar_qarzi += b - ayir
    if asosiy is not None:
        kerak = band.get(asosiy, 0) + boshqalar_qarzi
        ayir = min(kerak, naqd.get(asosiy, 0))
        qoplaydi = min(boshqalar_qarzi, max(0, ayir - band.get(asosiy, 0)))
        natija[asosiy] = {"band": band.get(asosiy, 0), "ayirildi": ayir,
                          "qarz": kerak - ayir, "qoplaydi": qoplaydi}
    return natija


def odam_qarzlari(db, odam_id: int) -> dict:
    """`ledger.odam_qarzlari` + rejaga band puldan hisobida yo'q qismi
    (`band_hisob` dagi `qarz`) — «Qarzim» shundan o'qiydi.
    `reja_jami` — shu qarz; `jami` ga qo'shilgan."""
    q = ledger.odam_qarzlari(db, odam_id)
    r = band_hisob(db).get(odam_id, {}).get("qarz", 0)
    q["reja_jami"] = r
    q["reja_kimga"] = (None if odam_id == asosiy_odam(db) else
                       db.skalyar("SELECT nom FROM odam WHERE id=?",
                                  asosiy_odam(db), birlamchi=""))
    q["jami"] += r
    return q


def band_tafsilot(db, odam_id: int, kun: date | str | None = None) -> dict:
    """«Rejaga band» kartasi bosilganda: shu odamning band puli NIMADAN.

    umumiy  — umumiy rejaning sarflanmagan kategoriyalari (reja, fakt,
              qolgan), `umumiy_qolgan` — jami, `umumiy_ulush` — undan
              shu odamga tushgan TENG ulush (`band_pul` bilan bir xil);
    shaxsiy — shu odamning shaxsiy rejasi kategoriyalari, `shaxsiy_qolgan`;
    hisob   — `band_hisob` dagi qatori (ayirildi, qarz, qoplaydi).
    """
    oy = oy_kaliti(kun)
    idlar = [r["id"] for r in db.q(
        "SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id")]
    rf = reja_va_fakt(db, oy)
    um_qolgan = max(0, rf["qolgan"]) if rf["reja_bor"] else 0
    ulush = 0
    if um_qolgan and odam_id in idlar:
        ulush = next(u.summa for u in money.bol_teng(um_qolgan, idlar)
                     if u.odam_id == odam_id)
    rs = reja_va_fakt(db, oy, odam_id)
    sh_qolgan = max(0, rs["qolgan"]) if rs["reja_bor"] else 0
    tanla = lambda r: [q for q in r["qatorlar"] if q["reja"]]
    return {"oy": oy, "odamlar_soni": len(idlar),
            "umumiy": tanla(rf), "umumiy_reja": rf["reja"],
            "umumiy_fakt": rf["fakt"], "umumiy_qolgan": um_qolgan,
            "umumiy_ulush": ulush,
            "shaxsiy": tanla(rs), "shaxsiy_reja": rs["reja"],
            "shaxsiy_fakt": rs["fakt"], "shaxsiy_qolgan": sh_qolgan,
            "jami": ulush + sh_qolgan,
            "hisob": band_hisob(db, kun).get(
                odam_id, {"band": 0, "ayirildi": 0, "qarz": 0,
                          "qoplaydi": 0})}


def band_ayirma(db, kun: date | str | None = None) -> dict[int, int]:
    """{odam_id: qo'lidagi puldan ayiriladigani} — ko'rsatish uchun
    (`ledger.darajalar`, «Shaxsiy», «Hisobot»). Hech qachon naqddan ko'p
    emas — rejadan minus balans chiqmaydi."""
    return {k: v["ayirildi"] for k, v in band_hisob(db, kun).items()
            if v["ayirildi"]}


def qoldagi_pul(db, kun: date | str | None = None) -> dict:
    """Yon panel: FAQAT asosiy odamning qo'lidagi pul, rejaga band
    ayirilgan (2026-10-01, foydalanuvchi so'ragan).

    O'z band ulushi + boshqalarning band ulushidan ularning qo'lidagi
    pul (naqd, manfiy bo'lsa 0) yetmagan qismi — ya'ni boshqada pul
    bo'lmasa, uning rejaga ulushi asosiy odamning pulidan ayiriladi.
    Faqat ko'rsatish: `v_balans` ga tegmaydi.
    """
    oid = asosiy_odam(db)
    if oid is None:
        return {"odam_id": None, "nom": "", "naqd": 0, "band": 0, "qoldi": 0}
    # `band_hisob` bilan BITTA qoida: o'z ulushi + boshqalarning hisobida
    # yo'q qismi, lekin qo'lidagi puldan ortiq emas.
    ayir = band_hisob(db, kun).get(oid, {}).get("ayirildi", 0)
    naqd = db.skalyar("SELECT naqd FROM v_balans WHERE id=?", oid)
    return {"odam_id": oid,
            "nom": db.skalyar("SELECT nom FROM odam WHERE id=?", oid,
                              birlamchi=""),
            "naqd": naqd, "band": ayir, "qoldi": naqd - ayir}


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

    Ichki kategoriyalardagi mahsulotlar ham chiqadi: «Bozorlik» tanlansa
    «Mevalar», «Sabzavotlar» dagilari ham (`turi_nom` — qaysi birida).
    """
    if turi_id is None:
        return db.q("SELECT * FROM item WHERE faol=1 AND ochirilgan=0"
                    " AND turi_id IS NULL ORDER BY nom")
    return db.q(
        "WITH RECURSIVE a(id) AS (SELECT ?"
        " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)"
        " SELECT i.*, t.nom turi_nom, (i.turi_id<>?) ichkida FROM item i"
        " JOIN turi t ON t.id=i.turi_id"
        " WHERE i.faol=1 AND i.ochirilgan=0 AND i.turi_id IN (SELECT id FROM a)"
        " ORDER BY ichkida, t.tartib, i.nom COLLATE NOCASE", turi_id, turi_id)


def item_narx_yangila(db, item_id: int, narx: int) -> None:
    """Xarid paytida narx boshqacha chiqsa — katalogdagi narxni yangilaydi."""
    with db.amal("Mahsulot narxi yangilandi"):
        db.apply("item", "UPDATE", {"narx": int(narx)}, item_id)


def item_topib_qosh(db, nom: str, narx: int, turi_id: int | None) -> int:
    """Shu nomdagi mahsulot bo'lsa qaytaradi, bo'lmasa yaratadi."""
    nom = nom.strip()
    bor = db.q1("SELECT id FROM item WHERE faol=1 AND ochirilgan=0 AND nom=? AND"
                " (turi_id IS ? OR turi_id=?)", nom, turi_id, turi_id)
    if bor:
        return bor["id"]
    return item_qosh(db, nom, narx, turi_id)
