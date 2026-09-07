"""UI'ni ekransiz tekshirish — hamma sahifa xatosiz qurilishi kerak.

    py -3.14 src\\ui_tekshir.py

Haqiqiy ma'lumot bilan ishlaydi: Excel'dan ko'chiradi, keyin har bir
sahifani quradi va `yangila()` chaqiradi. Agar biror sahifada xato bo'lsa
shu yerda chiqadi — dastur ochilgandan keyin emas.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
for _o in (sys.stdout, sys.stderr):
    try:
        _o.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_TMP = Path(tempfile.mkdtemp(prefix="farvonuy-ui-"))
os.environ["FARVONUY_DATA"] = str(_TMP)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXCEL = r"C:\Users\Acer\Desktop\Uy moliya.xlsx"

OK, XATO = [], []


def bosqich(nom: str, ish):
    try:
        ish()
    except Exception:
        XATO.append(nom)
        print(f"[ XATO ] {nom}")
        print(traceback.format_exc())
    else:
        OK.append(nom)
        print(f"[  OK  ] {nom}")


def main() -> int:
    from PySide6.QtWidgets import QApplication

    import db as dbm
    from core import importer, ledger
    from ui.eski import theme

    app = QApplication.instance() or QApplication([])

    # ── OTASIZ widgetni KO'RSATISH taqiqlanadi
    #
    # Qt'da otasi yo'q widget — bu OYNA. Uni `setVisible(True)` bilan
    # ko'rsatsak (masalan `addWidget()` dan OLDIN), Windows unga
    # sarlavha satri chizadi: dastur ikonkasi, «yoyish», «✕». Ekranda
    # bu kichkina qora quti bo'lib chaqnab o'tadi va darhol yo'qoladi.
    # Aynan shu xato `_Blok` da bo'lgan: har bajarilgan vazifa uchun
    # bittadan, ya'ni kalendar ochilganda o'nlab marta.
    #
    # `setVisible(False)` xavfsiz — u oyna yaratmaydi.
    from PySide6.QtWidgets import QWidget as _QW
    _asl_setVisible = _QW.setVisible
    OTASIZ = []

    def _kuzatuvchi(ozi, koringan):
        try:
            if koringan and ozi.parent() is None and ozi.isWindow():
                nomi = type(ozi).__name__
                if nomi not in ("Oyna", "QMenu", "QMessageBox"):
                    iz = "".join(traceback.format_stack(limit=6)[:-1])
                    OTASIZ.append((nomi, iz))
        except Exception:
            pass
        return _asl_setVisible(ozi, koringan)

    _QW.setVisible = _kuzatuvchi

    bosqich("stil qo'llanadi", lambda: app.setStyleSheet(theme.STIL))

    _tema_tekshir()

    d = dbm.Db()
    if Path(EXCEL).exists():
        bosqich("Excel'dan ko'chirish", lambda: importer.import_qil(d, EXCEL))
    else:
        print(f"[ o'tkazildi ] {EXCEL} topilmadi — bo'sh baza bilan davom etamiz")

    bosqich("audit toza", lambda: _tasdiq(ledger.audit(d).toza, "kitob teng emas"))

    from ui.eski.oyna import HAMMA, SAHIFALAR, Oyna

    oyna = None

    def oyna_qur():
        nonlocal oyna
        oyna = Oyna(d)

    bosqich("asosiy oyna quriladi", oyna_qur)
    if oyna is None:
        return 1

    # ── bosh ekran: yon menyusiz ikkita bo'lim
    bosqich("bosh ekran birinchi ko'rinadi",
            lambda: _tasdiq(oyna.tashqi_stek.currentIndex() == 0,
                            "dastur bo'lim tanlovidan boshlanmadi"))
    bosqich("bosh ekranda tanlov sahifasi yangilanadi",
            lambda: oyna.tanlov.yangila())

    # ── tezkor tugma QOLMAGAN bo'lishi kerak
    def _tugmasiz():
        qolgan = [a.shortcut().toString() for a in oyna.actions()
                  if not a.shortcut().isEmpty()]
        _tasdiq(not qolgan, f"tezkor tugma qolib ketgan: {qolgan}")

    bosqich("tezkor tugma yo'q", _tugmasiz)

    # ── `setParent(None)` FAQAT `widgets.yoq()` ichida
    #
    # Otasiz widget Qt'da alohida OYNA. Ko'rinib turgan widgetni
    # otasidan uzsak, Windows unga bir kadrga sarlavha satri chizadi:
    # dastur ikonkasi, «yoyish» va «✕». Ekranda qora quti chaqnab
    # o'tadi. `yoq()` avval yashiradi, keyin uzadi — shuning uchun
    # uzish boshqa joyda umuman bo'lmasligi kerak.
    def _yoq_orqali():
        from pathlib import Path as P
        ildiz = P(__file__).resolve().parent / "ui" / "eski"
        aybdor = []
        for fayl in sorted(ildiz.glob("*.py")):
            if fayl.name == "widgets.py":
                continue          # `yoq()` ning o'zi shu yerda
            matn = fayl.read_text(encoding="utf-8")
            for n, qator in enumerate(matn.splitlines(), start=1):
                if "setParent(None)" in qator and not qator.strip().startswith("#"):
                    aybdor.append(f"{fayl.name}:{n}")
        _tasdiq(not aybdor,
                "setParent(None) `yoq()` dan tashqarida: "
                + ", ".join(aybdor))

    bosqich("widget o'chirish faqat yoq() orqali", _yoq_orqali)


    # ── bo'limlar
    bosqich("«Moliya» bo'limi ochiladi",
            lambda: oyna.bolim_och("moliya"))
    for i, (nom, _, _) in enumerate(SAHIFALAR):
        bosqich(f"sahifa «{nom}»", lambda n=i: oyna._sahifa(n, bosish=True))

    bosqich("«Vazifalar» bo'limi ochiladi",
            lambda: oyna.bolim_och("vazifalar"))
    siljish = len(SAHIFALAR)
    for i, (nom, _, _) in enumerate(HAMMA[siljish:]):
        bosqich(f"sahifa «{nom}»",
                lambda n=siljish + i: oyna._sahifa(n, bosish=True))

    # Indeksni nom bo'yicha topamiz — varaqlar tartibi o'zgarsa ham
    # testlar boshqa sahifani tekshirib qolmaydi.
    def _varaq(nom):
        for i, (n, _, _) in enumerate(HAMMA[siljish:], start=siljish):
            if n == nom:
                return oyna.sahifalar[i]
        raise AssertionError(f"«{nom}» varag'i topilmadi")

    # ── vazifa turlari ro'yxati (kalendar EMAS)
    turlar_sahifa = _varaq("Vazifalar")

    def _turlar_royxati():
        from core import vazifa as vz3
        _tasdiq(not hasattr(turlar_sahifa, "taqvim"),
                "«Vazifalar» varag'ida kalendar bo'lmasligi kerak")
        oldin = len(vz3.turlar(d))
        _tasdiq(oldin >= 1, "ish turlari ekilmagan")
        _tasdiq(turlar_sahifa.royxat_layout.count() == oldin,
                "ro'yxatdagi qatorlar soni turlar soniga mos emas")
        yid = vz3.tur_qosh(d, "Kir yuvish", 45)
        turlar_sahifa.yangila()
        _tasdiq(turlar_sahifa.royxat_layout.count() == oldin + 1,
                "yangi tur ro'yxatda ko'rinmadi")
        vz3.tur_ochir(d, yid)
        turlar_sahifa.yangila()
        _tasdiq(turlar_sahifa.royxat_layout.count() == oldin,
                "o'chirilgan tur ro'yxatdan chiqmadi")

    bosqich("vazifa turlari ro'yxati", _turlar_royxati)

    # ── ish qadamlari (guruhdagi xabarda ro'yxat bo'lib chiqadi)
    def _qadamlar():
        from core import vazifa as vz4
        ub = vz4.uborka_turlari(d)
        _tasdiq(len(ub) >= 1, "general uborka ishlari ekilmagan")
        tid = ub[0]["id"]
        oldin = len(vz4.qadamlar(d, tid))
        _tasdiq(oldin >= 1, "boshlang'ich qadamlar ekilmagan")
        # Yopiq holatda panel qurilmaydi
        turlar_sahifa._ochiq.clear()
        turlar_sahifa.yangila()
        turlar_sahifa._qadam_ochildi(tid, True)
        _tasdiq(tid in turlar_sahifa._ochiq, "qadamlar paneli ochilmadi")
        turlar_sahifa._qadam_qosh(tid, "Sinov qadami")
        _tasdiq(len(vz4.qadamlar(d, tid)) == oldin + 1,
                "qadam qo'shilmadi")
        _tasdiq(tid in turlar_sahifa._ochiq,
                "qadam qo'shilgach panel yopilib qoldi")
        yangi = [q for q in vz4.qadamlar(d, tid)
                 if q["nom"] == "Sinov qadami"][0]
        turlar_sahifa._qadam_ochir(yangi["id"])
        _tasdiq(len(vz4.qadamlar(d, tid)) == oldin,
                "qadam o'chirilmadi")
        turlar_sahifa._qadam_ochildi(tid, False)
        _tasdiq(tid not in turlar_sahifa._ochiq, "panel yopilmadi")

    bosqich("ish qadamlari", _qadamlar)

    # ── ochish/yopish: ro'yxat QAYTA QURILMAYDI
    def _ochish_silliq():
        from core import vazifa as vz7
        tid = vz7.uborka_turlari(d)[0]["id"]
        turlar_sahifa._ochiq.clear()
        turlar_sahifa.yangila()
        q = turlar_sahifa._qatorlar[tid]
        yopiq_h = q.height()
        _tasdiq(not q.panel.isVisibleTo(q), "panel boshida ochiq turibdi")
        q.almashtir()
        # Widget O'ZGARMAYDI — ya'ni ro'yxat qayta qurilmagan.
        _tasdiq(turlar_sahifa._qatorlar[tid] is q,
                "ochishda qator qayta qurilgan (sahifa sakraydi)")
        _tasdiq(tid in turlar_sahifa._ochiq, "holat eslab qolinmadi")
        _tasdiq(q.panel.isVisibleTo(q), "panel ochilmadi")
        # Animatsiya bor va oqilona uzunlikda
        _tasdiq(60 <= q.ANIM_MS <= 320,
                f"animatsiya uzunligi g'alati: {q.ANIM_MS} ms")
        for _ in range(60):
            app.processEvents()
        q.almashtir()
        _tasdiq(turlar_sahifa._qatorlar[tid] is q,
                "yopishda qator qayta qurilgan")
        _tasdiq(tid not in turlar_sahifa._ochiq, "yopilgani eslanmadi")
        for _ in range(60):
            app.processEvents()
        turlar_sahifa._ochiq.clear()
        turlar_sahifa.yangila()
        _tasdiq(turlar_sahifa._qatorlar[tid].height() > 0,
                f"yopilgach balandlik yo'qoldi ({yopiq_h} edi)")

    bosqich("qadamlar silliq ochiladi", _ochish_silliq)

    # ── shaxsiy tugma butun sahifani qayta qurmaydi
    def _shaxsiy_joyida():
        from core import vazifa as vz8
        tid = vz8.turlar(d)[0]["id"]
        turlar_sahifa.yangila()
        q = turlar_sahifa._qatorlar[tid]
        oldin = bool(vz8.tur_bitta(d, tid)["shaxsiy"])
        turlar_sahifa._shaxsiy_qoy(tid, not oldin)
        _tasdiq(turlar_sahifa._qatorlar[tid] is q,
                "shaxsiy tugmasi butun ro'yxatni qayta qurdi")
        kutilgan = "Shaxsiy" if not oldin else "Umumiy"
        _tasdiq(kutilgan in q.shaxsiy_tugma.text(),
                f"tugma yozuvi yangilanmadi: {q.shaxsiy_tugma.text()!r}")
        turlar_sahifa._shaxsiy_qoy(tid, oldin)

    bosqich("shaxsiy tugmasi joyida yangilanadi", _shaxsiy_joyida)

    # ── ro'yxat qayta qurilganda OTASIZ widget qolmaydi
    def _otasiz_qolmaydi():
        from PySide6.QtWidgets import QWidget
        oldin = {id(w) for w in app.topLevelWidgets()}
        varaq = _varaq("Vazifalar")
        for _ in range(3):
            varaq.yangila()
            app.processEvents()
        kal = _varaq("Kalendar")
        for _ in range(3):
            kal.yangila()
            app.processEvents()
        yangi = [w for w in app.topLevelWidgets()
                 if id(w) not in oldin and w.parent() is None
                 and not w.isHidden()]
        _tasdiq(not yangi,
                "qayta qurishdan keyin otasiz KO'RINADIGAN widget qoldi: "
                + ", ".join(type(w).__name__ for w in yangi))

    bosqich("qayta qurishda otasiz oyna qolmaydi", _otasiz_qolmaydi)

    # ── shaxsiy / umumiy almashtirgich
    def _shaxsiy_tugma():
        from core import vazifa as vz6
        from core import xabar as xb6
        tid = vz6.turlar(d)[0]["id"]
        oldin = bool(vz6.tur_bitta(d, tid)["shaxsiy"])
        turlar_sahifa._shaxsiy_qoy(tid, not oldin)
        _tasdiq(bool(vz6.tur_bitta(d, tid)["shaxsiy"]) != oldin,
                "shaxsiy bayrog'i almashmadi")
        nom = vz6.tur_bitta(d, tid)["nom"]
        _tasdiq(nom in vz6.shaxsiy_nomlari(d) if not oldin
                else nom not in vz6.shaxsiy_nomlari(d),
                "shaxsiy ro'yxatga tushmadi")
        turlar_sahifa._shaxsiy_qoy(tid, oldin)
        _tasdiq(bool(vz6.tur_bitta(d, tid)["shaxsiy"]) == oldin,
                "eski holatga qaytmadi")
        _tasdiq(isinstance(xb6.dm_yoqmaganlar(d), list),
                "dm_yoqmaganlar ro'yxat qaytarmadi")

    bosqich("shaxsiy / umumiy almashtirgich", _shaxsiy_tugma)

    # ── general uborka kartasi
    def _uborka_kartasi():
        from core import vazifa as vz5
        matn = turlar_sahifa.uborka_oldin.text()
        _tasdiq("Birinchi kun" in matn,
                f"uborka ko'rinishi bo'sh: {matn!r}")
        _tasdiq(turlar_sahifa.uborka_kun.currentData()
                == vz5.uborka_kuni(d), "uborka kuni combodan mos emas")
        oldin = len(vz5.oraliq(d, "2000-01-01", "2100-01-01"))
        turlar_sahifa.uborka_hafta.setCurrentIndex(
            turlar_sahifa.uborka_hafta.findData(2))
        reja, xato = turlar_sahifa._uborka_reja()
        _tasdiq(reja is not None, f"reja tuzilmadi: {xato}")
        _tasdiq(len(reja) == 2 * len(vz5.uborka_turlari(d)),
                "reja uzunligi noto'g'ri")
        # Kartadagi kun/soat saqlanadi va qaytib o'qiladi
        turlar_sahifa.uborka_kun.setCurrentIndex(
            turlar_sahifa.uborka_kun.findData(5))
        turlar_sahifa._uborka_saqla()
        _tasdiq(vz5.uborka_kuni(d) == 5, "uborka kuni saqlanmadi")
        vz5.uborka_kuni_qoy(d, 6)
        turlar_sahifa.yangila()
        _tasdiq(len(vz5.oraliq(d, "2000-01-01", "2100-01-01")) == oldin,
                "reja ko'rish bazaga yozib yubordi")

    bosqich("general uborka kartasi", _uborka_kartasi)

    # ── g'ildirak tanlagichni O'ZGARTIRMAYDI (sahifa aylanadi)
    def _gildirak_qalqoni():
        from PySide6.QtCore import QPoint, QPointF, Qt as Qt2
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox,
                                       QScrollArea)

        def hodisa(w):
            nuqta = QPointF(w.rect().center())
            return QWheelEvent(nuqta, w.mapToGlobal(nuqta.toPoint()).toPointF(),
                               QPoint(0, -120), QPoint(0, -120),
                               Qt2.NoButton, Qt2.NoModifier,
                               Qt2.ScrollUpdate, False)

        sinaldi = 0
        for varaq in oyna.sahifalar:
            if varaq is None:
                continue
            for w in (varaq.findChildren(QComboBox)
                      + varaq.findChildren(QAbstractSpinBox)):
                ota = w.parentWidget()
                while ota is not None and not isinstance(ota, QScrollArea):
                    ota = ota.parentWidget()
                if ota is None or not w.isEnabled():
                    continue
                oldin = (w.currentIndex() if isinstance(w, QComboBox)
                         else w.text())
                app.sendEvent(w, hodisa(w))
                app.processEvents()
                keyin = (w.currentIndex() if isinstance(w, QComboBox)
                         else w.text())
                _tasdiq(keyin == oldin,
                        f"g'ildirak {type(w).__name__} qiymatini "
                        f"o'zgartirdi ({oldin} -> {keyin})")
                sinaldi += 1
        _tasdiq(sinaldi >= 10,
                f"juda kam maydon sinaldi ({sinaldi}) — qalqon "
                f"tekshirilmagan bo'lishi mumkin")

    bosqich("g'ildirak tanlagichni o'zgartirmaydi", _gildirak_qalqoni)

    # ── kalendar yon tomonga ham aylanadi
    def _kalendar_yon():
        taqvim = _varaq("Kalendar").taqvim
        _tasdiq(taqvim.tor.minimumWidth() > 0,
                "to'rning eng kam kengligi qo'yilmagan")
        # Bosh va to'r AYNAN bir enda: ustun kengligi enidan
        # hisoblanadi, bir piksel farq ham sarlavhani siljitadi.
        _tasdiq(taqvim.bosh.width() == taqvim.tor.width(),
                f"bosh {taqvim.bosh.width()} != to'r {taqvim.tor.width()}")
        bar = taqvim.aylanma.horizontalScrollBar()
        bar.setValue(bar.maximum())
        app.processEvents()
        _tasdiq(taqvim.bosh.x() == -bar.value(),
                f"bosh to'r bilan birga surilmadi "
                f"({taqvim.bosh.x()} != {-bar.value()})")
        bar.setValue(0)
        app.processEvents()

    bosqich("kalendar yon tomonga aylanadi", _kalendar_yon)

    # ── hisobot tanlagichi FAQAT kalendarda
    def _hisobot_tanlagichi():
        kal = _varaq("Kalendar")
        _tasdiq(hasattr(kal, "hisobot_tur"), "hisobot tanlagichi yo'q")
        kalitlar = [kal.hisobot_tur.itemData(i)
                    for i in range(kal.hisobot_tur.count())]
        _tasdiq(kalitlar == ["vazifa", "umumiy", "ulush"],
                f"hisobot ro'yxati kutilganidek emas: {kalitlar}")
        _tasdiq(not hasattr(_varaq("Shaxsiy"), "_eksport"),
                "hisobot Shaxsiy varag'ida ham qolib ketgan")

    bosqich("hisobot tanlagichi", _hisobot_tanlagichi)

    # ── xabar kartasi
    def _xabar_kartasi():
        from core import vazifa as vz9
        from ui.eski.sahifa_vazifalar import XabarDialog
        tid = vz9.turlar(d)[0]["id"]
        dlg = XabarDialog(d, tid, parent=oyna)
        _tasdiq(dlg.bosh.text() == vz9.tur_bitta(d, tid)["nom"],
                "kartada ishning nomi yo'q")
        _tasdiq("Kunlik ro'yxat" in dlg.qachon_matn.text(),
                "qachon yuborilishi yozilmagan")
        _tasdiq(len(dlg.k_matn.text()) > 10, "kunlik matn bo'sh")
        _tasdiq(len(dlg.e_matn.text()) > 10, "eslatma matni bo'sh")
        _tasdiq("Hali yo'q" in dlg.tugma_matn.text(),
                "kechiktirish tugmasi tushuntirilmagan")
        oldin = vz9.tur_bitta(d, tid)["davomiylik"]
        dlg.davomiylik.setValue(oldin + 5)
        dlg._saqla()
        _tasdiq(vz9.tur_bitta(d, tid)["davomiylik"] == oldin + 5,
                "kartadan davomiylik saqlanmadi")
        vz9.tur_davomiylik_qoy(d, tid, oldin)

    bosqich("xabar kartasi", _xabar_kartasi)

    # ── odatlar (streak)
    def _odatlar():
        from datetime import timedelta as _td9
        from core import vazifa as vz10
        varaq = _varaq("Vazifalar")
        _tasdiq(hasattr(varaq, "streaklar_quti"), "odatlar kartasi yo'q")
        odam = d.q1("SELECT id FROM odam WHERE faol=1 ORDER BY tartib")["id"]
        tur = vz10.turlar(d)[0]["id"]
        varaq.streak_odam.setCurrentIndex(
            varaq.streak_odam.findData(odam))
        varaq.streak_tur.setCurrentIndex(varaq.streak_tur.findData(tur))
        varaq.streak_nishon.setCurrentIndex(0)
        varaq._streak_qosh()
        _tasdiq(len(vz10.streaklar(d)) == 1, "odat qo'shilmadi")
        # Bo'sh ro'yxatda ham bitta yorliq turadi, shuning uchun
        # SON emas, widget TURI tekshiriladi.
        from ui.eski.sahifa_vazifalar import _StreakQator
        w = varaq.streaklar_layout.itemAt(0).widget()
        _tasdiq(isinstance(w, _StreakQator),
                f"odat ro'yxatda ko'rinmadi ({type(w).__name__})")
        s10 = vz10.streaklar(d)[0]
        h = vz10.streak_holati(d, s10)
        _tasdiq(h["nishon"] == 7, f"nishon 7 emas: {h['nishon']}")
        vz10.streak_ochir(d, s10["id"])
        varaq.yangila()
        _tasdiq(len(vz10.streaklar(d)) == 0, "odat to'xtatilmadi")

    bosqich("odatlar kartasi", _odatlar)


    # ── menyu (guruhdagi «Menyuyimizda nimalar bor» shu ro'yxatni beradi)
    def _menyu_royxati():
        from core import menyu as mn3
        oldin = len(mn3.royxat(d))
        _tasdiq(oldin >= 1, "boshlang'ich menyu ekilmagan")
        _tasdiq(turlar_sahifa.taomlar_layout.count() == oldin,
                "menyudagi qatorlar soni taomlar soniga mos emas")
        tid = mn3.qosh(d, "Somsa")
        turlar_sahifa.yangila()
        _tasdiq(turlar_sahifa.taomlar_layout.count() == oldin + 1,
                "yangi taom ro'yxatda ko'rinmadi")
        mn3.ochir(d, tid)
        turlar_sahifa.yangila()
        _tasdiq(turlar_sahifa.taomlar_layout.count() == oldin,
                "o'chirilgan taom ro'yxatdan chiqmadi")

    bosqich("menyu ro'yxati", _menyu_royxati)

    from ui.eski.sahifa_vazifalar import TurDialog
    def _tur_dialog():
        dlg = TurDialog(d, parent=oyna)
        _tasdiq(dlg.kimga.count() == 2, "umumiy/shaxsiy tanlovi yo'q")
        _tasdiq(dlg.kimga.currentData() is False,
                "birlamchi tanlov umumiy bo'lishi kerak")
        _tasdiq(dlg.kimga.itemData(1) is True, "shaxsiy tanlovi yo'q")

    bosqich("dialog «Yangi vazifa turi»", _tur_dialog)

    def _biriktirish_oynasi():
        from core import vazifa as vz4
        from ui.eski.sahifa_vazifalar import VazifaDialog as VD
        tur = vz4.turlar(d)[0]
        dlg = VD(d, tur=tur, parent=oyna)
        _tasdiq(dlg.nom.currentText() == tur["nom"],
                "biriktirish oynasida ish nomi qo'yilmagan")
        _tasdiq(not dlg.nom.isEnabled(),
                "biriktirishda ish nomi o'zgartirib bo'lmasligi kerak")

    bosqich("biriktirish oynasi tur bilan ochiladi", _biriktirish_oynasi)

    kalendar = _varaq("Kalendar")
    for j, (nom, _) in enumerate(kalendar.KORINISH):
        bosqich(f"kalendar «{nom}»", lambda n=j: kalendar._korinish_ozgardi(n))
    bosqich("kalendar: oldingi/keyingi", lambda: (kalendar._sur(-1),
                                                  kalendar._sur(1)))
    bosqich("kalendar: bugunga qaytish", lambda: kalendar._bugunga())

    # ── shaxsiy varaq: faqat bitta odamniki
    shaxsiy = _varaq("Shaxsiy")

    def _shaxsiy_bir_odam():
        from core import vazifa as vz2
        odamlar = d.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib")
        if len(odamlar) < 2:
            return
        # Ikkinchi odamga bitta vazifa yozamiz, keyin birinchisiga
        # o'tib, uning varag'ida chiqmasligini tekshiramiz.
        vz2.qosh(d, "Musorlarni tashlash", odamlar[1]["id"], date.today(),
                 "18:00")
        shaxsiy.kim.tanla(odamlar[0]["id"])
        shaxsiy.yangila()
        _tasdiq(shaxsiy.kim.odam_id() == odamlar[0]["id"],
                "shaxsiy varaq odamni almashtirmadi")
        nomlar = {shaxsiy.jadval.item(i, 2).text()
                  for i in range(shaxsiy.jadval.rowCount())}
        _tasdiq("Musorlarni tashlash" not in nomlar,
                "shaxsiy varaqda boshqa odamning vazifasi ko'rindi")
        shaxsiy.kim.tanla(odamlar[1]["id"])
        shaxsiy.yangila()
        nomlar2 = {shaxsiy.jadval.item(i, 2).text()
                   for i in range(shaxsiy.jadval.rowCount())}
        _tasdiq("Musorlarni tashlash" in nomlar2,
                "shaxsiy varaq o'z vazifasini ko'rsatmadi")

    bosqich("shaxsiy varaq: faqat o'z vazifalari", _shaxsiy_bir_odam)
    bosqich("shaxsiy varaq: hafta almashadi",
            lambda: (shaxsiy._sur(-1), shaxsiy._sur(1), shaxsiy._bugunga()))

    bosqich("bosh ekranga qaytish", lambda: oyna.boshga())
    bosqich("«Moliya» ga qaytish", lambda: oyna.bolim_och("moliya"))

    # dialoglar
    from ui.eski.dialogs import (KirimDialog, QarzDialog, RasxodDialog, TolovDialog,
                            YoqKunDialog)
    for nom, sinf in (("Rasxod", RasxodDialog), ("Kirim", KirimDialog),
                      ("Qarz", QarzDialog), ("To'lov", TolovDialog),
                      ("Yo'q kun", YoqKunDialog)):
        bosqich(f"dialog «{nom}»", lambda s=sinf: s(d, parent=oyna))

    # rasxod dialogini mavjud yozuv bilan
    r = d.q1("SELECT id FROM rasxod WHERE umumiymi=1 AND ochirilgan=0 LIMIT 1")
    if r:
        bosqich("dialog «Rasxod» (tahrirlash)",
                lambda: RasxodDialog(d, r["id"], parent=oyna))
        # Bekor qilish endi shu oynada — quriladimi?
        from ui.eski.dialogs import RasxodTafsilot
        bosqich("dialog «Rasxod tafsiloti»",
                lambda: RasxodTafsilot(d, r["id"], parent=oyna))

    # ── juftlik qarzi: qatorga bosilganda ochiladigan oyna
    def _juft_tafsilot():
        from core import ledger as lg
        from ui.eski.dialogs import JuftTafsilot
        juftlar = lg.juft_qarzlar(d)
        if not juftlar:
            return
        j = juftlar[0]
        dlg = JuftTafsilot(d, j.qarzdor_id, j.kreditor_id, parent=oyna)
        tarkib = lg.juft_tarkibi(d, j.qarzdor_id, j.kreditor_id)
        _tasdiq(sum(x["summa"] for x in tarkib) == j.summa,
                "tafsilot yig'indisi juftlik summasidan farq qiladi")
        _tasdiq(dlg.jami_yorliq.text().strip() != "",
                "tafsilot oynasida jami ko'rsatilmadi")

    bosqich("dialog «Juftlik qarzi tafsiloti»", _juft_tafsilot)

    # vazifa oynalari
    from core import vazifa as vz
    from ui.eski.sahifa_vazifalar import VazifaDialog, VazifaTafsilot
    bosqich("dialog «Vazifa»", lambda: VazifaDialog(d, parent=oyna))
    kim = d.q1("SELECT id FROM odam WHERE faol=1 ORDER BY tartib LIMIT 1")
    if kim:
        vid = None

        def _vazifa_qosh():
            nonlocal vid
            vid = vz.qosh(d, "Ovqat qilish", kim["id"], date.today(), "09:00")

        bosqich("vazifa yoziladi", _vazifa_qosh)
        bosqich("dialog «Vazifa» (tahrirlash)",
                lambda: VazifaDialog(d, vid, parent=oyna))
        bosqich("dialog «Vazifa tafsiloti»",
                lambda: VazifaTafsilot(d, vid, parent=oyna))
        bosqich("kalendarda vazifa ko'rinadi",
                lambda: _tasdiq(len(vz.hafta(d, date.today())) >= 1,
                                "kalendar vazifani ko'rmadi"))

    bosqich("undo", lambda: d.undo())
    bosqich("redo", lambda: d.redo())
    bosqich("umumiy yangilash", lambda: oyna.yangila())

    def _otasiz_korsatilmadi():
        if OTASIZ:
            nomi, iz = OTASIZ[0]
            _tasdiq(False,
                    f"otasiz widget ko'rsatildi ({len(OTASIZ)} marta), "
                    f"birinchisi {nomi}:\n{iz}")

    bosqich("otasiz widget ko'rsatilmadi", _otasiz_korsatilmadi)

    # hisobotlar
    from core import plan, reports
    dan, gacha = "2026-08-01", plan.oy_oxiri()
    bosqich("HTML hisobot", lambda: reports.html_hisobot(d, dan, gacha))
    bosqich("Excel hisobot", lambda: reports.excel(d, dan, gacha))

    d.yop()
    print("\n" + "═" * 62)
    print(f"  OK: {len(OK)}     XATO: {len(XATO)}")
    for x in XATO:
        print("   -", x)
    print("═" * 62)
    return 1 if XATO else 0


# ── dizayn tizimi (spetsifikatsiya §2, qiymatlar HTML ko'rgazmasidan) ──
#
# Kontrast ikkiga bo'lingan va buning sababi bor:
#
#   MUHIM juftliklar — asosiy matn, nishon ichidagi yozuv, to'ldirilgan
#   tugma ustidagi matn. Bular 4.5:1 dan past bo'lsa test YIQILADI.
#
#   YORDAMCHI juftliklar — `matn3` (maslahat), ogohlantirish ranglari,
#   `neytral`. Bular HTML ko'rgazmasidan AYNAN olingan va bir qismi
#   4.5:1 dan past. Brif qoidasi aniq: piksel uchun HTML ustun (spec
#   §13.5 dan ham). Shuning uchun ular yiqitmaydi, lekin hisobotda
#   ko'rsatiladi — jimgina o'tib ketmasin.

MUHIM_JUFT = [
    ("matn", "fon"), ("matn", "sirt"), ("matn", "sirt2"),
    ("matn", "sirt_hover"), ("matn", "sirt_tanlangan"),
    ("matn2", "sirt"),
    ("aksent", "sirt"), ("aksent", "fon"),
    ("aksent_ustida", "aksent_tola"),
    ("aksent_fon_matn", "aksent_fon"),
    ("yashil", "sirt"), ("qizil", "sirt"),
    ("yashil_fon_matn", "yashil_fon"),
    ("qizil_fon_matn", "qizil_fon"),
    ("toq_sariq_fon_matn", "toq_sariq_fon"),
    ("sariq_fon_matn", "sariq_fon"),
]
YORDAMCHI_JUFT = [
    ("matn2", "fon"),
    ("matn3", "sirt"), ("matn3", "sirt2"), ("matn3", "fon"),
    ("toq_sariq", "sirt"), ("sariq", "sirt"), ("neytral", "sirt"),
]
KONTRAST_CHEGARA = 4.5


def _tema_tekshir():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from ui import theme as T
    from ui import widgets as Q

    def kalitlar_bir_xil():
        asos = set(T.ILIQ)
        for nom, p in T.TOKENLAR.items():
            _tasdiq(set(p) == asos,
                    f"«{nom}» rejimida token kalitlari boshqacha")

    bosqich("tema: uchala rejimda token kalitlari bir xil", kalitlar_bir_xil)

    def muhim_kontrast():
        past = []
        for kalit, _ in T.REJIMLAR:
            T.rejim_qoy(kalit)
            for a, b in MUHIM_JUFT:
                k = T.kontrast(T.R(a), T.R(b))
                if k < KONTRAST_CHEGARA:
                    past.append(f"{kalit}: {a}/{b} = {k:.2f}")
        T.rejim_qoy("iliq")
        _tasdiq(not past, "muhim matn kontrasti past — " + "; ".join(past))

    bosqich(f"tema: muhim juftliklar >= {KONTRAST_CHEGARA}:1 "
            f"(3 rejim x {len(MUHIM_JUFT)})", muhim_kontrast)

    def yordamchi_kontrast_hisoboti():
        past = []
        for kalit, _ in T.REJIMLAR:
            T.rejim_qoy(kalit)
            for a, b in YORDAMCHI_JUFT:
                k = T.kontrast(T.R(a), T.R(b))
                if k < KONTRAST_CHEGARA:
                    past.append(f"{kalit} {a}/{b}={k:.2f}")
        T.rejim_qoy("iliq")
        if past:
            print(f"       HTML'dan kelgan {len(past)} ta yordamchi juftlik "
                  f"{KONTRAST_CHEGARA}:1 dan past:")
            for x in past:
                print(f"         - {x}")

    bosqich("tema: yordamchi kontrast hisoboti", yordamchi_kontrast_hisoboti)

    def notogri_token_xato_beradi():
        try:
            T.R("bunday_token_yoq")
        except KeyError:
            return
        raise AssertionError("noma'lum token KeyError bermadi")

    bosqich("tema: noma'lum token darhol xato beradi",
            notogri_token_xato_beradi)

    def qss_quriladi():
        for kalit, _ in T.REJIMLAR:
            T.rejim_qoy(kalit)
            q = T.qss()
            _tasdiq(len(q) > 2000, f"«{kalit}» uslubi juda qisqa")
            # CLAUDE.md qoidasi: bu selektorlar Qt'ning standart chizishini
            # to'xtatadi va strelka umuman yo'qoladi. Izohlarda ular haqida
            # ogohlantirish YOZILGAN — shuning uchun izohlarni tashlaymiz.
            selektorlar = re.sub(r"/\*.*?\*/", "", q, flags=re.S)
            for taqiq in ("::drop-down", "::down-arrow", "::up-button"):
                _tasdiq(taqiq not in selektorlar,
                        f"QSS'da {taqiq} selektori bor — strelka yo'qoladi")
            QApplication.instance().setStyleSheet(q)
        T.rejim_qoy("iliq")

    bosqich("tema: uchala rejimning QSS'i quriladi va qo'llanadi",
            qss_quriladi)

    def shriftlar():
        _tasdiq(bool(T.shriftlarni_yukla()), "shrift oilasi aniqlanmadi")
        for rol in T.ROLLAR:
            f = T.shrift(rol)
            kutilgan = T.olcham(rol) * 0.75
            _tasdiq(abs(f.pointSizeF() - kutilgan) < 0.01,
                    f"«{rol}» o'lchami mos emas: {f.pointSizeF()} != {kutilgan}")
        # HTML'dagi kasr o'lchamlar (11.5 / 12.5 px) aynan saqlanishi shart
        _tasdiq(abs(T.olcham("yorliq") - 11.5) < 1e-9, "11.5 px yo'qoldi")
        _tasdiq(abs(T.olcham("jadval") - 12.5) < 1e-9, "12.5 px yo'qoldi")
        for rol in ("pul", "jadval_pul", "raqam", "holat_katta"):
            _tasdiq(len(T.shrift(rol).featureTags()) == 1,
                    f"«{rol}» da tnum yoqilmagan")
        _tasdiq(not T.shrift("asos").featureTags(),
                "oddiy matnga tnum kerak emas")

    bosqich("tema: shriftlar, kasr o'lchamlar va tabular raqamlar", shriftlar)

    def darajalar_core_bilan_mos():
        from core import ledger
        kerak = set(ledger.HOLAT_NOM) | {"manfiy"}
        for kalit, _ in T.REJIMLAR:
            T.rejim_qoy(kalit)
            for h in kerak:
                asos, fon, matn_rang = T.daraja_rangi(h)
                _tasdiq(all(x.startswith("#") for x in (asos, fon, matn_rang)),
                        f"«{h}» darajasi rangsiz")
                _tasdiq(T.kontrast(matn_rang, fon) >= KONTRAST_CHEGARA,
                        f"{kalit}: «{h}» nishonining matni fonida o'qilmaydi")
        _tasdiq(sum(u for u, _ in T.ZINAPOYA) == 100,
                "zinapoya bo'laklari 100% ga teng emas")
        T.rejim_qoy("iliq")

    bosqich("tema: pul darajalari core.ledger bilan mos",
            darajalar_core_bilan_mos)

    def rejim_signali():
        kelgan = []
        T.XABARCHI.ozgardi.connect(kelgan.append)
        T.rejim_qoy("tungi")
        T.rejim_qoy("iliq")
        _tasdiq(kelgan == ["tungi", "iliq"], f"signal kelmadi: {kelgan}")

    bosqich("tema: rejim almashgani e'lon qilinadi", rejim_signali)

    def komponentlar_quriladi():
        # Komponentlar OTALI quriladi: otasiz widgetni `korsat()`
        # bilan ko'rsatish Qt'da alohida OYNA ochadi va ekranda
        # kichkina quti chaqnab o'tadi (pastdagi «otasiz widget»
        # tekshiruvi aynan shuni ushlaydi).
        from PySide6.QtWidgets import QWidget as _Uy
        uy = _Uy()
        Q.tugma("Qo'shish", "asosiy")
        Q.tugma("O'chirish", "xavfli")
        Q.Karta("Sarlavha").qosh(Q.matn("ichida"))
        Q.RaqamKarta("Real balans", -102_334, "izoh", rangli=True)
        n = Q.Nishon("kitob teng", "ok")
        n.daraja_qoy("qarzda")
        pm = Q.PulMaydon(1_559_000)
        _tasdiq(pm.qiymat() == 1_559_000, "PulMaydon qiymati yo'qoldi")
        pm.maydon.setText("1,5 mln")
        _tasdiq(pm.qiymat() == 1_500_000, "«1,5 mln» tushunilmadi")
        pm.maydon.setText("salom")
        _tasdiq(not pm.togrimi(), "noto'g'ri pul xato holatini ko'rsatmadi")
        _tasdiq(Q.SanaMaydon("2026-08-30").iso() == "2026-08-30", "sana buzildi")
        seg = Q.SegmentTugma([("u", "Umumiy"), ("s", "Shaxsiy")])
        seg.qoy("s")
        _tasdiq(seg.qiymat() == "s", "segment almashmadi")
        j = Q.Jadval(["Sana", "Summa"], pul_ustunlar={1})
        j.tuldir([["30.08.2026", 519_667]], [7])
        _tasdiq(j.j.item(0, 0).data(Qt.UserRole) == 7, "jadval id yo'qoldi")
        j.tuldir([])
        _tasdiq(j.bosh.isVisible() or not j.j.isVisible(),
                "bo'sh jadvalda BoshHolat chiqmadi")
        Q.DarajaChiziq().qoy(0.4, "kam")
        Q.XabarQatori(uy).korsat("saqlandi", "ok", qaytarish=lambda: None)
        Q.Banner(uy).korsat("kitob teng emas", "xato")
        yp = Q.YopishqoqPanel(uy)
        yp.amal_qosh("To'landi", lambda: None)
        yp.yangila(3, 890_000, "blok")
        Q.YonSubNav().bolim_qosh("Ko'rinish", Q.Karta("K"))
        Q.HolatSatri().qoy("Ctrl+Z: ...")
        Q.Oyna("Yangi rasxod").xato("sinov")

    bosqich(f"vidjetlar: {len(Q.__all__)} ta komponent quriladi va ishlaydi",
            komponentlar_quriladi)

    def rejim_almashsa_yiqilmaydi():
        """O'chirilgan widget rejim signalida dasturni yiqitmasligi kerak."""
        import gc
        for _ in range(3):
            k = Q.Karta("vaqtinchalik")
            k.qosh(Q.RaqamKarta("R", 1, "i"))
            k.deleteLater()
            del k
        gc.collect()
        QApplication.processEvents()
        for kalit, _ in T.REJIMLAR:
            T.rejim_qoy(kalit)
        T.rejim_qoy("iliq")

    bosqich("vidjetlar: o'chirilgan widget rejim almashuvida yiqitmaydi",
            rejim_almashsa_yiqilmaydi)


def _tasdiq(shart, xabar):
    if not shart:
        raise AssertionError(xabar)


if __name__ == "__main__":
    try:
        kod = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(kod)
