r"""Fayl yo'llari va dastur sozlamalari.

Baza %LOCALAPPDATA%\FarvonUy ichida yashaydi — dastur yangilanganda
o'chib ketmaydi. Bu yerda hech qanday og'ir import yo'q, shuning uchun
uni istalgan modul xavfsiz import qila oladi.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NOM = "Farovon Hayot"
APP_ID = "FarvonUy"
VERSIYA = "1.2.1"

# Pul birligi
VALYUTA = "so'm"


def _muzlaganmi() -> bool:
    """PyInstaller ichida ishlayapmizmi?"""
    return getattr(sys, "frozen", False)


def resurs(*qismlar: str) -> Path:
    """Dastur bilan birga kelgan fayl (ikonka, schema.sql, ...)."""
    if _muzlaganmi():
        baza = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        baza = Path(__file__).resolve().parent
    return baza.joinpath(*qismlar)


def _malumot_papkasi() -> Path:
    """Foydalanuvchi ma'lumotlari — dastur yangilansa ham qoladi."""
    ort = os.environ.get("FARVONUY_DATA")
    if ort:
        p = Path(ort)
    else:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
        p = Path(local) / APP_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


def ish_stoli() -> Path | None:
    """Ish stoli papkasi, topilmasa None.

    `%USERPROFILE%\\Desktop` deb yozib qo'yish YETARLI EMAS: OneDrive
    yoqilgan bo'lsa ish stoli `…\\OneDrive\\Desktop` ga ko'chiriladi va
    eski yo'l ham qolib ketishi mumkin. Shuning uchun avval Windows'ning
    o'zidan so'raymiz (CSIDL_DESKTOPDIRECTORY), keyingina taxmin qilamiz.
    """
    nomzodlar: list[Path] = []
    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes as wt
            bufer = ctypes.create_unicode_buffer(wt.MAX_PATH)
            # 0x0010 = CSIDL_DESKTOPDIRECTORY, 0 = SHGFP_TYPE_CURRENT
            if ctypes.windll.shell32.SHGetFolderPathW(
                    None, 0x0010, None, 0, bufer) == 0 and bufer.value:
                nomzodlar.append(Path(bufer.value))
        except Exception:
            pass
    uy = os.environ.get("USERPROFILE") or str(Path.home())
    nomzodlar += [Path(uy) / "Desktop", Path.home() / "Desktop"]
    for p in nomzodlar:
        if p.is_dir():
            return p
    return None


def eksport_papkasi() -> Path:
    """Hisobotlar tushadigan joy.

    Ish stoli — chunki fayl darhol yuboriladi (Telegram, pochta), va
    uni chuqur papkadan qidirib o'tirish shart emas. Ish stoli
    topilmasa (yoki yozib bo'lmasa) eski `eksport` papkasiga tushadi.
    """
    # `FARVONUY_DATA` qo'yilgan bo'lsa — «hamma narsa shu papkada
    # tursin» degani. Testlar aynan shu bilan ishlaydi: aks holda har
    # ishga tushirishda ish stoliga hisobot fayllari to'kilardi.
    if os.environ.get("FARVONUY_DATA"):
        EKSPORT.mkdir(parents=True, exist_ok=True)
        return EKSPORT
    d = ish_stoli()
    if d is not None and os.access(d, os.W_OK):
        return d
    EKSPORT.mkdir(parents=True, exist_ok=True)
    return EKSPORT


DATA = _malumot_papkasi()

# Demo rejim: `demo.yoq` fayli bor bo'lsa dastur HAQIQIY baza o'rniga
# `demo/` papkadagi soxta ma'lumotli bazani ochadi (src/demo.py quradi).
# Zaxira, cheklar, rasmlar ham o'sha papkada — haqiqiy fayllarga tegilmaydi,
# server bilan sinxron ham o'chiq (sinx.sozlamalar).
DEMO_BAYROQ = DATA / "demo.yoq"
DEMO_PAPKA = DATA / "demo"
DEMO = DEMO_BAYROQ.exists()
_ISH = DEMO_PAPKA if DEMO else DATA
_ISH.mkdir(parents=True, exist_ok=True)

DB_YOL = _ISH / "farvonuy.db"
ZAXIRA = _ISH / "zaxira"          # avtomatik backuplar
CHEKLAR = _ISH / "cheklar"        # chek rasmlari
MAHSULOT_RASM = _ISH / "mahsulot_rasm"   # mahsulot rasmlari
EKSPORT = _ISH / "eksport"        # hisobotlar
LOG_YOL = DATA / "farvonuy.log"
HAQIQIY_DB = DATA / "farvonuy.db"

for _p in (ZAXIRA, CHEKLAR, MAHSULOT_RASM, EKSPORT):
    _p.mkdir(parents=True, exist_ok=True)

# Nechta zaxira nusxa saqlanadi
ZAXIRA_SONI = 20

ICON_YOL = resurs("..", "assets", "farvonuy.ico")
if not ICON_YOL.exists():
    ICON_YOL = resurs("assets", "farvonuy.ico")
