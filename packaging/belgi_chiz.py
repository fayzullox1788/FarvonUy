"""Kategoriya ikonkalarini asl kategoriyalar USLUBIDA qayta chizadi.

    py -3.14 packaging\\belgi_chiz.py            # hamma ikonkani chizadi
    py -3.14 packaging\\belgi_chiz.py --namuna   # faqat ko'rib chiqish varag'i

Dizayn naqshi — birinchi yaratilgan kategoriyalar (Ovqat 🍲, Bozorlik 🛒,
Ro'zg'or 🏠 …). Ular emoji bilan ko'rinadi, Windows 11 esa emojini
Microsoft **Fluent Emoji (Color)** uslubida chizadi: rangli, yumshoq
gradient va yorug'lik, shaffof fon, konturi yo'q. Fluent Emoji — ochiq
to'plam (MIT), SVG lari tizim emojisi bilan AYNAN bir xil (tekshirilgan).
Shuning uchun har ikonka o'sha to'plamdan, eski belgining MA'NOSIGA
qarab tanlangan (`belgi_xarita.json`, 198 ta, hammasi har xil) va eski
emoji kategoriyalar yonida begona turmaydi. Fon shaffof — «Iliq», «Oq»
va «Tungi» rejimlarning hammasiga tushadi.

Har ikonka uchun `src/belgilar/` ga IKKI fayl yoziladi:
  * `<kalit>.svg` — dastur shuni ishlatadi (`widgets.belgi_ikon`): Qt uni
    so'ralgan o'lcham × ekran masshtabida vektordan chizadi, ya'ni
    125–150% ekranda ham xira bo'lmaydi;
  * `<kalit>.png` — 256 px zaxira (SVG o'qilmasa) — fayl NOMI o'zgarmaydi,
    u `turi.rasm` dagi kalit: baza tegilmaydi.

Asl kesilgan PNG birinchi marta `belgilar_asl/` ga zaxiralanadi —
qaytarish: o'sha PNG ni `src/belgilar/` ga ko'chirib, yonidagi `.svg`
ni o'chirish. Manba SVG lar `belgi_svg/fluent/` da (litsenziyasi —
`belgi_svg/LITSENZIYA.txt`). Yangi ikonka: Fluent Emoji'dan
`<nom>_color.svg` ni o'sha papkaga qo'yib, `belgi_xarita.json` ga
qator yozing. Skript dastur ichida ishlamaydi.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

BU_YER = Path(__file__).resolve().parent
BELGILAR = BU_YER.parent / "src" / "belgilar"
ASL = BU_YER / "belgilar_asl"
SVG = BU_YER / "belgi_svg" / "fluent"
XARITA: dict[str, str] = json.loads(
    (BU_YER / "belgi_xarita.json").read_text(encoding="utf-8"))

OLCHAM = 256            # px, kvadrat, shaffof
CHET = 6                # px — emojining o'z bo'sh joyi bor, ozgina qo'shimcha

# Namuna varag'ida yonma-yon turadigan asl kategoriyalar emojisi.
ASL_EMOJI = "🍲🛒🏠🧼🚕💡👕💊📦🍿"
FONLAR = [("Iliq", "#FFFFFF"), ("Tungi", "#181A2C")]


def manba(nom: str) -> Path:
    """Odam emojilari (skin-tone'li) Fluent'da `_color_default.svg`."""
    for yol in (SVG / f"{nom}_color.svg", SVG / f"{nom}_color_default.svg"):
        if yol.exists():
            return yol
    raise FileNotFoundError(f"{nom}: SVG topilmadi ({SVG})")


def chiz(nom: str, olcham: int = OLCHAM) -> QImage:
    r = QSvgRenderer(str(manba(nom)))
    if not r.isValid():
        raise ValueError(f"{nom}: SVG o'qilmadi")
    rasm = QImage(olcham, olcham, QImage.Format_ARGB32_Premultiplied)
    rasm.fill(Qt.transparent)
    p = QPainter(rasm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    r.render(p, QRectF(CHET, CHET, olcham - 2 * CHET, olcham - 2 * CHET))
    p.end()
    return rasm


def namuna(fayllar: list[str], yol: Path) -> None:
    """Hamma ikonka to'ri ikkala rejim fonida, 40 px da (dasturdagidek
    SVG dan), tepada asl emoji kategoriyalar — «mos tushadimi?» uchun."""
    ustun, qadam = 20, 48
    qator = (len(fayllar) + ustun - 1) // ustun
    en = 24 + ustun * qadam
    blok = 70 + qator * qadam
    rasm = QImage(en, 16 + len(FONLAR) * (blok + 16), QImage.Format_ARGB32)
    rasm.fill(QColor("#F3ECE0"))
    p = QPainter(rasm)
    p.setRenderHint(QPainter.Antialiasing, True)
    emoji = QFont("Segoe UI Emoji")
    emoji.setPixelSize(30)
    for k, (nom, karta) in enumerate(FONLAR):
        y0 = 16 + k * (blok + 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(karta))
        p.drawRoundedRect(QRectF(8, y0, en - 16, blok), 14, 14)
        p.setPen(QColor("#655C4F") if k == 0 else QColor("#B0A7C9"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(20, y0 + 18, f"{nom}: asl kategoriyalar (tizim emojisi) "
                                "va pastda yangi ikonkalar")
        p.setFont(emoji)
        for i, e in enumerate(ASL_EMOJI):
            p.drawText(QRectF(18 + i * qadam, y0 + 24, 40, 40), Qt.AlignCenter, e)
        for i, f in enumerate(fayllar):
            x = 18 + (i % ustun) * qadam
            y = y0 + 70 + (i // ustun) * qadam
            QSvgRenderer(str(BELGILAR / f).replace(".png", ".svg")).render(
                p, QRectF(x, y, 40, 40))
    p.end()
    rasm.save(str(yol))


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(sys.argv)
    fayllar = [f for f in XARITA if (BELGILAR / f).exists()]
    yoq = sorted(set(XARITA) - set(fayllar))
    if yoq:
        print("ogohlantirish: belgilar/ da yo'q:", ", ".join(yoq))
    if "--namuna" not in sys.argv:
        ASL.mkdir(exist_ok=True)
        for f in fayllar:
            if not (ASL / f).exists():          # faqat BIRINCHI marta
                shutil.copy2(BELGILAR / f, ASL / f)
            nom = XARITA[f]
            if not chiz(nom).save(str(BELGILAR / f)):
                raise OSError(f"{f} yozilmadi")
            shutil.copyfile(manba(nom), BELGILAR / f.replace(".png", ".svg"))
        print(f"chizildi: {len(fayllar)} ta (PNG + SVG)")
    namuna(fayllar, BU_YER / "belgi_namuna.png")
    print("namuna:", BU_YER / "belgi_namuna.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
