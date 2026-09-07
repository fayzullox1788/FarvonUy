"""Dizayn tizimi: ranglar, shriftlar, o'lchovlar va umumiy QSS.

Qiymatlar **`Farvon_Uy_-_Dizayn_korgazmasi.html` dan aynan ko'chirilgan** —
u piksel bo'yicha haqiqat manbai (brif: «for pixels, HTML wins over spec»).
Bu yerda hech narsa «yaxshilanmagan»: hex ham, padding ham, shrift o'lchami
ham HTML dagidek.

Uchta qat'iy qoida:

1.  **Hech qayerda hex yozilmaydi.** Komponent rangni faqat `R("aksent")`
    orqali oladi. Noto'g'ri token nomi darhol `KeyError` beradi.

2.  **Rang yolg'iz ma'no tashimaydi.** Yashil/qizil yonida doim matn
    yorlig'i bo'ladi — buni komponentlar ta'minlaydi.

3.  **Uchala rejimda kalitlar bir xil.** Aks holda rejim almashganda
    yetishmagan token oldingi rejimdan qolib ketadi. Import paytida
    tekshiriladi.

QSS haqida uchta eslatma — uchalasi ham eski koddan qonda o'tgan:

*   Ota-widgetga `background: transparent` yozilsa Qt uni BUTUN avlodga
    tarqatadi va kartalar, tugmalar fonini ham o'chiradi. Shaffoflik
    faqat `QWidget#Shaffof` selektori bilan beriladi.
*   `::drop-down`, `::down-arrow`, `::up-button` stillanmaydi — Qt o'sha
    zahoti standart chizishni to'xtatadi va strelka umuman yo'qoladi.
*   Soya yo'q: `QGraphicsDropShadowEffect` butun shoxni dasturiy
    rasterlashga majbur qiladi (8 sahifada 2760 ms ↔ 865 ms). Chuqurlik
    soch-chiziq va karta/fon kontrastidan keladi.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QFontDatabase

# ══════════════════════════════════════════════════════ 1. rang tokenlari
#
# HTML: html[data-theme="…"] bloklaridagi CSS o'zgaruvchilari.
#   --hover  → sirt_hover        --kuchli → chiziq_kuchli
#   --tanl   → sirt_tanlangan    --*-t    → *_fon_matn
#   --aksent-fill → aksent_tola  --page   → page (ko'rgazma foni)

ILIQ = dict(
    page="#E5DCC6", fon="#F1E9D7", sirt="#FBF6EA", sirt2="#FFFFFF",
    sirt_hover="#F3ECDA", sirt_tanlangan="#E9EFF8",
    chiziq="#DCCFB4", chiziq_kuchli="#C9B896",
    matn="#322B21", matn2="#7A6F5D", matn3="#9A8E79",

    aksent="#2456A0", aksent_hover="#1D4685", aksent_tola="#2456A0",
    aksent_fon="#E4ECF7", aksent_fon_matn="#1D4685", aksent_ustida="#FFFFFF",

    yashil="#237B4B", yashil_fon="#E2EEE2", yashil_fon_matn="#1E5B36",
    qizil="#BF3B2C", qizil_fon="#F7E3DF", qizil_fon_matn="#93291D",
    toq_sariq="#C2620E", toq_sariq_fon="#F6E3CE", toq_sariq_fon_matn="#8A4A07",
    sariq="#A87B08", sariq_fon="#F6E7C8", sariq_fon_matn="#7A5A06",
    sariq_bar="#E3AE1F",

    neytral="#8D8371", fokus="#2456A0",
)

OQ = dict(
    page="#E9E8E4", fon="#F5F4F1", sirt="#FFFFFF", sirt2="#FFFFFF",
    sirt_hover="#F2F1EE", sirt_tanlangan="#E9EFF8",
    chiziq="#E1DFD9", chiziq_kuchli="#C9C6BD",
    matn="#26241F", matn2="#6B6759", matn3="#96917F",

    aksent="#2456A0", aksent_hover="#1D4685", aksent_tola="#2456A0",
    aksent_fon="#E8EEF8", aksent_fon_matn="#1D4685", aksent_ustida="#FFFFFF",

    yashil="#237B4B", yashil_fon="#E3F0E6", yashil_fon_matn="#1E5B36",
    qizil="#BF3B2C", qizil_fon="#F9E5E1", qizil_fon_matn="#93291D",
    toq_sariq="#C2620E", toq_sariq_fon="#F8E8D4", toq_sariq_fon_matn="#8A4A07",
    sariq="#A87B08", sariq_fon="#F8EDCF", sariq_fon_matn="#7A5A06",
    sariq_bar="#E3AE1F",

    neytral="#8B8878", fokus="#2456A0",
)

TUNGI = dict(
    page="#17140F", fon="#201C16", sirt="#2A251D", sirt2="#332D23",
    sirt_hover="#3A3327", sirt_tanlangan="#2C3648",
    chiziq="#3E3729", chiziq_kuchli="#58513E",
    matn="#EDE6D6", matn2="#B3A98F", matn3="#857C66",

    aksent="#5B8FD6", aksent_hover="#6FA0E0", aksent_tola="#2E5FA8",
    aksent_fon="#26334A", aksent_fon_matn="#9FC0EC", aksent_ustida="#FFFFFF",

    yashil="#5CBF8A", yashil_fon="#24352B", yashil_fon_matn="#7FD1A6",
    qizil="#E0705F", qizil_fon="#40261F", qizil_fon_matn="#EE9384",
    toq_sariq="#E09044", toq_sariq_fon="#3D2E1C", toq_sariq_fon_matn="#EAA968",
    sariq="#D9B04A", sariq_fon="#3B3318", sariq_fon_matn="#E5C36E",
    sariq_bar="#D9B04A",

    neytral="#7A7260", fokus="#6FA0E0",
)

REJIMLAR = [("iliq", "Iliq"), ("oq", "Oq"), ("tungi", "Tungi")]
TOKENLAR = {"iliq": ILIQ, "oq": OQ, "tungi": TUNGI}

# Uchala palitrada kalitlar bir xil bo'lishi SHART.
_KALITLAR = set(ILIQ)
for _nom, _p in TOKENLAR.items():
    _farq = _KALITLAR ^ set(_p)
    if _farq:
        raise RuntimeError(
            f"«{_nom}» rejimida token kalitlari mos emas: {sorted(_farq)}")

_REJIM = "iliq"


class _Xabarchi(QObject):
    """Rejim almashganini e'lon qiladi.

    O'zini chizadigan komponentlar shunga ulanadi: eski koddagi
    `qayta_boya(ildiz)` daraxt bo'ylab yurishining o'rniga har widget
    o'zini yangilaydi.
    """
    ozgardi = Signal(str)


XABARCHI = _Xabarchi()


def rejim() -> str:
    return _REJIM


def rejim_nomi(kalit: str | None = None) -> str:
    return dict(REJIMLAR).get(kalit or _REJIM, kalit or _REJIM)


def rejim_qoy(kalit: str) -> str:
    """Rejimni almashtiradi va kuzatuvchilarga xabar beradi.

    Chaqirgandan keyin `app.setStyleSheet(theme.qss())` qayta qo'yiladi —
    QSS tokenlardan qurilgani uchun u ham yangilanadi.
    """
    global _REJIM
    if kalit not in TOKENLAR:
        kalit = "iliq"
    if kalit != _REJIM:
        _REJIM = kalit
        XABARCHI.ozgardi.emit(kalit)
    return _REJIM


def R(nom: str) -> str:
    """Joriy rejimdagi token rangi. Noma'lum nom — darhol `KeyError`."""
    try:
        return TOKENLAR[_REJIM][nom]
    except KeyError:
        raise KeyError(
            f"«{nom}» degan rang tokeni yo'q. Mavjudlari: "
            f"{', '.join(sorted(_KALITLAR))}") from None


# ══════════════════════════════════════════════════════ 2. rang yordamchi

def aralash(a: str, b: str, ulush: float) -> str:
    """`a` va `b` ni aralashtiradi (`ulush` — `a` ning ulushi)."""
    t = max(0.0, min(1.0, ulush))
    x, y = a.lstrip("#"), b.lstrip("#")
    return "#%02X%02X%02X" % tuple(
        round(int(x[i:i + 2], 16) * t + int(y[i:i + 2], 16) * (1 - t))
        for i in (0, 2, 4))


def _yorqinlik(rang: str) -> float:
    """WCAG relative luminance."""
    h = rang.lstrip("#")

    def kanal(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (kanal(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a: str, b: str) -> float:
    """WCAG kontrast nisbati (1.0 … 21.0).

    `ui_tekshir.py` shu bilan har uch rejimni tekshiradi. Muhim matn
    juftliklari 4.5:1 dan past bo'lsa test yiqiladi; yordamchi
    tokenlar (`matn3`, ogohlantirish ranglari) HTML'dan aynan
    olingani uchun ular faqat hisobotda ko'rsatiladi.
    """
    x, y = _yorqinlik(a), _yorqinlik(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def ustiga(rang: str) -> str:
    """Shu fon ustida o'qiladigan matn: oq yoki quyuq."""
    return "#141210" if _yorqinlik(rang) > 0.4 else "#FFFFFF"


def pul_rangi(qiymat: int) -> str:
    """Musbat = yashil (senga qaytadi), manfiy = qizil (sen berasan)."""
    if qiymat > 0:
        return R("yashil")
    if qiymat < 0:
        return R("qizil")
    return R("neytral")


# ── odam ranglari ────────────────────────────────────────────────────
# Odam rangi HECH QACHON yolg'iz ma'no tashimaydi — doim ism yonidagi
# nuqta (HTML: `.dot`, 8×8 px).

ODAM_RANG = ["#B85C2C", "#2F7D6D", "#6B5EA8",
             "#A8443F", "#3F6DA8", "#7D6A2C"]


def odam_rangi(kalit) -> str:
    """Odamning doimiy rangi — `id` yoki ism bo'yicha, barqaror."""
    n = len(ODAM_RANG)
    if isinstance(kalit, int):
        return ODAM_RANG[(kalit - 1) % n if kalit > 0 else 0]
    # `hash()` har ishga tushishda boshqacha — harflar yig'indisi barqaror
    return ODAM_RANG[sum(ord(c) for c in str(kalit)) % n]


# ── pul darajasi ─────────────────────────────────────────────────────
#
# `core.ledger` da ikkita alohida lug'at bor:
#   holat()        → qarzda | juda_kam | kam | yaxshi   (qarz ustun turadi)
#   pul_darajasi() → manfiy | juda_kam | kam | yaxshi   (faqat cho'ntak)
# Ikkalasi ham shu yerdan rang oladi, shuning uchun `manfiy` va `qarzda`
# bir xil qizilda.

_DARAJA = {
    "qarzda":   ("qizil", "qizil_fon", "qizil_fon_matn"),
    "manfiy":   ("qizil", "qizil_fon", "qizil_fon_matn"),
    "juda_kam": ("toq_sariq", "toq_sariq_fon", "toq_sariq_fon_matn"),
    "kam":      ("sariq_bar", "sariq_fon", "sariq_fon_matn"),
    "yaxshi":   ("yashil", "yashil_fon", "yashil_fon_matn"),
}

# Zinapoyaning to'rt bo'lagi (HTML `.ladder`): eni % va rangi
ZINAPOYA = [(12, "qizil"), (12, "toq_sariq"), (16, "sariq_bar"), (60, "yashil")]


def daraja_rangi(holat: str) -> tuple[str, str, str]:
    """`holat` → (asos rang, yumshoq fon, o'sha fon ustidagi matn)."""
    a, f, m = _DARAJA.get(holat, _DARAJA["yaxshi"])
    return R(a), R(f), R(m)


# ══════════════════════════════════════════════════════════ 3. o'lchovlar
#
# Hammasi HTML CSS'idan. Yangi qiymat o'ylab topilmaydi.

# qobiq
APPBAR_H = 54
STATUSBAR_H = 26
QOBIQ_CHET = 18                 # appbar/statusbar yon bo'shlig'i
MAZMUN_CHET = (18, 16, 18, 18)  # .content: chap, tep, o'ng, past
MAZMUN_ORALIQ = 12              # .content gap
MAZMUN_MAX = 1200               # .sect max-width

# karta
KARTA_PAD = (14, 12, 14, 12)    # .card padding: 12px 14px
KARTA_ORALIQ = 9                # .cardhead margin-bottom
B_KARTA = 10
B_QOBIQ = 12                    # .frame / .modal

# kiritish va tugma
MAYDON_H = 34
MAYDON_PAD = 10
B_MAYDON = 8
TUGMA_H = 34
TUGMA_PAD = 14
TUGMA_KICHIK_H = 28
TUGMA_KICHIK_PAD = 11

# segment
SEG_PAD = 3
SEG_ORALIQ = 2
B_SEG = 9
SEG_ICH_PAD = (13, 6)
B_SEG_ICH = 6

# jadval
QATOR_H = 36
JADVAL_PAD = 8
JADVAL_BOSH_PAD = (8, 6)

# nishon / chip / check
B_NISHON = 999
NISHON_PAD = (10, 4)
B_CHIP = 7
CHIP_PAD = (9, 5)
CHECK_OLCHAM = 16
B_CHECK = 4

# raqam kartasi
METRIC_PAD = (13, 11)
METRIC_MIN_EN = 150

# zinapoya
ZINAPOYA_H = 8
BELGI_EN = 3
BELGI_H = 14

# panel
STICKY_PAD = (14, 10)
SUBNAV_EN = 180
SUBNAV_PAD = (11, 7)
INNER_PAD = (12, 11)
B_INNER = 9

# oyna
OYNA_EN = 640
OYNA_BOSH_PAD = (16, 13)
OYNA_TANA_PAD = (16, 14)
OYNA_TANA_ORALIQ = 10
OYNA_OYOQ_PAD = (16, 12)

# umumiy
ORALIQ = 8                      # .row gap
ORALIQ_KARTA = 12               # .metrics / .cols2 gap
ORALIQ_BOLIM = 16               # .split gap

OYNA_MIN = (1000, 680)
OYNA_ASOS = (1200, 820)
TOR_CHEGARA = 1080              # shundan tor bo'lsa sarlavha yorlig'i yashirinadi


# ══════════════════════════════════════════════════════════ 4. shriftlar

FONT_PAPKA = Path(__file__).resolve().parent / "fonts"

_AFZAL = ("Inter", "Segoe UI Variable Text", "Segoe UI")
_OILA: str | None = None


def shriftlarni_yukla() -> str:
    """`ui/fonts/` dagi shriftlarni yuklaydi va oilani tanlaydi.

    Papka bo'sh bo'lsa tizimdagi eng yaxshi mavjud oilaga tushadi.
    Hech qachon xato bermaydi — shrift yo'qligi dasturning ochilmasligiga
    sabab bo'lmaydi. Nima ishlatilayotganini `shrift_oilasi()` aytadi.
    """
    global _OILA
    if FONT_PAPKA.is_dir():
        for fayl in sorted(FONT_PAPKA.glob("*")):
            if fayl.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(fayl))

    bor = set(QFontDatabase.families())
    for nom in _AFZAL:
        if nom in bor:
            _OILA = nom
            break
    else:
        # Font bazasi bo'sh bo'lishi mumkin (offscreen platformada shunday)
        _OILA = "Segoe UI"
    return _OILA


def shrift_oilasi() -> str:
    return _OILA or shriftlarni_yukla()


# Rol → (px, og'irlik, tabular raqammi). O'lchamlar HTML'dan, shu jumladan
# kasrlilari (11.5 / 12.5) — ular `setPointSizeF` orqali aniq beriladi.
ROLLAR = {
    "asos":         (13,   QFont.Normal,   False),  # body
    "pul":          (13,   QFont.Medium,   True),   # .pul
    "brand":        (14,   QFont.DemiBold, False),  # .brand
    "tab":          (13,   QFont.Normal,   False),  # .tab
    "tab_faol":     (13,   QFont.Medium,   False),  # .tab.on
    "bolim":        (13,   QFont.DemiBold, False),  # .cardhead .h
    "sarlavha":     (16,   QFont.DemiBold, False),  # .sect h2
    "oyna_bosh":    (14,   QFont.DemiBold, False),  # .modal .mh
    "jadval":       (12.5, QFont.Normal,   False),  # table
    "jadval_pul":   (12.5, QFont.Medium,   True),
    "jadval_bosh":  (11.5, QFont.Medium,   False),  # th
    "yorliq":       (11.5, QFont.Normal,   False),  # .t2 / .sub
    "maslahat":     (11.5, QFont.Normal,   False),  # .hint / .err
    "nishon":       (11.5, QFont.Medium,   False),  # .badge / .chip
    "tugma":        (13,   QFont.Medium,   False),  # .btn
    "tugma_kichik": (12,   QFont.Medium,   False),  # .btn.sm
    "segment":      (12.5, QFont.Normal,   False),  # .seg span
    "segment_faol": (12.5, QFont.Medium,   False),  # .seg span.on
    "raqam":        (19,   QFont.DemiBold, True),   # .metric .v
    "raqam_yorliq": (11.5, QFont.Normal,   False),  # .metric .l
    "raqam_izoh":   (11,   QFont.Normal,   False),  # .metric .s
    "holat_kichik": (11,   QFont.Normal,   False),  # .status .lbl
    "holat_katta":  (13,   QFont.DemiBold, True),   # .status .lbl b
    "satr":         (11.5, QFont.Normal,   False),  # .statusbar
    "havola":       (12.5, QFont.Normal,   False),  # .link
    "sumline":      (12,   QFont.Normal,   False),  # .sumline
}

_TNUM = QFont.Tag("tnum")      # DIQQAT: setFeature() satr qabul qilmaydi
_TNUM_BOR = True


def shrift(rol: str = "asos") -> QFont:
    """Rol bo'yicha shrift. Pul rollarida `tnum` yoqiladi.

    `tnum` — tabular raqamlar: 1 va 8 bir xil kenglikda, ustunlar daftar
    kabi tik turadi. QSS buni qila olmaydi, faqat `QFont`. Qt eski bo'lsa
    `setFeature` yo'q — bunda jimgina o'tkazib yuboriladi, chunki pul
    ustunlarining O'NGGA TEKISLANISHI baribir majburiy va u ishlaydi.

    O'lcham `setPointSizeF` bilan beriladi: HTML'da 11.5 va 12.5 px kabi
    kasr qiymatlar bor, `setPixelSize` esa faqat butun son oladi.
    """
    px, ogirlik, tabular = ROLLAR.get(rol, ROLLAR["asos"])
    f = QFont(shrift_oilasi())
    f.setPointSizeF(px * 0.75)          # 96 dpi: 1 px = 0.75 pt
    f.setWeight(ogirlik)
    if tabular and _TNUM_BOR:
        try:
            f.setFeature(_TNUM, 1)
        except Exception:                # noqa: BLE001 — eski Qt
            globals()["_TNUM_BOR"] = False
    return f


def olcham(rol: str = "asos") -> float:
    return ROLLAR.get(rol, ROLLAR["asos"])[0]


def px(rol: str = "asos") -> int:
    """QSS uchun butun songa yaxlitlangan o'lcham."""
    return round(olcham(rol))


# ══════════════════════════════════════════════════════════════ 5. QSS

def qss(t: dict | None = None) -> str:
    """Umumiy uslub. `t` berilmasa — joriy rejim.

    Funksiya, konstanta emas: rejim almashganda qayta chaqiriladi.
    """
    t = t if t is not None else TOKENLAR[_REJIM]
    oila = shrift_oilasi()
    return f"""
/* ── asos ──────────────────────────────────────────────────────── */
QWidget {{
    background: {t['fon']};
    color: {t['matn']};
    font-family: "{oila}";
    font-size: {px('asos')}px;
}}
QWidget#Shaffof {{ background: transparent; }}
QMainWindow, QDialog {{ background: {t['fon']}; }}

QToolTip {{
    background: {t['sirt']};
    color: {t['matn']};
    border: 1px solid {t['chiziq_kuchli']};
    border-radius: {B_MAYDON}px;
    padding: 6px 9px;
}}

QLabel {{ background: transparent; color: {t['matn']}; }}

/* ── karta va ramka ────────────────────────────────────────────── */
QFrame#Karta {{
    background: {t['sirt']};
    border: 1px solid {t['chiziq']};
    border-radius: {B_KARTA}px;
}}
QFrame#Ichki {{
    background: {t['sirt']};
    border: 1px solid {t['chiziq']};
    border-radius: {B_INNER}px;
}}
QFrame#Chiziq {{ background: {t['chiziq']}; border: none; max-height: 1px; }}

/* ── kiritish maydonlari ───────────────────────────────────────────
   DIQQAT: ::drop-down, ::down-arrow, ::up-button STILLANMAYDI —
   Qt o'sha zahoti standart chizishni to'xtatadi va strelka yo'qoladi. */
QLineEdit, QComboBox, QDateEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
    background: {t['sirt2']};
    color: {t['matn']};
    border: 1px solid {t['chiziq']};
    border-radius: {B_MAYDON}px;
    padding: 0 {MAYDON_PAD}px;
    min-height: {MAYDON_H - 2}px;
    selection-background-color: {t['aksent_tola']};
    selection-color: {t['aksent_ustida']};
}}
QPlainTextEdit, QTextEdit {{ padding: 7px {MAYDON_PAD}px; }}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover {{
    border-color: {t['chiziq_kuchli']};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {t['fokus']};
}}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
QSpinBox:disabled {{
    background: {t['fon']};
    color: {t['matn3']};
    border-color: {t['chiziq']};
}}
QLineEdit[xato="true"] {{ border: 1px solid {t['qizil']}; }}

QComboBox QAbstractItemView {{
    background: {t['sirt2']};
    color: {t['matn']};
    border: 1px solid {t['chiziq_kuchli']};
    border-radius: {B_MAYDON}px;
    padding: 4px;
    outline: none;
    selection-background-color: {t['sirt_tanlangan']};
    selection-color: {t['matn']};
}}

/* ── tugmalar ──────────────────────────────────────────────────── */
QPushButton {{
    background: transparent;
    color: {t['matn']};
    border: 1px solid {t['chiziq_kuchli']};
    border-radius: {B_MAYDON}px;
    padding: 0 {TUGMA_PAD}px;
    min-height: {TUGMA_H - 2}px;
    font-size: {px('tugma')}px;
    font-weight: 500;
}}
QPushButton:hover   {{ background: {t['sirt_hover']}; }}
QPushButton:pressed {{ background: {t['sirt_tanlangan']}; }}
QPushButton:focus   {{ border-color: {t['fokus']}; }}
QPushButton:disabled {{ color: {t['matn3']}; border-color: {t['chiziq']}; }}

QPushButton#Asosiy {{
    background: {t['aksent_tola']};
    color: {t['aksent_ustida']};
    border-color: {t['aksent_tola']};
}}
QPushButton#Asosiy:hover {{ background: {t['aksent_hover']};
                            border-color: {t['aksent_hover']}; }}
QPushButton#Asosiy:disabled {{ background: {t['chiziq']};
                               border-color: {t['chiziq']};
                               color: {t['matn3']}; }}

QPushButton#Aksent {{ color: {t['aksent']}; border-color: {t['aksent']}; }}
QPushButton#Xavfli {{ color: {t['qizil']}; border-color: {t['qizil']}; }}
QPushButton#Xavfli:hover {{ background: {t['qizil_fon']}; }}
QPushButton#Soya {{ border-color: transparent; color: {t['matn2']};
                    padding: 0 {TUGMA_KICHIK_PAD}px; }}
QPushButton#Soya:hover {{ background: {t['sirt_hover']};
                          border-color: transparent; color: {t['matn']}; }}

/* ── belgilash ─────────────────────────────────────────────────── */
QCheckBox, QRadioButton {{ background: transparent; spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: {CHECK_OLCHAM}px; height: {CHECK_OLCHAM}px;
}}
QCheckBox::indicator {{
    border: 1px solid {t['chiziq_kuchli']};
    border-radius: {B_CHECK}px;
    background: {t['sirt2']};
}}
QRadioButton::indicator {{
    border: 1px solid {t['chiziq_kuchli']};
    border-radius: {CHECK_OLCHAM // 2}px;
    background: {t['sirt2']};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {t['aksent']};
    border-color: {t['aksent']};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t['aksent']};
}}

/* ── jadval ────────────────────────────────────────────────────── */
QTableView, QTableWidget {{
    background: {t['sirt']};
    alternate-background-color: {t['sirt']};
    color: {t['matn']};
    border: none;
    gridline-color: transparent;
    outline: none;
    selection-background-color: {t['sirt_tanlangan']};
    selection-color: {t['matn']};
}}
QTableView::item, QTableWidget::item {{
    border: none;
    border-bottom: 1px solid {t['chiziq']};
    padding: 0 {JADVAL_PAD}px;
}}
QTableView::item:hover, QTableWidget::item:hover {{
    background: {t['sirt_hover']};
}}
QTableView::item:selected, QTableWidget::item:selected {{
    background: {t['sirt_tanlangan']};
    color: {t['matn']};
}}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {t['sirt']};
    color: {t['matn2']};
    border: none;
    border-bottom: 1px solid {t['chiziq_kuchli']};
    padding: 0 {JADVAL_PAD}px;
    font-size: {px('jadval_bosh')}px;
    font-weight: 500;
}}
QTableCornerButton::section {{ background: {t['sirt']}; border: none; }}

/* ── aylantirgich ──────────────────────────────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {t['chiziq_kuchli']};
    border-radius: 5px;
    min-height: 32px;
    min-width: 32px;
}}
QScrollBar::handle:hover {{ background: {t['neytral']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ── ro'yxat (YonSubNav) ───────────────────────────────────────── */
QListWidget {{
    background: transparent; border: none; outline: none;
    color: {t['matn2']};
}}
QListWidget::item {{
    padding: 0 {SUBNAV_PAD[0]}px;
    border-radius: {B_MAYDON}px;
}}
QListWidget::item:hover {{ background: {t['sirt_hover']}; }}
QListWidget::item:selected {{
    background: {t['aksent_fon']};
    color: {t['aksent_fon_matn']};
    font-weight: 500;
}}
"""


# Eski nom bilan chaqiruvlar buzilmasin (ko'rgazma va vidjetlar).
def STIL() -> str:                                   # noqa: N802
    """`qss()` ning eski nomi."""
    return qss()
