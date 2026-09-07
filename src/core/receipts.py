"""Chek rasmlari.

Rasm dastur papkasiga NUSXALANADI (`%LOCALAPPDATA%\\FarvonUy\\cheklar`).
Asl fayl ko'chirilsa yoki o'chirilsa ham chek qoladi — aks holda bir oydan
keyin hamma chek "topilmadi" bo'lib qoladi.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import config

TURLAR = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".pdf", ".heic")
MAX_BAYT = 25 * 1024 * 1024


def qosh(db, rasxod_id: int, manba: str | Path) -> int:
    manba = Path(manba)
    if not manba.exists():
        raise ValueError(f"Fayl topilmadi: {manba}")
    if manba.suffix.lower() not in TURLAR:
        raise ValueError(f"Bu turdagi fayl qo'llab-quvvatlanmaydi: {manba.suffix}")
    if manba.stat().st_size > MAX_BAYT:
        raise ValueError("Fayl juda katta (25 MB dan oshmasin)")

    # nom to'qnashmasligi uchun mazmun xeshi ishlatiladi
    xesh = hashlib.sha1(manba.read_bytes()).hexdigest()[:16]
    nishon_nom = f"{rasxod_id}-{xesh}{manba.suffix.lower()}"
    nishon = config.CHEKLAR / nishon_nom
    if not nishon.exists():
        config.CHEKLAR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manba, nishon)

    bor = db.q1("SELECT id FROM chek WHERE rasxod_id=? AND fayl=?",
                rasxod_id, nishon_nom)
    if bor:
        return bor["id"]

    with db.amal("Chek qo'shildi"):
        return db.apply("chek", "INSERT",
                        {"rasxod_id": rasxod_id, "fayl": nishon_nom})


def royxat(db, rasxod_id: int) -> list[dict]:
    return [{"id": r["id"], "fayl": r["fayl"],
             "yol": config.CHEKLAR / r["fayl"],
             "bormi": (config.CHEKLAR / r["fayl"]).exists()}
            for r in db.q("SELECT * FROM chek WHERE rasxod_id=? ORDER BY id",
                          rasxod_id)]


def soni(db, rasxod_id: int) -> int:
    return db.skalyar("SELECT COUNT(*) FROM chek WHERE rasxod_id=?", rasxod_id)


def ochir(db, chek_id: int) -> None:
    """Yozuvni o'chiradi. Rasm faylining o'zi papkada qoladi — pul
    hujjatini diskdan yo'q qilish dasturning ishi emas."""
    with db.amal("Chek o'chirildi"):
        db.apply("chek", "DELETE", qator_id=chek_id)
