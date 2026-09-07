"""Jadval va daraja chizig'i.

Spetsifikatsiya §3.5, §3.6. Jadval uslubi bitta joyda turadi: sarlavha
KATTA HARF emas, zebra yo'q, qatorlar orasida soch-chiziq, pul ustunlari
o'ngga tekislangan va tabular.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import money
from ui import theme as T
from ui.widgets.asos import BoshHolat, _boyanadi, shaffof


class Jadval(QWidget):
    """Bitta umumiy uslubdagi jadval.

    Bo'sh bo'lsa o'rnida `BoshHolat` ko'rinadi — foydalanuvchi bo'm-bo'sh
    to'rtburchakka qarab «yuklanyaptimi yoki yozuv yo'qmi?» deb o'ylamaydi.

    Ikki marta bosish = tahrirlash. DIQQAT: pul yozadigan ekranlarda
    (Qarz → to'lanmagan bloklar) bu ULANMAYDI — tasodifan bosilib pul
    o'zgarib ketishi juda oson (§3.5, TZ §5.4).
    """

    tanlov_ozgardi = Signal()
    ikki_marta = Signal(object)          # qator id

    def __init__(self, ustunlar: list[str], pul_ustunlar: set[int] | None = None,
                 rangli_ustunlar: set[int] | None = None,
                 bosh_matn: str = "Bu oraliqda yozuv yo'q.",
                 kop_tanlash: bool = False, parent=None):
        super().__init__(parent)
        shaffof(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.pul_ustunlar = pul_ustunlar or set()
        self.rangli_ustunlar = rangli_ustunlar or set()

        self.j = QTableWidget(0, len(ustunlar))
        self.j.setHorizontalHeaderLabels(ustunlar)
        self.j.verticalHeader().setVisible(False)
        self.j.setShowGrid(False)
        self.j.setAlternatingRowColors(False)
        self.j.setWordWrap(False)
        self.j.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.j.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.j.setSelectionMode(QAbstractItemView.ExtendedSelection
                                if kop_tanlash
                                else QAbstractItemView.SingleSelection)
        self.j.horizontalHeader().setHighlightSections(False)
        self.j.horizontalHeader().setFixedHeight(T.QATOR_H)
        self.j.setFont(T.shrift("asos"))
        self.j.itemSelectionChanged.connect(self.tanlov_ozgardi)
        self.j.doubleClicked.connect(
            lambda *_: self.ikki_marta.emit(self.tanlangan_id()))
        v.addWidget(self.j)

        self.bosh = BoshHolat(bosh_matn)
        self.bosh.setVisible(False)
        v.addWidget(self.bosh)

        _boyanadi(self, self._boya)

    # ── ko'rinish ────────────────────────────────────────────────────

    def _boya(self) -> None:
        self.j.setFont(T.shrift("asos"))

    def kengliklar(self, *kengliklar: int) -> None:
        """0 — qolgan joyni egallaydi (elastik ustun)."""
        bosh = self.j.horizontalHeader()
        for i, k in enumerate(kengliklar):
            if i >= self.j.columnCount():
                break
            if k == 0:
                bosh.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                bosh.setSectionResizeMode(i, QHeaderView.Fixed)
                self.j.setColumnWidth(i, k)

    def balandlik(self, qator_soni: int) -> None:
        self.j.setMinimumHeight(T.QATOR_H * (qator_soni + 1) + 6)

    # ── to'ldirish ───────────────────────────────────────────────────

    def tuldir(self, qatorlar: list[list], idlar: list | None = None,
               belgilar: dict[int, str] | None = None) -> None:
        """Jadvalni to'ldiradi.

        `belgilar` — {qator raqami: daraja nomi}: o'sha qatorni xira
        qiladi (masalan «uyda bor» yoki to'langan blok).
        """
        self.j.setRowCount(0)
        bor = bool(qatorlar)
        self.j.setVisible(bor)
        self.bosh.setVisible(not bor)
        if not bor:
            return

        self.j.setRowCount(len(qatorlar))
        for r, qator in enumerate(qatorlar):
            self.j.setRowHeight(r, T.QATOR_H)
            for c, qiymat in enumerate(qator):
                pulmi = c in self.pul_ustunlar
                matn = money.fmt(qiymat) if pulmi and isinstance(qiymat, int) \
                    else ("" if qiymat is None else str(qiymat))
                it = QTableWidgetItem(matn)
                it.setFont(T.shrift("pul" if pulmi else "asos"))
                if pulmi:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if c in self.rangli_ustunlar and isinstance(qiymat, int):
                        it.setForeground(QColor(T.pul_rangi(qiymat)))
                else:
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if belgilar and r in belgilar:
                    it.setForeground(QColor(T.R("matn3")))
                if c == 0 and idlar and r < len(idlar):
                    it.setData(Qt.UserRole, idlar[r])
                self.j.setItem(r, c, it)

    # ── tanlov ───────────────────────────────────────────────────────

    def tanlangan_id(self):
        r = self.j.currentRow()
        if r < 0:
            return None
        it = self.j.item(r, 0)
        return it.data(Qt.UserRole) if it else None

    def tanlangan_idlar(self) -> list:
        idlar = []
        for r in sorted({i.row() for i in self.j.selectedIndexes()}):
            it = self.j.item(r, 0)
            if it is not None and it.data(Qt.UserRole) is not None:
                idlar.append(it.data(Qt.UserRole))
        return idlar

    def tanlovni_bekor(self) -> None:
        self.j.clearSelection()


# ══════════════════════════════════════════════════════════ daraja chizig'i

class DarajaChiziq(QWidget):
    """Pul darajasi zinapoyasi (§3.6).

    To'rt segmentli chiziq: qizil → to'q sariq → sariq → yashil. Ustida
    odamning `naqd` qiymati joylashgan nuqtada belgi.

    Ikkita alohida savolga javob beradi, chunki `core.ledger` da ham
    ikkita funksiya bor:
      * chiziq — `pul_darajasi()`: faqat cho'ntakdagi pul;
      * yonidagi nishon — `holat()`: qarz hammasidan ustun turadi.
    Qarzdor odam ham cho'ntagi bo'shashini ko'rishi kerak.
    """

    BALANDLIK = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.setFixedHeight(self.BALANDLIK)
        self.setMinimumWidth(120)
        self._ulush = 0.0
        self._daraja = "yaxshi"
        _boyanadi(self, self.update)

    def qoy(self, ulush: float, daraja: str) -> None:
        """`ulush` — 0..1 (eng ko'p puli borga nisbatan), `daraja` — rang."""
        self._ulush = max(0.0, min(1.0, float(ulush)))
        self._daraja = daraja
        self.update()

    def paintEvent(self, _hodisa):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        radius = self.BALANDLIK / 2

        # o'zan
        yol = QPainterPath()
        yol.addRoundedRect(QRectF(r), radius, radius)
        p.fillPath(yol, QColor(T.R("sirt_hover")))

        # to'ldirilgan qism
        asos, _, _ = T.daraja_rangi(self._daraja)
        en = r.width() * self._ulush
        if en > 0:
            tola = QPainterPath()
            tola.addRoundedRect(
                QRectF(0, 0, max(en, self.BALANDLIK), r.height()),
                radius, radius)
            p.fillPath(tola.intersected(yol), QColor(asos))
        p.end()
