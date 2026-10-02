"""«Hamyon» varag'i — pulim qayerda: naqd va kartalar (2026-10-01).

Hisob `core/hamyon.py` da: kartaning qoldig'i unga bog'langan kirim,
rasxod va o'tkazmalardan chiqadi, naqd esa — qolgani (jami − kartalar).
Bu varaq faqat chizadi va oynalarni ochadi.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout,
                               QGridLayout, QInputDialog, QLabel, QLineEdit,
                               QVBoxLayout, QWidget)

import money
from core import hamyon, plan
from ui.eski import theme
from ui.eski.dialogs import (KirimDialog, RasxodDialog, tasdiq,
                             xato_koraset)
from ui.eski.sahifa_asosiy import Sahifa, sana_qisqa, shaffof
from ui.eski.widgets import (HamyonTanla, Jadval, Karta, OdamTanla, PulEdit,
                             RaqamKarta, SanaEdit, izoh, qator, sarlavha,
                             tugma, yoq)

USTUN = 3          # kartalar to'rida bir qatorda nechta


def _bosiladigan(k: RaqamKarta, fn) -> RaqamKarta:
    k.setCursor(Qt.PointingHandCursor)
    k.mousePressEvent = lambda _e: fn()
    return k


# ═══════════════════════════════════════════════════════════ varaq

class HamyonSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        self.kim = OdamTanla(self.db)
        oid = plan.asosiy_odam(self.db)
        if oid is not None:
            self.kim.tanla(oid)
        self.kim.currentIndexChanged.connect(self.yangila)
        yangi = tugma("+ Karta qo'shish", asosiy=True)
        yangi.clicked.connect(self._karta_qosh)
        otk = tugma("⇄ O'tkazma")
        otk.setToolTip("Bankomatdan yechish, kartaga solish, karta → karta")
        otk.clicked.connect(lambda: self._otkazma())
        self.tana.addWidget(qator(sarlavha("Pulim qayerda"), None,
                                  "Kim:", self.kim, otk, yangi))
        self.jami_izoh = izoh("")
        self.tana.addWidget(self.jami_izoh)

        quti = shaffof(QWidget())
        self.naqd_k = RaqamKarta("💵 Naqd", 0, "")
        self.karta_k = _bosiladigan(RaqamKarta("💳 Kartalar", 0, ""),
                                    self._kartalarni_ochyop)
        hl = QGridLayout(quti)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setHorizontalSpacing(14)
        hl.addWidget(self.naqd_k, 0, 0)
        hl.addWidget(self.karta_k, 0, 1)
        self.tana.addWidget(quti)

        # «Kartalar» bosilganda ochiladi — har karta alohida qoldig'i bilan.
        self.kartalar_karta = Karta("Kartalar")
        self.kartalar_quti = shaffof(QWidget())
        self.tor = QGridLayout(self.kartalar_quti)
        self.tor.setContentsMargins(0, 0, 0, 0)
        self.tor.setHorizontalSpacing(14)
        self.tor.setVerticalSpacing(14)
        self.kartalar_karta.qosh(self.kartalar_quti)
        self.kartalar_karta.qosh(izoh(
            "Kartani bosing — tarixi, qoldiqni to'g'irlash, o'tkazma."))
        self.kartalar_karta.setVisible(False)
        self.tana.addWidget(self.kartalar_karta)
        self.tana.addStretch(1)

    def odam_id(self):
        return self.kim.odam_id()

    def yangila(self):
        with QSignalBlocker(self.kim):
            self.kim.yangila()
        oid = self.odam_id()
        if oid is None:
            return
        h = hamyon.hamyon(self.db, oid)
        self.jami_izoh.setText(
            f"Qo'ldagi jami pul: {money.fmt_som(h['jami'])} — naqd va "
            f"kartalarga bo'lingan. Rasxod/kirim yozayotganda «Qayerdan» "
            f"ni tanlang.")
        n = len(h["kartalar"])
        if h["naqd"] < 0:
            self.naqd_k.qoy(h["naqd"], "kartalardagi pul jamidan ko'p — "
                                       "qoldiqlarni tekshiring")
            self.naqd_k.izoh_holati("berasan")
        else:
            self.naqd_k.qoy(h["naqd"], "qo'ldagi naqd pul")
            self.naqd_k.izoh_holati(None)
        self.karta_k.qoy(h["karta"], (f"{n} ta karta · bosing" if n else
                                      "karta yo'q · bosing"))
        self._kartalarni_chiz(h["kartalar"])

    def _kartalarni_chiz(self, kartalar: list[dict]):
        while self.tor.count():
            w = self.tor.takeAt(0).widget()
            if w:
                yoq(w)
        if not kartalar:
            self.tor.addWidget(izoh("Hali karta qo'shilmagan. "
                                    "«+ Karta qo'shish» ni bosing."), 0, 0)
            return
        for i, k in enumerate(kartalar):
            rk = _bosiladigan(RaqamKarta("💳 " + k["nom"], k["qoldiq"],
                                         "bosing — tarixi"),
                              lambda kid=k["id"]: self._karta_och(kid))
            self.tor.addWidget(rk, i // USTUN, i % USTUN)

    def showEvent(self, hodisa):
        # Kartalar ro'yxati FAQAT «Kartalar» bosilganda ochiladi
        # (foydalanuvchi so'rovi): varaqqa har kirganda yopiq turadi.
        self.kartalar_karta.setVisible(False)
        super().showEvent(hodisa)

    def _kartalarni_ochyop(self):
        self.kartalar_karta.setVisible(not self.kartalar_karta.isVisible())

    def _karta_qosh(self):
        oid = self.odam_id()
        if oid is not None and KartaDialog(self.db, oid, self).exec():
            self.oyna.yangila()

    def _otkazma(self, dan=None, ga=None):
        oid = self.odam_id()
        if oid is not None and OtkazmaDialog(self.db, oid, dan, ga,
                                             self).exec():
            self.oyna.yangila()

    def _karta_och(self, karta_id: int):
        d = KartaOyna(self.db, karta_id, self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()


# ═══════════════════════════════════════════════════════════ oynalar

def _tugmalar(dialog, saqla) -> QDialogButtonBox:
    t = QDialogButtonBox()
    t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
    t.addButton("Bekor", QDialogButtonBox.RejectRole)
    t.accepted.connect(saqla)
    t.rejected.connect(dialog.reject)
    return t


def _odam_nomi(db, oid) -> str:
    return db.skalyar("SELECT nom FROM odam WHERE id=?", oid, birlamchi="")


class KartaDialog(QDialog):
    """Yangi karta: nomi va undagi HOZIRGI pul (naqddan ko'chadi)."""

    def __init__(self, db, odam_id: int, parent=None):
        super().__init__(parent)
        self.db, self.odam_id = db, odam_id
        self.setWindowTitle(f"Yangi karta — {_odam_nomi(db, odam_id)}")
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("masalan: Humo, Uzcard, Visa")
        self.qoldiq = PulEdit()
        f.addRow("Karta nomi *", self.nom)
        f.addRow("Hozir kartada", self.qoldiq)
        v.addLayout(f)
        e = izoh("Bu pul allaqachon hisobingizda — u naqddan kartaga "
                 "ko'chadi, jami pulingiz o'zgarmaydi.")
        e.setWordWrap(True)
        v.addWidget(e)
        v.addWidget(_tugmalar(self, self._saqla))

    def _saqla(self):
        try:
            hamyon.karta_qosh(self.db, self.odam_id, self.nom.text(),
                              self.qoldiq.qiymat())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class OtkazmaDialog(QDialog):
    """Bitta odamning naqdi va kartalari orasida pul ko'chirish."""

    def __init__(self, db, odam_id: int, dan=None, ga=None, parent=None):
        super().__init__(parent)
        self.db, self.odam_id = db, odam_id
        self.setWindowTitle(f"O'tkazma — {_odam_nomi(db, odam_id)}")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        self.sana = SanaEdit()
        self.dan = HamyonTanla(db)
        self.ga = HamyonTanla(db)
        self.dan.odam_qoy(odam_id)
        self.ga.odam_qoy(odam_id)
        kartalar = [k for k, _ in hamyon.tanlov(db, odam_id) if k is not None]
        # Birlamchi — bankomatdan yechish: birinchi karta → naqd.
        if dan is None and ga is None and kartalar:
            dan = kartalar[0]
        self.dan.tanla(dan)
        self.ga.tanla(ga)
        if self.dan.karta_id() == self.ga.karta_id() and self.ga.count() > 1:
            self.ga.setCurrentIndex(1 if self.dan.currentIndex() == 0 else 0)
        self.summa = PulEdit()
        self.izohm = QLineEdit()
        self.izohm.setPlaceholderText("masalan: bankomatdan yechdim")
        f.addRow("Sana", self.sana)
        f.addRow("Qayerdan", self.dan)
        f.addRow("Qayerga", self.ga)
        f.addRow("Summa", self.summa)
        f.addRow("Izoh", self.izohm)
        v.addLayout(f)
        v.addWidget(_tugmalar(self, self._saqla))

    def _saqla(self):
        try:
            hamyon.otkazma(self.db, self.sana.iso(), self.odam_id,
                           self.dan.karta_id(), self.ga.karta_id(),
                           self.summa.qiymat(),
                           self.izohm.text().strip() or None)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class KartaOyna(QDialog):
    """Bitta karta: qoldig'i, tarixi va amallar. O'zini o'zi yangilaydi;
    `ozgardi` bo'lsa chaqiruvchi dasturni yangilaydi."""

    def __init__(self, db, karta_id: int, parent=None):
        super().__init__(parent)
        self.db, self.karta_id = db, karta_id
        self.ozgardi = False
        self.setMinimumSize(620, 540)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        self.bosh = sarlavha("")
        v.addWidget(self.bosh)
        self.qoldiq = QLabel()
        self.qoldiq.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-family:{theme.RAQAM_OILA};"
            f"font-size:{theme.O_KATTA}px;font-weight:700;")
        v.addWidget(self.qoldiq)
        self.jadval = Jadval(["Sana", "Nima", "Summa"], pul_ustunlar={2},
                             bosh_matn="Bu kartada hali harakat yo'q")
        self.jadval.kengliklar(105, 0, 140)
        self.jadval.doubleClicked.connect(self._qator_och)
        v.addWidget(self.jadval, 1)
        v.addWidget(izoh("Qatorni ikki marta bosing — rasxod/kirimni "
                         "tahrirlash yoki o'tkazmani o'chirish."))

        otk = tugma("⇄ O'tkazma")
        otk.clicked.connect(self._otkazma)
        tog = tugma("Qoldiqni to'g'irlash")
        tog.setToolTip("Bank ilovasidagi haqiqiy qoldiqni yozing — farq "
                       "naqd bilan to'g'irlanadi")
        tog.clicked.connect(self._togirla)
        nom = tugma("Nomini o'zgartirish")
        nom.clicked.connect(self._nomla)
        och = tugma("O'chirish", xavfli=True)
        och.clicked.connect(self._ochir)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        v.addWidget(qator(otk, tog, nom, och, None, yop))
        self.harakat: list[dict] = []
        self._yangila()

    def _karta(self):
        return self.db.q1("SELECT * FROM karta WHERE id=?", self.karta_id)

    def _yangila(self):
        k = self._karta()
        self.setWindowTitle(f"Karta — {k['nom']}")
        self.bosh.setText(f"💳 {k['nom']}")
        q = next((x["qoldiq"] for x in hamyon.kartalar(self.db, k["odam_id"])
                  if x["id"] == self.karta_id), 0)
        self.qoldiq.setText(money.fmt_som(q))
        self.harakat = hamyon.harakatlar(self.db, self.karta_id)
        self.jadval.tuldir(
            [[sana_qisqa(x["sana"]), x["nima"], x["summa"]]
             for x in self.harakat],
            list(range(len(self.harakat))), rangli_ustunlar={2})

    def _ozgardi(self):
        self.ozgardi = True
        self._yangila()

    def _qator_och(self, *_):
        i = self.jadval.tanlangan_id()
        if i is None or i >= len(self.harakat):
            return
        x = self.harakat[i]
        if x["tur"] == "rasxod":
            if RasxodDialog(self.db, x["id"], parent=self).exec():
                self._ozgardi()
        elif x["tur"] == "kirim":
            if KirimDialog(self.db, x["id"], parent=self).exec():
                self._ozgardi()
        elif tasdiq(self, f"O'tkazma o'chirilsinmi?\n{x['nima']} — "
                          f"{money.fmt_som(abs(x['summa']))}"):
            try:
                hamyon.otkazma_ochir(self.db, x["id"])
            except Exception as e:
                xato_koraset(self, str(e))
                return
            self._ozgardi()

    def _otkazma(self):
        k = self._karta()
        if OtkazmaDialog(self.db, k["odam_id"], self.karta_id, None,
                         self).exec():
            self._ozgardi()

    def _togirla(self):
        d = QDialog(self)
        d.setWindowTitle("Qoldiqni to'g'irlash")
        v = QVBoxLayout(d)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        e = izoh("Bank ilovasida hozir qancha turibdi? Farq naqd bilan "
                 "o'tkazma bo'lib yoziladi — jami pulingiz o'zgarmaydi.")
        e.setWordWrap(True)
        v.addWidget(e)
        summa = PulEdit()
        v.addWidget(summa)

        def saqla():
            try:
                hamyon.qoldiq_togirla(self.db, self.karta_id, summa.qiymat(),
                                      date.today().isoformat())
            except Exception as ex:
                xato_koraset(d, str(ex))
                return
            d.accept()
        v.addWidget(_tugmalar(d, saqla))
        if d.exec():
            self._ozgardi()

    def _nomla(self):
        k = self._karta()
        yangi, ok = QInputDialog.getText(self, "Karta nomi", "Yangi nom:",
                                         text=k["nom"])
        if not ok:
            return
        try:
            hamyon.karta_nomla(self.db, self.karta_id, yangi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self._ozgardi()

    def _ochir(self):
        k = self._karta()
        q = next((x["qoldiq"] for x in hamyon.kartalar(self.db, k["odam_id"])
                  if x["id"] == self.karta_id), 0)
        if not tasdiq(self, f"«{k['nom']}» kartasi o'chirilsinmi?\n"
                            f"Undagi {money.fmt_som(q)} naqdga qaytadi; "
                            f"yozuvlar o'chmaydi."):
            return
        try:
            hamyon.karta_ochir(self.db, self.karta_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()
