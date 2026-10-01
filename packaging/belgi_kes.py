"""Telefon skrinshotlaridagi ikonkalarni bittalab kesib oladi.

    py -3.14 packaging\\belgi_kes.py "C:\\Users\\Acer\\Desktop\\expense categories"

Har skrinshot — qora fonda kulrang doiralar to'ri, har doira ichida
bitta chiziqli ikonka. Doiralar rangidan topiladi (fon ~27, doira ~50),
qator va ustun proyeksiyasi bilan: sarlavha matni oq, aylantirgich va
pastdagi chiziq esa tor — ikkalasi ham o'lcham filtridan o'tmaydi.

Natija: `src/belgilar/<skrinshot>_<nn>.png`, doiradan tashqarisi
shaffof. Fayl nomi faqat ichki kalit — foydalanuvchiga ko'rsatilmaydi,
ikonkaga nomni dasturning o'zida foydalanuvchi beradi.

Bu skript dastur ichida ishlamaydi (PIL/numpy build'dan chiqarilgan) —
ikonkalar bir marta kesiladi va `src/belgilar` da saqlanadi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

CHIQISH = Path(__file__).resolve().parent.parent / "src" / "belgilar"
KAM, KOP = 38, 75          # doira kulrangining chegarasi
ENG_KAM_DOIRA = 80         # px — aylantirgich va pastki chiziq bundan tor


def _bolaklar(proyeksiya: np.ndarray, chegara: int) -> list[tuple[int, int]]:
    bor = proyeksiya > chegara
    natija, boshi = [], None
    for i, b in enumerate(bor):
        if b and boshi is None:
            boshi = i
        elif not b and boshi is not None:
            natija.append((boshi, i))
            boshi = None
    if boshi is not None:
        natija.append((boshi, len(bor)))
    return [(a, b) for a, b in natija if b - a >= ENG_KAM_DOIRA]


def doiralar(rasm: Image.Image) -> list[tuple[int, int, int, int]]:
    kul = np.asarray(rasm.convert("L")).astype(int)
    niqob = (kul >= KAM) & (kul <= KOP)
    qutilar = []
    for y0, y1 in _bolaklar(niqob.sum(axis=1), 40):
        for x0, x1 in _bolaklar(niqob[y0:y1].sum(axis=0), 15):
            if 0.8 < (x1 - x0) / (y1 - y0) < 1.25:
                qutilar.append((x0, y0, x1, y1))
    return qutilar


DOIRA_RANG = (47, 47, 47)
CHET = 80                  # px — chetda kesilgan doira uchun zaxira


def kes(rasm: Image.Image, quti) -> Image.Image:
    x0, y0, x1, y1 = quti
    en, boy = x1 - x0, y1 - y0
    tomon = max(en, boy) + 2
    cx = (x0 + x1) // 2
    # Skrinshot chekkasida kesilgan doira pastdan yoki tepadan kalta
    # chiqadi. Markaz butun qismidan hisoblanadi, yetishmagan joy
    # doiraning o'z rangi bilan to'ldiriladi — aks holda doira qiyshiq
    # va bir cheti kesik bo'lib qolardi.
    if boy < en and y1 >= rasm.height - 1:
        cy = y0 + en // 2
    elif boy < en and y0 <= 0:
        cy = y1 - en // 2
    else:
        cy = (y0 + y1) // 2
    toldirilgan = Image.new("RGB", (rasm.width + 2 * CHET,
                                    rasm.height + 2 * CHET), DOIRA_RANG)
    toldirilgan.paste(rasm.convert("RGB"), (CHET, CHET))
    cx, cy = cx + CHET, cy + CHET
    b = toldirilgan.convert("RGBA").crop(
        (cx - tomon // 2, cy - tomon // 2,
         cx - tomon // 2 + tomon, cy - tomon // 2 + tomon))
    # Silliq chekka: 4 barobar katta niqob chizib, kichraytiramiz.
    katta = Image.new("L", (tomon * 4, tomon * 4), 0)
    ImageDraw.Draw(katta).ellipse((4, 4, tomon * 4 - 5, tomon * 4 - 5), fill=255)
    b.putalpha(katta.resize((tomon, tomon), Image.LANCZOS))
    return b


def main(papka: str) -> int:
    CHIQISH.mkdir(parents=True, exist_ok=True)
    jami = 0
    for fayl in sorted(Path(papka).glob("*.jpg")):
        rasm = Image.open(fayl)
        qutilar = doiralar(rasm)
        for i, q in enumerate(qutilar, 1):
            kes(rasm, q).save(CHIQISH / f"{fayl.stem}_{i:02d}.png")
        print(f"{fayl.name:22} {len(qutilar):3} ta")
        jami += len(qutilar)
    print(f"jami: {jami}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
