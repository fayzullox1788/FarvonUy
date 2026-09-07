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

---

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
`ergash_turi_id` — o'sha kuni AVVALGI navbatchiga tushadigan ish.
Ikkalasi ham ustun, nom EMAS: foydalanuvchi ish nomini o'zgartirsa yoki
o'chirib qaytadan yaratsa (aynan shunday bo'lgan) nomga qarab
taxmin qiladigan kod jimgina ishlamay qo'yadi.

Yuvuvchi — `idlar[(boshi + i - 1) % n]`, ya'ni navbatdagi OLDINGI odam.
Buni `+1` ga o'zgartirsangiz Fayzulloxon pishirganda Otabek yuvadigan
bo'ladi — `tekshir.py` uchala juftlikni ham nomma-nom tekshiradi.

Navbat tuzilgandan keyin `almashtir()` va `bersin()` bilan
o'zgartiriladi. `almashtir()` — ikki kunni o'rin almashtiradi
(keyingi kunlarga TEGMAYDI, navbat soni saqlanadi); `bersin()` — faqat
bitta kunni ko'chiradi. Ikkalasi ham oxirida `_yuvuvchini_tugrila()`
chaqiradi: oshpaz o'zgargach yuvuvchi eskisicha qolsa, «kim pishirsa
undan oldingi yuvadi» qoidasi jimgina buziladi. `tekshir.py` almashuvdan
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

Ikkala bo'lakning ustun kengligi bitta funksiyadan (`_ustun_kengligi`)
keladi — aks holda bosh va to'r bir-biriga to'g'ri kelmaydi.

**To'r aylantirgich ichida, bosh esa tashqarida.** Demak to'rning eni
aylantirgich enicha KICHIK. Shuning uchun bosh o'sha kenglikni bo'sh
joy qilib qoldiradi va aylantirgich `ScrollBarAlwaysOn` — u paydo
bo'lib-yo'qolsa ustunlar sakrab qoladi. «Kalendar qiyshiq» muammosi
aynan shu edi.

---

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
