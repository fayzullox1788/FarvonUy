"""Yozuvlar: kirim, rasxod, qarz, hisob-kitob.

Har bir funksiya `db.amal()` ichida ishlaydi — ya'ni rasxod va uning
ulushlari BITTA Ctrl+Z qadami bo'ladi. UI shu funksiyalardan boshqa
hech narsa chaqirmaydi.
"""
from __future__ import annotations

import money
from core import hamyon, splitting

# "berilmagan" ni "None qilib qo'y" dan ajratish uchun.
# kim_uchun=None — "endi boshqa uchun emas" degani, shuning uchun
# oddiy None ni "tegmasin" deb talqin qilib bo'lmaydi.
_TEGMA = object()


# ────────────────────────────────────────────────────────────── kirim

def kirim_qosh(db, sana: str, odam_id: int, summa: int,
               sabab: str | None = None, karta_id: int | None = None) -> int:
    """`karta_id` — pul qaysi kartaga tushdi (None — naqd)."""
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Kirim summasi musbat bo'lishi kerak")
    hamyon.tekshir_karta(db, karta_id, odam_id)
    nom = _odam_nom(db, odam_id)
    with db.amal(f"Kirim: {nom} +{money.fmt(summa)}"):
        return db.apply("kirim", "INSERT", {
            "sana": sana, "odam_id": odam_id, "summa": summa,
            "sabab": sabab or None, "karta_id": karta_id})


def kirim_tahrir(db, kirim_id: int, **maydonlar) -> None:
    if "karta_id" in maydonlar or "odam_id" in maydonlar:
        eski = db.q1("SELECT odam_id, karta_id FROM kirim WHERE id=?", kirim_id)
        if eski:
            hamyon.tekshir_karta(
                db, maydonlar.get("karta_id", eski["karta_id"]),
                maydonlar.get("odam_id", eski["odam_id"]))
    with db.amal("Kirim tahrirlandi"):
        db.apply("kirim", "UPDATE", maydonlar, kirim_id)


def kirim_ochir(db, kirim_id: int) -> None:
    with db.amal("Kirim o'chirildi"):
        db.apply("kirim", "DELETE", qator_id=kirim_id)


# ───────────────────────────────────────────────────────────── rasxod

def rasxod_majburiy(db, nom: str | None, turi_id: int | None) -> None:
    """Qo'lda yoziladigan har rasxodda sabab VA kategoriya bo'lishi shart.

    `rasxod_qosh()` ning o'zida tekshirilmaydi: Excel importi va takroriy
    rasxodlar eski ma'lumotdan keladi, ularda kategoriya bo'lmasligi
    mumkin. Shuning uchun uni rasxod yozadigan har bir OYNA chaqiradi.
    """
    if not (nom or "").strip():
        raise ValueError("Sabab yozilmagan — rasxod nima uchun?")
    if turi_id is None:
        raise ValueError("Kategoriya tanlanmagan.")
    if not db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", turi_id):
        raise ValueError("Bu kategoriya endi yo'q — boshqasini tanlang.")


def rasxod_qosh(db, sana: str, nom: str, summa: int, kim_toladi: int,
                umumiymi: bool = True, turi_id: int | None = None,
                usul: str = money.USUL_TENG,
                parametrlar: dict[int, float] | None = None,
                izoh: str | None = None, item_id: int | None = None,
                reja_id: int | None = None, takror_id: int | None = None,
                kim_uchun: int | None = None,
                karta_id: int | None = None) -> int:
    """Rasxod + (umumiy bo'lsa) ulushlar. Bitta undo qadami.

    `karta_id` — pul qaysi kartadan chiqdi (None — naqd, `core/hamyon.py`).

    `kim_uchun` berilsa — bu BOSHQA ODAM UCHUN qilingan xarid:
    pulni `kim_toladi` chiqaradi, lekin rasxod butunlay `kim_uchun`
    niki bo'ladi va u shu summaga qarzdor bo'ladi.

    Bu KIRIM emas. Pul o'sha odamning qo'liga tegmagan, shuning uchun
    uning `naqd` (real balans) raqami umuman o'zgarmaydi — faqat qarzi
    ortadi. Aynan shu narsa "pul berib, keyin uni sarfladi" deb
    yozishdan farq qiladi.
    """
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Rasxod summasi musbat bo'lishi kerak")
    hamyon.tekshir_karta(db, karta_id, kim_toladi)

    if kim_uchun is not None:
        # 100% bitta odamga — bo'lish shart emas, qoldiq ham yo'q.
        umumiymi = True
        usul = money.USUL_ANIQ
        parametrlar = {kim_uchun: summa}

    ulushlar = []
    if umumiymi:
        ulushlar = splitting.hisobla(db, summa, sana, usul, parametrlar)

    kim = _odam_nom(db, kim_toladi)
    if kim_uchun is not None:
        tur = f"{_odam_nom(db, kim_uchun)} uchun"
    else:
        tur = "Umumiy" if umumiymi else "Shaxsiy"
    with db.amal(f"{tur} rasxod: {nom or '—'} {money.fmt(summa)} ({kim})"):
        rid = db.apply("rasxod", "INSERT", {
            "sana": sana, "nom": nom or "", "turi_id": turi_id, "summa": summa,
            "kim_toladi": kim_toladi, "umumiymi": 1 if umumiymi else 0,
            "bolish_usul": usul, "item_id": item_id, "reja_id": reja_id,
            "takror_id": takror_id, "kim_uchun": kim_uchun,
            "izoh": izoh or None, "karta_id": karta_id})
        for u in ulushlar:
            db.apply("ulush", "INSERT", {
                "rasxod_id": rid, "odam_id": u.odam_id,
                "summa": u.summa, "yaxlitlash": u.yaxlitlash})
        return rid


def rasxod_tahrir(db, rasxod_id: int, *, sana=None, nom=None, summa=None,
                  kim_toladi=None, umumiymi=None, turi_id=None,
                  usul=None, parametrlar=None, izoh=None,
                  kim_uchun=_TEGMA, item_id=_TEGMA,
                  karta_id=_TEGMA) -> None:
    """Rasxodni o'zgartiradi va kerak bo'lsa ulushlarni QAYTA hisoblaydi."""
    eski = db.q1("SELECT * FROM rasxod WHERE id=?", rasxod_id)
    if not eski:
        raise ValueError("Rasxod topilmadi")

    yangi = {
        "sana": sana if sana is not None else eski["sana"],
        "nom": nom if nom is not None else eski["nom"],
        "summa": int(summa) if summa is not None else eski["summa"],
        "kim_toladi": kim_toladi if kim_toladi is not None else eski["kim_toladi"],
        "umumiymi": (1 if umumiymi else 0) if umumiymi is not None else eski["umumiymi"],
        "turi_id": turi_id if turi_id is not None else eski["turi_id"],
        "bolish_usul": usul if usul is not None else eski["bolish_usul"],
        "izoh": izoh if izoh is not None else eski["izoh"],
        "kim_uchun": (eski["kim_uchun"] if kim_uchun is _TEGMA else kim_uchun),
        "item_id": (eski["item_id"] if item_id is _TEGMA else item_id),
        "karta_id": (eski["karta_id"] if karta_id is _TEGMA else karta_id),
    }
    if yangi["summa"] <= 0:
        raise ValueError("Rasxod summasi musbat bo'lishi kerak")
    if karta_id is not _TEGMA or yangi["kim_toladi"] != eski["kim_toladi"]:
        # To'lovchi almashsa eski kartasi unga tegishli emas — naqdga.
        if (karta_id is _TEGMA and yangi["karta_id"] is not None
                and not db.q1("SELECT 1 FROM karta WHERE id=? AND odam_id=?",
                              yangi["karta_id"], yangi["kim_toladi"])):
            yangi["karta_id"] = None
        hamyon.tekshir_karta(db, yangi["karta_id"], yangi["kim_toladi"])

    # "Boshqa uchun" rasxod har doim 100% bitta odamga tegishli.
    if yangi["kim_uchun"] is not None:
        yangi["umumiymi"] = 1
        yangi["bolish_usul"] = money.USUL_ANIQ
        parametrlar = {yangi["kim_uchun"]: yangi["summa"]}

    # ulushlarni qayta hisoblash kerakmi?
    qayta = yangi["umumiymi"] == 1 and (
        yangi["summa"] != eski["summa"] or yangi["sana"] != eski["sana"]
        or yangi["umumiymi"] != eski["umumiymi"]
        or yangi["bolish_usul"] != eski["bolish_usul"]
        or yangi["kim_uchun"] != eski["kim_uchun"] or parametrlar is not None)

    with db.amal(f"Rasxod tahrirlandi: {yangi['nom'] or '—'}"):
        db.apply("rasxod", "UPDATE", yangi, rasxod_id)
        if yangi["umumiymi"] == 0:
            for r in db.q("SELECT id FROM ulush WHERE rasxod_id=?", rasxod_id):
                db.apply("ulush", "DELETE", qator_id=r["id"])
        elif qayta:
            for r in db.q("SELECT id FROM ulush WHERE rasxod_id=?", rasxod_id):
                db.apply("ulush", "DELETE", qator_id=r["id"])
            for u in splitting.hisobla(db, yangi["summa"], yangi["sana"],
                                       yangi["bolish_usul"], parametrlar):
                db.apply("ulush", "INSERT", {
                    "rasxod_id": rasxod_id, "odam_id": u.odam_id,
                    "summa": u.summa, "yaxlitlash": u.yaxlitlash})


def rasxod_ochir(db, rasxod_id: int) -> None:
    r = db.q1("SELECT nom, summa FROM rasxod WHERE id=?", rasxod_id)
    nom = (r["nom"] if r else "") or "—"
    with db.amal(f"Rasxod o'chirildi: {nom}"):
        db.apply("rasxod", "DELETE", qator_id=rasxod_id)


def rasxod_turi_qoy(db, rasxod_idlar: list[int], turi_id: int) -> int:
    """Bir yoki bir nechta rasxodning kategoriyasini almashtiradi —
    BITTA undo qadami. Pulga tegmaydi (summa, ulush o'zgarmaydi).

    Bog'langan mahsulot boshqa kategoriyaniki bo'lib qolsa `item_id`
    bo'shatiladi — `RasxodDialog` da kategoriya almashganda ham mahsulot
    tanlovi yangi kategoriyadan qayta olinadi. Qaytaradi: nechta rasxod
    o'zgardi (allaqachon shu kategoriyada bo'lgani sanalmaydi).
    """
    if turi_id is None or not db.q1(
            "SELECT 1 FROM turi WHERE id=? AND faol=1", turi_id):
        raise ValueError("Kategoriya tanlanmagan yoki endi yo'q.")
    nomi = db.skalyar("SELECT nom FROM turi WHERE id=?", turi_id,
                      birlamchi="")
    ozgarish = []
    for rid in dict.fromkeys(rasxod_idlar):
        r = db.q1("SELECT r.turi_id, r.item_id, i.turi_id item_turi"
                  " FROM rasxod r LEFT JOIN item i ON i.id=r.item_id"
                  " WHERE r.id=? AND r.ochirilgan=0", rid)
        if r is None or r["turi_id"] == turi_id:
            continue
        yangi = {"turi_id": turi_id}
        if r["item_id"] is not None and r["item_turi"] != turi_id:
            yangi["item_id"] = None
        ozgarish.append((rid, yangi))
    # Hech narsa o'zgarmasa amal OCHILMAYDI: bo'sh guruh redo yo'lini yopadi.
    if ozgarish:
        with db.amal(f"Kategoriya almashtirildi: {nomi}"):
            for rid, yangi in ozgarish:
                db.apply("rasxod", "UPDATE", yangi, rid)
    return len(ozgarish)


# ─────────────────────────────────────────────────────────────── qarz

def qarz_qosh(db, sana: str, kim_berdi: int, kimga: int, summa: int,
              sabab: str | None = None) -> int:
    summa = int(summa)
    if summa <= 0:
        raise ValueError("Qarz summasi musbat bo'lishi kerak")
    if kim_berdi == kimga:
        raise ValueError("O'ziga o'zi qarz bera olmaydi")
    a, b = _odam_nom(db, kim_berdi), _odam_nom(db, kimga)
    with db.amal(f"Qarz: {a} → {b} {money.fmt(summa)}"):
        return db.apply("qarz", "INSERT", {
            "sana": sana, "kim_berdi": kim_berdi, "kimga": kimga,
            "summa": summa, "sabab": sabab or None})


def qarz_ochir(db, qarz_id: int) -> None:
    with db.amal("Qarz o'chirildi"):
        db.apply("qarz", "DELETE", qator_id=qarz_id)


# ────────────────────────────────────────────────────────── tashqi qarz
# Uydan tashqaridagi odamdan olingan qarz. SHAXSIY — pul olganning
# qo'liga tushadi va qarz uniki. UMUMIY (2026-10-01) — pul ham, qarz ham
# hammaga ulushi bo'yicha (teng yoki rasxoddagidek sozlanadi); qaytarish
# ham har kimning o'z ulushidan. Uydagilar orasidagi qarzga (`sof`)
# ikkalasi ham tegmaydi.

def tashqi_qarz_qosh(db, sana: str, odam_id: int, kimdan: str, summa: int,
                     sabab: str | None = None, umumiy: bool = False,
                     qatnashchilar: list[int] | None = None,
                     usul: str = money.USUL_TENG,
                     parametrlar: dict[int, float] | None = None) -> int:
    """`umumiy=True` — pul va qarz hammaniki: `parametrlar`/`usul` bo'yicha
    (rasxoddagidek), berilmasa `qatnashchilar` ga (yoki shu kuni
    uydagilarga) teng bo'linadi."""
    summa = int(summa)
    kimdan = (kimdan or "").strip()
    if summa <= 0:
        raise ValueError("Qarz summasi musbat bo'lishi kerak")
    if not kimdan:
        raise ValueError("Kimdan olingani yozilmagan")
    nom = _odam_nom(db, odam_id)
    tur = "Umumiy tashqi qarz" if umumiy else "Tashqi qarz"
    with db.amal(f"{tur}: {nom} ← {kimdan} {money.fmt(summa)}"):
        qid = db.apply("tashqi_qarz", "INSERT", {
            "sana": sana, "odam_id": odam_id, "kimdan": kimdan,
            "summa": summa, "sabab": sabab or None})
        if umumiy:
            tashqi_umumiy_qoy(db, qid, qatnashchilar or
                              splitting.qatnashchilar(db, sana),
                              usul=usul, parametrlar=parametrlar)
        return qid


def _tashqi_ulushlar(db, qarz_id: int, tolov_id: int | None) -> list:
    shart = "tolov_id IS NULL" if tolov_id is None else "tolov_id=?"
    args = (qarz_id,) if tolov_id is None else (qarz_id, tolov_id)
    return db.q(f"SELECT id, odam_id, summa FROM tashqi_ulush"
                f" WHERE ochirilgan=0 AND qarz_id=? AND {shart}", *args)


def _tolov_ulushini_yoz(db, qarz_id: int, tolov_id: int, summa: int,
                        usul: str | None = None,
                        parametrlar: dict[int, float] | None = None) -> None:
    """To'lov kimdan qanchadan ayirilishi — yig'indisi aynan `summa`.
    Birlamchi: qarz ulushlari NISBATIDA (teng olingan bo'lsa — teng);
    `usul`/`parametrlar` berilsa — rasxoddagidek (`money.bol`)."""
    if parametrlar:
        bolinish = money.bol(int(summa), usul or money.USUL_TENG,
                             {int(k): float(v) for k, v in parametrlar.items()})
    else:
        vazn = {r["odam_id"]: float(r["summa"])
                for r in _tashqi_ulushlar(db, qarz_id, None)}
        if not vazn:
            return
        bolinish = money.bol(int(summa), money.USUL_OGIRLIK, vazn)
    for u in bolinish:
        db.apply("tashqi_ulush", "INSERT", {
            "qarz_id": qarz_id, "tolov_id": tolov_id,
            "odam_id": u.odam_id, "summa": u.summa})


def tashqi_umumiy_qoy(db, qarz_id: int, qatnashchilar: list[int] | None,
                      usul: str = money.USUL_TENG,
                      parametrlar: dict[int, float] | None = None) -> None:
    """Qarzni UMUMIY qiladi (`qatnashchilar` ga teng, yoki `parametrlar`/
    `usul` bo'yicha — rasxoddagidek) yoki `None` — shaxsiy.

    Oldingi ulushlar (qaytarilgan to'lovlarniki ham) o'chiriladi va
    qaytadan quriladi — bitta undo qadami. Allaqachon qaytarilgan
    to'lovlar ham yangi nisbatda bo'linadi.
    """
    q = db.q1("SELECT * FROM tashqi_qarz WHERE id=? AND ochirilgan=0", qarz_id)
    if not q:
        raise ValueError("Qarz topilmadi")
    if qatnashchilar is not None:
        qatnashchilar = [int(i) for i in dict.fromkeys(qatnashchilar)]
        if not qatnashchilar:
            raise ValueError("Kamida bitta odam tanlangan bo'lishi kerak.")
    tavsif = (f"Tashqi qarz umumiy qilindi: {q['kimdan']}" if qatnashchilar
              else f"Tashqi qarz shaxsiy qilindi: {q['kimdan']}")
    with db.amal(tavsif):
        for r in db.q("SELECT id FROM tashqi_ulush WHERE qarz_id=? AND ochirilgan=0",
                      qarz_id):
            db.apply("tashqi_ulush", "DELETE", qator_id=r["id"])
        db.apply("tashqi_qarz", "UPDATE", {"umumiy": 1 if qatnashchilar else 0},
                 qarz_id)
        if not qatnashchilar:
            return
        p = ({int(k): float(v) for k, v in parametrlar.items() if v}
             if parametrlar else {i: 1.0 for i in qatnashchilar})
        for u in money.bol(int(q["summa"]),
                           usul if parametrlar else money.USUL_TENG, p):
            db.apply("tashqi_ulush", "INSERT", {
                "qarz_id": qarz_id, "tolov_id": None,
                "odam_id": u.odam_id, "summa": u.summa})
        for t in db.q("SELECT id, summa FROM tashqi_tolov"
                      " WHERE tashqi_qarz_id=? AND ochirilgan=0 ORDER BY id",
                      qarz_id):
            _tolov_ulushini_yoz(db, qarz_id, t["id"], t["summa"])


def tashqi_qarz_ochir(db, qarz_id: int) -> None:
    """Qarz va uning HAMMA to'lovi — bitta undo qadami.

    To'lovlar qarzsiz osilib qolmasin: `v_balans` ularni baribir
    hisobga olmaydi, lekin ro'yxatda «nimaning to'lovi?» bo'lib turardi.
    """
    q = db.q1("SELECT kimdan FROM tashqi_qarz WHERE id=?", qarz_id)
    with db.amal(f"Tashqi qarz o'chirildi: {q['kimdan'] if q else '?'}"):
        for r in db.q("SELECT id FROM tashqi_ulush WHERE qarz_id=? AND ochirilgan=0",
                      qarz_id):
            db.apply("tashqi_ulush", "DELETE", qator_id=r["id"])
        for t in db.q("SELECT id FROM tashqi_tolov"
                      " WHERE tashqi_qarz_id=? AND ochirilgan=0", qarz_id):
            db.apply("tashqi_tolov", "DELETE", qator_id=t["id"])
        db.apply("tashqi_qarz", "DELETE", qator_id=qarz_id)


def tashqi_qoldiq(db, qarz_id: int) -> int:
    return db.skalyar(
        "SELECT q.summa - COALESCE((SELECT SUM(t.summa) FROM tashqi_tolov t"
        "  WHERE t.tashqi_qarz_id=q.id AND t.ochirilgan=0),0)"
        " FROM tashqi_qarz q WHERE q.id=? AND q.ochirilgan=0", qarz_id)


def tashqi_tolov_qosh(db, qarz_id: int, sana: str, summa: int,
                      izoh: str | None = None, usul: str | None = None,
                      parametrlar: dict[int, float] | None = None) -> int:
    """Tashqi qarzni qaytarish (to'liq yoki qisman). Shaxsiy qarzni olgan
    odam to'laydi; umumiysida har kimdan o'z ulushi ayiriladi — birlamchi
    qarz ulushlari nisbatida, `usul`/`parametrlar` bilan sozlanadi."""
    summa = int(summa)
    q = db.q1("SELECT kimdan, umumiy FROM tashqi_qarz WHERE id=? AND ochirilgan=0",
              qarz_id)
    if not q:
        raise ValueError("Qarz topilmadi")
    if summa <= 0:
        raise ValueError("To'lov summasi musbat bo'lishi kerak")
    qoldiq = tashqi_qoldiq(db, qarz_id)
    if summa > qoldiq:
        raise ValueError(
            f"Qarzning qoldig'i {money.fmt(qoldiq)} — undan ko'p "
            f"qaytarib bo'lmaydi")
    with db.amal(f"Tashqi qarz qaytarildi: {q['kimdan']} {money.fmt(summa)}"):
        tid = db.apply("tashqi_tolov", "INSERT", {
            "tashqi_qarz_id": qarz_id, "sana": sana, "summa": summa,
            "izoh": izoh or None})
        if q["umumiy"]:
            # Umumiy qarz: har kimning qo'lidagi puldan o'z ulushi.
            _tolov_ulushini_yoz(db, qarz_id, tid, summa, usul, parametrlar)
        return tid


def tashqi_qarz_yop(db, qarz_id: int, sana: str, izoh: str | None = None,
                    usul: str | None = None,
                    parametrlar: dict[int, float] | None = None) -> int:
    """Qarzni to'liq yopish — butun qoldiq bitta to'lov bo'lib yoziladi."""
    if not db.q1("SELECT 1 FROM tashqi_qarz WHERE id=? AND ochirilgan=0", qarz_id):
        raise ValueError("Qarz topilmadi")
    qoldiq = tashqi_qoldiq(db, qarz_id)
    if qoldiq <= 0:
        raise ValueError("Bu qarz allaqachon yopilgan")
    return tashqi_tolov_qosh(db, qarz_id, sana, qoldiq, izoh or "Qarz yopildi",
                             usul, parametrlar)


def tashqi_tolov_ochir(db, tolov_id: int) -> None:
    with db.amal("Tashqi qarz to'lovi o'chirildi"):
        for r in db.q("SELECT id FROM tashqi_ulush WHERE tolov_id=? AND ochirilgan=0",
                      tolov_id):
            db.apply("tashqi_ulush", "DELETE", qator_id=r["id"])
        db.apply("tashqi_tolov", "DELETE", qator_id=tolov_id)


# ────────────────────────────────────────────────────────── hisob-kitob

def hisob_kitob_qosh(db, sana: str, kim_toladi: int, kimga: int, summa: int,
                     izoh: str | None = None) -> int:
    """Qarzni yopish uchun haqiqiy to'lov."""
    summa = int(summa)
    if summa <= 0:
        raise ValueError("To'lov summasi musbat bo'lishi kerak")
    if kim_toladi == kimga:
        raise ValueError("O'ziga o'zi to'lay olmaydi")
    a, b = _odam_nom(db, kim_toladi), _odam_nom(db, kimga)
    with db.amal(f"Hisob-kitob: {a} → {b} {money.fmt(summa)}"):
        return db.apply("hisob_kitob", "INSERT", {
            "sana": sana, "kim_toladi": kim_toladi, "kimga": kimga,
            "summa": summa, "izoh": izoh or None})


def hisob_kitob_ochir(db, hk_id: int) -> None:
    with db.amal("Hisob-kitob o'chirildi"):
        db.apply("hisob_kitob", "DELETE", qator_id=hk_id)


# ────────────────────────────────────────────────────────────── odamlar

def odam_qosh(db, nom: str, rang: str = "#6b7fd7") -> int:
    nom = nom.strip()
    if not nom:
        raise ValueError("Ism bo'sh bo'lmasin")
    if db.q1("SELECT 1 FROM odam WHERE nom=? AND faol=1", nom):
        raise ValueError(f"{nom} allaqachon bor")
    n = db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM odam")
    with db.amal(f"Odam qo'shildi: {nom}"):
        return db.apply("odam", "INSERT", {"nom": nom, "rang": rang, "tartib": n})


def _odam_nom(db, odam_id: int) -> str:
    r = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    return r["nom"] if r else "?"


def odam_ochir(db, odam_id: int) -> None:
    """Odamni ro'yxatdan olib tashlaydi (nofaol qiladi).

    Yozuvlari HECH QAYERGA yo'qolmaydi — o'tgan rasxodlar, ulushlar va
    qarzlar joyida qoladi, aks holda kitob teng bo'lmay qolardi. Odam
    faqat yangi rasxodlarda ko'rinmaydi.
    """
    o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    if not o:
        raise ValueError("Odam topilmadi")
    if db.skalyar("SELECT COUNT(*) FROM odam WHERE faol=1") <= 1:
        raise ValueError("Oxirgi odamni o'chirib bo'lmaydi")

    b = db.q1("SELECT sof FROM v_balans WHERE id=?", odam_id)
    if b and b["sof"] != 0:
        yon = "qarzdor" if b["sof"] < 0 else "unga qarzdorlar"
        raise ValueError(
            f"{o['nom']} hali {money.fmt(abs(b['sof']))} so'mga {yon}.\n\n"
            f"Avval hisob-kitob qiling — qarz ochiq turganda odamni "
            f"ro'yxatdan olib tashlash hisobni chalkashtiradi.")
    b = db.q1("SELECT tashqi_qoldiq FROM v_balans WHERE id=?", odam_id)
    if b and b["tashqi_qoldiq"]:
        raise ValueError(
            f"{o['nom']} tashqaridan olgan {money.fmt(b['tashqi_qoldiq'])} "
            f"so'm qarzni hali qaytarmagan.")

    with db.amal(f"Odam ro'yxatdan olindi: {o['nom']}"):
        db.apply("odam", "UPDATE", {"faol": 0}, odam_id)


def odam_qaytar(db, odam_id: int) -> None:
    o = db.q1("SELECT nom FROM odam WHERE id=?", odam_id)
    with db.amal(f"Odam qaytarildi: {o['nom'] if o else '?'}"):
        db.apply("odam", "UPDATE", {"faol": 1}, odam_id)


def odam_nomi_ozgartir(db, odam_id: int, yangi: str) -> None:
    yangi = yangi.strip()
    if not yangi:
        raise ValueError("Ism bo'sh bo'lmasin")
    if db.q1("SELECT 1 FROM odam WHERE nom=? AND id<>?", yangi, odam_id):
        raise ValueError(f"{yangi} allaqachon bor")
    with db.amal(f"Ism o'zgartirildi: {yangi}"):
        db.apply("odam", "UPDATE", {"nom": yangi}, odam_id)
