# Farvon Uy — agentlar uchun ish qoidalari

PySide6 desktop dasturi (Python 3.14), uch kishilik uy moliyasi hisobi.
UI tili — o'zbekcha. `README.md` da loyiha tuzilishi va ishga tushirish bor —
avval shuni o'qing. Bu fayl faqat README'da yo'q narsalar haqida:
arxitektura chegarasi, buzib bo'lmaydigan qoidalar va kim nimani egallaydi.

---

## Buzib bo'lmaydigan uchta qoida

**1. Pul — har doim butun son.**
`float` bilan pul hisoblash TAQIQLANADI. `money.py` dan tashqarida bo'lish
amali (`/`) pul ustida bajarilmaydi. Bo'lish faqat `money.bol()` orqali,
u har doim aniq yig'indi qaytaradi. Bu Excel'dagi `519666.6666…` muammosini
tuzatish uchun qilingan — orqaga qaytarmang.

**2. Hamma yozuv `db.apply()` dan o'tadi.**
UI va `core/` hech qachon `con.execute("INSERT …")` yozmaydi. Sabab: har
o'zgarish `ozgarishlar` jadvaliga log bo'lishi kerak, aks holda Ctrl+Z
yolg'on gapiradi. Bir nechta yozuvni bitta undo qadamiga bog'lash uchun
`with db.amal("tavsif"):` ishlatiladi.

Yagona istisno — `davr` jadvali (oy yopish), u audit qilinmaydi.

**3. Hech narsa o'chirilmaydi.**
`apply(..., "DELETE")` aslida `ochirilgan=1` qo'yadi. Barcha SELECT'lar
`WHERE ochirilgan=0` bilan yoziladi. Buni unutish — balansni jimgina
buzadigan eng oson yo'l.

---

## Kitob tengligi — `ledger.audit()`

Dastur o'z hisobini o'zi tekshiradi. Beshta shart README'da yozilgan.
**Yangi funksiya qo'shsangiz `audit()` toza qolishi shart.**

`src/tekshir.py` shu shartlarni haqiqiy Excel ma'lumoti ustida tekshiradi
(51 ta test). Balansga tegadigan o'zgarish qilsangiz — avval shuni
ishga tushiring:

```
py -3.14 src\tekshir.py      # yadro
py -3.14 src\ui_tekshir.py   # UI, ekransiz
```

`build.bat` ham shu ikkisini chaqiradi va yiqilsa build'ni to'xtatadi.

### Nega `naqd` va `adolat` alohida

Excel'da «Balans» va «Real balans» bor edi, lekin ular orasidagi
bog'lanish hech qayerda tekshirilmasdi. Bu yerda:

```
adolat = naqd + sof        (har odam uchun, har safar tekshiriladi)
SUM(sof) = 0               (matematik jihatdan boshqacha bo'lishi mumkin emas)
```

Uchtasi `v_balans` viewida bitta SQL bilan hisoblanadi. Agar balans
formulasini o'zgartirsangiz — **uchalasini birga** o'zgartiring, aks holda
audit darhol qizil bo'ladi (va bu yaxshi: xato uch oydan keyin emas,
o'sha kuni chiqadi).

---

## Arxitektura chegarasi

```
ui/  →  core/  →  db.py  →  SQLite
```

- **`ui/` hech qachon SQL yozmaydi**, `core/` funksiyalarini chaqiradi.
  (Faqat o'qish uchun `db.q(...)` ishlatiladi — bu ruxsat etilgan.)
- **`core/` hech qachon PySide6 import qilmaydi.** Shuning uchun butun
  moliyaviy logikani ekransiz test qilib bo'ladi — `tekshir.py` shunday
  ishlaydi.
- **`money.py` hech narsani import qilmaydi** (config'dan tashqari hech
  nima). U sof matematika.

---

## Qarz tafsiloti — faqat to'lanmagani

«Kim kimga qarzdor» qatoriga bosilganda `ledger.juft_tolanmagan()`
chiqadi, `juft_tarkibi()` EMAS. Amalda deyarli hamma to'lov «erkin»
(`hisob_kitob.ulush_id` bo'sh) — ya'ni «to'landi» bayrog'iga qarab
filtrlash hech narsani yashirmaydi. Shuning uchun:

1. belgilangan ulush + unga bog'langan to'lov birga chiqariladi
   (`ulush_id` bo'yicha yig'indisi 0 bo'lsa);
2. qolgan manfiy qatorlar ENG ESKI musbat qatordan boshlab ayiriladi.

Natija yig'indisi juftlik summasiga teng qoladi. Qatorlarni «to'landi
emas» deb oddiy filtrlasangiz bu tenglik buziladi va oyna yuqoridagi
sondan boshqa raqam ko'rsatadi.

## Analitika — doira ranglari

`ui/eski/sahifa_analitika.py` dagi doira ranglari bo'lakning O'RNI
bo'yicha beriladi, kategoriya `id` si bo'yicha EMAS. Doirada qo'shni
bo'laklar — o'lchami bo'yicha qo'shni, `theme.TUR_RANG` tartibi esa
aynan qo'shni juftliklar (oxirgi→birinchi bilan) rang ajrata olmaydigan
ko'zga ham farqlanadigan qilib tekshirilgan. `id` bo'yicha bo'yasangiz
istalgan ikki rang yonma-yon tushadi, kategoriya esa 8 tadan ko'p.

Birlamchi holatda eng katta `ledger.DOIRA_QADAM` (6) ta kategoriya
o'z bo'lagi bilan, ortig'i «Qolganlari» da. «Yana 6 ta» tugmasi (yoki
«Qolganlari» ni bosish) `AnalitikaSahifa._korsat` ni 6 taga oshiradi —
kategoriya qolmaguncha; «Yig'ish» 6 taga qaytaradi (2026-09-30,
foydalanuvchi so'ragan). Shuning uchun bo'lak palitradan (8) ko'p
bo'lishi mumkin: ranglar `bolak_ranglari()` da AYLANADI, doira
halqasida oxirgi va birinchi rang bir xil tushsa, oxirgisi almashadi.
`ui_tekshir.py` 1–40 bo'lakda qo'shni ranglar farqini tekshiradi.
Doira balandligi ro'yxat uzunligidan (`_balandlik`).

«Hamma kategoriyalar» jadvali foydalanuvchi so'rovi bilan YASHIRILGAN
(`hamma_karta`), lekin hisoblanib turadi.

## `kim_uchun` — "boshqa uchun olingan"

`rasxod.kim_uchun` to'ldirilgan bo'lsa: pulni `kim_toladi` chiqargan, lekin
rasxod butunlay `kim_uchun` niki. Ichkarida bu 100% bitta odamga tegadigan
`umumiymi=1` rasxod (`bolish_usul='aniq'`), shuning uchun butun balans
matematikasi o'zgarishsiz ishlaydi.

**Nega alohida ustun kerak** — faqat ko'rsatish uchun emas: `v_balans` da
`umumiy_ulush` (haqiqiy umumiy rasxod) va `uchun_ulush` (uning uchun
olingani) ajratilgan. Aks holda odam o'z varag'ida "umumiy rasxoddan
ulushim" deb poyabzalining pulini ko'rardi.

Buni **kirim + shaxsiy rasxod** deb yozish xato: unda odamning kirimi ham,
rasxodi ham soxta bo'lib ketadi va "qancha pul oldim" degan savolga
dastur yolg'on javob beradi.

## Tashqi qarz — uydan tashqaridagi odamdan

`tashqi_qarz` (kim oldi = `odam_id`, kimdan = oddiy MATN) va
`tashqi_tolov` (qaytarish). Qarz beruvchi `odam` jadvaliga YOZILMAYDI —
u hisob a'zosi emas, `odam` ga qo'shilsa balans, ulush va navbatga
tushib qolardi.

Pul olganning qo'liga haqiqatan tushadi: `naqd` VA `adolat` ikkalasi
ham `+ olingan − qaytarilgan`. `sof` ga TEGMAYDI — shuning uchun
`SUM(sof)=0` va `adolat = naqd + sof` o'z-o'zidan saqlanadi. Audit
2-sharti `kirim − rasxod + tashqi_qoldiq` ga o'zgargan; 6-shart —
qarz ortig'i bilan qaytarilmagan. Qaytarishni har doim qarzni olgan
odamning o'zi qiladi. Qarz o'chirilsa to'lovlari ham o'sha amalda
o'chadi (bitta undo).

**UI — alohida oyna, `dialogs.TashqiQarzOyna`** (2026-09-25). Qarz
varag'ida faqat qisqa xulosa va «Tashqaridan qarz · <qoldiq>» tugmasi
qoladi; yozish, «kimga qancha qaytarish kerak»
(`ledger.tashqi_kimga_qaytarish()` — `tashqi_qarzlar()` dan yig'iladi,
qoldiq qoidasini qayta yozmang), qisman qaytarish va «Qarzni yopish»
(`entries.tashqi_qarz_yop()` — butun qoldiq bitta to'lov) shu oynada.
Forma `_TashqiForma` — oyna ham, kichik `TashqiQarzDialog` ham shundan.
Oyna o'zini `_yangila()` qiladi; yopilganda `ozgardi` bo'lsa chaqiruvchi
dasturni yangilaydi.

## Ikonkali kategoriya va majburiy maydonlar

`src/belgilar/*.png` — 200 ta ikonka, foydalanuvchining telefon
skrinshotlaridan `packaging/belgi_kes.py` bilan kesilgan (qayta kesish
kerak bo'lsa o'sha skript; PIL/numpy faqat unga kerak, build'ga
kirmaydi). Foydalanuvchi olib tashlatgan ikonkalar (robot, xoch)
fayl sifatida qoladi, lekin `kategoriya.YASHIRIN` orqali ro'yxatga
chiqmaydi — qayta kesilsa ham qaytmasin. Ikonkalar NOMSIZ — foydalanuvchi o'zi talab qilgan: nomni
«Iconlar» varag'ida (`sahifa_kategoriya.py`) o'zi beradi. Fayl
nomi (`food_03.png`) faqat kalit, ekranga chiqmasin. Guruh sarlavhalari
(«Shaxsiy», «Oziq-ovqat»…) skrinshotlardagi bo'lim nomlari —
`kategoriya.GURUH_NOMI`, foydalanuvchi so'rab qo'shdirgan. Ular ikonka
nomi EMAS va kategoriya yaratmaydi.

**Ikonkalar asl kategoriyalar uslubida — `packaging/belgi_chiz.py`**
(2026-09-30). Dizayn naqshi — birinchi kategoriyalar (🍲🛒🏠…), ya'ni
Windows 11 dagi Microsoft **Fluent Emoji (Color)**: rangli gradient,
shaffof fon, konturi yo'q. Kesilgan 115 px ikonkalar (to'q doira +
kulrang chiziq) bu uslubga mos emas edi. Hamma 198 ta (yashirin 2 tadan
tashqari) `packaging/belgi_xarita.json` bo'yicha (eski belgining
MA'NOSIGA qarab, takrorsiz) `belgi_svg/fluent/` dagi SVG dan (MIT)
chiziladi. `src/belgilar/` da har kalit uchun `.svg` (dastur shuni
ishlatadi) va 256 px `.png` (zaxira, `turi.rasm` kaliti — NOMI
o'zgarmaydi). Asli `packaging/belgilar_asl/` da.

**Xiralik — ekran masshtabi.** Noutbuk 125%: mantiqiy 26 px rasm
Windows'da cho'zilib xira chiqardi. Kategoriya ikonkasi FAQAT
`widgets.belgi_ikon(yol)` (QIcon, SVG afzal) yoki
`widgets.belgi_rasm(yol, olcham, widget)` (aniq ekran pikselida) orqali
olinadi — `QPixmap(...).scaled(n)` va `QIcon(str(png))` YOZMANG.
QPainter'da `ikon.paint(p, rect)` (doira ro'yxati shunday). SVG uchun
Qt'ning `qsvgicon` plagini kerak — spec'da `PySide6.QtSvg` hiddenimport.

Nom berilgan ikonka — oddiy `turi` qatori, `turi.rasm` = fayl nomi.
Nomi olib tashlansa `faol=0` (o'chmaydi), shu nom qayta berilsa o'sha
qator tiriladi — eski rasxodlar kategoriyasini yo'qotmaydi.

**Qo'lda yoziladigan har rasxodda sabab (`nom`) va faol kategoriya
majburiy** — `entries.rasxod_majburiy()`. U `rasxod_qosh()` ICHIDA
EMAS: import va takroriy rasxod eski ma'lumotdan keladi. Rasxod
yozadigan yangi oyna qo'shsangiz — uni o'zingiz chaqiring
(`RasxodDialog._saqla`, Bugun'dagi tezkor qo'shish).

---

## Mahsulotlar va kategoriya daraxti — `core/mahsulot.py`

Mahsulot — eski `item` jadvali (yangi jadval EMAS): reja, rasxod
oynasi va Sozlamalardagi katalog ham shundan o'qiydi. Qo'shilgan
ustunlar: `rasm`, `miqdor`, `ogirlik`, `litr` (REAL — pul emas),
`olchov`, `ochirilgan`. `faol=0` — vaqtincha ishlatilmaydi (varaqda
ko'rinadi, rasxodda tanlanmaydi); `ochirilgan=1` — o'chirilgan. Ikkalasi
BOSHQA narsa, aralashtirmang.

Ichki kategoriya — `turi.ota_id`. Uch joyda otasiga qo'shiladi:
`ledger.turi_boyicha()` (doira, hisobot), `kategoriya_jadvali()`
(faqat asosiylar) va `plan.turi_budjet()`. Yangi hisob qo'shsangiz
shu qoidaga amal qiling, aks holda bitta bozorlik ikki bo'lakka
bo'linib ko'rinadi. Kategoriya ichida faol ichki kategoriya yoki
mahsulot bo'lsa o'chirilmaydi.

**Ichki kategoriyaga rasm MAJBURIY** (2026-09-30, foydalanuvchi
so'ragan): `mh.kategoriya_qosh(..., ota_id, rasm=...)` rasmsiz rad
etadi. Rasm — `belgilar/` dagi ikonka va faqat BO'SHI
(`mh.bosh_belgilar()`): bitta ikonka — bitta faol kategoriya, chunki
«Iconlar» varag'i (`kategoriya.nomlanganlar`) ikonkadan
kategoriyani topadi. UI — `sahifa_mahsulot.IchkiKategoriyaDialog`.
Shu sabab rasmli ichki kategoriya «Iconlar» varag'ida ham nomi
bilan ko'rinadi. Katta kategoriya uchun rasm ixtiyoriy qoladi.

Mavjud kategoriyani boshqasining ichiga ko'chirish —
`mh.kategoriya_kochir()` (faqat `ota_id` o'zgaradi, bitta undo;
ichki kategoriya va mahsulotlari birga ko'chadi). O'zi yoki avlodi
ichiga ko'chirish rad etiladi — halqa bo'lsa daraxt va `yol_nomi()`
buziladi. Tanlagich `mh.kochish_joylari()` dan (o'zi va avlodlarisiz).
Eski rasxodning `turi_id` si o'zgarmaydi — doira/budjetda yangi
otasiga qo'shiladi.

**Rasxodda kategoriya — ikki bosqich: `widgets.KategoriyaTanla`**
(2026-09-30). Chapda faqat katta kategoriyalar, o'ngda tanlangan
kattaning ichkilari («— ichki kategoriyasiz —» = kattaning o'zi).
`RasxodDialog` (kiritish va tahrirlash), «Bugun» dagi tezkor kiritish
va `KategoriyaRasxodlari` shuni ishlatadi; bot o'zi ikki bosqichli
(`rx:k:` → 📂). Signal — `ozgardi`, `currentIndexChanged` EMAS;
tahrirlashda `tanla(turi_id)` (ichkisini ham joyiga qo'yadi).
Filtr/budjet tanlagichlari (`TuriTanla`) o'zgarmagan.

Rasxod oynalaridagi «Mahsulot» tanlagichi BITTA funksiyadan —
`dialogs.mahsulotlarni_toldir()`. Tahrirlashda bog'langan mahsulot
qayta tanlanadi (nofaol/o'chirilgan bo'lsa ham qo'shiladi) — 2026-09-25
gacha bu qilinmagan va tahrirlash `item_id` ni jimgina bo'shatardi;
yangi rasxodda esa `item_id` umuman yozilmasdi.

Rasm `config.MAHSULOT_RASM` ga nusxalanadi (nomi — mazmun xeshi),
kompyuterdan yuklansa 1280px gacha kichraytiriladi. Olib tashlansa fayl
diskda qoladi — undo qaytara olsin. **Telefondan yo'l — Telegram:**
uy a'zosi botga SHAXSIY rasm yuboradi, izohida mahsulot nomi
(`xabar._rasmni_ishla`, har daqiqada). Begona odam va guruh rasmlari
e'tiborsiz — bot ochiq.

### Umumiy tashqi qarz (`tashqi_qarz.umumiy=1`, `tashqi_ulush`)

**Qoida 2026-10-01 da o'zgardi (foydalanuvchi so'ragan).** Olingan pul
HAMMAGA ulushi bo'yicha beriladi (har kimning `naqd` iga o'z ulushi),
qarz ham hammaniki; qaytarilganda har kimning qo'lidan o'z to'lov
ulushi ayiriladi. Bo'lish rasxoddagidek: Teng / Foiz / Og'irlik / Aniq
(`dialogs._Qatnashchilar`, `money.bol`); qaytarishda birlamchi — qarz
qanday bo'lingan bo'lsa shu nisbatda. Uy ichida qarz YARATMAYDI:
`v_balans` da `tsq`/`ttq` naqd VA adolatga bir xil qo'shiladi, `sof` ga
tegmaydi; `v_juft_qarz` va `ledger.juft_tarkibi()` da umumiy tashqi qarz
YO'Q. (Eskisi: pul olganning qo'lida, u boshqalarga ichki qarzdor edi —
adolat ikkalasida bir xil, farq faqat naqd/sof.) `tashqi_qoldiq` —
har kimning o'z ulushi; «Qarzim» da umumiy qarzdan faqat o'z ulushi
(`jami_qoldiq` — butun qoldiq). Ulushlar yig'indisi = qarz/to'lov —
audit 7-sharti. Umumiy/shaxsiy almashtirish (`tashqi_umumiy_qoy`) eski
ulushlarni o'chirib qaytadan quradi — bitta undo.

## Rasxod kiritish — BITTA mantiq: `core/rasxod_kirit.py`

Rasxod uch joydan yoziladi: `RasxodDialog`, «Bugun» dagi tezkor
qo'shish va Telegram bot (`core/tg_rasxod.py`). Uchalasi ham
`Qoralama` ni to'ldiradi va `rk.saqla()` / `rk.tekshir()` ni chaqiradi.
Mahsulotdan nom/narx olish (`rk.mahsulot_tanla`), kim qatnashishi va
ulush ko'rinishi (`rk.qatnashchilar`, `rk.ulushlar`) ham shu yerda.
**Yangi qoida faqat shu faylga yoziladi** — oynaga yoki botga
yozilsa platformalar ajralib ketadi. `tekshir.py` bot va oyna BIR XIL
rasxod va ulush yozishini solishtiradi.

`parametrlar`: `None` — «tanlanmagan, uydagilar»; `{}` — «hech kim
tanlanmagan» (saqlanmaydi). Ikkalasini aralashtirmang.

Bot faqat SHAXSIY chatda va faqat uy a'zosiga (`odam.telegram`)
ishlaydi; callback `rx:` bilan boshlanadi (`xabar._bittasini_ishla`
ajratadi). Suhbat holati `sozlama.tg_rx:<chat>` da — `tg_offset` kabi
texnik holat, undo ga tushmaydi. Sana almashganda uydagilar qayta
olinadi, LEKIN foydalanuvchi kimlarni o'zi tanlagan bo'lsa (`qolda`)
tegilmaydi — aks holda olib tashlangan odam jimgina qaytardi.
Botda bo'lish faqat «teng»; foiz/og'irlik/aniq — oynada.

**Xabarchi — DOIMIY jarayon** (2026-10-01, «bot juda sekin»): avval reja
har 5 daqiqada ishga tushirib, skript ~292 s tinglab chiqardi — oraliqda
va noutbuk BATAREYADA (reja batareyada ishga tushmasdi) bot daqiqalab
jim edi. Endi `xabarchi.py` chiqmaydi: `getUpdates(timeout=50)` ni
tinimsiz tinglaydi, eslatmalar har daqiqada, takroriy vazifa + dars
`DAVRIY_ORALIQ` (10 daq) da. BITTA nusxa — `DATA/xabarchi.lock` fayl
qulfi; Windows rejasi har DAQIQADA chaqiradi (nazoratchi), qulf band
bo'lsa yangi nusxa og'ir importdan oldin chiqadi. Reja sozlamalari:
batareyada ham, vaqt chegarasiz, «IgnoreNew» (`xabarchi_reja.bat`).
`src/**/*.py` o'zgarsa jarayon o'zi chiqadi — nazoratchi ≤1 daqiqada
yangi kod bilan ko'taradi. Tarmoq: `xabar._sorov` keep-alive HTTPS
ulanishda (`_ULANISHLAR`: «tinglash» va «asosiy»), so'rov ~0,3 s dan
~0,1 s ga tushdi; uzilgan ulanish bir marta qayta ochiladi. Dastur
ichidagi «guruhni topish» (`guruhlarni_top`) ham `getUpdates` chaqiradi —
doimiy tinglash paytida Telegram 409 berishi mumkin, qayta bosish kifoya.

**Xabarchi TO'G'RIDAN-TO'G'RI shu `src/` dan ishlaydi.** `xabar.py`,
`tg_rasxod.py` yoki `xabarchi.py` ni tahrirlayotganda yarim yozilgan
fayl jonli botni yiqitadi (2026-09-25 da bir marta bo'lgan). Tahrirdan
keyin darhol `py_compile` qiling.

## Analitika — birlamchi oraliq

Birlamchi oraliq — joriy oyning 1-kunidan BUGUNGACHA
(`plan.oy_bugungacha()`), oy oxirigacha EMAS: 1-noyabrda faqat
1-noyabr ko'rinadi. Foydalanuvchi sanani qo'lda o'zgartirmaguncha
(`_qolda`) har `yangila()` da qayta hisoblanadi — dastur oy almashganda
ochiq tursa ham eski oy qolib ketmasin. «Shu oy» `_qolda` ni qaytaradi.

«Hamma kategoriyalar» jadvali (`ledger.kategoriya_jadvali()`) HAR faol
kategoriyani chiqaradi, rasxodi 0 bo'lganini ham — hozir yashirin.

## Analitika — odam filtri va kategoriya ichi

«Kim:» tanlagichi (`OdamTanla(hammasi=True)`). Odam tanlansa — uning
rasxodi `v_balans` bilan AYNAN bir xil qoidada (`ledger._odam_manba`):
**shaxsiy** = o'z shaxsiy rasxodi + boshqa odam UNING UCHUN olgani
(`kim_uchun`), **umumiy** = umumiy rasxoddagi ULUSHI, butun summasi
EMAS (aks holda uch odamning analitikasi yig'ilsa uyning rasxodi uch
barobar chiqardi). `turi_boyicha`, `doira_bolaklari`,
`kategoriya_jadvali` `odam_id`/`qism` oladi; xulosa kartalari —
`odam_rasxod_xulosa()`.

Bo'lak yoki jadval qatori bosilsa `dialogs.KategoriyaRasxodlari` —
har bir rasxod (`ledger.kategoriya_rasxodlari()`, doira bilan BITTA
manba `_manba()` dan: qatorlar yig'indisi bo'lakka teng). «Qolganlari»
bo'lagi `idlar` orqali ichidagi hamma kategoriyani ochadi. Rasxod shu
oynadan tahrirlanadi (`RasxodDialog`) yoki tafsiloti ochiladi;
o'zgarsa oyna o'zini, yopilganda sahifa `oyna.yangila()` ni chaqiradi.

Shu oynada bir nechta rasxodni tanlab (Ctrl/Shift) kategoriyasini
almashtirish — `entries.rasxod_turi_qoy()`: bitta undo, pulga/ulushga
tegmaydi. Bog'langan mahsulot yangi kategoriyaniki bo'lmasa `item_id`
bo'shatiladi (undo qaytaradi). O'zgarish bo'lmasa `amal()` OCHILMAYDI.

## Analitika → «Reja va fakt»

Alohida varaq EMAS: `AnalitikaSahifa` sarlavhasidagi «Kategoriyalar |
Reja va fakt» tugmalari (`sahifa_reja_fakt.RejaFaktPanel`). Yangi jadval
yo'q — umumiy oylik reja `reja` qatorida (`tur='oylik'`, `budjet`
ustuni), kategoriya rejasi eski `budjet` jadvalida (oy yoki `'*'`).
Hisob bitta joyda — `plan.reja_va_fakt()`; fakt = oyning HAMMA
rasxodi, ichki kategoriya otasiga qo'shiladi. Umumiy qo'yilmagan
bo'lsa reja = kategoriyalar yig'indisi. Foiz `money.foiz()` (butun son,
100 dan oshadi — oshib ketgan reja CHEKLANMAYDI). «Limitga yaqin» —
`plan.YAQIN_FOIZ` (80). `reja_saqla()` va `reja_kochir()` — bitta undo.

### Rejaga band pul — `plan.band_pul()` (2026-10-01)

Reja tuzilgach pul BAND: joriy oyning sarflanmagan rejasi
(`reja − fakt`, manfiy bo'lsa 0) faol odamlarga `money.bol_teng` bilan
TENG bo'linadi va «Shaxsiy» varag'idagi Real/Adolatli balans, Hisobot
balans jadvali, pul darajasi chiziqlari (`ledger.darajalar(db, band)`)
va yon paneldagi «Qo'ldagi jami pul» dan ayirib ko'rsatiladi. Bu FAQAT
ko'rsatish: `v_balans`, audit va qarzga TEGMAYDI — `naqd`/`adolat` ni
bazada o'zgartirsangiz `adolat = naqd + sof` buziladi. Sarf
oshgani sari band kamayadi (aks holda bir pul ikki marta ayiriladi).

## Bir nechta mahsulot va reja yozuvlari (2026-10-01)

**Rasxodda kategoriya ichidan bir nechta mahsulot** — `dialogs.MahsulotRoyxat`
(qator: mahsulot, miqdor (dona, butun son), summa). Qatorlar
`rasxod_mahsulot` da; `rasxod.summa` = qatorlar yig'indisi
(`rk.tekshir` rad etadi), balans faqat `rasxod.summa` ni o'qiydi —
`v_balans`/audit o'zgarmagan. Bitta qator bo'lsa `rasxod.item_id` unga
bog'lanadi (avvalgidek), bir nechta bo'lsa NULL. Qoida
`rk.mahsulot_qatorlari()` / `rk.qatorlarni_yoz()` da — reja ham shuni
ishlatadi. Tahrirlash `rk.tahrirla()` (rasxod + qatorlar, bitta undo).
Eski qatorsiz rasxod tahrirda `item_id` dan bitta qator bo'lib ochiladi.
Mahsulot katalogda bo'lishi SHART EMAS (2026-10-01, foydalanuvchi
so'ragan): tanlagich yoziladigan, yangi nom yozilsa saqlashda
`rk.yangi_mahsulotlarni_qosh()` uni shu kategoriyaga katalogga qo'shadi
(narx = bir dona, `money.bol_teng` bilan; shu nom bo'lsa — o'sha,
katta-kichik harfga qaramay). Rasxod va reja bilan BITTA amalda.
Bot va «Bugun» dagi tezkor qo'shish hali bitta mahsulotli (qatorsiz).

**Reja rasxod kabi qo'shiladi** — `sahifa_reja_fakt.RejaYozuvDialog`:
sana, kategoriya, mahsulotlar, sabab, summa (kim to'ladi/bo'lish YO'Q —
pul chiqmaydi). Yozuv — oylik `reja` ning `reja_qator` qatori
(`sana` ustuni qo'shilgan), mahsulotlari `reja_mahsulot` da;
`plan.reja_yozuv_saqla/ochir/yozuvlari`. Kategoriya rejasi
`plan.turi_reja()` = yozuvlar (`yozuv_reja`, ichkisi otasiga) + eski
limit (`limit_reja`, `budjet` jadvali). «Umumiy reja va limitlar»
oynasi (`RejaDialog`) FAQAT limitni tahrirlaydi — `reja_saqla` ga
`turi_reja` bersangiz yozuvlar limitga aylanib ikki marta sanaladi.
`reja_kochir` yozuvlarni ham (mahsulotlari bilan) ko'chiradi.

### Umumiy va shaxsiy reja; «aslida to'landi» (2026-10-01)

Reja ikki DOIRADA: umumiy (`reja_qator.umumiymi=1`) va bitta odamning
shaxsiysi (`umumiymi=0, odam_id`). `plan.turi_reja/yozuv_reja/
reja_va_fakt/reja_yozuvlari(…, odam_id)`: `None` — umumiy (+ umumiy
summa va limitlar), `<id>` — o'sha odamniki. Fakt ham doirada:
umumiy — umumiy rasxodning BUTUN summasi (`ledger._manba` da
`odam_id=None, qism='umumiy'`), shaxsiy — odamning shaxsiy rasxodi va
unga olingani. Panelda «Umumiy | Shaxsiy» (birlamchi — umumiy).
`reja_bormi(db, oy)` birlamchi HAR QANDAY doirani so'raydi (`HAMMASI`).
`band_pul`: umumiy qolgani hammaga teng, shaxsiy qolgani — o'sha odamga.

Toifa qatori bosilsa `RejaKategoriyaOyna` — shu toifaning reja
RO'YXATLARI (har reja yozuvi bitta ro'yxat; yangi va o'chirish shu
yerda). Ro'yxat ochilsa `RejaRoyxatOyna` — mahsulotlari, har biriga
«aslida to'landi» va «Tahrirlash» (FAQAT shu yerda: umumiy/shaxsiy,
mahsulot qo'shish/olib tashlash; oyna `_qur()` bilan qayta quriladi,
saqlanmagan summalar nom bo'yicha saqlanadi). Reja o'chirilsa unga yozilgan rasxod QOLADI.
Eski kategoriya LIMITI ham shu oynada «Limit (mahsulotsiz)» qatori bo'lib
chiqadi; ochilsa `plan.limitni_royxatga()` uni oddiy ro'yxatga aylantiradi
(reja summasi o'zgarmaydi, bitta undo).
Panelning «Reja yozuvlari» kartasi YASHIRIN (`yozuvlar_karta`). `plan.reja_bajar()`
HAQIQIY rasxod yozadi/yangilaydi (`reja_qator.rasxod_id`), hammasi 0
bo'lsa uni o'chiradi; summalar `reja_mahsulot.tolangan` (mahsulotsiz
yozuvda `reja_qator.tolangan`). Fakt baribir rasxoddan — alohida fakt
saqlanmaydi. Shaxsiy rejani boshqa odam to'lasa — «uning uchun».

## «Shaxsiy» varag'i va yon panel (2026-10-01)

Qarz uchun YAGONA karta — «Qarzim» (ichki + tashqi,
`ledger.odam_qarzlari`), bosilsa `dialogs.QarzlarimOyna` (to'lash,
qisman qaytarish, yopish — mavjud oynalar orqali). «Sof pozitsiya»,
«Men uchun olingan», «Tashqi qarz» kartalari olib tashlangan;
«Kunlik harakat» YASHIRIN (`kunlik_karta`), «Jami kirim» kartasi olib tashlangan. Yon paneldagi pul — faqat
asosiy odamniki (`plan.qoldagi_pul`, `asosiy_odam` = `sozlama.asosiy_odam`
yoki birinchi faol odam): boshqalarning band ulushidan ularning
qo'lidagi pul yetmagani ham undan ayiriladi. Faqat ko'rsatish.

**Band pul hisobda bo'lmasa — qarz** (`plan.band_hisob`): hech kimdan
qo'lidagi puldan (naqd, manfiy bo'lsa 0) ortiq ayirilmaydi, real
balans rejadan minusga TUSHMAYDI. Yetmagani asosiy odam qoplaydi
(puli yetganicha); qolgani «Qarzim» ga «rejadan» bo'lib qo'shiladi
(`plan.odam_qarzlari` = `ledger.odam_qarzlari` + band qarzi). Ko'rsatish
joylari `plan.band_ayirma()` oladi, `band_pul()` EMAS.

«Bugun» sahifasi: «Oxirgi yozuvlar» YASHIRIN (`oxirgi_karta`), o'rniga
«Bugunga rejalangan» — `plan.kun_reja_yozuvlari()` (umumiy + hammaning
shaxsiysi), ikki marta bosilsa `RejaRoyxatOyna`. «Holat» matni —
`plan.royxat_holati()` (toifa oynasi bilan bitta). «Rejaga band» kartasi
bosilsa `dialogs.RejagaBandOyna` (`plan.band_tafsilot`).

Reja ro'yxatidan nusxa — `plan.reja_yozuv_nusxa` (keyingi kunga, oydan
chiqmaydi; to'langani va rasxodi ko'chmaydi).

## Hamyon — pulim qayerda: naqd va kartalar (2026-10-01)

`core/hamyon.py`, varaq `sahifa_hamyon.HamyonSahifa` («Hamyon»). Jadvallar:
`karta` (odamniki) va `karta_otkazma` (bitta odamning naqdi/kartalari
orasida; NULL = naqd). `rasxod.karta_id` / `kirim.karta_id` — pul
qayerdan chiqdi / qayerga tushdi (NULL = naqd).

**Naqd SAQLANMAYDI — u qolgani:** `naqd = v_balans.naqd − kartalar`.
Shuning uchun `naqd + kartalar = v_balans.naqd` har doim, `v_balans` va
audit O'ZGARMAGAN, belgisiz yozuvlar (import, bot, qarz, hisob-kitob,
tashqi qarz) o'z-o'zidan naqdda. Karta qoldig'iga faqat EGASINING yozuvi
kiradi (`kim_toladi`/`odam_id` = `karta.odam_id`). Yangi karta qoldig'i va
«Qoldiqni to'g'irlash» — naqd bilan O'TKAZMA (jami pul o'zgarmaydi).
Karta o'chirilsa qoldig'i naqdga qaytadi (o'tkazmasiz, undo bilan).
`rasxod_tahrir` da to'lovchi almashsa eski karta bog'lanishi NULL bo'ladi.

Tanlagich — `widgets.HamyonTanla` (RasxodDialog, Bugun tezkor qo'shish,
KirimDialog); odam almashsa `odam_qoy()`. Bot hozircha har doim naqd.

## Varaqlar nomi (2026-09-30)

Menyuda `MahsulotSahifa` — **«Kategoriyalar»** (kategoriya daraxti +
mahsulotlar), `KategoriyaSahifa` — **«Iconlar»** (ikonkaga nom berish).
Sinf va fayl nomlari ESKICHA qoldi — shuning uchun testlar varaqni
nomi bo'yicha emas, sinfi bo'yicha qidiradi. «Reja» va «Hisobot» varaqlari menyudan
olingan (`oyna.py` da izohga olingan qatorlar; sinflar joyida).

## Ikkita bo'lim va bekor qilish

`Oyna` ikki qavatli: `tashqi_stek` da 0 — `TanlovSahifa` (yon menyusiz
bosh ekran), 1 — qobiq (yon menyu + sahifalar steki). Ikkala bo'limning
sahifalari BITTA stekda (`HAMMA`), yon menyu faqat joriysini ko'rsatadi.
Shuning uchun bo'lim almashganda sahifa qayta qurilmaydi va filtrlar
joyida qoladi. Yangi sahifa `MOLIYA_SAHIFALAR` yoki `VAZIFA_SAHIFALAR`
ro'yxatiga qo'shiladi — `BOLIMLAR` dagi siljish o'zi hisoblanadi.

**Tezkor tugma qo'shmang.** `Ctrl+Z`, `Ctrl+1…8`, `F5` — hammasi ataylab
olib tashlangan. Bekor qilish faqat yozuvning tafsilot oynasidan
(`RasxodTafsilot`, `VazifaTafsilot`) bo'ladi: foydalanuvchi summasini va
ulushlarini ko'rib turib bosadi. `ui_tekshir.py` oynada tezkor tugma
qolmaganini tekshiradi — qo'shsangiz test qizil bo'ladi.

`db.undo()/redo()` o'zi joyida turibdi va testlar uni ishlatadi; faqat
UI dan chiqarilgan.

### Ovqat navbati

`vazifa_turi.navbat=1` — ish odamlar bo'ylab aylanadi;
`ergash_turi_id` — o'sha kuni OSHPAZNING O'ZIGA tushadigan ish.
Ikkalasi ham ustun, nom EMAS: foydalanuvchi ish nomini o'zgartirsa yoki
o'chirib qaytadan yaratsa (aynan shunday bo'lgan) nomga qarab
taxmin qiladigan kod jimgina ishlamay qo'yadi.

Yuvuvchi — oshpazning O'ZI (`yuvuvchi = oshpaz`). 2026-09-17 gacha
navbatdagi OLDINGI odam edi (`idlar[(boshi + i - 1) % n]`) —
foydalanuvchi o'zi o'zgartirdi, eskisiga qaytarmang. Idish baribir
alohida vazifa bo'lib qoladi: eslatma, «Albatta!» va hisobot uni
ovqatdan ajratib ko'radi. `tekshir.py` uchala odamni ham nomma-nom
tekshiradi.

Navbat tuzilgandan keyin `almashtir()` va `bersin()` bilan
o'zgartiriladi. `almashtir()` — ikki kunni o'rin almashtiradi
(keyingi kunlarga TEGMAYDI, navbat soni saqlanadi); `bersin()` — faqat
bitta kunni ko'chiradi. Ikkalasi ham oxirida `_yuvuvchini_tugrila()`
chaqiradi: oshpaz o'zgargach yuvuvchi eskisicha qolsa, «kim pishirsa
o'sha yuvadi» qoidasi jimgina buziladi. `tekshir.py` almashuvdan
keyin ikkala kunning yuvuvchisini ham tekshiradi.

`ergash_turi_id` o'chirilgan turga ishora qilishi mumkin. `tur_ergash()`
bunda None qaytaradi va navbat faqat pishirishni yozadi — dialog buni
ogohlantirib turadi, aks holda idish yuvish jimgina yo'qolardi.

### General uborka — haftalik navbat

`vazifa_turi.haftalik=1` — «general uborka» ishi. Bu `navbat` DAN
BOSHQA narsa, ikkalasini aralashtirmang:

| | `navbat=1` | `haftalik=1` |
|---|---|---|
| nechta ish | bitta (ovqat) | bir nechta (oshxona, sanuzel, uy) |
| qachon | har kuni | haftada bir marta |
| kim | bitta odam, ertaga keyingisi | hammasi bir kunda, har biri boshqa odamda |
| siljish | har KUN bir odam | har HAFTA hamma ish bir odam |

`uborka_rejasi()` ning yuragi bitta qator:
`idlar[(boshi + i + h) % n]` — `i` ishning raqami, `h` haftaning.
`+ h` ni olib tashlasangiz navbat aylanmay qoladi va Fayzulloxon
abadiy oshxonani tozalaydi. Uch hafta ichida har kim har ishni aynan
bir marta qiladi — `tekshir.py` juftliklarni sanab tekshiradi.

Uborka kuni `sozlama.uborka_kuni` da (0 = dushanba … 6 = yakshanba),
turlarda EMAS: u butun guruhga bitta, har turga takrorlab yozilsa
ular bir-biridan ajralib ketishi mumkin edi.

Uch ish `db.UBORKA` da va bir marta ekiladi (`meta.uborka_ekildi`).
Ekish yangi tur YARATMAYDI — avval nomi bo'yicha qidiradi va topilsa
faqat `haftalik=1` qo'yadi, aks holda mavjud bazalarda o'sha ish ikki
marta ko'rinardi.

### Ish qadamlari

`ish_qadam` — bitta ish turining ichidagi mayda ishlar ro'yxati
(«Sanuzelni tozalash» → unitaz, vanna, pol). Ular TURGA bog'lanadi,
vazifaga emas: ro'yxat har hafta bir xil, uni har biriktirishda
nusxalash mantiqsiz bo'lardi.

Qadam kalendarga tushmaydi va alohida belgilanmaydi — u guruhga
ketadigan xabardagi ro'yxat. Har qadamni alohida vazifa qilish
kalendarni o'nlab bir daqiqalik blok bilan to'ldirib tashlardi.

Vazifa qatorida faqat NOM turadi, shuning uchun `xabar._uborka_qadamlari()`
nom → qadamlar xaritasini quradi. Xaritaning O'ZI ustundan (`haftalik=1`)
quriladi — ya'ni nomga qarab taxmin qilinmaydi, `_rollar()` bilan
aynan bir xil qoida.

### Takroriy vazifa — qoida, nusxa emas

`vazifa_takror` — «har kuni namoz» degan QOIDA. Kalendardagi kunlar
undan chiqariladi: `takror_toldir()` bugundan boshlab `TAKROR_UFQ`
(30) kunga yetguncha yetishmagan `vazifa` qatorlarini yozadi. U
`main.py` da (oyna qurilishidan oldin) va `xabarchi.py` da chaqiriladi.

**Nega haqiqiy qator yoziladi, «virtual vazifa» emas.** Kalendar,
eslatma, hisobot va streak — hammasi `vazifa` jadvalidan o'qiydi.
Ikkinchi manba qo'shilsa o'sha to'rttasi ham ikki joydan o'qishga
majbur bo'lardi. `dars` bilan aynan bir xil sabab, va bog'lanish ham
o'shanaqa: `vazifa.manba` = `takror:<id>:<sana>`.

**Kalit ichida SANA turadi** — shuning uchun to'ldirish necha marta
chaqirilsa ham ikkinchi nusxa yozilmaydi. `xabarchi.py` har daqiqada
ishlaydi, ya'ni bu idempotentlik shart, tozalik emas.

**O'tmishga yozilmaydi.** Sanoq bugundan boshlanadi: dastur bir hafta
ochilmasa, o'tib ketgan kunlar «bajarilmagan» bo'lib kalendarga
to'kilardi.

**O'chirilgan kun qayta tirilmaydi.** Mavjudlik `ochirilgan` ni
filtrlamasdan tekshiriladi — foydalanuvchi bitta kunni bekor qilsa u
keyingi to'ldirishda qaytib kelmaydi. Bu shartni «faqat o'chirilmagani
bor» deb tuzatsangiz bekor qilingan kun bir daqiqadan keyin
qaytadi.

**`oraliq` naqshida sanoq har doim `boshlanish` dan yuradi**, «oxirgi
yozilgan kun» dan emas: bitta kun o'chirilsa yoki dastur bir hafta
ochilmasa ham «har 3 kunda» joyidan siljimasin.

**`oraliq or 1` YOZMANG.** 0 ham bo'sh deb hisoblanib jimgina 1 ga
aylanardi — «har 0 kunda» degan xato har kunlik qoidaga o'girilib
ketardi. `tekshir.py` buni tekshiradi.

**Hech narsa yetishmasa `db.amal()` ham ochilmaydi.** Bo'sh guruh undo
stekini ma'nosiz qadam bilan to'ldiradi VA `_redo_yolini_yop()` ni
chaqiradi — har daqiqada bir marta.

**To'xtatish tarixga tegmaydi.** `takror_ochir()` bugundan boshlab
faqat `holat='ochiq'` kunlarni oladi: bajarilgani ham, o'tgan kunlar
ham joyida qoladi.

Qoida FAQAT bitta joyda tuziladi — `VazifaDialog` dagi «Takrorlansin».
`VazifaTurlariSahifa` dagi karta faqat ro'yxat va ✕ ko'rsatadi:
ikkinchi yaratish shakli qo'yilsa ikkalasi jimgina bir-biridan
ajralib ketardi. Navbatli (ovqat) turda karta umuman chiqmaydi —
u allaqachon aylanma jadval.

### Namoz qazosi — `vz.qazo_qil()`

Uchinchi holat: `vazifa.holat='qazo'` (`vz.QAZO`). «Qazo bo'ldi»
(tafsilot oynasi yoki eslatma ostidagi `qazo:<id>` tugmasi) namozni
QAZO qiladi va o'sha odamga «<namoz> — qazosini o'qish» ishini
yozadi: vaqtsiz, bugunga, `manba='qazo:<namoz_id>'`. Ikkalasi bitta
undo. Namoz qayta ochilsa hali o'qilmagan qazo ishi ham o'chadi.

«Eslatish kerakmi» tekshiruvi `holat == BAJARILDI` EMAS, `vz.yopiqmi()`
— aks holda qazo bo'lgan namoz haqida bot so'rashda davom etadi.
Namoz NOMIDAN taniladi (`vz.namozmi()`, `NAMOZ_SOZLAR`) — takror
qoidalarida tur ustuni yo'q; qazo ishining o'zi namoz hisoblanmaydi.

### Shaxsiy va umumiy ish

`vazifa_turi.shaxsiy=1` — bu ish GURUHGA CHIQMAYDI. Bot uni faqat
egasiga shaxsiy yozadi («Kitob o'qish», «Dori ichish»).

Filtr `xabar._guruh_qatorlari()` da — YAGONA joyda. Sarlavha ham,
odam bloklari ham shundan oziqlanadi: ikkinchi nusxa qilsangiz
«bugun ish yo'q» degan sarlavha ostida vazifa ro'yxati chiqib qoladi.

**Bot o'zi boshlab shaxsiy yoza olmaydi** — Telegram taqiqlaydi.
Odam avval botga `/start` bosishi kerak; `_chatni_eslab_qol()` o'sha
paytda `odam.tg_chat` ni to'ldiradi (`username` bo'yicha topadi,
nom kiritilmagan bo'lsa hech kimga bog'lanmaydi — noto'g'ri odamga
shaxsiy xabar ketgandan ko'ra bog'lanmagani yaxshi).

`tg_chat` bo'sh bo'lsa shaxsiy vazifa YUBORILMAYDI **va guruhga ham
tushmaydi**. Buni «hech bo'lmasa guruhga yuboraylik» deb tuzatmang —
o'shanda «bu faqat sizga» degan va'da buziladi. Kim bosmagani
Sozlamalar → Telegram kartasida ko'rinib turadi (`dm_yoqmaganlar()`).

`kutilayotgan()` har bir xabarga `chat` qo'shadi: `None` — guruh,
raqam — shaxsiy suhbat. `yubor_kutilayotgan()` shuni o'qiydi.
`tugmani_ishla()` esa javobni bosilgan xabarning O'Z chatiga
qaytaradi (`sorov["message"]["chat"]["id"]`), aks holda shaxsiy
xabardagi «Albatta!» guruhdagi xabarni tahrirlab qo'yardi.

### Odatlar (streak) va yutuq

`streak` — bitta odam + bitta ish turi + nishon (7/14/21/28 kun).
`UNIQUE(odam_id, turi_id)`, ya'ni bir odamga bir ish uchun bitta odat.

**Ketma-ket kunlar soni HECH QAYERDA SAQLANMAYDI.** U har safar
`vazifa` jadvalidan qayta hisoblanadi (`streak_kunlari()`). Saqlangan
hisoblagich undo bilan ajralib qolardi: vazifa qaytarilsa hisoblagich
o'sha joyda turib olardi va streak yolg'on gapirardi. Kitob tengligi
bilan bir xil qoida — haqiqat bitta joyda, qolgani undan chiqadi.

**Bugun hisobga olinmaydi, agar hali bajarilmagan bo'lsa:** kun
tugamagan, streak esa uzilmagan. Bu shartni olib tashlasangiz har
ertalab hamma odat nolga tushib ketadi.

Nishonga yetilsa `yutuq` jadvaliga «Po'lat iroda» yoziladi va guruhga
tabrik boradi. Yutuq `bajar()` ning O'SHA amali ichida beriladi —
bitta undo qadami, aks holda vazifa qaytarilganda yutuq osilib
qolardi. Ikkinchi marta berilmaydi (`yutuq_bormi()`), va streak keyin
uzilsa ham joyida qoladi: «men buni qilgandim» degan yozuv o'chmaydi.

### Eslatmani kechiktirish

`vazifa.kechiktirildi` — eslatma shu vaqtdan oldin qayta yuborilmaydi.
Guruhda «Hali yo'q ⏳» bosilganda tanlov chiqadi (birlamchi 10/30/60
daqiqa, `sozlama.tg_kechiktirish` da).

**Vazifaning `vaqt` i O'ZGARTIRILMAYDI.** Vaqt — reja («men buni
19:00 da qilaman»), kechiktirish esa bir martalik holat. Vaqt surilsa
kalendardagi blok joyidan siljib ketardi va «har kuni 19:00» degan
odat asta-sekin yarim tunga surilardi.

**Eslatma kaliti kechiktirish vaqtini ham o'z ichiga oladi**
(`vazifa:12:2026-09-05 14:30:00`). Aks holda birinchi eslatma
«yuborilgan» deb belgilangani uchun surilgani HECH QACHON kelmasdi.

Vaqt SQLite formatida saqlanadi (orasida BO'SH JOY), `isoformat()`
emas — `tg_rasxod_dan` bilan aynan bir xil sabab.

### Xabar namunasi

`xabar.tur_namunasi()` — «bu ish guruhga qachon va qanday yoziladi?»
degan savolga javob (Vazifalar ro'yxatidagi 🔔 tugmasi).

Matn HAQIQIY funksiyalardan quriladi: `_bitta_blok()` va
`eslatma_matn()`. **Ko'rsatish uchun alohida matn YOZMANG** — nusxa
qilinsa ikkalasi jimgina bir-biridan ajralib ketadi va karta yolg'on
ko'rsata boshlaydi. Namuna qatori xotirada quriladi, bazaga hech
narsa yozilmaydi.

`_bitta_blok()` aynan shuning uchun `kunlik_odam_matn()` dan ajratib
olingan.

### Kalendar uch bo'lakdan

`HaftaTaqvim` — qobiq: ustida `HaftaBosh` (kun sarlavhalari + vaqtsiz
vazifalar), ostida aylanadigan `HaftaTor` (soat to'ri + vaqtli bloklar).

**Bosh ataylab aylanmaydi.** To'r 06:00 dan boshlanadi, uy ishlari esa
09:00 dan keyin — shuning uchun `qoy()` birinchi vazifaga surib qo'yadi.
Bosh ham aylanganida sarlavhalar ekrandan chiqib ketardi va qaysi ustun
qaysi kun ekani bilinmasdi. Vaqtsiz vazifalar ham boshda: aks holda
surilgandan keyin ular ko'rinmay qolardi.

**To'r — 24 soatlik HALQA** (2026-09-26). Sutka `NUSXA` (3) marta
ketma-ket chiziladi, har vazifa har nusxada bittadan blok
(`_bloklar` = `(blok, nusxa)`), `y_vaqtdan(daqiqa, nusxa=1)`.
`HaftaTaqvim._halqa()` aylantirgichni doim o'rtadagi sutkada ushlab
turadi — chegaradan chiqsa bir sutka balandligiga sakraydi, nusxalar
bir xil bo'lgani uchun ko'zga ko'rinmaydi: 23:59 dan keyin o'sha
kunning 00:00 i keladi. Diapazon `2 * sutka` dan kichik bo'lsa
sakramaydi (aks holda qisilgan qiymat halqani qayta chaqiradi).

Ikkala bo'lakning ustun kengligi bitta funksiyadan (`_ustun_kengligi`)
keladi — aks holda bosh va to'r bir-biriga to'g'ri kelmaydi.

**To'r aylantirgich ichida, bosh esa tashqarida.** Demak to'rning eni
aylantirgich enicha KICHIK. Shuning uchun bosh o'sha kenglikni bo'sh
joy qilib qoldiradi va aylantirgich `ScrollBarAlwaysOn` — u paydo
bo'lib-yo'qolsa ustunlar sakrab qoladi. «Kalendar qiyshiq» muammosi
aynan shu edi.

---

## Dars jadvali — `core/dars.py`

EduPage'ning ochiq API'sidan bitta guruhning haftalik jadvali olinadi
va bitta odamning shaxsiy kalendariga qo'yiladi. Ikkita chaqiruv:
`ttviewer.js?__func=getTTViewerData` qaysi hafta e'lon qilinganini
aytadi, `regulartt.js?__func=regularttGetData` esa o'sha haftaning
hamma kartasini beradi.

**Dars alohida jadval EMAS, oddiy `vazifa` qatori.** Aks holda
kalendar, eslatma va hisobot ikki manbadan o'qishga majbur bo'lardi.
Dars ekani `vazifa.manba` ustunidan bilinadi.

**`manba` kaliti — `dars:<sana>:<para>`**, EduPage'ning ichki `id` si
emas. Maktab jadvalni qayta chizsa `lessonid`/`cardid` lar butunlay
o'zgaradi va har hafta butun kalendar o'chib-qayta yozilardi. Sana
bilan para esa o'zgarmaydi, shuning uchun sinxron farqni ko'radi.

**Sinxron faqat `manba LIKE 'dars:%'` qatorlarga tegadi.** Qo'lda
yozilgan vazifa hech qachon o'chmaydi. `holat` va `bajarilgan` ham
tegilmaydi: jadval qayta o'qilgani odamning «bajardim» degan javobini
bekor qilmaydi — `tekshir.py` shuni tekshiradi.

**Bo'sh jadval kalendarni o'chirmaydi** (`sinxronla()` yiqiladi).
Tarmoq yarim javob bersa yoki guruh nomi o'zgarsa, butun hafta
jimgina o'chib ketardi.

**Fan nomi `vazifa_turi` da `shaxsiy=1` bo'lishi SHART.** Guruh/shaxsiy
filtri NOM bo'yicha ishlaydi (`vz.shaxsiy_nomlari()`), demak tur
bo'lmasa dars guruh xabariga chiqib ketadi. `_turni_taminla()` shuning
uchun o'chirilgan turni ham tiriltiradi.

**Tarmoqqa soatiga bir marta chiqiladi** (`ORALIQ_DAQIQA`), chegara
`sozlama.dars_tekshirildi` da. `xabarchi.py` har daqiqada ishlaydi,
jadval esa haftada bir marta o'zgaradi. Chegara urinishdan OLDIN
yoziladi — aks holda tarmoq yiqilganda har daqiqada qayta urinib,
xabarchini 20 soniyaga ushlab turardi.

Dars sinxroni `xabarchi.py` da Telegram tekshiruvidan OLDIN turadi:
kalendar bot sozlanmagan bo'lsa ham to'ldirilishi kerak. Yiqilsa
xabarchi to'xtamaydi — eslatma kelmagani jadval kechikkanidan yomonroq.

**Dars ikkita chegara bilan eslatiladi** (`OGOH_DAQIQA` = 5 soat
oldin, `KECHIKISH_DAQIQA` = 10 daqiqa keyin). Ogohlantirish —
`kutilayotgan()` dagi YAGONA oldindan ketadigan xabar, kaliti ham
boshqa (`dars_ogoh:`): bitta kalit ishlatilsa ogohlantirish
yuborilgani davomat savolini bo'g'ib qo'yardi.

Davomat tugmasining YOZUVI boshqa (`DARS_ALBATTA_TUGMA`), lekin
`callback_data` o'sha-o'sha (`bajar:id`). Ma'lumotni o'zgartirsangiz
guruhda va shaxsiy suhbatda turgan ESKI xabarlardagi tugmalar jimgina
o'lik bo'lib qoladi — bosiladi, hech narsa bo'lmaydi.

**Shaxsiy ish umumiy kalendarga ham tushmaydi.** Filtr —
`vz.oraliq(..., shaxsiysiz=True)`, nom bo'yicha, `xabar.py` dagi bilan
AYNAN bir xil qoida. Umumiy varaqning sanog'i ham o'sha bayroq bilan
chaqiriladi: qatorlar yashirinib, sanoq eskisicha qolsa «7 ta vazifa»
deb yozib, uchtasini ko'rsatardi.

`darslar()` kun raqamini `days` jadvalining tartibidan oladi, nomdan
emas. `hafta_boshi()` esa `datefrom` ni dushanbaga suradi: TTPU'da u
yakshanbaga tushadi, ya'ni jadval o'sha kundan emas, ERTASIDAN
boshlanadi.

## Telegram

`core/xabar.py` — sof mantiq, Qt bilmaydi; `xabarchi.py` uni Windows
rejasidan chaqiradi (dastur yopiq bo'lganda ham ishlashi uchun).
Reja **har daqiqada** ishlaydi: skript xabar yuborish bilan birga
guruhdagi tugma bosilishini ham qabul qiladi.

**Kunlik xabar ODAM BOSHIGA BO'LINADI**: `kunlik_bosh_matn()` —
sarlavha, `kunlik_bloklar()` — har odamga bittadan. Har bo'lakning
o'z kaliti (`odam_kaliti()`), demak bittasi yiqilsa qolgani qayta
yuborilmaydi. `kunlik_matn()` hammasini bitta matnga yig'adi, lekin
u FAQAT dastur ichidagi ko'rinish va testlar uchun — guruhga u
ko'rinishda yuborilmaydi.

Nega muhim: tugma bosilganda `_odam_xabarini_yangila()` faqat
o'sha odamning xabarini tahrirlaydi. Yagona xabar bo'lganda oshpaz
menyu tanlashi bilan hammaning ro'yxati qayta yozilardi.

Guruhdagi tugmalar: «Menyuyimizda nimalar bor» (kunlik xabar ostida,
taomni `vazifa.menyu` ga yozadi) va «Albatta!» (eslatma ostida,
`vz.bajar()` ni chaqiradi). Ikkalasini ham FAQAT vazifaning egasi
bosa oladi — `_egasimi()` `odam.telegram` bilan solishtiradi; nom
kiritilmagan bo'lsa tekshirib bo'lmaydi va ruxsat beriladi (aks holda
tugma jimgina o'lik bo'lardi).

Taomlar ro'yxati KODDA EMAS, `menyu` jadvalida (`core/menyu.py`,
Vazifalar varag'idagi «Menyu» kartasi) — `turi` va `vazifa_turi`
bilan bir xil g'oya. Boshlang'ich beshtasi `db.MENYU` da va bir
marta ekiladi, bayroq `meta.menyu_ekildi`.

Oshpaz tanlagan taom `vazifa.menyu` ga NOM bilan yoziladi, `menyu.id`
bilan emas: taom ro'yxatdan olib tashlansa ham «o'sha kuni nima
pishirilgan» degan yozuv qolishi kerak.

**Token manbada emas.** U `sozlama` jadvalida. Kodga yozib qo'ymang —
`tekshir.py` `core/xabar.py` ichida token borligini tekshiradi.

**`yuborilgan` — `db.apply()` dan o'tmaydigan ikkinchi jadval**
(`davr` dan keyin). Sabab: bu texnik iz, foydalanuvchi ma'lumoti emas.
Undo qilinsa xabar guruhga TAKROR tushardi.

**Guruhdagi tugma — `callback_data`, 64 baytdan oshmaydi.** Shuning
uchun data da faqat `amal:id` turadi (`menyu:12`, `taom:12:3`,
`bajar:12`), taom yoki vazifa NOMI emas. Oshsa Telegram tugmani
jimgina rad etadi: bosiladi, lekin hech narsa bo'lmaydi.

**Tugma bosilganda yangi xabar yuborilmaydi** — `yuborilgan.xabar_id`
dagi `message_id` bo'yicha O'SHA xabar tahrirlanadi. Aks holda har
menyu tanlovidan keyin guruhda yana bitta kunlik ro'yxat paydo
bo'lardi. `editMessageText` matn ham, klaviatura ham o'zgarmagan
bo'lsa xato beradi («message is not modified») — `_tahrirla_jim()`
uni yutadi, chunki bu bizda xato emas.

**`tg_offset` — `getUpdates` qayerdan davom etishi.** Saqlanmasa
Telegram bir xil bosilishni qayta-qayta beradi va bitta «Albatta!»
har daqiqada qayta bajarilardi. Offset qayta ishlashdan KEYIN
suriladi (`offsetni_sur()`): oldin surilsa, dastur o'rtada yiqilganda
bosilish yo'qoladi.

**Rasxod chegarasi (`tg_rasxod_dan`) SQLite formatida saqlanadi** —
`"2026-09-04 12:47:06"`, orasida BO'SH JOY. `isoformat()` ishlatsangiz
`"…T12:47:06"` chiqadi, matn solishtiruvida `' ' < 'T'` bo'lgani uchun
hech bir rasxod chegaradan o'tmaydi va e'lonlar JIMGINA yuborilmay
qoladi. Aynan shu xato bir marta bo'lgan.

---

## Qo'lga tushgan xatolar — qaytarmang

**`iter_rows(values_only=True)` A ustunidan boshlanadi**, varaqning
birinchi to'la ustunidan emas. `importer.py` da `min_col=B_USTUN` shuning
uchun turibdi. Buni olib tashlasangiz import jimgina 0 ta qator ko'chiradi.

**`OdamTanla.yangila()` `currentIndexChanged` ni uyg'otadi.** Agar sahifaning
`yangila()` funksiyasi ichida combo qayta to'ldirilsa va o'sha combo
`yangila` ga ulangan bo'lsa — cheksiz rekursiya. `sahifa_qosh.py` da
`QSignalBlocker` shuning uchun ishlatiladi.

**`v_juft_qarz` da hisob-kitob yo'nalishi.** To'lov qarzni kamaytiradi,
demak `kim_toladi` = qarzdor, `kimga` = kreditor, summa **minus** bilan.
Bir marta teskari yozilgan edi va to'lagan odam qarzdor bo'lib ko'rindi.

**`setStyleSheet("background:transparent")` ota-widgetga yozilsa** — Qt uni
BUTUN avlodga tarqatadi va global stildagi `background`ni bosib ketadi.
Natijada kartalar, tugmalar va kiritish maydonlari fonsiz qoladi (bir marta
"Umumiy qo'shish" tugmasi oq fonda oq bo'lib ko'rinmay qolgan). Shuning
uchun `sahifa_asosiy.py` dagi `shaffof()` yordamchisi selektor bilan
yozadi: `QWidget#Shaffof { background: transparent; }`. Yangi konteyner
qo'shsangiz — o'sha funksiyadan foydalaning, qo'lda yozmang.

**`QComboBox` va `QSpinBox` sahifani aylantirayotgan g'ildirakni
o'g'irlaydi.** Sichqoncha ustidan o'tsa Qt g'ildirakni maydonga
beradi va QIYMATNI o'zgartiradi — foydalanuvchi shunchaki pastga
aylantirmoqchi bo'lganda yo'l-yo'lakay sana, odam va davomiylik
jimgina almashib ketadi («hamma narsa qimirlayapti» degan shikoyat
aynan shundan). `widgets.GildirakQalqoni` butun dasturga
o'rnatilgan (`Oyna.__init__`): maydon FOKUSDA bo'lmasa hodisa eng
yaqin aylantirgichga uzatiladi. Yangi tanlagich qo'shsangiz hech
narsa qilish shart emas — qalqon turida ishlaydi, `ui_tekshir.py`
esa har varaqdagi har maydonni sinab ko'radi.

**Kalendar boshi IKKINCHI aylantirgichda emas.** U oddiy qutida
turadi va `_boshni_sur()` bilan to'r qancha surilsa SHUNCHA suriladi.
Ikkinchi aylantirgich qilib ko'rilgan edi: uning diapazoni to'rniki
bilan bir necha piksel farq qiladi (aylantirgich dastasining haqiqiy
eni `sizeHint()` dan boshqacha) va o'ng chekkada sarlavha o'z
ustunidan siljib qolardi. Bosh eni ham to'rniki bilan AYNAN teng
bo'lishi shart — ustun kengligi enidan hisoblanadi.

**Mayda o'zgarish uchun `oyna.yangila()` chaqirmang.** U butun
dasturni qayta quradi: bosilgan tugma o'chib qaytadan yasaladi,
sahifa ko'z oldida sakraydi va ochiq panel yopilib ketadi. Bitta
tugmaning yozuvi yoki bitta ro'yxat o'zgargan bo'lsa — o'sha
widgetning o'zini yangilang (`_qatorlar` xaritasi shuning uchun bor,
qarang `_shaxsiy_qoy()` va `_qadamlarni_yangila()`).
`oyna.yangila()` faqat balans yoki kalendar o'zgarganda kerak.

**Aylantirgich ichida `setFocus()` sahifani sakratadi.** Fokus olgan
widget ko'rinishi uchun `QScrollArea` o'sha yerga suradi. Shuning
uchun qadam o'chirilgandan keyin fokus ko'chirilmaydi, faqat
qo'shilgandan keyin (u yerda foydalanuvchi allaqachon o'sha
maydonga qarab turibdi).

**Ochilish/yopilish animatsiyasi `maximumHeight` bo'ylab boradi**
(`_TurQator.ochiqni_qoy()`), 190 ms, `InOutCubic`. Uch narsani
buzmang:
· animatsiya paytida `resizeEvent` o'lchov qo'ymaydi
  (`_animatsiyada`) — aks holda birinchi kadrdayoq oxiriga sakraydi;
· yopiq balandlik `sizeHint()` dan OLINMAYDI, `_yopiq_h` da
  saqlanadi — panel ko'rinib turganda `sizeHint` uni ham qo'shadi va
  yopilish maqsadi joriy balandlikka teng bo'lib qoladi (ya'ni hech
  narsa qimirlamaydi);
· yarim yo'lda qayta bosilsa harakat ORQAGA qaytadi, e'tiborsiz
  qolmaydi — `finished` avval uziladi, keyin `stop()`.

**`setVisible(True)` ni `addWidget()` DAN OLDIN chaqirmang.** Otasi
hali yo'q widget Qt'da OYNA demakdir: Windows unga sarlavha satri
chizadi (dastur ikonkasi — uy, «yoyish», «✕») va ekranda kichkina
qora quti bo'lib chaqnab o'tadi. `_Blok` da aynan shu bo'lgan —
bajarilgan vazifaning ✓ yorlig'i layoutga qo'shilishdan oldin
ko'rsatilardi, ya'ni kalendar ochilganda har bajarilgan ish uchun
bittadan quti. Windows ilgagi (`SetWinEventHook`) uni shunday
ko'rsatgan edi:

    Qt6112QWindowIcon  133x58  sarlavha='Farvon Uy'  KO'RSATILDI/YASHIRILDI

Sarlavha `setApplicationDisplayName()` dan keladi — sarlavhasi bo'sh
har qanday oyna «Farvon Uy» bo'lib ko'rinadi, ya'ni bu bizniki.
`setVisible(False)` xavfsiz: u oyna yaratmaydi.

`ui_tekshir.py` butun sinov davomida `QWidget.setVisible` ni kuzatadi
va otasiz widget ko'rsatilsa chaqiruv izi bilan yiqiladi.

**`setParent(None)` ko'rinib turgan widgetda — ekranda qora quti
chaqnaydi.** Otasiz widget Qt'da alohida OYNA demakdir: Windows unga
bir kadrga sarlavha satri chizadi (dastur ikonkasi — uy, «yoyish»,
«✕») va ostida bo'm-bo'sh oq maydon. `deleteLater()` o'chirishni
hodisalar navbatiga qoldiradi, ya'ni quti navbat kelguncha ekranda
turadi. Foydalanuvchi buni «Vazifalar»ga va «Shaxsiy»ga o'tganda
ko'rgan: ikkalasi ham ro'yxatni qayta quradi.

Widgetni o'chirishning YAGONA to'g'ri yo'li — `widgets.yoq()`:
avval `hide()`, keyin `setParent(None)`, keyin `deleteLater()`.
Yashirilgan widget oyna bo'lib chizilmaydi. `ui_tekshir.py`
`setParent(None)` ni `widgets.py` dan tashqarida uchratsa yiqiladi.

**Sahifa `QWidget` dan emas, `Sahifa` dan meros olsin.** `Sahifa`
(`sahifa_asosiy.py`) ichida aylantirgich bor. Oddiy `QWidget` bo'lsa
mazmun oyna balandligiga siqiladi va qatorlar bir-birining ustiga
chiqib ketadi — ro'yxat qancha uzun bo'lsa shuncha yomon.
«Vazifalar» varag'i aynan shu sabab buzilgan edi.

**Wrap qilingan `QLabel` qatorni siqib qo'yadi.** `QHBoxLayout` ning
`sizeHint` i wrap balandligini KO'RMAYDI (u faqat `heightForWidth`
dan chiqadi), demak uzun nomli qator o'zining eng kam o'lchamini bir
qatorlik deb aytadi va matn qirqiladi. `_TurQator.resizeEvent()`
shuning uchun `setMinimumHeight(self.sizeHint().height())` qiladi:
bu chegara kartadan aylantirgichgacha o'zi ko'tariladi.

**QSS'da `::drop-down`, `::down-arrow`, `::up-button` ni stillashtirmang** —
Qt o'sha zahoti standart chizishni to'xtatadi va strelka umuman
yo'qoladi. Xuddi shu narsa `image: url(none)` uchun ham.

**Ikonka.** Har o'lcham alohida chiziladi (`make_icon.py`). Bitta katta
rasmni cho'zib `.ico` yasash — vazifalar panelida xira ikonka demakdir.

**`keyingi_guruh()` da `ASC`, `DESC` emas.** Undo orqaga qarab yuradi,
demak redo uni teskari yechishi kerak: oxirgi undo qaysi guruhni olgan
bo'lsa, birinchi redo o'shani qaytaradi — ya'ni eng ESKI qaytarilgan
guruhni. `DESC` bo'lsa redo stekning narigi uchiga sakraydi va log
shoxlanadi: bir qism guruh qaytarilgan holda qolib, undan keyingilari
amalda bo'lib turadi. 2026-09-02 da aynan shu 45 ta yozuvni yo'qotgan.
Invariant: **amaldagi guruhlarning `id` si har doim qaytarilganlardan
kichik.** `tekshir.py` shuni tekshiradi.

**Undo'dan keyin yangi yozuv redo yo'lini yopadi** (`_redo_yolini_yop()`
`bekor=1` qo'yadi). Bu shunchaki tozalik emas: INSERT ni undo qilish
qatorni rostdan o'chiradi va SQLite o'sha `id` ni keyingi yozuvga qayta
beradi. Redo yopilmasa, u o'sha `id` ni egallagan **yangi** yozuvni bosib
ketardi. Shu sababli testlarda yozuvni `id` bo'yicha emas, mazmuni
bo'yicha tekshiring.

**Global QSS `QLabel { font-size }` `setFont()` dan kuchliroq.**
`e.setFont(theme.matn_shrift(38, 700))` yozsangiz yorliq baribir
oddiy o'lchamda chiqadi — stil varag'i uni bosib ketadi. Katta sarlavha
kerak bo'lsa o'lchamni widgetning O'Z stilida bering:
`e.setStyleSheet("font-size:40px;font-weight:700;…")`. `QPainter` bilan
chizilganda bu muammo yo'q — u yerda `setFont()` ishlaydi.

**`theme.aralash(a, b, ulush)` da `ulush` — `a` ning ulushi.**
Ochiq fon kerak bo'lsa raqam KICHIK bo'ladi: `aralash(rang, KARTA, 0.16)`
— 16% odam rangi, 84% karta. Teskarisini yozsangiz blok to'q rangda
chiqadi va ustidagi matn o'qilmaydi (kalendar bloklarida aynan shu
bo'lgan).

**Build Python 3.14 bilan.** 3.13 (Store versiyasi) da PySide6 yo'q.

---

## Fayl egaligi

| Qism | Fayllar |
|---|---|
| **Moliya yadrosi** | `money.py` `schema.sql` `db.py` `core/*.py` |
| **Vazifalar yadrosi** | `core/vazifa.py` (pulga tegmaydi, `audit()` uni ko'rmaydi) |
| **Dars jadvali** | `core/dars.py` (pulga tegmaydi; tarmoqqa chiqadigan yagona `core/` fayli — `xabar.py` dan tashqari) |
| **Frontend** | `ui/theme.py` `ui/widgets.py` `ui/dialogs.py` `ui/sahifa_*.py` `ui/oyna.py` |
| **Infra** | `main.py` `config.py` `crashlog.py` `xabarchi.py` `packaging/` `*.bat` |
| **Testlar** | `tekshir.py` `ui_tekshir.py` |

Bir vaqtda bir nechta agent ishlayotgan bo'lsa: `theme.py` va `widgets.py`
ni faqat frontend agenti tahrirlaydi — ular butun dastur ko'rinishini
belgilaydi va ikki tomondan tahrirlansa stil urishib ketadi.

`widgets.py` dagi ommaviy nomlar va ularning imzolari **o'zgarmaydi** —
to'rtta sahifa fayli va `dialogs.py` ularga tayanadi. Yangi widget qo'shish
mumkin, borini qayta nomlash mumkin emas.

---

## Yangi narsa qo'shish

**Yangi rasxod turi** — kod o'zgarmaydi, `turi` jadvaliga bitta INSERT
(Sozlamalar sahifasidan).

**Yangi bo'lish usuli** — `money.py` ga funksiya + `money.bol()` ga bitta
shart + `dialogs.py` ga radio tugma. `core/` va `db.py` ga tegmaydi.

**Yangi sahifa** — `ui/sahifa_*.py` da `Sahifa` dan meros olgan sinf,
keyin `oyna.py` dagi `MOLIYA_SAHIFALAR` (yoki `VAZIFA_SAHIFALAR`)
ro'yxatiga bitta qator. Sahifa faqat `yangila()` ni bajarishi kerak.

**Yangi vazifa turi** — kod umuman o'zgarmaydi: dasturning o'zidan,
Vazifalar varag'idagi «+ Yangi vazifa turi» dan qo'shiladi
(`vazifa_turi` jadvali).

Boshlang'ich beshta ish `db.VAZIFA_TURLARI` da va **bir marta**
ekiladi: bayroq `meta.vazifa_turi_ekildi` da turadi. Bayroqni olib
tashlasangiz foydalanuvchi o'chirgan turlar qayta tiriladi — shuning
uchun u bor. `_boshlangich()` da emas, chunki u faqat YANGI bazaga
ishlaydi, jadval esa mavjud bazalarga keyin qo'shilgan.
