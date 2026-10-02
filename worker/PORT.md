# Python → JS port qoidalari (worker/)

Bot Cloudflare Worker + D1 da ishlaydi. Python kod (`../src/`) — HAQIQAT MANBAI;
JS uning aniq egizagi. Desktop ilova o'zgarmagan Python kod bilan ishlashda davom
etadi va D1 bilan `ozgarishlar` jurnali orqali sinxronlanadi.

## Nomlar
- Bir Python modul = bir JS fayl: `core/vazifa.py` → `src/vazifa.js`, `core/xabar.py` → `src/xabar.js`.
- Funksiya va konstanta nomlari Python'dagidek **snake_case**, `_xususiy` prefiksi ham saqlanadi
  (testlar uchun export qilinadi). Har funksiyaga `// vazifa.py:668` kabi manba izohi.
- DB yozadigan / o'qiydigan funksiyalar `async`.

## Asos (tayyor, o'zgartirmang — kerak bo'lsa koordinatorga ayting)
- `src/db.js`: `db.q(sql,...a)`, `db.q1`, `db.skalyar(sql,[args],birlamchi)`, `db.sozlama(k,b)`,
  `db.sozlama_qoy(k,v)`, `db.exec(sql,...a)` (audit qilinmaydigan xom yozuv: `yuborilgan`, `davr`),
  `db.apply(jadval, amal, data, qator_id, tavsif)`, `db.amal(tavsif)` → `Amal`.
  - Python `with db.amal("x"):` → `const a = db.amal("x"); await a.apply(...); …; await a.commit();`
  - **Navbatli yozuv**: `a.apply()` commit'gacha bazada ko'rinmaydi. Ichma-ich chaqiruv
    (Python'da ichki `amal` tashqisiga qo'shiladi) → JS'da funksiyaga ixtiyoriy `a` (Amal)
    parametri bering: `async function bajar(db, vid, {a = null} = {})` — berilmasa o'zi ochib
    commit qiladi. O'z yozuvini o'qish kerak bo'lsa — qiymatni JS'da hisoblang (mas.
    `yutuqlarni_tekshir` bajarilgan vazifani hisobga olishi kerak) yoki commit qilib davom eting.
  - INSERT id'si `a.apply()` dan darhol qaytadi (toq id, oldindan hisoblanadi).
  - Python `except DavrYopilgan` → JS `DavrYopilgan` (db.js'dan).
- `src/vaqt.js`: Toshkent vaqti. `hozir()` (Date, UTC maydonlari = Toshkent devor soati),
  `bugun()`, `hozirStr()` ("YYYY-MM-DD HH:MM:SS"), `sanaStr`, `vaqtStr`, `sanaDan`, `vaqtDan`,
  `kunQosh`, `daqiqaQosh`, `weekday` (Du=0), `toordinal`, `kunFarqi`, `daqiqa("HH:MM")`,
  `daqiqaDan(d)`, `sanaNuqta`. **`new Date()`/`Date.now()` ni to'g'ridan-to'g'ri ishlatmang** —
  testlar `soatniQoy()` bilan soatni muzlatadi. Python `date.today()` → `bugun()`,
  `datetime.now()` → `hozir()`.
- `src/money.js`: `fmt`, `fmt_som`, `bol`, `bol_teng`, `bol_tortli`, `bol_aniq`, `USUL_*`.
  Ulush obyekti `{odam_id, summa, yaxlitlash}`.
- `src/tg.js`: `sorov(token, metod, maydonlar)` (yagona tarmoq nuqtasi = Python `_sorov`),
  `xabarYubor` (= `_xabar_yubor`), `tahrirlaJim`, `rasmYubor(token, chat, baytlar, fayl, izoh)`,
  `faylYukla(token, file_id)`, `klaviaturaJson(rows)` (= `_klaviatura_json`), `e()` (= `html.escape(quote=False)`),
  `transportQoy(fn)` testlar uchun.

## Python xatti-harakatini aniq takrorlang
- `{odam_id: x}` lug'atlari → **`Map`** (JS obyekti butun son kalitlarni saralaydi, Python
  qo'shilish tartibini saqlaydi). JSON'ga yozishda `Object.fromEntries(map)` (kalitlar matn bo'ladi —
  Python ham `json.dumps` da shunday qiladi).
- `str.casefold()` → `.toLowerCase()` + `ß→ss` yetarli; `isalnum` → `/[\p{L}\p{N}]/u`.
- `f"{x:,}"` → `money.fmt`; `f"{x:g}"` → `Number(x).toString()` (1.0 → "1", 0.5 → "0.5").
- `json.dumps(..., ensure_ascii=False)` matnga kirsa (sozlama holati) — tarkib muhim, bo'shliq
  emas; parity testi JSON'ni parse qilib solishtiradi.
- SQL o'zgarmaydi (D1 = SQLite). `datetime('now','localtime')` ishlatmang — vaqtni JS'dan
  (`hozirStr()`) parametr qilib bering.
- `sqlite3.Row` → oddiy obyekt (`r.nom`); `bool(row)` → `row != null`.

## Testlar (`node --test`) — har port qilingan funksiya PARITY bilan
- `test/fixture.js`: `yangiBaza(pyKod)` → Python `db.Db()` bilan haqiqiy sxemali baza yaratadi
  (ixtiyoriy Python ekish kodi bilan), JS uni `D1Shim` orqali ochadi → `{db, d1, papka}`.
  `py(papka, kod)` → shu bazada Python ishga tushirib stdout qaytaradi.
- Parity naqshi: bir xil bazada Python funksiya natijasini `print(json.dumps(...))` qiling,
  JS natijasi bilan `assert.deepEqual`. Telegram chaqiruvlari uchun: Python'da `xb._sorov` ni
  yozib oluvchi bilan almashtiring, JS'da `transportQoy` — ikki ro'yxat (metod, maydonlar) teng
  bo'lsin (`reply_markup` ni parse qilib solishtiring). Soat: Python'da modul ichidagi
  `date`/`datetime` ni muzlatilgan sinf bilan almashtiring, JS'da `soatniQoy`.
- Testlar Python 3.14 (`py -3.14`) ni chaqiradi; har test o'z vaqtinchalik bazasida.
- Bitta test fayli — bitta modul guruhi (`test/vazifa.test.js`, `test/xabar.test.js`, …).
- Ishga tushirish: `cd worker && npm test` (yoki `node --test test/xabar.test.js`).
