"""Asosiy komponentlar: tugma, karta, nishon, yorliq.

Spetsifikatsiya §3.1, §3.4, §3.6, §3.10. Ekranlar faqat shu yerdagi
bo'laklardan yig'iladi — «bir martalik» vidjet yozilmaydi.

Rang har doim `theme.R(...)` dan olinadi va rejim almashganda widget
o'zini qayta bo'yaydi (`_boyanadi` yordamchisi shunga ulaydi).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from shiboken6 import isValid

import money
from ui import theme as T


# ══════════════════════════════════════════════════════════ yordamchilar

def shaffof(w: QWidget) -> QWidget:
    """Fonsiz konteyner.

    DIQQAT: oddiy `setStyleSheet("background:transparent")` Qt'da BUTUN
    avlodga tarqaladi va kartalar, tugmalar fonini ham o'chiradi. Nomli
    selektor bilan yozilsa — faqat shu widgetga tegadi.
    """
    w.setObjectName("Shaffof")
    return w


def _boyanadi(w: QWidget, boya) -> None:
    """Widgetni rejim almashganda o'zini qayta bo'yashga ulaydi.

    Eski koddagi `qayta_boya(ildiz)` butun daraxt bo'ylab yurar edi;
    bu yerda har widget o'ziga javob beradi.

    DIQQAT — ikkita himoya bor va ikkalasi ham shart:

    1.  `isValid(w)` tekshiruvi. Global signalga ulangan **lambda** Qt
        uchun egasiz: widget o'chsa ham ulanish qoladi va keyingi rejim
        almashuvida «Internal C++ object already deleted» beradi.
        (Qt faqat qabul qiluvchi QObject ning BOG'LANGAN METODIga
        ulanganda o'zi uzadi — yopilma bunga kirmaydi.)
    2.  `destroyed` da uzish — o'lik ulanishlar to'planib qolmasin.
    """
    boya()

    def qayta(_=None):
        if isValid(w):
            boya()

    T.XABARCHI.ozgardi.connect(qayta)

    def uzish(*_):
        try:
            T.XABARCHI.ozgardi.disconnect(qayta)
        except (RuntimeError, TypeError):
            pass

    w.destroyed.connect(uzish)


# ══════════════════════════════════════════════════════════════ yorliqlar

def _yorliq(matn: str, rol: str, nom: str = "", rang_token: str = "matn") -> QLabel:
    e = QLabel(matn)
    if nom:
        e.setObjectName(nom)
    e.setFont(T.shrift(rol))
    _boyanadi(e, lambda: e.setStyleSheet(
        f"background:transparent;color:{T.R(rang_token)};"))
    return e


def sarlavha(matn: str) -> QLabel:
    """Sahifa sarlavhasi — 20 px."""
    return _yorliq(matn, "sarlavha", "Sarlavha")


def bolim(matn: str) -> QLabel:
    """Bo'lim sarlavhasi — 15 px."""
    return _yorliq(matn, "bolim", "Bolim")


def yorliq(matn: str) -> QLabel:
    """Ikkinchi darajali yozuv — 12 px."""
    return _yorliq(matn, "yorliq", "Yorliq", "matn2")


def maslahat(matn: str) -> QLabel:
    """Yordamchi maslahat — 11 px, xira."""
    e = _yorliq(matn, "maslahat", "Maslahat", "matn3")
    e.setWordWrap(True)
    return e


def matn(matn_: str) -> QLabel:
    """Oddiy matn — 13 px."""
    return _yorliq(matn_, "asos")


class PulYorliq(QLabel):
    """Pul raqami — tabular, kerak bo'lsa semantik rangda.

    `rangli=True` bo'lsa musbat yashil, manfiy qizil (§7.7). Bu faqat
    qarz/sof kabi yo'nalishi bor raqamlar uchun — oddiy summa neytral
    qoladi, aks holda butun jadval yashil-qizil bo'lib ketadi.
    """

    def __init__(self, qiymat: int = 0, rol: str = "pul",
                 rangli: bool = False, belgi: bool = False, parent=None):
        super().__init__(parent)
        self._qiymat = int(qiymat)
        self._rol, self._rangli, self._belgi = rol, rangli, belgi
        self.setFont(T.shrift(rol))
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        _boyanadi(self, self._boya)

    def qoy(self, qiymat: int) -> None:
        self._qiymat = int(qiymat)
        self._boya()

    def _boya(self) -> None:
        self.setFont(T.shrift(self._rol))
        self.setText(money.fmt(self._qiymat, self._belgi))
        rang = T.pul_rangi(self._qiymat) if self._rangli else T.R("matn")
        self.setStyleSheet(f"background:transparent;color:{rang};")


def chiziq() -> QFrame:
    """Nozik ajratuvchi."""
    c = QFrame()
    c.setObjectName("Chiziq")
    c.setFixedHeight(1)
    _boyanadi(c, lambda: c.setStyleSheet(
        f"background:{T.R('chiziq')};border:none;"))
    return c


def kengaytirgich() -> QWidget:
    """Qatorda bo'sh joyni egallaydigan bo'shliq."""
    w = shaffof(QWidget())
    w.setSizePolicy(w.sizePolicy().horizontalPolicy().Expanding,
                    w.sizePolicy().verticalPolicy().Preferred)
    return w


def qator(*bolaklar, oraliq: int = T.ORALIQ) -> QWidget:
    """Gorizontal qator.

    `None` — cho'ziladigan bo'shliq, `str` — oddiy yorliq, qolgani widget.
    """
    q = shaffof(QWidget())
    v = QHBoxLayout(q)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(oraliq)
    for b in bolaklar:
        if b is None:
            v.addStretch(1)
        elif isinstance(b, str):
            v.addWidget(yorliq(b))
        else:
            v.addWidget(b)
    return q


def ustun(*bolaklar, oraliq: int = T.ORALIQ) -> QWidget:
    """Vertikal ustun — `qator()` bilan bir xil qoidalar."""
    q = shaffof(QWidget())
    v = QVBoxLayout(q)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(oraliq)
    for b in bolaklar:
        if b is None:
            v.addStretch(1)
        elif isinstance(b, str):
            v.addWidget(yorliq(b))
        else:
            v.addWidget(b)
    return q


# ══════════════════════════════════════════════════════════════ tugmalar

TURLAR = {"asosiy": "Asosiy", "oddiy": "", "xavfli": "Xavfli", "soya": "Soya"}


def tugma(matn_: str, tur: str = "oddiy", kichik: bool = False) -> QPushButton:
    """Tugma. Uslub QSS'dan `objectName` orqali keladi.

    Qoida (§3.1): bitta ko'rinishda BITTA `asosiy` tugma bo'ladi —
    ekrandagi bosh amal. Qolgani `oddiy`. O'chirish va qaytarilmas
    amallar `xavfli`, jadval ichidagi maydalar `soya`.
    """
    if tur not in TURLAR:
        raise ValueError(f"noma'lum tugma turi: {tur!r} "
                         f"({', '.join(TURLAR)})")
    b = QPushButton(matn_)
    if TURLAR[tur]:
        b.setObjectName(TURLAR[tur])
    b.setFont(T.shrift("tugma"))
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(T.TUGMA_KICHIK_H if kichik else T.TUGMA_H)
    return b


# ══════════════════════════════════════════════════════════════ kartalar

class Karta(QFrame):
    """Mustaqil blok: `sirt` fon, nozik hoshiya, 10 px burchak."""

    def __init__(self, sarlavha_matn: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Karta")
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(*T.KARTA_PAD)
        self._v.setSpacing(T.KARTA_ORALIQ)
        self.bosh: QLabel | None = None
        if sarlavha_matn:
            self.bosh = bolim(sarlavha_matn)
            self._v.addWidget(self.bosh)

    def qosh(self, w) -> None:
        self._v.addWidget(w) if isinstance(w, QWidget) else self._v.addLayout(w)

    def sarlavha_qoy(self, matn_: str) -> None:
        if self.bosh is not None:
            self.bosh.setText(matn_)


class RaqamKarta(QFrame):
    """Yorliq + katta raqam + izoh. 2–5 tasi bir qatorda, teng enlikda."""

    def __init__(self, yorliq_matn: str, qiymat: int = 0, izoh: str = "",
                 rangli: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("Karta")
        v = QVBoxLayout(self)
        v.setContentsMargins(T.METRIC_PAD[0], T.METRIC_PAD[1],
                             T.METRIC_PAD[0], T.METRIC_PAD[1])
        v.setSpacing(3)

        self._yorliq = yorliq(yorliq_matn)
        self._son = PulYorliq(qiymat, "raqam", rangli=rangli)
        self._son.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._izoh = maslahat(izoh)

        v.addWidget(self._yorliq)
        v.addWidget(self._son)
        v.addWidget(self._izoh)
        self._izoh.setVisible(bool(izoh))

    def qoy(self, qiymat: int, izoh: str | None = None) -> None:
        self._son.qoy(qiymat)
        if izoh is not None:
            self._izoh.setText(izoh)
            self._izoh.setVisible(bool(izoh))


# ══════════════════════════════════════════════════════════ nishon / holat

class Nishon(QLabel):
    """Pill shaklidagi holat yorlig'i: rangli fon + o'sha oilaning to'q matni.

    Rang HECH QACHON yolg'iz ma'no tashimaydi — nishonning ichida doim
    matn bor (§1.3).
    """

    # daraja nomi → (fon tokeni, matn tokeni)
    OILALAR = {
        "ok":      ("yashil_fon", "yashil_fon_matn"),
        "xato":    ("qizil_fon", "qizil_fon_matn"),
        "ogoh":    ("sariq_fon", "sariq_fon_matn"),
        "diqqat":  ("toq_sariq_fon", "toq_sariq_fon_matn"),
        "aksent":  ("aksent_fon", "aksent_fon_matn"),
        "neytral": ("sirt_hover", "matn2"),
    }

    def __init__(self, matn_: str = "", tur: str = "neytral", parent=None):
        super().__init__(parent)
        self._tur = tur
        self.setFont(T.shrift("yorliq"))
        self.setAlignment(Qt.AlignCenter)
        self.setText(matn_)
        _boyanadi(self, self._boya)

    def qoy(self, matn_: str, tur: str | None = None) -> None:
        self.setText(matn_)
        if tur:
            self._tur = tur
        self._boya()

    def daraja_qoy(self, holat: str, matn_: str | None = None) -> None:
        """`core.ledger` darajasi bo'yicha: qarzda/manfiy/juda_kam/kam/yaxshi."""
        _, fon, matn_rang = T.daraja_rangi(holat)
        self.setText(matn_ if matn_ is not None else holat.replace("_", " "))
        self.setStyleSheet(
            f"background:{fon};color:{matn_rang};"
            f"border-radius:9px;padding:3px 10px;")
        self._tur = None          # daraja rangi qo'lda qo'yildi

    def _boya(self) -> None:
        if self._tur is None:
            return
        fon, matn_rang = self.OILALAR.get(self._tur, self.OILALAR["neytral"])
        self.setStyleSheet(
            f"background:{T.R(fon)};color:{T.R(matn_rang)};"
            f"border-radius:9px;padding:3px 10px;")


class BoshHolat(QWidget):
    """Bo'sh ro'yxat o'rnida: bitta jumla va kerak bo'lsa bitta tugma."""

    def __init__(self, matn_: str, tugma_matn: str = "", parent=None):
        super().__init__(parent)
        shaffof(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 22, 0, 22)
        v.setSpacing(10)
        v.setAlignment(Qt.AlignCenter)

        e = QLabel(matn_)
        e.setFont(T.shrift("asos"))
        e.setAlignment(Qt.AlignCenter)
        e.setWordWrap(True)
        _boyanadi(e, lambda: e.setStyleSheet(
            f"background:transparent;color:{T.R('matn2')};"))
        v.addWidget(e)

        self.tugma: QPushButton | None = None
        if tugma_matn:
            self.tugma = tugma(tugma_matn, "oddiy")
            v.addWidget(self.tugma, 0, Qt.AlignCenter)
