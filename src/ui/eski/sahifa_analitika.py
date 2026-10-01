"""Analitika sahifasi.

Hozircha bitta narsa: rasxod kategoriyalar bo'yicha doira. Bo'laklar
`ledger.doira_bolaklari()` dan keladi — bu fayl faqat CHIZADI, hech
narsani o'zi hisoblamaydi (foiz ham core'dan, yig'indisi aniq 100%).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QSizePolicy, QTableWidgetItem,
                               QToolTip, QVBoxLayout, QWidget)

import money
from core import kategoriya, ledger, plan
from ui.eski import theme
from ui.eski.dialogs import KategoriyaRasxodlari
from ui.eski.sahifa_asosiy import Sahifa, shaffof
from ui.eski.sahifa_reja_fakt import RejaFaktPanel
from ui.eski.widgets import (Jadval, Karta, OdamTanla, RaqamKarta, SanaEdit,
                             belgi_ikon, izoh, qator, sarlavha, tugma)

TOLIQ_DOIRA = 360 * 16      # Qt burchagi gradusning 1/16 qismida


def foiz_matn(ulush: int) -> str:
    """0,1% birligidagi butun son → «12,3%»."""
    return f"{ulush // 10},{ulush % 10}%"


def bolak_nomi(b: dict) -> str:
    return f"{b['belgi']} {b['nom']}".strip()


def bolak_ranglari(turlar: list[str], palitra: list[str]) -> list[str | None]:
    """Har rangli bo'lakka palitradan rang (`None` — kulrang bo'laklar).

    Kategoriya palitradan (8 ta) ko'p bo'lishi mumkin («Yana 6 ta»), shuning
    uchun ranglar AYLANADI. `TUR_RANG` tartibi qo'shni juftliklar farqlanadigan
    qilib tekshirilgan, ya'ni aylanishda ham qo'shni bo'laklar farq qiladi.
    Yagona xavfli joy — doira halqasi: oxirgi rangli bo'lak birinchisiga
    tegib tursa (orada kulrang bo'lak yo'q) va rangi bir xil chiqsa, u
    ikkala qo'shnisidan farqli boshqa rangga almashtiriladi.
    """
    n, rang = len(palitra), []
    k = 0
    for t in turlar:
        if t == "turi":
            rang.append(palitra[k % n])
            k += 1
        else:
            rang.append(None)
    if k > 2 and turlar[-1] == "turi" and rang[-1] == rang[0]:
        oldingi = rang[-2]
        rang[-1] = next(c for c in palitra[n // 2:] + palitra
                        if c not in (rang[0], oldingi))
    return rang


class DoiraDiagramma(QWidget):
    """Doira + yonida ro'yxat (rang, nom, summa, foiz).

    Ranglar bo'lakning doiradagi O'RNI bo'yicha beriladi, kategoriya
    `id` si bo'yicha emas. Doirada qo'shni bo'laklar — o'lchami bo'yicha
    qo'shnilar, `theme.TUR_RANG` tartibi esa aynan qo'shni juftliklar
    (oxirgi→birinchi bilan birga) ajralib turadigan qilib tekshirilgan.
    `id` bo'yicha bo'yalsa istalgan ikki rang yonma-yon tushib qolardi,
    kategoriya esa 8 tadan ko'p — ranglar baribir takrorlanardi.
    Kategoriya rangi davr almashganda o'zgarishi mumkin, shuning uchun
    ro'yxatda nom har doim rang yonida turadi.

    «Qolganlari» va «Kategoriyasiz» rangsiz (kulrang): ular kategoriya
    emas. Ikkalasi yonma-yon tushishi mumkin, shuning uchun
    «Kategoriyasiz» qo'shimcha shtrix bilan chiziladi.

    QPainter bilan chiziladi — widget yaratilmaydi, ya'ni `yangila()`
    da hech narsa o'chirilib qayta qurilmaydi (qora quti chaqnashi yo'q).
    """

    bosildi = Signal(int)   # bo'lak tartib raqami

    ORALIQ = 8           # chetdagi bo'sh joy
    DOIRA_MAX = 260      # doira diametri
    QATOR = 34           # ro'yxat qatori balandligi
    ROYXAT_MAX = 480     # ro'yxat eni
    YORLIQ_DAN = 100     # 10% dan katta bo'lakda foiz doira ichida ham

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._bolaklar: list[dict] = []
        self._burchaklar: list[int] = []
        self._tanlangan: int | None = None
        self._doira = QRectF()
        self._qatorlar: list[QRectF] = []
        self._jami_qator = QRectF()
        self._rasmlar: dict[str, QIcon] = {}

    def sizeHint(self) -> QSize:
        return QSize(720, self._balandlik())

    def _balandlik(self) -> int:
        """Ro'yxat uzaysa («Yana 6 ta») doira kartasi ham o'ssin."""
        return max(300, (len(self._bolaklar) + 1) * self.QATOR + 40)

    # ── ma'lumot ─────────────────────────────────────────────────────

    def qoy(self, bolaklar: list[dict]) -> None:
        self._bolaklar = list(bolaklar)
        for b in self._bolaklar:
            yol = kategoriya.rasm_yoli(b.get("rasm"))
            if yol and b["rasm"] not in self._rasmlar:
                self._rasmlar[b["rasm"]] = belgi_ikon(yol)
        self._burchaklar = []
        if self._bolaklar:
            self._burchaklar = [u.summa for u in money.bol_tortli(
                TOLIQ_DOIRA,
                {i: b["summa"] for i, b in enumerate(self._bolaklar)})]
        self._tanlangan = None
        QToolTip.hideText()
        self.setMinimumHeight(self._balandlik())
        self.updateGeometry()
        self.update()

    def _boya(self):
        """Rejim almashganda — ranglar chizish paytida o'qiladi."""
        self.update()

    def _ranglar(self) -> list[str]:
        rangli = bolak_ranglari([b["tur"] for b in self._bolaklar],
                                list(theme.TUR_RANG))
        natija = []
        for b, r in zip(self._bolaklar, rangli):
            if r is not None:
                natija.append(r)
            elif b["tur"] == "qolgan":
                natija.append(theme.KUL_OCH)
            else:
                natija.append(theme.aralash(theme.KUL_OCH, theme.KARTA, 0.45))
        return natija

    def _korinadigan(self, i: int, rang: str) -> str:
        """Bo'lak aslida qaysi rangda chiziladi: boshqasi tanlangan
        bo'lsa xiralashadi. Ustidagi foiz matni ham SHU rangdan
        tanlanadi, aks holda xira bo'lakda oq yozuv o'qilmay qoladi."""
        if self._tanlangan is not None and self._tanlangan != i:
            return theme.aralash(rang, theme.KARTA, 0.35)
        return rang

    def _boyoq(self, i: int, rang: str) -> QBrush:
        return QBrush(QColor(self._korinadigan(i, rang)))

    # ── chizish ──────────────────────────────────────────────────────

    def _joylash(self) -> None:
        h, w = self.height(), self.width()
        d = min(h - 2 * self.ORALIQ, self.DOIRA_MAX, int(w * 0.4))
        d = max(d, 0)
        self._doira = QRectF(self.ORALIQ, (h - d) / 2, d, d)

        x0 = self.ORALIQ + d + 40
        en = max(0, min(w - x0 - self.ORALIQ, self.ROYXAT_MAX))
        n = len(self._bolaklar)
        balandlik = (n + 1) * self.QATOR + 8
        y0 = (h - balandlik) / 2
        self._qatorlar = [QRectF(x0, y0 + i * self.QATOR, en, self.QATOR)
                          for i in range(n)]
        self._jami_qator = QRectF(x0, y0 + n * self.QATOR + 8, en, self.QATOR)

    def paintEvent(self, _hodisa):
        self._joylash()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        # Ikonkalar 256 px — 22 px ga silliq kichraysin, aks holda qirrali.
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._bolaklar:
            self._bosh_holat(p)
        else:
            ranglar = self._ranglar()
            self._doirani_chiz(p, ranglar)
            self._royxatni_chiz(p, ranglar)
        p.end()

    def _bosh_holat(self, p: QPainter) -> None:
        p.setPen(QPen(QColor(theme.CHIZIQ_TUQ), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(self._doira.adjusted(2, 2, -2, -2))
        p.setPen(QColor(theme.KUL))
        p.setFont(theme.matn_shrift(theme.O_ASOS))
        x0 = self._doira.right() + 40
        p.drawText(QRectF(x0, 0, max(0.0, self.width() - x0), self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft,
                   "Bu oraliqda rasxod yo'q")

    def _doirani_chiz(self, p: QPainter, ranglar: list[str]) -> None:
        # Bo'laklar orasidagi 2px oraliq — karta rangidagi chiziq.
        # Chegara chizig'i EMAS: u faqat bo'laklarni bir-biridan ajratadi.
        ajratgich = QPen(QColor(theme.KARTA), 2)
        ajratgich.setJoinStyle(Qt.RoundJoin)
        r = self._doira
        if len(self._bolaklar) == 1:
            p.setPen(Qt.NoPen)
            p.setBrush(self._boyoq(0, ranglar[0]))
            p.drawEllipse(r)
            self._shtrix(p, 0, lambda: p.drawEllipse(r))
        else:
            boshi = 90 * 16                       # soat 12 dan
            for i, burchak in enumerate(self._burchaklar):
                if burchak <= 0:
                    continue
                p.setPen(ajratgich)
                p.setBrush(self._boyoq(i, ranglar[i]))
                p.drawPie(r, boshi, -burchak)     # soat yo'nalishida
                self._shtrix(p, i, lambda b=boshi, a=burchak:
                             p.drawPie(r, b, -a), ajratgich)
                boshi -= burchak

        # Tanlangan foizlar doira ichida ham — faqat katta bo'laklarda,
        # aks holda raqam bo'lakdan chiqib ketadi.
        if r.width() < 160:
            return
        p.setFont(theme.raqam_shrift(theme.O_KICHIK, 700))
        markaz, radius = r.center(), r.width() / 2 * 0.64
        jam = 0
        for i, b in enumerate(self._bolaklar):
            burchak = self._burchaklar[i]
            orta = (jam + burchak / 2) / 16       # gradus, soat 12 dan
            jam += burchak
            if b["ulush"] < self.YORLIQ_DAN:
                continue
            rad = math.radians(orta)
            nuqta = QPointF(markaz.x() + radius * math.sin(rad),
                            markaz.y() - radius * math.cos(rad))
            p.setPen(QColor(theme.ustiga(self._korinadigan(i, ranglar[i]))))
            p.drawText(QRectF(nuqta.x() - 32, nuqta.y() - 10, 64, 20),
                       Qt.AlignCenter, foiz_matn(b["ulush"]))

    def _shtrix(self, p: QPainter, i: int, chiz, pen=None) -> None:
        """«Kategoriyasiz» — «Qolganlari» dan rang bilan emas, naqsh
        bilan ham ajralsin (ikkalasi kulrang va yonma-yon tushadi)."""
        if self._bolaklar[i]["tur"] != "kategoriyasiz":
            return
        p.setPen(pen or Qt.NoPen)
        p.setBrush(QBrush(QColor(theme.KUL_OCH), Qt.BDiagPattern))
        chiz()

    def _royxatni_chiz(self, p: QPainter, ranglar: list[str]) -> None:
        nom_shrift = theme.matn_shrift(theme.O_ASOS)
        raqam = theme.raqam_shrift(theme.O_ASOS, 600)
        foiz_en, summa_en = 64, 130
        for i, (b, q) in enumerate(zip(self._bolaklar, self._qatorlar)):
            if self._tanlangan == i:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(theme.KARTA_ICH))
                p.drawRoundedRect(q.adjusted(-8, 1, 8, -1), 8, 8)

            belgi = QRectF(q.x(), q.center().y() - 6, 12, 12)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ranglar[i]))
            p.drawRoundedRect(belgi, 3, 3)
            if b["tur"] == "kategoriyasiz":
                p.setBrush(QBrush(QColor(theme.KUL_OCH), Qt.BDiagPattern))
                p.drawRoundedRect(belgi, 3, 3)

            chap = 24
            rasm = self._rasmlar.get(b.get("rasm") or "")
            if rasm is not None:
                # Ikonkali kategoriya — rang belgisidan keyin ikonkasi ham.
                # Vektordan, ekran pikselida — cho'zilgan PNG xira edi.
                rasm.paint(p, QRectF(q.x() + 20, q.center().y() - 11,
                                     22, 22).toRect())
                chap = 48
            nom_q = QRectF(q.x() + chap, q.y(),
                           q.width() - chap - summa_en - foiz_en - 12, q.height())
            p.setFont(nom_shrift)
            p.setPen(QColor(theme.MATN))
            nom = p.fontMetrics().elidedText(
                bolak_nomi(b), Qt.ElideRight, int(max(0.0, nom_q.width())))
            p.drawText(nom_q, Qt.AlignVCenter | Qt.AlignLeft, nom)

            p.setFont(raqam)
            p.drawText(QRectF(q.right() - foiz_en - summa_en, q.y(),
                              summa_en, q.height()),
                       Qt.AlignVCenter | Qt.AlignRight, money.fmt(b["summa"]))
            p.setPen(QColor(theme.KUL))
            p.drawText(QRectF(q.right() - foiz_en, q.y(), foiz_en, q.height()),
                       Qt.AlignVCenter | Qt.AlignRight, foiz_matn(b["ulush"]))

        j = self._jami_qator
        p.setPen(QPen(QColor(theme.CHIZIQ), 1))
        p.drawLine(QPointF(j.x(), j.y() - 4), QPointF(j.right(), j.y() - 4))
        p.setFont(theme.matn_shrift(theme.O_ASOS, 600))
        p.setPen(QColor(theme.KUL))
        p.drawText(QRectF(j.x() + 24, j.y(), 120, j.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, "Jami")
        p.setFont(theme.raqam_shrift(theme.O_ASOS, 700))
        p.setPen(QColor(theme.MATN))
        p.drawText(QRectF(j.right() - foiz_en - summa_en - 60, j.y(),
                          summa_en + 60, j.height()),
                   Qt.AlignVCenter | Qt.AlignRight,
                   money.fmt(sum(b["summa"] for b in self._bolaklar)))
        p.setPen(QColor(theme.KUL))
        p.drawText(QRectF(j.right() - foiz_en, j.y(), foiz_en, j.height()),
                   Qt.AlignVCenter | Qt.AlignRight, "so'm")

    # ── sichqoncha ───────────────────────────────────────────────────

    def _topish(self, pos: QPointF) -> int | None:
        for i, q in enumerate(self._qatorlar):
            if q.adjusted(-8, 0, 8, 0).contains(pos):
                return i
        if not self._bolaklar or self._doira.isEmpty():
            return None
        markaz = self._doira.center()
        dx, dy = pos.x() - markaz.x(), pos.y() - markaz.y()
        radius = self._doira.width() / 2
        if dx * dx + dy * dy > radius * radius:
            return None
        # soat 12 dan soat yo'nalishida, 1/16 gradusda
        burchak = (math.degrees(math.atan2(dx, -dy)) + 360) % 360 * 16
        jam = 0
        for i, a in enumerate(self._burchaklar):
            jam += a
            if burchak < jam:
                return i
        return len(self._bolaklar) - 1

    def _izoh(self, i: int) -> str:
        b = self._bolaklar[i]
        qatorlar = [bolak_nomi(b),
                    f"{money.fmt_som(b['summa'])} · {foiz_matn(b['ulush'])}"
                    f" · {b['soni']} ta rasxod"]
        if b["ichida"]:
            qatorlar.append(", ".join(b["ichida"]))
        if b["tur"] == "kategoriyasiz":
            qatorlar.append("Kategoriya tanlanmagan rasxodlar")
        return "\n".join(qatorlar)

    def mouseMoveEvent(self, hodisa):
        i = self._topish(hodisa.position())
        if i != self._tanlangan:
            self._tanlangan = i
            self.update()
            if i is None:
                QToolTip.hideText()
            else:
                QToolTip.showText(hodisa.globalPosition().toPoint(),
                                  self._izoh(i), self)
        super().mouseMoveEvent(hodisa)

    def mousePressEvent(self, hodisa):
        if hodisa.button() == Qt.LeftButton:
            i = self._topish(hodisa.position())
            if i is not None:
                self.bosildi.emit(i)
                return
        super().mousePressEvent(hodisa)

    def leaveEvent(self, hodisa):
        if self._tanlangan is not None:
            self._tanlangan = None
            QToolTip.hideText()
            self.update()
        super().leaveEvent(hodisa)


# ═══════════════════════════════════════════════════════════ ANALITIKA

class AnalitikaSahifa(Sahifa):
    """Birlamchi oraliq — joriy oyning 1-kunidan BUGUNGACHA.

    Foydalanuvchi sanani o'zi o'zgartirmaguncha (`_qolda`) oraliq har
    `yangila()` da qayta hisoblanadi: dastur oy almashganda ham ochiq
    tursa, 1-noyabrda eski sentabr emas, faqat 1-noyabr ko'rinadi.
    """

    KORINISH = ["Kategoriyalar", "Reja va fakt"]
    # Odam tanlanganda: uning qaysi rasxodi (`ledger.ODAM_QISMLARI`).
    QISMLAR = [("hammasi", "Shaxsiy + umumiy"), ("shaxsiy", "Shaxsiy"),
               ("umumiy", "Umumiy ulushi")]

    def __init__(self, oyna):
        super().__init__(oyna)
        dan, gacha = plan.oy_bugungacha()
        self._qolda = False
        self.dan = SanaEdit(dan)
        self.gacha = SanaEdit(gacha)
        self.dan.dateChanged.connect(self._qolda_ozgardi)
        self.gacha.dateChanged.connect(self._qolda_ozgardi)
        oy = tugma("Shu oy")
        hafta = tugma("Shu hafta")
        oy.clicked.connect(self._shu_oy)
        hafta.clicked.connect(lambda: self._oraliq(plan.hafta_boshi(),
                                                   plan.hafta_oxiri()))

        # Ichki ko'rinishlar — yon menyuda alohida varaq EMAS.
        self.korinish = QButtonGroup(self)
        self.korinish.setExclusive(True)
        tugmalar = []
        for i, nom in enumerate(self.KORINISH):
            b = tugma(nom)
            b.setCheckable(True)
            self.korinish.addButton(b, i)
            tugmalar.append(b)
        self.korinish.idClicked.connect(self._korinish_ozgardi)
        self.bosh_sarlavha = sarlavha("Analitika")
        self.tana.addWidget(qator(self.bosh_sarlavha, None, *tugmalar))

        self.kategoriyalar = QWidget()
        shaffof(self.kategoriyalar)
        kv = QVBoxLayout(self.kategoriyalar)
        kv.setContentsMargins(0, 0, 0, 0)
        kv.setSpacing(16)
        kv.addWidget(qator(hafta, oy, None,
                           "Dan:", self.dan, "Gacha:", self.gacha))

        # Odam filtri. «Hammasi» — uyning butun rasxodi; odam tanlansa —
        # uning shaxsiy rasxodi va umumiy rasxoddagi ULUSHI (butun
        # summasi emas — `ledger.turi_boyicha` ga qarang).
        self.odam = OdamTanla(self.db, hammasi=True)
        self.odam.currentIndexChanged.connect(self._odam_ozgardi)
        self.qism = QButtonGroup(self)
        self.qism.setExclusive(True)
        qism_tugmalar = []
        for i, (_, nom) in enumerate(self.QISMLAR):
            b = tugma(nom)
            b.setCheckable(True)
            self.qism.addButton(b, i)
            qism_tugmalar.append(b)
        self.qism.idClicked.connect(self._qism_ozgardi)
        self.qism_qator = qator(*qism_tugmalar)
        kv.addWidget(qator("Kim:", self.odam, None, self.qism_qator))

        self.k_shaxsiy = RaqamKarta("Shaxsiy rasxodi", 0,
                                    "o'zi uchun + uning uchun olingan")
        self.k_umumiy = RaqamKarta("Umumiy rasxoddagi ulushi", 0,
                                   "uy rasxodidan o'z hissasi")
        self.k_jami = RaqamKarta("Jami", 0, "shaxsiy + umumiy ulush")
        self.xulosa = qator(self.k_shaxsiy, self.k_umumiy, self.k_jami,
                            oraliq=16)
        kv.addWidget(self.xulosa)

        k = Karta("Rasxod — kategoriyalar bo'yicha")
        self.doira_karta = k
        self.doira = DoiraDiagramma()
        self.doira.bosildi.connect(self._bolak_bosildi)
        k.qosh(self.doira)
        # Birlamchi 6 ta kategoriya; «Yana 6 ta» — keyingi 6 tasi, kategoriya
        # qolmaguncha. «Qolganlari» ning o'zini bosish ham shu.
        self._korsat = ledger.DOIRA_QADAM
        self.t_yana = tugma(f"Yana {ledger.DOIRA_QADAM} ta")
        self.t_yana.clicked.connect(self._yana)
        self.t_yigish = tugma("Yig'ish")
        self.t_yigish.clicked.connect(self._yigish)
        self.yana_izoh = izoh("")
        k.qosh(qator(self.t_yana, self.t_yigish, self.yana_izoh, None))
        k.qosh(izoh("Kategoriya ustiga bosing — ichidagi har bir rasxod "
                    "chiqadi va shu yerdan tahrirlanadi. «Qolganlari» ni "
                    "bossangiz — keyingi kategoriyalar ochiladi."))
        kv.addWidget(k)

        # Doira faqat eng kattalarini ko'rsatadi — bu yerda HAMMASI,
        # yangi, hali ishlatilmagan kategoriyalar ham (0 bilan).
        h = Karta("Hamma kategoriyalar")
        self.jadval = Jadval(["Kategoriya", "Soni", "Summa", "Ulushi"],
                             pul_ustunlar={2})
        self.jadval.kengliklar(0, 90, 150, 100)
        self.jadval.setIconSize(QSize(24, 24))
        # Ichki aylantirgich yo'q — jadval hamma qatorni sig'diradi,
        # sahifaning o'zi aylanadi (kategoriya ko'paysa ham hammasi ko'rinsin).
        self.jadval.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.jadval.cellClicked.connect(self._qator_bosildi)
        self._jadval_turlar: list[dict] = []
        h.qosh(self.jadval)
        self.jadval_izoh = izoh("")
        h.qosh(self.jadval_izoh)
        kv.addWidget(h)
        # Foydalanuvchi o'chirib qo'yishni so'ragan (2026-09-30): doira endi
        # «Yana 6 ta» bilan hamma kategoriyani ko'rsata oladi. Jadval
        # hisoblanib turadi (testlar va keyin qaytarish uchun), faqat
        # ko'rinmaydi.
        self.hamma_karta = h
        h.setVisible(False)
        self.tana.addWidget(self.kategoriyalar)

        self.reja_fakt = RejaFaktPanel(self.db)
        self.tana.addWidget(self.reja_fakt)
        self.tana.addStretch(1)
        self.qism.button(0).setChecked(True)
        self._qism_boya()
        self._korinish_ozgardi(0, yangilama=True)

    # ── odam filtri ──────────────────────────────────────────────────

    def filtr(self) -> tuple[int | None, str]:
        """(odam_id, qism) — odam tanlanmagan bo'lsa (None, 'hammasi')."""
        odam_id = self.odam.odam_id()
        if odam_id is None:
            return None, "hammasi"
        return odam_id, self.QISMLAR[max(0, self.qism.checkedId())][0]

    def _qism_boya(self):
        for i in range(len(self.QISMLAR)):
            b = self.qism.button(i)
            b.setObjectName("Asosiy" if b.isChecked() else "")
            b.style().unpolish(b)
            b.style().polish(b)

    def _odam_ozgardi(self, *_):
        self.yangila()

    def _qism_ozgardi(self, _indeks: int):
        self._qism_boya()
        self.yangila()

    # ── bosish → rasxodlar ro'yxati ──────────────────────────────────

    def _bolak_bosildi(self, i: int):
        if 0 <= i < len(self.doira._bolaklar):
            b = self.doira._bolaklar[i]
            if b["tur"] == "qolgan":
                self._yana()            # ichidagi kategoriyalar ochiladi
                return
            self._ichini_och(bolak_nomi(b), b.get("idlar") or [])

    # ── «Yana 6 ta» / «Yig'ish» ──────────────────────────────────────

    def _yana(self):
        self._korsat += ledger.DOIRA_QADAM
        self.yangila()

    def _yigish(self):
        self._korsat = ledger.DOIRA_QADAM
        self.yangila()

    def _yana_tugmalari(self):
        qolgan = next((b for b in self.doira._bolaklar
                       if b["tur"] == "qolgan"), None)
        qoldi = len(qolgan["idlar"]) if qolgan else 0
        self.t_yana.setVisible(qoldi > 0)
        self.t_yana.setText(f"Yana {min(ledger.DOIRA_QADAM, qoldi)} ta")
        self.t_yigish.setVisible(self._korsat > ledger.DOIRA_QADAM)
        self.yana_izoh.setText(f"yana {qoldi} ta kategoriya «Qolganlari» da"
                               if qoldi else "")

    def _qator_bosildi(self, qator_: int, _ustun: int):
        if 0 <= qator_ < len(self._jadval_turlar):
            t = self._jadval_turlar[qator_]
            self._ichini_och(f"{t['belgi']} {t['nom']}".strip(),
                             [t["turi_id"]])

    def _ichini_och(self, nom: str, turi_idlar: list):
        if not turi_idlar:
            return
        odam_id, qism = self.filtr()
        if odam_id is not None:
            nom = f"{nom} — {self.odam.currentText()}"
        d = KategoriyaRasxodlari(self.db, nom, turi_idlar, self.dan.iso(),
                                 self.gacha.iso(), odam_id, qism, parent=self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()

    def _korinish_ozgardi(self, indeks: int, yangilama: bool = False):
        """Faol tugma «Asosiy» — Vazifalar'dagi ko'rinish tugmalari
        bilan bir xil naqsh (objectName + qayta sayqallash)."""
        self.korinish.button(indeks).setChecked(True)
        for i in range(len(self.KORINISH)):
            b = self.korinish.button(i)
            b.setObjectName("Asosiy" if i == indeks else "")
            b.style().unpolish(b)
            b.style().polish(b)
        reja = indeks == 1
        self.bosh_sarlavha.setText("Reja va fakt" if reja else "Analitika")
        self.kategoriyalar.setVisible(not reja)
        self.reja_fakt.setVisible(reja)
        if not yangilama:
            self.yangila()

    def _oraliq(self, a, b):
        with QSignalBlocker(self.dan), QSignalBlocker(self.gacha):
            self.dan.qoy(a)
            self.gacha.qoy(b)
        self._qolda = True
        self.yangila()

    def _shu_oy(self):
        self._qolda = False
        self.yangila()

    def _qolda_ozgardi(self):
        self._qolda = True
        self.yangila()

    def yangila(self):
        # Faqat ko'rinib turgani hisoblanadi.
        if self.korinish.checkedId() == 1:
            self.reja_fakt.yangila()
            return
        if not self._qolda:
            dan, gacha = plan.oy_bugungacha()
            with QSignalBlocker(self.dan), QSignalBlocker(self.gacha):
                self.dan.qoy(dan)
                self.gacha.qoy(gacha)
        dan, gacha = self.dan.iso(), self.gacha.iso()

        # Odamlar ro'yxati o'zgargan bo'lishi mumkin. Signal to'sig'i
        # SHART: `OdamTanla.yangila()` `currentIndexChanged` ni uyg'otadi
        # va u yana shu `yangila()` ni chaqirib cheksiz aylanardi.
        with QSignalBlocker(self.odam):
            self.odam.yangila(hammasi=True)
        odam_id, qism = self.filtr()
        self.qism_qator.setVisible(odam_id is not None)
        self.xulosa.setVisible(odam_id is not None)
        if odam_id is not None:
            x = ledger.odam_rasxod_xulosa(self.db, odam_id, dan, gacha)
            self.k_shaxsiy.qoy(x["shaxsiy"])
            self.k_umumiy.qoy(x["umumiy"])
            self.k_jami.qoy(x["jami"])
            sarlavha_ = (f"{self.odam.currentText()} — "
                         f"{dict(self.QISMLAR)[qism].lower()}")
        else:
            sarlavha_ = "Rasxod — kategoriyalar bo'yicha"
        if self.doira_karta._sarlavha is not None:
            self.doira_karta._sarlavha.setText(sarlavha_.upper())

        self.doira.qoy(ledger.doira_bolaklari(self.db, dan, gacha,
                                              korsat=self._korsat,
                                              odam_id=odam_id, qism=qism))
        self._yana_tugmalari()

        qatorlar = []
        hammasi = ledger.kategoriya_jadvali(self.db, dan, gacha, odam_id, qism)
        self._jadval_turlar = hammasi
        for t in hammasi:
            it = QTableWidgetItem(
                t["nom"] if t["rasm"] else f"{t['belgi']} {t['nom']}".strip())
            yol = kategoriya.rasm_yoli(t["rasm"])
            if yol:
                it.setIcon(belgi_ikon(yol))
            qatorlar.append([it, t["soni"] or "—", t["summa"],
                             foiz_matn(t["ulush"]) if t["summa"] else "—"])
        self.jadval.tuldir(qatorlar)
        self.jadval.setFixedHeight(
            self.jadval.horizontalHeader().height()
            + sum(self.jadval.rowHeight(i) for i in range(len(qatorlar)))
            + 2 * self.jadval.frameWidth() + 4)
        # «Kategoriyasiz» qatori kategoriya emas — sanoqqa kirmaydi.
        haqiqiy = [t for t in hammasi if t["turi_id"] is not None]
        ishlatilmagan = sum(1 for t in haqiqiy if not t["summa"])
        self.jadval_izoh.setText(
            f"{len(haqiqiy)} ta kategoriya · {ishlatilmagan} tasida bu "
            f"oraliqda rasxod yo'q" if ishlatilmagan
            else f"{len(haqiqiy)} ta kategoriya")
