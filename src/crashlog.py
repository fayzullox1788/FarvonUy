"""Xatolarni faylga yozish va foydalanuvchiga ko'rsatish.

Muzlatilgan (.exe) holatda konsol yo'q — xato hech kimga ko'rinmasdan
yo'qoladi. Shuning uchun hamma tutilmagan xato shu yerdan o'tadi:
faylga yoziladi va oynada ko'rsatiladi.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

import config


def yoz(matn: str) -> None:
    try:
        with open(config.LOG_YOL, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 70}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n{matn}\n")
    except Exception:
        pass


def _korsat(sarlavha: str, matn: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is None:
            return
        q = QMessageBox()
        q.setIcon(QMessageBox.Critical)
        q.setWindowTitle(sarlavha)
        q.setText("Dasturda kutilmagan xato yuz berdi.")
        q.setInformativeText(
            f"Ma'lumotlaringiz joyida — hech narsa yo'qolmadi.\n\n"
            f"Xato tafsiloti:\n{config.LOG_YOL}")
        q.setDetailedText(matn)
        q.exec()
    except Exception:
        pass


def ornat() -> None:
    """Global xato tutgichni o'rnatadi."""

    def tutgich(turi, qiymat, iz):
        if issubclass(turi, KeyboardInterrupt):
            sys.__excepthook__(turi, qiymat, iz)
            return
        matn = "".join(traceback.format_exception(turi, qiymat, iz))
        yoz(matn)
        _korsat("Farovon Hayot — xato", matn)

    sys.excepthook = tutgich
