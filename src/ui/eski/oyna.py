"""Asosiy oyna: bosh ekranda ikki bo'lim, ichkarida yon menyu.

Ikki qavat:

    tashqi_stek ─┬─ 0  TanlovSahifa      (yon menyusiz bosh ekran)
                 └─ 1  qobiq             (yon menyu + sahifalar steki)

Sahifalar ikkala bo'lim uchun BITTA stekda turadi (`HAMMA`), yon menyu
esa faqat joriy bo'limnikini ko'rsatadi. Shuning uchun bo'lim
almashtirilganda sahifalar qayta qurilmaydi — filtrlar va tanlovlar
joyida qoladi.

TEZKOR TUGMA YO'Q. Amalni bekor qilish faqat yozuvning o'z tafsilot
oynasidan bo'ladi — «Ctrl+Z bosib yubordim, nima o'chdi?» degan holat
umuman bo'lmasligi uchun. `ozgarishlar` jurnali ostida ishlab turaveradi.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout,
                               QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

import config
import money
import sinx
from core import ledger, plan
from core import vazifa as vz
from ui.eski import theme
from ui.eski.sahifa_asosiy import (BugunSahifa, KirimSahifa, QarzSahifa,
                              RasxodSahifa)
from ui.eski.sahifa_analitika import AnalitikaSahifa
from ui.eski.sahifa_hamyon import HamyonSahifa
from ui.eski.sahifa_kategoriya import KategoriyaSahifa
from ui.eski.sahifa_mahsulot import MahsulotSahifa
from ui.eski.sahifa_qosh import (HisobotSahifa, OdamSahifa,  # noqa: F401
                                 RejaSahifa, SozlamaSahifa)  # noqa: F401
from ui.eski.sahifa_tanlov import TanlovSahifa
from ui.eski.widgets import GildirakQalqoni, qayta_chiz, yoq
from ui.eski.sahifa_vazifalar import (ShaxsiyVazifaSahifa,
                                      VazifalarSahifa, VazifaTurlariSahifa)

MOLIYA_SAHIFALAR = [
    ("Bugun",       "◆", BugunSahifa),
    # «Rasxodlar» varag'i foydalanuvchi so'rovi bilan menyudan olindi
    # (2026-09-25): rasxod «Bugun» da yoziladi va tahrirlanadi. Sinf
    # joyida — qaytarish uchun shu qatorni ochish kifoya.
    # ("Rasxodlar",   "▤", RasxodSahifa),
    ("Kirim",       "▲", KirimSahifa),
    ("Qarz",        "⇄", QarzSahifa),
    ("Shaxsiy",     "◉", OdamSahifa),
    # Pulim qayerda: naqd va kartalar (2026-10-01, foydalanuvchi so'ragan).
    ("Hamyon",      "▭", HamyonSahifa),
    # «Reja» va «Hisobot» varaqlari foydalanuvchi so'rovi bilan menyudan
    # olindi (2026-09-30). Sinflar joyida — qaytarish uchun qatorni ochish
    # kifoya. (Oylik reja/fakt Analitika → «Reja va fakt» da qoladi.)
    # ("Reja",        "☰", RejaSahifa),
    # ("Hisobot",     "▦", HisobotSahifa),
    # Nomlar foydalanuvchi so'rovi bilan almashtirilgan (2026-09-30):
    # mahsulot/kategoriya daraxti — «Kategoriyalar», ikonkalar — «Iconlar».
    ("Kategoriyalar", "▣", MahsulotSahifa),
    ("Iconlar",     "◈", KategoriyaSahifa),
    ("Analitika",   "◔", AnalitikaSahifa),
    ("Sozlamalar",  "⚙", SozlamaSahifa),
]

VAZIFA_SAHIFALAR = [
    ("Kalendar",    "▦", VazifalarSahifa),
    ("Vazifalar",   "☰", VazifaTurlariSahifa),
    ("Shaxsiy",     "◉", ShaxsiyVazifaSahifa),
]

# Eski nom: `ui_tekshir.py` va odatdagi murojaatlar shuni kutadi.
SAHIFALAR = MOLIYA_SAHIFALAR

HAMMA = MOLIYA_SAHIFALAR + VAZIFA_SAHIFALAR
BOLIMLAR = {
    "moliya":    ("uy moliyasi hisobi", MOLIYA_SAHIFALAR, 0),
    "vazifalar": ("uy vazifalari", VAZIFA_SAHIFALAR, len(MOLIYA_SAHIFALAR)),
}


class _SinxSignal(QObject):
    """Fon oqimidagi sinxron natijasini bosh (UI) oqimga o'tkazadi."""
    tayyor = Signal(object)


class Oyna(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._sinxronchi = None
        self._sinx_yangila_kerak = False
        self.bolim = "moliya"
        self.setWindowTitle(f"{config.APP_NOM} {config.VERSIYA}"
                            + ("  —  DEMO (soxta ma'lumot)" if config.DEMO else ""))
        self.resize(1280, 860)
        # Eng tor sahifa (Rasxodlar) ~1033px joy so'raydi, yon panel 212px.
        # Minimalni shundan past qo'yish = gorizontal aylantirgich demak.
        self.setMinimumSize(1260, 700)
        if config.ICON_YOL.exists():
            self.setWindowIcon(QIcon(str(config.ICON_YOL)))

        self.tashqi_stek = QStackedWidget()
        self.tanlov = TanlovSahifa(self)
        self.tanlov.bolim_tanlandi.connect(self.bolim_och)
        self.tashqi_stek.addWidget(self.tanlov)
        self.tashqi_stek.addWidget(self._qobiq())
        self.setCentralWidget(self.tashqi_stek)

        self.tashqi_stek.setCurrentIndex(0)
        self.tanlov.yangila()
        self.statusBar().showMessage("Bo'limni tanlang")

    # ── qobiq ────────────────────────────────────────────────────────

    def _qobiq(self) -> QWidget:
        markaz = QWidget()
        tashqi = QHBoxLayout(markaz)
        tashqi.setContentsMargins(0, 0, 0, 0)
        tashqi.setSpacing(0)

        yon = QWidget()
        yon.setObjectName("Yon")
        yon.setFixedWidth(212)
        yv = QVBoxLayout(yon)
        yv.setContentsMargins(0, 0, 0, 12)
        yv.setSpacing(0)

        bosh = QLabel(config.APP_NOM)
        bosh.setObjectName("YonSarlavha")
        yv.addWidget(bosh)
        self.yon_izoh = QLabel("uy moliyasi hisobi")
        self.yon_izoh.setObjectName("YonIzoh")
        yv.addWidget(self.yon_izoh)

        orqaga = QPushButton("  ‹   Bo'limlar")
        orqaga.setObjectName("Nav")
        orqaga.setCheckable(False)
        orqaga.setCursor(Qt.PointingHandCursor)
        orqaga.clicked.connect(self.boshga)
        yv.addWidget(orqaga)

        # Nav tugmalari shu konteynerda — bo'lim almashganda faqat shu
        # qism qayta quriladi.
        self.nav = QWidget()
        self.nav.setObjectName("NavQuti")
        self.nav.setStyleSheet("QWidget#NavQuti { background: transparent; }")
        self.nav_layout = QVBoxLayout(self.nav)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(0)
        yv.addWidget(self.nav)
        yv.addStretch(1)

        self.yon_holat = QLabel()
        self.yon_holat.setWordWrap(True)
        yv.addWidget(self.yon_holat)

        # Server (D1) bilan sinxron holati — sozlanmagan bo'lsa yashirin.
        self.sinx_holat = QLabel()
        self.sinx_holat.setObjectName("SinxHolat")
        yv.addWidget(self.sinx_holat)
        self.sinx_holat.setVisible(False)

        # Taqdimot uchun: haqiqiy ma'lumot o'rniga soxta baza (`demo.py`).
        # Almashtirish dasturni qayta ochadi — baza yo'li `config` da
        # import paytida tanlanadi.
        self.demo_tugma = QPushButton(
            "  ●   Demo: YOQIQ — o'chirish" if config.DEMO else "  ○   Demo rejim")
        self.demo_tugma.setObjectName("Nav")
        self.demo_tugma.setCursor(Qt.PointingHandCursor)
        self.demo_tugma.setToolTip(
            "Soxta ma'lumot bilan ko'rsatish. Haqiqiy baza o'zgarmaydi,\n"
            "server bilan sinxron demo paytida o'chiq.")
        if config.DEMO:
            self.demo_tugma.setStyleSheet(f"color: {theme.QIZIL_TUQ}; font-weight: 700;")
        self.demo_tugma.clicked.connect(self._demo_almashtir)
        yv.addWidget(self.demo_tugma)

        tashqi.addWidget(yon)

        # Tanlagichlar sahifani aylantirayotgan g'ildirakni yutmasin.
        # Butun dasturga o'rnatiladi: bitta sahifada unutilsa o'sha
        # yerda sana yoki odam jimgina o'zgarib ketardi.
        self._gildirak = GildirakQalqoni(self)
        qoll = QApplication.instance()
        if qoll is not None:
            qoll.installEventFilter(self._gildirak)

        self.guruh = QButtonGroup(self)
        self.guruh.setExclusive(True)
        self.guruh.idClicked.connect(self._sahifa)

        # Sahifalar KERAK BO'LGANDA quriladi. To'qqiztasini birdan qurish
        # dastur ochilishini sekinlashtiradi va foydalanuvchi ko'pincha
        # ularning yarmini ochmaydi ham.
        self.stek = QStackedWidget()
        self.sahifalar: list = [None] * len(HAMMA)
        for _ in HAMMA:
            self.stek.addWidget(QWidget())
        tashqi.addWidget(self.stek, 1)
        return markaz

    def _demo_almashtir(self):
        """Demo rejimni yoqadi/o'chiradi va dasturni qayta ochadi."""
        import os
        import sys
        import demo
        from PySide6.QtCore import QProcess
        try:
            if config.DEMO:
                demo.ochir()
            else:
                self.statusBar().showMessage("Demo baza tayyorlanmoqda…")
                QApplication.processEvents()
                demo.yoq()
        except Exception as e:
            self.statusBar().showMessage(f"Demo rejim almashmadi: {e}")
            return
        if getattr(sys, "frozen", False):
            QProcess.startDetached(sys.executable, sys.argv[1:])
        else:
            QProcess.startDetached(sys.executable,
                                   [os.path.abspath(sys.argv[0])] + sys.argv[1:])
        QApplication.quit()

    # ── bo'limlar ────────────────────────────────────────────────────

    def boshga(self):
        """Bosh ekranga qaytish."""
        self.tanlov.yangila()
        self.tashqi_stek.setCurrentIndex(0)
        qayta_chiz(self.tanlov)
        self.statusBar().showMessage("Bo'limni tanlang")

    def bolim_och(self, nom: str):
        if nom not in BOLIMLAR:
            return
        self.bolim = nom
        izoh_matn, sahifalar, siljish = BOLIMLAR[nom]
        self.yon_izoh.setText(izoh_matn)

        for b in list(self.guruh.buttons()):
            self.guruh.removeButton(b)
            yoq(b)
        while self.nav_layout.count():
            self.nav_layout.takeAt(0)

        for i, (sahifa_nom, belgi, _) in enumerate(sahifalar):
            b = QPushButton(f"  {belgi}   {sahifa_nom}")
            b.setObjectName("Nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.guruh.addButton(b, siljish + i)
            self.nav_layout.addWidget(b)

        self.tashqi_stek.setCurrentIndex(1)
        self._sahifa(siljish, bosish=True)
        # Bo'lim almashganda butun qobiq qaytadan chiziladi: yon menyu
        # tugmalari o'chirilib qayta yasaladi va shaffof konteynerlar
        # ostida eski piksellar qolib ketishi mumkin.
        qayta_chiz(self.tashqi_stek.currentWidget())

    # ── sahifalar ────────────────────────────────────────────────────

    def sahifa_ol(self, indeks: int):
        """Sahifani birinchi murojaatda quradi."""
        s = self.sahifalar[indeks]
        if s is None:
            s = HAMMA[indeks][2](self)
            self.sahifalar[indeks] = s
            eski = self.stek.widget(indeks)
            self.stek.insertWidget(indeks, s)
            if eski is not None:
                self.stek.removeWidget(eski)
                eski.deleteLater()
        return s

    def _sahifa(self, indeks: int, bosish: bool = False):
        if bosish:
            tugma = self.guruh.button(indeks)
            if tugma is not None:
                tugma.setChecked(True)
        s = self.sahifa_ol(indeks)
        self.stek.setCurrentIndex(indeks)
        s.yangila()
        # Sahifa almashgach toza chizamiz: `yangila()` ro'yxatlarni
        # o'chirib qayta quradi, shaffof konteyner esa o'z fonini
        # chizmagani uchun eski piksellar qolib ketishi mumkin.
        qayta_chiz(s)
        self._holat()

    # ── umumiy yangilash ─────────────────────────────────────────────

    def yangila(self):
        joriy = self.sahifalar[self.stek.currentIndex()]
        if joriy is not None:
            joriy.yangila()
        # Qolgan sahifalar ochilganda o'zi yangilanadi — hammasini
        # har safar qayta chizish sekinlikning asosiy sababi edi.
        self._holat()

    def _holat(self):
        """Yon paneldagi qisqa holat: moliyada kitob, vazifalarda hafta."""
        self.yon_holat.setStyleSheet(
            f"QLabel{{color:{theme.YON_KUL};font-size:11px;"
            f"padding:12px 18px;background:transparent;}}")

        if self.bolim == "vazifalar":
            kunlar = vz.hafta_kunlari(date.today())
            s = vz.sanoq(self.db, kunlar[0], kunlar[-1])
            rang = theme.YON_KUL if not s["kechikkan"] else theme.QIZIL_TUQ
            self.yon_holat.setText(
                f"Shu hafta<br><b style='font-size:14px;"
                f"color:{theme.MATN_OQ}'>{s['bajarildi']} / {s['jami']}</b>"
                f" bajarildi<br><br>"
                f"<span style='color:{rang}'>{s['kechikkan']} ta kechikkan"
                f"</span>")
            self.statusBar().showMessage(
                f"Vazifalar · shu hafta {s['jami']} ta vazifa")
            return

        a = ledger.audit(self.db)
        # Faqat asosiy odamning (Fayzulloxon) puli; boshqalarda pul
        # bo'lmasa ularning rejaga ulushi ham undan — `plan.qoldagi_pul`.
        qp = plan.qoldagi_pul(self.db)
        jp = plan.jami_pul(self.db)
        holat = ("✔ kitob teng" if a.toza else "✘ kitob teng emas!")
        rang = theme.YON_KUL if a.toza else theme.QIZIL_TUQ
        self.yon_holat.setText(
            f"{qp['nom']}ning qo'lidagi pul<br>"
            f"<b style='font-size:14px;color:{theme.MATN_OQ}'>"
            f"{money.fmt(qp['qoldi'])}</b> so'm"
            + (f"<br>rejaga band {money.fmt(qp['band'])}" if qp["band"] else "")
            + "<br><br>"
            f"Hammaning puli (birga)<br>"
            f"<b style='font-size:14px;color:{theme.MATN_OQ}'>"
            f"{money.fmt(jp['qoldi'])}</b> so'm"
            + (f"<br>rejaga band {money.fmt(jp['band'])}" if jp["band"] else "")
            + "<br><br>"
            f"<span style='color:{rang}'>{holat}</span>")
        self.statusBar().showMessage("Moliya")

    # ── server bilan sinxron ─────────────────────────────────────────

    def sinx_boshla(self):
        """Fon sinxronini ishga tushiradi (faqat `main.py` dan).

        Uch tetik: ochilganda, har COMMIT dan keyin (`db.commitdan_keyin`)
        va har 30 soniyada. Ketma-ket tetiklar `sinx.Sinxronchi` ichida
        birlashadi — bir vaqtda faqat bitta sinxron.
        """
        if self._sinxronchi is not None:
            return
        self._sinx_signal = _SinxSignal(self)
        self._sinx_signal.tayyor.connect(self._sinx_natija)
        self._sinxronchi = sinx.Sinxronchi(
            self.db.yol, natija_fn=self._sinx_signal.tayyor.emit)
        # COMMIT tugma ishlovchisi ICHIDA bo'ladi — hodisalar navbatiga
        # qoldiramiz, ishlovchi tugaguncha hech narsa qilinmaydi.
        self.db.commitdan_keyin.append(
            lambda: QTimer.singleShot(0, self._sinx_tetikla))
        self._sinx_taymer = QTimer(self)
        self._sinx_taymer.setInterval(30_000)
        self._sinx_taymer.timeout.connect(self._sinx_davriy)
        self._sinx_taymer.start()
        self._sinx_tetikla()

    def _sinx_davriy(self):
        # Dialog ochiq bo'lgani uchun qoldirilgan yangilash.
        if self._sinx_yangila_kerak:
            self._sinx_yangila()
        self._sinx_tetikla()

    def _sinx_tetikla(self):
        if self._sinxronchi is None:
            return
        if sinx.sozlamalar(self.db) is None:
            self.sinx_holat.setVisible(False)
            return
        self._sinx_holat_qoy("⏳")
        self._sinxronchi.tetikla()

    def _sinx_holat_qoy(self, matn: str, rang: str | None = None):
        self.sinx_holat.setStyleSheet(
            f"QLabel#SinxHolat{{color:{rang or theme.YON_KUL};"
            f"font-size:11px;padding:0 18px;background:transparent;}}")
        self.sinx_holat.setText(f"Sinxron: {matn}")
        self.sinx_holat.setVisible(True)

    def _sinx_natija(self, natija: dict):
        holat = natija.get("holat")
        if holat == "sozlanmagan":
            self.sinx_holat.setVisible(False)
            return
        if holat == "ok":
            self._sinx_holat_qoy(f"✔ {natija.get('vaqt', '')}")
            self.sinx_holat.setToolTip("")
        elif holat == "oflayn":
            self._sinx_holat_qoy("✖ internet yo'q")
            self.sinx_holat.setToolTip(natija.get("xabar", ""))
        else:
            self._sinx_holat_qoy("✖ xato", theme.QIZIL_TUQ)
            self.sinx_holat.setToolTip(natija.get("xabar", ""))
        if natija.get("ozgardi"):
            # Serverdan yangi yozuv keldi (bot orqali rasxod, vazifa…) —
            # balans va kalendar o'zgargan bo'lishi mumkin.
            self._sinx_yangila_kerak = True
            self._sinx_yangila()

    def _sinx_yangila(self):
        """Ochiq dialog bo'lsa uning ostidagi sahifani qayta qurmaymiz —
        keyingi tetikda (≤30 s) yangilanadi."""
        if QApplication.activeModalWidget() is not None:
            return
        self._sinx_yangila_kerak = False
        if self.tashqi_stek.currentIndex() == 0:
            self.tanlov.yangila()
        else:
            self.yangila()

    def closeEvent(self, hodisa):
        if self._sinxronchi is not None:
            self._sinxronchi.toxtat()
        try:
            self.db.yop()
        except Exception:
            pass
        super().closeEvent(hodisa)
