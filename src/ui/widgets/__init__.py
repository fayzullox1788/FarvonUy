"""Komponentlar kutubxonasi — spetsifikatsiya §3.

Ekranlar FAQAT shu yerdagi bo'laklardan yig'iladi. «Bir martalik» vidjet
yozilmaydi: agar biror ekranga yangi ko'rinish kerak bo'lsa, u shu yerga
komponent bo'lib qo'shiladi va boshqalar ham undan foydalanadi.

Nima uchun bitta joyda: eski kodda har sahifa o'z uslubini o'zi yozardi
va natijada bitta tugma to'rt xil ko'rinishda bo'lardi. Bu yerda tugma
bitta — `tugma(matn, tur)`.

    from ui import widgets as Q

    Q.tugma("Qo'shish", "asosiy")
    Q.Karta("Bugun yozilganlar")
    Q.Jadval(["Sana", "Nomi", "Summa"], pul_ustunlar={2})
"""
from ui.widgets.asos import (BoshHolat, Karta, Nishon, PulYorliq, RaqamKarta,
                             bolim, chiziq, kengaytirgich, maslahat, matn,
                             qator, sarlavha, shaffof, tugma, ustun, yorliq)
from ui.widgets.jadval import DarajaChiziq, Jadval
from ui.widgets.maydon import (MatnMaydon, OdamTanlagich, OraliqTanlagich,
                               PulMaydon, SanaMaydon, SegmentTugma, Tanlagich,
                               TuriTanlagich)
from ui.widgets.panel import (Banner, HolatSatri, Oyna, Xabarcha, XabarQatori,
                              YonSubNav, YopishqoqPanel, tasdiq)

__all__ = [
    # asos
    "BoshHolat", "Karta", "Nishon", "PulYorliq", "RaqamKarta",
    "bolim", "chiziq", "kengaytirgich", "maslahat", "matn",
    "qator", "sarlavha", "shaffof", "tugma", "ustun", "yorliq",
    # jadval
    "DarajaChiziq", "Jadval",
    # maydon
    "MatnMaydon", "OdamTanlagich", "OraliqTanlagich", "PulMaydon",
    "SanaMaydon", "SegmentTugma", "Tanlagich", "TuriTanlagich",
    # panel
    "Banner", "HolatSatri", "Oyna", "Xabarcha", "XabarQatori",
    "YonSubNav", "YopishqoqPanel", "tasdiq",
]
