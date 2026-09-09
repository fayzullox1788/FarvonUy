"""Vazifalar — uy ishlarining haftalik kalendari.

Excel «Vazifalar» varag'i shuni so'ragan:
  · haftalik umumiy kalendar — hamma nima qilishi ko'rinib turadi;
  · vazifa aniq odamga, aniq kunga va aniq soatga biriktiriladi;
  · «shaxsma shaxs» — odam faqat o'zinikini ko'ra oladi;
  · bir kun o'tkazib yuborilsa, keyingi ishlar surilib ketadi (B13).

Kalendarning o'zi — `HaftaTaqvim`: ustunlar kun, qatorlar soat.
Bloklar bolalar widget, to'r esa `paintEvent` da chiziladi: 18 soat ×
7 kun = 126 katak, ularning har birini widget qilish sahifani
sezilarli sekinlashtiradi.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import (QEasingCurve, QPropertyAnimation,
                            QSignalBlocker, QTime, Qt, Signal)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QScrollArea,
                               QSpinBox, QTimeEdit, QVBoxLayout, QWidget)

from core import reports
from core import menyu as mn
from core import xabar
from core import vazifa as vz
from ui.eski import theme
from ui.eski.dialogs import tasdiq, xato_koraset
from ui.eski.sahifa_asosiy import Sahifa, shaffof
from ui.eski.sahifa_qosh import och
from ui.eski.widgets import (Jadval, Karta, OdamTanla, RaqamKarta, SanaEdit,
                             bolim, izoh, qator, sarlavha, tugma, yoq,
                             yorliq)

SOAT_DAN = 6         # to'r shu soatdan boshlanadi
SOAT_GACHA = 24
SOAT_H = 52          # bir soatning balandligi (piksel)
YONBOSH = 62         # chapdagi soat ustuni
BOSH_H = 62          # kun sarlavhalari
KUNSIZ_H = 34        # "vaqti yo'q" yo'lagining bir qatori
USTUN_ENG_KAM = 132  # bir kun ustunining eng kam kengligi


def _rang(odam_id: int) -> str:
    return theme.odam_rangi(odam_id)


def _kun_nomi(p, kun, kenglik: float) -> str:
    """To'liq kun nomi; ustunga sig'masa qisqasi.

    «Chorshanba» tor ustunda kesilib qolmasin — oyna kichraytirilganda
    yoki odam ko'p bo'lganda ustun ensiz bo'ladi.
    """
    toliq = vz.KUNLAR[kun.weekday()]
    if p.fontMetrics().horizontalAdvance(toliq) <= kenglik - 10:
        return toliq
    return vz.KUN_QISQA[kun.weekday()]


# ═══════════════════════════════════════════════════════ vazifa oynasi

class VazifaDialog(QDialog):
    """Vazifa qo'shish / tahrirlash."""

    def __init__(self, db, vazifa_id: int | None = None, sana=None,
                 tur=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.vazifa_id = vazifa_id
        self.tur = tur
        if tur is not None:
            self.setWindowTitle("Biriktirish")
        else:
            self.setWindowTitle("Vazifa" if vazifa_id else "Yangi vazifa")
        self.setMinimumWidth(430)

        tashqi = QVBoxLayout(self)
        forma = QFormLayout()
        forma.setSpacing(10)

        self.nom = QComboBox()
        self.nom.setEditable(True)
        self.nom.addItems(vz.tur_nomlari(db))
        self.nom.setCurrentText("")
        self.odam = OdamTanla(db)
        self.sana = SanaEdit(sana)
        self.vaqtsiz = QCheckBox("Aniq vaqtsiz (kun davomida)")
        self.vaqt = QTimeEdit(QTime(9, 0))
        self.vaqt.setDisplayFormat("HH:mm")
        self.davomiylik = QSpinBox()
        self.davomiylik.setRange(5, 12 * 60)
        self.davomiylik.setSingleStep(15)
        self.davomiylik.setValue(60)
        self.davomiylik.setSuffix(" daqiqa")
        self.izoh = QLineEdit()
        self.izoh.setPlaceholderText("Ixtiyoriy")

        forma.addRow("Vazifa:", self.nom)
        forma.addRow("Kim bajaradi:", self.odam)
        forma.addRow("Kun:", self.sana)
        forma.addRow("", self.vaqtsiz)
        forma.addRow("Vaqt:", self.vaqt)
        forma.addRow("Davomiyligi:", self.davomiylik)
        forma.addRow("Izoh:", self.izoh)
        tashqi.addLayout(forma)

        # ── navbat (ovqat): bittasi tanlansa qolgani o'zi joylashadi
        self.navbatli = tur is not None and bool(tur["navbat"])
        self.navbat = QCheckBox("Navbat bilan davom etsin")
        self.navbat_kun = QSpinBox()
        self.navbat_kun.setRange(1, 28)
        self.navbat_kun.setValue(7)
        self.navbat_kun.setSuffix(" kun")
        self.navbat_korsat = izoh("")
        if self.navbatli:
            self.navbat.setChecked(True)
            navbat_karta = Karta("Ovqat navbati")
            navbat_karta.qosh(qator(self.navbat, None, self.navbat_kun))
            navbat_karta.qosh(self.navbat_korsat)
            tashqi.addWidget(navbat_karta)
            for signal in (self.navbat.toggled, self.odam.currentIndexChanged,
                           self.navbat_kun.valueChanged,
                           self.sana.dateChanged, self.vaqt.timeChanged,
                           self.vaqtsiz.toggled):
                signal.connect(self._navbatni_korsat)

        self.vaqtsiz.toggled.connect(self._vaqtsiz_ozgardi)

        tugmalar = QDialogButtonBox(QDialogButtonBox.Save
                                    | QDialogButtonBox.Cancel)
        tugmalar.button(QDialogButtonBox.Save).setText("Saqlash")
        tugmalar.button(QDialogButtonBox.Cancel).setText("Bekor qilish")
        tugmalar.accepted.connect(self._saqla)
        tugmalar.rejected.connect(self.reject)
        tashqi.addWidget(tugmalar)

        if vazifa_id:
            self._yukla(vazifa_id)
        elif tur is not None:
            # Tur ro'yxatidan kelindi: nomi tayyor, o'zgartirilmaydi —
            # bu yerda faqat «kim, qachon» hal qilinadi.
            self.nom.setCurrentText(tur["nom"])
            self.nom.setEnabled(False)
            self.davomiylik.setValue(tur["davomiylik"])
            if self.navbatli:
                self.vaqt.setTime(QTime(19, 0))
                self._navbatni_korsat()

    def _vaqtsiz_ozgardi(self, yoqilgan: bool):
        self.vaqt.setEnabled(not yoqilgan)
        self.davomiylik.setEnabled(not yoqilgan)

    def _navbatni_korsat(self):
        """Navbat rejasini oldindan ko'rsatadi — kim pishiradi, kim yuvadi."""
        if not self.navbatli:
            return
        yoqilgan = self.navbat.isChecked()
        self.navbat_kun.setEnabled(yoqilgan)
        if not yoqilgan:
            self.navbat_korsat.setText(
                "Faqat tanlangan odamga, bitta kunga yoziladi.")
            return
        try:
            reja = vz.navbat_rejasi(
                self.db, self.tur["id"], self.odam.odam_id(),
                self.sana.iso(),
                None if self.vaqtsiz.isChecked()
                else self.vaqt.time().toString("HH:mm"),
                self.navbat_kun.value())
        except Exception as e:
            self.navbat_korsat.setText(str(e))
            return
        satrlar = [f"• {x['sana'].strftime('%d.%m')} "
                   f"{x['vaqt'] or '—'}  {x['odam']} — {x['nom']}"
                   for x in reja[:6]]
        qolgan = len(reja) - len(satrlar)
        if qolgan > 0:
            satrlar.append(f"• … yana {qolgan} ta")
        matn = f"{len(reja)} ta vazifa yoziladi:\n" + "\n".join(satrlar)
        if vz.tur_ergash(self.db, self.tur["id"]) is None:
            matn += ("\n\n⚠ Ovqatdan keyingi ish tanlanmagan — faqat "
                     "pishirish yoziladi. Vazifalar ro'yxatidagi «keyin:» "
                     "dan idish yuvishni tanlang.")
        self.navbat_korsat.setText(matn)

    def _yukla(self, vazifa_id: int):
        v = vz.bitta(self.db, vazifa_id)
        if not v:
            return
        self.nom.setCurrentText(v["nom"])
        self.odam.tanla(v["odam_id"])
        self.sana.qoy(v["sana"])
        if v["vaqt"]:
            self.vaqt.setTime(QTime.fromString(v["vaqt"], "HH:mm"))
        else:
            self.vaqtsiz.setChecked(True)
        self.davomiylik.setValue(v["davomiylik"])
        self.izoh.setText(v["izoh"] or "")

    def _saqla(self):
        maydonlar = dict(
            nom=self.nom.currentText().strip(),
            odam_id=self.odam.odam_id(),
            sana=self.sana.iso(),
            vaqt=None if self.vaqtsiz.isChecked()
            else self.vaqt.time().toString("HH:mm"),
            davomiylik=self.davomiylik.value(),
            izoh=self.izoh.text())
        try:
            if self.vazifa_id:
                vz.tahrir(self.db, self.vazifa_id, **maydonlar)
            elif self.navbatli and self.navbat.isChecked():
                vz.navbat_biriktir(
                    self.db, self.tur["id"], maydonlar["odam_id"],
                    maydonlar["sana"], maydonlar["vaqt"],
                    self.navbat_kun.value())
            else:
                vz.qosh(self.db, **maydonlar)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


# ══════════════════════════════════════════════════ tafsilot + bekor

class VazifaTafsilot(QDialog):
    """Bitta vazifa: hammasi ko'rinadi, shu yerda bekor qilinadi."""

    def __init__(self, db, vazifa_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.vazifa_id = vazifa_id
        self.ozgardi = False
        v = vz.bitta(db, vazifa_id)
        if not v:
            self.reject()
            return
        self.setWindowTitle("Vazifa tafsiloti")
        self.setMinimumWidth(470)

        tashqi = QVBoxLayout(self)
        tashqi.setSpacing(12)
        bosh = sarlavha(v["nom"])
        bosh.setWordWrap(True)
        tashqi.addWidget(bosh)

        odam = db.q1("SELECT nom FROM odam WHERE id=?", v["odam_id"])
        kun = vz._sana(v["sana"])
        satrlar = [
            ("Kim bajaradi", odam["nom"] if odam else "—"),
            ("Kun", f"{kun.strftime('%d.%m.%Y')}, "
                    f"{vz.KUNLAR[kun.weekday()].lower()}"),
            ("Vaqt", f"{v['vaqt']} · {v['davomiylik']} daqiqa"
                     if v["vaqt"] else "aniq vaqtsiz"),
            ("Holati", "Bajarildi" if v["holat"] == vz.BAJARILDI
                       else "Bajarilmagan"),
        ]
        if v["bajarilgan"]:
            satrlar.append(("Bajarilgan vaqti",
                            str(v["bajarilgan"]).replace("T", " ")))
        # Guruhda oshpaz tanlagan taom. Alohida qator, `izoh` EMAS:
        # izohni foydalanuvchi yozadi, buni Telegram tugmasi yozadi —
        # bittasi ikkinchisini bosib ketmasligi kerak.
        if v["menyu"]:
            satrlar.append(("Menyu", f"🍲 {v['menyu']}"))
        if v["izoh"]:
            satrlar.append(("Izoh", v["izoh"]))

        karta = Karta("Ma'lumot")
        for yorliq_matn, qiymat in satrlar:
            e = QLabel(qiymat)
            e.setWordWrap(True)
            karta.qosh(qator(yorliq(yorliq_matn + ":"), None, e))
        tashqi.addWidget(karta)

        bajarildi = v["holat"] == vz.BAJARILDI
        t_holat = tugma("Qayta ochish" if bajarildi else "Bajarildi",
                        asosiy=not bajarildi)
        t_holat.clicked.connect(lambda: self._holat(not bajarildi))
        t_tahrir = tugma("Tahrirlash")
        t_tahrir.clicked.connect(self._tahrir)
        t_bekor = tugma("Vazifani bekor qilish", xavfli=True)
        t_bekor.clicked.connect(self._bekor)
        tashqi.addWidget(qator(t_holat, t_tahrir, None, t_bekor))

        # ── navbatni o'zgartirish
        almash = Karta("Navbatni o'zgartirish")
        self.yangi_odam = OdamTanla(db)
        self.yangi_odam.tanla(v["odam_id"])
        t_almash = tugma("Almashtirish", asosiy=True)
        t_almash.setToolTip(
            "Ikkalasi navbatini almashadi: bu kun tanlangan odamga o'tadi, "
            "uning keyingi navbati esa hozirgi egasiga. Keyingi kunlar "
            "joyida qoladi.")
        t_almash.clicked.connect(self._almashtir)
        t_bersin = tugma("Faqat shu kunni berish")
        t_bersin.setToolTip(
            "Almashuvsiz: shu kun tanlangan odamga o'tadi, boshqa hech "
            "narsa o'zgarmaydi. Avvalgi tartibsizlikni tekislash uchun.")
        t_bersin.clicked.connect(self._bersin)
        # Ikkala tugma alohida qatorda: bitta qatorga siqilsa
        # «Faqat shu kunni berish» qirqilib qoladi.
        almash.qosh(qator(yorliq("Kimga:"), self.yangi_odam, None))
        almash.qosh(qator(t_almash, t_bersin, None))
        self.almash_izoh = izoh(
            "Kim pishirsa, idishni undan oldingi navbatchi yuvadi — "
            "o'zgartirilganda o'sha kunning yuvuvchisi ham o'zi to'g'rilanadi.")
        almash.qosh(self.almash_izoh)
        tashqi.addWidget(almash)

        yop = tugma("Yopish")
        yop.clicked.connect(self.accept)
        tashqi.addWidget(qator(None, yop))

    def _almashtir(self):
        yangi = self.yangi_odam.odam_id()
        if yangi is None:
            return
        try:
            reja = vz.almashtirish_rejasi(self.db, self.vazifa_id, yangi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        v, juft = reja["vazifa"], reja["juft"]
        eski_nom = self.db.q1("SELECT nom FROM odam WHERE id=?",
                              reja["eski_odam"])["nom"]
        yangi_nom = self.db.q1("SELECT nom FROM odam WHERE id=?",
                               reja["yangi_odam"])["nom"]
        if not tasdiq(self, f"Ikki navbat almashadi:\n\n"
                            f"  • {v['sana']} — {eski_nom} o'rniga "
                            f"{yangi_nom}\n"
                            f"  • {juft['sana']} — {yangi_nom} o'rniga "
                            f"{eski_nom}\n\n"
                            f"Qolgan kunlarga tegilmaydi, navbat soni "
                            f"ikkalasida ham o'zgarmaydi. Davom etilsinmi?"):
            return
        try:
            vz.almashtir(self.db, self.vazifa_id, yangi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()

    def _bersin(self):
        yangi = self.yangi_odam.odam_id()
        if yangi is None:
            return
        v = vz.bitta(self.db, self.vazifa_id)
        if not v:
            return
        yangi_nom = self.db.q1("SELECT nom FROM odam WHERE id=?", yangi)["nom"]
        if not tasdiq(self, f"«{v['nom']}» ({v['sana']}) {yangi_nom}ga "
                            f"o'tsinmi?\n\n"
                            f"Almashuv YO'Q — boshqa kunlarga tegilmaydi."):
            return
        try:
            vz.bersin(self.db, self.vazifa_id, yangi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()

    def _holat(self, bajarildi: bool):
        try:
            vz.bajar(self.db, self.vazifa_id, bajarildi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()

    def _tahrir(self):
        if VazifaDialog(self.db, self.vazifa_id, parent=self).exec():
            self.ozgardi = True
            self.accept()

    def _bekor(self):
        v = vz.bitta(self.db, self.vazifa_id)
        if not v:
            return
        if not tasdiq(self, f"«{v['nom']}» vazifasi bekor qilinsinmi?\n\n"
                            f"Kalendardan yo'qoladi, lekin tarixda qoladi."):
            return
        try:
            vz.ochir(self.db, self.vazifa_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.ozgardi = True
        self.accept()


# ═════════════════════════════════════════════════════════════ bloklar

class _Blok(QFrame):
    """Kalendardagi bitta vazifa."""

    bosildi = Signal(int)

    def __init__(self, qator_, parent=None):
        super().__init__(parent)
        self.vazifa_id = qator_["id"]
        self.setCursor(Qt.PointingHandCursor)
        bajarildi = qator_["holat"] == vz.BAJARILDI
        kechikkan = (not bajarildi
                     and vz._sana(qator_["sana"]) < date.today())
        asos = _rang(qator_["odam_id"])
        # Bajarilgan ish O'CHIB qolmaydi, YASHIL bo'lib yonadi.
        #
        # Avval u kulrangga aylanardi — mantiqan «bu endi muhim emas»,
        # lekin ko'zga «bu ish o'lgan» bo'lib ko'rinardi. Bajarish —
        # kunning yagona mukofoti, shuning uchun eng ko'zga
        # tashlanadigan holat aynan shu bo'lishi kerak: to'q yashil
        # chek, yashil fon va katta ✓.
        #
        # `aralash(a, b, ulush)` da `ulush` — a ning ulushi. Blok fon
        # ochiq bo'lishi kerak, shuning uchun odam rangidan ozgina.
        if bajarildi:
            fon = theme.YASHIL_FON
            chek = theme.YASHIL
        else:
            fon = theme.aralash(asos, theme.KARTA, 0.16)
            chek = asos
        self.setObjectName("VazifaBlok")
        self.setStyleSheet(
            f"QFrame#VazifaBlok {{ background: {fon};"
            f" border-left: {'5' if bajarildi else '3'}px solid {chek};"
            f" border-radius: {theme.R_KICHIK}px; }}")

        ich = QVBoxLayout(self)
        ich.setContentsMargins(8, 4, 6, 4)
        ich.setSpacing(0)
        # DIQQAT: global QSS `QLabel { font-size }` `setFont()` dan
        # kuchliroq — o'lcham ham shu yerda, stilda berilishi kerak.
        # ✓ nom bilan bir xil o'lchamda emas: u alohida, kattaroq va
        # yashil yorliqda turadi (pastda). Matnda faqat kechikkan
        # belgisi qoladi.
        belgi = "" if bajarildi else ("⏳ " if kechikkan else "")
        self._toliq = belgi + qator_["nom"]
        pas_matn = f"{qator_['vaqt'] or ''} · {qator_['odam']}".strip(" ·")
        # Oshpaz Telegramda taom tanlagan bo'lsa kalendarda ham
        # ko'rinsin — «o'sha kuni nima pishirilgan?» eng ko'p
        # so'raladigan savol.
        taom = (qator_["menyu"] if "menyu" in qator_.keys() else None)
        if taom:
            pas_matn = f"{pas_matn} · 🍲 {taom}".strip(" ·")
        # Ixcham qatorda vaqt YOZILMAYDI: u to'rdagi joyidan ko'rinib
        # turibdi. Eng muhimi kim ekani — u birinchi turadi.
        self._ixcham = f"{belgi}{qator_['odam']} · {qator_['nom']}"

        nom_qatori = QWidget()
        shaffof(nom_qatori)
        nq = QHBoxLayout(nom_qatori)
        nq.setContentsMargins(0, 0, 0, 0)
        nq.setSpacing(5)

        # DIQQAT: global QSS `QLabel { font-size }` `setFont()` dan
        # kuchliroq — o'lcham stil varag'ida berilishi shart.
        self.belgi_yorliq = QLabel("✓")
        self.belgi_yorliq.setStyleSheet(
            f"color:{theme.YASHIL};background:transparent;"
            f"font-size:{theme.O_ORTA}px;font-weight:800;")
        # DIQQAT: `setVisible(True)` avval `addWidget()` dan KEYIN.
        # Otasi yo'q widget Qt'da OYNA demakdir: uni ko'rsatsak,
        # Windows unga sarlavha satri chizadi (dastur ikonkasi + «✕»)
        # va u ekranda bir kadrga qora quti bo'lib chaqnab o'tadi.
        # Har bajarilgan vazifa uchun bittadan — ya'ni kalendar
        # ochilganda o'nlab marta.
        nq.addWidget(self.belgi_yorliq, 0, Qt.AlignTop)
        self.belgi_yorliq.setVisible(bajarildi)

        self.nom_yorliq = QLabel(self._toliq)
        self.nom_yorliq.setWordWrap(True)
        self.nom_yorliq.setStyleSheet(
            f"color:{theme.YASHIL_TUQ if bajarildi else theme.MATN};"
            f"background:transparent;font-size:{theme.O_MAYDA}px;"
            f"font-weight:{'700' if bajarildi else '600'};")
        nq.addWidget(self.nom_yorliq, 1)
        ich.addWidget(nom_qatori)

        self.pas = QLabel(pas_matn)
        self.pas.setStyleSheet(
            f"color:{theme.YASHIL if bajarildi else theme.KUL};"
            f"background:transparent;"
            f"font-size:{theme.O_MIKRO}px;font-weight:500;")
        ich.addWidget(self.pas)
        ich.addStretch(1)

        holat = "bajarildi" if bajarildi else (
            "kechikkan" if kechikkan else "bajarilmagan")
        maslahat = (f"{qator_['nom']}\n{qator_['odam']} · "
                    f"{qator_['sana']} {qator_['vaqt'] or ''}\n{holat}")
        if taom:
            maslahat += f"\nMenyu: {taom}"
        self.setToolTip(maslahat)

    def ixcham(self, ha: bool):
        """Past blokka (yarim soatlik ish) ikki qator sig'maydi.

        Shunda vaqt va ism pastdan nomning YONIGA ko'chadi — aks holda
        ikkinchi qator birinchisining ustiga chiqib, ikkalasi ham
        o'qilmay qoladi.
        """
        self.pas.setVisible(not ha)
        self.nom_yorliq.setWordWrap(not ha)
        self.nom_yorliq.setText(self._ixcham if ha else self._toliq)
        self.layout().setContentsMargins(8, 2 if ha else 4, 6, 2 if ha else 4)

    def mousePressEvent(self, hodisa):
        if hodisa.button() == Qt.LeftButton:
            self.bosildi.emit(self.vazifa_id)
        super().mousePressEvent(hodisa)


# ═══════════════════════════════════════════════════════ vaqt to'ri
#
# Kalendar uch bo'lak:
#   HaftaBosh  — kun sarlavhalari + vaqtsiz vazifalar. YOPISHGAN:
#                aylantirilmaydi, aks holda 09:00 ga surilganda qaysi
#                ustun qaysi kun ekani ko'rinmay qoladi.
#   HaftaTor   — soat to'ri va vaqtli bloklar, aylanadi.
#   HaftaTaqvim— ikkalasini birlashtiruvchi qobiq (tashqi kod shu bilan
#                ishlaydi).


def _ustun_kengligi(kenglik: int, n: int) -> float:
    if not n:
        return 0.0
    return max(1.0, (kenglik - YONBOSH - 4) / n)


def _eng_kam_kenglik(n: int) -> int:
    """To'r shundan tor bo'lmaydi — undan keyin YON TOMONGA aylanadi.

    Oyna kichrayganda ustunlar cheksiz siqilaverardi: yetti kun
    140 pikselga bo'linib, blokdagi matn o'qilmay qolardi. Endi
    ustun `USTUN_ENG_KAM` dan tor bo'lmaydi va o'rniga gorizontal
    aylantirgich chiqadi.
    """
    return YONBOSH + 4 + n * USTUN_ENG_KAM


class HaftaBosh(QWidget):
    """Kun sarlavhalari + \"kun bo'yi\" yo'lagi. Aylantirilmaydi."""

    vazifa_bosildi = Signal(int)
    bosh_joy_bosildi = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.kunlar: list[date] = []
        self.qatorlar: list = []
        self._bloklar: list[_Blok] = []
        self._qator_soni = 0
        self.setFixedHeight(BOSH_H)

    def qoy(self, kunlar, qatorlar):
        self.kunlar = list(kunlar)
        self.qatorlar = [r for r in qatorlar if not r["vaqt"]]
        for b in self._bloklar:
            yoq(b)
        self._bloklar = []
        for r in self.qatorlar:
            b = _Blok(r, self)
            b.bosildi.connect(self.vazifa_bosildi)
            b.show()
            self._bloklar.append(b)
        eng_kop = 0
        for k in self.kunlar:
            n = sum(1 for r in self.qatorlar if r["sana"] == k.isoformat())
            eng_kop = max(eng_kop, n)
        self._qator_soni = eng_kop
        self.setFixedHeight(BOSH_H + eng_kop * KUNSIZ_H
                            + (6 if eng_kop else 0))
        self._joylashtir()
        self.update()

    def _joylashtir(self):
        if not self.kunlar:
            return
        kw = _ustun_kengligi(self.width(), len(self.kunlar))
        hisob: dict[str, int] = {}
        for blok, r in zip(self._bloklar, self.qatorlar):
            try:
                ustun = self.kunlar.index(vz._sana(r["sana"]))
            except ValueError:
                blok.hide()
                continue
            blok.show()
            n = hisob.get(r["sana"], 0)
            hisob[r["sana"]] = n + 1
            blok.setGeometry(int(YONBOSH + ustun * kw + 3),
                             int(BOSH_H + 3 + n * KUNSIZ_H),
                             int(kw - 7), KUNSIZ_H - 4)
            blok.ixcham(KUNSIZ_H - 4 < 38)

    def resizeEvent(self, hodisa):
        super().resizeEvent(hodisa)
        self._joylashtir()

    def mousePressEvent(self, hodisa):
        if not self.kunlar or hodisa.button() != Qt.LeftButton:
            return
        x, y = hodisa.position().x(), hodisa.position().y()
        if x < YONBOSH or y < BOSH_H:
            return
        ustun = int((x - YONBOSH)
                    // max(1.0, _ustun_kengligi(self.width(), len(self.kunlar))))
        if 0 <= ustun < len(self.kunlar):
            self.bosh_joy_bosildi.emit(self.kunlar[ustun], None)

    def paintEvent(self, hodisa):
        if not self.kunlar:
            return
        p = QPainter(self)
        kw = _ustun_kengligi(self.width(), len(self.kunlar))
        bugun = date.today()
        p.fillRect(self.rect(), QColor(theme.KARTA))

        p.setFont(theme.matn_shrift(theme.O_MIKRO, 600))
        for i, k in enumerate(self.kunlar):
            x = YONBOSH + i * kw
            shu_kun = k == bugun
            if shu_kun:
                p.fillRect(int(x), 0, int(kw), self.height(),
                           QColor(theme.KOK_FON))
            p.setPen(QPen(QColor(theme.KUL)))
            p.drawText(int(x), 10, int(kw), 18,
                       Qt.AlignHCenter | Qt.AlignVCenter,
                       _kun_nomi(p, k, kw))
            p.setFont(theme.raqam_shrift(theme.O_BOLIM, 700))
            p.setPen(QPen(QColor(theme.KOK if shu_kun else theme.MATN)))
            p.drawText(int(x), 26, int(kw), 26,
                       Qt.AlignHCenter | Qt.AlignVCenter, str(k.day))
            p.setFont(theme.matn_shrift(theme.O_MIKRO, 600))

        if self._qator_soni:
            p.setPen(QPen(QColor(theme.CHIZIQ_OCH)))
            p.drawLine(0, BOSH_H, self.width(), BOSH_H)
            p.setPen(QPen(QColor(theme.KUL_OCH)))
            p.drawText(4, BOSH_H, YONBOSH - 10, self.height() - BOSH_H,
                       Qt.AlignRight | Qt.AlignVCenter, "kun bo'yi")

        p.setPen(QPen(QColor(theme.CHIZIQ)))
        for i in range(len(self.kunlar) + 1):
            x = YONBOSH + i * kw
            p.drawLine(int(x), 0, int(x), self.height())
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        p.end()


class HaftaTor(QWidget):
    """Soat to'ri va vaqti belgilangan bloklar. Aylanadi."""

    vazifa_bosildi = Signal(int)
    bosh_joy_bosildi = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.kunlar: list[date] = []
        self.qatorlar: list = []
        self._bloklar: list[_Blok] = []
        self.setMinimumHeight((SOAT_GACHA - SOAT_DAN) * SOAT_H + 8)

    def qoy(self, kunlar, qatorlar):
        self.kunlar = list(kunlar)
        self.qatorlar = [r for r in qatorlar if r["vaqt"]]
        for b in self._bloklar:
            yoq(b)
        self._bloklar = []
        for r in self.qatorlar:
            b = _Blok(r, self)
            b.bosildi.connect(self.vazifa_bosildi)
            b.show()
            self._bloklar.append(b)
        self._joylashtir()
        self.update()

    def y_vaqtdan(self, daqiqa: int) -> float:
        return (daqiqa - SOAT_DAN * 60) / 60 * SOAT_H

    def _joylashtir(self):
        if not self.kunlar:
            return
        kw = _ustun_kengligi(self.width(), len(self.kunlar))
        bandlik: dict[tuple[str, int], list] = {}
        for r in self.qatorlar:
            bandlik.setdefault((r["sana"], vz._daqiqa(r["vaqt"])),
                               []).append(r["id"])
        for blok, r in zip(self._bloklar, self.qatorlar):
            try:
                ustun = self.kunlar.index(vz._sana(r["sana"]))
            except ValueError:
                blok.hide()
                continue
            blok.show()
            daqiqa = vz._daqiqa(r["vaqt"])
            y = self.y_vaqtdan(daqiqa)
            h = max(26, r["davomiylik"] / 60 * SOAT_H - 3)
            birga = bandlik.get((r["sana"], daqiqa), [r["id"]])
            n = len(birga)
            i = birga.index(r["id"])
            kichik_w = (kw - 7) / n
            blok.setGeometry(int(YONBOSH + ustun * kw + 3 + i * kichik_w),
                             int(y + 1), int(kichik_w - 2), int(h))
            blok.ixcham(h < 38)

    def resizeEvent(self, hodisa):
        super().resizeEvent(hodisa)
        self._joylashtir()

    def mousePressEvent(self, hodisa):
        if not self.kunlar or hodisa.button() != Qt.LeftButton:
            return
        x, y = hodisa.position().x(), hodisa.position().y()
        if x < YONBOSH:
            return
        kw = _ustun_kengligi(self.width(), len(self.kunlar))
        ustun = int((x - YONBOSH) // max(1.0, kw))
        if not 0 <= ustun < len(self.kunlar):
            return
        daqiqa = SOAT_DAN * 60 + int(y / SOAT_H * 60)
        daqiqa = max(0, min(23 * 60 + 30, (daqiqa // 30) * 30))
        self.bosh_joy_bosildi.emit(self.kunlar[ustun], vz._vaqt_matn(daqiqa))

    def paintEvent(self, hodisa):
        if not self.kunlar:
            return
        p = QPainter(self)
        kw = _ustun_kengligi(self.width(), len(self.kunlar))
        bugun = date.today()
        p.fillRect(self.rect(), QColor(theme.KARTA))

        for i, k in enumerate(self.kunlar):
            if k == bugun:
                p.fillRect(int(YONBOSH + i * kw), 0, int(kw), self.height(),
                           QColor(theme.KOK_FON))

        p.setFont(theme.raqam_shrift(theme.O_MIKRO, 500))
        for soat in range(SOAT_DAN, SOAT_GACHA + 1):
            y = self.y_vaqtdan(soat * 60)
            p.setPen(QPen(QColor(theme.CHIZIQ_OCH)))
            p.drawLine(YONBOSH, int(y), self.width(), int(y))
            if soat < SOAT_GACHA:
                p.setPen(QPen(QColor(theme.KUL_OCH)))
                p.drawText(0, int(y) - 7, YONBOSH - 10, 14,
                           Qt.AlignRight | Qt.AlignVCenter, f"{soat:02d}:00")
                p.setPen(QPen(QColor(theme.CHIZIQ_OCH), 1, Qt.DotLine))
                p.drawLine(YONBOSH, int(y + SOAT_H / 2),
                           self.width(), int(y + SOAT_H / 2))

        p.setPen(QPen(QColor(theme.CHIZIQ)))
        for i in range(len(self.kunlar) + 1):
            x = YONBOSH + i * kw
            p.drawLine(int(x), 0, int(x), self.height())

        if bugun in self.kunlar and SOAT_DAN <= datetime.now().hour < SOAT_GACHA:
            hozir = datetime.now()
            y = self.y_vaqtdan(hozir.hour * 60 + hozir.minute)
            i = self.kunlar.index(bugun)
            p.setPen(QPen(QColor(theme.QIZIL), 2))
            p.drawLine(int(YONBOSH + i * kw), int(y),
                       int(YONBOSH + (i + 1) * kw), int(y))
        p.end()


class HaftaTaqvim(QWidget):
    """Yopishgan bosh + aylanadigan soat to'ri."""

    vazifa_bosildi = Signal(int)
    bosh_joy_bosildi = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.aylanma = QScrollArea()
        self.aylanma.setWidgetResizable(True)
        self.aylanma.setFrameShape(QFrame.NoFrame)
        # Aylantirgich DOIM ko'rinadi: u paydo bo'lib-yo'qolsa to'rning
        # eni o'zgaradi va ustunlar bosh bilan mos kelmay qoladi.
        self.aylanma.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # Gorizontal esa KERAK BO'LGANDA: ustunlar `USTUN_ENG_KAM`
        # dan tor bo'lib ketmasin. Keng oynada u umuman chiqmaydi.
        self.aylanma.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Bosh aylanmaydi, ya'ni aylantirgich enini O'ZI hisobga olishi
        # kerak — aks holda ustunlar to'rnikidan shuncha piksel siljiydi.
        # Aynan shu "kalendar qiyshiq" muammosi edi.
        self.bosh = HaftaBosh()
        self.bosh.vazifa_bosildi.connect(self.vazifa_bosildi)
        self.bosh.bosh_joy_bosildi.connect(self.bosh_joy_bosildi)
        # Bosh IKKINCHI aylantirgichda emas, oddiy qutida turadi va
        # to'r bilan birga qo'lda suriladi (`_boshni_sur`).
        #
        # Nega ikkinchi aylantirgich emas: uning o'z diapazoni to'rniki
        # bilan bir necha piksel farq qiladi (aylantirgich dastasining
        # haqiqiy eni `sizeHint()` dan boshqacha), va o'ng chekkada
        # sarlavha o'z ustunidan siljib qolardi. Qo'lda surishda esa
        # siljish AYNAN to'rniki qancha bo'lsa shuncha.
        #
        # Vertikal esa avvalgidek qimirlamaydi: 09:00 ga surilganda
        # kun sarlavhalari joyida qolishi kerak.
        self.bosh_quti = QWidget()
        shaffof(self.bosh_quti)
        self.bosh.setParent(self.bosh_quti)
        self.bosh.move(0, 0)
        v.addWidget(self.bosh_quti)

        self.tor = HaftaTor()
        self.tor.vazifa_bosildi.connect(self.vazifa_bosildi)
        self.tor.bosh_joy_bosildi.connect(self.bosh_joy_bosildi)
        self.aylanma.setWidget(self.tor)
        v.addWidget(self.aylanma, 1)

        # To'r yon tomonga surilganda bosh AYNAN shuncha suriladi.
        self.aylanma.horizontalScrollBar().valueChanged.connect(
            self._boshni_sur)

    def qoy(self, kunlar, qatorlar):
        self.bosh.qoy(kunlar, qatorlar)
        self.tor.qoy(kunlar, qatorlar)
        eng_kam = _eng_kam_kenglik(len(kunlar))
        self.tor.setMinimumWidth(eng_kam)
        # Bosh o'zining tayin balandligini aylantirgichga ham beradi:
        # `QScrollArea` aks holda uni o'zicha cho'zib yuboradi.
        self._boshni_olcha()
        self._vaqtga_sur()

    def resizeEvent(self, hodisa):
        super().resizeEvent(hodisa)
        self._boshni_olcha()

    def _boshni_olcha(self):
        """Bosh to'r bilan BIR XIL enda bo'lsin.

        Ustun kengligi enidan hisoblanadi (`_ustun_kengligi`), demak
        eni bir piksel farq qilsa ham sarlavha o'z ustunidan siljiydi.
        `QScrollArea` to'rni `max(eng kam, viewport)` qilib cho'zadi —
        bosh ham aynan shu qoida bilan o'lchanadi.
        """
        en = max(self.tor.minimumWidth(), self.aylanma.viewport().width())
        if self.bosh.width() != en:
            self.bosh.resize(en, self.bosh.height())
        if self.bosh_quti.height() != self.bosh.height():
            self.bosh_quti.setFixedHeight(self.bosh.height())

    def _boshni_sur(self, qiymat: int):
        self.bosh.move(-int(qiymat), 0)
        # Ko'chirilgan widget ortidagi joyni ota to'ldirishi kerak;
        # quti shaffof bo'lgani uchun buni o'zi qilmaydi va sarlavha
        # izi ekranda qolib ketardi.
        self.bosh_quti.update()

    def _vaqtga_sur(self):
        """Birinchi vazifa ko'rinadigan joyga suradi.

        To'r 06:00 dan boshlanadi, uy ishlari esa odatda 09:00 dan
        keyin — aks holda foydalanuvchi bo'sh to'rni ko'rib \"vazifam
        yo'q\" deb o'ylaydi.
        """
        daqiqalar = [vz._daqiqa(r["vaqt"]) for r in self.tor.qatorlar]
        boshlanish = min(daqiqalar) if daqiqalar else 8 * 60
        y = self.tor.y_vaqtdan(boshlanish) - 20
        self.aylanma.verticalScrollBar().setValue(max(0, int(y)))



# ═════════════════════════════════════════════════════════════ oy to'ri

class OyTaqvim(QWidget):
    """Oylik ko'rinish: har kunda nechta vazifa borligi."""

    kun_bosildi = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        shaffof(self)
        self.oy_boshi = date.today().replace(day=1)
        self.qatorlar: list = []
        self.setMinimumHeight(430)

    def qoy(self, oy_boshi: date, qatorlar: list):
        self.oy_boshi = oy_boshi
        self.qatorlar = list(qatorlar)
        self.update()

    def _to_r(self) -> list[date]:
        bosh = vz.hafta_boshi(self.oy_boshi)
        return [bosh + timedelta(days=i) for i in range(42)]

    def mousePressEvent(self, hodisa):
        w = self.width() / 7
        h = (self.height() - 26) / 6
        ustun = int(hodisa.position().x() // max(1.0, w))
        qatr = int((hodisa.position().y() - 26) // max(1.0, h))
        if 0 <= ustun < 7 and 0 <= qatr < 6:
            self.kun_bosildi.emit(self._to_r()[qatr * 7 + ustun])

    def paintEvent(self, hodisa):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.KARTA))
        w = self.width() / 7
        h = (self.height() - 26) / 6
        bugun = date.today()
        sanoq: dict[str, list] = {}
        for r in self.qatorlar:
            sanoq.setdefault(r["sana"], []).append(r)

        p.setFont(theme.matn_shrift(theme.O_MIKRO, 600))
        p.setPen(QPen(QColor(theme.KUL)))
        for i, nom in enumerate(vz.KUNLAR):
            if p.fontMetrics().horizontalAdvance(nom) > w - 10:
                nom = vz.KUN_QISQA[i]
            p.drawText(int(i * w), 0, int(w), 24, Qt.AlignCenter, nom)

        for i, k in enumerate(self._to_r()):
            x, y = (i % 7) * w, 26 + (i // 7) * h
            shu_oy = k.month == self.oy_boshi.month
            if k == bugun:
                p.fillRect(int(x) + 1, int(y) + 1, int(w) - 2, int(h) - 2,
                           QColor(theme.KOK_FON))
            p.setPen(QPen(QColor(theme.CHIZIQ_OCH)))
            p.drawRect(int(x), int(y), int(w), int(h))
            p.setFont(theme.raqam_shrift(theme.O_KICHIK, 600))
            p.setPen(QPen(QColor(theme.MATN if shu_oy else theme.KUL_OCH)))
            p.drawText(int(x) + 6, int(y) + 4, int(w) - 12, 18,
                       Qt.AlignLeft | Qt.AlignVCenter, str(k.day))

            kun_qatorlar = sanoq.get(k.isoformat(), [])
            p.setFont(theme.matn_shrift(theme.O_MIKRO, 500))
            for j, r in enumerate(kun_qatorlar[:3]):
                yy = y + 24 + j * 17
                if yy + 15 > y + h:
                    break
                asos = _rang(r["odam_id"])
                bajarildi = r["holat"] == vz.BAJARILDI
                p.fillRect(int(x) + 4, int(yy), int(w) - 8, 15,
                           QColor(theme.aralash(asos, theme.KARTA,
                                                0.08 if bajarildi else 0.18)))
                p.setPen(QPen(QColor(theme.KUL if bajarildi else theme.MATN)))
                matn = ("✓ " if bajarildi else "") + r["nom"]
                p.drawText(int(x) + 7, int(yy), int(w) - 14, 15,
                           Qt.AlignLeft | Qt.AlignVCenter,
                           p.fontMetrics().elidedText(
                               matn, Qt.ElideRight, int(w) - 14))
            if len(kun_qatorlar) > 3:
                p.setPen(QPen(QColor(theme.KUL)))
                p.drawText(int(x) + 7, int(y + h) - 17, int(w) - 14, 15,
                           Qt.AlignLeft | Qt.AlignVCenter,
                           f"+{len(kun_qatorlar) - 3} ta")
        p.end()


# ═══════════════════════════════════════════════════════════ sahifa

class VazifalarSahifa(QWidget):
    """Vazifalar bo'limining asosiy sahifasi."""

    # Hisobot turlari. Kalit `_eksport()` da ishlatiladi.
    #
    # «Umumiy rasxod» va «Shaxsiy ulush» FAQAT umumiy xarajatni
    # ko'radi (`umumiymi=1`): shaxsiy rasxod odamning o'z puli va uni
    # jamoaga ko'rsatishning ma'nosi yo'q. Ikkinchisi «mening
    # rasxodim» emas — umumiy xaridning shu odamga tushgan qismi.
    HISOBOTLAR = [
        ("Vazifalar kalendari", "vazifa"),
        ("Umumiy rasxodlar", "umumiy"),
        ("Shaxsiy ulush", "ulush"),
    ]


    KORINISH = [("Kunlik", 1), ("Haftalik", 7), ("Oylik", 0)]

    def __init__(self, oyna):
        super().__init__()
        self.oyna = oyna
        self.db = oyna.db
        self.joriy = date.today()
        self.korinish = 7

        tashqi = QVBoxLayout(self)
        tashqi.setContentsMargins(24, 20, 24, 20)
        tashqi.setSpacing(14)

        qosh_t = tugma("+ Vazifa qo'shish", asosiy=True)
        qosh_t.clicked.connect(lambda: self._yangi(self.joriy))
        # Hisobotlar SHU YERDA, bitta joyda. Avval ikkita tugma
        # («HTML», «Excel») ikkita varaqda takrorlanardi va qaysi
        # hisobot chiqishi tugmadan bilinmasdi. Endi avval NIMA
        # kerakligi tanlanadi, keyin qaysi ko'rinishda saqlash.
        self.hisobot_tur = QComboBox()
        for nom, kalit in self.HISOBOTLAR:
            self.hisobot_tur.addItem(nom, kalit)
        self.hisobot_tur.setMinimumWidth(190)
        self.hisobot_tur.setToolTip(
            "Qaysi hisobot saqlansin. Oraliq — hozir ko'rinib "
            "turgani, odam esa yuqoridagi tanlovdan.")
        html_t = tugma("HTML")
        html_t.setToolTip("Tanlangan hisobotni HTML qilib saqlaydi")
        html_t.clicked.connect(lambda: self._eksport("html"))
        excel_t = tugma("Excel")
        excel_t.setToolTip("Tanlangan hisobotni Excel qilib saqlaydi")
        excel_t.clicked.connect(lambda: self._eksport("excel"))
        tashqi.addWidget(qator(sarlavha("Vazifalar"), None,
                               self.hisobot_tur, html_t, excel_t, qosh_t))

        # ── boshqaruv yo'lagi
        self.korinish_guruh = QButtonGroup(self)
        self.korinish_guruh.setExclusive(True)
        korinish_qatori = []
        for i, (nom, _) in enumerate(self.KORINISH):
            b = tugma(nom)
            b.setCheckable(True)
            self.korinish_guruh.addButton(b, i)
            korinish_qatori.append(b)
        self.korinish_guruh.button(1).setChecked(True)
        self.korinish_guruh.idClicked.connect(self._korinish_ozgardi)
        self._korinish_boya()

        oldingi = tugma("‹")
        keyingi = tugma("›")
        bugun_t = tugma("Bugun")
        oldingi.setMaximumWidth(38)
        keyingi.setMaximumWidth(38)
        oldingi.clicked.connect(lambda: self._sur(-1))
        keyingi.clicked.connect(lambda: self._sur(1))
        bugun_t.clicked.connect(self._bugunga)

        self.odam = OdamTanla(self.db, hammasi=True)
        self.odam.currentIndexChanged.connect(self.yangila)

        surish_t = tugma("Kunni surish →")
        surish_t.setToolTip(
            "Shu kundan boshlab bajarilmagan hamma vazifa bir kunga "
            "suriladi — kun o'tkazib yuborilganda shunday qilinadi.")
        surish_t.clicked.connect(self._surish)

        self.oraliq_yorliq = bolim("")
        tashqi.addWidget(qator(*korinish_qatori, oldingi, keyingi, bugun_t,
                               self.oraliq_yorliq, None,
                               yorliq("Kim:"), self.odam, surish_t))

        self.xulosa = izoh("")
        tashqi.addWidget(self.xulosa)

        # ── kalendar
        self.taqvim = HaftaTaqvim()
        self.taqvim.vazifa_bosildi.connect(self._tafsilot)
        self.taqvim.bosh_joy_bosildi.connect(self._yangi)

        self.oy_taqvim = OyTaqvim()
        self.oy_taqvim.kun_bosildi.connect(self._kunga_otish)
        self.oy_taqvim.hide()

        tashqi.addWidget(self.taqvim, 1)
        tashqi.addWidget(self.oy_taqvim, 1)

        self.yordam = izoh(
            "Blokka bosilsa — tafsilot va bekor qilish. Bo'sh katakka "
            "bosilsa — o'sha kun va soatga yangi vazifa.")
        tashqi.addWidget(self.yordam)

        self.yangila()

    # ── boshqaruv ───────────────────────────────────────────────────

    def _korinish_boya(self):
        """Faol ko'rinish tugmasi «Asosiy» bo'lib turadi.

        QSS objectName bo'yicha yozilgan, shuning uchun nomni almashtirib
        widgetni qayta sayqallash kerak — aks holda stil eskisicha qoladi.
        """
        faol = self.korinish_guruh.checkedId()
        for i in range(len(self.KORINISH)):
            b = self.korinish_guruh.button(i)
            if b is None:
                continue
            b.setObjectName("Asosiy" if i == faol else "")
            b.style().unpolish(b)
            b.style().polish(b)

    def _korinish_ozgardi(self, indeks: int):
        self.korinish = self.KORINISH[indeks][1]
        self.korinish_guruh.button(indeks).setChecked(True)
        self._korinish_boya()
        self.yangila()

    def _sur(self, yon: int):
        if self.korinish == 0:
            oy = self.joriy.month + yon
            yil = self.joriy.year + (oy - 1) // 12
            self.joriy = date(yil, (oy - 1) % 12 + 1, 1)
        else:
            self.joriy += timedelta(days=yon * max(1, self.korinish))
        self.yangila()

    def _bugunga(self):
        self.joriy = date.today()
        self.yangila()

    def _kunga_otish(self, kun: date):
        """Oylik ko'rinishda kunga bosilsa — o'sha kunning kunlik ko'rinishi."""
        self.joriy = kun
        self._korinish_ozgardi(0)

    # ── amallar ─────────────────────────────────────────────────────

    def _yangi(self, kun=None, vaqt=None):
        d = VazifaDialog(self.db, sana=(kun or self.joriy).isoformat(),
                         parent=self)
        if vaqt:
            d.vaqt.setTime(QTime.fromString(vaqt, "HH:mm"))
        elif kun is not None and vaqt is None:
            d.vaqtsiz.setChecked(True)
        if d.exec():
            self.oyna.yangila()

    def _tafsilot(self, vazifa_id: int):
        d = VazifaTafsilot(self.db, vazifa_id, parent=self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()

    def _oraliq(self) -> tuple[str, str]:
        """Hozir ko'rinib turgan sana oralig'i (kunlik/haftalik/oylik)."""
        if self.korinish == 0:
            oy_boshi = self.joriy.replace(day=1)
            bosh = vz.hafta_boshi(oy_boshi)
            return oy_boshi.isoformat(), (bosh + timedelta(days=41)).isoformat()
        kunlar = self._kunlar()
        return kunlar[0].isoformat(), kunlar[-1].isoformat()

    def _eksport(self, tur: str):
        """Tanlangan hisobotni, ko'rinib turgan oraliq uchun chiqaradi."""
        dan, gacha = self._oraliq()
        odam_id = self.odam.odam_id()
        qaysi = self.hisobot_tur.currentData()
        try:
            if qaysi == "umumiy":
                # Umumiy rasxod butun uyniki — odam bo'yicha
                # filtrlanmaydi, aks holda ma'nosi yo'qoladi.
                yol = (reports.umumiy_rasxod_html(self.db, dan, gacha)
                       if tur == "html" else
                       reports.umumiy_rasxod_excel(self.db, dan, gacha))
            elif qaysi == "ulush":
                yol = (reports.shaxsiy_ulush_html(self.db, dan, gacha, odam_id)
                       if tur == "html" else
                       reports.shaxsiy_ulush_excel(self.db, dan, gacha,
                                                   odam_id))
            else:
                yol = (reports.vazifa_html(self.db, dan, gacha, odam_id)
                       if tur == "html" else
                       reports.vazifa_excel(self.db, dan, gacha, odam_id))
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.xulosa.setText(f"Saqlandi: {yol}")
        och(yol)

    def _surish(self):
        """Excel B13: kun o'tkazib yuborilsa, qolgan hamma ish suriladi."""
        kun = self._kunlar()[0] if self.korinish else self.joriy.replace(day=1)
        odam_id = self.odam.odam_id()
        qatorlar = vz.surilganlar(self.db, kun, odam_id)
        if not qatorlar:
            self.xulosa.setText(
                f"{kun.strftime('%d.%m.%Y')} dan keyin suriladigan "
                f"bajarilmagan vazifa yo'q.")
            return
        korsat = "\n".join(
            f"  • {vz._sana(r['sana']).strftime('%d.%m')} "
            f"{r['vaqt'] or '—'}  {r['nom']} ({r['odam']})"
            for r in qatorlar[:10])
        if len(qatorlar) > 10:
            korsat += f"\n  • … yana {len(qatorlar) - 10} ta"
        kim = "" if not odam_id else f" ({self.odam.currentText()})"
        if not tasdiq(self, f"{kun.strftime('%d.%m.%Y')} dan boshlab "
                            f"{len(qatorlar)} ta bajarilmagan vazifa"
                            f"{kim} bir kunga suriladi:\n\n{korsat}\n\n"
                            f"Davom etilsinmi?"):
            return
        try:
            vz.surish(self.db, kun, odam_id, 1)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    # ── yangilash ───────────────────────────────────────────────────

    def _kunlar(self) -> list[date]:
        if self.korinish == 1:
            return [self.joriy]
        return vz.hafta_kunlari(self.joriy)

    def yangila(self):
        odam_id = self.odam.odam_id()
        if self.korinish == 0:
            oy_boshi = self.joriy.replace(day=1)
            bosh = vz.hafta_boshi(oy_boshi)
            qatorlar = vz.oraliq(self.db, bosh, bosh + timedelta(days=41),
                                 odam_id, shaxsiysiz=True)
            self.oy_taqvim.qoy(oy_boshi, qatorlar)
            self.taqvim.hide()
            self.oy_taqvim.show()
            self.oraliq_yorliq.setText(oy_boshi.strftime("%B %Y"))
            dan, gacha = oy_boshi, bosh + timedelta(days=41)
        else:
            kunlar = self._kunlar()
            qatorlar = vz.oraliq(self.db, kunlar[0], kunlar[-1], odam_id,
                                 shaxsiysiz=True)
            self.taqvim.qoy(kunlar, qatorlar)
            self.oy_taqvim.hide()
            self.taqvim.show()
            if len(kunlar) == 1:
                self.oraliq_yorliq.setText(
                    f"{kunlar[0].strftime('%d.%m.%Y')}, "
                    f"{vz.KUNLAR[kunlar[0].weekday()].lower()}")
            else:
                self.oraliq_yorliq.setText(
                    f"{kunlar[0].strftime('%d.%m')} — "
                    f"{kunlar[-1].strftime('%d.%m.%Y')}")
            dan, gacha = kunlar[0], kunlar[-1]

        s = vz.sanoq(self.db, dan, gacha, odam_id, shaxsiysiz=True)
        qismlar = [f"{s['jami']} ta vazifa",
                   f"{s['bajarildi']} bajarildi",
                   f"{s['ochiq']} qoldi"]
        if s["kechikkan"]:
            qismlar.append(f"{s['kechikkan']} kechikkan")
        self.xulosa.setText("  ·  ".join(qismlar))


# ═════════════════════════════════════════════════════ shaxsiy varaq

class ShaxsiyVazifaSahifa(QWidget):
    """Bitta odamning o'z kalendari.

    Excel: «Shaxsma shaxs achchotlar — haftalik faqat o'zini
    vazifalarini ko'radi». Shuning uchun bu yerda «Hammasi» varianti
    YO'Q: sahifa har doim aniq bitta odamniki.
    """

    def __init__(self, oyna):
        super().__init__()
        self.oyna = oyna
        self.db = oyna.db
        self.joriy = date.today()

        tashqi = QVBoxLayout(self)
        tashqi.setContentsMargins(24, 20, 24, 20)
        tashqi.setSpacing(14)

        self.kim = OdamTanla(self.db)
        self.kim.currentIndexChanged.connect(self.yangila)
        qosh_t = tugma("+ Shu odamga vazifa", asosiy=True)
        qosh_t.clicked.connect(self._yangi)
        # Hisobot bu yerda YO'Q: hammasi «Kalendar» varag'ida, bitta
        # tanlagich ostida. Ikki joyda turganda qaysi biri nimani
        # chiqarishi bilinmasdi va ikkalasini birga o'zgartirish
        # kerak bo'lardi.
        tashqi.addWidget(qator(sarlavha("Shaxsiy"), self.kim, None, qosh_t))

        oldingi = tugma("‹")
        keyingi = tugma("›")
        bugun_t = tugma("Bugun")
        oldingi.setMaximumWidth(38)
        keyingi.setMaximumWidth(38)
        oldingi.clicked.connect(lambda: self._sur(-1))
        keyingi.clicked.connect(lambda: self._sur(1))
        bugun_t.clicked.connect(self._bugunga)
        self.oraliq_yorliq = bolim("")
        surish_t = tugma("Shu odamning kunini surish →")
        surish_t.setToolTip(
            "Shu kundan boshlab FAQAT shu odamning bajarilmagan "
            "vazifalari bir kunga suriladi.")
        surish_t.clicked.connect(self._surish)
        tashqi.addWidget(qator(oldingi, keyingi, bugun_t, self.oraliq_yorliq,
                               None, surish_t))

        # ── sanoq kartalari
        kartalar = QWidget()
        shaffof(kartalar)
        kq = QHBoxLayout(kartalar)
        kq.setContentsMargins(0, 0, 0, 0)
        kq.setSpacing(14)
        self.k_jami = RaqamKarta("Shu hafta", 0, "vazifa")
        self.k_bajarildi = RaqamKarta("Bajarildi", 0, "")
        self.k_qoldi = RaqamKarta("Qoldi", 0, "")
        self.k_kechikkan = RaqamKarta("Kechikkan", 0, "")
        for k in (self.k_jami, self.k_bajarildi, self.k_qoldi,
                  self.k_kechikkan):
            kq.addWidget(k)
        kq.addStretch(1)
        tashqi.addWidget(kartalar)

        # ── o'z kalendari
        self.taqvim = HaftaTaqvim()
        self.taqvim.setMinimumHeight(420)
        self.taqvim.vazifa_bosildi.connect(self._tafsilot)
        self.taqvim.bosh_joy_bosildi.connect(self._yangi_vaqtda)
        tashqi.addWidget(self.taqvim, 1)

        # ── ro'yxat: kalendarda ko'rinmaydigan tafsilot shu yerda
        karta = Karta("Shu haftadagi vazifalari")
        self.jadval = Jadval(["Kun", "Vaqt", "Vazifa", "Holati"])
        self.jadval.kengliklar(190, 90, 0, 130)
        self.jadval.setMinimumHeight(140)
        self.jadval.setMaximumHeight(210)
        self.jadval.doubleClicked.connect(self._jadvaldan)
        karta.qosh(self.jadval)
        tashqi.addWidget(karta)

        self.yangila()

    # ── boshqaruv ───────────────────────────────────────────────────

    def _sur(self, yon: int):
        self.joriy += timedelta(days=yon * 7)
        self.yangila()

    def _bugunga(self):
        self.joriy = date.today()
        self.yangila()

    def _yangi(self, kun=None, vaqt=None):
        d = VazifaDialog(self.db, sana=(kun or self.joriy).isoformat(),
                         parent=self)
        if self.kim.odam_id():
            d.odam.tanla(self.kim.odam_id())
        if vaqt:
            d.vaqt.setTime(QTime.fromString(vaqt, "HH:mm"))
        elif kun is not None:
            d.vaqtsiz.setChecked(True)
        if d.exec():
            self.oyna.yangila()

    def _yangi_vaqtda(self, kun, vaqt):
        self._yangi(kun, vaqt)

    def _tafsilot(self, vazifa_id: int):
        d = VazifaTafsilot(self.db, vazifa_id, parent=self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()

    def _jadvaldan(self):
        vid = self.jadval.tanlangan_id()
        if vid:
            self._tafsilot(vid)

    def _surish(self):
        odam_id = self.kim.odam_id()
        if not odam_id:
            return
        kun = vz.hafta_kunlari(self.joriy)[0]
        qatorlar = vz.surilganlar(self.db, kun, odam_id)
        if not qatorlar:
            return
        korsat = "\n".join(
            f"  • {vz._sana(r['sana']).strftime('%d.%m')} "
            f"{r['vaqt'] or '—'}  {r['nom']}" for r in qatorlar[:10])
        if len(qatorlar) > 10:
            korsat += f"\n  • … yana {len(qatorlar) - 10} ta"
        if not tasdiq(self, f"{self.kim.currentText()}ning "
                            f"{kun.strftime('%d.%m.%Y')} dan keyingi "
                            f"{len(qatorlar)} ta bajarilmagan vazifasi "
                            f"bir kunga suriladi:\n\n{korsat}\n\n"
                            f"Davom etilsinmi?"):
            return
        try:
            vz.surish(self.db, kun, odam_id, 1)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    # ── yangilash ───────────────────────────────────────────────────

    def yangila(self):
        # Ro'yxatni qayta to'ldirish `currentIndexChanged` ni uyg'otadi,
        # u esa yana shu funksiyani chaqiradi — signalni to'smasak,
        # cheksiz rekursiya bo'ladi.
        with QSignalBlocker(self.kim):
            self.kim.yangila()
        odam_id = self.kim.odam_id()
        kunlar = vz.hafta_kunlari(self.joriy)
        self.oraliq_yorliq.setText(
            f"{kunlar[0].strftime('%d.%m')} — "
            f"{kunlar[-1].strftime('%d.%m.%Y')}")

        if not odam_id:
            self.taqvim.qoy(kunlar, [])
            self.jadval.tuldir([], [])
            for k in (self.k_jami, self.k_bajarildi, self.k_qoldi,
                      self.k_kechikkan):
                k.qoy(0)
            return

        qatorlar = vz.oraliq(self.db, kunlar[0], kunlar[-1], odam_id)
        self.taqvim.qoy(kunlar, qatorlar)

        bugun = date.today()
        satrlar, idlar = [], []
        for r in qatorlar:
            kun = vz._sana(r["sana"])
            if r["holat"] == vz.BAJARILDI:
                holat = "✓ Bajarildi"
            elif kun < bugun:
                holat = "⏳ Kechikkan"
            else:
                holat = "Kutilmoqda"
            satrlar.append([
                f"{vz.KUNLAR[kun.weekday()]}, {kun.strftime('%d.%m')}",
                r["vaqt"] or "—", r["nom"], holat])
            idlar.append(r["id"])
        self.jadval.tuldir(satrlar, idlar)

        s = vz.sanoq(self.db, kunlar[0], kunlar[-1], odam_id)
        self.k_jami.qoy(s["jami"], "vazifa")
        self.k_bajarildi.qoy(s["bajarildi"], "")
        self.k_qoldi.qoy(s["ochiq"], "")
        self.k_kechikkan.qoy(s["kechikkan"], "")
        self.k_bajarildi.izoh_holati(
            "qaytadi" if s["bajarildi"] and s["bajarildi"] == s["jami"]
            else None)
        self.k_kechikkan.izoh_holati("berasan" if s["kechikkan"] else "tinch")


# ═══════════════════════════════════════════════════ vazifa turlari

def _tg_html(matn: str) -> str:
    """Telegram HTML → Qt yorlig'i uchun.

    Teglar (`<b>`, `<i>`) ikkalasida ham bir xil, farqi faqat qator
    ko'chirishda: Telegram `\n` ni ko'chirish deb biladi, Qt esa
    `<br>` kutadi.
    """
    return (matn or "").replace("\n", "<br>")


class _QadamQator(QFrame):
    """Ish ichidagi bitta mayda qadam."""

    ochir = Signal(int)

    def __init__(self, qadam, parent=None):
        super().__init__(parent)
        self.setObjectName("QadamQator")
        self.setStyleSheet(
            f"QFrame#QadamQator {{ background: transparent;"
            f" border: none; }}")
        ich = QHBoxLayout(self)
        ich.setContentsMargins(0, 0, 0, 0)
        ich.setSpacing(8)

        nom = QLabel(f"•  {qadam['nom']}")
        nom.setStyleSheet(
            f"color:{theme.MATN_2};background:transparent;"
            f"font-size:{theme.O_KICHIK}px;")
        ich.addWidget(nom, 1)

        o = tugma("✕", xavfli=True)
        o.setMaximumWidth(32)
        o.setMinimumHeight(26)
        o.setToolTip("Qadamni olib tashlash")
        o.clicked.connect(lambda: self.ochir.emit(qadam["id"]))
        ich.addWidget(o)


class _TurQator(QFrame):
    """Ro'yxatdagi bitta ish nomi + amallari.

    Ikki qavat: tepada ishning o'zi, ostida qadamlari. Qadamlar paneli
    HAR DOIM quriladi, faqat yopiq turadi — ochish/yopish shu qatorning
    ichida hal bo'ladi va butun ro'yxatni qayta qurmaydi.

    Nega muhim: avval «Qadamlar» tugmasi `yangila()` ni chaqirardi,
    ya'ni sakkizta qator o'chirilib qaytadan yasalardi. Ko'zga bu
    sahifaning sakrashi bo'lib ko'rinadi — bosilgan tugma ham o'rnidan
    qo'zg'aladi. Endi faqat panel ochiladi, qolgani joyida qoladi.
    """

    biriktir = Signal(int)
    ochir = Signal(int)
    ergash_ozgardi = Signal(int, object)   # (tur_id, ergash_turi_id|None)
    qadam_qosh = Signal(int, str)          # (tur_id, qadam nomi)
    qadam_ochir = Signal(int)              # qadam id
    shaxsiy_ozgardi = Signal(int, bool)    # (tur_id, shaxsiymi)
    xabar_korsat = Signal(int)             # tur_id
    ochildi = Signal(int, bool)            # (tur_id, ochiqmi)

    # Ochilish/yopilish tezligi. 190 ms — ko'z harakatni ILG'AYDI,
    # lekin kutib turmaydi. 100 dan past bo'lsa «sakradi» deb
    # tuyuladi, 300 dan yuqorisi sekin ko'rinadi.
    ANIM_MS = 190

    def __init__(self, tur, hamma_turlar=(), qadamlar=(), ochiq=False,
                 parent=None):
        super().__init__(parent)
        self.tur_id = tur["id"]
        self._ochiq = bool(ochiq)
        self._animatsiyada = False
        self._anim = None
        # Yopiq holatdagi balandlik — birinchi joylashuvda o'lchanadi.
        self._yopiq_h = 0
        self.setObjectName("TurQator")
        self.setStyleSheet(
            f"QFrame#TurQator {{ background: {theme.KARTA_ICH};"
            f" border: 1px solid {theme.CHIZIQ_OCH};"
            f" border-radius: {theme.R_KICHIK}px; }}")

        tashqi = QVBoxLayout(self)
        tashqi.setContentsMargins(14, 8, 10, 8)
        tashqi.setSpacing(8)

        bosh = self.bosh = QWidget()
        shaffof(bosh)
        ich = QHBoxLayout(bosh)
        ich.setContentsMargins(0, 0, 0, 0)
        ich.setSpacing(10)
        tashqi.addWidget(bosh)

        nom = self.nom = QLabel(tur["nom"])
        nom.setWordWrap(True)
        nom.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-size:{theme.O_ASOS}px;font-weight:600;")
        ich.addWidget(nom, 1)

        # Shaxsiy / umumiy. Shaxsiy ish guruhga E'LON QILINMAYDI —
        # bot uni faqat egasiga yozadi. Bayroq `shaxsiy` ustunida.
        self._shaxsiymi = bool(tur["shaxsiy"])
        self.shaxsiy_tugma = tugma("")
        self.shaxsiy_tugma.setMinimumWidth(112)
        self._shaxsiy_korinish()
        self.shaxsiy_tugma.clicked.connect(
            lambda: self.shaxsiy_ozgardi.emit(self.tur_id,
                                              not self._shaxsiymi))
        ich.addWidget(self.shaxsiy_tugma)

        # General uborka belgisi. Ustundan (`haftalik`) keladi, nomdan
        # emas — foydalanuvchi ish nomini o'zgartirsa belgi qolaveradi.
        if tur["haftalik"]:
            nishon = QLabel("general uborka")
            nishon.setStyleSheet(
                f"color:{theme.KOK_TUQ};background:{theme.KOK_FON};"
                f"border-radius:{theme.R_ORTA}px;padding:2px 9px;"
                f"font-size:{theme.O_MIKRO}px;font-weight:700;")
            nishon.setToolTip(
                "Bu ish haftada bir marta qilinadi va har hafta "
                "keyingi odamga o'tadi.")
            ich.addWidget(nishon)

        uzunlik = QLabel(f"{tur['davomiylik']} daqiqa")
        uzunlik.setStyleSheet(
            f"color:{theme.KUL};background:transparent;"
            f"font-size:{theme.O_MAYDA}px;")
        ich.addWidget(uzunlik)

        # Navbatli ish (ovqat): undan keyin AVVALGI navbatchi nima
        # qilishini shu yerda tanlanadi. Nomga qarab taxmin qilmaymiz —
        # foydalanuvchi ish nomini o'zgartirsa taxmin buziladi.
        if tur["navbat"]:
            yorliqcha = QLabel("keyin:")
            yorliqcha.setStyleSheet(
                f"color:{theme.KUL};background:transparent;"
                f"font-size:{theme.O_MAYDA}px;")
            ich.addWidget(yorliqcha)
            self.ergash = QComboBox()
            self.ergash.setMinimumWidth(190)
            self.ergash.addItem("— yo'q —", None)
            for x in hamma_turlar:
                if x["id"] != tur["id"]:
                    self.ergash.addItem(x["nom"], x["id"])
            i = self.ergash.findData(tur["ergash_turi_id"])
            self.ergash.setCurrentIndex(i if i >= 0 else 0)
            self.ergash.setToolTip(
                "Ovqatdan keyin idishni avvalgi navbatchi yuvadi. "
                "Qaysi ish ekanini shu yerda tanlang.")
            self.ergash.currentIndexChanged.connect(
                lambda: self.ergash_ozgardi.emit(self.tur_id,
                                                 self.ergash.currentData()))
            ich.addWidget(self.ergash)

        self.xabar_tugma = tugma("🔔")
        self.xabar_tugma.setMaximumWidth(46)
        self.xabar_tugma.setToolTip(
            "Bu ish guruhga qachon va qanday yoziladi — "
            "matni bilan ko'rsatadi, shu yerdan o'zgartiriladi.")
        self.xabar_tugma.clicked.connect(
            lambda: self.xabar_korsat.emit(self.tur_id))
        ich.addWidget(self.xabar_tugma)

        self.qadam_tugma = tugma("")
        self.qadam_tugma.setMinimumWidth(132)
        self.qadam_tugma.setToolTip(
            "Ish ichidagi mayda ishlar. Guruhga ketadigan xabarda "
            "ro'yxat bo'lib chiqadi.")
        self.qadam_tugma.clicked.connect(self.almashtir)
        ich.addWidget(self.qadam_tugma)

        b = tugma("Biriktirish", asosiy=True)
        b.clicked.connect(lambda: self.biriktir.emit(self.tur_id))
        ich.addWidget(b)

        o = tugma("✕", xavfli=True)
        o.setMaximumWidth(40)
        o.setToolTip("Ro'yxatdan olib tashlash")
        o.clicked.connect(lambda: self.ochir.emit(self.tur_id))
        ich.addWidget(o)

        # ── qadamlar paneli: har doim bor, boshida yopiq
        self.panel = QWidget()
        shaffof(self.panel)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(6, 4, 0, 2)
        self.panel_layout.setSpacing(6)
        tashqi.addWidget(self.panel)
        self.panel.setVisible(self._ochiq)
        self.qadamlarni_qoy(qadamlar)

    # ── ko'rinish ───────────────────────────────────────────────────

    def _shaxsiy_korinish(self):
        self.shaxsiy_tugma.setText(
            "🔒 Shaxsiy" if self._shaxsiymi else "👥 Umumiy")
        self.shaxsiy_tugma.setToolTip(
            "Shaxsiy ish guruhga chiqmaydi: bot uni faqat egasining "
            "o'ziga yozadi.\nBosib umumiy qiling."
            if self._shaxsiymi else
            "Umumiy ish guruhga e'lon qilinadi — hamma ko'radi.\n"
            "Bosib shaxsiy qiling: u faqat egasiga yoziladi.")

    def shaxsiyni_qoy(self, shaxsiymi: bool):
        """Bayroq o'zgardi — faqat shu tugma yangilanadi.

        Butun sahifani qayta qurish shart emas: o'zgargani shu
        tugmaning yozuvi, xolos.
        """
        self._shaxsiymi = bool(shaxsiymi)
        self._shaxsiy_korinish()

    def qadamlarni_qoy(self, qadamlar):
        """Panelni qaytadan to'ldiradi — faqat SHU qatorniki."""
        while self.panel_layout.count():
            x = self.panel_layout.takeAt(0)
            w = x.widget()
            yoq(w)

        if not qadamlar:
            bosh_matn = QLabel("Qadam yo'q — pastdan qo'shing.")
            bosh_matn.setStyleSheet(
                f"color:{theme.KUL};background:transparent;"
                f"font-size:{theme.O_MAYDA}px;")
            self.panel_layout.addWidget(bosh_matn)
        for q in qadamlar:
            qq = _QadamQator(q)
            qq.ochir.connect(self.qadam_ochir)
            self.panel_layout.addWidget(qq)

        self.maydon = QLineEdit()
        self.maydon.setPlaceholderText("Yangi qadam")
        qosh_tugma = tugma("+ Qo'shish")

        def _qosh():
            matn = self.maydon.text().strip()
            if matn:
                self.qadam_qosh.emit(self.tur_id, matn)

        self.maydon.returnPressed.connect(_qosh)
        qosh_tugma.clicked.connect(_qosh)
        self.panel_layout.addWidget(qator(self.maydon, qosh_tugma))

        self.qadam_tugma.setText(
            f"Qadamlar ({len(qadamlar)}) {'▾' if self._ochiq else '▸'}")
        if self._ochiq:
            # Panel o'sdi yoki qisqardi — qator balandligi ergashsin.
            self.setMinimumHeight(self._kerakli(True))
            self.setMaximumHeight(16777215)

    # ── ochish / yopish ─────────────────────────────────────────────
    #
    # Balandlik `maximumHeight` bo'ylab suriladi: bola widgetlar ota
    # widgetning chegarasidan tashqarida chizilmaydi, shuning uchun
    # panel pastdan ochilib chiqayotgandek ko'rinadi.
    #
    # Animatsiya paytida `resizeEvent` dagi o'lchov TO'XTATILADI
    # (`_animatsiyada`): aks holda u har kadrda eng kam balandlikni
    # qayta qo'yib, animatsiyani birinchi kadrdayoq oxiriga tashlaydi.

    def _kerakli(self, ochiq: bool) -> int:
        """Ochiq yoki yopiq holatdagi balandlik.

        Yopiq balandlik `sizeHint()` dan OLINMAYDI: panel hali
        ko'rinib turgan paytda u panelni ham qo'shib yuboradi va
        yopilish maqsadi joriy balandlikka teng bo'lib qoladi — ya'ni
        hech narsa qimirlamaydi. Shuning uchun u qator yopiq turganda
        o'lchanadi va `_yopiq_h` da saqlanadi.
        """
        m = self.layout().contentsMargins()
        yopiq = self._yopiq_h or (self.bosh.sizeHint().height()
                                  + m.top() + m.bottom())
        if not ochiq:
            return yopiq
        return yopiq + self.layout().spacing() + self.panel.sizeHint().height()

    def almashtir(self):
        self.ochiqni_qoy(not self._ochiq)
        self.ochildi.emit(self.tur_id, self._ochiq)

    def _animni_tuxtat(self):
        """Ketayotgan animatsiyani to'xtatadi.

        `finished` avval uziladi: to'xtatish ham uni qo'zg'atishi
        mumkin, va o'shanda tugatuvchi eski MAQSAD balandlikni qo'yib,
        yangi harakatni birinchi kadrdayoq bekor qilardi.
        """
        if self._anim is None:
            return
        try:
            self._anim.finished.disconnect()
        except (TypeError, RuntimeError):
            pass
        self._anim.stop()
        self._anim = None
        self._animatsiyada = False

    def ochiqni_qoy(self, ochiq: bool, animatsiya: bool = True):
        ochiq = bool(ochiq)
        # Yarim yo'lda qayta bosilsa harakat ORQAGA qaytadi, bosilish
        # e'tiborsiz qolmaydi: tugma «ishlamadi» degan tuyg'u
        # bermasligi kerak.
        self._animni_tuxtat()
        if ochiq == self._ochiq and self.panel.isVisibleTo(self) == ochiq:
            return
        self._ochiq = ochiq
        self.qadam_tugma.setText(
            f"Qadamlar ({max(0, self.panel_layout.count() - 2)})"
            f" {'▾' if ochiq else '▸'}")
        boshi = self.height()
        if ochiq:
            self.panel.setVisible(True)
        oxiri = self._kerakli(ochiq)

        if not animatsiya:
            self.panel.setVisible(ochiq)
            self.setMinimumHeight(oxiri)
            self.setMaximumHeight(16777215)
            return

        self._animatsiyada = True
        self.setMinimumHeight(min(boshi, oxiri))
        a = QPropertyAnimation(self, b"maximumHeight", self)
        # Qolgan masofaga qarab: yarim yo'ldan qaytganda to'liq 190 ms
        # sarflash sekin ko'rinadi.
        toliq = max(1, abs(self._kerakli(True) - self._kerakli(False)))
        ulush = min(1.0, abs(oxiri - boshi) / toliq)
        a.setDuration(max(70, int(self.ANIM_MS * ulush)))
        # InOutCubic — boshida ham, oxirida ham sekinlashadi: harakat
        # tortib-uzilgandek emas, tabiiy ko'rinadi.
        a.setEasingCurve(QEasingCurve.InOutCubic)
        a.setStartValue(boshi)
        a.setEndValue(oxiri)
        a.finished.connect(lambda: self._tugadi(ochiq, oxiri))
        self._anim = a
        a.start()

    def _tugadi(self, ochiq: bool, balandlik: int):
        self._animatsiyada = False
        self._anim = None
        self.panel.setVisible(ochiq)
        self.setMinimumHeight(balandlik)
        self.setMaximumHeight(16777215)

    # ── balandlik ───────────────────────────────────────────────────
    #
    # «Sig'maydi» muammosining ildizi: qator o'z `sizeHint` ini
    # to'g'ri aytadi (uzun nom ikki qatorga chiqsa 80 piksel), lekin
    # ENG KAM o'lchami baribir bir qatorlik bo'lib qoladi. Karta esa
    # eng kam o'lchamga qarab siqiladi — natijada matn qirqilib,
    # keyingi qatorning ustiga chiqadi.
    #
    # Shuning uchun qatorning eng kam balandligi o'z `sizeHint` iga
    # tenglashtiriladi: bu chegara kartadan aylantirgichgacha o'zi
    # ko'tariladi va sahifa siqilish o'rniga aylanadi.

    def resizeEvent(self, hodisa):
        super().resizeEvent(hodisa)
        if self._animatsiyada:
            return
        kerak = self.sizeHint().height()
        if kerak > 0 and kerak != self.minimumHeight():
            self.setMinimumHeight(kerak)
        # Panel yopiq bo'lgan paytdagi o'lcham — yopilish maqsadi
        # o'shanga qaytadi. Uzun nom ikki qatorga chiqqan bo'lsa bu
        # yerda allaqachon hisobga olingan.
        if not self._ochiq and kerak > 0:
            self._yopiq_h = kerak


class _StreakQator(QFrame):
    """Bitta odat: kim, qaysi ish, va nechta kun ketma-ket."""

    ochir = Signal(int)

    def __init__(self, holat, parent=None):
        super().__init__(parent)
        self.streak_id = holat["id"]
        self.setObjectName("TurQator")
        tugadi = holat["bajarildi"]
        self.setStyleSheet(
            f"QFrame#TurQator {{"
            f" background: {theme.YASHIL_FON if tugadi else theme.KARTA_ICH};"
            f" border: 1px solid "
            f"{theme.YASHIL if tugadi else theme.CHIZIQ_OCH};"
            f" border-radius: {theme.R_KICHIK}px; }}")

        ich = QHBoxLayout(self)
        ich.setContentsMargins(14, 8, 10, 8)
        ich.setSpacing(10)

        nom = QLabel(f"{holat['odam']} · {holat['ish']}")
        nom.setWordWrap(True)
        nom.setStyleSheet(
            f"color:{theme.YASHIL_TUQ if tugadi else theme.MATN};"
            f"background:transparent;font-size:{theme.O_ASOS}px;"
            f"font-weight:600;")
        ich.addWidget(nom, 1)

        # Chiziqcha o'rniga kvadratchalar: «yigirma birdan o'n to'rttasi»
        # degan gapni sanab ko'rish mumkin, foizni esa yo'q.
        n = holat["nishon"]
        toldi = min(n, holat["kun"])
        chiziq = QLabel("▪" * toldi + "▫" * (n - toldi))
        chiziq.setStyleSheet(
            f"color:{theme.YASHIL if tugadi else theme.KOK};"
            f"background:transparent;font-size:{theme.O_ASOS}px;"
            f"letter-spacing:1px;")
        ich.addWidget(chiziq)

        sanoq = QLabel(f"{holat['kun']}/{n}")
        sanoq.setStyleSheet(
            f"color:{theme.YASHIL if tugadi else theme.KUL};"
            f"background:transparent;font-size:{theme.O_ASOS}px;"
            f"font-weight:700;")
        ich.addWidget(sanoq)

        if tugadi:
            nishon = QLabel(f"🏅 {vz.YUTUQ_IRODA}")
            nishon.setStyleSheet(
                f"color:{theme.YASHIL_TUQ};background:{theme.KARTA};"
                f"border-radius:{theme.R_ORTA}px;padding:2px 9px;"
                f"font-size:{theme.O_MIKRO}px;font-weight:700;")
            ich.addWidget(nishon)
        else:
            qoldi = QLabel(f"{holat['qoldi']} kun qoldi")
            qoldi.setStyleSheet(
                f"color:{theme.KUL};background:transparent;"
                f"font-size:{theme.O_MAYDA}px;")
            ich.addWidget(qoldi)

        o = tugma("✕", xavfli=True)
        o.setMaximumWidth(40)
        o.setToolTip("Odatni to'xtatish")
        o.clicked.connect(lambda: self.ochir.emit(self.streak_id))
        ich.addWidget(o)


class _TaomQator(QFrame):
    """Menyudagi bitta taom."""

    ochir = Signal(int)

    def __init__(self, taom, parent=None):
        super().__init__(parent)
        self.taom_id = taom["id"]
        self.setObjectName("TurQator")
        self.setStyleSheet(
            f"QFrame#TurQator {{ background: {theme.KARTA_ICH};"
            f" border: 1px solid {theme.CHIZIQ_OCH};"
            f" border-radius: {theme.R_KICHIK}px; }}")

        ich = QHBoxLayout(self)
        ich.setContentsMargins(14, 6, 10, 6)
        ich.setSpacing(10)

        nom = QLabel(f"🍲 {taom['nom']}")
        nom.setWordWrap(True)
        nom.setStyleSheet(
            f"color:{theme.MATN};background:transparent;"
            f"font-size:{theme.O_ASOS}px;font-weight:600;")
        ich.addWidget(nom, 1)

        o = tugma("✕", xavfli=True)
        o.setMaximumWidth(40)
        o.setToolTip("Menyudan olib tashlash")
        o.clicked.connect(lambda: self.ochir.emit(self.taom_id))
        ich.addWidget(o)


class VazifaTurlariSahifa(Sahifa):
    """Uy ishlarining ro'yxati — kalendar EMAS.

    Excel B16: «Vazifalarga shu topshiriqlarni qo'shish» + C17:C21.
    Bu yerda kun ham, vaqt ham yo'q: shunchaki qaysi ishlar bor.
    «Biriktirish» bosilganda kim/qachon so'raladi va ish kalendarga
    tushadi.

    `Sahifa` dan meros — ya'ni AYLANTIRGICH ichida. Oddiy `QWidget`
    bo'lganda ro'yxat oyna balandligiga siqilib, qatorlar bir-birining
    ustiga chiqib ketardi: ish turi qancha ko'p bo'lsa shuncha yomon.
    """

    def __init__(self, oyna):
        super().__init__(oyna)
        # Qaysi ishning qadamlari ochiq. Sahifa har `yangila()` da
        # qaytadan quriladi, shuning uchun holat SAHIFADA saqlanadi —
        # aks holda qadam qo'shilishi bilan panel yopilib qolardi.
        self._ochiq: set[int] = set()
        # Qurilgan qatorlar: mayda o'zgarish (qadam qo'shildi, shaxsiy
        # bayrog'i almashdi) butun ro'yxatni emas, FAQAT shu qatorni
        # yangilaydi — aks holda bosilgan tugma o'rnidan qo'zg'aladi
        # va sahifa sakragandek ko'rinadi.
        self._qatorlar: dict = {}

        yangi = tugma("+ Yangi vazifa turi", asosiy=True)
        yangi.clicked.connect(self._yangi_tur)
        self.tana.addWidget(qator(sarlavha("Vazifalar"), None, yangi))
        self.tana.addWidget(izoh(
            "«Biriktirish» — ishni odamga, kunga va soatga bog'laydi. "
            "🔔 — qachon va qanday xabar ketishini ko'rsatadi."))

        self.karta = Karta("Ish turlari")
        self.royxat = QWidget()
        shaffof(self.royxat)
        self.royxat_layout = QVBoxLayout(self.royxat)
        self.royxat_layout.setContentsMargins(0, 0, 0, 0)
        self.royxat_layout.setSpacing(8)
        self.karta.qosh(self.royxat)
        self.tana.addWidget(self.karta)

        self.bosh_matn = izoh("")
        self.tana.addWidget(self.bosh_matn)

        self._uborka_kartasi()
        self._streak_kartasi()
        self._menyu_kartasi()
        self.tana.addStretch(1)

        self.yangila()

    # ── general uborka ──────────────────────────────────────────────
    #
    # Ovqat navbatidan boshqa narsa: bir nechta KATTA ish bir kunda,
    # har biri boshqa odamda, va har hafta hammasi bir odam oldinga
    # suriladi. Shuning uchun uning o'z kartasi bor — ovqat navbati
    # esa «Biriktirish» dialogida qoladi.

    # Soat va hafta soni ham TANLAGICH — `QTimeEdit`/`QSpinBox` emas.
    # Ular qatordagi yagona o'q-tugmali maydon bo'lib, qolganlariga
    # o'xshamay turardi; qiymatlar esa baribir sanoqli, ya'ni yozib
    # kiritishning hojati yo'q.
    SOATLAR = [f"{s:02d}:{d:02d}" for s in range(6, 24) for d in (0, 30)]
    HAFTALAR = [1, 2, 3, 4, 6, 8, 12, 16, 26]

    def _uborka_kartasi(self):
        self.uborka_karta = Karta("General uborka")

        self.uborka_kun = QComboBox()
        for i, nom in enumerate(vz.KUNLAR):
            self.uborka_kun.addItem(nom, i)
        self.uborka_vaqt = QComboBox()
        for v in self.SOATLAR:
            self.uborka_vaqt.addItem(v, v)
        self.uborka_odam = OdamTanla(self.db)
        self.uborka_sana = SanaEdit()
        self.uborka_hafta = QComboBox()
        for h in self.HAFTALAR:
            self.uborka_hafta.addItem(f"{h} hafta", h)

        self.uborka_karta.qosh(qator(
            "Kuni:", self.uborka_kun, "Soat:", self.uborka_vaqt,
            "Boshlaydi:", self.uborka_odam, None))
        self.uborka_karta.qosh(qator(
            "Sanadan:", self.uborka_sana,
            "Necha hafta:", self.uborka_hafta, None))

        tuz = tugma("Rejani tuzish", asosiy=True)
        tuz.clicked.connect(self._uborka_tuz)
        saqla = tugma("Kun va soatni saqlash")
        saqla.clicked.connect(self._uborka_saqla)
        self.uborka_karta.qosh(qator(saqla, None, tuz))

        self.uborka_oldin = izoh("")
        self.uborka_karta.qosh(self.uborka_oldin)
        self.tana.addWidget(self.uborka_karta)

    def _uborka_saqla(self):
        try:
            vz.uborka_kuni_qoy(self.db, self.uborka_kun.currentData())
            vz.uborka_vaqti_qoy(
                self.db, self.uborka_vaqt.currentData())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    def _uborka_reja(self):
        """Joriy tanlov bo'yicha reja. Xato bo'lsa — (None, xabar)."""
        try:
            return vz.uborka_rejasi(
                self.db,
                self.uborka_sana.iso(),
                self.uborka_odam.odam_id(),
                self.uborka_hafta.currentData(),
                self.uborka_vaqt.currentData()), ""
        except Exception as e:
            return None, str(e)

    def _uborka_tuz(self):
        reja, xato = self._uborka_reja()
        if reja is None:
            xato_koraset(self, xato)
            return
        birinchi = [x for x in reja if x["sana"] == reja[0]["sana"]]
        kimlar = "\n".join(f"   {x['odam']} — {x['nom']}" for x in birinchi)
        if not tasdiq(self, f"{len(reja)} ta vazifa yozilsinmi?\n\n"
                            f"Birinchi kun ({reja[0]['sana']}):\n{kimlar}"):
            return
        try:
            vz.uborka_biriktir(
                self.db, self.uborka_sana.iso(),
                self.uborka_odam.odam_id(), self.uborka_hafta.currentData(),
                self.uborka_vaqt.currentData())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    # ── odatlar (streak) ────────────────────────────────────────────
    #
    # Ketma-ket kunlar soni SAQLANMAYDI, har safar `vazifa` jadvalidan
    # qayta hisoblanadi (`vz.streak_kunlari`) — shuning uchun undo
    # bilan hech qachon ajralib qolmaydi.

    def _streak_kartasi(self):
        self.streak_karta = Karta("Odatlar")
        self.streak_odam = OdamTanla(self.db)
        self.streak_tur = QComboBox()
        self.streak_nishon = QComboBox()
        for n in vz.NISHONLAR:
            self.streak_nishon.addItem(f"{n} kun", n)
        bosh = tugma("Boshlash", asosiy=True)
        bosh.clicked.connect(self._streak_qosh)
        self.streak_karta.qosh(qator(
            "Kim:", self.streak_odam, "Qaysi ish:", self.streak_tur,
            "Nishon:", self.streak_nishon, None, bosh))

        self.streaklar_quti = QWidget()
        shaffof(self.streaklar_quti)
        self.streaklar_layout = QVBoxLayout(self.streaklar_quti)
        self.streaklar_layout.setContentsMargins(0, 0, 0, 0)
        self.streaklar_layout.setSpacing(8)
        self.streak_karta.qosh(self.streaklar_quti)

        self.yutuq_matn = izoh("")
        self.streak_karta.qosh(self.yutuq_matn)
        self.tana.addWidget(self.streak_karta)

    def _streak_qosh(self):
        try:
            vz.streak_qosh(self.db, self.streak_odam.odam_id(),
                           self.streak_tur.currentData(),
                           self.streak_nishon.currentData())
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.yangila()

    def _streak_ochir(self, streak_id: int):
        if not tasdiq(self, "Bu odat to'xtatilsinmi?\n\n"
                            "Qo'lga kiritilgan yutuq joyida qoladi."):
            return
        try:
            vz.streak_ochir(self.db, streak_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.yangila()

    def _streaklarni_chiz(self, turlar):
        self._bosal(self.streaklar_layout)
        with QSignalBlocker(self.streak_tur):
            joriy = self.streak_tur.currentData()
            self.streak_tur.clear()
            for t in turlar:
                self.streak_tur.addItem(t["nom"], t["id"])
            i = self.streak_tur.findData(joriy)
            if i >= 0:
                self.streak_tur.setCurrentIndex(i)
        with QSignalBlocker(self.streak_odam):
            self.streak_odam.yangila()

        royxat = vz.streaklar(self.db)
        for x in royxat:
            q = _StreakQator(vz.streak_holati(self.db, x))
            q.ochir.connect(self._streak_ochir)
            self.streaklar_layout.addWidget(q)
        if not royxat:
            self.streaklar_layout.addWidget(
                izoh("Hali odat belgilanmagan."))

        # Yutuq yo'q bo'lsa qator umuman KO'RSATILMAYDI: «hali yo'q»
        # degan yozuv har ochilganda ko'zga tashlanib turadi va
        # kartani bo'sh gap bilan to'ldiradi.
        y = vz.yutuqlar(self.db)
        self.yutuq_matn.setVisible(bool(y))
        if y:
            self.yutuq_matn.setText(
                "🏅 " + ",  ".join(
                    f"{x['odam']} — {x['nom']} ({x['nishon']} kun)"
                    for x in y[:6])
                + (f"  va yana {len(y) - 6} ta" if len(y) > 6 else ""))

    def _menyu_kartasi(self):
        # Taomlar KODDA emas, jadvalda: guruhdagi «Menyuyimizda nimalar
        # bor» tugmasi shu ro'yxatni ko'rsatadi, ya'ni yangi taom
        # qo'shish uchun dastur qayta qurilmaydi.
        self.menyu_karta = Karta("Menyu")
        self.taom_maydon = QLineEdit()
        self.taom_maydon.setPlaceholderText("Taom nomi")
        self.taom_maydon.returnPressed.connect(self._taom_qosh)
        t_qosh = tugma("+ Qo'shish", asosiy=True)
        t_qosh.clicked.connect(self._taom_qosh)
        self.menyu_karta.qosh(qator(self.taom_maydon, t_qosh))
        self.taomlar = QWidget()
        shaffof(self.taomlar)
        self.taomlar_layout = QVBoxLayout(self.taomlar)
        self.taomlar_layout.setContentsMargins(0, 0, 0, 0)
        self.taomlar_layout.setSpacing(8)
        self.menyu_karta.qosh(self.taomlar)
        self.menyu_karta.qosh(izoh(
            "Guruhda oshpaz «Menyuyimizda nimalar bor» tugmasini bosganda "
            "shu ro'yxat chiqadi. Tanlagani o'sha kungi vazifada "
            "«Menyu» bo'lib ko'rinadi."))
        self.tana.addWidget(self.menyu_karta)

    # ── amallar ─────────────────────────────────────────────────────

    def _yangi_tur(self):
        d = TurDialog(self.db, parent=self)
        if d.exec():
            self.oyna.yangila()

    def _biriktir(self, tur_id: int):
        tur = vz.tur_bitta(self.db, tur_id)
        if not tur:
            return
        d = VazifaDialog(self.db, sana=date.today().isoformat(), tur=tur,
                         parent=self)
        if d.exec():
            self.oyna.yangila()

    def _qadam_ochildi(self, tur_id: int, ochiqmi: bool):
        # Panelni qator O'ZI ochib-yopadi (animatsiya bilan). Bu yerda
        # faqat holat eslab qolinadi — sahifa keyin qayta qurilsa
        # panel o'sha holatda ochiladi.
        if ochiqmi:
            self._ochiq.add(tur_id)
        else:
            self._ochiq.discard(tur_id)

    def _qadam_qosh(self, tur_id: int, nom: str):
        try:
            vz.qadam_qosh(self.db, tur_id, nom)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self._ochiq.add(tur_id)
        self._qadamlarni_yangila(tur_id, fokus=True)

    def _xabar_korsat(self, tur_id: int):
        d = XabarDialog(self.db, tur_id, parent=self)
        if d.exec():
            self.oyna.yangila()

    def _shaxsiy_qoy(self, tur_id: int, shaxsiymi: bool):
        try:
            vz.tur_shaxsiy_qoy(self.db, tur_id, shaxsiymi)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        # O'zgargani shu tugmaning yozuvi, xolos.
        q = self._qatorlar.get(tur_id)
        if q is not None:
            q.shaxsiyni_qoy(shaxsiymi)
        else:
            self.yangila()

    def _qadam_ochir(self, qadam_id: int):
        q = self.db.q1("SELECT turi_id FROM ish_qadam WHERE id=?", qadam_id)
        try:
            vz.qadam_ochir(self.db, qadam_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self._qadamlarni_yangila(q["turi_id"] if q else None)

    def _qadamlarni_yangila(self, tur_id, fokus: bool = False):
        """Bitta ishning qadamlarini qayta chizadi.

        `oyna.yangila()` emas: u butun dasturni qayta quradi va panel
        ko'z oldida yopilib-ochilib ketadi. Qadam ro'yxatidan boshqa
        hech qayerda o'zgargan narsa yo'q.
        """
        qator_ = self._qatorlar.get(tur_id)
        if qator_ is None:
            self.yangila()
            return
        qator_.qadamlarni_qoy(vz.qadamlar(self.db, tur_id))
        # Fokus faqat QO'SHISHDAN keyin: ketma-ket qadam yozish qulay
        # bo'lsin. O'chirishdan keyin ko'chirilsa aylantirgich o'sha
        # maydonni ko'rsatish uchun sahifani sakratadi.
        if fokus:
            qator_.maydon.setFocus()

    def _taom_qosh(self):
        nom = self.taom_maydon.text().strip()
        if not nom:
            return
        try:
            mn.qosh(self.db, nom)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.taom_maydon.clear()
        self.oyna.yangila()

    def _taom_ochir(self, taom_id: int):
        t = mn.bitta(self.db, taom_id)
        if not t:
            return
        if not tasdiq(self, f"«{t['nom']}» menyudan olib tashlansinmi?"
                            f"\n\nAvval tanlangan kunlarda u yozuv "
                            f"bo'lib qoladi."):
            return
        try:
            mn.ochir(self.db, taom_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    def _ergash_qoy(self, tur_id: int, ergash_id):
        try:
            vz.tur_ergash_qoy(self.db, tur_id, ergash_id)
        except Exception as e:
            xato_koraset(self, str(e))
        self.oyna.yangila()

    def _ochir(self, tur_id: int):
        tur = vz.tur_bitta(self.db, tur_id)
        if not tur:
            return
        if not tasdiq(self, f"«{tur['nom']}» ro'yxatdan olib tashlansinmi?"
                            f"\n\nAllaqachon biriktirilgan vazifalar "
                            f"kalendarda qoladi."):
            return
        try:
            vz.tur_ochir(self.db, tur_id)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    # ── yangilash ───────────────────────────────────────────────────

    def _bosal(self, layout):
        while layout.count():
            x = layout.takeAt(0)
            w = x.widget()
            yoq(w)

    def yangila(self):
        self._bosal(self.royxat_layout)
        self._qatorlar = {}
        turlar = vz.turlar(self.db)
        for t in turlar:
            q = _TurQator(t, turlar, vz.qadamlar(self.db, t["id"]),
                          t["id"] in self._ochiq)
            self._qatorlar[t["id"]] = q
            q.biriktir.connect(self._biriktir)
            q.ochir.connect(self._ochir)
            q.ergash_ozgardi.connect(self._ergash_qoy)
            q.qadam_qosh.connect(self._qadam_qosh)
            q.qadam_ochir.connect(self._qadam_ochir)
            q.shaxsiy_ozgardi.connect(self._shaxsiy_qoy)
            q.xabar_korsat.connect(self._xabar_korsat)
            q.ochildi.connect(self._qadam_ochildi)
            self.royxat_layout.addWidget(q)
        if turlar:
            self.bosh_matn.setText(f"{len(turlar)} ta ish turi.")
        else:
            self.bosh_matn.setText(
                "Ro'yxat bo'sh — «+ Yangi vazifa turi» bilan qo'shing.")

        self._streaklarni_chiz(turlar)

        # ── general uborka
        # Tanlagichlar shu yerda to'ldiriladi, lekin ularning
        # signallari `yangila` ga ULANMAGAN — `sahifa_qosh.py` dagi
        # cheksiz rekursiya bu yerda takrorlanmasin.
        with QSignalBlocker(self.uborka_kun):
            i = self.uborka_kun.findData(vz.uborka_kuni(self.db))
            self.uborka_kun.setCurrentIndex(i if i >= 0 else 6)
        with QSignalBlocker(self.uborka_vaqt):
            i = self.uborka_vaqt.findData(vz.uborka_vaqti(self.db))
            # Saqlangan soat ro'yxatda bo'lmasa (qo'lda yozilgan yoki
            # yarim soatlik to'rga tushmaydigan) — o'sha zahoti
            # qo'shiladi, aks holda tanlov jimgina boshqa vaqtga
            # sakrab ketardi.
            if i < 0:
                self.uborka_vaqt.insertItem(0, vz.uborka_vaqti(self.db),
                                            vz.uborka_vaqti(self.db))
                i = 0
            self.uborka_vaqt.setCurrentIndex(i)
        with QSignalBlocker(self.uborka_odam):
            self.uborka_odam.yangila()
        # Sana faqat foydalanuvchi unga tegmagan bo'lsa yangilanadi:
        # aks holda u kiritayotgan paytda kursor ostidan o'zgarardi.
        if not self.uborka_sana.hasFocus():
            with QSignalBlocker(self.uborka_sana):
                self.uborka_sana.qoy(vz.uborka_sanasi(self.db).isoformat())
        reja, xato = self._uborka_reja()
        if reja is None:
            self.uborka_oldin.setText(xato)
        else:
            birinchi = [x for x in reja if x["sana"] == reja[0]["sana"]]
            self.uborka_oldin.setText(
                f"Birinchi kun ({reja[0]['sana']}): "
                + ",  ".join(f"{x['odam']} — {x['nom']}" for x in birinchi)
                + f".  Jami {len(reja)} ta vazifa.")

        self._bosal(self.taomlar_layout)
        for t in mn.royxat(self.db):
            q = _TaomQator(t)
            q.ochir.connect(self._taom_ochir)
            self.taomlar_layout.addWidget(q)


class TurDialog(QDialog):
    """Yangi ish turi: nomi va odatdagi davomiyligi."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Yangi vazifa turi")
        self.setMinimumWidth(400)

        tashqi = QVBoxLayout(self)
        forma = QFormLayout()
        forma.setSpacing(10)
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("Masalan: Kir yuvish")
        self.davomiylik = QSpinBox()
        self.davomiylik.setRange(5, 12 * 60)
        self.davomiylik.setSingleStep(15)
        self.davomiylik.setValue(60)
        self.davomiylik.setSuffix(" daqiqa")
        # Kimga ko'rinishi — SHU YERDA, keyin ro'yxatdan qidirib
        # emas: yangi ish qo'shayotgan odam «bu hammagami yoki
        # menikimi?» degan savolga o'sha zahoti javob beradi.
        self.kimga = QComboBox()
        self.kimga.addItem("👥 Umumiy — guruhga e'lon qilinadi", False)
        self.kimga.addItem("🔒 Shaxsiy — faqat egasiga yoziladi", True)
        forma.addRow("Nomi:", self.nom)
        forma.addRow("Odatda:", self.davomiylik)
        forma.addRow("Kimga:", self.kimga)
        tashqi.addLayout(forma)
        tashqi.addWidget(izoh(
            "Umumiy ish uy guruhiga tushadi — hamma ko'radi. "
            "Shaxsiy ish esa faqat egasiga, bot bilan shaxsiy "
            "suhbatda. Keyin ro'yxatdan ham o'zgartirsa bo'ladi."))

        t = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        t.button(QDialogButtonBox.Save).setText("Qo'shish")
        t.button(QDialogButtonBox.Cancel).setText("Bekor qilish")
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        tashqi.addWidget(t)

    def _saqla(self):
        try:
            vz.tur_qosh(self.db, self.nom.text(), self.davomiylik.value(),
                        bool(self.kimga.currentData()))
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()


class XabarDialog(QDialog):
    """«Bu ish guruhga qachon va qanday yoziladi?» — bitta karta.

    Matn HAQIQIY xabar funksiyalaridan quriladi (`xabar.tur_namunasi`),
    ya'ni bu yerda ko'ringan narsa aynan yuboriladi. Ko'rsatish uchun
    alohida matn yozilsa ikkalasi jimgina bir-biridan ajralib
    ketardi — shuning uchun bu yerda birorta ham qo'lda yozilgan
    xabar matni yo'q.

    Sozlamalar SHU YERDA o'zgaradi: karta savolni ham, javobini ham
    bir joyda beradi. Aks holda «xabar kech kelyapti» deb Sozlamalar
    varag'iga borib, u yerda qaysi ish ekanini eslab o'tirish kerak
    bo'lardi.
    """

    def __init__(self, db, tur_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.tur_id = tur_id
        self.setWindowTitle("Xabar")
        self.setMinimumWidth(620)

        tashqi = QVBoxLayout(self)
        tashqi.setSpacing(12)

        self.bosh = sarlavha("")
        tashqi.addWidget(self.bosh)
        self.holat = izoh("")
        tashqi.addWidget(self.holat)

        # ── sozlamalar
        forma = QFormLayout()
        forma.setSpacing(10)
        self.kim = OdamTanla(db)
        self.kim.currentIndexChanged.connect(self._yangila)
        self.vaqt = QTimeEdit(QTime(19, 0))
        self.vaqt.setDisplayFormat("HH:mm")
        self.vaqt.setToolTip("Namuna uchun: ish soat nechada biriktirilsa")
        self.vaqt.timeChanged.connect(self._yangila)
        self.davomiylik = QSpinBox()
        self.davomiylik.setRange(5, 12 * 60)
        self.davomiylik.setSingleStep(5)
        self.davomiylik.setSuffix(" daqiqa")
        self.davomiylik.setToolTip(
            "Eslatma ish vaqti TUGAGACH yuboriladi — ya'ni "
            "boshlanish + davomiylik.")
        self.kimga = QComboBox()
        self.kimga.addItem("👥 Umumiy — uy guruhiga", False)
        self.kimga.addItem("🔒 Shaxsiy — faqat egasiga", True)
        self.kunlik = QTimeEdit()
        self.kunlik.setDisplayFormat("HH:mm")
        self.kunlik.setToolTip("Kunlik ro'yxat soati — HAMMA ish uchun bitta")
        self.keyin = QLineEdit()
        self.keyin.setPlaceholderText("10, 30, 60")
        self.keyin.setToolTip(
            "«Hali yo'q» bosilganda taklif qilinadigan vaqtlar, "
            "daqiqada. Vergul bilan, ko'pi bilan to'rtta.")

        forma.addRow("Namuna kimga:", qator(self.kim, "soat:", self.vaqt))
        forma.addRow("Davomiyligi:", self.davomiylik)
        forma.addRow("Kimga boradi:", self.kimga)
        forma.addRow("Kunlik ro'yxat:", self.kunlik)
        forma.addRow("«Keyinroq»:", self.keyin)
        tashqi.addLayout(forma)

        # ── qachon
        self.qachon = Karta("Qachon yuboriladi")
        self.qachon_matn = izoh("")
        self.qachon.qosh(self.qachon_matn)
        tashqi.addWidget(self.qachon)

        # ── matnlar
        self.k_karta = Karta("Kunlik ro'yxatda")
        self.k_matn = QLabel()
        self.k_matn.setWordWrap(True)
        self.k_matn.setTextFormat(Qt.RichText)
        self.k_karta.qosh(self.k_matn)
        tashqi.addWidget(self.k_karta)

        self.e_karta = Karta("Vaqti tugagach")
        self.e_matn = QLabel()
        self.e_matn.setWordWrap(True)
        self.e_matn.setTextFormat(Qt.RichText)
        self.e_karta.qosh(self.e_matn)
        self.tugma_matn = izoh("")
        self.e_karta.qosh(self.tugma_matn)
        tashqi.addWidget(self.e_karta)

        t = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        t.button(QDialogButtonBox.Save).setText("Saqlash")
        t.button(QDialogButtonBox.Close).setText("Yopish")
        t.accepted.connect(self._saqla)
        t.rejected.connect(self.reject)
        tashqi.addWidget(t)

        self._yukla()

    # ── ma'lumot ────────────────────────────────────────────────────

    def _yukla(self):
        tur = vz.tur_bitta(self.db, self.tur_id)
        if not tur:
            self.reject()
            return
        with QSignalBlocker(self.davomiylik):
            self.davomiylik.setValue(tur["davomiylik"])
        with QSignalBlocker(self.kimga):
            self.kimga.setCurrentIndex(1 if tur["shaxsiy"] else 0)
        s = xabar.sozlamalar(self.db)
        with QSignalBlocker(self.kunlik):
            self.kunlik.setTime(
                QTime.fromString(s["kunlik_vaqt"], "HH:mm") or QTime(8, 0))
        self.keyin.setText(", ".join(
            str(x) for x in xabar.kechiktirish_variantlari(self.db)))
        self._yangila()

    def _yangila(self):
        n = xabar.tur_namunasi(self.db, self.tur_id, self.kim.odam_id(),
                               self.vaqt.time().toString("HH:mm"))
        if not n:
            return
        self.bosh.setText(n["tur"]["nom"])
        if not n["yoqilgan"]:
            self.holat.setText(
                "⚠ Telegram o'chirilgan — hozir hech narsa yuborilmaydi. "
                "Sozlamalar → Telegram guruhi.")
        elif not n["tayyormi"]:
            self.holat.setText(
                f"⚠ {n['odam']} botga hali /start bosmagan — shaxsiy "
                f"xabar unga bormaydi (va guruhga ham tushmaydi).")
        else:
            self.holat.setText(f"{n['qayerga']} · {n['odam']}")

        eslatma_vaqt = n["eslatma_vaqt"] or "—"
        self.qachon_matn.setText(
            f"1) Kunlik ro'yxat — har kuni soat {n['kunlik_vaqt']} da.\n"
            f"2) Eslatma — ish vaqti tugagach, ya'ni "
            f"{self.vaqt.time().toString('HH:mm')} + "
            f"{self.davomiylik.value()} daqiqa = {eslatma_vaqt} da.\n"
            f"Ish bajarilgan bo'lsa ikkalasi ham yuborilmaydi.")
        self.k_matn.setText(_tg_html(n["kunlik"]))
        self.e_matn.setText(_tg_html(n["eslatma"]))
        keyin = ", ".join(str(x) for x in n["kechiktirish"])
        self.tugma_matn.setText(
            f"Tugmalar: «{xabar.ALBATTA_TUGMA}» va «{xabar.YOQ_TUGMA}». "
            f"«Hali yo'q» bosilsa: {keyin} daqiqadan keyin qayta "
            f"so'raladi.")

    # ── saqlash ─────────────────────────────────────────────────────

    def _saqla(self):
        try:
            tur = vz.tur_bitta(self.db, self.tur_id)
            if tur and self.davomiylik.value() != tur["davomiylik"]:
                vz.tur_davomiylik_qoy(self.db, self.tur_id,
                                      self.davomiylik.value())
            shaxsiy = bool(self.kimga.currentData())
            if tur and bool(tur["shaxsiy"]) != shaxsiy:
                vz.tur_shaxsiy_qoy(self.db, self.tur_id, shaxsiy)
            xabar.sozlama_qoy(
                self.db, kunlik_vaqt=self.kunlik.time().toString("HH:mm"))
            xom = [x.strip() for x in self.keyin.text().split(",")]
            xabar.kechiktirish_qoy(self.db, [x for x in xom if x])
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.accept()
