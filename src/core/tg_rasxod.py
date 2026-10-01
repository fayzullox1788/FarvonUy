"""Telegram bot orqali rasxod kiritish.

Bu fayl FAQAT suhbat: qaysi savol, qaysi tugma. Rasxodning o'zi —
`core/rasxod_kirit.py` dagi `Qoralama` va `saqla()`, dasturdagi oyna
ham aynan shularni chaqiradi. Shuning uchun bu yerda tekshiruv,
narx/nom to'ldirish yoki ulush hisoblash YOZILMAYDI — kerak bo'lsa
`rasxod_kirit` ga qo'shing, ikkala platformaga birdan ta'sir qiladi.

Tartib dasturdagi oyna bilan bir xil:
    kategoriya (daraxt: Bozorlik › Mevalar) → mahsulot → sabab → summa
    → kim to'ladi → umumiy / shaxsiy / boshqa uchun → kimlarga bo'linadi
    → sana va tasdiq → saqlash.

Faqat uy a'zosi (odam.telegram), faqat SHAXSIY chatda. Suhbat holati
`sozlama` da (`tg_rx:<chat>`) — xabarchi har ishga tushganda qayta
o'qiydi. Bu texnik holat, foydalanuvchi ma'lumoti emas (`tg_offset`
kabi) — undo ga tushmaydi. Rasxod esa oddiy `db.apply()` bilan yoziladi.

Bo'lish usuli botda faqat «teng» (kimlar qatnashishi tanlanadi). Foiz,
og'irlik va aniq summa — dasturdagi oynada: telefonda har odamga son
yozdirish noqulay, mantiq esa baribir o'sha `rasxod_kirit`.
"""
from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta

import money
from core import mahsulot as mh
from core import plan
from core import rasxod_kirit as rk

BOSHLASH_TUGMA = "➕ Rasxod"
BUYRUQLAR = {"/rasxod", "rasxod", BOSHLASH_TUGMA.casefold()}
BEKOR_BUYRUQ = {"/bekor", "bekor"}
ESKIRISH_SOAT = 6          # shundan eski yarim qolgan suhbat hisobga olinmaydi
QATORDA = 2                # tugmalar bir qatorda nechta


def _xb():
    # xabar.py bu faylni import qiladi — aylanma importdan qochish uchun
    # kech olinadi (testlar `xb._sorov` ni almashtiradi, shu ham ishlaydi).
    from core import xabar
    return xabar


# ═══════════════════════════════════════════════════════════ holat

def _kalit(chat_id) -> str:
    return f"tg_rx:{chat_id}"


def holat_ol(db, chat_id) -> dict | None:
    matn = db.sozlama(_kalit(chat_id), "")
    if not matn:
        return None
    try:
        h = json.loads(matn)
        vaqt = datetime.fromisoformat(h["vaqt"])
    except Exception:
        return None
    if datetime.now() - vaqt > timedelta(hours=ESKIRISH_SOAT):
        return None
    h["q"] = rk.Qoralama.lugatdan(h["q"])
    return h


def _holat_saqla(db, chat_id, h: dict) -> None:
    d = dict(h, q=h["q"].lugat(), vaqt=datetime.now().isoformat())
    db.sozlama_qoy(_kalit(chat_id), json.dumps(d, ensure_ascii=False))


def _holat_tozala(db, chat_id) -> None:
    db.sozlama_qoy(_kalit(chat_id), "")


# ═══════════════════════════════════════════════════════════ ko'rinish

def _e(x) -> str:
    # quote=False: «so'm» dagi apostrof `&#x27;` bo'lib ketmasin.
    return html.escape(str(x), quote=False)


def _odamlar(db) -> list:
    return db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id")


def _nom(db, odam_id) -> str:
    return db.skalyar("SELECT nom FROM odam WHERE id=?", odam_id, birlamchi="?")


def _qatorlab(tugmalar: list, n: int = QATORDA) -> list:
    return [tugmalar[i:i + n] for i in range(0, len(tugmalar), n)]


def _xulosa(db, q: rk.Qoralama) -> list[str]:
    """Hozircha tanlanganlar — har ekranning tepasida."""
    s = []
    if q.turi_id:
        s.append(f"🗂 {_e(mh.yol_nomi(db, q.turi_id))}")
    if q.item_id:
        it = db.q1("SELECT nom FROM item WHERE id=?", q.item_id)
        s.append(f"📦 {_e(it['nom'] if it else '?')}")
    if q.nom:
        s.append(f"✏️ {_e(q.nom)}")
    if q.summa:
        s.append(f"💰 {_e(money.fmt_som(q.summa))}")
    return s


def _ulush_matn(db, q: rk.Qoralama) -> str:
    try:
        u = rk.ulushlar(db, q)
    except ValueError:
        return ""
    return "\n".join(f"   • {_e(_nom(db, x.odam_id))}: {_e(money.fmt(x.summa))}"
                     for x in u)


def _tur_matn(db, q) -> str:
    if q.tur == rk.SHAXSIY:
        return "Shaxsiy"
    if q.tur == rk.UCHUN:
        return f"{_e(_nom(db, q.kim_uchun))} uchun"
    return "Umumiy"


def ekran(db, h: dict) -> tuple[str, list]:
    """(matn, tugmalar) — joriy qadam uchun. Tugma: (yozuv, callback_data)."""
    q, qadam = h["q"], h["qadam"]
    bosh = ["<b>➕ Yangi rasxod</b>"] + _xulosa(db, q)
    bekor = [("✖ Bekor", "rx:x")]
    tug: list = []

    if qadam == "kat":
        ota = h.get("ota")
        tugunlar = mh.daraxt(db)
        if ota is not None:
            tugun = _tugun_top(tugunlar, ota)
            tugunlar = tugun["bolalar"] if tugun else []
            savol = f"«{_e(mh.yol_nomi(db, ota))}» ichidan tanlang:"
        else:
            savol = "Kategoriyani tanlang:"
        k = []
        for t in tugunlar:
            belgi = "📂 " if t["bolalar"] else ""
            k.append((f"{belgi}{t['belgi']} {t['nom']}".strip(), f"rx:k:{t['id']}"))
        tug = _qatorlab(k)
        if ota is not None:
            tug.insert(0, [(f"✔ «{mh.yol_nomi(db, ota).split(' › ')[-1]}» o'zi",
                            f"rx:kt:{ota}")])
            tug.append([("‹ Orqaga", "rx:ko")] + bekor)
        else:
            tug.append(bekor)
        return "\n".join(bosh + ["", savol]), tug

    if qadam == "mah":
        k = []
        for it in plan.turi_itemlari(db, q.turi_id):
            yoz = it["nom"]
            if "ichkida" in it.keys() and it["ichkida"]:
                yoz = f"{it['turi_nom']} › {yoz}"
            if it["narx"]:
                yoz += f" · {money.fmt(it['narx'])}"
            k.append((yoz, f"rx:m:{it['id']}"))
        tug = _qatorlab(k, 1) + [[("Mahsulotsiz ›", "rx:m:0")],
                                 [("‹ Orqaga", "rx:mo")] + bekor]
        return "\n".join(bosh + ["", "Mahsulotni tanlang:"]), tug

    if qadam == "nom":
        if q.nom:
            tug.append([(f"✔ «{q.nom[:40]}»", "rx:n")])
        tug.append(bekor)
        return "\n".join(bosh + ["", "✏️ Sabab — nima uchun? <i>Yozib yuboring.</i>"]), tug

    if qadam == "summa":
        if q.summa:
            tug.append([(f"✔ {money.fmt(q.summa)}", "rx:s")])
        tug.append(bekor)
        return "\n".join(bosh + ["", "💰 Summa (so'm)? <i>Yozib yuboring, "
                                     "masalan 25000.</i>"]), tug

    if qadam == "kim":
        k = [(("✔ " if o["id"] == q.kim_toladi else "") + o["nom"],
              f"rx:p:{o['id']}") for o in _odamlar(db)]
        tug = _qatorlab(k) + [bekor]
        return "\n".join(bosh + ["", "👤 Kim to'ladi?"]), tug

    if qadam == "tur":
        tug = [[("Umumiy", "rx:t:u"), ("Shaxsiy", "rx:t:s")],
               [("Boshqa uchun", "rx:t:b")], bekor]
        return "\n".join(bosh + [f"👤 {_e(_nom(db, q.kim_toladi))} to'ladi",
                                 "", "Qanday rasxod?"]), tug

    if qadam == "uchun":
        k = [(o["nom"], f"rx:u:{o['id']}") for o in _odamlar(db)
             if o["id"] != q.kim_toladi]
        tug = _qatorlab(k) + [bekor]
        return "\n".join(bosh + ["", "Kim uchun olindi? <i>(u qarzdor bo'ladi, "
                                     "kirim emas)</i>"]), tug

    if qadam == "bol":
        tanlangan = set(rk.qatnashchilar(db, q))
        k = [(("✅ " if o["id"] in tanlangan else "⬜ ") + o["nom"],
              f"rx:q:{o['id']}") for o in _odamlar(db)]
        tug = _qatorlab(k) + [[("Davom ›", "rx:qd")], bekor]
        return "\n".join(bosh + ["", "Kimlarga teng bo'linadi?",
                                 _ulush_matn(db, q)]), tug

    if qadam == "tasdiq":
        bugun = h["bugun"]
        kecha = (date.fromisoformat(bugun) - timedelta(days=1)).isoformat()
        satr = bosh + [f"👤 {_e(_nom(db, q.kim_toladi))} to'ladi · {_tur_matn(db, q)}"]
        if q.tur == rk.UMUMIY:
            satr.append(_ulush_matn(db, q))
        satr.append(f"📅 {date.fromisoformat(q.sana).strftime('%d.%m.%Y')}")
        if h.get("xato"):
            satr += ["", f"⚠️ {_e(h['xato'])}"]
        tug = [[(("✔ " if q.sana == bugun else "") + "Bugun", "rx:d:0"),
                (("✔ " if q.sana == kecha else "") + "Kecha", "rx:d:1")],
               [("💾 Saqlash", "rx:ok")],
               [("‹ Orqaga", "rx:to")] + bekor]
        return "\n".join(satr), tug

    return "Noma'lum qadam.", [bekor]


def _tugun_top(tugunlar, tid):
    for t in tugunlar:
        if t["id"] == tid:
            return t
        topildi = _tugun_top(t["bolalar"], tid)
        if topildi:
            return topildi
    return None


# ═══════════════════════════════════════════════════════════ yuborish

def _klav(tug) -> str:
    return _xb()._klaviatura_json(tug)


def _chiz(db, token, chat_id, h, yangi: bool = False) -> None:
    """Joriy ekranni ko'rsatadi: eski xabarni tahrirlaydi yoki yangisini yuboradi.

    `yangi=True` — foydalanuvchi matn yozgan: savol uning xabaridan
    PASTDA qolmasin, eski xabar o'chirilib, yangisi yuboriladi.
    """
    xb = _xb()
    matn, tug = ekran(db, h)
    if h.get("xabar") and not yangi:
        try:
            xb._sorov(token, "editMessageText", chat_id=chat_id,
                      message_id=h["xabar"], text=matn, parse_mode="HTML",
                      reply_markup=_klav(tug))
            return
        except RuntimeError as e:
            if "not modified" in str(e):
                return
    if h.get("xabar"):
        try:
            xb._sorov(token, "deleteMessage", chat_id=chat_id,
                      message_id=h["xabar"])
        except Exception:
            pass
    r = xb._sorov(token, "sendMessage", chat_id=chat_id, text=matn,
                  parse_mode="HTML", reply_markup=_klav(tug)) or {}
    h["xabar"] = r.get("message_id")


# ═══════════════════════════════════════════════════════════ qadamlar

def _keyingi_kat_dan(db, h) -> None:
    """Kategoriya tanlandi → mahsulot bo'lsa mahsulot, bo'lmasa sabab."""
    h["qadam"] = "mah" if plan.turi_itemlari(db, h["q"].turi_id) else "nom"


def _ota(db, tid):
    return db.skalyar("SELECT ota_id FROM turi WHERE id=?", tid, birlamchi=None)


def boshlash(db, token, chat_id, odam_id, bugun: str | None = None) -> None:
    bugun = bugun or date.today().isoformat()
    h = {"odam": odam_id, "qadam": "kat", "ota": None, "xabar": None,
         "bugun": bugun,
         "q": rk.Qoralama(sana=bugun, kim_toladi=odam_id, manba="telegram")}
    _chiz(db, token, chat_id, h, yangi=True)
    _holat_saqla(db, chat_id, h)


def _summa_oqi(matn: str) -> int | None:
    """«25000», «25 000», «25.000» → 25000. Kasr va harf — rad."""
    t = matn.strip().replace(" ", "").replace(" ", "").replace(".", "")
    t = t.replace(",", "").lower().removesuffix("so'm").removesuffix("som")
    return int(t) if t.isdigit() and int(t) > 0 else None


def matn_keldi(db, token, msg: dict, odam_id: int) -> str | None:
    """Shaxsiy chatdagi matn. Rasxodga tegishli bo'lsa — ishlaydi."""
    xb = _xb()
    chat_id = msg["chat"]["id"]
    matn = (msg.get("text") or "").strip()
    if not matn:
        return None
    kichik = matn.casefold()

    # /start va menyu — `tg_menyu.py` da (u bu funksiyadan OLDIN chaqiriladi).
    if kichik in BUYRUQLAR:
        boshlash(db, token, chat_id, odam_id)
        return "rx: boshlandi"

    h = holat_ol(db, chat_id)
    if h is None:
        return None
    if kichik in BEKOR_BUYRUQ:
        _holat_tozala(db, chat_id)
        xb._sorov(token, "sendMessage", chat_id=chat_id, text="✖ Bekor qilindi.")
        return "rx: bekor"

    q = h["q"]
    if h["qadam"] == "nom":
        q.nom = matn[:200]
        h["qadam"] = "summa"
    elif h["qadam"] == "summa":
        s = _summa_oqi(matn)
        if s is None:
            xb._sorov(token, "sendMessage", chat_id=chat_id,
                      text="Summani raqam bilan yozing, masalan: 25000")
            return "rx: summa xato"
        q.summa = s
        h["qadam"] = "kim"
    else:
        # Tugma kutilayotganda matn yozildi — savolni pastga qayta chiqaramiz.
        pass
    _chiz(db, token, chat_id, h, yangi=True)
    _holat_saqla(db, chat_id, h)
    return f"rx: {h['qadam']}"


def tugma_bosildi(db, token, cb: dict, odam_id: int) -> str | None:
    """«rx:» bilan boshlanadigan tugma. Boshqasi — None (xabar.py ishlaydi)."""
    data = cb.get("data") or ""
    if not data.startswith("rx:"):
        return None
    xb = _xb()
    msg = cb.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    qism = data.split(":")[1:]
    amal, arg = qism[0], (qism[1] if len(qism) > 1 else None)

    def javob(matn=None):
        try:
            xb._sorov(token, "answerCallbackQuery", callback_query_id=cb.get("id"),
                      **({"text": matn} if matn else {}))
        except Exception:
            pass

    # Saqlangan rasxodni bekor qilish — suhbat tugagandan keyin ham ishlaydi.
    if amal == "del" and arg and arg.isdigit():
        from core import entries
        r = db.q1("SELECT nom FROM rasxod WHERE id=? AND ochirilgan=0", int(arg))
        if not r:
            javob("Allaqachon bekor qilingan")
            return "rx: del (yo'q)"
        entries.rasxod_ochir(db, int(arg))
        xb._sorov(token, "editMessageText", chat_id=chat_id,
                  message_id=msg.get("message_id"),
                  text=f"↶ Bekor qilindi: {_e(r['nom'])}", parse_mode="HTML")
        javob("Bekor qilindi")
        return f"rx: del #{arg}"

    h = holat_ol(db, chat_id)
    if h is None or msg.get("message_id") != h.get("xabar"):
        javob("Bu eski xabar — «➕ Rasxod» ni qayta bosing")
        return "rx: eski"
    q = h["q"]

    if amal == "x":
        _holat_tozala(db, chat_id)
        xb._sorov(token, "editMessageText", chat_id=chat_id, message_id=h["xabar"],
                  text="✖ Bekor qilindi.")
        javob()
        return "rx: bekor"

    if amal == "k" and arg:
        tid = int(arg)
        if db.skalyar("SELECT COUNT(*) FROM turi WHERE ota_id=? AND faol=1", tid):
            h["ota"] = tid                      # ichiga kiramiz
        else:
            q.turi_id = tid
            _keyingi_kat_dan(db, h)
    elif amal == "kt" and arg:
        q.turi_id = int(arg)
        _keyingi_kat_dan(db, h)
    elif amal == "ko":
        h["ota"] = _ota(db, h["ota"]) if h.get("ota") is not None else None
    elif amal == "mo":
        # Orqaga — tanlangan kategoriyaning qo'shnilari ko'rinsin.
        h["ota"] = _ota(db, q.turi_id) if q.turi_id else None
        q.turi_id, q.item_id = None, None
        h["qadam"] = "kat"
    elif amal == "m" and arg is not None:
        rk.mahsulot_tanla(db, q, int(arg))      # nom va narx — umumiy qoida
        h["qadam"] = "nom"
        if q.item_id:
            _rasmini_yubor(db, token, chat_id, q.item_id)
            _chiz(db, token, chat_id, h, yangi=True)
            _holat_saqla(db, chat_id, h)
            javob()
            return "rx: nom"
    elif amal == "n" and q.nom:
        h["qadam"] = "summa"
    elif amal == "s" and q.summa:
        h["qadam"] = "kim"
    elif amal == "p" and arg:
        q.kim_toladi = int(arg)
        if q.kim_uchun == q.kim_toladi:
            q.kim_uchun = None
        h["qadam"] = "tur"
    elif amal == "t" and arg in ("u", "s", "b"):
        q.tur = {"u": rk.UMUMIY, "s": rk.SHAXSIY, "b": rk.UCHUN}[arg]
        if q.tur == rk.UMUMIY:
            if q.parametrlar is None:
                q.parametrlar = {i: 1.0 for i in rk.qatnashchilar(db, q)}
            h["qadam"] = "bol"
        elif q.tur == rk.UCHUN:
            h["qadam"] = "uchun"
        else:
            h["qadam"] = "tasdiq"
    elif amal == "u" and arg:
        q.kim_uchun = int(arg)
        h["qadam"] = "tasdiq"
    elif amal == "q" and arg:
        oid = int(arg)
        p = dict(q.parametrlar or {})
        if oid in p:
            p.pop(oid)
        else:
            p[oid] = 1.0
        q.parametrlar = p
        h["qolda"] = True           # sana almashsa ham tanlov saqlansin
    elif amal == "qd":
        h["qadam"] = "tasdiq"
    elif amal == "d" and arg in ("0", "1"):
        kun = date.fromisoformat(h["bugun"]) - timedelta(days=int(arg))
        q.sana = kun.isoformat()
        # Uyda kim borligi sanaga bog'liq — qayta olinadi, lekin faqat
        # foydalanuvchi kimlarni o'zi tanlamagan bo'lsa: aks holda olib
        # tashlangan odam sana almashgach jimgina qaytib qolardi.
        if (q.tur == rk.UMUMIY and q.parametrlar is not None
                and not h.get("qolda")):
            q.parametrlar = {i: 1.0 for i in
                             rk.qatnashchilar(db, rk.Qoralama(sana=q.sana))}
    elif amal == "to":
        h["qadam"] = {rk.UMUMIY: "bol", rk.UCHUN: "uchun"}.get(q.tur, "tur")
    elif amal == "ok":
        return _saqla(db, token, chat_id, h, javob)
    else:
        javob()
        return "rx: noma'lum"

    h.pop("xato", None)
    _chiz(db, token, chat_id, h)
    _holat_saqla(db, chat_id, h)
    javob()
    return f"rx: {h['qadam']}"


def _saqla(db, token, chat_id, h, javob) -> str:
    xb = _xb()
    q = h["q"]
    try:
        rid = rk.saqla(db, q)                   # dasturdagi oyna bilan bitta
    except Exception as e:
        h["xato"] = str(e)
        _chiz(db, token, chat_id, h)
        _holat_saqla(db, chat_id, h)
        javob("Saqlanmadi")
        return f"rx: xato ({e})"
    _holat_tozala(db, chat_id)
    matn = "\n".join(["<b>✔ Rasxod saqlandi</b>"] + _xulosa(db, q) + [
        f"👤 {_e(_nom(db, q.kim_toladi))} to'ladi · {_tur_matn(db, q)}",
        f"📅 {date.fromisoformat(q.sana).strftime('%d.%m.%Y')}",
        "", "<i>Dasturda darhol ko'rinadi.</i>"])
    xb._sorov(token, "editMessageText", chat_id=chat_id, message_id=h["xabar"],
              text=matn, parse_mode="HTML",
              reply_markup=_klav([[("↶ Bekor qilish", f"rx:del:{rid}")]]))
    javob("Saqlandi")
    return f"rx: saqlandi #{rid}"


def _rasmini_yubor(db, token, chat_id, item_id) -> None:
    """Mahsulot tanlanganda — uning rasmi va saqlangan ma'lumotlari."""
    it = db.q1("SELECT * FROM item WHERE id=?", item_id)
    yol = mh.rasm_yoli(it["rasm"]) if it else None
    if not yol:
        return
    izoh = "\n".join(x for x in (f"<b>{_e(it['nom'])}</b>",
                                 _e(mh.yol_nomi(db, it["turi_id"])),
                                 _e(mh.tavsif(it)), _e(it["izoh"] or "")) if x)
    try:
        _xb()._rasm_yubor(token, chat_id, yol, izoh)
    except Exception:
        pass                    # rasm yetmasa ham rasxod davom etadi
