"""Analitika → «Reja va fakt»: oylik reja haqiqiy rasxod bilan.

Alohida sahifa EMAS — `AnalitikaSahifa` ichidagi ikkinchi ko'rinish
(«Kategoriyalar» | «Reja va fakt» tugmalari). Hamma raqam
`plan.reja_va_fakt()` dan keladi: bu fayl faqat CHIZADI.

Rang — `theme.daraja_rangi()` zinapoyasi, dasturning qolgan joyi bilan
bir xil: yashil — reja doirasida, sariq — limitga yaqin
(`plan.YAQIN_FOIZ`), qizil — oshib ketdi. Oshib ketgan summa
yashirilmaydi va chiziq to'lib turadi.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox,
                               QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QRadioButton, QScrollArea,
                               QVBoxLayout, QWidget)

import money
from core import kategoriya, plan
from core import mahsulot as mh
from ui.eski import theme
from ui.eski.dialogs import MahsulotRoyxat, tasdiq, xato_koraset
from ui.eski.sahifa_asosiy import OYLAR, shaffof
from ui.eski.widgets import (Chizgi, Jadval, Karta, KategoriyaTanla, OdamTanla,
                             PulEdit, RaqamKarta, SanaEdit, belgi_rasm, bolim,
                             chiziq, izoh, qator, sarlavha, tugma, yoq)

# plan holati → theme daraja zinapoyasi
DARAJA = {"yaxshi": "yaxshi", "yaqin": "kam", "oshdi": "qarzda"}
HOLAT_MATN = {"yaqin": "⚠ Limitga yaqin", "oshdi": "✕ Rejadan oshdi",
              "rejasiz": "Reja qo'yilmagan"}


def oy_nomi(oy: str) -> str:
    """'2026-09' → 'Sentabr 2026'."""
    return f"{OYLAR[int(oy[5:7]) - 1].capitalize()} {oy[:4]}"


def _yozuv(matn: str = "", rang: str | None = None, olcham: int = theme.O_ASOS,
           ogirlik: int = 400, ong: bool = False) -> QLabel:
    """Rangli yorliq. O'lcham QSS'da — global `QLabel` stili `setFont()`
    ni bosib ketadi."""
    e = QLabel(matn)
    e._stil = (rang, olcham, ogirlik)
    _yozuv_boya(e)
    if ong:
        e.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return e


def _yozuv_boya(e: QLabel, rang: str | None = None) -> None:
    if rang is not None:
        e._stil = (rang, *e._stil[1:])
    r, o, w = e._stil
    e.setStyleSheet(
        f"QLabel {{ color:{r or theme.MATN}; background:transparent;"
        f" border:none; font-size:{o}px; font-weight:{w}; }}")


def _belgi(q: dict, olcham: int = 26) -> QLabel:
    e = QLabel()
    e.setFixedSize(olcham, olcham)
    e.setAlignment(Qt.AlignCenter)
    e.setStyleSheet("QLabel { background:transparent; border:none; }")
    yol = kategoriya.rasm_yoli(q.get("rasm"))
    if yol:
        e.setPixmap(belgi_rasm(yol, olcham, e))
    else:
        e.setText(q.get("belgi") or "•")
    return e


# ═══════════════════════════════════════════ reja yozuvi (rasxod kabi)

class RejaYozuvDialog(QDialog):
    """Rejaga yozuv — xuddi rasxod kabi: sana, kategoriya, ichida bir
    nechta mahsulot, sabab va summa. Pul hech kimdan chiqmaydi, shuning
    uchun «kim to'ladi» va bo'lish yo'q. Saqlash — `plan.reja_yozuv_saqla`
    (bitta undo)."""

    def __init__(self, db, oy: str, qator_id: int | None = None, parent=None,
                 odam_id: int | None = None):
        super().__init__(parent)
        self.db, self.oy, self.qator_id = db, oy, qator_id
        self.setWindowTitle("Rejani tahrirlash" if qator_id
                            else f"Rejaga qo'shish — {oy_nomi(oy)}")
        self.setMinimumWidth(600)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setSpacing(11)
        f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        bugun = plan.oy_bugungacha()[1]
        self.sana = SanaEdit(bugun if bugun[:7] == oy else oy + "-01")
        self.turi = KategoriyaTanla(db)
        self.mahsulotlar = MahsulotRoyxat(db)
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("masalan: Haftalik bozorlik")
        self.summa = PulEdit()
        self.turi.ozgardi.connect(
            lambda: self.mahsulotlar.turi_qoy(self.turi.turi_id()))
        f.addRow("Sana", self.sana)
        f.addRow("Kategoriya *", self.turi)
        f.addRow("Mahsulotlar", self.mahsulotlar)
        f.addRow("Nomi / sabab *", self.nom)
        f.addRow("Summa", self.summa)
        v.addLayout(f)

        # Umumiy (uyniki) yoki shaxsiy (bitta odamniki) reja.
        self.umumiy = QRadioButton("Umumiy")
        self.shaxsiy = QRadioButton("Shaxsiy")
        guruh = QButtonGroup(self)
        guruh.addButton(self.umumiy)
        guruh.addButton(self.shaxsiy)
        self.kim = OdamTanla(db)
        (self.umumiy if odam_id is None else self.shaxsiy).setChecked(True)
        if odam_id is not None:
            self.kim.tanla(odam_id)
        self.shaxsiy.toggled.connect(
            lambda: self.kim.setVisible(self.shaxsiy.isChecked()))
        self.kim.setVisible(self.shaxsiy.isChecked())
        v.addWidget(qator(self.umumiy, self.shaxsiy, self.kim, None))
        v.addWidget(izoh("Reja — faqat mo'ljal: pul hech kimdan chiqmaydi. "
                         "Sana qaysi oyga tushsa, o'sha oyning rejasiga "
                         "qo'shiladi."))

        t = QDialogButtonBox()
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)

        self.mahsulotlar.turi_qoy(self.turi.turi_id())
        self.mahsulotlar.bogla(self.summa, self.nom)
        if qator_id:
            self._yukla(qator_id)

    def _yukla(self, qator_id: int):
        r = self.db.q1("SELECT * FROM reja_qator WHERE id=?", qator_id)
        if not r:
            return
        if r["sana"]:
            self.sana.qoy(r["sana"])
        self.turi.tanla(r["turi_id"])
        self.mahsulotlar.yukla(plan.reja_yozuv_mahsulotlari(self.db, qator_id))
        self.nom.setText(r["nom"] or "")
        self.summa.qoy(r["summa"])
        if r["umumiymi"]:
            self.umumiy.setChecked(True)
        else:
            self.shaxsiy.setChecked(True)
            self.kim.tanla(r["odam_id"])

    def _saqla(self):
        try:
            self.qator_id = plan.reja_yozuv_saqla(
                self.db, self.sana.iso(), self.nom.text(),
                self.turi.turi_id(), self.summa.qiymat(),
                self.mahsulotlar.qatorlar(), self.qator_id,
                umumiymi=self.umumiy.isChecked(),
                odam_id=(self.kim.odam_id() if self.shaxsiy.isChecked()
                         else None))
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ═══════════════════════════════════════════ umumiy reja va limitlar

class RejaDialog(QDialog):
    """Umumiy oylik summa + har kategoriya limiti. Bitta undo qadami.

    Kategoriya rejasi = shu limit + rasxod kabi kiritilgan reja
    yozuvlari (`plan.turi_reja`). Bu oyna faqat limit qismini o'zgartiradi.
    """

    def __init__(self, db, oy: str, parent=None):
        super().__init__(parent)
        self.db, self.oy = db, oy
        self.setWindowTitle(f"Umumiy reja va limitlar — {oy_nomi(oy)}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(560)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)

        v.addWidget(bolim("Umumiy oylik reja"))
        self.umumiy = PulEdit(plan.oylik_reja(db, oy) or 0)
        self.umumiy.setPlaceholderText("kategoriyalar yig'indisi")
        v.addWidget(self.umumiy)
        v.addWidget(izoh("Bo'sh qoldirilsa, oylik reja kategoriyalar "
                         "rejasining yig'indisi bo'ladi."))

        v.addWidget(bolim("Kategoriya limitlari"))
        v.addWidget(izoh("Limit kiritilgan reja yozuvlariga QO'SHILADI. "
                         "Mahsulotlar bilan reja — «+ Reja qo'shish»."))
        ichki = QWidget()
        shaffof(ichki)
        g = QGridLayout(ichki)
        g.setContentsMargins(0, 0, 8, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        self.maydonlar: dict[int, PulEdit] = {}
        for i, k in enumerate(plan.reja_kategoriyalari(db, oy)):
            g.addWidget(_belgi(k, 24), i, 0)
            nom = _yozuv(k["nom"])
            if k["fakt"]:
                nom.setToolTip(f"Bu oy sarflangan: {money.fmt_som(k['fakt'])}")
            g.addWidget(nom, i, 1)
            qism = ([f"yozuvlar {money.fmt(k['yozuv'])}"] if k["yozuv"]
                    else []) + ([f"fakt {money.fmt(k['fakt'])}"]
                                if k["fakt"] else [])
            g.addWidget(_yozuv(" · ".join(qism), theme.KUL, theme.O_MAYDA,
                               ong=True), i, 2)
            p = PulEdit(k["reja"])
            p.setFixedWidth(150)
            p.ozgardi.connect(self._jami_yangila)
            g.addWidget(p, i, 3)
            self.maydonlar[k["turi_id"]] = p
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setFrameShape(QScrollArea.NoFrame)
        aylanma.setWidget(ichki)
        v.addWidget(aylanma, 1)

        self.jami = izoh("")
        v.addWidget(self.jami)

        t = QDialogButtonBox()
        kochir = t.addButton("O'tgan oydan olish", QDialogButtonBox.ResetRole)
        kochir.setToolTip(f"{oy_nomi(plan.oy_sur(oy, -1))} rejasini "
                          f"maydonlarga qo'yadi (saqlanmaguncha yozilmaydi)")
        kochir.clicked.connect(self._otgan_oy)
        t.addButton("Saqlash", QDialogButtonBox.AcceptRole).setObjectName("Asosiy")
        t.addButton("Bekor", QDialogButtonBox.RejectRole)
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        v.addWidget(t)
        self._jami_yangila()

    def _jami_yangila(self, *_):
        jami = sum(p.qiymat() for p in self.maydonlar.values())
        umumiy = self.umumiy.qiymat()
        jami += sum(plan.yozuv_reja(self.db, self.oy).values())
        matn = f"Kategoriyalar jami (yozuvlar bilan): {money.fmt_som(jami)}"
        if umumiy and jami > umumiy:
            matn += (f" — umumiy rejadan {money.fmt_som(jami - umumiy)} "
                     f"ko'p")
        self.jami.setText(matn)

    def _otgan_oy(self):
        dan = plan.oy_sur(self.oy, -1)
        if not plan.reja_bormi(self.db, dan):
            xato_koraset(self, f"{oy_nomi(dan)} uchun reja yo'q.")
            return
        self.umumiy.qoy(plan.oylik_reja(self.db, dan) or 0)
        eski = plan.limit_reja(self.db, dan)
        for tid, p in self.maydonlar.items():
            p.qoy(eski.get(tid, 0))
        self._jami_yangila()

    def _saqla(self):
        try:
            plan.reja_saqla(self.db, self.oy, self.umumiy.qiymat() or None,
                            {tid: p.qiymat() for tid, p in self.maydonlar.items()})
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ═══════════════════════════════════ toifa ichi: reja ro'yxatlari va fakt

def reja_ochir_sora(ota, db, qid: int) -> bool:
    """Reja ro'yxatini tasdiq bilan o'chiradi (bitta undo). Unga yozilgan
    haqiqiy rasxod O'CHMAYDI — pul rostdan to'langan."""
    r = db.q1("SELECT nom, summa, rasxod_id FROM reja_qator WHERE id=?", qid)
    if not r:
        return False
    matn = (f"«{r['nom']}» ({money.fmt_som(r['summa'])}) rejadan "
            f"o'chirilsinmi?")
    if r["rasxod_id"] and db.q1(
            "SELECT 1 FROM rasxod WHERE id=? AND ochirilgan=0", r["rasxod_id"]):
        matn += "\n\nUnga yozilgan haqiqiy rasxod o'chmaydi."
    if not tasdiq(ota, matn):
        return False
    plan.reja_yozuv_ochir(db, qid)
    return True


class RejaKategoriyaOyna(QDialog):
    """«Toifalar bo'yicha» qatori bosilganda: shu toifaning reja
    RO'YXATLARI (har reja yozuvi — bitta ro'yxat: sanasi, nomi, nechta
    mahsulot, reja va aslida to'langani). Ro'yxat ochilsa —
    `RejaRoyxatOyna`: uning mahsulotlari va «aslida to'landi».
    Doira — panelniki (umumiy yoki tanlangan odamning shaxsiysi)."""

    def __init__(self, db, oy: str, turi_id: int, nom: str,
                 odam_id: int | None = None, parent=None):
        super().__init__(parent)
        self.db, self.oy, self.turi_id = db, oy, turi_id
        self.nom, self.odam_id = nom, odam_id
        self.ozgardi = False
        self.setWindowTitle(f"{nom} — {oy_nomi(oy)}")
        self.setMinimumSize(760, 620)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        v.addWidget(sarlavha(nom))
        self.xulosa = izoh("")
        v.addWidget(self.xulosa)
        # Kun bo'yicha: reja — kategoriyaga ajratilgan pul; shu
        # kategoriyadan qilingan HAR QANDAY rasxod ayiriladi, ro'yxatdagi
        # mahsulotlar bilan mos kelishi shart emas (`plan.kategoriya_kunlari`).
        v.addWidget(bolim("Kunlar bo'yicha"))
        self.kunlar = Jadval(["Sana", "Ro'yxatlar", "Reja", "Sarflandi",
                              "Holat"], pul_ustunlar={2, 3},
                             bosh_matn="Bu oy bu toifada reja ham, rasxod ham yo'q")
        self.kunlar.kengliklar(90, 0, 110, 110, 140)
        v.addWidget(self.kunlar, 1)
        v.addWidget(bolim("Reja ro'yxatlari (tafsilot)"))
        self.royxat = Jadval(["Sana", "Ro'yxat", "Mahsulotlar", "Reja"],
                             pul_ustunlar={3},
                             bosh_matn="Bu toifada hali reja ro'yxati yo'q")
        self.royxat.kengliklar(90, 0, 100, 110)
        self.royxat.doubleClicked.connect(self._och)
        v.addWidget(self.royxat, 1)

        och = tugma("Ro'yxatni ochish", asosiy=True)
        och.clicked.connect(self._och)
        qosh = tugma("+ Yangi ro'yxat")
        qosh.clicked.connect(self._qosh)
        nusxa = tugma("Nusxa olish")
        nusxa.setToolTip("Tanlangan ro'yxatdan nusxa — keyingi kunga, "
                         "mahsulotlari bilan")
        nusxa.clicked.connect(self._nusxa)
        ochir = tugma("O'chirish", xavfli=True)
        ochir.clicked.connect(self._ochir)
        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        # Tahrirlash — ro'yxatning ICHIDA (`RejaRoyxatOyna`), bu yerda emas.
        v.addWidget(qator(qosh, nusxa, ochir, None, och, yop))
        self._qur()

    def _qur(self):
        self.yozuvlar = plan.kategoriya_reja_yozuvlari(
            self.db, self.oy, self.turi_id, self.odam_id)
        # Eski «limit» (ro'yxatsiz kategoriya rejasi) ham qator bo'lib
        # chiqadi; ochilsa oddiy ro'yxatga aylanadi (`limitni_royxatga`).
        kk = plan.kategoriya_kunlari(self.db, self.oy, self.turi_id,
                                     self.odam_id)
        self.limit = kk["limit"]
        qolgan = kk["qolgan"]
        self.xulosa.setText(
            f"Reja {money.fmt_som(kk['reja'])} · shu kategoriyadan "
            f"sarflandi {money.fmt_som(kk['fakt'])} · "
            + (f"qoldi {money.fmt_som(qolgan)}" if qolgan >= 0 else
               f"rejadan {money.fmt_som(-qolgan)} oshdi"))
        self.kunlar.tuldir(
            [[f"{k['sana'][8:10]}.{k['sana'][5:7]}",
              ", ".join(k["royxatlar"]) or "— (rejasiz rasxod)",
              k["reja"], k["fakt"], plan.kun_holati(k["reja"], k["fakt"])]
             for k in kk["kunlar"]])
        satrlar = []
        for y in self.yozuvlar:
            iso = (y["sana"] or self.oy + "-01")[:10]
            soni = len(y["mahsulotlar"])
            satrlar.append([f"{iso[8:10]}.{iso[5:7]}", y["nom"],
                            f"{soni} ta" if soni else "—", y["summa"]])
        idlar = [y["id"] for y in self.yozuvlar]
        if self.limit:
            satrlar.append(["—", "Limit (mahsulotsiz, butun oyga)", "—",
                            self.limit])
            idlar.append(self.LIMIT)
        self.royxat.tuldir(satrlar, idlar)

    LIMIT = "limit"

    def _tanlangan(self):
        qid = self.royxat.tanlangan_id()
        if qid is None and self.royxat.rowCount() == 1:
            qid = self.royxat.item(0, 0).data(Qt.UserRole)
        return qid

    def _nusxa(self):
        qid = self._tanlangan()
        if qid is None:
            return
        try:
            if qid == self.LIMIT:
                qid = plan.limitni_royxatga(self.db, self.oy, self.turi_id)
            yangi = plan.reja_yozuv_nusxa(self.db, qid)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self._qur()
        # Yangi nusxa tanlangan tursin — darhol ochish yoki tahrirlash uchun.
        for r in range(self.royxat.rowCount()):
            if self.royxat.item(r, 0).data(Qt.UserRole) == yangi:
                self.royxat.selectRow(r)

    def _ochir(self):
        qid = self._tanlangan()
        if qid == self.LIMIT:
            if tasdiq(self, f"{self.nom} limiti ({money.fmt_som(self.limit)}) "
                            f"shu oy rejasidan olib tashlansinmi?"):
                plan.budjet_qoy(self.db, self.turi_id, self.oy, 0)
                self.ozgardi = True
                self._qur()
            return
        if qid is not None and reja_ochir_sora(self, self.db, qid):
            self.ozgardi = True
            self._qur()

    def _och(self, *_):
        qid = self._tanlangan()
        if qid is None:
            return
        if qid == self.LIMIT:
            try:
                qid = plan.limitni_royxatga(self.db, self.oy, self.turi_id)
            except Exception as e:
                xato_koraset(self, str(e))
                return
            self.ozgardi = True
            self._qur()
        o = RejaRoyxatOyna(self.db, qid, self)
        o.exec()
        if o.ozgardi:
            self.ozgardi = True
            self._qur()

    def _qosh(self):
        d = RejaYozuvDialog(self.db, self.oy, parent=self,
                            odam_id=self.odam_id)
        d.turi.tanla(self.turi_id)
        if d.exec():
            self.ozgardi = True
            self._qur()


class RejaRoyxatOyna(QDialog):
    """Bitta reja ro'yxati: mahsulotlari va har biriga «aslida qancha
    to'landi». «Saqlash» — `plan.reja_bajar` haqiqiy rasxod yozadi/
    yangilaydi (fakt shundan hisoblanadi). «Tahrirlash» — ro'yxatning
    o'zini (umumiy/shaxsiy, mahsulot qo'shish/olib tashlash, sana…)
    `RejaYozuvDialog` da o'zgartiradi; oyna o'zini qayta quradi."""

    def __init__(self, db, qator_id: int, parent=None):
        super().__init__(parent)
        self.db, self.qid = db, qator_id
        self.ozgardi = False
        self.setMinimumSize(700, 560)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 20, 22, 18)
        self.v.setSpacing(12)
        self.tana: QWidget | None = None

        saqla = tugma("Saqlash", asosiy=True)
        saqla.clicked.connect(self._saqla)
        tahrir = tugma("Tahrirlash")
        tahrir.setToolTip("Umumiy/shaxsiy, mahsulot qo'shish yoki olib "
                          "tashlash, sana, nom")
        tahrir.clicked.connect(self._tahrir)
        ochir = tugma("Ro'yxatni o'chirish", xavfli=True)
        ochir.clicked.connect(self._ochir)
        yop = tugma("Yopish")
        yop.clicked.connect(self.reject)
        self.tugmalar = qator(tahrir, ochir, None, saqla, yop)
        self.v.addWidget(self.tugmalar)
        self._qur()

    def _qur(self, yozilgan: dict | None = None):
        """Mazmunni (qayta) quradi. `yozilgan` — saqlanmagan «aslida
        to'landi» qiymatlari {nom: summa}: tahrirdan keyin yo'qolmasin."""
        if self.tana is not None:
            self.v.removeWidget(self.tana)
            yoq(self.tana)
        self.y = y = plan.reja_yozuv_toliq(self.db, self.qid)
        iso = (y["sana"] or "")[:10]
        self.setWindowTitle(f"{y['nom']} — {iso[8:10]}.{iso[5:7]}.{iso[:4]}")
        self.tana = QWidget()
        shaffof(self.tana)
        v = QVBoxLayout(self.tana)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        bosh = sarlavha(y["nom"])
        bosh.setWordWrap(True)
        v.addWidget(bosh)
        v.addWidget(izoh(f"{iso[8:10]}.{iso[5:7]}.{iso[:4]} · "
                         f"{y['turi_nom'] or ''} · "
                         + ("umumiy" if y["umumiymi"]
                            else f"{y['odam_nom']} — shaxsiy")))

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        g.setColumnStretch(0, 1)
        for ust, s in enumerate(("Mahsulot", "Miqdor", "Reja",
                                 "Aslida to'landi")):
            g.addWidget(_yozuv(s, theme.KUL, theme.O_MAYDA, 600,
                               ong=ust >= 1), 0, ust)
        self.maydon: dict = {}
        qatorlar = y["mahsulotlar"] or [
            {"id": None, "nom": y["nom"], "miqdor": 1, "summa": y["summa"],
             "tolangan": y["tolangan"]}]
        for i, m in enumerate(qatorlar, 1):
            g.addWidget(_yozuv(m["nom"]), i, 0)
            g.addWidget(_yozuv(f"× {m['miqdor']}", theme.KUL, ong=True), i, 1)
            g.addWidget(_yozuv(money.fmt(m["summa"]), ong=True), i, 2)
            qiymat = (yozilgan or {}).get(m["nom"], m["tolangan"] or 0)
            p = PulEdit(qiymat)
            p.setFixedWidth(140)
            p.setPlaceholderText("olinmagan")
            p.ozgardi.connect(self._jami)
            g.addWidget(p, i, 3)
            self.maydon[m["id"]] = (p, m["summa"], m["nom"])
        g.setRowStretch(len(qatorlar) + 1, 1)
        ichki = QWidget()
        shaffof(ichki)
        ichki.setLayout(g)
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setFrameShape(QScrollArea.NoFrame)
        aylanma.setWidget(ichki)
        v.addWidget(aylanma, 1)

        self.kim = OdamTanla(self.db)
        if y["rasxod"]:
            self.kim.tanla(y["rasxod"]["kim_toladi"])
        elif not y["umumiymi"]:
            self.kim.tanla(y["odam_id"])
        self.sana = SanaEdit(y["rasxod"]["sana"] if y["rasxod"] else iso)
        rejadek = tugma("Rejadagidek")
        rejadek.setToolTip("Bo'sh maydonlarga reja summasini qo'yadi")
        rejadek.clicked.connect(self._rejadek)
        v.addWidget(qator("Kim to'ladi:", self.kim, "Sana:", self.sana,
                          None, rejadek))
        self.holat = izoh("")
        v.addWidget(self.holat)
        self.v.insertWidget(0, self.tana, 1)
        self._jami()

    def _tahrir(self):
        yozilgan = {nom: p.qiymat() for p, _, nom in self.maydon.values()
                    if p.qiymat()}
        oy = (self.y["sana"] or "")[:7] or plan.oy_kaliti()
        if RejaYozuvDialog(self.db, oy, self.qid, self).exec():
            self.ozgardi = True
            self._qur(yozilgan)

    def _ochir(self):
        if reja_ochir_sora(self, self.db, self.qid):
            self.ozgardi = True
            self.accept()

    def _jami(self, *_):
        jami = sum(p.qiymat() for p, _, _ in self.maydon.values())
        reja = self.y["summa"]
        matn = f"Reja {money.fmt_som(reja)} · aslida {money.fmt_som(jami)}"
        if jami:
            farq = jami - reja
            matn += (f" · {money.fmt_som(abs(farq))} "
                     f"{'ortiq' if farq > 0 else 'tejaldi'}" if farq else
                     " · rejadagidek")
        if self.y["rasxod"]:
            matn += "  ·  ✓ rasxod yozilgan"
        self.holat.setText(matn)

    def _rejadek(self):
        for p, reja, _ in self.maydon.values():
            if not p.qiymat():
                p.qoy(reja)

    def _saqla(self):
        try:
            plan.reja_bajar(
                self.db, self.qid,
                {k: p.qiymat() for k, (p, _, _) in self.maydon.items()},
                self.kim.odam_id(), self.sana.iso())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()


# ═══════════════════════════════════════════════════════ ko'rinish

class RejaFaktPanel(QWidget):
    """«Reja va fakt» ko'rinishining butun mazmuni (sarlavhadan pasti)."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.db = db
        self.oy: str | None = None       # None — joriy oy (oy almashsa ergashadi)
        self.odam_id: int | None = None  # None — umumiy, <id> — shaxsiy
        self._r: dict | None = None
        self._qatorlar: list[QWidget] = []

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        v.addWidget(izoh("Rejalashtirilgan va haqiqiy xarajatlarni "
                         "solishtiring: oy uchun reja qo'ying, sarf esa "
                         "rasxodlardan o'zi hisoblanadi."))

        # ── oy tanlash + amal
        oldingi, keyingi = tugma("‹"), tugma("›")
        oldingi.setMaximumWidth(38)
        keyingi.setMaximumWidth(38)
        oldingi.clicked.connect(lambda: self._sur(-1))
        keyingi.clicked.connect(lambda: self._sur(1))
        self.oy_yorliq = bolim("")
        self.oy_yorliq.setMinimumWidth(130)
        self.oy_yorliq.setAlignment(Qt.AlignCenter)
        self.bu_oy = tugma("Bu oy")
        self.bu_oy.clicked.connect(self._bu_oyga)
        self.limit_t = tugma("Umumiy reja va limitlar")
        self.limit_t.clicked.connect(self._reja_och)
        self.qosh_t = tugma("+ Reja qo'shish", asosiy=True)
        self.qosh_t.clicked.connect(self._yozuv_qosh)
        v.addWidget(qator(oldingi, self.oy_yorliq, keyingi, self.bu_oy,
                          None, self.limit_t, self.qosh_t))

        # ── doira: umumiy reja yoki bitta odamning shaxsiy rejasi
        self.doira = QButtonGroup(self)
        self.doira.setExclusive(True)
        self.d_umumiy, self.d_shaxsiy = tugma("Umumiy"), tugma("Shaxsiy")
        for i, b in enumerate((self.d_umumiy, self.d_shaxsiy)):
            b.setCheckable(True)
            self.doira.addButton(b, i)
        self.doira.idClicked.connect(self._doira_ozgardi)
        self.d_odam = OdamTanla(db)
        self.d_odam.currentIndexChanged.connect(self._doira_ozgardi)
        v.addWidget(qator(self.d_umumiy, self.d_shaxsiy, self.d_odam, None))
        self._doira_boya()

        # ── bo'sh holat
        self.bosh = Karta()
        self.bosh.qosh(bolim("Bu oy uchun reja yo'q"))
        self.bosh_izoh = izoh("")
        self.bosh.qosh(self.bosh_izoh)
        bosh_qosh = tugma("+ Reja qo'shish", asosiy=True)
        bosh_qosh.clicked.connect(self._yozuv_qosh)
        self.bosh_limit = tugma("Umumiy summa yoki limit")
        self.bosh_limit.clicked.connect(self._reja_och)
        self.kochir_t = tugma("")
        self.kochir_t.clicked.connect(self._kochir)
        self.bosh.qosh(qator(bosh_qosh, self.bosh_limit, self.kochir_t))
        v.addWidget(self.bosh)

        # ── dashboard
        self.tana = QWidget()
        shaffof(self.tana)
        t = QVBoxLayout(self.tana)
        t.setContentsMargins(0, 0, 0, 0)
        t.setSpacing(16)

        kartalar = QWidget()
        shaffof(kartalar)
        h = QHBoxLayout(kartalar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(theme.B3)
        self.k_reja = RaqamKarta("Oylik reja")
        self.k_fakt = RaqamKarta("Hozirgacha sarflandi")
        self.k_qolgan = RaqamKarta("Qolgan reja")
        for k in (self.k_reja, self.k_fakt, self.k_qolgan):
            h.addWidget(k, 1)
        t.addWidget(kartalar)

        um = Karta()
        self.um_foiz = _yozuv("", olcham=theme.O_ORTA, ogirlik=600)
        self.um_nisbat = _yozuv("", theme.KUL, theme.O_MAYDA, ong=True)
        um.qosh(qator(self.um_foiz, None, self.um_nisbat))
        self.um_chiziq = Chizgi()
        self.um_chiziq.setFixedHeight(12)
        um.qosh(self.um_chiziq)
        t.addWidget(um)

        tk = Karta("Toifalar bo'yicha — bosing: reja kunlari va "
                   "aslida to'langani")
        self.jadval = QWidget()
        shaffof(self.jadval)
        self.g = QGridLayout(self.jadval)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setHorizontalSpacing(14)
        self.g.setVerticalSpacing(6)
        self.g.setColumnStretch(1, 3)
        self.g.setColumnStretch(2, 4)
        for ustun, en in ((3, 44), (4, 100), (5, 100), (6, 110)):
            self.g.setColumnMinimumWidth(ustun, en)
        tk.qosh(self.jadval)
        self.jadval_izoh = izoh("")
        tk.qosh(self.jadval_izoh)
        t.addWidget(tk)

        self.diqqat = QLabel()
        self.diqqat.setWordWrap(True)
        self.diqqat.setTextFormat(Qt.RichText)
        t.addWidget(self.diqqat)

        # ── rasxod kabi kiritilgan reja yozuvlari
        yk = Karta("Reja yozuvlari")
        self.yozuvlar = Jadval(["Sana", "Kategoriya", "Nomi / sabab",
                                "Mahsulotlar", "Summa"], pul_ustunlar={4},
                               bosh_matn="Hali reja yozuvi yo'q — "
                                         "«+ Reja qo'shish»")
        self.yozuvlar.ichkarida()
        self.yozuvlar.kengliklar(90, 150, 0, 110, 120)
        self.yozuvlar.doubleClicked.connect(self._yozuv_tahrir)
        yk.qosh(self.yozuvlar)
        tahrir = tugma("Tahrirlash")
        tahrir.clicked.connect(self._yozuv_tahrir)
        ochir = tugma("O'chirish", xavfli=True)
        ochir.clicked.connect(self._yozuv_ochir)
        yk.qosh(qator(None, tahrir, ochir))
        # Foydalanuvchi so'rovi bilan YASHIRILGAN (2026-10-01): ro'yxatlar
        # endi toifa ichida (`RejaKategoriyaOyna`) — tahrir/o'chirish o'sha yerda.
        self.yozuvlar_karta = yk
        yk.setVisible(False)
        t.addWidget(yk)
        v.addWidget(self.tana)
        # Ortiqcha balandlik pastga — aks holda bo'sh holatda qatorlar
        # sahifa bo'ylab tarqalib ketadi.
        v.addStretch(1)

    # ── boshqaruv ────────────────────────────────────────────────────

    def joriy_oy(self) -> str:
        return self.oy or plan.oy_kaliti()

    def _sur(self, qadam: int):
        yangi = plan.oy_sur(self.joriy_oy(), qadam)
        self.oy = None if yangi == plan.oy_kaliti() else yangi
        self.yangila()

    def _bu_oyga(self):
        self.oy = None
        self.yangila()

    def _reja_och(self):
        if RejaDialog(self.db, self.joriy_oy(), self).exec():
            self.yangila()

    def _doira_ozgardi(self, *_):
        self.odam_id = (self.d_odam.odam_id()
                        if self.doira.checkedId() == 1 else None)
        self._doira_boya()
        self.yangila()

    def _doira_boya(self):
        if self.doira.checkedId() < 0:
            self.d_umumiy.setChecked(True)
        for b in (self.d_umumiy, self.d_shaxsiy):
            b.setObjectName("Asosiy" if b.isChecked() else "")
            b.style().unpolish(b)
            b.style().polish(b)
        self.d_odam.setVisible(self.d_shaxsiy.isChecked())

    def _yozuv_qosh(self):
        if RejaYozuvDialog(self.db, self.joriy_oy(), parent=self,
                           odam_id=self.odam_id).exec():
            self.yangila()

    def _toifa_och(self, q: dict):
        """Toifa ichi: reja kunlari va mahsulotlari, «aslida to'landi»."""
        if q["turi_id"] is None:
            return
        o = RejaKategoriyaOyna(self.db, self.joriy_oy(), q["turi_id"],
                               q["nom"], self.odam_id, self)
        o.exec()
        if o.ozgardi:
            self.yangila()
            oyna = self.window()
            if hasattr(oyna, "yangila") and oyna is not self:
                oyna.yangila()

    def _yozuv_tahrir(self, *_):
        qid = self.yozuvlar.tanlangan_id()
        if qid is None:
            return
        if RejaYozuvDialog(self.db, self.joriy_oy(), qid, self).exec():
            self.yangila()

    def _yozuv_ochir(self):
        qid = self.yozuvlar.tanlangan_id()
        if qid is None:
            return
        r = self.db.q1("SELECT nom, summa FROM reja_qator WHERE id=?", qid)
        if r and tasdiq(self, f"«{r['nom']}» ({money.fmt_som(r['summa'])}) "
                              f"rejadan olib tashlansinmi?"):
            plan.reja_yozuv_ochir(self.db, qid)
            self.yangila()

    def _kochir(self):
        oy = self.joriy_oy()
        plan.reja_kochir(self.db, plan.oy_sur(oy, -1), oy)
        self.yangila()

    def _boya(self):
        """Rejim almashganda — qo'lda qo'yilgan ranglar qayta."""
        if self._r is not None:
            self._chiz(self._r)

    # ── chizish ──────────────────────────────────────────────────────

    def yangila(self):
        oy = self.joriy_oy()
        self.oy_yorliq.setText(oy_nomi(oy))
        self.bu_oy.setEnabled(self.oy is not None)
        self._chiz(plan.reja_va_fakt(self.db, oy, self.odam_id))

    def _chiz(self, r: dict):
        self._r = r
        bor = r["reja_bor"]
        self.bosh.setVisible(not bor)
        self.tana.setVisible(bor)
        # Bo'sh holatda tugma kartaning o'zida — tepadagisi takror bo'lardi.
        self.qosh_t.setVisible(bor)
        # Umumiy summa va limitlar faqat umumiy rejada.
        self.limit_t.setVisible(bor and self.odam_id is None)
        self.bosh_limit.setVisible(self.odam_id is None)
        if not bor:
            self._bosh_holat(r)
            return
        self._kartalar(r)
        self._umumiy(r)
        self._jadval(r)
        self._diqqat(r)
        self._yozuvlar(r)

    def _yozuvlar(self, r: dict):
        satrlar, idlar = [], []
        for y in plan.reja_yozuvlari(self.db, r["oy"], self.odam_id):
            iso = (y["sana"] or r["boshi"])[:10]
            satrlar.append([
                f"{iso[8:10]}.{iso[5:7]}",
                mh.yol_nomi(self.db, y["turi_id"]) or "—",
                y["nom"],
                f"{y['mahsulot_soni']} ta" if y["mahsulot_soni"] else "—",
                y["summa"]])
            idlar.append(y["id"])
        self.yozuvlar.tuldir(satrlar, idlar)
        # Jadval qatorlariga qarab — bo'sh joy sahifani cho'zmasin.
        self.yozuvlar.setFixedHeight(
            40 + 42 * max(2, min(len(satrlar), 10)))

    def _bosh_holat(self, r: dict):
        kim = ("" if self.odam_id is None else
               f"{self.d_odam.currentText()}ning shaxsiy ")
        self.bosh_izoh.setText(
            f"{oy_nomi(r['oy'])} uchun {kim}reja yo'q. Rejani rasxod kabi "
            f"qo'shing — kategoriya va ichidagi mahsulotlar bilan — yoki "
            f"umumiy summa/limit qo'ying. Sarf rasxodlardan o'zi "
            f"hisoblanadi. Bu oy hozirgacha sarflandi: "
            f"{money.fmt_som(r['fakt'])}.")
        otgan = plan.oy_sur(r["oy"], -1)
        self.kochir_t.setText(f"{oy_nomi(otgan)} rejasini ko'chirish")
        self.kochir_t.setVisible(plan.reja_bormi(self.db, otgan))

    def _kartalar(self, r: dict):
        self.k_reja.qoy(r["reja"], "" if r["umumiy_qoyilgan"]
                        else "kategoriyalar rejasi yig'indisi")
        if r["umumiy_qoyilgan"] and r["turi_reja_jami"] > r["reja"]:
            self.k_reja.qoy(r["reja"], "kategoriyalar jami ko'proq: "
                            + money.fmt(r["turi_reja_jami"]))
            self.k_reja.izoh_holati("ogoh")
        else:
            self.k_reja.izoh_holati(None)

        self.k_reja._yorliq.setText(
            "UMUMIY REJA" if self.odam_id is None
            else f"{self.d_odam.currentText().upper()} — SHAXSIY REJA")
        self.k_fakt.qoy(r["fakt"], f"{oy_nomi(r['oy'])} — " + (
            "umumiy rasxodlar" if self.odam_id is None
            else "shaxsiy rasxodlari"))

        foiz = r["foiz"] or 0
        if r["qolgan"] >= 0:
            self.k_qolgan._yorliq.setText("QOLGAN REJA")
            band = (plan.band_pul(self.db) if r["oy"] == plan.oy_kaliti()
                    else {})
            if self.odam_id is None:
                odamlar = [o["id"] for o in self.db.q(
                    "SELECT id FROM odam WHERE faol=1")]
                ulush = (max(u.summa for u in money.bol_teng(
                    r["qolgan"], odamlar)) if band and odamlar
                    and r["qolgan"] else 0)
                band_matn = (f" · har kishidan {money.fmt(ulush)} band"
                             if ulush else "")
            else:
                band_matn = (" · shuncha pul band" if band.get(self.odam_id)
                             else "")
            self.k_qolgan.qoy(r["qolgan"], f"rejaning {foiz}% i ishlatildi"
                              + band_matn)
            self.k_qolgan.izoh_holati("ogoh" if r["holat"] == "yaqin"
                                      else "qaytadi")
        else:
            self.k_qolgan._yorliq.setText("REJADAN OSHDI")
            self.k_qolgan.qoy(-r["qolgan"], f"reja {foiz}% bajarildi — "
                              f"{foiz - 100}% ortiq")
            self.k_qolgan.izoh_holati("berasan")

    def _umumiy(self, r: dict):
        asos, fon, _ = theme.daraja_rangi(DARAJA.get(r["holat"], "yaxshi"))
        foiz = r["foiz"] or 0
        self.um_foiz.setText(
            f"Umumiy xarajat: <span style='color:{asos}'>{foiz}%</span>")
        self.um_nisbat.setText(f"{money.fmt(r['fakt'])} / "
                               f"{money.fmt_som(r['reja'])}")
        _yozuv_boya(self.um_foiz)
        _yozuv_boya(self.um_nisbat, theme.KUL)
        self.um_chiziq.qoy(min(foiz, 100) / 100, False, asos,
                           theme.aralash(asos, theme.KARTA, 0.14))

    def _jadval(self, r: dict):
        for w in self._qatorlar:
            self.g.removeWidget(w)
            yoq(w)
        self._qatorlar = []

        def qosh(w, qat, ust, span=1):
            self.g.addWidget(w, qat, ust, 1, span)
            self._qatorlar.append(w)

        sarlavhalar = ["", "Toifa", "Sarf", "", "Reja", "Fakt", "Qolgan"]
        for ust, s in enumerate(sarlavhalar):
            qosh(_yozuv(s, theme.KUL, theme.O_MAYDA, 600, ong=ust >= 4), 0, ust)

        qat = 1
        for q in r["qatorlar"]:
            qosh(chiziq(), qat, 0, 7)
            qat += 1
            boshi = len(self._qatorlar)
            holat = q["holat"]
            asos, _, _ = theme.daraja_rangi(DARAJA.get(holat, "yaxshi"))

            qosh(_belgi(q), qat, 0)
            qosh(_yozuv(q["nom"], ogirlik=600), qat, 1)   # belgisi 0-ustunda

            ustun = QWidget()
            shaffof(ustun)
            u = QVBoxLayout(ustun)
            u.setContentsMargins(0, 4, 0, 4)
            u.setSpacing(3)
            ch = Chizgi()
            if holat == "rejasiz":
                ch.qoy(0, False, theme.KUL_OCH, theme.CHIZIQ_OCH)
            else:
                ch.qoy(min(q["foiz"], 100) / 100, False, asos,
                       theme.aralash(asos, theme.KARTA, 0.14))
            u.addWidget(ch)
            if holat in HOLAT_MATN:
                u.addWidget(_yozuv(HOLAT_MATN[holat],
                                   theme.KUL if holat == "rejasiz" else asos,
                                   theme.O_MAYDA, 600))
            qosh(ustun, qat, 2)

            qosh(_yozuv("—" if q["foiz"] is None else f"{q['foiz']}%",
                        theme.KUL if holat in ("yaxshi", "rejasiz") else asos,
                        theme.O_KICHIK, 600, ong=True), qat, 3)
            qosh(_yozuv(money.fmt(q["reja"]) if q["reja"] else "—",
                        ong=True), qat, 4)
            qosh(_yozuv(money.fmt(q["fakt"]), ong=True), qat, 5)
            qosh(_yozuv("—" if holat == "rejasiz" else money.fmt(q["qolgan"]),
                        theme.KUL if holat == "rejasiz"
                        else theme.pul_rangi(q["qolgan"]),
                        ogirlik=600, ong=True), qat, 6)
            # Qatorning istalgan joyi bosilsa — toifa ichi ochiladi.
            if q["turi_id"] is not None:
                for w in self._qatorlar[boshi:]:
                    w.setCursor(Qt.PointingHandCursor)
                    w.setToolTip("Reja kunlari va aslida to'langani")
                    w.mousePressEvent = (lambda _e, q=q: self._toifa_och(q))
            qat += 1

        rejali = sum(1 for q in r["qatorlar"] if q["reja"])
        oshgan = sum(1 for q in r["qatorlar"] if q["holat"] == "oshdi")
        rejasiz = sum(q["fakt"] for q in r["qatorlar"] if not q["reja"])
        qismlar = [f"{rejali} ta toifada reja bor"]
        if oshgan:
            qismlar.append(f"{oshgan} tasi oshib ketdi")
        if rejasiz:
            qismlar.append(f"rejasiz toifalarda {money.fmt_som(rejasiz)}")
        self.jadval_izoh.setText(" · ".join(qismlar) if r["qatorlar"]
                                 else "Bu oyda hali rasxod ham, "
                                      "kategoriya rejasi ham yo'q.")

    def _diqqat(self, r: dict):
        q = r["diqqat"]
        if q is not None:
            holat, nom = q["holat"], f"<b>{q['nom']}</b>"
            if holat == "oshdi":
                matn = (f"{nom} rejadan <b>{money.fmt_som(-q['qolgan'])}</b> "
                        f"oshib ketdi — rejaning {q['foiz']}% i sarflandi.")
            else:
                matn = (f"{nom} rejaning {q['foiz']}% ini ishlatdi. "
                        f"Qolgan limit: <b>{money.fmt_som(q['qolgan'])}</b>.")
        elif r["holat"] in ("oshdi", "yaqin"):
            holat = r["holat"]
            matn = (f"Umumiy reja {money.fmt_som(-r['qolgan'])} ga oshib ketdi."
                    if holat == "oshdi" else
                    f"Umumiy rejaning {r['foiz']}% i ishlatildi. Qolgan: "
                    f"<b>{money.fmt_som(r['qolgan'])}</b>.")
        else:
            holat = "yaxshi"
            matn = "Hamma toifalar reja doirasida."
        asos, fon, tuq = theme.daraja_rangi(DARAJA[holat])
        belgi = {"oshdi": "✕", "yaqin": "⚠"}.get(holat, "✓")
        self.diqqat.setText(
            f"<span style='color:{asos};font-weight:700'>{belgi}</span>"
            f"&nbsp;&nbsp;{matn}")
        self.diqqat.setStyleSheet(
            f"QLabel {{ background:{fon}; color:{tuq};"
            f" border:1px solid {theme.aralash(asos, fon, 0.25)};"
            f" border-radius:{theme.R_ORTA}px; padding:12px 16px;"
            f" font-size:{theme.O_ASOS}px; }}")
