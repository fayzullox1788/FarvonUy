"""Kiritish maydonlari va tanlagichlar.

Spetsifikatsiya §3.2, §3.3. Har bir maydon o'zining xato holatini o'zi
ko'rsatadi — dialog «Saqlash» bosilgunicha kutmaydi.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QVBoxLayout, QWidget)

import money
from ui import theme as T
from ui.widgets.asos import maslahat, shaffof, tugma


# ══════════════════════════════════════════════════════════════ matn

class MatnMaydon(QLineEdit):
    """Oddiy matn. Placeholder — haqiqiy misol, «matn kiriting» emas."""

    def __init__(self, ornak: str = "", parent=None):
        super().__init__(parent)
        self.setFont(T.shrift("asos"))
        self.setPlaceholderText(ornak)
        self.setMinimumHeight(T.MAYDON_H)


# ══════════════════════════════════════════════════════════════ pul

class PulMaydon(QWidget):
    """Pul maydoni: yozayotganda o'zi guruhlaydi, aqlli parse qiladi.

    `money.parse()` tushunadigan hamma shaklni qabul qiladi — `1559k`,
    `1,5 mln`, `1559 ming`, `1.559.000`. Ichki qiymat HAR DOIM butun son.

    Noto'g'ri matn kiritilsa hoshiya qizil bo'ladi va pastida xato
    yozuvi chiqadi (§3.2) — foydalanuvchi «Saqlash» bosgandan keyin
    emas, o'sha zahoti biladi.
    """

    ozgardi = Signal(int)
    qaytdi = Signal()          # Enter bosildi

    def __init__(self, qiymat: int = 0, parent=None):
        super().__init__(parent)
        shaffof(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        self.maydon = QLineEdit()
        self.maydon.setFont(T.shrift("pul"))
        self.maydon.setAlignment(Qt.AlignRight)
        self.maydon.setPlaceholderText("0")
        self.maydon.setMinimumHeight(T.MAYDON_H)
        v.addWidget(self.maydon)

        self._xato = maslahat("")
        self._xato.setVisible(False)
        v.addWidget(self._xato)

        self._ichkarida = False
        self.maydon.textChanged.connect(self._matn_ozgardi)
        self.maydon.returnPressed.connect(self.qaytdi)
        if qiymat:
            self.qoy(qiymat)

    # ── qiymat ───────────────────────────────────────────────────────

    def qiymat(self) -> int:
        try:
            return money.parse(self.maydon.text())
        except ValueError:
            return 0

    def qoy(self, qiymat: int) -> None:
        self._ichkarida = True
        self.maydon.setText(money.fmt(int(qiymat)) if qiymat else "")
        self._ichkarida = False
        self._xato_qoy("")

    def tozala(self) -> None:
        self.qoy(0)

    def togrimi(self) -> bool:
        t = self.maydon.text().strip()
        if not t:
            return True
        try:
            money.parse(t)
            return True
        except ValueError:
            return False

    def setFocus(self) -> None:                      # noqa: N802 (Qt nomi)
        self.maydon.setFocus()

    # ── ichki ────────────────────────────────────────────────────────

    def _matn_ozgardi(self, t: str) -> None:
        if self._ichkarida:
            return
        xom = t.strip()
        if not xom:
            self._xato_qoy("")
            self.ozgardi.emit(0)
            return
        try:
            son = money.parse(xom)
        except ValueError:
            self._xato_qoy("Bu pul emas — masalan 250 000 yoki 250k")
            return

        self._xato_qoy("")
        # Faqat sof raqam yozilayotganda qayta formatlaymiz. «1,5 mln» kabi
        # matnni yozib bo'lgunicha almashtirsak, foydalanuvchi yozayotgan
        # narsa qo'lidan tortib olinadi.
        if all(c.isdigit() or c in " " for c in xom):
            yangi = money.fmt(son)
            if yangi != xom:
                joy = self.maydon.cursorPosition() + (len(yangi) - len(xom))
                self._ichkarida = True
                self.maydon.setText(yangi)
                self.maydon.setCursorPosition(max(0, min(len(yangi), joy)))
                self._ichkarida = False
        self.ozgardi.emit(son)

    def _xato_qoy(self, matn_: str) -> None:
        self._xato.setText(matn_)
        self._xato.setVisible(bool(matn_))
        # QSS `QLineEdit[xato="true"]` ni tanlaydi — xususiyat o'zgargach
        # uslubni qayta hisoblash kerak.
        self.maydon.setProperty("xato", "true" if matn_ else "false")
        self.maydon.style().unpolish(self.maydon)
        self.maydon.style().polish(self.maydon)


# ══════════════════════════════════════════════════════════════ sana

class SanaMaydon(QDateEdit):
    """`31.12.2026` ko'rinishida, kalendar tugmasi bilan."""

    def __init__(self, sana: str | None = None, parent=None):
        super().__init__(parent)
        self.setFont(T.shrift("asos"))
        self.setDisplayFormat("dd.MM.yyyy")
        self.setCalendarPopup(True)
        self.setMinimumHeight(T.MAYDON_H)
        self.qoy(sana)

    def qoy(self, sana: str | None) -> None:
        d = date.fromisoformat(sana[:10]) if sana else date.today()
        self.setDate(QDate(d.year, d.month, d.day))

    def iso(self) -> str:
        q = self.date()
        return f"{q.year():04d}-{q.month():02d}-{q.day():02d}"


class OraliqTanlagich(QWidget):
    """Ikki sana + tez tugmalar. Har ekranda bir xil komponent (§3.2)."""

    ozgardi = Signal(str, str)

    TEZ = [("Shu hafta", "hafta"), ("Shu oy", "oy"),
           ("60 kun", "60"), ("Hammasi", "hammasi")]

    def __init__(self, dan: str | None = None, gacha: str | None = None,
                 parent=None):
        super().__init__(parent)
        shaffof(self)
        v = QHBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(T.ORALIQ)

        self.dan = SanaMaydon(dan)
        self.gacha = SanaMaydon(gacha)
        self.dan.setFixedWidth(120)
        self.gacha.setFixedWidth(120)
        self.dan.dateChanged.connect(self._xabar)
        self.gacha.dateChanged.connect(self._xabar)

        from ui.widgets.asos import yorliq
        v.addWidget(yorliq("Dan:"))
        v.addWidget(self.dan)
        v.addWidget(yorliq("Gacha:"))
        v.addWidget(self.gacha)
        for matn_, kalit in self.TEZ:
            b = tugma(matn_, "soya", kichik=True)
            b.clicked.connect(lambda _=None, k=kalit: self.tez(k))
            v.addWidget(b)
        v.addStretch(1)

    def tez(self, kalit: str) -> None:
        from core import plan
        if kalit == "hafta":
            a, b = plan.hafta_boshi(), plan.hafta_oxiri()
        elif kalit == "oy":
            a, b = plan.oy_boshi(), plan.oy_oxiri()
        elif kalit == "60":
            from datetime import timedelta
            a = (date.today() - timedelta(days=60)).isoformat()
            b = date.today().isoformat()
        else:                                    # hammasi
            a, b = "2000-01-01", date.today().isoformat()
        self.qoy(a, b)

    def qoy(self, dan: str, gacha: str) -> None:
        self.dan.blockSignals(True)
        self.gacha.blockSignals(True)
        self.dan.qoy(dan)
        self.gacha.qoy(gacha)
        self.dan.blockSignals(False)
        self.gacha.blockSignals(False)
        self._xabar()

    def oraliq(self) -> tuple[str, str]:
        return self.dan.iso(), self.gacha.iso()

    def _xabar(self) -> None:
        self.ozgardi.emit(*self.oraliq())


# ══════════════════════════════════════════════════════════ tanlagichlar

class Tanlagich(QComboBox):
    """Ro'yxatdan tanlash uchun asos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(T.shrift("asos"))
        self.setMinimumHeight(T.MAYDON_H)

    def qiymat(self):
        return self.currentData()

    def tanla(self, qiymat) -> None:
        i = self.findData(qiymat)
        if i >= 0:
            self.setCurrentIndex(i)


class OdamTanlagich(Tanlagich):
    """Odamlar ro'yxati — ism oldida rang nuqtasi (§3.2).

    Nuqta bezak emas: bir odam butun dasturda bir xil rangda ko'rinadi,
    shuning uchun jadvaldagi rangli nuqta bilan bu ro'yxat bir tilda
    gapiradi. Lekin rang YOLG'IZ ishlatilmaydi — yonida doim ism bor.
    """

    def __init__(self, db, hammasi: bool = False, parent=None):
        super().__init__(parent)
        self.db = db
        self.yangila(hammasi)

    def yangila(self, hammasi: bool = False) -> None:
        eski = self.currentData()
        self.clear()
        if hammasi:
            self.addItem("Hammasi", None)
        for r in self.db.q(
                "SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id"):
            self.addItem(f"●  {r['nom']}", r["id"])
            self.setItemData(self.count() - 1,
                             T.odam_rangi(r["id"]), Qt.ForegroundRole)
        if eski is not None:
            self.tanla(eski)

    def odam_id(self):
        return self.currentData()


class TuriTanlagich(Tanlagich):
    """Kategoriyalar — belgisi (emoji) bilan."""

    def __init__(self, db, hammasi: bool = False, parent=None):
        super().__init__(parent)
        self.db = db
        self.yangila(hammasi)

    def yangila(self, hammasi: bool = False) -> None:
        eski = self.currentData()
        self.clear()
        if hammasi:
            self.addItem("Hamma kategoriya", None)
        else:
            self.addItem("— kategoriyasiz —", None)
        for r in self.db.q(
                "SELECT id, nom, belgi FROM turi WHERE faol=1 ORDER BY tartib"):
            self.addItem(f"{r['belgi']} {r['nom']}".strip(), r["id"])
        if eski is not None:
            self.tanla(eski)

    def turi_id(self):
        return self.currentData()


# ══════════════════════════════════════════════════════════ segment tugma

class SegmentTugma(QWidget):
    """Bir qatorda 2–4 variant, bittasi tanlangan (§3.3).

    Ishlatiladi: rasxod turi, Daftar rejimi, bo'lish usuli, odam tanlash.
    Klaviatura: ←/→ bilan almashadi — sichqoncha majburiy emas (§1.1).
    """

    tanlandi = Signal(object)

    def __init__(self, variantlar: list[tuple[object, str]],
                 joriy=None, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.setFocusPolicy(Qt.StrongFocus)
        v = QHBoxLayout(self)
        v.setContentsMargins(3, 3, 3, 3)
        v.setSpacing(3)

        self._tugmalar: list[QPushButton] = []
        self._kalitlar: list[object] = []
        for kalit, matn_ in variantlar:
            b = QPushButton(matn_)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(T.shrift("tugma"))
            b.setMinimumHeight(T.TUGMA_KICHIK_H)
            b.clicked.connect(lambda _=None, k=kalit: self.qoy(k))
            v.addWidget(b)
            self._tugmalar.append(b)
            self._kalitlar.append(kalit)

        self._joriy = joriy if joriy is not None else (
            self._kalitlar[0] if self._kalitlar else None)
        from ui.widgets.asos import _boyanadi
        _boyanadi(self, self._boya)

    # ── holat ────────────────────────────────────────────────────────

    def qiymat(self):
        return self._joriy

    def qoy(self, kalit, xabar: bool = True) -> None:
        if kalit not in self._kalitlar:
            return
        ozgardi = kalit != self._joriy
        self._joriy = kalit
        self._boya()
        if xabar and ozgardi:
            self.tanlandi.emit(kalit)

    def keyPressEvent(self, hodisa):
        if not self._kalitlar:
            return super().keyPressEvent(hodisa)
        i = self._kalitlar.index(self._joriy)
        if hodisa.key() == Qt.Key_Left:
            self.qoy(self._kalitlar[(i - 1) % len(self._kalitlar)])
        elif hodisa.key() == Qt.Key_Right:
            self.qoy(self._kalitlar[(i + 1) % len(self._kalitlar)])
        else:
            super().keyPressEvent(hodisa)

    def _boya(self) -> None:
        self.setStyleSheet(
            f"QWidget#Shaffof {{ background:{T.R('sirt_hover')};"
            f" border:1px solid {T.R('chiziq')};"
            f" border-radius:{T.B_MAYDON + 2}px; }}")
        for b, kalit in zip(self._tugmalar, self._kalitlar):
            tanlangan = kalit == self._joriy
            b.setChecked(tanlangan)
            if tanlangan:
                b.setStyleSheet(
                    f"QPushButton {{ background:{T.R('sirt2')};"
                    f" color:{T.R('aksent')}; border:1px solid {T.R('chiziq')};"
                    f" border-radius:{T.B_MAYDON}px; padding:0 14px;"
                    f" font-weight:600; }}")
            else:
                b.setStyleSheet(
                    f"QPushButton {{ background:transparent;"
                    f" color:{T.R('matn2')}; border:1px solid transparent;"
                    f" border-radius:{T.B_MAYDON}px; padding:0 14px; }}"
                    f"QPushButton:hover {{ color:{T.R('matn')}; }}")
