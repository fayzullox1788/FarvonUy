"""«Yangi rasxod kategoriyalari» — ikonkalarga nom berish.

Ikonkalar NOMSIZ keladi (`core/kategoriya.py`). Foydalanuvchi ikonkaga
bosadi va nom yozadi — o'sha zahoti u rasxod kategoriyasi bo'ladi va
rasxod oynalaridagi «Kategoriya» tanlagichida ikonkasi bilan chiqadi.

Katakchalar BIR MARTA quriladi (200 ta), `yangila()` faqat
yozuv va ramkani o'zgartiradi: har nom berishda hammasini qayta qurish
sahifani sakratardi (CLAUDE.md, «Mayda o'zgarish uchun…»).
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QLayout,
                               QLineEdit, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from core import kategoriya
from ui.eski import theme
from ui.eski.dialogs import tasdiq, xato_koraset
from ui.eski.sahifa_asosiy import Sahifa, shaffof
from ui.eski.widgets import (Karta, Xabar, belgi_ikon, belgi_rasm, bolim, izoh,
                             qator, sarlavha, tugma)

USTUN = 8          # boshlang'ich; keyin eniga qarab `_joyla` o'zgartiradi
IKONKA = 50
KATAK = QSize(116, 104)


class NomDialog(QDialog):
    """Bitta ikonkaga nom berish / nomini o'zgartirish / olib tashlash."""

    def __init__(self, db, fayl: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.fayl = fayl
        joriy = kategoriya.nomlanganlar(db).get(fayl)
        self.setWindowTitle("Kategoriya nomi")
        self.setMinimumWidth(380)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)

        rasm = QLabel()
        rasm.setAlignment(Qt.AlignCenter)
        rasm.setPixmap(belgi_rasm(kategoriya.rasm_yoli(fayl), 88, rasm))
        v.addWidget(rasm)

        self.nom = QLineEdit(joriy["nom"] if joriy else "")
        self.nom.setPlaceholderText("masalan: Bozorlik")
        self.nom.returnPressed.connect(self._saqla)
        v.addWidget(self.nom)
        v.addWidget(izoh("Nom berilgach bu ikonka rasxod yozishda "
                         "kategoriya bo'lib chiqadi."))

        saqla = tugma("Saqlash", asosiy=True)
        bekor = tugma("Bekor")
        saqla.clicked.connect(self._saqla)
        bekor.clicked.connect(self.reject)
        olib = None
        if joriy:
            olib = tugma("Nomini olib tashlash", xavfli=True)
            olib.clicked.connect(self._olib_tashla)
        v.addWidget(qator(olib, None, bekor, saqla))

    def _saqla(self):
        try:
            kategoriya.nom_ber(self.db, self.fayl, self.nom.text())
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self.accept()

    def _olib_tashla(self):
        if tasdiq(self, "Ikonka yana nomsiz bo'ladi.\n\n"
                        "Oldin shu kategoriya bilan yozilgan rasxodlar "
                        "o'chmaydi. Davom etilsinmi?"):
            kategoriya.nomini_olib_tashla(self.db, self.fayl)
            self.accept()


class KategoriyaSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        self.tana.addWidget(qator(sarlavha("Iconlar"), None))
        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        karta = Karta("Ikonkaga bosing va nom bering")
        self.xulosa = izoh("")
        karta.qosh(self.xulosa)

        # Har skrinshot guruhi — o'z sarlavhasi («Shaxsiy», «Oziq-ovqat»…)
        # va o'z panjarasi. Sarlavha faqat GURUH nomi: ikonkaning o'ziga
        # nomni foydalanuvchi beradi.
        # Ustunlar soni eniga qarab o'zgaradi (`_joyla`): qat'iy son
        # kichik oynada gorizontal aylantirgich chiqarardi.
        self.quti = QWidget()
        shaffof(self.quti)
        vq = QVBoxLayout(self.quti)
        vq.setContentsMargins(0, 6, 0, 0)
        vq.setSpacing(10)
        # Qutining eni mazmundan EMAS, kartadan kelsin — aks holda 8
        # ustunlik panjara o'zining eng kam enini majburlab, oyna
        # torayganda ham qayta joylash uchun resize kelmasdi.
        vq.setSizeConstraint(QLayout.SetNoConstraint)
        self.quti.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.kataklar: dict[str, QToolButton] = {}
        self._guruhlar: list[tuple[QGridLayout, list[QToolButton]]] = []
        self.guruh_sarlavhalari: list[QLabel] = []
        for fayl in kategoriya.belgilar():
            g = kategoriya.guruh(fayl)
            if not self._guruhlar or self._guruhlar[-1][0].objectName() != g:
                panjara = QGridLayout()
                panjara.setObjectName(g)
                panjara.setSpacing(6)
                panjara.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                if self._guruhlar:
                    vq.addSpacing(14)
                bosh = bolim(kategoriya.guruh_nomi(g))
                self.guruh_sarlavhalari.append(bosh)
                vq.addWidget(bosh)
                vq.addLayout(panjara)
                self._guruhlar.append((panjara, []))
            k = QToolButton()
            k.setIcon(belgi_ikon(kategoriya.rasm_yoli(fayl)))
            k.setIconSize(QSize(IKONKA, IKONKA))
            k.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            k.setFixedSize(KATAK)
            k.setCursor(Qt.PointingHandCursor)
            k.clicked.connect(lambda _=False, f=fayl: self._och(f))
            self._guruhlar[-1][1].append(k)
            self.kataklar[fayl] = k
        self._ustun = 0
        self._joyla(USTUN)
        self.quti.installEventFilter(self)
        karta.qosh(self.quti)
        if not self.kataklar:
            karta.qosh(izoh("Ikonkalar topilmadi (belgilar papkasi bo'sh)."))
        self.tana.addWidget(karta)
        self.tana.addStretch(1)

    def _joyla(self, ustun: int):
        ustun = max(3, ustun)
        if ustun == self._ustun:
            return
        self._ustun = ustun
        for panjara, kataklar in self._guruhlar:
            for i, k in enumerate(kataklar):
                panjara.removeWidget(k)
                panjara.addWidget(k, i // ustun, i % ustun)

    def eventFilter(self, obj, hodisa):
        if obj is self.quti and hodisa.type() == QEvent.Resize:
            self._joyla(hodisa.size().width() // (KATAK.width() + 6))
        return super().eventFilter(obj, hodisa)

    def _och(self, fayl: str):
        if NomDialog(self.db, fayl, self).exec():
            self.yangila()
            joriy = kategoriya.nomlanganlar(self.db).get(fayl)
            self.xabar.korsat(
                f"✔ «{joriy['nom']}» kategoriyasi tayyor." if joriy
                else "Ikonka yana nomsiz.", "ok", 3000)

    def yangila(self):
        nomlar = kategoriya.nomlanganlar(self.db)
        oddiy = (f"QToolButton{{background:transparent;border:1px solid transparent;"
                 f"border-radius:{theme.R_ORTA}px;color:{theme.MATN};"
                 f"font-size:{theme.O_MAYDA}px;padding:4px;}}"
                 f"QToolButton:hover{{background:{theme.KARTA_ICH};"
                 f"border-color:{theme.CHIZIQ};}}")
        tanlangan = (f"QToolButton{{background:{theme.KOK_FON};"
                     f"border:2px solid {theme.KOK};border-radius:{theme.R_ORTA}px;"
                     f"color:{theme.MATN};font-size:{theme.O_MAYDA}px;"
                     f"font-weight:600;padding:3px;}}")
        for fayl, k in self.kataklar.items():
            t = nomlar.get(fayl)
            nom = t["nom"] if t else ""
            k.setText(k.fontMetrics().elidedText(nom, Qt.ElideRight,
                                                 KATAK.width() - 12))
            k.setToolTip(nom or "Nom berish uchun bosing")
            k.setStyleSheet(tanlangan if t else oddiy)
        n = len(nomlar)
        self.xulosa.setText(
            f"{len(self.kataklar)} ta ikonka · {n} tasiga nom berilgan"
            if n else f"{len(self.kataklar)} ta ikonka · hali hech biriga nom "
                      f"berilmagan")
