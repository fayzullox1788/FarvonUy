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
# Namoz o'z vaqtida o'qilmadi. Bajarilmagan, lekin «ochiq» ham emas:
# eslatma endi so'ramaydi, o'rniga alohida «qazosini o'qish» ishi turadi.
QAZO = "qazo"

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
#   2. Idishni PISHIRGAN ODAMNING O'ZI yuvadi. Ya'ni:
#         Fayzulloxon pishirsa  → Fayzulloxon yuvadi
#         Otabek pishirsa       → Otabek yuvadi
#         Abbosxon pishirsa     → Abbosxon yuvadi
#      2026-09-17 gacha idishni navbatdagi OLDINGI odam yuvardi (`-1`);
#      foydalanuvchi o'zi o'zgartirdi. Idish baribir ALOHIDA vazifa
#      bo'lib qoladi: eslatma, «Albatta!» tugmasi va hisobot uni
#      ovqatdan ajratib ko'radi.

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
        yuvuvchi = oshpaz
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
# «kim pishirsa, o'sha yuvadi» qoidasi buzilmasin.


def navbat_turi(db):
    """Navbatli ish turi (odatda «Ovqat qilish»). Yo'q bo'lsa None."""
    return db.q1("SELECT * FROM vazifa_turi"
                 " WHERE navbat=1 AND ochirilgan=0 ORDER BY tartib LIMIT 1")


def yuvuvchi_id(db, oshpaz_id: int):
    """Shu oshpazning idishini kim yuvadi — oshpazning O'ZI."""
    idlar = [r["id"] for r in navbat_odamlari(db)]
    if oshpaz_id not in idlar:
        return None
    return oshpaz_id


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
        # Qazo deb belgilangan namoz qayta ochilsa yoki o'qildi deyilsa,
        # uning hali o'qilmagan qazo ishi ham shu amalda olib tashlanadi.
        if v["holat"] == QAZO:
            for q in qazo_ishlari(db, vazifa_id, faqat_ochiq=True):
                db.apply("vazifa", "DELETE", qator_id=q["id"])


def yopiqmi(v) -> bool:
    """Endi eslatish shart emasmi — bajarilgan yoki qazo bo'lgan."""
    return v["holat"] in (BAJARILDI, QAZO)


# ─────────────────────────────────────────────────────────────── qazo
#
# Namoz o'qilmay qolsa: «Qazo bo'ldi» bosiladi. Namoz `QAZO` holatiga
# o'tadi va o'sha odamga «<namoz> — qazosini o'qish» degan yangi ish
# yoziladi (vaqtsiz, bugun). Ikkalasi BITTA amal — bitta Ctrl+Z.
#
# Namoz NOMIDAN taniladi: takror qoidalari («Asr namozi», «Peshin»)
# foydalanuvchi o'zi yozgan nomlar, alohida belgi yo'q.

NAMOZ_SOZLAR = ("namoz", "nomoz", "namaz", "bomdod", "peshin", "asr",
                "shom", "xufton")
QAZO_QOSHIMCHA = "qazosini o'qish"
QAZO_BELGI = "qazo"


def qazo_ishimi(v) -> bool:
    return str(v["manba"] or "").startswith(f"{QAZO_BELGI}:") if v else False


def namozmi(v) -> bool:
    """Bu vazifa namozmi (qazo ishining o'zi emas)."""
    if not v or qazo_ishimi(v):
        return False
    sozlar = str(v["nom"] or "").lower().replace("'", " ").split()
    return any(s.startswith(n) for s in sozlar for n in NAMOZ_SOZLAR)


def qazo_nomi(nom: str) -> str:
    return f"{nom} — {QAZO_QOSHIMCHA}"


def qazo_ishlari(db, vazifa_id: int, faqat_ochiq: bool = False) -> list:
    shart = " AND holat=?" if faqat_ochiq else ""
    p = [f"{QAZO_BELGI}:{int(vazifa_id)}"] + ([OCHIQ] if faqat_ochiq else [])
    return db.q("SELECT * FROM vazifa WHERE ochirilgan=0 AND manba=?"
                + shart, *p)


def qazo_qil(db, vazifa_id: int, bugun=None) -> int:
    """Namozni qazo deb belgilaydi va qazosini o'qish ishini yozadi.

    Qazo ishi bugunga (yoki namoz kelajakda bo'lsa — o'sha kunga)
    tushadi. Yangi ishning id sini qaytaradi.
    """
    v = bitta(db, vazifa_id)
    if not v:
        raise ValueError("Vazifa topilmadi")
    if not namozmi(v):
        raise ValueError(f"«{v['nom']}» namoz emas")
    if v["holat"] != OCHIQ:
        raise ValueError("Faqat hali o'qilmagan namoz qazo bo'ladi")
    kun = max(_sana(v["sana"]), _sana(bugun or date.today()))
    asl = _sana(v["sana"])
    with db.amal(f"Qazo: {v['nom']} ({asl.strftime('%d.%m')})"):
        db.apply("vazifa", "UPDATE", {
            "holat": QAZO, "bajarilgan": None, "kechiktirildi": None},
            vazifa_id)
        return db.apply("vazifa", "INSERT", {
            "nom": qazo_nomi(v["nom"]), "odam_id": v["odam_id"],
            "sana": kun.isoformat(), "vaqt": None,
            "davomiylik": v["davomiylik"], "holat": OCHIQ,
            "izoh": f"{asl.strftime('%d.%m.%Y')} kungi {v['nom']}",
            "manba": f"{QAZO_BELGI}:{int(vazifa_id)}"})


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
    qazo = sum(1 for r in qatorlar if r["holat"] == QAZO)
    return {"jami": len(qatorlar), "bajarildi": bajarildi,
            "ochiq": len(qatorlar) - bajarildi, "kechikkan": kechikkan,
            "qazo": qazo}


# ═════════════════════════════ takroriy vazifa
#
# "Namoz o'qish har kuni" - bitta QOIDA, ming dona qator emas.
#
# Qoida `vazifa_takror` da turadi, kalendardagi kunlar esa undan
# chiqariladi: `takror_toldir()` bugundan boshlab `TAKROR_UFQ` kunga
# yetguncha yetishmagan `vazifa` qatorlarini yozadi. U dastur
# ochilganda va `xabarchi.py` har chaqirilganda ishlaydi - ya'ni
# ro'yxat hech qachon tugamaydi va foydalanuvchi "yana 30 kunga
# yozib qo'y" deb esga olishi shart emas.
#
# Nega haqiqiy qator yoziladi, "virtual vazifa" ko'rsatilmaydi:
# kalendar, eslatma, hisobot va streak - hammasi `vazifa` jadvalidan
# o'qiydi. Ikkinchi manba qo'shilsa o'sha to'rttasi ham ikki joydan
# o'qishga majbur bo'lardi. `dars` bilan aynan bir xil sabab.
#
# Bog'lanish `vazifa.manba` orqali: `takror:<id>:<sana>` - sana
# kalitning ICHIDA, shuning uchun to'ldirish necha marta chaqirilsa
# ham ikkinchi nusxa yozilmaydi.

TAKROR_UFQ = 30          # necha kun oldinga to'ldiriladi
TAKROR_BELGI = "takror"

NAQSH_KUNLIK = "kunlik"
NAQSH_KUNLAR = "kunlar"
NAQSH_ORALIQ = "oraliq"
NAQSHLAR = {
    NAQSH_KUNLIK: "Har kuni",
    NAQSH_KUNLAR: "Tanlangan kunlar",
    NAQSH_ORALIQ: "Har N kunda",
}


def takror_kaliti(takror_id: int, sana) -> str:
    return f"{TAKROR_BELGI}:{int(takror_id)}:{_sana(sana).isoformat()}"


def _kunlar_matn(kunlar) -> str:
    """[0, 2, 4] -> "0,2,4". Tartiblangan va takrorsiz."""
    if isinstance(kunlar, str):
        kunlar = [x for x in kunlar.replace(" ", "").split(",") if x]
    toza = sorted({int(x) for x in (kunlar or [])})
    if any(not 0 <= k <= 6 for k in toza):
        raise ValueError("Hafta kuni 0 (dushanba) va 6 (yakshanba) orasida")
    return ",".join(str(k) for k in toza)


def takror_kunlari(t) -> list[int]:
    """Qatordagi "0,2,4" -> [0, 2, 4]."""
    return [int(x) for x in str(t["kunlar"] or "").split(",") if x != ""]


def _takrorni_tekshir(db, nom, odam_id, vaqt, davomiylik, naqsh,
                      kunlar, oraliq, boshlanish, tugash) -> dict:
    nom, iso, vaqt, davomiylik = _tekshir(db, nom, odam_id, boshlanish,
                                          vaqt, davomiylik)
    if naqsh not in NAQSHLAR:
        raise ValueError(f"Noma'lum takror naqshi: {naqsh}")
    kunlar_m = ""
    # `oraliq or 1` EMAS: 0 ham bo'sh deb hisoblanib jimgina 1 ga
    # aylanardi, ya'ni «har 0 kunda» degan xato har kunlik qoidaga
    # o'girilib ketardi.
    oraliq = 1 if oraliq is None else int(oraliq)
    if naqsh == NAQSH_KUNLAR:
        kunlar_m = _kunlar_matn(kunlar)
        if not kunlar_m:
            raise ValueError("Kamida bitta hafta kuni tanlanishi kerak")
        oraliq = 1
    elif naqsh == NAQSH_ORALIQ:
        if not 1 <= oraliq <= 90:
            raise ValueError("Oraliq 1 va 90 kun orasida bo'lishi kerak")
    else:
        oraliq = 1
    tugash_iso = None
    if tugash:
        tugash_iso = _sana(tugash).isoformat()
        if tugash_iso < iso:
            raise ValueError("Tugash sanasi boshlanishdan oldin bo'lmaydi")
    return {"nom": nom, "odam_id": odam_id, "vaqt": vaqt,
            "davomiylik": davomiylik, "naqsh": naqsh,
            "kunlar": kunlar_m or None, "oraliq": oraliq,
            "boshlanish": iso, "tugash": tugash_iso}


def takrorlar(db, faqat_faol: bool = False) -> list:
    shart = " AND tk.faol=1" if faqat_faol else ""
    return db.q(
        "SELECT tk.*, o.nom odam FROM vazifa_takror tk"
        " JOIN odam o ON o.id = tk.odam_id"
        f" WHERE tk.ochirilgan=0{shart}"
        " ORDER BY tk.nom, tk.id")


def takror_bitta(db, takror_id: int):
    return db.q1("SELECT * FROM vazifa_takror WHERE id=? AND ochirilgan=0",
                 takror_id)


def takror_tavsif(t) -> str:
    """"Har kuni 06:00" - kartada va tasdiq oynasida ko'rinadigan qator."""
    if t["naqsh"] == NAQSH_KUNLAR:
        kunlar = takror_kunlari(t)
        qachon = ", ".join(KUN_QISQA[k] for k in kunlar) or "—"
    elif t["naqsh"] == NAQSH_ORALIQ:
        qachon = ("Har kuni" if t["oraliq"] == 1
                  else f"Har {t['oraliq']} kunda")
    else:
        qachon = NAQSHLAR[NAQSH_KUNLIK]
    return f"{qachon} {t['vaqt'] or 'vaqtsiz'}"


def takror_sanalari(t, dan, gacha) -> list:
    """Qoida shu oraliqda qaysi kunlarga tushadi. Bazaga tegmaydi."""
    b = _sana(t["boshlanish"])
    d0 = max(_sana(dan), b)
    d1 = _sana(gacha)
    if t["tugash"]:
        d1 = min(d1, _sana(t["tugash"]))
    naqsh = t["naqsh"]
    kunlar = set(takror_kunlari(t)) if naqsh == NAQSH_KUNLAR else set()
    oraliq = max(1, int(t["oraliq"] or 1))
    natija = []
    kun = d0
    while kun <= d1:
        if naqsh == NAQSH_KUNLAR:
            mos = kun.weekday() in kunlar
        elif naqsh == NAQSH_ORALIQ:
            # Sanoq HAR DOIM `boshlanish` dan yuradi, "oxirgi yozilgan
            # kun" dan emas: bitta kun qo'lda o'chirilsa yoki dastur bir
            # hafta ochilmasa ham naqsh joyidan siljimasin.
            mos = (kun - b).days % oraliq == 0
        else:
            mos = True
        if mos:
            natija.append(kun)
        kun += timedelta(days=1)
    return natija


def takror_toldir(db, bugun=None, ufq: int = TAKROR_UFQ) -> int:
    """Har bir faol qoidani `ufq` kunga yetguncha to'ldiradi.

    O'TMISHGA YOZMAYDI: sanoq bugundan boshlanadi. Aks holda dastur
    bir hafta ochilmasa, o'tib ketgan kunlar "bajarilmagan" bo'lib
    kalendarga to'kilardi.

    O'CHIRILGAN kun QAYTA TIRILMAYDI: mavjudlik `ochirilgan` ni
    filtrlamasdan tekshiriladi, ya'ni foydalanuvchi bitta kunni bekor
    qilsa u keyingi to'ldirishda qaytib kelmaydi.
    """
    d0 = _sana(bugun or date.today())
    d1 = d0 + timedelta(days=max(0, int(ufq)))
    yoziladi = []
    for t in takrorlar(db, faqat_faol=True):
        sanalar = takror_sanalari(t, d0, d1)
        if not sanalar:
            continue
        bor = {r["manba"] for r in db.q(
            "SELECT manba FROM vazifa WHERE manba LIKE ?"
            " AND sana BETWEEN ? AND ?",
            f"{TAKROR_BELGI}:{t['id']}:%",
            sanalar[0].isoformat(), sanalar[-1].isoformat())}
        for kun in sanalar:
            kalit = takror_kaliti(t["id"], kun)
            if kalit not in bor:
                yoziladi.append((t, kun, kalit))
    if not yoziladi:
        # Hech narsa yozilmasa `amal()` ham ochilmaydi: bu funksiya har
        # daqiqada chaqiriladi, bo'sh guruh esa undo stekini ma'nosiz
        # qadamlar bilan to'ldirardi (va redo yo'lini yopardi).
        return 0
    with db.amal(f"Takroriy vazifalar: {len(yoziladi)} ta kun qo'shildi"):
        for t, kun, kalit in yoziladi:
            db.apply("vazifa", "INSERT", {
                "nom": t["nom"], "odam_id": t["odam_id"],
                "sana": kun.isoformat(), "vaqt": t["vaqt"],
                "davomiylik": t["davomiylik"], "holat": OCHIQ,
                "izoh": t["izoh"], "manba": kalit})
    return len(yoziladi)


def takror_qosh(db, nom: str, odam_id: int, vaqt: str | None = None,
                davomiylik: int = 60, naqsh: str = NAQSH_KUNLIK,
                kunlar=None, oraliq: int = 1, izoh: str | None = None,
                boshlanish=None, tugash=None, bugun=None) -> int:
    """Yangi takror qoidasi - va o'sha zahoti birinchi kunlar.

    Qoida va undan chiqqan kunlar BITTA amal: foydalanuvchi
    "takrorlansin" deb bosgan narsa bitta qadamda qaytishi kerak.
    """
    d = _takrorni_tekshir(db, nom, odam_id, vaqt, davomiylik, naqsh,
                          kunlar, oraliq,
                          boshlanish or (bugun or date.today()), tugash)
    d["izoh"] = (izoh or "").strip() or None
    with db.amal(f"Takroriy vazifa: {d['nom']}"):
        tid = db.apply("vazifa_takror", "INSERT", d)
        takror_toldir(db, bugun)
    return tid


def _takror_kelajagini_ochir(db, takror_id: int, bugun=None) -> int:
    """Bugundan boshlab hali OCHIQ kunlarni o'chiradi.

    Bajarilgani ham, o'tgan kunlar ham tegilmaydi - tarix qoidaning
    keyingi taqdiriga bog'liq emas.
    """
    d0 = _sana(bugun or date.today()).isoformat()
    qatorlar = db.q(
        "SELECT id FROM vazifa WHERE ochirilgan=0 AND holat=?"
        " AND sana>=? AND manba LIKE ?",
        OCHIQ, d0, f"{TAKROR_BELGI}:{int(takror_id)}:%")
    for r in qatorlar:
        db.apply("vazifa", "DELETE", qator_id=r["id"])
    return len(qatorlar)


def takror_tahrir(db, takror_id: int, bugun=None, **maydonlar) -> None:
    """Qoidani o'zgartiradi. O'TGAN kunlarga tegmaydi.

    Bugundan boshlab hali BAJARILMAGAN kunlar o'chiriladi va qoida
    qaytadan to'ldiriladi. Bajarilgani joyida qoladi: "men buni
    qildim" degan yozuvni qoida tahriri bekor qilmaydi.
    """
    t = takror_bitta(db, takror_id)
    if not t:
        raise ValueError("Takroriy vazifa topilmadi")
    b = dict(t) | {k: v for k, v in maydonlar.items() if k in
                   ("nom", "odam_id", "vaqt", "davomiylik", "naqsh",
                    "kunlar", "oraliq", "izoh", "boshlanish", "tugash",
                    "faol")}
    d = _takrorni_tekshir(db, b["nom"], b["odam_id"], b["vaqt"],
                          b["davomiylik"], b["naqsh"], b["kunlar"],
                          b["oraliq"], b["boshlanish"], b["tugash"])
    d["izoh"] = (b["izoh"] or "").strip() or None
    d["faol"] = 1 if b["faol"] else 0
    with db.amal(f"Takroriy vazifa tahrirlandi: {d['nom']}"):
        db.apply("vazifa_takror", "UPDATE", d, takror_id)
        _takror_kelajagini_ochir(db, takror_id, bugun)
        takror_toldir(db, bugun)


def takror_ochir(db, takror_id: int, bugun=None) -> int:
    """Qoidani to'xtatadi va kelajakdagi kunlarini olib tashlaydi."""
    t = takror_bitta(db, takror_id)
    if not t:
        raise ValueError("Takroriy vazifa topilmadi")
    with db.amal(f"Takroriy vazifa to'xtatildi: {t['nom']}"):
        db.apply("vazifa_takror", "DELETE", qator_id=takror_id)
        return _takror_kelajagini_ochir(db, takror_id, bugun)


def takrorlimi(v) -> bool:
    """Bu vazifa qatori takror qoidasidan chiqqanmi?"""
    if not v:
        return False
    try:
        manba = v["manba"]
    except (IndexError, KeyError):
        return False
    return str(manba or "").startswith(f"{TAKROR_BELGI}:")


def takror_egasi(db, v):
    """Vazifa qaysi qoidadan chiqqan. Qoida o'chirilgan bo'lsa None."""
    if not takrorlimi(v):
        return None
    try:
        tid = int(str(v["manba"]).split(":")[1])
    except (IndexError, ValueError):
        return None
    return takror_bitta(db, tid)


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
