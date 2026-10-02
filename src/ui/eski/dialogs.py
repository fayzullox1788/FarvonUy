"""Yozuv kiritish oynalari."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QRadioButton, QVBoxLayout,
                               QWidget)

import money
from core import entries, ledger, plan, receipts, splitting
from core import rasxod_kirit as rk
from ui.eski import theme
from ui.eski.widgets import (HamyonTanla, Jadval, Karta, KategoriyaTanla, OdamTanla,
                        PulEdit, SanaEdit, TuriTanla, Xabar, bolim, izoh, qator, sarlavha,
                        tugma,
                        yorliq)


def mahsulotlarni_toldir(combo: QComboBox, db, turi_id) -> None:
    """Rasxod oynalaridagi «Mahsulot» tanlagichi — ikkala oyna uchun bitta.

    Kategoriya tanlansa uning VA ichki kategoriyalarining mahsulotlari
    chiqadi; ichkidagisi «Mevalar › Olma» ko'rinishida, rasmi bilan.
    """
    from PySide6.QtCore import QSignalBlocker, QSize
    from PySide6.QtGui import QIcon
    from core import mahsulot as mh
    with QSignalBlocker(combo):
        combo.clear()
        combo.setIconSize(QSize(28, 28))
        combo.addItem("— mahsulot tanlanmagan —", None)
        for it in plan.turi_itemlari(db, turi_id):
            yorliqcha = it["nom"]
            if "ichkida" in it.keys() and it["ichkida"]:
                yorliqcha = f"{it['turi_nom']} › {yorliqcha}"
            if it["narx"]:
                yorliqcha += f"  ·  {money.fmt(it['narx'])}"
            yol = mh.rasm_yoli(it["rasm"])
            if yol:
                combo.addItem(QIcon(str(yol)), yorliqcha, it["id"])
            else:
                combo.addItem(yorliqcha, it["id"])


class MahsulotRoyxat(QWidget):
    """Kategoriya ichidan BIR NECHTA mahsulot: har qatorda mahsulot,
    miqdor (dona) va summa. Rasxod oynasi ham, reja oynasi ham shuni
    ishlatadi — qoidasi `core/rasxod_kirit.py` da (`mahsulot_qatorlari`).

    Mahsulot katalogda bo'lishi SHART EMAS: tanlagichga yangi nom
    yozilsa, u saqlanganda shu kategoriyaga katalogga qo'shiladi
    (`rk.yangi_mahsulotlarni_qosh`).

    Mahsulot tanlansa summa = narx × miqdor o'zi qo'yiladi; summa qo'lda
    o'zgartirilsa, keyin miqdor almashganda ustidan yozilmaydi.
    `bogla(summa, nom)` — yozuvning «Summa» si qatorlar yig'indisiga
    teng bo'ladi (qo'lda kiritilmaydi), sabab bo'sh bo'lsa mahsulot
    nomlari taklif qilinadi.
    """

    ozgardi = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.turi_id = None
        self._qatorlar: list[dict] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self._quti = QVBoxLayout()
        self._quti.setSpacing(6)
        v.addLayout(self._quti)
        self.qosh_t = tugma("+ Yana mahsulot")
        self.qosh_t.clicked.connect(lambda: self.qator_qosh())
        self.jami_yorliq = izoh("")
        v.addWidget(qator(self.qosh_t, None, self.jami_yorliq))
        self._summa = self._nom = None
        self._avto_nom = ""
        self.qator_qosh()

    # ── qatorlar ─────────────────────────────────────────────────────

    def qator_qosh(self, x: dict | None = None) -> dict:
        combo = QComboBox()
        combo.setMinimumWidth(220)
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.lineEdit().setPlaceholderText("tanlang yoki yangi nom yozing")
        # Global QLineEdit stili (chekka, padding) tanlagich ichida matnni
        # pastga surib qo'yardi — ichki maydon shaffof va chekkasiz.
        combo.lineEdit().setStyleSheet(
            "QLineEdit { background:transparent; border:none; padding:0;"
            " margin:0; min-height:0; }")
        self._toldir(combo)
        # Miqdor — butun son (dona). PulEdit: shu oynadagi maydonlar bilan
        # bir xil ko'rinish; QSpinBox global stilda raqamni qirqib qo'yardi.
        miqdor = PulEdit(1)
        miqdor.setMinimumWidth(0)
        miqdor.setFixedWidth(64)
        miqdor.setAlignment(Qt.AlignCenter)
        miqdor.setPlaceholderText("1")
        miqdor.setToolTip("Miqdor (dona)")
        summa = PulEdit()
        summa.setFixedWidth(130)
        ochir = tugma("×")
        ochir.setFixedWidth(40)
        ochir.setToolTip("Qatorni olib tashlash")
        q = {"combo": combo, "miqdor": miqdor, "summa": summa, "ochir": ochir,
             "avto": True}
        q["w"] = qator(combo, miqdor, summa, ochir, oraliq=6)
        q["w"].layout().setStretch(0, 1)
        self._qatorlar.append(q)
        self._quti.addWidget(q["w"])

        combo.currentIndexChanged.connect(lambda _i, q=q: self._narx(q, True))
        combo.editTextChanged.connect(lambda _t, q=q: self._yozildi(q))
        miqdor.ozgardi.connect(lambda _v, q=q: self._narx(q, False))
        summa.textEdited.connect(lambda _t, q=q: q.update(avto=False))
        summa.ozgardi.connect(self._ozgardi)
        ochir.clicked.connect(lambda _c=False, q=q: self._olib_tashla(q))
        if x:
            self._qoy(q, x)
        return q

    def _toldir(self, combo: QComboBox) -> None:
        mahsulotlarni_toldir(combo, self.db, self.turi_id)
        # Bo'sh birinchi qator — yozish maydoni toza tursin (izoh ko'rinadi).
        combo.setItemText(0, "")
        with QSignalBlocker(combo):
            combo.setCurrentIndex(0)
            combo.setEditText("")

    def _tanlangan(self, q: dict) -> tuple[int | None, str]:
        """(item_id, yangi nom). Ro'yxatdagi mahsulot — (id, ""); yangi
        yozilgan nom — (None, nom); bo'sh — (None, "")."""
        c = q["combo"]
        matn = c.currentText().strip()
        if not matn:
            return None, ""
        i = c.findText(c.currentText())
        if i > 0:
            return c.itemData(i), ""
        # Ro'yxatdagi bilan bir xil nom yozilgan bo'lsa (bezaksiz) — o'sha.
        iid = self.db.skalyar(
            "SELECT id FROM item WHERE ochirilgan=0 AND faol=1 AND nom=?"
            " COLLATE NOCASE AND turi_id IS ?", matn, self.turi_id,
            birlamchi=None)
        return (iid, "") if iid else (None, matn)

    def _yozildi(self, q: dict) -> None:
        """Qo'lda yozilyapti: ro'yxatdagi nomga to'liq mos kelsa narxi
        olinadi, aks holda bu yangi mahsulot — summani o'zingiz yozasiz."""
        iid, _ = self._tanlangan(q)
        oldingi = q.get("oxirgi")
        if iid == oldingi:
            self._ozgardi()
            return
        q["oxirgi"] = iid
        q["avto"] = True
        if iid is None and oldingi is not None:
            # Katalogdagidan yangi nomga o'tildi — eski narx qolmasin.
            with QSignalBlocker(q["summa"]):
                q["summa"].tozala()
        self._narx(q, False)

    def _qoy(self, q: dict, x: dict) -> None:
        iid = x.get("item_id")
        with QSignalBlocker(q["combo"]), QSignalBlocker(q["miqdor"]):
            if iid is not None and q["combo"].findData(iid) < 0:
                # Mahsulot nofaol/boshqa kategoriyada — bog'lanish uzilmasin.
                q["combo"].addItem(f"{x.get('nom') or '?'}  (nofaol)", iid)
            if iid is not None:
                q["combo"].setCurrentIndex(q["combo"].findData(iid))
            else:
                q["combo"].setCurrentIndex(0)
                q["combo"].setEditText(x.get("nom") or "")
            q["oxirgi"] = iid
            q["miqdor"].qoy(int(x.get("miqdor") or 1))
        q["avto"] = False
        q["summa"].qoy(int(x.get("summa") or 0))

    def _olib_tashla(self, q: dict) -> None:
        if len(self._qatorlar) == 1:
            with QSignalBlocker(q["combo"]), QSignalBlocker(q["miqdor"]):
                q["combo"].setCurrentIndex(0)
                q["combo"].setEditText("")
                q["miqdor"].qoy(1)
            q["oxirgi"] = None
            q["avto"] = True
            q["summa"].tozala()
            self._ozgardi()
            return
        self._qatorlar.remove(q)
        self._quti.removeWidget(q["w"])
        q["w"].deleteLater()
        self._ozgardi()

    def _narx(self, q: dict, mahsulot_almashdi: bool) -> None:
        if mahsulot_almashdi:
            q["avto"] = True
        iid, _ = self._tanlangan(q)
        q["oxirgi"] = iid
        narx = (self.db.skalyar("SELECT narx FROM item WHERE id=?", iid)
                if iid else 0)
        if q["avto"] and narx:
            q["summa"].qoy(int(narx) * self._miqdor(q))
        elif mahsulot_almashdi and not iid:
            q["summa"].tozala()
        self._ozgardi()

    def turi_qoy(self, turi_id) -> None:
        """Kategoriya almashdi — har qatorning tanlagichi qayta to'ladi.
        Yangi kategoriyada yo'q mahsulot tanlovi tushib qoladi."""
        self.turi_id = turi_id
        for q in self._qatorlar:
            joriy, yangi = self._tanlangan(q)
            self._toldir(q["combo"])
            i = q["combo"].findData(joriy) if joriy is not None else 0
            with QSignalBlocker(q["combo"]):
                q["combo"].setCurrentIndex(max(0, i))
                if yangi:                       # yozilgan yangi nom qoladi
                    q["combo"].setEditText(yangi)
            q["oxirgi"] = joriy if i > 0 else None
            if joriy is not None and i < 0:
                q["avto"] = True
                q["summa"].tozala()
        self._ozgardi()

    def yukla(self, qatorlar: list[dict]) -> None:
        for q in list(self._qatorlar):
            self._quti.removeWidget(q["w"])
            q["w"].deleteLater()
        self._qatorlar = []
        for x in qatorlar or [{}]:
            self.qator_qosh(x or None)
        self._ozgardi()

    def qatorlar(self) -> list[dict]:
        """To'ldirilgan qatorlar — `rk.mahsulot_qatorlari` ga beriladi."""
        natija = []
        for q in self._qatorlar:
            (iid, nom), summa = self._tanlangan(q), q["summa"].qiymat()
            if iid is None and not nom and not summa:
                continue
            if iid:
                nom = self.db.skalyar("SELECT nom FROM item WHERE id=?", iid,
                                      birlamchi="")
            natija.append({"item_id": iid, "nom": nom,
                           "miqdor": self._miqdor(q), "summa": summa})
        return natija

    @staticmethod
    def _miqdor(q: dict) -> int:
        return q["miqdor"].qiymat() or 1

    def jami(self) -> int:
        return sum(x["summa"] for x in self.qatorlar())

    # ── yozuv bilan bog'lash ─────────────────────────────────────────

    def bogla(self, summa: PulEdit, nom: QLineEdit) -> None:
        self._summa, self._nom = summa, nom
        self._ozgardi()

    def _ozgardi(self, *_):
        tanlangan = self.qatorlar()
        jami = sum(x["summa"] for x in tanlangan)
        self.jami_yorliq.setText(
            f"{len(tanlangan)} ta mahsulot · {money.fmt_som(jami)}"
            if len(tanlangan) > 1 else "")
        if self._summa is not None:
            self._summa.setReadOnly(bool(tanlangan))
            self._summa.setToolTip("Mahsulotlar yig'indisi" if tanlangan
                                   else "")
            if tanlangan and self._summa.qiymat() != jami:
                self._summa.qoy(jami)
        if self._nom is not None:
            nomli = [x for x in tanlangan if x["nom"]]
            taklif = rk.qatorlar_nomi(nomli) if nomli else ""
            joriy = self._nom.text().strip()
            if not joriy or joriy == self._avto_nom:
                if taklif != joriy:
                    self._nom.setText(taklif)
                self._avto_nom = taklif
        self.ozgardi.emit()


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
        # Ikki bosqich: katta kategoriya + uning ichkisi.
        self.turi = KategoriyaTanla(db)
        self.kim = OdamTanla(db)
        # Naqd yoki to'lovchining qaysi kartasi (2026-10-01).
        self.joy = HamyonTanla(db)
        self.joy.odam_qoy(self.kim.odam_id())
        self.kim.currentIndexChanged.connect(
            lambda: self.joy.odam_qoy(self.kim.odam_id()))

        # Kategoriya ichidan bir nechta mahsulot (2026-10-01).
        self.mahsulotlar = MahsulotRoyxat(db)
        self.turi.ozgardi.connect(self._itemlarni_yukla)

        f.addRow("Sana", self.sana)
        f.addRow("Kategoriya *", self.turi)
        f.addRow("Mahsulotlar", self.mahsulotlar)
        f.addRow("Nomi / sabab *", self.nom)
        f.addRow("Summa", self.summa)
        f.addRow("Kim to'ladi", self.kim)
        f.addRow("Qayerdan to'landi", self.joy)
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
        self.mahsulotlar.bogla(self.summa, self.nom)
        self._odamlarni_chiz()
        if rasxod_id:
            self._yukla(rasxod_id)
        self._umumiy_ozgardi()

    # ── kategoriya → mahsulot ────────────────────────────────────────

    def _itemlarni_yukla(self):
        """Kategoriya tanlangach shu kategoriyaning mahsulotlari chiqadi."""
        self.mahsulotlar.turi_qoy(self.turi.turi_id())

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
        self.joy.odam_qoy(r["kim_toladi"])
        self.joy.tanla(r["karta_id"])
        self.turi.tanla(r["turi_id"])
        # Mahsulot qatorlari qayta qo'yiladi — aks holda saqlashda
        # `item_id` jimgina bo'shab qolardi. Eski (qatorsiz) rasxodning
        # bitta mahsuloti — bitta qator. Mahsulot keyin nofaol yoki
        # o'chirilgan bo'lsa ham qo'shiladi: bog'lanish uzilmasin.
        qatorlar = rk.rasxod_mahsulotlari(self.db, rid)
        if not qatorlar and r["item_id"] is not None:
            it = self.db.q1("SELECT nom FROM item WHERE id=?", r["item_id"])
            qatorlar = [{"item_id": r["item_id"],
                         "nom": it["nom"] if it else "?", "miqdor": 1,
                         "summa": r["summa"]}]
        self.mahsulotlar.yukla(qatorlar)
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

    def qoralama(self) -> rk.Qoralama:
        """Oynadagi hamma maydon — Telegram bot to'ldiradigan o'sha qoralama."""
        tur = (rk.UCHUN if self.uchun.isChecked() else
               rk.UMUMIY if self.umumiy.isChecked() else rk.SHAXSIY)
        p = self._parametrlar() if tur == rk.UMUMIY else None
        mahsulotlar = self.mahsulotlar.qatorlar()
        return rk.Qoralama(
            sana=self.sana.iso(), kim_toladi=self.kim.odam_id(),
            karta_id=self.joy.karta_id(),
            turi_id=self.turi.turi_id(), mahsulotlar=mahsulotlar,
            item_id=(mahsulotlar[0]["item_id"] if len(mahsulotlar) == 1
                     else None),
            nom=self.nom.text().strip(), summa=self.summa.qiymat(), tur=tur,
            kim_uchun=self.uchun_kim.odam_id() if tur == rk.UCHUN else None,
            usul=self.usul(),
            # Hech kim belgilanmagan bo'lsa — bo'sh lug'at: `tekshir()`
            # «kamida bitta odam» deb to'xtatadi (None uydagilarni olardi).
            parametrlar=p if p is not None or tur != rk.UMUMIY else {})

    def _saqla(self):
        # Tekshiruv va yozish — `core/rasxod_kirit.py` da, Telegram bot
        # bilan BITTA joyda.
        q = self.qoralama()
        try:
            rk.tekshir(self.db, q)
            if self.rasxod_id:
                rk.tahrirla(self.db, self.rasxod_id, q)
            else:
                self.rasxod_id = rk.saqla(self.db, q)
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
        self.joy = HamyonTanla(db)
        self.joy.odam_qoy(self.kim.odam_id())
        self.kim.currentIndexChanged.connect(
            lambda: self.joy.odam_qoy(self.kim.odam_id()))
        f.addRow("Sana", self.sana)
        f.addRow("Kim oldi", self.kim)
        f.addRow("Summa", self.summa)
        f.addRow("Qayerdan", self.sabab)
        f.addRow("Qayerga tushdi", self.joy)
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
                self.joy.odam_qoy(r["odam_id"])
                self.joy.tanla(r["karta_id"])
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
                    sabab=self.sabab.text().strip() or None,
                    karta_id=self.joy.karta_id())
            else:
                entries.kirim_qosh(self.db, self.sana.iso(), self.kim.odam_id(),
                                   self.summa.qiymat(),
                                   self.sabab.text().strip() or None,
                                   karta_id=self.joy.karta_id())
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


# ═══════════════════════════════════════════════════ tashqi qarz

class _Qatnashchilar(QWidget):
    """Umumiy tashqi qarz (yoki uning qaytarilishi) kimlarga qanday
    bo'linadi — rasxoddagidek: Teng / Foiz / Og'irlik / Aniq summa,
    har odam belgilanadi, ulushlar jonli ko'rinadi (`money.bol`).

    `tanlangan()` — belgilanganlar; `usul()` va `parametrlar()` —
    `entries.tashqi_*` ga beriladi. Teng bo'lsa `parametrlar()` ham
    {id: 1.0} qaytaradi."""

    USULLAR = ((money.USUL_TENG, "Teng"), (money.USUL_FOIZ, "Foiz"),
               (money.USUL_OGIRLIK, "Og'irlik"), (money.USUL_ANIQ, "Aniq summa"))

    def __init__(self, db, sana: str, summa_fn, tanlangan=None, parent=None,
                 usul: str = money.USUL_TENG,
                 qiymatlar: dict[int, float] | None = None):
        super().__init__(parent)
        self.db = db
        self.summa_fn = summa_fn
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.usul_t: dict[str, QRadioButton] = {}
        guruh = QButtonGroup(self)
        for kod, nom in self.USULLAR:
            b = QRadioButton(nom)
            guruh.addButton(b)
            b.setChecked(kod == usul)
            b.toggled.connect(self.yangila)
            self.usul_t[kod] = b
        v.addWidget(qator(*self.usul_t.values(), None))
        uyda = set(tanlangan if tanlangan is not None
                   else splitting.qatnashchilar(db, sana))
        setka = QGridLayout()
        setka.setHorizontalSpacing(10)
        setka.setVerticalSpacing(5)
        self.belgilar: dict[int, QCheckBox] = {}
        self.qiymat: dict[int, QLineEdit] = {}
        self.ulush: dict[int, QLabel] = {}
        for r, o in enumerate(db.q(
                "SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id")):
            cb = QCheckBox(o["nom"])
            cb.setChecked(o["id"] in uyda)
            cb.toggled.connect(self.yangila)
            le = QLineEdit()
            le.setAlignment(Qt.AlignRight)
            le.setFixedWidth(110)
            if qiymatlar and o["id"] in qiymatlar:
                le.setText(str(qiymatlar[o["id"]]).rstrip("0").rstrip(".")
                           if isinstance(qiymatlar[o["id"]], float)
                           else str(qiymatlar[o["id"]]))
            le.textChanged.connect(self.yangila)
            lb = QLabel("—")
            lb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lb.setMinimumWidth(110)
            setka.addWidget(cb, r, 0)
            setka.addWidget(le, r, 1)
            setka.addWidget(lb, r, 2)
            self.belgilar[o["id"]] = cb
            self.qiymat[o["id"]] = le
            self.ulush[o["id"]] = lb
        quti = QWidget()
        quti.setLayout(setka)
        v.addWidget(quti)
        self.natija = izoh("")
        v.addWidget(self.natija)
        self.yangila()

    def tanlangan(self) -> list[int]:
        return [i for i, cb in self.belgilar.items() if cb.isChecked()]

    def usul(self) -> str:
        return next(k for k, b in self.usul_t.items() if b.isChecked())

    def parametrlar(self) -> dict[int, float]:
        u = self.usul()
        if u == money.USUL_TENG:
            return {i: 1.0 for i in self.tanlangan()}
        p = {}
        for i in self.tanlangan():
            t = self.qiymat[i].text().strip().replace(",", ".").replace(" ", "")
            try:
                p[i] = float("".join(c for c in t if c.isdigit() or c == ".")
                             or 0)
            except ValueError:
                p[i] = 0.0
        return p

    def yangila(self, *_):
        teng = self.usul() == money.USUL_TENG
        for i, le in self.qiymat.items():
            le.setVisible(not teng)
            le.setEnabled(self.belgilar[i].isChecked())
            le.setPlaceholderText({money.USUL_FOIZ: "%",
                                   money.USUL_ANIQ: "so'm"}.get(self.usul(), "—"))
            self.ulush[i].setText("—")
        summa, p = self.summa_fn(), self.parametrlar()
        if not p:
            self.natija.setText("Kamida bitta odam tanlang.")
            return
        if summa <= 0:
            self.natija.setText("")
            return
        try:
            bolinish = money.bol(summa, self.usul(), p)
        except ValueError as e:
            self.natija.setText(f"⚠ {e}")
            return
        for u in bolinish:
            if u.odam_id in self.ulush:
                self.ulush[u.odam_id].setText(money.fmt(u.summa))
        self.natija.setText(
            f"Yig'indi: {money.fmt_som(sum(u.summa for u in bolinish))}")

    def tekshir(self) -> str | None:
        """Saqlashdan oldin: xato matni yoki None."""
        p = self.parametrlar()
        if not p or not any(p.values()):
            return "Kamida bitta odam tanlangan bo'lishi kerak."
        try:
            money.bol(max(1, self.summa_fn()), self.usul(), p)
        except ValueError as e:
            return str(e)
        return None


class TashqiUmumiyDialog(QDialog):
    """Mavjud tashqi qarzni umumiy yoki shaxsiy qilish."""

    def __init__(self, db, qarz_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.qarz_id = qarz_id
        q = db.q1("SELECT q.*, o.nom FROM tashqi_qarz q JOIN odam o ON o.id=q.odam_id"
                  " WHERE q.id=?", qarz_id)
        bor_ulush = {r["odam_id"]: r["summa"] for r in db.q(
            "SELECT odam_id, summa FROM tashqi_ulush WHERE qarz_id=?"
            " AND tolov_id IS NULL AND ochirilgan=0", qarz_id)}
        bor = list(bor_ulush)
        tengmi = (not bor_ulush or
                  max(bor_ulush.values()) - min(bor_ulush.values()) <= 1)
        self.setWindowTitle("Umumiy yoki shaxsiy")
        self.setMinimumWidth(430)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        v.addWidget(sarlavha(f"{q['kimdan']} — {money.fmt_som(q['summa'])}"))
        v.addWidget(izoh(f"{q['nom']} olgan. Umumiy bo'lsa pul ham, qarz ham "
                         f"tanlanganlarga bo'linadi — har kimning qo'liga o'z "
                         f"ulushi, qaytarishda ham har kimdan o'z ulushi."))
        self.umumiy = QCheckBox("Umumiy qarz — hammaga bo'linadi")
        self.umumiy.setChecked(bool(q["umumiy"]))
        v.addWidget(self.umumiy)
        self.odamlar = _Qatnashchilar(
            db, q["sana"], lambda: int(q["summa"]), bor or None,
            usul=money.USUL_TENG if tengmi else money.USUL_ANIQ,
            qiymatlar=None if tengmi else bor_ulush)
        v.addWidget(self.odamlar)
        self.umumiy.toggled.connect(self.odamlar.setEnabled)
        self.odamlar.setEnabled(self.umumiy.isChecked())
        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _saqla(self):
        if self.umumiy.isChecked() and (x := self.odamlar.tekshir()):
            xato_koraset(self, x)
            return
        try:
            entries.tashqi_umumiy_qoy(
                self.db, self.qarz_id,
                self.odamlar.tanlangan() if self.umumiy.isChecked() else None,
                usul=self.odamlar.usul(),
                parametrlar=self.odamlar.parametrlar())
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class _TashqiForma(QWidget):
    """Yangi tashqi qarz maydonlari — oyna ham, kichik dialog ham shundan."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.kim = OdamTanla(db)
        # Oldin yozilgan ismlar taklif qilinadi, yangisini ham yozsa bo'ladi.
        self.kimdan = QComboBox()
        self.kimdan.setEditable(True)
        self.kimdan.addItems(ledger.tashqi_kimdanlar(db))
        self.kimdan.setCurrentText("")
        self.kimdan.lineEdit().setPlaceholderText("masalan: Aziz aka")
        self.summa = PulEdit()
        self.sabab = QLineEdit()
        f.addRow("Kimdan olindi", self.kimdan)
        f.addRow("Qancha qaytarish kerak", self.summa)
        f.addRow("Kim oldi", self.kim)
        f.addRow("Sana", self.sana)
        f.addRow("Sabab", self.sabab)
        v.addLayout(f)

        # Umumiy: pul ham, qarz ham hammaniki — rasxoddagidek bo'linadi.
        self.umumiy = QCheckBox("Umumiy qarz — pul va qarz hammaga bo'linadi")
        v.addWidget(self.umumiy)
        self.odamlar = _Qatnashchilar(db, self.sana.iso(), self.summa.qiymat)
        self.odamlar.setVisible(False)
        v.addWidget(self.odamlar)
        self.umumiy.toggled.connect(self.odamlar.setVisible)
        self.summa.textChanged.connect(lambda *_: self.odamlar.yangila())

    def saqla(self, ota) -> int | None:
        """Yozadi va id qaytaradi; xato bo'lsa ko'rsatib `None`."""
        if not self.kimdan.currentText().strip():
            xato_koraset(ota, "Kimdan olingani yozilmagan.")
            return None
        if self.summa.qiymat() <= 0:
            xato_koraset(ota, "Qancha qaytarish kerakligi kiritilmagan.")
            return None
        umumiy = self.umumiy.isChecked()
        if umumiy and (x := self.odamlar.tekshir()):
            xato_koraset(ota, x)
            return None
        try:
            return entries.tashqi_qarz_qosh(
                self.db, self.sana.iso(), self.kim.odam_id(),
                self.kimdan.currentText(), self.summa.qiymat(),
                self.sabab.text().strip() or None, umumiy=umumiy,
                qatnashchilar=self.odamlar.tanlangan() if umumiy else None,
                usul=self.odamlar.usul(),
                parametrlar=self.odamlar.parametrlar() if umumiy else None)
        except Exception as e:
            xato_koraset(ota, str(e))
            return None

    def tozala(self) -> str:
        """Saqlangandan keyin — keyingi qarz uchun bo'sh forma.

        Qaytaradi: hozirgina yozilgan «kimdan» (xabar uchun).
        """
        from PySide6.QtCore import QSignalBlocker
        joriy = self.kimdan.currentText().strip()
        with QSignalBlocker(self.kimdan):
            self.kimdan.clear()
            self.kimdan.addItems(ledger.tashqi_kimdanlar(self.db))
            self.kimdan.setCurrentText("")
        self.summa.qoy(0)
        self.sabab.clear()
        self.umumiy.setChecked(False)
        return joriy


class TashqiQarzDialog(QDialog):
    """Uydan tashqaridagi odamdan olingan qarz: kim oldi, kimdan."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Tashqaridan qarz olish")
        self.setMinimumWidth(430)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        v.addWidget(izoh("Shaxsiy qarz — pul va qarz faqat olganniki. Umumiy "
                         "qarz — pul ham, qarz ham hammaga bo'linadi."))
        self.forma = _TashqiForma(db)
        v.addWidget(self.forma)
        for nom in ("sana", "kim", "kimdan", "summa", "sabab", "umumiy",
                    "odamlar"):
            setattr(self, nom, getattr(self.forma, nom))

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _saqla(self):
        if self.forma.saqla(self) is not None:
            self.accept()


class TashqiQarzOyna(QDialog):
    """Tashqi qarzlar — alohida oyna: yozish, kimga qancha, qaytarish, yopish.

    Qarz varag'idagi «Tashqaridan qarz» tugmasi ochadi. Hamma yozuv
    `entries` orqali (undo ishlaydi); oyna yopilganda chaqiruvchi
    `ozgardi` ga qarab dasturni yangilaydi.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QScrollArea
        self.db = db
        self.ozgardi = False
        self.setWindowTitle("Tashqaridan olingan qarzlar")
        self.resize(940, 780)
        self.setMinimumSize(760, 560)

        tashqi = QVBoxLayout(self)
        tashqi.setContentsMargins(0, 0, 0, 0)
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setFrameShape(QScrollArea.NoFrame)
        ichi = QWidget()
        ichi.setObjectName("Shaffof")
        ichi.setStyleSheet("QWidget#Shaffof { background: transparent; }")
        v = QVBoxLayout(ichi)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)

        v.addWidget(sarlavha("Tashqaridan olingan qarzlar"))
        v.addWidget(izoh("Uydan tashqaridagi odamdan olingan qarz. Pul olganning "
                         "qo'liga tushadi; uydagilar orasidagi qarzga tegmaydi."))
        self.xabar = Xabar()
        v.addWidget(self.xabar)

        # ── kimga qancha qaytarish kerak ─────────────────────────────
        k = Karta("Kimga qancha qaytarish kerak")
        self.jami = QLabel("")
        self.jami.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        k.qosh(self.jami)
        self.kimga_jadval = Jadval(["Kimga", "Nechta qarz", "Qaytarish kerak"],
                                   pul_ustunlar={2},
                                   bosh_matn="✔ Hech kimga qarz yo'q")
        self.kimga_jadval.kengliklar(0, 130, 160)
        self.kimga_jadval.setMinimumHeight(120)
        k.qosh(self.kimga_jadval)
        v.addWidget(k)

        # ── yangi qarz ───────────────────────────────────────────────
        y = Karta("Yangi qarz yozish")
        self.forma = _TashqiForma(db)
        y.qosh(self.forma)
        qosh = tugma("Qarzni yozish", asosiy=True)
        qosh.clicked.connect(self._qosh)
        y.qosh(qator(None, qosh))
        v.addWidget(y)

        # ── qarzlar ──────────────────────────────────────────────────
        q = Karta("Qarzlar")
        self.jadval = Jadval(
            ["Sana", "Kimdan", "Kim oldi", "Sabab", "Olingan", "Qaytarilgan",
             "Qoldiq"], pul_ustunlar={4, 5, 6})
        self.jadval.kengliklar(100, 140, 130, 0, 110, 110, 110)
        self.jadval.setMinimumHeight(180)
        q.qosh(self.jadval)
        self.hammasi = QCheckBox("Yopilganlari ham ko'rinsin")
        self.hammasi.toggled.connect(self._yangila)
        och = tugma("O'chirish", xavfli=True)
        umu = tugma("Umumiy / shaxsiy")
        qis = tugma("Qisman qaytarish")
        yop = tugma("Qarzni yopish", asosiy=True)
        och.clicked.connect(self._ochir)
        umu.clicked.connect(self._umumiy)
        qis.clicked.connect(self._qisman)
        yop.clicked.connect(self._yop)
        q.qosh(qator(self.hammasi, None, och, umu, qis, yop))
        v.addWidget(q)

        # ── qaytarilgan to'lovlar ────────────────────────────────────
        t = Karta("Qaytarilgan to'lovlar")
        self.tolov_jadval = Jadval(
            ["Sana", "Kim qaytardi", "Kimga", "Izoh", "Summa"], pul_ustunlar={4})
        self.tolov_jadval.kengliklar(100, 130, 140, 0, 130)
        self.tolov_jadval.setMinimumHeight(140)
        t.qosh(self.tolov_jadval)
        to = tugma("To'lovni o'chirish", xavfli=True)
        to.clicked.connect(self._tolov_ochir)
        t.qosh(qator(None, to))
        v.addWidget(t)

        yopish = QDialogButtonBox()
        yopish.addButton("Yopish", QDialogButtonBox.RejectRole)
        yopish.rejected.connect(self.reject)
        v.addWidget(yopish)

        aylanma.setWidget(ichi)
        tashqi.addWidget(aylanma)
        self._yangila()

    def _yangila(self):
        from ui.eski.sahifa_asosiy import sana_qisqa
        hammasi = ledger.tashqi_qarzlar(self.db)
        ochiq = [r for r in hammasi if r["qoldiq"] > 0]
        korinadi = hammasi if self.hammasi.isChecked() else ochiq
        self.jadval.tuldir(
            [[sana_qisqa(r["sana"]), r["kimdan"],
              r["odam_nom"] + ("  · umumiy" if r["umumiy"] else ""),
              r["sabab"] or "—", r["summa"], r["qaytgan"],
              r["qoldiq"] or "✔ yopildi"] for r in korinadi],
            [r["id"] for r in korinadi])

        kimga = ledger.tashqi_kimga_qaytarish(self.db)
        self.kimga_jadval.tuldir(
            [[x["kimdan"], f"{x['soni']} ta", x["qoldiq"]] for x in kimga])
        jami = sum(x["qoldiq"] for x in kimga)
        self.jami.setText(f"Jami qaytarish kerak: {money.fmt_som(jami)}"
                          if jami else "Tashqi qarz yo'q")

        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT t.*, q.kimdan, o.nom FROM tashqi_tolov t"
                " JOIN tashqi_qarz q ON q.id=t.tashqi_qarz_id"
                " JOIN odam o ON o.id=q.odam_id"
                " WHERE t.ochirilgan=0 AND q.ochirilgan=0"
                " ORDER BY t.sana DESC, t.id DESC"):
            qatorlar.append([sana_qisqa(r["sana"]), r["nom"], r["kimdan"],
                             r["izoh"] or "—", r["summa"]])
            idlar.append(r["id"])
        self.tolov_jadval.tuldir(qatorlar, idlar)

    def _ozgardi(self, matn: str):
        self.ozgardi = True
        self._yangila()
        self.xabar.korsat(matn, "ok", 3500)

    def _tanlangan(self):
        qid = self.jadval.tanlangan_id()
        if not qid:
            self.xabar.korsat("Avval jadvaldan qarzni tanlang.", "ogoh", 3000)
        return qid

    def _qosh(self):
        if self.forma.saqla(self) is None:
            return
        kimdan = self.forma.tozala()
        self._ozgardi(f"✔ {kimdan} dan olingan qarz yozildi.")

    def _yop(self, *, soramasdan: bool = False):
        """Tanlangan qarzning butun qoldig'i qaytarildi — qarz yopiladi."""
        from datetime import date
        qid = self._tanlangan()
        if not qid:
            return
        q = self.db.q1("SELECT kimdan FROM tashqi_qarz WHERE id=?", qid)
        qoldiq = entries.tashqi_qoldiq(self.db, qid)
        if qoldiq <= 0:
            self.xabar.korsat("Bu qarz allaqachon yopilgan.", "ogoh", 3000)
            return
        if not soramasdan and not tasdiq(
                self, f"{q['kimdan']} ga {money.fmt_som(qoldiq)} qaytarildi "
                      f"deb qarz yopilsinmi?"):
            return
        try:
            entries.tashqi_qarz_yop(self.db, qid, date.today().isoformat())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self._ozgardi(f"✔ {q['kimdan']} ga qarz yopildi.")

    def _qisman(self):
        qid = self._tanlangan()
        if not qid:
            return
        if entries.tashqi_qoldiq(self.db, qid) <= 0:
            self.xabar.korsat("Bu qarz to'liq qaytarilgan.", "ogoh", 3000)
            return
        if TashqiTolovDialog(self.db, qid, self).exec():
            self._ozgardi("✔ Qaytarish yozildi.")

    def _umumiy(self):
        qid = self._tanlangan()
        if qid and TashqiUmumiyDialog(self.db, qid, self).exec():
            self._ozgardi("✔ Saqlandi.")

    def _ochir(self):
        qid = self._tanlangan()
        if qid and tasdiq(self, "Tashqi qarz yozuvi o'chirilsinmi?\n\n"
                                "Uning qaytarilgan to'lovlari ham o'chadi."):
            entries.tashqi_qarz_ochir(self.db, qid)
            self._ozgardi("✔ O'chirildi.")

    def _tolov_ochir(self):
        tid = self.tolov_jadval.tanlangan_id()
        if not tid:
            self.xabar.korsat("Avval to'lovni tanlang.", "ogoh", 3000)
            return
        if tasdiq(self, "Qaytarish yozuvi o'chirilsinmi?"):
            entries.tashqi_tolov_ochir(self.db, tid)
            self._ozgardi("✔ To'lov o'chirildi.")


class TashqiTolovDialog(QDialog):
    """Tashqi qarzni qaytarish — to'liq yoki qisman."""

    def __init__(self, db, qarz_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.qarz_id = qarz_id
        q = db.q1("SELECT q.kimdan, q.umumiy, q.sana, o.nom FROM tashqi_qarz q"
                  " JOIN odam o ON o.id=q.odam_id WHERE q.id=?", qarz_id)
        self.qoldiq = entries.tashqi_qoldiq(db, qarz_id)
        self.setWindowTitle("Tashqi qarzni qaytarish")
        self.setMinimumWidth(430)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        v.addWidget(izoh(f"{q['nom']} → {q['kimdan']} · qoldiq "
                         f"{money.fmt_som(self.qoldiq)}"))
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.summa = PulEdit(self.qoldiq)
        self.izohm = QLineEdit()
        f.addRow("Sana", self.sana)
        f.addRow("Summa", self.summa)
        f.addRow("Izoh", self.izohm)
        v.addLayout(f)

        # Umumiy qarz: to'lov kimdan qanchadan ayiriladi — rasxoddagidek.
        # Birlamchi — qarz qanday bo'lingan bo'lsa shunday.
        self.odamlar = None
        if q["umumiy"]:
            ul = {r["odam_id"]: r["summa"] for r in db.q(
                "SELECT odam_id, summa FROM tashqi_ulush WHERE qarz_id=?"
                " AND tolov_id IS NULL AND ochirilgan=0", qarz_id)}
            tengmi = not ul or max(ul.values()) - min(ul.values()) <= 1
            v.addWidget(bolim("Kimdan qanchadan ayiriladi"))
            self.odamlar = _Qatnashchilar(
                db, q["sana"], self.summa.qiymat, list(ul) or None,
                usul=money.USUL_TENG if tengmi else money.USUL_OGIRLIK,
                qiymatlar=None if tengmi else {k: float(x) for k, x in ul.items()})
            self.summa.ozgardi.connect(self.odamlar.yangila)
            v.addWidget(self.odamlar)

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
        if self.odamlar is not None and (x := self.odamlar.tekshir()):
            xato_koraset(self, x)
            return
        try:
            entries.tashqi_tolov_qosh(
                self.db, self.qarz_id, self.sana.iso(), self.summa.qiymat(),
                self.izohm.text().strip() or None,
                usul=self.odamlar.usul() if self.odamlar else None,
                parametrlar=(self.odamlar.parametrlar() if self.odamlar
                             else None))
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


# ═══════════════════════════════════════════════════════ rejaga band

class RejagaBandOyna(QDialog):
    """«Shaxsiy» dagi «Rejaga band» kartasi: band pul NIMADAN — umumiy
    rejadan teng ulush va shaxsiy reja, kategoriyalar bo'yicha (reja,
    sarflangan, qolgan). Hisob `plan.band_tafsilot()` da — bu oyna faqat
    chizadi."""

    def __init__(self, db, odam_id: int, parent=None):
        super().__init__(parent)
        t = plan.band_tafsilot(db, odam_id)
        nom = db.skalyar("SELECT nom FROM odam WHERE id=?", odam_id,
                         birlamchi="")
        self.setWindowTitle(f"Rejaga band — {nom}")
        self.setMinimumSize(640, 560)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        v.addWidget(sarlavha("Rejaga band"))
        jami = QLabel(money.fmt_som(t["jami"]))
        jami.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(jami)
        h = t["hisob"]
        qism = [f"umumiy rejadan {money.fmt(t['umumiy_ulush'])}",
                f"shaxsiy rejadan {money.fmt(t['shaxsiy_qolgan'])}"]
        v.addWidget(izoh(" · ".join(qism)))
        holat = [f"qo'lingizdagi puldan ayirildi {money.fmt(h['ayirildi'])}"]
        if h["qoplaydi"]:
            holat.append(f"shundan boshqalar o'rniga {money.fmt(h['qoplaydi'])}")
        if h["qarz"]:
            holat.append(f"{money.fmt(h['qarz'])} hisobda yo'q — qarzga yozildi")
        e = izoh(" · ".join(holat))
        v.addWidget(e)

        from PySide6.QtWidgets import QScrollArea
        ichki = QWidget()
        ichki.setObjectName("Shaffof")
        ichki.setStyleSheet("QWidget#Shaffof { background: transparent; }")
        q = QVBoxLayout(ichki)
        q.setContentsMargins(0, 0, 8, 0)
        q.setSpacing(12)
        q.addWidget(self._karta(
            "Umumiy reja",
            f"Sarflanmagan {money.fmt_som(t['umumiy_qolgan'])} — "
            f"{t['odamlar_soni']} kishiga teng: sizga "
            f"{money.fmt_som(t['umumiy_ulush'])}",
            t["umumiy"], t["umumiy_reja"], t["umumiy_fakt"]))
        q.addWidget(self._karta(
            "Shaxsiy reja",
            f"Sarflanmagan {money.fmt_som(t['shaxsiy_qolgan'])} — "
            f"hammasi sizdan",
            t["shaxsiy"], t["shaxsiy_reja"], t["shaxsiy_fakt"]))
        q.addStretch(1)
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setFrameShape(QScrollArea.NoFrame)
        aylanma.setWidget(ichki)
        v.addWidget(aylanma, 1)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(None, yop))

    @staticmethod
    def _karta(sarlavha_: str, izohi: str, qatorlar: list[dict],
               reja: int, fakt: int) -> Karta:
        k = Karta(sarlavha_)
        k.qosh(izoh(izohi))
        if not qatorlar:
            k.qosh(izoh("Bu oy reja yo'q."))
            return k
        j = Jadval(["Kategoriya", "Reja", "Sarflandi", "Qolgan"],
                   pul_ustunlar={1, 2, 3})
        j.ichkarida()
        j.kengliklar(0, 110, 110, 110)
        j.tuldir([[f"{x['belgi'] or ''} {x['nom']}".strip(), x["reja"],
                   x["fakt"], x["qolgan"]] for x in qatorlar]
                 + [["Jami", reja, fakt, reja - fakt]],
                 rangli_ustunlar={3})
        j.setFixedHeight(40 + 42 * (len(qatorlar) + 1))
        k.qosh(j)
        return k


# ═══════════════════════════════════════════════════════ qarzlarim

class QarzlarimOyna(QDialog):
    """«Shaxsiy» dagi «Qarzim» tugmasi: bitta odamning HAMMA qarzi —
    uy ichidagi (kimga qancha) va tashqi (kimdan olgan) — va shu yerda
    yopish. Hisob `ledger.odam_qarzlari()` dan; yozish mavjud
    oynalar/funksiyalar orqali (`TolovDialog`, `TashqiTolovDialog`,
    `entries.tashqi_qarz_yop`) — qoidalar ikki joyda yozilmaydi."""

    def __init__(self, db, odam_id: int, parent=None):
        super().__init__(parent)
        self.db, self.odam_id = db, odam_id
        self.ozgardi = False
        nom = db.skalyar("SELECT nom FROM odam WHERE id=?", odam_id,
                         birlamchi="")
        self.setWindowTitle(f"Qarzlarim — {nom}")
        self.setMinimumSize(620, 520)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        self.jami = QLabel()
        self.jami.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        self.jami_izoh = izoh("")
        v.addWidget(sarlavha("Jami qarzim"))
        v.addWidget(self.jami)
        v.addWidget(self.jami_izoh)

        from PySide6.QtWidgets import QScrollArea
        self.ichki = QWidget()
        self.ichki.setObjectName("Shaffof")
        self.ichki.setStyleSheet("QWidget#Shaffof { background: transparent; }")
        self.qavat = QVBoxLayout(self.ichki)
        self.qavat.setContentsMargins(0, 0, 8, 0)
        self.qavat.setSpacing(12)
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setFrameShape(QScrollArea.NoFrame)
        aylanma.setWidget(self.ichki)
        v.addWidget(aylanma, 1)

        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(None, yop))
        self._qur()

    def _qur(self):
        from ui.eski.widgets import yoq
        while self.qavat.count():
            x = self.qavat.takeAt(0)
            if x.widget():
                yoq(x.widget())
        q = plan.odam_qarzlari(self.db, self.odam_id)
        self.jami.setText(money.fmt_som(q["jami"]))
        qism = [f"uy ichida {money.fmt(q['ichki_jami'])}",
                f"tashqi {money.fmt(q['tashqi_jami'])}"]
        if q["reja_jami"]:
            qism.append(f"rejadan {money.fmt(q['reja_jami'])}")
        if q["menga_jami"]:
            qism.append(f"sizga qarzdorlar {money.fmt(q['menga_jami'])}")
        self.jami_izoh.setText(" · ".join(qism))

        k = Karta("Uy ichida — men qarzdorman")
        for j in q["ichki"]:
            taf = tugma("Tafsilot")
            taf.clicked.connect(lambda _c=False, j=j: self._tafsilot(
                j.qarzdor_id, j.kreditor_id))
            yop = tugma("To'lab yopish", asosiy=True)
            yop.clicked.connect(lambda _c=False, j=j: self._tola(
                j.qarzdor_id, j.kreditor_id, j.summa))
            k.qosh(qator(yorliq(j.kreditor_nom), None,
                         QLabel(money.fmt_som(j.summa)), taf, yop))
        if not q["ichki"]:
            k.qosh(izoh("Uy ichida hech kimga qarzingiz yo'q."))
        self.qavat.addWidget(k)

        if q["reja_jami"]:
            k = Karta("Rejaga band — hisobda yo'q")
            k.qosh(qator(yorliq(
                f"Oy rejasidagi ulushingizga qo'lingizda pul yetmadi"
                + (f" — {q['reja_kimga']} qoplaydi" if q["reja_kimga"]
                   else "")), None, QLabel(money.fmt_som(q["reja_jami"]))))
            k.qosh(izoh("Reja sarflanib, puli hisobingizga tushgach bu qarz "
                        "o'zi kamayadi."))
            self.qavat.addWidget(k)

        k = Karta("Tashqi qarzlar — uydan tashqaridagilardan")
        for t in q["tashqi"]:
            iso = str(t["sana"])[:10]
            qisman = tugma("Qisman qaytarish")
            qisman.clicked.connect(lambda _c=False, t=t: self._qisman(t["id"]))
            yop = tugma("Qarzni yopish", asosiy=True)
            yop.clicked.connect(lambda _c=False, t=t: self._tashqi_yop(t))
            nom = f"{t['kimdan']}  ·  {iso[8:10]}.{iso[5:7]}"
            if t["umumiy"]:
                nom += (f"  ·  umumiy, jami qoldiq "
                        f"{money.fmt(t['jami_qoldiq'])}")
            k.qosh(qator(yorliq(nom), None,
                         QLabel(money.fmt_som(t["qoldiq"])), qisman, yop))
        if not q["tashqi"]:
            k.qosh(izoh("Tashqi qarz yo'q."))
        yangi = tugma("Tashqi qarzlar oynasi…")
        yangi.setToolTip("Yangi tashqi qarz yozish, tarix")
        yangi.clicked.connect(self._tashqi_oyna)
        k.qosh(qator(None, yangi))
        self.qavat.addWidget(k)

        if q["menga"]:
            k = Karta("Sizga qarzdorlar")
            for j in q["menga"]:
                taf = tugma("Tafsilot")
                taf.clicked.connect(lambda _c=False, j=j: self._tafsilot(
                    j.qarzdor_id, j.kreditor_id))
                oldim = tugma("Qaytarib berdi")
                oldim.clicked.connect(lambda _c=False, j=j: self._tola(
                    j.qarzdor_id, j.kreditor_id, j.summa))
                k.qosh(qator(yorliq(j.qarzdor_nom), None,
                             QLabel(money.fmt_som(j.summa)), taf, oldim))
            self.qavat.addWidget(k)
        self.qavat.addStretch(1)

    def _yangi(self):
        self.ozgardi = True
        self._qur()

    def _tola(self, kimdan: int, kimga: int, summa: int):
        if TolovDialog(self.db, kimdan, kimga, summa, self).exec():
            self._yangi()

    def _tafsilot(self, qarzdor: int, kreditor: int):
        d = JuftTafsilot(self.db, qarzdor, kreditor, self)
        d.exec()
        self._yangi()

    def _qisman(self, qarz_id: int):
        if TashqiTolovDialog(self.db, qarz_id, self).exec():
            self._yangi()

    def _tashqi_yop(self, t: dict):
        qoldiq = t.get("jami_qoldiq", t["qoldiq"])
        if not tasdiq(self, f"{t['kimdan']}dan olingan qarzning qolgan "
                            f"{money.fmt_som(qoldiq)} si bugun "
                            f"qaytarildi deb yopilsinmi?"
                            + ("\n\nUmumiy qarz: har kimdan o'z ulushi "
                               "ayiriladi." if t["umumiy"] else "")):
            return
        try:
            from datetime import date
            entries.tashqi_qarz_yop(self.db, t["id"], date.today().isoformat())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self._yangi()

    def _tashqi_oyna(self):
        d = TashqiQarzOyna(self.db, self)
        d.exec()
        self._yangi()


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

        mahsulotlar = rk.rasxod_mahsulotlari(db, rasxod_id)
        if mahsulotlar:
            m_karta = Karta("Mahsulotlar")
            for x in mahsulotlar:
                nom = (x["nom"] if x["miqdor"] == 1
                       else f"{x['nom']}  × {x['miqdor']}")
                m_karta.qosh(qator(yorliq(nom), None,
                                   QLabel(money.fmt_som(x["summa"]))))
            v.addWidget(m_karta)

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

    Faqat HALI TO'LANMAGAN qarzlar (`ledger.juft_tolanmagan()`):
    to'lovlar eng eski qarzdan boshlab ayirilgan, to'liq yopilgani
    ko'rinmaydi. Qatorlar yig'indisi aynan yuqoridagi songa teng.
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

        tarkib = ledger.juft_tolanmagan(db, qarzdor_id, kreditor_id)
        jami = sum(x["summa"] for x in tarkib)

        self.jami_yorliq = QLabel(money.fmt_som(jami))
        self.jami_yorliq.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(self.jami_yorliq)

        v.addWidget(izoh(f"{len(tarkib)} ta to'lanmagan yozuv"))

        jadval = Jadval(["Sana", "Turi", "Nima uchun", "Holati", "Summa"],
                        pul_ustunlar={4},
                        bosh_matn="To'lanmagan qarz yo'q")
        self.jadval = jadval
        jadval.kengliklar(105, 125, 0, 165, 130)
        def kun(s) -> str:
            """ISO sanani dastur ko'rinishiga: 22.08.2026."""
            s = str(s or "")[:10]
            return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 else s

        qatorlar = []
        for x in tarkib:
            if x["summa"] < x["asl"]:
                holat = f"Qisman · asli {money.fmt(x['asl'])}"
            else:
                holat = "To'lanmagan"
            turi, nom = x["turi"], x["nom"]
            if turi == "To'lov":
                # Bu ro'yxatda to'lov faqat kreditordan qarzdorga
                # berilgan pul bo'lib chiqadi (masalan ortiqcha to'lov) —
                # «To'lov · To'lov» deb yozilsa nega qarz ekani bilinmaydi.
                turi = "Berilgan pul"
                berdi = f"{self.kreditor_nom} → {self.qarzdor_nom}"
                nom = berdi if nom == "To'lov" else f"{berdi}  ({nom})"
            if x["izoh"]:
                nom = f"{nom}  ({x['izoh']})"
            qatorlar.append([kun(x["sana"]), turi, nom, holat,
                             x["summa"]])
        jadval.tuldir(qatorlar)
        v.addWidget(jadval, 1)

        v.addWidget(izoh(
            "Faqat hali to'lanmagan qarzlar. To'lovlar va teskari "
            "yo'nalishdagi rasxodlar eng eski qarzdan boshlab ayirilgan — "
            "«Qisman» qatorda qolgan qismi turibdi. "
            "Qatorlar yig'indisi yuqoridagi songa teng."))

        t_tolov = tugma("To'lov yozish", asosiy=True)
        t_tolov.clicked.connect(self._tolov)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(t_tolov, None, yop))

    def _tolov(self):
        self.tolov_soraldi = True
        self.accept()


class KategoriyaRasxodlari(QDialog):
    """Analitikadagi bo'lak / kategoriya qatorining ICHI — har bir rasxod.

    Ro'yxat `ledger.kategoriya_rasxodlari()` dan, analitika bilan BITTA
    manbadan: qatorlar yig'indisi bosilgan bo'lakdagi songa teng. Odam
    tanlangan bo'lsa «Summa» — uning hissasi, «Butun summa» — rasxodning
    o'zi. Rasxod shu yerdan tahrirlanadi (ikki marta bosish yoki
    «Tahrirlash»); saqlangach ro'yxat o'zi yangilanadi, `ozgardi` esa
    chaqiruvchiga butun dasturni yangilash kerakligini aytadi.

    Bir nechta qatorni tanlab (Ctrl/Shift) «Kategoriyani o'zgartirish»
    — hammasi bitta undo qadamida (`entries.rasxod_turi_qoy`).
    """

    def __init__(self, db, nom: str, turi_idlar: list, boshi: str,
                 oxiri: str, odam_id: int | None = None,
                 qism: str = "hammasi", parent=None):
        super().__init__(parent)
        self.db = db
        self.turi_idlar = list(turi_idlar)
        self.boshi, self.oxiri = boshi, oxiri
        self.odam_id, self.qism = odam_id, qism
        self.ozgardi = False

        self.setWindowTitle(nom)
        self.setMinimumSize(860, 560)
        v = QVBoxLayout(self)
        v.setSpacing(12)

        bosh = sarlavha(nom)
        bosh.setWordWrap(True)
        v.addWidget(bosh)
        self.jami_yorliq = QLabel()
        self.jami_yorliq.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(self.jami_yorliq)
        self.soni_izoh = izoh("")
        v.addWidget(self.soni_izoh)

        ustunlar = ["Sana", "Nima uchun", "Kategoriya", "Kim to'ladi", "Turi",
                    "Summa"]
        kengliklar = [100, 0, 150, 120, 150, 120]
        if odam_id is not None:
            ustunlar.append("Butun summa")
            kengliklar.append(120)
        self.jadval = Jadval(ustunlar,
                             pul_ustunlar=set(range(5, len(ustunlar))),
                             bosh_matn="Bu oraliqda rasxod yo'q")
        self.jadval.kengliklar(*kengliklar)
        self.jadval.setSelectionMode(Jadval.ExtendedSelection)
        self.jadval.doubleClicked.connect(self._tahrirla)
        v.addWidget(self.jadval, 1)
        v.addWidget(izoh("Rasxodni tahrirlash uchun ustiga ikki marta "
                         "bosing. Kategoriyani o'zgartirish uchun bir yoki "
                         "bir nechtasini tanlang (Ctrl/Shift bilan)."))

        self.yangi_turi = KategoriyaTanla(db)
        t_turi = tugma("Kategoriyani o'zgartirish")
        t_turi.clicked.connect(self._turi_ozgartir)
        self.ogoh = Xabar()
        v.addWidget(qator("Yangi kategoriya:", self.yangi_turi, t_turi, None))
        v.addWidget(self.ogoh)

        t_tahrir = tugma("Tahrirlash", asosiy=True)
        t_tahrir.clicked.connect(self._tahrirla)
        t_tafsilot = tugma("Tafsilot")
        t_tafsilot.clicked.connect(self._tafsilot)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(t_tahrir, t_tafsilot, None, yop))
        self._toldir()

    def tanlangan_idlar(self) -> list[int]:
        qatorlar = sorted({i.row() for i in self.jadval.selectedIndexes()})
        idlar = []
        for r in qatorlar:
            it = self.jadval.item(r, 0)
            if it is not None and it.data(Qt.UserRole):
                idlar.append(it.data(Qt.UserRole))
        return idlar

    def _turi_ozgartir(self):
        idlar = self.tanlangan_idlar()
        if not idlar:
            xato_koraset(self, "Avval rasxodni tanlang (bir nechtasini "
                               "Ctrl yoki Shift bilan).")
            return
        turi_id = self.yangi_turi.turi_id()
        if turi_id is None:
            xato_koraset(self, "Yangi kategoriyani tanlang.")
            return
        try:
            n = entries.rasxod_turi_qoy(self.db, idlar, turi_id)
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        nom = self.yangi_turi.currentText()
        if n:
            self.ozgardi = True
            self._toldir()
            self.ogoh.korsat(f"✔ {n} ta rasxod «{nom}» ga o'tkazildi", "ok",
                             4000)
        else:
            self.ogoh.korsat(f"Tanlanganlar allaqachon «{nom}» da", "ogoh",
                             4000)

    @staticmethod
    def _kun(s) -> str:
        s = str(s or "")[:10]
        return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 else s

    @staticmethod
    def _turi(x: dict) -> str:
        if x["kim_uchun"] is not None:
            return f"{x['kim_uchun_nom'] or '?'} uchun"
        if x["qism"] == "shaxsiy":
            return "Shaxsiy"
        return "Umumiy ulush" if x["summa"] != x["jami"] else "Umumiy"

    def _toldir(self):
        rows = ledger.kategoriya_rasxodlari(
            self.db, self.turi_idlar, self.boshi, self.oxiri,
            self.odam_id, self.qism)
        qatorlar = []
        for x in rows:
            nom = x["nom"] or "—"
            if x["izoh"]:
                nom = f"{nom}  ({x['izoh']})"
            q = [self._kun(x["sana"]), nom, x["kategoriya"] or "—",
                 x["kim_toladi"], self._turi(x), x["summa"]]
            if self.odam_id is not None:
                q.append(x["jami"])
            qatorlar.append(q)
        self.jadval.tuldir(qatorlar, idlar=[x["id"] for x in rows])
        self.jami_yorliq.setText(money.fmt_som(sum(x["summa"] for x in rows)))
        self.soni_izoh.setText(f"{len(rows)} ta rasxod · "
                               f"{self._kun(self.boshi)} — {self._kun(self.oxiri)}")

    def _tahrirla(self, *_):
        rid = self.jadval.tanlangan_id()
        if not rid:
            xato_koraset(self, "Avval rasxodni tanlang.")
            return
        if RasxodDialog(self.db, rid, parent=self).exec():
            self.ozgardi = True
            self._toldir()

    def _tafsilot(self):
        rid = self.jadval.tanlangan_id()
        if not rid:
            xato_koraset(self, "Avval rasxodni tanlang.")
            return
        d = RasxodTafsilot(self.db, rid, parent=self)
        d.exec()
        if d.ozgardi:
            self.ozgardi = True
            self._toldir()
