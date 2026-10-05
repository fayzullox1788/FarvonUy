"""Odamlar, Reja, Hisobot, Sozlamalar sahifalari."""
from __future__ import annotations

import subprocess
import sys
from datetime import date, timedelta

from PySide6.QtCore import QSignalBlocker, Qt, QTime
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QSpinBox,
                               QTimeEdit, QVBoxLayout, QWidget)

import config
import money
import sinx
from core import (entries, importer, ledger, plan, recurring,
                  reports, xabar)
from ui.eski import theme
from ui.eski.dialogs import (YoqKunDialog, tasdiq, xato_koraset)
from ui.eski.sahifa_asosiy import Sahifa, sana_qisqa, shaffof
from ui.eski.widgets import (DarajaQatori, Jadval, Karta, OdamTanla, PulEdit,
                        RaqamKarta, SanaEdit, TuriTanla, Xabar, izoh, qator,
                        sarlavha, tugma, yorliq)


def och(yol):
    """Faylni tizim dasturida ochadi."""
    try:
        if sys.platform == "win32":
            import os
            os.startfile(str(yol))
        else:
            subprocess.Popen(["xdg-open", str(yol)])
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════ ODAMLAR

class OdamSahifa(Sahifa):
    """Excel'dagi shaxsiy varaqning o'rnini bosadi."""

    def __init__(self, oyna):
        super().__init__(oyna)
        self.kim = OdamTanla(self.db)
        self.kim.currentIndexChanged.connect(self.yangila)
        self.dan = SanaEdit((date.today() - timedelta(days=60)).isoformat())
        self.gacha = SanaEdit()
        self.dan.dateChanged.connect(self.yangila)
        self.gacha.dateChanged.connect(self.yangila)
        eksport = tugma("Hisobotni chiqarish")
        eksport.clicked.connect(self._eksport)
        self.tana.addWidget(qator(sarlavha("Shaxsiy"), self.kim, None))
        self.tana.addWidget(qator("Dan:", self.dan, "Gacha:", self.gacha,
                                  None, eksport))

        # Faqat yuqorida tanlangan odamning chizig'i. Hammasini birga
        # ko'rish uchun «Hisobot» sahifasi bor.
        dk = Karta("Pul darajasi")
        self.darajalar = DarajaQatori(ledger.darajalar(self.db)[:1])
        dk.qosh(self.darajalar)
        self.tana.addWidget(dk)

        self.kartalar_quti = QWidget()
        shaffof(self.kartalar_quti)
        self.kartalar = QHBoxLayout(self.kartalar_quti)
        self.kartalar.setContentsMargins(0, 0, 0, 0)
        self.kartalar.setSpacing(14)
        self.tana.addWidget(self.kartalar_quti)

        self.tushuntirish = Karta("Hisob")
        self.tush_matn = izoh("")
        self.tushuntirish.qosh(self.tush_matn)
        self.tana.addWidget(self.tushuntirish)

        # Foydalanuvchi so'rovi bilan YASHIRILGAN (2026-10-01) — hisoblanib
        # turadi, `setVisible(True)` qaytaradi.
        k = Karta("Kunlik harakat")
        self.kunlik_karta = k
        k.setVisible(False)
        self.jadval = Jadval(
            ["Kun", "Kirim", "Shaxsiy rasxod", "Umumiy ulushi", "Qoldiq"],
            pul_ustunlar={1, 2, 3, 4})
        self.jadval.kengliklar(120, 140, 160, 160, 0)
        self.jadval.setMinimumHeight(400)
        k.qosh(self.jadval)
        self.tana.addWidget(k)

        r = Karta("Shu odamning rasxodlari")
        self.rasxod_jadval = Jadval(["Sana", "Nomi", "Kategoriya", "Turi", "Summa"],
                                    pul_ustunlar={4})
        self.rasxod_jadval.kengliklar(105, 0, 150, 95, 130)
        self.rasxod_jadval.setMinimumHeight(280)
        r.qosh(self.rasxod_jadval)
        self.tana.addWidget(r)
        self.tana.addStretch(1)

    def yangila(self):
        # Ro'yxatni qayta to'ldirish `currentIndexChanged` ni uyg'otadi, u esa
        # yana shu funksiyani chaqiradi — signalni to'sib turmasak, cheksiz
        # rekursiya bo'ladi.
        with QSignalBlocker(self.kim):
            self.kim.yangila()
        oid = self.kim.odam_id()
        if not oid:
            return
        b = ledger.balans(self.db, oid)
        if not b:
            return
        # Reja tuzilgan bo'lsa, oyning sarflanmagan rejasidan shu odamning
        # teng ulushi band — qo'ldagi va adolatli puldan ayiriladi.
        # Qo'ldagi puldan faqat bor qismi ayiriladi (`plan.band_hisob`):
        # yetmagani — qarz, balans rejadan minusga tushmaydi.
        bh = plan.band_hisob(self.db)
        mening = bh.get(oid, {"band": 0, "ayirildi": 0, "qarz": 0,
                              "qoplaydi": 0})
        band = mening["ayirildi"]
        band_hamma = plan.band_ayirma(self.db)
        self.darajalar.qoy([x for x in ledger.darajalar(self.db, band_hamma)
                            if x["id"] == oid])

        while self.kartalar.count():
            x = self.kartalar.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        self.kartalar.addWidget(RaqamKarta(
            "Real balans", b["naqd"] - band,
            f"rejaga band {money.fmt(band)} ayirilgan" if band
            else "hozir qo'lingdagi pul"))
        if mening["band"] or mening["qoplaydi"]:
            if mening["qarz"]:
                izohi = (f"{money.fmt(mening['qarz'])} hisobda yo'q — "
                         f"qarzga yozildi")
            elif mening["qoplaydi"]:
                izohi = (f"boshqalar o'rniga {money.fmt(mening['qoplaydi'])}"
                         f" qoplandi")
            else:
                izohi = "oy rejasidan ulush"
            k = RaqamKarta("Rejaga band", mening["band"] + mening["qoplaydi"],
                           izohi)
            k.izoh_holati("berasan")
            # Tugma: umumiy va shaxsiy reja uchun ajratilgan pul.
            k.setCursor(Qt.PointingHandCursor)
            k.setToolTip("Bosing — umumiy va shaxsiy reja uchun ajratilgan pul")
            k.mousePressEvent = lambda _e, oid=oid: self._band(oid)
            self.band_karta = k
            self.kartalar.addWidget(k)
        self.kartalar.addWidget(RaqamKarta(
            "Adolatli balans", b["adolat"] - mening["band"],
            "rejadan keyin qoladi" if band else "hisoblashgandan keyin qoladi"))
        # «Jami kirim» kartasi foydalanuvchi so'rovi bilan olib tashlangan
        # (2026-10-01); kirim «Hisob» qatorida va tooltipda ko'rinadi.
        # Qarz uchun YAGONA karta-tugma (2026-10-01, foydalanuvchi so'ragan):
        # ichki + tashqi qarz jami; bosilsa `QarzlarimOyna` — ikkalasi ham
        # ro'yxati bilan, shu yerda yopiladi. «Sof pozitsiya», «Men uchun
        # olingan» va «Tashqi qarz» kartalari shu bilan almashgan.
        qz = plan.odam_qarzlari(self.db, oid)
        izohlar = []
        if qz["jami"]:
            izohlar.append(f"uyda {money.fmt(qz['ichki_jami'])} · "
                           f"tashqi {money.fmt(qz['tashqi_jami'])}"
                           + (f" · rejadan {money.fmt(qz['reja_jami'])}"
                              if qz["reja_jami"] else ""))
        else:
            izohlar.append("qarz yo'q")
        if qz["menga_jami"]:
            izohlar.append(f"senga qarzdor {money.fmt(qz['menga_jami'])}")
        k = RaqamKarta("Qarzim", qz["jami"], " · ".join(izohlar))
        k.izoh_holati("berasan" if qz["jami"] else "qaytadi")
        k.setCursor(Qt.PointingHandCursor)
        k.setToolTip("Bosing — ichki va tashqi qarzlar, shu yerda yopish")
        k.mousePressEvent = lambda _e, oid=oid: self._qarzlar(oid)
        self.qarz_karta = k
        self.kartalar.addWidget(k)

        # Uzun tushuntirish emas — bitta qatorlik hisob. Kim batafsil
        # ko'rmoqchi bo'lsa, sichqonchani ustiga olib borsa chiqadi.
        self.tush_matn.setText(
            f"{money.fmt(b['kirim'])} kirim  −  "
            f"{money.fmt(b['shaxsiy'])} shaxsiy  −  "
            f"{money.fmt(b['umumiy_ulush'] + b['uchun_ulush'])} ulush  "
            + (f"−  {money.fmt(mening['band'])} rejaga band  " if mening['band'] else "")
            + f"=  <b>{money.fmt(b['adolat'] - mening['band'])}</b> adolatli balans")
        self.tushuntirish.setToolTip(
            f"Real balans (qo'ldagi pul): {money.fmt(b['naqd'] - band)}\n"
            f"  kirim {money.fmt(b['kirim'])}\n"
            f"  − shaxsiy {money.fmt(b['shaxsiy'])}\n"
            f"  − umumiyga to'lagani {money.fmt(b['umumiy_tolagan'])}\n"
            f"  − bergan qarzi {money.fmt(b['qarz_bergan'])}\n"
            f"  + olgan qarzi {money.fmt(b['qarz_olgan'])}\n"
            f"  − to'lagani {money.fmt(b['hk_tolagan'])}\n"
            f"  + olgani {money.fmt(b['hk_olgan'])}\n"
            f"  + tashqaridan olgan qarzi {money.fmt(b['tashqi_olgan'])}\n"
            f"  − uni qaytargani {money.fmt(b['tashqi_qaytargan'])}\n"
            f"  − rejaga band {money.fmt(band)}\n\n"
            f"Sof pozitsiya: {money.fmt(b['sof'], True)}\n"
            f"Adolatli balans = real balans + sof pozitsiya\n"
            f"(Rejaga band — oyning sarflanmagan rejasi, hammaga teng)")

        self.jadval.tuldir(
            [[sana_qisqa(k["sana"]), k["kirim"], k["shaxsiy"], k["ulush"],
              k["qoldiq"]]
             for k in ledger.kunlik_qator(self.db, oid, self.dan.iso(),
                                          self.gacha.iso())])

        qatorlar = []
        for r in self.db.q(
                "SELECT r.*, t.nom turi_nom, t.belgi belgi, p.nom tolovchi"
                " FROM rasxod r LEFT JOIN turi t ON t.id=r.turi_id"
                " JOIN odam p ON p.id=r.kim_toladi"
                " WHERE r.ochirilgan=0 AND r.sana BETWEEN ? AND ?"
                "   AND (r.kim_toladi=? OR r.kim_uchun=?)"
                " ORDER BY r.sana DESC, r.id DESC",
                self.dan.iso(), self.gacha.iso(), oid, oid):
            if r["kim_uchun"] == oid and r["kim_toladi"] != oid:
                tur = f"{r['tolovchi']} olib berdi"
            elif r["kim_uchun"] is not None:
                tur = "Boshqa uchun"
            else:
                tur = "Umumiy" if r["umumiymi"] else "Shaxsiy"
            qatorlar.append([
                sana_qisqa(r["sana"]), r["nom"] or "—",
                f"{r['belgi'] or ''} {r['turi_nom'] or ''}".strip() or "—",
                tur, r["summa"]])
        self.rasxod_jadval.tuldir(qatorlar)

    def _band(self, oid: int):
        from ui.eski.dialogs import RejagaBandOyna
        RejagaBandOyna(self.db, oid, self).exec()

    def _qarzlar(self, oid: int):
        from ui.eski.dialogs import QarzlarimOyna
        d = QarzlarimOyna(self.db, oid, self)
        d.exec()
        if d.ozgardi:
            self.oyna.yangila()

    def _eksport(self):
        oid = self.kim.odam_id()
        if not oid:
            return
        yol = reports.odam_hisoboti(self.db, oid, self.dan.iso(), self.gacha.iso())
        och(yol)


# ══════════════════════════════════════════════════════════════ REJA

class RejaSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        self.hafta = SanaEdit(plan.hafta_boshi())
        self.hafta.dateChanged.connect(self.yangila)
        oldingi = tugma("‹ Oldingi")
        keyingi = tugma("Keyingi ›")
        oldingi.clicked.connect(lambda: self._sur(-7))
        keyingi.clicked.connect(lambda: self._sur(7))
        yarat = tugma("Katalogdan reja tuzish", asosiy=True)
        yarat.clicked.connect(self._yarat)
        self.tana.addWidget(qator(sarlavha("Haftalik reja"), None,
                                  oldingi, self.hafta, keyingi))
        self.tana.addWidget(qator(None, yarat))

        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        self.kartalar_quti = QWidget()
        shaffof(self.kartalar_quti)
        self.kartalar = QHBoxLayout(self.kartalar_quti)
        self.kartalar.setContentsMargins(0, 0, 0, 0)
        self.kartalar.setSpacing(14)
        self.tana.addWidget(self.kartalar_quti)

        k = Karta("Reja qatorlari")
        self.jadval = Jadval(["Uyda bor", "Nomi", "Kategoriya", "Miqdor", "Summa"],
                             pul_ustunlar={4})
        self.jadval.kengliklar(90, 0, 150, 90, 130)
        self.jadval.setMinimumHeight(330)
        self.jadval.cellDoubleClicked.connect(self._bor_almashtir)
        k.qosh(self.jadval)

        self.q_nom = QLineEdit()
        self.q_nom.setPlaceholderText("Mahsulot nomi")
        self.q_summa = PulEdit()
        self.q_summa.setFixedWidth(130)
        self.q_turi = TuriTanla(self.db)
        qosh = tugma("Qo'shish", asosiy=True)
        qosh.clicked.connect(self._qator_qosh)
        ochir = tugma("O'chirish", xavfli=True)
        ochir.clicked.connect(self._qator_ochir)
        bor = tugma("Uyda bor")
        bor.clicked.connect(lambda: self._bor_almashtir(self.jadval.currentRow(), 0))
        k.qosh(qator(self.q_nom, self.q_summa, self.q_turi))
        k.qosh(qator(None, bor, ochir, qosh))
        self.tana.addWidget(k)

        kat = Karta("Katalog — narxi bilan mahsulotlar")
        self.kat_jadval = Jadval(["Nomi", "Kategoriya", "Birlik", "Narxi", "Sikl (kun)"],
                                 pul_ustunlar={3})
        self.kat_jadval.kengliklar(0, 150, 100, 130, 110)
        self.kat_jadval.setMinimumHeight(260)
        kat.qosh(self.kat_jadval)
        self.k_nom = QLineEdit()
        self.k_nom.setPlaceholderText("Mahsulot")
        self.k_narx = PulEdit()
        self.k_narx.setFixedWidth(120)
        self.k_turi = TuriTanla(self.db)
        self.k_birlik = QLineEdit()
        self.k_birlik.setPlaceholderText("kg / dona")
        self.k_birlik.setFixedWidth(95)
        self.k_cikl = QSpinBox()
        self.k_cikl.setRange(0, 365)
        self.k_cikl.setValue(7)
        self.k_cikl.setSuffix(" kun")
        self.k_cikl.setFixedWidth(95)
        kq = tugma("Katalogga qo'shish", asosiy=True)
        kq.clicked.connect(self._item_qosh)
        ko = tugma("O'chirish", xavfli=True)
        ko.clicked.connect(self._item_ochir)
        kat.qosh(qator(self.k_nom, self.k_turi, self.k_birlik))
        kat.qosh(qator(self.k_narx, self.k_cikl, None, ko, kq))
        kat.qosh(izoh("Sikl: 7 = har hafta, 0 = rejaga qo'shilmaydi."))
        self.tana.addWidget(kat)

        t = Karta("O'tgan haftalar: reja va fakt")
        self.tarix_jadval = Jadval(
            ["Hafta", "Reja", "Fakt", "Farq", "Bajarilishi"], pul_ustunlar={1, 2, 3})
        self.tarix_jadval.kengliklar(190, 140, 140, 140, 0)
        self.tarix_jadval.setMinimumHeight(230)
        t.qosh(self.tarix_jadval)
        self.tana.addWidget(t)
        self.tana.addStretch(1)

    def _sur(self, kun: int):
        yangi = date.fromisoformat(self.hafta.iso()) + timedelta(days=kun)
        self.hafta.qoy(plan.hafta_boshi(yangi))

    def _reja_id(self):
        r = plan.reja_ol(self.db, plan.hafta_boshi(self.hafta.iso()))
        return r["id"] if r else None

    def _yarat(self):
        boshi = plan.hafta_boshi(self.hafta.iso())
        if plan.reja_ol(self.db, boshi):
            self.xabar.korsat("Bu haftaga reja allaqachon bor.", "ogoh", 4000)
            return
        if not plan.itemlar(self.db):
            self.xabar.korsat(
                "Katalog bo'sh — avval pastdagi «Katalog» bo'limiga "
                "mahsulot qo'shing.", "ogoh", 6000)
            return
        plan.reja_yarat(self.db, boshi)
        self.yangila()
        self.xabar.korsat("Reja tuzildi.", "ok", 3000)

    def _qator_qosh(self):
        rid = self._reja_id()
        if not rid:
            boshi = plan.hafta_boshi(self.hafta.iso())
            rid = plan.reja_yarat(self.db, boshi, katalogdan=False)
        nom = self.q_nom.text().strip()
        if not nom or self.q_summa.qiymat() <= 0:
            self.xabar.korsat("Nomi va summasi kerak.", "xato", 3000)
            return
        plan.qator_qosh(self.db, rid, nom, self.q_summa.qiymat(),
                        self.q_turi.turi_id())
        self.q_nom.clear()
        self.q_summa.tozala()
        self.yangila()

    def _qator_ochir(self):
        qid = self.jadval.tanlangan_id()
        if qid:
            plan.qator_ochir(self.db, qid)
            self.yangila()

    def _bor_almashtir(self, satr, _ustun=0):
        if satr < 0:
            return
        it = self.jadval.item(satr, 0)
        if not it:
            return
        qid = it.data(Qt.UserRole)
        r = self.db.q1("SELECT bor FROM reja_qator WHERE id=?", qid)
        if r:
            plan.bor_belgila(self.db, qid, not r["bor"])
            self.yangila()

    def _item_qosh(self):
        nom = self.k_nom.text().strip()
        if not nom or self.k_narx.qiymat() <= 0:
            self.xabar.korsat("Mahsulot nomi va narxi kerak.", "xato", 3000)
            return
        plan.item_qosh(self.db, nom, self.k_narx.qiymat(), self.k_turi.turi_id(),
                       self.k_birlik.text().strip() or None,
                       self.k_cikl.value() or None)
        self.k_nom.clear()
        self.k_narx.tozala()
        self.yangila()

    def _item_ochir(self):
        iid = self.kat_jadval.tanlangan_id()
        if iid and tasdiq(self, "Katalogdan o'chirilsinmi?"):
            plan.item_ochir(self.db, iid)
            self.yangila()

    def yangila(self):
        with QSignalBlocker(self.q_turi), QSignalBlocker(self.k_turi):
            self.q_turi.yangila()
            self.k_turi.yangila()
        rid = self._reja_id()

        while self.kartalar.count():
            x = self.kartalar.takeAt(0)
            if x.widget():
                x.widget().deleteLater()

        if rid:
            rf = plan.solishtir(self.db, rid)
            self.kartalar.addWidget(RaqamKarta("Reja", rf.reja, "olinishi kerak"))
            self.kartalar.addWidget(RaqamKarta(
                "Uyda bor", rf.reja_hammasi - rf.reja, "olish shart emas"))
            self.kartalar.addWidget(RaqamKarta(
                "Fakt", rf.fakt, f"{rf.boshi} — {rf.oxiri}"))
            self.kartalar.addWidget(RaqamKarta(
                "Farq", rf.farq,
                f"rejadan {rf.foiz:.0f}%" if rf.reja else "reja qo'yilmagan",
                rangli=True))

            qatorlar, idlar = [], []
            for q in plan.qatorlar(self.db, rid):
                qatorlar.append([
                    "✔ bor" if q["bor"] else "—", q["nom"],
                    f"{q['turi_belgi'] or ''} {q['turi_nom'] or ''}".strip() or "—",
                    f"{q['miqdor']:g}", q["summa"]])
                idlar.append(q["id"])
            self.jadval.tuldir(qatorlar, idlar)
        else:
            self.jadval.tuldir([])
            k = RaqamKarta("Reja", 0, "bu haftaga reja tuzilmagan")
            k.izoh_holati("tinch")
            self.kartalar.addWidget(k)

        qatorlar, idlar = [], []
        for it in plan.itemlar(self.db):
            qatorlar.append([
                it["nom"],
                f"{it['turi_belgi'] or ''} {it['turi_nom'] or ''}".strip() or "—",
                it["birlik"] or "—", it["narx"],
                str(it["cikl_kun"]) if it["cikl_kun"] else "—"])
            idlar.append(it["id"])
        self.kat_jadval.tuldir(qatorlar, idlar)

        qatorlar = []
        for rf in plan.oxirgi_rejalar(self.db, 12):
            qatorlar.append([f"{sana_qisqa(rf.boshi)} — {sana_qisqa(rf.oxiri)}",
                             rf.reja, rf.fakt, rf.farq,
                             f"{rf.foiz:.0f}%" if rf.reja else "—"])
        self.tarix_jadval.tuldir(qatorlar, rangli_ustunlar={3})


# ═══════════════════════════════════════════════════════════ HISOBOT

class HisobotSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        self.dan = SanaEdit(plan.oy_boshi())
        self.gacha = SanaEdit(plan.oy_oxiri())
        self.dan.dateChanged.connect(self.yangila)
        self.gacha.dateChanged.connect(self.yangila)
        oy = tugma("Shu oy")
        hafta = tugma("Shu hafta")
        oy.clicked.connect(lambda: self._oraliq(plan.oy_boshi(), plan.oy_oxiri()))
        hafta.clicked.connect(lambda: self._oraliq(plan.hafta_boshi(),
                                                   plan.hafta_oxiri()))
        self.tana.addWidget(qator(sarlavha("Hisobot"), None))
        self.tana.addWidget(qator(hafta, oy, None,
                                  "Dan:", self.dan, "Gacha:", self.gacha))

        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        e = Karta("Chiqarish va ulashish")
        h1 = tugma("HTML hisobot", asosiy=True)
        h2 = tugma("Excel hisobot")
        h3 = tugma("Papkani ochish")
        h1.clicked.connect(self._html)
        h2.clicked.connect(self._excel)
        h3.clicked.connect(lambda: och(config.EKSPORT))
        e.qosh(qator(h1, h2, h3, None))
        e.qosh(izoh("HTML — Telegramga yuborish uchun."))
        self.tana.addWidget(e)

        self.kartalar_quti = QWidget()
        shaffof(self.kartalar_quti)
        self.kartalar = QHBoxLayout(self.kartalar_quti)
        self.kartalar.setContentsMargins(0, 0, 0, 0)
        self.kartalar.setSpacing(14)
        self.tana.addWidget(self.kartalar_quti)

        dk = Karta("Pul darajasi")
        self.darajalar = DarajaQatori(ledger.darajalar(self.db))
        dk.qosh(self.darajalar)
        self.tana.addWidget(dk)

        b = Karta("Balanslar")
        self.balans_jadval = Jadval(
            ["Odam", "Kirim", "Shaxsiy", "Umumiy to'lagan", "Ulushi",
             "Real balans", "Sof", "Adolatli"],
            pul_ustunlar={1, 2, 3, 4, 5, 6, 7})
        self.balans_jadval.kengliklar(130, 115, 110, 140, 115, 125, 115, 0)
        self.balans_jadval.setMaximumHeight(210)
        b.qosh(self.balans_jadval)
        self.tana.addWidget(b)

        t = Karta("Nimaga ketdi")
        self.turi_jadval = Jadval(["Kategoriya", "Soni", "Summa", "Ulushi"],
                                  pul_ustunlar={2})
        self.turi_jadval.kengliklar(0, 100, 150, 120)
        self.turi_jadval.setMinimumHeight(280)
        t.qosh(self.turi_jadval)
        self.tana.addWidget(t)

        bu = Karta("Kategoriya budjeti (shu oy)")
        self.budjet_jadval = Jadval(
            ["Kategoriya", "Budjet", "Fakt", "Farq", "Bajarilishi"],
            pul_ustunlar={1, 2, 3})
        self.budjet_jadval.kengliklar(0, 130, 130, 130, 130)
        self.budjet_jadval.setMinimumHeight(230)
        bu.qosh(self.budjet_jadval)
        self.b_turi = TuriTanla(self.db)
        self.b_summa = PulEdit()
        self.b_summa.setFixedWidth(140)
        bq = tugma("Budjet qo'yish", asosiy=True)
        bq.clicked.connect(self._budjet)
        bu.qosh(qator(self.b_turi, self.b_summa, bq, None))
        self.tana.addWidget(bu)

        self.audit_karta = Karta("Kitob tekshiruvi")
        self.audit_matn = QLabel()
        self.audit_matn.setWordWrap(True)
        shaffof(self.audit_matn)
        self.audit_karta.qosh(self.audit_matn)
        self.tana.addWidget(self.audit_karta)
        self.tana.addStretch(1)

    def _oraliq(self, a, b):
        self.dan.qoy(a)
        self.gacha.qoy(b)

    def _html(self):
        yol = reports.html_hisobot(self.db, self.dan.iso(), self.gacha.iso())
        self.xabar.korsat(f"Yozildi: {yol}", "ok", 8000)
        och(yol)

    def _excel(self):
        yol = reports.excel(self.db, self.dan.iso(), self.gacha.iso())
        self.xabar.korsat(f"Yozildi: {yol}", "ok", 8000)
        och(yol)

    def _budjet(self):
        if not self.b_turi.turi_id() or self.b_summa.qiymat() <= 0:
            self.xabar.korsat("Kategoriya va summa tanlang.", "xato", 3000)
            return
        plan.budjet_qoy(self.db, self.b_turi.turi_id(),
                        self.dan.iso()[:7], self.b_summa.qiymat())
        self.b_summa.tozala()
        self.yangila()

    def yangila(self):
        with QSignalBlocker(self.b_turi):
            self.b_turi.yangila()
        dan, gacha = self.dan.iso(), self.gacha.iso()

        while self.kartalar.count():
            x = self.kartalar.takeAt(0)
            if x.widget():
                x.widget().deleteLater()
        kirim = self.db.skalyar(
            "SELECT SUM(summa) FROM kirim WHERE ochirilgan=0 AND sana BETWEEN ? AND ?",
            dan, gacha)
        rasxod = self.db.skalyar(
            "SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0 AND sana BETWEEN ? AND ?",
            dan, gacha)
        umumiy = self.db.skalyar(
            "SELECT SUM(summa) FROM rasxod WHERE ochirilgan=0 AND umumiymi=1"
            " AND sana BETWEEN ? AND ?", dan, gacha)
        p = plan.prognoz(self.db)
        self.kartalar.addWidget(RaqamKarta("Kirim", kirim, "shu oraliqda"))
        self.kartalar.addWidget(RaqamKarta("Rasxod", rasxod, "shu oraliqda"))
        self.kartalar.addWidget(RaqamKarta("Umumiy rasxod", umumiy, "bo'lingan"))
        self.kartalar.addWidget(RaqamKarta(
            "Kunlik o'rtacha", p["kunlik"],
            f"shu tempda pul {p['yetadi_kun']} kunga yetadi"
            if p["yetadi_kun"] else "hisoblab bo'lmadi"))

        band = plan.band_ayirma(self.db)
        self.darajalar.qoy(ledger.darajalar(self.db, band))

        self.balans_jadval.tuldir(
            [[r["nom"], r["kirim"], r["shaxsiy"], r["umumiy_tolagan"],
              r["umumiy_ulush"], r["naqd"] - band.get(r["id"], 0), r["sof"],
              r["adolat"] - band.get(r["id"], 0)]
             for r in ledger.balanslar(self.db)], rangli_ustunlar={6})

        turlar = ledger.turi_boyicha(self.db, dan, gacha)
        jami = sum(t["summa"] for t in turlar) or 1
        self.turi_jadval.tuldir(
            [[f"{t['belgi']} {t['nom']}".strip(), t["soni"], t["summa"],
              f"{t['summa'] / jami * 100:.0f}%"] for t in turlar])

        self.budjet_jadval.tuldir(
            [[f"{b['belgi']} {b['nom']}".strip(), b["budjet"], b["fakt"], b["farq"],
              f"{b['foiz']:.0f}%" if b["budjet"] else "—"]
             for b in plan.turi_budjet(self.db, dan[:7])], rangli_ustunlar={3})

        a = ledger.audit(self.db)
        if a.toza:
            self.audit_matn.setText(
                f"<span style='color:{theme.YASHIL};font-weight:700'>"
                f"✔ KITOB TENG</span><br><br>"
                f"Qarzlar yig'indisi: {a.sof_yigindi} (nolga teng bo'lishi shart)<br>"
                f"Naqd pul: {money.fmt(a.naqd_yigindi)} = kirim − rasxod + tashqi qarz "
                f"({money.fmt(a.kutilgan_naqd)})<br>"
                f"Har odam uchun: adolatli balans = real balans + sof pozitsiya ✔<br>"
                f"Har umumiy rasxodning ulushlari summasiga teng ✔")
        else:
            self.audit_matn.setText(
                f"<span style='color:{theme.QIZIL};font-weight:700'>"
                f"✘ MUAMMO BOR</span><br><br>" +
                "<br>".join(a.muammolar))


# ═════════════════════════════════════════════════════════ SOZLAMA

class SozlamaSahifa(Sahifa):
    def __init__(self, oyna):
        super().__init__(oyna)
        self.tana.addWidget(sarlavha("Sozlamalar"))
        self.xabar = Xabar()
        self.tana.addWidget(self.xabar)

        # ── ko'rinish ────────────────────────────────────────────────
        kr = Karta("Ko'rinish")
        self.rejim = QComboBox()
        for kalit, nom in theme.REJIMLAR:
            self.rejim.addItem(nom, kalit)
        joriy = self.db.sozlama("rejim", theme.REJIM)
        i = self.rejim.findData(joriy)
        if i >= 0:
            self.rejim.setCurrentIndex(i)
        self.rejim.currentIndexChanged.connect(self._rejim)
        kr.qosh(qator("Rang rejimi:", self.rejim, None))
        self.tana.addWidget(kr)

        # ── demo rejim ───────────────────────────────────────────────
        # Taqdimot uchun soxta ma'lumot (`demo.py`). Belgilansa/olinsa
        # dastur o'zi qayta ochiladi — `Oyna._demo_almashtir`.
        dm = Karta("Demo rejim")
        self.demo = QCheckBox("Soxta ma'lumot bilan ko'rsatish (haqiqiy ma'lumot yashiriladi)")
        self.demo.setChecked(config.DEMO)
        self.demo.clicked.connect(lambda _: self.oyna._demo_almashtir())
        dm.qosh(qator(self.demo, None))
        self.tana.addWidget(dm)

        # ── Telegram ─────────────────────────────────────────────────
        tg = Karta("Telegram guruhi")
        self.tg_yoq = QCheckBox("Yoqilgan")
        self.tg_token = QLineEdit()
        self.tg_token.setPlaceholderText("BotFather bergan token")
        self.tg_token.setEchoMode(QLineEdit.Password)
        self.tg_guruh = QLineEdit()
        self.tg_guruh.setPlaceholderText("guruh raqami, masalan -1001234567890")
        self.tg_guruh.setFixedWidth(230)
        self.tg_vaqt = QTimeEdit(QTime(8, 0))
        self.tg_vaqt.setDisplayFormat("HH:mm")
        tg.qosh(qator(self.tg_yoq, None))
        tg.qosh(qator("Token:", self.tg_token))
        tg.qosh(qator("Guruh:", self.tg_guruh,
                      "Kunlik xulosa:", self.tg_vaqt, None))
        # Bot Cloudflare'da: desktop server bazasi (D1) bilan shu
        # manzil va maxfiy kalit orqali sinxronlanadi (`sinx.py`).
        self.sinx_url = QLineEdit()
        self.sinx_url.setPlaceholderText("https://farvonuy.….workers.dev")
        self.sinx_kalit = QLineEdit()
        self.sinx_kalit.setPlaceholderText("sinxron kaliti")
        self.sinx_kalit.setEchoMode(QLineEdit.Password)
        self.sinx_kalit.setFixedWidth(230)
        tg.qosh(qator("Server:", self.sinx_url,
                      "Kalit:", self.sinx_kalit, None))

        tg_top = tugma("Guruhni aniqlash")
        tg_top.setToolTip("Botni guruhga qo'shib, u yerga bitta xabar "
                          "yozing \u2014 keyin shu tugmani bosing")
        tg_top.clicked.connect(self._tg_guruh_top)
        tg_sinov = tugma("Sinov xabari")
        tg_sinov.clicked.connect(self._tg_sinov)
        tg_saqla = tugma("Saqlash", asosiy=True)
        tg_saqla.clicked.connect(self._tg_saqla)
        tg.qosh(qator(tg_saqla, tg_top, tg_sinov, None))

        self.tg_holat = izoh("")
        tg.qosh(self.tg_holat)
        # Shaxsiy vazifa faqat botga /start bosgan odamga boradi —
        # Telegram botga o'zi boshlab yozishga ruxsat bermaydi. Kim
        # bosmagani shu yerda ko'rinib tursin, aks holda shaxsiy
        # xabar jimgina yuborilmay qolardi va sababi bilinmasdi.
        self.tg_shaxsiy = izoh("")
        tg.qosh(self.tg_shaxsiy)
        tg.qosh(izoh(
            "Bot har kuni belgilangan soatda kunlik ro'yxatni, vazifa "
            "vaqti tugagach esa mas'ul odamni teg qilib \u00abbajardingizmi?\u00bb "
            "deb so'raydi. Buning uchun kompyuter yoniq bo'lishi kerak "
            "\u2014 reja `xabarchi_reja.bat` bilan o'rnatiladi."))
        self.tana.addWidget(tg)

        # ── chegaralar ───────────────────────────────────────────────
        ch = Karta("Ogohlantirish chegarasi")
        self.ch_kam = PulEdit()
        self.ch_kam.setFixedWidth(150)
        self.ch_juda = PulEdit()
        self.ch_juda.setFixedWidth(150)
        chs = tugma("Saqlash", asosiy=True)
        chs.clicked.connect(self._chegara)
        ch.qosh(qator("Kam qoldi:", self.ch_kam,
                      "Juda kam:", self.ch_juda, chs, None))
        self.tana.addWidget(ch)

        # ── odamlar ──────────────────────────────────────────────────
        o = Karta("Odamlar")
        self.odam_jadval = Jadval(
            ["Ism", "Telegram", "Holat", "Real balans", "Sof pozitsiya"],
            pul_ustunlar={3, 4})
        self.odam_jadval.kengliklar(0, 210, 120, 150, 150)
        self.odam_jadval.setMaximumHeight(210)
        o.qosh(self.odam_jadval)
        self.o_nom = QLineEdit()
        self.o_nom.setPlaceholderText("Yangi odam ismi")
        oq = tugma("Qo'shish", asosiy=True)
        oo = tugma("Ro'yxatdan olish", xavfli=True)
        oqa = tugma("Qaytarish")
        oq.clicked.connect(self._odam_qosh)
        oo.clicked.connect(self._odam_ochir)
        oqa.clicked.connect(self._odam_qaytar)
        o.qosh(qator(self.o_nom, oq, None, oqa, oo))
        o.qosh(izoh("Qarzi bor odamni ro'yxatdan olib bo'lmaydi."))

        # Telegram nomi — guruhda shu odam teg qilinadi
        self.tg_odam = OdamTanla(self.db)
        self.tg_nom = QLineEdit()
        self.tg_nom.setPlaceholderText("@foydalanuvchi_nomi")
        self.tg_nom.setFixedWidth(240)
        self.tg_odam.currentIndexChanged.connect(self._tg_nom_yukla)
        tg_saqla_nom = tugma("Saqlash")
        tg_saqla_nom.clicked.connect(self._tg_nom_saqla)
        o.qosh(qator("Telegram:", self.tg_odam, self.tg_nom,
                     tg_saqla_nom, None))
        self.tana.addWidget(o)

        # ── kategoriya ───────────────────────────────────────────────
        k = Karta("Kategoriyalar")
        self.turi_jadval = Jadval(["Belgi", "Nomi", "Yozuvlar", "Mahsulotlar"])
        self.turi_jadval.kengliklar(80, 0, 120, 130)
        self.turi_jadval.setMaximumHeight(230)
        k.qosh(self.turi_jadval)
        self.t_belgi = QLineEdit()
        self.t_belgi.setPlaceholderText("🍲")
        self.t_belgi.setFixedWidth(70)
        self.t_nom = QLineEdit()
        self.t_nom.setPlaceholderText("Kategoriya nomi")
        tq = tugma("Qo'shish", asosiy=True)
        tq.clicked.connect(self._turi_qosh)
        k.qosh(qator(self.t_belgi, self.t_nom, tq, None))
        self.turi_jadval.itemSelectionChanged.connect(self._mahsulotlar_yukla)
        self.tana.addWidget(k)

        # ── kategoriya ichidagi mahsulotlar ──────────────────────────
        mh = Karta("Kategoriya mahsulotlari")
        self.mh_izoh = izoh("Yuqoridan kategoriyani tanlang.")
        mh.qosh(self.mh_izoh)
        self.mh_jadval = Jadval(["Mahsulot", "Birlik", "Narxi", "Sikl (kun)"],
                                pul_ustunlar={2})
        self.mh_jadval.kengliklar(0, 110, 140, 120)
        self.mh_jadval.setMinimumHeight(240)
        mh.qosh(self.mh_jadval)
        self.mh_nom = QLineEdit()
        self.mh_nom.setPlaceholderText("Mahsulot nomi")
        self.mh_narx = PulEdit()
        self.mh_narx.setFixedWidth(130)
        self.mh_birlik = QLineEdit()
        self.mh_birlik.setPlaceholderText("kg / dona")
        self.mh_birlik.setFixedWidth(100)
        self.mh_cikl = QSpinBox()
        self.mh_cikl.setRange(0, 365)
        self.mh_cikl.setSuffix(" kun")
        self.mh_cikl.setFixedWidth(100)
        mq = tugma("Qo'shish", asosiy=True)
        mt = tugma("Narxini yangilash")
        mo = tugma("O'chirish", xavfli=True)
        mq.clicked.connect(self._mahsulot_qosh)
        mt.clicked.connect(self._mahsulot_narx)
        mo.clicked.connect(self._mahsulot_ochir)
        mh.qosh(qator(self.mh_nom, self.mh_birlik, self.mh_narx, self.mh_cikl))
        mh.qosh(qator(None, mo, mt, mq))
        self.tana.addWidget(mh)

        # ── yo'q kunlar ──────────────────────────────────────────────
        y = Karta("Uyda yo'q kunlar")
        self.yoq_jadval = Jadval(["Kim", "Dan", "Gacha", "Sabab"])
        self.yoq_jadval.kengliklar(150, 120, 120, 0)
        self.yoq_jadval.setMaximumHeight(200)
        y.qosh(self.yoq_jadval)
        yq = tugma("+ Qo'shish", asosiy=True)
        yo = tugma("O'chirish", xavfli=True)
        yq.clicked.connect(self._yoq_qosh)
        yo.clicked.connect(self._yoq_ochir)
        y.qosh(qator(None, yo, yq))
        y.qosh(izoh("Bu kunlardagi umumiy rasxodlar shu odamga bo'linmaydi."))
        self.tana.addWidget(y)

        # ── takroriy ─────────────────────────────────────────────────
        t = Karta("Takroriy rasxodlar")
        self.takror_jadval = Jadval(
            ["Nomi", "Summa", "Davriylik", "Kim to'laydi", "Keyingi sana"],
            pul_ustunlar={1})
        self.takror_jadval.kengliklar(0, 130, 130, 150, 130)
        self.takror_jadval.setMaximumHeight(200)
        t.qosh(self.takror_jadval)
        self.tk_nom = QLineEdit()
        self.tk_nom.setPlaceholderText("masalan: Internet")
        self.tk_summa = PulEdit()
        self.tk_summa.setFixedWidth(130)
        self.tk_kim = OdamTanla(self.db)
        self.tk_davr = QComboBox()
        for kalit, nom in recurring.DAVRIYLIK.items():
            self.tk_davr.addItem(nom, kalit)
        self.tk_davr.setCurrentIndex(2)
        self.tk_kun = QSpinBox()
        self.tk_kun.setRange(1, 28)
        self.tk_kun.setValue(1)
        self.tk_kun.setPrefix("kun ")
        self.tk_kun.setFixedWidth(95)
        tkq = tugma("Qo'shish", asosiy=True)
        tko = tugma("O'chirish", xavfli=True)
        tkq.clicked.connect(self._takror_qosh)
        tko.clicked.connect(self._takror_ochir)
        t.qosh(qator(self.tk_nom, self.tk_summa, self.tk_kim))
        t.qosh(qator(self.tk_davr, self.tk_kun, None, tko, tkq))
        t.qosh(izoh("Muddati kelganda «Bugun» da eslatma chiqadi."))
        self.tana.addWidget(t)

        # ── davr yopish ──────────────────────────────────────────────
        d = Karta("Oyni yopish")
        d.qosh(izoh("Yopilgan oyga yozuv kiritib bo'lmaydi."))
        self.davr_jadval = Jadval(["Oy", "Holat", "Yopilgan vaqt"])
        self.davr_jadval.kengliklar(130, 150, 0)
        self.davr_jadval.setMaximumHeight(180)
        d.qosh(self.davr_jadval)
        self.d_oy = QLineEdit()
        self.d_oy.setPlaceholderText("2026-08")
        self.d_oy.setFixedWidth(120)
        self.d_oy.setText(date.today().strftime("%Y-%m"))
        dy = tugma("Yopish", asosiy=True)
        do = tugma("Ochish")
        dy.clicked.connect(lambda: self._davr("yopilgan"))
        do.clicked.connect(lambda: self._davr("ochiq"))
        d.qosh(qator(self.d_oy, dy, do, None))
        self.tana.addWidget(d)

        # ── ma'lumot ─────────────────────────────────────────────────
        m = Karta("Ma'lumot va zaxira")
        self.m_matn = izoh("")
        m.qosh(self.m_matn)
        z1 = tugma("Hozir zaxira olish", asosiy=True)
        z2 = tugma("Zaxira papkasini ochish")
        z3 = tugma("Excel'dan ko'chirish")
        z1.clicked.connect(self._zaxira)
        z2.clicked.connect(lambda: och(config.ZAXIRA))
        z3.clicked.connect(self._import)
        m.qosh(qator(z1, z2, z3, None))
        self.tana.addWidget(m)

        # ── o'zgarishlar tarixi ──────────────────────────────────────
        oz = Karta("O'zgarishlar tarixi")
        self.oz_jadval = Jadval(["Vaqt", "Nima qilindi", "Holat"])
        self.oz_jadval.kengliklar(160, 0, 130)
        self.oz_jadval.setMinimumHeight(260)
        oz.qosh(self.oz_jadval)
        self.tana.addWidget(oz)
        self.tana.addStretch(1)

    # ── amallar ──────────────────────────────────────────────────────

    def _rejim(self):
        """Rang rejimini almashtiradi va butun oynani qayta bo'yaydi."""
        from PySide6.QtWidgets import QApplication
        from ui.eski import widgets as W

        kalit = self.rejim.currentData()
        theme.rejim_qoy(kalit)
        QApplication.instance().setStyleSheet(theme.STIL)
        W.qayta_boya(self.oyna)
        self.db.sozlama_qoy("rejim", kalit)
        self.oyna.yangila()

    def _chegara(self):
        kam, juda = self.ch_kam.qiymat(), self.ch_juda.qiymat()
        if kam <= 0 or juda <= 0:
            self.xabar.korsat("Ikkala chegara ham musbat bo'lsin.", "xato", 3000)
            return
        if juda >= kam:
            self.xabar.korsat("«Juda kam» «kam qoldi» dan past bo'lishi kerak.",
                              "xato", 4000)
            return
        ledger.chegara_qoy(self.db, kam, juda)
        self.oyna.yangila()
        self.xabar.korsat("Chegaralar saqlandi.", "ok", 3000)

    # ── Telegram ─────────────────────────────────────────────────

    def _tg_yukla(self):
        s = xabar.sozlamalar(self.db)
        self.tg_yoq.setChecked(s["yoqilgan"])
        self.tg_token.setText(s["token"])
        self.tg_guruh.setText(s["guruh"])
        self.sinx_url.setText(self.db.sozlama(sinx.K_URL, ""))
        self.sinx_kalit.setText(self.db.sozlama(sinx.K_KALIT, ""))
        self.tg_vaqt.setTime(QTime.fromString(s["kunlik_vaqt"], "HH:mm")
                             or QTime(8, 0))
        yoq = xabar.dm_yoqmaganlar(self.db)
        if yoq:
            self.tg_shaxsiy.setText(
                "Shaxsiy vazifalar hali bormaydi: "
                + ", ".join(r["nom"] for r in yoq)
                + " — botni Telegramda ochib bir marta /start bossin.")
        else:
            self.tg_shaxsiy.setText(
                "Shaxsiy vazifalar ishlaydi: hamma botga yozgan.")

    def _tg_saqla(self):
        xabar.sozlama_qoy(
            self.db,
            token=self.tg_token.text(),
            guruh=self.tg_guruh.text(),
            yoqilgan=self.tg_yoq.isChecked(),
            kunlik_vaqt=self.tg_vaqt.time().toString("HH:mm"))
        sinx.sozlama_qoy(self.db, self.sinx_url.text(),
                         self.sinx_kalit.text())
        tetik = getattr(self.oyna, "_sinx_tetikla", None)
        if tetik is not None:
            tetik()
        self.xabar.korsat("Telegram sozlamalari saqlandi", "ok")

    def _tg_guruh_top(self):
        """Bot ko'rgan guruhlardan tanlash."""
        token = self.tg_token.text().strip()
        if not token:
            xato_koraset(self, "Avval tokenni kiriting.")
            return
        try:
            guruhlar = xabar.guruhlarni_top(token)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        guruhlar = [g for g in guruhlar if g["turi"] in ("group", "supergroup")]
        if not guruhlar:
            xato_koraset(
                self,
                "Guruh topilmadi.\n\nBotni guruhga qo'shing va o'sha "
                "guruhga bitta xabar yozing, keyin qaytadan urinib "
                "ko'ring. (Telegram faqat oxirgi xabarlarni ko'rsatadi.)")
            return
        if len(guruhlar) == 1:
            g = guruhlar[0]
        else:
            nomlar = [f"{x['nom']}  ({x['id']})" for x in guruhlar]
            tanlov, ok = QInputDialog.getItem(
                self, "Guruhni tanlang", "Guruh:", nomlar, 0, False)
            if not ok:
                return
            g = guruhlar[nomlar.index(tanlov)]
        self.tg_guruh.setText(g["id"])
        self.tg_holat.setText(f"Topildi: {g['nom']} ({g['id']})")

    def _tg_sinov(self):
        """Hozir nima yuborilardi — va guruhga sinov xabari."""
        token = self.tg_token.text().strip()
        guruh = self.tg_guruh.text().strip()
        if not token or not guruh:
            xato_koraset(self, "Token va guruh kiritilishi kerak.")
            return
        try:
            bot = xabar.bot_haqida(token)
            # Guruhga xuddi ertalabkidek BO'LAK-BO'LAK
            # yuboriladi: sinov boshqacha ko'rinsa, u sinov
            # bo'lmay qoladi.
            xabar.sinov_yubor(self.db, token, guruh)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        kutilgan = xabar.kutilayotgan(self.db)
        self.tg_holat.setText(
            f"@{bot.get('username', '?')} orqali yuborildi. "
            f"Hozir navbatda {len(kutilgan)} ta xabar bor.")
        self.xabar.korsat("Sinov xabari guruhga yuborildi", "ok")

    def _tg_nom_yukla(self):
        oid = self.tg_odam.odam_id()
        if not oid:
            return
        r = self.db.q1("SELECT telegram FROM odam WHERE id=?", oid)
        self.tg_nom.setText(f"@{r['telegram']}" if r and r["telegram"] else "")

    def _tg_nom_saqla(self):
        """Odamning Telegram nomi — guruhda shu bilan teg qilinadi."""
        oid = self.tg_odam.odam_id()
        if not oid:
            return
        matn = (self.tg_nom.text() or "").strip().lstrip("@") or None
        with self.db.amal("Telegram nomi o'zgardi"):
            self.db.apply("odam", "UPDATE", {"telegram": matn}, oid)
        self.oyna.yangila()
        self.xabar.korsat(
            f"Telegram nomi saqlandi: {'@' + matn if matn else '—'}", "ok")

    def _odam_qosh(self):
        nom = self.o_nom.text().strip()
        if not nom:
            return
        try:
            entries.odam_qosh(self.db, nom)
        except Exception as e:
            self.xabar.korsat(str(e), "xato", 4000)
            return
        self.o_nom.clear()
        self.oyna.yangila()

    def _odam_ochir(self):
        oid = self.odam_jadval.tanlangan_id()
        if not oid:
            self.xabar.korsat("Avval jadvaldan odamni tanlang.", "ogoh", 3000)
            return
        nom = self.db.q1("SELECT nom FROM odam WHERE id=?", oid)["nom"]
        if not tasdiq(self, f"{nom} ro'yxatdan olinsinmi?\n\n"
                            f"Eski yozuvlari o'chmaydi, faqat yangi "
                            f"rasxodlarda ko'rinmaydi."):
            return
        try:
            entries.odam_ochir(self.db, oid)
        except Exception as e:
            xato_koraset(self, str(e))
            return
        self.oyna.yangila()

    def _odam_qaytar(self):
        oid = self.odam_jadval.tanlangan_id()
        if not oid:
            self.xabar.korsat("Avval jadvaldan odamni tanlang.", "ogoh", 3000)
            return
        entries.odam_qaytar(self.db, oid)
        self.oyna.yangila()

    def _turi_qosh(self):
        nom = self.t_nom.text().strip()
        if not nom:
            return
        n = self.db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM turi")
        try:
            with self.db.amal(f"Kategoriya: {nom}"):
                self.db.apply("turi", "INSERT", {
                    "nom": nom, "belgi": self.t_belgi.text().strip(), "tartib": n})
        except Exception as e:
            self.xabar.korsat(str(e), "xato", 4000)
            return
        self.t_nom.clear()
        self.t_belgi.clear()
        self.oyna.yangila()

    # ── kategoriya mahsulotlari ──────────────────────────────────────

    def _tanlangan_turi(self):
        return self.turi_jadval.tanlangan_id()

    def _mahsulotlar_yukla(self):
        tid = self._tanlangan_turi()
        if not tid:
            self.mh_izoh.setText("Yuqoridan kategoriyani tanlang.")
            self.mh_jadval.tuldir([])
            return
        t = self.db.q1("SELECT nom, belgi FROM turi WHERE id=?", tid)
        self.mh_izoh.setText(
            f"{t['belgi']} {t['nom']} — shu kategoriyaning mahsulotlari")
        qatorlar, idlar = [], []
        for it in plan.turi_itemlari(self.db, tid):
            qatorlar.append([it["nom"], it["birlik"] or "—", it["narx"],
                             str(it["cikl_kun"]) if it["cikl_kun"] else "—"])
            idlar.append(it["id"])
        self.mh_jadval.tuldir(qatorlar, idlar)

    def _mahsulot_qosh(self):
        tid = self._tanlangan_turi()
        if not tid:
            self.xabar.korsat("Avval kategoriyani tanlang.", "ogoh", 3000)
            return
        nom = self.mh_nom.text().strip()
        if not nom:
            self.xabar.korsat("Mahsulot nomi kerak.", "xato", 3000)
            return
        plan.item_qosh(self.db, nom, self.mh_narx.qiymat(), tid,
                       self.mh_birlik.text().strip() or None,
                       self.mh_cikl.value() or None)
        self.mh_nom.clear()
        self.mh_narx.tozala()
        self.mh_birlik.clear()
        self.yangila()

    def _mahsulot_narx(self):
        iid = self.mh_jadval.tanlangan_id()
        if not iid:
            self.xabar.korsat("Avval mahsulotni tanlang.", "ogoh", 3000)
            return
        if self.mh_narx.qiymat() <= 0:
            self.xabar.korsat("Yangi narxni kiriting.", "xato", 3000)
            return
        plan.item_narx_yangila(self.db, iid, self.mh_narx.qiymat())
        self.mh_narx.tozala()
        self.yangila()

    def _mahsulot_ochir(self):
        iid = self.mh_jadval.tanlangan_id()
        if iid and tasdiq(self, "Mahsulot katalogdan o'chirilsinmi?"):
            plan.item_ochir(self.db, iid)
            self.yangila()

    def _yoq_qosh(self):
        if YoqKunDialog(self.db, self).exec():
            self.oyna.yangila()

    def _yoq_ochir(self):
        yid = self.yoq_jadval.tanlangan_id()
        if yid:
            with self.db.amal("Yo'q kunlar o'chirildi"):
                self.db.apply("yoq_kun", "DELETE", qator_id=yid)
            self.oyna.yangila()

    def _takror_qosh(self):
        nom = self.tk_nom.text().strip()
        if not nom or self.tk_summa.qiymat() <= 0:
            self.xabar.korsat("Nomi va summasi kerak.", "xato", 3000)
            return
        recurring.qosh(self.db, nom, self.tk_summa.qiymat(), self.tk_kim.odam_id(),
                       self.tk_davr.currentData(), self.tk_kun.value())
        self.tk_nom.clear()
        self.tk_summa.tozala()
        self.oyna.yangila()

    def _takror_ochir(self):
        tid = self.takror_jadval.tanlangan_id()
        if tid and tasdiq(self, "Takroriy rasxod o'chirilsinmi?"):
            recurring.ochir(self.db, tid)
            self.oyna.yangila()

    def _davr(self, holat: str):
        oy = self.d_oy.text().strip()
        if len(oy) != 7 or oy[4] != "-":
            self.xabar.korsat("Oy formati: 2026-08", "xato", 3000)
            return
        if holat == "yopilgan" and not tasdiq(
                self, f"{oy} oyi yopilsinmi?\n\n"
                      f"Shundan keyin bu oyga yozuv kiritib yoki o'zgartirib "
                      f"bo'lmaydi (keyin qayta ochish mumkin)."):
            return
        self.db.con.execute(
            "INSERT INTO davr(oy,holat,yopilgan_vaqt) VALUES(?,?,datetime('now','localtime'))"
            " ON CONFLICT(oy) DO UPDATE SET holat=excluded.holat,"
            " yopilgan_vaqt=excluded.yopilgan_vaqt", (oy, holat))
        self.xabar.korsat(
            f"{oy} oyi {'yopildi' if holat == 'yopilgan' else 'ochildi'}.", "ok", 4000)
        self.yangila()

    def _zaxira(self):
        import db as dbm
        yol = dbm.zaxira_ol(self.db.yol)
        self.xabar.korsat(f"Zaxira olindi: {yol.name if yol else '—'}", "ok", 5000)
        self.yangila()

    def _import(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Uy moliya.xlsx faylini tanlang",
            str(config.DATA.parent), "Excel (*.xlsx)")
        if not yol:
            return
        if not tasdiq(self, "Excel'dagi yozuvlar shu bazaga QO'SHILADI.\n\n"
                            "Agar avval ham ko'chirgan bo'lsangiz, yozuvlar "
                            "ikki marta tushadi. Davom etilsinmi?"):
            return
        try:
            n = importer.import_qil(self.db, yol)
        except Exception as e:
            xato_koraset(self, f"Ko'chirishda xato:\n{e}")
            return
        self.oyna.yangila()
        self.xabar.korsat(n.hisobot().replace("\n", "  "), "ok", 12000)

    # ── yangilash ────────────────────────────────────────────────────

    def yangila(self):
        with QSignalBlocker(self.tk_kim):
            self.tk_kim.yangila()
        kam, juda = ledger.chegaralar(self.db)
        self.ch_kam.qoy(kam)
        self.ch_juda.qoy(juda)
        self._tg_yukla()
        with QSignalBlocker(self.tg_odam):
            self.tg_odam.yangila()
        self._tg_nom_yukla()
        tg_nomlar = {r["id"]: (r["telegram"] or "")
                     for r in self.db.q("SELECT id, telegram FROM odam")}
        qatorlar, idlar = [], []
        for r in ledger.balanslar(self.db, hammasi=True):
            tg = tg_nomlar.get(r["id"], "")
            qatorlar.append([r["nom"],
                             f"@{tg}" if tg else "—",
                             "faol" if r["faol"] else "ro'yxatdan olingan",
                             r["naqd"], r["sof"]])
            idlar.append(r["id"])
        self.odam_jadval.tuldir(qatorlar, idlar, rangli_ustunlar={4})

        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT t.id, t.belgi, t.nom, COUNT(r.id) soni,"
                "  (SELECT COUNT(*) FROM item i WHERE i.turi_id=t.id AND i.faol=1) mh"
                " FROM turi t"
                " LEFT JOIN rasxod r ON r.turi_id=t.id AND r.ochirilgan=0"
                " WHERE t.faol=1 GROUP BY t.id ORDER BY t.tartib"):
            qatorlar.append([r["belgi"], r["nom"], r["soni"], r["mh"]])
            idlar.append(r["id"])
        self.turi_jadval.tuldir(qatorlar, idlar)
        self._mahsulotlar_yukla()

        qatorlar, idlar = [], []
        for r in self.db.q(
                "SELECT y.*, o.nom FROM yoq_kun y JOIN odam o ON o.id=y.odam_id"
                " WHERE y.ochirilgan=0 ORDER BY y.boshi DESC"):
            qatorlar.append([r["nom"], sana_qisqa(r["boshi"]),
                             sana_qisqa(r["oxiri"]), r["sabab"] or "—"])
            idlar.append(r["id"])
        self.yoq_jadval.tuldir(qatorlar, idlar)

        qatorlar, idlar = [], []
        for t in recurring.hammasi(self.db):
            qatorlar.append([t["nom"], t["summa"],
                             recurring.DAVRIYLIK.get(t["davriylik"], t["davriylik"]),
                             t["odam_nom"], sana_qisqa(t["keyingi_sana"])])
            idlar.append(t["id"])
        self.takror_jadval.tuldir(qatorlar, idlar)

        self.davr_jadval.tuldir([
            [r["oy"], "🔒 Yopilgan" if r["holat"] == "yopilgan" else "Ochiq",
             r["yopilgan_vaqt"] or "—"]
            for r in self.db.q("SELECT * FROM davr ORDER BY oy DESC")])

        zaxiralar = sorted(config.ZAXIRA.glob("farvonuy-*.db"))
        olcham = self.db.yol.stat().st_size / 1024 if self.db.yol.exists() else 0
        self.m_matn.setText(
            f"Baza: <code>{self.db.yol}</code><br>"
            f"Hajmi: {olcham:.0f} KB &nbsp;·&nbsp; "
            f"zaxira nusxalari: {len(zaxiralar)} ta "
            f"(oxirgi {config.ZAXIRA_SONI} tasi saqlanadi)<br>"
            f"Zaxira papkasi: <code>{config.ZAXIRA}</code><br>"
            f"Hisobotlar: <code>{config.EKSPORT}</code><br><br>"
            f"Har safar dastur ochilganda avtomatik zaxira olinadi.")

        self.oz_jadval.tuldir([
            [r["vaqt"], r["tavsif"],
             "↩ qaytarilgan" if r["qaytarilgan"] else "amalda"]
            for r in self.db.q(
                "SELECT vaqt, tavsif, qaytarilgan, MIN(id) i FROM ozgarishlar"
                " GROUP BY guruh_id ORDER BY i DESC LIMIT 60")])
