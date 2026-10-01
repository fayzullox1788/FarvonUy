"""«Kategoriyalar» varag'i (oldin «Mahsulotlar»): kategoriya daraxti + rasmli mahsulot kartalari.

Chapda — kategoriyalar daraxti («Bozorlik» › «Mevalar»). Kategoriya
tanlansa o'ngda uning VA hamma ichki kategoriyalarining mahsulotlari
chiqadi. Hisob-kitob hammasi `core/mahsulot.py` da — bu fayl faqat
ko'rsatadi va chaqiradi.

Telefondan rasm: dastur kompyuterda ishlaydi, shuning uchun telefon
yo'li — Telegram bot (rasm + izohida mahsulot nomi,
`xabar._rasmni_ishla`). Bu yerdagi «Rasm tanlash…» — kompyuterdagi fayl.
"""
from __future__ import annotations

from PySide6.QtCore import (QBuffer, QByteArray, QIODevice, QSignalBlocker,
                            QSize, Qt)
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from core import kategoriya
from core import mahsulot as mh
from ui.eski import theme
from ui.eski.dialogs import tasdiq, xato_koraset
from ui.eski.sahifa_asosiy import Sahifa, shaffof
from ui.eski.widgets import (Karta, PulEdit, Xabar, belgi_ikon, belgi_rasm,
                             izoh, qator, sarlavha, tugma)

KARTA_RASM = 104
KATTA_RASM = 1280        # yuklangan rasm shu o'lchamdan katta bo'lsa kichraytiriladi
TELEFON_IZOH = ("Telefondan: rasmni Telegram botga shaxsiy yuboring, "
                "izohiga mahsulot nomini aynan yozing — bir daqiqada "
                "shu yerda paydo bo'ladi.")


def _son_matn(x) -> str:
    return "" if x is None else f"{x:g}".replace(".", ",")


def _bosh_rasm(nom: str, olcham: int) -> QPixmap:
    """Rasmsiz mahsulot uchun: yumshoq fon + bosh harf."""
    p = QPixmap(olcham, olcham)
    p.fill(Qt.transparent)
    ch = QPainter(p)
    ch.setRenderHint(QPainter.Antialiasing)
    ch.setPen(Qt.NoPen)
    ch.setBrush(QColor(theme.KOK_FON))
    ch.drawRoundedRect(0, 0, olcham, olcham, 14, 14)
    ch.setPen(QColor(theme.KOK))
    f = QFont(theme.SHRIFT)
    f.setPixelSize(olcham // 2)
    f.setBold(True)
    ch.setFont(f)
    ch.drawText(p.rect(), Qt.AlignCenter, (nom.strip()[:1] or "?").upper())
    ch.end()
    return p


def _kvadrat(p: QPixmap, olcham: int) -> QPixmap:
    """Rasmni kvadratga qirqib kichraytiradi (karta bir xil o'lchamda)."""
    k = p.scaled(olcham, olcham, Qt.KeepAspectRatioByExpanding,
                 Qt.SmoothTransformation)
    x, y = (k.width() - olcham) // 2, (k.height() - olcham) // 2
    return k.copy(x, y, olcham, olcham)


def rasm_baytlari(yol: str) -> bytes:
    """Faylni o'qib, katta bo'lsa kichraytirib JPEG baytlarini qaytaradi.

    Telefon rasmi 4–8 MB bo'ladi — kartalar ro'yxati sekinlashmasin.
    """
    img = QImage(yol)
    if img.isNull():
        raise ValueError("Bu faylni rasm sifatida o'qib bo'lmadi.")
    if max(img.width(), img.height()) > KATTA_RASM:
        img = img.scaled(KATTA_RASM, KATTA_RASM, Qt.KeepAspectRatio,
                         Qt.SmoothTransformation)
    bayt = QByteArray()
    buf = QBuffer(bayt)
    buf.open(QIODevice.WriteOnly)
    img.convertToFormat(QImage.Format_RGB32).save(buf, "JPG", 88)
    buf.close()
    return bytes(bayt)


# ═══════════════════════════════════════════════════════ mahsulot oynasi

class MahsulotDialog(QDialog):
    """Mahsulot qo'shish / tahrirlash. Rasm «Saqlash» bosilganda yoziladi."""

    def __init__(self, db, item_id: int | None = None,
                 turi_id: int | None = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.item_id = item_id
        self._yangi_rasm: bytes | None = None      # tanlangan, hali saqlanmagan
        self._rasm_olib_tashla = False
        r = db.q1("SELECT * FROM item WHERE id=?", item_id) if item_id else None
        self.setWindowTitle("Mahsulotni tahrirlash" if r else "Yangi mahsulot")
        self.setMinimumWidth(520)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)

        # ── rasm ─────────────────────────────────────────────────────
        self.rasm = QLabel()
        self.rasm.setFixedSize(132, 132)
        self.rasm.setAlignment(Qt.AlignCenter)
        self.rasm.setStyleSheet(
            f"QLabel{{background:{theme.KARTA_ICH};border:1px dashed "
            f"{theme.CHIZIQ_TUQ};border-radius:12px;color:{theme.KUL};}}")
        tanla = tugma("Rasm tanlash…")
        tanla.clicked.connect(self._rasm_tanla)
        self.rasm_ochir = tugma("Rasmni o'chirish", xavfli=True)
        self.rasm_ochir.clicked.connect(self._rasm_ochir)
        ong = QWidget()
        shaffof(ong)
        ov = QVBoxLayout(ong)
        ov.setContentsMargins(0, 0, 0, 0)
        ov.addWidget(qator(tanla, self.rasm_ochir, None))
        tel = izoh(TELEFON_IZOH)
        tel.setWordWrap(True)
        ov.addWidget(tel)
        ov.addStretch(1)
        v.addWidget(qator(self.rasm, ong))

        # ── maydonlar ────────────────────────────────────────────────
        f = QFormLayout()
        f.setSpacing(10)
        self.nom = QLineEdit(r["nom"] if r else "")
        self.nom.setPlaceholderText("masalan: Olma")
        self.asosiy = QComboBox()
        self.ichki = QComboBox()
        self.narx = PulEdit(r["narx"] if r else 0)
        self.miqdor = QLineEdit(_son_matn(r["miqdor"]) if r else "")
        self.miqdor.setPlaceholderText("masalan: 1 yoki 0,5")
        self.olchov = QComboBox()
        self.olchov.setEditable(True)
        self.olchov.addItem("")
        self.olchov.addItems(mh.OLCHOVLAR)
        self.olchov.setCurrentText((r["olchov"] or "") if r else "")
        self.ogirlik = QLineEdit(_son_matn(r["ogirlik"]) if r else "")
        self.ogirlik.setPlaceholderText("masalan: 0,5")
        self.litr = QLineEdit(_son_matn(r["litr"]) if r else "")
        self.litr.setPlaceholderText("masalan: 1,5")
        self.izohm = QLineEdit((r["izoh"] or "") if r else "")
        self.faol = QCheckBox("Faol (rasxod yozishda tanlanadi)")
        self.faol.setChecked(bool(r["faol"]) if r else True)

        f.addRow("Nomi *", self.nom)
        f.addRow("Kategoriya *", self.asosiy)
        f.addRow("Ichki kategoriya", self.ichki)
        f.addRow("Narxi", self.narx)
        f.addRow("Miqdori / hajmi", qator(self.miqdor, self.olchov))
        f.addRow("Og'irligi (kg)", self.ogirlik)
        f.addRow("Litri", self.litr)
        f.addRow("Izoh", self.izohm)
        f.addRow("", self.faol)
        v.addLayout(f)

        for t in mh.daraxt(db):
            self.asosiy.addItem(f"{t['belgi']} {t['nom']}".strip(), t["id"])
        self.asosiy.currentIndexChanged.connect(self._ichkilar)
        joriy = r["turi_id"] if r else turi_id
        ildiz = self._ildiz(joriy)
        if ildiz is not None:
            self.asosiy.setCurrentIndex(max(0, self.asosiy.findData(ildiz)))
        self._ichkilar()
        if joriy is not None and joriy != ildiz:
            self.ichki.setCurrentIndex(max(0, self.ichki.findData(joriy)))

        self._eski_rasm = r["rasm"] if r else None
        self._rasm_chiz()

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def _ildiz(self, turi_id):
        korilgan = set()
        while turi_id is not None and turi_id not in korilgan:
            korilgan.add(turi_id)
            r = self.db.q1("SELECT ota_id FROM turi WHERE id=?", turi_id)
            if not r or r["ota_id"] is None:
                return turi_id
            turi_id = r["ota_id"]
        return turi_id

    def _ichkilar(self):
        self.ichki.clear()
        self.ichki.addItem("— yo'q —", None)
        ildiz = self.asosiy.currentData()
        ichidagilar = (set(mh.avlodlar(self.db, ildiz)) - {ildiz}
                       if ildiz is not None else set())
        for t, chuq in mh.tekis(self.db):
            if t["id"] in ichidagilar:
                self.ichki.addItem("   " * (chuq - 1) + t["nom"], t["id"])
        self.ichki.setEnabled(self.ichki.count() > 1)

    # ── rasm ─────────────────────────────────────────────────────────

    def _rasm_chiz(self):
        if self._yangi_rasm:
            p = QPixmap()
            p.loadFromData(self._yangi_rasm)
        elif not self._rasm_olib_tashla and mh.rasm_yoli(self._eski_rasm):
            p = QPixmap(str(mh.rasm_yoli(self._eski_rasm)))
        else:
            p = None
        if p is not None and not p.isNull():
            self.rasm.setPixmap(_kvadrat(p, 128))
            self.rasm_ochir.setEnabled(True)
        else:
            self.rasm.setPixmap(QPixmap())
            self.rasm.setText("Rasm yo'q")
            self.rasm_ochir.setEnabled(False)

    def _rasm_tanla(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Mahsulot rasmi", "",
            "Rasmlar (*.jpg *.jpeg *.png *.webp *.bmp *.gif)")
        if not yol:
            return
        # Yuklanish holati: katta rasm kichraytirilguncha bir lahza.
        self.rasm.setPixmap(QPixmap())
        self.rasm.setText("Yuklanmoqda…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self._yangi_rasm = rasm_baytlari(yol)
            self._rasm_olib_tashla = False
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self._rasm_chiz()
            xato_koraset(self, str(e))
            return
        QApplication.restoreOverrideCursor()
        self._rasm_chiz()

    def _rasm_ochir(self):
        self._yangi_rasm = None
        self._rasm_olib_tashla = True
        self._rasm_chiz()

    # ── saqlash ──────────────────────────────────────────────────────

    def _saqla(self):
        turi_id = self.ichki.currentData() or self.asosiy.currentData()
        try:
            # Mahsulot + rasm — bitta undo qadami.
            with self.db.amal(f"Mahsulot saqlandi: {self.nom.text().strip()}"):
                self.item_id = mh.saqla(
                    self.db, self.item_id, nom=self.nom.text(),
                    turi_id=turi_id, narx=self.narx.qiymat(),
                    miqdor=self.miqdor.text(), ogirlik=self.ogirlik.text(),
                    litr=self.litr.text(), olchov=self.olchov.currentText(),
                    izoh=self.izohm.text(), faol=self.faol.isChecked())
                if self._yangi_rasm:
                    mh.rasm_baytdan(self.db, self.item_id, self._yangi_rasm)
                elif self._rasm_olib_tashla and self._eski_rasm:
                    mh.rasm_olib_tashla(self.db, self.item_id)
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class IchkiKategoriyaDialog(QDialog):
    """Ichki kategoriya: nomi + RASMI (majburiy).

    Rasm — `belgilar/` dagi ikonkalardan, faqat hali hech bir faol
    kategoriyada band bo'lmaganlari (`mh.bosh_belgilar`): bitta ikonka —
    bitta kategoriya, aks holda «Iconlar» varag'i ularni
    aralashtirib yuborardi. Tekshiruv `mh.kategoriya_qosh` ning o'zida
    ham bor — bu oyna faqat tanlatadi.
    """

    IKONKA = 44

    def __init__(self, db, ota_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.ota_id = ota_id
        self.yangi_id: int | None = None
        self._tanlangan: str | None = None   # guruh almashganda ham eslanadi
        self.setWindowTitle("Ichki kategoriya")
        self.setMinimumSize(620, 560)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        bosh = sarlavha(f"«{mh.yol_nomi(db, ota_id)}» ichiga")
        bosh.setWordWrap(True)
        v.addWidget(bosh)

        f = QFormLayout()
        f.setSpacing(10)
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("masalan: Mevalar")
        f.addRow("Nomi *", self.nom)
        self.guruh = QComboBox()
        self.guruh.addItem("Hammasi", None)
        self._fayllar = mh.bosh_belgilar(db)
        for g in dict.fromkeys(kategoriya.guruh(x) for x in self._fayllar):
            self.guruh.addItem(kategoriya.guruh_nomi(g), g)
        self.guruh.currentIndexChanged.connect(self._toldir)
        f.addRow("Guruh", self.guruh)
        v.addLayout(f)

        v.addWidget(izoh("Rasm * — kategoriyaning belgisi. Boshqa "
                         "kategoriyada band bo'lgan rasmlar ko'rsatilmaydi."))
        self.royxat = QListWidget()
        self.royxat.setViewMode(QListWidget.IconMode)
        self.royxat.setIconSize(QSize(self.IKONKA, self.IKONKA))
        self.royxat.setGridSize(QSize(self.IKONKA + 22, self.IKONKA + 22))
        self.royxat.setResizeMode(QListWidget.Adjust)
        self.royxat.setMovement(QListWidget.Static)
        self.royxat.setSelectionMode(QListWidget.SingleSelection)
        self.royxat.itemSelectionChanged.connect(self._tanlandi)
        self.royxat.itemDoubleClicked.connect(lambda _it: self._saqla())
        v.addWidget(self.royxat, 1)

        self.tanlov = QLabel()
        self.tanlov.setFixedSize(self.IKONKA, self.IKONKA)
        self.tanlov_matn = izoh("Rasm tanlanmagan")
        v.addWidget(qator(self.tanlov, self.tanlov_matn, None))

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)
        self._toldir()

    def _toldir(self, *_):
        g = self.guruh.currentData()
        joriy = self._tanlangan
        with QSignalBlocker(self.royxat):
            self.royxat.clear()
            for fayl in self._fayllar:
                if g is not None and kategoriya.guruh(fayl) != g:
                    continue
                it = QListWidgetItem(belgi_ikon(kategoriya.rasm_yoli(fayl)), "")
                it.setData(Qt.UserRole, fayl)
                it.setToolTip(kategoriya.guruh_nomi(kategoriya.guruh(fayl)))
                it.setSizeHint(QSize(self.IKONKA + 18, self.IKONKA + 18))
                self.royxat.addItem(it)
                if fayl == joriy:
                    it.setSelected(True)
        if not self._fayllar:
            self.tanlov_matn.setText("Bo'sh rasm qolmagan — «Iconlar» "
                                     "varag'ida biror rasmning nomini olib "
                                     "tashlang.")

    def rasm(self) -> str | None:
        tanlangan = self.royxat.selectedItems()
        return tanlangan[0].data(Qt.UserRole) if tanlangan else None

    def _tanlandi(self):
        fayl = self.rasm()
        if fayl is None:
            return          # guruh almashganda ko'rinmay qolgan tanlov saqlanadi
        self._tanlangan = fayl
        self.tanlov.setPixmap(belgi_rasm(kategoriya.rasm_yoli(fayl),
                                         self.IKONKA, self.tanlov))
        self.tanlov_matn.setText("Tanlangan rasm")

    def _saqla(self):
        rasm = self.rasm() or self._tanlangan
        if not self.nom.text().strip():
            xato_koraset(self, "Ichki kategoriya nomini yozing.")
            return
        if not rasm:
            xato_koraset(self, "Ichki kategoriya uchun rasm tanlang.")
            return
        try:
            self.yangi_id = mh.kategoriya_qosh(self.db, self.nom.text(),
                                               self.ota_id, rasm=rasm)
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class RasmKorish(QDialog):
    def __init__(self, yol: str, nom: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(nom)
        v = QVBoxLayout(self)
        e = QLabel()
        p = QPixmap(yol)
        ekran = QApplication.primaryScreen().availableGeometry()
        e.setPixmap(p.scaled(int(ekran.width() * 0.6), int(ekran.height() * 0.7),
                             Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v.addWidget(e)


# ═══════════════════════════════════════════════════════════ sahifa

class KategoriyaKochirDialog(QDialog):
    """Kategoriya qayerga ko'chsin — daraxtdan tanlanadi.

    O'zi va ichki kategoriyalari ro'yxatda yo'q (halqa bo'lmasin); ular
    kategoriya bilan BIRGA ko'chadi.
    """

    ASOSIY = "— asosiy kategoriya (hech qaysi ichida emas) —"

    def __init__(self, db, turi_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        nom = mh.yol_nomi(db, turi_id)
        self.setWindowTitle("Kategoriyani ko'chirish")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        v.addWidget(sarlavha(f"«{nom}» qayerga?"))
        v.addWidget(izoh("Ichki kategoriyalari va mahsulotlari birga ko'chadi. "
                         "Eski rasxodlar o'zgarmaydi — analitika va budjetda "
                         "endi yangi joyiga qo'shilib hisoblanadi."))
        self.joy = QComboBox()
        self.joy.addItem(self.ASOSIY, None)
        hozirgi = db.skalyar("SELECT ota_id FROM turi WHERE id=?", turi_id,
                             birlamchi=None)
        for t, chuq in mh.kochish_joylari(db, turi_id):
            yorliqcha = "    " * chuq + f"{t['belgi'] or ''} {t['nom']}".strip()
            yol = kategoriya.rasm_yoli(t["rasm"])
            if yol:
                self.joy.addItem(belgi_ikon(yol), yorliqcha, t["id"])
            else:
                self.joy.addItem(yorliqcha, t["id"])
        i = self.joy.findData(hozirgi)
        self.joy.setCurrentIndex(max(i, 0))
        f = QFormLayout()
        f.addRow("Qaysi kategoriya ichiga", self.joy)
        v.addLayout(f)
        t = QDialogButtonBox()
        t.addButton("Ko'chirish", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self.accept)
        t.rejected.connect(self.reject)
        v.addWidget(t)

    def ota_id(self):
        return self.joy.currentData()


class MahsulotSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        yangi = tugma("+ Mahsulot", asosiy=True)
        yangi.clicked.connect(self._yangi)
        self.tana.addWidget(qator(sarlavha("Kategoriyalar"), None, yangi))
        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        # ── chap: kategoriya daraxti ─────────────────────────────────
        kk = Karta("Kategoriyalar")
        self.daraxt = QTreeWidget()
        self.daraxt.setHeaderHidden(True)
        self.daraxt.setIndentation(18)
        self.daraxt.setMinimumHeight(420)
        self.daraxt.currentItemChanged.connect(lambda *_: self._mahsulotlar())
        kk.qosh(self.daraxt)
        b1 = tugma("+ Kategoriya")
        b2 = tugma("+ Ichki")
        b3 = tugma("Nomini o'zgartirish")
        b4 = tugma("O'chirish", xavfli=True)
        b5 = tugma("Boshqasiga ko'chirish")
        b5.setToolTip("Tanlangan kategoriyani boshqa kategoriya ichiga "
                      "qo'yish — masalan «Gigiena»ni «Katta bozorlik»ka")
        b1.clicked.connect(lambda: self._kat_qosh(ichki=False))
        b2.clicked.connect(lambda: self._kat_qosh(ichki=True))
        b3.clicked.connect(self._kat_nomla)
        b4.clicked.connect(self._kat_ochir)
        b5.clicked.connect(self._kat_kochir)
        kk.qosh(qator(b1, b2, None))
        kk.qosh(qator(b3, b5, None))
        kk.qosh(qator(b4, None))
        kk.setFixedWidth(320)

        # ── o'ng: mahsulotlar ────────────────────────────────────────
        mk = Karta("Mahsulotlar")
        self.qidiruv = QLineEdit()
        self.qidiruv.setPlaceholderText("Nomi bo'yicha qidirish…")
        self.qidiruv.setClearButtonEnabled(True)
        self.qidiruv.textChanged.connect(lambda *_: self._mahsulotlar())
        self.hammasi = QCheckBox("Faol emaslari ham")
        self.hammasi.setChecked(True)
        self.hammasi.toggled.connect(lambda *_: self._mahsulotlar())
        mk.qosh(qator(self.qidiruv, self.hammasi))
        self.joy = izoh("")
        mk.qosh(self.joy)

        self.royxat = QListWidget()
        self.royxat.setViewMode(QListWidget.IconMode)
        self.royxat.setIconSize(QSize(KARTA_RASM, KARTA_RASM))
        self.royxat.setGridSize(QSize(158, 182))
        self.royxat.setResizeMode(QListWidget.Adjust)
        self.royxat.setMovement(QListWidget.Static)
        self.royxat.setWordWrap(True)
        self.royxat.setSpacing(4)
        self.royxat.setUniformItemSizes(True)
        self.royxat.setMinimumHeight(420)
        self.royxat.itemDoubleClicked.connect(lambda *_: self._tahrir())
        mk.qosh(self.royxat)
        self.bosh = QLabel()
        self.bosh.setAlignment(Qt.AlignCenter)
        self.bosh.setWordWrap(True)
        self.bosh.setMinimumHeight(420)
        self.bosh.setStyleSheet(f"color:{theme.KUL};font-size:{theme.O_ORTA}px;")
        mk.qosh(self.bosh)

        t1 = tugma("Tahrirlash", asosiy=True)
        t2 = tugma("Rasmni ko'rish")
        t3 = tugma("Faol / faol emas")
        t4 = tugma("O'chirish", xavfli=True)
        t1.clicked.connect(self._tahrir)
        t2.clicked.connect(self._rasm_kor)
        t3.clicked.connect(self._faol)
        t4.clicked.connect(self._ochir)
        mk.qosh(qator(None, t4, t3, t2, t1))

        ikki = QWidget()
        shaffof(ikki)
        h = QHBoxLayout(ikki)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)
        h.addWidget(kk, 0, Qt.AlignTop)
        h.addWidget(mk, 1)
        self.tana.addWidget(ikki)
        self.tana.addStretch(1)
        self._kesh: dict[str, QIcon] = {}

    # ── daraxt ───────────────────────────────────────────────────────

    def _tanlangan_kat(self):
        it = self.daraxt.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def _daraxtni_chiz(self):
        joriy = self._tanlangan_kat()
        with QSignalBlocker(self.daraxt):
            self.daraxt.clear()
            jami = self.db.skalyar("SELECT COUNT(*) FROM item WHERE ochirilgan=0")
            ildiz = QTreeWidgetItem([f"Hammasi  ({jami})"])
            ildiz.setData(0, Qt.UserRole, None)
            self.daraxt.addTopLevelItem(ildiz)
            tanla = ildiz

            def qosh(ota, tugunlar):
                nonlocal tanla
                for t in tugunlar:
                    n = self.db.skalyar(
                        "WITH RECURSIVE a(id) AS (SELECT ?"
                        " UNION SELECT x.id FROM turi x JOIN a ON x.ota_id=a.id)"
                        " SELECT COUNT(*) FROM item WHERE ochirilgan=0"
                        " AND turi_id IN (SELECT id FROM a)", t["id"])
                    it = QTreeWidgetItem(
                        [f"{t['belgi']} {t['nom']}".strip() + (f"  ({n})" if n else "")])
                    it.setData(0, Qt.UserRole, t["id"])
                    yol = kategoriya.rasm_yoli(t["rasm"])
                    if yol:
                        it.setIcon(0, belgi_ikon(yol))
                    ota.addChild(it)
                    if t["id"] == joriy:
                        tanla = it
                    qosh(it, t["bolalar"])
            qosh(ildiz, mh.daraxt(self.db))
            self.daraxt.expandAll()
            self.daraxt.setCurrentItem(tanla)

    def _kat_qosh(self, ichki: bool):
        ota = self._tanlangan_kat() if ichki else None
        if ichki and ota is None:
            self.xabar.korsat("Avval chapdan asosiy kategoriyani tanlang.",
                              "ogoh", 3500)
            return
        if ichki:
            # Ichki kategoriyaga rasm majburiy — alohida oyna.
            d = IchkiKategoriyaDialog(self.db, ota, parent=self)
            if not d.exec() or d.yangi_id is None:
                return
            yangi, nom = d.yangi_id, d.nom.text()
        else:
            nom, ok = QInputDialog.getText(self, "Yangi kategoriya", "Nomi:")
            if not ok:
                return
            try:
                yangi = mh.kategoriya_qosh(self.db, nom, ota)
            except ValueError as e:
                xato_koraset(self, str(e))
                return
        self._daraxtni_chiz()
        self._kat_tanla(yangi)
        self.xabar.korsat(f"✔ «{nom.strip()}» kategoriyasi qo'shildi.", "ok", 3500)

    def _kat_tanla(self, turi_id):
        for it in self._hamma_tugun():
            if it.data(0, Qt.UserRole) == turi_id:
                self.daraxt.setCurrentItem(it)
                return

    def _hamma_tugun(self):
        stek = [self.daraxt.topLevelItem(i)
                for i in range(self.daraxt.topLevelItemCount())]
        while stek:
            it = stek.pop()
            yield it
            stek.extend(it.child(i) for i in range(it.childCount()))

    def _kat_nomla(self):
        tid = self._tanlangan_kat()
        if tid is None:
            self.xabar.korsat("Avval kategoriyani tanlang.", "ogoh", 3000)
            return
        eski = self.db.skalyar("SELECT nom FROM turi WHERE id=?", tid, birlamchi="")
        nom, ok = QInputDialog.getText(self, "Kategoriya nomi", "Yangi nomi:",
                                       text=eski)
        if not ok or nom.strip() == eski:
            return
        try:
            mh.kategoriya_nomla(self.db, tid, nom)
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self._daraxtni_chiz()
        self.xabar.korsat("✔ Kategoriya nomi saqlandi.", "ok", 3000)

    def _kat_kochir(self):
        tid = self._tanlangan_kat()
        if tid is None:
            self.xabar.korsat("Avval chapdan ko'chiriladigan kategoriyani "
                              "tanlang.", "ogoh", 3500)
            return
        d = KategoriyaKochirDialog(self.db, tid, self)
        if not d.exec():
            return
        try:
            mh.kategoriya_kochir(self.db, tid, d.ota_id())
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self._daraxtni_chiz()
        self._kat_tanla(tid)
        self.xabar.korsat(f"✔ Endi: {mh.yol_nomi(self.db, tid)}", "ok", 3500)

    def _kat_ochir(self):
        tid = self._tanlangan_kat()
        if tid is None:
            self.xabar.korsat("Avval kategoriyani tanlang.", "ogoh", 3000)
            return
        nom = mh.yol_nomi(self.db, tid)
        if not tasdiq(self, f"«{nom}» kategoriyasi o'chirilsinmi?\n\n"
                            "Oldin shu kategoriya bilan yozilgan rasxodlar "
                            "o'zgarmaydi."):
            return
        try:
            mh.kategoriya_ochir(self.db, tid)
        except ValueError as e:
            xato_koraset(self, str(e))
            return
        self._daraxtni_chiz()
        self.xabar.korsat(f"✔ «{nom}» o'chirildi.", "ok", 3000)

    # ── mahsulotlar ──────────────────────────────────────────────────

    def _belgi(self, r) -> QIcon:
        kalit = r["rasm"] or f"#{r['nom'][:1]}"
        if kalit not in self._kesh:
            yol = mh.rasm_yoli(r["rasm"])
            p = QPixmap(str(yol)) if yol else QPixmap()
            p = _kvadrat(p, KARTA_RASM) if not p.isNull() \
                else _bosh_rasm(r["nom"], KARTA_RASM)
            self._kesh[kalit] = QIcon(p)
        return self._kesh[kalit]

    def _mahsulotlar(self):
        tid = self._tanlangan_kat()
        qatorlar = mh.mahsulotlar(self.db, tid, self.qidiruv.text())
        if not self.hammasi.isChecked():
            qatorlar = [r for r in qatorlar if r["faol"]]
        self.royxat.clear()
        for r in qatorlar:
            matn = r["nom"]
            ikkinchi = mh.tavsif(r)
            if ikkinchi:
                matn += "\n" + ikkinchi
            if not r["faol"]:
                matn += "\n(faol emas)"
            it = QListWidgetItem(self._belgi(r), matn)
            it.setData(Qt.UserRole, r["id"])
            it.setToolTip("\n".join(x for x in (
                r["nom"], r["kategoriya"], ikkinchi, r["izoh"] or "") if x))
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            if not r["faol"]:
                it.setForeground(QColor(theme.KUL_OCH))
            self.royxat.addItem(it)

        kat = mh.yol_nomi(self.db, tid) if tid else "Hammasi"
        self.joy.setText(f"{kat} · {len(qatorlar)} ta mahsulot")
        bor = bool(qatorlar)
        self.royxat.setVisible(bor)
        self.bosh.setVisible(not bor)
        if not bor:
            if self.qidiruv.text().strip():
                self.bosh.setText(f"«{self.qidiruv.text().strip()}» bo'yicha "
                                  f"mahsulot topilmadi.")
            else:
                self.bosh.setText("Bu kategoriyada hali mahsulot yo'q.\n"
                                  "«+ Mahsulot» tugmasi bilan qo'shing.")

    def _tanlangan(self):
        it = self.royxat.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _kerak(self):
        iid = self._tanlangan()
        if iid is None:
            self.xabar.korsat("Avval mahsulotni tanlang.", "ogoh", 3000)
        return iid

    def _yangi(self):
        d = MahsulotDialog(self.db, turi_id=self._tanlangan_kat(), parent=self)
        if d.exec():
            self.yangila()
            self.xabar.korsat("✔ Mahsulot saqlandi.", "ok", 3000)

    def _tahrir(self):
        iid = self._kerak()
        if iid is None:
            return
        if MahsulotDialog(self.db, iid, parent=self).exec():
            self.yangila()
            self.xabar.korsat("✔ O'zgarishlar saqlandi.", "ok", 3000)

    def _rasm_kor(self):
        iid = self._kerak()
        if iid is None:
            return
        r = self.db.q1("SELECT nom, rasm FROM item WHERE id=?", iid)
        yol = mh.rasm_yoli(r["rasm"])
        if not yol:
            self.xabar.korsat("Bu mahsulotda rasm yo'q.", "ogoh", 3000)
            return
        RasmKorish(str(yol), r["nom"], self).exec()

    def _faol(self):
        iid = self._kerak()
        if iid is None:
            return
        faol = mh.faol_almashtir(self.db, iid)
        self._mahsulotlar()
        self.xabar.korsat("✔ Faol qilindi." if faol else
                          "✔ Faol emas — rasxod yozishda tanlanmaydi.", "ok", 3000)

    def _ochir(self):
        iid = self._kerak()
        if iid is None:
            return
        nom = self.db.skalyar("SELECT nom FROM item WHERE id=?", iid, birlamchi="")
        if not tasdiq(self, f"«{nom}» o'chirilsinmi?\n\nUnga bog'langan eski "
                            f"rasxodlar o'zgarmaydi."):
            return
        mh.ochir(self.db, iid)
        self.yangila()
        self.xabar.korsat(f"✔ «{nom}» o'chirildi.", "ok", 3000)

    def yangila(self):
        self._kesh.clear()
        self._daraxtni_chiz()
        self._mahsulotlar()
