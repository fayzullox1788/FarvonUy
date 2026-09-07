"""Yozuv kiritish oynalari."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QRadioButton, QVBoxLayout, QWidget)

import money
from core import entries, ledger, plan, receipts, splitting
from ui.eski import theme
from ui.eski.widgets import (Jadval, Karta, OdamTanla, PulEdit, SanaEdit,
                        TuriTanla, izoh, qator, sarlavha, tugma, yorliq)


def xato_koraset(ota, matn: str):
    q = QMessageBox(ota)
    q.setIcon(QMessageBox.Warning)
    q.setWindowTitle("Xato")
    q.setText(matn)
    q.exec()


def tasdiq(ota, matn: str, sarlavha_matn: str = "Tasdiqlang") -> bool:
    q = QMessageBox(ota)
    q.setIcon(QMessageBox.Question)
    q.setWindowTitle(sarlavha_matn)
    q.setText(matn)
    q.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    q.setDefaultButton(QMessageBox.No)
    q.button(QMessageBox.Yes).setText("Ha")
    q.button(QMessageBox.No).setText("Yo'q")
    return q.exec() == QMessageBox.Yes


# ═══════════════════════════════════════════════════════════ rasxod

class RasxodDialog(QDialog):
    """Rasxod qo'shish/tahrirlash — bo'lish tahrirchisi bilan."""

    def __init__(self, db, rasxod_id: int | None = None, parent=None,
                 boshlangich_umumiy: bool = True):
        super().__init__(parent)
        self.db = db
        self.rasxod_id = rasxod_id
        self.setWindowTitle("Rasxodni tahrirlash" if rasxod_id else "Yangi rasxod")
        self.setMinimumWidth(560)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)

        # ── asosiy maydonlar ──────────────────────────────────────────
        f = QFormLayout()
        f.setSpacing(11)
        f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.sana = SanaEdit()
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("masalan: Haftalik bozorlik")
        self.summa = PulEdit()
        self.turi = TuriTanla(db)
        self.kim = OdamTanla(db)

        self.item = QComboBox()
        self.turi.currentIndexChanged.connect(self._itemlarni_yukla)
        self.item.currentIndexChanged.connect(self._item_tanlandi)

        f.addRow("Sana", self.sana)
        f.addRow("Kategoriya", self.turi)
        f.addRow("Mahsulot", self.item)
        f.addRow("Nomi / sabab", self.nom)
        f.addRow("Summa", self.summa)
        f.addRow("Kim to'ladi", self.kim)
        v.addLayout(f)

        # ── umumiy / shaxsiy ─────────────────────────────────────────
        self.umumiy = QRadioButton("Umumiy")
        self.shaxsiy = QRadioButton("Shaxsiy")
        self.uchun = QRadioButton("Boshqa uchun")
        guruh = QButtonGroup(self)
        for x in (self.umumiy, self.shaxsiy, self.uchun):
            guruh.addButton(x)
        (self.umumiy if boshlangich_umumiy else self.shaxsiy).setChecked(True)
        self.uchun_kim = OdamTanla(db)
        v.addWidget(qator(self.umumiy, self.shaxsiy, self.uchun,
                          self.uchun_kim, None))
        self.uchun_izoh = izoh("Siz to'laysiz — u qarzdor bo'ladi. Kirim emas.")
        v.addWidget(self.uchun_izoh)

        # ── bo'lish ──────────────────────────────────────────────────
        self.bolish = Karta("Qanday bo'linadi")
        self.usul_teng = QRadioButton("Teng")
        self.usul_foiz = QRadioButton("Foiz")
        self.usul_ogirlik = QRadioButton("Og'irlik")
        self.usul_aniq = QRadioButton("Aniq summa")
        self.usul_teng.setChecked(True)
        ug = QButtonGroup(self)
        for b in (self.usul_teng, self.usul_foiz, self.usul_ogirlik, self.usul_aniq):
            ug.addButton(b)
            b.toggled.connect(self._qayta)
        self.bolish.qosh(qator(self.usul_teng, self.usul_foiz,
                               self.usul_ogirlik, self.usul_aniq, None))

        self.setka = QGridLayout()
        self.setka.setHorizontalSpacing(10)
        self.setka.setVerticalSpacing(7)
        quti = QWidget()
        quti.setLayout(self.setka)
        self.bolish.qosh(quti)

        self.natija = izoh("")
        self.bolish.qosh(self.natija)
        v.addWidget(self.bolish)

        # ── cheklar ──────────────────────────────────────────────────
        self.cheklar_kutayotgan: list[Path] = []
        chek_karta = Karta("Chek")
        biriktir = tugma("+ Chek rasmini biriktirish")
        biriktir.clicked.connect(self._chek_tanla)
        self.chek_royxat = QLabel("Chek biriktirilmagan")
        self.chek_royxat.setObjectName("Izoh")
        self.chek_royxat.setWordWrap(True)
        self.chek_royxat.setOpenExternalLinks(False)
        self.chek_royxat.linkActivated.connect(self._chek_och)
        chek_karta.qosh(qator(biriktir, None))
        chek_karta.qosh(self.chek_royxat)
        v.addWidget(chek_karta)

        # ── tugmalar ─────────────────────────────────────────────────
        tugmalar = QDialogButtonBox()
        self.saqla = tugmalar.addButton("Saqlash", QDialogButtonBox.AcceptRole)
        self.saqla.setObjectName("Asosiy")
        bekor = tugmalar.addButton("Bekor", QDialogButtonBox.RejectRole)
        tugmalar.accepted.connect(self._saqla)
        tugmalar.rejected.connect(self.reject)
        v.addWidget(tugmalar)

        self.qatnashchi: dict[int, QCheckBox] = {}
        self.qiymat: dict[int, QLineEdit] = {}
        self.ulush_yorliq: dict[int, QLabel] = {}

        self.umumiy.toggled.connect(self._umumiy_ozgardi)
        self.uchun.toggled.connect(self._umumiy_ozgardi)
        self.shaxsiy.toggled.connect(self._umumiy_ozgardi)
        self.summa.ozgardi.connect(self._qayta)
        self.sana.dateChanged.connect(self._odamlarni_chiz)
        self.kim.currentIndexChanged.connect(self._qayta)

        self._itemlarni_yukla()
        self._odamlarni_chiz()
        if rasxod_id:
            self._yukla(rasxod_id)
        self._umumiy_ozgardi()

    # ── kategoriya → mahsulot ────────────────────────────────────────

    def _itemlarni_yukla(self):
        """Kategoriya tanlangach shu kategoriyaning mahsulotlari chiqadi."""
        from PySide6.QtCore import QSignalBlocker
        with QSignalBlocker(self.item):
            self.item.clear()
            self.item.addItem("— mahsulot tanlanmagan —", None)
            for it in plan.turi_itemlari(self.db, self.turi.turi_id()):
                yorliqcha = it["nom"]
                if it["narx"]:
                    yorliqcha += f"  ·  {money.fmt(it['narx'])}"
                self.item.addItem(yorliqcha, it["id"])

    def _item_tanlandi(self):
        iid = self.item.currentData()
        if not iid:
            return
        it = self.db.q1("SELECT nom, narx FROM item WHERE id=?", iid)
        if not it:
            return
        if not self.nom.text().strip():
            self.nom.setText(it["nom"])
        if it["narx"] and self.summa.qiymat() == 0:
            self.summa.qoy(it["narx"])

    # ── qurish ───────────────────────────────────────────────────────

    def _odamlarni_chiz(self):
        while self.setka.count():
            x = self.setka.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        self.qatnashchi.clear()
        self.qiymat.clear()
        self.ulush_yorliq.clear()

        sana = self.sana.iso()
        uyda = set(splitting.qatnashchilar(self.db, sana))
        yoqlar = splitting.yoq_odamlar(self.db, sana)

        r = 0
        if yoqlar:
            e = izoh(f"⚑ {', '.join(yoqlar)} bu kuni uyda yo'q — "
                     f"avtomatik chiqarib tashlandi")
            e.setStyleSheet(f"color:{theme.SARIQ};background:transparent;font-size:12px;")
            self.setka.addWidget(e, r, 0, 1, 3)
            r += 1

        for o in self.db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id"):
            oid = o["id"]
            cb = QCheckBox(o["nom"])
            cb.setChecked(oid in uyda)
            cb.toggled.connect(self._qayta)
            self.qatnashchi[oid] = cb

            le = QLineEdit()
            le.setAlignment(Qt.AlignRight)
            le.setFixedWidth(110)
            le.setPlaceholderText("—")
            le.textChanged.connect(self._qayta)
            self.qiymat[oid] = le

            lb = QLabel("—")
            lb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lb.setStyleSheet(
                f"font-family:{theme.RAQAM};font-weight:600;background:transparent;")
            lb.setMinimumWidth(115)
            self.ulush_yorliq[oid] = lb

            self.setka.addWidget(cb, r, 0)
            self.setka.addWidget(le, r, 1)
            self.setka.addWidget(lb, r, 2)
            r += 1
        self._qayta()

    def _umumiy_ozgardi(self):
        uchunmi = self.uchun.isChecked()
        self.bolish.setVisible(self.umumiy.isChecked())
        self.uchun_kim.setVisible(uchunmi)
        self.uchun_izoh.setVisible(uchunmi)
        self._qayta()

    def usul(self) -> str:
        if self.usul_foiz.isChecked():
            return money.USUL_FOIZ
        if self.usul_ogirlik.isChecked():
            return money.USUL_OGIRLIK
        if self.usul_aniq.isChecked():
            return money.USUL_ANIQ
        return money.USUL_TENG

    def _parametrlar(self) -> dict[int, float] | None:
        tanlangan = [i for i, cb in self.qatnashchi.items() if cb.isChecked()]
        if not tanlangan:
            return None
        u = self.usul()
        if u == money.USUL_TENG:
            return {i: 1.0 for i in tanlangan}
        p = {}
        for i in tanlangan:
            t = self.qiymat[i].text().strip().replace(",", ".")
            try:
                p[i] = float("".join(c for c in t if c.isdigit() or c == ".") or 0)
            except ValueError:
                p[i] = 0.0
        return p

    def _qayta(self):
        """Ulushlarni jonli qayta hisoblaydi."""
        aniq = self.usul_aniq.isChecked()
        teng = self.usul_teng.isChecked()
        for i, le in self.qiymat.items():
            le.setVisible(not teng)
            le.setEnabled(self.qatnashchi[i].isChecked())
            if aniq and not le.text():
                le.setPlaceholderText("so'm")
            elif self.usul_foiz.isChecked():
                le.setPlaceholderText("%")
            else:
                le.setPlaceholderText("—")

        if not self.umumiy.isChecked():
            self.natija.setText("")
            return

        summa = self.summa.qiymat()
        p = self._parametrlar()
        if not summa or not p:
            for lb in self.ulush_yorliq.values():
                lb.setText("—")
            self.natija.setText("")
            return
        try:
            ulushlar = money.bol(summa, self.usul(), p,
                                 splitting.yaxlitlash_tarixi(self.db))
        except ValueError as e:
            for lb in self.ulush_yorliq.values():
                lb.setText("—")
            self.natija.setText(f"⚠ {e}")
            self.natija.setStyleSheet(
                f"color:{theme.QIZIL};background:transparent;font-size:12px;")
            return

        for i, lb in self.ulush_yorliq.items():
            lb.setText("—")
            lb.setStyleSheet(
                f"font-family:{theme.RAQAM};color:{theme.KUL};background:transparent;")
        ortiqcha = []
        for u in ulushlar:
            lb = self.ulush_yorliq.get(u.odam_id)
            if lb:
                lb.setText(money.fmt(u.summa))
                lb.setStyleSheet(f"font-family:{theme.RAQAM};font-weight:600;"
                                 f"color:{theme.MATN};background:transparent;")
            if u.yaxlitlash:
                nom = self.qatnashchi[u.odam_id].text()
                ortiqcha.append(nom)

        matn = f"Yig'indi: {money.fmt_som(sum(u.summa for u in ulushlar))}"
        if ortiqcha:
            matn += (f"   ·   yaxlitlashdan ortgan {len(ortiqcha)} so'm "
                     f"{', '.join(ortiqcha)}ga qo'shildi")
        self.natija.setText(matn)
        self.natija.setStyleSheet(
            f"color:{theme.KUL};background:transparent;font-size:12px;")

    # ── cheklar ──────────────────────────────────────────────────────

    def _chek_tanla(self):
        yollar, _ = QFileDialog.getOpenFileNames(
            self, "Chek rasmini tanlang", str(Path.home()),
            "Rasm va PDF (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.pdf);;"
            "Hamma fayl (*.*)")
        for y in yollar:
            if self.rasxod_id:
                try:
                    receipts.qosh(self.db, self.rasxod_id, y)
                except Exception as e:
                    xato_koraset(self, str(e))
            else:
                self.cheklar_kutayotgan.append(Path(y))
        self._chek_chiz()

    def _chek_chiz(self):
        qismlar = []
        if self.rasxod_id:
            for c in receipts.royxat(self.db, self.rasxod_id):
                belgi = "" if c["bormi"] else "  ⚠ fayl topilmadi"
                qismlar.append(
                    f"<a href='{c['yol']}'>{c['fayl']}</a>{belgi}")
        for p in self.cheklar_kutayotgan:
            qismlar.append(f"{p.name}  <i>(saqlanganda biriktiriladi)</i>")
        self.chek_royxat.setText("<br>".join(qismlar) or "Chek biriktirilmagan")

    def _chek_och(self, yol: str):
        try:
            if sys.platform == "win32":
                os.startfile(yol)
            else:
                subprocess.Popen(["xdg-open", yol])
        except Exception:
            pass

    # ── yuklash / saqlash ────────────────────────────────────────────

    def _yukla(self, rid: int):
        r = self.db.q1("SELECT * FROM rasxod WHERE id=?", rid)
        if not r:
            return
        self.sana.qoy(r["sana"])
        self.nom.setText(r["nom"] or "")
        self.summa.qoy(r["summa"])
        self.kim.tanla(r["kim_toladi"])
        i = self.turi.findData(r["turi_id"])
        if i >= 0:
            self.turi.setCurrentIndex(i)
        if r["kim_uchun"] is not None:
            self.uchun.setChecked(True)
            self.uchun_kim.tanla(r["kim_uchun"])
        else:
            (self.umumiy if r["umumiymi"] else self.shaxsiy).setChecked(True)

        {money.USUL_TENG: self.usul_teng, money.USUL_FOIZ: self.usul_foiz,
         money.USUL_OGIRLIK: self.usul_ogirlik,
         money.USUL_ANIQ: self.usul_aniq}.get(
            r["bolish_usul"], self.usul_teng).setChecked(True)

        bor = {x["odam_id"]: x["summa"] for x in
               self.db.q("SELECT odam_id, summa FROM ulush WHERE rasxod_id=?", rid)}
        for oid, cb in self.qatnashchi.items():
            cb.setChecked(oid in bor)
            if r["bolish_usul"] == money.USUL_ANIQ and oid in bor:
                self.qiymat[oid].setText(str(bor[oid]))
        self._qayta()
        self._chek_chiz()

    def _saqla(self):
        summa = self.summa.qiymat()
        if summa <= 0:
            xato_koraset(self, "Summa kiritilmagan.")
            return
        uchunmi = self.uchun.isChecked()
        kim_uchun = self.uchun_kim.odam_id() if uchunmi else None
        if uchunmi and kim_uchun is None:
            xato_koraset(self, "Kim uchun olinganini tanlang.")
            return
        if uchunmi and kim_uchun == self.kim.odam_id():
            xato_koraset(
                self, "To'lovchi va «kim uchun» bir odam bo'lsa — bu oddiy "
                      "shaxsiy rasxod. «Shaxsiy» ni tanlang.")
            return

        umumiymi = self.umumiy.isChecked()
        p = self._parametrlar() if umumiymi else None
        if umumiymi and not p:
            xato_koraset(self, "Kamida bitta odam tanlangan bo'lishi kerak.")
            return

        try:
            if self.rasxod_id:
                entries.rasxod_tahrir(
                    self.db, self.rasxod_id, sana=self.sana.iso(),
                    nom=self.nom.text().strip(), summa=summa,
                    kim_toladi=self.kim.odam_id(), umumiymi=umumiymi,
                    turi_id=self.turi.turi_id(), usul=self.usul(),
                    parametrlar=p, kim_uchun=kim_uchun,
                    item_id=self.item.currentData())
            else:
                self.rasxod_id = entries.rasxod_qosh(
                    self.db, self.sana.iso(), self.nom.text().strip(), summa,
                    self.kim.odam_id(), umumiymi=umumiymi,
                    turi_id=self.turi.turi_id(), usul=self.usul(),
                    parametrlar=p, kim_uchun=kim_uchun)
        except Exception as e:
            xato_koraset(self, str(e))
            return

        # Rasxod saqlangandan keyingina chekni biriktirib bo'ladi — unga id kerak.
        for yol in self.cheklar_kutayotgan:
            try:
                receipts.qosh(self.db, self.rasxod_id, yol)
            except Exception as e:
                xato_koraset(self, f"Chek biriktirilmadi ({yol.name}):\n{e}")
        self.cheklar_kutayotgan.clear()
        self.accept()


# ═══════════════════════════════════════════════════════════ kirim

class KirimDialog(QDialog):
    def __init__(self, db, kirim_id: int | None = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.kirim_id = kirim_id
        self.setWindowTitle("Kirimni tahrirlash" if kirim_id else "Yangi kirim")
        self.setMinimumWidth(420)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.kim = OdamTanla(db)
        self.summa = PulEdit()
        self.sabab = QLineEdit()
        self.sabab.setPlaceholderText("masalan: Oylik")
        f.addRow("Sana", self.sana)
        f.addRow("Kim oldi", self.kim)
        f.addRow("Summa", self.summa)
        f.addRow("Qayerdan", self.sabab)
        v.addLayout(f)

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

        if kirim_id:
            r = db.q1("SELECT * FROM kirim WHERE id=?", kirim_id)
            if r:
                self.sana.qoy(r["sana"])
                self.kim.tanla(r["odam_id"])
                self.summa.qoy(r["summa"])
                self.sabab.setText(r["sabab"] or "")

    def _saqla(self):
        if self.summa.qiymat() <= 0:
            xato_koraset(self, "Summa kiritilmagan.")
            return
        try:
            if self.kirim_id:
                entries.kirim_tahrir(
                    self.db, self.kirim_id, sana=self.sana.iso(),
                    odam_id=self.kim.odam_id(), summa=self.summa.qiymat(),
                    sabab=self.sabab.text().strip() or None)
            else:
                entries.kirim_qosh(self.db, self.sana.iso(), self.kim.odam_id(),
                                   self.summa.qiymat(),
                                   self.sabab.text().strip() or None)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ═══════════════════════════════════════════════════════════ qarz

class QarzDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Yangi qarz")
        self.setMinimumWidth(430)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.berdi = OdamTanla(db)
        self.oldi = OdamTanla(db)
        if self.oldi.count() > 1:
            self.oldi.setCurrentIndex(1)
        self.summa = PulEdit()
        self.sabab = QLineEdit()
        f.addRow("Sana", self.sana)
        f.addRow("Kim berdi", self.berdi)
        f.addRow("Kimga", self.oldi)
        f.addRow("Summa", self.summa)
        f.addRow("Sabab", self.sabab)
        v.addLayout(f)

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _saqla(self):
        if self.summa.qiymat() <= 0:
            xato_koraset(self, "Summa kiritilmagan.")
            return
        if self.berdi.odam_id() == self.oldi.odam_id():
            xato_koraset(self, "Bir odamning o'ziga qarz bera olmaydi.")
            return
        try:
            entries.qarz_qosh(self.db, self.sana.iso(), self.berdi.odam_id(),
                              self.oldi.odam_id(), self.summa.qiymat(),
                              self.sabab.text().strip() or None)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ═══════════════════════════════════════════════════ hisob-kitob

class TolovDialog(QDialog):
    """Qarzni yopish uchun to'lov (to'liq yoki qisman)."""

    def __init__(self, db, kimdan: int | None = None, kimga: int | None = None,
                 summa: int = 0, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("To'lov")
        self.setMinimumWidth(430)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.kimdan = OdamTanla(db)
        self.kimga = OdamTanla(db)
        self.summa = PulEdit(summa)
        self.izohm = QLineEdit()
        f.addRow("Sana", self.sana)
        f.addRow("Kim to'ladi", self.kimdan)
        f.addRow("Kimga", self.kimga)
        f.addRow("Summa", self.summa)
        f.addRow("Izoh", self.izohm)
        v.addLayout(f)

        if kimdan:
            self.kimdan.tanla(kimdan)
        if kimga:
            self.kimga.tanla(kimga)

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _saqla(self):
        if self.summa.qiymat() <= 0:
            xato_koraset(self, "Summa kiritilmagan.")
            return
        if self.kimdan.odam_id() == self.kimga.odam_id():
            xato_koraset(self, "Bir odamning o'ziga to'lay olmaydi.")
            return
        try:
            entries.hisob_kitob_qosh(
                self.db, self.sana.iso(), self.kimdan.odam_id(),
                self.kimga.odam_id(), self.summa.qiymat(),
                self.izohm.text().strip() or None)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ═══════════════════════════════════════════════════════ yo'q kun

class YoqKunDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Uyda yo'q kunlar")
        self.setMinimumWidth(430)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        v.addWidget(izoh("Bu kunlarda umumiy rasxod unga bo'linmaydi."))
        f = QFormLayout()
        f.setSpacing(11)
        self.kim = OdamTanla(db)
        self.boshi = SanaEdit()
        self.oxiri = SanaEdit()
        self.sabab = QLineEdit()
        f.addRow("Kim", self.kim)
        f.addRow("Dan", self.boshi)
        f.addRow("Gacha", self.oxiri)
        f.addRow("Sabab", self.sabab)
        v.addLayout(f)

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _saqla(self):
        if self.oxiri.iso() < self.boshi.iso():
            xato_koraset(self, "Tugash sanasi boshlanishdan oldin bo'lmaydi.")
            return
        with self.db.amal("Yo'q kunlar qo'shildi"):
            self.db.apply("yoq_kun", "INSERT", {
                "odam_id": self.kim.odam_id(), "boshi": self.boshi.iso(),
                "oxiri": self.oxiri.iso(),
                "sabab": self.sabab.text().strip() or None})
        self.accept()


# ═════════════════════════════════════════════════ rasxod tafsiloti

class RasxodTafsilot(QDialog):
    """Bitta rasxod: hammasi ko'rinadi va SHU YERDA bekor qilinadi.

    Tezkor tugma bilan bekor qilish olib tashlangan — «nima o'chdi?»
    degan savol tug'ilmasligi uchun bekor qilish har doim aniq
    yozuvning ustida, uning summasi va ulushlari ko'rinib turganda
    bo'ladi.
    """

    def __init__(self, db, rasxod_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.rasxod_id = rasxod_id
        self.ozgardi = False

        r = db.q1(
            "SELECT r.*, t.nom turi_nom, t.belgi belgi, o.nom odam_nom,"
            "       u.nom kim_uchun_nom"
            " FROM rasxod r LEFT JOIN turi t ON t.id=r.turi_id"
            " JOIN odam o ON o.id=r.kim_toladi"
            " LEFT JOIN odam u ON u.id=r.kim_uchun"
            " WHERE r.id=? AND r.ochirilgan=0", rasxod_id)
        if not r:
            self.reject()
            return

        self.setWindowTitle("Rasxod tafsiloti")
        self.setMinimumWidth(470)
        v = QVBoxLayout(self)
        v.setSpacing(12)

        bosh = sarlavha(r["nom"] or "—")
        bosh.setWordWrap(True)
        v.addWidget(bosh)

        # Global QSS `QLabel { font-size }` `setFont()` dan kuchliroq —
        # o'lcham shu yerda, stilda berilishi kerak.
        summa = QLabel(money.fmt_som(r["summa"]))
        summa.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(summa)

        if r["kim_uchun_nom"]:
            tur = f"{r['kim_uchun_nom']} uchun olingan"
        elif r["umumiymi"]:
            tur = "Umumiy rasxod"
        else:
            tur = "Shaxsiy rasxod"

        iso = str(r["sana"])[:10]
        karta = Karta("Ma'lumot")
        satrlar = [
            ("Sana", f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"),
            ("Kim to'ladi", r["odam_nom"]),
            ("Turi", tur),
            ("Kategoriya",
             f"{r['belgi'] or ''} {r['turi_nom'] or ''}".strip() or "—"),
        ]
        if r["umumiymi"]:
            satrlar.append(("Bo'lish usuli", r["bolish_usul"]))
        if r["izoh"]:
            satrlar.append(("Izoh", r["izoh"]))
        cheklar = db.skalyar(
            "SELECT COUNT(*) FROM chek WHERE rasxod_id=?", rasxod_id)
        if cheklar:
            satrlar.append(("Chek", f"{cheklar} ta fayl"))
        for nom, qiymat in satrlar:
            e = QLabel(str(qiymat))
            e.setWordWrap(True)
            karta.qosh(qator(yorliq(nom + ":"), None, e))
        v.addWidget(karta)

        ulushlar = db.q(
            "SELECT u.summa, u.yaxlitlash, o.nom FROM ulush u"
            " JOIN odam o ON o.id=u.odam_id WHERE u.rasxod_id=?"
            " ORDER BY o.tartib", rasxod_id)
        if ulushlar:
            u_karta = Karta("Kim qancha ko'taradi")
            for x in ulushlar:
                qosh_matn = (f"  (+{x['yaxlitlash']} yaxlitlash)"
                             if x["yaxlitlash"] else "")
                u_karta.qosh(qator(
                    yorliq(x["nom"]), None,
                    QLabel(money.fmt_som(x["summa"]) + qosh_matn)))
            v.addWidget(u_karta)

        t_tahrir = tugma("Tahrirlash")
        t_tahrir.clicked.connect(self._tahrir)
        t_bekor = tugma("Rasxodni bekor qilish", xavfli=True)
        t_bekor.clicked.connect(self._bekor)
        v.addWidget(qator(t_tahrir, None, t_bekor))

        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(None, yop))

    def _tahrir(self):
        if RasxodDialog(self.db, self.rasxod_id, parent=self).exec():
            self.ozgardi = True
            self.accept()

    def _bekor(self):
        r = self.db.q1("SELECT nom, summa FROM rasxod WHERE id=?",
                       self.rasxod_id)
        if not r:
            return
        if not tasdiq(self, f"«{r['nom'] or '—'}» — "
                            f"{money.fmt_som(r['summa'])}\n\n"
                            f"Shu rasxod bekor qilinsinmi?\n"
                            f"Balansdan chiqadi, lekin tarixda qoladi."):
            return
        try:
            entries.rasxod_ochir(self.db, self.rasxod_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()


# ═══════════════════════════════════════════════ juftlik qarzi tafsiloti

class JuftTafsilot(QDialog):
    """«Otabek → Fayzulloxon: 547 667» qatorining ICHI.

    Yakuniy son o'zicha hech narsa aytmaydi: u umumiy rasxod ulushlari,
    to'g'ridan-to'g'ri qarzlar va to'lovlardan yig'iladi. Shu yerda
    har biri sanasi, nomi va holati bilan ko'rinadi — qatorlar
    yig'indisi aynan yuqoridagi songa teng.
    """

    def __init__(self, db, qarzdor_id: int, kreditor_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.qarzdor_id = qarzdor_id
        self.kreditor_id = kreditor_id
        self.tolov_soraldi = False

        qarzdor = db.q1("SELECT nom FROM odam WHERE id=?", qarzdor_id)
        kreditor = db.q1("SELECT nom FROM odam WHERE id=?", kreditor_id)
        self.qarzdor_nom = qarzdor["nom"] if qarzdor else "?"
        self.kreditor_nom = kreditor["nom"] if kreditor else "?"

        self.setWindowTitle(f"{self.qarzdor_nom} → {self.kreditor_nom}")
        self.setMinimumSize(760, 560)

        v = QVBoxLayout(self)
        v.setSpacing(12)

        bosh = sarlavha(f"{self.qarzdor_nom} → {self.kreditor_nom}")
        bosh.setWordWrap(True)
        v.addWidget(bosh)

        tarkib = ledger.juft_tarkibi(db, qarzdor_id, kreditor_id)
        jami = sum(x["summa"] for x in tarkib)

        self.jami_yorliq = QLabel(money.fmt_som(jami))
        self.jami_yorliq.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(self.jami_yorliq)

        qoshildi = sum(x["summa"] for x in tarkib if x["summa"] > 0)
        ayrildi = -sum(x["summa"] for x in tarkib if x["summa"] < 0)
        v.addWidget(izoh(
            f"{len(tarkib)} ta yozuv:  "
            f"qarz oshgani {money.fmt_som(qoshildi)}  ·  "
            f"kamaygani {money.fmt_som(ayrildi)}"))

        jadval = Jadval(["Sana", "Turi", "Nima uchun", "Holati", "Summa"],
                        pul_ustunlar={4},
                        bosh_matn="Bu ikkisi orasida yozuv yo'q")
        jadval.kengliklar(105, 125, 0, 165, 130)
        def kun(s) -> str:
            """ISO sanani dastur ko'rinishiga: 22.08.2026."""
            s = str(s or "")[:10]
            return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 else s

        qatorlar = []
        for x in tarkib:
            if x["turi"] == "To'lov":
                holat = f"To'landi · {kun(x['sana'])}"
            elif x["tolandi"]:
                holat = "To'landi"
                if x["tolangan_sana"]:
                    holat += f" · {kun(x['tolangan_sana'])}"
            else:
                holat = "To'lanmagan"
            nom = x["nom"]
            if x["izoh"]:
                nom = f"{nom}  ({x['izoh']})"
            qatorlar.append([kun(x["sana"]), x["turi"], nom, holat,
                             x["summa"]])
        jadval.tuldir(qatorlar, rangli_ustunlar={4})
        v.addWidget(jadval, 1)

        v.addWidget(izoh(
            "«+» — qarzni oshirgan yozuv, «−» — kamaytirgan "
            "(teskari yo'nalishdagi rasxod yoki to'lov). "
            "Qatorlar yig'indisi yuqoridagi songa teng."))

        t_tolov = tugma("To'lov yozish", asosiy=True)
        t_tolov.clicked.connect(self._tolov)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(t_tolov, None, yop))

    def _tolov(self):
        self.tolov_soraldi = True
        self.accept()
