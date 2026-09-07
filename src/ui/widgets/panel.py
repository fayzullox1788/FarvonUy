"""Xabar, panel va oyna komponentlari.

Spetsifikatsiya §3.7, §3.8, §3.9, §3.11, §3.12.

Bu yerdagi eng muhim g'oya — **«Qaytarish» tugmasi**. Yozuv yaratgan yoki
o'zgartirgan har muvaffaqiyat xabarida u bo'ladi: Ctrl+Z ni bilmagan odam
ham xatoni darhol tuzata oladi (§1.4).
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QVBoxLayout, QWidget)

import money
from ui import theme as T
from ui.widgets.asos import (_boyanadi, bolim, maslahat, matn as matn_yorliq,
                             shaffof, tugma, yorliq)

# xabar turi → (fon tokeni, matn tokeni, standart muddat ms)
TURLAR = {
    "ok":   ("yashil_fon", "yashil_fon_matn", 4000),
    "ogoh": ("sariq_fon", "sariq_fon_matn", 6000),
    "xato": ("qizil_fon", "qizil_fon_matn", 8000),
}


class Xabarcha(QFrame):
    """Bitta qalqib chiquvchi xabar (toast).

    Odatda `XabarQatori` orqali ishlatiladi — yolg'iz emas.
    """

    yopildi = Signal(object)

    def __init__(self, matn_: str, tur: str = "ok",
                 qaytarish=None, parent=None):
        super().__init__(parent)
        self._tur = tur if tur in TURLAR else "ok"
        v = QHBoxLayout(self)
        v.setContentsMargins(14, 10, 10, 10)
        v.setSpacing(12)

        self._yozuv = QLabel(matn_)
        self._yozuv.setFont(T.shrift("asos"))
        self._yozuv.setWordWrap(True)
        v.addWidget(self._yozuv, 1)

        if qaytarish is not None:
            b = tugma("Qaytarish", "soya", kichik=True)
            b.clicked.connect(qaytarish)
            b.clicked.connect(self._yop)
            v.addWidget(b)

        yopish = tugma("✕", "soya", kichik=True)
        yopish.setFixedWidth(28)
        yopish.clicked.connect(self._yop)
        v.addWidget(yopish)

        self.setMaximumWidth(520)
        _boyanadi(self, self._boya)

        muddat = TURLAR[self._tur][2]
        self._soat = QTimer(self)
        self._soat.setSingleShot(True)
        self._soat.timeout.connect(self._yop)
        self._soat.start(muddat)

    def _yop(self) -> None:
        self._soat.stop()
        self.yopildi.emit(self)
        self.deleteLater()

    def _boya(self) -> None:
        fon, matn_rang, _ = TURLAR[self._tur]
        self.setStyleSheet(
            f"QFrame {{ background:{T.R(fon)};"
            f" border:1px solid {T.R('chiziq')};"
            f" border-radius:{T.B_KARTA}px; }}")
        self._yozuv.setStyleSheet(
            f"background:transparent;color:{T.R(matn_rang)};")


class XabarQatori(QWidget):
    """Xabarchalar ustuni — o'ng yuqorida, ustma-ust emas, navbat bilan (§3.7)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(0, 0, 0, 0)
        self._v.setSpacing(8)
        self._v.setAlignment(Qt.AlignTop | Qt.AlignRight)

    def korsat(self, matn_: str, tur: str = "ok", qaytarish=None) -> Xabarcha:
        x = Xabarcha(matn_, tur, qaytarish, self)
        x.yopildi.connect(self._olib_tashla)
        self._v.addWidget(x, 0, Qt.AlignRight)
        return x

    def _olib_tashla(self, x) -> None:
        self._v.removeWidget(x)

    def tozala(self) -> None:
        while self._v.count():
            e = self._v.takeAt(0)
            if e.widget():
                e.widget().deleteLater()


class Banner(QFrame):
    """Sahifa yuqorisidagi doimiy ogohlantirish satri (§3.7).

    Xabarchadan farqi: o'zi yo'qolmaydi. Sabab yo'qolgandagina yashiriladi
    — audit buzilgan bo'lsa, u ekranda turishi kerak.
    """

    bosildi = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tur = "ogoh"
        v = QHBoxLayout(self)
        v.setContentsMargins(14, 9, 14, 9)
        v.setSpacing(10)
        self._yozuv = QLabel("")
        self._yozuv.setFont(T.shrift("asos"))
        self._yozuv.setWordWrap(True)
        v.addWidget(self._yozuv, 1)
        self.setVisible(False)
        self.setCursor(Qt.PointingHandCursor)
        _boyanadi(self, self._boya)

    def korsat(self, matn_: str, tur: str = "ogoh") -> None:
        self._tur = tur if tur in TURLAR else "ogoh"
        self._yozuv.setText(matn_)
        self._boya()
        self.setVisible(bool(matn_))

    def yashir(self) -> None:
        self.setVisible(False)

    def mouseReleaseEvent(self, hodisa):
        self.bosildi.emit()
        super().mouseReleaseEvent(hodisa)

    def _boya(self) -> None:
        fon, matn_rang, _ = TURLAR[self._tur]
        self.setStyleSheet(
            f"QFrame {{ background:{T.R(fon)};"
            f" border:1px solid {T.R('chiziq')};"
            f" border-radius:{T.B_KARTA}px; }}")
        self._yozuv.setStyleSheet(
            f"background:transparent;color:{T.R(matn_rang)};")


class YopishqoqPanel(QFrame):
    """Jadvalda qator tanlanganda pastdan chiqadigan amal paneli (§3.8).

    Ko'p-tanlov amallari FAQAT shu orqali bajariladi. Sabab: tanlangani
    va jami summasi ko'z oldida turadi, ya'ni «to'landi deb belgilash»
    tugmasini bosayotgan odam nimani tasdiqlayotganini biladi.
    """

    bekor = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QHBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(T.ORALIQ)

        self._yozuv = QLabel("")
        self._yozuv.setFont(T.shrift("asos"))
        v.addWidget(self._yozuv)
        v.addStretch(1)

        self._bekor = tugma("Bekor qilish", "soya", kichik=True)
        self._bekor.clicked.connect(self.bekor)
        v.addWidget(self._bekor)

        self._amallar = v
        self.setVisible(False)
        _boyanadi(self, self._boya)

    def amal_qosh(self, matn_: str, ish, tur: str = "asosiy"):
        b = tugma(matn_, tur, kichik=True)
        b.clicked.connect(ish)
        self._amallar.addWidget(b)
        return b

    def yangila(self, soni: int, jami: int | None = None,
                birlik: str = "qator") -> None:
        if soni <= 0:
            self.setVisible(False)
            return
        matn_ = f"{soni} ta {birlik} tanlandi"
        if jami is not None:
            matn_ += f"  ·  jami {money.fmt_som(jami)}"
        self._yozuv.setText(matn_)
        self.setVisible(True)

    def _boya(self) -> None:
        self.setStyleSheet(
            f"QFrame {{ background:{T.R('sirt_tanlangan')};"
            f" border:1px solid {T.R('aksent')};"
            f" border-radius:{T.B_KARTA}px; }}")
        self._yozuv.setStyleSheet(
            f"background:transparent;color:{T.R('matn')};font-weight:600;")


class YonSubNav(QWidget):
    """Sahifa ichidagi chap ustun + o'ngda tanlangan bo'lim (§3.9).

    Sozlamalar sahifasining asosi: 10 blokli uzun aylanma o'rniga
    bir vaqtda bitta bo'lim ko'rinadi (TZ §12.4 yechimi).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        v = QHBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(T.ORALIQ_KARTA)

        self.royxat = QListWidget()
        self.royxat.setFixedWidth(180)
        self.royxat.setFont(T.shrift("asos"))
        self.royxat.setFrameShape(QFrame.NoFrame)
        v.addWidget(self.royxat)

        self.stek = QStackedWidget()
        v.addWidget(self.stek, 1)

        self.royxat.currentRowChanged.connect(self.stek.setCurrentIndex)
        _boyanadi(self, self._boya)

    def bolim_qosh(self, nom: str, mazmun: QWidget) -> None:
        it = QListWidgetItem(nom)
        it.setSizeHint(it.sizeHint().expandedTo(
            it.sizeHint().__class__(0, T.QATOR_H)))
        self.royxat.addItem(it)
        self.stek.addWidget(mazmun)
        if self.royxat.count() == 1:
            self.royxat.setCurrentRow(0)

    def _boya(self) -> None:
        self.royxat.setStyleSheet(
            f"QListWidget {{ background:transparent; border:none;"
            f" outline:none; color:{T.R('matn2')}; }}"
            f"QListWidget::item {{ padding:0 12px;"
            f" border-radius:{T.B_MAYDON}px; }}"
            f"QListWidget::item:hover {{ background:{T.R('sirt_hover')}; }}"
            f"QListWidget::item:selected {{ background:{T.R('aksent_fon')};"
            f" color:{T.R('aksent_fon_matn')}; font-weight:600; }}")


class HolatSatri(QFrame):
    """Oynaning eng pastidagi 26 px satr (§3.12).

    Chapda — keyingi Ctrl+Z nima qilishi. Bu doim halol: redo yo'q bo'lsa
    Ctrl+Y haqida hech narsa va'da qilinmaydi (§13.2).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(T.STATUSBAR_H)
        v = QHBoxLayout(self)
        v.setContentsMargins(T.QOBIQ_CHET, 0, T.QOBIQ_CHET, 0)
        v.setSpacing(12)
        self._chap = QLabel("Tayyor")
        self._chap.setFont(T.shrift("maslahat"))
        self._ong = QLabel("")
        self._ong.setFont(T.shrift("maslahat"))
        v.addWidget(self._chap)
        v.addStretch(1)
        v.addWidget(self._ong)
        self._vaqtli = QTimer(self)
        self._vaqtli.setSingleShot(True)
        self._vaqtli.timeout.connect(lambda: self.qoy(self._doimiy))
        self._doimiy = "Tayyor"
        _boyanadi(self, self._boya)

    def qoy(self, matn_: str) -> None:
        self._doimiy = matn_
        self._chap.setText(matn_)

    def vaqtli(self, matn_: str, ms: int = 2500) -> None:
        self._chap.setText(matn_)
        self._vaqtli.start(ms)

    def ong_qoy(self, matn_: str) -> None:
        self._ong.setText(matn_)

    def _boya(self) -> None:
        self.setStyleSheet(
            f"QFrame {{ background:{T.R('sirt')};"
            f" border-top:1px solid {T.R('chiziq')}; }}")
        for e in (self._chap, self._ong):
            e.setStyleSheet(f"background:transparent;color:{T.R('matn3')};")


class Oyna(QDialog):
    """Modal oynaning asosi (§3.11).

    Pastda o'ngga tekislangan tugmalar: `[Bekor] [Saqlash]`. Esc = Bekor.
    """

    def __init__(self, sarlavha_matn: str, en: int = 520, parent=None):
        super().__init__(parent)
        self.setWindowTitle(sarlavha_matn)
        self.setMinimumWidth(en)
        self.setModal(True)

        self._tashqi = QVBoxLayout(self)
        self._tashqi.setContentsMargins(T.QOBIQ_CHET, 18,
                                        T.QOBIQ_CHET, 16)
        self._tashqi.setSpacing(14)

        self.bosh = bolim(sarlavha_matn)
        self._tashqi.addWidget(self.bosh)

        self.tana = QVBoxLayout()
        self.tana.setSpacing(12)
        self._tashqi.addLayout(self.tana)

        self.xato_yozuv = maslahat("")
        self.xato_yozuv.setVisible(False)
        self._tashqi.addWidget(self.xato_yozuv)

        self.bekor_tugma = tugma("Bekor", "oddiy")
        self.saqla_tugma = tugma("Saqlash", "asosiy")
        self.bekor_tugma.clicked.connect(self.reject)
        self.saqla_tugma.clicked.connect(self._saqla_bosildi)

        past = QHBoxLayout()
        past.addStretch(1)
        past.setSpacing(T.ORALIQ)
        past.addWidget(self.bekor_tugma)
        past.addWidget(self.saqla_tugma)
        self._tashqi.addLayout(past)

        _boyanadi(self, self._boya)

    def qosh(self, w) -> None:
        self.tana.addWidget(w) if isinstance(w, QWidget) else self.tana.addLayout(w)

    def xato(self, matn_: str) -> None:
        """Xatoni oynaning ichida ko'rsatadi — alohida oyna ochmasdan."""
        self.xato_yozuv.setText(matn_)
        self.xato_yozuv.setVisible(bool(matn_))
        if matn_:
            self.xato_yozuv.setStyleSheet(
                f"background:transparent;color:{T.R('qizil')};")

    def saqla(self) -> bool:
        """Vorislar qayta yozadi. `True` qaytarsa oyna yopiladi."""
        return True

    def _saqla_bosildi(self) -> None:
        self.xato("")
        try:
            if self.saqla():
                self.accept()
        except Exception as e:                       # noqa: BLE001
            self.xato(str(e))

    def _boya(self) -> None:
        self.setStyleSheet(f"QDialog {{ background:{T.R('fon')}; }}")


def tasdiq(ota, savol: str, ha_matn: str = "Ha", xavflimi: bool = False,
           tafsilot: str = "") -> bool:
    """Tasdiq oynasi (§3.11).

    Standart javob DOIM «Yo'q» — tasodifan Enter bosilishi pul
    o'zgartirmasin. Xavfli amallarda «Ha» tugmasi qizil.
    """
    o = Oyna("Tasdiqlang", 460, ota)
    o.bosh.setText("Tasdiqlang")
    o.qosh(matn_yorliq(savol))
    if tafsilot:
        o.qosh(maslahat(tafsilot))
    o.saqla_tugma.setText(ha_matn)
    o.bekor_tugma.setText("Yo'q")
    if xavflimi:
        o.saqla_tugma.setObjectName("Xavfli")
    o.bekor_tugma.setDefault(True)
    o.bekor_tugma.setFocus()
    return bool(o.exec())
