# Farvon Uy

Uch kishilik uy uchun moliya hisobi. Lokal, oflayn, bitta kompyuterda.
SQLite + PySide6. Hech qanday server, hech qanday internet.

`Uy moliya.xlsx` ning o'rnini bosadi — va Excel qila olmagan uchta ishni
qiladi: **yaxlitlashda tiyin yo'qotmaydi**, **kitob tengligini o'zi
tekshiradi**, va **kim kimga qancha berishini o'zi hisoblab beradi**.

---

## Ishga tushirish

| | |
|---|---|
| Manbadan ochish (test uchun) | `run.bat` |
| Hamma testni ishga tushirish | `tekshir.bat` |
| Installer yasash | `build.bat` → `installer\FarvonUySetup.exe` |

Kerak: **Python 3.14** (`py -3.14`) va **Inno Setup 6** (faqat build uchun).

Ma'lumotlar bazasi `%LOCALAPPDATA%\FarvonUy\farvonuy.db` da.
Dastur o'chirilsa ham **baza o'chmaydi**.

---

## Ikkita bo'lim

Dastur ochilganda yon menyu emas, **tanlov** chiqadi:

| Bo'lim | Nima uchun |
|---|---|
| **Moliya** | kirim, rasxod, qarz, reja, hisobot — pul hisobi |
| **Vazifalar** | haftalik kalendar: kim, qaysi kuni, soat nechada |

Har bo'limning o'z yon menyusi bor; «‹ Bo'limlar» tanlovga qaytaradi.

### Vazifalar

Uchta varaq:

| Varaq | Nima ko'rsatadi |
|---|---|
| **Kalendar** | umumiy haftalik kalendar — uchalasining ishi birga; yangi vazifa shu yerda ham yaratiladi |
| **Vazifalar** | uy ishlarining ro'yxati (kalendar EMAS). Har ishning yonida «Biriktirish» — kim, qaysi kun, soat nechada |
| **Shaxsiy** | bitta odamning o'z kalendari — sanoqlari, hafta to'ri va ro'yxati |

«Vazifalar» dagi ro'yxat `vazifa_turi` jadvalida turadi: bu shunchaki
tayyor ish nomlari, ular kalendarga tushmaydi. Biriktirilganda
`vazifa` jadvaliga yangi qator bo'ladi — shuning uchun ish turini
ro'yxatdan olib tashlash allaqachon biriktirilgan vazifalarga tegmaydi.

`uy moliya plan.xlsx` ning «Vazifalar» varag'idan olingan:

* haftalik umumiy kalendar — hamma nima qilishi ko'rinib turadi;
* vazifa aniq odamga, aniq kunga va aniq **soatga** biriktiriladi;
* «Kim» filtri — odam faqat o'zinikini ko'radi («shaxsma shaxs»);
* **kun o'tkazib yuborilsa** — «Kunni surish» o'sha kundan keyingi
  bajarilmagan hamma vazifani bir kunga suradi (bajarilganlar joyida
  qoladi). Bu bitta qadam: kerak bo'lsa birdaniga qaytariladi.

Kunlik / haftalik / oylik ko'rinish bor. Bo'sh katakka bosilsa — o'sha
kun va soatga yangi vazifa.

### Hisobotlar

Hisobotlar **Kalendar** varag'ida, bitta tanlagich ostida. Oraliq —
hozir ko'rinib turgani, odam esa yuqoridagi tanlovdan:

| Hisobot | Nima ko'rsatadi |
|---|---|
| **Vazifalar kalendari** | kim qaysi kuni nima qilgan |
| **Umumiy rasxodlar** | uy nimaga qancha sarfladi — **faqat umumiy** xarajat, turlar bo'yicha ulushi bilan |
| **Shaxsiy ulush** | o'sha umumiy rasxoddan **har kimga qancha tushdi** |

«Shaxsiy ulush» — «mening rasxodim» EMAS: bu umumiy xaridning shu
odamga to'g'ri keladigan qismi. Shaxsiy rasxod ikkala hisobotga ham
umuman kirmaydi — u odamning o'z puli.

### Kalendarni ulashish

Ikkala kalendar ham faylga chiqadi — «Kalendar» varag'ida umumiy,
«Shaxsiy» da bitta odamniki:

| Tugma | Nima chiqadi |
|---|---|
| **HTML** | bitta o'zi ochiladigan fayl — kunlar bo'yicha kartalar, bajarilgani chizib tashlangan, kechikkani qizil. Telegramga tashlansa telefonda ham to'liq ochiladi. |
| **Excel** | ikkita varaq: «Vazifalar» (filtrli ro'yxat) va «Xulosa» (kim nechta bajardi) |

Umumiy kalendarda «Kim» filtri va ko'rinish (kunlik/haftalik/oylik)
faylga ham tushadi: nima ko'rinib tursa, o'sha chiqadi.

**Fayllar to'g'ri ish stoliga tushadi** va darhol ochiladi — shu yerdan
Telegramga sudrab tashlash oson. (OneDrive yoqilgan bo'lsa ham to'g'ri
joyga tushadi: ish stoli yo'li Windows'ning o'zidan so'raladi.)
`FARVONUY_DATA` o'rnatilgan bo'lsa — masalan testlarda — fayllar o'sha
papkadagi `eksport` ichida qoladi.

### Ovqat navbati

Ovqat qilish — **navbatli** ish. Bitta odamga biriktirilsa, qolganlari
o'zi joylashadi (`odam.tartib` bo'yicha), va har kuni idish yuvish ham
qo'shiladi:

```
Dushanba   19:00  Fayzulloxon pishiradi   20:00  Abbosxon yuvadi
Seshanba   19:00  Otabek pishiradi        20:00  Fayzulloxon yuvadi
Chorshanba 19:00  Abbosxon pishiradi      20:00  Otabek yuvadi
Payshanba  19:00  Fayzulloxon … (aylanadi)
```

Qoida: **idishni navbatdagi OLDINGI odam yuvadi** — ya'ni kecha
pishirgan odam bugun yuvadi.

Necha kunga yozilishi «Biriktirish» oynasida tanlanadi (birlamchi
7 kun) va yozishdan oldin butun ro'yxat ko'rsatiladi. Hammasi bitta
amal: kerak bo'lsa birdaniga qaytariladi.

### Navbatni o'zgartirish

Reja tuzilgandan keyin ham o'zgartirish mumkin — vazifa blokiga bosing,
tafsilot oynasida «Navbatni o'zgartirish» bor:

| Tugma | Nima qiladi |
|---|---|
| **Almashtirish** | ikki odam navbatini almashadi: bu kun tanlangan odamga, uning keyingi navbati esa hozirgi egasiga o'tadi. **Qolgan kunlar joyida qoladi va navbat soni ikkalasida ham o'zgarmaydi.** |
| **Faqat shu kunni berish** | almashuvsiz — shu kun boshqasiga o'tadi, xolos. Reja tuzilishidan oldingi tartibsizlikni tekislash uchun: kim ortiqcha qilgan bo'lsa, bitta navbat boshqasiga o'tkaziladi. |

Ikkalasida ham o'sha kunning **idish yuvuvchisi o'zi qayta hisoblanadi** —
«kim pishirsa, undan oldingi yuvadi» qoidasi buzilmaydi. Har biri bitta
amal: kerak bo'lsa bitta qadamda qaytariladi.

Ovqatdan keyin qaysi ish kelishi Vazifalar ro'yxatidagi «keyin:»
tanlagichida turadi — ish nomiga qarab taxmin qilinmaydi, shuning uchun
nomni o'zgartirsangiz ham buzilmaydi.

Excel'dagi beshta ish bazaga bir marta ekiladi (ovqat qilish, idish
yuvish, dasturxon, gaz plitasi, musor). «Vazifalar» varag'idan yangisini
qo'shish yoki keraksizini olib tashlash mumkin — o'chirilgani dastur
qayta ochilganda tirilmaydi.

### General uborka

Haftada bir marta qilinadigan katta ishlar — birlamchi holda
**yakshanba**, uchtasi bir kunda:

| Ish | Ichida nima bor |
|---|---|
| **Oshxonani tozalash** | gaz plitasi, rakovina va kran, stol va javon usti, muzlatkich, pol |
| **Sanuzelni tozalash** | unitaz, vanna va dush, rakovina va oyna, pol, sochiqlar |
| **Umumiy uyni tozalash** | changlarni artish, pollarni artish, pilesos |

Har birini boshqa odam qiladi, va **har hafta hammasi keyingi odamga
o'tadi**. Ya'ni birinchi yakshanba Fayzulloxon oshxonani tozalasa,
keyingi yakshanba u sanuzelga o'tadi, oshxona esa Otabekka tushadi.
Uch hafta ichida har kim har ishni aynan bir marta qiladi — «men doim
sanuzelni tozalayman» degan gap chiqmaydi.

Reja «Vazifalar» varag'idagi **General uborka** kartasidan tuziladi:
kuni, soati, kim boshlashi va necha haftaga. Yozishdan oldin birinchi
kun kimga nima tushishi ko'rsatiladi. Hammasi bitta amal — kerak
bo'lsa birdaniga qaytariladi.

Uborka kuni yakshanba bo'lishi shart emas: kartadagi «Kuni:» ni
o'zgartirib «Kun va soatni saqlash» ni bosing.

### Ish qadamlari

Har ishning ichiga mayda ishlar qo'shish mumkin — ro'yxatdagi
**«Qadamlar»** tugmasi shuni ochadi. Qadam kalendarga tushmaydi va
alohida belgilanmaydi: u guruhga ketadigan xabarda ish nomining
ostida ro'yxat bo'lib chiqadi, ya'ni «nima qilish kerak edi?» degan
savol takrorlanmaydi.

Boshlang'ich qadamlar bir marta ekiladi; xohlaganini qo'shish yoki
olib tashlash mumkin.

### Odatlar va yutuqlar

«Har kuni kitob o'qish» kabi odat: **Vazifalar → Odatlar** kartasidan
kim, qaysi ish va nishon (7, 14, 21 yoki 28 kun) tanlanadi.

Kvadratchalar to'lib boradi: `▪▪▪▪▪▫▫ 5/7`. Nishonga yetilsa
**«Po'lat iroda»** yutug'i beriladi va guruhda tabrik chiqadi.

* Bugun hali bajarilmagan bo'lsa sanoq **uzilmaydi** — kun tugamagan.
* O'rtada bir kun o'tkazib yuborilsa sanoq qaytadan boshlanadi.
* Qo'lga kiritilgan yutuq **hech qachon yo'qolmaydi**: keyin odat
  uzilsa ham, to'xtatilsa ham joyida qoladi.

### «Hali yo'q» — eslatmani kechiktirish

Ish vaqti tugagach bot so'raydi: **«Albatta! ✅»** yoki
**«Hali yo'q ⏳»**. Ikkinchisi bosilsa qachon qilishingiz so'raladi —
birlamchi holda 10 daqiqa, 30 daqiqa yoki 1 soat. O'sha vaqt kelgach
eslatma qayta keladi.

Variantlarni o'zgartirsa bo'ladi: ro'yxatdagi **🔔** tugmasi →
«Keyinroq» qatori (vergul bilan, masalan `15, 45, 90`).

Vazifaning **soati o'zgarmaydi** — kalendardagi joyi o'sha-o'sha
qoladi, faqat eslatma suriladi.

### 🔔 — bu ish qanday yoziladi

Ro'yxatdagi har ishning yonida **🔔** tugmasi bor. U bitta kartada
ko'rsatadi:

* **qachon** — kunlik ro'yxat soati va eslatma vaqti
  (boshlanish + davomiylik);
* **qanday** — guruhga tushadigan matnning O'ZI, so'zma-so'z;
* **qayerga** — uy guruhiga yoki shaxsiy suhbatga.

Hammasini shu yerda o'zgartirsa ham bo'ladi: davomiylik, umumiy/shaxsiy,
kunlik soat va «keyinroq» variantlari.

### Dars jadvali

Universitet jadvali (EduPage) bitta odamning **shaxsiy** kalendariga
o'zi ko'chiriladi. Hozir sozlangani: **SE-25 → Fayzulloxon**.

Har dars oddiy vazifa bo'lib tushadi — soati, davomiyligi (80 daqiqa)
va izohida **o'qituvchi · xona**:

```
🔒 Shaxsiy ro'yxatingiz:
⏳ 14:20  Fundamentals of Computer Architecture (lec)
      Asretdinova Lobar · BLUE HALL
⏳ 15:50  Data Structures and Algorithms (lec)
      Mahamatov Nurilla · BLUE HALL
```

Dars **guruhga ham, umumiy kalendarga ham chiqmaydi** — u shaxsiy ish,
uy vazifasi emas. «Kalendar» varag'ida faqat uy ishlari turadi,
darslar «Shaxsiy» varag'ida.

Bot ikki marta yozadi, ikkalasi ham **shaxsiy suhbatga**:

| Qachon | Nima |
|---|---|
| Dars boshlanishidan **5 soat oldin** | «bugun soat 14:20 da darsingiz bor» — fan, o'qituvchi va xona. Tugma yo'q, bu shunchaki eslatma. |
| Dars tugagach **10 daqiqadan keyin** | «Davomat: darsda bo'ldingizmi?» — **Qatnashdim ✅** yoki **Hali yo'q ⏳** |

Nega 10 daqiqa: dars tugagan zahoti so'ralsa odam hali auditoriyada
bo'ladi. Uy ishlarida esa eskisicha — vaqti tugashi bilan so'raladi.

**Jadval o'zgarsa o'zi yangilanadi.** `xabarchi.py` soatiga bir marta
EduPage'dan o'qiydi va farqni qo'yadi: yangi dars qo'shiladi, xonasi
yoki soati o'zgargani tuzatiladi, olib tashlangani o'chadi. Hech narsa
o'zgarmagan bo'lsa hech narsa yozilmaydi.

Ikki narsaga **tegilmaydi**: qo'lda yozilgan vazifa (dars emas) va
allaqachon «bajarildi» deb belgilangan dars. Butun yangilanish bitta
amal — kerak bo'lsa bitta qadamda qaytariladi.

Sozlash `sozlama` jadvalida: `dars_yoq`, `dars_sinf`, `dars_odam`.
Boshqa guruh kerak bo'lsa `dars_sinf` ni o'zgartirish yetarli — kod
tegilmaydi.

### Shaxsiy va umumiy ish

Ro'yxatdagi har ishning yonida **«👥 Umumiy» / «🔒 Shaxsiy»**
tugmasi bor (yangi ish qo'shayotganda ham «Kimga:» qatorida
so'raladi):

| | Kimga boradi |
|---|---|
| **Umumiy** | uy guruhiga — hamma ko'radi (musor, ovqat, uborka) |
| **Shaxsiy** | faqat egasiga, bot bilan shaxsiy suhbatda (kitob o'qish, dori ichish) |

Shaxsiy ish guruh xabarida **umuman ko'rinmaydi** — na ro'yxatda, na
eslatmada. Agar kunning hamma ishi shaxsiy bo'lsa, guruhga «bugun
vazifa yo'q» deb yoziladi.

Xuddi shu qoida **«Kalendar» varag'ida** ham ishlaydi: umumiy kalendar
uchalasining UY ishlarini ko'rsatadi, shaxsiy ish u yerga tushmaydi.
Egasi uni «Shaxsiy» varag'ida ko'radi. Yuqoridagi sanoq (nechta
vazifa, nechta bajarildi) ham shunga qarab hisoblanadi.

**Shaxsiy xabar ishlashi uchun odam botga bir marta `/start` bosishi
kerak** — Telegram botga o'zi boshlab yozishga ruxsat bermaydi.
Kim bosmagani **Sozlamalar → Telegram guruhi** kartasida ko'rinib
turadi. Bosmagan odamning shaxsiy vazifasi yuborilmaydi va guruhga
ham tushmaydi: «bu faqat sizga» degan va'da buzilmaydi.

---

## Uchta raqam

Har odamning uchta soni bor. Ular bir-biriga bog'langan va bu bog'lanish
dasturning eng muhim qoidasi:

```
adolatli balans  =  real balans  +  sof pozitsiya
```

| Raqam | Ma'nosi |
|---|---|
| **Real balans** (`naqd`) | Hozir qo'lida turgan pul |
| **Sof pozitsiya** (`sof`) | + boshqalar unga qarzdor · − u qarzdor |
| **Adolatli balans** (`adolat`) | Hamma hisoblashsa qoladigan pul |

Excel'da bu ikkitasi bor edi, lekin ular orasidagi bog'lanish hech qayerda
tekshirilmasdi. Bu yerda `ledger.audit()` uni **har safar** tekshiradi.

### Rasxodning uch turi

| Tur | Kim to'laydi | Kimning rasxodi | Natija |
|---|---|---|---|
| **Umumiy** | bir kishi | hammaniki | teng (yoki foiz/og'irlik/aniq) bo'linadi |
| **Shaxsiy** | o'zi | o'ziniki | faqat uning balansidan chiqadi |
| **Boshqa uchun** | bir kishi | boshqasiniki | **to'liq o'sha odamning qarzi** |

«Boshqa uchun» — bu dasturning eng muhim mayda detali. Masalan Fayzulloxon
Otabekka 300 000 lik poyabzal olib berdi:

```
NOTO'G'RI (Excel'da shunday qilishga majbur edik):
    Otabekka  +300 000 kirim
    Otabekka  −300 000 shaxsiy rasxod
    →  uning kirimi ham, rasxodi ham soxta ko'rinadi

TO'G'RI (dastur shunday yozadi):
    Otabekning qo'lidagi puli  →  o'zgarmaydi
    Otabekning qarzi           →  +300 000
    →  chunki pul uning qo'liga umuman tegmagan
```

Pulni qo'liga bergan bo'lsangiz — u **Qarz**. Uning o'rniga narsani
o'zingiz sotib olgan bo'lsangiz — bu **Boshqa uchun**. Ikkisi boshqa
narsa, va dastur ularni chalkashtirmaydi.

### Kafolatlar

Dastur har ochilganda va har yozuvdan keyin quyidagilarni tekshiradi:

1. `SUM(sof) = 0` — kimdir qarzdor bo'lsa, kimdir kreditor. Boshqacha bo'lishi mumkin emas.
2. `SUM(naqd) = SUM(kirim) − SUM(rasxod)` — pul yo'qdan paydo bo'lmaydi.
3. Har odam uchun `adolat = naqd + sof`.
4. Har umumiy rasxodning ulushlari yig'indisi aynan rasxodga teng.
5. Shaxsiy rasxodda ulush bo'lmaydi.

Bittasi buzilsa — «Hisobot» sahifasida qizil yozuv chiqadi.

---

## Qarz qayerdan chiqqan

«Qarz» sahifasidagi «Otabek → Fayzulloxon: 547 667» qatoriga bosilsa,
o'sha son NIMADAN yig'ilgani ochiladi: har bir umumiy rasxod ulushi,
to'g'ridan-to'g'ri qarz va to'lov — sanasi, nomi va holati bilan.

`+` qarzni oshirgan yozuv, `−` kamaytirgan (teskari yo'nalishdagi
rasxod yoki to'lov). **Qatorlar yig'indisi aynan yuqoridagi songa
teng** — `tekshir.py` har juftlik uchun shuni tekshiradi, chunki
tafsilot boshqa raqam ko'rsatsa butun sahifaga ishonch yo'qoladi.

---

## Yaxlitlash

`1 559 000 ÷ 3 = 519 666.666…` — Excel buni float qilib saqlaydi va har
hisobda tiyin yo'qoladi.

Bu yerda pul **har doim butun son**. Bo'lganda qoldiq yo'qolmaydi:

```
1 559 000  →  519 667 + 519 667 + 519 666   (yig'indi aniq)
```

Ortiqcha so'm kimga tushishi tasodifiy emas: **shu paytgacha eng kam
ortiqcha so'm olgan odamga** beriladi (`v_yaxlitlash` viewi hisoblab
turadi). Shuning uchun vaqt o'tishi bilan yaxlitlash hech kimga zarar
qilmaydi — va rasxod oynasida kimga tushgani yozib ko'rsatiladi.

---

## Loyiha tuzilishi

```
src/
  config.py        yo'llar, %LOCALAPPDATA%
  money.py         butun son pul, bo'lish algoritmlari (teng/foiz/og'irlik/aniq)
  schema.sql       25 jadval, 5 view
  db.py            YAGONA yozuv nuqtasi: apply() + undo/redo + zaxira + davr qulfi
  crashlog.py      tutilmagan xatolarni faylga yozadi
  core/
    entries.py     kirim / rasxod / qarz / hisob-kitob
    splitting.py   kim qatnashadi (yo'q kunlar) + yaxlitlash navbati
    ledger.py      balanslar, juft qarzlar, AUDIT
    settle.py      minimal to'lovlar (n kishi → ko'pi bilan n−1 to'lov)
    plan.py        katalog, haftalik reja, reja/fakt, budjet, prognoz
    recurring.py   takroriy rasxodlar (ijara, internet)
    reports.py     Excel va HTML hisobot (moliya + vazifa kalendari)
    importer.py    Uy moliya.xlsx → baza
    vazifa.py      uy vazifalari (pulga tegmaydi)
    xabar.py       Telegram xabarlari
  ui/
    theme.py       ranglar va stil
    widgets.py     qayta ishlatiladigan bo'laklar
    dialogs.py     yozuv kiritish oynalari
    sahifa_tanlov.py     bosh ekran: ikkita bo'lim
    sahifa_vazifalar.py  kalendar + ish turlari + general uborka + shaxsiy varaq
    sahifa_*.py    moliya sahifalari
    oyna.py        asosiy oyna (ikkita bo'lim)
  xabarchi.py      Telegram xabarchisi (rejadan chaqiriladi)
  tekshir.py       yadro testlari
  ui_tekshir.py    UI testlari (ekransiz)
```

---

## Ikkita qat'iy qoida

**1. Hamma yozuv `db.apply()` dan o'tadi.**
UI hech qachon to'g'ridan-to'g'ri `INSERT`/`UPDATE` yozmaydi. Shuning uchun
har o'zgarish `ozgarishlar` jadvalida qoladi va bir amal — u nechta qator
yozgan bo'lsa ham — bitta qadamda qaytariladi.

**2. Hech narsa o'chirilmaydi.**
`DELETE` — bu `ochirilgan=1`. Tarix hech qachon yo'qolmaydi.

---

## Ulashish

Dastur bitta kompyuterda turadi, lekin hisob uchta odamniki.
«Hisobot» sahifasidan:

- **HTML hisobot** — bitta o'zi ochiladigan fayl. Telegramga tashlansa
  Otabek ham, Abbosxon ham o'z balansini, qarzini va pul nimaga ketganini
  ko'radi. Internet ham, Excel ham kerak emas.
- **Excel hisobot** — eski `Uy moliya.xlsx` ga o'xshash tuzilishda.
- **Shaxsiy hisobot** — «Shaxsiy» sahifasida, bitta odam uchun.

---

## Telegram guruhi

Bot uy guruhiga uch xil xabar yozadi:

| Qachon | Nima |
|---|---|
| Har kuni belgilangan soatda | sana sarlavhasi, keyin **har odamga alohida xabar** — faqat o'ziniki |
| Vazifa vaqti tugagach | o'sha odam teg qilinadi: «bajardingizmi?» + «Albatta!» tugmasi |
| Yangi **umumiy rasxod** yozilganda | nomi, summasi, kim to'lagani va kim qancha ko'tarishi |

Shaxsiy deb belgilangan ishlar guruhga emas, **egasining o'ziga**
boradi — pastdagi «Shaxsiy va umumiy ish» ga qarang.

Sozlash: **Sozlamalar → Telegram guruhi**. Token va guruh raqami
`sozlama` jadvalida — ya'ni sizning bazangizda saqlanadi, manba kodda
ham, installerda ham yo'q. Odamlarning `@nom` lari o'sha sahifadagi
«Telegram:» qatoridan qo'yiladi.

Guruh raqamini qo'lda topish shart emas: botni guruhga qo'shing, o'sha
guruhga bitta xabar yozing va «Guruhni aniqlash» tugmasini bosing.

### Kunlik xabar bo'lak-bo'lak

Ertalabki xabar bitta uzun ro'yxat EMAS. Avval sarlavha (sana va
kirish), keyin **har odam uchun bittadan xabar** — unda faqat
o'zining ishlari turadi va o'zi teg qilinadi.

Sabab: uyumda odam o'z qatorini izlashi kerak bo'lardi, va tugma
bosilganda («Albatta!», menyu) qaysi qism kimniki ekani bilinmasdi.
Alohida bo'lgach — bosilganda **faqat o'sha odamning xabari**
tahrirlanadi, qolganlariniki tegilmaydi.

Har bo'lakning o'z kaliti bor (`kunlik:2026-09-05`,
`kunlik:2026-09-05:odam:2`), ya'ni bittasi yuborilmay qolsa keyingi
urinishda faqat o'sha qayta yuboriladi. Hamma ishi allaqachon
bajarilgan odamga yangi xabar ochilmaydi.

### Guruhdagi tugmalar

Xabarlar ostida tugma bor — ya'ni javob guruhdan beriladi, dasturga
kirish shart emas.

| Tugma | Qayerda | Nima qiladi |
|---|---|---|
| **Menyuyimizda nimalar bor 🍲** | kunlik ro'yxat ostida | taomlar ro'yxatini ochadi; tanlangani o'sha kungi vazifaga yoziladi va dasturda «Menyu» bo'lib ko'rinadi |
| **Albatta! ✅** | eslatma ostida | vazifani bajarildi deb belgilaydi |

Tugmani **faqat o'sha vazifaning egasi** bosa oladi — boshqasi bossa
«bu falonchining vazifasi» degan javob chiqadi. (Odamning Telegram
nomi kiritilmagan bo'lsa tekshirib bo'lmaydi va tugma hammaga
ochiq — shuning uchun «Telegram:» qatorini to'ldirib qo'ying.)

Yangi xabar yuborilmaydi: bosilgandan keyin **o'sha xabar
tahrirlanadi**, aks holda guruh takrorlardan to'lib ketardi.

Menyu ro'yxati kodda emas — **Vazifalar → Menyu** kartasida
tahrirlanadi. Bo'sh bo'lsa tugma umuman chiqmaydi.

### Kompyuter yoniq bo'lishi kerak

Dasturda server yo'q, demak xabarni kimdir yuborishi kerak.
`xabarchi_reja.bat` Windows rejasini o'rnatadi va u **har daqiqada**
`src\xabarchi.py` ni chaqiradi — dastur oynasi ochiq bo'lmasa ham
ishlaydi. Har daqiqada, chunki skript ayni paytda guruhdagi tugma
bosilishini ham qabul qiladi: javob 5 daqiqa kutsa odam tugmani
buzuq deb o'ylaydi. Kompyuter o'chiq bo'lsa xabar ketmaydi; yoqilganda o'sha
kunning o'tkazib yuborilganlari yuboriladi (eski kunlarniki emas).

O'chirish: `xabarchi_reja.bat /o`

### Nima qayta yuborilmaydi

Har xabar `yuborilgan` jadvalida kalit bilan belgilanadi
(`kunlik:2026-09-04`, `vazifa:12`, `rasxod:34`). Shuning uchun
xabarchi kuniga o'nlab marta ishga tushsa ham guruhga bir marta
tushadi. Tugma bosilishi ham shunday: `getUpdates` o'qigan joyi
`sozlama.tg_offset` da turadi, aks holda bitta «Albatta!» har
daqiqada qayta bajarilardi.

**Eski rasxodlar hech qachon e'lon qilinmaydi**: Telegram birinchi
marta yoqilgan payt `tg_rasxod_dan` ga yozib qo'yiladi va faqat
shundan keyin yozilganlari yuboriladi. Aks holda yoqilgan zahoti
butun tarix guruhga to'kilardi.

---

## Zaxira

Dastur **har ochilganda** avtomatik zaxira oladi
(`%LOCALAPPDATA%\FarvonUy\zaxira\`), oxirgi 20 tasi saqlanadi.
Qo'lda olish: Sozlamalar → «Hozir zaxira olish».

---

## Bekor qilish

**Tezkor tugma yo'q** — `Ctrl+Z` ham, `Ctrl+1…8` ham, `F5` ham ishlamaydi.
Sabab oddiy: «bosib yubordim, nima o'chdi?» degan holat pul hisobida
qimmatga tushadi.

Buning o'rniga bekor qilish har doim **yozuvning o'z ustida**:

1. Rasxod qatoriga bosing (yoki «Tafsilot va bekor qilish»);
2. summasi, kim to'lagani va kim qancha ko'tarishi ko'rinib turadi;
3. «Rasxodni bekor qilish» — tasdiqlagach balansdan chiqadi.

Vazifalarda ham xuddi shunday: blokka bosilsa tafsilot ochiladi, bekor
qilish o'sha yerda.

O'chirilgan yozuv **yo'qolmaydi** — `ochirilgan=1` bo'ladi va
`ozgarishlar` jurnalida qolaveradi.
