"""Dizayn tizimi: ranglar, shriftlar, oraliqlar va umumiy stil.

Rang bu yerda bezak emas, ma'no: yashil = senga qarzdorlar, qizil =
sen qarzdorsan. Shu ikkisi hech qachon almashmaydi.

Uchta rejim: `iliq` (iliq qog'oz, asosiy), `oq` (toza), `tungi`
(quyuq, lekin TINIQ). Palitra modul darajasidagi nomlarda yashaydi
(`FON`, `KARTA`, `MATN`…) va `rejim_qoy()` ularni qayta bog'laydi::

    theme.rejim_qoy("tungi")
    app.setStyleSheet(theme.STIL)
    widgets.qayta_boya(oyna)        # keshlangan ranglar
    oyna.yangila()

Rang oilalari: `KOK` — asosiy (siyoh-binafsha), `IKKI` — ikkilamchi
(firuza), `UCH` — uchlamchi (olcha), `YASHIL`/`QIZIL` — pul,
`SARIQ`/`TOQ` — ogohlantirish, `ODAM_RANG`/`TUR_RANG` — odam va
kategoriya ranglari.

QSS haqida uchta eslatma (uchalasi ham qonda yozilgan):

1.  Ota-widgetdagi `setStyleSheet("background:transparent")` BUTUN
    avlodga tarqaladi va global fonni bosib ketadi. Shuning uchun
    kartalar, tugmalar va jadvallar fonini o'zida, selektor bilan
    e'lon qiladi (`widgets._stil()`).
2.  `box-shadow` yo'q, `QGraphicsDropShadowEffect` esa butun shoxni
    dasturiy rasterlashga majbur qiladi: 8 sahifada 2760 ms ↔ 865 ms.
    Soya O'CHIQ (`SOYA_YOQ=False`), chuqurlik soch-chiziq va
    karta/fon kontrastidan keladi.
3.  `QCalendarWidget` ichida oddiy `QTableView` + `QHeaderView` bor,
    va umumiy `::item`/`::section` to'ldirmalari ularni shishirib
    oyning oxirgi qatorini qirqib yuboradi. Taqvim ataylab alohida,
    aniq selektorlar bilan qayta yoziladi (`TAQVIM_STIL`).
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect

# ══════════════════════════════════════════════════════════ shriftlar
#
# Matn — Segoe UI Variable (Win11), eski tizimlarda oddiy Segoe UI.
# Raqam — "Segoe UI": uning raqamlari tabular, ya'ni 1 va 8 bir xil
# kenglikda. Ustunlar tebranmaydi. (Segoe UI Variable esa standart
# holatda proporsional raqam beradi — shuning uchun pul uchun emas.)

SHRIFT      = "Segoe UI Variable Text"
SHRIFT_ZAX  = "Segoe UI"
SHRIFT_BOSH = "Segoe UI Variable Display"     # sarlavhalar
RAQAM       = "Segoe UI"                      # pul (tabular raqamlar)

MATN_OILA  = f'"{SHRIFT}", "{SHRIFT_ZAX}"'
RAQAM_OILA = f'"{RAQAM}"'
BOSH_OILA  = f'"{SHRIFT_BOSH}", "{SHRIFT_ZAX}"'

# ── o'lcham shkalasi ─────────────────────────────────────────────────
O_MIKRO  = 11   # ko'z-qosh yorliq (KARTA SARLAVHASI)
O_MAYDA  = 12   # izoh, yordamchi matn
O_KICHIK = 13   # jadval katagi, yorliq
O_ASOS   = 14   # oddiy matn
O_ORTA   = 15   # ta'kidlangan matn
O_BOLIM  = 17   # bo'lim sarlavhasi
O_BOSH   = 22   # sahifa sarlavhasi
O_KATTA  = 28   # asosiy pul raqami

# ── oraliq shkalasi (8px ritm) ───────────────────────────────────────
B1, B2, B3, B4, B5, B6 = 4, 8, 12, 16, 24, 32

# ── burchaklar ───────────────────────────────────────────────────────
R_KICHIK = 8    # tugma, kiritish
R_ORTA   = 10   # yo'lak, chip
R_KARTA  = 14   # karta

# ── soya ─────────────────────────────────────────────────────────────
# Ataylab o'chiq: qarang yuqoridagi 2-eslatma.
SOYA_YOQ = False


# ══════════════════════════════════════════════════════════ palitralar

REJIMLAR = [
    ("iliq",  "Iliq"),      # iliq qog'oz — asosiy
    ("oq",    "Oq"),        # toza oq
    ("tungi", "Tungi"),     # quyuq, tiniq
]

_PALITRA = {

    # ── iliq: iliq qog'oz + to'yingan siyoh-binafsha ─────────────────
    # Yer iliq qum, karta oq — shuning uchun karta qog'ozdan ko'tarilib
    # turadi. Asosiy rang siyoh-binafsha (indigo): u na yashil, na
    # qizil, ya'ni pul ma'nosini o'g'irlamaydi, lekin iliq yerda
    # kuchli va tirik ko'rinadi.
    "iliq": dict(
        FON="#F3ECE0", FON_TUQ="#E8DFCF",
        KARTA="#FFFFFF", KARTA_ICH="#FBF7EF", KARTA_FOKUS="#FFFFFF",
        CHIZIQ="#E4DACA", CHIZIQ_OCH="#EFE8DC", CHIZIQ_TUQ="#CEC1A9",

        MATN="#191510", MATN_2="#3A332A", KUL="#655C4F", KUL_OCH="#8A8071",

        YON="#221D33", YON_2="#2C2642", YON_FAOL="#3A3260",
        YON_CHIZIQ="#37305A", YON_CHEK="#130F1E",
        MATN_OQ="#F4F1EA", YON_KUL="#B0A7C9",

        KOK="#4A40BE", KOK_OCH="#5C52D4", KOK_TUQ="#39308F",
        KOK_YORUG="#A79EF5", KOK_FON="#EAE7FB", KOK_MATN="#FFFFFF",

        IKKI="#0D7490", IKKI_FON="#DEF0F6", IKKI_TUQ="#0A5568",
        UCH="#A02D74", UCH_FON="#FAE4F0", UCH_TUQ="#7B1F58",

        YASHIL="#12784E", YASHIL_FON="#DDF2E6", YASHIL_TUQ="#0B5637",
        QIZIL="#C33A2A", QIZIL_FON="#FBE3DE", QIZIL_TUQ="#95271A",
        QIZIL_BOS="#F5D0C8",
        SARIQ="#96600A", SARIQ_FON="#FAEACA", SARIQ_TUQ="#6F4602",
        TOQ="#B2490A", TOQ_FON="#FBE2CF", TOQ_TUQ="#873605",

        SARLAVHA="#5B51C4",
        JADVAL_BOSH="#F4F1FC", JADVAL_BOSH_MATN="#564CB8",

        AYLANMA="#D3C7B2", AYLANMA_HOVER="#B8A88C",
        SOYA_RANG=(74, 58, 40),
        ODAM_RANG=["#4A40BE", "#0D7490", "#B0421F",
                   "#9C2C74", "#1D6F3F", "#8A5A12"],
        TUR_RANG=["#B2490A", "#96600A", "#4D7C0F", "#12784E", "#0D7490",
                  "#0369A1", "#3B5BDB", "#6D28D9", "#A02D74", "#BE123C"],
    ),

    # ── oq: toza, salqin oq yer; xuddi shu siyoh-binafsha asos ───────
    "oq": dict(
        FON="#F4F5F8", FON_TUQ="#E9EAF0",
        KARTA="#FFFFFF", KARTA_ICH="#FAFAFD", KARTA_FOKUS="#FFFFFF",
        CHIZIQ="#E2E4EC", CHIZIQ_OCH="#EDEEF4", CHIZIQ_TUQ="#C9CCD8",

        MATN="#12141C", MATN_2="#343846", KUL="#5C616F", KUL_OCH="#838897",

        YON="#191B2E", YON_2="#23253C", YON_FAOL="#2E3150",
        YON_CHIZIQ="#2B2E4A", YON_CHEK="#0D0E19",
        MATN_OQ="#F2F3F9", YON_KUL="#A2A7C4",

        KOK="#3E36CC", KOK_OCH="#5048E0", KOK_TUQ="#2E289E",
        KOK_YORUG="#A49DFA", KOK_FON="#E9E7FD", KOK_MATN="#FFFFFF",

        IKKI="#0B7285", IKKI_FON="#DDF0F5", IKKI_TUQ="#08525F",
        UCH="#A31E6E", UCH_FON="#FBE3F1", UCH_TUQ="#7C1453",

        YASHIL="#0E7A4A", YASHIL_FON="#DCF3E6", YASHIL_TUQ="#085733",
        QIZIL="#C22E22", QIZIL_FON="#FCE3E0", QIZIL_TUQ="#921E14",
        QIZIL_BOS="#F7CFCA",
        SARIQ="#9A6300", SARIQ_FON="#FCEECB", SARIQ_TUQ="#714800",
        TOQ="#BF4A08", TOQ_FON="#FDE6D6", TOQ_TUQ="#8E3604",

        SARLAVHA="#4F46D4",
        JADVAL_BOSH="#F2F1FE", JADVAL_BOSH_MATN="#4A42C4",

        AYLANMA="#CDD0DC", AYLANMA_HOVER="#AAAEC0",
        SOYA_RANG=(40, 40, 38),
        ODAM_RANG=["#3E36CC", "#0B7285", "#B23C18",
                   "#9E2470", "#146B3C", "#835310"],
        TUR_RANG=["#C24A08", "#9A6300", "#4A7C0A", "#0E7A4A", "#0B7285",
                  "#0369A1", "#2F4FD8", "#6926D6", "#A31E6E", "#BE0F39"],
    ),

    # ── tungi: quyuq siyoh-ko'k, lekin TINIQ ─────────────────────────
    # "Quyuq" degani "kulrang" ham, "past kontrast" ham emas: yer
    # tungi ko'k (kulrang emas), matn kartada 12:1 dan past emas,
    # yashil/qizil hamon aniq yashil/qizil.
    # DIQQAT: bu yerda `*_TUQ` = OCHROQ (quyuq yerda ochroq rang
    # ta'kidlaydi) — yorug' rejimlarning teskarisi.
    "tungi": dict(
        FON="#0E0F1C", FON_TUQ="#161829",
        KARTA="#181A2C", KARTA_ICH="#20223A", KARTA_FOKUS="#262943",
        CHIZIQ="#2E3150", CHIZIQ_OCH="#252843", CHIZIQ_TUQ="#3F4368",

        MATN="#F2F2FA", MATN_2="#D2D3E6", KUL="#A0A3C0", KUL_OCH="#7C80A0",

        YON="#090A16", YON_2="#151830", YON_FAOL="#242850",
        YON_CHIZIQ="#1E2140", YON_CHEK="#000000",
        MATN_OQ="#F2F2FA", YON_KUL="#9EA2C6",

        KOK="#7B73F5", KOK_OCH="#948DFF", KOK_TUQ="#645CE0",
        KOK_YORUG="#B4AEFF", KOK_FON="#1A1E40", KOK_MATN="#0B0A1C",

        IKKI="#37B8D4", IKKI_FON="#0F3A45", IKKI_TUQ="#7FD8EA",
        UCH="#E86BB0", UCH_FON="#40182F", UCH_TUQ="#F7A8D0",

        YASHIL="#3BD68C", YASHIL_FON="#0F3327", YASHIL_TUQ="#7EEBB6",
        QIZIL="#FF7B6A", QIZIL_FON="#3D1D1A", QIZIL_TUQ="#FFA79A",
        QIZIL_BOS="#52251F",
        SARIQ="#F0BE45", SARIQ_FON="#3A2D0E", SARIQ_TUQ="#FAD98A",
        TOQ="#FF8F4D", TOQ_FON="#41220F", TOQ_TUQ="#FFB88A",

        SARLAVHA="#A8A2FF",
        JADVAL_BOSH="#1E2138", JADVAL_BOSH_MATN="#A29CF0",

        AYLANMA="#383C60", AYLANMA_HOVER="#4E5382",
        SOYA_RANG=(0, 0, 0),
        ODAM_RANG=["#9A93FF", "#4CC8E0", "#F0906B",
                   "#F07CC0", "#5FD79B", "#E0B36A"],
        TUR_RANG=["#FF8F4D", "#F0BE45", "#A3D65B", "#3BD68C", "#37B8D4",
                  "#5BB0F5", "#8B9BFF", "#B98BFF", "#E86BB0", "#FF7B8E"],
    ),
}

# Har uchala palitrada kalitlar bir xil bo'lishi SHART. Aks holda
# `rejim_qoy()` faqat mavjud kalitlarni almashtiradi va yetishmagani
# oldingi rejimdan qolib ketadi — masalan tungi rejimda yorug' fon.
_KALITLAR = set(_PALITRA["iliq"])
for _n, _p in _PALITRA.items():
    _yoq = _KALITLAR ^ set(_p)
    if _yoq:
        raise RuntimeError(f"palitra «{_n}» kalitlari mos emas: {sorted(_yoq)}")

REJIM = "iliq"       # joriy rejim (rejim_qoy() bilan almashadi)


# ══════════════════════════════════════════════════════════ yordamchi

def pul_rangi(qiymat: int) -> str:
    """Musbat = yashil (senga qaytadi), manfiy = qizil (sen berasan)."""
    if qiymat > 0:
        return YASHIL
    if qiymat < 0:
        return QIZIL
    return KUL


def pul_foni(qiymat: int) -> str:
    """Shu qiymatga mos yumshoq fon (chip/pill uchun)."""
    if qiymat > 0:
        return YASHIL_FON
    if qiymat < 0:
        return QIZIL_FON
    return FON_TUQ


def aralash(a: str, b: str, ulush: float) -> str:
    """`a` va `b` ni aralashtiradi (`ulush` = `a` ning ulushi).

    Rejimga bog'liq oraliq rang kerak bo'lganda ishlatiladi — masalan
    daraja chizig'ining o'zani: u fonga ham, to'ldirilgan qismga ham
    yaqin bo'lishi kerak, va bu uchala rejimda ham to'g'ri chiqishi
    uchun qo'lda yozilmaydi, hisoblanadi.
    """
    t = max(0.0, min(1.0, ulush))
    x, y = a.lstrip("#"), b.lstrip("#")
    q = [round(int(x[i:i + 2], 16) * t + int(y[i:i + 2], 16) * (1 - t))
         for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(q)


def ustiga(rang: str) -> str:
    """Shu fon ustida o'qiladigan matn rangi (oq yoki quyuq).

    Rejimga qarab qo'lda tanlash shart bo'lmasin: tungi rejimda asos
    ranglar OCHIQ (masalan `#FF7B6A`), yorug' rejimlarda esa QUYUQ —
    bitta chip ikkalasida ham o'qilishi kerak.
    """
    h = rang.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    yorq = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0C0B14" if yorq > 0.5 else "#FFFFFF"


def odam_rangi(kalit) -> str:
    """Odamning doimiy rangi — `id` yoki ism bo'yicha.

    Bir odam har sahifada bir xil rangda ko'rinishi uchun rang
    tasodifiy emas, kalitdan hisoblanadi.
    """
    return ODAM_RANG[_indeks(kalit, len(ODAM_RANG))]


def tur_rangi(kalit) -> str:
    """Kategoriya (`turi`) rangi — `id` yoki nom bo'yicha."""
    return TUR_RANG[_indeks(kalit, len(TUR_RANG))]


def _indeks(kalit, n: int) -> int:
    if isinstance(kalit, int):
        return (kalit - 1) % n if kalit > 0 else 0
    # ism: harflar yig'indisi — barqaror, chunki `hash()` har ishga
    # tushishda boshqacha bo'ladi
    return sum(ord(c) for c in str(kalit)) % n


# ── pul darajasi (core.ledger.holat() bilan bitta lug'at) ────────────
#
# Qizil → to'q sariq → sariq → yashil: bu shunchaki to'rt rang emas,
# og'irlik zinapoyasi. O'qimasdan ham kim qiyinchilikda ekani ko'rinadi.

DARAJA_NOM = {
    "qarzda":   "qarzda",
    "juda_kam": "juda kam",
    "kam":      "kam qoldi",
    "yaxshi":   "yetarli",
}

_DARAJA = {
    "qarzda":   ("QIZIL", "QIZIL_FON", "QIZIL_TUQ"),
    "juda_kam": ("TOQ", "TOQ_FON", "TOQ_TUQ"),
    "kam":      ("SARIQ", "SARIQ_FON", "SARIQ_TUQ"),
    "yaxshi":   ("YASHIL", "YASHIL_FON", "YASHIL_TUQ"),
}


def daraja_rangi(holat: str) -> tuple[str, str, str]:
    """`holat` → (asos, yumshoq fon, quyuq matn).

    `asos` — chiziqning to'ldirilgan qismi;
    `fon`  — chip foni va chiziq o'zani;
    `matn` — chip matni (yorug' rejimda quyuqroq, tungida ochroq).
    """
    a, f, m = _DARAJA.get(holat, _DARAJA["yaxshi"])
    return globals()[a], globals()[f], globals()[m]


def raqam_shrift(olcham: int = O_ASOS, ogirlik: int = 600) -> QFont:
    """Pul uchun shrift — raqamlari doim bir xil kenglikda (tabular).

    Diqqat: QSS har doim `setFont()` dan kuchli. Shuning uchun bu
    shrift faqat QSS raqam o'lchamini belgilamagan joyda (masalan
    jadval kataklarida, Qt::FontRole orqali) ishlaydi.
    """
    f = QFont(RAQAM)
    f.setPixelSize(olcham)
    f.setWeight(QFont.Weight(ogirlik))
    try:                       # ehtiyot uchun — Segoe UI o'zi tabular
        f.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        pass
    return f


def matn_shrift(olcham: int = O_ASOS, ogirlik: int = 400) -> QFont:
    f = QFont(SHRIFT)
    f.setFamilies([SHRIFT, SHRIFT_ZAX])
    f.setPixelSize(olcham)
    f.setWeight(QFont.Weight(ogirlik))
    return f


def soya(widget, radius: int = 22, y: int = 3, alfa: int = 26):
    """Yumshoq soya — FAQAT `SOYA_YOQ=True` bo'lganda (modul boshidagi
    2-eslatma: effekt butun shoxni rasterlaydi va lag beradi)."""
    if not SOYA_YOQ:
        return None
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(radius)
    e.setXOffset(0)
    e.setYOffset(y)
    e.setColor(QColor(*SOYA_RANG, alfa))
    widget.setGraphicsEffect(e)
    return e


# ══════════════════════════════════════════════════════════ shablonlar
#
# Quyidagilar `{NOM}` o'rin egalari bilan yozilgan va `_qur()` ichida
# joriy palitra bilan to'ldiriladi. QSS'ning o'z qavslari ikkilangan.

_KARTA = """
QFrame#Karta {{
    background: {KARTA};
    border: 1px solid {CHIZIQ};
    border-bottom-color: {CHIZIQ_TUQ};
    border-radius: {R_KARTA}px;
}}
"""

_YORLIQ = """
/* Karta "ko'z-qoshi" — kulrang emas, asosiy rangda. Har kartada
   bittadan turgani uchun sahifaga rang shu yerdan tarqaladi. */
QLabel#KartaSarlavha {{
    color: {SARLAVHA}; font-size: {O_MIKRO}px; font-weight: 700;
    letter-spacing: 1.1px; background: transparent; border: none;
}}
QLabel#Yorliq {{
    color: {MATN_2}; font-size: {O_KICHIK}px; background: transparent;
    border: none;
}}
QLabel#Izoh {{
    color: {KUL}; font-size: {O_MAYDA}px; background: transparent;
    border: none;
}}
QLabel#Sarlavha {{
    font-family: {BOSH_OILA};
    font-size: {O_BOSH}px; font-weight: 700; color: {MATN};
    background: transparent; border: none;
}}
QLabel#Bolim {{
    font-family: {BOSH_OILA};
    font-size: {O_BOLIM}px; font-weight: 600; color: {MATN};
    background: transparent; border: none;
}}
/* Oila ataylab "Segoe UI" — uning raqamlari standart holatda
   tabular. 'Segoe UI Variable' chiroyliroq, lekin raqamlari
   proporsional: 1 111 111 va 8 888 888 turli kenglikda chiqadi va
   yangilanganda raqam sakraydi. QSS `font-feature-settings` ni
   bilmaydi, shuning uchun `tnum` bilan tuzatib ham bo'lmaydi. */
QLabel#Katta {{
    font-family: {RAQAM_OILA};
    font-size: {O_KATTA}px; font-weight: 600; color: {MATN};
    background: transparent; border: none;
}}
QLabel#Orta {{
    font-family: {RAQAM_OILA};
    font-size: {O_BOLIM}px; font-weight: 600; color: {MATN};
    background: transparent; border: none;
}}
"""

_TUGMA = """
QPushButton {{
    background: {KARTA};
    border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_KICHIK}px;
    padding: 8px 16px;
    color: {MATN_2};
    font-size: {O_KICHIK}px;
    font-weight: 600;
    min-height: 18px;
}}
/* Ikkilamchi tugma sichqoncha ostida asosiy rangga o'tadi — sahifada
   bosiladigan joy qayerdaligi kulrangda emas, rangda ko'rinadi. */
QPushButton:hover  {{ background: {KOK_FON}; border-color: {KOK};
                      color: {KOK}; }}
QPushButton:pressed{{ background: {KOK_FON}; border-color: {KOK_TUQ}; }}
QPushButton:disabled {{ color: {KUL_OCH}; background: {FON}; border-color: {CHIZIQ}; }}

QPushButton#Asosiy {{
    background: {KOK}; color: {KOK_MATN}; border: 1px solid {KOK_TUQ};
    padding: 9px 18px; font-weight: 600;
}}
QPushButton#Asosiy:hover   {{ background: {KOK_OCH}; border-color: {KOK}; }}
QPushButton#Asosiy:pressed {{ background: {KOK_TUQ}; }}
QPushButton#Asosiy:disabled{{ background: {CHIZIQ}; border-color: {CHIZIQ};
                              color: {KUL_OCH}; }}

QPushButton#Xavfli {{ color: {QIZIL}; border-color: {CHIZIQ_TUQ}; }}
QPushButton#Xavfli:hover   {{ background: {QIZIL_FON}; border-color: {QIZIL};
                              color: {QIZIL_TUQ}; }}
QPushButton#Xavfli:pressed {{ background: {QIZIL_BOS}; }}
"""

_KIRITISH = """
/* `QAbstractSpinBox` — QSpinBox, QDoubleSpinBox, QDateEdit va
   QTimeEdit ning HAMMASI. Ilgari ular nomma-nom sanalgan edi va
   `QTimeEdit` ro'yxatga tushmay qolgandi: QSS turi selektori faqat
   sinf va uning VORISLARIGA tegadi, `QTimeEdit` esa `QDateEdit` ning
   vorisi emas — ikkalasi `QDateTimeEdit` dan keladigan aka-uka.
   Natijada «Soat» maydoni butunlay stilsiz, tizim ko'rinishida
   chiqib turardi va qatordagi qolgan maydonlarga to'g'ri kelmasdi. */
QLineEdit, QComboBox, QAbstractSpinBox,
QPlainTextEdit, QTextEdit {{
    background: {KARTA};
    border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_KICHIK}px;
    padding: 7px 10px;
    color: {MATN};
    font-size: {O_KICHIK}px;
    selection-background-color: {KOK_OCH};
    selection-color: {KOK_MATN};
    min-height: 18px;
}}
QLineEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {{
    border-color: {KUL_OCH};
}}
QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {KOK}; background: {KARTA_FOKUS};
}}
QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled {{
    background: {FON_TUQ}; color: {KUL_OCH}; border-color: {CHIZIQ};
}}
/* O'q tugmalari maydonning O'NG chekkasida chiziladi va odatdagi
   to'ldirma ular uchun yetmaydi — raqam o'qlarning tagiga kirib
   ketadi. Sub-kontrolning O'ZI stillanmaydi (`::up-button` va
   boshqalari): Qt shunda standart chizishni to'xtatadi va o'q
   umuman yo'qoladi. */
QAbstractSpinBox {{ padding-right: 22px; }}
QLineEdit {{ placeholder-text-color: {KUL_OCH}; }}
QLineEdit#Pul {{
    font-family: {RAQAM_OILA};
    font-size: {O_ORTA}px; font-weight: 600; letter-spacing: .2px;
}}
/* ::drop-down ni stillamaymiz — Qt shunda o'q rasmini butunlay
   chizmay qo'yadi (image: kerak bo'lib qoladi), tanlagich esa
   o'qsiz qolib "bu ro'yxatmi?" degan savol tug'diradi. */
QComboBox QAbstractItemView {{
    background: {KARTA}; border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_KICHIK}px; padding: 4px;
    color: {MATN};
    selection-background-color: {KOK}; selection-color: {KOK_MATN};
    outline: none;
}}
QCheckBox, QRadioButton {{
    background: transparent; spacing: 8px;
    color: {MATN_2}; font-size: {O_KICHIK}px;
}}
/* Belgi (✓ / •) uchun QSS'da faqat `image: url(fayl)` bor — fayl
   ishlatmaslik uchun shakl bilan ko'rsatamiz: belgilangan katakcha
   to'ldirilgan kvadrat, belgilangan radio esa halqa. Ikkisi ham
   bo'sh holatdan bir qarashda ajralib turadi. */
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {CHIZIQ_TUQ}; background: {KARTA};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {KOK_OCH};
}}
QCheckBox::indicator:checked {{
    background: {KOK}; border: 1px solid {KOK};
}}
QCheckBox::indicator:checked:hover {{ background: {KOK_OCH}; border-color: {KOK_OCH}; }}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background: {FON_TUQ}; border-color: {CHIZIQ};
}}
QRadioButton::indicator:checked {{
    width: 8px; height: 8px;
    background: {KARTA}; border: 4px solid {KOK}; border-radius: 8px;
}}
"""

_JADVAL = """
QTableWidget, QTableView {{
    background: {KARTA};
    alternate-background-color: {KARTA_ICH};
    border: 1px solid {CHIZIQ};
    border-radius: {R_ORTA}px;
    gridline-color: transparent;
    outline: none;
    font-size: {O_KICHIK}px;
    color: {MATN_2};
    selection-background-color: {KOK_FON};
}}
QTableWidget::item, QTableView::item {{
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {CHIZIQ_OCH};
}}
/* `color` ataylab yo'q: tanlangan qatorda ham yashil/qizil ma'no
   saqlanishi kerak — rangni har katak o'zi (delegat orqali) beradi. */
QTableWidget::item:selected, QTableView::item:selected {{
    background: {KOK_FON};
}}
/* Sarlavha yo'lagi ataylab rangli: ustunlar qayerda boshlanishini
   ko'z chiziqsiz ham topadi. */
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {JADVAL_BOSH};
    color: {JADVAL_BOSH_MATN};
    border: none;
    border-bottom: 1px solid {CHIZIQ_TUQ};
    padding: 9px 10px;
    font-size: {O_MIKRO}px; font-weight: 700; letter-spacing: .7px;
}}
QHeaderView::section:first {{
    padding-left: 12px; border-top-left-radius: {R_ORTA}px;
}}
QHeaderView::section:last {{ border-top-right-radius: {R_ORTA}px; }}
QTableCornerButton::section {{ background: {JADVAL_BOSH}; border: none; }}
"""

_AYLANMA = """
QScrollBar:vertical {{
    background: transparent; width: 12px; margin: 2px 2px 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {AYLANMA}; border-radius: 5px; min-height: 34px;
    margin: 0 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {AYLANMA_HOVER}; }}
QScrollBar:horizontal {{
    background: transparent; height: 12px; margin: 0 2px 2px 2px;
}}
QScrollBar::handle:horizontal {{
    background: {AYLANMA}; border-radius: 5px; min-width: 34px; margin: 2px 0;
}}
QScrollBar::handle:horizontal:hover {{ background: {AYLANMA_HOVER}; }}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0; width: 0; border: none; background: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""

# ── taqvim ───────────────────────────────────────────────────────────
#
# NEGA BU SHUNCHA UZUN.  `QCalendarWidget` ichida to'liq huquqli
# `QTableView` (`qt_calendar_calendarview`), `QHeaderView` va
# `QWidget#qt_calendar_navigationbar` (+ QToolButton'lar, QSpinBox)
# bor.  Umumiy `::item`/`::section`/`QSpinBox` to'ldirmalarimiz o'sha
# ichki widgetlarga ham tushib, katakni shishiradi — QCalendarWidget
# esa sizeHint'ni QSS'ni bilmagan holda shrift metrikasidan
# hisoblaydi, natijada oyning 6-haftasi popup'ga sig'may qirqiladi.
# Shuning uchun bu yerda hammasi ANIQ selektor bilan qayta yoziladi va
# to'ldirmalar nolga tushadi.  Katak balandligi `widgets.Taqvim` da
# kod bilan ham majburlanadi.

_TAQVIM = """
QCalendarWidget {{
    background: {KARTA};
    border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_ORTA}px;
}}
QCalendarWidget QWidget {{ background: {KARTA}; color: {MATN}; }}

/* ── tepadagi yo'lak ─────────────────────────────────────────── */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {FON_TUQ};
    border: none;
    border-bottom: 1px solid {CHIZIQ};
    border-top-left-radius: {R_ORTA}px;
    border-top-right-radius: {R_ORTA}px;
    min-height: 36px;
}}
QCalendarWidget QToolButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {MATN};
    font-size: {O_KICHIK}px;
    font-weight: 600;
    padding: 4px 10px;
    margin: 4px 2px;
    min-height: 24px;
}}
QCalendarWidget QToolButton:hover  {{ background: {CHIZIQ}; }}
QCalendarWidget QToolButton:pressed{{ background: {CHIZIQ_TUQ}; }}
QCalendarWidget QToolButton#qt_calendar_prevmonth,
QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    min-width: 28px; max-width: 34px; padding: 4px 4px;
    font-size: {O_BOLIM}px; font-weight: 700;
}}
/* Oy tugmasidagi menyu uchburchagini olib tashlaymiz — u matnni
   siqib qo'yadi va oy nomi qirqiladi. */
QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0; }}
QCalendarWidget QMenu {{
    background: {KARTA}; border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_KICHIK}px; padding: 4px; color: {MATN};
}}
QCalendarWidget QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; }}
QCalendarWidget QMenu::item:selected {{ background: {KOK}; color: {KOK_MATN}; }}
QCalendarWidget QSpinBox#qt_calendar_yearedit {{
    background: {KARTA};
    border: 1px solid {CHIZIQ_TUQ};
    border-radius: 6px;
    color: {MATN};
    font-size: {O_KICHIK}px; font-weight: 600;
    padding: 2px 4px;
    margin: 4px 2px;
    min-height: 22px;
    min-width: 62px;
    selection-background-color: {KOK}; selection-color: {KOK_MATN};
}}

/* ── kunlar to'ri ────────────────────────────────────────────── */
/* DIQQAT: umumiy `QTableView` qoidalarini bekor qilamiz. Chegara,
   burchak va to'ldirma nolga tushadi — aks holda 6-hafta qirqiladi. */
QCalendarWidget QAbstractItemView#qt_calendar_calendarview,
QCalendarWidget QTableView {{
    background: {KARTA};
    alternate-background-color: {KARTA};
    border: none;
    border-radius: 0;
    padding: 0;
    margin: 0;
    outline: none;
    gridline-color: transparent;
    color: {MATN};
    font-size: {O_ASOS}px;
    selection-background-color: {KOK};
    selection-color: {KOK_MATN};
}}
QCalendarWidget QAbstractItemView#qt_calendar_calendarview::item,
QCalendarWidget QTableView::item {{
    padding: 0;
    margin: 0;
    border: none;
}}
/* Hafta nomlari (Du Se Ch …) — QHeaderView. Umumiy 9px to'ldirma
   bu yerda vertikal joyni yeb qo'yadi. */
QCalendarWidget QHeaderView {{ background: {KARTA}; border: none; }}
QCalendarWidget QHeaderView::section {{
    background: {KARTA};
    color: {KUL};
    border: none;
    padding: 0;
    margin: 0;
    font-size: {O_MAYDA}px; font-weight: 700; letter-spacing: .5px;
}}
QCalendarWidget QHeaderView::section:first {{ padding-left: 0; }}
"""


# ══════════════════════════════════════════════════════════ qurish

_OLCHAMLAR = dict(
    MATN_OILA=MATN_OILA, RAQAM_OILA=RAQAM_OILA, BOSH_OILA=BOSH_OILA,
    O_MIKRO=O_MIKRO, O_MAYDA=O_MAYDA, O_KICHIK=O_KICHIK, O_ASOS=O_ASOS,
    O_ORTA=O_ORTA, O_BOLIM=O_BOLIM, O_BOSH=O_BOSH, O_KATTA=O_KATTA,
    R_KICHIK=R_KICHIK, R_ORTA=R_ORTA, R_KARTA=R_KARTA,
)

# `qayta_boya()` shu ro'yxat bo'yicha widgetlarni qayta stillaydi.
STIL_NOMLARI = ("STIL", "KARTA_STIL", "YORLIQ_STIL", "TUGMA_STIL",
                "KIRITISH_STIL", "JADVAL_STIL", "AYLANMA_STIL", "TAQVIM_STIL",
                "ICHKI_STIL", "RAQAM_KARTA_STIL", "KARTA_ICHI_STIL",
                "JADVAL_YAKKA_STIL", "JADVAL_ICHKI_STIL")


def _qur() -> None:
    """Joriy palitradan barcha stil bo'laklarini va `STIL` ni quradi."""
    g = globals()
    ns = dict(_OLCHAMLAR)
    ns.update({k: v for k, v in g.items() if k.isupper() and isinstance(v, str)})

    def f(shablon: str) -> str:
        return shablon.format(**ns)

    karta     = f(_KARTA)
    yorliq    = f(_YORLIQ)
    tugma     = f(_TUGMA)
    kiritish  = f(_KIRITISH)
    jadval    = f(_JADVAL)
    aylanma   = f(_AYLANMA)
    taqvim    = f(_TAQVIM)

    g["KARTA_STIL"]   = karta
    g["YORLIQ_STIL"]  = yorliq
    g["TUGMA_STIL"]   = tugma
    g["KIRITISH_STIL"] = kiritish
    g["JADVAL_STIL"]  = jadval
    g["AYLANMA_STIL"] = aylanma
    g["TAQVIM_STIL"]  = taqvim

    # ── tayyor to'plamlar ────────────────────────────────────────────
    # Bularni widget'ning o'ziga qo'yamiz, shunda ota-widgetdagi
    # `background:transparent` ularni buzolmaydi (1-eslatma).
    g["ICHKI_STIL"]        = tugma + kiritish
    g["RAQAM_KARTA_STIL"]  = karta + yorliq
    g["KARTA_ICHI_STIL"]   = karta + yorliq + tugma + kiritish + jadval
    g["JADVAL_YAKKA_STIL"] = jadval + aylanma
    g["JADVAL_ICHKI_STIL"] = f("""
QTableWidget, QTableView {{
    border: none; border-radius: 0; background: transparent;
}}
QHeaderView::section {{ background: {JADVAL_BOSH}; }}
QHeaderView::section:first {{ border-top-left-radius: 6px; }}
QHeaderView::section:last {{ border-top-right-radius: 6px; }}
""")
    # jadval karta ichida — bitta satrda tayyor turadi (har chaqiruvda
    # yangi satr yasamaslik uchun)
    g["JADVAL_KARTADA_STIL"] = g["JADVAL_YAKKA_STIL"] + g["JADVAL_ICHKI_STIL"]

    # DIQQAT: bo'laklar (karta, yorliq…) allaqachon formatlangan —
    # ularda QSS'ning YAKKA qavslari bor. Shuning uchun tepa va past
    # qismlar ALOHIDA formatlanadi, keyin qo'shiladi. Hammasini birga
    # `.format()` ga berish `KeyError` beradi.
    g["STIL"] = f("""
/* ── asos ────────────────────────────────────────────────────── */
QWidget {{
    background: {FON};
    color: {MATN};
    font-family: {MATN_OILA};
    font-size: {O_ASOS}px;
}}
QMainWindow, QDialog {{ background: {FON}; }}
QScrollArea {{ border: none; background: transparent; }}
QLabel {{ background: transparent; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    background: {CHIZIQ}; border: none;
}}

/* ── chap panel: dasturning imzosi ───────────────────────────── */
#Yon {{
    background: {YON};
    border-right: 1px solid {YON_CHEK};
}}
#Yon QLabel {{ background: transparent; color: {MATN_OQ}; }}
#YonSarlavha {{
    font-family: {BOSH_OILA};
    color: {MATN_OQ}; font-size: 19px; font-weight: 600;
    letter-spacing: .2px;
    padding: 24px 20px 2px 20px; background: transparent;
}}
#YonIzoh {{
    color: {YON_KUL}; font-size: {O_MIKRO}px; letter-spacing: .3px;
    padding: 0 2px 16px 2px; margin: 0 18px 14px 18px;
    border-bottom: 1px solid {YON_CHIZIQ};
    background: transparent;
}}
#YonHolat {{
    color: {YON_KUL}; font-size: {O_MIKRO}px;
    padding: 12px 18px; background: transparent;
}}
QPushButton#Nav {{
    background: transparent;
    color: {YON_KUL};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 11px 14px 11px 15px;
    margin: 1px 10px 1px 0;
    text-align: left;
    font-size: {O_ASOS}px; font-weight: 500;
    min-height: 20px;
}}
QPushButton#Nav:hover {{
    background: {YON_2}; color: {MATN_OQ};
}}
QPushButton#Nav:checked {{
    background: {YON_FAOL};
    color: {MATN_OQ};
    font-weight: 600;
    border-left: 3px solid {KOK_YORUG};
}}
QPushButton#Nav:focus {{ outline: none; }}

/* ── umumiy bo'laklar ────────────────────────────────────────── */
""") + karta + yorliq + tugma + kiritish + jadval + aylanma + taqvim + f("""
/* ── dialog tugmalari ────────────────────────────────────────── */
QDialogButtonBox {{ background: transparent; }}
QDialogButtonBox QPushButton {{ min-width: 88px; }}

/* ── boshqa ──────────────────────────────────────────────────── */
QToolTip {{
    background: {YON}; color: {MATN_OQ};
    border: 1px solid {YON_CHEK}; padding: 8px 11px; border-radius: 8px;
    font-size: {O_KICHIK}px;
}}
QProgressBar {{
    background: {FON_TUQ}; border: none; border-radius: 5px;
    height: 8px; max-height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {KOK}; border-radius: 5px; }}
QSplitter::handle {{ background: {CHIZIQ}; }}
QMenu {{
    background: {KARTA}; border: 1px solid {CHIZIQ_TUQ};
    border-radius: {R_ORTA}px; padding: 6px; color: {MATN};
}}
QMenu::item {{ padding: 8px 26px 8px 14px; border-radius: 6px;
               font-size: {O_KICHIK}px; }}
QMenu::item:selected {{ background: {KOK}; color: {KOK_MATN}; }}
QMenu::separator {{ height: 1px; background: {CHIZIQ}; margin: 5px 8px; }}
QStatusBar {{
    background: {FON_TUQ}; color: {KUL};
    border-top: 1px solid {CHIZIQ}; font-size: {O_MAYDA}px;
}}
QStatusBar::item {{ border: none; }}
QMessageBox {{ background: {FON}; }}
QMessageBox QLabel {{ background: transparent; color: {MATN};
                      font-size: {O_ASOS}px; }}
""")


def rejim_qoy(nom: str) -> str:
    """Rejimni almashtiradi: palitrani qayta bog'laydi va `STIL` ni quradi.

    Qaytaradi: haqiqatda qo'llangan rejim nomi (noma'lum nom berilsa
    «iliq» ga qaytadi).

    Bu FAQAT modul darajasidagi qiymatlarni o'zgartiradi. Ekranga
    tushishi uchun chaqiruvchi::

        theme.rejim_qoy("tungi")
        app.setStyleSheet(theme.STIL)
        widgets.qayta_boya(oyna)      # keshlangan ranglar
        oyna.yangila()
    """
    global REJIM
    if nom not in _PALITRA:
        nom = "iliq"
    REJIM = nom
    globals().update(_PALITRA[nom])
    _qur()
    return nom


def stil() -> str:
    """Joriy rejim uchun to'liq QSS."""
    return STIL


def rejim_nomi(nom: str | None = None) -> str:
    """Rejimning ko'rinadigan nomi («iliq» → «Iliq»)."""
    nom = nom or REJIM
    for k, v in REJIMLAR:
        if k == nom:
            return v
    return nom


rejim_qoy(REJIM)        # modul yuklanganda palitra tayyor bo'lsin
