"""Telegram botning menyusi: «Moliya» va «Vazifalar».

Menyu — chat ostidagi doimiy tugmalar (reply keyboard): telefonda
bosish oson va har doim ko'rinib turadi. Bosilgan tugma oddiy matn
bo'lib keladi, shuning uchun bu yerda matn → javob.

Bu fayl HECH NARSA hisoblamaydi. Pul — `ledger` (`v_balans`, juftlik
qarzlari, tashqi qarz), vazifalar — `vazifa`, rasxod yozish —
`tg_rasxod` → `rasxod_kirit`. Ya'ni bot dasturdagi varaqlar bilan
aynan bir xil sonni ko'rsatadi: ikkalasi ham bitta bazadan, bitta
funksiyadan o'qiydi.

Ko'rsatiladigan hamma narsa — SO'RAGAN odamniki (`odam_id`): «Qancha
pulim bor» Fayzulloxonga uning pulini, Otabekka Otabeknikini aytadi.

«Qancha qarzim bor» va har odam bilan alohida qarz («Otabekdan qarz»)
2026-09-25 da foydalanuvchi so'rovi bilan olib tashlangan — keraksiz
deb topildi. Kim kimga qarzdorligi «Aylanma qarz» da ko'rinadi.
"""
from __future__ import annotations

import html
import json
from datetime import date

import money
from core import ledger
from core import vazifa as vz

MOLIYA = "💰 Moliya"
VAZIFALAR = "📋 Vazifalar"
ASOSIY = "‹ Asosiy menyu"

PULIM = "💵 Qancha pulim bor"
AYLANMA = "🔄 Aylanma qarz"
TASHQI = "🌐 Tashqaridan qarz"
RASXOD = "➕ Rasxod yozish"

UY_ISH = "🏠 Uy ishlari"          # uyning umumiy ishidan menga biriktirilgani
SHAXSIY = "🔒 Shaxsiy ishlar"
DARS = "🎓 Universitet"           # bugungi darslar (EduPage jadvali)
# Eski tugma matnlari — chatda eski klaviatura qolgan bo'lsa ham ishlasin.
_ESKI = {"🏠 Bugun uyda qanday vazifalarim bor": UY_ISH,
         "🎓 Bugun qanday darslarim bor": DARS,
         "🔒 Bugun shaxsiy qanday ishlarim bor": SHAXSIY}

BOSHLASH = {"/start", "/menu", "/menyu", "menyu"}


def _e(x) -> str:
    return html.escape(str(x), quote=False)


def _som(x) -> str:
    return _e(money.fmt_som(x))


def _xb():
    from core import xabar
    return xabar


def _klaviatura(qatorlar: list[list[str]]) -> str:
    return json.dumps({"keyboard": [[{"text": t} for t in q] for q in qatorlar],
                       "resize_keyboard": True, "is_persistent": True},
                      ensure_ascii=False)


# ═══════════════════════════════════════════════════════════ menyular

def asosiy_menyu() -> list[list[str]]:
    return [[MOLIYA, VAZIFALAR]]


def moliya_menyu() -> list[list[str]]:
    return [[PULIM, AYLANMA], [TASHQI], [RASXOD], [ASOSIY]]


def vazifa_menyu() -> list[list[str]]:
    return [[UY_ISH, SHAXSIY], [DARS], [ASOSIY]]


# ═══════════════════════════════════════════════════════════ moliya

def pulim(db, odam_id) -> str:
    b = ledger.balans(db, odam_id)
    if not b:
        return "Ma'lumot topilmadi."
    s = [f"<b>💵 {_e(b['nom'])}, sizning pulingiz</b>", "",
         f"Qo'lingizdagi pul: <b>{_som(b['naqd'])}</b>"]
    if b["sof"] > 0:
        s.append(f"Sizga qarzdorlar: +{_som(b['sof'])}")
    elif b["sof"] < 0:
        s.append(f"Siz qarzdorsiz: −{_som(-b['sof'])}")
    s.append(f"Hisob-kitobdan keyin qoladi: <b>{_som(b['adolat'])}</b>")
    if b["tashqi_qoldiq"]:
        s += ["", f"⚠️ Shundan {_som(b['tashqi_qoldiq'])} — tashqaridan "
                  f"olingan qarz, qaytarilishi kerak."]
    return "\n".join(s)


def aylanma(db) -> str:
    juftlar = ledger.juft_qarzlar(db)
    if not juftlar:
        return "<b>🔄 Aylanma qarz</b>\n\n✔ Hech kim hech kimga qarzdor emas."
    s = ["<b>🔄 Aylanma qarz — kim kimga qarzdor</b>", ""]
    s += [f"• {_e(j.qarzdor_nom)} → {_e(j.kreditor_nom)}: <b>{_som(j.summa)}</b>"
          for j in juftlar]
    return "\n".join(s)


def _ulush_qoldiq(db, qarz_id, odam_id) -> int:
    """Umumiy qarzdan shu odamning HALI qaytarilmagan ulushi."""
    return db.skalyar(
        "SELECT COALESCE(SUM(CASE WHEN u.tolov_id IS NULL THEN u.summa"
        "                         ELSE -u.summa END),0)"
        " FROM tashqi_ulush u LEFT JOIN tashqi_tolov t ON t.id=u.tolov_id"
        " WHERE u.qarz_id=? AND u.odam_id=? AND u.ochirilgan=0"
        "   AND (u.tolov_id IS NULL OR t.ochirilgan=0)", qarz_id, odam_id)


def tashqi(db, odam_id) -> str:
    """O'zi olgan qarzlar + UMUMIY qarzlardagi o'z ulushi.

    Umumiy qarzni boshqa odam olgan bo'lsa ham, uning ulushi shu odamniki —
    shuning uchun u ham ko'radi («Fayzulloxon olgan, sizning ulushingiz»).
    """
    qarzlar = []
    for r in ledger.tashqi_qarzlar(db, faqat_ochiq=True):
        ulush = _ulush_qoldiq(db, r["id"], odam_id) if r["umumiy"] else None
        if r["odam_id"] == odam_id or ulush:
            qarzlar.append((r, ulush))
    if not qarzlar:
        return "<b>🌐 Tashqaridan qarz</b>\n\n✔ Tashqaridan olingan qarzingiz yo'q."
    s = ["<b>🌐 Tashqaridan olingan qarzlar</b>", ""]
    jami = 0
    for r, ulush in qarzlar:
        sana = date.fromisoformat(r["sana"]).strftime("%d.%m.%Y")
        s.append(f"• <b>{_e(r['kimdan'])}</b> — {_som(r['qoldiq'])}"
                 + ("  · umumiy" if r["umumiy"] else ""))
        tafsil = f"   {sana}, {_e(r['odam_nom'])} olgan {_som(r['summa'])}"
        if r["qaytgan"]:
            tafsil += f", qaytarilgan {_som(r['qaytgan'])}"
        s.append(tafsil)
        if r["umumiy"]:
            s.append(f"   Sizning ulushingiz: <b>{_som(ulush or 0)}</b>")
            jami += ulush or 0
        else:
            jami += r["qoldiq"]
        if r["sabab"]:
            s.append(f"   {_e(r['sabab'])}")
    s += ["", f"Sizga tushadigani: <b>{_som(jami)}</b>"]
    return "\n".join(s)


# ═══════════════════════════════════════════════════════════ vazifalar
#
# Uch xil ish ALOHIDA: dars (EduPage jadvali, `manba` = «dars:…»),
# shaxsiy ish (`vazifa_turi.shaxsiy=1`) va uy vazifasi (qolgani).
# Dars turi ham `shaxsiy=1` (guruhga chiqmasligi uchun) — shuning uchun
# darsni avval `manba` bo'yicha ajratamiz, aks holda u shaxsiy ishlar
# ro'yxatiga ham tushib qolardi.

def _darsmi(v) -> bool:
    return str(v["manba"] or "").startswith("dars:")


def bugungi(db, odam_id, qism: str, bugun=None) -> list:
    bugun = bugun or date.today()
    yopiq = vz.shaxsiy_nomlari(db)
    natija = []
    for v in vz.kun(db, bugun, odam_id):
        if _darsmi(v):
            tur = "dars"
        elif v["nom"] in yopiq:
            tur = "shaxsiy"
        else:
            tur = "uy"
        if tur == qism:
            natija.append(v)
    return natija


def _vazifa_matn(royxat: list, sarlavha: str, bosh: str) -> str:
    if not royxat:
        return f"<b>{sarlavha}</b>\n\n{bosh}"
    s = [f"<b>{sarlavha}</b>", ""]
    for v in royxat:
        belgi = ("✅" if v["holat"] == vz.BAJARILDI
                 else "🕌" if v["holat"] == vz.QAZO else "⏳")
        vaqt = f"{v['vaqt']}  " if v["vaqt"] else ""
        s.append(f"{belgi} {_e(vaqt)}{_e(v['nom'])}")
        if v["izoh"]:
            s.append(f"      {_e(v['izoh'])}")
    ochiq = sum(1 for v in royxat if not vz.yopiqmi(v))
    s += ["", f"{len(royxat)} ta, {ochiq} tasi hali bajarilmagan." if ochiq
          else f"{len(royxat)} ta — hammasi bajarilgan ✔"]
    return "\n".join(s)


def uy_vazifalari(db, odam_id, bugun=None) -> str:
    return _vazifa_matn(bugungi(db, odam_id, "uy", bugun),
                        "🏠 Uy ishlari — bugun sizga biriktirilgan",
                        "✔ Bugun sizga uy ishi biriktirilmagan.")


def darslar(db, odam_id, bugun=None) -> str:
    return _vazifa_matn(bugungi(db, odam_id, "dars", bugun),
                        "🎓 Universitet — bugungi darslar", "✔ Bugun dars yo'q.")


def shaxsiy_ishlar(db, odam_id, bugun=None) -> str:
    return _vazifa_matn(bugungi(db, odam_id, "shaxsiy", bugun),
                        "🔒 Shaxsiy ishlar — bugun", "✔ Bugun shaxsiy ishingiz yo'q.")


# ═══════════════════════════════════════════════════════════ kirish

def _norm(matn: str) -> str:
    """Tugma matni ham, qo'lda yozilgani ham bir xil ko'rinishga.

    Emoji, tinish belgisi va katta-kichik harf farqi yo'qoladi,
    apostrofning har xil turi (ʻ ’ ` ') bittaga keladi. Shunda
    «💰 Moliya», «moliya» va «MOLIYA» — bitta tugma. Tugma ko'rinmay
    qolgan odam so'zni o'zi yozsa ham bot tushunsin.
    """
    t = (matn or "").casefold()
    for b in "ʻʼ’‘`´":
        t = t.replace(b, "'")
    t = "".join(c if (c.isalnum() or c in "' ") else " " for c in t)
    return " ".join(t.split())


# Menyu so'zlari — `_norm` qilingan ko'rinishda.
_MOLIYA_JAVOBLARI = {
    _norm(PULIM): pulim, _norm(TASHQI): tashqi,
    _norm(UY_ISH): uy_vazifalari, _norm(DARS): darslar,
    _norm(SHAXSIY): shaxsiy_ishlar,
    **{_norm(eski): {UY_ISH: uy_vazifalari, DARS: darslar,
                     SHAXSIY: shaxsiy_ishlar}[yangi]
       for eski, yangi in _ESKI.items()},
    "universitet": darslar, "darslar": darslar, "darslarim": darslar,
}
_BOSHLASH = {_norm(x) for x in BOSHLASH} | {_norm(ASOSIY), "start", "menu",
                                            "asosiy", "bosh menyu"}


def javob(db, matn: str, odam_id: int) -> tuple[str, list | None] | None:
    """Menyu matni → (javob, yangi menyu yoki None). Menyu emas → None.

    Tarmoqqa chiqmaydi — shuning uchun testda to'g'ridan-to'g'ri
    chaqiriladi.
    """
    n = _norm(matn)
    if not n:
        return None
    if n in _BOSHLASH:
        return "Bo'limni tanlang:", asosiy_menyu()
    if n == _norm(MOLIYA):
        return "💰 Moliya — nimani ko'ramiz?", moliya_menyu()
    if n == _norm(VAZIFALAR):
        return "📋 Vazifalar — bugungi kun:", vazifa_menyu()
    if n == _norm(AYLANMA):
        return aylanma(db), None
    if n in _MOLIYA_JAVOBLARI:
        return _MOLIYA_JAVOBLARI[n](db, odam_id), None
    return None


def tushunmadim(db, token, chat_id) -> str:
    """Hech narsa mos kelmadi — jim qolmaymiz, menyuni qayta beramiz."""
    _xb()._sorov(token, "sendMessage", chat_id=chat_id,
                 text="Tushunmadim 🙂 Pastdagi menyudan tanlang:",
                 reply_markup=_klaviatura(asosiy_menyu()))
    return "menyu: tushunmadim"


def matn_keldi(db, token, msg: dict, odam_id: int) -> str | None:
    """Shaxsiy chatdagi matn menyu tugmasi bo'lsa — javob beradi."""
    t = (msg.get("text") or "").strip()
    chat_id = msg["chat"]["id"]
    if _norm(t) == _norm(RASXOD):
        # Rasxod — dasturdagi oyna bilan bitta mantiq (tg_rasxod → rasxod_kirit).
        from core import tg_rasxod
        tg_rasxod.boshlash(db, token, chat_id, odam_id)
        return "menyu: rasxod"
    j = javob(db, t, odam_id)
    if j is None:
        return None
    matn, menyu = j
    maydon = {"chat_id": chat_id, "text": matn, "parse_mode": "HTML"}
    if menyu is not None:
        maydon["reply_markup"] = _klaviatura(menyu)
    _xb()._sorov(token, "sendMessage", **maydon)
    return f"menyu: {t}"
