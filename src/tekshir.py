"""Yadro testlari — UI'siz.

Ishga tushirish:  py -3.14 src\\tekshir.py

Bu fayl dasturning eng muhim va'dalarini tekshiradi:
  * bo'lish qoldiqsiz va adolatli
  * undo/redo tiklaydi
  * yopilgan davrga yozib bo'lmaydi
  * SUM(sof) = 0  va  naqd + sof = adolat   (kitob teng)
  * hisob-kitob qarzni to'g'ri yopadi
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))

for _oqim in (sys.stdout, sys.stderr):
    try:
        _oqim.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_TMP = Path(tempfile.mkdtemp(prefix="farvonuy-test-"))
os.environ["FARVONUY_DATA"] = str(_TMP)

import config  # noqa: E402
import money   # noqa: E402
import db as dbm  # noqa: E402
from core import entries, ledger, settle  # noqa: E402

OK, XATO = [], []


def tekshir(nom: str, shart: bool, izoh: str = "") -> None:
    (OK if shart else XATO).append(nom)
    belgi = "  OK  " if shart else " XATO "
    print(f"[{belgi}] {nom}" + (f"   — {izoh}" if izoh and not shart else ""))


def teng(nom: str, kutilgan, olingan) -> None:
    tekshir(nom, kutilgan == olingan, f"kutilgan {kutilgan}, olingan {olingan}")


# ═══════════════════════════════════════════════════════════ 1. money

print("\n── money: bo'lish ───────────────────────────────────────────")

u = money.bol_teng(1_559_000, [1, 2, 3])
teng("3 ga bo'lish yig'indisi aniq", 1_559_000, sum(x.summa for x in u))
teng("ulushlar 519666/519667", {519_666, 519_667}, {x.summa for x in u})
# 1 559 000 = 3 × 519 666 + 2  →  ortiqcha 2 so'm, 2 kishiga 1 tadan
teng("ortiqcha so'm aynan qoldiqcha", 2, sum(x.yaxlitlash for x in u))

u2 = money.bol_teng(1_559_000, [1, 2, 3], qarz_tarixi={1: 10, 2: 10, 3: 0})
teng("ortiqcha eng kam olganga tushdi", 519_667,
     next(x.summa for x in u2 if x.odam_id == 3))

u3 = money.bol_teng(1_000_000, [1, 2])
teng("teng bo'linsa qoldiq yo'q", 0, sum(x.yaxlitlash for x in u3))

u4 = money.bol(100_000, money.USUL_FOIZ, {1: 50, 2: 30, 3: 20})
teng("foiz bo'lish", [50_000, 30_000, 20_000], [x.summa for x in u4])

u5 = money.bol(100_000, money.USUL_OGIRLIK, {1: 2, 2: 1, 3: 1})
teng("og'irlik bo'lish", [50_000, 25_000, 25_000], [x.summa for x in u5])

try:
    money.bol_aniq(100, {1: 40, 2: 50})
    tekshir("aniq ulush noto'g'ri bo'lsa xato beradi", False)
except ValueError:
    tekshir("aniq ulush noto'g'ri bo'lsa xato beradi", True)

teng("parse '1 559 000'", 1_559_000, money.parse("1 559 000"))
teng("parse '1559k'", 1_559_000, money.parse("1559k"))
teng("parse '1,5 mln'", 1_500_000, money.parse("1,5 mln"))

# jami 1 so'mdan 1000 tagacha — hech qachon yig'indi buzilmasin
buzuq = [j for j in range(1, 3000)
         if sum(x.summa for x in money.bol_teng(j, [1, 2, 3])) != j]
teng("1..3000 oralig'ida bo'lish hech qachon buzilmadi", [], buzuq)


# ═══════════════════════════════════════════════════════════ 2. db

print("\n── db: yozuv, undo, davr qulfi ──────────────────────────────")

d = dbm.Db()
F = d.apply("odam", "INSERT", {"nom": "Fayzulloxon", "tartib": 0})
O = d.apply("odam", "INSERT", {"nom": "Otabek", "tartib": 1})
A = d.apply("odam", "INSERT", {"nom": "Abbosxon", "tartib": 2})
tekshir("3 odam yaratildi", len(d.q("SELECT 1 FROM odam")) == 3)

kid = d.apply("kirim", "INSERT",
              {"sana": "2026-09-01", "odam_id": F, "summa": 500_000})
teng("kirim yozildi", 500_000, d.q1("SELECT summa FROM kirim WHERE id=?", kid)["summa"])

d.undo()
tekshir("undo kirimni olib tashladi",
        d.q1("SELECT 1 FROM kirim WHERE id=?", kid) is None)
d.redo()
tekshir("redo kirimni qaytardi",
        d.q1("SELECT 1 FROM kirim WHERE id=?", kid) is not None)

print("\n── undo / redo tartibi ──────────────────────────────────────")

# 2026-09-02 da ma'lumot aynan shu yerda buzilgan: redo eng ESKI emas, eng
# YANGI qaytarilgan guruhni olardi va log shoxlanib ketardi.

dU = dbm.Db(_TMP / "bU.db", zaxirasiz=True)
FU = dU.apply("odam", "INSERT", {"nom": "F", "tartib": 0})
entries.kirim_qosh(dU, "2026-09-01", FU, 100_000, "bir")
entries.kirim_qosh(dU, "2026-09-02", FU, 200_000, "ikki")
entries.kirim_qosh(dU, "2026-09-03", FU, 300_000, "uch")


def _kirimlar() -> set:
    """Bazadagi kirimlar — `id` bo'yicha emas, sababi bo'yicha.

    INSERT ni undo qilish qatorni ROSTDAN o'chiradi va SQLite o'sha `id` ni
    keyingi yozuvga qayta beradi. Shuning uchun `id` bo'yicha tekshirish
    yolg'on gapiradi: yangi yozuv eski `id` ni egallab, "eskisi qaytibdi"
    degan taassurot qoldiradi. Aynan shu sabab redo yo'lini yopish shart —
    o'sha `id` ni band qilgan yangi yozuvni redo bosib ketishi mumkin edi.
    """
    return {r["sabab"] for r in dU.q(
        "SELECT sabab FROM kirim WHERE ochirilgan=0")}


dU.undo()
dU.undo()
teng("ikki marta undo — oxirgi ikkitasi ketdi", {"bir"}, _kirimlar())

dU.redo()
teng("redo undo'ni teskari yechadi — avval «ikki» qaytadi",
     {"bir", "ikki"}, _kirimlar())
dU.redo()
teng("ikkinchi redo «uch» ni qaytardi", {"bir", "ikki", "uch"}, _kirimlar())
teng("hammasi qaytgach redo tugadi", None, dU.keyingi_guruh())

# Log shoxlanmasligi: amaldagi guruhlar HAR DOIM qaytarilganlardan oldin
# turadi. Buzilgan bazada 66–110 qaytarilgan, 111–118 esa amalda edi.
dU.undo()
dU.undo()
dU.redo()
_eng_katta_amalda = dU.skalyar(
    "SELECT MAX(id) FROM ozgarishlar WHERE qaytarilgan=0", birlamchi=-1)
_eng_kichik_qaytarilgan = dU.skalyar(
    "SELECT MIN(id) FROM ozgarishlar WHERE qaytarilgan=1", birlamchi=10 ** 9)
tekshir("log shoxlanmadi: amaldagilar qaytarilganlardan oldin turadi",
        _eng_katta_amalda < _eng_kichik_qaytarilgan,
        f"amalda {_eng_katta_amalda}, qaytarilgan {_eng_kichik_qaytarilgan}")

# Oxirgi undo nimani olgan bo'lsa, birinchi redo aynan o'shani qaytaradi.
dU.undo()
teng("redo oxirgi undo'ni nishonga oladi",
     f"Kirim: F +{money.fmt(200_000)}", dU.keyingi_guruh()[1])

# Undo'dan keyin YANGI yozuv — redo yo'li yopiladi, tarix shoxlanmaydi.
entries.kirim_qosh(dU, "2026-09-04", FU, 400_000, "to'rt")
teng("yangi yozuvdan keyin redo yo'li yopildi", None, dU.keyingi_guruh())
teng("bekor qilingan yozuvlar tiklanmadi", {"bir", "to'rt"}, _kirimlar())
teng("bekor qilingan guruhlar logda qoldi — o'chirilmadi", 2,
     dU.skalyar("SELECT COUNT(DISTINCT guruh_id) FROM ozgarishlar"
                " WHERE bekor=1"))

dU.undo()
teng("bekordan keyin ham undo ishlaydi", {"bir"}, _kirimlar())
tekshir("undo/redo tsiklidan keyin kitob teng", ledger.audit(dU)["toza"])


d.con.execute("INSERT INTO davr(oy,holat) VALUES('2026-09','yopilgan')")
try:
    d.apply("kirim", "INSERT", {"sana": "2026-09-05", "odam_id": F, "summa": 1})
    tekshir("yopilgan davrga yozib bo'lmaydi", False)
except dbm.DavrYopilgan:
    tekshir("yopilgan davrga yozib bo'lmaydi", True)
d.con.execute("DELETE FROM davr WHERE oy='2026-09'")


# ═══════════════════════════════════════════════ 3. Excel stsenariysi

print("\n── ledger: Excel'dagi aynan shu holat ───────────────────────")

d2 = dbm.Db(_TMP / "b2.db", zaxirasiz=True)
F = d2.apply("odam", "INSERT", {"nom": "Fayzulloxon", "tartib": 0})
O = d2.apply("odam", "INSERT", {"nom": "Otabek", "tartib": 1})
A = d2.apply("odam", "INSERT", {"nom": "Abbosxon", "tartib": 2})

entries.kirim_qosh(d2, "2026-08-22", A, 700_000, "From Akmal aka")
entries.kirim_qosh(d2, "2026-08-22", F, 300_000)
entries.kirim_qosh(d2, "2026-08-26", F, 1_780_000, "Oylik")
entries.kirim_qosh(d2, "2026-08-28", A, 1_200_000)
entries.kirim_qosh(d2, "2026-08-31", F, 40_000, "From Akmal aka")

# Fayzulloxon to'lagan umumiy rasxodlar (Excel'dagi 11 qator)
umumiy = [90_000, 330_000, 113_000, 70_000, 39_000, 134_000,
          49_000, 572_000, 50_000, 96_000, 16_000]
for i, s in enumerate(umumiy):
    entries.rasxod_qosh(d2, f"2026-08-{22 + i:02d}"[:10].replace("-32", "-31"),
                        f"umumiy {i}", s, F, umumiymi=True)

# shaxsiy rasxodlar
for s in (57_000, 280_000, 18_000, 20_000, 37_000, 170_000,
          85_000, 15_000, 41_000, 432_000):
    entries.rasxod_qosh(d2, "2026-08-24", "shaxsiy", s, F, umumiymi=False)
for s in (18_000, 6_000):
    entries.rasxod_qosh(d2, "2026-08-27", "shaxsiy", s, O, umumiymi=False)
for s in (155_000, 100_000, 18_000):
    entries.rasxod_qosh(d2, "2026-08-22", "shaxsiy", s, A, umumiymi=False)

# qarz: Fayzulloxon -> Otabek
entries.qarz_qosh(d2, "2026-08-27", F, O, 18_000, "Chinni")
entries.qarz_qosh(d2, "2026-08-27", F, O, 10_000, "Yo'lkira")

b = {r["nom"]: r for r in ledger.balanslar(d2)}
teng("Fayzulloxon kirim", 2_120_000, b["Fayzulloxon"]["kirim"])
teng("Abbosxon kirim", 1_900_000, b["Abbosxon"]["kirim"])
teng("Otabek kirim", 0, b["Otabek"]["kirim"])
teng("Fayzulloxon shaxsiy", 1_155_000, b["Fayzulloxon"]["shaxsiy"])
teng("Abbosxon shaxsiy", 273_000, b["Abbosxon"]["shaxsiy"])
teng("Otabek shaxsiy", 24_000, b["Otabek"]["shaxsiy"])
teng("umumiy jami", 1_559_000,
     d2.skalyar("SELECT SUM(summa) FROM rasxod WHERE umumiymi=1 AND ochirilgan=0"))

# Excel: har biriga 519,666.67 — bu yerda butun sonlar, yig'indi aniq
ulushlar = {r["nom"]: r["umumiy_ulush"] for r in ledger.balanslar(d2)}
teng("ulushlar yig'indisi = umumiy jami", 1_559_000, sum(ulushlar.values()))
tekshir("har bir ulush ~519,666", all(abs(v - 519_666) <= 11 for v in ulushlar.values()),
        str(ulushlar))

# Excel: Abbosxon hamma ulushini to'lagan (G ustuni "Ha")
entries.hisob_kitob_qosh(d2, "2026-09-01", A, F, ulushlar["Abbosxon"], "Ulush to'landi")

b = {r["nom"]: r for r in ledger.balanslar(d2)}

# Excel har kimga 519 666.67 bergan — butun songa sig'maydigan son.
# Bu yerda ulush butun: 519 667 / 519 667 / 519 666. Shuning uchun ayrim
# raqamlar Excel'dan aynan 1 so'mga farq qiladi. Bu xato emas — aksincha,
# Excel'da yo'qolayotgan tiyinni shu yerda tutib qolyapmiz.
def excelga_yaqin(nom, excel, olingan):
    tekshir(f"{nom} (Excel: {money.fmt(excel)}, farq ≤1 so'm)",
            abs(olingan - excel) <= 1, f"olingan {money.fmt(olingan)}")

teng("Otabek naqd", 4_000, b["Otabek"]["naqd"])
excelga_yaqin("Abbosxon naqd", 1_107_333, b["Abbosxon"]["naqd"])
excelga_yaqin("Fayzulloxon naqd", -102_333, b["Fayzulloxon"]["naqd"])
teng("Otabek sof (Excel: -547,667)", -547_667, b["Otabek"]["sof"])
teng("Fayzulloxon sof (Excel: +547,667)", 547_667, b["Fayzulloxon"]["sof"])
teng("naqd yig'indisi = kirim - rasxod",
     ledger.jami_kirim(d2) - ledger.jami_rasxod(d2),
     sum(r["naqd"] for r in ledger.balanslar(d2)))

# Abbosxon ulushini to'liq qaytardi — juftlik ro'yxatida qolmasligi kerak
juftlar = {(j.qarzdor_nom, j.kreditor_nom): j.summa for j in ledger.juft_qarzlar(d2)}
teng("to'langan juftlik ro'yxatdan chiqdi", [("Otabek", "Fayzulloxon")], list(juftlar))
teng("Otabek->Fayzulloxon juftlik summasi", 547_667,
     juftlar[("Otabek", "Fayzulloxon")])
teng("juftlik summasi = sof pozitsiya", -b["Otabek"]["sof"],
     juftlar[("Otabek", "Fayzulloxon")])


# ═══════════════════════════════════════════════════ 4. kitob teng

print("\n── audit: kitob teng bo'lishi ───────────────────────────────")

nat = ledger.audit(d2)
teng("SUM(sof) = 0", 0, nat["sof_yigindi"])
tekshir("naqd + sof = adolat (har odam uchun)", nat["identifikatsiya_ok"])
teng("SUM(naqd) = kirim - rasxod", nat["naqd_yigindi"], nat["kutilgan_naqd"])
tekshir("umumiy audit toza", nat["toza"], str(nat["muammolar"]))


# ═══════════════════════════════════════════════════ 5. hisob-kitob

print("\n── settle: minimal to'lovlar ────────────────────────────────")

kochirmalar = settle.taklif(d2)
teng("3 kishi uchun 1 ta to'lov yetarli", 1, len(kochirmalar))
k = kochirmalar[0]
teng("Otabek -> Fayzulloxon", ("Otabek", "Fayzulloxon"), (k.kimdan_nom, k.kimga_nom))
teng("to'lov summasi", 547_667, k.summa)

settle.bajar(d2, kochirmalar, "2026-09-02")
b = {r["nom"]: r for r in ledger.balanslar(d2)}
teng("hisob-kitobdan keyin hamma sof = 0", [0, 0, 0],
     [b[n]["sof"] for n in ("Fayzulloxon", "Otabek", "Abbosxon")])
tekshir("hisob-kitobdan keyin naqd = adolat",
        all(b[n]["naqd"] == b[n]["adolat"] for n in b))
tekshir("audit hali ham toza", ledger.audit(d2)["toza"])


# ═══════════════════════════════════════════════════ 6. yo'q kunlar

print("\n── yo'qlik: bo'lishdan chiqarish ────────────────────────────")

d3 = dbm.Db(_TMP / "b3.db", zaxirasiz=True)
F = d3.apply("odam", "INSERT", {"nom": "F", "tartib": 0})
O = d3.apply("odam", "INSERT", {"nom": "O", "tartib": 1})
A = d3.apply("odam", "INSERT", {"nom": "A", "tartib": 2})
d3.apply("yoq_kun", "INSERT",
         {"odam_id": O, "boshi": "2026-09-01", "oxiri": "2026-09-07",
          "sabab": "safarda"})
rid = entries.rasxod_qosh(d3, "2026-09-03", "ovqat", 90_000, F, umumiymi=True)
ul = {r["odam_id"]: r["summa"] for r in d3.q("SELECT * FROM ulush WHERE rasxod_id=?", rid)}
tekshir("yo'q odamga ulush yozilmadi", O not in ul, str(ul))
teng("qolgan 2 kishiga 45,000 dan", [45_000, 45_000], sorted(ul.values()))

rid2 = entries.rasxod_qosh(d3, "2026-09-20", "ovqat", 90_000, F, umumiymi=True)
ul2 = {r["odam_id"] for r in d3.q("SELECT * FROM ulush WHERE rasxod_id=?", rid2)}
teng("yo'qlik tugagach yana 3 kishi", 3, len(ul2))


# ═══════════════════════════════════════════════ 7. cheklar va o'chirish

print("\n── pul darajasi va ogohlantirish ────────────────────────────")

teng("200 000 dan yuqori — yetarli", "yaxshi", ledger.holat(250_000, 0))
teng("200 000 dan past — kam qoldi", "kam", ledger.holat(150_000, 0))
teng("100 000 dan past — juda kam", "juda_kam", ledger.holat(90_000, 0))
teng("chegaraning o'zi hali kam emas", "yaxshi", ledger.holat(200_000, 0))
teng("100 000 aynan — kam, juda kam emas", "kam", ledger.holat(100_000, 0))
teng("manfiy pul — qarzda", "qarzda", ledger.holat(-5_000, 0))
teng("puli ko'p, lekin qarzdor — qarzda", "qarzda", ledger.holat(900_000, -50_000))
teng("puli kam, lekin unga qarzdorlar — baribir kam",
     "kam", ledger.holat(150_000, 300_000))

d7 = dbm.Db(_TMP / "b7.db", zaxirasiz=True)
X = d7.apply("odam", "INSERT", {"nom": "Boy", "tartib": 0})
Y = d7.apply("odam", "INSERT", {"nom": "Kam", "tartib": 1})
Z = d7.apply("odam", "INSERT", {"nom": "Qarzdor", "tartib": 2})
entries.kirim_qosh(d7, "2026-09-01", X, 1_000_000)
entries.kirim_qosh(d7, "2026-09-01", Y, 150_000)
entries.qarz_qosh(d7, "2026-09-01", X, Z, 50_000)

dar = {x["nom"]: x for x in ledger.darajalar(d7)}
teng("Boy — yetarli", "yaxshi", dar["Boy"]["holat"])
teng("Kam — kam qoldi", "kam", dar["Kam"]["holat"])
teng("Qarzdor — qarzda", "qarzda", dar["Qarzdor"]["holat"])
teng("eng boyning chizig'i to'la", 1.0, dar["Boy"]["ulush"])
tekshir("ulush 0..1 oralig'ida",
        all(0.0 <= x["ulush"] <= 1.0 for x in dar.values()))
teng("2 ta ogohlantirish (Kam va Qarzdor)", 2, len(ledger.ogohlantirish(d7)))
teng("qarzdor bo'lsa ham cho'ntagi bo'shligi aytiladi", "juda_kam",
     ledger.pul_darajasi(50_000))
teng("holat qarzni ustun qo'yadi", "qarzda", ledger.holat(50_000, -50_000))

ledger.chegara_qoy(d7, 100_000, 50_000)
teng("chegara o'zgarsa holat ham o'zgaradi", "yaxshi",
     {x["nom"]: x for x in ledger.darajalar(d7)}["Kam"]["holat"])
d7.yop()


print("\n── blok-blok hisob-kitob ────────────────────────────────────")

# Excel'dagi qator yonidagi "Ha" belgisi: hammasini birdan emas,
# har bir rasxodni ALOHIDA to'landi deb belgilash.
d6 = dbm.Db(_TMP / "b6.db", zaxirasiz=True)
F6 = d6.apply("odam", "INSERT", {"nom": "F", "tartib": 0})
O6 = d6.apply("odam", "INSERT", {"nom": "O", "tartib": 1})
A6 = d6.apply("odam", "INSERT", {"nom": "A", "tartib": 2})
entries.kirim_qosh(d6, "2026-09-01", F6, 900_000)
for i, s in enumerate((300_000, 60_000, 90_000)):
    entries.rasxod_qosh(d6, f"2026-09-0{i + 1}", f"bozor {i + 1}", s, F6,
                        umumiymi=True)

bloklar = settle.ochiq_bloklar(d6)
teng("3 rasxod × 2 qarzdor = 6 ta blok", 6, len(bloklar))
teng("to'lovchining o'z ulushi blok emas", 0,
     sum(1 for b in bloklar if b["qarzdor_id"] == F6))

sof_oldin = {r["nom"]: r["sof"] for r in ledger.balanslar(d6)}
otabek_bloklari = settle.ochiq_bloklar(d6, qarzdor_id=O6)
teng("Otabekda 3 ta ochiq blok", 3, len(otabek_bloklari))

bitta = next(b for b in otabek_bloklari if b["rasxod_summa"] == 60_000)
settle.blok_yop(d6, bitta["ulush_id"])
teng("faqat bitta blok yopildi", 2, len(settle.ochiq_bloklar(d6, qarzdor_id=O6)))
teng("Abbosxonning bloklari tegilmadi", 3,
     len(settle.ochiq_bloklar(d6, qarzdor_id=A6)))
teng("Otabekning qarzi aynan shu blokka kamaydi",
     sof_oldin["O"] + bitta["summa"],
     {r["nom"]: r["sof"] for r in ledger.balanslar(d6)}["O"])
tekshir("blokdan keyin kitob teng", ledger.audit(d6)["toza"])

settle.blok_och(d6, bitta["ulush_id"])
teng("blok qayta ochildi", 3, len(settle.ochiq_bloklar(d6, qarzdor_id=O6)))
teng("qarz avvalgi holatga qaytdi", sof_oldin["O"],
     {r["nom"]: r["sof"] for r in ledger.balanslar(d6)}["O"])
teng("qayta ochilganda to'lov ham bekor bo'ldi", 0,
     d6.skalyar("SELECT COUNT(*) FROM hisob_kitob WHERE ochirilgan=0"))

settle.bloklarni_yop(d6, [b["ulush_id"] for b in settle.ochiq_bloklar(d6, qarzdor_id=O6)])
teng("Otabekda ochiq blok qolmadi", 0, len(settle.ochiq_bloklar(d6, qarzdor_id=O6)))
teng("Otabekning qarzi nolga tushdi", 0,
     {r["nom"]: r["sof"] for r in ledger.balanslar(d6)}["O"])
tekshir("hammasi yopilgach ham kitob teng", ledger.audit(d6)["toza"])
d6.undo()
teng("undo bir yo'la yopishni qaytardi", 3,
     len(settle.ochiq_bloklar(d6, qarzdor_id=O6)))


print("\n── odam qo'shish / ro'yxatdan olish ─────────────────────────")

yangi = entries.odam_qosh(d6, "Sardor")
teng("yangi odam qo'shildi", 4, len(ledger.balanslar(d6)))
entries.odam_ochir(d6, yangi)
teng("qarzsiz odam ro'yxatdan olindi", 3, len(ledger.balanslar(d6)))
tekshir("olib tashlangach ham kitob teng", ledger.audit(d6)["toza"])
entries.odam_qaytar(d6, yangi)
teng("odam qaytarildi", 4, len(ledger.balanslar(d6)))
entries.odam_ochir(d6, yangi)

try:
    entries.odam_ochir(d6, O6)          # Otabek qarzdor
    tekshir("qarzdor odamni o'chirib bo'lmaydi", False)
except ValueError:
    tekshir("qarzdor odamni o'chirib bo'lmaydi", True)
d6.yop()


print("\n── boshqa uchun xarid: qarz, kirim emas ─────────────────────")

# Fayzulloxon Otabekka poyabzal olib berdi — 300 000.
# TO'G'RI:   Otabekning qarzi 300 000 ga oshadi, qo'lidagi pul o'zgarmaydi.
# NOTO'G'RI: "Otabekka 300 000 kirim + 300 000 shaxsiy rasxod" —
#            bu uning kirimini ham, rasxodini ham soxta ko'rsatadi.
d5 = dbm.Db(_TMP / "b5.db", zaxirasiz=True)
F5 = d5.apply("odam", "INSERT", {"nom": "Fayzulloxon", "tartib": 0})
O5 = d5.apply("odam", "INSERT", {"nom": "Otabek", "tartib": 1})
A5 = d5.apply("odam", "INSERT", {"nom": "Abbosxon", "tartib": 2})
entries.kirim_qosh(d5, "2026-09-01", F5, 1_000_000)

oldin = {r["nom"]: dict(r) for r in ledger.balanslar(d5)}
rid5 = entries.rasxod_qosh(d5, "2026-09-02", "Poyabzal", 300_000, F5,
                           kim_uchun=O5, turi_id=None)
b5 = {r["nom"]: dict(r) for r in ledger.balanslar(d5)}

teng("Otabekka kirim yozilmadi", 0, b5["Otabek"]["kirim"])
teng("Otabekning qo'lidagi pul o'zgarmadi",
     oldin["Otabek"]["naqd"], b5["Otabek"]["naqd"])
teng("Otabek 300 000 qarzdor bo'ldi", -300_000, b5["Otabek"]["sof"])
teng("Fayzulloxonga 300 000 qaytishi kerak", 300_000, b5["Fayzulloxon"]["sof"])
teng("Fayzulloxonning qo'lidan 300 000 chiqdi",
     oldin["Fayzulloxon"]["naqd"] - 300_000, b5["Fayzulloxon"]["naqd"])
teng("Abbosxonga umuman tegmadi", 0, b5["Abbosxon"]["sof"])
teng("bu umumiy rasxod emas — Otabekning ulushi alohida",
     300_000, b5["Otabek"]["uchun_ulush"])
teng("umumiy ulush 0 bo'lib qoldi", 0, b5["Otabek"]["umumiy_ulush"])
teng("Otabekning adolatli balansi 300 000 ga kamaydi",
     oldin["Otabek"]["adolat"] - 300_000, b5["Otabek"]["adolat"])
tekshir("kitob teng", ledger.audit(d5)["toza"])

# uchta odam bo'lsa ham uchdan birga bo'linib ketmasin
ul5 = {r["odam_id"]: r["summa"] for r in
       d5.q("SELECT odam_id, summa FROM ulush WHERE rasxod_id=?", rid5)}
teng("ulush faqat bitta odamga", {O5: 300_000}, ul5)

# hisob-kitob taklifi shuni ko'rsatsin
k5 = settle.taklif(d5)
teng("bitta to'lov taklif qilindi", 1, len(k5))
teng("Otabek -> Fayzulloxon 300 000",
     ("Otabek", "Fayzulloxon", 300_000),
     (k5[0].kimdan_nom, k5[0].kimga_nom, k5[0].summa))
d5.yop()

print("\n── nofaol odam qarzni yashira olmaydi ───────────────────────")

# O'yin: Otabek qarzdor. Uni "nofaol" qilib qo'ysak, qarzi hisobdan
# tushib ketmasligi kerak — aks holda 500 mingni bir bosishda yo'q
# qilib yuborish mumkin bo'lardi.
d4 = dbm.Db(_TMP / "b4.db", zaxirasiz=True)
F4 = d4.apply("odam", "INSERT", {"nom": "F", "tartib": 0})
O4 = d4.apply("odam", "INSERT", {"nom": "O", "tartib": 1})
entries.kirim_qosh(d4, "2026-09-01", F4, 100_000)
entries.rasxod_qosh(d4, "2026-09-01", "ovqat", 100_000, F4, umumiymi=True)
teng("nofaoldan oldin sof yig'indisi", 0, ledger.audit(d4)["sof_yigindi"])
d4.apply("odam", "UPDATE", {"faol": 0}, O4)
teng("nofaol qilingach ham sof yig'indisi 0", 0, ledger.audit(d4)["sof_yigindi"])
tekshir("nofaol qilingach ham audit toza", ledger.audit(d4)["toza"])
teng("UI ro'yxatida faqat faol odam", 1, len(ledger.balanslar(d4)))
teng("audit hamma odamni ko'radi", 2, len(ledger.balanslar(d4, hammasi=True)))
d4.yop()

print("\n── cheklar ──────────────────────────────────────────────────")

from core import receipts  # noqa: E402

_chek = _TMP / "chek.png"
_chek.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
cid = receipts.qosh(d3, rid2, _chek)
teng("chek biriktirildi", 1, receipts.soni(d3, rid2))
tekshir("chek fayli nusxalandi",
        receipts.royxat(d3, rid2)[0]["bormi"])
_chek.unlink()
tekshir("asl fayl o'chsa ham chek qoladi",
        receipts.royxat(d3, rid2)[0]["bormi"])
receipts.qosh(d3, rid2, receipts.royxat(d3, rid2)[0]["yol"])
teng("bir xil chek ikki marta yozilmadi", 1, receipts.soni(d3, rid2))
receipts.ochir(d3, cid)
teng("chek o'chirildi", 0, receipts.soni(d3, rid2))
d3.undo()
teng("undo chekni qaytardi", 1, receipts.soni(d3, rid2))

print("\n── o'chirish: hech narsa yo'qolmaydi ────────────────────────")

entries.rasxod_ochir(d3, rid2)
tekshir("rasxod bazadan yo'qolmadi",
        d3.q1("SELECT ochirilgan FROM rasxod WHERE id=?", rid2)["ochirilgan"] == 1)
tekshir("o'chirilgan rasxod balansga ta'sir qilmaydi", ledger.audit(d3)["toza"])
d3.undo()
tekshir("undo o'chirishni qaytardi",
        d3.q1("SELECT ochirilgan FROM rasxod WHERE id=?", rid2)["ochirilgan"] == 0)


# ═══════════════════════════════════════════════ vazifalar

print("\n── vazifalar: qo'shish va biriktirish ────────────────")

from datetime import date as _date, datetime as _datetime, timedelta as _td  # noqa: E402

from core import vazifa as vz  # noqa: E402

d8 = dbm.Db(_TMP / "b8.db", zaxirasiz=True)
vA = entries.odam_qosh(d8, "Fayzulloxon")
vB = entries.odam_qosh(d8, "Otabek")
_du = vz.hafta_boshi(_date(2026, 9, 4))
teng("hafta boshi — dushanba", 0, _du.weekday())
teng("haftada 7 kun", 7, len(vz.hafta_kunlari(_date(2026, 9, 4))))

t1 = vz.qosh(d8, "Ovqat qilish", vA, _du, "09:00", 90)
t2 = vz.qosh(d8, "Musorlarni tashlash", vB, _du + _td(days=1), "18:30")
t3 = vz.qosh(d8, "Dasturxon yozish", vA, _du + _td(days=2))
teng("haftada 3 ta vazifa", 3, len(vz.hafta(d8, _du)))
teng("vaqtsiz vazifa saqlanadi", None, vz.bitta(d8, t3)["vaqt"])
teng("shaxsma shaxs: faqat o'ziniki", 2, len(vz.hafta(d8, _du, vA)))
teng("boshqa haftada yo'q", 0, len(vz.hafta(d8, _du + _td(days=7))))

print("\n── vazifalar: holat va sanoq ──────────────────────")

vz.bajar(d8, t1)
teng("bajarildi deb belgilandi", vz.BAJARILDI, vz.bitta(d8, t1)["holat"])
tekshir("bajarilgan vaqti yozildi", bool(vz.bitta(d8, t1)["bajarilgan"]))
_s = vz.sanoq(d8, _du, _du + _td(days=6))
teng("sanoq: jami", 3, _s["jami"])
teng("sanoq: bajarildi", 1, _s["bajarildi"])
teng("sanoq: ochiq", 2, _s["ochiq"])
vz.bajar(d8, t1, False)
teng("qayta ochildi", vz.OCHIQ, vz.bitta(d8, t1)["holat"])
teng("qayta ochilganda vaqt tozalandi", None, vz.bitta(d8, t1)["bajarilgan"])

print("\n── vazifalar: kun surilsa qolgani ergashadi (Excel B13) ───")

vz.bajar(d8, t1)
_n = vz.surish(d8, _du, kunlar=1)
teng("2 ta ochiq vazifa surildi", 2, _n)
teng("bajarilgan vazifa joyida qoldi", _du.isoformat(),
     vz.bitta(d8, t1)["sana"])
teng("t2 bir kunga surildi", (_du + _td(days=2)).isoformat(),
     vz.bitta(d8, t2)["sana"])
teng("t3 ham ergashdi", (_du + _td(days=3)).isoformat(),
     vz.bitta(d8, t3)["sana"])
tekshir("surish bitta undo qadami",
        "surildi" in (d8.oxirgi_guruh() or ("", ""))[1])
d8.undo()
teng("undo surishni butunlay qaytardi", (_du + _td(days=1)).isoformat(),
     vz.bitta(d8, t2)["sana"])

_n2 = vz.surish(d8, _du, vA, kunlar=1)
teng("faqat bitta odamniki surildi", 1, _n2)
teng("boshqa odamnikiga tegilmadi", (_du + _td(days=1)).isoformat(),
     vz.bitta(d8, t2)["sana"])

print("\n── vazifalar: o'chirish va tekshiruv ────────────────")

vz.ochir(d8, t3)
teng("ro'yxatdan chiqdi", 2, len(vz.hafta(d8, _du)))
teng("bazada saqlanib qoldi (3-qoida)", 1,
     d8.q1("SELECT ochirilgan FROM vazifa WHERE id=?", t3)["ochirilgan"])
d8.undo()
teng("undo o'chirishni qaytardi", 3, len(vz.hafta(d8, _du)))


def _yiqiladimi(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


tekshir("bo'sh nom rad etiladi", _yiqiladimi(lambda: vz.qosh(d8, "  ", vA, _du)))
tekshir("yo'q odam rad etiladi", _yiqiladimi(lambda: vz.qosh(d8, "x", 999, _du)))
tekshir("noto'g'ri vaqt rad etiladi",
        _yiqiladimi(lambda: vz.qosh(d8, "x", vA, _du, "99:99")))
tekshir("manfiy davomiylik rad etiladi",
        _yiqiladimi(lambda: vz.qosh(d8, "x", vA, _du, "09:00", 0)))
entries.odam_ochir(d8, vB)
tekshir("nofaol odamga vazifa berilmaydi",
        _yiqiladimi(lambda: vz.qosh(d8, "x", vB, _du)))

tekshir("vazifa kitob tengligiga tegmaydi", ledger.audit(d8)["toza"])
# Excel'dagi 5 ta + general uborkaning 3 tasi (`db.UBORKA`)
teng("tayyor ish turlari ekildi", 8, len(vz.turlar(d8)))

_t = vz.turlar(d8)[0]
_bid = vz.biriktir(d8, _t["id"], vA, _du, "07:00")
teng("tur odamga biriktirildi", _t["nom"], vz.bitta(d8, _bid)["nom"])
teng("turning davomiyligi ko'chdi", _t["davomiylik"],
     vz.bitta(d8, _bid)["davomiylik"])
vz.tur_ochir(d8, _t["id"])
teng("tur ro'yxatdan chiqdi", 7, len(vz.turlar(d8)))
tekshir("biriktirilgan vazifa turi bilan o'chmaydi",
        vz.bitta(d8, _bid) is not None)
teng("o'chirilgan tur qayta qo'shilsa tiriladi", _t["id"],
     vz.tur_qosh(d8, _t["nom"]))
tekshir("bir xil nomli tur ikki marta qo'shilmaydi",
        _yiqiladimi(lambda: vz.tur_qosh(d8, _t["nom"])))
tekshir("bo'sh nomli tur rad etiladi",
        _yiqiladimi(lambda: vz.tur_qosh(d8, "   ")))
_yid = vz.tur_qosh(d8, "Kir yuvish", 45)
teng("yangi tur qo'shildi", 9, len(vz.turlar(d8)))
teng("yangi turning davomiyligi", 45, vz.tur_bitta(d8, _yid)["davomiylik"])

print("\n── vazifalar: ovqat navbati ─────────────────────")

d9 = dbm.Db(_TMP / "b9.db", zaxirasiz=True)
nF = entries.odam_qosh(d9, "Fayzulloxon")
nO = entries.odam_qosh(d9, "Otabek")
nA = entries.odam_qosh(d9, "Abbosxon")
_ovqat = [t for t in vz.turlar(d9) if t["navbat"]]
teng("bitta navbatli ish turi bor", 1, len(_ovqat))
_ovqat = _ovqat[0]
teng("navbatli ish - ovqat qilish", "Ovqat qilish", _ovqat["nom"])
_idish = vz.tur_bitta(d9, _ovqat["ergash_turi_id"])
tekshir("ergash ish - idish yuvish", "idish" in _idish["nom"].lower())

_yid2 = vz.tur_qosh(d9, "Kir yuvish", 45)
_du9 = vz.hafta_boshi(_date(2026, 9, 7))
_reja = vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9, "19:00", 3)
teng("3 kun = 3 ovqat + 3 idish", 6, len(_reja))

_oshpaz = {x["sana"]: x["odam"] for x in _reja if x["nom"] == _ovqat["nom"]}
_yuvuvchi = {x["sana"]: x["odam"] for x in _reja if x["nom"] == _idish["nom"]}
teng("1-kun Fayzulloxon pishiradi", "Fayzulloxon", _oshpaz[_du9])
teng("2-kun Otabek pishiradi", "Otabek", _oshpaz[_du9 + _td(days=1)])
teng("3-kun Abbosxon pishiradi", "Abbosxon", _oshpaz[_du9 + _td(days=2)])
teng("Fayzulloxon pishirsa o'zi yuvadi", "Fayzulloxon", _yuvuvchi[_du9])
teng("Otabek pishirsa o'zi yuvadi", "Otabek",
     _yuvuvchi[_du9 + _td(days=1)])
teng("Abbosxon pishirsa o'zi yuvadi", "Abbosxon",
     _yuvuvchi[_du9 + _td(days=2)])
teng("har kuni yuvuvchi = oshpaz", _oshpaz, _yuvuvchi)
teng("idish ovqatdan keyin", "20:00",
     [x["vaqt"] for x in _reja if x["nom"] == _idish["nom"]][0])

teng("navbat 4-kunda aylanadi", "Fayzulloxon",
     [x["odam"] for x in vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9,
                                          "19:00", 4)
      if x["nom"] == _ovqat["nom"]][3])
teng("boshqa odamdan boshlansa navbat undan yuradi", "Otabek",
     vz.navbat_rejasi(d9, _ovqat["id"], nO, _du9, "19:00", 1)[0]["odam"])
teng("Otabekdan boshlansa Otabek o'zi yuvadi", "Otabek",
     vz.navbat_rejasi(d9, _ovqat["id"], nO, _du9, "19:00", 1)[1]["odam"])

_n = vz.navbat_biriktir(d9, _ovqat["id"], nF, _du9, "19:00", 3)
teng("navbat bazaga yozildi", 6, _n)
teng("kalendarda 6 ta vazifa", 6, len(vz.hafta(d9, _du9)))
tekshir("navbat bitta undo qadami",
        "navbati" in (d9.oxirgi_guruh() or ("", ""))[1])
d9.undo()
teng("undo butun navbatni oldi", 0, len(vz.hafta(d9, _du9)))

tekshir("navbatsiz ishga navbat qo'llanmaydi",
        _yiqiladimi(lambda: vz.navbat_rejasi(d9, _yid2, nF, _du9, "19:00", 3)))
teng("navbatli ishni oddiy biriktirish ham mumkin", 1,
     (vz.biriktir(d9, _ovqat["id"], nF, _du9, "19:00") is not None) and 1)

# Ergash ish o'chirilsa: navbat JIM qolmasligi kerak
vz.tur_ochir(d9, _idish["id"])
tekshir("o'chirilgan ergash None qaytaradi",
        vz.tur_ergash(d9, _ovqat["id"]) is None)
teng("ergashsiz navbat faqat pishirishni yozadi", 3,
     len(vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9, "19:00", 3)))
vz.tur_ergash_qoy(d9, _ovqat["id"], _yid2)
teng("ergash almashtirildi", "Kir yuvish",
     vz.tur_ergash(d9, _ovqat["id"])["nom"])
teng("yangi ergash bilan navbat to'liq", 6,
     len(vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9, "19:00", 3)))
teng("yangi ergash to'g'ri odamga tushdi (oshpazning o'ziga)", "Fayzulloxon",
     vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9, "19:00", 1)[1]["odam"])
tekshir("ish o'zidan keyin kelolmaydi",
        _yiqiladimi(lambda: vz.tur_ergash_qoy(d9, _ovqat["id"], _ovqat["id"])))

# ── kalendar eksporti
from core import reports as _rep  # noqa: E402

# yuqorida o'chirilgan edi — tur_qosh uni tiriltiradi
_idish2 = vz.tur_qosh(d9, _idish["nom"])
vz.tur_ergash_qoy(d9, _ovqat["id"], _idish2)
vz.navbat_biriktir(d9, _ovqat["id"], nF, _du9, "19:00", 7)
_dan, _gacha = _du9.isoformat(), (_du9 + _td(days=6)).isoformat()

_h = _rep.vazifa_html(d9, _dan, _gacha)
tekshir("umumiy kalendar HTML yozildi", _h.exists() and _h.stat().st_size > 800)
_matn = _h.read_text(encoding="utf-8")
tekshir("HTML da to'liq kun nomlari", "Dushanba" in _matn and "Yakshanba" in _matn)
tekshir("HTML da uchala odam ham bor",
        all(x in _matn for x in ("Fayzulloxon", "Otabek", "Abbosxon")))
tekshir("HTML o'zi yetarli (tashqi fayl yo'q)",
        "<style>" in _matn and "src=" not in _matn and "http" not in _matn)

_hs = _rep.vazifa_html(d9, _dan, _gacha, nO)
_matns = _hs.read_text(encoding="utf-8")
tekshir("shaxsiy HTML — faqat o'sha odam",
        "Otabek — vazifalar" in _matns and ">Abbosxon<" not in _matns)

_x = _rep.vazifa_excel(d9, _dan, _gacha)
tekshir("umumiy kalendar Excel yozildi", _x.exists() and _x.stat().st_size > 3000)
import openpyxl as _op  # noqa: E402
_wb = _op.load_workbook(_x)
teng("Excel'da ikki varaq", ["Vazifalar", "Xulosa"], _wb.sheetnames)
teng("Excel qatorlari kalendardagicha", len(vz.oraliq(d9, _dan, _gacha)),
     _wb["Vazifalar"].max_row - 1)

_xs = _rep.vazifa_excel(d9, _dan, _gacha, nO)
_wbs = _op.load_workbook(_xs)
_kimlar = {_wbs["Vazifalar"].cell(r, 5).value
           for r in range(2, _wbs["Vazifalar"].max_row + 1)}
teng("shaxsiy Excel — faqat o'sha odam", {"Otabek"}, _kimlar)
tekshir("fayl nomida odam ismi bor", "Otabek" in _xs.name)

# Hisobot ish stoliga tushadi — lekin FARVONUY_DATA qo'yilgan bo'lsa YO'Q.
# (Aks holda har test ishga tushganda ish stoli axlatga to'lardi.)
teng("test rejimida eksport ma'lumot papkasida", config.EKSPORT,
     config.eksport_papkasi())
tekshir("eksport fayllari ish stoliga tushmadi",
        _h.parent == config.EKSPORT and _x.parent == config.EKSPORT)
_stol = config.ish_stoli()
tekshir("ish stoli topildi", _stol is None or _stol.is_dir())

print("\n── qarz: juftlik tarkibi ─────────────────────")

# Tafsilot oynasi shu funksiyaga tayanadi: qatorlar yig'indisi
# yuqorida ko'rsatilgan songa TENG bo'lishi shart, aks holda oyna
# boshqa raqam ko'rsatadi va odam ishonchni yo'qotadi.
dB = dbm.Db(_TMP / "bB.db", zaxirasiz=True)
bF = entries.odam_qosh(dB, "Fayzulloxon")
bO = entries.odam_qosh(dB, "Otabek")
bA = entries.odam_qosh(dB, "Abbosxon")
entries.rasxod_qosh(dB, "2026-08-10", "Bozorlik", 90_000, bF)   # 30k ulush
entries.qarz_qosh(dB, "2026-08-11", bF, bO, 20_000, "Taksi")
entries.hisob_kitob_qosh(dB, "2026-08-12", bO, bF, 5_000, "qisman")

_t = ledger.juft_tarkibi(dB, bO, bF)
teng("tarkibda uchta yozuv", 3, len(_t))
teng("tarkib yig'indisi 45 000", 45_000, sum(x["summa"] for x in _t))
teng("juftlik summasi ham 45 000", 45_000,
     [j.summa for j in ledger.juft_qarzlar(dB)
      if j.qarzdor_id == bO and j.kreditor_id == bF][0])
teng("uchala turi ham bor", {"Umumiy rasxod", "Qarz", "To'lov"},
     {x["turi"] for x in _t})
teng("umumiy rasxod ulushi musbat", 30_000,
     [x["summa"] for x in _t if x["turi"] == "Umumiy rasxod"][0])
teng("qarz musbat", 20_000, [x["summa"] for x in _t if x["turi"] == "Qarz"][0])
teng("to'lov MANFIY (qarzni kamaytiradi)", -5_000,
     [x["summa"] for x in _t if x["turi"] == "To'lov"][0])
tekshir("har qatorda sana bor", all(x["sana"] for x in _t))
tekshir("sana bo'yicha tartiblangan",
        [x["sana"] for x in _t] == sorted(x["sana"] for x in _t))
tekshir("to'lovning bajarilgan sanasi bor",
        all(x["tolangan_sana"] for x in _t if x["turi"] == "To'lov"))

entries.rasxod_qosh(dB, "2026-08-13", "Non", 30_000, bO)
_t2 = ledger.juft_tarkibi(dB, bO, bF)
teng("teskari yo'nalish manfiy qator qo'shdi", -10_000,
     [x["summa"] for x in _t2 if x["nom"] == "Non"][0])
teng("teskaridan keyin ham yig'indi juftlikka teng",
     [j.summa for j in ledger.juft_qarzlar(dB)
      if j.qarzdor_id == bO and j.kreditor_id == bF][0],
     sum(x["summa"] for x in _t2))

for _j in ledger.juft_qarzlar(d):
    teng(f"Excel: {_j.qarzdor_nom}→{_j.kreditor_nom} tarkibi mos",
         _j.summa,
         sum(x["summa"] for x in ledger.juft_tarkibi(
             d, _j.qarzdor_id, _j.kreditor_id)))

print("\n── qarz: faqat to'lanmagani ───────────────────")

# dB hozir: Bozorlik ulushi +30k, Taksi qarzi +20k, erkin to'lov −5k,
# teskari «Non» −10k. Jami 35k. Kamaytiruvchi 15k eng eski qarzni —
# Bozorlikni — qisman yopadi.
_tm = ledger.juft_tolanmagan(dB, bO, bF)
teng("to'lanmagan: ikkita qator", 2, len(_tm))
teng("to'lanmagan yig'indisi juftlikka teng", 35_000,
     sum(x["summa"] for x in _tm))
teng("to'lovlar eng eski qarzdan ayirildi (Bozorlik 30k → 15k)",
     (15_000, 30_000), (_tm[0]["summa"], _tm[0]["asl"]))
teng("yangirog'i tegilmadi (Taksi 20k)", (20_000, 20_000),
     (_tm[1]["summa"], _tm[1]["asl"]))
tekshir("to'lov va manfiy qator chiqmaydi",
        all(x["summa"] > 0 and x["turi"] != "To'lov" for x in _tm))
teng("teskari yo'nalishda bo'sh", [], ledger.juft_tolanmagan(dB, bF, bO))

# «To'landi» deb belgilangan blok va uning to'lovi birga yo'qoladi —
# erkin to'lov esa boshqa qarzni yopishga ketadi.
_bz = [b for b in settle.ochiq_bloklar(dB, bO, bF) if b["nom"] == "Bozorlik"][0]
settle.bloklarni_yop(dB, [_bz["ulush_id"]], "2026-08-14")
_tm2 = ledger.juft_tolanmagan(dB, bO, bF)
_j2 = [j.summa for j in ledger.juft_qarzlar(dB)
       if j.qarzdor_id == bO and j.kreditor_id == bF][0]
teng("belgilangandan keyin ham yig'indi juftlikka teng", _j2,
     sum(x["summa"] for x in _tm2))
teng("to'langan blok ro'yxatdan chiqdi", ["Taksi"], [x["nom"] for x in _tm2])
teng("erkin to'lov keyingi qarzni yopdi (Taksi 20k → 5k)", 5_000,
     _tm2[0]["summa"])
dB.undo()
teng("undo'dan keyin blok qaytdi", 2, len(ledger.juft_tolanmagan(dB, bO, bF)))

for _j in ledger.juft_qarzlar(d):
    _tmx = ledger.juft_tolanmagan(d, _j.qarzdor_id, _j.kreditor_id)
    teng(f"Excel: {_j.qarzdor_nom}→{_j.kreditor_nom} to'lanmagani mos",
         _j.summa, sum(x["summa"] for x in _tmx))
    tekshir(f"Excel: {_j.qarzdor_nom}→{_j.kreditor_nom} faqat musbat qatorlar",
            all(0 < x["summa"] <= x["asl"] for x in _tmx))


print("── vazifalar: navbatni o'zgartirish ──────────────")

dA = dbm.Db(_TMP / "bA.db", zaxirasiz=True)
aF = entries.odam_qosh(dA, "Fayzulloxon")
aO = entries.odam_qosh(dA, "Otabek")
aA = entries.odam_qosh(dA, "Abbosxon")
_ovq = vz.navbat_turi(dA)
_idi = vz.tur_ergash(dA, _ovq["id"])
_duA = vz.hafta_boshi(_date(2026, 8, 31))
vz.navbat_biriktir(dA, _ovq["id"], aF, _duA, "19:00", 6)


def _oshpaz(db, sana):
    r = db.q1("SELECT o.nom FROM vazifa v JOIN odam o ON o.id=v.odam_id"
              " WHERE v.ochirilgan=0 AND v.nom=? AND v.sana=?",
              _ovq["nom"], sana)
    return r["nom"] if r else None


def _yuvuvchi(db, sana):
    r = db.q1("SELECT o.nom FROM vazifa v JOIN odam o ON o.id=v.odam_id"
              " WHERE v.ochirilgan=0 AND v.nom=? AND v.sana=?",
              _idi["nom"], sana)
    return r["nom"] if r else None


def _pishirish_soni(db):
    return {r["nom"]: r["n"] for r in db.q(
        "SELECT o.nom, COUNT(*) n FROM vazifa v JOIN odam o ON o.id=v.odam_id"
        " WHERE v.ochirilgan=0 AND v.nom=? GROUP BY o.nom", _ovq["nom"])}


_k3, _k4, _k5 = "2026-09-03", "2026-09-04", "2026-09-05"
teng("boshida 03.09 Fayzulloxon", "Fayzulloxon", _oshpaz(dA, _k3))
teng("boshida 05.09 Abbosxon", "Abbosxon", _oshpaz(dA, _k5))
_oldingi_soni = _pishirish_soni(dA)

_v3 = dA.q1("SELECT id FROM vazifa WHERE nom=? AND sana=? AND ochirilgan=0",
            _ovq["nom"], _k3)["id"]
_natija = vz.almashtir(dA, _v3, aA)
teng("almashuv jufti — Abbosxonning keyingi navbati", _k5,
     _natija["juft_sana"])
teng("03.09 endi Abbosxon", "Abbosxon", _oshpaz(dA, _k3))
teng("05.09 endi Fayzulloxon", "Fayzulloxon", _oshpaz(dA, _k5))
teng("oradagi 04.09 tegilmadi", "Otabek", _oshpaz(dA, _k4))
teng("navbat soni o'zgarmadi", _oldingi_soni, _pishirish_soni(dA))
teng("03.09 yuvuvchi qoidaga mos (Abbosxon o'zi yuvadi)", "Abbosxon",
     _yuvuvchi(dA, _k3))
teng("05.09 yuvuvchi qoidaga mos (Fayzulloxon o'zi yuvadi)", "Fayzulloxon",
     _yuvuvchi(dA, _k5))
tekshir("almashuv bitta undo qadami",
        "almashdi" in (dA.oxirgi_guruh() or ("", ""))[1])
dA.undo()
teng("undo almashuvni qaytardi", "Fayzulloxon", _oshpaz(dA, _k3))
teng("undo yuvuvchini ham qaytardi", "Fayzulloxon", _yuvuvchi(dA, _k3))

# «faqat shu kunni berish» — almashuvsiz
vz.bersin(dA, _v3, aA)
teng("bersin: 03.09 Abbosxon", "Abbosxon", _oshpaz(dA, _k3))
teng("bersin: 05.09 tegilmadi", "Abbosxon", _oshpaz(dA, _k5))
teng("bersin: yuvuvchi ham to'g'rilandi", "Abbosxon", _yuvuvchi(dA, _k3))
_yangi_soni = _pishirish_soni(dA)
teng("bersin: Abbosxonda bitta ko'p", _oldingi_soni["Abbosxon"] + 1,
     _yangi_soni["Abbosxon"])
dA.undo()

tekshir("o'ziga almashtirib bo'lmaydi",
        _yiqiladimi(lambda: vz.almashtir(dA, _v3, aF)))
tekshir("o'ziga berib bo'lmaydi",
        _yiqiladimi(lambda: vz.bersin(dA, _v3, aF)))
_oxirgi = dA.q1("SELECT id FROM vazifa WHERE nom=? AND ochirilgan=0"
                " ORDER BY sana DESC LIMIT 1", _ovq["nom"])["id"]
tekshir("keyingi navbati yo'q odam bilan almashtirib bo'lmaydi",
        _yiqiladimi(lambda: vz.almashtir(dA, _oxirgi, aO)))


# ══════════════════════════════════════════════ telegram

print("\n── telegram: xabar matnlari ─────────────────────")

import time as _time  # noqa: E402

from core import xabar as xb  # noqa: E402

dC = dbm.Db(_TMP / "bC.db", zaxirasiz=True)
cF = entries.odam_qosh(dC, "Fayzulloxon")
cO = entries.odam_qosh(dC, "Otabek")
cA = entries.odam_qosh(dC, "Abbosxon")
for _oid, _tg in ((cF, "fsultonoov"), (cO, "otabek_33"), (cA, "NothingTrue1")):
    dC.apply("odam", "UPDATE", {"telegram": _tg}, _oid)
xb.sozlama_qoy(dC, token="sinov", guruh="-1", yoqilgan=True,
               kunlik_vaqt="08:00")

_bugun = _date.today()
_ovq = vz.navbat_turi(dC)
vz.navbat_biriktir(dC, _ovq["id"], cF, _bugun, "19:00", 1)

_km = xb.kunlik_matn(dC, _bugun)
tekshir("kunlik xabarda sana bor", vz.KUNLAR[_bugun.weekday()] in _km)
tekshir("kunlik xabarda vaqt bor", "19:00" in _km)
tekshir("kunlik xabarda @teg bor", "@fsultonoov" in _km)

_v = vz.kun(dC, _bugun)[0]
_em = xb.eslatma_matn(dC, _v)
tekshir("eslatma mas'ulni teg qiladi", "@" in _em)
tekshir("eslatma savol beradi", "bajarildimi?" in _em)

# Ovqat/idish uchun kunlik xabar rol bloki bilan chiqadi: birinchi
# qatorda mas'ulning tegi, keyingisida missiya.
_satrlar = _km.splitlines()
_i = next(i for i, x in enumerate(_satrlar) if "@fsultonoov" in x)
tekshir("oshpaz bloki tegdan boshlanadi",
        _satrlar[_i].index("@") < _satrlar[_i].index(","))
tekshir("oshpaz blokida missiya bor", "issiya" in _satrlar[_i + 1])
tekshir("oshpaz blokida vaqt bor", "19:00" in _satrlar[_i])
tekshir("eslatma tegdan boshlanadi", _em.splitlines()[0].count("@") == 1)

# Iboralar aylanadi, lekin TASODIFIY emas: bir xil urug' — bir xil matn.
tekshir("bir xil kun — bir xil matn", xb.kunlik_matn(dC, _bugun) == _km)
# Sarlavha: [0] sana, [1] bo'sh qator, [2] kirish iborasi.
tekshir("boshqa kun — boshqa ibora",
        any(xb.kunlik_bosh_matn(dC, _bugun + _td(days=i)).splitlines()[2]
            != xb.kunlik_bosh_matn(dC, _bugun).splitlines()[2]
            for i in range(1, 5)))


print("\n── telegram: qachon yuboriladi ──────────────────")


def _paytda(soat, daqiqa=0):
    return _datetime.combine(_bugun, _datetime.min.time()).replace(
        hour=soat, minute=daqiqa)


_turlari = lambda h: sorted({x["turi"] for x in xb.kutilayotgan(dC, h)})
teng("07:00 da hech narsa yo'q", [], _turlari(_paytda(7)))
teng("08:05 da kunlik chiqadi", ["kunlik"], _turlari(_paytda(8, 5)))
teng("19:30 da hali eslatma yo'q (ovqat 20:00 da tugaydi)",
     ["kunlik"], _turlari(_paytda(19, 30)))
teng("20:05 da eslatma ham chiqadi", ["eslatma", "kunlik"],
     _turlari(_paytda(20, 5)))

# Bir marta yuborilgani ikkinchi marta chiqmaydi
for _x in xb.kutilayotgan(dC, _paytda(20, 5)):
    xb.belgila(dC, _x["kalit"])
teng("belgilangandan keyin bo'sh", [], _turlari(_paytda(20, 5)))

# Bajarilgan vazifaga eslatma yo'q
# Kunlik xabar odam boshiga bo'lingani uchun: bugun hali xabar
# olmagan odamga ish qo'shilsa, u O'Z xabarini oladi.
_v2 = vz.qosh(dC, "Musorlarni tashlash", cO, _bugun, "10:00", 30)
teng("yangi odamga eslatma ham, o'z xabari ham",
     ["eslatma", "kunlik"], _turlari(_paytda(11)))
vz.bajar(dC, _v2)
teng("bajarilganiga na eslatma, na xabar", [], _turlari(_paytda(11)))

print("\n── telegram: umumiy rasxod e'loni ───────────────")

_eski = entries.rasxod_qosh(dC, "2026-08-01", "Eski", 90_000, cF)
dC.con.execute("UPDATE rasxod SET yaratilgan='2020-01-01 00:00:00'"
               " WHERE id=?", (_eski,))
tekshir("chegaradan oldingi rasxod e'lon qilinmaydi",
        not any(x["turi"] == "rasxod"
                for x in xb.kutilayotgan(dC, _paytda(12))))

_time.sleep(1.1)   # `yaratilgan` chegaradan keyin bo'lsin
_yangi = entries.rasxod_qosh(dC, _bugun.isoformat(), "Bozorlik", 110_000, cF)
_re = [x for x in xb.kutilayotgan(dC, _paytda(12)) if x["turi"] == "rasxod"]
teng("yangi umumiy rasxod e'lon qilinadi", 1, len(_re))
_rm = _re[0]["matn"]
tekshir("e'londa kim to'lagani bor", "To'ladi: Fayzulloxon" in _rm)
tekshir("e'londa summa bor", money.fmt_som(110_000) in _rm)
tekshir("e'londa ulushlar bor", "Kim qancha ko'taradi" in _rm)
tekshir("e'londa qarzdorlar teg qilingan", "@otabek_33" in _rm)
tekshir("to'lovchining o'zi teg qilinmagan",
        _rm.count("@fsultonoov") == 1)

_shaxsiy = entries.rasxod_qosh(dC, _bugun.isoformat(), "O'zimniki", 5_000,
                               cO, umumiymi=False)
teng("shaxsiy rasxod e'lon qilinmaydi", 1,
     len([x for x in xb.kutilayotgan(dC, _paytda(12))
          if x["turi"] == "rasxod"]))

xb.belgila(dC, _re[0]["kalit"])
teng("e'lon takrorlanmaydi", 0,
     len([x for x in xb.kutilayotgan(dC, _paytda(12))
          if x["turi"] == "rasxod"]))

_uchun = entries.rasxod_qosh(dC, _bugun.isoformat(), "Poyabzal", 300_000,
                             cF, kim_uchun=cO)
_um = [x for x in xb.kutilayotgan(dC, _paytda(12))
       if x["turi"] == "rasxod"][0]["matn"]
tekshir("«boshqa uchun» alohida sarlavha bilan",
        "Boshqa uchun olingan" in _um)

# Sozlanmagan bo'lsa hech narsa yuborilmaydi
xb.sozlama_qoy(dC, yoqilgan=False)
tekshir("o'chirilganda yuborilmaydi",
        xb.yubor_kutilayotgan(dC, _paytda(12)) == [])
xb.sozlama_qoy(dC, yoqilgan=True)

# Token manbada bo'lmasligi SHART
_manba = (SRC / "core" / "xabar.py").read_text(encoding="utf-8")
tekshir("token manba kodda yo'q",
        "api.telegram.org" in _manba and ":AA" not in _manba)


print("\n── telegram: menyu va tugmalar ──────────────────")

# Tugmalar Telegramga chiqadi, ya'ni tarmoq kerak. Shu yerdan keyin
# `_sorov` SOXTA: nima yuborilgani ro'yxatga yozilib boradi.
from core import menyu as mn  # noqa: E402

_yuborilgan_sorovlar = []


def _soxta_sorov(token, metod, **maydonlar):
    _yuborilgan_sorovlar.append((metod, maydonlar))
    return {"message_id": 777}


xb._sorov = _soxta_sorov

_taomlar = mn.royxat(dC)
tekshir("boshlang'ich menyu ekilgan", len(_taomlar) == 5)
tekshir("menyuda Mastava bor", "Mastava" in [t["nom"] for t in _taomlar])

# ── klaviaturalar
_oshpaz_v = xb.oshpaz_vazifasi(dC, _bugun)
tekshir("oshpaz vazifasi topildi", _oshpaz_v is not None)
_kk = xb.kunlik_klaviatura(dC, _bugun)
tekshir("kunlik xabarda menyu tugmasi bor",
        _kk and _kk[0][0][0] == xb.MENYU_TUGMA)
tekshir("menyu tugmasi oshpaz vazifasiga tegishli",
        _kk[0][0][1] == f"menyu:{_oshpaz_v['id']}")

_tk = xb._taom_klaviatura(dC, _oshpaz_v["id"])
tekshir("taomlar ikkitadan qatorga", all(len(q) <= 2 for q in _tk))
tekshir("hamma taom tugmasi bor", sum(len(q) for q in _tk) == len(_taomlar))
# 64 bayt — Telegramning cheki. Oshsa tugma JIMGINA ishlamay qoladi.
tekshir("callback_data 64 baytdan oshmaydi",
        all(len(d.encode()) <= 64 for q in _tk for _, d in q))

# ── «Albatta!» eslatma ostida
_eslatmalar = [x for x in xb.kutilayotgan(dC, _paytda(20, 5))
               if x["turi"] == "eslatma"]
tekshir("eslatma ostida Albatta tugmasi bor",
        all(x["klaviatura"][0][0][0] == xb.ALBATTA_TUGMA
            for x in _eslatmalar) if _eslatmalar else True)


def _bosish(data, kim="fsultonoov"):
    return {"id": "cb1", "data": data,
            "from": {"username": kim},
            "message": {"message_id": 777, "chat": {"id": -1}}}


# ── menyu tanlash
_mastava = [t for t in _taomlar if t["nom"] == "Mastava"][0]
xb.tugmani_ishla(dC, _bosish(f"menyu:{_oshpaz_v['id']}"), "sinov", "-1")
_ochilgan = [m for m in _yuborilgan_sorovlar if m[0] == "editMessageText"][-1]
tekshir("menyu tugmasi ro'yxatni ochadi",
        xb.MENYU_SOROV in _ochilgan[1]["text"])
tekshir("ro'yxat ochilganda taomlar chiqadi",
        "Mastava" in _ochilgan[1]["reply_markup"])

xb.tugmani_ishla(
    dC, _bosish(f"taom:{_oshpaz_v['id']}:{_mastava['id']}"), "sinov", "-1")
teng("tanlangan taom vazifaga yozildi", "Mastava",
     vz.bitta(dC, _oshpaz_v["id"])["menyu"])
tekshir("kunlik xabarda taom ko'rinadi",
        "Mastava" in xb.kunlik_matn(dC, _bugun))
tekshir("eslatmada ham taom ko'rinadi",
        "Mastava" in xb.eslatma_matn(dC, vz.bitta(dC, _oshpaz_v["id"])))

# Boshqa odam bosa — hech narsa o'zgarmaydi.
xb.tugmani_ishla(dC, _bosish(f"taom:{_oshpaz_v['id']}:{_taomlar[0]['id']}",
                             kim="NothingTrue1"), "sinov", "-1")
teng("begona odam menyuni o'zgartira olmaydi", "Mastava",
     vz.bitta(dC, _oshpaz_v["id"])["menyu"])

# ── «Albatta!» vazifani belgilaydi
_yuv_id = vz._ergash_vazifa(dC, vz.bitta(dC, _oshpaz_v["id"]))
xb.tugmani_ishla(dC, _bosish(f"bajar:{_oshpaz_v['id']}"), "sinov", "-1")
teng("«Albatta!» oshpaz vazifasini belgiladi", vz.BAJARILDI,
     vz.bitta(dC, _oshpaz_v["id"])["holat"])
tekshir("belgilangandan keyin tugma olib tashlanadi",
        [m for m in _yuborilgan_sorovlar
         if m[0] == "editMessageText"][-1][1].get("reply_markup") is None)

if _yuv_id:
    _yuv = vz.bitta(dC, _yuv_id["id"] if hasattr(_yuv_id, "keys") else _yuv_id)
    _yuvuvchi_odam = dC.q1("SELECT telegram FROM odam WHERE id=?",
                           _yuv["odam_id"])["telegram"]
    xb.tugmani_ishla(dC, _bosish(f"bajar:{_yuv['id']}", kim=_yuvuvchi_odam),
                     "sinov", "-1")
    teng("«Albatta!» yuvuvchi vazifasini ham belgiladi", vz.BAJARILDI,
         vz.bitta(dC, _yuv["id"])["holat"])

# Egasi bo'lmagan odam bosa — vazifa ochiq qoladi.
_boshqa = vz.qosh(dC, "Musorlarni tashlash", cA, _bugun, "09:00", 30)
xb.tugmani_ishla(dC, _bosish(f"bajar:{_boshqa}", kim="fsultonoov"),
                 "sinov", "-1")
teng("begona odam vazifani belgilay olmaydi", vz.OCHIQ,
     vz.bitta(dC, _boshqa)["holat"])

# ── offset: bir bosilish IKKI MARTA hisoblanmaydi
xb.offsetni_sur(dC, [{"update_id": 41}, {"update_id": 42}])
teng("offset oxirgisidan keyingiga suriladi", "43",
     dC.sozlama(xb.K_OFFSET, ""))

# Menyu bo'sh bo'lsa tugma ham yo'q — bosiladigan narsa qolmasin.
for _t in mn.royxat(dC):
    mn.ochir(dC, _t["id"])
tekshir("menyu bo'sh bo'lsa kunlik tugmasi yo'q",
        xb.kunlik_klaviatura(dC, _bugun) is None)
for _nom in dbm.Db.MENYU:
    mn.qosh(dC, _nom)
teng("o'chirilgan taom qaytadan qo'shiladi", len(dbm.Db.MENYU),
     len(mn.royxat(dC)))


print("\n── telegram: kunlik xabar bo'lak-bo'lak ─────────")

# Sarlavha alohida, har odam alohida — bitta uyum EMAS.
_bosh = xb.kunlik_bosh_matn(dC, _bugun)
tekshir("sarlavhada sana bor", vz.KUNLAR[_bugun.weekday()] in _bosh)
tekshir("sarlavhada hech kim teg qilinmaydi", "@" not in _bosh)

_bolaklar = xb.kunlik_bloklar(dC, _bugun)
tekshir("har odamga bitta bo'lak",
        len(_bolaklar) == len({b["odam_id"] for b in _bolaklar}))
tekshir("bo'lakda faqat o'z odami teg qilinadi",
        all(sum(x.count("@") for x in [b["matn"]]) <= 2 for b in _bolaklar))
for _b in _bolaklar:
    _tg = dC.q1("SELECT telegram FROM odam WHERE id=?",
                _b["odam_id"])["telegram"]
    tekshir(f"bo'lak «@{_tg}» ga tegishli", f"@{_tg}" in _b["matn"])

# Menyu tugmasi FAQAT oshpazning bo'lagida.
_tugmali = [b for b in _bolaklar if b["klaviatura"]]
tekshir("menyu tugmasi bitta bo'lakda", len(_tugmali) == 1)
tekshir("menyu tugmasi oshpazniki",
        _tugmali[0]["odam_id"] == xb.oshpaz_vazifasi(dC, _bugun)["odam_id"])

# Har bo'lakning O'Z kaliti bor: bittasi yiqilsa qolganiga tegmaydi.
# Yuqoridagi testlar hammasini yuborilgan/bajarilgan qilib qo'ygan —
# shu yerda kunni qaytadan ochamiz.
dC.con.execute("DELETE FROM yuborilgan")
for _r in vz.kun(dC, _bugun):
    if _r["holat"] == vz.BAJARILDI:
        vz.bajar(dC, _r["id"], False)

_kalitlar = [x["kalit"] for x in xb.kutilayotgan(dC, _paytda(8, 5))
             if x["turi"] == "kunlik"]
tekshir("kun qaytadan ochilganda hamma bo'lak chiqadi",
        len(_kalitlar) == 1 + len(xb.kunlik_bloklar(dC, _bugun)))
tekshir("kalitlar takrorlanmaydi", len(_kalitlar) == len(set(_kalitlar)))
tekshir("sarlavha birinchi ketadi",
        _kalitlar[0] == f"kunlik:{_bugun.isoformat()}")

# Bittasi yuborilgan bo'lsa faqat QOLGANI qayta chiqadi.
xb.belgila(dC, _kalitlar[0], 100)
_qolgan = [x["kalit"] for x in xb.kutilayotgan(dC, _paytda(8, 5))
           if x["turi"] == "kunlik"]
teng("yuborilgani ikkinchi marta chiqmaydi", _kalitlar[1:], _qolgan)

print("\n── general uborka: haftalik navbat ──────────────")

dG = dbm.Db(_TMP / "bG.db", zaxirasiz=True)
gF = entries.odam_qosh(dG, "Fayzulloxon")
gO = entries.odam_qosh(dG, "Otabek")
gA = entries.odam_qosh(dG, "Abbosxon")

_ub = vz.uborka_turlari(dG)
teng("uchta katta ish ekildi", 3, len(_ub))
teng("birinchisi — oshxona", "Oshxonani tozalash", _ub[0]["nom"])
tekshir("uborka ishi navbatli ish EMAS", not any(t["navbat"] for t in _ub))
teng("uborka kuni — yakshanba", 6, vz.uborka_kuni(dG))

# Qadamlar: nom emas, TURGA bog'langan ro'yxat
teng("oshxonaning qadamlari ekildi", 5, len(vz.qadamlar(dG, _ub[0]["id"])))
tekshir("uy tozalashda pilesos bor",
        "Pilesos qilish" in vz.qadam_nomlari(dG, _ub[2]["id"]))
_q = vz.qadam_qosh(dG, _ub[0]["id"], "Choynakni tozalash")
teng("qadam qo'shildi", 6, len(vz.qadamlar(dG, _ub[0]["id"])))
tekshir("bir xil qadam ikki marta qo'shilmaydi",
        _yiqiladimi(lambda: vz.qadam_qosh(dG, _ub[0]["id"],
                                          "choynakni tozalash")))
vz.qadam_ochir(dG, _q)
teng("qadam ro'yxatdan chiqdi", 5, len(vz.qadamlar(dG, _ub[0]["id"])))
tekshir("qadam rostdan o'chmaydi",
        dG.q1("SELECT ochirilgan FROM ish_qadam WHERE id=?", _q)["ochirilgan"] == 1)

# ── reja: kim qaysi ishni qiladi
# 2026-09-05 — shanba, demak birinchi uborka ertasi (yakshanba).
_g0 = vz.uborka_sanasi(dG, _date(2026, 9, 5))
teng("uborka yakshanbaga tushadi", _date(2026, 9, 6), _g0)
teng("shanbadan keyingi yakshanba", 6, _g0.weekday())
teng("uborka kuni bo'lsa o'sha kun olinadi", _g0,
     vz.uborka_sanasi(dG, _g0))

_gr = vz.uborka_rejasi(dG, _date(2026, 9, 5), gF, 3)
teng("3 hafta × 3 ish", 9, len(_gr))


def _uborka(kun):
    return {x["nom"]: x["odam"] for x in _gr if x["sana"] == kun}


_h1 = _uborka(_g0)
teng("1-hafta: oshxona Fayzulloxonda", "Fayzulloxon",
     _h1["Oshxonani tozalash"])
teng("1-hafta: sanuzel Otabekda", "Otabek", _h1["Sanuzelni tozalash"])
teng("1-hafta: uy Abbosxonda", "Abbosxon", _h1["Umumiy uyni tozalash"])

_h2 = _uborka(_g0 + _td(days=7))
teng("2-hafta: oshxona Otabekka o'tdi", "Otabek",
     _h2["Oshxonani tozalash"])
teng("2-hafta: sanuzel Abbosxonga o'tdi", "Abbosxon",
     _h2["Sanuzelni tozalash"])
teng("2-hafta: uy Fayzulloxonga o'tdi", "Fayzulloxon",
     _h2["Umumiy uyni tozalash"])

# Har hafta har kimga BITTA ish tushadi — hech kim ikki ish qilmaydi
for _n, _kun in enumerate((_g0, _g0 + _td(days=7), _g0 + _td(days=14))):
    teng(f"{_n + 1}-haftada har kimga bitta ish", 3,
         len(set(_uborka(_kun).values())))

# Uch haftada har kim har ishni AYNAN bir marta qiladi
_juftlar = {(x["odam"], x["nom"]) for x in _gr}
teng("uch haftada 9 ta boshqacha juftlik", 9, len(_juftlar))

_gr_a = {x["nom"]: x["odam"]
         for x in vz.uborka_rejasi(dG, _date(2026, 9, 5), gA, 1)}
teng("boshqa odamdan boshlansa navbat undan yuradi", "Abbosxon",
     _gr_a["Oshxonani tozalash"])
teng("undan keyingisi ro'yxat boshiga qaytadi", "Fayzulloxon",
     _gr_a["Sanuzelni tozalash"])

tekshir("noto'g'ri odam rad etiladi",
        _yiqiladimi(lambda: vz.uborka_rejasi(dG, _g0, 999, 1)))
tekshir("nol hafta rad etiladi",
        _yiqiladimi(lambda: vz.uborka_rejasi(dG, _g0, gF, 0)))

# ── bazaga yozish: bitta undo qadami
_n = vz.uborka_biriktir(dG, _date(2026, 9, 5), gF, 2)
teng("uborka bazaga yozildi", 6, _n)
teng("birinchi yakshanbada 3 ta vazifa", 3, len(vz.kun(dG, _g0)))
tekshir("uborka bitta undo qadami",
        "uborka" in (dG.oxirgi_guruh() or ("", ""))[1].lower())
dG.undo()
teng("undo butun uborkani oldi", 0, len(vz.kun(dG, _g0)))
dG.redo()
teng("redo qaytardi", 3, len(vz.kun(dG, _g0)))

# Uborka kuni o'zgarsa reja ham ko'chadi
vz.uborka_kuni_qoy(dG, 5)          # shanba
teng("kun saqlandi", 5, vz.uborka_kuni(dG))
teng("reja shanbaga ko'chdi", 5,
     vz.uborka_rejasi(dG, _date(2026, 9, 5), gF, 1)[0]["sana"].weekday())
vz.uborka_kuni_qoy(dG, 6)
tekshir("hafta kuni 0..6 dan tashqarida bo'lmaydi",
        _yiqiladimi(lambda: vz.uborka_kuni_qoy(dG, 7)))

# Ish uborkadan chiqarilsa rejadan ham chiqadi
vz.tur_haftalik_qoy(dG, _ub[2]["id"], False)
teng("uborkada ikkita ish qoldi", 2, len(vz.uborka_turlari(dG)))
teng("reja ham qisqardi", 2,
     len(vz.uborka_rejasi(dG, _date(2026, 9, 5), gF, 1)))
vz.tur_haftalik_qoy(dG, _ub[2]["id"], True)

print("\n── general uborka: guruhga ketadigan xabar ──────")

dG.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, gF)
_gm = xb.kunlik_odam_matn(dG, _g0, gF)
tekshir("uborka bloki teg bilan boshlanadi", "@fsultonoov" in _gm)
tekshir("xabarda ishning nomi bor", "Oshxonani tozalash" in _gm)
tekshir("xabarda qadamlar ro'yxati bor",
        "Rakovina va kranni tozalash" in _gm)
tekshir("qadam nuqta bilan yoziladi", "   • " in _gm)
teng("beshta qadam beshta qator", 5, _gm.count("   • "))

_gm_o = xb.kunlik_odam_matn(dG, _g0, gO)
tekshir("boshqa odam faqat o'z ishini ko'radi",
        "Sanuzelni tozalash" in _gm_o and "Oshxonani tozalash" not in _gm_o)
tekshir("uch odam uch xil ibora oladi",
        len({xb.kunlik_odam_matn(dG, _g0, x).split("\n")[0][:20]
             for x in (gF, gO, gA)}) > 1)

_gm2 = xb.kunlik_odam_matn(dG, _g0, gF)
teng("bir xil kun — bir xil matn", _gm, _gm2)

_gv = [r for r in vz.kun(dG, _g0) if r["odam_id"] == gF][0]
_ge = xb.eslatma_matn(dG, _gv)
tekshir("eslatma uborka ohangida", "general uborka" in _ge.lower())
tekshir("eslatmada ish nomi bor", "Oshxonani tozalash" in _ge)

vz.bajar(dG, _gv["id"])
_gm3 = xb.kunlik_odam_matn(dG, _g0, gF)
tekshir("bajarilgach rahmat aytiladi", "Rahmat" in _gm3)
tekshir("bajarilgach qadamlar takrorlanmaydi", "   • " not in _gm3)

# Qadamsiz ish ham ishlaydi — xabar shunchaki ro'yxatsiz chiqadi
for _x in vz.qadamlar(dG, _ub[1]["id"]):
    vz.qadam_ochir(dG, _x["id"])
_gm4 = xb.kunlik_odam_matn(dG, _g0, gO)
tekshir("qadamsiz uborka ishi ham xabarga tushadi",
        "Sanuzelni tozalash" in _gm4)
tekshir("qadamsiz ishda bo'sh ro'yxat chizilmaydi", "   • " not in _gm4)

tekshir("uborka kitob tengligiga tegmaydi", ledger.audit(dG)["toza"])


print("\n── shaxsiy vazifa: guruhga emas, egasiga ───────")

dS = dbm.Db(_TMP / "bS.db", zaxirasiz=True)
sF = entries.odam_qosh(dS, "Fayzulloxon")
sO = entries.odam_qosh(dS, "Otabek")
dS.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, sF)
dS.apply("odam", "UPDATE", {"telegram": "otabek_33"}, sO)

_skun = _date(2026, 9, 10)
_kitob = vz.tur_qosh(dS, "Kitob o'qish", 30)
_musor = vz.tur_qosh(dS, "Musorni tashlash", 15)
teng("boshida hamma ish umumiy", 0, len(vz.shaxsiy_turlari(dS)))
vz.tur_shaxsiy_qoy(dS, _kitob, True)
_darhol = vz.tur_qosh(dS, "Dori ichish", 5, shaxsiy=True)
tekshir("yangi tur darhol shaxsiy bo'lib tug'iladi",
        bool(vz.tur_bitta(dS, _darhol)["shaxsiy"]))
tekshir("va bir amalda — undo ikkalasini oladi",
        (dS.undo() or "") and not vz.tur_bitta(dS, _darhol))
teng("kitob o'qish shaxsiy bo'ldi", 1, len(vz.shaxsiy_turlari(dS)))
tekshir("shaxsiy nomlar to'plamida",
        "Kitob o'qish" in vz.shaxsiy_nomlari(dS))

_v_kitob = vz.biriktir(dS, _kitob, sF, _skun, "21:00")
_v_musor = vz.biriktir(dS, _musor, sF, _skun, "08:00")

# ── guruh xabari shaxsiy ishni KO'RMAYDI
_gmatn = xb.kunlik_odam_matn(dS, _skun, sF)
tekshir("guruhda umumiy ish bor", "Musorni tashlash" in _gmatn)
tekshir("guruhda shaxsiy ish YO'Q", "Kitob o'qish" not in _gmatn)

# ── shaxsiy xabar: chat raqami bo'lmasa yuborilmaydi
teng("chat raqami hali yo'q", None, xb.odam_chati(dS, sF))
teng("chatsiz odam shaxsiy blokka tushmaydi", 0,
     len(xb.shaxsiy_bloklar(dS, _skun)))
tekshir("sozlamalar ogohlantiradi",
        sF in [r["id"] for r in xb.dm_yoqmaganlar(dS)])

# ── odam botga yozdi → chat raqami eslab qolinadi
_yang = {"update_id": 1, "message": {
    "chat": {"id": 5551234, "type": "private"},
    "from": {"username": "fsultonoov"}, "text": "/start"}}
teng("chat raqami odamga bog'landi", sF, xb._chatni_eslab_qol(dS, _yang))
teng("chat raqami saqlandi", 5551234, xb.odam_chati(dS, sF))
teng("ikkinchi marta qayta yozmaydi", None, xb._chatni_eslab_qol(dS, _yang))
teng("endi ogohlantirishda yo'q", False,
     sF in [r["id"] for r in xb.dm_yoqmaganlar(dS)])

_guruh_yang = {"update_id": 2, "message": {
    "chat": {"id": -100999, "type": "supergroup"},
    "from": {"username": "fsultonoov"}, "text": "salom"}}
teng("guruh chati bog'lanmaydi", None, xb._chatni_eslab_qol(dS, _guruh_yang))
_notanish = {"update_id": 3, "message": {
    "chat": {"id": 777, "type": "private"},
    "from": {"username": "kimdir"}, "text": "salom"}}
teng("notanish odam bog'lanmaydi", None, xb._chatni_eslab_qol(dS, _notanish))

# ── endi shaxsiy xabar tayyor
_bloklar = xb.shaxsiy_bloklar(dS, _skun)
teng("bitta shaxsiy blok", 1, len(_bloklar))
teng("shaxsiy blok o'z chatiga ketadi", 5551234, _bloklar[0]["chat"])
_smatn = _bloklar[0]["matn"]
tekshir("shaxsiy xabarda kitob bor", "Kitob o'qish" in _smatn)
tekshir("shaxsiy xabarda umumiy ish yo'q", "Musorni tashlash" not in _smatn)
tekshir("shaxsiy xabar qulf belgisi bilan", _smatn.startswith("🔒"))
tekshir("shaxsiy xabarda guruh tegi yo'q", "@" not in _smatn)
tekshir("«Albatta!» tugmasi bor",
        xb.shaxsiy_klaviatura(dS, _skun, sF) is not None)

teng("boshqa odamda shaxsiy ish yo'q", None,
     xb.shaxsiy_matn(dS, _skun, sO))

# ── kutilayotgan: qaysi biri qayerga
xb.sozlama_qoy(dS, token="T", guruh="-100999", yoqilgan=True,
               kunlik_vaqt="08:00")
_hozir = _datetime(2026, 9, 10, 9, 0)
_kut = xb.kutilayotgan(dS, _hozir)
_shaxsiy = [x for x in _kut if x["turi"] == "shaxsiy"]
teng("bitta shaxsiy xabar kutilyapti", 1, len(_shaxsiy))
teng("u shaxsiy chatga ketadi", 5551234, _shaxsiy[0]["chat"])
_kunlik = [x for x in _kut if x["turi"] == "kunlik"]
tekshir("kunlik xabarlar guruhga ketadi",
        all(x.get("chat") is None for x in _kunlik))
tekshir("kunlik xabarda shaxsiy ish ko'rinmaydi",
        all("Kitob o'qish" not in x["matn"] for x in _kunlik))

# Eslatma: umumiy ish guruhga, shaxsiy ish shaxsiy chatga
_esl = {x["vazifa_id"]: x for x in _kut if x["turi"] == "eslatma"}
teng("umumiy ish eslatmasi guruhga", None, _esl[_v_musor].get("chat"))
_hozir2 = _datetime(2026, 9, 10, 22, 0)
_esl2 = {x["vazifa_id"]: x for x in xb.kutilayotgan(dS, _hozir2)
         if x["turi"] == "eslatma"}
teng("shaxsiy ish eslatmasi shaxsiy chatga", 5551234,
     _esl2[_v_kitob]["chat"])

# Chat raqami o'chsa — shaxsiy eslatma umuman yuborilmaydi
dS.apply("odam", "UPDATE", {"tg_chat": None}, sF)
_kut3 = xb.kutilayotgan(dS, _hozir2)
tekshir("chatsiz shaxsiy eslatma yuborilmaydi",
        all(x.get("vazifa_id") != _v_kitob for x in _kut3))
tekshir("chatsiz shaxsiy ish guruhga TUSHMAYDI",
        all("Kitob o'qish" not in x["matn"] for x in _kut3))
dS.apply("odam", "UPDATE", {"tg_chat": 5551234}, sF)

# ── umumiyga qaytarilsa yana guruhda
vz.tur_shaxsiy_qoy(dS, _kitob, False)
tekshir("umumiyga qaytdi", "Kitob o'qish" in xb.kunlik_odam_matn(dS, _skun, sF))
teng("shaxsiy blok qolmadi", 0, len(xb.shaxsiy_bloklar(dS, _skun)))
vz.tur_shaxsiy_qoy(dS, _kitob, True)

# Kunning HAMMA ishi shaxsiy bo'lsa, guruh sarlavhasi bo'sh kun deydi
vz.ochir(dS, _v_musor)
tekshir("hamma ish shaxsiy bo'lsa guruhga bo'sh kun",
        "vazifa" in xb.kunlik_bosh_matn(dS, _skun).lower()
        or "bo'sh" in xb.kunlik_bosh_matn(dS, _skun).lower())
teng("guruhga odam bloki ketmaydi", 0, len(xb.kunlik_bloklar(dS, _skun)))
teng("shaxsiy esa baribir ketadi", 1, len(xb.shaxsiy_bloklar(dS, _skun)))

tekshir("shaxsiy vazifa kitob tengligiga tegmaydi", ledger.audit(dS)["toza"])


print("\n── hisobot: umumiy rasxod va ulush ──────────────")

from core import reports  # noqa: E402

dR = dbm.Db(_TMP / "bR.db", zaxirasiz=True)
rF = entries.odam_qosh(dR, "Fayzulloxon")
rO = entries.odam_qosh(dR, "Otabek")
rA = entries.odam_qosh(dR, "Abbosxon")
_tid = dR.q1("SELECT id FROM turi WHERE nom='Bozorlik'")["id"]
entries.rasxod_qosh(dR, "2026-09-01", "Bozorlik", 300_000, rF, True, _tid)
entries.rasxod_qosh(dR, "2026-09-02", "Kommunal", 150_000, rO, True, _tid)
entries.rasxod_qosh(dR, "2026-09-03", "Poyabzal", 500_000, rA, False, _tid)

_uh = reports.umumiy_rasxod_html(dR, "2026-09-01", "2026-09-30")
_um = _uh.read_text(encoding="utf-8")
tekshir("umumiy hisobotda umumiy rasxod bor", "Bozorlik" in _um)
tekshir("umumiy hisobotda SHAXSIY rasxod yo'q", "Poyabzal" not in _um)
tekshir("umumiy hisobotda jami to'g'ri", money.fmt(450_000) in _um)

_sh = reports.shaxsiy_ulush_html(dR, "2026-09-01", "2026-09-30")
_sm = _sh.read_text(encoding="utf-8")
tekshir("ulush hisobotida uchala odam ham bor",
        all(n in _sm for n in ("Fayzulloxon", "Otabek", "Abbosxon")))
tekshir("ulush hisobotida shaxsiy rasxod yo'q", "Poyabzal" not in _sm)
# Har kimning ulushi 450 000 / 3 = 150 000 — uchta xulosa kartasi.
# (Raqamning o'zi jadvallarda ham uchraydi, shuning uchun aynan
# karta sanaladi.)
teng("450 000 uchga teng bo'lindi", 3,
     _sm.count(f"<div class='katta'>{money.fmt(150_000)}"))

_sh1 = reports.shaxsiy_ulush_html(dR, "2026-09-01", "2026-09-30", rF)
tekshir("bitta odamning hisoboti faqat uniki",
        "Fayzulloxon" in _sh1.read_text(encoding="utf-8"))
tekshir("umumiy rasxod Excel yoziladi",
        reports.umumiy_rasxod_excel(dR, "2026-09-01", "2026-09-30").exists())
tekshir("ulush Excel yoziladi",
        reports.shaxsiy_ulush_excel(dR, "2026-09-01", "2026-09-30").exists())
tekshir("hisobot kitob tengligiga tegmaydi", ledger.audit(dR)["toza"])


print("\n── eslatmani kechiktirish ───────────────────────")

dK = dbm.Db(_TMP / "bK.db", zaxirasiz=True)
kF = entries.odam_qosh(dK, "Fayzulloxon")
entries.odam_qosh(dK, "Otabek")
dK.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, kF)
xb.sozlama_qoy(dK, token="T", guruh="-100", yoqilgan=True, kunlik_vaqt="08:00")
_kbugun = _date.today()
_kv = vz.qosh(dK, "Musorlarni tashlash", kF, _kbugun, "09:00", 30)

_soat10 = _datetime.combine(_kbugun, _datetime.min.time()).replace(hour=10)
_esl = [x for x in xb.kutilayotgan(dK, _soat10) if x["turi"] == "eslatma"]
teng("vaqti tugagach eslatma chiqadi", 1, len(_esl))
_tugmalar = [t[0] for qat in _esl[0]["klaviatura"] for t in qat]
teng("ikkita javob tugmasi", 2, len(_tugmalar))
tekshir("«Albatta!» bor", any("Albatta" in t for t in _tugmalar))
tekshir("«Hali yo'q» bor", any("Hali yo'q" in t for t in _tugmalar))

teng("birlamchi kechiktirish", [10, 30, 60],
     xb.kechiktirish_variantlari(dK))
_kk = xb.kechiktirish_klaviatura(dK, _kv)
_kmatn = [t[0] for qat in _kk for t in qat]
teng("uchta variant", 3, len(_kmatn))
tekshir("«1 soatdan keyin» deb yoziladi", "1 soatdan keyin" in _kmatn)
tekshir("«10 daqiqadan keyin» deb yoziladi", "10 daqiqadan keyin" in _kmatn)
for _qat in _kk:
    for _t, _data in _qat:
        tekshir(f"callback_data 64 baytdan oshmaydi ({_data})",
                len(_data.encode("utf-8")) <= 64)

xb.belgila(dK, _esl[0]["kalit"], 111)
teng("belgilangach qayta chiqmaydi", 0,
     len([x for x in xb.kutilayotgan(dK, _soat10) if x["turi"] == "eslatma"]))

vz.kechiktir(dK, _kv, 30, _soat10)
tekshir("kechiktirilgan deb belgilandi",
        vz.kechiktirilganmi(vz.bitta(dK, _kv), _soat10))
teng("kechiktirilgan payt eslatma yo'q", 0,
     len([x for x in xb.kutilayotgan(dK, _soat10) if x["turi"] == "eslatma"]))
_soat11 = _soat10 + _td(hours=1)
_esl2 = [x for x in xb.kutilayotgan(dK, _soat11) if x["turi"] == "eslatma"]
teng("vaqt kelgach eslatma QAYTA chiqadi", 1, len(_esl2))
tekshir("kaliti boshqacha — birinchisi to'sib qo'ymaydi",
        _esl2[0]["kalit"] != _esl[0]["kalit"])
tekshir("kechiktirish SQLite formatida (orasida bo'sh joy)",
        "T" not in (vz.bitta(dK, _kv)["kechiktirildi"] or "T"))
vz.bajar(dK, _kv)
teng("bajarilgach kechiktirish tozalanadi", None,
     vz.bitta(dK, _kv)["kechiktirildi"])
tekshir("nol daqiqa rad etiladi",
        _yiqiladimi(lambda: vz.kechiktir(dK, _kv, 0)))

xb.kechiktirish_qoy(dK, [5, 15])
teng("variantlar saqlandi", [5, 15], xb.kechiktirish_variantlari(dK))
dK.sozlama_qoy(xb.K_KECHIKTIRISH, "buzuq")
teng("buzuq yozuv birlamchiga qaytadi", [10, 30, 60],
     xb.kechiktirish_variantlari(dK))


print("\n── xabar namunasi (oldindan ko'rsatish) ─────────")

_nam = xb.tur_namunasi(dK, vz.turlar(dK)[0]["id"], kF, "19:00")
tekshir("namuna qaytdi", _nam is not None)
teng("kunlik soat sozlamadan", "08:00", _nam["kunlik_vaqt"])
tekshir("eslatma vaqti = boshlanish + davomiylik",
        _nam["eslatma_vaqt"] is not None)
tekshir("umumiy ish guruhga", _nam["qayerga"] == "Uy guruhi")
tekshir("namuna matni haqiqiy funksiyadan",
        _nam["tur"]["nom"] in _nam["eslatma"])
teng("namuna bazaga yozmaydi", 0,
     len([r for r in vz.kun(dK, _date.today())
          if r["nom"] == _nam["tur"]["nom"] and r["id"] == 0]))

_kitob_t = vz.tur_qosh(dK, "Kitob o'qish", 30, shaxsiy=True)
_nam2 = xb.tur_namunasi(dK, _kitob_t, kF)
tekshir("shaxsiy ish shaxsiy suhbatga",
        _nam2["qayerga"] == "Shaxsiy suhbat")
tekshir("chat yo'q — tayyor emas deb ogohlantiradi", not _nam2["tayyormi"])


print("\n── odatlar (streak) va yutuq ────────────────────")

dO = dbm.Db(_TMP / "bO.db", zaxirasiz=True)
oF = entries.odam_qosh(dO, "Fayzulloxon")
oO = entries.odam_qosh(dO, "Otabek")
dO.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, oF)
_kitob = vz.tur_qosh(dO, "Kitob o'qish", 30)
_obugun = _date.today()

teng("boshida odat yo'q", 0, len(vz.streaklar(dO)))
_sid = vz.streak_qosh(dO, oF, _kitob, 7, _obugun - _td(days=10))
teng("odat qo'shildi", 1, len(vz.streaklar(dO)))
tekshir("bir odamga bir ish uchun ikkita odat bo'lmaydi",
        _yiqiladimi(lambda: vz.streak_qosh(dO, oF, _kitob, 7)))
tekshir("nishon 7/14/21/28 dan biri bo'lishi kerak",
        _yiqiladimi(lambda: vz.streak_qosh(dO, oO, _kitob, 9)))

teng("hech narsa bajarilmagan — 0 kun", 0,
     vz.streak_kunlari(dO, oF, _kitob, _obugun))
for _i in range(6, 0, -1):
    vz.bajar(dO, vz.qosh(dO, "Kitob o'qish", oF,
                         _obugun - _td(days=_i), "21:00", 30))
_h = vz.streak_holati(dO, vz.streaklar(dO)[0], _obugun)
teng("6 kun ketma-ket", 6, _h["kun"])
teng("bir kun qoldi", 1, _h["qoldi"])
tekshir("hali bajarilmagan", not _h["bajarildi"])
teng("yutuq hali yo'q", 0, len(vz.yutuqlar(dO)))

# Bugun hali bajarilmagan bo'lsa sanoq UZILMAYDI — kun tugamagan
teng("bugun bo'sh bo'lsa ham streak turadi", 6,
     vz.streak_kunlari(dO, oF, _kitob, _obugun))

_v7 = vz.qosh(dO, "Kitob o'qish", oF, _obugun, "21:00", 30)
vz.bajar(dO, _v7)
_h = vz.streak_holati(dO, vz.streaklar(dO)[0], _obugun)
teng("7 kun bo'ldi", 7, _h["kun"])
tekshir("nishon qo'lga kiritildi", _h["bajarildi"])
_y = vz.yutuqlar(dO)
teng("bitta yutuq berildi", 1, len(_y))
teng("yutuq nomi", vz.YUTUQ_IRODA, _y[0]["nom"])
tekshir("yutuq izohida ish va kun bor",
        "Kitob o'qish" in _y[0]["izoh"] and "7" in _y[0]["izoh"])
vz.yutuqlarni_tekshir(dO, _obugun)
teng("yutuq IKKINCHI marta berilmaydi", 1, len(vz.yutuqlar(dO)))

_ym = xb.yutuq_matn(dO, _y[0])
tekshir("guruh tabrigida teg bor", "@fsultonoov" in _ym)
tekshir("guruh tabrigida yutuq nomi bor", vz.YUTUQ_IRODA in _ym)
tekshir("guruh tabrigida kun soni bor", "7 kun" in _ym)
xb.sozlama_qoy(dO, token="T", guruh="-100", yoqilgan=True, kunlik_vaqt="08:00")
_kut = [x for x in xb.kutilayotgan(dO) if x["turi"] == "yutuq"]
teng("yutuq guruhga yuborilishi kutilyapti", 1, len(_kut))
xb.belgila(dO, _kut[0]["kalit"], 5)
teng("bir marta e'lon qilinadi", 0,
     len([x for x in xb.kutilayotgan(dO) if x["turi"] == "yutuq"]))

# Undo: bajarish ham, yutuq ham BIRGA qaytadi
dO.undo()
teng("undo yutuqni ham oldi", 0, len(vz.yutuqlar(dO)))
teng("undo streakni ham qaytardi", 6,
     vz.streak_kunlari(dO, oF, _kitob, _obugun))
dO.redo()
teng("redo yutuqni qaytardi", 1, len(vz.yutuqlar(dO)))

# Uzilish: o'rtadagi kun bajarilmagan bo'lsa sanoq qaytadan boshlanadi
_ozgan = [r for r in vz.kun(dO, _obugun - _td(days=3))
          if r["nom"] == "Kitob o'qish"][0]
vz.bajar(dO, _ozgan["id"], False)
teng("o'rtada uzilsa sanoq qisqaradi", 3,
     vz.streak_kunlari(dO, oF, _kitob, _obugun))
tekshir("lekin qo'lga kiritilgan yutuq QOLADI", len(vz.yutuqlar(dO)) == 1)

vz.streak_ochir(dO, _sid)
teng("odat to'xtatildi", 0, len(vz.streaklar(dO)))
tekshir("yutuq baribir joyida", len(vz.yutuqlar(dO)) == 1)
tekshir("odat kitob tengligiga tegmaydi", ledger.audit(dO)["toza"])


# ══════════════════════════════════════════ dars jadvali (EduPage)
#
# Tarmoqqa CHIQMAYDI: `dars.darslar()` va `dars.sinxronla()` tayyor
# JSON ustida ishlaydi, shuning uchun butun mantiq shu yerda soxta
# jadval bilan tekshiriladi.

print("\n── dars jadvali ─────────────────────────────────────────────")

from core import dars  # noqa: E402


def _tt(kartalar) -> dict:
    """EduPage javobiga o'xshash eng kichik jadval."""
    def jad(nom, qatorlar):
        return {"id": nom, "data_rows": qatorlar}
    return {"r": {"dbiAccessorRes": {"tables": [
        jad("days", [{"id": str(i), "name": n} for i, n in enumerate(
            ["Mo", "Tu", "We", "Th", "Fr", "Sa"])]),
        jad("periods", [
            {"id": "4", "period": "4", "starttime": "14:20", "endtime": "15:40"},
            {"id": "5", "period": "5", "starttime": "15:50", "endtime": "17:10"},
        ]),
        jad("classes", [{"id": "c1", "name": "SE-25"},
                        {"id": "c2", "name": "SE-24"}]),
        jad("subjects", [{"id": "s1", "name": "Databases (lec)"},
                         {"id": "s2", "name": "OOP (lec)"}]),
        jad("teachers", [{"id": "t1", "name": "ABDUMANNOPOVA MA'MURA"}]),
        jad("classrooms", [{"id": "r1", "name": "GREEN HALL"},
                           {"id": "r2", "name": "404AB"}]),
        jad("lessons", [
            {"id": "l1", "subjectid": "s1", "teacherids": ["t1"],
             "classids": ["c1"]},
            {"id": "l2", "subjectid": "s2", "teacherids": ["t1"],
             "classids": ["c2"]},          # boshqa guruh — tegmasligi kerak
        ]),
        jad("cards", kartalar),
    ]}}}


_BOSHI = _date(2026, 9, 7)          # dushanba
_MON5 = {"id": "k1", "lessonid": "l1", "period": "5", "days": "100000",
         "classroomids": ["r1"]}
_WED4 = {"id": "k2", "lessonid": "l1", "period": "4", "days": "001000",
         "classroomids": ["r1"]}
_BOSHQA = {"id": "k3", "lessonid": "l2", "period": "4", "days": "010000",
           "classroomids": ["r2"]}

teng("yakshanbadan boshlangan jadval dushanbaga suriladi",
     _BOSHI, dars.hafta_boshi("2026-09-06"))
teng("dushanbadan boshlangani joyida qoladi",
     _BOSHI, dars.hafta_boshi("2026-09-07"))

_d = dars.darslar(_tt([_MON5, _WED4, _BOSHQA]), "SE-25", _BOSHI)
teng("faqat o'z guruhining darslari olinadi", 2, len(_d))
teng("kun bitmaskadan to'g'ri chiqadi", _date(2026, 9, 7), _d[0]["sana"])
teng("ikkinchisi chorshanba", _date(2026, 9, 9), _d[1]["sana"])
teng("davomiylik paradan hisoblanadi", 80, _d[0]["davomiylik"])
teng("kalit sana va paradan quriladi", "dars:2026-09-07:5", _d[0]["manba"])
teng("izohda o'qituvchi va xona",
     "Abdumannopova Ma'mura · GREEN HALL", _d[0]["izoh"])
tekshir("apostrofdan keyin katta harf qo'yilmaydi",
        dars._nomlash("ABDUMANNOPOVA MA'MURA") == "Abdumannopova Ma'mura")
tekshir("noma'lum guruh jimgina bo'sh qaytarmaydi",
        _yiqiladimi(lambda: dars.darslar(_tt([_MON5]), "YO'Q-99", _BOSHI)))

dD = dbm.Db(_TMP / "bD.db", zaxirasiz=True)
oD = entries.odam_qosh(dD, "Fayzulloxon")
_GACHA = _BOSHI + _td(days=6)

_n = dars.sinxronla(dD, _d, oD, _BOSHI, _GACHA)
teng("ikkita dars yozildi", 2, _n["qoshildi"])
teng("kalendarda ikkita vazifa", 2, len(vz.hafta(dD, _BOSHI, oD)))
tekshir("dars SHAXSIY — guruhga chiqmaydi",
        "Databases (lec)" in vz.shaxsiy_nomlari(dD))
teng("dars kitob tengligiga tegmaydi", True, ledger.audit(dD)["toza"])

# Ikkinchi marta chaqirish hech narsa yozmaydi.
_n2 = dars.sinxronla(dD, _d, oD, _BOSHI, _GACHA)
teng("o'zgarmagan jadval hech narsa yozmaydi",
     (0, 0, 0), (_n2["qoshildi"], _n2["yangilandi"], _n2["ochirildi"]))

# «Bajardim» degan javob sinxrondan keyin ham qoladi.
_dv = [v for v in vz.hafta(dD, _BOSHI, oD) if v["vaqt"] == "15:50"][0]
vz.bajar(dD, _dv["id"])
dars.sinxronla(dD, _d, oD, _BOSHI, _GACHA)
teng("bajarilgan dars sinxrondan keyin ham bajarilgan",
     vz.BAJARILDI, vz.bitta(dD, _dv["id"])["holat"])

# Qo'lda yozilgan vazifaga TEGILMAYDI.
_qol = vz.qosh(dD, "Kitob o'qish", oD, _BOSHI, "21:00", 30)
# Xona o'zgardi, chorshanbagi dars olib tashlandi.
_MON5B = dict(_MON5, classroomids=["r2"])
_d3 = dars.darslar(_tt([_MON5B]), "SE-25", _BOSHI)
_n3 = dars.sinxronla(dD, _d3, oD, _BOSHI, _GACHA)
teng("xona o'zgargani yangilandi", 1, _n3["yangilandi"])
teng("jadvaldan chiqqan dars o'chirildi", 1, _n3["ochirildi"])
teng("yangi xona izohga tushdi", "Abdumannopova Ma'mura · 404AB",
     vz.bitta(dD, _dv["id"])["izoh"])
tekshir("qo'lda yozilgan vazifa joyida", vz.bitta(dD, _qol) is not None)
teng("kalendarda dars + qo'lda yozilgani", 2, len(vz.hafta(dD, _BOSHI, oD)))

_shx = xb.shaxsiy_matn(dD, _BOSHI, oD)
tekshir("shaxsiy ro'yxatda dars bor", "Databases (lec)" in _shx)
tekshir("shaxsiy ro'yxatda xona ham bor", "404AB" in _shx)
tekshir("dars guruh xabariga tushmaydi",
        "Databases" not in (xb.kunlik_matn(dD, _BOSHI) or ""))

tekshir("umumiy kalendarda dars ko'rinmaydi",
        not [r for r in vz.oraliq(dD, _BOSHI, _GACHA, shaxsiysiz=True)
             if dars.darsmi(r)])
tekshir("shaxsiy varaqda esa ko'rinadi",
        [r for r in vz.oraliq(dD, _BOSHI, _GACHA, oD) if dars.darsmi(r)])
teng("umumiy kalendar sanog'i ham darssiz", 1,
     vz.sanoq(dD, _BOSHI, _GACHA, shaxsiysiz=True)["jami"])
teng("shaxsiy sanoq hammasini sanaydi", 2,
     vz.sanoq(dD, _BOSHI, _GACHA, oD)["jami"])

tekshir("bo'sh jadval kalendarni o'chirmaydi",
        _yiqiladimi(lambda: dars.sinxronla(dD, [], oD, _BOSHI, _GACHA)))
teng("o'chirilmadi", 2, len(vz.hafta(dD, _BOSHI, oD)))

# Butun sinxron BITTA undo qadami.
dD.undo()
teng("undo butun yangilanishni qaytardi", 3, len(vz.hafta(dD, _BOSHI, oD)))
dD.redo()
teng("redo qaytadan qo'lladi", 2, len(vz.hafta(dD, _BOSHI, oD)))

# ── dars xabarlari: oldindan ogohlantirish + davomat
dD.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 555}, oD)
_dars = [r for r in vz.oraliq(dD, _BOSHI, _GACHA, oD) if dars.darsmi(r)][0]
vz.bajar(dD, _dars["id"], False)      # yuqorida bajarilgan edi — qayta ochamiz


def _dars_xabar(soat, daqiqa, turi):
    kutilgan = xb.kutilayotgan(dD, _datetime(2026, 9, 7, soat, daqiqa))
    return [x for x in kutilgan if x["turi"] == turi
            and x.get("vazifa_id", _dars["id"]) == _dars["id"]]


teng("dars 15:50 da boshlanadi", "15:50", _dars["vaqt"])
tekshir("6 soat oldin hali erta", not _dars_xabar(9, 30, "dars"))
tekshir("5 soatdan kam qolganda ogohlantiradi", _dars_xabar(11, 0, "dars"))
tekshir("dars boshlangach ogohlantirish yubormaydi",
        not _dars_xabar(16, 0, "dars"))
_og = _dars_xabar(11, 0, "dars")[0]
teng("ogohlantirish SHAXSIY chatga ketadi", 555, _og["chat"])
tekshir("ogohlantirishda xona bor", "404AB" in _og["matn"])
tekshir("ogohlantirishda tugma yo'q", _og["klaviatura"] is None)

# Dars 17:10 da tugaydi — davomat 10 daqiqadan keyin so'raladi.
tekshir("dars tugagan zahoti so'ralmaydi", not _dars_xabar(17, 12, "eslatma"))
_dv2 = _dars_xabar(17, 25, "eslatma")
tekshir("10 daqiqadan keyin so'raladi", _dv2)
tekshir("savol davomat haqida", "Davomat" in _dv2[0]["matn"])
teng("tugma «Qatnashdim»", xb.DARS_ALBATTA_TUGMA,
     _dv2[0]["klaviatura"][0][0][0])
teng("tugma ma'lumoti o'zgarmagan", f"bajar:{_dars['id']}",
     _dv2[0]["klaviatura"][0][0][1])
tekshir("dars guruhga emas, shaxsiy chatga", _dv2[0]["chat"] == 555)

# Shaxsiy ro'yxat tugmalari bir-biridan ajralib turadi.
_kl = xb.shaxsiy_klaviatura(dD, _BOSHI, oD)
teng("har ish uchun bitta tugma", 1, len(_kl))
tekshir("tugmada vaqt bor", "15:50" in _kl[0][0][0])
tekshir("dars tugmasida «Qatnashdim»", "Qatnashdim" in _kl[0][0][0])
teng("tugma ma'lumoti qisqa qolgan", f"bajar:{_dars['id']}", _kl[0][0][1])
tekshir("callback_data 64 baytdan oshmaydi",
        len(_kl[0][0][1].encode("utf-8")) <= 64)

# Uy ishi eskisicha: vaqti tugagan zahoti so'raladi.
_uy = [x for x in xb.kutilayotgan(dD, _datetime(2026, 9, 7, 21, 35))
       if x["turi"] == "eslatma" and x.get("vazifa_id") == _qol]
tekshir("uy ishi 10 daqiqa kutmaydi", _uy)
tekshir("uy ishida tugma eskisicha",
        _uy[0]["klaviatura"][0][0][0] == xb.ALBATTA_TUGMA)

# Sozlanmagan bo'lsa tarmoqqa umuman chiqmaydi.
tekshir("sozlanmagan holda yangila() hech narsa qilmaydi",
        dars.yangila(dD) is None)
dars.sozlama_qoy(dD, yoq=True, sinf="SE-25", odam_id=oD)
tekshir("sozlangach chiqishga tayyor", dars.sozlangami(dD))
tekshir("birinchi marta tekshirish kerak", dars.kerakmi(dD))
dD.sozlama_qoy(dars.K_TEKSHIRILDI,
               _datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
tekshir("soat to'lmaguncha tarmoqqa chiqilmaydi", not dars.kerakmi(dD))
tekshir("soat o'tgach yana chiqiladi",
        dars.kerakmi(dD, _datetime.now() + _td(hours=2)))


# ════════════════════════════════════ takroriy vazifa
#
# "Namoz o'qish har kuni" - qoida `vazifa_takror` da, kunlar esa
# `vazifa` da. Bu yerda tekshiriladigan va'dalar:
#
#   * to'ldirish IDEMPOTENT: ikkinchi chaqiruv nusxa yozmaydi;
#   * ufq har kuni suriladi, ya'ni ro'yxat tugamaydi;
#   * o'tmishga hech qachon yozilmaydi;
#   * qo'lda o'chirilgan kun QAYTA TIRILMAYDI;
#   * qoida to'xtatilsa bajarilgani va o'tgani JOYIDA QOLADI.

print("\n── takroriy vazifa ──────────────────────────────────────")

dT = dbm.Db(_TMP / "bT.db", zaxirasiz=True)
tF = entries.odam_qosh(dT, "Fayzulloxon")
tO = entries.odam_qosh(dT, "Otabek")
_TB = _date(2026, 9, 9)              # chorshanba
_TOX = _TB + _td(days=vz.TAKROR_UFQ)


def _tkunlar(odam=None, dan=None, gacha=None):
    return vz.oraliq(dT, (dan or _TB).isoformat(),
                     (gacha or _TOX).isoformat(), odam)


_namoz = vz.takror_qosh(dT, "Namoz o'qish", tF, "06:00", 20, bugun=_TB)
_kun = _tkunlar(tF)
teng("har kuni: ufq bo'yicha hamma kun yozildi", vz.TAKROR_UFQ + 1, len(_kun))
teng("birinchi kun - bugun", _TB.isoformat(), _kun[0]["sana"])
tekshir("hammasi qoidadan chiqqan", all(vz.takrorlimi(v) for v in _kun))
teng("kalit sana bilan quriladi",
     f"takror:{_namoz}:{_TB.isoformat()}", _kun[0]["manba"])
teng("vaqt va davomiylik qoidadan", ("06:00", 20),
     (_kun[0]["vaqt"], _kun[0]["davomiylik"]))

# Idempotentlik: xabarchi har DAQIQADA chaqiradi.
teng("qayta to'ldirish nusxa yozmaydi", 0, vz.takror_toldir(dT, _TB))
teng("kunlar soni o'zgarmadi", vz.TAKROR_UFQ + 1, len(_tkunlar(tF)))

# Ufq suriladi - "yana 30 kunga yozib qo'y" degan ish yo'q.
teng("ertasiga bitta yangi kun qo'shiladi", 1,
     vz.takror_toldir(dT, _TB + _td(days=1)))
teng("o'tmishga yozilmaydi", 0,
     len(_tkunlar(tF, _date(2026, 1, 1), _TB - _td(days=1))))

# Qo'lda o'chirilgan kun qaytib kelmaydi.
_ertaga = [v for v in _tkunlar(tF) if v["sana"] == (_TB + _td(days=1)).isoformat()]
vz.ochir(dT, _ertaga[0]["id"])
teng("o'chirilgan kun tirilmaydi", 0, vz.takror_toldir(dT, _TB))
tekshir("o'sha kun kalendarda yo'q",
        not [v for v in _tkunlar(tF)
             if v["sana"] == (_TB + _td(days=1)).isoformat()])

# ── tanlangan kunlar
_dush_juma = vz.takror_qosh(dT, "Sport", tO, "07:00", 60,
                            naqsh=vz.NAQSH_KUNLAR, kunlar=[0, 4], bugun=_TB)
_sport = [v for v in _tkunlar(tO) if v["nom"] == "Sport"]
tekshir("faqat dushanba va juma",
        {_date.fromisoformat(v["sana"]).weekday() for v in _sport} == {0, 4})
tekshir("bir necha hafta yoziladi", len(_sport) >= 8)
tekshir("bo'sh kun ro'yxati rad etiladi",
        _yiqiladimi(lambda: vz.takror_qosh(dT, "X", tO,
                                           naqsh=vz.NAQSH_KUNLAR,
                                           kunlar=[], bugun=_TB)))

# ── har N kunda
_har3 = vz.takror_qosh(dT, "Kir yuvish", tO, "18:00", 60,
                       naqsh=vz.NAQSH_ORALIQ, oraliq=3, bugun=_TB)
_kir = sorted(v["sana"] for v in _tkunlar(tO) if v["nom"] == "Kir yuvish")
teng("sanoq boshlanishdan yuradi", _TB.isoformat(), _kir[0])
teng("keyingisi uch kundan keyin", (_TB + _td(days=3)).isoformat(), _kir[1])
tekshir("oraliq 0 rad etiladi",
        _yiqiladimi(lambda: vz.takror_qosh(dT, "Y", tO,
                                           naqsh=vz.NAQSH_ORALIQ,
                                           oraliq=0, bugun=_TB)))

# ── to'xtatish: tarix qoladi, kelajak ketadi
_bugungi = [v for v in _tkunlar(tF) if v["sana"] == _TB.isoformat()][0]
vz.bajar(dT, _bugungi["id"])
_keyingi = [v for v in _tkunlar(tF)
            if v["sana"] == (_TB + _td(days=5)).isoformat()][0]
vz.takror_ochir(dT, _namoz, bugun=_TB)
tekshir("bajarilgan kun joyida qoladi",
        vz.bitta(dT, _bugungi["id"]) is not None)
tekshir("kelajakdagi kun olib tashlanadi",
        vz.bitta(dT, _keyingi["id"]) is None)
tekshir("qoida ro'yxatdan chiqdi",
        "Namoz o'qish" not in [t["nom"] for t in vz.takrorlar(dT)])
teng("to'xtagan qoida qayta to'lmaydi", 0, vz.takror_toldir(dT, _TB))
tekshir("qoidasiz qolgan kun ham takroriy deb bilinadi",
        vz.takrorlimi(vz.bitta(dT, _bugungi["id"])))
tekshir("lekin egasi topilmaydi",
        vz.takror_egasi(dT, vz.bitta(dT, _bugungi["id"])) is None)

# ── boshqa jadvallarga tegmaydi
tekshir("takror kitob tengligiga tegmaydi", ledger.audit(dT)["toza"])

# ── undo: qoida va undan chiqqan kunlar BITTA qadam
dT2 = dbm.Db(_TMP / "bT2.db", zaxirasiz=True)
t2 = entries.odam_qosh(dT2, "Abbosxon")
vz.takror_qosh(dT2, "Dori ichish", t2, "08:00", 10, bugun=_TB)
teng("qoidadan kunlar chiqdi", vz.TAKROR_UFQ + 1,
     len(vz.oraliq(dT2, _TB.isoformat(), _TOX.isoformat())))
dT2.undo()
teng("bitta undo hammasini oldi", 0,
     len(vz.oraliq(dT2, _TB.isoformat(), _TOX.isoformat())))
teng("qoida ham qaytdi", 0, len(vz.takrorlar(dT2)))


# ═════════════════════════════════════════════════════════ namoz qazosi
#
# «Qazo bo'ldi»: namoz QAZO holatiga o'tadi va o'sha odamga
# «qazosini o'qish» ishi yoziladi — bitta amal, bitta undo.

print("\n── namoz qazosi ─────────────────────────────────────────")

_asr_q = vz.takror_qosh(dT, "Asr namozi", tF, "17:00", 5, bugun=_TB)
_asr1 = [v for v in _tkunlar(tF) if v["nom"] == "Asr namozi"
         and v["sana"] == _TB.isoformat()][0]
tekshir("«Asr namozi» — namoz", vz.namozmi(_asr1))
tekshir("«Peshin» ham namoz", vz.namozmi({"nom": "Peshin", "manba": None}))
tekshir("«Shom nomozi» (imlo) ham namoz",
        vz.namozmi({"nom": "Shom nomozi", "manba": None}))
tekshir("«Sport» namoz emas", not vz.namozmi({"nom": "Sport", "manba": None}))
tekshir("namoz bo'lmagan ishni qazo qilib bo'lmaydi",
        _yiqiladimi(lambda: vz.qazo_qil(dT, _sport[0]["id"], bugun=_TB)))

_qid = vz.qazo_qil(dT, _asr1["id"], bugun=_TB)
_q = vz.bitta(dT, _qid)
teng("namoz qazo holatida", vz.QAZO, vz.bitta(dT, _asr1["id"])["holat"])
teng("qazo ishi nomi", "Asr namozi — qazosini o'qish", _q["nom"])
teng("qazo ishi o'sha odamda", tF, _q["odam_id"])
teng("qazo ishi bugunga, vaqtsiz", (_TB.isoformat(), None),
     (_q["sana"], _q["vaqt"]))
tekshir("qazo ishining o'zi namoz deb olinmaydi", not vz.namozmi(_q))
tekshir("qazo bo'lgan namoz yopiq — eslatma so'ramaydi",
        vz.yopiqmi(vz.bitta(dT, _asr1["id"])))
tekshir("qazoni qayta qazo qilib bo'lmaydi",
        _yiqiladimi(lambda: vz.qazo_qil(dT, _asr1["id"], bugun=_TB)))
teng("sanoqda qazo alohida", 1,
     vz.sanoq(dT, _TB.isoformat(), _TB.isoformat(), tF)["qazo"])

# O'tgan kun qazo bo'lsa ham qazo ishi BUGUNGA tushadi.
_asr0 = vz.qosh(dT, "Asr namozi", tF, _TB - _td(days=2), "17:00", 5)
_qid0 = vz.qazo_qil(dT, _asr0, bugun=_TB)
teng("o'tgan kunning qazosi bugunga", _TB.isoformat(),
     vz.bitta(dT, _qid0)["sana"])

# Undo — ikkalasi birga qaytadi.
dT.undo()
teng("undo: namoz yana ochiq", vz.OCHIQ, vz.bitta(dT, _asr0)["holat"])
tekshir("undo: qazo ishi yo'q", vz.bitta(dT, _qid0) is None)

# Qayta ochilsa — hali o'qilmagan qazo ishi olib tashlanadi.
vz.bajar(dT, _asr1["id"], False)
teng("qayta ochildi", vz.OCHIQ, vz.bitta(dT, _asr1["id"])["holat"])
tekshir("ochiq qazo ishi ham ketdi", vz.bitta(dT, _qid) is None)


# ═══════════════════════════════════════════ analitika: doira bo'laklari

print("\n── analitika: doira bo'laklari ──────────────────────")

dP = dbm.Db(_TMP / "bP.db", zaxirasiz=True)
pF = entries.odam_qosh(dP, "Fayzulloxon")
_pt = {r["nom"]: r["id"] for r in dP.q("SELECT id, nom FROM turi")}
_P1, _P2 = "2026-09-01", "2026-09-30"


def _prasxod(summa, tur=None, sana="2026-09-10"):
    return entries.rasxod_qosh(dP, sana, "sinov", summa, pF, umumiymi=False,
                               turi_id=_pt[tur] if tur else None)


teng("rasxod yo'q — bo'lak yo'q", [], ledger.doira_bolaklari(dP, _P1, _P2))

# Uchta teng bo'lak: oddiy yaxlitlash 99,9% berardi.
for _t in ("Ovqat", "Kiyim", "Transport"):
    _prasxod(100_000, _t)
_uch = ledger.doira_bolaklari(dP, _P1, _P2)
teng("uch teng bo'lak foizi aynan 100%", 1000, sum(b["ulush"] for b in _uch))
teng("uch teng bo'lak: 33,4 / 33,3 / 33,3", [333, 333, 334],
     sorted(b["ulush"] for b in _uch))
tekshir("5 tadan kam — yig'ilmaydi",
        all(b["tur"] == "turi" for b in _uch))

for _t, _s in (("Bozorlik", 90_000), ("Gigiena", 20_000),
               ("Sog'liq", 15_000), ("Kommunal", 5_000)):
    _prasxod(_s, _t)
_prasxod(900_000)                                  # kategoriyasiz — eng kattasi
_prasxod(700_000, "Ovqat", sana="2026-08-31")      # oraliqdan tashqarida
_ochir = _prasxod(500_000, "Kiyim")
entries.rasxod_ochir(dP, _ochir)                   # o'chirilgan

_bol = ledger.doira_bolaklari(dP, _P1, _P2, korsat=4)
_jami = dP.skalyar("SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0"
                   " AND sana BETWEEN ? AND ?", _P1, _P2)
teng("bo'laklar yig'indisi = oraliqdagi rasxod", _jami,
     sum(b["summa"] for b in _bol))
teng("foizlar yig'indisi aynan 100%", 1000, sum(b["ulush"] for b in _bol))
teng("korsat=4 — 4 ta kategoriya + «Qolganlari»", 5,
     sum(1 for b in _bol if b["tur"] in ("turi", "qolgan")))
_hammasi = ledger.doira_bolaklari(dP, _P1, _P2, korsat=100)
tekshir("hammasi ochilsa «Qolganlari» yo'q",
        all(b["tur"] != "qolgan" for b in _hammasi))
teng("ochilganda ham yig'indi o'sha", _jami, sum(b["summa"] for b in _hammasi))
teng("birlamchi — 6 ta ko'rsatiladi", 6, ledger.DOIRA_QADAM)
teng("tartib: kategoriyalar katta→kichik, keyin qolgan, keyin kategoriyasiz",
     ["turi", "turi", "turi", "turi", "qolgan", "kategoriyasiz"],
     [b["tur"] for b in _bol])
teng("kategoriyasiz katta bo'lsa ham oxirida", 900_000, _bol[-1]["summa"])
teng("qolganlari = kichik kategoriyalar yig'indisi", 20_000 + 15_000 + 5_000,
     _bol[4]["summa"])
teng("qolganlari ichida kimlar borligi aytiladi", 3, len(_bol[4]["ichida"]))
tekshir("kategoriyalar kamayish tartibida",
        [b["summa"] for b in _bol[:4]]
        == sorted((b["summa"] for b in _bol[:4]), reverse=True))
tekshir("o'chirilgan rasxod kirmaydi",
        next(b for b in _bol if b["nom"] == "Kiyim")["summa"] == 100_000)
dP.yop()


# ═════════════════════════════════════════════════════════ tashqi qarz

print("\n── Tashqi qarz ──")
dX = dbm.Db(_TMP / "bX.db", zaxirasiz=True)
xF = entries.odam_qosh(dX, "Fayzulloxon")
xO = entries.odam_qosh(dX, "Otabek")
entries.kirim_qosh(dX, "2026-09-01", xF, 1_000_000)


def _xb(oid):
    return ledger.balans(dX, oid)


_n0, _a0, _s0 = _xb(xF)["naqd"], _xb(xF)["adolat"], _xb(xF)["sof"]
_tq = entries.tashqi_qarz_qosh(dX, "2026-09-05", xF, "  Aziz aka ", 500_000,
                               "telefon")
teng("qarz naqdga tushadi", _n0 + 500_000, _xb(xF)["naqd"])
teng("adolat ham oshadi (ayniyat saqlanadi)", _a0 + 500_000, _xb(xF)["adolat"])
teng("sof ga tegmaydi — uydagilar orasidagi qarz emas", _s0, _xb(xF)["sof"])
teng("qoldiq ko'rinadi", 500_000, _xb(xF)["tashqi_qoldiq"])
teng("boshqa odamga tegmaydi", 0, _xb(xO)["naqd"])
teng("kimdan tozalab yoziladi", "Aziz aka",
     dX.skalyar("SELECT kimdan FROM tashqi_qarz WHERE id=?", _tq))
tekshir("audit toza (qarz olingandan keyin)", ledger.audit(dX).toza,
        "; ".join(ledger.audit(dX).muammolar))
tekshir("juft qarzlarda chiqmaydi", ledger.juft_qarzlar(dX) == [])

entries.tashqi_tolov_qosh(dX, _tq, "2026-09-10", 200_000)
teng("qisman qaytarildi — qoldiq", 300_000, _xb(xF)["tashqi_qoldiq"])
teng("qaytarilgan naqddan chiqadi", _n0 + 300_000, _xb(xF)["naqd"])
teng("tashqi_qoldiq funksiyasi", 300_000, entries.tashqi_qoldiq(dX, _tq))
tekshir("ortig'i bilan qaytarib bo'lmaydi",
        _yiqiladimi(lambda: entries.tashqi_tolov_qosh(dX, _tq, "2026-09-11",
                                                      300_001)))
tekshir("kimdan bo'sh bo'lsa yiqiladi",
        _yiqiladimi(lambda: entries.tashqi_qarz_qosh(dX, "2026-09-05", xF,
                                                     "  ", 1)))
tekshir("ochiq tashqi qarzli odamni o'chirib bo'lmaydi",
        _yiqiladimi(lambda: entries.odam_ochir(dX, xF)))
_ro = ledger.tashqi_qarzlar(dX)
teng("ro'yxat: olingan/qaytgan/qoldiq",
     [(500_000, 200_000, 300_000)],
     [(r["summa"], r["qaytgan"], r["qoldiq"]) for r in _ro])
teng("oldingi ismlar taklif qilinadi", ["Aziz aka"],
     ledger.tashqi_kimdanlar(dX))

entries.tashqi_tolov_qosh(dX, _tq, "2026-09-12", 300_000)
teng("to'liq qaytarildi", 0, _xb(xF)["tashqi_qoldiq"])
teng("yopilgani ochiqlar ro'yxatida yo'q", [],
     ledger.tashqi_qarzlar(dX, faqat_ochiq=True))
tekshir("audit toza (qaytarilgandan keyin)", ledger.audit(dX).toza)

# O'chirish — to'lovlari bilan birga, bitta undo qadami.
_tq2 = entries.tashqi_qarz_qosh(dX, "2026-09-15", xF, "Bank", 400_000)
entries.tashqi_tolov_qosh(dX, _tq2, "2026-09-16", 100_000)
_n1 = _xb(xF)["naqd"]
entries.tashqi_qarz_ochir(dX, _tq2)
teng("o'chirilgan qarz va to'lovi naqddan chiqadi", _n1 - 300_000,
     _xb(xF)["naqd"])
teng("to'lovlari ham o'chdi", 0, dX.skalyar(
    "SELECT COUNT(*) FROM tashqi_tolov WHERE tashqi_qarz_id=? AND ochirilgan=0",
    _tq2))
dX.undo()
teng("undo — qarz va to'lov birga qaytadi", _n1, _xb(xF)["naqd"])
tekshir("audit toza (undo'dan keyin)", ledger.audit(dX).toza)

# Alohida oyna: kimga qancha qaytarish kerak + qarzni bir tugmada yopish.
_n2 = _xb(xF)["naqd"]
_tq3 = entries.tashqi_qarz_qosh(dX, "2026-09-18", xF, "Aziz aka", 250_000)
teng("kimga qaytarish: qarz beruvchi bo'yicha, kattasi birinchi",
     [("Bank", 300_000, 1), ("Aziz aka", 250_000, 1)],
     [(x["kimdan"], x["qoldiq"], x["soni"])
      for x in ledger.tashqi_kimga_qaytarish(dX)])
entries.tashqi_tolov_qosh(dX, _tq3, "2026-09-19", 50_000)
_yt = entries.tashqi_qarz_yop(dX, _tq3, "2026-09-20")
teng("yopish — butun qoldiq bitta to'lov", 200_000,
     dX.skalyar("SELECT summa FROM tashqi_tolov WHERE id=?", _yt))
teng("yopilgan qarz qoldig'i 0", 0, entries.tashqi_qoldiq(dX, _tq3))
teng("yopilgani «kimga qaytarish» dan chiqdi", ["Bank"],
     [x["kimdan"] for x in ledger.tashqi_kimga_qaytarish(dX)])
teng("olib-qaytarilgan qarz naqdni o'zgartirmaydi", _n2, _xb(xF)["naqd"])
tekshir("yopilganni qayta yopib bo'lmaydi",
        _yiqiladimi(lambda: entries.tashqi_qarz_yop(dX, _tq3, "2026-09-21")))
tekshir("audit toza (yopishdan keyin)", ledger.audit(dX).toza)
dX.undo()
teng("undo — yopish bekor, qoldiq qaytdi", 200_000,
     entries.tashqi_qoldiq(dX, _tq3))

# Yopilgan oy tashqi qarzni ham qulflaydi.
dX.con.execute("INSERT INTO davr(oy,holat) VALUES('2026-08','yopilgan')")
try:
    entries.tashqi_qarz_qosh(dX, "2026-08-20", xF, "Aziz aka", 1_000)
    _qulf = False
except dbm.DavrYopilgan:
    _qulf = True
tekshir("yopilgan oyga tashqi qarz yozilmaydi", _qulf)
dX.yop()


# ═════════════════════════════════════════ umumiy tashqi qarz

print("\n── Umumiy tashqi qarz ──")
dUq = dbm.Db(_TMP / "bUq.db", zaxirasiz=True)
uF = entries.odam_qosh(dUq, "Fayzulloxon")
uO = entries.odam_qosh(dUq, "Otabek")
uA = entries.odam_qosh(dUq, "Abbosxon")
entries.kirim_qosh(dUq, "2026-09-01", uF, 1_000_000)


def _b(oid):
    r = ledger.balans(dUq, oid)
    return r["naqd"], r["sof"], r["adolat"]


_boshi = {o: _b(o) for o in (uF, uO, uA)}


def _farq(oid):
    return tuple(x - y for x, y in zip(_b(oid), _boshi[oid]))


_uq = entries.tashqi_qarz_qosh(dUq, "2026-09-10", uF, "Aziz aka", 300_000,
                               "ijara", umumiy=True)
# Yangi qoida (2026-10-01): pul hammaga TENG beriladi, ichki qarz yo'q.
for _o, _n in ((uF, "olgan"), (uO, "Otabek"), (uA, "Abbosxon")):
    teng(f"{_n}: qo'liga o'z ulushi — naqd +100k, sof 0, adolat +100k",
         (100_000, 0, 100_000), _farq(_o))
teng("kim kimga: umumiy tashqi qarz ichki qarz yaratmaydi", [],
     ledger.juft_qarzlar(dUq))
teng("tashqi qoldiq — har kimda o'z ulushi", [100_000] * 3,
     [ledger.balans(dUq, o)["tashqi_qoldiq"] for o in (uF, uO, uA)])
teng("qarzim: Otabekda o'z ulushi", 100_000,
     ledger.odam_qarzlari(dUq, uO)["tashqi_jami"])
tekshir("audit toza (olingandan keyin)", ledger.audit(dUq).toza,
        "; ".join(ledger.audit(dUq).muammolar))

entries.tashqi_tolov_qosh(dUq, _uq, "2026-09-15", 150_000)
teng("yarmi qaytarildi: hammadan teng ayirildi", [(50_000, 0, 50_000)] * 3,
     [_farq(o) for o in (uF, uO, uA)])
tekshir("audit toza (qisman)", ledger.audit(dUq).toza)
entries.tashqi_tolov_qosh(dUq, _uq, "2026-09-20", 150_000)
for _o, _n in ((uF, "olgan"), (uO, "Otabek"), (uA, "Abbosxon")):
    teng(f"to'liq qaytarildi — {_n}: hammasi joyiga qaytdi", (0, 0, 0), _farq(_o))
teng("to'liq qaytarilgach — ichki qarz yo'q", [], ledger.juft_qarzlar(dUq))
tekshir("audit toza (to'liq)", ledger.audit(dUq).toza)

# Ikki kishiga, toq summa — tiyin yo'qolmaydi
_uq2 = entries.tashqi_qarz_qosh(dUq, "2026-09-21", uO, "Bank", 100_001,
                                umumiy=True, qatnashchilar=[uO, uF])
teng("ulushlar yig'indisi aynan qarz", 100_001, dUq.skalyar(
    "SELECT SUM(summa) FROM tashqi_ulush WHERE qarz_id=? AND tolov_id IS NULL",
    _uq2))
tekshir("Abbosxonga ulush tushmadi", not dUq.q1(
    "SELECT 1 FROM tashqi_ulush WHERE qarz_id=? AND odam_id=?", _uq2, uA))
entries.tashqi_tolov_qosh(dUq, _uq2, "2026-09-22", 33_333)
teng("to'lov ulushlari yig'indisi aynan to'lov", 33_333, dUq.skalyar(
    "SELECT SUM(summa) FROM tashqi_ulush WHERE qarz_id=? AND tolov_id IS NOT NULL",
    _uq2))
tekshir("audit toza (toq summa)", ledger.audit(dUq).toza)
entries.tashqi_qarz_ochir(dUq, _uq2)
teng("o'chirilgan umumiy qarz — hech kimga ta'sir yo'q", (0, 0, 0), _farq(uO))
tekshir("audit toza (o'chirilgach)", ledger.audit(dUq).toza)

# Mavjud shaxsiy qarzni (to'lovi bilan) umumiy qilish va qaytarish
_uq3 = entries.tashqi_qarz_qosh(dUq, "2026-09-23", uF, "Akbarshox", 90_000)
entries.tashqi_tolov_qosh(dUq, _uq3, "2026-09-24", 30_000)
_oldin = {o: _b(o) for o in (uF, uO, uA)}
entries.tashqi_umumiy_qoy(dUq, _uq3, [uF, uO, uA])
teng("umumiy qilindi: Otabek — qolgan 60k dan ulushi 20k (qo'liga)",
     (20_000, 0), (_b(uO)[0] - _oldin[uO][0], _b(uO)[1] - _oldin[uO][1]))
teng("olganning naqdi — endi faqat o'z ulushi", _oldin[uF][0] - 40_000,
     _b(uF)[0])
tekshir("audit toza (umumiy qilingach)", ledger.audit(dUq).toza)
tekshir("ro'yxatda ulushlar ko'rinadi", "Otabek:30000" in next(
    r["ulushlar"] for r in ledger.tashqi_qarzlar(dUq) if r["id"] == _uq3))
dUq.undo()
teng("undo — yana shaxsiy", _oldin[uO], _b(uO))
entries.tashqi_umumiy_qoy(dUq, _uq3, [uF, uO, uA])
entries.tashqi_umumiy_qoy(dUq, _uq3, None)
teng("shaxsiy qilinsa — avvalgi holat", _oldin[uO], _b(uO))
tekshir("bo'sh ro'yxat bilan umumiy qilib bo'lmaydi",
        _yiqiladimi(lambda: entries.tashqi_umumiy_qoy(dUq, _uq3, [])))
tekshir("audit toza (oxiri)", ledger.audit(dUq).toza)

# Qaytarish rasxoddagidek sozlanadi: aniq summalar
_uq4 = entries.tashqi_qarz_qosh(dUq, "2026-09-25", uF, "Do'kon", 90_000,
                                umumiy=True, qatnashchilar=[uF, uO, uA])
_o4 = {o: _b(o) for o in (uF, uO, uA)}
entries.tashqi_tolov_qosh(dUq, _uq4, "2026-09-26", 30_000,
                          usul=money.USUL_ANIQ,
                          parametrlar={uF: 20_000, uO: 10_000})
teng("sozlangan qaytarish: kim qancha to'lagan", (-20_000, -10_000, 0),
     tuple(_b(o)[0] - _o4[o][0] for o in (uF, uO, uA)))
tekshir("sozlangan qaytarish: sof o'zgarmadi",
        all(_b(o)[1] == _o4[o][1] for o in (uF, uO, uA)))
_uq5 = entries.tashqi_qarz_qosh(dUq, "2026-09-27", uF, "Bank", 100_000,
                                umumiy=True, usul=money.USUL_FOIZ,
                                parametrlar={uF: 50, uO: 50})
teng("olishda ham sozlanadi: foiz", {uF: 50_000, uO: 50_000}, {
    r["odam_id"]: r["summa"] for r in dUq.q(
        "SELECT odam_id, summa FROM tashqi_ulush WHERE qarz_id=?"
        " AND tolov_id IS NULL AND ochirilgan=0", _uq5)})
tekshir("audit toza (sozlangan)", ledger.audit(dUq).toza)

# Botda: umumiy qarz ulushdorga ham ko'rinadi — o'z ulushi bilan
from core import tg_menyu as _tm  # noqa: E402
_uq4 = entries.tashqi_qarz_qosh(dUq, "2026-09-25", uF, "Shoxrux aka", 60_000,
                                umumiy=True, qatnashchilar=[uF, uO, uA])
entries.tashqi_tolov_qosh(dUq, _uq4, "2026-09-25", 30_000)
_tO = _tm.tashqi(dUq, uO)
tekshir("bot: Otabek umumiy qarzni ko'radi", "Shoxrux aka" in _tO and "umumiy" in _tO)
tekshir("bot: Otabekning qolgan ulushi 10 000",
        "Sizning ulushingiz: <b>" + money.fmt_som(10_000) in _tO)
tekshir("bot: shaxsiy qarz boshqaga ko'rinmaydi", "Akbarshox" not in _tO)
tekshir("bot: olgan odam ham ko'radi", "Shoxrux aka" in _tm.tashqi(dUq, uF))
dUq.yop()


# ═════════════════════════════════════════ ikonkali kategoriya

print("\n── Ikonkali kategoriya ──")
from core import kategoriya as kt
from core import plan  # noqa: E402
dI = dbm.Db(_TMP / "bI.db", zaxirasiz=True)
iF = entries.odam_qosh(dI, "Fayzulloxon")
_bl = kt.belgilar()
teng("200 ta ikonka kesilgan, yashirinlari chiqmaydi",
     200 - len(kt.YASHIRIN), len(_bl))
tekshir("yashirin ikonka ro'yxatda yo'q", not kt.YASHIRIN & set(_bl))
tekshir("ikonkalar nomsiz keladi", kt.nomlanganlar(dI) == {})
_f1, _f2 = _bl[0], _bl[1]
_t1 = kt.nom_ber(dI, _f1, "  Kitoblar ")
teng("nom berildi — kategoriya bo'ldi", "Kitoblar",
     dI.skalyar("SELECT nom FROM turi WHERE id=?", _t1))
teng("ikonka faylga bog'landi", _f1,
     dI.skalyar("SELECT rasm FROM turi WHERE id=?", _t1))
kt.nom_ber(dI, _f1, "Darsliklar")
teng("qayta nom — o'sha kategoriya o'zgaradi, yangisi yaratilmaydi",
     (_t1, "Darsliklar"), (kt.nomlanganlar(dI)[_f1]["id"],
                           kt.nomlanganlar(dI)[_f1]["nom"]))
tekshir("band nom rad etiladi",
        _yiqiladimi(lambda: kt.nom_ber(dI, _f2, "Darsliklar")))
tekshir("bo'sh nom rad etiladi", _yiqiladimi(lambda: kt.nom_ber(dI, _f2, " ")))
tekshir("yo'q ikonka rad etiladi",
        _yiqiladimi(lambda: kt.nom_ber(dI, "yoq_99.png", "X")))

_r = entries.rasxod_qosh(dI, "2026-09-20", "daftar", 30_000, iF,
                         umumiymi=False, turi_id=_t1)
kt.nomini_olib_tashla(dI, _f1)
tekshir("nomi olib tashlangan ikonka yana nomsiz", _f1 not in kt.nomlanganlar(dI))
teng("eski rasxod kategoriyasini yo'qotmaydi", _t1,
     dI.skalyar("SELECT turi_id FROM rasxod WHERE id=?", _r))
teng("qayta o'sha nom — eski kategoriya tiriladi", _t1,
     kt.nom_ber(dI, _f2, "Darsliklar"))

# Sabab va kategoriya majburiy
tekshir("sababsiz rasxod rad etiladi",
        _yiqiladimi(lambda: entries.rasxod_majburiy(dI, "  ", _t1)))
tekshir("kategoriyasiz rasxod rad etiladi",
        _yiqiladimi(lambda: entries.rasxod_majburiy(dI, "non", None)))
kt.nomini_olib_tashla(dI, _f2)
tekshir("nofaol kategoriya rad etiladi",
        _yiqiladimi(lambda: entries.rasxod_majburiy(dI, "non", _t1)))
_ot = dI.skalyar("SELECT id FROM turi WHERE faol=1 AND rasm IS NULL LIMIT 1")
tekshir("sabab + faol kategoriya — o'tadi",
        not _yiqiladimi(lambda: entries.rasxod_majburiy(dI, "non", _ot)))
tekshir("audit toza", ledger.audit(dI).toza)

# Analitika: hamma kategoriya, ishlatilmagani ham
_tA = kt.nom_ber(dI, _bl[10], "Sinov yangi")
entries.rasxod_qosh(dI, "2026-09-21", "x", 10_000, iF, umumiymi=False,
                    turi_id=_ot)
entries.rasxod_qosh(dI, "2026-09-22", "y", 5_000, iF, umumiymi=False)
_kj = ledger.kategoriya_jadvali(dI, "2026-09-01", "2026-09-30")
_kjn = {x["nom"]: x for x in _kj}
tekshir("yangi, ishlatilmagan kategoriya ham bor (0 bilan)",
        _kjn.get("Sinov yangi", {}).get("summa") == 0)
tekshir("ikonkasi bilan", _kjn["Sinov yangi"]["rasm"] == _bl[10])
teng("hamma faol kategoriya ro'yxatda",
     dI.skalyar("SELECT COUNT(*) FROM turi WHERE faol=1"),
     sum(1 for x in _kj if x["turi_id"] is not None and x["nom"] != "Darsliklar"))
tekshir("nofaol, lekin rasxodi bor kategoriya chiqadi",
        "Darsliklar" in _kjn)
teng("kategoriyasiz oxirida", "Kategoriyasiz", _kj[-1]["nom"])
teng("ulushlar yig'indisi aynan 100%", 1000, sum(x["ulush"] for x in _kj))
teng("summa yig'indisi = oraliqdagi rasxod",
     dI.skalyar("SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0"
                " AND sana BETWEEN '2026-09-01' AND '2026-09-30'"),
     sum(x["summa"] for x in _kj))
teng("oyning 1-kunidan bugungacha", ("2026-09-01", "2026-09-25"),
     plan.oy_bugungacha("2026-09-25"))
teng("1-noyabrda — faqat 1-noyabr", ("2026-11-01", "2026-11-01"),
     plan.oy_bugungacha("2026-11-01"))
dI.yop()


# ═════════════════════════════════════════ mahsulotlar va daraxt

print("\n── Mahsulotlar ──")
from core import mahsulot as mh  # noqa: E402
dM = dbm.Db(_TMP / "bM.db", zaxirasiz=True)
mF = entries.odam_qosh(dM, "Fayzulloxon")
mO = entries.odam_qosh(dM, "Otabek")
_eski_turi = dM.skalyar("SELECT COUNT(*) FROM turi")
_boz = dM.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
_mev = mh.kategoriya_qosh(dM, "Mevalar", _boz, rasm=mh.bosh_belgilar(dM)[0])
_sab = mh.kategoriya_qosh(dM, "Sabzavotlar", _boz, rasm=mh.bosh_belgilar(dM)[0])
_sut = mh.kategoriya_qosh(dM, "Sut mahsulotlari", _boz,
                          rasm=mh.bosh_belgilar(dM)[0])
_tro = mh.kategoriya_qosh(dM, "Tropik", _mev,                     # 3-daraja
                          rasm=mh.bosh_belgilar(dM)[0])
# Ichki kategoriyaga rasm majburiy, bo'sh va haqiqiy bo'lishi shart
tekshir("ichki kategoriya rasmsiz — rad etiladi",
        _yiqiladimi(lambda: mh.kategoriya_qosh(dM, "Rasmsiz", _boz)))
tekshir("ichki kategoriya — yo'q rasm rad etiladi",
        _yiqiladimi(lambda: mh.kategoriya_qosh(dM, "Soxta", _boz,
                                               rasm="yoq_99.png")))
_mev_rasm = dM.skalyar("SELECT rasm FROM turi WHERE id=?", _mev)
tekshir("ichki kategoriya rasmi yozildi", bool(_mev_rasm))
tekshir("band rasm (boshqa kategoriyada) rad etiladi",
        _yiqiladimi(lambda: mh.kategoriya_qosh(dM, "Band", _boz,
                                               rasm=_mev_rasm)))
tekshir("band rasm bo'sh ro'yxatda yo'q", _mev_rasm not in mh.bosh_belgilar(dM))
teng("rad etilganlar yozilmadi", 0,
     dM.skalyar("SELECT COUNT(*) FROM turi WHERE nom IN ('Rasmsiz','Soxta','Band')"))
teng("mavjud kategoriyalar o'chmadi", _eski_turi + 4,
     dM.skalyar("SELECT COUNT(*) FROM turi WHERE faol=1"))
_boz_tugun = next(t for t in mh.daraxt(dM) if t["id"] == _boz)
teng("daraxt: Bozorlik ichida 3 ta ichki", 3, len(_boz_tugun["bolalar"]))
teng("avlodlar — har chuqurlikda", {_boz, _mev, _sab, _sut, _tro},
     set(mh.avlodlar(dM, _boz)))
teng("yo'l nomi", "Bozorlik › Mevalar › Tropik", mh.yol_nomi(dM, _tro))
tekshir("band nom rad etiladi",
        _yiqiladimi(lambda: mh.kategoriya_qosh(dM, "Mevalar", _boz,
                                               rasm=mh.bosh_belgilar(dM)[0])))

_olma = mh.saqla(dM, nom="Olma", turi_id=_mev, narx=18_000, miqdor="1",
                 olchov="kg")
_banan = mh.saqla(dM, nom="Banan", turi_id=_tro, narx="25000", miqdor=None,
                  ogirlik="", litr="", olchov="", izoh="")
_sut_m = mh.saqla(dM, nom="Sut", turi_id=_sut, litr="0,9", narx=None)
_non = mh.saqla(dM, nom="Non", turi_id=_boz)
r = dM.q1("SELECT * FROM item WHERE id=?", _banan)
tekshir("bo'sh maydonlar NULL — xato yo'q",
        r["miqdor"] is None and r["ogirlik"] is None and r["olchov"] is None)
teng("vergulli son o'qiladi", 0.9,
     dM.skalyar("SELECT litr FROM item WHERE id=?", _sut_m))
teng("bo'sh narx — 0", 0, dM.skalyar("SELECT narx FROM item WHERE id=?", _sut_m))
tekshir("nomsiz mahsulot rad", _yiqiladimi(
    lambda: mh.saqla(dM, nom=" ", turi_id=_mev)))
tekshir("kategoriyasiz mahsulot rad", _yiqiladimi(
    lambda: mh.saqla(dM, nom="X", turi_id=None)))
tekshir("manfiy narx rad", _yiqiladimi(
    lambda: mh.saqla(dM, nom="X", turi_id=_mev, narx=-1)))
tekshir("son emas — tushunarli xato", _yiqiladimi(
    lambda: mh.saqla(dM, nom="X", turi_id=_mev, ogirlik="abc")))

teng("Bozorlik — ichkidagilar ham ko'rinadi", {"Olma", "Banan", "Sut", "Non"},
     {r["nom"] for r in mh.mahsulotlar(dM, _boz)})
teng("Mevalar — Tropik ichidagisi ham", {"Olma", "Banan"},
     {r["nom"] for r in mh.mahsulotlar(dM, _mev)})
teng("Sabzavotlar — bo'sh", [], mh.mahsulotlar(dM, _sab))
teng("qidiruv (katta-kichik harf farqsiz)", ["Olma"],
     [r["nom"] for r in mh.mahsulotlar(dM, None, "OLM")])
teng("kategoriya yo'li mahsulotda", "Bozorlik › Mevalar › Tropik",
     next(r for r in mh.mahsulotlar(dM) if r["nom"] == "Banan")["kategoriya"])

mh.saqla(dM, _olma, nom="Olma", turi_id=_mev, narx=20_000, miqdor=1,
         olchov="kg", faol=False)
tekshir("faol emas — rasxod ro'yxatida yo'q",
        "Olma" not in [r["nom"] for r in plan.turi_itemlari(dM, _boz)])
tekshir("faol emas — Mahsulotlar varag'ida bor",
        "Olma" in [r["nom"] for r in mh.mahsulotlar(dM, _boz)])
teng("faol almashtirish", True, mh.faol_almashtir(dM, _olma))
_ti = plan.turi_itemlari(dM, _boz)
teng("rasxod oynasi: Bozorlik → ichkidagi mahsulotlar ham",
     {"Olma", "Banan", "Sut", "Non"}, {r["nom"] for r in _ti})
teng("o'zi to'g'ridan-to'g'ri Bozorlikdagi birinchi", "Non", _ti[0]["nom"])
teng("ichkidagisi qaysi kategoriyada ekani bilan", "Tropik",
     next(r for r in _ti if r["nom"] == "Banan")["turi_nom"])

# Rasxod mahsulot bilan, narx o'zgarsa eski rasxod o'zgarmaydi
_rx = entries.rasxod_qosh(dM, "2026-09-20", "Olma", 20_000, mF, umumiymi=True,
                          turi_id=_mev, item_id=_olma)
teng("rasxod mahsulotga bog'landi", _olma,
     dM.skalyar("SELECT item_id FROM rasxod WHERE id=?", _rx))
mh.saqla(dM, _olma, nom="Olma", turi_id=_mev, narx=30_000)
teng("mahsulot narxi o'zgardi — eski rasxod o'zgarmadi", 20_000,
     dM.skalyar("SELECT summa FROM rasxod WHERE id=?", _rx))
mh.ochir(dM, _olma)
teng("o'chirilgan mahsulot ro'yxatda yo'q", [],
     [r for r in mh.mahsulotlar(dM) if r["id"] == _olma])
teng("o'chirilgan mahsulotning rasxodi joyida", _olma,
     dM.skalyar("SELECT item_id FROM rasxod WHERE id=? AND ochirilgan=0", _rx))
dM.undo()
tekshir("undo — mahsulot qaytdi",
        any(r["id"] == _olma for r in mh.mahsulotlar(dM)))

# Doira va budjet: ichki kategoriya otasiga qo'shiladi
# Umumiy — «Reja va fakt» ning umumiy doirasi shularni sanaydi.
entries.rasxod_qosh(dM, "2026-09-21", "bozor", 50_000, mF, umumiymi=True,
                    turi_id=_boz)
_tb = {t["nom"]: t["summa"] for t in ledger.turi_boyicha(dM, "2026-09-01",
                                                          "2026-09-30")}
teng("doira: Mevalar rasxodi Bozorlikka qo'shildi", 70_000, _tb.get("Bozorlik"))
tekshir("doirada ichki kategoriya alohida bo'lak emas", "Mevalar" not in _tb)
tekshir("«Hamma kategoriyalar» da faqat asosiylar",
        "Mevalar" not in [x["nom"] for x in
                          ledger.kategoriya_jadvali(dM, "2026-09-01", "2026-09-30")])
plan.budjet_qoy(dM, _boz, "2026-09", 100_000)
teng("budjet: ichki kategoriya rasxodi ham hisoblandi", 70_000,
     next(b for b in plan.turi_budjet(dM, "2026-09") if b["turi_id"] == _boz)["fakt"])
tekshir("audit toza", ledger.audit(dM).toza)

# Reja va fakt (Analitika): oylik reja, kategoriya rejasi, oshib ketish
import money as _mn
teng("foiz: 1 860 000 / 3 000 000 = 62%", 62, _mn.foiz(1_860_000, 3_000_000))
teng("foiz: oshib ketsa cheklanmaydi", 120, _mn.foiz(120, 100))
tekshir("foiz: reja 0 — None", _mn.foiz(5, 0) is None)
teng("oy surish: dekabr → yanvar", "2027-01", plan.oy_sur("2026-12", 1))


def _rf_qator(oy="2026-09"):
    r = plan.reja_va_fakt(dM, oy)
    return r, next((q for q in r["qatorlar"] if q["turi_id"] == _boz), None)


_rf, _rq = _rf_qator()
tekshir("reja-fakt: faqat kategoriya rejasi — reja bor", _rf["reja_bor"])
teng("reja-fakt: umumiy yo'q → reja = kategoriyalar yig'indisi",
     _rf["turi_reja_jami"], _rf["reja"])
teng("reja-fakt: Bozorlik (ichki bilan) fakt", 70_000, _rq["fakt"])
teng("reja-fakt: Bozorlik qolgan", 30_000, _rq["qolgan"])
teng("reja-fakt: 70% — yaxshi", ("yaxshi", 70), (_rq["holat"], _rq["foiz"]))
tekshir("reja-fakt: ichki kategoriya alohida qator emas",
        "Mevalar" not in [q["nom"] for q in _rf["qatorlar"]])
teng("reja-fakt: umumiy fakt = oyning UMUMIY rasxodi (butun summasi)",
     dM.skalyar("SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0"
                " AND umumiymi=1 AND kim_uchun IS NULL"
                " AND sana BETWEEN '2026-09-01' AND '2026-09-30'"), _rf["fakt"])

# Shaxsiy reja — alohida doira: o'z yozuvlari va o'z shaxsiy rasxodi
_shx = entries.rasxod_qosh(dM, "2026-09-22", "kitob", 30_000, mF,
                           umumiymi=False, turi_id=_boz)
teng("shaxsiy rasxod umumiy faktga kirmaydi", _rf["fakt"],
     plan.reja_va_fakt(dM, "2026-09")["fakt"])
tekshir("shaxsiy reja: odamsiz rad etiladi", _yiqiladimi(
    lambda: plan.reja_yozuv_saqla(dM, "2026-09-05", "x", _boz, 1,
                                  umumiymi=False)))
_shq = plan.reja_yozuv_saqla(dM, "2026-09-05", "Kitoblar", _boz, 40_000,
                             umumiymi=False, odam_id=mF)
_rs = plan.reja_va_fakt(dM, "2026-09", mF)
teng("shaxsiy reja: reja/fakt/qolgan", (40_000, 30_000, 10_000),
     (_rs["reja"], _rs["fakt"], _rs["qolgan"]))
teng("shaxsiy reja umumiy rejaga qo'shilmaydi", _rf["reja"],
     plan.reja_va_fakt(dM, "2026-09")["reja"])
tekshir("shaxsiy reja: boshqa odamda ko'rinmaydi",
        not plan.reja_bormi(dM, "2026-09", mO))
teng("shaxsiy reja: yozuvlar ro'yxati doira bo'yicha", ([_shq], []),
     ([y["id"] for y in plan.reja_yozuvlari(dM, "2026-09", mF)],
      [y["id"] for y in plan.reja_yozuvlari(dM, "2026-09", mO)]))
dM.undo()
dM.undo()

plan.reja_saqla(dM, "2026-09", 50_000, {_boz: 60_000})
_rf, _rq = _rf_qator()
teng("reja-fakt: umumiy reja qo'yildi", (50_000, True),
     (_rf["reja"], _rf["umumiy_qoyilgan"]))
teng("reja-fakt: oshib ketgani yashirilmaydi (manfiy qolgan)",
     50_000 - _rf["fakt"], _rf["qolgan"])
teng("reja-fakt: Bozorlik oshdi", ("oshdi", -10_000, 117),
     (_rq["holat"], _rq["qolgan"], _rq["foiz"]))
teng("reja-fakt: diqqat — oshib ketgan kategoriya", _boz,
     _rf["diqqat"]["turi_id"])
plan.reja_saqla(dM, "2026-09", 50_000, {_boz: 87_500})
teng("reja-fakt: 80% — limitga yaqin", ("yaqin", 80),
     (_rf_qator()[1]["holat"], _rf_qator()[1]["foiz"]))
dM.undo()
teng("reja-fakt: undo — bitta saqlash bitta qadam", 60_000, _rf_qator()[1]["reja"])
dM.undo()
_rf, _rq = _rf_qator()
teng("reja-fakt: undo — umumiy reja va kategoriya qaytdi", (False, 100_000),
     (_rf["umumiy_qoyilgan"], _rq["reja"]))
tekshir("reja-fakt: 2026-10 da reja yo'q", not plan.reja_bormi(dM, "2026-10"))
tekshir("reja-fakt: o'tgan oydan ko'chirildi",
        plan.reja_kochir(dM, "2026-09", "2026-10")
        and plan.turi_reja(dM, "2026-10") == plan.turi_reja(dM, "2026-09"))
dM.undo()
tekshir("reja-fakt: ko'chirish ham bitta undo", not plan.reja_bormi(dM, "2026-10"))
tekshir("audit toza (reja-fakt)", ledger.audit(dM).toza)

# Reja rasxod kabi: yozuv + mahsulotlar, kategoriya rejasiga qo'shiladi
from core import rasxod_kirit as _rk
_ni = plan.item_qosh(dM, "Reja non", 4_000, _mev)
_yq = plan.reja_yozuv_saqla(dM, "2026-12-07", "Meva", _mev, 9_000,
                            [{"item_id": _ni, "miqdor": 2, "summa": 8_000},
                             {"item_id": _ni, "summa": 1_000}])
teng("reja yozuvi: ichki kategoriya otasining rejasiga", {_boz: 9_000},
     plan.turi_reja(dM, "2026-12"))
teng("reja yozuvi: mahsulotlari", [8_000, 1_000],
     [x["summa"] for x in plan.reja_yozuv_mahsulotlari(dM, _yq)])
tekshir("reja yozuvi: summa ≠ yig'indi rad etiladi", _yiqiladimi(
    lambda: plan.reja_yozuv_saqla(dM, "2026-12-07", "x", _mev, 5,
                                  [{"item_id": _ni, "summa": 4_000}])))
tekshir("reja yozuvi: sababsiz rad etiladi", _yiqiladimi(
    lambda: plan.reja_yozuv_saqla(dM, "2026-12-07", "", _mev, 5)))
plan.budjet_qoy(dM, _boz, "2026-12", 1_000)
teng("reja yozuvi: limit bilan qo'shiladi", 10_000,
     plan.turi_reja(dM, "2026-12")[_boz])
teng("reja yozuvi: limit oynasi faqat limitni ko'radi", {_boz: 1_000},
     plan.limit_reja(dM, "2026-12"))
dM.undo()
plan.reja_yozuv_saqla(dM, "2027-01-15", "Meva", _mev, 4_000,
                      [{"item_id": _ni, "summa": 4_000}], qator_id=_yq)
tekshir("reja yozuvi: sana boshqa oyga — o'sha oyga o'tdi",
        not plan.reja_bormi(dM, "2026-12")
        and plan.turi_reja(dM, "2027-01") == {_boz: 4_000})
dM.undo()
tekshir("reja yozuvi: kochir — yozuv va mahsulotlari",
        plan.reja_kochir(dM, "2026-12", "2027-02")
        and [len(plan.reja_yozuv_mahsulotlari(dM, y["id"]))
             for y in plan.reja_yozuvlari(dM, "2027-02")] == [2])
dM.undo()
plan.reja_yozuv_ochir(dM, _yq)
tekshir("reja yozuvi: o'chirildi", not plan.reja_bormi(dM, "2026-12"))
dM.undo()
dM.undo()
tekshir("reja yozuvi: undo — hammasi qaytdi", not plan.reja_bormi(dM, "2026-12"))
tekshir("audit toza (reja yozuvi)", ledger.audit(dM).toza)

# «Aslida to'landi»: rejadan haqiqiy rasxod (toifa ichi oynasi)
_bq = plan.reja_yozuv_saqla(dM, "2026-12-06", "Bozor", _mev, 9_000,
                            [{"item_id": _ni, "miqdor": 2, "summa": 8_000},
                             {"item_id": _ni, "summa": 1_000}])
_bk = plan.kategoriya_reja_yozuvlari(dM, "2026-12", _boz)
teng("toifa ichi: ichki kategoriyadagi reja kuni otasida", [_bq],
     [y["id"] for y in _bk])
_bm = [m["id"] for m in _bk[0]["mahsulotlar"]]
_brid = plan.reja_bajar(dM, _bq, {_bm[0]: 8_500, _bm[1]: 0}, mF)
teng("bajar: rasxod — aslida to'langani, rejadagi sana", (8_500, "2026-12-06", 1),
     (dM.skalyar("SELECT summa FROM rasxod WHERE id=?", _brid),
      dM.skalyar("SELECT sana FROM rasxod WHERE id=?", _brid),
      dM.skalyar("SELECT umumiymi FROM rasxod WHERE id=?", _brid)))
teng("bajar: faqat olingan mahsulot rasxodda", [8_500],
     [x["summa"] for x in _rk.rasxod_mahsulotlari(dM, _brid)])
teng("bajar: umumiy fakt rasxoddan", 8_500,
     next(q for q in plan.reja_va_fakt(dM, "2026-12")["qatorlar"]
          if q["turi_id"] == _boz)["fakt"])
teng("bajar: qayta saqlash — o'sha rasxod yangilanadi", (_brid, 9_700),
     (plan.reja_bajar(dM, _bq, {_bm[0]: 8_500, _bm[1]: 1_200}, mF),
      dM.skalyar("SELECT summa FROM rasxod WHERE id=?", _brid)))
teng("bajar: to'langanlar rejada saqlandi", [8_500, 1_200],
     [m["tolangan"] for m in plan.kategoriya_reja_yozuvlari(
         dM, "2026-12", _boz)[0]["mahsulotlar"]])
tekshir("bajar: manfiy rad etiladi", _yiqiladimi(
    lambda: plan.reja_bajar(dM, _bq, {_bm[0]: -1}, mF)))
tekshir("audit toza (bajar)", ledger.audit(dM).toza)
plan.reja_bajar(dM, _bq, {}, mF)
tekshir("bajar: hammasi 0 — rasxod o'chdi", not dM.skalyar(
    "SELECT COUNT(*) FROM rasxod WHERE id=? AND ochirilgan=0", _brid))
dM.undo()
teng("bajar: undo — rasxod qaytdi", 9_700,
     dM.skalyar("SELECT summa FROM rasxod WHERE id=? AND ochirilgan=0", _brid))
_bs = plan.reja_yozuv_saqla(dM, "2026-12-08", "Kitob", _boz, 5_000,
                            umumiymi=False, odam_id=mF)
_bsr = plan.reja_bajar(dM, _bs, {None: 6_000}, mO)
teng("bajar: shaxsiy rejani boshqasi to'lasa — «uning uchun»", (mO, mF),
     (dM.skalyar("SELECT kim_toladi FROM rasxod WHERE id=?", _bsr),
      dM.skalyar("SELECT kim_uchun FROM rasxod WHERE id=?", _bsr)))
teng("bajar: shaxsiy fakt o'sha odamda", 6_000,
     plan.reja_va_fakt(dM, "2026-12", mF)["fakt"])
tekshir("audit toza (shaxsiy bajar)", ledger.audit(dM).toza)
for _ in range(5):
    dM.undo()
tekshir("bajar: undo — reja ham, rasxodlar ham qaytdi",
        not plan.reja_bormi(dM, "2026-12") and not dM.skalyar(
            "SELECT COUNT(*) FROM rasxod WHERE id IN (?, ?) AND ochirilgan=0",
            _brid, _bsr))

# Ro'yxatdan nusxa — keyingi kunga, mahsulotlari bilan, to'lanmagan
_nq0 = plan.reja_yozuv_saqla(dM, "2026-12-31", "Non", _mev, 4_000,
                             [{"item_id": _ni, "summa": 4_000}],
                             umumiymi=False, odam_id=mF)
plan.reja_bajar(dM, _nq0, {plan.kategoriya_reja_yozuvlari(
    dM, "2026-12", _boz, mF)[0]["mahsulotlar"][0]["id"]: 4_500}, mF)
_nq1 = plan.reja_yozuv_nusxa(dM, _nq0)
_nqy = plan.reja_yozuv_toliq(dM, _nq1)
teng("nusxa: oy oxirida — o'sha kun (oydan chiqmaydi)", "2026-12-31",
     _nqy["sana"])
teng("nusxa: nom, doira, mahsulotlar", ("Non", 0, mF, [4_000]),
     (_nqy["nom"], _nqy["umumiymi"], _nqy["odam_id"],
      [m["summa"] for m in _nqy["mahsulotlar"]]))
tekshir("nusxa: to'langani va rasxodi ko'chmadi",
        _nqy["rasxod"] is None
        and all(m["tolangan"] is None for m in _nqy["mahsulotlar"]))
_nq2 = plan.reja_yozuv_saqla(dM, "2026-12-07", "Sut", _mev, 1_000)
teng("nusxa: keyingi kunga", "2026-12-08", plan.reja_yozuv_toliq(
    dM, plan.reja_yozuv_nusxa(dM, _nq2))["sana"])
for _ in range(5):
    dM.undo()
tekshir("nusxa: undo — hammasi qaytdi", not plan.reja_bormi(dM, "2026-12"))

# Rejaga band — hisobda yo'q qismi qarz, balans minusga tushmaydi
plan.reja_saqla(dM, plan.oy_kaliti(), 10_000_000, {})
_bh = plan.band_hisob(dM)
_nq = {r["id"]: max(0, r["naqd"]) for r in ledger.balanslar(dM)}
tekshir("band: hech kimdan qo'lidagidan ko'p ayirilmaydi",
        all(v["ayirildi"] <= _nq[k] for k, v in _bh.items()))
_as = plan.asosiy_odam(dM)
_boshqalar = sum(v["qarz"] for k, v in _bh.items() if k != _as)
tekshir("band: boshqalarda ayirilgan + qarz = band",
        all(v["ayirildi"] + v["qarz"] == v["band"]
            for k, v in _bh.items() if k != _as))
teng("band: asosiy — o'zi + boshqalarning yetmagani", _bh[_as]["band"]
     + _boshqalar, _bh[_as]["ayirildi"] + _bh[_as]["qarz"])
for _o in _bh:
    _bt = plan.band_tafsilot(dM, _o)
    teng(f"band tafsilot ({_o}): umumiy ulush + shaxsiy = band",
         plan.band_pul(dM).get(_o, 0), _bt["jami"])
_boshqa = next(k for k in _bh if k != plan.asosiy_odam(dM))
teng("band: hisobda yo'q qismi «Qarzim» ga qo'shildi",
     ledger.odam_qarzlari(dM, _boshqa)["jami"] + _bh[_boshqa]["qarz"],
     plan.odam_qarzlari(dM, _boshqa)["jami"])
dM.undo()

# «Bugun»: shu kunga rejalangan ro'yxatlar — umumiy va shaxsiy
_kq1 = plan.reja_yozuv_saqla(dM, "2026-12-09", "Non", _mev, 2_000)
_kq2 = plan.reja_yozuv_saqla(dM, "2026-12-09", "Kitob", _mev, 3_000,
                             umumiymi=False, odam_id=mF)
plan.reja_yozuv_saqla(dM, "2026-12-10", "Ertaga", _mev, 1_000)
teng("bugunga reja: faqat shu kun, umumiy oldin", [_kq1, _kq2],
     [y["id"] for y in plan.kun_reja_yozuvlari(dM, "2026-12-09")])
teng("ro'yxat holati", ["olinmagan", "rejadagidek", "+500 ortiq"],
     [plan.royxat_holati(1_000, t) for t in (0, 1_000, 1_500)])
for _ in range(3):
    dM.undo()

# Reja — kategoriyaga ajratilgan pul: shu kategoriyadan qilingan HAR
# QANDAY rasxod ayiriladi, ro'yxatga bog'lanishi shart emas
_kr1 = plan.reja_yozuv_saqla(dM, "2026-12-09", "Bozor", _mev, 10_000,
                             [{"item_id": _ni, "summa": 10_000}])
plan.reja_yozuv_saqla(dM, "2026-12-11", "Bozor 2", _boz, 4_000)
_ka = _rk.saqla(dM, _rk.Qoralama(sana="2026-12-09", kim_toladi=mF,
                                  turi_id=_mev, nom="Olma", summa=3_000,
                                  tur=_rk.UMUMIY))
_rk.saqla(dM, _rk.Qoralama(sana="2026-12-10", kim_toladi=mF, turi_id=_boz,
                           nom="Rejasiz kun", summa=2_000, tur=_rk.UMUMIY))
_kk = plan.kategoriya_kunlari(dM, "2026-12", _boz)
teng("kunlar: bog'lanmagan rasxod ham ayirildi (ichki kategoriya otasida)",
     [("2026-12-09", 10_000, 3_000, 7_000), ("2026-12-10", 0, 2_000, -2_000),
      ("2026-12-11", 4_000, 0, 4_000)],
     [(k["sana"], k["reja"], k["fakt"], k["qolgan"]) for k in _kk["kunlar"]])
_kq = next(q for q in plan.reja_va_fakt(dM, "2026-12")["qatorlar"]
           if q["turi_id"] == _boz)
teng("kunlar jami = «Reja va fakt» qatori", (_kq["reja"], _kq["fakt"]),
     (_kk["reja"], _kk["fakt"]))
_kb = plan.kun_kategoriyalari(dM, "2026-12-09")
teng("bugun: kategoriya bo'yicha — reja, bugungi rasxod, oyda qolgan",
     [(_boz, None, 10_000, 3_000, 7_000, _kk["qolgan"])],
     [(g["turi_id"], g["odam_id"], g["reja"], g["fakt"], g["qolgan"],
       g["oy_qolgan"]) for g in _kb])
teng("kun holati", ["sarflanmagan", "7\xa0000 qoldi", "rejadagidek", "500 oshdi",
                    "rejasiz"],
     [plan.kun_holati(*x) for x in ((1, 0), (10_000, 3_000), (5, 5),
                                    (1_000, 1_500), (0, 9))])
for _ in range(4):
    dM.undo()
tekshir("audit toza (kategoriya kunlari)", ledger.audit(dM).toza)

# Limit (ro'yxatsiz kategoriya rejasi) → oddiy ro'yxat
plan.budjet_qoy(dM, _boz, "2026-12", 70_000)
_rj0 = plan.turi_reja(dM, "2026-12")
_lq = plan.limitni_royxatga(dM, "2026-12", _boz)
teng("limit → ro'yxat: kategoriya rejasi o'zgarmadi", _rj0,
     plan.turi_reja(dM, "2026-12"))
teng("limit → ro'yxat: limit 0, ro'yxat summasi = limit", ({}, 70_000),
     (plan.limit_reja(dM, "2026-12"),
      dM.skalyar("SELECT summa FROM reja_qator WHERE id=?", _lq)))
dM.undo()
teng("limit → ro'yxat: bitta undo", ({_boz: 70_000}, 0),
     (plan.limit_reja(dM, "2026-12"), len(plan.reja_yozuvlari(dM, "2026-12"))))
dM.undo()

# Bitta rasxodda bir nechta mahsulot
_o1 = dM.skalyar("SELECT id FROM odam WHERE faol=1 ORDER BY id")
_kq = _rk.Qoralama(sana="2026-09-20", kim_toladi=_o1, turi_id=_mev,
                   nom="Bozor", summa=13_000, mahsulotlar=[
                       {"item_id": _ni, "miqdor": 2, "summa": 8_000},
                       {"item_id": _ni, "summa": 5_000}, {}])
_krid = _rk.saqla(dM, _kq)
teng("ko'p mahsulot: qatorlar (bo'shi tashlandi)", [8_000, 5_000],
     [x["summa"] for x in _rk.rasxod_mahsulotlari(dM, _krid)])
teng("ko'p mahsulot: rasxod bitta mahsulotga bog'lanmaydi", None,
     dM.skalyar("SELECT item_id FROM rasxod WHERE id=?", _krid, birlamchi=None))
teng("ko'p mahsulot: ulushlar yig'indisi = summa", 13_000,
     dM.skalyar("SELECT SUM(summa) FROM ulush WHERE rasxod_id=?", _krid))
tekshir("ko'p mahsulot: summa ≠ yig'indi rad etiladi", _yiqiladimi(
    lambda: _rk.saqla(dM, _rk.Qoralama(
        sana="2026-09-20", kim_toladi=_o1, turi_id=_mev, nom="x", summa=1,
        mahsulotlar=[{"item_id": _ni, "summa": 5_000}]))))
tekshir("ko'p mahsulot: summasiz qator rad etiladi", _yiqiladimi(
    lambda: _rk.saqla(dM, _rk.Qoralama(
        sana="2026-09-20", kim_toladi=_o1, turi_id=_mev, nom="x", summa=0,
        mahsulotlar=[{"item_id": _ni, "summa": 0}]))))
_kq.summa, _kq.mahsulotlar = 4_000, [{"item_id": _ni, "summa": 4_000}]
_rk.tahrirla(dM, _krid, _kq)
teng("ko'p mahsulot: tahrir — bitta qolsa unga bog'lanadi", (4_000, _ni, 1),
     (dM.skalyar("SELECT summa FROM rasxod WHERE id=?", _krid),
      dM.skalyar("SELECT item_id FROM rasxod WHERE id=?", _krid),
      len(_rk.rasxod_mahsulotlari(dM, _krid))))
tekshir("audit toza (ko'p mahsulot)", ledger.audit(dM).toza)
dM.undo()
teng("ko'p mahsulot: tahrir bitta undo", (13_000, 2),
     (dM.skalyar("SELECT summa FROM rasxod WHERE id=?", _krid),
      len(_rk.rasxod_mahsulotlari(dM, _krid))))
dM.undo()
tekshir("ko'p mahsulot: saqlash bitta undo", not dM.skalyar(
    "SELECT COUNT(*) FROM rasxod WHERE id=? AND ochirilgan=0", _krid))
tekshir("ko'p mahsulot: bot qoralamasi lug'atdan tiklanadi",
        _rk.Qoralama.lugatdan(_rk.Qoralama(sana="2026-09-20").lugat())
        == _rk.Qoralama(sana="2026-09-20"))

# Katalogda yo'q mahsulot — o'sha zahoti yoziladi, katalogga qo'shiladi
_yn = _rk.Qoralama(sana="2026-09-20", kim_toladi=_o1, turi_id=_mev,
                   nom="Yangi", summa=10_001, mahsulotlar=[
                       {"nom": "Anor (yangi)", "miqdor": 3, "summa": 10_001}])
_yrid = _rk.saqla(dM, _yn)
_yi = dM.q1("SELECT * FROM item WHERE nom='Anor (yangi)' AND ochirilgan=0")
tekshir("yangi mahsulot: katalogga qo'shildi (shu kategoriyaga)",
        _yi is not None and _yi["turi_id"] == _mev)
teng("yangi mahsulot: narx — bir dona (pastga yaxlit)", 3_333, _yi["narx"])
teng("yangi mahsulot: qator va rasxod unga bog'landi", (_yi["id"], _yi["id"]),
     (_rk.rasxod_mahsulotlari(dM, _yrid)[0]["item_id"],
      dM.skalyar("SELECT item_id FROM rasxod WHERE id=?", _yrid)))
_yq2 = plan.reja_yozuv_saqla(dM, "2026-12-01", "Anor", _mev, 5_000,
                             [{"nom": "anor (YANGI)", "summa": 5_000}])
teng("yangi mahsulot: shu nom qayta yozilsa yangisi yaratilmaydi", 1,
     dM.skalyar("SELECT COUNT(*) FROM item WHERE nom LIKE 'anor (yangi)'"
                " AND ochirilgan=0"))
teng("yangi mahsulot: rejada ham o'sha mahsulotga", _yi["id"],
     plan.reja_yozuv_mahsulotlari(dM, _yq2)[0]["item_id"])
dM.undo()
dM.undo()
tekshir("yangi mahsulot: undo — mahsulot ham, rasxod ham qaytdi",
        not dM.skalyar("SELECT COUNT(*) FROM item WHERE nom='Anor (yangi)'"
                       " AND ochirilgan=0")
        and not dM.skalyar("SELECT COUNT(*) FROM rasxod WHERE id=? AND"
                           " ochirilgan=0", _yrid))
tekshir("audit toza (yangi mahsulot)", ledger.audit(dM).toza)
dM.undo()                                     # «Reja non» katalogdan

# Rejaga band pul: sarflanmagan reja faol odamlarga TENG bo'linadi
tekshir("band: reja yo'q oyda — hech kimdan band emas",
        plan.band_pul(dM, "2026-11-05") == {})
_v0 = {r["id"]: (r["naqd"], r["adolat"]) for r in ledger.balanslar(dM)}
plan.reja_saqla(dM, "2026-09", _rf["fakt"] + 100_000, {})
_band = plan.band_pul(dM, "2026-09-15")
teng("band: yig'indisi = sarflanmagan reja", 100_000, sum(_band.values()))
teng("band: hamma faol odamdan", {r["id"] for r in ledger.balanslar(dM)},
     set(_band))
tekshir("band: teng (farq ko'pi bilan 1 so'm)",
        max(_band.values()) - min(_band.values()) <= 1)
_dj = {x["id"]: x["naqd"] for x in ledger.darajalar(dM, _band)}
tekshir("band: darajalarda qo'ldagi puldan ayirildi",
        all(_dj[i] == _v0[i][0] - _band[i] for i in _band))
teng("band: v_balans o'zgarmadi (faqat ko'rsatish)", _v0,
     {r["id"]: (r["naqd"], r["adolat"]) for r in ledger.balanslar(dM)})
plan.reja_saqla(dM, "2026-09", max(1, _rf["fakt"] - 5_000), {})
tekshir("band: reja oshib ketsa — band 0",
        plan.band_pul(dM, "2026-09-15") == {})
plan.reja_yozuv_saqla(dM, "2026-09-05", "Kitoblar", _boz, 7_000,
                      umumiymi=False, odam_id=mF)
teng("band: shaxsiy reja qolgani — faqat o'sha odamdan", {mF: 7_000},
     plan.band_pul(dM, "2026-09-15"))
dM.undo()
dM.undo()
dM.undo()
tekshir("audit toza (band)", ledger.audit(dM).toza)

# Yon panel: faqat asosiy odamning puli; boshqada pul bo'lmasa band undan
plan.reja_saqla(dM, plan.oy_kaliti(), 10_000_000, {})
_qp = plan.qoldagi_pul(dM)
_bp = plan.band_pul(dM)
_nq = {r["id"]: r["naqd"] for r in ledger.balanslar(dM)}
teng("qo'ldagi pul: asosiy odam — birinchi faol", dM.skalyar(
    "SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id"), _qp["odam_id"])
teng("qo'ldagi pul: o'z bandi + boshqalarning yetmagani, qo'ldagidan ko'p emas",
     min(max(0, _nq[_qp["odam_id"]]), _bp.get(_qp["odam_id"], 0) + sum(
         max(0, b - max(0, _nq.get(o, 0))) for o, b in _bp.items()
         if o != _qp["odam_id"])), _qp["band"])
tekshir("qo'ldagi pul: rejadan minusga tushmaydi",
        _qp["qoldi"] >= min(0, _nq[_qp["odam_id"]]))
teng("qo'ldagi pul = naqd − band", _nq[_qp["odam_id"]] - _qp["band"],
     _qp["qoldi"])
dM.undo()

# «Qarzim»: ichki + tashqi, juft_qarzlar va tashqi_qarzlar bilan bir xil
for _o in (mF, mO):
    _q = plan.ledger.odam_qarzlari(dM, _o)
    teng(f"qarzim ({_o}): ichki = juftlikdagi qarzi", sum(
        j.summa for j in ledger.juft_qarzlar(dM) if j.qarzdor_id == _o),
        _q["ichki_jami"])
    teng(f"qarzim ({_o}): tashqi = ochiq tashqi qarz qoldig'i", sum(
        t["qoldiq"] for t in ledger.tashqi_qarzlar(dM, True)
        if t["odam_id"] == _o), _q["tashqi_jami"])
    teng(f"qarzim ({_o}): jami", _q["ichki_jami"] + _q["tashqi_jami"],
         _q["jami"])

# Kategoriya o'chirish himoyasi
tekshir("ichida ichki kategoriya bor — o'chmaydi",
        _yiqiladimi(lambda: mh.kategoriya_ochir(dM, _mev)))
tekshir("ichida mahsulot bor — o'chmaydi",
        _yiqiladimi(lambda: mh.kategoriya_ochir(dM, _sut)))
mh.kategoriya_ochir(dM, _sab)
tekshir("bo'sh kategoriya o'chdi (faol=0, qator joyida)",
        dM.skalyar("SELECT faol FROM turi WHERE id=?", _sab) == 0)
teng("qayta qo'shilsa — o'sha qator tiriladi", _sab,
     mh.kategoriya_qosh(dM, "Sabzavotlar", _boz,
                        rasm=mh.bosh_belgilar(dM)[0]))
mh.kategoriya_nomla(dM, _sab, "Ko'katlar")
teng("nomi o'zgardi", "Ko'katlar", dM.skalyar("SELECT nom FROM turi WHERE id=?", _sab))

# Mavjud kategoriyani boshqasining ichiga ko'chirish (Gigiena → Bozorlik)
_gig = mh.kategoriya_qosh(dM, "Gigiena sinov")
entries.rasxod_qosh(dM, "2026-09-22", "sovun", 15_000, mF, umumiymi=False,
                    turi_id=_gig)
_tb0 = {t["nom"]: t["summa"] for t in ledger.turi_boyicha(dM, "2026-09-01",
                                                           "2026-09-30")}
teng("ko'chirishdan oldin — alohida bo'lak", 15_000, _tb0.get("Gigiena sinov"))
tekshir("ko'chish joylari: o'zi va avlodlari yo'q",
        not {_mev, _tro} & {t["id"] for t, _ in mh.kochish_joylari(dM, _mev)}
        and _boz in {t["id"] for t, _ in mh.kochish_joylari(dM, _mev)})
mh.kategoriya_kochir(dM, _gig, _boz)
teng("ko'chdi — yo'l", "Bozorlik › Gigiena sinov", mh.yol_nomi(dM, _gig))
_tb1 = {t["nom"]: t["summa"] for t in ledger.turi_boyicha(dM, "2026-09-01",
                                                           "2026-09-30")}
teng("doira: rasxodi yangi otasiga qo'shildi", _tb0["Bozorlik"] + 15_000,
     _tb1.get("Bozorlik"))
tekshir("doirada endi alohida bo'lak emas", "Gigiena sinov" not in _tb1)
teng("eski rasxodning kategoriyasi o'zgarmadi", 1, dM.skalyar(
    "SELECT COUNT(*) FROM rasxod WHERE turi_id=? AND ochirilgan=0", _gig))
tekshir("o'z avlodining ichiga ko'chmaydi (halqa)",
        _yiqiladimi(lambda: mh.kategoriya_kochir(dM, _mev, _tro)))
tekshir("o'zining ichiga ko'chmaydi",
        _yiqiladimi(lambda: mh.kategoriya_kochir(dM, _boz, _boz)))
mh.kategoriya_kochir(dM, _mev, _gig)       # ichki kategoriyasi bilan birga
teng("ichki kategoriya ham birga ko'chdi",
     "Bozorlik › Gigiena sinov › Mevalar › Tropik", mh.yol_nomi(dM, _tro))
dM.undo()
teng("undo — joyiga qaytdi", "Bozorlik › Mevalar", mh.yol_nomi(dM, _mev))
mh.kategoriya_kochir(dM, _gig, None)
teng("asosiyga qaytarish", "Gigiena sinov", mh.yol_nomi(dM, _gig))
tekshir("audit toza (ko'chirish)", ledger.audit(dM).toza)

# Rasm
_png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")
_manba = _TMP / "olma.png"
_manba.write_bytes(_png)
_f = mh.rasm_qoy(dM, _banan, _manba)
tekshir("rasm dastur papkasiga nusxalandi", mh.rasm_yoli(_f) is not None)
_manba.unlink()
tekshir("asl fayl o'chsa ham rasm qoladi", mh.rasm_yoli(_f) is not None)
mh.rasm_olib_tashla(dM, _banan)
tekshir("rasm olib tashlandi",
        dM.q1("SELECT rasm FROM item WHERE id=?", _banan)["rasm"] is None)
tekshir("fayl diskda qoldi (undo uchun)", (config.MAHSULOT_RASM / _f).exists())
dM.undo()
teng("undo — rasm qaytdi", _f, dM.skalyar("SELECT rasm FROM item WHERE id=?", _banan))
tekshir("noto'g'ri tur rad", _yiqiladimi(
    lambda: mh.rasm_baytdan(dM, _banan, b"x", ".exe")))
tekshir("bo'sh rasm rad", _yiqiladimi(
    lambda: mh.rasm_baytdan(dM, _banan, b"", ".jpg")))
tekshir("rasmsiz mahsulotda rasm_yoli None — xato yo'q",
        mh.rasm_yoli(None) is None and mh.rasm_yoli("yoq.jpg") is None)

# Telegram: telefondan rasm
dM.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, mF)
_tg = []


def _tg_sorov(token, metod, **m):
    _tg.append((metod, m))
    return {"file_path": "photos/file_7.jpg"} if metod == "getFile" else {}


_asl_sorov, _asl_yukla = xb._sorov, xb._fayl_yukla
xb._sorov = _tg_sorov
xb._fayl_yukla = lambda token, yol: _png
try:
    def _rasm_xabar(izoh, kim="fsultonoov", tur="private"):
        return {"chat": {"id": 55, "type": tur}, "from": {"username": kim},
                "caption": izoh,
                "photo": [{"file_id": "kichik", "width": 90, "height": 90},
                          {"file_id": "orta", "width": 1280, "height": 960},
                          {"file_id": "katta", "width": 4000, "height": 3000}]}
    teng("izohdagi nom bo'yicha biriktirildi", "rasm: Sut",
         xb._rasmni_ishla(dM, _rasm_xabar("  sut "), "T"))
    tekshir("mahsulotga rasm yozildi",
            dM.q1("SELECT rasm FROM item WHERE id=?", _sut_m)["rasm"] is not None)
    teng("1280 dan katta bo'lmagan eng katta o'lcham olindi", "orta",
         next(m for mt, m in _tg if mt == "getFile")["file_id"])
    tekshir("javob yuborildi", any(mt == "sendMessage" and "✔" in m["text"]
                                   for mt, m in _tg))
    teng("topilmasa — xabar", "rasm: topilmadi (Qovun)",
         xb._rasmni_ishla(dM, _rasm_xabar("Qovun"), "T"))
    teng("izohsiz — xabar", "rasm: izohsiz",
         xb._rasmni_ishla(dM, _rasm_xabar(""), "T"))
    tekshir("notanish odam rasmi e'tiborsiz",
            xb._rasmni_ishla(dM, _rasm_xabar("Sut", kim="begona"), "T") is None)
    tekshir("guruhdagi rasm e'tiborsiz",
            xb._rasmni_ishla(dM, _rasm_xabar("Sut", tur="group"), "T") is None)
finally:
    xb._sorov, xb._fayl_yukla = _asl_sorov, _asl_yukla
dM.yop()


# ═════════════════════════════════════════ Telegram orqali rasxod

print("\n── Telegram rasxod ──")
from core import rasxod_kirit as rk  # noqa: E402
from core import tg_rasxod as tr  # noqa: E402
dX2 = dbm.Db(_TMP / "bX2.db", zaxirasiz=True)
xF2 = entries.odam_qosh(dX2, "Fayzulloxon")
xO2 = entries.odam_qosh(dX2, "Otabek")
xA2 = entries.odam_qosh(dX2, "Abbosxon")
dX2.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, xF2)
dX2.apply("odam", "UPDATE", {"telegram": "otabek"}, xO2)
_bz2 = dX2.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
_tr2 = dX2.skalyar("SELECT id FROM turi WHERE nom='Transport'")
_mv2 = mh.kategoriya_qosh(dX2, "Mevalar", _bz2,
                          rasm=mh.bosh_belgilar(dX2)[0])
_ol2 = mh.saqla(dX2, nom="Olma", turi_id=_mv2, narx=18_000, miqdor=1, olchov="kg")
mh.rasm_baytdan(dX2, _ol2, _png, ".png")
xb.sozlama_qoy(dX2, token="T", guruh="-100", yoqilgan=True)

_tq, _rasmlar, _navbat = [], [], []
_mid = [100]


def _tq_sorov(token, metod, **m):
    m.pop("_vaqt", None)
    _tq.append((metod, m))
    if metod == "sendMessage":
        _mid[0] += 1
        return {"message_id": _mid[0]}
    if metod == "getUpdates":
        u, _navbat[:] = list(_navbat), []
        return u
    return {}


_asl_sorov2, _asl_rasm2 = xb._sorov, getattr(xb, "_rasm_yubor", None)
xb._sorov = _tq_sorov
xb._rasm_yubor = lambda token, chat, yol, izoh: _rasmlar.append((chat, izoh))
_CHAT = 555
_BUGUN = "2026-09-25"


def _tugma(data, mid=None, kim=xF2):
    h = tr.holat_ol(dX2, _CHAT)
    cb = {"id": "c", "data": data, "from": {"username": "fsultonoov"},
          "message": {"message_id": mid or (h or {}).get("xabar"),
                      "chat": {"id": _CHAT, "type": "private"}}}
    return tr.tugma_bosildi(dX2, "T", cb, kim)


def _matn(t, kim=xF2):
    return tr.matn_keldi(dX2, "T", {"chat": {"id": _CHAT, "type": "private"},
                                    "text": t}, kim)


def _oxirgi_klav():
    for mt, m in reversed(_tq):
        if "reply_markup" in m and "inline_keyboard" in m["reply_markup"]:
            return [b["callback_data"] for q in json.loads(
                m["reply_markup"])["inline_keyboard"] for b in q]
    return []


import json  # noqa: E402
try:
    # ── 1. Mahsulot bilan, umumiy, bir odam chiqarilgan, kecha ──────────
    tr.boshlash(dX2, "T", _CHAT, xF2, bugun=_BUGUN)
    tekshir("boshlandi: kategoriyalar ko'rinadi", f"rx:k:{_bz2}" in _oxirgi_klav())
    _tugma(f"rx:k:{_bz2}")
    tekshir("ichki kategoriyasi bor — ichiga kirdi",
            tr.holat_ol(dX2, _CHAT)["ota"] == _bz2
            and f"rx:kt:{_bz2}" in _oxirgi_klav() and f"rx:k:{_mv2}" in _oxirgi_klav())
    _tugma(f"rx:k:{_mv2}")
    teng("kategoriya → mahsulot qadami", "mah", tr.holat_ol(dX2, _CHAT)["qadam"])
    tekshir("mahsulot ro'yxatda", f"rx:m:{_ol2}" in _oxirgi_klav())
    _tugma(f"rx:m:{_ol2}")
    _h = tr.holat_ol(dX2, _CHAT)
    teng("mahsulotdan nom va narx (umumiy qoida)", ("Olma", 18_000),
         (_h["q"].nom, _h["q"].summa))
    tekshir("mahsulot rasmi va ma'lumoti yuborildi",
            _rasmlar and "Olma" in _rasmlar[-1][1] and "Mevalar" in _rasmlar[-1][1])
    _tugma("rx:n")
    _tugma("rx:s")
    _tugma(f"rx:p:{xF2}")
    _tugma("rx:t:u")
    teng("umumiy — uydagilar belgilangan", {xF2, xO2, xA2},
         set(tr.holat_ol(dX2, _CHAT)["q"].parametrlar))
    _tugma(f"rx:q:{xA2}")
    teng("Abbosxon olib tashlandi", {xF2, xO2},
         set(tr.holat_ol(dX2, _CHAT)["q"].parametrlar))
    _tugma("rx:qd")
    _tugma("rx:d:1")
    teng("kecha tanlandi", "2026-09-24", tr.holat_ol(dX2, _CHAT)["q"].sana)
    _xabar_oldin = tr.holat_ol(dX2, _CHAT)["xabar"]
    _r = _tugma("rx:ok")
    tekshir("saqlandi", _r.startswith("rx: saqlandi"))
    _rid = int(_r.split("#")[1])
    _rx = dX2.q1("SELECT * FROM rasxod WHERE id=?", _rid)
    teng("rasxod maydonlari", ("2026-09-24", "Olma", 18_000, _mv2, _ol2, xF2, 1),
         (_rx["sana"], _rx["nom"], _rx["summa"], _rx["turi_id"], _rx["item_id"],
          _rx["kim_toladi"], _rx["umumiymi"]))
    teng("ulushlar — faqat tanlanganlarga", {xF2: 9_000, xO2: 9_000},
         {r["odam_id"]: r["summa"] for r in dX2.q(
             "SELECT odam_id, summa FROM ulush WHERE rasxod_id=?", _rid)})
    tekshir("suhbat tozalandi", tr.holat_ol(dX2, _CHAT) is None)
    tekshir("«Bekor qilish» tugmasi bor", f"rx:del:{_rid}" in _oxirgi_klav())

    # Dasturdagi oyna bilan AYNAN bir xil natija
    _q = rk.Qoralama(sana="2026-09-24", kim_toladi=xF2, turi_id=_mv2,
                     tur=rk.UMUMIY, parametrlar={xF2: 1.0, xO2: 1.0})
    rk.mahsulot_tanla(dX2, _q, _ol2)
    _rid_d = rk.saqla(dX2, _q)
    _qat = "SELECT sana,nom,summa,turi_id,item_id,kim_toladi,umumiymi,kim_uchun FROM rasxod WHERE id=?"
    teng("bot va dastur — bir xil rasxod", tuple(dX2.q1(_qat, _rid_d)),
         tuple(dX2.q1(_qat, _rid)))
    teng("bot va dastur — bir xil ulushlar",
         [tuple(r) for r in dX2.q("SELECT odam_id, summa FROM ulush WHERE rasxod_id=? ORDER BY odam_id", _rid_d)],
         [tuple(r) for r in dX2.q("SELECT odam_id, summa FROM ulush WHERE rasxod_id=? ORDER BY odam_id", _rid)])
    entries.rasxod_ochir(dX2, _rid_d)

    # ── 2. Matn bilan: mahsulotsiz kategoriya, boshqa uchun ────────────
    tr.boshlash(dX2, "T", _CHAT, xO2, bugun=_BUGUN)
    _tugma(f"rx:k:{_tr2}", kim=xO2)
    teng("mahsuloti yo'q — to'g'ri sababga", "nom", tr.holat_ol(dX2, _CHAT)["qadam"])
    _matn("Taksi", kim=xO2)
    _matn("abc", kim=xO2)
    teng("noto'g'ri summa — o'sha qadamda qoladi", "summa",
         tr.holat_ol(dX2, _CHAT)["qadam"])
    _matn("25 000", kim=xO2)
    teng("summa o'qildi", 25_000, tr.holat_ol(dX2, _CHAT)["q"].summa)
    teng("to'lovchi — yozgan odam", xO2, tr.holat_ol(dX2, _CHAT)["q"].kim_toladi)
    _tugma(f"rx:p:{xO2}", kim=xO2)
    _tugma("rx:t:b", kim=xO2)
    tekshir("«kim uchun» da to'lovchi yo'q", f"rx:u:{xO2}" not in _oxirgi_klav())
    _tugma(f"rx:u:{xF2}", kim=xO2)
    _r2 = _tugma("rx:ok", kim=xO2)
    _rid2 = int(_r2.split("#")[1])
    _rx2 = dX2.q1("SELECT * FROM rasxod WHERE id=?", _rid2)
    teng("boshqa uchun saqlandi", (xO2, xF2, "Taksi", _tr2, None),
         (_rx2["kim_toladi"], _rx2["kim_uchun"], _rx2["nom"], _rx2["turi_id"],
          _rx2["item_id"]))
    teng("u qarzdor bo'ldi (to'liq ulush)", 25_000, dX2.skalyar(
        "SELECT summa FROM ulush WHERE rasxod_id=? AND odam_id=?", _rid2, xF2))

    # ── 3. Tekshiruv botda ham xuddi dasturdagidek to'xtatadi ──────────
    tr.boshlash(dX2, "T", _CHAT, xF2, bugun=_BUGUN)
    _tugma(f"rx:k:{_tr2}")
    _matn("Avtobus")
    _matn("5000")
    _tugma(f"rx:p:{xF2}")
    _tugma("rx:t:u")
    for _o in (xF2, xO2, xA2):
        _tugma(f"rx:q:{_o}")
    _tugma("rx:qd")
    _oldin = dX2.skalyar("SELECT COUNT(*) FROM rasxod")
    _tugma("rx:ok")
    teng("hech kim tanlanmasa saqlanmaydi", _oldin,
         dX2.skalyar("SELECT COUNT(*) FROM rasxod"))
    teng("xato matni — dasturdagi bilan bir xil",
         "Kamida bitta odam tanlangan bo'lishi kerak.",
         tr.holat_ol(dX2, _CHAT)["xato"])
    _matn("/bekor")
    tekshir("/bekor — suhbat tozalandi", tr.holat_ol(dX2, _CHAT) is None)

    # ── 4. Eski xabar, bekor qilish, ruxsat ────────────────────────────
    teng("eski xabardagi tugma e'tiborsiz", "rx: eski", _tugma("rx:t:u", mid=1))
    _tugma(f"rx:del:{_rid}", mid=999)
    teng("«Bekor qilish» — rasxod o'chdi", 1,
         dX2.skalyar("SELECT ochirilgan FROM rasxod WHERE id=?", _rid))
    teng("ikkinchi marta — tegmaydi", "rx: del (yo'q)",
         _tugma(f"rx:del:{_rid}", mid=999))
    teng("summa: nuqtali", 25_000, tr._summa_oqi("25.000"))
    teng("summa: so'm bilan", 7_000, tr._summa_oqi("7000 so'm"))
    tekshir("summa: manfiy/harf rad",
            tr._summa_oqi("-5") is None and tr._summa_oqi("besh") is None)

    # To'liq yo'l: getUpdates → xabar.py → tg_rasxod
    _off = int(dX2.sozlama("tg_offset", "0") or 0)
    _navbat[:] = [
        {"update_id": 900, "message": {"chat": {"id": _CHAT, "type": "private"},
                                       "from": {"username": "fsultonoov"},
                                       "text": "➕ Rasxod"}},
        {"update_id": 901, "message": {"chat": {"id": 777, "type": "private"},
                                       "from": {"username": "begona"},
                                       "text": "/rasxod"}},
        {"update_id": 902, "message": {"chat": {"id": -100, "type": "group"},
                                       "from": {"username": "fsultonoov"},
                                       "text": "/rasxod"}},
    ]
    _nat = xb.tugmalarni_qayta_ishla(dX2)
    tekshir("uy a'zosi shaxsiy chatda — boshlandi", "rx: boshlandi" in _nat)
    tekshir("begona va guruh — e'tiborsiz",
            _nat.count("rx: boshlandi") == 1 and tr.holat_ol(dX2, 777) is None
            and tr.holat_ol(dX2, -100) is None)
    teng("offset surildi", "903", dX2.sozlama("tg_offset"))
    _navbat[:] = [{"update_id": 903, "callback_query": {
        "id": "z", "data": "rx:x", "from": {"username": "fsultonoov"},
        "message": {"message_id": tr.holat_ol(dX2, _CHAT)["xabar"],
                    "chat": {"id": _CHAT, "type": "private"}}}}]
    teng("tugma ham xabar.py orqali yetib keladi", ["rx: bekor"],
         xb.tugmalarni_qayta_ishla(dX2))
    teng("uzun so'rov: timeout Telegramga beriladi", 20, next(
        m for mt, m in reversed(_tq) if mt == "getUpdates") and (
        xb.tugmalarni_qayta_ishla(dX2, kutish=20) or True) and next(
        m for mt, m in reversed(_tq) if mt == "getUpdates")["timeout"])
    tekshir("audit toza", ledger.audit(dX2).toza)

    # ── 5. Menyu: Moliya va Vazifalar ──────────────────────────────────
    from core import tg_menyu as tm  # noqa: E402
    teng("/start — asosiy menyu", [[tm.MOLIYA, tm.VAZIFALAR]],
         tm.javob(dX2, "/start", xF2)[1])
    _mm = [t for q in tm.javob(dX2, tm.MOLIYA, xF2)[1] for t in q]
    teng("Moliya menyusi — faqat kerakli bo'limlar",
         [tm.PULIM, tm.AYLANMA, tm.TASHQI, tm.RASXOD, tm.ASOSIY], _mm)
    tekshir("olib tashlanganlar menyuda yo'q",
            not any(x in t for t in _mm for x in
                    ("Qancha qarzim", "Otabekdan", "Abbosxondan", "Fayzulloxondan")))
    teng("Vazifalar menyusi: Uy ishlari, Shaxsiy ishlar, Universitet",
         [["🏠 Uy ishlari", "🔒 Shaxsiy ishlar"], ["🎓 Universitet"], [tm.ASOSIY]],
         tm.javob(dX2, tm.VAZIFALAR, xF2)[1])
    tekshir("eski tugma matni ham ishlaydi",
            "Universitet" in (tm.javob(dX2, "🎓 Bugun qanday darslarim bor", xF2)
                              or ("",))[0])
    tekshir("qo'lda «universitet» — darslar",
            "Universitet" in (tm.javob(dX2, "universitet", xF2) or ("",))[0])

    # Pul — dasturdagi `v_balans` bilan aynan bir xil son
    _bF = ledger.balans(dX2, xF2)
    tekshir("«Qancha pulim bor» — naqd va adolat dasturdagidek",
            money.fmt_som(_bF["naqd"]) in tm.pulim(dX2, xF2)
            and money.fmt_som(_bF["adolat"]) in tm.pulim(dX2, xF2))
    _juft = {(j.qarzdor_id, j.kreditor_id): j.summa for j in ledger.juft_qarzlar(dX2)}
    teng("test holati: Fayzulloxon Otabekka qarzdor",
         True, (xF2, xO2) in _juft)
    tekshir("aylanma — hamma juftlik",
            all(money.fmt_som(s) in tm.aylanma(dX2) for s in _juft.values()))
    entries.tashqi_qarz_qosh(dX2, "2026-09-20", xF2, "Aziz aka", 40_000, "telefon")
    tekshir("tashqi qarz — o'zinikida bor", "Aziz aka" in tm.tashqi(dX2, xF2))
    tekshir("tashqi qarz — boshqanikida yo'q", "Aziz aka" not in tm.tashqi(dX2, xO2))

    # Vazifa, dars va shaxsiy ish — ALOHIDA
    _kun = _date(2026, 9, 25)
    _ttur = vz.tur_qosh(dX2, "Kitob o'qish", shaxsiy=True)
    vz.tur_qosh(dX2, "Algoritmlar", shaxsiy=True)
    vz.qosh(dX2, "Idish yuvish", xF2, _kun, "20:00")
    vz.qosh(dX2, "Kitob o'qish", xF2, _kun, "21:00")
    _dv = vz.qosh(dX2, "Algoritmlar", xF2, _kun, "09:00", izoh="Karimov · B-204")
    dX2.apply("vazifa", "UPDATE", {"manba": "dars:2026-09-25:1"}, _dv)
    vz.qosh(dX2, "Idish yuvish", xO2, _kun, "20:00")
    teng("uy vazifasi — faqat uyniki", ["Idish yuvish"],
         [v["nom"] for v in tm.bugungi(dX2, xF2, "uy", _kun)])
    teng("dars — faqat dars (shaxsiy turi bo'lsa ham)", ["Algoritmlar"],
         [v["nom"] for v in tm.bugungi(dX2, xF2, "dars", _kun)])
    teng("shaxsiy — darssiz", ["Kitob o'qish"],
         [v["nom"] for v in tm.bugungi(dX2, xF2, "shaxsiy", _kun)])
    tekshir("dars izohi (o'qituvchi · xona) ko'rinadi",
            "B-204" in tm.darslar(dX2, xF2, _kun))
    tekshir("boshqa odamning vazifasi chiqmaydi",
            len(tm.bugungi(dX2, xF2, "uy", _kun)) == 1)
    tekshir("bo'sh kun — tushunarli javob",
            "biriktirilmagan" in tm.uy_vazifalari(dX2, xA2, _kun))

    # Router: menyu tugmasi → reply keyboard; rasxod suhbati buzilmaydi
    _tq.clear()
    _navbat[:] = [{"update_id": 950, "message": {
        "chat": {"id": _CHAT, "type": "private"},
        "from": {"username": "fsultonoov"}, "text": tm.MOLIYA}}]
    teng("«Moliya» xabar.py orqali", ["menyu: 💰 Moliya"],
         xb.tugmalarni_qayta_ishla(dX2))
    _km = next(m for mt, m in _tq if mt == "sendMessage")["reply_markup"]
    tekshir("javobda Moliya tugmalari (reply keyboard)",
            tm.PULIM in _km and '"is_persistent": true' in _km)
    tm.matn_keldi(dX2, "T", {"chat": {"id": _CHAT, "type": "private"},
                             "text": tm.RASXOD}, xF2)
    teng("«Rasxod yozish» — o'sha suhbat boshlandi", "kat",
         tr.holat_ol(dX2, _CHAT)["qadam"])
    _tugma(f"rx:k:{_tr2}")
    _navbat[:] = [{"update_id": 951, "message": {
        "chat": {"id": _CHAT, "type": "private"},
        "from": {"username": "fsultonoov"}, "text": tm.PULIM}}]
    xb.tugmalarni_qayta_ishla(dX2)
    teng("suhbat o'rtasida menyu bosilsa — sabab bo'lib yozilmaydi", "",
         tr.holat_ol(dX2, _CHAT)["q"].nom)
    _matn("/bekor")

    # Qo'lda yozilgan so'z ham tugmadek; tushunilmasa — jim qolmaydi
    for _yoz, _kut in (("moliya", tm.PULIM), ("MOLIYA", tm.PULIM),
                       ("vazifalar", tm.DARS), ("/menu", tm.MOLIYA)):
        tekshir(f"qo'lda «{_yoz}» — menyu ochiladi",
                any(_kut in q for q in (tm.javob(dX2, _yoz, xF2) or ("", [[]]))[1]))
    tekshir("qo'lda «qancha pulim bor?» — javob",
            "pulingiz" in (tm.javob(dX2, "qancha pulim bor?", xF2) or ("",))[0])
    tekshir("olib tashlanganlarni qo'lda yozish ham ishlamaydi",
            tm.javob(dX2, "otabekdan qarz", xF2) is None
            and tm.javob(dX2, "qancha qarzim bor", xF2) is None)
    _tq.clear()
    _navbat[:] = [{"update_id": 960, "message": {
        "chat": {"id": _CHAT, "type": "private"},
        "from": {"username": "fsultonoov"}, "text": "salom"}}]
    teng("tushunarsiz matn — javobsiz qolmaydi", ["menyu: tushunmadim"],
         xb.tugmalarni_qayta_ishla(dX2))
    tekshir("tushunmadim — menyu tugmalari bilan", tm.MOLIYA in next(
        m for mt, m in _tq if mt == "sendMessage")["reply_markup"])

    # xabarchi: uzun so'rov oynasi reja oralig'idan oshmaydi
    import xabarchi as _xch  # noqa: E402
    _soat = [0.0]
    _kutishlar, _eslatmalar = [], []

    class _SoxtaXabar:
        @staticmethod
        def tugmalarni_qayta_ishla(baza, kutish=0):
            _kutishlar.append(kutish)
            _soat[0] += kutish or 1
            return []

        @staticmethod
        def yubor_kutilayotgan(baza, hozir, sinov=False):
            _eslatmalar.append(_soat[0])
            return []

    _asl_mono = _xch.time.monotonic
    _xch.time.monotonic = lambda: _soat[0]
    try:
        _xch._tingla(_SoxtaXabar, None)
    finally:
        _xch.time.monotonic = _asl_mono
    tekshir("tinglash reja oralig'idan (300 s) oldin tugaydi",
            _soat[0] <= _xch.ISH_VAQTI < 300)
    tekshir("har so'rov Telegram chegarasidan (50 s) oshmaydi",
            max(_kutishlar) <= _xch.SOROV_VAQTI <= 50)
    tekshir("tinglash paytida eslatma har daqiqada tekshiriladi",
            len(_eslatmalar) >= 3)

    class _XatoXabar(_SoxtaXabar):
        @staticmethod
        def tugmalarni_qayta_ishla(baza, kutish=0):
            _kutishlar.append("x")
            return ["Xato: tarmoq yo'q"]
    _kutishlar.clear()
    _soat[0] = 0.0
    _asl_uxla = _xch.time.sleep
    _xch.time.monotonic = lambda: _soat[0]
    _xch.time.sleep = lambda t: _soat.__setitem__(0, _soat[0] + t)
    try:
        _xch._tingla(_XatoXabar, None, 0.0)
    finally:
        _xch.time.monotonic, _xch.time.sleep = _asl_mono, _asl_uxla
    tekshir("tarmoq xatosidan keyin chiqib ketmaydi — qayta urinadi",
            len(_kutishlar) > 10)
    tekshir("xato bo'lsa ham oyna vaqtida tugaydi", _soat[0] <= _xch.ISH_VAQTI)

    # Doimiy rejim: vaqt bilan tugamaydi, faqat `toxta()` (kod o'zgardi)
    _kutishlar.clear()
    _eslatmalar.clear()
    _davr = []
    _soat[0] = 0.0
    _xch.time.monotonic = lambda: _soat[0]
    try:
        sabab = _xch._tingla(_SoxtaXabar, None, 0.0, ish_vaqti=None,
                             toxta=lambda: _soat[0] > 3_600,
                             davriy=lambda b: _davr.append(_soat[0]))
    finally:
        _xch.time.monotonic = _asl_mono
    teng("doimiy rejim: faqat kod o'zgarganda to'xtaydi", "toxta", sabab)
    tekshir("doimiy rejim: soat davomida eslatma har daqiqada",
            len(_eslatmalar) >= 55)
    tekshir("doimiy rejim: davriy ishlar ~10 daqiqada bir",
            5 <= len(_davr) <= 7)
    tekshir("doimiy rejim: so'rov eslatmani kechiktirmaydi",
            all(k <= _xch.ESLATMA_ORALIQ for k in _kutishlar))

    # Bitta nusxa: qulf band bo'lsa ikkinchisi ololmaydi
    _ql = _TMP / "sinov.lock"
    _q1 = _xch._qulfla(_ql)
    _q2 = _xch._qulfla(_ql)
    tekshir("bitta nusxa: ikkinchi qulf olinmaydi", _q1 is not None and _q2 is None)
    if _q1:
        _q1.close()
    _q3 = _xch._qulfla(_ql)
    tekshir("qulf bo'shagach — yana olinadi", _q3 is not None)
    if _q3:
        _q3.close()
finally:
    xb._sorov = _asl_sorov2
    if _asl_rasm2:
        xb._rasm_yubor = _asl_rasm2
dX2.yop()


# ═════════════════════════════════════ analitika — odam bo'yicha filtr

print("\n── Analitika: odam filtri va kategoriya ichi ──")
dAn = dbm.Db(_TMP / "bAn.db", zaxirasiz=True)
aF = entries.odam_qosh(dAn, "Fayzulloxon")
aO = entries.odam_qosh(dAn, "Otabek")
aB = entries.odam_qosh(dAn, "Bobur")
_aboz = dAn.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
_akiy = dAn.skalyar("SELECT id FROM turi WHERE nom<>'Bozorlik'"
                    " AND ota_id IS NULL ORDER BY id LIMIT 1")
_ameva = mh.kategoriya_qosh(dAn, "Mevalar", _aboz,
                            rasm=mh.bosh_belgilar(dAn)[0])
_A1, _A2 = "2026-09-01", "2026-09-30"
# umumiy 90 000 (uchga teng), Mevalar ichki kategoriyada
entries.rasxod_qosh(dAn, "2026-09-02", "bozor", 90_000, aF, turi_id=_aboz)
entries.rasxod_qosh(dAn, "2026-09-03", "olma", 30_000, aO, turi_id=_ameva)
# Fayzulloxonning shaxsiy rasxodi
entries.rasxod_qosh(dAn, "2026-09-04", "kiyim", 50_000, aF, umumiymi=False,
                    turi_id=_akiy)
# Otabek Fayzulloxon UCHUN olgan — Fayzulloxonning shaxsiysi
entries.rasxod_qosh(dAn, "2026-09-05", "poyabzal", 70_000, aO,
                    turi_id=_akiy, kim_uchun=aF)
# oraliqdan tashqarida — hisobga kirmaydi
entries.rasxod_qosh(dAn, "2026-10-01", "oktabr", 99_000, aF, umumiymi=False,
                    turi_id=_akiy)

_ax = ledger.odam_rasxod_xulosa(dAn, aF, _A1, _A2)
teng("odam: shaxsiy = o'zi + uning uchun olingan", 120_000, _ax["shaxsiy"])
teng("odam: umumiy = faqat ULUSHI (butun summa emas)", 40_000, _ax["umumiy"])
teng("odam: jami", 160_000, _ax["jami"])
# v_balans butun davrni ko'radi — solishtirish ham butun davr bilan
_bal = {b["id"]: b for b in dAn.q("SELECT * FROM v_balans")}
_axh = ledger.odam_rasxod_xulosa(dAn, aF, "2000-01-01", "2100-12-31")
teng("odam: v_balans bilan bir xil (shaxsiy + uchun_ulush)",
     _bal[aF]["shaxsiy"] + _bal[aF]["uchun_ulush"], _axh["shaxsiy"])
teng("odam: v_balans bilan bir xil (umumiy_ulush)",
     _bal[aF]["umumiy_ulush"], _axh["umumiy"])
_atb = {t["turi_id"]: t for t in ledger.turi_boyicha(dAn, _A1, _A2, aF, "umumiy")}
teng("odam: ichki kategoriya ulushi otasiga qo'shildi", 40_000,
     _atb[_aboz]["summa"])
tekshir("odam: umumiyda shaxsiy kategoriya yo'q", _akiy not in _atb)
teng("odam: uch kishining ulushi = uyning umumiy rasxodi", 120_000,
     sum(ledger.odam_rasxod_xulosa(dAn, o, _A1, _A2)["umumiy"]
         for o in (aF, aO, aB)))
teng("filtrsiz — eskicha, uyning butun rasxodi", 240_000,
     sum(t["summa"] for t in ledger.turi_boyicha(dAn, _A1, _A2)))
_adoira = ledger.doira_bolaklari(dAn, _A1, _A2, odam_id=aF, qism="hammasi")
teng("doira (odam): yig'indi = jami", 160_000,
     sum(b["summa"] for b in _adoira))
teng("doira (odam): ulush 100%", 1000, sum(b["ulush"] for b in _adoira))
_akj = ledger.kategoriya_jadvali(dAn, _A1, _A2, aF, "shaxsiy")
teng("jadval (odam, shaxsiy)", 120_000, sum(t["summa"] for t in _akj))

# Kategoriya ichi: har rasxod, yig'indisi bo'lakdagi songa teng
_aich = ledger.kategoriya_rasxodlari(dAn, [_aboz], _A1, _A2)
teng("ichi: Bozorlik — ichki kategoriya rasxodi ham", 2, len(_aich))
teng("ichi: yig'indi = bo'lak", 120_000, sum(x["summa"] for x in _aich))
_aich = ledger.kategoriya_rasxodlari(dAn, [_aboz], _A1, _A2, aF, "hammasi")
teng("ichi (odam): faqat ulushi", 40_000, sum(x["summa"] for x in _aich))
teng("ichi (odam): butun summa ham bor", 120_000, sum(x["jami"] for x in _aich))
_aich = ledger.kategoriya_rasxodlari(dAn, [_akiy], _A1, _A2, aF, "shaxsiy")
teng("ichi (odam, shaxsiy): kiyim + poyabzal", {"kiyim", "poyabzal"},
     {x["nom"] for x in _aich})
tekshir("ichi: oraliqdan tashqarisi yo'q",
        all(x["nom"] != "oktabr" for x in _aich))
teng("ichi: bo'sh ro'yxat", [],
     ledger.kategoriya_rasxodlari(dAn, [], _A1, _A2))
entries.rasxod_qosh(dAn, "2026-09-06", "nomsiz", 6_000, aF, umumiymi=False)
teng("ichi: «Kategoriyasiz»", ["nomsiz"],
     [x["nom"] for x in ledger.kategoriya_rasxodlari(dAn, [None], _A1, _A2)])
_aql = ledger.doira_bolaklari(dAn, _A1, _A2, korsat=1)
_anomli = {t["turi_id"] for t in ledger.turi_boyicha(dAn, _A1, _A2)
           if t["turi_id"] is not None}
teng("doira: «Qolganlari» ichida birinchisidan boshqa hammasi",
     _anomli - {_aql[0]["turi_id"]},
     set(next(b for b in _aql if b["tur"] == "qolgan")["idlar"]))
try:
    ledger.turi_boyicha(dAn, _A1, _A2, aF, "yolgon")
    tekshir("noma'lum qism rad etiladi", False)
except ValueError:
    tekshir("noma'lum qism rad etiladi", True)
tekshir("audit toza (analitika)", ledger.audit(dAn).toza)

# Kategoriyani ro'yxatdan almashtirish — bir nechtasi, bitta undo
_akiy2 = dAn.skalyar("SELECT id FROM turi WHERE ota_id IS NULL AND faol=1"
                     " AND id NOT IN (?, ?) ORDER BY id LIMIT 1", _aboz, _akiy)
_aitem = dAn.apply("item", "INSERT", {"nom": "Olma", "turi_id": _ameva})
_ax1 = entries.rasxod_qosh(dAn, "2026-09-07", "olma2", 12_000, aF,
                           turi_id=_ameva, item_id=_aitem)
_ax2 = entries.rasxod_qosh(dAn, "2026-09-07", "non", 8_000, aO, turi_id=_aboz)
_bal0 = [dict(r) for r in dAn.q("SELECT * FROM v_balans ORDER BY id")]
_ulush0 = dAn.q("SELECT rasxod_id, odam_id, summa FROM ulush ORDER BY id")
teng("turi: ikkitasi almashdi", 2,
     entries.rasxod_turi_qoy(dAn, [_ax1, _ax2, _ax2], _akiy2))
teng("turi: yangi kategoriya yozildi", {_akiy2},
     {r["turi_id"] for r in dAn.q("SELECT turi_id FROM rasxod WHERE id IN (?,?)",
                                  _ax1, _ax2)})
teng("turi: boshqa kategoriyaning mahsuloti bo'shatildi", None,
     dAn.skalyar("SELECT item_id FROM rasxod WHERE id=?", _ax1, birlamchi=None))
teng("turi: balansga tegmadi", _bal0,
     [dict(r) for r in dAn.q("SELECT * FROM v_balans ORDER BY id")])
teng("turi: ulushlar o'zgarmadi", [tuple(r) for r in _ulush0],
     [tuple(r) for r in dAn.q("SELECT rasxod_id, odam_id, summa FROM ulush"
                              " ORDER BY id")])
tekshir("audit toza (kategoriya almashgandan keyin)", ledger.audit(dAn).toza)
_aguruh = dAn.skalyar("SELECT COUNT(*) FROM ozgarishlar")
teng("turi: allaqachon shu kategoriyada — 0, yozuv yo'q", 0,
     entries.rasxod_turi_qoy(dAn, [_ax1], _akiy2))
teng("turi: bo'sh chaqiruv log yozmadi", _aguruh,
     dAn.skalyar("SELECT COUNT(*) FROM ozgarishlar"))
dAn.undo()
teng("turi: bitta undo ikkalasini qaytardi", [_ameva, _aboz],
     [dAn.skalyar("SELECT turi_id FROM rasxod WHERE id=?", x)
      for x in (_ax1, _ax2)])
teng("turi: undo mahsulotni ham qaytardi", _aitem,
     dAn.skalyar("SELECT item_id FROM rasxod WHERE id=?", _ax1))
for _yomon in (None, 999_999):
    try:
        entries.rasxod_turi_qoy(dAn, [_ax1], _yomon)
        tekshir(f"turi: yaroqsiz kategoriya ({_yomon}) rad etiladi", False)
    except ValueError:
        tekshir(f"turi: yaroqsiz kategoriya ({_yomon}) rad etiladi", True)
dAn.yop()


# ═════════════════════════════════════════════ hamyon: naqd va kartalar

print("\n── hamyon: naqd va kartalar ─────────────────────────────────")
from core import hamyon as hy  # noqa: E402
from core import rasxod_kirit as _rkh  # noqa: E402

dH = dbm.Db(_TMP / "bH.db", zaxirasiz=True)
hF = entries.odam_qosh(dH, "Fayzulloxon")
hO = entries.odam_qosh(dH, "Otabek")
_hturi = dH.skalyar("SELECT id FROM turi WHERE faol=1 ORDER BY id")
entries.kirim_qosh(dH, "2026-10-01", hF, 1_000_000, "Oylik")


def _hjami(oid):
    return dH.skalyar("SELECT naqd FROM v_balans WHERE id=?", oid)


_h0 = hy.hamyon(dH, hF)
teng("hamyon: karta yo'q — hammasi naqd", (1_000_000, 0),
     (_h0["naqd"], _h0["karta"]))
hHumo = hy.karta_qosh(dH, hF, "Humo", 600_000, "2026-10-01")
_h1 = hy.hamyon(dH, hF)
teng("hamyon: karta qoldig'i naqddan ko'chdi", (400_000, 600_000, 1_000_000),
     (_h1["naqd"], _h1["karta"], _h1["jami"]))
tekshir("hamyon: bir odamda bir xil nomli karta rad etiladi",
        _yiqiladimi(lambda: hy.karta_qosh(dH, hF, "humo")))
hUz = hy.karta_qosh(dH, hF, "Uzcard")
teng("hamyon: bo'sh karta 0", 0,
     next(k["qoldiq"] for k in hy.kartalar(dH, hF) if k["id"] == hUz))

# Rasxod kartadan — karta kamayadi, jami (naqd) v_balans bilan bir xil.
_hr = _rkh.saqla(dH, _rkh.Qoralama(
    sana="2026-10-01", kim_toladi=hF, turi_id=_hturi, nom="Bozor",
    summa=150_000, tur=_rkh.UMUMIY, karta_id=hHumo))
_h2 = hy.hamyon(dH, hF)
teng("hamyon: kartadan rasxod kartani kamaytirdi", 450_000,
     next(k["qoldiq"] for k in _h2["kartalar"] if k["id"] == hHumo))
teng("hamyon: naqd tegmadi", 400_000, _h2["naqd"])
teng("hamyon: naqd + kartalar = v_balans.naqd", _hjami(hF),
     _h2["naqd"] + _h2["karta"])
tekshir("audit toza (kartadan rasxod)", ledger.audit(dH).toza)

# Boshqa odamning kartasi bilan rasxod/kirim rad etiladi.
tekshir("hamyon: o'zganing kartasidan to'lov rad etiladi", _yiqiladimi(
    lambda: _rkh.saqla(dH, _rkh.Qoralama(
        sana="2026-10-01", kim_toladi=hO, turi_id=_hturi, nom="X",
        summa=1_000, tur=_rkh.SHAXSIY, karta_id=hHumo))))
tekshir("hamyon: o'zganing kartasiga kirim rad etiladi", _yiqiladimi(
    lambda: entries.kirim_qosh(dH, "2026-10-01", hO, 5, karta_id=hHumo)))

# Kirim kartaga.
_hk = entries.kirim_qosh(dH, "2026-10-02", hF, 200_000, "Bonus",
                         karta_id=hUz)
teng("hamyon: kartaga kirim", 200_000,
     next(k["qoldiq"] for k in hy.kartalar(dH, hF) if k["id"] == hUz))

# To'lovchi almashsa eski karta bog'lanishi naqdga tushadi.
entries.rasxod_tahrir(dH, _hr, kim_toladi=hO)
teng("hamyon: to'lovchi almashdi — karta bo'shatildi", None,
     dH.skalyar("SELECT karta_id FROM rasxod WHERE id=?", _hr,
                birlamchi=None))
dH.undo()
teng("hamyon: undo karta bog'lanishini qaytardi", hHumo,
     dH.skalyar("SELECT karta_id FROM rasxod WHERE id=?", _hr))

# O'tkazma: bankomatdan yechish (karta → naqd).
hy.otkazma(dH, "2026-10-02", hF, hHumo, None, 50_000, "bankomat")
_h3 = hy.hamyon(dH, hF)
teng("hamyon: bankomat — karta kamaydi, naqd oshdi",
     (400_000, 450_000),
     (next(k["qoldiq"] for k in _h3["kartalar"] if k["id"] == hHumo),
      _h3["naqd"]))
teng("hamyon: o'tkazma jami pulni o'zgartirmadi", _h2["jami"] + 200_000,
     _h3["jami"])
tekshir("hamyon: o'ziga o'tkazma rad etiladi",
        _yiqiladimi(lambda: hy.otkazma(dH, "2026-10-02", hF, hUz, hUz, 5)))
tekshir("hamyon: o'zganing kartasiga o'tkazma rad etiladi",
        _yiqiladimi(lambda: hy.otkazma(dH, "2026-10-02", hO, None, hUz, 5)))

# Qoldiqni to'g'irlash — farq naqd bilan.
hy.qoldiq_togirla(dH, hHumo, 380_000, "2026-10-02")
_h4 = hy.hamyon(dH, hF)
teng("hamyon: to'g'irlangan qoldiq", 380_000,
     next(k["qoldiq"] for k in _h4["kartalar"] if k["id"] == hHumo))
teng("hamyon: to'g'irlash jami pulni o'zgartirmadi", _h3["jami"],
     _h4["jami"])
teng("hamyon: farq yo'q — yozuv yo'q", None,
     hy.qoldiq_togirla(dH, hHumo, 380_000, "2026-10-02"))

# Karta o'chirilsa qoldig'i naqdga qaytadi, undo qaytaradi.
hy.karta_ochir(dH, hUz)
_h5 = hy.hamyon(dH, hF)
teng("hamyon: o'chirilgan karta qoldig'i naqdga", _h4["naqd"] + 200_000,
     _h5["naqd"])
teng("hamyon: o'chirilgan karta ro'yxatda yo'q", [hHumo],
     [k["id"] for k in _h5["kartalar"]])
dH.undo()
teng("hamyon: undo kartani qaytardi", 2, len(hy.kartalar(dH, hF)))

# Tarix: rasxod minus, kirim plus, yig'indi = qoldiq.
_hh = hy.harakatlar(dH, hHumo)
teng("hamyon: tarix yig'indisi = karta qoldig'i", 380_000,
     sum(x["summa"] for x in _hh))
teng("hamyon: tarix turlari", {"rasxod", "otkazma"},
     {x["tur"] for x in _hh})
tekshir("audit toza (hamyon oxirida)", ledger.audit(dH).toza)
dH.yop()

# ═════════════════════════════════════════════════ sinxron (sinx.py)

print("\n── sinxron: juft id, push, pull (Cloudflare D1) ─────────────")

import base64 as _b64  # noqa: E402
import json as _sj  # noqa: E402
import sqlite3 as _sq  # noqa: E402
import threading as _th  # noqa: E402
import urllib.parse as _up  # noqa: E402

import sinx  # noqa: E402

# ── juft id: desktop faqat JUFT id beradi
dX = dbm.Db(_TMP / "bX.db", zaxirasiz=True)
_m1 = dX.apply("menyu", "INSERT", {"nom": "sx taom 1"})
with dX.amal("ikkita"):
    _m2 = dX.apply("menyu", "INSERT", {"nom": "sx taom 2"})
    _m3 = dX.apply("menyu", "INSERT", {"nom": "sx taom 3"})
tekshir("sinx: INSERT id juft", _m1 % 2 == 0 and _m2 % 2 == 0 and _m3 % 2 == 0,
        f"{_m1} {_m2} {_m3}")
tekshir("sinx: bitta amalda ketma-ket juft id", _m3 - _m2 == 2, f"{_m2} {_m3}")
teng("sinx: jurnal id'lari ham juft", 0,
     dX.skalyar("SELECT COUNT(*) FROM ozgarishlar WHERE id%2=1"))
# toq MAX dan keyin — keyingi juft
dX.con.execute("INSERT INTO menyu(id,nom) VALUES(?,?)", (_m3 + 5, "toq qator"))
_m4 = dX.apply("menyu", "INSERT", {"nom": "sx taom 4"})
teng("sinx: toq MAX dan keyingi juft", _m3 + 6, _m4)
teng("sinx: juft MAX dan keyingi juft", _m4 + 2,
     dX.apply("menyu", "INSERT", {"nom": "sx taom 5"}))
teng("sinx: aniq berilgan id o'zgarmaydi", 999,
     dX.apply("menyu", "INSERT", {"id": 999, "nom": "sx aniq"}))
# undo/redo aniq id bilan qayta yozadi — juft id saqlanadi
dX.undo()
teng("sinx: undo INSERT ni olib tashladi", None,
     dX.q1("SELECT 1 FROM menyu WHERE id=999"))
dX.redo()
teng("sinx: redo o'sha id bilan qaytardi", "sx aniq",
     dX.skalyar("SELECT nom FROM menyu WHERE id=999"))

# ── COMMIT dan keyingi ilgak: bitta amal — bitta chaqiruv
_ilgak = []
dX.commitdan_keyin.append(lambda: _ilgak.append(1))
with dX.amal("ilgak"):
    dX.apply("menyu", "INSERT", {"nom": "sx ilgak 1"})
    with dX.amal("ichki"):
        dX.apply("menyu", "INSERT", {"nom": "sx ilgak 2"})
teng("sinx: ichma-ich amal — ilgak bir marta", 1, len(_ilgak))
dX.apply("menyu", "INSERT", {"nom": "sx ilgak 3"})
teng("sinx: mustaqil apply — ilgak chaqirildi", 2, len(_ilgak))
dX.commitdan_keyin.append(lambda: 1 / 0)
dX.apply("menyu", "INSERT", {"nom": "sx ilgak 4"})
tekshir("sinx: ilgak xatosi yozuvni buzmadi",
        dX.q1("SELECT 1 FROM menyu WHERE nom='sx ilgak 4'") is not None)
dX.commitdan_keyin.clear()

# ── migratsiya: eski bazada ustun qo'shiladi, tarix «yuborilgan»
teng("sinx: yangi jurnal qatori sinx=0", 0,
     dX.skalyar("SELECT sinx FROM ozgarishlar ORDER BY id DESC LIMIT 1"))
dX.yop()
_c = _sq.connect(str(_TMP / "bX.db"))
_c.execute("ALTER TABLE ozgarishlar DROP COLUMN sinx")
_c.commit()
_c.close()
dX = dbm.Db(_TMP / "bX.db", zaxirasiz=True)
tekshir("sinx: migratsiya ustunni qo'shdi", dX._ustun_bormi("ozgarishlar", "sinx"))
teng("sinx: eski tarix sinx=1 (D1 ga eksport bilan tushadi)", 0,
     dX.skalyar("SELECT COUNT(*) FROM ozgarishlar WHERE sinx=0"))
teng("sinx: pull kursori eksport nuqtasida (eski toq qatorlar qaytmaydi)",
     str(dX.skalyar("SELECT MAX(id) FROM ozgarishlar WHERE id%2=1")),
     sinx._meta(dX, sinx.META_OXIRGI))
dX.con.execute("DELETE FROM meta WHERE kalit=?", (sinx.META_OXIRGI,))
teng("sinx: kursor yo'q — eng katta toq id dan",
     dX.skalyar("SELECT MAX(id) FROM ozgarishlar WHERE id%2=1"), sinx._kursor(dX))
dX.yop()


class _SoxtaServer:
    """`sinx._sorov` o'rniga: Worker protokolini xotirada takrorlaydi."""

    def __init__(self):
        self.sorovlar = []
        self.olingan = []
        self.sozlama = None
        self.davr = None
        self.rasm_keldi = {}
        self.rasm_bor = {"server.jpg": b"SERVER-RASM"}
        self.toq = []
        self.sahifa = 2
        self.rad = set()
        self.oflayn = False
        self.rad_et = False
        self.get = []

    def __call__(self, usul, url, kalit, tana=None, vaqt=30):
        if self.oflayn:
            raise sinx.Oflayn("internet yo'q")
        assert kalit == "maxfiy", kalit
        qism = _up.urlsplit(url)
        if usul == "GET":
            nom = _up.parse_qs(qism.query)["nom"][0]
            self.get.append(nom)
            return self.rasm_bor[nom]
        b = _sj.loads(tana.decode("utf-8"))
        self.sorovlar.append((qism.path, b))
        if self.rad_et:
            return _sj.dumps({"ok": False, "xato": "kalit noto'g'ri"}).encode()
        if qism.path == "/sinx/push":
            self.olingan += b["ozgarishlar"]
            self.sozlama, self.davr = b["sozlama"], b["davr"]
            for r in b["rasmlar"]:
                self.rasm_keldi[r["nom"]] = _b64.b64decode(r["data"])
            return _sj.dumps({"ok": True, "qabul": [
                q["id"] for q in b["ozgarishlar"]
                if q["id"] not in self.rad]}).encode()
        assert qism.path == "/sinx/pull", qism.path
        dan = b["dan"]
        qolgan = [q for q in self.toq if q["id"] > dan]
        qs = qolgan[:self.sahifa]
        return _sj.dumps({
            "ok": True, "ozgarishlar": qs,
            "oxirgi": qs[-1]["id"] if qs else dan,
            "kop": len(qolgan) > len(qs),
            "sozlama": {"tg_korilgan_guruhlar": "[-100]",
                        "tg_rasxod_dan": "2026-10-01 08:00:00"},
            "rasmlar": sorted(set(self.rasm_bor) | set(self.rasm_keldi)
                              | {"../yomon.jpg"}),
        }).encode()


def _toq(i, amal, qid, keyin, jadval="menyu"):
    return {"id": i, "vaqt": "2026-10-02 10:00:00", "guruh_id": f"g{i}",
            "tavsif": "bot", "jadval": jadval, "qator_id": qid,
            "amal": amal, "oldin": None,
            "keyin": _sj.dumps(keyin) if keyin is not None else None,
            "qaytarilgan": 0, "bekor": 0}


def _yuborilmagan(db):
    return db.skalyar(
        "SELECT COUNT(*) FROM ozgarishlar WHERE sinx=0 AND id%2=0")


_asl_sorov = sinx._sorov
_srv = _SoxtaServer()
sinx._sorov = _srv
try:
    dY = dbm.Db(_TMP / "bY.db", zaxirasiz=True)

    # ── sozlanmagan — hech narsa qilmaydi
    teng("sinx: sozlanmagan — holat", "sozlanmagan", sinx.sinxla(dY)["holat"])
    teng("sinx: sozlanmagan — tarmoqqa chiqilmadi", 0, len(_srv.sorovlar))

    sinx.sozlama_qoy(dY, "https://sinov.workers.dev/", "maxfiy")
    teng("sinx: url oxiridagi / olib tashlanadi", "https://sinov.workers.dev",
         sinx.sozlamalar(dY)["url"])

    # ── desktop egalik qiladigan sozlamalar
    for _k, _v in [("tg_token", "T"), ("rejim", "tun"), ("tg_offset", "5"),
                   ("tg_rx:123", "{}"), ("dars_tekshirildi", "x"),
                   ("tg_korilgan_guruhlar", "[]"), ("tg_rasxod_dan", "y")]:
        dY.sozlama_qoy(_k, _v)
    dY.con.execute("INSERT INTO davr(oy,holat) VALUES('2026-08','yopilgan')")

    # ── 250 ta mahalliy yozuv + bitta eski toq yozuv (yuborilmaydi)
    for _i in range(250):
        dY.apply("menyu", "INSERT", {"nom": f"push taom {_i}"})
    _eski = dY.skalyar("SELECT MAX(id) FROM ozgarishlar") + 1
    dY.con.execute(
        "INSERT INTO ozgarishlar(id,guruh_id,jadval,qator_id,amal) "
        "VALUES(?,?,?,?,?)", (_eski, "eski", "menyu", 1, "UPDATE"))
    _juftlar = _yuborilmagan(dY)
    _rad = dY.skalyar("SELECT MAX(id) FROM ozgarishlar WHERE id%2=0")
    _srv.rad = {_rad}

    _n = sinx.push(dY, sinx.sozlamalar(dY))
    _push = [b for y, b in _srv.sorovlar if y == "/sinx/push"]
    teng("sinx: push — qabul qilinganlar", _juftlar - 1, _n)
    tekshir("sinx: push — bo'laklarga bo'lindi (≤200)",
            len(_push) >= 2
            and max(len(b["ozgarishlar"]) for b in _push) <= sinx.PUSH_QATOR,
            str([len(b["ozgarishlar"]) for b in _push]))
    tekshir("sinx: push — faqat juft id",
            all(q["id"] % 2 == 0 for q in _srv.olingan))
    tekshir("sinx: push — eski toq qator ketmadi",
            all(q["id"] != _eski for q in _srv.olingan))
    _ids = [q["id"] for q in _push[0]["ozgarishlar"]]
    tekshir("sinx: push — id tartibida", _ids == sorted(_ids))
    tekshir("sinx: push — sinx ustuni yuborilmaydi",
            all("sinx" not in q for q in _srv.olingan))
    tekshir("sinx: push — to'liq qator (keyin JSON bilan)",
            all({"guruh_id", "jadval", "qator_id", "keyin", "vaqt"} <= set(q)
                for q in _srv.olingan))
    teng("sinx: qabul qilingani sinx=1, rad etilgani 0", [_rad],
         [r["id"] for r in dY.q(
             "SELECT id FROM ozgarishlar WHERE sinx=0 AND id%2=0")])
    teng("sinx: desktop sozlamalari filtri", {"tg_token": "T", "rejim": "tun"},
         {k: v for k, v in _srv.sozlama.items() if k in (
             "tg_token", "rejim", "tg_offset", "tg_rx:123", "dars_tekshirildi",
             "tg_korilgan_guruhlar", "tg_rasxod_dan", "sinx_url", "sinx_kalit")})
    teng("sinx: davr yuborildi", [("2026-08", "yopilgan")],
         [(r["oy"], r["holat"]) for r in _srv.davr])
    _srv.rad = set()

    # ── pull: serverning toq qatorlari
    _srv.toq = [
        _toq(10001, "INSERT", 10001,
             {"id": 10001, "nom": "Palov", "tartib": 3, "ochirilgan": 0,
              "server_ustuni": "e'tiborsiz"}),
        _toq(10003, "UPDATE", 10001,
             {"id": 10001, "nom": "Palov (bot)", "tartib": 4, "ochirilgan": 0}),
        _toq(10005, "INSERT", 10005,
             {"id": 10005, "nom": "Somsa", "tartib": 5, "ochirilgan": 0}),
        _toq(10007, "DELETE", 10005, None),
        _toq(10009, "INSERT", 10009, {"id": 10009, "nom": "x"}, "yoq_jadval"),
    ]
    _juft_oldin = dY.skalyar("SELECT COUNT(*) FROM ozgarishlar WHERE id%2=0")
    _r = sinx.sinxla(dY)
    teng("sinx: sinxla — ok", "ok", _r["holat"])
    teng("sinx: pull — 5 qator qo'yildi", 5, _r["ozgardi"])
    teng("sinx: pull — upsert (oxirgi holat)", ("Palov (bot)", 4),
         tuple(dY.q1("SELECT nom, tartib FROM menyu WHERE id=10001")))
    teng("sinx: pull — keyin=None → DELETE", None,
         dY.q1("SELECT 1 FROM menyu WHERE id=10005"))
    teng("sinx: pull — qayta log bo'lmadi", _juft_oldin,
         dY.skalyar("SELECT COUNT(*) FROM ozgarishlar WHERE id%2=0"))
    teng("sinx: pull — jurnalga sinx=1 bilan",
         [(i, 1) for i in (10001, 10003, 10005, 10007, 10009)],
         [tuple(r) for r in dY.q(
             "SELECT id, sinx FROM ozgarishlar WHERE id>=10001 ORDER BY id")])
    teng("sinx: pull — meta.sinx_server_oxirgi", "10009",
         sinx._meta(dY, sinx.META_OXIRGI))
    teng("sinx: pull — sahifalab (kop)", 3,
         len([1 for y, b in _srv.sorovlar if y == "/sinx/pull"]))
    teng("sinx: server sozlamasi olindi", "[-100]",
         dY.sozlama("tg_korilgan_guruhlar"))
    teng("sinx: yuborilmagan qolmadi", 0, _yuborilmagan(dY))

    # qayta qo'llash — hech narsa o'zgarmaydi
    dY.apply("menyu", "UPDATE", {"tartib": 77}, 10001)
    teng("sinx: qayta qo'llash — 0 ta yangi", 0,
         sinx.qatorlarni_qoy(dY, _srv.toq))
    teng("sinx: qayta qo'llash keyingi mahalliy o'zgarishni bosmadi", 77,
         dY.skalyar("SELECT tartib FROM menyu WHERE id=10001"))
    teng("sinx: ikkinchi sinxla — o'zgarish yo'q", 0, sinx.sinxla(dY)["ozgardi"])
    # MAX(menyu.id) = 10001 (10005 o'chirilgan) → keyingi juft 10002.
    teng("sinx: pull'dan keyin mahalliy id juft va kattaroq", 10002,
         dY.apply("menyu", "INSERT", {"nom": "pull keyin"}))
    tekshir("sinx: audit toza (pull keyin)", ledger.audit(dY).toza)

    # ── rasmlar
    for _nom in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
        (config.MAHSULOT_RASM / _nom).write_bytes(_nom.encode() * 3)
        dY.apply("item", "INSERT", {"nom": f"mahsulot {_nom}", "rasm": _nom})
    dY.apply("item", "INSERT", {"nom": "fayli yo'q", "rasm": "yoq.jpg"})
    _oldin = len(_srv.sorovlar)
    _r = sinx.sinxla(dY)
    teng("sinx: rasmlar bilan sinxla ok", "ok", _r["holat"])
    teng("sinx: yangi rasmlar yuborildi", {"a.jpg", "b.jpg", "c.jpg", "d.jpg"},
         set(_srv.rasm_keldi))
    teng("sinx: rasm mazmuni base64 orqali to'g'ri", b"a.jpga.jpga.jpg",
         _srv.rasm_keldi["a.jpg"])
    tekshir("sinx: bitta so'rovda ≤3 rasm",
            all(len(b.get("rasmlar", [])) <= sinx.PUSH_RASM
                for _, b in _srv.sorovlar[_oldin:]))
    teng("sinx: server rasmi yuklab olindi", b"SERVER-RASM",
         (config.MAHSULOT_RASM / "server.jpg").read_bytes())
    teng("sinx: yomon nomli rasm so'ralmadi", ["server.jpg"], _srv.get)
    _oldin = len(_srv.sorovlar)
    sinx.sinxla(dY)
    teng("sinx: rasm ikkinchi marta yuborilmadi", 0,
         sum(len(b.get("rasmlar", [])) for _, b in _srv.sorovlar[_oldin:]))

    # ── oflayn va rad
    dY.apply("menyu", "INSERT", {"nom": "oflayn taom"})
    _srv.oflayn = True
    _r = sinx.sinxla(dY)
    teng("sinx: internet yo'q — holat oflayn", "oflayn", _r["holat"])
    teng("sinx: oflayn — qator yuborilmagan bo'lib qoldi", 1, _yuborilmagan(dY))
    _srv.oflayn = False
    _srv.rad_et = True
    _r = sinx.sinxla(dY)
    teng("sinx: server rad etdi — holat xato", "xato", _r["holat"])
    tekshir("sinx: xato matni bor", "kalit" in _r["xabar"], _r["xabar"])
    _srv.rad_et = False
    teng("sinx: tiklangach yuborildi", "ok", sinx.sinxla(dY)["holat"])
    teng("sinx: hammasi yuborildi", 0, _yuborilmagan(dY))
    dY.yop()

    # ── fon oqimi: o'z ulanishi, natija qaytaradi
    dZ = dbm.Db(_TMP / "bZ.db", zaxirasiz=True)
    sinx.sozlama_qoy(dZ, "https://sinov2.workers.dev", "maxfiy")
    dZ.apply("menyu", "INSERT", {"nom": "fon taom"})
    _tayyor = _th.Event()
    _nat = []
    _sx = sinx.Sinxronchi(
        dZ.yol, natija_fn=lambda r: (_nat.append(r), _tayyor.set()),
        kechikish=0.05)
    _sx.tetikla()
    _sx.tetikla()
    _tayyor.wait(10)
    _sx.toxtat()
    teng("sinx: fon oqimi — ok", "ok", _nat[0]["holat"] if _nat else None)
    teng("sinx: fon oqimi — bitta sinxron (tetiklar birlashdi)", 1, len(_nat))
    teng("sinx: fon oqimi — UI ulanishida ko'rinadi", 0, _yuborilmagan(dZ))
    dZ.yop()
finally:
    sinx._sorov = _asl_sorov


# ═════════════════════════════════════════════════════════ yakun

dG.yop(); dS.yop(); dR.yop(); dK.yop(); dO.yop(); d.yop(); d2.yop(); d3.yop(); dU.yop(); d8.yop(); d9.yop(); dA.yop(); dB.yop(); dC.yop(); dD.yop(); dT.yop(); dT2.yop()
shutil.rmtree(_TMP, ignore_errors=True)

print("\n" + "═" * 62)
print(f"  OK: {len(OK)}     XATO: {len(XATO)}")
if XATO:
    print("\n  Yiqilgan testlar:")
    for x in XATO:
        print("   -", x)
print("═" * 62)
sys.exit(1 if XATO else 0)
