"""Farovon Hayot ikonkasini yasaydi.

    py -3.14 packaging\\make_icon.py

MUHIM: har bir o'lcham ALOHIDA chiziladi (4x supersampling bilan), keyin
kichraytiriladi. Bitta katta rasmni cho'zib .ico yasash — vazifalar
panelida xira ikonka chiqishining sababi. Shu xato bir marta bo'lgan,
qaytarilmasin.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Brend ranglari — `ui/theme.py` palitrasiga mos
FON_1 = (60, 86, 128)       # KOK      #3C5680  urg'u ko'k
FON_2 = (37, 54, 82)        # quyuqroq — pastga qarab gradient
UY = (245, 242, 236)        # FON      #F5F2EC  iliq qog'oz
TANGA = (216, 160, 74)      # iliq oltin
SOYA = (32, 29, 25)         # MATN     #201D19  tanga ichidagi halqa

OLCHAMLAR = [16, 24, 32, 48, 64, 128, 256]
SS = 4                      # supersampling


def chiz(o: int) -> Image.Image:
    n = o * SS
    r = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(r)

    # ── yumaloq kvadrat fon (vertikal gradient) ──────────────────────
    radius = int(n * 0.22)
    fon = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fon)
    fd.rounded_rectangle([0, 0, n - 1, n - 1], radius=radius, fill=FON_1 + (255,))
    gradient = Image.new("L", (1, n))
    for y in range(n):
        gradient.putpixel((0, y), int(255 * (y / n)))
    ust = Image.new("RGBA", (n, n), FON_2 + (255,))
    ust.putalpha(gradient.resize((n, n)))
    fon = Image.alpha_composite(fon, ust)
    # burchaklarni yana kesib olamiz
    niqob = Image.new("L", (n, n), 0)
    ImageDraw.Draw(niqob).rounded_rectangle(
        [0, 0, n - 1, n - 1], radius=radius, fill=255)
    fon.putalpha(niqob)
    r = Image.alpha_composite(r, fon)
    d = ImageDraw.Draw(r)

    # ── uy ───────────────────────────────────────────────────────────
    # tom: uchburchak,  tana: to'rtburchak
    cx = n / 2
    tom_ust = n * 0.24
    tom_past = n * 0.50
    tom_chap = n * 0.17
    tom_ong = n * 0.83
    d.polygon([(cx, tom_ust), (tom_ong, tom_past), (tom_chap, tom_past)],
              fill=UY + (255,))

    tana_chap = n * 0.27
    tana_ong = n * 0.73
    tana_past = n * 0.79
    d.rounded_rectangle([tana_chap, tom_past - n * 0.02, tana_ong, tana_past],
                        radius=int(n * 0.045), fill=UY + (255,))

    # ── tanga (kichik o'lchamda tushirib qoldiriladi) ────────────────
    if o >= 32:
        # Tanga: to'la doira + ichki halqa. Belgisiz — 16px da ham toza
        # ko'rinadi, harf yoki so'm belgisi bu o'lchamda loyqalanadi.
        rr = n * 0.145
        cy = n * 0.555
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=TANGA + (255,))
        halqa = max(1, int(n * 0.022))
        ir = rr * 0.55
        d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir],
                  outline=SOYA + (150,), width=halqa)
    else:
        # 16-24px da tanga o'rniga oddiy eshik — aniqroq ko'rinadi
        ew, eh = n * 0.16, n * 0.26
        d.rounded_rectangle([cx - ew / 2, tana_past - eh, cx + ew / 2, tana_past],
                            radius=int(n * 0.03), fill=TANGA + (255,))

    return r.resize((o, o), Image.LANCZOS)


def main() -> int:
    ildiz = Path(__file__).resolve().parent.parent
    assets = ildiz / "assets"
    assets.mkdir(exist_ok=True)

    rasmlar = [chiz(o) for o in OLCHAMLAR]
    ico = assets / "farvonuy.ico"
    rasmlar[-1].save(ico, format="ICO",
                     sizes=[(o, o) for o in OLCHAMLAR],
                     append_images=rasmlar[:-1])
    rasmlar[-1].save(assets / "farvonuy.png", format="PNG")

    print(f"Yozildi: {ico}")
    print(f"O'lchamlar: {', '.join(str(o) for o in OLCHAMLAR)}")
    print(f"Hajmi: {ico.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
