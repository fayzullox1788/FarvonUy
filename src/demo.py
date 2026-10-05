"""Demo rejim: haqiqiy ma'lumotsiz taqdimot uchun soxta baza.

Yoqilganda (`config.DEMO_BAYROQ` fayli bor) dastur haqiqiy baza o'rniga
`config.DEMO_PAPKA/farvonuy.db` ni ochadi. U shu modul bilan quriladi:
o'ylab topilgan uch kishi, ikki oylik kirim/rasxod, kartalar, qarzlar,
oylik reja va shu haftaning vazifalari. Hammasi oddiy yadro funksiyalari
orqali yoziladi — kitob teng, undo ishlaydi, sahifalar xuddi haqiqiy
bazadagidek to'ladi.

Haqiqiy bazaga TEGILMAYDI: quruvchi faqat demo papkasiga yozadi
(`_xavfsiz_yol`), sinxron demo rejimida o'chiq (`sinx.sozlamalar`),
Telegram xabarchi har doim haqiqiy bazani ochadi.

Qo'lda:  py -3.14 src\\demo.py yoq | ochir | qayta | holat
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config  # noqa: E402

DEMO_DB = config.DEMO_PAPKA / "farvonuy.db"

ODAMLAR = [("Sardor", "#6b7fd7"), ("Jasur", "#e0884f"), ("Bekzod", "#4fae7f")]

# (kategoriya, ikonka yoki None, ota) — bazaviy turlar `_boshlangich` dan.
QOSHIMCHA_TURLAR = [
    ("Kafe", "food_06.png", None),
    ("Obuna", "office_09.png", None),
    ("Sartarosh", "life_18.png", None),
    ("Non", "food_01.png", "Bozorlik"),
    ("Mevalar", "food_14.png", "Bozorlik"),
]

# (kategoriya, [(sabab, summa oralig'i)], kunlik ehtimol)
RASXODLAR = [
    ("Non", [("Non", (20_000, 30_000))], 0.85),
    ("Bozorlik", [("Haftalik bozorlik", (180_000, 320_000)),
                  ("Go'sht", (120_000, 220_000)),
                  ("Sabzavotlar", (40_000, 90_000))], 0.30),
    ("Mevalar", [("Olma, banan", (35_000, 70_000))], 0.15),
    ("Ro'zg'or", [("Kir yuvish kukuni", (45_000, 80_000)),
                  ("Idish yuvish vositasi", (18_000, 30_000))], 0.08),
    ("Gigiena", [("Shampun, sovun", (30_000, 60_000))], 0.06),
    ("Transport", [("Taksi", (15_000, 40_000)),
                   ("Metro karta", (20_000, 50_000))], 0.25),
    ("Kafe", [("Lavash", (28_000, 45_000)),
              ("Osh markazi", (35_000, 60_000))], 0.12),
    ("Sog'liq", [("Dorixona", (25_000, 90_000))], 0.04),
]

VAZIFALAR = [
    ("Bozorga borish", "10:00", 90),
    ("Kir yuvish", "19:00", 60),
    ("Uyni yig'ishtirish", "18:00", 45),
    ("Gullarga suv quyish", "08:00", 15),
    ("Kitob o'qish", "21:00", 30),
]


def _xavfsiz_yol(yol: Path) -> Path:
    """Faqat demo papkasi ichiga yozishga ruxsat."""
    yol = Path(yol).resolve()
    papka = config.DEMO_PAPKA.resolve()
    if papka not in yol.parents or yol == config.HAQIQIY_DB.resolve():
        raise RuntimeError(f"Demo baza demo papkasida bo'lishi shart: {yol}")
    return yol


def yoqilganmi() -> bool:
    return config.DEMO_BAYROQ.exists()


def yoq() -> None:
    """Demo rejimni yoqadi (keyingi ishga tushishdan). Baza yo'q bo'lsa quradi."""
    if not DEMO_DB.exists():
        qur()
    config.DEMO_BAYROQ.write_text("1", encoding="utf-8")


def ochir() -> None:
    """Demo rejimni o'chiradi — keyingi ishga tushishda haqiqiy baza."""
    config.DEMO_BAYROQ.unlink(missing_ok=True)


def _eskisini_tozala(yol: Path) -> None:
    for qoshimcha in ("", "-wal", "-shm"):
        Path(str(yol) + qoshimcha).unlink(missing_ok=True)


def qur(yol: Path | str = DEMO_DB, bugun: date | None = None,
        urug: int = 2026) -> Path:
    """Demo bazani NOLDAN quradi (eskisi o'chiriladi)."""
    import db as dbm
    from core import entries, hamyon, plan
    from core import vazifa as vz

    yol = _xavfsiz_yol(Path(yol))
    yol.parent.mkdir(parents=True, exist_ok=True)
    _eskisini_tozala(yol)
    bugun = bugun or date.today()
    tasodif = random.Random(urug)

    db = dbm.Db(yol, zaxirasiz=True)
    try:
        boshi = (bugun.replace(day=1) - timedelta(days=1)).replace(day=1)

        # ── odamlar va kategoriyalar ───────────────────────────────
        odam = [entries.odam_qosh(db, nom, rang) for nom, rang in ODAMLAR]
        asosiy = odam[0]
        with db.amal("Demo kategoriyalar"):
            tartib = db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM turi")
            for i, (nom, rasm, ota) in enumerate(QOSHIMCHA_TURLAR):
                ota_id = (db.skalyar("SELECT id FROM turi WHERE nom=?", ota)
                          if ota else None)
                db.apply("turi", "INSERT", {
                    "nom": nom, "belgi": "", "tartib": tartib + i,
                    "rasm": rasm, "ota_id": ota_id})
        turi = {r["nom"]: r["id"] for r in db.q("SELECT id, nom FROM turi")}

        # ── kirim: har oy maosh, ukalar — vaqti-vaqti bilan ─────────
        oy = boshi
        while oy <= bugun:
            entries.kirim_qosh(db, oy.replace(day=2).isoformat(), asosiy,
                               4_500_000, "Oylik maosh")
            entries.kirim_qosh(db, oy.replace(day=5).isoformat(), odam[1],
                               1_200_000, "Stipendiya")
            if oy.month == bugun.month:
                break
            oy = (oy.replace(day=28) + timedelta(days=4)).replace(day=1)
        entries.kirim_qosh(db, (boshi + timedelta(days=20)).isoformat(),
                           odam[2], 1_600_000, "Frilans buyurtma")

        # ── kartalar ───────────────────────────────────────────────
        humo = hamyon.karta_qosh(db, asosiy, "Humo", 1_500_000,
                                 boshi.isoformat())
        hamyon.karta_qosh(db, odam[1], "Uzcard", 400_000, boshi.isoformat())

        # ── rasxodlar: ~1.5 oy, har kuni ────────────────────────────
        kun = boshi
        while kun <= bugun:
            for kat, variantlar, ehtimol in RASXODLAR:
                if tasodif.random() > ehtimol:
                    continue
                sabab, (past, yuqori) = tasodif.choice(variantlar)
                summa = tasodif.randrange(past, yuqori + 1, 1_000)
                toladi = asosiy if tasodif.random() < 0.7 else tasodif.choice(odam)
                karta = humo if toladi == asosiy and tasodif.random() < 0.3 else None
                entries.rasxod_qosh(db, kun.isoformat(), sabab, summa, toladi,
                                    umumiymi=True, turi_id=turi[kat],
                                    karta_id=karta)
            if kun.day == 10:
                entries.rasxod_qosh(db, kun.isoformat(), "Kommunal to'lovlar",
                                    tasodif.randrange(350_000, 450_000, 1_000),
                                    asosiy, turi_id=turi["Kommunal"])
                entries.rasxod_qosh(db, kun.isoformat(), "Spotify",
                                    35_000, odam[1], umumiymi=False,
                                    turi_id=turi["Obuna"])
            if kun.day == 15:
                entries.rasxod_qosh(db, kun.isoformat(), "Soch oldirish",
                                    50_000, odam[2], umumiymi=False,
                                    turi_id=turi["Sartarosh"])
            kun += timedelta(days=1)

        entries.rasxod_qosh(db, (bugun - timedelta(days=6)).isoformat(),
                            "Krossovka", 450_000, asosiy,
                            turi_id=turi["Kiyim"], kim_uchun=odam[2])

        # ── qarz, hisob-kitob, tashqi qarz ─────────────────────────
        entries.qarz_qosh(db, (bugun - timedelta(days=12)).isoformat(),
                          asosiy, odam[1], 300_000, "Telefon ta'miri")
        entries.hisob_kitob_qosh(db, (bugun - timedelta(days=3)).isoformat(),
                                 odam[1], asosiy, 150_000)
        entries.tashqi_qarz_qosh(db, (bugun - timedelta(days=9)).isoformat(),
                                 odam[2], "Aka (qo'shni)", 500_000,
                                 "Kurs to'lovi uchun")

        # ── oylik reja ─────────────────────────────────────────────
        plan.reja_saqla(db, plan.oy_kaliti(bugun), 6_000_000, {
            turi["Bozorlik"]: 2_500_000, turi["Transport"]: 600_000,
            turi["Kafe"]: 400_000, turi["Kommunal"]: 450_000,
            turi["Ro'zg'or"]: 300_000})

        # ── vazifalar: shu hafta ────────────────────────────────────
        for i, k in enumerate(vz.hafta_kunlari(bugun)):
            nom, vaqt, davom = VAZIFALAR[i % len(VAZIFALAR)]
            vid = vz.qosh(db, nom, odam[i % len(odam)], k, vaqt, davom)
            if k < bugun:
                vz.bajar(db, vid)
            nom2, vaqt2, davom2 = VAZIFALAR[(i + 2) % len(VAZIFALAR)]
            vz.qosh(db, nom2, odam[(i + 1) % len(odam)], k, vaqt2, davom2)
    finally:
        db.yop()
    return yol


def main(argv: list[str]) -> int:
    buyruq = argv[1] if len(argv) > 1 else "holat"
    if buyruq == "yoq":
        yoq()
    elif buyruq == "ochir":
        ochir()
    elif buyruq == "qayta":
        qur()
    elif buyruq != "holat":
        print(__doc__)
        return 2
    print(f"Demo rejim: {'YOQIQ' if yoqilganmi() else 'ochiq emas'}  ({DEMO_DB})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
