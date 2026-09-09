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
teng("Fayzulloxon pishirsa Abbosxon yuvadi", "Abbosxon", _yuvuvchi[_du9])
teng("Otabek pishirsa Fayzulloxon yuvadi", "Fayzulloxon",
     _yuvuvchi[_du9 + _td(days=1)])
teng("Abbosxon pishirsa Otabek yuvadi", "Otabek",
     _yuvuvchi[_du9 + _td(days=2)])
teng("idish ovqatdan keyin", "20:00",
     [x["vaqt"] for x in _reja if x["nom"] == _idish["nom"]][0])

teng("navbat 4-kunda aylanadi", "Fayzulloxon",
     [x["odam"] for x in vz.navbat_rejasi(d9, _ovqat["id"], nF, _du9,
                                          "19:00", 4)
      if x["nom"] == _ovqat["nom"]][3])
teng("boshqa odamdan boshlansa navbat undan yuradi", "Otabek",
     vz.navbat_rejasi(d9, _ovqat["id"], nO, _du9, "19:00", 1)[0]["odam"])
teng("Otabekdan boshlansa Fayzulloxon yuvadi", "Fayzulloxon",
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
teng("yangi ergash to'g'ri odamga tushdi", "Abbosxon",
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
teng("03.09 yuvuvchi qoidaga mos (Abbosxon→Otabek)", "Otabek",
     _yuvuvchi(dA, _k3))
teng("05.09 yuvuvchi qoidaga mos (Fayzulloxon→Abbosxon)", "Abbosxon",
     _yuvuvchi(dA, _k5))
tekshir("almashuv bitta undo qadami",
        "almashdi" in (dA.oxirgi_guruh() or ("", ""))[1])
dA.undo()
teng("undo almashuvni qaytardi", "Fayzulloxon", _oshpaz(dA, _k3))
teng("undo yuvuvchini ham qaytardi", "Abbosxon", _yuvuvchi(dA, _k3))

# «faqat shu kunni berish» — almashuvsiz
vz.bersin(dA, _v3, aA)
teng("bersin: 03.09 Abbosxon", "Abbosxon", _oshpaz(dA, _k3))
teng("bersin: 05.09 tegilmadi", "Abbosxon", _oshpaz(dA, _k5))
teng("bersin: yuvuvchi ham to'g'rilandi", "Otabek", _yuvuvchi(dA, _k3))
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


# ═════════════════════════════════════════════════════════ yakun

dG.yop(); dS.yop(); dR.yop(); dK.yop(); dO.yop(); d.yop(); d2.yop(); d3.yop(); dU.yop(); d8.yop(); d9.yop(); dA.yop(); dB.yop(); dC.yop(); dD.yop()
shutil.rmtree(_TMP, ignore_errors=True)

print("\n" + "═" * 62)
print(f"  OK: {len(OK)}     XATO: {len(XATO)}")
if XATO:
    print("\n  Yiqilgan testlar:")
    for x in XATO:
        print("   -", x)
print("═" * 62)
sys.exit(1 if XATO else 0)
