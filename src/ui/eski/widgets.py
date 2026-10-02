"""Qayta ishlatiladigan UI bo'laklari.

Har bo'lak o'z fonini o'zi e'lon qiladi (global `theme.STIL` dan
tashqari widget darajasida ham): ota-widgetdagi
`setStyleSheet("background:transparent")` butun avlodga tarqaladi va
global fonni bosib ketadi.

Rejim almashtirish: widget darajasidagi stil bir marta qo'yilgani
uchun `_stil()` orqali qo'yiladi (u qaysi `theme.*_STIL` ekanini
eslaydi), rangni o'zi hisoblaydigan bo'laklar esa `_boya()` beradi.
Ikkalasini `qayta_boya(oyna)` yuradi::

    theme.rejim_qoy("tungi")
    app.setStyleSheet(theme.STIL)
    widgets.qayta_boya(oyna)
    oyna.yangila()
"""
from __future__ import annotations

from PySide6.QtCore import (QDate, QEvent, QObject, QRectF, QSignalBlocker,
                            QSize, Qt, QTimer,
                            Signal)
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPalette, QPen,
                           QPixmap, QTextCharFormat)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea,
                               QAbstractSpinBox, QApplication,
                               QCalendarWidget, QComboBox, QDateEdit,
                               QFrame, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QSizePolicy,
                               QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

import money
from ui.eski import theme


# ────────────────────────────────────────────────────── ichki yordamchi

_KIRITISH = (QLineEdit, QComboBox, QDateEdit)

_STIL_XOS = "_farvon_stil"      # widgetda saqlanadigan stil nomi
_HIMOYA_XOS = "_farvon_himoya"  # _himoya() bir marta yurgani belgisi

# jadval katagida pul qiymatini eslab qolamiz — rejim almashganda
# yashil/qizil rangni qayta hisoblash uchun (aks holda eski rang qoladi)
_PUL_ROLI = Qt.ItemDataRole(Qt.UserRole + 17)
_RANGLI_ROLI = Qt.ItemDataRole(Qt.UserRole + 18)


def _stil(w: QWidget, nom: str) -> QWidget:
    """`theme.<nom>` stilini qo'yadi va qaysi ekanini widgetda eslaydi."""
    w.setProperty(_STIL_XOS, nom)
    w.setStyleSheet(getattr(theme, nom))
    return w


def qayta_boya(ildiz: QWidget) -> None:
    """Rejim almashgandan keyin butun daraxtni qayta bo'yaydi:
    `_stil()` bilan qo'yilgan stillarni qayta qo'yadi va `_boya()`
    beradigan widgetlarni chaqiradi."""
    for w in (ildiz, *ildiz.findChildren(QWidget)):
        nom = w.property(_STIL_XOS)
        if nom:
            w.setStyleSheet(getattr(theme, nom, "") or "")
        boya = getattr(w, "_boya", None)
        if callable(boya):
            try:
                boya()
            except Exception:      # bitta widget butun rejimni buzmasin
                pass
    st = ildiz.style()
    st.unpolish(ildiz)
    st.polish(ildiz)
    ildiz.update()


def _himoya(w) -> None:
    """Widget va uning avlodlaridagi 'yalang'och' tugma/kiritishlarni
    ota-widgetdagi `background:transparent` dan himoya qiladi.

    `findChildren` — arzon emas, shuning uchun bitta widgetga bir marta
    yuriladi (`_HIMOYA_XOS` belgisi).
    """
    if w is None or not isinstance(w, QWidget):
        return
    if w.property(_HIMOYA_XOS):
        return
    w.setProperty(_HIMOYA_XOS, True)
    uchun = []
    if isinstance(w, (QPushButton, *_KIRITISH)):
        uchun.append(w)
    uchun += w.findChildren(QPushButton)
    for sinf in _KIRITISH:
        uchun += w.findChildren(sinf)
    for x in uchun:
        if not x.styleSheet():
            _stil(x, "ICHKI_STIL")


def _shaffof(w: QWidget, nom: str = "Shaffof") -> QWidget:
    """Fonsiz konteyner — selektor bilan, shuning uchun bolalarga
    tarqalmaydi."""
    w.setObjectName(nom)
    w.setStyleSheet(f"QWidget#{nom} {{ background: transparent; }}")
    return w


def _rangla(yorliq: QLabel, rang: str) -> None:
    """Yorliq matnining rangi. Qo'yilgan qiymat eslab qolinadi —
    `setStyleSheet` har chaqirilganda Qt butun shoxni qayta "polish"
    qiladi, bu esa har `yangila()` da behuda ish."""
    if getattr(yorliq, "_rang_kesh", None) == rang:
        return
    yorliq._rang_kesh = rang
    yorliq.setStyleSheet(
        f"QLabel {{ color:{rang}; background:transparent; border:none; }}")


# ───────────────────────────────────────────────── widgetni o'chirish

def qayta_chiz(w) -> None:
    """Widget va uning IChKI hamma bolalarini qayta chizdiradi.

    Nega kerak: `shaffof()` qo'yilgan konteyner o'z fonini
    CHIZMAYDI — ostidagi narsa ko'rinib tursin uchun shunday. Lekin
    ustidagi widget yashirilsa yoki ko'chirilsa, Qt faqat o'sha
    joyni "iflos" deb belgilaydi; shaffof ota esa uni to'ldirmaydi
    va eski piksellar EKRANDA QOLIB KETADI. Ko'zga bu «g'alati
    quti paydo bo'lib yo'qoldi» bo'lib ko'rinadi.

    `update()` — `repaint()` emas: birinchisi navbatga qo'yadi va
    bitta kadrda hammasini birga chizadi, ikkinchisi esa har
    chaqiruvda darhol chizib, sahifa almashuvini sekinlashtiradi.
    """
    if w is None:
        return
    w.update()
    for bola in w.findChildren(QWidget):
        bola.update()


def yoq(w) -> None:
    """Widgetni ro'yxatdan olib tashlaydi — MILTILLAMASDAN.

    `setParent(None)` widgetni OTASIZ qiladi, otasiz widget esa Qt'da
    alohida OYNA demakdir. Agar u o'sha paytda ko'rinib turgan bo'lsa,
    Windows unga bir kadrga sarlavha satri chizadi: dastur ikonkasi
    (uy), «yoyish» va «✕» tugmalari, ostida bo'm-bo'sh oq maydon.
    Ekranda bu kichkina qora quti bo'lib chaqnab o'tadi — «g'alati
    narsa paydo bo'lib yo'qolyapti» degan shikoyat aynan shu edi.
    `deleteLater()` esa o'chirishni hodisalar navbatiga qoldiradi,
    ya'ni quti navbat kelguncha ekranda turadi.

    Shuning uchun tartib QAT'IY: avval yashiramiz, keyin otadan
    uzamiz, keyin o'chiramiz. Ro'yxat qayta qurilganda widget
    o'chirishning YAGONA to'g'ri yo'li shu — `ui_tekshir.py`
    `setParent(None)` ni boshqa joyda ishlatishga yo'l qo'ymaydi.
    """
    if w is None:
        return
    w.hide()
    w.setParent(None)
    w.deleteLater()


# ──────────────────────────────────────────────────── g'ildirak qalqoni

class GildirakQalqoni(QObject):
    """Tanlagichlar sahifani aylantirayotgan g'ildirakni O'G'IRLAMASIN.

    Qt'da `QComboBox` va `QAbstractSpinBox` (demak `QDateEdit`,
    `QTimeEdit`, `QSpinBox` ham) sichqoncha ustidan o'tsa g'ildirakni
    o'zi yutadi va QIYMATNI o'zgartiradi. Sahifada o'nlab shunday
    maydon bor, ya'ni foydalanuvchi shunchaki pastga aylantirmoqchi
    bo'lganda yo'l-yo'lakay sana, odam va davomiylik jimgina
    o'zgarib ketadi — «hamma narsa qimirlayapti» degan tuyg'u aynan
    shundan.

    Qoida: maydon FOKUSDA bo'lsa g'ildirak unga tegishli (odam ataylab
    ichiga kirgan), aks holda hodisa eng yaqin aylantirgichga
    uzatiladi va maydon qiymati qolaveradi.

    Aylantirgich topilmasa (masalan oddiy dialog) hodisa avvalgidek
    maydonning o'ziga qoladi — u yerda tasodifiy aylantirish xavfi yo'q.
    """

    def eventFilter(self, nishon, hodisa):
        if hodisa.type() != QEvent.Type.Wheel:
            return False
        if not isinstance(nishon, (QComboBox, QAbstractSpinBox)):
            return False
        if nishon.hasFocus():
            return False
        ota = nishon.parentWidget()
        while ota is not None and not isinstance(ota, QAbstractScrollArea):
            ota = ota.parentWidget()
        if ota is None:
            return False
        QApplication.sendEvent(ota.viewport(), hodisa)
        return True


# ────────────────────────────────────────────────────────────── karta

class Karta(QFrame):
    """Oq, yumshoq chegarali quti — sahifaning asosiy bo'lagi.

    Soya YO'Q: effekt butun shoxni rasterlaydi va sahifa qurilishini
    3 barobar sekinlashtiradi. Chuqurlik soch-chiziq va karta/fon
    kontrastidan keladi.
    """

    def __init__(self, sarlavha: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Karta")
        _stil(self, "KARTA_ICHI_STIL")
        self.tana = QVBoxLayout(self)
        self.tana.setContentsMargins(theme.B5 - 4, theme.B4 + 2,
                                     theme.B5 - 4, theme.B4 + 2)
        self.tana.setSpacing(theme.B3)
        self._sarlavha = None
        if sarlavha:
            e = QLabel(sarlavha.upper())
            e.setObjectName("KartaSarlavha")
            self._sarlavha = e
            self.tana.addWidget(e)

    def qosh(self, w):
        if isinstance(w, Jadval):
            w.ichkarida()
        else:
            _himoya(w)
        self.tana.addWidget(w)
        return w


class RaqamKarta(QFrame):
    """Bitta katta raqam + yorliq + izoh.

    `rangli=True` bo'lsa raqam ma'no tashiydi: yashil — senga qaytadi,
    qizil — sen berasan. Izoh ham shu ma'noga mos yumshoq fon oladi,
    shunda qarz "ayblov" emas, oddiy ma'lumot bo'lib ko'rinadi.
    """

    def __init__(self, yorliq: str, qiymat: int = 0, izoh: str = "",
                 rangli: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("Karta")
        _stil(self, "RAQAM_KARTA_STIL")
        self.rangli = rangli
        self.setMinimumWidth(168)
        self._son = int(qiymat)
        self._holat = None
        self._pill_kesh = None

        v = QVBoxLayout(self)
        v.setContentsMargins(theme.B5 - 4, theme.B4 + 2, theme.B5 - 4, theme.B4 + 2)
        v.setSpacing(theme.B1 + 1)

        self._yorliq = QLabel(yorliq.upper())
        self._yorliq.setObjectName("KartaSarlavha")

        self._qiymat = QLabel()
        self._qiymat.setObjectName("Katta")
        self._qiymat.setFont(theme.raqam_shrift(theme.O_KATTA, 600))
        self._qiymat.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._izoh = QLabel(izoh)
        self._izoh.setObjectName("Izoh")

        v.addWidget(self._yorliq)
        v.addWidget(self._qiymat)
        if rangli:
            # izoh — kichkina rangli yorliqcha (pill), matn kengligicha.
            # Stretch ishlatmaymiz: u kartaning o'lchov siyosatini
            # "Expanding" ga aylantirib, qatordagi boshqa kartalarni
            # siqib qo'yadi.
            self._izoh.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            v.addWidget(self._izoh, 0, Qt.AlignLeft | Qt.AlignTop)
        else:
            self._izoh.setWordWrap(True)
            v.addWidget(self._izoh)
        v.addStretch(1)

        self.qoy(qiymat, izoh)

    # Diqqat: raqamning o'lchami va oilasi QSS'dan (`QLabel#Katta`)
    # keladi — Qt'da QSS har doim `setFont()` dan kuchli.

    HOLATLAR = {
        "qaytadi": ("YASHIL", "YASHIL_FON"),   # senga qaytishi kerak
        "berasan": ("QIZIL", "QIZIL_FON"),     # sen berishing kerak
        "tinch":   ("KUL", "FON_TUQ"),         # qarz yo'q
        "ogoh":    ("SARIQ", "SARIQ_FON"),
    }

    def qoy(self, qiymat: int, izoh: str | None = None):
        self._son = int(qiymat)
        self._qiymat.setText(money.fmt(qiymat, belgi=self.rangli))
        rang = theme.pul_rangi(qiymat) if self.rangli else theme.MATN
        _rangla(self._qiymat, rang)
        if izoh is not None:
            self._izoh.setText(izoh)
            self._izoh.setVisible(bool(izoh))
        if self.rangli:
            self._yorliqcha(rang, theme.pul_foni(qiymat))

    def izoh_holati(self, holat: str | None):
        """Izohni ma'no rangiga bo'yaydi (`rangli=False` kartalarda ham)::

            k.izoh_holati("qaytadi" if sof > 0 else
                          "berasan" if sof < 0 else "tinch")
        """
        self._holat = holat
        if not holat:
            self._pill_kesh = None
            self._izoh.setStyleSheet("")
            return
        rang_n, fon_n = self.HOLATLAR.get(holat, self.HOLATLAR["tinch"])
        self._yorliqcha(getattr(theme, rang_n), getattr(theme, fon_n))

    def _yorliqcha(self, rang: str, fon: str):
        """Izohni kichkina rangli pill qilib ko'rsatadi."""
        self._izoh.setWordWrap(False)
        self._izoh.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        if self._pill_kesh == (rang, fon):
            return                     # bir xil — qayta "polish" shart emas
        self._pill_kesh = (rang, fon)
        self._izoh.setStyleSheet(
            f"QLabel {{ background:{fon}; color:{rang}; border:none;"
            f" border-radius:{theme.R_ORTA}px;"
            f" padding:3px 10px; font-size:{theme.O_MAYDA}px;"
            f" font-weight:600; }}")

    def _boya(self):
        self._qiymat._rang_kesh = None
        self._pill_kesh = None
        self.qoy(self._son)
        if self._holat:
            self.izoh_holati(self._holat)


# ───────────────────────────────────────────────────── pul darajasi

class _Chizgi(QWidget):
    """`OdamDaraja` ning chizig'i. QProgressBar emas, chunki bizga
    manfiy holatni ko'rsatadigan chiziqli (shtrixli) o'zan kerak —
    QProgressBar buni qila olmaydi, `setStyleSheet` esa har bo'yashda
    butun shoxni qayta "polish" qiladi.

    Grafik effekt YO'Q (soya kabi) — ular chizish keshini o'chiradi.
    """

    BALANDLIK = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.BALANDLIK)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ulush = 0.0
        self._manfiy = False
        self._asos = "#000000"
        self._ozan = "#EEEEEE"

    def qoy(self, ulush: float, manfiy: bool, asos: str, ozan: str):
        self._ulush = max(0.0, min(1.0, float(ulush or 0.0)))
        self._manfiy = bool(manfiy)
        self._asos, self._ozan = asos, ozan
        self.update()

    def paintEvent(self, _hodisa):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = r.height() / 2

        p.setBrush(QColor(self._ozan))
        p.drawRoundedRect(r, radius, radius)

        asos = QColor(self._asos)
        if self._manfiy:
            # Qo'ldagi pul manfiy: "to'ldirilish" tushunchasi yo'q.
            # Butun o'zan qiya shtrix bilan chiziladi — bu hech qachon
            # "shuncha foiz to'lgan" deb o'qilmaydi.
            p.setBrush(QBrush(asos, Qt.BDiagPattern))
            p.drawRoundedRect(r, radius, radius)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(asos, 1))
            p.drawRoundedRect(r, radius, radius)
        elif self._ulush > 0:
            # Juda kichik ulush ham ko'rinsin — aks holda "nol" bilan
            # "deyarli nol" bir xil ko'rinadi.
            kenglik = max(r.height(), r.width() * self._ulush)
            p.setBrush(asos)
            p.drawRoundedRect(QRectF(r.x(), r.y(), kenglik, r.height()),
                              radius, radius)
        p.end()


# Ommaviy nom — «Reja va fakt» dagi foiz chiziqlari ham shu chizg'ichdan.
Chizgi = _Chizgi


class OdamDaraja(QWidget):
    """Bitta odam: ism, puli, holat nishoni va daraja chizig'i.

    `holat` — `core.ledger.holat()` dan: qarzda | juda_kam | kam | yaxshi.
    `ulush` — 0.0–1.0, chiziqning to'ldirilishi (eng boy odamga nisbatan).

    Rang zinapoyasi qizil → to'q sariq → sariq → yashil: kim
    qiyinchilikda ekani o'qimasdan ko'rinadi.

    Manfiy naqd pul: chiziq orqaga ham ketmaydi, to'lib ham ketmaydi —
    butun o'zan qizil shtrix bilan chiziladi (`_Chizgi`).
    """

    def __init__(self, nom: str, naqd: int, sof: int, holat: str,
                 ulush: float, parent=None):
        super().__init__(parent)
        self.setObjectName("OdamDaraja")
        # Oddiy QWidget QSS fonini O'ZI chizmaydi (QFrame chizadi) —
        # bu bayroqsiz quyidagi `background`/`border` ko'rinmaydi.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._holat = (nom, int(naqd), int(sof), holat, float(ulush))

        v = QVBoxLayout(self)
        v.setContentsMargins(theme.B3 + 2, theme.B3, theme.B3 + 2, theme.B3)
        v.setSpacing(theme.B2)

        tepa = QHBoxLayout()
        tepa.setContentsMargins(0, 0, 0, 0)
        tepa.setSpacing(theme.B2)

        self._nishon = QLabel()            # ism harfi — odamning rangi
        self._nishon.setFixedSize(24, 24)
        self._nishon.setAlignment(Qt.AlignCenter)
        self._nom = QLabel()
        self._chip = QLabel()
        self._chip.setAlignment(Qt.AlignCenter)

        tepa.addWidget(self._nishon)
        tepa.addWidget(self._nom)
        tepa.addStretch(1)
        tepa.addWidget(self._chip)

        self._pul = QLabel()
        self._chizgi = _Chizgi(self)

        v.addLayout(tepa)
        v.addWidget(self._pul)
        v.addWidget(self._chizgi)

        self.setMinimumWidth(196)
        self.qoy(nom, naqd, sof, holat, ulush)

    def qoy(self, nom: str, naqd: int, sof: int, holat: str,
            ulush: float) -> None:
        self._holat = (nom, int(naqd), int(sof), holat, float(ulush))
        self._boya()

    def _boya(self):
        nom, naqd, sof, holat, ulush = self._holat
        asos, fon, _ = theme.daraja_rangi(holat)

        self.setStyleSheet(
            f"QWidget#OdamDaraja {{ background:{fon};"
            f" border:1px solid {theme.CHIZIQ_OCH};"
            f" border-left:4px solid {asos};"
            f" border-radius:{theme.R_ORTA}px; }}")

        odam = theme.odam_rangi(nom)
        self._nishon.setText(nom[:1].upper())
        self._nishon.setStyleSheet(
            f"QLabel {{ background:{odam}; color:{theme.ustiga(odam)};"
            f" border:none;"
            f" border-radius:12px; font-size:{theme.O_MAYDA}px;"
            f" font-weight:700; }}")

        self._nom.setText(nom)
        self._nom.setStyleSheet(
            f"QLabel {{ color:{theme.MATN}; background:transparent;"
            f" border:none; font-size:{theme.O_KICHIK}px;"
            f" font-weight:600; }}")

        # Chip to'ldirilgan: kartaning o'zi yumshoq rangda turgani
        # uchun yumshoq chip unda ko'rinmay qolardi.
        self._chip.setText(theme.DARAJA_NOM.get(holat, holat))
        self._chip.setStyleSheet(
            f"QLabel {{ background:{asos}; color:{theme.ustiga(asos)};"
            f" border:none; border-radius:{theme.R_ORTA}px;"
            f" padding:2px 9px; font-size:{theme.O_MIKRO}px;"
            f" font-weight:700; }}")

        # Raqamning rangi ishorani bildiradi (manfiy = qizil), holatni
        # emas — dasturning "yashil/qizil = qarz yo'nalishi" qoidasi
        # buzilmasin. Holat chiziq va chipda turibdi.
        self._pul.setText(money.fmt(naqd))
        self._pul.setFont(theme.raqam_shrift(theme.O_BOLIM, 600))
        self._pul.setStyleSheet(
            f"QLabel {{ color:{theme.QIZIL if naqd < 0 else theme.MATN};"
            f" background:transparent; border:none; }}")

        # O'zan foniga ham, to'ldirilgan qismga ham yaqin oraliq rang —
        # uchala rejimda ham ko'rinadi (qo'lda yozilgan rang tungi
        # rejimda fonga qo'shilib ketardi).
        self._chizgi.qoy(ulush, naqd < 0, asos, theme.aralash(asos, fon, .3))

        qarz = ("" if sof == 0 else
                f"\nboshqalar unga {money.fmt(sof)} qarzdor" if sof > 0 else
                f"\nu boshqalarga {money.fmt(-sof)} qarzdor")
        self.setToolTip(f"{nom}: {money.fmt(naqd)} "
                        f"({theme.DARAJA_NOM.get(holat, holat)}){qarz}")


class DarajaQatori(QWidget):
    """Bir necha `OdamDaraja` — yonma-yon, teng kenglikda.

    `core.ledger.darajalar()` natijasini to'g'ridan-to'g'ri qabul
    qiladi::

        qator = widgets.DarajaQatori(ledger.darajalar(db))
        ...
        qator.qoy(ledger.darajalar(db))      # yangilashda
    """

    def __init__(self, darajalar: list[dict] | None = None, parent=None):
        super().__init__(parent)
        _shaffof(self, "DarajaQatori")
        self._h = QHBoxLayout(self)
        self._h.setContentsMargins(0, 0, 0, 0)
        self._h.setSpacing(theme.B3)
        self._bolaklar: list[OdamDaraja] = []
        self.qoy(darajalar or [])

    def qoy(self, darajalar: list[dict]) -> None:
        # Mavjud bo'laklar qayta ishlatiladi — har `yangila()` da
        # butun qatorni qayta qurish keraksiz ish va miltillash.
        while len(self._bolaklar) > len(darajalar):
            w = self._bolaklar.pop()
            self._h.removeWidget(w)
            w.deleteLater()
        for i, d in enumerate(darajalar):
            qism = (d["nom"], int(d["naqd"]), int(d.get("sof", 0)),
                    d["holat"], float(d.get("ulush", 0.0)))
            if i < len(self._bolaklar):
                self._bolaklar[i].qoy(*qism)
            else:
                w = OdamDaraja(*qism, parent=self)
                self._bolaklar.append(w)
                self._h.addWidget(w, 1)


# ──────────────────────────────────────────────────────── kiritish

class PulEdit(QLineEdit):
    """Pul kiritish: yozayotganda 1 559 000 ko'rinishida ajratadi."""

    ozgardi = Signal(int)

    def __init__(self, qiymat: int = 0, parent=None):
        super().__init__(parent)
        self.setObjectName("Pul")
        _stil(self, "ICHKI_STIL")
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setPlaceholderText("0")
        self.setMinimumWidth(110)
        self._ichkarida = False
        self.textChanged.connect(self._formatla)
        if qiymat:
            self.qoy(qiymat)

    def _formatla(self, _matn: str):
        if self._ichkarida:
            return
        self._ichkarida = True
        try:
            xom = self.text()
            oxirdan = len(xom) - self.cursorPosition()
            raqamlar = "".join(c for c in xom if c.isdigit())
            yangi = money.fmt(int(raqamlar)) if raqamlar else ""
            if yangi != xom:
                self.setText(yangi)
                self.setCursorPosition(max(0, len(yangi) - oxirdan))
            self.ozgardi.emit(self.qiymat())
        finally:
            self._ichkarida = False

    def qiymat(self) -> int:
        raqamlar = "".join(c for c in self.text() if c.isdigit())
        return int(raqamlar) if raqamlar else 0

    def qoy(self, qiymat: int):
        self.setText(money.fmt(int(qiymat)) if qiymat else "")

    def tozala(self):
        self.clear()


class Taqvim(QCalendarWidget):
    """Sana tanlagichning ochiladigan taqvimi.

    NEGA ALOHIDA SINF KERAK.  Global `QTableView::item` va
    `QHeaderView::section` to'ldirmalari taqvimning ichki jadvaliga
    ham tushib kataklarni shishiradi, taqvim esa o'lchamini QSS'siz
    shrift metrikasidan hisoblaydi — natijada oyning 6-haftasi popup'ga
    sig'may qoladi («taqvim hamma kunni ko'rsatmayapti» shu edi).

    Uchta narsa qilinadi:
      1. `theme.TAQVIM_STIL` — global qoidalar aniq selektorlar bilan
         bekor qilinadi (to'ldirmalar 0 ga tushadi);
      2. o'lcham kod bilan majburlanadi — 6 qator × 7 ustun aniq
         sig'adigan minimum;
      3. ranglar palitraga ham yoziladi (QSS `:disabled` boshqa oy
         kunlariga tushmaydi — ular `QPalette::Disabled` orqali keladi).
    """

    QATOR_H = 34        # bitta kun katagining balandligi
    USTUN_W = 40        # bitta kun katagining kengligi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Taqvim")
        self.setGridVisible(False)
        self.setFirstDayOfWeek(Qt.Monday)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.setNavigationBarVisible(True)
        self.setDateEditEnabled(True)
        _stil(self, "TAQVIM_STIL")
        self._boya()

    def _boya(self):
        self.setStyleSheet(theme.TAQVIM_STIL)

        # ── palitra: QSS yetmaydigan joylar ──────────────────────────
        p = self.palette()
        p.setColor(QPalette.Window, QColor(theme.KARTA))
        p.setColor(QPalette.Base, QColor(theme.KARTA))
        p.setColor(QPalette.Text, QColor(theme.MATN))
        p.setColor(QPalette.WindowText, QColor(theme.MATN))
        p.setColor(QPalette.ButtonText, QColor(theme.MATN))
        p.setColor(QPalette.Highlight, QColor(theme.KOK))
        p.setColor(QPalette.HighlightedText, QColor(theme.KOK_MATN))
        # qo'shni oyning kunlari — o'chirilgan guruh orqali keladi
        p.setColor(QPalette.Disabled, QPalette.Text, QColor(theme.KUL_OCH))
        p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(theme.KUL_OCH))
        self.setPalette(p)

        # ── matn formatlari ─────────────────────────────────────────
        sarlavha_f = QTextCharFormat()
        sarlavha_f.setForeground(QColor(theme.KUL))
        sarlavha_f.setFontWeight(700)
        self.setHeaderTextFormat(sarlavha_f)

        oddiy = QTextCharFormat()
        oddiy.setForeground(QColor(theme.MATN))
        for kun in (Qt.Monday, Qt.Tuesday, Qt.Wednesday,
                    Qt.Thursday, Qt.Friday):
            self.setWeekdayTextFormat(kun, oddiy)
        dam = QTextCharFormat()
        dam.setForeground(QColor(theme.QIZIL))
        for kun in (Qt.Saturday, Qt.Sunday):
            self.setWeekdayTextFormat(kun, dam)

        self._olcham()

    def _olcham(self):
        """6 qator × 7 ustun ANIQ sig'adigan eng kichik o'lcham.

        Popup o'z o'lchamini taqvimning `minimumSizeHint` idan oladi,
        shuning uchun bu yerdagi son to'g'ridan-to'g'ri "oxirgi hafta
        ko'rinadimi" degan savolga javob beradi.
        """
        kor = self.findChild(QAbstractItemView, "qt_calendar_calendarview")
        if kor is not None:
            kor.setMinimumSize(self.USTUN_W * 7, self.QATOR_H * 6)
            v = kor.verticalHeader()
            v.setMinimumSectionSize(self.QATOR_H)
            v.setDefaultSectionSize(self.QATOR_H)
            g = kor.horizontalHeader()
            g.setMinimumSectionSize(self.USTUN_W)
            g.setDefaultSectionSize(self.USTUN_W)
            kor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            kor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            kor.setFrameShape(QFrame.NoFrame)
        # navbar (36) + hafta nomlari (~22) + 6 qator + chegara
        self.setMinimumSize(self.USTUN_W * 7 + 16, self.QATOR_H * 6 + 74)


class SanaEdit(QDateEdit):
    def __init__(self, sana: str | None = None, parent=None):
        super().__init__(parent)
        _stil(self, "ICHKI_STIL")
        self.setCalendarPopup(True)
        # O'z taqvimimiz: standart taqvimga global QSS tushib, oxirgi
        # hafta qatorini qirqib qo'yadi (`Taqvim` izohiga qarang).
        self.setCalendarWidget(Taqvim(self))
        self.setDisplayFormat("dd.MM.yyyy")
        self.setMinimumWidth(134)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.qoy(sana)

    def qoy(self, sana: str | None):
        if sana:
            self.setDate(QDate.fromString(str(sana)[:10], "yyyy-MM-dd"))
        else:
            self.setDate(QDate.currentDate())

    def iso(self) -> str:
        return self.date().toString("yyyy-MM-dd")


class OdamTanla(QComboBox):
    def __init__(self, db, hammasi: bool = False, parent=None):
        super().__init__(parent)
        self.db = db
        _stil(self, "ICHKI_STIL")
        self.setMinimumWidth(126)
        self.yangila(hammasi)

    def yangila(self, hammasi: bool = False):
        joriy = self.odam_id()
        self.clear()
        if hammasi:
            self.addItem("Hammasi", None)
        for r in self.db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id"):
            self.addItem(r["nom"], r["id"])
        if joriy is not None:
            self.tanla(joriy)

    def odam_id(self):
        return self.currentData()

    def tanla(self, odam_id):
        i = self.findData(odam_id)
        if i >= 0:
            self.setCurrentIndex(i)


class HamyonTanla(QComboBox):
    """Pul qayerdan chiqdi / qayerga tushdi: «💵 Naqd» yoki odamning
    kartalari (`core/hamyon.py`). Odam almashganda `odam_qoy()` bilan
    qayta to'ldiriladi; tanlangan karta o'sha odamniki bo'lsa joyida
    qoladi, aks holda naqdga qaytadi."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        _stil(self, "ICHKI_STIL")
        self.setMinimumWidth(150)
        self.odam_qoy(None)

    def odam_qoy(self, odam_id):
        from core import hamyon
        joriy = self.karta_id()
        with QSignalBlocker(self):
            self.clear()
            for kid, nom in hamyon.tanlov(self.db, odam_id):
                self.addItem(("💵 " if kid is None else "💳 ") + nom, kid)
            self.tanla(joriy)

    def karta_id(self):
        return self.currentData()

    def tanla(self, karta_id):
        i = self.findData(karta_id)
        self.setCurrentIndex(i if i >= 0 else 0)


# ─────────────────────────────────────────────── kategoriya ikonkasi
#
# Ekran masshtabi 125–150% bo'lsa, mantiqiy o'lchamda (26 px) tayyorlangan
# rasmni Windows cho'zadi — ikonka XIRA chiqadi. Shuning uchun kategoriya
# ikonkasi hech qachon `QPixmap(...).scaled(n)` bilan olinmaydi: yonida
# SVG bo'lsa (`packaging/belgi_chiz.py` qo'yadi) Qt uni SO'RALGAN o'lcham
# × ekran masshtabida vektordan chizadi; bo'lmasa PNG silliq
# kichraytiriladi — baribir ekran pikselida.

_BELGI_KESH: dict[str, QIcon] = {}


def belgi_ikon(yol) -> QIcon:
    """Kategoriya ikonkasi (`kategoriya.rasm_yoli()` yo'li) — SVG afzal."""
    kalit = str(yol)
    ikon = _BELGI_KESH.get(kalit)
    if ikon is None:
        from pathlib import Path
        svg = Path(kalit).with_suffix(".svg")
        ikon = QIcon(str(svg)) if svg.exists() else QIcon()
        if ikon.isNull():                  # SVG dvigateli yo'q / fayl buzuq
            ikon = QIcon(kalit)
        _BELGI_KESH[kalit] = ikon
    return ikon


def belgi_rasm(yol, olcham: int, widget: QWidget | None = None) -> QPixmap:
    """Aniq ekran pikselida tayyor rasm (`QLabel.setPixmap` uchun)."""
    if widget is not None:
        dpr = widget.devicePixelRatioF()
    else:
        ekran = QApplication.primaryScreen()
        dpr = ekran.devicePixelRatio() if ekran else 1.0
    return belgi_ikon(yol).pixmap(QSize(olcham, olcham), dpr)


class TuriTanla(QComboBox):
    """Kategoriya tanlagich.

    `majburiy=True` — rasxod oynalari uchun: bo'sh variant «kategoriyasiz»
    deb emas, «tanlang» deb yoziladi, chunki u yerda kategoriyasiz
    saqlab bo'lmaydi (`entries.rasxod_majburiy`).
    """

    def __init__(self, db, hammasi: bool = False, parent=None,
                 majburiy: bool = False):
        super().__init__(parent)
        self.db = db
        self.majburiy = majburiy
        _stil(self, "ICHKI_STIL")
        self.setMinimumWidth(150)
        self.setIconSize(QSize(20, 20))
        self.yangila(hammasi)

    def yangila(self, hammasi: bool = False):
        from core import kategoriya, mahsulot
        joriy = self.currentData()
        self.clear()
        bosh = ("Hammasi" if hammasi else
                "— kategoriya tanlang —" if self.majburiy else
                "— kategoriyasiz —")
        self.addItem(bosh, None)
        # Daraxt tartibida: ichki kategoriya otasining ostida, surilgan.
        for r, chuq in mahsulot.tekis(self.db):
            surish = "      " * chuq + ("↳ " if chuq else "")
            yol = kategoriya.rasm_yoli(r["rasm"])
            if yol:
                self.addItem(belgi_ikon(yol), surish + r["nom"], r["id"])
            else:
                self.addItem(surish + f"{r['belgi']} {r['nom']}".strip(),
                             r["id"])
        if joriy is not None:
            i = self.findData(joriy)
            if i >= 0:
                self.setCurrentIndex(i)

    def turi_id(self):
        return self.currentData()


class KategoriyaTanla(QWidget):
    """Rasxod uchun IKKI BOSQICHLI kategoriya: katta + uning ichkisi.

    Chapda faqat katta (asosiy) kategoriyalar, o'ngda — tanlangan
    kattaning ichki kategoriyalari (har chuqurlikda, surilgan). Ichkisi
    yo'q bo'lsa o'ng maydon o'chiq turadi. Botdagi «📂 → ichidan
    tanlang» bilan bir xil g'oya.

    `turi_id()` — ichki tanlangan bo'lsa o'sha, aks holda katta.
    `ozgardi` — ikkala maydondan biri o'zgarganda (bitta signal):
    tashqaridan `QSignalBlocker(self)` bilan to'sish kifoya.
    """

    ozgardi = Signal()
    ICHKISIZ = "— ichki kategoriyasiz —"

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        _shaffof(self, "Qator")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.asosiy = QComboBox()
        self.ichki = QComboBox()
        for c in (self.asosiy, self.ichki):
            _stil(c, "ICHKI_STIL")
            c.setMinimumWidth(150)
            c.setIconSize(QSize(20, 20))
            h.addWidget(c)
        self.asosiy.setToolTip("Katta kategoriya")
        self.ichki.setToolTip("Tanlangan kategoriyaning ichki kategoriyasi")
        self.asosiy.currentIndexChanged.connect(self._asosiy_ozgardi)
        self.ichki.currentIndexChanged.connect(lambda _i: self.ozgardi.emit())
        self.yangila()

    def _yorliq(self, t, surish: str = "") -> tuple:
        from core import kategoriya
        yol = kategoriya.rasm_yoli(t["rasm"])
        if yol:
            return belgi_ikon(yol), surish + t["nom"]
        return None, surish + f"{t['belgi']} {t['nom']}".strip()

    def _qosh(self, combo: QComboBox, belgi, matn: str, turi_id) -> None:
        if belgi is not None:
            combo.addItem(belgi, matn, turi_id)
        else:
            combo.addItem(matn, turi_id)

    def yangila(self, *_):
        """Kategoriyalar qayta o'qiladi, tanlov joyida qoladi."""
        from core import mahsulot
        joriy = self.turi_id()
        with QSignalBlocker(self.asosiy), QSignalBlocker(self.ichki):
            self.asosiy.clear()
            self.asosiy.addItem("— kategoriya tanlang —", None)
            for t in mahsulot.daraxt(self.db):
                self._qosh(self.asosiy, *self._yorliq(t), t["id"])
            self._ichkilarni_toldir()
        if joriy is not None:
            with QSignalBlocker(self):
                self.tanla(joriy)

    def _ichkilarni_toldir(self) -> None:
        from core import mahsulot
        self.ichki.clear()
        self.ichki.addItem(self.ICHKISIZ, None)
        ota = self.asosiy.currentData()
        if ota is not None:
            def yur(tugunlar, chuq):
                for t in tugunlar:
                    surish = "      " * chuq + ("↳ " if chuq else "")
                    self._qosh(self.ichki, *self._yorliq(t, surish), t["id"])
                    yur(t["bolalar"], chuq + 1)
            tugun = next((t for t in mahsulot.daraxt(self.db)
                          if t["id"] == ota), None)
            if tugun is not None:
                yur(tugun["bolalar"], 0)
        self.ichki.setEnabled(self.ichki.count() > 1)

    def _asosiy_ozgardi(self, _i=None):
        with QSignalBlocker(self.ichki):
            self._ichkilarni_toldir()
        self.ozgardi.emit()

    def tanla(self, turi_id) -> bool:
        """Istalgan chuqurlikdagi kategoriyani tanlaydi: katta maydonga
        uning eng yuqori otasi, ichkisiga o'zi. Topilmasa (nofaol) —
        False, tanlov o'zgarmaydi."""
        if turi_id is None:
            return False
        yol, joriy, korilgan = [], turi_id, set()
        while joriy is not None and joriy not in korilgan:
            korilgan.add(joriy)
            yol.append(joriy)
            r = self.db.q1("SELECT ota_id FROM turi WHERE id=?", joriy)
            joriy = r["ota_id"] if r else None
        # Otasi nofaol bo'lsa `daraxt` bolani ildiz qiladi — shuning
        # uchun katta maydonda BOR bo'lgan eng yuqori ajdod olinadi.
        ildiz = next((x for x in reversed(yol)
                      if self.asosiy.findData(x) >= 0), None)
        if ildiz is None:
            return False
        with QSignalBlocker(self.asosiy), QSignalBlocker(self.ichki):
            self.asosiy.setCurrentIndex(self.asosiy.findData(ildiz))
            self._ichkilarni_toldir()
            i = self.ichki.findData(turi_id) if turi_id != ildiz else 0
            self.ichki.setCurrentIndex(max(0, i))
        self.ozgardi.emit()
        return turi_id == ildiz or i >= 0

    def turi_id(self):
        return self.ichki.currentData() or self.asosiy.currentData()

    def currentText(self) -> str:
        """Tanlangan kategoriyaning to'liq nomi («Bozorlik › Mevalar»)."""
        from core import mahsulot
        return mahsulot.yol_nomi(self.db, self.turi_id())


# ──────────────────────────────────────────────────────────── jadval

class _Chizguvchi(QStyledItemDelegate):
    """Tanlangan qatorda ham katakning o'z rangini saqlaydi.

    Aks holda qator tanlanishi bilan yashil «+656 666» qora bo'lib
    qoladi va ma'no yo'qoladi — moliyaviy dasturda bu yo'l qo'yilmaydi.
    """

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        rang = index.data(Qt.ForegroundRole)
        if rang is not None:
            q = rang.color() if hasattr(rang, "color") else QColor(rang)
            if q.isValid():
                option.palette.setColor(QPalette.HighlightedText, q)


class Jadval(QTableWidget):
    """Faqat o'qish uchun jadval, pul ustunlari o'nga tekislangan."""

    def __init__(self, ustunlar: list[str], pul_ustunlar: set[int] | None = None,
                 parent=None, bosh_matn: str = "Hozircha yozuv yo'q"):
        super().__init__(0, len(ustunlar), parent)
        self.pul_ustunlar = pul_ustunlar or set()
        self._ichkarida = False
        _stil(self, "JADVAL_YAKKA_STIL")
        self.setHorizontalHeaderLabels(ustunlar)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setFocusPolicy(Qt.StrongFocus)

        h = self.horizontalHeader()
        h.setStretchLastSection(True)
        h.setHighlightSections(False)
        h.setFixedHeight(38)
        h.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.verticalHeader().setDefaultSectionSize(42)
        self.verticalHeader().setMinimumSectionSize(30)

        # pul ustunining sarlavhasi ham o'ngda tursin — ko'z ustun
        # bo'ylab pastga tushganda sarlavha va raqam bir chiziqda
        for c in self.pul_ustunlar:
            it = self.horizontalHeaderItem(c)
            if it is not None:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.setItemDelegate(_Chizguvchi(self))

        # bo'sh holat — jadval quruq turmasin
        self._bosh = QLabel(bosh_matn, self.viewport())
        self._bosh.setAlignment(Qt.AlignCenter)
        self._bosh.setVisible(True)      # hozircha qator yo'q
        self._boya()

    # ── ko'rinish ────────────────────────────────────────────────────

    def _boya(self):
        """Rejim almashganda: palitra, shriftlar va katak ranglari."""
        _stil(self, "JADVAL_KARTADA_STIL" if self._ichkarida
              else "JADVAL_YAKKA_STIL")

        pal = self.palette()
        pal.setColor(QPalette.Highlight, QColor(theme.KOK_FON))
        pal.setColor(QPalette.HighlightedText, QColor(theme.MATN))
        self.setPalette(pal)

        self._matn = theme.matn_shrift(theme.O_KICHIK, 400)
        self._pul = theme.raqam_shrift(theme.O_KICHIK, 600)

        self._bosh.setStyleSheet(
            f"QLabel {{ color:{theme.KUL_OCH}; background:transparent;"
            f" border:none; font-size:{theme.O_KICHIK}px; }}")

        # mavjud kataklarni qayta bo'yash — pul qiymati katakda
        # saqlangani uchun yashil/qizil ma'no yangi palitrada tiklanadi
        oq = QColor(theme.MATN)
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it is None:
                    continue
                v = it.data(_PUL_ROLI)
                if v is None:
                    it.setFont(self._matn)
                    continue
                it.setFont(self._pul)
                it.setForeground(QColor(theme.pul_rangi(int(v)))
                                 if it.data(_RANGLI_ROLI) else oq)

    def ichkarida(self, ha: bool = True):
        """Karta ichida turganda ikkilangan chegara kerak emas."""
        self._ichkarida = ha
        _stil(self, "JADVAL_KARTADA_STIL" if ha else "JADVAL_YAKKA_STIL")

    def bosh_yozuv(self, matn: str):
        """Jadval bo'sh bo'lganda ko'rinadigan matn."""
        self._bosh.setText(matn)
        self._joyla()

    def _joyla(self):
        self._bosh.setGeometry(self.viewport().rect())

    def resizeEvent(self, hodisa):
        super().resizeEvent(hodisa)
        self._joyla()

    # ── ma'lumot ─────────────────────────────────────────────────────

    def kengliklar(self, *kengliklar: int):
        """Ustun kengliklari. 0 — qolgan joyni egallaydi.

        `Fixed` emas, `Interactive` ishlatiladi: `Fixed` ustunlar jadvalning
        eng kichik kengligini ularning yig'indisiga bog'lab qo'yadi, natijada
        BUTUN sahifa eniga cho'zilib ketadi va oynada gorizontal aylantirgich
        paydo bo'ladi. `Interactive` da kenglik o'sha-o'sha, lekin jadval
        kerak bo'lsa qisilib, ortiqchasini o'z ichida aylantiradi.
        """
        h = self.horizontalHeader()
        for i, w in enumerate(kengliklar):
            if w <= 0:
                h.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                h.setSectionResizeMode(i, QHeaderView.Interactive)
                self.setColumnWidth(i, w)
        # Jadval sahifaning enini belgilamasin — o'zi qisilsin.
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Ignored, self.sizePolicy().verticalPolicy())

    def tuldir(self, qatorlar: list[list], idlar: list | None = None,
               rangli_ustunlar: set[int] | None = None):
        rangli_ustunlar = rangli_ustunlar or set()
        # katta ro'yxatda har `setItem` dan keyin ko'rinishni qayta
        # hisoblamasin
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(len(qatorlar))
            oq = QColor(theme.MATN)
            ranglar = {}
            for r, qator_ in enumerate(qatorlar):
                for c, qiymat in enumerate(qator_):
                    if isinstance(qiymat, QTableWidgetItem):
                        item = qiymat
                    elif c in self.pul_ustunlar and isinstance(qiymat, (int, float)):
                        rangli = c in rangli_ustunlar
                        item = QTableWidgetItem(money.fmt(qiymat, belgi=rangli))
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        item.setFont(self._pul)
                        item.setData(_PUL_ROLI, int(qiymat))
                        if rangli:
                            item.setData(_RANGLI_ROLI, True)
                            nom = theme.pul_rangi(int(qiymat))
                            rang = ranglar.get(nom)
                            if rang is None:
                                rang = ranglar[nom] = QColor(nom)
                            item.setForeground(rang)
                        else:
                            item.setForeground(oq)
                    else:
                        item = QTableWidgetItem("" if qiymat is None else str(qiymat))
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        item.setFont(self._matn)
                    if idlar and r < len(idlar):
                        item.setData(Qt.UserRole, idlar[r])
                    self.setItem(r, c, item)
        finally:
            self.setUpdatesEnabled(True)
        self._bosh.setVisible(not qatorlar)
        self._joyla()

    def tanlangan_id(self):
        r = self.currentRow()
        if r < 0:
            return None
        it = self.item(r, 0)
        return it.data(Qt.UserRole) if it else None


# ──────────────────────────────────────────────────────── yordamchi

def sarlavha(matn: str) -> QLabel:
    """Sahifa sarlavhasi."""
    e = QLabel(matn)
    e.setObjectName("Sarlavha")
    return _stil(e, "YORLIQ_STIL")


def bolim(matn: str) -> QLabel:
    """Karta ichidagi kichik bo'lim sarlavhasi."""
    e = QLabel(matn)
    e.setObjectName("Bolim")
    return _stil(e, "YORLIQ_STIL")


def izoh(matn: str) -> QLabel:
    e = QLabel(matn)
    e.setObjectName("Izoh")
    _stil(e, "YORLIQ_STIL")
    e.setWordWrap(True)
    return e


def yorliq(matn: str) -> QLabel:
    e = QLabel(matn)
    e.setObjectName("Yorliq")
    return _stil(e, "YORLIQ_STIL")


def tugma(matn: str, asosiy: bool = False, xavfli: bool = False) -> QPushButton:
    b = QPushButton(matn)
    if asosiy:
        b.setObjectName("Asosiy")
    elif xavfli:
        b.setObjectName("Xavfli")
    _stil(b, "TUGMA_STIL")
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(36)
    return b


def kengaytirgich() -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    return _shaffof(w, "Kengaytirgich")


def qator(*widgetlar, oraliq: int = 10) -> QWidget:
    """Gorizontal qator.

    `None` — bo'sh joy (stretch). Agar `None` berilmagan va qatorda
    kengayadigan widget bo'lmasa, oxiriga o'zi stretch qo'shadi —
    shunda yorliq/tanlagichlar sahifa bo'ylab cho'zilib ketmaydi.
    """
    w = QWidget()
    _shaffof(w, "Qator")
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(oraliq)
    stretch_bor = False
    kengayadi = False
    for x in widgetlar:
        if x is None:
            h.addStretch(1)
            stretch_bor = True
        elif isinstance(x, str):
            h.addWidget(yorliq(x))
        else:
            _himoya(x)
            if x.sizePolicy().horizontalPolicy().value & QSizePolicy.ExpandFlag.value:
                kengayadi = True
            h.addWidget(x)
    if not stretch_bor and not kengayadi:
        h.addStretch(1)
    return w


class Xabar(QLabel):
    """Yuqorida chiqadigan xabar yo'lagi (ok / xato / ogohlantirish)."""

    RANGLAR = {
        "ok":   ("YASHIL_FON", "YASHIL", "YASHIL_TUQ"),
        "xato": ("QIZIL_FON", "QIZIL", "QIZIL_TUQ"),
        "ogoh": ("SARIQ_FON", "SARIQ", "SARIQ"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setVisible(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._oxirgi = None

    def korsat(self, matn: str, turi: str = "ok", muddat: int = 0):
        self._oxirgi = (matn, turi)
        fon_n, chek_n, matn_n = self.RANGLAR.get(turi, self.RANGLAR["ok"])
        fon = getattr(theme, fon_n)
        chek = getattr(theme, chek_n)
        matn_rang = getattr(theme, matn_n)
        self.setStyleSheet(
            f"QLabel {{ background:{fon}; color:{matn_rang};"
            f" border:1px solid {fon}; border-left:3px solid {chek};"
            f" border-radius:{theme.R_ORTA}px; padding:11px 14px;"
            f" font-size:{theme.O_KICHIK}px; font-weight:600; }}")
        self.setText(matn)
        self.setVisible(True)
        if muddat:
            QTimer.singleShot(muddat, lambda: self.setVisible(False))

    def yashir(self):
        self.setVisible(False)

    def _boya(self):
        if not self._oxirgi:
            return
        korinsin = self.isVisible()
        self.korsat(*self._oxirgi)
        self.setVisible(korinsin)


class Holat(QLabel):
    """Tinch holat yo'lagi — «hech kim qarzdor emas» kabi."""

    def __init__(self, matn: str = "", turi: str = "ok", parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self._oxirgi = (matn, turi)
        self.qoy(matn, turi)

    def qoy(self, matn: str, turi: str = "ok"):
        self._oxirgi = (matn, turi)
        ranglar = {
            "ok":   (theme.YASHIL_FON, theme.YASHIL_TUQ, theme.YASHIL),
            "sokin": (theme.KARTA_ICH, theme.KUL, theme.CHIZIQ),
            "ogoh": (theme.SARIQ_FON, theme.SARIQ, theme.SARIQ),
        }
        fon, matn_rang, chek = ranglar.get(turi, ranglar["ok"])
        self.setStyleSheet(
            f"QLabel {{ background:{fon}; color:{matn_rang};"
            f" border:1px solid {chek}; border-radius:{theme.R_KARTA}px;"
            f" padding:18px 16px; font-size:{theme.O_ORTA}px;"
            f" font-weight:600; }}")
        self.setText(matn)

    def _boya(self):
        self.qoy(*self._oxirgi)


class _PulYorliq(QLabel):
    """`pul_yorliq()` qaytaradigan yorliq — rejim almashsa qayta bo'yaladi."""

    def __init__(self, qiymat: int, olcham: int, rangli: bool, belgi: bool):
        super().__init__()
        self._qiymat = int(qiymat)
        self._olcham = olcham
        self._rangli = rangli
        self._belgi = belgi
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._boya()

    def _boya(self):
        self.setText(money.fmt(self._qiymat, belgi=self._belgi))
        self.setFont(theme.raqam_shrift(self._olcham, 600))
        rang = theme.pul_rangi(self._qiymat) if self._rangli else theme.MATN
        self._rang_kesh = None
        _rangla(self, rang)


def pul_yorliq(qiymat: int, olcham: int = theme.O_ORTA,
               rangli: bool = True, belgi: bool = False) -> QLabel:
    """Bitta pul raqami — tabular shrift bilan, o'nga tekislangan."""
    return _PulYorliq(qiymat, olcham, rangli, belgi)


class _Chiziq(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(1)
        self._boya()

    def _boya(self):
        self.setStyleSheet(
            f"QFrame {{ background:{theme.CHIZIQ}; border:none; }}")


def chiziq() -> QFrame:
    """Yumshoq ajratgich chiziq."""
    return _Chiziq()
