"""Hamyon — «pulim qayerda?»: naqd va kartalar (2026-10-01).

Odamning qo'lidagi puli (`v_balans.naqd`) ikki joyda turadi: naqd va
kartalar. Kartaning qoldig'i shu yerda hisoblanadi:

    karta = kirim (karta_id=shu) − rasxod (karta_id=shu)
            + kelgan o'tkazma − ketgan o'tkazma

NAQD alohida saqlanmaydi — u QOLGANI: `naqd = v_balans.naqd − kartalar`.
Shuning uchun `naqd + kartalar = v_balans.naqd` har doim to'g'ri, belgisi
yo'q eski yozuvlar (import, bot, qarz, hisob-kitob) o'z-o'zidan naqdda
hisoblanadi va balans/audit matematikasiga hech narsa qo'shilmaydi.

Karta o'chirilsa uning qoldig'i shu qoidaga ko'ra NAQDGA qaytadi —
o'tkazma yozish shart emas, undo ham uni joyiga qaytaradi.

Kartaning egasi — `karta.odam_id`. Yozuv boshqa odamning kartasiga
bog'lansa (masalan, rasxodning to'lovchisi keyin almashtirilsa) u kartaga
hisoblanmaydi — ya'ni yana naqdga tushadi; yozishda esa `tekshir_karta`
buni umuman o'tkazmaydi.
"""
from __future__ import annotations

from datetime import date

import money

NAQD_NOM = "Naqd"


# ─────────────────────────────────────────────────────────── o'qish

def _qoldiqlar(db, odam_id: int | None = None) -> dict[int, int]:
    """{karta_id: qoldiq} — faqat o'chirilmagan kartalar."""
    shart, args = "", []
    if odam_id is not None:
        shart, args = " AND k.odam_id=?", [odam_id]
    rows = db.q(f"""
        SELECT k.id,
          COALESCE((SELECT SUM(summa) FROM kirim x
                    WHERE x.karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0)
        - COALESCE((SELECT SUM(summa) FROM rasxod x
                    WHERE x.karta_id=k.id AND x.kim_toladi=k.odam_id
                      AND x.ochirilgan=0), 0)
        + COALESCE((SELECT SUM(summa) FROM karta_otkazma x
                    WHERE x.ga_karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0)
        - COALESCE((SELECT SUM(summa) FROM karta_otkazma x
                    WHERE x.dan_karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0) AS qoldiq
        FROM karta k WHERE k.ochirilgan=0{shart}""", *args)
    return {r["id"]: int(r["qoldiq"]) for r in rows}


def kartalar(db, odam_id: int) -> list[dict]:
    """[{id, nom, qoldiq}] — tartib bo'yicha."""
    q = _qoldiqlar(db, odam_id)
    return [{"id": r["id"], "nom": r["nom"], "qoldiq": q.get(r["id"], 0)}
            for r in db.q("SELECT id, nom FROM karta WHERE odam_id=?"
                          " AND ochirilgan=0 ORDER BY tartib, id", odam_id)]


def hamyon(db, odam_id: int) -> dict:
    """{jami, naqd, karta, kartalar} — jami = v_balans.naqd."""
    jami = int(db.skalyar("SELECT naqd FROM v_balans WHERE id=?", odam_id))
    k = kartalar(db, odam_id)
    kjami = sum(x["qoldiq"] for x in k)
    return {"jami": jami, "naqd": jami - kjami, "karta": kjami,
            "kartalar": k}


def umumiy(db) -> dict:
    """Qo'ldagi HAMMA pul (2026-10-03, foydalanuvchi so'ragan: uch kishining
    puli bitta odamning qo'lida turadi). Faqat ikki narsa: naqd va kartalar.

    jami = SUM(v_balans.naqd); karta — hammaning kartalari; naqd — qolgani.
    `kartalar` — hamma kartalar (egasi tartibida). Faqat ko'rsatish.
    """
    jami = int(db.skalyar("SELECT SUM(naqd) FROM v_balans", birlamchi=0) or 0)
    q = _qoldiqlar(db)
    k = [{"id": r["id"], "nom": r["nom"], "qoldiq": q.get(r["id"], 0)}
         for r in db.q("SELECT k.id, k.nom FROM karta k JOIN odam o"
                       " ON o.id=k.odam_id WHERE k.ochirilgan=0"
                       " ORDER BY o.tartib, o.id, k.tartib, k.id")]
    kjami = sum(x["qoldiq"] for x in k)
    return {"jami": jami, "naqd": jami - kjami, "karta": kjami,
            "kartalar": k}


def tanlov(db, odam_id: int | None) -> list[tuple[int | None, str]]:
    """Rasxod/kirim oynasidagi «qayerdan» ro'yxati: naqd + kartalari."""
    natija: list[tuple[int | None, str]] = [(None, NAQD_NOM)]
    if odam_id is not None:
        natija += [(r["id"], r["nom"]) for r in db.q(
            "SELECT id, nom FROM karta WHERE odam_id=? AND ochirilgan=0"
            " ORDER BY tartib, id", odam_id)]
    return natija


def joy_nomi(db, karta_id: int | None) -> str:
    if karta_id is None:
        return NAQD_NOM
    return db.skalyar("SELECT nom FROM karta WHERE id=?", karta_id,
                      birlamchi="?")


def tekshir_karta(db, karta_id: int | None, odam_id: int | None) -> None:
    """Karta shu odamniki va o'chirilmagan bo'lishi SHART (NULL — naqd)."""
    if karta_id is None:
        return
    if not db.q1("SELECT 1 FROM karta WHERE id=? AND odam_id IS ?"
                 " AND ochirilgan=0", karta_id, odam_id):
        raise ValueError("Bu karta to'lovchiniki emas yoki o'chirilgan — "
                         "«Qayerdan» ni qayta tanlang.")


def harakatlar(db, karta_id: int) -> list[dict]:
    """Kartaning tarixi, yangisi tepada: [{sana, nima, summa(±), tur, id}]."""
    k = db.q1("SELECT odam_id FROM karta WHERE id=?", karta_id)
    if not k:
        return []
    oid = k["odam_id"]
    natija = []
    for r in db.q("SELECT id, sana, summa, sabab FROM kirim WHERE karta_id=?"
                  " AND odam_id=? AND ochirilgan=0", karta_id, oid):
        natija.append({"tur": "kirim", "id": r["id"], "sana": r["sana"],
                       "nima": f"Kirim: {r['sabab'] or '—'}",
                       "summa": r["summa"]})
    for r in db.q("SELECT id, sana, summa, nom FROM rasxod WHERE karta_id=?"
                  " AND kim_toladi=? AND ochirilgan=0", karta_id, oid):
        natija.append({"tur": "rasxod", "id": r["id"], "sana": r["sana"],
                       "nima": r["nom"] or "Rasxod", "summa": -r["summa"]})
    for r in db.q("SELECT * FROM karta_otkazma WHERE odam_id=? AND ochirilgan=0"
                  " AND (dan_karta_id=? OR ga_karta_id=?)",
                  oid, karta_id, karta_id):
        kelgan = r["ga_karta_id"] == karta_id
        boshqa = joy_nomi(db, r["dan_karta_id"] if kelgan else r["ga_karta_id"])
        nima = (f"{boshqa} → shu karta" if kelgan else f"Shu karta → {boshqa}")
        if r["izoh"]:
            nima += f" ({r['izoh']})"
        natija.append({"tur": "otkazma", "id": r["id"], "sana": r["sana"],
                       "nima": nima,
                       "summa": r["summa"] if kelgan else -r["summa"]})
    natija.sort(key=lambda x: (x["sana"], x["tur"], x["id"]), reverse=True)
    return natija


# ─────────────────────────────────────────────────────────── yozish

def _odam_bormi(db, odam_id) -> str:
    r = db.q1("SELECT nom FROM odam WHERE id=? AND faol=1", odam_id)
    if not r:
        raise ValueError("Odam tanlanmagan.")
    return r["nom"]


def karta_qosh(db, odam_id: int, nom: str, qoldiq: int = 0,
               sana: str | None = None) -> int:
    """Yangi karta. `qoldiq` — undagi HOZIRGI pul: naqddan kartaga o'tkazma
    bo'lib yoziladi (jami puli o'zgarmaydi — pul allaqachon hisobda,
    faqat qayerda turgani aniqlanadi). Bitta undo."""
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Karta nomini yozing (masalan: Humo, Uzcard).")
    qoldiq = int(qoldiq or 0)
    if qoldiq < 0:
        raise ValueError("Qoldiq manfiy bo'lmaydi.")
    kim = _odam_bormi(db, odam_id)
    if db.q1("SELECT 1 FROM karta WHERE odam_id=? AND ochirilgan=0"
             " AND nom=? COLLATE NOCASE", odam_id, nom):
        raise ValueError(f"{kim}da «{nom}» degan karta bor.")
    tartib = db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM karta"
                        " WHERE odam_id=?", odam_id)
    with db.amal(f"Karta qo'shildi: {nom} ({kim})"):
        kid = db.apply("karta", "INSERT", {
            "odam_id": odam_id, "nom": nom, "tartib": tartib})
        if qoldiq:
            db.apply("karta_otkazma", "INSERT", {
                "sana": sana or date.today().isoformat(), "odam_id": odam_id,
                "dan_karta_id": None, "ga_karta_id": kid, "summa": qoldiq,
                "izoh": "Boshlang'ich qoldiq"})
    return kid


def karta_nomla(db, karta_id: int, nom: str) -> None:
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Karta nomini yozing.")
    k = db.q1("SELECT odam_id, nom FROM karta WHERE id=?", karta_id)
    if not k:
        raise ValueError("Karta topilmadi.")
    if nom == k["nom"]:
        return
    if db.q1("SELECT 1 FROM karta WHERE odam_id=? AND ochirilgan=0 AND id<>?"
             " AND nom=? COLLATE NOCASE", k["odam_id"], karta_id, nom):
        raise ValueError(f"«{nom}» degan karta bor.")
    with db.amal(f"Karta nomi: {k['nom']} → {nom}"):
        db.apply("karta", "UPDATE", {"nom": nom}, karta_id)


def karta_ochir(db, karta_id: int) -> None:
    """O'chiriladi; qoldig'i naqdga qaytadi (yozuvlari joyida qoladi)."""
    k = db.q1("SELECT nom FROM karta WHERE id=? AND ochirilgan=0", karta_id)
    if not k:
        raise ValueError("Karta topilmadi.")
    with db.amal(f"Karta o'chirildi: {k['nom']}"):
        db.apply("karta", "DELETE", qator_id=karta_id)


def otkazma(db, sana: str, odam_id: int, dan: int | None, ga: int | None,
            summa: int, izoh: str | None = None) -> int:
    """Naqd ↔ karta yoki karta → karta (bitta odamning ichida)."""
    summa = int(summa or 0)
    if summa <= 0:
        raise ValueError("Summa kiritilmagan.")
    if dan == ga:
        raise ValueError("Qayerdan va qayerga bir xil.")
    kim = _odam_bormi(db, odam_id)
    tekshir_karta(db, dan, odam_id)
    tekshir_karta(db, ga, odam_id)
    with db.amal(f"O'tkazma ({kim}): {joy_nomi(db, dan)} → "
                 f"{joy_nomi(db, ga)} {money.fmt(summa)}"):
        return db.apply("karta_otkazma", "INSERT", {
            "sana": sana, "odam_id": odam_id, "dan_karta_id": dan,
            "ga_karta_id": ga, "summa": summa, "izoh": izoh or None})


def otkazma_ochir(db, otkazma_id: int) -> None:
    with db.amal("O'tkazma o'chirildi"):
        db.apply("karta_otkazma", "DELETE", qator_id=otkazma_id)


def qoldiq_togirla(db, karta_id: int, haqiqiy: int, sana: str) -> int | None:
    """Bank ilovasidagi haqiqiy qoldiqqa tenglaydi: farq naqd bilan
    o'tkazma bo'lib yoziladi (jami puli o'zgarmaydi). Farq yo'q — None."""
    haqiqiy = int(haqiqiy)
    if haqiqiy < 0:
        raise ValueError("Qoldiq manfiy bo'lmaydi.")
    k = db.q1("SELECT odam_id FROM karta WHERE id=? AND ochirilgan=0",
              karta_id)
    if not k:
        raise ValueError("Karta topilmadi.")
    farq = haqiqiy - _qoldiqlar(db, k["odam_id"]).get(karta_id, 0)
    if farq == 0:
        return None
    if farq > 0:
        return otkazma(db, sana, k["odam_id"], None, karta_id, farq,
                       "Qoldiq to'g'irlandi")
    return otkazma(db, sana, k["odam_id"], karta_id, None, -farq,
                   "Qoldiq to'g'irlandi")
