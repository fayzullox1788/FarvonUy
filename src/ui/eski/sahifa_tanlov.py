"""Bosh ekran — ikkita bo'lim: Moliya va Vazifalar.

Dastur shu ekrandan boshlanadi. Bu yerda yon menyu YO'Q: foydalanuvchi
avval qaysi ish bilan kelganini aytadi, keyin o'sha bo'limning o'z
menyusi ochiladi. Shuning uchun `Oyna` ni ikki qavat qilib qo'yilgan —
tashqi stekda tanlov, ichkarisida bo'lim qobig'i.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

import config
from ui.eski import theme
from ui.eski.sahifa_asosiy import shaffof


class _Karta(QFrame):
    """Bosiladigan bo'lim kartasi."""

    bosildi = Signal()

    def __init__(self, belgi: str, nom: str, izoh_matn: str,
                 havola: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TanlovKarta")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(330, 250)
        self._boya(False)

        ich = QVBoxLayout(self)
        ich.setContentsMargins(28, 26, 28, 24)
        ich.setSpacing(0)

        nishon = QLabel(belgi)
        nishon.setObjectName("TanlovNishon")
        nishon.setAlignment(Qt.AlignCenter)
        nishon.setFixedSize(56, 56)
        nishon.setStyleSheet(
            f"QLabel#TanlovNishon {{ background: {theme.KOK_FON};"
            f" color: {theme.KOK}; border-radius: {theme.R_ORTA + 4}px;"
            f" font-size: 26px; font-weight: 600; }}")
        ich.addWidget(nishon)
        ich.addSpacing(20)

        bosh = QLabel(nom)
        bosh.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-size:{theme.O_BOSH}px;font-weight:700;")
        ich.addWidget(bosh)
        ich.addSpacing(8)

        tavsif = QLabel(izoh_matn)
        tavsif.setWordWrap(True)
        tavsif.setStyleSheet(
            f"color:{theme.KUL};background:transparent;"
            f"font-size:{theme.O_ASOS}px;line-height:150%;")
        ich.addWidget(tavsif)
        ich.addStretch(1)

        self.havola = QLabel(f"{havola}  →")
        self.havola.setStyleSheet(
            f"color:{theme.KOK};background:transparent;"
            f"font-size:{theme.O_ORTA}px;font-weight:600;")
        ich.addWidget(self.havola)

    def _boya(self, ustida: bool):
        chegara = theme.KOK if ustida else theme.CHIZIQ
        self.setStyleSheet(
            f"QFrame#TanlovKarta {{ background: {theme.KARTA};"
            f" border: 1px solid {chegara};"
            f" border-radius: {theme.R_KARTA}px; }}")

    def enterEvent(self, hodisa):
        self._boya(True)
        super().enterEvent(hodisa)

    def leaveEvent(self, hodisa):
        self._boya(False)
        super().leaveEvent(hodisa)

    def mousePressEvent(self, hodisa):
        if hodisa.button() == Qt.LeftButton:
            self.bosildi.emit()
        super().mousePressEvent(hodisa)


class TanlovSahifa(QWidget):
    """«Bo'limni tanlang» ekrani."""

    bolim_tanlandi = Signal(str)      # "moliya" | "vazifalar"

    def __init__(self, oyna):
        super().__init__()
        self.oyna = oyna
        self.db = oyna.db
        shaffof(self)

        tashqi = QVBoxLayout(self)
        tashqi.setContentsMargins(40, 40, 40, 40)
        tashqi.addStretch(1)

        nishon = QLabel("BO'LIMNI TANLANG")
        nishon.setAlignment(Qt.AlignCenter)
        nishon.setStyleSheet(
            f"color:{theme.KOK};background:{theme.KOK_FON};"
            f"border-radius:{theme.R_ORTA}px;padding:8px 20px;"
            f"font-size:{theme.O_MIKRO}px;font-weight:700;"
            f"letter-spacing:1px;")
        nishon_qatori = QWidget()
        shaffof(nishon_qatori)
        nq = QHBoxLayout(nishon_qatori)
        nq.setContentsMargins(0, 0, 0, 0)
        nq.addStretch(1)
        nq.addWidget(nishon)
        nq.addStretch(1)
        tashqi.addWidget(nishon_qatori)
        tashqi.addSpacing(18)

        bosh = QLabel(f"{config.APP_NOM} ga xush kelibsiz")
        bosh.setAlignment(Qt.AlignCenter)
        bosh.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-size:40px;font-weight:700;")
        tashqi.addWidget(bosh)
        tashqi.addSpacing(6)

        self.pastki = QLabel()
        self.pastki.setAlignment(Qt.AlignCenter)
        self.pastki.setStyleSheet(
            f"color:{theme.KUL};background:transparent;"
            f"font-size:{theme.O_BOLIM}px;")
        tashqi.addWidget(self.pastki)
        tashqi.addSpacing(34)

        kartalar = QWidget()
        shaffof(kartalar)
        kq = QHBoxLayout(kartalar)
        kq.setContentsMargins(0, 0, 0, 0)
        kq.setSpacing(22)
        kq.addStretch(1)

        moliya = _Karta("◆", "Moliya",
                        "Kirim, rasxod, qarz, reja va hisobotlar — "
                        "uchalangizning pul hisobingiz.",
                        "Moliyaga o'tish")
        moliya.bosildi.connect(lambda: self.bolim_tanlandi.emit("moliya"))
        kq.addWidget(moliya)

        vazifalar = _Karta("▦", "Vazifalar",
                           "Haftalik kalendar: kim, qaysi kuni va soat "
                           "nechada qaysi uy ishini qiladi.",
                           "Vazifalarga o'tish")
        vazifalar.bosildi.connect(
            lambda: self.bolim_tanlandi.emit("vazifalar"))
        kq.addWidget(vazifalar)
        kq.addStretch(1)

        tashqi.addWidget(kartalar)
        tashqi.addStretch(2)

    def yangila(self):
        """Oyna sahifa almashtirganda shu chaqiriladi."""
        odamlar = [r["nom"] for r in self.db.q(
            "SELECT nom FROM odam WHERE faol=1 ORDER BY tartib, id")]
        if odamlar:
            self.pastki.setText(" · ".join(odamlar))
        else:
            self.pastki.setText("Sozlamalar bo'limidan odam qo'shing")
