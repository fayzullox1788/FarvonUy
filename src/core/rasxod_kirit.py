"""Rasxod kiritish — dastur va Telegram bot uchun BITTA mantiq.

Rasxod ikki joydan kiritiladi: dasturdagi oyna (`RasxodDialog`, «Bugun»
dagi tezkor qo'shish) va Telegram bot (`core/tg_rasxod.py`). Ikkalasi
ham shu fayldagi `Qoralama` ni to'ldiradi va `saqla()` ni chaqiradi.
Tekshiruv, mahsulotdan nom/narx olish, kim qatnashishi va ulushlar
FAQAT shu yerda — shuning uchun bot «soddalashtirilgan» rasxod yoza
olmaydi: dasturda qaysi qoida bo'lsa, botda ham o'sha.

Yangi qoida qo'shsangiz (majburiy maydon, cheklov) — shu yerga qo'shing,
oynaga emas. Aks holda ikki platforma bir-biridan ajralib ketadi.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import money
from core import entries, splitting

UMUMIY, SHAXSIY, UCHUN = "umumiy", "shaxsiy", "uchun"


@dataclass
class Qoralama:
    """Dasturdagi rasxod oynasining maydonlari — aynan o'shalar."""
    sana: str
    kim_toladi: int | None = None
    turi_id: int | None = None
    item_id: int | None = None
    nom: str = ""
    summa: int = 0
    tur: str = UMUMIY                 # umumiy | shaxsiy | uchun
    kim_uchun: int | None = None
    usul: str = money.USUL_TENG
    # {odam_id: qiymat}. None — shu sanada uyda bo'lganlar, teng
    # (oynadagi boshlang'ich holat bilan bir xil).
    parametrlar: dict[int, float] | None = None
    izoh: str | None = None
    manba: str = field(default="dastur", compare=False)
    # Kategoriya ichidagi bir nechta mahsulot: [{item_id, nom, miqdor,
    # summa}]. Bo'sh — oddiy rasxod (bot, «Bugun», eski yozuvlar).
    # To'ldirilgan bo'lsa `summa` — ularning yig'indisi (`tekshir`).
    mahsulotlar: list[dict] = field(default_factory=list)

    def lugat(self) -> dict:
        d = asdict(self)
        if d["parametrlar"] is not None:          # JSON kaliti — matn
            d["parametrlar"] = {str(k): v for k, v in d["parametrlar"].items()}
        return d

    @classmethod
    def lugatdan(cls, d: dict) -> "Qoralama":
        d = dict(d)
        if d.get("parametrlar") is not None:
            d["parametrlar"] = {int(k): float(v)
                                for k, v in d["parametrlar"].items()}
        return cls(**d)


# ────────────────────────────────────────────────────── mahsulotdan

def mahsulot_tanla(db, q: Qoralama, item_id: int | None) -> None:
    """Mahsulot tanlanganda nom va narx O'ZI to'ldiriladi — agar bo'sh bo'lsa.

    Narx faqat taklif: foydalanuvchi keyin o'zgartira oladi. Rasxodga
    summa NUSXALANADI, ya'ni mahsulot narxi keyin o'zgarsa eski rasxod
    o'zgarmaydi.
    """
    q.item_id = item_id or None
    if not q.item_id:
        return
    it = db.q1("SELECT nom, narx FROM item WHERE id=?", q.item_id)
    if not it:
        q.item_id = None
        return
    if not (q.nom or "").strip():
        q.nom = it["nom"]
    if it["narx"] and not q.summa:
        q.summa = int(it["narx"])


# ─────────────────────────────────── bir nechta mahsulot (rasxod va reja)
#
# Rasxod oynasi ham, reja oynasi ham kategoriya ichidan BIR NECHTA
# mahsulot oladi. Qoida bitta joyda — shu yerda: har qator musbat
# summali, nomi bor; yozuvning summasi — qatorlar yig'indisi. Qatorlar
# `rasxod_mahsulot` / `reja_mahsulot` ga yoziladi; balans ularni
# o'qimaydi (faqat `rasxod.summa`), shuning uchun audit o'zgarmaydi.

def mahsulot_qatorlari(db, qatorlar: list[dict] | None) -> list[dict]:
    """Tekshiradi va tozalaydi: bo'sh qatorlar (mahsulotsiz va summasiz)
    tashlanadi, nom bo'sh bo'lsa mahsulotnikidan olinadi."""
    natija = []
    for i, x in enumerate(qatorlar or [], 1):
        iid = x.get("item_id") or None
        summa = int(x.get("summa") or 0)
        nom = (x.get("nom") or "").strip()
        if not iid and not summa and not nom:
            continue
        if iid:
            it = db.q1("SELECT nom FROM item WHERE id=?", iid)
            if not it:
                raise ValueError(f"{i}-mahsulot topilmadi.")
            nom = nom or it["nom"]
        if not nom:
            raise ValueError(f"{i}-qatorda mahsulot tanlanmagan.")
        if summa <= 0:
            raise ValueError(f"«{nom}» summasi kiritilmagan.")
        miqdor = int(x.get("miqdor") or 1)
        if miqdor <= 0:
            raise ValueError(f"«{nom}» miqdori musbat bo'lishi kerak.")
        natija.append({"item_id": iid, "nom": nom, "miqdor": miqdor,
                       "summa": summa})
    return natija


def yangi_mahsulotlarni_qosh(db, qatorlar: list[dict],
                             turi_id: int | None) -> None:
    """Katalogda yo'q, o'sha zahoti yozilgan mahsulot (`item_id` bo'sh)
    shu kategoriyaga katalogga qo'shiladi va qator unga bog'lanadi —
    keyingi safar ro'yxatda tanlanadi. Shu nomli mahsulot kategoriyada
    bo'lsa yangisi yaratilmaydi. `amal()` ICHIDA chaqiring (bitta undo).

    Narx — bitta donaning narxi: summa miqdorga `money.bol_teng` bilan
    bo'linadi va eng kichik ulush olinadi (pulni `/` bilan bo'lmaymiz).
    """
    from core import plan
    for x in qatorlar:
        if x["item_id"]:
            continue
        mavjud = db.q1(
            "SELECT id FROM item WHERE ochirilgan=0 AND turi_id IS ?"
            " AND nom=? COLLATE NOCASE", turi_id, x["nom"])
        if mavjud:
            x["item_id"] = mavjud["id"]
            continue
        miqdor = max(1, int(x["miqdor"]))
        narx = min(u.summa for u in money.bol_teng(
            int(x["summa"]), list(range(miqdor))))
        x["item_id"] = plan.item_topib_qosh(db, x["nom"], narx, turi_id)


def qatorlar_jami(qatorlar: list[dict]) -> int:
    return sum(int(x["summa"]) for x in qatorlar)


def qatorlar_nomi(qatorlar: list[dict], uzunlik: int = 60) -> str:
    """«Non, Sut, Tuxum» — sabab bo'sh qolganda taklif."""
    nomlar = [x["nom"] if int(x.get("miqdor") or 1) == 1
              else f"{x['nom']} ×{x['miqdor']}" for x in qatorlar]
    matn = ", ".join(nomlar)
    return matn if len(matn) <= uzunlik else matn[:uzunlik - 1] + "…"


def qatorlarni_yoz(db, jadval: str, ota_ustun: str, ota_id: int,
                   qatorlar: list[dict]) -> None:
    """Yozuvning mahsulot qatorlarini YANGILAYDI (amal ichida chaqiring).

    O'zgarmagan bo'lsa hech narsa yozilmaydi; aks holda eskilari
    `ochirilgan=1`, yangilari qo'shiladi — undo eski ro'yxatni qaytaradi.
    """
    assert jadval in ("rasxod_mahsulot", "reja_mahsulot")
    eski = db.q(f"SELECT id, item_id, nom, miqdor, summa FROM {jadval}"
                f" WHERE {ota_ustun}=? AND ochirilgan=0 ORDER BY tartib, id",
                ota_id)
    kalit = lambda x: (x["item_id"], x["nom"], int(x["miqdor"]), int(x["summa"]))
    if [kalit(x) for x in eski] == [kalit(x) for x in qatorlar]:
        return
    # Rejada «aslida to'landi» summasi bor — qayta yozilganda shu
    # mahsulotniki (item_id, nom bo'yicha) saqlanib qolsin.
    tolangan = {}
    if jadval == "reja_mahsulot":
        for x in db.q("SELECT item_id, nom, tolangan FROM reja_mahsulot"
                      " WHERE qator_id=? AND ochirilgan=0"
                      " AND tolangan IS NOT NULL", ota_id):
            tolangan.setdefault((x["item_id"], x["nom"]), x["tolangan"])
    for x in eski:
        db.apply(jadval, "DELETE", qator_id=x["id"])
    for i, x in enumerate(qatorlar):
        maydon = {
            ota_ustun: ota_id, "item_id": x["item_id"], "nom": x["nom"],
            "miqdor": int(x["miqdor"]), "summa": int(x["summa"]),
            "tartib": i}
        t = tolangan.pop((x["item_id"], x["nom"]), None)
        if t is not None:
            maydon["tolangan"] = t
        db.apply(jadval, "INSERT", maydon)


def qatorlarni_ol(db, jadval: str, ota_ustun: str, ota_id: int) -> list[dict]:
    assert jadval in ("rasxod_mahsulot", "reja_mahsulot")
    return [dict(x) for x in db.q(
        f"SELECT item_id, nom, miqdor, summa FROM {jadval}"
        f" WHERE {ota_ustun}=? AND ochirilgan=0 ORDER BY tartib, id", ota_id)]


def rasxod_mahsulotlari(db, rasxod_id: int) -> list[dict]:
    return qatorlarni_ol(db, "rasxod_mahsulot", "rasxod_id", rasxod_id)


# ──────────────────────────────────────────────────── qatnashchilar

def qatnashchilar(db, q: Qoralama) -> list[int]:
    """Umumiy rasxod kimlarga bo'linadi (tanlanmagan bo'lsa — uydagilar)."""
    # Bo'sh lug'at — «hech kim tanlanmagan», None — «tanlanmagan, uydagilar».
    # Ikkalasini aralashtirmang: aks holda hammani olib tashlagan odamga
    # ko'rinishda yana uydagilar chiqib qolardi.
    if q.parametrlar is not None:
        return [i for i, v in q.parametrlar.items() if v]
    return splitting.qatnashchilar(db, q.sana)


def ulushlar(db, q: Qoralama) -> list[money.Ulush]:
    """Saqlashdan OLDIN ko'rsatish uchun — `rasxod_qosh` bilan aynan bir xil."""
    if q.tur != UMUMIY or q.summa <= 0 or q.parametrlar == {}:
        return []
    return splitting.hisobla(db, int(q.summa), q.sana, q.usul, q.parametrlar)


# ──────────────────────────────────────────────────── tekshir / saqla

def tekshir(db, q: Qoralama) -> None:
    """Dasturdagi oyna ham, bot ham aynan shu xabarlar bilan to'xtaydi."""
    q.mahsulotlar = mahsulot_qatorlari(db, q.mahsulotlar)
    if q.mahsulotlar and qatorlar_jami(q.mahsulotlar) != int(q.summa or 0):
        raise ValueError(
            f"Summa mahsulotlar yig'indisiga teng emas "
            f"({money.fmt_som(qatorlar_jami(q.mahsulotlar))}).")
    if int(q.summa or 0) <= 0:
        raise ValueError("Summa kiritilmagan.")
    entries.rasxod_majburiy(db, q.nom, q.turi_id)
    if q.kim_toladi is None or not db.q1(
            "SELECT 1 FROM odam WHERE id=? AND faol=1", q.kim_toladi):
        raise ValueError("Kim to'laganini tanlang.")
    if q.tur not in (UMUMIY, SHAXSIY, UCHUN):
        raise ValueError("Rasxod turi noma'lum.")
    if q.tur == UCHUN:
        if q.kim_uchun is None:
            raise ValueError("Kim uchun olinganini tanlang.")
        if q.kim_uchun == q.kim_toladi:
            raise ValueError(
                "To'lovchi va «kim uchun» bir odam bo'lsa — bu oddiy "
                "shaxsiy rasxod. «Shaxsiy» ni tanlang.")
    if q.tur == UMUMIY and q.parametrlar is not None and not any(
            q.parametrlar.values()):
        raise ValueError("Kamida bitta odam tanlangan bo'lishi kerak.")


def saqla(db, q: Qoralama, katalog_narxi: bool = False) -> int:
    """Tekshiradi va YANGI rasxod yozadi (`entries.rasxod_qosh` — bitta undo).

    `katalog_narxi=True` — mahsulotning katalogdagi narxi shu to'langan
    summaga yangilanadi («Bugun» dagi tezkor qo'shish shunday ishlaydi:
    bozorda narx o'zgarib turadi). Eski rasxodlarga TEGMAYDI.
    """
    tekshir(db, q)
    if q.mahsulotlar:
        # Bitta mahsulot — rasxod unga bog'lanadi (avvalgidek); bir nechta
        # bo'lsa bog'lanish qatorlarda.
        with db.amal(f"Rasxod: {q.nom.strip()} {money.fmt(int(q.summa))}"
                     f" ({len(q.mahsulotlar)} ta mahsulot)"):
            yangi_mahsulotlarni_qosh(db, q.mahsulotlar, q.turi_id)
            q.item_id = (q.mahsulotlar[0]["item_id"]
                         if len(q.mahsulotlar) == 1 else None)
            rid = _yoz(db, q, q.tur == UMUMIY)
            qatorlarni_yoz(db, "rasxod_mahsulot", "rasxod_id", rid,
                           q.mahsulotlar)
        return rid
    umumiy = q.tur == UMUMIY
    it = (db.q1("SELECT narx FROM item WHERE id=?", q.item_id)
          if katalog_narxi and q.item_id else None)
    if not it or it["narx"] == int(q.summa):
        # Oddiy holat: `rasxod_qosh` ning o'z amali va tavsifi qoladi
        # («Umumiy rasxod: … (kim)») — undo ro'yxatida aynan shu ko'rinadi.
        return _yoz(db, q, umumiy)
    with db.amal(f"Rasxod: {q.nom.strip()} {money.fmt(int(q.summa))}"
                 f" (narx yangilandi)"):
        rid = _yoz(db, q, umumiy)
        db.apply("item", "UPDATE", {"narx": int(q.summa)}, q.item_id)
    return rid


def _yoz(db, q: Qoralama, umumiy: bool) -> int:
    return entries.rasxod_qosh(
        db, q.sana, q.nom.strip(), int(q.summa), q.kim_toladi,
        umumiymi=umumiy, turi_id=q.turi_id, usul=q.usul,
        parametrlar=q.parametrlar if umumiy else None,
        izoh=q.izoh, item_id=q.item_id,
        kim_uchun=q.kim_uchun if q.tur == UCHUN else None)


def tahrirla(db, rasxod_id: int, q: Qoralama) -> None:
    """Mavjud rasxodni oynadagi qoralama bilan almashtiradi — mahsulot
    qatorlari bilan birga, BITTA undo qadamida."""
    tekshir(db, q)
    with db.amal(f"Rasxod tahrirlandi: {q.nom.strip() or '—'}"):
        if q.mahsulotlar:
            yangi_mahsulotlarni_qosh(db, q.mahsulotlar, q.turi_id)
            q.item_id = (q.mahsulotlar[0]["item_id"]
                         if len(q.mahsulotlar) == 1 else None)
        entries.rasxod_tahrir(
            db, rasxod_id, sana=q.sana, nom=q.nom.strip(),
            summa=int(q.summa), kim_toladi=q.kim_toladi,
            umumiymi=q.tur == UMUMIY, turi_id=q.turi_id, usul=q.usul,
            parametrlar=q.parametrlar or None,
            kim_uchun=q.kim_uchun if q.tur == UCHUN else None,
            item_id=q.item_id)
        qatorlarni_yoz(db, "rasxod_mahsulot", "rasxod_id", rasxod_id,
                       q.mahsulotlar)
