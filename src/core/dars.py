"""EduPage dars jadvali → bitta odamning shaxsiy kalendari.

Sof mantiq: Qt ham, pul ham yo'q — `ledger.audit()` bu yerni ko'rmaydi.
Tarmoqqa faqat `_sorov()` chiqadi, qolgan hammasi tayyor JSON ustida
ishlaydi. Shuning uchun butun sinxronni tarmoqsiz test qilib bo'ladi
(`tekshir.py` shunday qiladi).

Nega darsga alohida jadval emas: dars ham o'sha kalendarga tushadigan,
o'sha eslatma keladigan, o'sha «Albatta!» tugmasi bosiladigan ish.
Ikkinchi jadval qilinsa kalendar, eslatma va hisobotning hammasi ikki
manbadan o'qishga majbur bo'lardi.

Dars qatori `vazifa.manba` bilan belgilanadi (`dars:2026-09-07:5` —
sana va para raqami). Kalit shu ikkitadan quriladi, EduPage'ning ichki
`id` sidan emas: maktab jadvalni qayta chizsa id lar o'zgaradi va har
hafta butun kalendar o'chib-qayta yozilardi.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta

from core import vazifa as vz

HOST = "ttpu.edupage.org"
GSH = "00000000"          # ochiq jadval uchun imzo talab qilinmaydi
KUTISH = 20               # soniya

K_YOQ = "dars_yoq"
K_HOST = "dars_host"
K_SINF = "dars_sinf"
K_ODAM = "dars_odam"
K_TT = "dars_tt"                  # oxirgi ko'chirilgan jadval raqami
K_TEKSHIRILDI = "dars_tekshirildi"

# Tarmoqqa har daqiqada emas, soatiga bir marta chiqamiz. `xabarchi.py`
# har daqiqada ishlaydi — jadval esa haftada bir marta o'zgaradi.
ORALIQ_DAQIQA = 60

# Dars uy ishidan ikki narsada farq qiladi, shuning uchun ikkita chegara:
#   · unga OLDINDAN tayyorlanish kerak (qayerga borish, nima olish) —
#     `OGOH_DAQIQA` boshlanishidan qancha oldin xabar berilishini aytadi;
#   · «bo'ldingizmi?» degan savol dars TUGAGAN zahoti emas, biroz
#     keyin so'raladi — odam auditoriyadan chiqib ulgurishi kerak.
OGOH_DAQIQA = 5 * 60
KECHIKISH_DAQIQA = 10


def darsmi(v) -> bool:
    """Bu vazifa dars jadvalidan kelganmi.

    `manba` USTUNIGA qaraydi, nomga emas: foydalanuvchi fan nomini
    o'zgartirsa ham dars dars bo'lib qolaveradi (`navbat`/`haftalik`
    bilan bir xil qoida).
    """
    kalitlar = v.keys() if hasattr(v, "keys") else v
    m = v["manba"] if "manba" in kalitlar else None
    return bool(m and str(m).startswith("dars:"))


class DarsXato(ValueError):
    """`core/` ning qolgani ham `ValueError` tashlaydi — UI bitta joyda
    tutadi, ya'ni dars xatosi uchun alohida `except` yozilmaydi."""


# ──────────────────────────────────────────────────────────── sozlama

def sozlamalar(db) -> dict:
    return {
        "yoq": db.sozlama(K_YOQ, "") == "1",
        "host": db.sozlama(K_HOST, HOST) or HOST,
        "sinf": db.sozlama(K_SINF, ""),
        "odam_id": int(db.sozlama(K_ODAM, "0") or 0),
        "tt": db.sozlama(K_TT, ""),
        "tekshirildi": db.sozlama(K_TEKSHIRILDI, ""),
    }


def sozlama_qoy(db, *, yoq: bool | None = None, host: str | None = None,
                sinf: str | None = None, odam_id: int | None = None) -> None:
    if yoq is not None:
        db.sozlama_qoy(K_YOQ, "1" if yoq else "")
    if host is not None:
        db.sozlama_qoy(K_HOST, host.strip().strip("/") or HOST)
    if sinf is not None:
        db.sozlama_qoy(K_SINF, sinf.strip())
    if odam_id is not None:
        db.sozlama_qoy(K_ODAM, str(int(odam_id)))


def sozlangami(db) -> bool:
    s = sozlamalar(db)
    return bool(s["yoq"] and s["sinf"] and s["odam_id"])


# ────────────────────────────────────────────────────────────── tarmoq

def _sorov(url: str, yuk: dict) -> dict:
    ma = json.dumps(yuk).encode("utf-8")
    s = urllib.request.Request(url, data=ma, headers={
        "Content-Type": "application/json",
        "User-Agent": "FarvonUy/1.0",
    })
    with urllib.request.urlopen(s, timeout=KUTISH) as j:
        return json.loads(j.read().decode("utf-8"))


def joriy_jadval(host: str = HOST) -> dict | None:
    """Hozir e'lon qilingan jadval: {tt_num, text, datefrom}.

    EduPage bir vaqtda BITTA haftani ko'rsatadi — shuning uchun
    «keyingi haftani ham olib qo'yamiz» degan yo'l yo'q.
    """
    url = f"https://{host}/timetable/server/ttviewer.js?__func=getTTViewerData"
    for yil in (date.today().year, date.today().year - 1):
        j = _sorov(url, {"__args": [None, str(yil)], "__gsh": GSH})
        royxat = (j.get("r") or {}).get("regular", {}).get("timetables") or []
        if royxat:
            return royxat[-1]
    return None


def jadval_malumot(host: str, tt_num: str) -> dict:
    url = f"https://{host}/timetable/server/regulartt.js?__func=regularttGetData"
    return _sorov(url, {"__args": [None, str(tt_num)], "__gsh": GSH})


# ─────────────────────────────────────────────────────────────── o'qish

def _jadvallar(malumot: dict) -> dict:
    """EduPage javobidagi jadvallarni {id: {qator_id: qator}} qilib beradi."""
    ichki = (malumot.get("r") or {}).get("dbiAccessorRes") or {}
    return {t["id"]: {r["id"]: r for r in t.get("data_rows", [])}
            for t in ichki.get("tables", [])}


def _nomlash(s: str) -> str:
    """«ABDUMANNOPOVA MA'MURA» → «Abdumannopova Ma'mura».

    `str.title()` emas: u apostrofdan keyin ham katta harf qo'yadi va
    ism «Ma'Mura» bo'lib chiqadi.
    """
    return " ".join(w[:1].upper() + w[1:].lower() for w in str(s).split())


def _daqiqa(vaqt: str) -> int:
    s, d = str(vaqt).split(":")[:2]
    return int(s) * 60 + int(d)


def hafta_boshi(datefrom: str) -> date:
    """Jadval boshlanadigan haftaning dushanbasi.

    `datefrom` yakshanbaga tushishi mumkin (TTPU'da aynan shunday) —
    u holda jadval ERTASI kunidan boshlanadi, o'sha kundan emas.
    """
    d = date.fromisoformat(str(datefrom)[:10])
    return d + timedelta(days=(7 - d.weekday()) % 7)


def darslar(malumot: dict, sinf: str, boshi: date) -> list[dict]:
    """Bitta guruhning haftalik darslari — sana va soati bilan.

    `boshi` — dushanba. Kun raqami EduPage'ning `days` jadvalidan
    olinadi (0 = dushanba), nomdan emas.
    """
    T = _jadvallar(malumot)
    sinflar = T.get("classes", {})
    kerakli = {k for k, v in sinflar.items()
               if str(v.get("name", "")).strip().lower() == sinf.strip().lower()}
    if not kerakli:
        raise DarsXato(f"«{sinf}» jadvalda topilmadi")

    kunlar = sorted(T.get("days", {}), key=lambda i: int(i))
    paralar = T.get("periods", {})
    darslar_j = T.get("lessons", {})
    fanlar = T.get("subjects", {})
    ustozlar = T.get("teachers", {})
    xonalar = T.get("classrooms", {})

    natija: list[dict] = []
    for c in T.get("cards", {}).values():
        L = darslar_j.get(c.get("lessonid"))
        if not L or not kerakli & set(L.get("classids") or []):
            continue
        p = paralar.get(str(c.get("period")))
        if not p or not p.get("starttime"):
            continue
        boshlanish = _daqiqa(p["starttime"])
        davomiylik = (_daqiqa(p["endtime"]) - boshlanish
                      if p.get("endtime") else 80)
        if davomiylik <= 0:
            continue
        nom = str(fanlar.get(L.get("subjectid"), {}).get("name", "")).strip()
        if not nom:
            continue
        ustoz = ", ".join(_nomlash(ustozlar[t]["name"])
                          for t in (L.get("teacherids") or []) if t in ustozlar)
        xona = ", ".join(str(xonalar[x]["name"])
                         for x in (c.get("classroomids") or []) if x in xonalar)
        for j, belgi in enumerate(str(c.get("days", ""))):
            if belgi != "1" or j >= len(kunlar):
                continue
            sana = boshi + timedelta(days=j)
            natija.append({
                "manba": f"dars:{sana.isoformat()}:{c['period']}",
                "nom": nom,
                "sana": sana,
                "vaqt": p["starttime"],
                "davomiylik": davomiylik,
                "izoh": " · ".join(x for x in (ustoz, xona) if x) or None,
            })
    natija.sort(key=lambda r: (r["sana"], r["vaqt"], r["nom"]))
    return natija


# ─────────────────────────────────────────────────────────── sinxronlash

def _turni_taminla(db, nom: str, davomiylik: int) -> None:
    """Fan nomi `vazifa_turi` da SHAXSIY bo'lib turishi kerak.

    Guruh/shaxsiy filtri NOM bo'yicha ishlaydi (`vz.shaxsiy_nomlari()`),
    demak tur bo'lmasa dars guruhga chiqib ketadi. O'chirilgani
    tiriltiriladi — «bu faqat sizga» degan va'da tur ro'yxatdan olib
    tashlangani uchun buzilmasligi kerak.
    """
    t = db.q1("SELECT id, shaxsiy, ochirilgan FROM vazifa_turi WHERE nom=?", nom)
    if t is None:
        tartib = db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM vazifa_turi")
        db.apply("vazifa_turi", "INSERT", {
            "nom": nom, "davomiylik": davomiylik, "tartib": tartib,
            "shaxsiy": 1})
    elif t["ochirilgan"] or not t["shaxsiy"]:
        db.apply("vazifa_turi", "UPDATE",
                 {"ochirilgan": 0, "shaxsiy": 1}, t["id"])


def sinxronla(db, qatorlar: list[dict], odam_id: int,
              dan: date, gacha: date) -> dict:
    """Oraliqdagi dars vazifalarini jadvalga TENGLASHTIRADI.

    Faqat `manba` si `dars:` bilan boshlanadigan qatorlarga tegadi —
    qo'lda yozilgan vazifa hech qachon o'chmaydi. `holat` va
    `bajarilgan` ham tegilmaydi: jadval qayta o'qilgani odamning
    «bajardim» degan javobini bekor qilmaydi.
    """
    if not qatorlar:
        raise DarsXato("Bo'sh jadval — kalendar o'chirilmadi")

    kerak = {r["manba"]: r for r in qatorlar}
    bor = {r["manba"]: r for r in db.q(
        "SELECT * FROM vazifa WHERE ochirilgan=0 AND manba LIKE 'dars:%'"
        " AND sana BETWEEN ? AND ?", dan.isoformat(), gacha.isoformat())}

    qoshildi = yangilandi = ochirildi = 0
    with db.amal("Dars jadvali yangilandi"):
        for nom in sorted({r["nom"] for r in qatorlar}):
            d = max(r["davomiylik"] for r in qatorlar if r["nom"] == nom)
            _turni_taminla(db, nom, d)

        for kalit, r in kerak.items():
            yangi = {"nom": r["nom"], "sana": r["sana"].isoformat(),
                     "vaqt": r["vaqt"], "davomiylik": r["davomiylik"],
                     "izoh": r["izoh"], "odam_id": odam_id}
            eski = bor.get(kalit)
            if eski is None:
                db.apply("vazifa", "INSERT",
                         yangi | {"holat": vz.OCHIQ, "manba": kalit})
                qoshildi += 1
                continue
            farq = {k: v for k, v in yangi.items() if eski[k] != v}
            if farq:
                db.apply("vazifa", "UPDATE", farq, eski["id"])
                yangilandi += 1

        for kalit, eski in bor.items():
            if kalit not in kerak:
                db.apply("vazifa", "DELETE", None, eski["id"])
                ochirildi += 1

    return {"qoshildi": qoshildi, "yangilandi": yangilandi,
            "ochirildi": ochirildi, "jami": len(kerak)}


# ───────────────────────────────────────────────────────────── yangilash

def kerakmi(db, hozir: datetime | None = None) -> bool:
    """Tarmoqqa chiqish vaqti keldimi (soatiga bir marta)."""
    if not sozlangami(db):
        return False
    oxirgi = db.sozlama(K_TEKSHIRILDI, "")
    if not oxirgi:
        return True
    try:
        o = datetime.strptime(oxirgi, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True
    return (hozir or datetime.now()) - o >= timedelta(minutes=ORALIQ_DAQIQA)


def yangila(db, hozir: datetime | None = None,
            majburiy: bool = False) -> dict | None:
    """Tarmoqdan o'qib, kalendarni tenglashtiradi.

    Hech narsa o'zgarmagan bo'lsa hech narsa yozilmaydi — `sinxronla()`
    farqni sanaydi, ya'ni bu funksiyani soatiga chaqirish `ozgarishlar`
    jurnalini bo'sh qadamlar bilan to'ldirmaydi.
    """
    if not sozlangami(db):
        return None
    if not majburiy and not kerakmi(db, hozir):
        return None
    s = sozlamalar(db)
    hozir = hozir or datetime.now()
    # Chegara urinishdan OLDIN yoziladi: tarmoq yiqilsa ham har
    # daqiqada qayta urinib, xabarchini ushlab turmaymiz.
    db.sozlama_qoy(K_TEKSHIRILDI, hozir.strftime("%Y-%m-%d %H:%M:%S"))

    jadval = joriy_jadval(s["host"])
    if not jadval:
        raise DarsXato("E'lon qilingan jadval yo'q")
    boshi = hafta_boshi(jadval.get("datefrom") or date.today().isoformat())
    malumot = jadval_malumot(s["host"], jadval["tt_num"])
    qatorlar = darslar(malumot, s["sinf"], boshi)
    natija = sinxronla(db, qatorlar, s["odam_id"],
                       boshi, boshi + timedelta(days=6))
    db.sozlama_qoy(K_TT, str(jadval["tt_num"]))
    natija["hafta"] = jadval.get("text") or boshi.isoformat()
    return natija
