"""Balanslar va kitob tekshiruvi.

Har odamning uchta soni bor va ular bir-biriga bog'langan:

    naqd    — qo'lidagi haqiqiy pul
    sof     — + boshqalar unga qarzdor,  − u boshqalarga qarzdor
    adolat  — hamma hisoblashib bo'lganda qoladigan pul

Va bitta ayniyat ularni bog'lab turadi:

    adolat = naqd + sof

`audit()` shu ayniyatni va pul saqlanish qonunini har safar tekshiradi.
Agar bittasi buzilsa — dasturda xato bor, va uni birinchi kunidayoq
ko'rasiz, uch oydan keyin emas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import money


def balanslar(db, hammasi: bool = False) -> list:
    """Faol odamlar. `hammasi=True` — nofaollari ham (audit uchun)."""
    shart = "" if hammasi else " WHERE faol=1"
    return db.q(f"SELECT * FROM v_balans{shart} ORDER BY tartib, id")


def balans(db, odam_id: int):
    return db.q1("SELECT * FROM v_balans WHERE id=?", odam_id)


def jami_kirim(db) -> int:
    return db.skalyar("SELECT SUM(summa) FROM kirim WHERE ochirilgan=0")


def jami_rasxod(db) -> int:
    return db.skalyar("SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0")


def jami_umumiy(db) -> int:
    return db.skalyar(
        "SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0 AND umumiymi=1")


# ────────────────────────────────────────────────────── kim kimga qarzdor

@dataclass
class Juft:
    qarzdor_id: int
    kreditor_id: int
    qarzdor_nom: str
    kreditor_nom: str
    summa: int


def juft_qarzlar(db) -> list[Juft]:
    """Netlangan juftlik qarzlari: A→B va B→A birlashtirilgan."""
    nomlar = {r["id"]: r["nom"] for r in db.q("SELECT id, nom FROM odam")}
    xom: dict[tuple[int, int], int] = {}
    for r in db.q("SELECT qarzdor, kreditor, summa FROM v_juft_qarz"):
        xom[(r["qarzdor"], r["kreditor"])] = \
            xom.get((r["qarzdor"], r["kreditor"]), 0) + int(r["summa"] or 0)

    net: dict[tuple[int, int], int] = {}
    for (a, b), s in xom.items():
        if a == b:
            continue
        kalit = (a, b) if a < b else (b, a)
        net[kalit] = net.get(kalit, 0) + (s if kalit == (a, b) else -s)

    natija = []
    for (a, b), s in net.items():
        if s == 0:
            continue
        qarzdor, kreditor, summa = (a, b, s) if s > 0 else (b, a, -s)
        natija.append(Juft(qarzdor, kreditor,
                           nomlar.get(qarzdor, "?"), nomlar.get(kreditor, "?"),
                           summa))
    natija.sort(key=lambda j: -j.summa)
    return natija


def juft_tarkibi(db, qarzdor_id: int, kreditor_id: int) -> list[dict]:
    """Ikki odam orasidagi qarz NIMADAN yig'ilgani — bittalab.

    `juft_qarzlar()` faqat yakuniy sonni beradi; bu esa o'sha sonning
    ichini ochadi. Belgilar `qarzdor → kreditor` yo'nalishiga nisbatan:

        +  qarzdorning qarzini oshiradi
        −  kamaytiradi (teskari yo'nalish yoki to'lov)

    Shuning uchun qatorlar yig'indisi aynan juftlik summasiga teng
    bo'ladi — `tekshir.py` shuni tekshiradi.
    """
    q, k = int(qarzdor_id), int(kreditor_id)
    natija: list[dict] = []

    # ── umumiy rasxoddagi ulushlar
    for yon, (odam, tolovchi) in ((1, (q, k)), (-1, (k, q))):
        for r in db.q(
                "SELECT u.summa, u.tolandi, u.tolangan_sana, r.sana, r.nom,"
                "       t.nom turi_nom"
                " FROM ulush u JOIN rasxod r ON r.id=u.rasxod_id"
                " LEFT JOIN turi t ON t.id=r.turi_id"
                " WHERE r.ochirilgan=0 AND r.umumiymi=1"
                "   AND u.odam_id=? AND r.kim_toladi=?"
                " ORDER BY r.sana, r.id", odam, tolovchi):
            natija.append({
                "sana": r["sana"], "turi": "Umumiy rasxod",
                "nom": r["nom"] or "—", "izoh": r["turi_nom"] or "",
                "summa": yon * int(r["summa"]),
                "tolandi": bool(r["tolandi"]),
                "tolangan_sana": r["tolangan_sana"]})

    # ── to'g'ridan-to'g'ri qarzlar
    for yon, (kimga, kim_berdi) in ((1, (q, k)), (-1, (k, q))):
        for r in db.q(
                "SELECT sana, summa, sabab FROM qarz"
                " WHERE ochirilgan=0 AND kimga=? AND kim_berdi=?"
                " ORDER BY sana, id", kimga, kim_berdi):
            natija.append({
                "sana": r["sana"], "turi": "Qarz",
                "nom": r["sabab"] or "Qarz olindi", "izoh": "",
                "summa": yon * int(r["summa"]),
                "tolandi": False, "tolangan_sana": None})

    # ── hisob-kitob (to'lov) — qarzni KAMAYTIRADI
    for yon, (kim_toladi, kimga) in ((-1, (q, k)), (1, (k, q))):
        for r in db.q(
                "SELECT sana, summa, izoh FROM hisob_kitob"
                " WHERE ochirilgan=0 AND kim_toladi=? AND kimga=?"
                " ORDER BY sana, id", kim_toladi, kimga):
            natija.append({
                "sana": r["sana"], "turi": "To'lov",
                "nom": r["izoh"] or "To'lov", "izoh": "",
                "summa": yon * int(r["summa"]),
                "tolandi": True, "tolangan_sana": r["sana"]})

    natija.sort(key=lambda x: (str(x["sana"]), x["turi"]))
    return natija


# ────────────────────────────────────────────────────────────── audit

@dataclass
class Audit:
    toza: bool = True
    muammolar: list[str] = field(default_factory=list)
    sof_yigindi: int = 0
    naqd_yigindi: int = 0
    kutilgan_naqd: int = 0
    identifikatsiya_ok: bool = True
    ulush_ok: bool = True

    def __getitem__(self, k):
        return getattr(self, k)


def audit(db) -> Audit:
    """Kitob teng turibdimi? Har ochilishda va har yozuvdan keyin chaqiriladi."""
    a = Audit()
    # Nofaol odamning qarzi ham hisobga kiradi — aks holda uni nofaol
    # qilib qo'yish bilan qarzni "yo'qotib" yuborish mumkin bo'lardi.
    qatorlar = balanslar(db, hammasi=True)

    # 1. Qarzlar yig'indisi nolga teng bo'lishi SHART.
    #    Kimdir qarzdor bo'lsa, kimdir kreditor — boshqacha bo'lishi mumkin emas.
    a.sof_yigindi = sum(r["sof"] for r in qatorlar)
    if a.sof_yigindi != 0:
        a.toza = False
        a.muammolar.append(
            f"Qarzlar yig'indisi nolga teng emas: {money.fmt(a.sof_yigindi, True)} so'm")

    # 2. Pul yo'qdan paydo bo'lmaydi va yo'qolmaydi.
    a.naqd_yigindi = sum(r["naqd"] for r in qatorlar)
    a.kutilgan_naqd = jami_kirim(db) - jami_rasxod(db)
    if a.naqd_yigindi != a.kutilgan_naqd:
        a.toza = False
        a.muammolar.append(
            f"Naqd pul mos kelmadi: {money.fmt(a.naqd_yigindi)} ≠ "
            f"kirim − rasxod = {money.fmt(a.kutilgan_naqd)}")

    # 3. adolat = naqd + sof  (har odam uchun)
    for r in qatorlar:
        if r["adolat"] != r["naqd"] + r["sof"]:
            a.identifikatsiya_ok = a.toza = False
            a.muammolar.append(
                f"{r['nom']}: adolat({money.fmt(r['adolat'])}) ≠ "
                f"naqd({money.fmt(r['naqd'])}) + sof({money.fmt(r['sof'])})")

    # 4. Har umumiy rasxodning ulushlari aynan rasxodga teng.
    yomon = db.q(
        "SELECT r.id, r.nom, r.sana, r.summa, COALESCE(SUM(u.summa),0) us"
        " FROM rasxod r LEFT JOIN ulush u ON u.rasxod_id=r.id"
        " WHERE r.ochirilgan=0 AND r.umumiymi=1"
        " GROUP BY r.id HAVING us <> r.summa")
    if yomon:
        a.ulush_ok = a.toza = False
        for r in yomon[:5]:
            a.muammolar.append(
                f"Rasxod #{r['id']} ({r['sana']} {r['nom'] or '—'}): "
                f"ulushlar {money.fmt(r['us'])} ≠ summa {money.fmt(r['summa'])}")
        if len(yomon) > 5:
            a.muammolar.append(f"...va yana {len(yomon) - 5} ta")

    # 5. Shaxsiy rasxodda ulush bo'lmasligi kerak.
    n = db.skalyar(
        "SELECT COUNT(*) FROM ulush u JOIN rasxod r ON r.id=u.rasxod_id"
        " WHERE r.umumiymi=0 AND r.ochirilgan=0")
    if n:
        a.toza = False
        a.muammolar.append(f"{n} ta shaxsiy rasxodda ortiqcha ulush qatori bor")

    return a


# ──────────────────────────────────────────────────── odam tafsiloti

def kunlik_qator(db, odam_id: int, boshi: str, oxiri: str) -> list[dict]:
    """Excel'dagi shaxsiy varaq: kun, shaxsiy, umumiy ulush, qoldiq."""
    kirimlar = {r["sana"]: r["s"] for r in db.q(
        "SELECT sana, SUM(summa) s FROM kirim"
        " WHERE ochirilgan=0 AND odam_id=? AND sana BETWEEN ? AND ?"
        " GROUP BY sana", odam_id, boshi, oxiri)}
    shaxsiy = {r["sana"]: r["s"] for r in db.q(
        "SELECT sana, SUM(summa) s FROM rasxod"
        " WHERE ochirilgan=0 AND umumiymi=0 AND kim_toladi=? AND sana BETWEEN ? AND ?"
        " GROUP BY sana", odam_id, boshi, oxiri)}
    ulushlar = {r["sana"]: r["s"] for r in db.q(
        "SELECT r.sana sana, SUM(u.summa) s FROM ulush u"
        " JOIN rasxod r ON r.id=u.rasxod_id"
        " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND u.odam_id=?"
        " AND r.sana BETWEEN ? AND ? GROUP BY r.sana", odam_id, boshi, oxiri)}

    sanalar = sorted(set(kirimlar) | set(shaxsiy) | set(ulushlar))
    qoldiq = 0
    natija = []
    for s in sanalar:
        k = kirimlar.get(s, 0)
        sh = shaxsiy.get(s, 0)
        u = ulushlar.get(s, 0)
        qoldiq += k - sh - u
        natija.append({"sana": s, "kirim": k, "shaxsiy": sh,
                       "ulush": u, "qoldiq": qoldiq})
    return natija


def turi_boyicha(db, boshi: str, oxiri: str) -> list[dict]:
    return [dict(r) for r in db.q(
        "SELECT COALESCE(t.nom,'Kategoriyasiz') nom, COALESCE(t.belgi,'') belgi,"
        "       SUM(r.summa) summa, COUNT(*) soni"
        " FROM rasxod r LEFT JOIN turi t ON t.id=r.turi_id"
        " WHERE r.ochirilgan=0 AND r.sana BETWEEN ? AND ?"
        " GROUP BY r.turi_id ORDER BY summa DESC", boshi, oxiri)]


# ──────────────────────────────────────────────────────── pul darajasi
#
# "Yetarlimi yoki yo'qmi" degan savolga bitta joydan javob beriladi,
# shunda jadval, karta va chiziq bir xil gapiradi.

CHEGARA_KAM = 200_000        # shundan past — kam qoldi
CHEGARA_JUDA_KAM = 100_000   # shundan past — juda kam

HOLAT_NOM = {
    "qarzda":   "qarzda",
    "juda_kam": "juda kam",
    "kam":      "kam qoldi",
    "yaxshi":   "yetarli",
}


def chegaralar(db) -> tuple[int, int]:
    """(kam, juda_kam) — Sozlamalardan o'zgartirilishi mumkin."""
    try:
        kam = int(db.sozlama("chegara_kam", str(CHEGARA_KAM)))
        juda = int(db.sozlama("chegara_juda_kam", str(CHEGARA_JUDA_KAM)))
    except ValueError:
        kam, juda = CHEGARA_KAM, CHEGARA_JUDA_KAM
    return kam, juda


def chegara_qoy(db, kam: int, juda_kam: int) -> None:
    db.sozlama_qoy("chegara_kam", str(int(kam)))
    db.sozlama_qoy("chegara_juda_kam", str(int(juda_kam)))


def holat(naqd: int, sof: int, kam: int = CHEGARA_KAM,
          juda_kam: int = CHEGARA_JUDA_KAM) -> str:
    """qarzda | juda_kam | kam | yaxshi

    Qarz eng muhim holat: puli bo'lsa ham qarzdor odam "yetarli" emas.
    Qo'lidagi pul manfiy bo'lsa ham — bu ham qarz.
    """
    if sof < 0 or naqd < 0:
        return "qarzda"
    if naqd < juda_kam:
        return "juda_kam"
    if naqd < kam:
        return "kam"
    return "yaxshi"


def darajalar(db) -> list[dict]:
    """Har odam uchun: holat + chiziqning to'ldirilish ulushi.

    Ulush eng ko'p puli bor odamga nisbatan hisoblanadi — shunda
    chiziqlar bir-biri bilan solishtiriladi. Hech kimda pul bo'lmasa
    chiziqlar bo'sh turadi.
    """
    kam, juda_kam = chegaralar(db)
    qatorlar = balanslar(db)
    eng_kop = max([r["naqd"] for r in qatorlar] + [0]) or 1
    natija = []
    for r in qatorlar:
        h = holat(r["naqd"], r["sof"], kam, juda_kam)
        natija.append({
            "id": r["id"], "nom": r["nom"],
            "naqd": r["naqd"], "sof": r["sof"], "adolat": r["adolat"],
            "holat": h, "holat_nom": HOLAT_NOM[h],
            "ulush": max(0.0, min(1.0, r["naqd"] / eng_kop)),
        })
    return natija


def pul_darajasi(naqd: int, kam: int = CHEGARA_KAM,
                 juda_kam: int = CHEGARA_JUDA_KAM) -> str:
    """Faqat QO'LDAGI pulga qaraydi — qarzdan qat'i nazar.

    `holat()` dan farqi shu: u odamning umumiy ahvolini aytadi va qarz
    hammasidan ustun turadi. Bu esa "cho'ntagida qancha bor" degan
    alohida savol. Qarzdor odam ham cho'ntagi bo'shashini bilishi kerak.
    """
    if naqd < 0:
        return "manfiy"
    if naqd < juda_kam:
        return "juda_kam"
    if naqd < kam:
        return "kam"
    return "yaxshi"


def ogohlantirish(db) -> list[str]:
    """Bugun sahifasidagi qisqa ogohlantirishlar — faqat naqd pul haqida."""
    kam, juda_kam = chegaralar(db)
    xabarlar = []
    for r in balanslar(db):
        daraja = pul_darajasi(r["naqd"], kam, juda_kam)
        if daraja == "manfiy":
            xabarlar.append(f"{r['nom']}: {money.fmt(r['naqd'])} — minusda")
        elif daraja == "juda_kam":
            xabarlar.append(f"{r['nom']}: {money.fmt(r['naqd'])} — juda kam")
        elif daraja == "kam":
            xabarlar.append(f"{r['nom']}: {money.fmt(r['naqd'])} — kam qoldi")
    return xabarlar
