"""Mahsulotlar va kategoriya daraxti.

Mahsulot — `item` jadvali (u avval ham bor edi: reja va rasxod oynasidagi
«Mahsulot» tanlagichi shundan o'qiydi). Bu yerda unga rasm, miqdor,
og'irlik, litr va o'lchov birligi qo'shilgan — yangi jadval EMAS, aks
holda eski katalog va unga bog'langan rasxodlar ikki joyga bo'linardi.

Kategoriya daraxti — `turi.ota_id`. Ichki kategoriya ham oddiy `turi`
qatori: rasxodga to'g'ridan-to'g'ri yozilishi mumkin, doira va budjetda
esa otasiga qo'shib hisoblanadi.

Qoidalar (CLAUDE.md dagi uchta qoida bilan bir xil):
  · hamma yozuv `db.apply()` orqali — undo ishlaydi;
  · hech narsa o'chirilmaydi: kategoriya `faol=0`, mahsulot `ochirilgan=1`;
  · rasm fayli ham o'chirilmaydi — faqat bog'lanish uziladi.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import config
import money

OLCHOVLAR = ["dona", "kg", "gramm", "litr", "millilitr", "qadoq", "bog'",
             "metr", "juft"]
RASM_TURLARI = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")
RASM_MAX_BAYT = 25 * 1024 * 1024


# ═══════════════════════════════════════════════════ kategoriya daraxti

def daraxt(db) -> list[dict]:
    """Faol kategoriyalar daraxti: [{id, nom, belgi, rasm, bolalar: [...]}].

    Otasi nofaol bo'lib qolgan kategoriya ildiz sifatida chiqadi —
    yo'qolib qolmasin.
    """
    qatorlar = [dict(r, bolalar=[]) for r in db.q(
        "SELECT id, nom, belgi, rasm, ota_id FROM turi WHERE faol=1"
        " ORDER BY tartib, id")]
    boyicha = {r["id"]: r for r in qatorlar}
    ildizlar = []
    for r in qatorlar:
        ota = boyicha.get(r["ota_id"])
        (ota["bolalar"] if ota else ildizlar).append(r)
    return ildizlar


def tekis(db) -> list[tuple[dict, int]]:
    """Daraxt — tanlagich uchun tekis ro'yxat: (kategoriya, chuqurlik)."""
    natija = []

    def yur(tugunlar, chuq):
        for t in tugunlar:
            natija.append((t, chuq))
            yur(t["bolalar"], chuq + 1)
    yur(daraxt(db), 0)
    return natija


def avlodlar(db, turi_id: int) -> list[int]:
    """Kategoriyaning o'zi + hamma ichki kategoriyalari (har chuqurlikda)."""
    return [r["id"] for r in db.q(
        "WITH RECURSIVE a(id) AS (SELECT ?"
        " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)"
        " SELECT id FROM a", turi_id)]


def yol_nomi(db, turi_id: int | None) -> str:
    """«Bozorlik › Mevalar» — ko'rsatish uchun."""
    if turi_id is None:
        return ""
    qismlar, joriy, korilgan = [], turi_id, set()
    while joriy is not None and joriy not in korilgan:
        korilgan.add(joriy)
        r = db.q1("SELECT nom, ota_id FROM turi WHERE id=?", joriy)
        if not r:
            break
        qismlar.append(r["nom"])
        joriy = r["ota_id"]
    return " › ".join(reversed(qismlar))


def bosh_belgilar(db) -> list[str]:
    """Hali hech bir FAOL kategoriyada ishlatilmagan ikonkalar.

    Bitta ikonka — bitta kategoriya: «Iconlar» varag'i
    (`kategoriya.nomlanganlar`) ikonkadan kategoriyani topadi, ikkitasi
    bitta rasmni olsa varaqda biri yo'qolib, nom berish boshqasini
    qayta nomlab yuborardi.
    """
    from core import kategoriya
    band = set(kategoriya.nomlanganlar(db))
    return [f for f in kategoriya.belgilar() if f not in band]


def _rasm_tekshir(db, rasm: str, ozi: int | None = None) -> None:
    from core import kategoriya
    if rasm not in kategoriya.belgilar():
        raise ValueError("Bunday rasm yo'q — ro'yxatdan tanlang.")
    egasi = db.q1("SELECT nom FROM turi WHERE faol=1 AND rasm=? AND id<>?",
                  rasm, -1 if ozi is None else ozi)
    if egasi:
        raise ValueError(f"Bu rasm «{egasi['nom']}» kategoriyasida band — "
                         "boshqasini tanlang.")


def kategoriya_qosh(db, nom: str, ota_id: int | None = None,
                    rasm: str | None = None) -> int:
    """Yangi kategoriya. ICHKI kategoriya (`ota_id` berilgan) uchun `rasm`
    — `belgilar/` dagi bo'sh ikonka — MAJBURIY (foydalanuvchi so'ragan):
    ichki kategoriya tanlagich va doira ro'yxatida rasmi bilan ko'rinsin."""
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Kategoriya nomi bo'sh bo'lmasin")
    if ota_id is not None and not db.q1(
            "SELECT 1 FROM turi WHERE id=? AND faol=1", ota_id):
        raise ValueError("Asosiy kategoriya topilmadi")
    if ota_id is not None and not rasm:
        raise ValueError("Ichki kategoriya uchun rasm tanlang.")
    band = db.q1("SELECT id, faol FROM turi WHERE nom=?", nom)
    if band and band["faol"]:
        raise ValueError(f"«{nom}» nomli kategoriya allaqachon bor")
    if rasm:
        _rasm_tekshir(db, rasm, band["id"] if band else None)
    if band:
        # Oldin o'chirilgan — o'sha qatorni tiriltiramiz, eski rasxodlari
        # yana shu nom ostida ko'rinadi.
        yangi = {"faol": 1, "ota_id": ota_id}
        if rasm:
            yangi["rasm"] = rasm
        with db.amal(f"Kategoriya qaytdi: {nom}"):
            db.apply("turi", "UPDATE", yangi, band["id"])
        return band["id"]
    n = db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM turi")
    tavsif = (f"Ichki kategoriya: {yol_nomi(db, ota_id)} › {nom}"
              if ota_id else f"Kategoriya: {nom}")
    with db.amal(tavsif):
        return db.apply("turi", "INSERT", {
            "nom": nom, "belgi": "", "tartib": n, "ota_id": ota_id,
            "rasm": rasm or None})


def kategoriya_nomla(db, turi_id: int, nom: str) -> None:
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Kategoriya nomi bo'sh bo'lmasin")
    band = db.q1("SELECT id FROM turi WHERE nom=? AND id<>?", nom, turi_id)
    if band:
        raise ValueError(f"«{nom}» nomli kategoriya allaqachon bor")
    with db.amal(f"Kategoriya nomi: {nom}"):
        db.apply("turi", "UPDATE", {"nom": nom}, turi_id)


def kategoriya_kochir(db, turi_id: int, ota_id: int | None) -> None:
    """Mavjud kategoriyani boshqasining ichiga ko'chiradi (`None` — asosiyga).

    «Gigiena» → «Katta bozorlik» ichiga: ichki kategoriyalari va
    mahsulotlari birga ko'chadi (ular `ota_id` orqali bog'langan). Eski
    rasxodlar `turi_id` si o'zgarmaydi — faqat doira/budjetda endi yangi
    otasiga qo'shilib hisoblanadi. O'zining ichiga (yoki o'z avlodiga)
    ko'chirib bo'lmaydi — daraxt halqaga aylanardi.
    """
    t = db.q1("SELECT nom, ota_id FROM turi WHERE id=? AND faol=1", turi_id)
    if not t:
        raise ValueError("Kategoriya topilmadi")
    if ota_id is not None:
        if not db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", ota_id):
            raise ValueError("Yangi asosiy kategoriya topilmadi")
        if ota_id in avlodlar(db, turi_id):
            raise ValueError(f"«{t['nom']}» ni o'zining ichiga ko'chirib "
                             f"bo'lmaydi.")
    if t["ota_id"] == ota_id:
        return
    tavsif = (f"Kategoriya ko'chdi: {t['nom']} → {yol_nomi(db, ota_id)}"
              if ota_id else f"Kategoriya asosiy qilindi: {t['nom']}")
    with db.amal(tavsif):
        db.apply("turi", "UPDATE", {"ota_id": ota_id}, turi_id)


def kochish_joylari(db, turi_id: int) -> list[tuple[dict, int]]:
    """Kategoriyani qayerga ko'chirsa bo'ladi: daraxt, o'zi va avlodlarisiz."""
    man = set(avlodlar(db, turi_id))
    natija, tashla = [], None
    for t, chuq in tekis(db):
        if tashla is not None and chuq > tashla:
            continue
        tashla = None
        if t["id"] in man:
            tashla = chuq
            continue
        natija.append((t, chuq))
    return natija


def kategoriya_ochir(db, turi_id: int) -> None:
    """`faol=0`. Ichida faol ichki kategoriya yoki mahsulot bo'lsa — rad.

    Eski rasxodlar kategoriyasini yo'qotmaydi: qator joyida qoladi.
    """
    t = db.q1("SELECT nom FROM turi WHERE id=?", turi_id)
    if not t:
        raise ValueError("Kategoriya topilmadi")
    n = db.skalyar("SELECT COUNT(*) FROM turi WHERE ota_id=? AND faol=1", turi_id)
    if n:
        raise ValueError(f"«{t['nom']}» ichida {n} ta ichki kategoriya bor — "
                         f"avval ularni o'chiring.")
    n = db.skalyar("SELECT COUNT(*) FROM item WHERE turi_id=? AND ochirilgan=0",
                   turi_id)
    if n:
        raise ValueError(f"«{t['nom']}» ichida {n} ta mahsulot bor — avval "
                         f"ularni boshqa kategoriyaga o'tkazing yoki o'chiring.")
    with db.amal(f"Kategoriya o'chirildi: {t['nom']}"):
        db.apply("turi", "UPDATE", {"faol": 0}, turi_id)


# ═══════════════════════════════════════════════════════════ mahsulot

def _son(x, nom: str) -> float | None:
    """Bo'sh → None. Manfiy yoki son emas → tushunarli xato."""
    if x is None:
        return None
    if isinstance(x, str):
        x = x.strip().replace(",", ".").replace(" ", "")
        if not x:
            return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"{nom} son bo'lishi kerak") from None
    if v < 0:
        raise ValueError(f"{nom} manfiy bo'lmasin")
    return v


def mahsulotlar(db, turi_id: int | None = None, qidiruv: str = "",
                faollar: bool = False) -> list[dict]:
    """O'chirilmagan mahsulotlar.

    `turi_id` berilsa — shu kategoriya VA uning hamma ichki kategoriyalari.
    `qidiruv` — nomi yoki izohida (katta-kichik harf farqsiz).
    `faollar=True` — faqat faollari (rasxod oynasi uchun).
    """
    shart, args = ["i.ochirilgan=0"], []
    if faollar:
        shart.append("i.faol=1")
    if turi_id is not None:
        idlar = avlodlar(db, turi_id)
        shart.append(f"i.turi_id IN ({','.join('?' * len(idlar))})")
        args += idlar
    qatorlar = [dict(r) for r in db.q(
        "SELECT i.*, t.nom turi_nom FROM item i LEFT JOIN turi t ON t.id=i.turi_id"
        f" WHERE {' AND '.join(shart)} ORDER BY i.faol DESC, i.nom COLLATE NOCASE",
        *args)]
    q = (qidiruv or "").strip().casefold()
    if q:
        qatorlar = [r for r in qatorlar
                    if q in (r["nom"] or "").casefold()
                    or q in (r["izoh"] or "").casefold()]
    for r in qatorlar:
        r["kategoriya"] = yol_nomi(db, r["turi_id"])
    return qatorlar


def saqla(db, item_id: int | None = None, *, nom: str, turi_id: int | None,
          narx=0, miqdor=None, ogirlik=None, litr=None, olchov=None,
          izoh=None, faol: bool = True) -> int:
    """Mahsulot qo'shadi yoki tahrirlaydi. Bo'sh maydonlar — NULL, xato emas."""
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Mahsulot nomi yozilmagan")
    if turi_id is None:
        raise ValueError("Kategoriya tanlanmagan")
    if not db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", turi_id):
        raise ValueError("Bu kategoriya endi yo'q — boshqasini tanlang")
    try:
        narx = int(narx or 0)
    except (TypeError, ValueError):
        raise ValueError("Narx butun son bo'lishi kerak") from None
    if narx < 0:
        raise ValueError("Narx manfiy bo'lmasin")
    maydonlar = {
        "nom": nom, "turi_id": turi_id, "narx": narx,
        "miqdor": _son(miqdor, "Miqdor"), "ogirlik": _son(ogirlik, "Og'irlik"),
        "litr": _son(litr, "Litr"),
        "olchov": (olchov or "").strip() or None,
        "izoh": (izoh or "").strip() or None, "faol": 1 if faol else 0,
    }
    if item_id is None:
        with db.amal(f"Mahsulot qo'shildi: {nom}"):
            return db.apply("item", "INSERT", maydonlar)
    with db.amal(f"Mahsulot tahrirlandi: {nom}"):
        db.apply("item", "UPDATE", maydonlar, item_id)
    return item_id


def ochir(db, item_id: int) -> None:
    """`ochirilgan=1`. Unga bog'langan eski rasxodlar joyida qoladi."""
    r = db.q1("SELECT nom FROM item WHERE id=?", item_id)
    with db.amal(f"Mahsulot o'chirildi: {r['nom'] if r else '?'}"):
        db.apply("item", "DELETE", qator_id=item_id)


def faol_almashtir(db, item_id: int) -> bool:
    r = db.q1("SELECT nom, faol FROM item WHERE id=?", item_id)
    if not r:
        raise ValueError("Mahsulot topilmadi")
    yangi = 0 if r["faol"] else 1
    with db.amal(f"{r['nom']}: {'faol' if yangi else 'faol emas'}"):
        db.apply("item", "UPDATE", {"faol": yangi}, item_id)
    return bool(yangi)


def tavsif(r) -> str:
    """«2 kg · 1,5 l · 12 000 so'm» — kartada va rasxod oynasida."""
    qism = []

    def son(x):
        return (f"{x:g}".replace(".", ",")) if x is not None else None
    if r["miqdor"] is not None:
        qism.append(f"{son(r['miqdor'])} {r['olchov'] or ''}".strip())
    elif r["olchov"]:
        qism.append(r["olchov"])
    elif r["birlik"]:
        qism.append(r["birlik"])            # eski katalogdagi «4 dona»
    if r["ogirlik"] is not None:
        qism.append(f"{son(r['ogirlik'])} kg")
    if r["litr"] is not None:
        qism.append(f"{son(r['litr'])} l")
    if r["narx"]:
        qism.append(money.fmt_som(r["narx"]))
    return " · ".join(qism)


# ═══════════════════════════════════════════════════════════ rasm

def rasm_yoli(fayl: str | None) -> Path | None:
    if not fayl:
        return None
    yol = config.MAHSULOT_RASM / fayl
    return yol if yol.exists() else None


def _rasm_yoz(db, item_id: int, bayt: bytes, kengaytma: str) -> str:
    kengaytma = kengaytma.lower()
    if kengaytma not in RASM_TURLARI:
        raise ValueError(f"Bu turdagi rasm qo'llab-quvvatlanmaydi: {kengaytma}")
    if len(bayt) > RASM_MAX_BAYT:
        raise ValueError("Rasm juda katta (25 MB dan oshmasin)")
    if not bayt:
        raise ValueError("Rasm fayli bo'sh")
    r = db.q1("SELECT nom FROM item WHERE id=? AND ochirilgan=0", item_id)
    if not r:
        raise ValueError("Mahsulot topilmadi")
    # Nom — mazmun xeshi: bir xil rasm ikki marta yuklansa nusxa ko'paymaydi.
    fayl = f"{item_id}-{hashlib.sha1(bayt).hexdigest()[:16]}{kengaytma}"
    nishon = config.MAHSULOT_RASM / fayl
    if not nishon.exists():
        config.MAHSULOT_RASM.mkdir(parents=True, exist_ok=True)
        nishon.write_bytes(bayt)
    with db.amal(f"Mahsulot rasmi: {r['nom']}"):
        db.apply("item", "UPDATE", {"rasm": fayl}, item_id)
    return fayl


def rasm_qoy(db, item_id: int, manba: str | Path) -> str:
    """Faylni dastur papkasiga NUSXALAYDI (asl fayl ko'chsa ham rasm qoladi)."""
    manba = Path(manba)
    if not manba.exists():
        raise ValueError(f"Fayl topilmadi: {manba}")
    return _rasm_yoz(db, item_id, manba.read_bytes(), manba.suffix)


def rasm_baytdan(db, item_id: int, bayt: bytes, kengaytma: str = ".jpg") -> str:
    """Telegramdan kelgan rasm uchun."""
    return _rasm_yoz(db, item_id, bayt, kengaytma)


def rasm_olib_tashla(db, item_id: int) -> None:
    """Bog'lanishni uzadi. Fayl diskda qoladi — undo uni qaytara olsin."""
    r = db.q1("SELECT nom FROM item WHERE id=?", item_id)
    with db.amal(f"Mahsulot rasmi olib tashlandi: {r['nom'] if r else '?'}"):
        db.apply("item", "UPDATE", {"rasm": None}, item_id)


def nom_boyicha(db, matn: str) -> list[dict]:
    """Aniq nom (katta-kichik harf farqsiz) — Telegram izohidan qidirish."""
    q = (matn or "").strip().casefold()
    if not q:
        return []
    return [dict(r) for r in db.q(
        "SELECT id, nom FROM item WHERE ochirilgan=0 ORDER BY faol DESC, id")
        if (r["nom"] or "").strip().casefold() == q]


def oxshashlar(db, matn: str, n: int = 5) -> list[str]:
    q = (matn or "").strip().casefold()
    if not q:
        return []
    return [r["nom"] for r in db.q(
        "SELECT nom FROM item WHERE ochirilgan=0 ORDER BY nom")
        if q in r["nom"].casefold() or r["nom"].casefold() in q][:n]
