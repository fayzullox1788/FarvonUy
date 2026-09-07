# Shriftlar

Bu papkaga **Inter** shriftining `.ttf` / `.otf` fayllarini tashlang —
`dizayn.shriftlarni_yukla()` ularni ishga tushishda o'zi yuklaydi
(`QFontDatabase.addApplicationFont`), tizimga o'rnatish shart emas.

Kerakli og'irliklar: **Regular (400)**, **Medium (500)**, **SemiBold (600)**.
Manba: https://github.com/rsms/inter/releases (SIL Open Font License).

## Papka bo'sh bo'lsa

Dastur tizimdagi eng yaxshi mavjud oilaga tushadi:

    Inter  →  Segoe UI Variable Text  →  Segoe UI

Bu kompyuterda tekshirilgan (Windows 11): **Inter yo'q**, lekin
**«Segoe UI Variable Text» bor** — hozir o'sha ishlatilmoqda. Ya'ni Inter
qo'shilmasa ham ko'rinish yomon emas; Inter faqat spetsifikatsiyadagi
aniq tipografikani beradi.

Nima ishlatilayotganini `dizayn.shrift_oilasi()` aytadi, ko'rgazmaning
sarlavhasida ham yozilib turadi:

    py -3.14 src\ui\korgazma.py

## Tabular raqamlar

`tnum` `QFont.setFeature(QFont.Tag("tnum"), 1)` orqali yoqiladi — QSS buni
qila olmaydi. **Diqqat:** `setFeature("tnum", 1)` (oddiy satr bilan)
`ValueError` beradi, `QFont.Tag` shart.
