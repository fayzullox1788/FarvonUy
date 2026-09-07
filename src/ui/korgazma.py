"""Dizayn tizimining ko'rgazmasi — palitra va komponentlar.

Spetsifikatsiya §16.2 talab qiladigan «kichik ko'rgazma oynasi».

    py -3.14 src\\ui\\korgazma.py            oynani ochadi
    py -3.14 src\\ui\\korgazma.py --saqla P   uch rejimni PNG qilib saqlaydi

Nega kerak: rangni ko'z bilan ko'rmasdan tanlab bo'lmaydi, va uchala
rejimni yonma-yon ko'rmasdan «tungi rejimda bu chip o'qilmaydi» degan
narsani payqash uchun oyni kutish kerak bo'ladi.

Ko'rgazma komponentlarning O'ZIDAN yig'iladi — ya'ni u bir vaqtning
o'zida kutubxonaning ishlashini ham tekshiradi.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import Qt                                    # noqa: E402
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout,  # noqa: E402
                               QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from ui import theme as T                                       # noqa: E402
from ui import widgets as Q                                      # noqa: E402

GURUHLAR = [
    ("Sirtlar", ["fon", "sirt", "sirt2", "sirt_hover", "sirt_tanlangan"]),
    ("Chiziqlar", ["chiziq", "chiziq_kuchli"]),
    ("Matn", ["matn", "matn2", "matn3", "neytral"]),
    ("Aksent", ["aksent", "aksent_hover", "aksent_tola", "aksent_fon",
                "aksent_fon_matn", "aksent_ustida", "fokus"]),
    ("Pul", ["yashil", "yashil_fon", "yashil_fon_matn",
             "qizil", "qizil_fon", "qizil_fon_matn"]),
    ("Ogohlantirish", ["toq_sariq", "toq_sariq_fon", "toq_sariq_fon_matn",
                       "sariq", "sariq_fon", "sariq_fon_matn",
                       "sariq_bar"]),
]

DARAJALAR = [("qarzda", -180_000, 0.0), ("juda_kam", 45_000, 0.12),
             ("kam", 180_000, 0.35), ("yaxshi", 620_000, 1.0)]


def _namuna(token: str) -> QWidget:
    """Bitta rang namunasi: kvadrat + nom + hex."""
    kvadrat = QFrame()
    kvadrat.setFixedSize(30, 30)
    kvadrat.setStyleSheet(
        f"background:{T.R(token)};border:1px solid {T.R('chiziq_kuchli')};"
        f"border-radius:6px;")
    ichki = Q.ustun(Q.yorliq(token), Q.maslahat(T.R(token).upper()), oraliq=0)
    return Q.qator(kvadrat, ichki, None)


def sahifa(rejim_kaliti: str) -> QWidget:
    """Bitta rejimning to'liq ko'rgazmasi."""
    T.rejim_qoy(rejim_kaliti)

    ildiz = QWidget()
    ildiz.setStyleSheet(T.qss())
    v = QVBoxLayout(ildiz)
    v.setContentsMargins(T.QOBIQ_CHET, T.QOBIQ_CHET,
                         T.QOBIQ_CHET, T.QOBIQ_CHET)
    v.setSpacing(T.ORALIQ_KARTA)

    v.addWidget(Q.sarlavha(f"Farvon Uy — «{T.rejim_nomi()}» rejimi"))
    v.addWidget(Q.maslahat(
        f"shrift: {T.shrift_oilasi()}   ·   pul raqamlari tabular (tnum)   "
        f"·   {len(Q.__all__)} ta komponent"))

    # ── tokenlar ────────────────────────────────────────────────────
    k = Q.Karta("Rang tokenlari")
    setka = QGridLayout()
    setka.setHorizontalSpacing(18)
    setka.setVerticalSpacing(6)
    for ustun_i, (nom, tokenlar) in enumerate(GURUHLAR):
        setka.addWidget(Q.yorliq(nom), 0, ustun_i)
        for r, t in enumerate(tokenlar, start=1):
            setka.addWidget(_namuna(t), r, ustun_i)
    quti = Q.shaffof(QWidget())
    quti.setLayout(setka)
    k.qosh(quti)
    v.addWidget(k)

    # ── tugmalar va maydonlar ───────────────────────────────────────
    k = Q.Karta("Tugmalar — bitta ko'rinishda bitta «asosiy»")
    k.qosh(Q.qator(Q.tugma("Qo'shish", "asosiy"), Q.tugma("Tahrirlash"),
                   Q.tugma("O'chirish", "xavfli"),
                   Q.tugma("Batafsil…", "soya"), None))
    v.addWidget(k)

    k = Q.Karta("Kiritish maydonlari")
    nom = Q.MatnMaydon("Nima olindi?")
    pul = Q.PulMaydon(1_559_000)
    pul.setFixedWidth(160)
    xato_pul = Q.PulMaydon()
    xato_pul.setFixedWidth(200)
    xato_pul.maydon.setText("salom")          # xato holatini ko'rsatish uchun
    k.qosh(Q.qator(Q.SanaMaydon("2026-08-30"), nom, pul))
    k.qosh(Q.qator(Q.yorliq("Xato holati:"), xato_pul, None))
    k.qosh(Q.qator(
        Q.SegmentTugma([("u", "Umumiy"), ("s", "Shaxsiy"),
                        ("b", "Boshqa uchun")]),
        Q.SegmentTugma([("r", "Rasxodlar"), ("k", "Kirim")], "r"), None))
    v.addWidget(k)

    # ── raqam kartalari ─────────────────────────────────────────────
    k = Q.Karta("Raqam kartalari")
    kartalar = QHBoxLayout()
    kartalar.setSpacing(T.ORALIQ_KARTA)
    for yorliq_matn, qiymat, izoh, rangli in (
            ("Real balans", -102_334, "hozir qo'lingdagi pul", False),
            ("Sof pozitsiya", 490_333, "senga qarzdorlar", True),
            ("Adolatli balans", 387_999, "hisoblashgandan keyin", False),
            ("Jami kirim", 2_120_000, "shaxsiy rasxod 1 155 000", False)):
        kartalar.addWidget(Q.RaqamKarta(yorliq_matn, qiymat, izoh, rangli))
    quti = Q.shaffof(QWidget())
    quti.setLayout(kartalar)
    k.qosh(quti)
    v.addWidget(k)

    # ── pul darajasi ────────────────────────────────────────────────
    k = Q.Karta("Pul darajasi — rang yolg'iz emas, yonida doim yorliq")
    qd = QHBoxLayout()
    qd.setSpacing(18)
    for holat, summa, ulush in DARAJALAR:
        chiziq = Q.DarajaChiziq()
        chiziq.qoy(ulush, holat)
        nishon = Q.Nishon()
        nishon.daraja_qoy(holat)
        son = Q.PulYorliq(summa, "raqam", rangli=True)
        son.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        qd.addWidget(Q.ustun(son, chiziq, Q.qator(nishon, None), oraliq=6))
    qd.addStretch(1)
    quti = Q.shaffof(QWidget())
    quti.setLayout(qd)
    k.qosh(quti)
    v.addWidget(k)

    # ── nishonlar va xabarlar ───────────────────────────────────────
    k = Q.Karta("Nishon va xabar")
    k.qosh(Q.qator(Q.Nishon("✔ kitob teng", "ok"),
                   Q.Nishon("✘ kitob teng emas!", "xato"),
                   Q.Nishon("🔒 Yopilgan", "neytral"),
                   Q.Nishon("takroriy", "aksent"), None))
    banner = Q.Banner()
    banner.korsat("Otabek: 45 000 — juda kam  ·  Abbosxon: 180 000 — kam qoldi",
                  "ogoh")
    k.qosh(banner)
    xabar = Q.XabarQatori()
    xabar.korsat("✔ Bozorlik — 330 000 so'm (umumiy)", "ok",
                 qaytarish=lambda: None)
    k.qosh(xabar)
    v.addWidget(k)

    # ── jadval + yopishqoq panel ────────────────────────────────────
    k = Q.Karta("Jadval — pul ustuni o'ngga tekislangan, tabular")
    j = Q.Jadval(["Sana", "Nomi", "Kim to'ladi", "Ulushi"],
                 pul_ustunlar={3}, kop_tanlash=True)
    j.kengliklar(110, 0, 150, 140)
    j.tuldir([["30.08.2026", "Haftalik bozorlik", "Fayzulloxon", 519_667],
              ["30.08.2026", "Qozon, instrument", "Otabek", 190_667],
              ["01.09.2026", "Rolton, non", "Abbosxon", 13_000]],
             [1, 2, 3])
    j.balandlik(3)
    j.j.selectRow(1)
    k.qosh(j)
    panel = Q.YopishqoqPanel()
    panel.amal_qosh("To'landi deb belgilash", lambda: None)
    panel.yangila(3, 723_334, "blok")
    k.qosh(panel)
    v.addWidget(k)

    # ── bo'sh holat ─────────────────────────────────────────────────
    k = Q.Karta("Bo'sh holat")
    k.qosh(Q.BoshHolat("✔  Hech kim hech kimga qarzdor emas.",
                       "Erkin to'lov yozish"))
    v.addWidget(k)

    v.addWidget(Q.HolatSatri())
    v.addStretch(1)
    return ildiz


def saqla(papka: Path) -> list[Path]:
    """Uchala rejimni PNG qilib saqlaydi."""
    papka.mkdir(parents=True, exist_ok=True)
    yollar = []
    for kalit, _nom in T.REJIMLAR:
        w = sahifa(kalit)
        w.resize(1200, 1420)
        w.ensurePolished()
        yol = papka / f"palitra-{kalit}.png"
        w.grab().save(str(yol))
        yollar.append(yol)
    return yollar


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    T.shriftlarni_yukla()

    if "--saqla" in sys.argv:
        i = sys.argv.index("--saqla")
        nishon = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else Path.cwd()
        for y in saqla(nishon):
            print(y)
        return 0

    from PySide6.QtWidgets import QScrollArea, QTabWidget
    oyna = QTabWidget()
    oyna.setWindowTitle("Farvon Uy — dizayn ko'rgazmasi")
    oyna.resize(1240, 940)
    for kalit, nom in T.REJIMLAR:
        aylanma = QScrollArea()
        aylanma.setWidgetResizable(True)
        aylanma.setWidget(sahifa(kalit))
        oyna.addTab(aylanma, nom)
    oyna.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
