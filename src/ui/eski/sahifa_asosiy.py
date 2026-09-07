"""Kundalik ishlatiladigan sahifalar: Bugun, Rasxod, Kirim, Qarz."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QRadioButton,
                               QScrollArea, QTableWidget, QVBoxLayout, QWidget)

import money
from core import entries, ledger, plan, recurring, settle
from ui.eski import theme
from ui.eski.dialogs import (JuftTafsilot, KirimDialog, QarzDialog,
                        RasxodDialog, RasxodTafsilot, TolovDialog,
                        tasdiq, xato_koraset)
from ui.eski.widgets import (Holat, Jadval, Karta, OdamTanla, PulEdit, RaqamKarta,
                        SanaEdit, TuriTanla, Xabar, izoh, qator, sarlavha,
                        tugma, yorliq)


OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
         "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
HAFTA = ["dushanba", "seshanba", "chorshanba", "payshanba",
         "juma", "shanba", "yakshanba"]


def sana_qisqa(s) -> str:
    """ISO sanani odam o'qiydigan ko'rinishga keltiradi: 30.08.2026."""
    if not s:
        return ""
    if isinstance(s, str):
        try:
            s = date.fromisoformat(s[:10])
        except ValueError:
            return s
    return s.strftime("%d.%m.%Y")


def sana_uzun(s) -> str:
    """30-avgust 2026, yakshanba."""
    if isinstance(s, str):
        s = date.fromisoformat(s[:10])
    return f"{s.day}-{OYLAR[s.month - 1]} {s.year}, {HAFTA[s.weekday()]}"


def shaffof(w):
    """Fonsiz konteyner.

    DIQQAT: oddiy `setStyleSheet("background:transparent")` Qt'da BUTUN
    avlodga tarqaladi va kartalar, tugmalar, jadvallarning fonini ham
    o'chirib yuboradi (bir marta shu sabab tugmalar oq-oqda ko'rinmay
    qolgan). Selektor bilan yozilsa — faqat shu widgetga tegadi.
    """
    w.setObjectName("Shaffof")
    w.setStyleSheet("QWidget#Shaffof { background: transparent; }")
    return w


class BosiladiganYorliq(QLabel):
    """Bosilganda signal beradigan yorliq.

    QPushButton emas: qatordagi matn qalin/rangli HTML bilan yozilgan,
    tugma esa HTML ni ko'rsatmaydi. Shuning uchun ko'rinish o'zgarmaydi,
    faqat bosiladigan bo'ladi.
    """

    bosildi = Signal()

    def __init__(self, matn: str, parent=None):
        super().__init__(matn, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, hodisa):
        if hodisa.button() == Qt.LeftButton:
            self.bosildi.emit()
        super().mousePressEvent(hodisa)


def rasxod_turi(r) -> str:
    """Jadvalda ko'rinadigan tur nomi."""
    if r["kim_uchun_nom"]:
        return f"{r['kim_uchun_nom']} uchun"
    return "Umumiy" if r["umumiymi"] else "Shaxsiy"


class Sahifa(QWidget):
    """Barcha sahifalar uchun asos."""

    def __init__(self, oyna):
        super().__init__()
        self.oyna = oyna
        self.db = oyna.db
        self.tashqi = QVBoxLayout(self)
        self.tashqi.setContentsMargins(0, 0, 0, 0)

        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        ichki = QWidget()
        shaffof(ichki)
        self.tana = QVBoxLayout(ichki)
        self.tana.setContentsMargins(26, 22, 26, 26)
        self.tana.setSpacing(16)
        aylanma.setWidget(ichki)
        self.tashqi.addWidget(aylanma)

    def yangila(self):
        pass


# ═══════════════════════════════════════════════════════════ BUGUN

class BugunSahifa(Sahifa):
    """Kunlik ish stoli: rasxod yozish va bugun nima bo'lganini ko'rish.

    Bu yerda balans raqamlari YO'Q — ular «Shaxsiy» va «Hisobot»
    sahifalarida. Bugun sahifasining bitta vazifasi bor: tez yozib qo'yish.
    """

    def __init__(self, oyna):
        super().__init__(oyna)

        self.bosh = sarlavha("Bugun")
        self.sana_izoh = izoh("")
        self.tana.addWidget(qator(self.bosh, None))
        self.tana.addWidget(self.sana_izoh)

        self.ogoh = Xabar()
        self.tana.addWidget(self.ogoh)

        # ── rasxod qo'shish ──────────────────────────────────────────
        quti = Karta("Rasxod qo'shish")

        self.t_sana = SanaEdit()
        self.t_sana.setFixedWidth(140)
        self.t_nom = QLineEdit()
        self.t_nom.setPlaceholderText("Nima olindi?")
        self.t_summa = PulEdit()
        self.t_summa.setFixedWidth(160)
        quti.qosh(qator(self.t_sana, self.t_nom, self.t_summa))

        self.t_kim = OdamTanla(self.db)
        self.t_turi = TuriTanla(self.db)
        self.t_item = QComboBox()
        self.t_item.setMinimumWidth(180)
        self.t_turi.currentIndexChanged.connect(self._itemlarni_yukla)
        self.t_item.currentIndexChanged.connect(self._item_tanlandi)
        quti.qosh(qator("Kim to'ladi:", self.t_kim,
                        "Kategoriya:", self.t_turi,
                        "Mahsulot:", self.t_item, None))

        self.t_umumiy = QRadioButton("Umumiy")
        self.t_shaxsiy = QRadioButton("Shaxsiy")
        self.t_uchun = QRadioButton("Boshqa uchun")
        self.t_umumiy.setChecked(True)
        g = QButtonGroup(self)
        for b in (self.t_umumiy, self.t_shaxsiy, self.t_uchun):
            g.addButton(b)
            b.toggled.connect(self._turi_ozgardi)
        self.t_uchun_kim = OdamTanla(self.db)
        self.t_uchun_kim.setVisible(False)

        qosh = tugma("Qo'shish", asosiy=True)
        qosh.clicked.connect(self._qosh)
        self.t_nom.returnPressed.connect(self._qosh)
        self.t_summa.returnPressed.connect(self._qosh)
        quti.qosh(qator(self.t_umumiy, self.t_shaxsiy, self.t_uchun,
                        self.t_uchun_kim, None, qosh))
        self.t_umumiy.setToolTip("Hammaga teng bo'linadi")
        self.t_shaxsiy.setToolTip("Faqat to'lovchining rasxodi")
        self.t_uchun.setToolTip("Siz to'laysiz, u qarzdor bo'ladi")
        self.tana.addWidget(quti)

        # ── takroriy eslatma ─────────────────────────────────────────
        self.takror_karta = Karta("Muddati kelgan takroriy rasxodlar")
        self.takror_quti = QVBoxLayout()
        self.takror_quti.setSpacing(7)
        w = shaffof(QWidget())
        w.setLayout(self.takror_quti)
        self.takror_karta.qosh(w)
        self.tana.addWidget(self.takror_karta)

        # ── bugungi rasxodlar ────────────────────────────────────────
        self.bugungi = Karta("Bugun yozilganlar")
        self.bugun_jadval = Jadval(
            ["Nomi", "Kategoriya", "Kim to'ladi", "Turi", "Summa"],
            pul_ustunlar={4})
        self.bugun_jadval.kengliklar(0, 150, 130, 130, 130)
        self.bugun_jadval.setMinimumHeight(170)
        self.bugun_jadval.doubleClicked.connect(
            lambda: self._tafsilot_och(self.bugun_jadval))
        self.bugungi.qosh(self.bugun_jadval)
        self.bugun_jami = izoh("")
        self.bugungi.qosh(self.bugun_jami)
        self.tana.addWidget(self.bugungi)

        # ── oxirgi rasxodlar ─────────────────────────────────────────
        oxirgi = Karta("Oxirgi yozuvlar")
        self.oxirgi_jadval = Jadval(
            ["Sana", "Nomi", "Kategoriya", "Kim to'ladi", "Turi", "Summa"],
            pul_ustunlar={5})
        self.oxirgi_jadval.kengliklar(110, 0, 130, 130, 130, 130)
        self.oxirgi_jadval.setMinimumHeight(290)
        self.oxirgi_jadval.doubleClicked.connect(
            lambda: self._tafsilot_och(self.oxirgi_jadval))
        oxirgi.qosh(self.oxirgi_jadval)
        self.tana.addWidget(oxirgi)
        self.tana.addStretch(1)

        self._itemlarni_yukla()

    # ── kategoriya → mahsulot ────────────────────────────────────────

    def _itemlarni_yukla(self):
        """Kategoriya tanlangach o'sha kategoriyaning mahsulotlari chiqadi."""
        with QSignalBlocker(self.t_item):
            self.t_item.clear()
            self.t_item.addItem("— mahsulot tanlanmagan —", None)
            for it in plan.turi_itemlari(self.db, self.t_turi.turi_id()):
                yorliqcha = it["nom"]
                if it["narx"]:
                    yorliqcha += f"  ·  {money.fmt(it['narx'])}"
                self.t_item.addItem(yorliqcha, it["id"])

    def _item_tanlandi(self):
        """Mahsulot tanlansa nomi va narxi o'zi to'ldiriladi.

        Narx qat'iy emas — bozorda har doim bir xil bo'lmaydi, shuning
        uchun uni qo'lda o'zgartirish mumkin, va o'zgartirilsa katalog
        ham yangilanadi.
        """
        iid = self.t_item.currentData()
        if not iid:
            return
        it = self.db.q1("SELECT nom, narx FROM item WHERE id=?", iid)
        if not it:
            return
        if not self.t_nom.text().strip():
            self.t_nom.setText(it["nom"])
        if it["narx"] and self.t_summa.qiymat() == 0:
            self.t_summa.qoy(it["narx"])

    def _turi_ozgardi(self):
        self.t_uchun_kim.setVisible(self.t_uchun.isChecked())

    # ── qo'shish ─────────────────────────────────────────────────────

    def _qosh(self):
        summa = self.t_summa.qiymat()
        if summa <= 0:
            self.ogoh.korsat("Summa kiritilmagan.", "xato", 3000)
            return

        uchunmi = self.t_uchun.isChecked()
        kim_uchun = self.t_uchun_kim.odam_id() if uchunmi else None
        if uchunmi and kim_uchun == self.t_kim.odam_id():
            self.ogoh.korsat(
                "To'lovchi va «kim uchun» bir odam — bu oddiy shaxsiy rasxod.",
                "xato", 5000)
            return

        iid = self.t_item.currentData()
        nom = self.t_nom.text().strip()
        try:
            entries.rasxod_qosh(
                self.db, self.t_sana.iso(), nom, summa, self.t_kim.odam_id(),
                umumiymi=self.t_umumiy.isChecked() or uchunmi,
                turi_id=self.t_turi.turi_id(), item_id=iid,
                kim_uchun=kim_uchun)
        except Exception as e:
            self.ogoh.korsat(str(e), "xato", 6000)
            return

        if iid:
            it = self.db.q1("SELECT narx FROM item WHERE id=?", iid)
            if it and it["narx"] != summa:
                plan.item_narx_yangila(self.db, iid, summa)

        self.t_nom.clear()
        self.t_summa.tozala()
        with QSignalBlocker(self.t_item):
            self.t_item.setCurrentIndex(0)
        self.t_nom.setFocus()
        self.oyna.yangila()

        tur = ("boshqa uchun" if uchunmi else
               "umumiy" if self.t_umumiy.isChecked() else "shaxsiy")
        self.ogoh.korsat(
            f"✔ {nom or 'rasxod'} — {money.fmt_som(summa)} ({tur})", "ok", 4000)

    def _tahrir(self):
        rid = self.oxirgi_jadval.tanlangan_id()
        if rid and RasxodDialog(self.db, rid, parent=self).exec():
            self.oyna.yangila()

    def _tafsilot_och(self, jadval):
        """Rasxod ustiga bosilganda: tafsilot + bekor qilish."""
        rid = jadval.tanlangan_id()
        if not rid:
            return
        d = RasxodTafsilot(self.db, rid, parent=self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()

    # ── yangilash ────────────────────────────────────────────────────

    def yangila(self):
        bugun = date.today()
        self.sana_izoh.setText(sana_uzun(bugun))
        # Dastur tunab qolsa ham sana ertalab bugungiga o'tsin
        if self.t_sana.iso() != bugun.isoformat() and not self.t_summa.qiymat():
            self.t_sana.qoy(bugun.isoformat())

        with QSignalBlocker(self.t_kim), QSignalBlocker(self.t_uchun_kim), \
                QSignalBlocker(self.t_turi):
            self.t_kim.yangila()
            self.t_uchun_kim.yangila()
            self.t_turi.yangila()
        self._itemlarni_yukla()

        a = ledger.audit(self.db)
        if not a.toza:
            self.ogoh.korsat("Kitob teng emas: " + "; ".join(a.muammolar[:2]),
                             "xato")
        else:
            # Puli kamayib qolganlar haqida ogohlantirish
            xabarlar = ledger.ogohlantirish(self.db)
            if xabarlar:
                self.ogoh.korsat("  ·  ".join(xabarlar), "ogoh")
            else:
                self.ogoh.yashir()

        # takroriy
        while self.takror_quti.count():
            x = self.takror_quti.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        kutilayotgan = recurring.kutilayotgan(self.db)
        self.takror_karta.setVisible(bool(kutilayotgan))
        for t in kutilayotgan:
            e = QLabel(f"<b>{t['nom']}</b> — {money.fmt_som(t['summa'])} "
                       f"({sana_qisqa(t['sana'])}, {t['odam_nom']})")
            e.setStyleSheet("QLabel{background:transparent;}")
            yoz = tugma("Yozish", asosiy=True)
            otkaz = tugma("O'tkazib yuborish")
            yoz.clicked.connect(lambda _, i=t["id"]: self._takror_yoz(i))
            otkaz.clicked.connect(lambda _, i=t["id"]: self._takror_otkaz(i))
            self.takror_quti.addWidget(qator(e, None, otkaz, yoz))

        # bugungi yozuvlar
        bugungi, idlar, jami = [], [], 0
        for r in self._rasxodlar("AND r.sana=?", bugun.isoformat()):
            bugungi.append([
                r["nom"] or "—",
                f"{r['belgi'] or ''} {r['turi_nom'] or ''}".strip() or "—",
                r["odam_nom"], rasxod_turi(r), r["summa"]])
            idlar.append(r["id"])
            jami += r["summa"]
        self.bugun_jadval.tuldir(bugungi, idlar)
        self.bugun_jami.setText(
            f"Bugun jami: {money.fmt_som(jami)}" if jami
            else "Bugun hali rasxod yozilmagan.")

        # oxirgi yozuvlar
        qatorlar, idlar = [], []
        for r in self._rasxodlar("", limit=15):
            qatorlar.append([
                sana_qisqa(r["sana"]), r["nom"] or "—",
                f"{r['belgi'] or ''} {r['turi_nom'] or ''}".strip() or "—",
                r["odam_nom"], rasxod_turi(r), r["summa"]])
            idlar.append(r["id"])
        self.oxirgi_jadval.tuldir(qatorlar, idlar)

    def _rasxodlar(self, qoshimcha: str = "", *p, limit: int | None = None):
        return self.db.q(
            "SELECT r.*, t.nom turi_nom, t.belgi belgi, o.nom odam_nom,"
            "       u.nom kim_uchun_nom"
            " FROM rasxod r LEFT JOIN turi t ON t.id=r.turi_id"
            " JOIN odam o ON o.id=r.kim_toladi"
            " LEFT JOIN odam u ON u.id=r.kim_uchun"
            f" WHERE r.ochirilgan=0 {qoshimcha}"
            " ORDER BY r.sana DESC, r.id DESC"
            + (f" LIMIT {int(limit)}" if limit else ""), *p)

    def _takror_yoz(self, tid):
        recurring.yoz(self.db, tid)
        self.oyna.yangila()

    def _takror_otkaz(self, tid):
        recurring.otkaz(self.db, tid)
        self.oyna.yangila()


# ═══════════════════════════════════════════════════════ RASXODLAR

class RasxodSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        yangi = tugma("+ Yangi rasxod", asosiy=True)
        yangi.clicked.connect(self._yangi)
        self.tana.addWidget(qator(sarlavha("Rasxodlar"), None, yangi))

        f = Karta("Saralash")
        self.f_dan = SanaEdit((date.today() - timedelta(days=60)).isoformat())
        self.f_gacha = SanaEdit()
        self.f_kim = OdamTanla(self.db, hammasi=True)
        self.f_turi = TuriTanla(self.db, hammasi=True)
        self.f_matn = QLineEdit()
        self.f_matn.setPlaceholderText("Nomi bo'yicha qidirish…")
        for w in (self.f_dan, self.f_gacha):
            w.dateChanged.connect(self.yangila)
        self.f_kim.currentIndexChanged.connect(self.yangila)
        self.f_turi.currentIndexChanged.connect(self.yangila)
        self.f_matn.textChanged.connect(self.yangila)
        f.qosh(qator("Dan:", self.f_dan, "Gacha:", self.f_gacha,
                     "Kim:", self.f_kim, "Kategoriya:", self.f_turi))
        f.qosh(self.f_matn)
        self.tana.addWidget(f)

        self.xulosa = izoh("")
        self.tana.addWidget(self.xulosa)

        self.jadval = Jadval(
            ["Sana", "Nomi", "Kategoriya", "Kim to'ladi", "Turi", "Chek", "Summa"],
            pul_ustunlar={6})
        self.jadval.kengliklar(105, 0, 145, 130, 105, 60, 125)
        self.jadval.setMinimumHeight(430)
        # Rasxod ustiga bosilsa — tafsilot oynasi. Bekor qilish o'sha
        # yerda: summasi va ulushlari ko'rinib turganda.
        self.jadval.doubleClicked.connect(self._tafsilot_och)
        self.tana.addWidget(self.jadval)

        t1 = tugma("Tafsilot va bekor qilish", asosiy=True)
        t2 = tugma("Tahrirlash")
        t1.clicked.connect(self._tafsilot_och)
        t2.clicked.connect(self._tahrir)
        self.tana.addWidget(qator(None, t1, t2))

        self.tafsilot = Karta("Tanlangan rasxodning ulushlari")
        self.tafsilot_jadval = Jadval(["Odam", "Ulushi", "Yaxlitlash"],
                                      pul_ustunlar={1})
        self.tafsilot_jadval.kengliklar(0, 130, 110)
        self.tafsilot_jadval.setMaximumHeight(190)
        self.tafsilot.qosh(self.tafsilot_jadval)
        self.tana.addWidget(self.tafsilot)
        self.jadval.itemSelectionChanged.connect(self._tafsilot)
        self.tana.addStretch(1)

    def _shart(self):
        w = ["r.ochirilgan=0", "r.sana BETWEEN ? AND ?"]
        p = [self.f_dan.iso(), self.f_gacha.iso()]
        if self.f_kim.odam_id():
            w.append("r.kim_toladi=?")
            p.append(self.f_kim.odam_id())
        if self.f_turi.turi_id():
            w.append("r.turi_id=?")
            p.append(self.f_turi.turi_id())
        if self.f_matn.text().strip():
            w.append("(r.nom LIKE ? OR r.izoh LIKE ?)")
            q = f"%{self.f_matn.text().strip()}%"
            p += [q, q]
        return " AND ".join(w), p

    def yangila(self):
        shart, p = self._shart()
        qatorlar, idlar = [], []
        umumiy = shaxsiy = uchun = 0
        for r in self.db.q(
                "SELECT r.*, t.nom turi_nom, t.belgi belgi, o.nom odam_nom,"
                "       u.nom kim_uchun_nom"
                "     , (SELECT COUNT(*) FROM chek c WHERE c.rasxod_id=r.id) chek"
                " FROM rasxod r LEFT JOIN turi t ON t.id=r.turi_id"
                " JOIN odam o ON o.id=r.kim_toladi"
                " LEFT JOIN odam u ON u.id=r.kim_uchun"
                f" WHERE {shart} ORDER BY r.sana DESC, r.id DESC", *p):
            qatorlar.append([
                sana_qisqa(r["sana"]), r["nom"] or "—",
                f"{r['belgi'] or ''} {r['turi_nom'] or ''}".strip() or "—",
                r["odam_nom"], rasxod_turi(r),
                ("📎 " + str(r["chek"])) if r["chek"] else "",
                r["summa"]])
            idlar.append(r["id"])
            if r["kim_uchun_nom"]:
                uchun += r["summa"]
            elif r["umumiymi"]:
                umumiy += r["summa"]
            else:
                shaxsiy += r["summa"]
        self.jadval.tuldir(qatorlar, idlar)
        qismlar = [f"{len(qatorlar)} ta yozuv",
                   f"umumiy {money.fmt_som(umumiy)}",
                   f"shaxsiy {money.fmt_som(shaxsiy)}"]
        if uchun:
            qismlar.append(f"boshqa uchun {money.fmt_som(uchun)}")
        qismlar.append(f"jami {money.fmt_som(umumiy + shaxsiy + uchun)}")
        self.xulosa.setText("  ·  ".join(qismlar))
        self._tafsilot()

    def _tafsilot(self):
        rid = self.jadval.tanlangan_id()
        if not rid:
            self.tafsilot.setVisible(False)
            return
        qatorlar = [[r["nom"], r["summa"],
                     f"+{r['yaxlitlash']}" if r["yaxlitlash"] else ""]
                    for r in self.db.q(
                        "SELECT u.summa, u.yaxlitlash, o.nom FROM ulush u"
                        " JOIN odam o ON o.id=u.odam_id WHERE u.rasxod_id=?"
                        " ORDER BY o.tartib", rid)]
        self.tafsilot.setVisible(bool(qatorlar))
        self.tafsilot_jadval.tuldir(qatorlar)

    def _yangi(self):
        if RasxodDialog(self.db, parent=self).exec():
            self.oyna.yangila()

    def _tahrir(self):
        rid = self.jadval.tanlangan_id()
        if not rid:
            return
        if RasxodDialog(self.db, rid, parent=self).exec():
            self.oyna.yangila()

    def _tafsilot_och(self):
        rid = self.jadval.tanlangan_id()
        if not rid:
            return
        d = RasxodTafsilot(self.db, rid, parent=self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()


# ═══════════════════════════════════════════════════════════ KIRIM

class KirimSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        yangi = tugma("+ Yangi kirim", asosiy=True)
        yangi.clicked.connect(self._yangi)
        self.tana.addWidget(qator(sarlavha("Kirim"), None, yangi))

        self.kartalar_quti = QWidget()
        shaffof(self.kartalar_quti)
        self.kartalar = QHBoxLayout(self.kartalar_quti)
        self.kartalar.setContentsMargins(0, 0, 0, 0)
        self.kartalar.setSpacing(14)
        self.tana.addWidget(self.kartalar_quti)

        self.jadval = Jadval(["Sana", "Kim", "Qayerdan", "Summa"], pul_ustunlar={3})
        self.jadval.kengliklar(105, 150, 0, 140)
        self.jadval.setMinimumHeight(430)
        self.jadval.doubleClicked.connect(self._tahrir)
        self.tana.addWidget(self.jadval)

        t1 = tugma("Tahrirlash")
        t2 = tugma("O'chirish", xavfli=True)
        t1.clicked.connect(self._tahrir)
        t2.clicked.connect(self._ochir)
        self.tana.addWidget(qator(None, t1, t2))
        self.tana.addStretch(1)

    def yangila(self):
        while self.kartalar.count():
            x = self.kartalar.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        for r in ledger.balanslar(self.db):
            self.kartalar.addWidget(RaqamKarta(r["nom"], r["kirim"], "jami kirim"))

        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT k.*, o.nom FROM kirim k JOIN odam o ON o.id=k.odam_id"
                " WHERE k.ochirilgan=0 ORDER BY k.sana DESC, k.id DESC"):
            qatorlar.append([sana_qisqa(r["sana"]), r["nom"],
                             r["sabab"] or "—", r["summa"]])
            idlar.append(r["id"])
        self.jadval.tuldir(qatorlar, idlar)

    def _yangi(self):
        if KirimDialog(self.db, parent=self).exec():
            self.oyna.yangila()

    def _tahrir(self):
        kid = self.jadval.tanlangan_id()
        if kid and KirimDialog(self.db, kid, parent=self).exec():
            self.oyna.yangila()

    def _ochir(self):
        kid = self.jadval.tanlangan_id()
        if not kid:
            return
        if tasdiq(self, "Kirim o'chirilsinmi?"):
            try:
                entries.kirim_ochir(self.db, kid)
            except Exception as e:
                xato_koraset(self, str(e))
                return
            self.oyna.yangila()


# ════════════════════════════════════════════════════════════ QARZ

class QarzSahifa(Sahifa):
    """Qarz — blok-blok yopiladi.

    Excel'da har rasxod qatorining yonida "Ha/Yo'q" ustuni bor edi:
    "mana shu bozorlikning pulini berdim". Shu mantiq shu yerda:
    hamma qarzni bir yo'la yopish SHART EMAS, har bir rasxodni alohida
    to'landi deb belgilash mumkin, va xato bo'lsa qayta ochish ham.
    """

    def __init__(self, oyna):
        super().__init__(oyna)
        yangi = tugma("+ Qarz yozish", asosiy=True)
        tolov = tugma("+ Erkin to'lov")
        yangi.clicked.connect(self._yangi)
        tolov.clicked.connect(lambda: self._tolov())
        self.tana.addWidget(qator(sarlavha("Qarz"), None, tolov, yangi))

        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        # ── kim kimga qarzdor ────────────────────────────────────────
        self.holat = Karta("Kim kimga qarzdor")
        self.holat_quti = QVBoxLayout()
        self.holat_quti.setSpacing(8)
        w = shaffof(QWidget())
        w.setLayout(self.holat_quti)
        self.holat.qosh(w)
        self.tana.addWidget(self.holat)

        # ── bloklar ──────────────────────────────────────────────────
        self.bloklar = Karta("To'lanmagan rasxodlar — bittalab yopiladi")
        self.f_qarzdor = OdamTanla(self.db, hammasi=True)
        self.f_kreditor = OdamTanla(self.db, hammasi=True)
        self.f_tolangan = QCheckBox("To'langanlari ham ko'rinsin")
        for w2 in (self.f_qarzdor, self.f_kreditor):
            w2.currentIndexChanged.connect(self.yangila)
        self.f_tolangan.toggled.connect(self.yangila)
        self.bloklar.qosh(qator("Kim qarzdor:", self.f_qarzdor,
                                "Kimga:", self.f_kreditor,
                                self.f_tolangan, None))

        self.blok_jadval = Jadval(
            ["", "Sana", "Rasxod", "Kategoriya", "Kim to'ladi", "Kim qarzdor",
             "Ulushi"], pul_ustunlar={6})
        self.blok_jadval.kengliklar(34, 105, 0, 140, 130, 130, 125)
        self.blok_jadval.setMinimumHeight(340)
        self.blok_jadval.setSelectionMode(QTableWidget.ExtendedSelection)
        self.bloklar.qosh(self.blok_jadval)

        yop = tugma("Tanlanganlarni to'landi deb belgilash", asosiy=True)
        och = tugma("Qayta ochish")
        yop.clicked.connect(self._tanlanganni_yop)
        och.clicked.connect(self._tanlanganni_och)
        self.blok_xulosa = izoh("")
        self.bloklar.qosh(qator(self.blok_xulosa, None, och, yop))
        # Ikki marta bosish bilan to'lov YOZILMAYDI: bu juda oson
        # tasodifan bosiladi va pulni jimgina o'zgartirib yuboradi.
        # Faqat aniq tugma bosilganda yoziladi.
        self.bloklar.qosh(izoh("Bir nechtasini Ctrl yoki Shift bilan tanlang."))
        self.tana.addWidget(self.bloklar)

        # ── qo'lda yozilgan qarzlar ──────────────────────────────────
        q = Karta("Qo'lma-qo'l berilgan qarzlar")
        self.qarz_jadval = Jadval(["Sana", "Kim berdi", "Kimga", "Sabab", "Summa"],
                                  pul_ustunlar={4})
        self.qarz_jadval.kengliklar(110, 140, 140, 0, 130)
        self.qarz_jadval.setMinimumHeight(170)
        q.qosh(self.qarz_jadval)
        qo = tugma("O'chirish", xavfli=True)
        qo.clicked.connect(self._qarz_ochir)
        q.qosh(qator(None, qo))
        self.tana.addWidget(q)

        # ── to'lovlar ────────────────────────────────────────────────
        h = Karta("To'lovlar tarixi")
        self.hk_jadval = Jadval(["Sana", "Kim to'ladi", "Kimga", "Nima uchun", "Summa"],
                                pul_ustunlar={4})
        self.hk_jadval.kengliklar(110, 140, 140, 0, 130)
        self.hk_jadval.setMinimumHeight(170)
        h.qosh(self.hk_jadval)
        ho = tugma("O'chirish", xavfli=True)
        ho.clicked.connect(self._hk_ochir)
        h.qosh(qator(None, ho))
        self.tana.addWidget(h)
        self.tana.addStretch(1)

    # ── bloklar ──────────────────────────────────────────────────────

    def _tanlangan_bloklar(self) -> list[int]:
        idlar = []
        for r in {i.row() for i in self.blok_jadval.selectedIndexes()}:
            it = self.blok_jadval.item(r, 0)
            if it:
                idlar.append(it.data(Qt.UserRole))
        return idlar

    def _tanlanganni_yop(self):
        idlar = [i for i in self._tanlangan_bloklar()
                 if not self._tolangan.get(i)]
        if not idlar:
            self.xabar.korsat("To'lanmagan qator tanlanmagan.", "ogoh", 3000)
            return
        settle.bloklarni_yop(self.db, idlar, date.today().isoformat())
        self.oyna.yangila()
        self.xabar.korsat(f"✔ {len(idlar)} ta rasxod to'landi deb belgilandi.",
                          "ok", 4000)

    def _tanlanganni_och(self):
        idlar = [i for i in self._tanlangan_bloklar() if self._tolangan.get(i)]
        if not idlar:
            self.xabar.korsat("To'langan qator tanlanmagan.", "ogoh", 3000)
            return
        with self.db.amal(f"{len(idlar)} ta blok qayta ochildi"):
            for i in idlar:
                settle.blok_och(self.db, i)
        self.oyna.yangila()

    # ── yangilash ────────────────────────────────────────────────────

    def yangila(self):
        with QSignalBlocker(self.f_qarzdor), QSignalBlocker(self.f_kreditor):
            self.f_qarzdor.yangila(hammasi=True)
            self.f_kreditor.yangila(hammasi=True)

        while self.holat_quti.count():
            x = self.holat_quti.takeAt(0)
            if x.widget():
                x.widget().deleteLater()

        juftlar = ledger.juft_qarzlar(self.db)
        if juftlar:
            for j in juftlar:
                e = BosiladiganYorliq(
                    f"<b>{j.qarzdor_nom}</b> → <b>{j.kreditor_nom}</b>: "
                    f"{money.fmt_som(j.summa)}  <span style='font-size:12px'>"
                    f"‹ tafsilot ›</span>")
                e.setStyleSheet("QLabel{background:transparent;font-size:15px;}")
                e.setToolTip("Shu qarz nimalardan yig'ilganini ko'rish")
                e.bosildi.connect(lambda x=j: self._juft_tafsilot(x))
                b = tugma("To'lov yozish")
                b.clicked.connect(lambda _, x=j: self._tolov(
                    x.qarzdor_id, x.kreditor_id, x.summa))
                self.holat_quti.addWidget(qator(e, None, b))
        else:
            self.holat_quti.addWidget(
                Holat("✔  Hech kim hech kimga qarzdor emas."))

        # bloklar
        qatorlar, idlar = [], []
        self._tolangan = {}
        ochiq_jami = 0
        for b in settle.ochiq_bloklar(
                self.db, self.f_qarzdor.odam_id(), self.f_kreditor.odam_id(),
                tolanganlar=self.f_tolangan.isChecked()):
            uid = b["ulush_id"]
            self._tolangan[uid] = bool(b["tolandi"])
            if not b["tolandi"]:
                ochiq_jami += b["summa"]
            nom = b["nom"] or "—"
            if b["kim_uchun"]:
                nom += "  (uning uchun olingan)"
            qatorlar.append([
                "✔" if b["tolandi"] else "",
                sana_qisqa(b["sana"]), nom,
                f"{b['turi_belgi'] or ''} {b['turi_nom'] or ''}".strip() or "—",
                b["kreditor"], b["qarzdor"], b["summa"]])
            idlar.append(uid)
        self.blok_jadval.tuldir(qatorlar, idlar)
        ochiq = sum(1 for v in self._tolangan.values() if not v)
        self.blok_xulosa.setText(
            f"{ochiq} ta to'lanmagan · jami {money.fmt_som(ochiq_jami)}"
            if ochiq else "Hamma rasxod to'langan.")

        # qarzlar
        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT q.*, a.nom a, b.nom b FROM qarz q"
                " JOIN odam a ON a.id=q.kim_berdi JOIN odam b ON b.id=q.kimga"
                " WHERE q.ochirilgan=0 ORDER BY q.sana DESC, q.id DESC"):
            qatorlar.append([sana_qisqa(r["sana"]), r["a"], r["b"],
                             r["sabab"] or "—", r["summa"]])
            idlar.append(r["id"])
        self.qarz_jadval.tuldir(qatorlar, idlar)

        # to'lovlar
        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT h.*, a.nom a, b.nom b FROM hisob_kitob h"
                " JOIN odam a ON a.id=h.kim_toladi JOIN odam b ON b.id=h.kimga"
                " WHERE h.ochirilgan=0 ORDER BY h.sana DESC, h.id DESC"):
            qatorlar.append([sana_qisqa(r["sana"]), r["a"], r["b"],
                             r["izoh"] or "—", r["summa"]])
            idlar.append(r["id"])
        self.hk_jadval.tuldir(qatorlar, idlar)

    # ── boshqa amallar ───────────────────────────────────────────────

    def _yangi(self):
        if QarzDialog(self.db, self).exec():
            self.oyna.yangila()

    def _juft_tafsilot(self, juft):
        """Qatorga bosilganda: shu qarz nimalardan yig'ilgan."""
        d = JuftTafsilot(self.db, juft.qarzdor_id, juft.kreditor_id,
                         parent=self)
        d.exec()
        if d.tolov_soraldi:
            self._tolov(juft.qarzdor_id, juft.kreditor_id, juft.summa)

    def _tolov(self, kimdan=None, kimga=None, summa=0):
        d = TolovDialog(self.db, kimdan if isinstance(kimdan, int) else None,
                        kimga if isinstance(kimga, int) else None,
                        summa if isinstance(summa, int) else 0, self)
        if d.exec():
            self.oyna.yangila()

    def _qarz_ochir(self):
        qid = self.qarz_jadval.tanlangan_id()
        if qid and tasdiq(self, "Qarz yozuvi o'chirilsinmi?"):
            entries.qarz_ochir(self.db, qid)
            self.oyna.yangila()

    def _hk_ochir(self):
        hid = self.hk_jadval.tanlangan_id()
        if not hid:
            return
        h = self.db.q1("SELECT ulush_id FROM hisob_kitob WHERE id=?", hid)
        if h and h["ulush_id"]:
            if not tasdiq(self, "Bu to'lov aniq bitta rasxodga bog'langan.\n\n"
                                "O'chirilsa o'sha rasxod yana to'lanmagan "
                                "bo'lib qoladi. Davom etilsinmi?"):
                return
            settle.blok_och(self.db, h["ulush_id"])
        elif tasdiq(self, "To'lov yozuvi o'chirilsinmi?"):
            entries.hisob_kitob_ochir(self.db, hid)
        else:
            return
        self.oyna.yangila()
