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

    # ── Analitika: doira har rejimda chiziladi va rangi yetadi
    def _analitika():
        from core import ledger as lg
        from ui.eski import theme as th
        i = [n for n, _, _ in SAHIFALAR].index("Analitika")
        s = oyna.sahifalar[i]
        from ui.eski.sahifa_analitika import bolak_ranglari
        for rejim, palitra in th._PALITRA.items():
            for n in range(1, 41):
                for oxiri in ([], ["qolgan"], ["qolgan", "kategoriyasiz"]):
                    turlar = ["turi"] * n + oxiri
                    r = bolak_ranglari(turlar, palitra["TUR_RANG"])
                    halqa = r + r[:1]
                    _tasdiq(all(a is None or b is None or a != b
                                for a, b in zip(halqa, halqa[1:]))
                            or n == 1,
                            f"«{rejim}»: {n} ta bo'lakda qo'shni ranglar bir xil")
        s._oraliq("2000-01-01", "2100-12-31")
        _tasdiq(s.doira._bolaklar
                == lg.doira_bolaklari(d, "2000-01-01", "2100-12-31"),
                "doira oraliq o'zgarganda yangilanmadi")
        _tasdiq(s.hamma_karta.isHidden(), "«Hamma kategoriyalar» ko'rinib turibdi")
        # «Yana 6 ta» — kategoriya qolmaguncha; «Yig'ish» — 6 taga qaytadi
        for _ in range(20):
            if s.t_yana.isHidden():
                break
            oldin = sum(1 for b in s.doira._bolaklar if b["tur"] == "turi")
            s.t_yana.click()
            _tasdiq(sum(1 for b in s.doira._bolaklar if b["tur"] == "turi")
                    > oldin, "«Yana 6 ta» yangi kategoriya ochmadi")
        _tasdiq(all(b["tur"] != "qolgan" for b in s.doira._bolaklar),
                "hammasi ochilgandan keyin ham «Qolganlari» qoldi")
        _tasdiq(s.doira.minimumHeight() >= (len(s.doira._bolaklar) + 1)
                * s.doira.QATOR, "ro'yxat uzayganda doira o'smadi")
        s.doira.resize(900, s.doira.minimumHeight())
        s.doira.grab()
        if not s.t_yigish.isHidden():
            s.t_yigish.click()
            _tasdiq(sum(1 for b in s.doira._bolaklar if b["tur"] == "turi")
                    <= lg.DOIRA_QADAM, "«Yig'ish» 6 taga qaytarmadi")
        _tasdiq(sum(s.doira._burchaklar) in (0, 360 * 16),
                "doira burchaklari 360° emas")
        eski = th.REJIM
        try:
            for rejim in th._PALITRA:
                th.rejim_qoy(rejim)
                s.doira.resize(900, 320)
                s.doira.grab()          # paintEvent yiqilmasin
            s.doira.qoy([])
            s.doira.grab()              # bo'sh holat ham chiziladi
        finally:
            th.rejim_qoy(eski)
            s.yangila()

    bosqich("Analitika: doira", _analitika)

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

    # ── takroriy vazifa: «Takrorlansin» qutisi bitta QOIDA yozadi va
    # kalendarni ufqqacha to'ldiradi. Test o'zidan keyin tozalaydi —
    # keyingi bosqichlar o'sha bazada ishlaydi.
    def _takror_oynasi():
        from datetime import timedelta
        from core import vazifa as vz5
        from ui.eski.sahifa_vazifalar import VazifaDialog as VD, _TakrorQator
        odam = d.q1("SELECT id FROM odam WHERE faol=1 ORDER BY tartib")["id"]
        dlg = VD(d, parent=oyna)
        _tasdiq(dlg.takrorli, "yangi vazifada takror kartasi yo'q")
        _tasdiq(not dlg.kunlar_qator.isVisibleTo(dlg),
                "kun qutilari «har kuni» da ko'rinmasligi kerak")
        dlg.nom.setCurrentText("Namoz o'qish")
        dlg.odam.tanla(odam)
        dlg.takror.setChecked(True)
        dlg.naqsh.setCurrentIndex(
            dlg.naqsh.findData(vz5.NAQSH_KUNLAR))
        _tasdiq(dlg.kunlar_qator.isVisibleTo(dlg),
                "«tanlangan kunlar» da qutilar ko'rinishi kerak")
        dlg.naqsh.setCurrentIndex(dlg.naqsh.findData(vz5.NAQSH_KUNLIK))
        _tasdiq(str(vz5.TAKROR_UFQ) in dlg.takror_korsat.text(),
                "oldindan ko'rsatishda ufq yozilmagan")
        dlg._saqla()

        qoidalar = [t for t in vz5.takrorlar(d) if t["nom"] == "Namoz o'qish"]
        _tasdiq(len(qoidalar) == 1, "takror qoidasi yozilmadi")
        kunlar = [v for v in vz5.oraliq(
            d, date.today().isoformat(),
            (date.today() + timedelta(days=vz5.TAKROR_UFQ)).isoformat())
            if v["nom"] == "Namoz o'qish"]
        _tasdiq(len(kunlar) == vz5.TAKROR_UFQ + 1,
                f"kalendar to'lmadi: {len(kunlar)}")

        varaq = _varaq("Vazifalar")
        varaq.yangila()
        w = varaq.takrorlar_layout.itemAt(0).widget()
        _tasdiq(isinstance(w, _TakrorQator),
                f"takror ro'yxatda ko'rinmadi ({type(w).__name__})")

        # tozalash: qoida ham, undan chiqqan kunlar ham
        vz5.takror_ochir(d, qoidalar[0]["id"])
        varaq.yangila()
        _tasdiq(not [v for v in vz5.oraliq(
            d, date.today().isoformat(),
            (date.today() + timedelta(days=vz5.TAKROR_UFQ)).isoformat())
            if v["nom"] == "Namoz o'qish"], "takror kunlari tozalanmadi")

    bosqich("takroriy vazifa oynasi", _takror_oynasi)

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
        tarkib = lg.juft_tolanmagan(d, j.qarzdor_id, j.kreditor_id)
        _tasdiq(sum(x["summa"] for x in tarkib) == j.summa,
                "tafsilot yig'indisi juftlik summasidan farq qiladi")
        _tasdiq(dlg.jadval.rowCount() == len(tarkib),
                "tafsilotda to'lanmaganlardan boshqa qator bor")
        _tasdiq(dlg.jami_yorliq.text().strip() != "",
                "tafsilot oynasida jami ko'rsatilmadi")

    bosqich("dialog «Juftlik qarzi tafsiloti»", _juft_tafsilot)

    # ── tashqi qarz: dialog orqali yoziladi, Qarz varag'ida chiqadi
    def _tashqi_qarz():
        from core import ledger as lg
        from core import entries
        from ui.eski.dialogs import (TashqiQarzDialog, TashqiQarzOyna,
                                     TashqiTolovDialog)
        from ui.eski.oyna import HAMMA as _H
        dlg = TashqiQarzDialog(d, parent=oyna)
        dlg.kimdan.setCurrentText("Sinov aka")
        dlg.summa.qoy(123_000)
        dlg._saqla()
        _tasdiq(dlg.result() == 1, "tashqi qarz saqlanmadi")
        q = next(r for r in lg.tashqi_qarzlar(d) if r["kimdan"] == "Sinov aka")
        sahifa = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                     if x[0] == "Qarz"))
        sahifa.yangila()
        _tasdiq("Sinov aka" in sahifa.tashqi_xulosa.text(),
                "tashqi qarz Qarz varag'idagi xulosada ko'rinmadi")
        _tasdiq("·" in sahifa.tashqi_tugma.text(),
                "«Tashqaridan qarz» tugmasida qoldiq yo'q")

        # Alohida oyna: ro'yxat, kimga qancha, yozish, yopish
        w = TashqiQarzOyna(d, parent=oyna)
        idlar = [w.jadval.item(i, 0).data(0x0100)
                 for i in range(w.jadval.rowCount())]
        _tasdiq(q["id"] in idlar, "tashqi qarz oynada ko'rinmadi")
        _tasdiq(any(w.kimga_jadval.item(i, 0).text() == "Sinov aka"
                    for i in range(w.kimga_jadval.rowCount())),
                "«Kimga qancha qaytarish kerak» da yo'q")
        t = TashqiTolovDialog(d, q["id"], parent=w)
        _tasdiq(t.summa.qiymat() == 123_000, "qaytarish summasi qoldiqdan olinmadi")
        t._saqla()
        _tasdiq(lg.audit(d).toza, "tashqi qarzdan keyin audit qizil")

        w.forma.kimdan.setCurrentText("Oyna aka")
        w.forma.summa.qoy(40_000)
        w._qosh()
        yangi = next((r for r in lg.tashqi_qarzlar(d) if r["kimdan"] == "Oyna aka"),
                     None)
        _tasdiq(yangi is not None and yangi["summa"] == 40_000,
                "oynadagi forma qarz yozmadi")
        _tasdiq(w.ozgardi and w.forma.summa.qiymat() == 0,
                "yozilgandan keyin forma tozalanmadi")
        qator_ = next(i for i in range(w.jadval.rowCount())
                      if w.jadval.item(i, 0).data(0x0100) == yangi["id"])
        w.jadval.setCurrentCell(qator_, 0)
        w._yop(soramasdan=True)
        _tasdiq(entries.tashqi_qoldiq(d, yangi["id"]) == 0, "qarz yopilmadi")
        _tasdiq(yangi["id"] not in [w.jadval.item(i, 0).data(0x0100)
                                    for i in range(w.jadval.rowCount())],
                "yopilgan qarz ochiqlar ro'yxatida qoldi")
        _tasdiq(lg.audit(d).toza, "qarz yopilgach audit qizil")
        w.close()

    bosqich("tashqi qarz: yozish va qaytarish", _tashqi_qarz)

    # ── umumiy tashqi qarz: oynadan umumiy yozish va mavjudini almashtirish
    def _umumiy_tashqi():
        from core import ledger as lg
        from ui.eski.dialogs import TashqiQarzDialog, TashqiUmumiyDialog
        dlg = TashqiQarzDialog(d, parent=oyna)
        dlg.kimdan.setCurrentText("Umumiy sinov")
        dlg.summa.qoy(90_000)
        dlg.umumiy.setChecked(True)
        _tasdiq(not dlg.odamlar.isHidden(), "umumiy belgilanganda odamlar chiqmadi")
        _tasdiq([lb.text().replace(" ", " ").replace(" ", " ")
                 for lb in dlg.odamlar.ulush.values()].count("30 000") == 3,
                "ulushlar oldindan ko'rinmadi")
        # rasxoddagidek sozlanadi: aniq summa
        dlg.odamlar.usul_t["aniq"].setChecked(True)
        ids = list(dlg.odamlar.qiymat)
        dlg.odamlar.qiymat[ids[0]].setText("60000")
        dlg.odamlar.qiymat[ids[1]].setText("30000")
        dlg.odamlar.belgilar[ids[2]].setChecked(False)
        _tasdiq(dlg.odamlar.tekshir() is None, "aniq bo'lish rad etildi")
        dlg._saqla()
        q = next(r for r in lg.tashqi_qarzlar(d) if r["kimdan"] == "Umumiy sinov")
        _tasdiq(q["umumiy"] == 1, "umumiy saqlanmadi")
        _tasdiq(sorted(r["summa"] for r in d.q(
            "SELECT summa FROM tashqi_ulush WHERE qarz_id=? AND tolov_id IS NULL"
            " AND ochirilgan=0", q["id"])) == [30_000, 60_000],
            "aniq ulushlar saqlanmadi")
        from ui.eski.dialogs import TashqiTolovDialog
        td = TashqiTolovDialog(d, q["id"], parent=oyna)
        _tasdiq(td.odamlar is not None and td.odamlar.usul() == "ogirlik",
                "qaytarishda bo'lish tanlovi yo'q")
        td.summa.qoy(30_000)
        td.odamlar.usul_t["teng"].setChecked(True)
        td._saqla()
        _tasdiq(sorted(r["summa"] for r in d.q(
            "SELECT u.summa FROM tashqi_ulush u JOIN tashqi_tolov t"
            " ON t.id=u.tolov_id WHERE u.qarz_id=? AND u.ochirilgan=0",
            q["id"])) == [15_000, 15_000], "qaytarish teng bo'linmadi")
        _tasdiq(lg.audit(d).toza, "umumiy qaytarishdan keyin audit qizil")
        _tasdiq(lg.audit(d).toza, "umumiy qarzdan keyin audit qizil")
        u = TashqiUmumiyDialog(d, q["id"], parent=oyna)
        u.umumiy.setChecked(False)
        u._saqla()
        _tasdiq(d.skalyar("SELECT umumiy FROM tashqi_qarz WHERE id=?", q["id"]) == 0,
                "shaxsiy qilinmadi")
        _tasdiq(lg.audit(d).toza, "shaxsiy qilingach audit qizil")

    bosqich("tashqi qarz: umumiy qilish", _umumiy_tashqi)

    # ── ikonkali kategoriya: nom berish → rasxod tanlagichida chiqadi
    def _kategoriya():
        from core import kategoriya as kt
        from ui.eski.dialogs import RasxodDialog
        from ui.eski.oyna import HAMMA as _H
        from ui.eski.sahifa_kategoriya import NomDialog
        sahifa = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                     if x[2].__name__ == "KategoriyaSahifa"))
        sahifa.yangila()
        fayl = kt.belgilar()[5]
        _tasdiq(len(sahifa.kataklar) == len(kt.belgilar()),
                "hamma ikonka sahifada emas")
        _tasdiq(sahifa.kataklar[fayl].text() == "",
                "nomsiz ikonkada yozuv bor")
        _tasdiq([x.text() for x in sahifa.guruh_sarlavhalari]
                == [kt.guruh_nomi(g) for g in
                    dict.fromkeys(kt.guruh(f) for f in kt.belgilar())],
                "guruh sarlavhalari mos emas")
        _tasdiq("Shaxsiy" in [x.text() for x in sahifa.guruh_sarlavhalari],
                "«Shaxsiy» guruhi sarlavhasi yo'q")
        dlg = NomDialog(d, fayl, parent=oyna)
        dlg.nom.setText("Sinov kategoriya")
        dlg._saqla()
        sahifa.yangila()
        _tasdiq(sahifa.kataklar[fayl].toolTip() == "Sinov kategoriya"
                and sahifa.kataklar[fayl].text().startswith("Sinov"),
                "nom katakchada ko'rinmadi")
        tid = kt.nomlanganlar(d)[fayl]["id"]
        r = RasxodDialog(d, parent=oyna)
        i = r.turi.asosiy.findData(tid)
        _tasdiq(i >= 0, "yangi kategoriya rasxod oynasida yo'q")
        _tasdiq(not r.turi.asosiy.itemIcon(i).isNull(),
                "kategoriya ikonkasiz chiqdi")
        # Sababsiz / kategoriyasiz saqlanmasin
        oldin = d.skalyar("SELECT COUNT(*) FROM rasxod")
        import ui.eski.dialogs as dm
        asl, dm.xato_koraset = dm.xato_koraset, lambda *a: None
        try:
            r.summa.qoy(10_000)
            r.turi.asosiy.setCurrentIndex(0)
            r.nom.setText("non")
            r._saqla()
            r.turi.asosiy.setCurrentIndex(i)
            r.nom.setText("")
            r._saqla()
        finally:
            dm.xato_koraset = asl
        _tasdiq(d.skalyar("SELECT COUNT(*) FROM rasxod") == oldin,
                "sababsiz yoki kategoriyasiz rasxod saqlandi")

    bosqich("kategoriya: ikonkaga nom berish", _kategoriya)

    # ── analitika: birlamchi oraliq — oy boshidan bugungacha
    def _analitika():
        from datetime import date
        from core import plan as pl
        from ui.eski.sahifa_analitika import AnalitikaSahifa
        # Yangi nusxa: oynadagisining oralig'ini yuqoridagi «doira»
        # testi ataylab qo'lda o'zgartirgan.
        s = AnalitikaSahifa(oyna)
        s.yangila()
        _tasdiq((s.dan.iso(), s.gacha.iso()) == pl.oy_bugungacha(),
                "birlamchi oraliq oy boshidan bugungacha emas")
        _tasdiq(s.gacha.iso() == date.today().isoformat(),
                "oraliq bugundan keyin ham davom etyapti")
        n = d.skalyar("SELECT COUNT(*) FROM turi WHERE faol=1")
        _tasdiq(s.jadval.rowCount() >= n,
                "«Hamma kategoriyalar» da hamma faol kategoriya yo'q")
        s._oraliq("2026-01-01", "2026-01-31")
        s.yangila()
        _tasdiq(s.dan.iso() == "2026-01-01",
                "qo'lda tanlangan oraliq yangilashda qaytib ketdi")
        s._shu_oy()
        _tasdiq((s.dan.iso(), s.gacha.iso()) == pl.oy_bugungacha(),
                "«Shu oy» oy boshidan bugungacha emas")
        _tasdiq(s.davr() == "oy", "«Shu oy» faol tugma emas")

        # «Custom»: taqvimda ikki bosish → oraliq (teskari bosilsa ham)
        from PySide6.QtCore import QDate
        from ui.eski.sahifa_analitika import OraliqOyna
        _tasdiq(not s.dan.isVisible() and not s.gacha.isVisible(),
                "Dan/Gacha maydonlari hali ekranda")
        hisoblandi = []
        dl = OraliqOyna(s.dan.iso(), s.gacha.iso(),
                        lambda a, b: hisoblandi.append((a, b)) or 12345,
                        parent=s)
        dl._bosildi(QDate(2026, 3, 20))
        _tasdiq(dl.oxiri is None, "birinchi bosish oraliqni yopib qo'ydi")
        _tasdiq(dl.oraliq() == ("2026-03-20", "2026-03-20"),
                "bitta kun tanlanganda oraliq o'sha kun emas")
        dl._bosildi(QDate(2026, 3, 5))
        _tasdiq(dl.oraliq() == ("2026-03-05", "2026-03-20"),
                f"custom oraliq noto'g'ri: {dl.oraliq()}")
        _tasdiq(hisoblandi[-1] == ("2026-03-05", "2026-03-20")
                and "12 345" in dl.summa.text().replace("\xa0", " "),
                f"oraliq summasi ko'rinmadi: {dl.summa.text()!r}")
        olindi = []
        dl.tanlandi.connect(lambda a, b: olindi.append((a, b)))
        dl._qolla()
        _tasdiq(olindi == [("2026-03-05", "2026-03-20")],
                "«Qo'llash» oraliqni bermadi")
        s._oraliq(*dl.oraliq())
        _tasdiq(s.davr() == "custom" and s.dan.iso() == "2026-03-05",
                "custom oraliq sahifaga tushmadi")
        s._oraliq(pl.hafta_boshi(), pl.hafta_oxiri())
        _tasdiq(s.davr() == "hafta", "«Shu hafta» faol tugma emas")
        s._shu_oy()

    bosqich("analitika: joriy oy va hamma kategoriya", _analitika)

    # ── analitika: odam filtri + kategoriya ichi (tahrirlash oynasi)
    def _analitika_odam():
        from core import ledger as lg
        from ui.eski.dialogs import KategoriyaRasxodlari
        from ui.eski.sahifa_analitika import AnalitikaSahifa
        s = AnalitikaSahifa(oyna)
        s._oraliq("2000-01-01", "2100-12-31")
        _tasdiq(s.qism_qator.isHidden() and s.xulosa.isHidden(),
                "odam tanlanmaganda qism tugmalari/xulosa ko'rinib turibdi")
        _tasdiq(s.odam.count() >= 2, "odam tanlagichida odam yo'q")
        s.odam.setCurrentIndex(1)           # signal → yangila()
        odam_id = s.odam.odam_id()
        _tasdiq(not s.qism_qator.isHidden() and not s.xulosa.isHidden(),
                "odam tanlanganda qism tugmalari/xulosa chiqmadi")
        for i, (qism, _) in enumerate(s.QISMLAR):
            s.qism.button(i).click()
            _tasdiq(s.filtr() == (odam_id, qism), f"qism «{qism}» olinmadi")
            _tasdiq(s.doira._bolaklar == lg.doira_bolaklari(
                d, "2000-01-01", "2100-12-31", odam_id=odam_id, qism=qism),
                f"doira odam filtriga ({qism}) mos emas")
        x = lg.odam_rasxod_xulosa(d, odam_id, "2000-01-01", "2100-12-31")
        _tasdiq(s.k_jami._son == x["jami"], "«Jami» kartasi noto'g'ri")
        s.qism.button(0).click()
        for b in s.doira._bolaklar:
            dlg = KategoriyaRasxodlari(d, "t", b["idlar"], "2000-01-01",
                                       "2100-12-31", odam_id, "hammasi",
                                       parent=s)
            ichi = lg.kategoriya_rasxodlari(d, b["idlar"], "2000-01-01",
                                            "2100-12-31", odam_id)
            _tasdiq(sum(r["summa"] for r in ichi) == b["summa"],
                    f"«{b['nom']}» ichidagi rasxodlar bo'lakka teng emas")
            _tasdiq(dlg.jadval.rowCount() == len(ichi),
                    "ichi oynasida qatorlar soni noto'g'ri")
            dlg.deleteLater()
        # Ichi oynasida kategoriyani almashtirish (bir nechta tanlov)
        b = next((b for b in s.doira._bolaklar if b["soni"] >= 1), None)
        if b is not None:
            dlg = KategoriyaRasxodlari(d, "t", b["idlar"], "2000-01-01",
                                       "2100-12-31", parent=s)
            dlg.jadval.selectAll()
            idlar = dlg.tanlangan_idlar()
            _tasdiq(len(idlar) == dlg.jadval.rowCount(),
                    "bir nechta rasxod tanlanmadi")
            eski = {i: d.skalyar("SELECT turi_id FROM rasxod WHERE id=?", i)
                    for i in idlar}
            dlg.yangi_turi.asosiy.setCurrentIndex(
                dlg.yangi_turi.asosiy.count() - 1)
            yangi = dlg.yangi_turi.turi_id()
            dlg._turi_ozgartir()
            _tasdiq(all(d.skalyar("SELECT turi_id FROM rasxod WHERE id=?", i)
                        == yangi for i in idlar),
                    "kategoriya oynadan almashmadi")
            if any(v != yangi for v in eski.values()):
                _tasdiq(dlg.ozgardi, "almashgandan keyin `ozgardi` yo'q")
                d.undo()
            _tasdiq(all(d.skalyar("SELECT turi_id FROM rasxod WHERE id=?", i)
                        == v for i, v in eski.items()),
                    "undo kategoriyani qaytarmadi")
            dlg.deleteLater()
        s.odam.setCurrentIndex(0)
        _tasdiq(s.filtr() == (None, "hammasi"), "«Hammasi» ga qaytmadi")

    bosqich("analitika: odam filtri va kategoriya ichi", _analitika_odam)

    # ── analitika → «Reja va fakt»: bo'sh holat, reja, oy almashuvi
    def _reja_fakt():
        from core import plan as pl
        from ui.eski import theme as th
        from ui.eski.sahifa_analitika import AnalitikaSahifa
        from ui.eski.sahifa_reja_fakt import RejaDialog
        s = AnalitikaSahifa(oyna)
        s._korinish_ozgardi(1)
        p = s.reja_fakt
        _tasdiq(not s.kategoriyalar.isVisibleTo(s) and p.isVisibleTo(s),
                "«Reja va fakt» tugmasi ko'rinishni almashtirmadi")
        oy = "2031-03"                      # rejasi yo'q, bo'sh oy
        p.oy = oy
        p.yangila()
        _tasdiq(p.bosh.isVisibleTo(p) and not p.tana.isVisibleTo(p),
                "reja yo'q oyda bo'sh holat chiqmadi")
        dl = RejaDialog(d, oy, p)
        dl.umumiy.qoy(1_000_000)
        tid = next(iter(dl.maydonlar))
        dl.maydonlar[tid].qoy(1)            # 1 so'm — albatta oshadi
        dl._saqla()
        _tasdiq(pl.oylik_reja(d, oy) == 1_000_000
                and pl.turi_reja(d, oy).get(tid) == 1,
                "reja oynasi saqlamadi")
        p.yangila()
        _tasdiq(p.tana.isVisibleTo(p) and not p.bosh.isVisibleTo(p),
                "reja saqlangach dashboard chiqmadi")
        _tasdiq(p.k_reja._son == 1_000_000, "«Oylik reja» kartasi noto'g'ri")
        p._sur(1)
        _tasdiq(p.joriy_oy() == "2031-04" and p.bosh.isVisibleTo(p),
                "oy surilganda yangilanmadi")
        p._bu_oyga()
        _tasdiq(p.joriy_oy() == pl.oy_kaliti(), "«Bu oy» joriy oyga qaytmadi")
        eski = th.REJIM
        try:
            p.oy = oy
            for rejim in th._PALITRA:
                th.rejim_qoy(rejim)
                p.yangila()
                s.resize(1100, 1200)
                s.grab()                    # chizish yiqilmasin
        finally:
            th.rejim_qoy(eski)
        d.undo()
        _tasdiq(not pl.reja_bormi(d, oy), "reja saqlash bitta undo emas")
        s._korinish_ozgardi(0)
        _tasdiq(s.kategoriyalar.isVisibleTo(s), "«Kategoriyalar» ga qaytmadi")

    bosqich("analitika: reja va fakt", _reja_fakt)

    # ── mahsulotlar: daraxt, karta, rasm, rasxod oynasi bilan bog'lanish
    def _mahsulotlar():
        import tempfile
        from pathlib import Path as _P
        from PySide6.QtGui import QColor, QImage
        from core import mahsulot as mh
        from ui.eski import dialogs as dm
        from ui.eski.oyna import HAMMA as _H
        from ui.eski.sahifa_mahsulot import MahsulotDialog, rasm_baytlari
        boz = d.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
        # Ichki kategoriya oynasi: rasmsiz saqlanmaydi, rasm bilan — ha
        from ui.eski.sahifa_mahsulot import IchkiKategoriyaDialog
        import ui.eski.sahifa_mahsulot as smm
        ik = IchkiKategoriyaDialog(d, boz, parent=oyna)
        _tasdiq(ik.royxat.count() == len(mh.bosh_belgilar(d)) > 0,
                "ichki kategoriya oynasida bo'sh rasmlar yo'q")
        ik.nom.setText("UI Mevalar")
        asl_x, smm.xato_koraset = smm.xato_koraset, lambda *a: None
        try:
            ik._saqla()
            _tasdiq(ik.yangi_id is None, "rasmsiz ichki kategoriya saqlandi")
            ik.guruh.setCurrentIndex(1)
            ik.royxat.item(0).setSelected(True)
            fayl = ik.rasm()
            ik.guruh.setCurrentIndex(ik.guruh.count() - 1)
            ik._saqla()
        finally:
            smm.xato_koraset = asl_x
        mev = ik.yangi_id
        _tasdiq(mev is not None, "ichki kategoriya oynadan saqlanmadi")
        _tasdiq(d.skalyar("SELECT rasm FROM turi WHERE id=?", mev) == fayl,
                "tanlangan rasm (guruh almashgandan keyin) yozilmadi")
        _tasdiq(d.skalyar("SELECT ota_id FROM turi WHERE id=?", mev) == boz,
                "ichki kategoriya otasiga bog'lanmadi")
        ik.deleteLater()
        s = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                if x[2].__name__ == "MahsulotSahifa"))
        s.yangila()
        _tasdiq(any(it.data(0, 0x0100) == mev for it in s._hamma_tugun()),
                "ichki kategoriya daraxtda yo'q")

        # Rasm: katta rasm kichraytiriladi
        img = QImage(3000, 2000, QImage.Format_RGB32)
        img.fill(QColor("#c0392b"))
        yol = _P(tempfile.mkdtemp()) / "olma.png"
        img.save(str(yol))
        bayt = rasm_baytlari(str(yol))
        kich = QImage.fromData(bayt)
        _tasdiq(max(kich.width(), kich.height()) <= 1280,
                "katta rasm kichraytirilmadi")

        dlg = MahsulotDialog(d, turi_id=mev, parent=oyna)
        _tasdiq(dlg.asosiy.currentData() == boz and dlg.ichki.currentData() == mev,
                "yangi mahsulot tanlangan kategoriyaga qo'yilmadi")
        dlg.nom.setText("UI Olma")
        dlg.narx.qoy(18_000)
        dlg.miqdor.setText("1,5")
        dlg.olchov.setCurrentText("kg")
        dlg._yangi_rasm = bayt
        dlg._saqla()
        _tasdiq(dlg.result() == 1, "mahsulot saqlanmadi")
        r = d.q1("SELECT * FROM item WHERE nom='UI Olma'")
        _tasdiq(r["turi_id"] == mev and r["miqdor"] == 1.5 and r["rasm"],
                "mahsulot maydonlari noto'g'ri saqlandi")

        # Bozorlik tanlansa — ichkidagi mahsulot ham kartada
        s.yangila()
        s._kat_tanla(boz)
        nomlar = [s.royxat.item(i).data(0x0100) for i in range(s.royxat.count())]
        _tasdiq(r["id"] in nomlar, "ichki kategoriyadagi mahsulot otasida ko'rinmadi")
        _tasdiq(not s.royxat.item(nomlar.index(r["id"])).icon().isNull(),
                "kartada rasm yo'q")
        s.qidiruv.setText("bunaqasi-yoq-xyz")
        _tasdiq(s.royxat.isHidden() and "topilmadi" in s.bosh.text(),
                "topilmaganda bo'sh holat ko'rinmadi")
        s.qidiruv.clear()

        # Rasxod oynasi: Bozorlik → ichkidagi mahsulot, rasmi va narxi bilan
        rd = dm.RasxodDialog(d, parent=oyna)
        rd.turi.tanla(boz)
        # Ikki bosqich: katta tanlangach ichkisi o'ng maydonda chiqadi
        mev_id = d.skalyar("SELECT turi_id FROM item WHERE id=?", r["id"])
        _tasdiq(rd.turi.ichki.isEnabled()
                and rd.turi.ichki.findData(mev_id) >= 0,
                "katta kategoriya tanlanganda ichkisi chiqmadi")
        _tasdiq(rd.turi.asosiy.findData(mev_id) < 0,
                "ichki kategoriya katta ro'yxatda ham turibdi")
        rd.turi.ichki.setCurrentIndex(rd.turi.ichki.findData(mev_id))
        _tasdiq(rd.turi.turi_id() == mev_id, "ichki kategoriya olinmadi")
        rd.turi.ichki.setCurrentIndex(0)
        _tasdiq(rd.turi.turi_id() == boz, "«ichkisiz» — katta olinmadi")
        q0 = rd.mahsulotlar._qatorlar[0]
        i = q0["combo"].findData(r["id"])
        _tasdiq(i >= 0, "rasxod oynasida ichki kategoriya mahsuloti yo'q")
        _tasdiq("UI Mevalar ›" in q0["combo"].itemText(i),
                "mahsulot qaysi ichki kategoriyada ekani ko'rinmadi")
        _tasdiq(not q0["combo"].itemIcon(i).isNull(), "tanlagichda rasm yo'q")
        q0["combo"].setCurrentIndex(i)
        _tasdiq(rd.summa.qiymat() == 18_000, "narx avtomatik qo'yilmadi")
        _tasdiq(rd.summa.isReadOnly(), "summa mahsulotlardan olinmadi")
        q0["miqdor"].qoy(2)
        _tasdiq(rd.summa.qiymat() == 36_000, "miqdor narxni ko'paytirmadi")
        q0["miqdor"].qoy(1)
        q0["summa"].qoy(21_000)                # narxni qo'lda o'zgartirish
        q0["summa"].textEdited.emit("21 000")
        _tasdiq(rd.summa.qiymat() == 21_000, "qator summasi yozuvga o'tmadi")
        rd.shaxsiy.setChecked(True)
        rd._saqla()
        rid = d.skalyar("SELECT MAX(id) FROM rasxod WHERE item_id=?", r["id"])
        if rid:
            from core import entries as _en
            _en.rasxod_turi_qoy(d, [rid], mev_id)
            rt = dm.RasxodDialog(d, rid, parent=oyna)
            _tasdiq(rt.turi.asosiy.currentData() == boz
                    and rt.turi.ichki.currentData() == mev_id,
                    "tahrirlashda katta/ichki kategoriya tiklanmadi")
            _tasdiq(rt.mahsulotlar.qatorlar()[0]["item_id"] == r["id"],
                    "tahrirlashda mahsulot tiklanmadi (ichki kategoriya)")
            rt.deleteLater()
            d.undo()
        _tasdiq(rid, "yangi rasxod mahsulotga bog'lanmadi")
        _tasdiq(d.skalyar("SELECT summa FROM rasxod WHERE id=?", rid) == 21_000,
                "qo'lda o'zgartirilgan narx saqlanmadi")

        # Tahrirlashda bog'lanish uzilmasin — mahsulot nofaol bo'lsa ham
        mh.faol_almashtir(d, r["id"])
        rt = dm.RasxodDialog(d, rid, parent=oyna)
        _tasdiq([x["item_id"] for x in rt.mahsulotlar.qatorlar()] == [r["id"]],
                "tahrirlashda mahsulot qayta tanlanmadi")
        rt._saqla()
        _tasdiq(d.skalyar("SELECT item_id FROM rasxod WHERE id=?", rid) == r["id"],
                "tahrirlash mahsulot bog'lanishini uzib yubordi")

    bosqich("mahsulotlar: daraxt, rasm, rasxod bilan bog'lanish", _mahsulotlar)

    # ── bitta rasxodda bir nechta mahsulot; reja ham rasxod kabi
    def _kop_mahsulot():
        from core import plan as pl
        from core import ledger as lg
        from core import rasxod_kirit as rk_
        import ui.eski.dialogs as dm
        from ui.eski.sahifa_reja_fakt import RejaFaktPanel, RejaYozuvDialog
        boz = d.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
        a = pl.item_qosh(d, "UI Non", 5_000, boz)
        b = pl.item_qosh(d, "UI Sut", 12_000, boz)
        rd = dm.RasxodDialog(d, parent=oyna)
        rd.turi.tanla(boz)
        m = rd.mahsulotlar
        m._qatorlar[0]["combo"].setCurrentIndex(
            m._qatorlar[0]["combo"].findData(a))
        m._qatorlar[0]["miqdor"].qoy(3)
        q2 = m.qator_qosh()
        q2["combo"].setCurrentIndex(q2["combo"].findData(b))
        _tasdiq(rd.summa.qiymat() == 27_000, "summa = yig'indi emas")
        _tasdiq(rd.nom.text() == "UI Non ×3, UI Sut",
                f"sabab taklif qilinmadi: {rd.nom.text()!r}")
        rd.shaxsiy.setChecked(True)
        rd._saqla()
        rid = rd.rasxod_id
        _tasdiq(rid and d.skalyar("SELECT summa FROM rasxod WHERE id=?",
                                  rid) == 27_000, "rasxod yozilmadi")
        _tasdiq([(x["item_id"], x["miqdor"], x["summa"])
                 for x in rk_.rasxod_mahsulotlari(d, rid)]
                == [(a, 3, 15_000), (b, 1, 12_000)], "qatorlar yozilmadi")
        # tahrirlash: qatorlar qayta yuklanadi, bittasi olib tashlanadi
        rt = dm.RasxodDialog(d, rid, parent=oyna)
        _tasdiq(len(rt.mahsulotlar.qatorlar()) == 2, "qatorlar yuklanmadi")
        rt.mahsulotlar._olib_tashla(rt.mahsulotlar._qatorlar[0])
        _tasdiq(rt.summa.qiymat() == 12_000, "olib tashlansa summa kamaymadi")
        rt._saqla()
        _tasdiq(d.skalyar("SELECT summa FROM rasxod WHERE id=?", rid) == 12_000
                and len(rk_.rasxod_mahsulotlari(d, rid)) == 1,
                "tahrir qatorlarni yangilamadi")
        dm.RasxodTafsilot(d, rid, parent=oyna).deleteLater()
        d.undo()
        _tasdiq(len(rk_.rasxod_mahsulotlari(d, rid)) == 2,
                "tahrir bitta undo emas")
        d.undo()
        _tasdiq(not d.skalyar("SELECT COUNT(*) FROM rasxod WHERE id=? AND"
                              " ochirilgan=0", rid), "saqlash bitta undo emas")
        _tasdiq(lg.audit(d).toza, "ko'p mahsulotdan keyin audit qizil")

        # katalogda yo'q mahsulot — o'sha zahoti yozish
        ry = dm.RasxodDialog(d, parent=oyna)
        ry.turi.tanla(boz)
        y0 = ry.mahsulotlar._qatorlar[0]
        y0["combo"].setEditText("UI Kefir yangi")
        _tasdiq(ry.mahsulotlar.qatorlar() == [
            {"item_id": None, "nom": "UI Kefir yangi", "miqdor": 1,
             "summa": 0}], "yozilgan yangi nom qator bo'lmadi")
        _tasdiq(ry.nom.text() == "UI Kefir yangi", "sabab taklif qilinmadi")
        y0["summa"].qoy(9_000)
        y0["summa"].textEdited.emit("9 000")
        ry.turi.tanla(boz)                  # kategoriya qayta — nom qolsin
        _tasdiq(y0["combo"].currentText() == "UI Kefir yangi",
                "kategoriya yangilanganda yozilgan nom o'chdi")
        ry.shaxsiy.setChecked(True)
        ry._saqla()
        yid = d.skalyar("SELECT id FROM item WHERE nom='UI Kefir yangi'"
                        " AND ochirilgan=0", birlamchi=None)
        _tasdiq(yid and ry.rasxod_id and d.skalyar(
            "SELECT item_id FROM rasxod WHERE id=?", ry.rasxod_id) == yid,
            "yangi mahsulot katalogga qo'shilmadi / bog'lanmadi")
        ry2 = dm.RasxodDialog(d, parent=oyna)
        ry2.turi.tanla(boz)
        y1 = ry2.mahsulotlar._qatorlar[0]
        _tasdiq(y1["combo"].findData(yid) > 0,
                "yangi mahsulot keyingi safar ro'yxatda yo'q")
        y1["combo"].setEditText("ui kefir YANGI")
        _tasdiq(ry2.mahsulotlar.qatorlar()[0]["item_id"] == yid
                and ry2.summa.qiymat() == 9_000,
                "katalogdagi nom yozilganda mahsulot/narx olinmadi")
        ry2.deleteLater()
        d.undo()
        _tasdiq(not d.skalyar("SELECT COUNT(*) FROM item WHERE id=? AND"
                              " ochirilgan=0", yid), "undo mahsulotni qaytarmadi")

        # reja — xuddi rasxod kabi oyna
        oy = "2031-05"
        dl = RejaYozuvDialog(d, oy, parent=oyna)
        _tasdiq(dl.sana.iso() == oy + "-01", "sana reja oyiga qo'yilmadi")
        dl.turi.tanla(boz)
        rm = dl.mahsulotlar
        rm._qatorlar[0]["combo"].setCurrentIndex(
            rm._qatorlar[0]["combo"].findData(a))
        q2 = rm.qator_qosh()
        q2["combo"].setCurrentIndex(q2["combo"].findData(b))
        dl._saqla()
        _tasdiq(pl.turi_reja(d, oy).get(boz) == 17_000,
                "reja yozuvi kategoriya rejasiga tushmadi")
        p = RejaFaktPanel(d)
        p.oy = oy
        p.yangila()
        _tasdiq(p.tana.isVisibleTo(p)
                and not p.yozuvlar_karta.isVisibleTo(p),
                "dashboard chiqmadi yoki «Reja yozuvlari» ko'rinyapti")
        qid = pl.reja_yozuvlari(d, oy)[0]["id"]
        dt = RejaYozuvDialog(d, oy, qid, parent=oyna)
        _tasdiq(len(dt.mahsulotlar.qatorlar()) == 2
                and dt.summa.qiymat() == 17_000, "reja tahrirda yuklanmadi")
        dt.deleteLater()

        # toifa ichi: reja kunlari, «aslida to'landi» → haqiqiy rasxod
        from ui.eski.sahifa_reja_fakt import RejaKategoriyaOyna
        from ui.eski.sahifa_reja_fakt import RejaRoyxatOyna
        ko = RejaKategoriyaOyna(d, oy, boz, "Bozorlik", parent=oyna)
        _tasdiq(ko.royxat.rowCount() == 1
                and ko.royxat.item(0, 1).text() == "UI Non, UI Sut",
                "toifada ro'yxatlar ro'yxati chiqmadi")
        ro = RejaRoyxatOyna(d, qid, parent=ko)
        _tasdiq(len(ro.maydon) == 2, "ro'yxat ichida mahsulotlar to'liq emas")
        # ro'yxat ichidan tahrir: shaxsiy qilish, mahsulot olib tashlash
        import ui.eski.sahifa_reja_fakt as srf0
        asl_dlg = srf0.RejaYozuvDialog

        class _Tahrir(asl_dlg):
            def exec(self_):
                self_.shaxsiy.setChecked(True)
                self_.mahsulotlar._olib_tashla(self_.mahsulotlar._qatorlar[1])
                self_._saqla()
                return True
        srf0.RejaYozuvDialog = _Tahrir
        try:
            list(ro.maydon.values())[0][0].qoy(4_000)    # saqlanmagan qiymat
            ro._tahrir()
        finally:
            srf0.RejaYozuvDialog = asl_dlg
        _tasdiq(len(ro.maydon) == 1 and not ro.y["umumiymi"]
                and list(ro.maydon.values())[0][0].qiymat() == 4_000,
                "ro'yxat ichidan tahrir ishlamadi")
        d.undo()
        ro._qur()
        ro._rejadek()
        ro._saqla()
        rid = d.skalyar("SELECT rasxod_id FROM reja_qator WHERE id=?", qid,
                        birlamchi=None)
        _tasdiq(rid and d.skalyar("SELECT summa FROM rasxod WHERE id=?",
                                  rid) == 17_000 and ro.ozgardi,
                "«aslida to'landi» rasxod yozmadi")
        ko._qur()
        _kun = [ko.kunlar.item(r, 3).text() for r in range(ko.kunlar.rowCount())]
        _tasdiq(ko.kunlar.item(0, 4).text() == "rejadagidek",
                f"kun holati yangilanmadi: {_kun}")
        import ui.eski.sahifa_reja_fakt as srf
        asl, srf.tasdiq = srf.tasdiq, lambda *a: True
        try:
            ko.royxat.selectRow(0)
            ko._ochir()
        finally:
            srf.tasdiq = asl
        _tasdiq(ko.royxat.rowCount() == 0 and d.skalyar(
            "SELECT summa FROM rasxod WHERE id=? AND ochirilgan=0", rid)
            == 17_000, "o'chirish ishlamadi yoki rasxodni ham o'chirdi")
        d.undo()
        ro.deleteLater()
        p.yangila()
        _tasdiq(p.k_fakt._son >= 17_000, "fakt yangilanmadi")
        ko.resize(800, 700)
        ko.grab()
        ko.deleteLater()
        d.undo()

        # doira: shaxsiy rejimda umumiy reja ko'rinmaydi
        p.d_shaxsiy.click()
        _tasdiq(p.odam_id == p.d_odam.odam_id() and p.bosh.isVisibleTo(p),
                "shaxsiy doirada umumiy reja chiqdi")
        p.d_umumiy.click()
        _tasdiq(p.odam_id is None and p.tana.isVisibleTo(p),
                "umumiy doiraga qaytmadi")
        d.undo()
        _tasdiq(not pl.reja_bormi(d, oy), "reja yozuvi bitta undo emas")
        p.deleteLater()

    bosqich("rasxod va rejada bir nechta mahsulot", _kop_mahsulot)

    # ── «Shaxsiy»: qarz uchun bitta karta-tugma, kunlik jadval yashirin
    def _qarzim():
        from core import ledger as lg
        from ui.eski import dialogs as dm
        from ui.eski.oyna import HAMMA as _H
        s = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                if x[2].__name__ == "OdamSahifa"))
        s.yangila()
        _tasdiq(not s.kunlik_karta.isVisibleTo(s), "kunlik harakat ko'rinyapti")
        nomlar = [s.kartalar.itemAt(i).widget()._yorliq.text()
                  for i in range(s.kartalar.count())]
        _tasdiq(not any(n in ("MEN UCHUN OLINGAN", "TASHQI QARZ",
                              "SOF POZITSIYA") for n in nomlar)
                and "QARZIM" in nomlar, f"qarz kartalari: {nomlar}")
        oid = s.kim.odam_id()
        _tasdiq(s.qarz_karta._son == lg.odam_qarzlari(d, oid)["jami"],
                "«Qarzim» summasi noto'g'ri")
        b_oyna = dm.RejagaBandOyna(d, oid, parent=oyna)
        b_oyna.resize(700, 600)
        b_oyna.grab()
        b_oyna.deleteLater()
        o = dm.QarzlarimOyna(d, oid, parent=oyna)
        o.resize(700, 600)
        o.grab()
        o.deleteLater()

    bosqich("shaxsiy: «Qarzim» tugmasi", _qarzim)

    # ── «Bugun»: oxirgi yozuvlar yashirin, bugunga rejalangan ro'yxatlar
    def _bugun_reja():
        from datetime import date
        from core import plan as pl
        from ui.eski.oyna import HAMMA as _H
        s = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                if x[2].__name__ == "BugunSahifa"))
        boz = d.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
        qid = pl.reja_yozuv_saqla(d, date.today().isoformat(), "UI bugun",
                                  boz, 5_000)
        s.yangila()
        _tasdiq(not s.oxirgi_karta.isVisibleTo(s), "«Oxirgi yozuvlar» ko'rinyapti")
        _tasdiq(not s.bugun_reja.isVisibleTo(s),
                "«Bugunga rejalangan» ko'rinyapti")
        _tasdiq(any(g["turi_id"] == boz for g in s.kun_kat)
                and s.reja_jadval.rowCount() == len(s.kun_kat),
                "bugungi reja kategoriyasi «Bugunga rejalangan» da yo'q")
        d.undo()
        s.yangila()

    bosqich("bugun: bugunga rejalangan", _bugun_reja)

    # ── mahsulotlar: mavjud kategoriyani boshqasining ichiga ko'chirish
    def _kat_kochir():
        from core import mahsulot as mh
        from ui.eski import sahifa_mahsulot as sm
        from ui.eski.oyna import HAMMA as _H
        boz = d.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
        gig = mh.kategoriya_qosh(d, "UI Gigiena")
        s = oyna.sahifa_ol(next(i for i, x in enumerate(_H)
                                if x[2].__name__ == "MahsulotSahifa"))
        s.yangila()
        dlg = sm.KategoriyaKochirDialog(d, gig, parent=oyna)
        _tasdiq(dlg.joy.findData(gig) < 0, "kategoriya o'zining ichiga taklif qilindi")
        _tasdiq(dlg.ota_id() is None, "hozirgi joyi (asosiy) tanlanmagan")
        _tasdiq(dlg.joy.findData(boz) >= 0, "Bozorlik tanlagichda yo'q")
        asl = sm.KategoriyaKochirDialog.exec

        def _exec(self):
            self.joy.setCurrentIndex(self.joy.findData(boz))
            return 1
        sm.KategoriyaKochirDialog.exec = _exec
        try:
            s._kat_tanla(gig)
            s._kat_kochir()
        finally:
            sm.KategoriyaKochirDialog.exec = asl
        _tasdiq(d.skalyar("SELECT ota_id FROM turi WHERE id=?", gig) == boz,
                "kategoriya ko'chmadi")
        it = next(x for x in s._hamma_tugun() if x.data(0, 0x0100) == gig)
        _tasdiq(it.parent() is not None and it.parent().data(0, 0x0100) == boz,
                "daraxtda yangi joyida ko'rinmadi")
        _tasdiq(s._tanlangan_kat() == gig, "ko'chgandan keyin tanlov yo'qoldi")
        from core import ledger as lg
        _tasdiq(lg.audit(d).toza, "ko'chirishdan keyin audit qizil")

    bosqich("mahsulotlar: kategoriyani ko'chirish", _kat_kochir)

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
