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


def jami_tashqi_qoldiq(db) -> int:
    """Tashqaridan olingan va hali qaytarilmagan qarz — hamma odam bo'yicha.

    `v_balans` dan olinadi, ya'ni `naqd` bilan AYNAN bir xil qoida:
    o'chirilgan qarzning to'lovi ham hisobga kirmaydi.
    """
    return db.skalyar("SELECT SUM(tashqi_qoldiq) FROM v_balans")


def tashqi_qarzlar(db, faqat_ochiq: bool = False) -> list[dict]:
    """Tashqi qarzlar ro'yxati: olingan, qaytarilgan va qoldig'i bilan."""
    qatorlar = [dict(r) for r in db.q(
        "SELECT q.*, o.nom odam_nom,"
        "  (SELECT GROUP_CONCAT(x.nom || ':' || u.summa, ', ') FROM tashqi_ulush u"
        "   JOIN odam x ON x.id=u.odam_id WHERE u.qarz_id=q.id AND u.tolov_id IS NULL"
        "   AND u.ochirilgan=0) ulushlar,"
        "  COALESCE((SELECT SUM(t.summa) FROM tashqi_tolov t"
        "            WHERE t.tashqi_qarz_id=q.id AND t.ochirilgan=0),0) qaytgan"
        " FROM tashqi_qarz q JOIN odam o ON o.id=q.odam_id"
        " WHERE q.ochirilgan=0 ORDER BY q.sana DESC, q.id DESC")]
    for r in qatorlar:
        r["qoldiq"] = r["summa"] - r["qaytgan"]
    if faqat_ochiq:
        qatorlar = [r for r in qatorlar if r["qoldiq"] > 0]
    return qatorlar


def tashqi_kimga_qaytarish(db) -> list[dict]:
    """Kimga qancha qaytarish kerak — ochiq qarzlar qarz beruvchi bo'yicha.

    [{kimdan, qoldiq, soni}], eng kattasi birinchi. `tashqi_qarzlar()` dan
    yig'iladi — qoldiq qoidasi ikki joyda yozilmasin.
    """
    yig: dict[str, dict] = {}
    for r in tashqi_qarzlar(db, faqat_ochiq=True):
        x = yig.setdefault(r["kimdan"], {"kimdan": r["kimdan"], "qoldiq": 0,
                                         "soni": 0})
        x["qoldiq"] += r["qoldiq"]
        x["soni"] += 1
    return sorted(yig.values(), key=lambda x: -x["qoldiq"])


def tashqi_kimdanlar(db) -> list[str]:
    """Oldin yozilgan qarz beruvchilar — tanlagichda taklif qilish uchun."""
    return [r["kimdan"] for r in db.q(
        "SELECT kimdan, MAX(sana) s FROM tashqi_qarz WHERE ochirilgan=0"
        " GROUP BY kimdan ORDER BY s DESC")]


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


def odam_qarzlari(db, odam_id: int) -> dict:
    """Bitta odamning qarzlari — «Shaxsiy» dagi «Qarzim» tugmasi uchun.

    ichki  — uy ichida u qarzdor bo'lgan juftliklar (`juft_qarzlar`);
    menga  — unga qarzdorlar (faqat ko'rsatish);
    tashqi — hali qaytarilmagan tashqi qarzlar: shaxsiysi (u olgan) —
             butun qoldig'i; UMUMIYSI — faqat UNING ulushi (olingandagi
             ulushi − qaytarilgandagi ulushlari), `qoldiq` shu ulush,
             `jami_qoldiq` — qarzning butun qoldig'i.
    `jami` = ichki + tashqi (u to'lashi kerak bo'lgan hamma pul).
    """
    juftlar = juft_qarzlar(db)
    ichki = [j for j in juftlar if j.qarzdor_id == odam_id]
    menga = [j for j in juftlar if j.kreditor_id == odam_id]
    tashqi = []
    for t in tashqi_qarzlar(db, faqat_ochiq=True):
        t["jami_qoldiq"] = t["qoldiq"]
        if t["umumiy"]:
            t["qoldiq"] = db.skalyar(
                "SELECT SUM(CASE WHEN u.tolov_id IS NULL THEN u.summa"
                "            ELSE -u.summa END) FROM tashqi_ulush u"
                " LEFT JOIN tashqi_tolov p ON p.id=u.tolov_id"
                " WHERE u.qarz_id=? AND u.odam_id=? AND u.ochirilgan=0"
                "   AND (u.tolov_id IS NULL OR p.ochirilgan=0)",
                t["id"], odam_id)
            if t["qoldiq"] > 0:
                tashqi.append(t)
        elif t["odam_id"] == odam_id:
            tashqi.append(t)
    ichki_jami = sum(j.summa for j in ichki)
    tashqi_jami = sum(t["qoldiq"] for t in tashqi)
    return {"ichki": ichki, "menga": menga, "tashqi": tashqi,
            "ichki_jami": ichki_jami, "tashqi_jami": tashqi_jami,
            "menga_jami": sum(j.summa for j in menga),
            "jami": ichki_jami + tashqi_jami}


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
                "SELECT u.id, u.summa, u.tolandi, u.tolangan_sana, r.sana,"
                "       r.nom, t.nom turi_nom"
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
                "tolangan_sana": r["tolangan_sana"], "ulush_id": r["id"]})

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
                "tolandi": False, "tolangan_sana": None, "ulush_id": None})

    # ── hisob-kitob (to'lov) — qarzni KAMAYTIRADI
    for yon, (kim_toladi, kimga) in ((-1, (q, k)), (1, (k, q))):
        for r in db.q(
                "SELECT sana, summa, izoh, ulush_id FROM hisob_kitob"
                " WHERE ochirilgan=0 AND kim_toladi=? AND kimga=?"
                " ORDER BY sana, id", kim_toladi, kimga):
            natija.append({
                "sana": r["sana"], "turi": "To'lov",
                "nom": r["izoh"] or "To'lov", "izoh": "",
                "summa": yon * int(r["summa"]),
                "tolandi": True, "tolangan_sana": r["sana"],
                "ulush_id": r["ulush_id"]})

    # Umumiy tashqi qarz juftlik qarziga KIRMAYDI (2026-10-01) — pul ham,
    # qaytarish ham har kimning o'z ulushida (`v_juft_qarz` bilan bir xil).

    natija.sort(key=lambda x: (str(x["sana"]), x["turi"]))
    return natija


def juft_tolanmagan(db, qarzdor_id: int, kreditor_id: int) -> list[dict]:
    """Juftlik qarzining HALI TO'LANMAGAN qismi — bittalab.

    `juft_tarkibi()` hamma narsani beradi: to'langan rasxodni ham, uning
    to'lovini ham. «Kim kimga qarzdor» qatoriga bosilganda esa faqat
    qolgan qarz kerak:

      1. «To'landi» deb belgilangan ulush va unga bog'langan to'lov
         (`hisob_kitob.ulush_id`) birga chiqariladi — ular bir-birini
         aynan yopadi.
      2. Qolgan kamaytiruvchilar (erkin to'lov, teskari yo'nalishdagi
         rasxod yoki qarz) ENG ESKI qarzdan boshlab yopadi. Erkin to'lov
         qaysi rasxod uchun ekanini aytmaydi — va amalda deyarli hamma
         to'lov shunaqa, shuning uchun faqat 1-qadam yetmaydi.
      3. To'liq yopilgan qarz chiqmaydi; qisman yopilganning QOLDIG'I
         chiqadi (`asl` — asl summasi).

    Qatorlar yig'indisi juftlik summasiga TENG bo'lib qoladi. Yo'nalish
    teskari bo'lsa (kreditor aslida qarzdor) — bo'sh ro'yxat.
    """
    tarkib = juft_tarkibi(db, qarzdor_id, kreditor_id)

    bogliq: dict[int, int] = {}
    for x in tarkib:
        if x["ulush_id"] is not None:
            bogliq[x["ulush_id"]] = bogliq.get(x["ulush_id"], 0) + x["summa"]
    hovuz = [x for x in tarkib
             if x["ulush_id"] is None or bogliq[x["ulush_id"]] != 0]

    yopadi = -sum(x["summa"] for x in hovuz if x["summa"] < 0)
    natija = []
    for x in hovuz:                       # sana bo'yicha — eskisi oldin
        if x["summa"] <= 0:
            continue
        yopildi = min(yopadi, x["summa"])
        yopadi -= yopildi
        if x["summa"] > yopildi:
            natija.append(dict(x, summa=x["summa"] - yopildi, asl=x["summa"]))
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
    #    Tashqaridan olingan qarz uyga pul olib kiradi, qaytarilgani olib
    #    chiqadi — ikkalasi ham haqiqiy pul harakati.
    a.kutilgan_naqd = (jami_kirim(db) - jami_rasxod(db)
                       + jami_tashqi_qoldiq(db))
    if a.naqd_yigindi != a.kutilgan_naqd:
        a.toza = False
        a.muammolar.append(
            f"Naqd pul mos kelmadi: {money.fmt(a.naqd_yigindi)} ≠ "
            f"kirim − rasxod + tashqi qarz = {money.fmt(a.kutilgan_naqd)}")

    # 7. Umumiy tashqi qarz: ulushlar yig'indisi = qarz (va har to'lov).
    for r in db.q(
            "SELECT q.id, q.kimdan, q.summa,"
            "  COALESCE((SELECT SUM(u.summa) FROM tashqi_ulush u WHERE u.qarz_id=q.id"
            "            AND u.tolov_id IS NULL AND u.ochirilgan=0),0) us"
            " FROM tashqi_qarz q WHERE q.ochirilgan=0 AND q.umumiy=1"
            " AND us <> q.summa"):
        a.toza = False
        a.muammolar.append(f"Umumiy tashqi qarz #{r['id']} ({r['kimdan']}): "
                           f"ulushlar {money.fmt(r['us'])} ≠ {money.fmt(r['summa'])}")
    for r in db.q(
            "SELECT t.id, t.summa,"
            "  COALESCE((SELECT SUM(u.summa) FROM tashqi_ulush u WHERE u.tolov_id=t.id"
            "            AND u.ochirilgan=0),0) us"
            " FROM tashqi_tolov t JOIN tashqi_qarz q ON q.id=t.tashqi_qarz_id"
            " WHERE t.ochirilgan=0 AND q.ochirilgan=0 AND q.umumiy=1"
            " AND us <> t.summa"):
        a.toza = False
        a.muammolar.append(f"Umumiy tashqi qarz to'lovi #{r['id']}: ulushlar "
                           f"{money.fmt(r['us'])} ≠ {money.fmt(r['summa'])}")

    # 6. Tashqi qarz ortig'i bilan qaytarilmaydi.
    for r in db.q(
            "SELECT q.id, q.kimdan, q.summa, SUM(t.summa) qaytgan"
            " FROM tashqi_qarz q JOIN tashqi_tolov t"
            "   ON t.tashqi_qarz_id=q.id AND t.ochirilgan=0"
            " WHERE q.ochirilgan=0 GROUP BY q.id HAVING qaytgan > q.summa"):
        a.toza = False
        a.muammolar.append(
            f"Tashqi qarz #{r['id']} ({r['kimdan']}): qaytarilgan "
            f"{money.fmt(r['qaytgan'])} > qarz {money.fmt(r['summa'])}")

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


# Har kategoriya → uning eng yuqori otasi. Ichki kategoriyaga
# («Mevalar») yozilgan rasxod doira, hisobot va jadvalda otasiga
# («Bozorlik») qo'shiladi: aks holda bitta bozorlik ikki bo'lakka
# bo'linib, «qaysi bo'lak katta?» degan savolga yolg'on javob berardi.
_ILDIZ = ("WITH RECURSIVE ild(id, ildiz) AS ("
          " SELECT id, id FROM turi WHERE ota_id IS NULL"
          " UNION ALL SELECT t.id, ild.ildiz FROM turi t"
          " JOIN ild ON t.ota_id=ild.id) ")


# Bitta odamning rasxodi — `v_balans` bilan AYNAN bir xil qoida:
#   shaxsiy = o'zi to'lagan shaxsiy rasxod (umumiymi=0)
#             + boshqa odam UNING UCHUN olgani (kim_uchun, `uchun_ulush`);
#   umumiy  = haqiqiy umumiy rasxoddagi ulushi (`umumiy_ulush`).
# Umumiy rasxodning butun summasi EMAS, faqat o'z ulushi: aks holda uch
# odamning analitikasi qo'shilganda uyning rasxodi uch barobar chiqardi.
ODAM_QISMLARI = ("hammasi", "shaxsiy", "umumiy")

# Har bo'lak parametrlari: (odam_id, boshi, oxiri).
_ODAM_SHAXSIY = (
    "SELECT r.id, r.turi_id, r.summa, 'shaxsiy' qism FROM rasxod r"
    " WHERE r.ochirilgan=0 AND r.umumiymi=0 AND r.kim_toladi=?"
    " AND r.sana BETWEEN ? AND ?",
    "SELECT r.id, r.turi_id, u.summa, 'shaxsiy' qism FROM ulush u"
    " JOIN rasxod r ON r.id=u.rasxod_id"
    " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NOT NULL"
    " AND u.odam_id=? AND u.summa<>0 AND r.sana BETWEEN ? AND ?")
_ODAM_UMUMIY = (
    "SELECT r.id, r.turi_id, u.summa, 'umumiy' qism FROM ulush u"
    " JOIN rasxod r ON r.id=u.rasxod_id"
    " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NULL"
    " AND u.odam_id=? AND u.summa<>0 AND r.sana BETWEEN ? AND ?",)


def _odam_manba(qism: str, odam_id: int, boshi: str,
                oxiri: str) -> tuple[str, tuple]:
    if qism not in ODAM_QISMLARI:
        raise ValueError(f"noma'lum qism: {qism!r}")
    bolaklar = {"shaxsiy": _ODAM_SHAXSIY, "umumiy": _ODAM_UMUMIY,
                "hammasi": _ODAM_SHAXSIY + _ODAM_UMUMIY}[qism]
    return (" UNION ALL ".join(bolaklar),
            (odam_id, boshi, oxiri) * len(bolaklar))


def _manba(boshi: str, oxiri: str, odam_id: int | None,
           qism: str) -> tuple[str, tuple]:
    """(id, turi_id, summa, qism) qatorlari — `turi_boyicha` va
    `kategoriya_rasxodlari` BITTA manbadan o'qiydi, aks holda ro'yxat
    yig'indisi doiradagi songa teng kelmay qolardi."""
    if odam_id is None:
        # Butun uy. `qism` bilan — faqat umumiy (butun summasi) yoki faqat
        # shaxsiy («boshqa uchun» ham shaxsiy — `v_balans` qoidasi).
        shart = {"hammasi": "",
                 "umumiy": " AND umumiymi=1 AND kim_uchun IS NULL",
                 "shaxsiy": " AND (umumiymi=0 OR kim_uchun IS NOT NULL)"}
        if qism not in shart:
            raise ValueError(f"noma'lum qism: {qism!r}")
        return ("SELECT id, turi_id, summa,"
                " CASE WHEN umumiymi=0 OR kim_uchun IS NOT NULL"
                " THEN 'shaxsiy' ELSE 'umumiy' END qism"
                " FROM rasxod WHERE ochirilgan=0 AND sana BETWEEN ? AND ?"
                + shart[qism], (boshi, oxiri))
    return _odam_manba(qism, odam_id, boshi, oxiri)


def turi_boyicha(db, boshi: str, oxiri: str, odam_id: int | None = None,
                 qism: str = "hammasi") -> list[dict]:
    """Kategoriya bo'yicha rasxod. `odam_id` berilsa — faqat o'sha
    odamning rasxodi (`qism`: 'hammasi' | 'shaxsiy' | 'umumiy')."""
    manba, args = _manba(boshi, oxiri, odam_id, qism)
    return [dict(r) for r in db.q(
        _ILDIZ +
        ", m AS (" + manba + ") "
        "SELECT ild.ildiz turi_id, COALESCE(t.nom,'Kategoriyasiz') nom,"
        "       COALESCE(t.belgi,'') belgi, t.rasm rasm,"
        "       SUM(m.summa) summa, COUNT(*) soni"
        " FROM m LEFT JOIN ild ON ild.id=m.turi_id"
        " LEFT JOIN turi t ON t.id=ild.ildiz"
        " GROUP BY ild.ildiz ORDER BY summa DESC", *args)]


def kategoriya_rasxodlari(db, turi_idlar: list, boshi: str, oxiri: str,
                          odam_id: int | None = None,
                          qism: str = "hammasi") -> list[dict]:
    """Doiradagi bo'lak / jadval qatorining ICHI — har bir rasxod.

    `turi_idlar` — asosiy kategoriyalar (ichkilari ham kiradi); `None`
    elementi — «Kategoriyasiz». `summa` — shu filtrdagi hissa (odam
    tanlangan bo'lsa uning ulushi), `jami` — rasxodning butun summasi.
    Qatorlar yig'indisi `turi_boyicha` dagi songa AYNAN teng.
    """
    manba, args = _manba(boshi, oxiri, odam_id, qism)
    idlar = [i for i in turi_idlar if i is not None]
    shart = []
    if idlar:
        shart.append(f"ild.ildiz IN ({','.join('?' * len(idlar))})")
    if None in turi_idlar:
        shart.append("ild.ildiz IS NULL")
    if not shart:
        return []
    return [dict(r) for r in db.q(
        _ILDIZ +
        ", m AS (" + manba + ") "
        "SELECT r.id, r.sana, r.nom, r.izoh, m.qism, m.summa,"
        "       r.summa jami, r.umumiymi, r.kim_uchun,"
        "       COALESCE(t.nom, '') kategoriya,"
        "       COALESCE(o.nom, '?') kim_toladi,"
        "       ou.nom kim_uchun_nom"
        " FROM m JOIN rasxod r ON r.id=m.id"
        " LEFT JOIN ild ON ild.id=m.turi_id"
        " LEFT JOIN turi t ON t.id=r.turi_id"
        " LEFT JOIN odam o ON o.id=r.kim_toladi"
        " LEFT JOIN odam ou ON ou.id=r.kim_uchun"
        " WHERE " + " OR ".join(shart) +
        " ORDER BY r.sana DESC, r.id DESC", *args, *idlar)]


def odam_rasxod_xulosa(db, odam_id: int, boshi: str, oxiri: str) -> dict:
    """{'shaxsiy', 'umumiy', 'jami'} — bitta odamning oraliqdagi rasxodi,
    `turi_boyicha(..., odam_id, qism)` bilan bir xil qoida."""
    x = {q: sum(t["summa"] for t in turi_boyicha(db, boshi, oxiri, odam_id, q))
         for q in ("shaxsiy", "umumiy")}
    x["jami"] = x["shaxsiy"] + x["umumiy"]
    return x


# ─────────────────────────────────────────────────── doira diagramma
#
# «Analitika» varag'idagi doira: rasxod kategoriyalar bo'yicha.
#
# Doira bitta savolga javob beradi — «qaysi bo'lak katta?». Birlamchi
# holatda eng katta DOIRA_QADAM (6) ta kategoriya o'z bo'lagi bilan,
# qolgani bitta «Qolganlari» ga yig'iladi. Foydalanuvchi «Yana 6 ta»
# (yoki «Qolganlari» ning o'zini) bossa `korsat` 6 taga oshadi —
# kategoriya qolmaguncha (2026-09-30, foydalanuvchi so'ragan: «Qolganlari»
# 32% ni yutib, ichida nima borligi ko'rinmas edi).
#
# Foiz `money.bol_tortli()` bilan, 0,1% birligida (1000 = 100%).
# Oddiy yaxlitlash uchta teng bo'lakni 33,3 + 33,3 + 33,3 = 99,9% deb
# ko'rsatardi — bu yerda yig'indi har doim aynan 100%.

DOIRA_QADAM = 6


def doira_bolaklari(db, boshi: str, oxiri: str,
                    korsat: int = DOIRA_QADAM, odam_id: int | None = None,
                    qism: str = "hammasi") -> list[dict]:
    """Doira bo'laklari: kategoriyalar katta → kichik, keyin rangsizlar.

    Har bo'lak: `nom`, `belgi`, `summa`, `soni`, `ulush` (0,1% birligida,
    hammasi birga aynan 1000), `tur` va `ichida` (yig'ilgan nomlar).

    `korsat` — nechta kategoriya o'z bo'lagi bilan chiqadi; ortig'i
    bo'lsa ular bitta «Qolganlari» ga yig'iladi (`idlar` — ichidagilar).

    `tur`: 'turi' — kategoriya; 'qolgan' — kichik kategoriyalar
    yig'indisi; 'kategoriyasiz' — turi tanlanmagan rasxod. Oxirgi
    ikkalasi kategoriya EMAS: har doim oxirida turadi va rangsiz
    chiziladi, katta bo'lsa ham.
    """
    turlar = sorted(turi_boyicha(db, boshi, oxiri, odam_id, qism),
                    key=lambda t: (-t["summa"], t["nom"]))
    nomli = [dict(t, tur="turi", ichida=[], idlar=[t["turi_id"]])
             for t in turlar if t["turi_id"] is not None]
    nomsiz = [dict(t, tur="kategoriyasiz", ichida=[], idlar=[None])
              for t in turlar if t["turi_id"] is None]

    korsat = max(1, korsat)
    if len(nomli) > korsat:
        kichik = nomli[korsat:]
        nomli = nomli[:korsat] + [{
            "turi_id": None, "nom": "Qolganlari", "belgi": "", "rasm": None,
            "summa": sum(t["summa"] for t in kichik),
            "soni": sum(t["soni"] for t in kichik),
            "tur": "qolgan",
            "ichida": [f"{t['belgi']} {t['nom']}".strip() for t in kichik],
            "idlar": [t["turi_id"] for t in kichik],
        }]

    bolaklar = nomli + nomsiz
    if bolaklar:
        # Kalit — bo'lakning tartib raqami (`bol_tortli` uni odam_id
        # deb ataydi, lekin unga har qanday butun son bo'laveradi).
        for u in money.bol_tortli(
                1000, {i: b["summa"] for i, b in enumerate(bolaklar)}):
            bolaklar[u.odam_id]["ulush"] = u.summa
    return bolaklar


def kategoriya_jadvali(db, boshi: str, oxiri: str, odam_id: int | None = None,
                       qism: str = "hammasi") -> list[dict]:
    """HAMMA kategoriya — oraliqda rasxodi bo'lmaganlari ham (0 bilan).

    Doira faqat eng kattalarini ko'rsatadi (`DOIRA_QADAM`); bu esa
    to'liq ro'yxat: yangi qo'shilgan, hali ishlatilmagan kategoriya ham
    shu yerda ko'rinsin. Nofaol kategoriya faqat oraliqda rasxodi
    bo'lsa chiqadi, «Kategoriyasiz» ham shunday — oxirida.

    `ulush` — 0,1% birligida, yig'indisi aynan 1000 (rasxod bo'lsa).
    """
    fakt = {t["turi_id"]: t for t in turi_boyicha(db, boshi, oxiri,
                                                  odam_id, qism)}
    natija = []
    # Faqat asosiy kategoriyalar — ichkilari otasiga qo'shilgan.
    for r in db.q("SELECT id, nom, belgi, rasm, faol FROM turi"
                  " WHERE ota_id IS NULL ORDER BY tartib, id"):
        f = fakt.get(r["id"])
        if not r["faol"] and not f:
            continue
        natija.append({"turi_id": r["id"], "nom": r["nom"],
                       "belgi": r["belgi"], "rasm": r["rasm"],
                       "summa": f["summa"] if f else 0,
                       "soni": f["soni"] if f else 0, "ulush": 0})
    natija.sort(key=lambda x: -x["summa"])      # barqaror: tartib saqlanadi
    if None in fakt:
        f = fakt[None]
        natija.append({"turi_id": None, "nom": "Kategoriyasiz", "belgi": "",
                       "rasm": None, "summa": f["summa"], "soni": f["soni"],
                       "ulush": 0})
    bor = {i: x["summa"] for i, x in enumerate(natija) if x["summa"] > 0}
    if bor:
        for u in money.bol_tortli(1000, bor):
            natija[u.odam_id]["ulush"] = u.summa
    return natija


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


def darajalar(db, band: dict[int, int] | None = None) -> list[dict]:
    """Har odam uchun: holat + chiziqning to'ldirilish ulushi.

    Ulush eng ko'p puli bor odamga nisbatan hisoblanadi — shunda
    chiziqlar bir-biri bilan solishtiriladi. Hech kimda pul bo'lmasa
    chiziqlar bo'sh turadi.

    `band` — {odam_id: rejaga band summa} (`plan.band_pul`): berilsa
    `naqd` va `adolat` shuncha kam ko'rsatiladi.
    """
    kam, juda_kam = chegaralar(db)
    band = band or {}
    qatorlar = [dict(r, naqd=r["naqd"] - band.get(r["id"], 0),
                     adolat=r["adolat"] - band.get(r["id"], 0))
                for r in balanslar(db)]
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
