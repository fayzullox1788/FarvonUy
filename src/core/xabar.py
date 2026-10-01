"""Telegram xabarlari — sof mantiq, Qt bilmaydi.

Uy guruhiga uch xil xabar ketadi, hammasi `kutilayotgan()` orqali:

    KUNLIK  — har kuni bir marta, sarlavha + har odamga alohida bo'lak.
    ESLATMA — har vazifaning vaqti tugagach, bittadan.
    RASXOD  — yangi umumiy xarajat yozilganda.
    DARS    — dars boshlanishidan oldin, faqat egasiga (shaxsiy).

`DARS` — YAGONA oldindan ketadigan xabar; qolgan hammasi ish vaqti
tugagach so'raladi.

Shaxsiy deb belgilangan ish guruhga chiqmaydi — egasining o'ziga,
shaxsiy suhbatda ketadi (agar u botga bir marta /start bosgan bo'lsa).

Yagona yozuv nuqtasi bu yerda YO'Q: `yuborilgan` jadvali `db.apply()`
dan o'tmaydi (texnik iz, `davr` kabi istisno) — undo qilinsa xabar
guruhga TAKROR tushib qolmasin deyilgan.

Token manbada emas — `sozlama` jadvalida, foydalanuvchi bazasida.
"""
from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

import money
from core import menyu as mn
from core import dars
from core import vazifa as vz

API = "https://api.telegram.org/bot{token}/{metod}"
FAYL_API = "https://api.telegram.org/file/bot{token}/{yol}"
RASM_MAX = 1280     # Telegram bergan o'lchamlardan shundan kattasini olmaymiz

# ── sozlama kalitlari ──────────────────────────────────────────────────
K_TOKEN = "tg_token"
K_GURUH = "tg_guruh"
K_YOQILGAN = "tg_yoqilgan"
K_KUNLIK_VAQT = "tg_kunlik_vaqt"
K_RASXOD_DAN = "tg_rasxod_dan"
K_OFFSET = "tg_offset"
K_KECHIKTIRISH = "tg_kechiktirish"

# ── tugma matnlari ──────────────────────────────────────────────────────
ALBATTA_TUGMA = "Albatta! ✅"
# Darsda qilinadigan ish — BORISH, shuning uchun tugma ham boshqacha
# yozilgan. `callback_data` esa o'sha-o'sha (`bajar:id`): yozuv
# o'zgarsa eski xabarlardagi tugmalar jimgina o'lik bo'lib qolardi.
DARS_ALBATTA_TUGMA = "Qatnashdim ✅"
YOQ_TUGMA = "Hali yo'q ⏳"
# Namoz o'qilmay qoldi → qazo ishi yoziladi (`vz.qazo_qil`).
QAZO_TUGMA = "Qazo bo'ldi 🕌"
MENYU_TUGMA = "Menyuyimizda nimalar bor 🍲"
MENYU_SOROV = "Bugun nima pishirasiz? 🍲"

# Oshpaz / yuvuvchi uchun tayyor matn — foydalanuvchining O'ZI yozgan,
# qayta so'z bilan yozib chiqmang.
_ROL_BLOK = {
    "oshpaz": (
        "👨‍🍳 {tag}, bugun oshxona sizniki 😄  ({vaqt})",
        "Bugungi missiya: hammamizni och qoldirmaslik 🍳",
    ),
    "yuvuvchi": (
        "🍽 {tag}, bugun rakovina sizni kutyapti 😄  ({vaqt})",
        "Missiya: idishlarni ertalabgacha qoldirmaslik 🫡",
    ),
}

# Eslatma savoli — bular ham foydalanuvchining o'zi yozgan, AYLANMAYDI.
_ROL_ESLATMA = {
    "oshpaz": "bugungi oshxona missiyasi nima bo'ldi?",
    "yuvuvchi": "rakovina bilan ishlar hal bo'ldimi?",
}

# Sarlavhadagi kirish iborasi — kun bo'yicha aylanadi (tasodifiy emas).
_BOSH_IBORA = [
    "Yangi kun, yangi vazifalar! 💪",
    "Bugun ham ajoyib kun bo'lsin! ☀️",
    "Kun boshlandi — ishga tushamiz 🚀",
    "Hammaga xayrli kun! 🌤",
    "Bugungi reja tayyor 📋",
    "Kun yaxshi o'tsin! ✨",
    "Ishlarni tartib bilan bajaramiz 🗓",
]


# ═══════════════════════════════════════════════════════════ yordamchi

def _sana(x) -> date:
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _daqiqa(vaqt: str | None) -> int | None:
    if not vaqt:
        return None
    s, d = str(vaqt).split(":")[:2]
    return int(s) * 60 + int(d)


def _daqiqa_dan(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _tanla(royxat: list, urugh: int):
    """Tasodifiy emas — bir xil urug' bir xil natija beradi."""
    return royxat[int(urugh) % len(royxat)]


def _teg(nom: str, telegram: str | None) -> str:
    """Mas'ul odam — Telegram nomi bo'lsa @bilan, bo'lmasa qalin ism."""
    if telegram:
        return f"<b>@{telegram}</b>"
    return f"<b>{nom}</b>"


def _odam_nom_telegram(db, odam_id: int) -> tuple[str, str | None]:
    r = db.q1("SELECT nom, telegram FROM odam WHERE id=?", odam_id)
    return (r["nom"], r["telegram"]) if r else ("?", None)


def _ish_belgi(v) -> str:
    nom = (v["nom"] or "").lower()
    if "musor" in nom:
        return "🗑"
    if "dasturxon" in nom:
        return "🍽"
    if "plita" in nom or "gaz" in nom:
        return "🔥"
    return "📌"


def _rol(db, v) -> str | None:
    """Vazifaning roli — NOMGA emas, USTUNGA qarab (navbat/ergash/haftalik)."""
    nt = vz.navbat_turi(db)
    if nt and v["nom"] == nt["nom"]:
        return "oshpaz"
    if nt:
        erg = vz.tur_ergash(db, nt["id"])
        if erg and v["nom"] == erg["nom"]:
            return "yuvuvchi"
    if v["nom"] in {t["nom"] for t in vz.uborka_turlari(db)}:
        return "uborka"
    return None


def _menyu_qiymati(v) -> str | None:
    return v["menyu"] if "menyu" in v.keys() else None


# ═══════════════════════════════════════════════════════════ sozlamalar

def sozlamalar(db) -> dict:
    return {
        "token": db.sozlama(K_TOKEN, ""),
        "guruh": db.sozlama(K_GURUH, ""),
        "yoqilgan": db.sozlama(K_YOQILGAN, "0") == "1",
        "kunlik_vaqt": db.sozlama(K_KUNLIK_VAQT, "08:00"),
    }


def sozlama_qoy(db, *, token: str | None = None, guruh: str | None = None,
                yoqilgan: bool | None = None,
                kunlik_vaqt: str | None = None) -> None:
    """Faqat berilgan maydonlarni yangilaydi — qolgani joyida qoladi."""
    if token is not None:
        db.sozlama_qoy(K_TOKEN, token)
    if guruh is not None:
        db.sozlama_qoy(K_GURUH, guruh)
    if yoqilgan is not None:
        db.sozlama_qoy(K_YOQILGAN, "1" if yoqilgan else "0")
    if kunlik_vaqt is not None:
        db.sozlama_qoy(K_KUNLIK_VAQT, kunlik_vaqt)
    # Birinchi marta sozlanganda BUGUNGI vaqt qayd etiladi — shundan
    # oldingi rasxodlar hech qachon e'lon qilinmaydi.
    if not db.q1("SELECT 1 FROM sozlama WHERE kalit=?", K_RASXOD_DAN):
        db.sozlama_qoy(K_RASXOD_DAN,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def sozlangami(db) -> bool:
    s = sozlamalar(db)
    return bool(s["yoqilgan"] and s["token"] and s["guruh"])


def dm_yoqmaganlar(db) -> list:
    """Telegram nomi bor, lekin botga hali /start bosmagan odamlar."""
    return db.q(
        "SELECT id, nom FROM odam WHERE faol=1 AND telegram IS NOT NULL"
        " AND telegram<>'' AND tg_chat IS NULL ORDER BY tartib, id")


def odam_chati(db, odam_id: int) -> int | None:
    r = db.q1("SELECT tg_chat FROM odam WHERE id=?", odam_id)
    return r["tg_chat"] if r else None


def kechiktirish_variantlari(db) -> list[int]:
    xom = db.sozlama(K_KECHIKTIRISH, "")
    if xom:
        try:
            qiymatlar = [int(x.strip()) for x in xom.split(",") if x.strip()]
            if qiymatlar and all(v > 0 for v in qiymatlar):
                return qiymatlar[:4]
        except ValueError:
            pass
    return list(vz.KECHIKTIRISH)


def kechiktirish_qoy(db, qiymatlar) -> None:
    tozalangan = []
    for x in qiymatlar:
        n = int(x)
        if n <= 0:
            raise ValueError("Kechiktirish musbat bo'lishi kerak")
        tozalangan.append(n)
    if not tozalangan:
        raise ValueError("Kamida bitta variant kerak")
    db.sozlama_qoy(K_KECHIKTIRISH,
                  ",".join(str(x) for x in tozalangan[:4]))


# ═══════════════════════════════════════════════════════════ /start → chat

def _chatni_eslab_qol(db, update: dict) -> int | None:
    """Odam botga SHAXSIY yozganda chat raqamini eslab qoladi.

    Guruh xabari, notanish odam yoki chat allaqachon bog'langan bo'lsa —
    None. Faqat SHU hollarda None qaytmasligi kerak: yangi bog'lanish.
    """
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return None
    username = (msg.get("from") or {}).get("username")
    if not username:
        return None
    r = db.q1(
        "SELECT id, nom, tg_chat FROM odam"
        " WHERE faol=1 AND telegram IS NOT NULL AND LOWER(telegram)=LOWER(?)",
        username)
    if not r or r["tg_chat"] is not None:
        return None
    with db.amal(f"Telegram chat bog'landi: {r['nom']}"):
        db.apply("odam", "UPDATE", {"tg_chat": chat["id"]}, r["id"])
    return r["id"]


# ═══════════════════════════════════════════════════ telefondan mahsulot rasmi
#
# Dastur kompyuterda, rasm esa telefonda olinadi. Yo'l: rasmni botga
# SHAXSIY yuborish, izohiga mahsulot nomini aynan yozish. Xabarchi har
# daqiqada ishlaydi — rasm bir daqiqada mahsulot kartasida bo'ladi.
#
# Faqat uy a'zosi (odam.telegram bilan mos) yuborgani qabul qilinadi:
# bot ochiq, uni istalgan odam topib rasm tashlashi mumkin.

def _uy_azosi(db, msg: dict):
    username = (msg.get("from") or {}).get("username")
    if not username:
        return None
    return db.q1("SELECT id, nom FROM odam WHERE faol=1 AND telegram IS NOT NULL"
                 " AND LOWER(telegram)=LOWER(?)", username)


def _rasm_fayl_id(msg: dict) -> str | None:
    """Rasm (siqilgan) yoki «fayl sifatida» yuborilgan rasm."""
    olchamlar = msg.get("photo") or []
    if olchamlar:
        mos = [p for p in olchamlar
               if max(p.get("width", 0), p.get("height", 0)) <= RASM_MAX]
        return (mos[-1] if mos else olchamlar[0])["file_id"]
    hujjat = msg.get("document") or {}
    if str(hujjat.get("mime_type", "")).startswith("image/"):
        return hujjat.get("file_id")
    return None


def _fayl_yukla(token: str, yol: str) -> bytes:
    """Telegram serveridan fayl — testlarda almashtiriladi."""
    url = FAYL_API.format(token=token, yol=yol)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Rasmni yuklab bo'lmadi: {e}") from e


def _rasmni_ishla(db, msg: dict, token: str) -> str | None:
    """Shaxsiy suhbatdagi rasm → izohdagi nomli mahsulotga. Natija matni."""
    import html
    from pathlib import PurePosixPath
    from core import mahsulot as mh

    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return None
    fayl_id = _rasm_fayl_id(msg)
    if not fayl_id or not _uy_azosi(db, msg):
        return None

    def javob(matn):
        try:
            _xabar_yubor(token, chat["id"], matn)
        except Exception:
            pass        # javob yetmasa ham rasm saqlangani muhimroq

    izoh = (msg.get("caption") or "").strip()
    if not izoh:
        javob("Rasm izohiga mahsulot nomini yozing — masalan: <b>Olma</b>")
        return "rasm: izohsiz"
    topilgan = mh.nom_boyicha(db, izoh)
    if not topilgan:
        oxshash = mh.oxshashlar(db, izoh)
        qosh = ("\nBalki: " +", ".join(html.escape(x) for x in oxshash)
                if oxshash else "")
        javob(f"«{html.escape(izoh)}» nomli mahsulot topilmadi. Nomni "
              f"dasturdagidek aniq yozing.{qosh}")
        return f"rasm: topilmadi ({izoh})"
    m = topilgan[0]
    try:
        f = _sorov(token, "getFile", file_id=fayl_id) or {}
        yol = f.get("file_path") or ""
        bayt = _fayl_yukla(token, yol)
        kengaytma = PurePosixPath(yol).suffix or ".jpg"
        mh.rasm_baytdan(db, m["id"], bayt, kengaytma)
    except Exception as e:
        javob(f"Rasmni saqlab bo'lmadi: {html.escape(str(e))}")
        return f"rasm: xato ({e})"
    javob(f"✔ «{html.escape(m['nom'])}» ga rasm biriktirildi.")
    return f"rasm: {m['nom']}"


# ═══════════════════════════════════════════════════════════ kunlik xabar

def oshpaz_vazifasi(db, sana):
    t = vz.navbat_turi(db)
    if not t:
        return None
    iso = _sana(sana).isoformat()
    return db.q1(
        "SELECT * FROM vazifa WHERE ochirilgan=0 AND sana=? AND nom=?"
        " ORDER BY COALESCE(vaqt,'99:99'), id LIMIT 1", iso, t["nom"])


def kunlik_klaviatura(db, sana):
    if not mn.royxat(db):
        return None
    v = oshpaz_vazifasi(db, sana)
    if not v:
        return None
    return [[(MENYU_TUGMA, f"menyu:{v['id']}")]]


def _taom_klaviatura(db, vazifa_id: int):
    taomlar = mn.royxat(db)
    tugmalar = [(t["nom"], f"taom:{vazifa_id}:{t['id']}") for t in taomlar]
    return [tugmalar[i:i + 2] for i in range(0, len(tugmalar), 2)]


def _holat_belgi(v, ochiq_belgi: str) -> str:
    if v["holat"] == vz.BAJARILDI:
        return "✅"
    if v["holat"] == vz.QAZO:
        return "🕌 qazo —"
    return ochiq_belgi


def _bitta_blok(db, v, tag: str) -> str:
    """Bitta vazifaning kunlik ro'yxatdagi ko'rinishi.

    `eslatma_matn()` va `tur_namunasi()` ham shu yerdan foydalanadi —
    ko'rsatish uchun alohida matn yozilmaydi.
    """
    rol = _rol(db, v)
    if rol in ("oshpaz", "yuvuvchi"):
        if v["holat"] == vz.BAJARILDI:
            return f"{tag} — Rahmat! ✅"
        birinchi, ikkinchi = _ROL_BLOK[rol]
        qatorlar = [birinchi.format(tag=tag, vaqt=v["vaqt"] or ""), ikkinchi]
        menyu = _menyu_qiymati(v)
        if rol == "oshpaz" and menyu:
            qatorlar.append(f"🍲 Bugun: {menyu}")
        return "\n".join(qatorlar)

    if rol == "uborka":
        if v["holat"] == vz.BAJARILDI:
            return f"🧹 {tag} {v['nom']} — Rahmat! ✅"
        turi = db.q1(
            "SELECT id FROM vazifa_turi WHERE nom=? AND ochirilgan=0",
            v["nom"])
        qadamlar = vz.qadam_nomlari(db, turi["id"]) if turi else []
        qatorlar = [f"🧹 {tag}, bugun general uborka: {v['nom']}"
                    f" ({v['vaqt'] or ''})"]
        qatorlar += [f"   • {q}" for q in qadamlar]
        return "\n".join(qatorlar)

    belgi = _holat_belgi(v, _ish_belgi(v))
    return (f"{tag}, bugun sizda 👇\n"
            f"{belgi} {v['vaqt'] or ''}  {v['nom']}").strip()


def kunlik_odam_matn(db, sana, odam_id) -> str | None:
    shaxsiy_nomlari = vz.shaxsiy_nomlari(db)
    tasks = [t for t in vz.kun(db, sana, odam_id)
             if t["nom"] not in shaxsiy_nomlari]
    if not tasks:
        return None
    nom, tg = _odam_nom_telegram(db, odam_id)
    tag_teng = _teg(nom, tg)
    tag_qisqa = f"<b>{nom}</b>"
    bolaklar = []
    for i, t in enumerate(tasks):
        bolaklar.append(_bitta_blok(db, t, tag_teng if i == 0 else tag_qisqa))
    return "\n\n".join(bolaklar)


def kunlik_bloklar(db, sana) -> list[dict]:
    """Har odamga bitta bo'lak — hali kamida bitta ochiq ishi bo'lsa."""
    natija = []
    shaxsiy_nomlari = vz.shaxsiy_nomlari(db)
    oshpaz = oshpaz_vazifasi(db, sana)
    oshpaz_odam = oshpaz["odam_id"] if oshpaz else None
    for o in db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id"):
        oid = o["id"]
        tasks = [t for t in vz.kun(db, sana, oid)
                 if t["nom"] not in shaxsiy_nomlari]
        if not tasks:
            continue
        matn = kunlik_odam_matn(db, sana, oid)
        if not matn:
            continue
        natija.append({
            "odam_id": oid, "matn": matn,
            "klaviatura": kunlik_klaviatura(db, sana)
            if oid == oshpaz_odam else None,
        })
    return natija


def kunlik_bosh_matn(db, sana) -> str:
    d = _sana(sana)
    kun_nomi = vz.KUNLAR[d.weekday()]
    sarlavha = f"📅 {kun_nomi}, {d.strftime('%d.%m.%Y')}"
    if not kunlik_bloklar(db, sana):
        return f"{sarlavha}\n\nBugun umumiy vazifa yo'q — hammaga bo'sh kun 🎉"
    ibora = _tanla(_BOSH_IBORA, d.toordinal())
    return f"{sarlavha}\n\n{ibora}"


def kunlik_matn(db, sana) -> str:
    """Bitta uyum — FAQAT ko'rsatish va testlar uchun, guruhga bo'lak-bo'lak ketadi."""
    bosh = kunlik_bosh_matn(db, sana)
    bloklar = kunlik_bloklar(db, sana)
    if not bloklar:
        return bosh
    return bosh + "\n\n" + "\n\n".join(b["matn"] for b in bloklar)


# ═══════════════════════════════════════════════════════════ eslatma

def dars_ogoh_matn(db, v) -> str:
    """Dars boshlanishidan oldin ketadigan xabar — SHAXSIY.

    Savol emas, tugma ham yo'q: bu shunchaki «bugun qayerda bo'lishing
    kerak» degan eslatma. Javob dars TUGAGACH so'raladi.
    """
    nom, tg = _odam_nom_telegram(db, v["odam_id"])
    qatorlar = [f"⏰ {_teg(nom, tg)}, bugun soat {v['vaqt']} da darsingiz bor:",
                f"📚 {v['nom']}"]
    if v["izoh"]:
        qatorlar.append(f"📍 {v['izoh']}")
    return "\n".join(qatorlar)


def eslatma_matn(db, v) -> str:
    nom, tg = _odam_nom_telegram(db, v["odam_id"])
    tag = _teg(nom, tg)
    if dars.darsmi(v):
        # Dars uchun savol «bajardingizmi?» emas: qilinadigan ish
        # darsga BORISH edi, shuning uchun davomat so'raladi.
        return "\n".join([
            f"{tag}, {v['nom']} darsi tugadi.",
            "Davomat: darsda bo'ldingizmi?",
            f"«{DARS_ALBATTA_TUGMA}» yoki «{YOQ_TUGMA}» tugmasini bosing.",
        ])
    rol = _rol(db, v)
    if rol == "uborka":
        satr1 = f"{tag}, general uborka — {v['nom']} bajarildimi?"
    else:
        satr1 = f"{tag}, {v['nom']} bajarildimi?"
    qatorlar = [satr1]
    if rol == "oshpaz":
        qatorlar.append(_ROL_ESLATMA["oshpaz"])
        menyu = _menyu_qiymati(v)
        if menyu:
            qatorlar.append(f"🍲 Bugun: {menyu}")
    elif rol == "yuvuvchi":
        qatorlar.append(_ROL_ESLATMA["yuvuvchi"])
    qatorlar.append(f"«{ALBATTA_TUGMA}» yoki «{YOQ_TUGMA}» tugmasini bosing.")
    return "\n".join(qatorlar)


# ═══════════════════════════════════════════════════════════ shaxsiy

def shaxsiy_matn(db, sana, odam_id) -> str | None:
    shaxsiy_nomlari = vz.shaxsiy_nomlari(db)
    tasks = [t for t in vz.kun(db, sana, odam_id)
             if t["nom"] in shaxsiy_nomlari]
    if not tasks:
        return None
    qatorlar = ["🔒 Shaxsiy ro'yxatingiz:"]
    for t in tasks:
        belgi = _holat_belgi(t, "⏳")
        qator = f"{belgi} {t['vaqt'] or ''}  {t['nom']}".strip()
        qatorlar.append(qator)
        # Izoh — «qayerda va kim bilan». Dars uchun bu asosiy ma'lumot
        # (o'qituvchi · xona): nomning o'zi «qaysi xonaga borishim
        # kerak?» degan savolga javob bermaydi.
        if t["izoh"]:
            qatorlar.append(f"      {t['izoh']}")
    return "\n".join(qatorlar)


def shaxsiy_bloklar(db, sana) -> list[dict]:
    natija = []
    for o in db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id"):
        chat = odam_chati(db, o["id"])
        if chat is None:
            continue
        matn = shaxsiy_matn(db, sana, o["id"])
        if not matn:
            continue
        natija.append({"odam_id": o["id"], "matn": matn, "chat": chat})
    return natija


def shaxsiy_klaviatura(db, sana, odam_id):
    shaxsiy_nomlari = vz.shaxsiy_nomlari(db)
    ochiq = [t for t in vz.kun(db, sana, odam_id)
             if t["nom"] in shaxsiy_nomlari and not vz.yopiqmi(t)]
    if not ochiq:
        return None
    # Tugmaga VAQT yoziladi: bir kunda uchta dars bo'lsa uchta bir xil
    # «Albatta! ✅» chiqib, qaysi biri qaysi ish ekani bilinmasdi.
    # `callback_data` esa o'sha-o'sha qisqa (`bajar:id`) — 64 bayt
    # chegarasi tugma YOZUVIGA emas, ma'lumotiga tegishli.
    qatorlar = []
    for t in ochiq:
        yozuv = DARS_ALBATTA_TUGMA if dars.darsmi(t) else ALBATTA_TUGMA
        if t["vaqt"]:
            yozuv = f"{yozuv} · {t['vaqt']}"
        qatorlar.append([(yozuv, f"bajar:{t['id']}")])
    return qatorlar


# ═══════════════════════════════════════════════════════════ rasxod

def rasxod_matn(db, rasxod_id: int) -> str | None:
    r = db.q1("SELECT * FROM rasxod WHERE id=? AND ochirilgan=0", rasxod_id)
    if not r:
        return None
    tolovchi = db.q1("SELECT nom FROM odam WHERE id=?", r["kim_toladi"])["nom"]
    sarlavha = ("🧾 Boshqa uchun olingan" if r["kim_uchun"]
               else "🛒 Yangi umumiy rasxod")
    qatorlar = [sarlavha]
    if r["nom"]:
        qatorlar.append(r["nom"])
    qatorlar.append(f"To'ladi: {tolovchi} — {money.fmt_som(r['summa'])}")
    qatorlar.append("")
    qatorlar.append("Kim qancha ko'taradi:")
    for u in db.q(
            "SELECT u.summa, o.nom, o.telegram FROM ulush u"
            " JOIN odam o ON o.id=u.odam_id WHERE u.rasxod_id=?"
            " ORDER BY o.tartib", rasxod_id):
        qatorlar.append(f"{_teg(u['nom'], u['telegram'])} — {money.fmt(u['summa'])}")
    return "\n".join(qatorlar)


# ═══════════════════════════════════════════════════════════ yutuq

def yutuq_matn(db, y) -> str:
    r = db.q1("SELECT telegram FROM odam WHERE id=?", y["odam_id"])
    tag = _teg(y["odam"] if "odam" in y.keys() else "",
              r["telegram"] if r else None)
    return f"🏅 {tag} — {y['nom']}!\n{y['izoh']}"


# ═══════════════════════════════════════════════════════════ kutilayotgan

def kutilayotgan(db, hozir: datetime | None = None) -> list[dict]:
    """Hozir yuborilishi kerak bo'lgan HAMMA xabar — yagona joydan.

    Yangi xabar turi qo'shsangiz — shu funksiyaga qo'shing, boshqa
    joydan yubormang, aks holda daqiqada bir marta ishlaydigan skript
    guruhni to'ldirib tashlaydi.
    """
    hozir = hozir or datetime.now()
    bugun = hozir.date()
    s = sozlamalar(db)
    yuborilgan_kalitlar = {r["kalit"] for r in db.q("SELECT kalit FROM yuborilgan")}
    natija: list[dict] = []

    kv = _daqiqa(s["kunlik_vaqt"])
    if kv is not None and _daqiqa_dan(hozir) >= kv:
        bosh_kalit = f"kunlik:{bugun.isoformat()}"
        if bosh_kalit not in yuborilgan_kalitlar:
            natija.append({"turi": "kunlik", "kalit": bosh_kalit,
                           "matn": kunlik_bosh_matn(db, bugun),
                           "chat": None, "klaviatura": None})
        shaxsiy_nomlari_k = vz.shaxsiy_nomlari(db)
        for b in kunlik_bloklar(db, bugun):
            kalit = f"kunlik:{bugun.isoformat()}:odam:{b['odam_id']}"
            if kalit in yuborilgan_kalitlar:
                continue
            # Hamma ishi allaqachon bajarilgan odamga yangi xabar ochilmaydi.
            tasks = [t for t in vz.kun(db, bugun, b["odam_id"])
                     if t["nom"] not in shaxsiy_nomlari_k]
            if all(vz.yopiqmi(t) for t in tasks):
                continue
            natija.append({"turi": "kunlik", "kalit": kalit,
                           "matn": b["matn"], "chat": None,
                           "klaviatura": b["klaviatura"]})

        for b in shaxsiy_bloklar(db, bugun):
            kalit = f"shaxsiy:{bugun.isoformat()}:odam:{b['odam_id']}"
            if kalit in yuborilgan_kalitlar:
                continue
            natija.append({"turi": "shaxsiy", "kalit": kalit,
                           "matn": b["matn"], "chat": b["chat"],
                           "klaviatura": shaxsiy_klaviatura(
                               db, bugun, b["odam_id"])})

    # ── eslatma: faqat BUGUNGI vazifalar, vaqti tugagan va bajarilmagan
    shaxsiy_nomlari = vz.shaxsiy_nomlari(db)
    for v in vz.kun(db, bugun):
        if vz.yopiqmi(v):
            continue
        if vz.kechiktirilganmi(v, hozir):
            continue
        if v["vaqt"] is None:
            continue
        tugadi = _daqiqa(v["vaqt"]) + v["davomiylik"]
        if dars.darsmi(v):
            tugadi += dars.KECHIKISH_DAQIQA
        if _daqiqa_dan(hozir) < tugadi:
            continue
        kech = v["kechiktirildi"] if "kechiktirildi" in v.keys() else None
        kalit = f"vazifa:{v['id']}" + (f":{kech}" if kech else "")
        if kalit in yuborilgan_kalitlar:
            continue
        is_shaxsiy = v["nom"] in shaxsiy_nomlari
        chat = None
        if is_shaxsiy:
            chat = odam_chati(db, v["odam_id"])
            if chat is None:
                continue
        natija.append({
            "turi": "eslatma", "kalit": kalit, "matn": eslatma_matn(db, v),
            "chat": chat, "vazifa_id": v["id"],
            "klaviatura": [[(DARS_ALBATTA_TUGMA if dars.darsmi(v)
                             else ALBATTA_TUGMA, f"bajar:{v['id']}"),
                            (YOQ_TUGMA, f"haliyoq:{v['id']}")]]
                          + ([[(QAZO_TUGMA, f"qazo:{v['id']}")]]
                             if vz.namozmi(v) else []),
        })

    # ── dars ogohlantirishi: boshlanishidan `OGOH_DAQIQA` oldin
    #
    # Alohida blok, chunki bu YAGONA oldindan ketadigan xabar: qolgan
    # hammasi ish vaqti tugagach so'raladi. Kaliti ham boshqa
    # (`dars_ogoh:`), aks holda ogohlantirish yuborilgani davomat
    # savolini bo'g'ib qo'yardi.
    for v in vz.kun(db, bugun):
        if not dars.darsmi(v) or vz.yopiqmi(v):
            continue
        if v["vaqt"] is None:
            continue
        boshlanish = _daqiqa(v["vaqt"])
        endi = _daqiqa_dan(hozir)
        if not boshlanish - dars.OGOH_DAQIQA <= endi < boshlanish:
            continue
        kalit = f"dars_ogoh:{v['id']}"
        if kalit in yuborilgan_kalitlar:
            continue
        chat = odam_chati(db, v["odam_id"])
        if chat is None:
            continue
        natija.append({"turi": "dars", "kalit": kalit,
                       "matn": dars_ogoh_matn(db, v), "chat": chat,
                       "klaviatura": None})

    # ── umumiy rasxod e'loni
    tg_rasxod_dan = db.sozlama(K_RASXOD_DAN, "")
    if tg_rasxod_dan:
        for r in db.q(
                "SELECT id FROM rasxod WHERE ochirilgan=0 AND umumiymi=1"
                " AND yaratilgan>=? ORDER BY yaratilgan, id", tg_rasxod_dan):
            kalit = f"rasxod:{r['id']}"
            if kalit in yuborilgan_kalitlar:
                continue
            matn = rasxod_matn(db, r["id"])
            if not matn:
                continue
            natija.append({"turi": "rasxod", "kalit": kalit, "matn": matn,
                           "chat": None, "klaviatura": None})

    # ── yutuq tabrigi
    for y in vz.yutuqlar(db):
        kalit = f"yutuq:{y['id']}"
        if kalit in yuborilgan_kalitlar:
            continue
        natija.append({"turi": "yutuq", "kalit": kalit,
                       "matn": yutuq_matn(db, y), "chat": None,
                       "klaviatura": None})

    return natija


def belgila(db, kalit: str, xabar_id: int | None = None) -> None:
    """`yuborilgan` ga yozadi. `db.apply()` DAN O'TMAYDI — texnik iz."""
    db.con.execute(
        "INSERT INTO yuborilgan(kalit, xabar_id) VALUES(?,?)"
        " ON CONFLICT(kalit) DO UPDATE SET xabar_id=excluded.xabar_id",
        (kalit, xabar_id))


def eski_izlarni_tozala(db) -> None:
    db.con.execute(
        "DELETE FROM yuborilgan WHERE vaqt < datetime('now','-60 days','localtime')")


# ═══════════════════════════════════════════════════════════ tarmoq

# Ochiq HTTPS ulanishlar (keep-alive). Har so'rovga yangi TCP + TLS ochish
# ~0,3 s olardi, ochiq ulanishda ~0,1 s (2026-10-01 da o'lchangan) — bitta
# tugma bir necha so'rov yuboradi, demak javob sezilarli tezlashadi.
# Uzun so'rov (getUpdates) o'z ulanishida: u 50 s gacha band turadi.
_ULANISHLAR: dict = {}


def _ulanish(kalit: str, vaqt: float):
    import http.client
    h = _ULANISHLAR.get(kalit)
    if h is None:
        h = http.client.HTTPSConnection("api.telegram.org", timeout=vaqt)
        _ULANISHLAR[kalit] = h
    h.timeout = vaqt
    if h.sock is not None:
        h.sock.settimeout(vaqt)
    return h


def _ulanishni_yop(kalit: str) -> None:
    h = _ULANISHLAR.pop(kalit, None)
    if h is not None:
        try:
            h.close()
        except Exception:
            pass


def _sorov(token: str, metod: str, **maydonlar):
    """Yagona tarmoq chaqiruvi — testlarda almashtiriladi."""
    # `_vaqt` — Telegramga ketmaydi: uzun so'rovda (getUpdates timeout=N)
    # ulanish N soniyadan ko'proq kutishi kerak, aks holda o'zimiz uzamiz.
    vaqt = maydonlar.pop("_vaqt", 15)
    yol = urllib.parse.urlsplit(API.format(token=token, metod=metod)).path
    data = json.dumps(maydonlar).encode("utf-8")
    kalit = "tinglash" if metod == "getUpdates" else "asosiy"
    # Ochiq ulanishni server yopib qo'ygan bo'lishi mumkin — bir marta
    # yangisini ochib qayta urinamiz (so'rov hali bajarilmagan bo'ladi).
    for urinish in (1, 2):
        h = _ulanish(kalit, vaqt)
        try:
            h.request("POST", yol, body=data,
                      headers={"Content-Type": "application/json"})
            javob = json.loads(h.getresponse().read().decode("utf-8"))
            break
        except (OSError, http.client.HTTPException) as e:
            _ulanishni_yop(kalit)
            uzildi = isinstance(e, (http.client.RemoteDisconnected,
                                    ConnectionResetError, BrokenPipeError,
                                    http.client.CannotSendRequest))
            if urinish == 2 or not uzildi:
                raise RuntimeError(f"Telegramga ulanib bo'lmadi: {e}") from e
    if not javob.get("ok"):
        raise RuntimeError(javob.get("description", "Noma'lum xato"))
    return javob.get("result")


def _klaviatura_json(rows) -> str:
    return json.dumps({
        "inline_keyboard": [
            [{"text": t, "callback_data": d} for t, d in qat] for qat in rows
        ]}, ensure_ascii=False)


def _xabar_yubor(token: str, chat_id, matn: str, klaviatura=None):
    maydonlar = {"chat_id": chat_id, "text": matn, "parse_mode": "HTML"}
    if klaviatura:
        maydonlar["reply_markup"] = _klaviatura_json(klaviatura)
    return _sorov(token, "sendMessage", **maydonlar)


def _rasm_yubor(token: str, chat_id, yol, izoh: str = ""):
    """Kompyuterdagi rasmni yuboradi (multipart) — testlarda almashtiriladi."""
    import uuid
    from pathlib import Path
    yol = Path(yol)
    chegara = uuid.uuid4().hex
    qator = "\r\n"
    qismlar = []
    for nom, qiymat in (("chat_id", str(chat_id)), ("caption", izoh),
                        ("parse_mode", "HTML")):
        qismlar.append((f"--{chegara}{qator}Content-Disposition: form-data; "
                        f'name="{nom}"{qator}{qator}{qiymat}{qator}')
                       .encode("utf-8"))
    qismlar.append((f"--{chegara}{qator}Content-Disposition: form-data; "
                    f'name="photo"; filename="{yol.name}"{qator}'
                    f"Content-Type: application/octet-stream{qator}{qator}")
                   .encode("utf-8") + yol.read_bytes() + qator.encode())
    qismlar.append(f"--{chegara}--{qator}".encode("utf-8"))
    req = urllib.request.Request(
        API.format(token=token, metod="sendPhoto"), data=b"".join(qismlar),
        headers={"Content-Type": f"multipart/form-data; boundary={chegara}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            javob = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Rasm yuborilmadi: {e}") from e
    if not javob.get("ok"):
        raise RuntimeError(javob.get("description", "Noma'lum xato"))
    return javob.get("result")


def bot_haqida(token: str) -> dict:
    return _sorov(token, "getMe")


def guruhlarni_top(token: str) -> list[dict]:
    """Bot ko'rgan oxirgi guruhlar — guruh raqamini qo'lda topish shart emas."""
    updates = _sorov(token, "getUpdates", limit=100) or []
    korilgan: dict = {}
    for u in updates:
        chat = ((u.get("message") or u.get("channel_post")
                or u.get("my_chat_member") or {}).get("chat"))
        if not chat or chat.get("type") not in ("group", "supergroup", "channel"):
            continue
        korilgan[chat["id"]] = {
            "id": str(chat["id"]), "nom": chat.get("title") or str(chat["id"]),
            "turi": chat.get("type"),
        }
    return list(korilgan.values())


def sinov_yubor(db, token: str, guruh: str) -> list:
    """Hozir navbatdagilarni xuddi ertalabkidek bo'lak-bo'lak yuboradi.

    `yuborilgan` ga YOZMAYDI — bu shunchaki sinov, real navbatga
    tegmaydi.
    """
    natija = []
    for x in kutilayotgan(db):
        chat = x["chat"] if x.get("chat") is not None else guruh
        natija.append(_xabar_yubor(token, chat, x["matn"], x.get("klaviatura")))
    return natija


def yubor_kutilayotgan(db, hozir: datetime | None = None,
                       sinov: bool = False) -> list[dict]:
    """Navbatdagi hammasini yuboradi (yoki `sinov=True` — faqat ko'rsatadi)."""
    if not sinov and not sozlangami(db):
        return []
    s = sozlamalar(db)
    natija = []
    for x in kutilayotgan(db, hozir):
        chat = x["chat"] if x.get("chat") is not None else s["guruh"]
        if sinov:
            natija.append(x)
            continue
        try:
            javob = _xabar_yubor(s["token"], chat, x["matn"], x.get("klaviatura"))
        except Exception:
            continue  # bitta xato qolganini to'xtatmaydi, keyingi urinishda qayta
        belgila(db, x["kalit"], (javob or {}).get("message_id"))
        natija.append(x)
    return natija


# ═══════════════════════════════════════════════════════════ tugmalar

def _egasimi(db, odam_id: int, username: str) -> bool:
    """Telegram nomi kiritilmagan bo'lsa tekshirib bo'lmaydi — ruxsat beriladi."""
    r = db.q1("SELECT telegram FROM odam WHERE id=?", odam_id)
    if not r or not r["telegram"]:
        return True
    return bool(username) and r["telegram"].lower() == username.lower()


def tugmani_ishla(db, sorov: dict, token: str, guruh: str) -> None:
    """Guruhda bosilgan bitta tugmani ishlaydi (callback_query)."""
    data = sorov.get("data") or ""
    qismlar = data.split(":")
    amal = qismlar[0] if qismlar else ""
    username = (sorov.get("from") or {}).get("username") or ""
    xabar = sorov.get("message") or {}
    chat_id = (xabar.get("chat") or {}).get("id")
    message_id = xabar.get("message_id")

    if amal == "menyu" and len(qismlar) == 2:
        vid = int(qismlar[1])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text=f"{MENYU_SOROV}\n(taomni tanlang)", parse_mode="HTML",
              reply_markup=_klaviatura_json(_taom_klaviatura(db, vid)))

    elif amal == "taom" and len(qismlar) == 3:
        vid, mid = int(qismlar[1]), int(qismlar[2])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        taom = mn.bitta(db, mid)
        if not taom:
            return
        vz.menyu_qoy(db, vid, taom["nom"])
        v = vz.bitta(db, vid)
        nom, tg = _odam_nom_telegram(db, v["odam_id"])
        kb = kunlik_klaviatura(db, v["sana"]) or []
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text=_bitta_blok(db, v, _teg(nom, tg)), parse_mode="HTML",
              reply_markup=_klaviatura_json(kb))

    elif amal == "bajar" and len(qismlar) == 2:
        vid = int(qismlar[1])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        vz.bajar(db, vid, True)
        v = vz.bitta(db, vid)
        nom, tg = _odam_nom_telegram(db, v["odam_id"])
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text=_bitta_blok(db, v, _teg(nom, tg)), parse_mode="HTML")

    elif amal == "qazo" and len(qismlar) == 2:
        vid = int(qismlar[1])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        if not vz.namozmi(v) or v["holat"] != vz.OCHIQ:
            return
        vz.qazo_qil(db, vid)
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text=f"🕌 {v['nom']} qazo bo'ldi. "
                   f"«{vz.qazo_nomi(v['nom'])}» ro'yxatingizga qo'shildi.",
              parse_mode="HTML")

    elif amal == "haliyoq" and len(qismlar) == 2:
        vid = int(qismlar[1])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text="Qachon eslataman? ⏳", parse_mode="HTML",
              reply_markup=_klaviatura_json(kechiktirish_klaviatura(db, vid)))

    elif amal == "kech" and len(qismlar) == 3:
        vid, daqiqa = int(qismlar[1]), int(qismlar[2])
        v = vz.bitta(db, vid)
        if not v or not _egasimi(db, v["odam_id"], username):
            return
        vz.kechiktir(db, vid, daqiqa)
        _sorov(token, "editMessageText", chat_id=chat_id, message_id=message_id,
              text=f"Xop, {daqiqa} daqiqadan keyin qayta so'rayman ⏳")


def kechiktirish_klaviatura(db, vazifa_id: int):
    tugmalar = []
    for d in kechiktirish_variantlari(db):
        matn = f"{d // 60} soatdan keyin" if d % 60 == 0 else f"{d} daqiqadan keyin"
        tugmalar.append((matn, f"kech:{vazifa_id}:{d}"))
    return [tugmalar[i:i + 2] for i in range(0, len(tugmalar), 2)]


def offsetni_sur(db, updates: list[dict]) -> None:
    if not updates:
        return
    maks = max(int(u["update_id"]) for u in updates)
    db.sozlama_qoy(K_OFFSET, str(maks + 1))


def _shaxsiy_azo(db, msg: dict):
    """Shaxsiy chatdagi uy a'zosi (rasxod boti faqat ularga ishlaydi)."""
    if ((msg.get("chat") or {}).get("type")) != "private":
        return None
    return _uy_azosi(db, msg)


def tugmalarni_qayta_ishla(db, kutish: int = 0) -> list[str]:
    """`getUpdates` ni o'qiydi: tugmalar, /start, rasxod suhbati, rasmlar.

    `kutish` > 0 — uzun so'rov: yangi xabar kelguncha shuncha soniya
    kutadi va kelishi bilan qaytadi (xabarchi shu bilan tez javob beradi).
    """
    from core import tg_rasxod
    s = sozlamalar(db)
    if not s["token"]:
        return []
    offset = int(db.sozlama(K_OFFSET, "0") or "0")
    try:
        updates = _sorov(s["token"], "getUpdates", offset=offset,
                         timeout=kutish, _vaqt=kutish + 15) or []
    except Exception as e:
        return [f"Xato: {e}"]
    natija = []
    for u in updates:
        try:
            natija += _bittasini_ishla(db, u, s, tg_rasxod)
        except Exception as e:
            # Bitta buzuq xabar qolganlarini to'xtatmasin — offset baribir
            # suriladi, aks holda u har safar qayta-qayta yiqilardi.
            natija.append(f"Xato ({u.get('update_id')}): {e}")
    offsetni_sur(db, updates)
    return natija


def _bittasini_ishla(db, u: dict, s: dict, tg_rasxod) -> list[str]:
    natija = []
    if "callback_query" in u:
        cb = u["callback_query"]
        if str(cb.get("data") or "").startswith("rx:"):
            # Rasxod suhbati — faqat uy a'zosining SHAXSIY chatida.
            msg = dict(cb.get("message") or {}, **{"from": cb.get("from")})
            azo = _shaxsiy_azo(db, msg)
            if azo:
                natija.append(tg_rasxod.tugma_bosildi(
                    db, s["token"], cb, azo["id"]) or "rx: ?")
        else:
            tugmani_ishla(db, cb, s["token"], s["guruh"])
            natija.append(f"tugma: {cb.get('data')}")
    elif "message" in u:
        msg = u["message"]
        oid = _chatni_eslab_qol(db, u)
        if oid:
            natija.append(f"chat bog'landi: odam#{oid}")
        azo = _shaxsiy_azo(db, msg)
        if azo and msg.get("text"):
            # Avval menyu (Moliya / Vazifalar): suhbat o'rtasida menyu
            # tugmasi bosilsa u «sabab» bo'lib yozilib qolmasin.
            from core import tg_menyu
            r = (tg_menyu.matn_keldi(db, s["token"], msg, azo["id"])
                 or tg_rasxod.matn_keldi(db, s["token"], msg, azo["id"])
                 or tg_menyu.tushunmadim(db, s["token"], msg["chat"]["id"]))
            natija.append(r)
        r = _rasmni_ishla(db, msg, s["token"])
        if r:
            natija.append(r)
    return natija


# ═══════════════════════════════════════════════════════════ namuna

def tur_namunasi(db, tur_id: int, odam_id: int, vaqt: str = "19:00") -> dict | None:
    """«Bu ish qachon va qanday yoziladi?» — HAQIQIY funksiyalardan quriladi.

    Bazaga hech narsa yozmaydi: soxta (id=0) vazifa xotirada quriladi.
    """
    tur = vz.tur_bitta(db, tur_id)
    odam = db.q1("SELECT * FROM odam WHERE id=?", odam_id)
    if not tur or not odam:
        return None
    soxta = {"id": 0, "nom": tur["nom"], "odam_id": odam_id,
             "sana": date.today().isoformat(), "vaqt": vaqt,
             "davomiylik": tur["davomiylik"], "holat": vz.OCHIQ,
             "kechiktirildi": None}
    s = sozlamalar(db)
    tag = _teg(odam["nom"], odam["telegram"])
    shaxsiy = bool(tur["shaxsiy"])
    tayyor = True
    if shaxsiy:
        tayyor = odam_chati(db, odam_id) is not None
    esl_vaqt = None
    if vaqt:
        d = (_daqiqa(vaqt) + tur["davomiylik"]) % (24 * 60)
        esl_vaqt = f"{d // 60:02d}:{d % 60:02d}"
    return {
        "tur": tur, "odam": odam["nom"], "yoqilgan": s["yoqilgan"],
        "tayyormi": tayyor and s["yoqilgan"],
        "qayerga": "Shaxsiy suhbat" if shaxsiy else "Uy guruhi",
        "kunlik_vaqt": s["kunlik_vaqt"], "eslatma_vaqt": esl_vaqt,
        "kunlik": _bitta_blok(db, soxta, tag),
        "eslatma": eslatma_matn(db, soxta),
        "kechiktirish": kechiktirish_variantlari(db),
    }
