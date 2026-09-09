"""Uy vazifalari: kim, qaysi kuni, soat nechada.

Pulga tegmaydi — `ledger.audit()` bu yerni ko'rmaydi. Lekin qolgan
hamma qoida bir xil: yozuv faqat `db.apply()` orqali, o'chirish —
`ochirilgan=1`, bir amal = bitta guruh.

`ui/` bu fayldan boshqa hech narsa chaqirmaydi.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

OCHIQ = "ochiq"
BAJARILDI = "bajarildi"

KUNLAR = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba",
          "Juma", "Shanba", "Yakshanba"]
KUN_QISQA = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


# ─────────────────────────────────────────────────────────── yordamchi

def hafta_boshi(sana) -> date:
    """Shu sana tushgan haftaning dushanbasi."""
    d = _sana(sana)
    return d - timedelta(days=d.weekday())


def hafta_kunlari(sana) -> list[date]:
    b = hafta_boshi(sana)
    return [b + timedelta(days=i) for i in range(7)]


def _sana(x) -> date:
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _daqiqa(vaqt: str | None) -> int | None:
    """'09:30' → 570. Vaqti yo'q vazifa uchun None."""
    if not vaqt:
        return None
    s, d = str(vaqt).split(":")[:2]
    return int(s) * 60 + int(d)


def _vaqt_matn(daqiqa: int) -> str:
    return f"{daqiqa // 60:02d}:{daqiqa % 60:02d}"


def _odam_nom(db, odam_id: int) -> str:
    r = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    if not r:
        raise ValueError(f"Odam topilmadi: {odam_id}")
    return r["nom"]


def _tekshir(db, nom: str, odam_id: int, sana, vaqt, davomiylik) -> tuple:
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Vazifa nomi bo'sh bo'lishi mumkin emas")
    r = db.q1("SELECT faol FROM odam WHERE id=?", odam_id)
    if not r:
        raise ValueError(f"Odam topilmadi: {odam_id}")
    if not r["faol"]:
        raise ValueError("Ro'yxatdan olingan odamga vazifa biriktirilmaydi")
    iso = _sana(sana).isoformat()
    if vaqt:
        d = _daqiqa(vaqt)
        if d is None or not 0 <= d < 24 * 60:
            raise ValueError(f"Vaqt noto'g'ri: {vaqt}")
        vaqt = _vaqt_matn(d)
    else:
        vaqt = None
    davomiylik = int(davomiylik)
    if davomiylik <= 0:
        raise ValueError("Davomiylik musbat bo'lishi kerak")
    return nom, iso, vaqt, davomiylik


# ───────────────────────────────────────────────────────── vazifa turi
#
# Tur — bu shunchaki tayyor ish nomi («Ovqat qilish»). U kalendarda
# ko'rinmaydi: odamga biriktirilganda `vazifa` jadvaliga yangi qator
# bo'ladi. Shuning uchun turni o'chirish allaqachon biriktirilgan
# vazifalarga tegmaydi.

def turlar(db) -> list:
    return db.q("SELECT * FROM vazifa_turi WHERE ochirilgan=0"
                " ORDER BY tartib, id")


def tur_nomlari(db) -> list[str]:
    return [r["nom"] for r in turlar(db)]


def tur_bitta(db, tur_id: int):
    return db.q1("SELECT * FROM vazifa_turi WHERE id=? AND ochirilgan=0",
                 tur_id)


def tur_qosh(db, nom: str, davomiylik: int = 60,
             shaxsiy: bool = False) -> int:
    """Yangi ish turi.

    `shaxsiy` shu yerda beriladi, keyin alohida chaqiruv bilan emas:
    yaratish va «bu guruhga chiqmaydi» degan qaror BITTA amal bo'lishi
    kerak — aks holda undo yarmini qaytarib qo'yardi.
    """
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Vazifa turi nomi bo'sh bo'lishi mumkin emas")
    davomiylik = int(davomiylik)
    if davomiylik <= 0:
        raise ValueError("Davomiylik musbat bo'lishi kerak")
    shaxsiy = 1 if shaxsiy else 0
    # `nom` UNIQUE: o'chirilgani bor bo'lsa qayta INSERT yiqiladi,
    # shuning uchun uni tiriltiramiz.
    eski = db.q1("SELECT id, ochirilgan FROM vazifa_turi WHERE nom=?", nom)
    if eski and eski["ochirilgan"]:
        with db.amal(f"Vazifa turi qaytarildi: {nom}"):
            db.apply("vazifa_turi", "UPDATE",
                     {"ochirilgan": 0, "davomiylik": davomiylik,
                      "shaxsiy": shaxsiy}, eski["id"])
        return eski["id"]
    if eski:
        raise ValueError(f"«{nom}» ro'yxatda bor")
    tartib = db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM vazifa_turi")
    with db.amal(f"Vazifa turi: {nom}"):
        return db.apply("vazifa_turi", "INSERT", {
            "nom": nom, "davomiylik": davomiylik, "tartib": tartib,
            "shaxsiy": shaxsiy})


def tur_ergash(db, tur_id: int):
    """Navbatli ishning ergashi. O'chirilgan bo'lsa — None.

    Ergash o'chirilgan turga ishora qilib qolishi mumkin (foydalanuvchi
    uni ro'yxatdan olib tashlagan). Shunda navbat jim turib idish
    yuvishni yozmay qo'yardi — shuning uchun bu yerda aniq None.
    """
    t = tur_bitta(db, tur_id)
    if not t or not t["ergash_turi_id"]:
        return None
    return tur_bitta(db, t["ergash_turi_id"])


def tur_ergash_qoy(db, tur_id: int, ergash_turi_id: int | None) -> None:
    """Navbatli ishdan keyin kim nima qilishini belgilaydi."""
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    if ergash_turi_id is not None:
        if int(ergash_turi_id) == int(tur_id):
            raise ValueError("Ish o'zidan keyin kelolmaydi")
        if not tur_bitta(db, ergash_turi_id):
            raise ValueError("Ergash ish topilmadi")
    with db.amal(f"«{t['nom']}» dan keyingi ish o'zgardi"):
        db.apply("vazifa_turi", "UPDATE",
                 {"ergash_turi_id": ergash_turi_id}, tur_id)


def tur_davomiylik_qoy(db, tur_id: int, davomiylik: int) -> None:
    """Odatdagi davomiylik. Eslatma vaqti shundan hisoblanadi."""
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    davomiylik = int(davomiylik)
    if davomiylik <= 0:
        raise ValueError("Davomiylik musbat bo'lishi kerak")
    with db.amal(f"«{t['nom']}» davomiyligi: {davomiylik} daqiqa"):
        db.apply("vazifa_turi", "UPDATE",
                 {"davomiylik": davomiylik}, tur_id)


def tur_navbat_qoy(db, tur_id: int, navbat: bool) -> None:
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    with db.amal(f"«{t['nom']}» navbati o'zgardi"):
        db.apply("vazifa_turi", "UPDATE",
                 {"navbat": 1 if navbat else 0}, tur_id)


def tur_ochir(db, tur_id: int) -> None:
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    with db.amal(f"Vazifa turi o'chirildi: {t['nom']}"):
        db.apply("vazifa_turi", "DELETE", qator_id=tur_id)


# ──────────────────────────────────────────────── shaxsiy va umumiy
#
# Umumiy ish — uyning ishi: guruhga e'lon qilinadi, hamma ko'radi
# («Musorlarni tashlash»). Shaxsiy ish faqat EGASIGA tegishli
# («Kitob o'qish», «Dori ichish») — bot uni guruhga emas, o'sha
# odamning o'ziga shaxsiy yozadi.
#
# Bayroq TURDA turadi, vazifada emas: «kitob o'qish shaxsiy ish»
# degan qaror bir marta qabul qilinadi, har biriktirishda emas.
# `core/xabar.py` shu USTUNGA qarab xabarni qayoqqa yuborishni hal
# qiladi — nomga qarab emas (`navbat` va `haftalik` bilan bir xil
# qoida).

def shaxsiy_turlari(db) -> list:
    return db.q("SELECT * FROM vazifa_turi WHERE shaxsiy=1 AND ochirilgan=0"
                " ORDER BY tartib, id")


def shaxsiy_nomlari(db) -> set[str]:
    """Shaxsiy ishlarning nomlari — xabar shu to'plam bilan ajratadi."""
    return {t["nom"] for t in shaxsiy_turlari(db)}


def tur_shaxsiy_qoy(db, tur_id: int, shaxsiy: bool) -> None:
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    holat = "shaxsiy" if shaxsiy else "umumiy"
    with db.amal(f"«{t['nom']}» {holat} bo'ldi"):
        db.apply("vazifa_turi", "UPDATE",
                 {"shaxsiy": 1 if shaxsiy else 0}, tur_id)


# ──────────────────────────────────────────────────────── ish qadamlari
#
# Katta ishning ichidagi mayda ishlar («Sanuzelni tozalash» → unitaz,
# vanna, pol). Ular TURGA bog'lanadi, vazifaga emas: ro'yxat har hafta
# bir xil, uni har biriktirishda nusxalash mantiqsiz bo'lardi.
#
# Qadam kalendarga tushmaydi va alohida belgilanmaydi — u guruhga
# ketadigan xabarda «nima qilish kerak» degan ro'yxat. Har qadamni
# alohida vazifa qilish kalendarni o'nlab bir daqiqalik blok bilan
# to'ldirib tashlardi.

def qadamlar(db, turi_id: int) -> list:
    return db.q("SELECT * FROM ish_qadam WHERE turi_id=? AND ochirilgan=0"
                " ORDER BY tartib, id", turi_id)


def qadam_nomlari(db, turi_id: int) -> list[str]:
    return [r["nom"] for r in qadamlar(db, turi_id)]


def qadam_qosh(db, turi_id: int, nom: str) -> int:
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Qadam nomi bo'sh bo'lishi mumkin emas")
    t = tur_bitta(db, turi_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    if any(x["nom"].lower() == nom.lower() for x in qadamlar(db, turi_id)):
        raise ValueError(f"«{nom}» bu ishda allaqachon bor")
    tartib = db.skalyar(
        "SELECT COALESCE(MAX(tartib),0)+1 FROM ish_qadam WHERE turi_id=?",
        turi_id)
    with db.amal(f"«{t['nom']}» ga qadam: {nom}"):
        return db.apply("ish_qadam", "INSERT", {
            "turi_id": turi_id, "nom": nom, "tartib": tartib})


def qadam_ochir(db, qadam_id: int) -> None:
    r = db.q1("SELECT * FROM ish_qadam WHERE id=? AND ochirilgan=0", qadam_id)
    if not r:
        raise ValueError("Qadam topilmadi")
    with db.amal(f"Qadam o'chirildi: {r['nom']}"):
        db.apply("ish_qadam", "DELETE", qator_id=qadam_id)


# ───────────────────────────────────────────────────────── general uborka
#
# Haftada bir marta qilinadigan KATTA ishlar (oshxona, sanuzel, uy).
# Ovqat navbatidan farqi shunda:
#
#   navbat   — bitta ish, HAR KUNI keyingi odamga o'tadi;
#   haftalik — bir nechta ish, hammasi BIR KUNI, har biri boshqa
#              odamda, va har HAFTA hammasi bir odam oldinga suriladi.
#
# Ya'ni birinchi yakshanba Fayzulloxon oshxonani tozalasa, keyingi
# yakshanba u sanuzelga o'tadi, oshxona esa Otabekka tushadi. Uch
# hafta ichida har kim har ishni bir marta qiladi — «men doim
# sanuzelni tozalayman» degan gap chiqmaydi.
#
# Ish NOMGA qarab emas, `haftalik` ustuniga qarab topiladi: nom
# o'zgarsa ham reja buzilmaydi (`navbat` bilan bir xil qoida).

UBORKA_KUNI_KALIT = "uborka_kuni"
UBORKA_VAQT_KALIT = "uborka_vaqt"


def uborka_turlari(db) -> list:
    """General uborkaga kiradigan ishlar, `tartib` bo'yicha."""
    return db.q("SELECT * FROM vazifa_turi WHERE haftalik=1 AND ochirilgan=0"
                " ORDER BY tartib, id")


def tur_haftalik_qoy(db, tur_id: int, haftalik: bool) -> None:
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    with db.amal(f"«{t['nom']}» general uborkada"
                 f" {'bor' if haftalik else 'yo`q'}"):
        db.apply("vazifa_turi", "UPDATE",
                 {"haftalik": 1 if haftalik else 0}, tur_id)


def uborka_kuni(db) -> int:
    """Hafta kuni: 0 = dushanba … 6 = yakshanba."""
    try:
        k = int(db.sozlama(UBORKA_KUNI_KALIT, "6"))
    except ValueError:
        return 6
    return k if 0 <= k <= 6 else 6


def uborka_kuni_qoy(db, kun: int) -> None:
    kun = int(kun)
    if not 0 <= kun <= 6:
        raise ValueError("Hafta kuni 0 dan 6 gacha bo'lishi kerak")
    db.sozlama_qoy(UBORKA_KUNI_KALIT, str(kun))


def uborka_vaqti(db) -> str:
    return db.sozlama(UBORKA_VAQT_KALIT, "10:00")


def uborka_vaqti_qoy(db, vaqt: str | None) -> None:
    d = _daqiqa(vaqt)
    if d is None or not 0 <= d < 24 * 60:
        raise ValueError(f"Vaqt noto'g'ri: {vaqt}")
    db.sozlama_qoy(UBORKA_VAQT_KALIT, _vaqt_matn(d))


def uborka_sanasi(db, sana=None):
    """Shu sanadan boshlab birinchi uborka kuni (o'zi ham bo'lishi mumkin)."""
    d = _sana(sana or date.today())
    return d + timedelta(days=(uborka_kuni(db) - d.weekday()) % 7)


def uborka_rejasi(db, sana=None, boshlovchi_id: int | None = None,
                  haftalar: int = 4, vaqt: str | None = None) -> list[dict]:
    """Rejani QURADI, bazaga yozmaydi — oldin ko'rsatish uchun.

    `boshlovchi_id` — birinchi haftada RO'YXATDAGI BIRINCHI ishni
    kim qiladi. Berilmasa odamlar ro'yxatining boshi olinadi.
    """
    turlar_ = uborka_turlari(db)
    if not turlar_:
        raise ValueError("General uborkaga birorta ish belgilanmagan")
    odamlar = navbat_odamlari(db)
    if len(odamlar) < 2:
        raise ValueError("General uborka uchun kamida ikkita faol odam kerak")
    idlar = [r["id"] for r in odamlar]
    nomlar = {r["id"]: r["nom"] for r in odamlar}
    if boshlovchi_id is None:
        boshlovchi_id = idlar[0]
    if boshlovchi_id not in idlar:
        raise ValueError("Tanlangan odam ro'yxatda yo'q")
    haftalar = int(haftalar)
    if haftalar <= 0:
        raise ValueError("Haftalar soni musbat bo'lishi kerak")

    vaqt = vaqt if vaqt is not None else uborka_vaqti(db)
    if vaqt:
        d = _daqiqa(vaqt)
        if d is None or not 0 <= d < 24 * 60:
            raise ValueError(f"Vaqt noto'g'ri: {vaqt}")
        vaqt = _vaqt_matn(d)

    boshi = idlar.index(boshlovchi_id)
    n = len(idlar)
    d0 = uborka_sanasi(db, sana)
    reja: list[dict] = []
    for h in range(haftalar):
        kun = d0 + timedelta(weeks=h)
        for i, t in enumerate(turlar_):
            # `+ h` — har hafta hamma ish bir odam oldinga suriladi.
            kim = idlar[(boshi + i + h) % n]
            reja.append({"sana": kun, "vaqt": vaqt, "nom": t["nom"],
                         "turi_id": t["id"], "odam_id": kim,
                         "odam": nomlar[kim], "davomiylik": t["davomiylik"],
                         "qadamlar": qadam_nomlari(db, t["id"])})
    return reja


def uborka_biriktir(db, sana=None, boshlovchi_id: int | None = None,
                    haftalar: int = 4, vaqt: str | None = None) -> int:
    """Butun uborka rejasini BITTA amal qilib yozadi."""
    reja = uborka_rejasi(db, sana, boshlovchi_id, haftalar, vaqt)
    with db.amal(f"General uborka: {haftalar} hafta,"
                 f" {len(reja)} ta vazifa"):
        for x in reja:
            qosh(db, x["nom"], x["odam_id"], x["sana"], x["vaqt"],
                 x["davomiylik"])
    return len(reja)


def biriktir(db, tur_id: int, odam_id: int, sana, vaqt: str | None = None,
             davomiylik: int | None = None, izoh: str | None = None) -> int:
    """Turni odamga biriktiradi — kalendarda yangi vazifa paydo bo'ladi."""
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    return qosh(db, t["nom"], odam_id, sana, vaqt,
                t["davomiylik"] if davomiylik is None else davomiylik, izoh)


# ────────────────────────────────────────────────────────────── navbat
#
# Ovqat navbati. Ikkita qoida:
#
#   1. Pishirish navbat bilan yuradi — `odam.tartib` bo'yicha, har kuni
#      keyingi odam. Bittasi tanlansa qolgani o'zi joylashadi.
#   2. Idishni O'SHA KUNI AVVALGI navbatchi yuvadi. Ya'ni:
#         Fayzulloxon pishirsa  → Abbosxon yuvadi
#         Otabek pishirsa       → Fayzulloxon yuvadi
#         Abbosxon pishirsa     → Otabek yuvadi
#      Boshqacha aytganda: kecha pishirgan odam bugun idish yuvadi.
#      Shuning uchun yuvuvchi — navbatdagi OLDINGI odam (`-1`).

def navbat_odamlari(db) -> list:
    return db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id")


def navbat_rejasi(db, tur_id: int, odam_id: int, sana,
                  vaqt: str | None = None, kunlar: int = 7) -> list[dict]:
    """Rejani QURADI, bazaga yozmaydi — oldin ko'rsatish uchun."""
    t = tur_bitta(db, tur_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    if not t["navbat"]:
        raise ValueError(f"«{t['nom']}» navbatli ish emas")
    odamlar = navbat_odamlari(db)
    if len(odamlar) < 2:
        raise ValueError("Navbat uchun kamida ikkita faol odam kerak")
    idlar = [r["id"] for r in odamlar]
    nomlar = {r["id"]: r["nom"] for r in odamlar}
    if odam_id not in idlar:
        raise ValueError("Tanlangan odam navbatda yo'q")
    kunlar = int(kunlar)
    if kunlar <= 0:
        raise ValueError("Kunlar soni musbat bo'lishi kerak")

    ergash = tur_ergash(db, tur_id)
    boshi = idlar.index(odam_id)
    n = len(idlar)
    d0 = _sana(sana)
    reja: list[dict] = []
    for i in range(kunlar):
        kun = d0 + timedelta(days=i)
        oshpaz = idlar[(boshi + i) % n]
        reja.append({"sana": kun, "vaqt": vaqt, "nom": t["nom"],
                     "odam_id": oshpaz, "odam": nomlar[oshpaz],
                     "davomiylik": t["davomiylik"]})
        if ergash is None:
            continue
        yuvuvchi = idlar[(boshi + i - 1) % n]
        y_vaqt = None
        if vaqt:
            # Idish ovqatdan keyin: yarim tunni oshib ketmasin.
            y_vaqt = _vaqt_matn(min(23 * 60 + 30,
                                    _daqiqa(vaqt) + t["davomiylik"]))
        reja.append({"sana": kun, "vaqt": y_vaqt, "nom": ergash["nom"],
                     "odam_id": yuvuvchi, "odam": nomlar[yuvuvchi],
                     "davomiylik": ergash["davomiylik"]})
    return reja


def navbat_biriktir(db, tur_id: int, odam_id: int, sana,
                    vaqt: str | None = None, kunlar: int = 7) -> int:
    """Butun navbatni BITTA amal qilib yozadi (bitta qadamda qaytadi)."""
    reja = navbat_rejasi(db, tur_id, odam_id, sana, vaqt, kunlar)
    with db.amal(f"Ovqat navbati: {kunlar} kun, {len(reja)} ta vazifa"):
        for x in reja:
            qosh(db, x["nom"], x["odam_id"], x["sana"], x["vaqt"],
                 x["davomiylik"])
    return len(reja)


# ──────────────────────────────────────────────── navbatni o'zgartirish
#
# Reja tuzilgandan keyin ham hayot o'zgaradi: kimdir kelolmaydi, yoki
# reja tuzilishidan oldingi tartibsizlikni tenglashtirish kerak
# bo'ladi. Ikki yo'l bor va ikkalasi ham zanjirni buzmaydi:
#
#   almashtir()  — ikki odam navbatini ALMASHADI. Keyingi kunlarga
#                  tegilmaydi, ikkalasining navbat soni ham o'zgarmaydi.
#   bersin()     — faqat shu kun boshqasiga o'tadi (almashuvsiz).
#                  Adolatni qo'lda tekislash uchun.
#
# Ikkalasida ham o'sha kunning idish yuvuvchisi qayta hisoblanadi —
# «kim pishirsa, undan oldingi yuvadi» qoidasi buzilmasin.


def navbat_turi(db):
    """Navbatli ish turi (odatda «Ovqat qilish»). Yo'q bo'lsa None."""
    return db.q1("SELECT * FROM vazifa_turi"
                 " WHERE navbat=1 AND ochirilgan=0 ORDER BY tartib LIMIT 1")


def yuvuvchi_id(db, oshpaz_id: int):
    """Shu oshpazning idishini kim yuvadi — navbatdagi OLDINGI odam."""
    idlar = [r["id"] for r in navbat_odamlari(db)]
    if oshpaz_id not in idlar or len(idlar) < 2:
        return None
    return idlar[(idlar.index(oshpaz_id) - 1) % len(idlar)]


def navbatlimi(db, vazifa_id: int) -> bool:
    v = bitta(db, vazifa_id)
    t = navbat_turi(db)
    return bool(v and t and v["nom"] == t["nom"])


def _ergash_vazifa(db, oshpaz_vazifa):
    """Shu kundagi, shu oshpazga juft keladigan ergash ish (idish)."""
    t = navbat_turi(db)
    if not t or oshpaz_vazifa["nom"] != t["nom"]:
        return None
    ergash = tur_ergash(db, t["id"])
    if not ergash:
        return None
    return db.q1(
        "SELECT * FROM vazifa WHERE ochirilgan=0 AND nom=? AND sana=?"
        " ORDER BY COALESCE(vaqt,'99:99'), id LIMIT 1",
        ergash["nom"], oshpaz_vazifa["sana"])


def _yuvuvchini_tugrila(db, oshpaz_vazifa_id: int) -> int:
    """Oshpaz o'zgargach, o'sha kunning yuvuvchisini qayta hisoblaydi."""
    v = bitta(db, oshpaz_vazifa_id)
    if not v:
        return 0
    ergash = _ergash_vazifa(db, v)
    if not ergash:
        return 0
    kerak = yuvuvchi_id(db, v["odam_id"])
    if kerak is None or kerak == ergash["odam_id"]:
        return 0
    db.apply("vazifa", "UPDATE", {"odam_id": kerak}, ergash["id"])
    return 1


def keyingi_navbat(db, vazifa_id: int, odam_id: int):
    """Shu vazifadan KEYIN o'sha odamning shu turdagi birinchi navbati."""
    v = bitta(db, vazifa_id)
    if not v:
        return None
    return db.q1(
        "SELECT * FROM vazifa WHERE ochirilgan=0 AND nom=? AND odam_id=?"
        " AND (sana>? OR (sana=? AND id>?))"
        " ORDER BY sana, COALESCE(vaqt,'99:99'), id LIMIT 1",
        v["nom"], odam_id, v["sana"], v["sana"], v["id"])


def almashtirish_rejasi(db, vazifa_id: int, yangi_odam_id: int) -> dict:
    """Almashuv nimani o'zgartirishini OLDINDAN aytadi."""
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    if int(yangi_odam_id) == v["odam_id"]:
        raise ValueError("Bu vazifa allaqachon o'shanikida")
    if not db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", yangi_odam_id):
        raise ValueError("Odam topilmadi yoki ro'yxatdan olingan")
    juft = keyingi_navbat(db, vazifa_id, yangi_odam_id)
    if not juft:
        nom = _odam_nom(db, yangi_odam_id)
        raise ValueError(
            f"{nom}ning bundan keyin «{v['nom']}» navbati yo'q — "
            f"almashtirib bo'lmaydi.\n"
            f"«Faqat shu kunni berish» dan foydalaning.")
    return {"vazifa": v, "juft": juft,
            "eski_odam": v["odam_id"], "yangi_odam": int(yangi_odam_id)}


def almashtir(db, vazifa_id: int, yangi_odam_id: int) -> dict:
    """1-variant: ikki odam navbatini almashtiradi.

    Keyingi kunlar JOYIDA qoladi va navbat soni o'zgarmaydi — faqat
    ikki kun bir-biri bilan o'rin almashadi.
    """
    r = almashtirish_rejasi(db, vazifa_id, yangi_odam_id)
    v, juft = r["vazifa"], r["juft"]
    eski_nom = _odam_nom(db, r["eski_odam"])
    yangi_nom = _odam_nom(db, r["yangi_odam"])
    with db.amal(f"Navbat almashdi: {eski_nom} ↔ {yangi_nom} "
                 f"({v['sana']} / {juft['sana']})"):
        db.apply("vazifa", "UPDATE", {"odam_id": r["yangi_odam"]}, v["id"])
        db.apply("vazifa", "UPDATE", {"odam_id": r["eski_odam"]}, juft["id"])
        tuzatildi = (_yuvuvchini_tugrila(db, v["id"])
                     + _yuvuvchini_tugrila(db, juft["id"]))
    return {"vazifa_id": v["id"], "juft_id": juft["id"],
            "juft_sana": juft["sana"], "yuvuvchi_tuzatildi": tuzatildi,
            "eski_nom": eski_nom, "yangi_nom": yangi_nom}


def bersin(db, vazifa_id: int, yangi_odam_id: int) -> dict:
    """Faqat shu kunni boshqa odamga beradi (almashuvsiz).

    Reja tuzilishidan oldingi tartibsizlikni tekislash uchun: kimdir
    ortiqcha qilgan bo'lsa, bitta navbat boshqasiga o'tkaziladi.
    """
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    if int(yangi_odam_id) == v["odam_id"]:
        raise ValueError("Bu vazifa allaqachon o'shanikida")
    if not db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", yangi_odam_id):
        raise ValueError("Odam topilmadi yoki ro'yxatdan olingan")
    eski_nom = _odam_nom(db, v["odam_id"])
    yangi_nom = _odam_nom(db, yangi_odam_id)
    with db.amal(f"«{v['nom']}» {eski_nom} → {yangi_nom} ({v['sana']})"):
        db.apply("vazifa", "UPDATE", {"odam_id": int(yangi_odam_id)}, v["id"])
        tuzatildi = _yuvuvchini_tugrila(db, v["id"])
    return {"vazifa_id": v["id"], "yuvuvchi_tuzatildi": tuzatildi,
            "eski_nom": eski_nom, "yangi_nom": yangi_nom}


# ─────────────────────────────────────────────────────────────── yozish

def qosh(db, nom: str, odam_id: int, sana, vaqt: str | None = None,
         davomiylik: int = 60, izoh: str | None = None) -> int:
    nom, iso, vaqt, davomiylik = _tekshir(db, nom, odam_id, sana, vaqt,
                                          davomiylik)
    kim = _odam_nom(db, odam_id)
    with db.amal(f"Vazifa: {nom} — {kim}, {iso}"):
        return db.apply("vazifa", "INSERT", {
            "nom": nom, "odam_id": odam_id, "sana": iso, "vaqt": vaqt,
            "davomiylik": davomiylik, "holat": OCHIQ,
            "izoh": (izoh or "").strip() or None})


def tahrir(db, vazifa_id: int, **maydonlar) -> None:
    """nom / odam_id / sana / vaqt / davomiylik / izoh."""
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    yangi = {k: maydonlar[k] for k in
             ("nom", "odam_id", "sana", "vaqt", "davomiylik", "izoh")
             if k in maydonlar}
    if not yangi:
        return
    birlashgan = dict(v) | yangi
    nom, iso, vaqt, davomiylik = _tekshir(
        db, birlashgan["nom"], birlashgan["odam_id"], birlashgan["sana"],
        birlashgan["vaqt"], birlashgan["davomiylik"])
    if "nom" in yangi:
        yangi["nom"] = nom
    if "sana" in yangi:
        yangi["sana"] = iso
    if "vaqt" in yangi:
        yangi["vaqt"] = vaqt
    if "davomiylik" in yangi:
        yangi["davomiylik"] = davomiylik
    if "izoh" in yangi:
        yangi["izoh"] = (yangi["izoh"] or "").strip() or None
    with db.amal(f"Vazifa tahrirlandi: {birlashgan['nom']}"):
        db.apply("vazifa", "UPDATE", yangi, vazifa_id)


def bajar(db, vazifa_id: int, bajarildi: bool = True) -> None:
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    holat = BAJARILDI if bajarildi else OCHIQ
    with db.amal(f"Vazifa {'bajarildi' if bajarildi else 'qayta ochildi'}:"
                 f" {v['nom']}"):
        db.apply("vazifa", "UPDATE", {
            "holat": holat,
            "bajarilgan": (datetime.now().isoformat(timespec="minutes")
                           if bajarildi else None),
            # Kechiktirish shu bilan tugaydi: ish bajarildi, endi
            # «keyinroq eslataman» degan va'daning ma'nosi yo'q.
            "kechiktirildi": None}, vazifa_id)
        # Yutuq SHU AMAL ICHIDA beriladi — bitta undo qadami.
        # Aks holda vazifa qaytarilganda yutuq osilib qolardi.
        if bajarildi:
            yutuqlarni_tekshir(db)


# ─────────────────────────────────────────────────────── kechiktirish
#
# «Bajardingizmi?» degan savolga «hali yo'q» deb javob berilsa, ish
# o'chirilmaydi va bajarilgan ham bo'lmaydi — u shunchaki KEYINROQQA
# suriladi. Shu paytgacha eslatma qayta yuborilmaydi.
#
# Nega vazifaning `vaqt` i o'zgartirilmaydi: vaqt — REJA («men buni
# soat 19:00 da qilaman»), kechiktirish esa bir martalik holat. Vaqt
# surilsa kalendardagi blok joyidan siljib ketardi va «har kuni 19:00»
# degan odat asta-sekin yarim tunga surilardi.

KECHIKTIRISH = [10, 30, 60]     # daqiqada, guruhdagi tugmalar


def kechiktir(db, vazifa_id: int, daqiqa: int, hozir=None) -> str:
    """Eslatmani `daqiqa` ga suradi va yangi vaqtni qaytaradi."""
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    daqiqa = int(daqiqa)
    if daqiqa <= 0:
        raise ValueError("Kechiktirish musbat bo'lishi kerak")
    yangi = (hozir or datetime.now()) + timedelta(minutes=daqiqa)
    # SQLite formati (orasida BO'SH JOY), `isoformat()` emas.
    matn = yangi.strftime("%Y-%m-%d %H:%M:%S")
    with db.amal(f"«{v['nom']}» {daqiqa} daqiqaga kechiktirildi"):
        db.apply("vazifa", "UPDATE", {"kechiktirildi": matn}, vazifa_id)
    return matn


def kechiktirilganmi(v, hozir=None) -> bool:
    """Shu vazifaning eslatmasi hali kutib turishi kerakmi?"""
    qiymat = v["kechiktirildi"] if "kechiktirildi" in v.keys() else None
    if not qiymat:
        return False
    return (hozir or datetime.now()).strftime("%Y-%m-%d %H:%M:%S") < qiymat


def menyu_qoy(db, vazifa_id: int, taom: str | None) -> None:
    """O'sha kuni nima pishirilgani.

    NOM bilan saqlanadi, `menyu.id` bilan emas: taom ro'yxatdan olib
    tashlansa ham «o'sha kuni nima pishirilgan» degan yozuv qolsin.
    """
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    taom = (taom or "").strip() or None
    with db.amal(f"Menyu: {taom or '—'} ({v['nom']})"):
        db.apply("vazifa", "UPDATE", {"menyu": taom}, vazifa_id)


def ochir(db, vazifa_id: int) -> None:
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    with db.amal(f"Vazifa o'chirildi: {v['nom']}"):
        db.apply("vazifa", "DELETE", qator_id=vazifa_id)


# ─────────────────────────────────────────────────────────────── surish

def surilganlar(db, sana, odam_id: int | None = None) -> list:
    """`surish()` nimani qo'zg'atishini OLDINDAN ko'rsatadi.

    Foydalanuvchi tasdiqlashdan oldin ro'yxatni ko'rsin — bir tugma
    bosishda o'nlab vazifa siljishi mumkin.
    """
    p = [OCHIQ, _sana(sana).isoformat()]
    qosh_shart = ""
    if odam_id:
        qosh_shart = " AND v.odam_id=?"
        p.append(odam_id)
    return db.q(
        "SELECT v.*, o.nom odam FROM vazifa v"
        " JOIN odam o ON o.id=v.odam_id"
        " WHERE v.ochirilgan=0 AND v.holat=? AND v.sana>=?" + qosh_shart +
        " ORDER BY v.sana, COALESCE(v.vaqt,'99:99'), v.id", *p)


def surish(db, sana, odam_id: int | None = None, kunlar: int = 1) -> int:
    """Excel B13: bir kun o'tkazib yuborilsa, keyingi hamma ish suriladi.

    `sana` dan boshlab BAJARILMAGAN vazifalarning hammasi `kunlar`
    kunga oldinga suriladi. Bajarilganlar joyida qoladi — ular allaqachon
    tarixning bir qismi.

    Hammasi bitta guruh: qaytarish kerak bo'lsa bitta qadamda qaytadi.
    """
    if kunlar == 0:
        return 0
    qatorlar = surilganlar(db, sana, odam_id)
    if not qatorlar:
        return 0
    kim = f" ({_odam_nom(db, odam_id)})" if odam_id else ""
    with db.amal(f"{len(qatorlar)} ta vazifa {kunlar} kunga surildi{kim}"):
        # Oldinga surishda oxirgisidan boshlanadi — shunda ikki vazifa
        # bir zumda bir xil kunga tushib qolmaydi.
        tartib = sorted(qatorlar, key=lambda r: r["sana"],
                        reverse=kunlar > 0)
        for r in tartib:
            yangi = (_sana(r["sana"]) + timedelta(days=kunlar)).isoformat()
            db.apply("vazifa", "UPDATE", {"sana": yangi}, r["id"])
    return len(qatorlar)


# ─────────────────────────────────────────────────────────────── o'qish

def bitta(db, vazifa_id: int):
    return db.q1("SELECT * FROM vazifa WHERE id=? AND ochirilgan=0",
                 vazifa_id)


def hafta(db, sana, odam_id: int | None = None,
          shaxsiysiz: bool = False) -> list:
    """Bir haftalik vazifalar, kun va vaqt bo'yicha tartiblangan."""
    kunlar = hafta_kunlari(sana)
    return oraliq(db, kunlar[0], kunlar[-1], odam_id, shaxsiysiz)


def oraliq(db, dan, gacha, odam_id: int | None = None,
           shaxsiysiz: bool = False) -> list:
    """`shaxsiysiz` — 🔒 shaxsiy ishlar tushib qoladi.

    Umumiy kalendar (uchalasining ishi birga) shu bilan chaqiriladi:
    shaxsiy ish guruh xabariga chiqmasa, umumiy varaqda ham turmasligi
    kerak — aks holda «bu faqat sizga» degan va'da yarmigacha bajariladi.
    Shaxsiy varaqda esa hammasi ko'rinadi.
    """
    p = [_sana(dan).isoformat(), _sana(gacha).isoformat()]
    qosh_shart = ""
    if odam_id:
        qosh_shart = " AND v.odam_id=?"
        p.append(odam_id)
    qatorlar = db.q(
        "SELECT v.*, o.nom odam, o.rang odam_rang"
        " FROM vazifa v JOIN odam o ON o.id=v.odam_id"
        " WHERE v.ochirilgan=0 AND v.sana BETWEEN ? AND ?" + qosh_shart +
        " ORDER BY v.sana, COALESCE(v.vaqt,'99:99'), v.id", *p)
    if shaxsiysiz:
        # Nom bo'yicha — `xabar.py` dagi filtr bilan AYNAN bir xil
        # qoida, ikkinchi ta'rif yozilmaydi.
        yopiq = shaxsiy_nomlari(db)
        qatorlar = [r for r in qatorlar if r["nom"] not in yopiq]
    return qatorlar


def kun(db, sana, odam_id: int | None = None,
        shaxsiysiz: bool = False) -> list:
    return oraliq(db, sana, sana, odam_id, shaxsiysiz)


def sanoq(db, dan, gacha, odam_id: int | None = None,
          shaxsiysiz: bool = False) -> dict:
    """Haftalik xulosa: nechta ochiq, nechta bajarilgan, nechta kechikkan."""
    qatorlar = oraliq(db, dan, gacha, odam_id, shaxsiysiz)
    bugun = date.today()
    kechikkan = sum(1 for r in qatorlar
                    if r["holat"] == OCHIQ and _sana(r["sana"]) < bugun)
    bajarildi = sum(1 for r in qatorlar if r["holat"] == BAJARILDI)
    return {"jami": len(qatorlar), "bajarildi": bajarildi,
            "ochiq": len(qatorlar) - bajarildi, "kechikkan": kechikkan}


# ═══════════════════════════════════════════════════════════ streak
#
# «Har kuni kitob o'qish» kabi odat: BITTA odam + BITTA ish turi +
# nishon (7 / 14 / 21 / 28 kun). Nishon qo'lga kiritilsa odam
# «Po'lat iroda» yutug'ini oladi.
#
# Ketma-ket kunlar soni HECH QAYERDA SAQLANMAYDI — u har safar
# `vazifa` jadvalidan qayta hisoblanadi. Saqlangan hisoblagich undo
# bilan ajralib qolardi: vazifa qaytarilsa hisoblagich o'sha joyda
# turib olardi va streak yolg'on gapirardi.
#
# Bugungi kun HISOBGA OLINMAYDI, agar bugun hali bajarilmagan bo'lsa:
# kun tugamagan, ya'ni streak hali uzilmagan. Aks holda har ertalab
# hamma streak nolga tushib ketardi.

NISHONLAR = [7, 14, 21, 28]
YUTUQ_IRODA = "Po'lat iroda"


def streaklar(db, odam_id: int | None = None) -> list:
    p = []
    shart = ""
    if odam_id:
        shart = " AND s.odam_id=?"
        p.append(odam_id)
    return db.q(
        "SELECT s.*, o.nom odam, t.nom ish"
        " FROM streak s"
        " JOIN odam o ON o.id = s.odam_id"
        " JOIN vazifa_turi t ON t.id = s.turi_id"
        " WHERE s.ochirilgan=0" + shart +
        " ORDER BY o.tartib, o.id, t.tartib, t.id", *p)


def streak_bitta(db, streak_id: int):
    return db.q1("SELECT * FROM streak WHERE id=? AND ochirilgan=0",
                 streak_id)


def streak_qosh(db, odam_id: int, turi_id: int, nishon: int = 7,
                boshlandi=None) -> int:
    if int(nishon) not in NISHONLAR:
        raise ValueError(f"Nishon {NISHONLAR} dan biri bo'lishi kerak")
    if not db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", odam_id):
        raise ValueError("Odam topilmadi yoki ro'yxatdan olingan")
    t = tur_bitta(db, turi_id)
    if not t:
        raise ValueError("Vazifa turi topilmadi")
    iso = _sana(boshlandi or date.today()).isoformat()
    # `UNIQUE(odam_id, turi_id)`: o'chirilgani bor bo'lsa tiriltiramiz,
    # aks holda qayta INSERT yiqiladi.
    eski = db.q1("SELECT id, ochirilgan FROM streak"
                 " WHERE odam_id=? AND turi_id=?", odam_id, turi_id)
    kim = _odam_nom(db, odam_id)
    if eski:
        if not eski["ochirilgan"]:
            raise ValueError(f"{kim} uchun «{t['nom']}» streagi allaqachon bor")
        with db.amal(f"Streak qaytarildi: {kim} — {t['nom']}"):
            db.apply("streak", "UPDATE",
                     {"ochirilgan": 0, "nishon": int(nishon),
                      "boshlandi": iso}, eski["id"])
        return eski["id"]
    with db.amal(f"Streak: {kim} — {t['nom']}, {nishon} kun"):
        return db.apply("streak", "INSERT", {
            "odam_id": odam_id, "turi_id": turi_id,
            "nishon": int(nishon), "boshlandi": iso})


def streak_ochir(db, streak_id: int) -> None:
    s = streak_bitta(db, streak_id)
    if not s:
        raise ValueError("Streak topilmadi")
    with db.amal("Streak to'xtatildi"):
        db.apply("streak", "DELETE", qator_id=streak_id)


def streak_kunlari(db, odam_id: int, turi_id: int, bugun=None) -> int:
    """Ketma-ket nechta kun bajarilgan.

    Bugun hali bajarilmagan bo'lsa sanoq KECHAdan boshlanadi: kun
    tugamagan, streak esa hali uzilmagan.
    """
    t = tur_bitta(db, turi_id)
    if not t:
        return 0
    kunlar = {r["sana"] for r in db.q(
        "SELECT DISTINCT sana FROM vazifa"
        " WHERE ochirilgan=0 AND holat=? AND odam_id=? AND nom=?",
        BAJARILDI, odam_id, t["nom"])}
    if not kunlar:
        return 0
    k = _sana(bugun or date.today())
    if k.isoformat() not in kunlar:
        k -= timedelta(days=1)
    n = 0
    while k.isoformat() in kunlar:
        n += 1
        k -= timedelta(days=1)
    return n


def streak_holati(db, s, bugun=None) -> dict:
    """Bitta streakning to'liq holati — UI shu bilan ishlaydi."""
    kun = streak_kunlari(db, s["odam_id"], s["turi_id"], bugun)
    nishon = int(s["nishon"])
    return {
        "id": s["id"], "odam_id": s["odam_id"], "turi_id": s["turi_id"],
        "odam": s["odam"] if "odam" in s.keys() else "",
        "ish": s["ish"] if "ish" in s.keys() else "",
        "kun": kun, "nishon": nishon,
        "qoldi": max(0, nishon - kun),
        "bajarildi": kun >= nishon,
        "ulush": min(1.0, kun / nishon) if nishon else 0.0,
    }


# ── yutuqlar ─────────────────────────────────────────────────────────

def yutuqlar(db, odam_id: int | None = None) -> list:
    p = []
    shart = ""
    if odam_id:
        shart = " AND y.odam_id=?"
        p.append(odam_id)
    return db.q(
        "SELECT y.*, o.nom odam FROM yutuq y"
        " JOIN odam o ON o.id = y.odam_id"
        " WHERE y.ochirilgan=0" + shart +
        " ORDER BY y.sana DESC, y.id DESC", *p)


def yutuq_bormi(db, odam_id: int, streak_id: int, nishon: int) -> bool:
    return bool(db.q1(
        "SELECT 1 FROM yutuq WHERE ochirilgan=0 AND odam_id=?"
        " AND streak_id=? AND nishon=?", odam_id, streak_id, nishon))


def yutuqlarni_tekshir(db, bugun=None) -> list[dict]:
    """Nishonga yetgan streaklarga yutuq beradi. Yangilarini qaytaradi.

    `bajar()` dan keyin chaqiriladi, lekin mustaqil ham ishlaydi:
    dastur bir hafta yopiq turgan bo'lsa ham yutuq yo'qolmaydi.

    Yutuq BIR MARTA beriladi (`yutuq_bormi`) — aks holda har
    bajarishda takrorlanardi.
    """
    yangi = []
    for s in streaklar(db):
        h = streak_holati(db, s, bugun)
        if not h["bajarildi"]:
            continue
        if yutuq_bormi(db, s["odam_id"], s["id"], h["nishon"]):
            continue
        izoh = f"{h['ish']} — {h['nishon']} kun ketma-ket"
        with db.amal(f"Yutuq: {h['odam']} — {YUTUQ_IRODA}"):
            yid = db.apply("yutuq", "INSERT", {
                "odam_id": s["odam_id"], "nom": YUTUQ_IRODA, "izoh": izoh,
                "sana": _sana(bugun or date.today()).isoformat(),
                "streak_id": s["id"], "nishon": h["nishon"]})
        yangi.append({"id": yid, "odam_id": s["odam_id"], "odam": h["odam"],
                      "nom": YUTUQ_IRODA, "izoh": izoh,
                      "nishon": h["nishon"], "ish": h["ish"]})
    return yangi
