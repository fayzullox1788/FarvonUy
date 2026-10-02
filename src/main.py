"""Farvon Uy — ishga tushirish nuqtasi."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    import config
    import crashlog

    crashlog.ornat()

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NOM)
    app.setApplicationDisplayName(config.APP_NOM)
    app.setOrganizationName(config.APP_ID)
    if config.ICON_YOL.exists():
        app.setWindowIcon(QIcon(str(config.ICON_YOL)))

    # Windows'da vazifalar panelida to'g'ri ikonka chiqishi uchun
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"{config.APP_ID}.{config.VERSIYA}")
        except Exception:
            pass

    import db as dbm
    from ui.eski import theme
    try:
        baza = dbm.Db(zaxirasiz=True)
    except Exception as e:
        crashlog.yoz(f"Bazani ochib bo'lmadi: {e}")
        QMessageBox.critical(
            None, "Farvon Uy",
            f"Ma'lumotlar bazasini ochib bo'lmadi:\n\n{e}\n\n{config.DB_YOL}")
        return 1

    # Takroriy vazifalar («har kuni namoz») endi FAQAT serverda
    # (Cloudflare Worker) yaratiladi va sinxron bilan keladi. Desktop
    # ham `vz.takror_toldir()` qilsa, bitta vazifa ikki tomonda har xil
    # id bilan ikki marta paydo bo'lardi.

    # Foydalanuvchi tanlagan rang rejimi oyna qurilishidan OLDIN
    # qo'yilishi kerak — aks holda widgetlar eski rang bilan quriladi.
    theme.rejim_qoy(baza.sozlama("rejim", theme.REJIM))
    app.setStyleSheet(theme.STIL)

    from ui.eski.oyna import Oyna
    oyna = Oyna(baza)
    oyna.show()
    # D1 bilan fon sinxroni — sozlanmagan bo'lsa jim turadi.
    oyna.sinx_boshla()
    # Zaxira oynani ko'rsatishni kutib turmaydi: dastur darhol ochiladi.
    QTimer.singleShot(750, lambda: dbm.zaxira_ol(baza.yol))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
