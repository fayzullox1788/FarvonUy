-- ═══════════════════════════════════════════════════════════════════════
--  Farvon Uy  —  SQLite schema  v1
--
--  Uchta qat'iy prinsip:
--    1. Hech narsa o'chirilmaydi — `ochirilgan=1` qo'yiladi.
--    2. Har o'zgarish `ozgarishlar` jadvaliga yoziladi (Ctrl+Z uchun).
--    3. Pul HAR DOIM butun son (so'm). REAL/FLOAT ishlatilmaydi.
-- ═══════════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  kalit  TEXT PRIMARY KEY,
  qiymat TEXT NOT NULL
);

-- ─────────────────────────────────────────────────── odamlar / kategoriya

CREATE TABLE IF NOT EXISTS odam (
  id       INTEGER PRIMARY KEY,
  nom      TEXT    NOT NULL UNIQUE,
  rang     TEXT    NOT NULL DEFAULT '#6b7fd7',
  tartib   INTEGER NOT NULL DEFAULT 0,
  faol     INTEGER NOT NULL DEFAULT 1,
  -- Telegram foydalanuvchi nomi (@ siz). Vazifa eslatmasida shu odam
  -- guruhda teg qilinadi.
  telegram TEXT,
  -- Bot bilan SHAXSIY suhbatning `chat_id` si. Bot o'zi boshlab
  -- yoza olmaydi: odam avval botga /start bosishi kerak, o'shanda
  -- bu maydon to'ladi (`xabar._chatni_eslab_qol()`). Bo'sh bo'lsa
  -- shaxsiy vazifa YUBORILMAYDI va guruhga ham tushmaydi — aks
  -- holda «shaxsiy» degan va'da buzilardi.
  tg_chat  INTEGER
);

-- Telegram xabarlari YUBORILGANI belgilanadigan jurnal.
--
-- `ozgarishlar` ga tushmaydi (`davr` kabi istisno): bu foydalanuvchi
-- ma'lumoti emas, texnik iz. Undo qilinsa xabar qayta yuborilib,
-- guruhga takror tushardi.
-- `xabar_id` — Telegram bergan message_id. Tugma bosilganda o'sha
-- xabarni TAHRIRLASH uchun kerak (yangi xabar yuborilsa guruh
-- takrorlardan to'lib ketardi).
CREATE TABLE IF NOT EXISTS yuborilgan (
  kalit    TEXT PRIMARY KEY,
  vaqt     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  xabar_id INTEGER
);

CREATE TABLE IF NOT EXISTS turi (
  id     INTEGER PRIMARY KEY,
  nom    TEXT    NOT NULL UNIQUE,
  belgi  TEXT    NOT NULL DEFAULT '',
  tartib INTEGER NOT NULL DEFAULT 0,
  faol   INTEGER NOT NULL DEFAULT 1
);

-- ────────────────────────────────────────────────────────────────── kirim

CREATE TABLE IF NOT EXISTS kirim (
  id         INTEGER PRIMARY KEY,
  sana       TEXT    NOT NULL,
  odam_id    INTEGER NOT NULL REFERENCES odam(id),
  summa      INTEGER NOT NULL CHECK (summa > 0),
  sabab      TEXT,
  ochirilgan INTEGER NOT NULL DEFAULT 0,
  yaratilgan TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_kirim_sana ON kirim(sana);

-- ───────────────────────────────────────────────────────────────── rasxod
-- umumiymi=1 -> `ulush` jadvalida bo'linadi.  umumiymi=0 -> faqat to'lovchiniki.

CREATE TABLE IF NOT EXISTS rasxod (
  id          INTEGER PRIMARY KEY,
  sana        TEXT    NOT NULL,
  nom         TEXT    NOT NULL DEFAULT '',
  turi_id     INTEGER REFERENCES turi(id),
  summa       INTEGER NOT NULL CHECK (summa > 0),
  kim_toladi  INTEGER NOT NULL REFERENCES odam(id),
  umumiymi    INTEGER NOT NULL DEFAULT 1,
  bolish_usul TEXT    NOT NULL DEFAULT 'teng',
  -- Kimningdir O'RNIGA qilingan xarid. To'lovchi pulni chiqaradi, lekin
  -- rasxod boshqa odamniki bo'lib qoladi va u qarzdor bo'ladi.
  -- Bu KIRIM emas: pul o'sha odamning qo'liga tegmagan.
  kim_uchun   INTEGER REFERENCES odam(id),
  item_id     INTEGER,
  reja_id     INTEGER,
  takror_id   INTEGER,
  izoh        TEXT,
  ochirilgan  INTEGER NOT NULL DEFAULT 0,
  yaratilgan  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_rasxod_sana ON rasxod(sana);
CREATE INDEX IF NOT EXISTS ix_rasxod_odam ON rasxod(kim_toladi);

-- Kim shu rasxoddan qancha qarzdor. To'lovchining o'z ulushi ham shu yerda,
-- lekin uni "to'lash" kerak emas — pulni o'zi chiqargan.
CREATE TABLE IF NOT EXISTS ulush (
  id            INTEGER PRIMARY KEY,
  rasxod_id     INTEGER NOT NULL REFERENCES rasxod(id) ON DELETE CASCADE,
  odam_id       INTEGER NOT NULL REFERENCES odam(id),
  summa         INTEGER NOT NULL,
  yaxlitlash    INTEGER NOT NULL DEFAULT 0,
  -- Har ulush ALOHIDA yopiladi. Excel'dagi "Ha" belgisining o'rni shu:
  -- hammasini bir yo'la emas, qator-qator to'lash mumkin.
  tolandi       INTEGER NOT NULL DEFAULT 0,
  tolangan_sana TEXT,
  UNIQUE(rasxod_id, odam_id)
);
CREATE INDEX IF NOT EXISTS ix_ulush_odam ON ulush(odam_id);

-- ─────────────────────────────────────────────────────────────────── qarz

CREATE TABLE IF NOT EXISTS qarz (
  id         INTEGER PRIMARY KEY,
  sana       TEXT    NOT NULL,
  kim_berdi  INTEGER NOT NULL REFERENCES odam(id),
  kimga      INTEGER NOT NULL REFERENCES odam(id),
  summa      INTEGER NOT NULL CHECK (summa > 0),
  sabab      TEXT,
  ochirilgan INTEGER NOT NULL DEFAULT 0,
  yaratilgan TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK (kim_berdi <> kimga)
);

-- ──────────────────────────────────────────────────────────── hisob-kitob
-- Qarzni yopish uchun to'lov. Excel'dagi "Ha" belgisi o'rniga — bu yerda
-- pulning haqiqiy harakati sana bilan yoziladi.

CREATE TABLE IF NOT EXISTS hisob_kitob (
  id         INTEGER PRIMARY KEY,
  sana       TEXT    NOT NULL,
  kim_toladi INTEGER NOT NULL REFERENCES odam(id),
  kimga      INTEGER NOT NULL REFERENCES odam(id),
  summa      INTEGER NOT NULL CHECK (summa > 0),
  izoh       TEXT,
  -- Agar bu to'lov aniq bitta blokni (ulushni) yopgan bo'lsa — shu yerda
  -- bog'lanadi. Blok qayta ochilganda aynan shu to'lov bekor qilinadi.
  ulush_id   INTEGER REFERENCES ulush(id),
  ochirilgan INTEGER NOT NULL DEFAULT 0,
  yaratilgan TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK (kim_toladi <> kimga)
);

-- ───────────────────────────────────────────────────────── yo'qlik kunlari

CREATE TABLE IF NOT EXISTS yoq_kun (
  id         INTEGER PRIMARY KEY,
  odam_id    INTEGER NOT NULL REFERENCES odam(id),
  boshi      TEXT    NOT NULL,
  oxiri      TEXT    NOT NULL,
  sabab      TEXT,
  ochirilgan INTEGER NOT NULL DEFAULT 0,
  CHECK (oxiri >= boshi)
);

-- ──────────────────────────────────────────────────────────── davr yopish

CREATE TABLE IF NOT EXISTS davr (
  oy            TEXT PRIMARY KEY,
  holat         TEXT NOT NULL DEFAULT 'ochiq',
  yopilgan_vaqt TEXT,
  izoh          TEXT
);

-- ───────────────────────────────────────────────────────────────── cheklar

CREATE TABLE IF NOT EXISTS chek (
  id        INTEGER PRIMARY KEY,
  rasxod_id INTEGER NOT NULL REFERENCES rasxod(id) ON DELETE CASCADE,
  fayl      TEXT    NOT NULL,
  qoshilgan TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_chek_rasxod ON chek(rasxod_id);

-- ────────────────────────────────────────────────────────── takroriy rasxod

CREATE TABLE IF NOT EXISTS takror (
  id           INTEGER PRIMARY KEY,
  nom          TEXT    NOT NULL,
  turi_id      INTEGER REFERENCES turi(id),
  summa        INTEGER NOT NULL CHECK (summa > 0),
  kim_toladi   INTEGER NOT NULL REFERENCES odam(id),
  umumiymi     INTEGER NOT NULL DEFAULT 1,
  davriylik    TEXT    NOT NULL DEFAULT 'oylik',
  kun          INTEGER NOT NULL DEFAULT 1,
  keyingi_sana TEXT    NOT NULL,
  faol         INTEGER NOT NULL DEFAULT 1,
  ochirilgan   INTEGER NOT NULL DEFAULT 0
);

-- ────────────────────────────────────────────────── katalog + haftalik reja

CREATE TABLE IF NOT EXISTS item (
  id       INTEGER PRIMARY KEY,
  nom      TEXT    NOT NULL,
  turi_id  INTEGER REFERENCES turi(id),
  birlik   TEXT,
  narx     INTEGER NOT NULL DEFAULT 0,
  cikl_kun INTEGER,
  faol     INTEGER NOT NULL DEFAULT 1,
  izoh     TEXT
);

CREATE TABLE IF NOT EXISTS reja (
  id         INTEGER PRIMARY KEY,
  tur        TEXT    NOT NULL DEFAULT 'haftalik',
  boshi      TEXT    NOT NULL,
  oxiri      TEXT    NOT NULL,
  budjet     INTEGER,
  holat      TEXT    NOT NULL DEFAULT 'ochiq',
  izoh       TEXT,
  yaratilgan TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(tur, boshi)
);

CREATE TABLE IF NOT EXISTS reja_qator (
  id         INTEGER PRIMARY KEY,
  reja_id    INTEGER NOT NULL REFERENCES reja(id) ON DELETE CASCADE,
  item_id    INTEGER,
  nom        TEXT    NOT NULL,
  turi_id    INTEGER REFERENCES turi(id),
  summa      INTEGER NOT NULL,
  miqdor     REAL    NOT NULL DEFAULT 1,
  bor        INTEGER NOT NULL DEFAULT 0,
  ochirilgan INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_reja_qator ON reja_qator(reja_id);

CREATE TABLE IF NOT EXISTS budjet (
  id      INTEGER PRIMARY KEY,
  turi_id INTEGER NOT NULL REFERENCES turi(id),
  oy      TEXT    NOT NULL,
  summa   INTEGER NOT NULL,
  UNIQUE(turi_id, oy)
);

-- ──────────────────────────────────────────────────────── undo / audit log

CREATE TABLE IF NOT EXISTS ozgarishlar (
  id          INTEGER PRIMARY KEY,
  vaqt        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  guruh_id    TEXT    NOT NULL,
  tavsif      TEXT    NOT NULL DEFAULT '',
  jadval      TEXT    NOT NULL,
  qator_id    INTEGER NOT NULL,
  amal        TEXT    NOT NULL,
  oldin       TEXT,
  keyin       TEXT,
  qaytarilgan INTEGER NOT NULL DEFAULT 0,
  -- Undo'dan keyin yangi yozuv kiritilsa, qaytarilgan guruhlar shu yerda
  -- "bekor" bo'ladi: tarix shoxlanmasligi uchun ular endi redo ro'yxatiga
  -- tushmaydi. O'chirilmaydi — 3-qoida.
  bekor       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ozg_guruh ON ozgarishlar(guruh_id);
CREATE INDEX IF NOT EXISTS ix_ozg_vaqt  ON ozgarishlar(vaqt);

CREATE TABLE IF NOT EXISTS sozlama (
  kalit  TEXT PRIMARY KEY,
  qiymat TEXT NOT NULL
);

-- ────────────────────────────────────────────────────────────── vazifa
--
-- Uy ishlari. Pulga TEGMAYDI — shuning uchun `ledger.audit()` bu
-- jadvalni umuman ko'rmaydi va kitob tengligiga ta'sir qilmaydi.
--
-- `vaqt` NULL bo'lishi mumkin: "bugun, lekin aniq soati yo'q".
-- Kalendarda bunday vazifa kunning tepasida alohida ko'rinadi.
-- `davomiylik` — daqiqada, kalendardagi blok balandligi shundan.
CREATE TABLE IF NOT EXISTS vazifa (
  id          INTEGER PRIMARY KEY,
  nom         TEXT    NOT NULL,
  odam_id     INTEGER NOT NULL REFERENCES odam(id),
  sana        TEXT    NOT NULL,
  vaqt        TEXT,
  davomiylik  INTEGER NOT NULL DEFAULT 60,
  holat       TEXT    NOT NULL DEFAULT 'ochiq',
  bajarilgan  TEXT,
  izoh        TEXT,
  -- «Hali yo'q, keyinroq» bosilganda: eslatma shu vaqtdan OLDIN
  -- qayta yuborilmaydi. SQLite formatida ("YYYY-MM-DD HH:MM:SS"),
  -- `isoformat()` EMAS — `tg_rasxod_dan` bilan bir xil sabab: matn
  -- solishtiruvida ' ' < 'T', ya'ni ikki format aralashsa
  -- taqqoslash jimgina noto'g'ri ishlaydi.
  kechiktirildi TEXT,
  -- Qatorni kim yozgani. Qo'lda yozilgan vazifada NULL; dars jadvalidan
  -- kelgani `dars:<sana>:<para>` («dars:2026-09-07:5»). Sinxron FAQAT
  -- shu belgili qatorlarga tegadi — aks holda qo'lda yozilgan vazifa
  -- keyingi yangilanishda jimgina o'chib ketardi.
  manba       TEXT,
  ochirilgan  INTEGER NOT NULL DEFAULT 0,
  yaratilgan  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_vazifa_sana ON vazifa(sana);
CREATE INDEX IF NOT EXISTS ix_vazifa_odam ON vazifa(odam_id, sana);

-- Vazifa turlari — «Vazifalar» varag'idagi ro'yxat. Bular kalendarga
-- tushmaydi: ular shunchaki tayyor ish nomlari, odamga biriktirilganda
-- `vazifa` jadvaliga yangi qator bo'ladi.
-- `navbat=1` — bu ish odamlar bo'ylab NAVBAT bilan yuradi (ovqat
-- qilish). Bir odamga biriktirilsa, keyingi kunlar qolganlarga
-- `odam.tartib` bo'yicha o'zi taqsimlanadi.
--
-- `ergash_turi_id` — o'sha kuni AVVALGI navbatchiga tushadigan ish
-- (ovqatdan keyingi idish). Nomga qarab emas, shu ustunga qarab
-- ishlaydi: foydalanuvchi ish nomini o'zgartirsa ham buzilmaydi.
--
-- `haftalik=1` — «general uborka» ishi: haftada bir marta, belgilangan
-- kuni bajariladi va HAR HAFTA keyingi odamga o'tadi. Bu `navbat` dan
-- boshqa narsa: `navbat` har KUNI aylanadi va bitta ishni uzatadi,
-- `haftalik` esa bir necha katta ishni bir kunda odamlar orasida
-- taqsimlaydi va har hafta ularni siljitadi.
--
-- Uborka kuni bu yerda emas, `sozlama.uborka_kuni` da: u butun
-- guruhga bitta va har turga takrorlab yozish uni bo'linib ketishga
-- ochiq qoldirardi.
--
-- `shaxsiy=1` — bu ish GURUHGA e'lon qilinmaydi: bot uni faqat
-- egasiga shaxsiy yozadi. Kitob o'qish yoki dori ichish hammaga
-- ko'rinib turishi shart emas, lekin eslatma baribir kerak.
-- Bot shaxsiy yoza olishi uchun odam avval botga /start bosishi
-- kerak — o'shanda `odam.tg_chat` to'ladi.
CREATE TABLE IF NOT EXISTS vazifa_turi (
  id             INTEGER PRIMARY KEY,
  nom            TEXT    NOT NULL UNIQUE,
  davomiylik     INTEGER NOT NULL DEFAULT 60,
  tartib         INTEGER NOT NULL DEFAULT 0,
  navbat         INTEGER NOT NULL DEFAULT 0,
  haftalik       INTEGER NOT NULL DEFAULT 0,
  shaxsiy        INTEGER NOT NULL DEFAULT 0,
  ergash_turi_id INTEGER REFERENCES vazifa_turi(id),
  ochirilgan     INTEGER NOT NULL DEFAULT 0
);

-- Menyu — guruhdagi oshpaz tanlaydigan taomlar.
--
-- Kodda emas, JADVALDA: yangi taom qo'shish uchun dastur qayta
-- qurilmasin (`turi` va `vazifa_turi` bilan bir xil g'oya). Tanlangan
-- taom `vazifa.menyu` ga yoziladi — ya'ni nomga emas, o'sha kungi
-- vazifaga bog'lanadi, keyin ro'yxatdan o'chirilsa ham tarix qoladi.
CREATE TABLE IF NOT EXISTS menyu (
  id         INTEGER PRIMARY KEY,
  nom        TEXT    NOT NULL UNIQUE,
  tartib     INTEGER NOT NULL DEFAULT 0,
  ochirilgan INTEGER NOT NULL DEFAULT 0
);

-- Ish qadamlari — bitta ish turining ichidagi mayda ishlar ro'yxati
-- («Sanuzelni tozalash» → unitaz, vanna, rakovina, pol).
--
-- Nega alohida jadval, `vazifa_turi` ga vergul bilan yozilgan matn
-- emas: qadam qo'shish/olib tashlash ish turining O'ZIGA tegmasligi
-- kerak, va guruhga ketadigan xabar shu ro'yxatni qatorma-qator
-- chiqaradi. Matn bo'lganda har safar uni bo'lib o'tirish kerak
-- bo'lardi va bitta vergul butun ro'yxatni buzardi.
--
-- Qadam VAZIFAGA emas, TURGA bog'lanadi: ro'yxat har hafta bir xil,
-- uni har biriktirishda nusxalash mantiqsiz bo'lardi.
CREATE TABLE IF NOT EXISTS ish_qadam (
  id         INTEGER PRIMARY KEY,
  turi_id    INTEGER NOT NULL REFERENCES vazifa_turi(id),
  nom        TEXT    NOT NULL,
  tartib     INTEGER NOT NULL DEFAULT 0,
  ochirilgan INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ish_qadam_turi ON ish_qadam(turi_id);

-- ──────────────────────────────────────────────────────────── streak
--
-- «Har kuni kitob o'qish» kabi ODAT: bitta odam + bitta ish turi +
-- nishon (7, 14, 21 yoki 28 kun).
--
-- Nega hisoblangan qiymat saqlanmaydi: ketma-ket kunlar soni har
-- safar `vazifa` jadvalidan qayta hisoblanadi (`vz.streak_kunlari`).
-- Saqlangan hisoblagich undo bilan ajralib qolardi — vazifa
-- qaytarilsa hisoblagich o'sha joyda turib olardi va streak yolg'on
-- gapirardi. Kitob tengligi bilan bir xil qoida: haqiqat bitta
-- joyda, qolgani undan chiqadi.
CREATE TABLE IF NOT EXISTS streak (
  id         INTEGER PRIMARY KEY,
  odam_id    INTEGER NOT NULL REFERENCES odam(id),
  turi_id    INTEGER NOT NULL REFERENCES vazifa_turi(id),
  nishon     INTEGER NOT NULL DEFAULT 7,
  boshlandi  TEXT    NOT NULL,
  ochirilgan INTEGER NOT NULL DEFAULT 0,
  UNIQUE(odam_id, turi_id)
);
CREATE INDEX IF NOT EXISTS ix_streak_odam ON streak(odam_id);

-- Qo'lga kiritilgan yutuqlar. Bir marta berilib, joyida qoladi:
-- streak keyin uzilsa ham «men buni qilgandim» degan yozuv o'chmaydi.
CREATE TABLE IF NOT EXISTS yutuq (
  id         INTEGER PRIMARY KEY,
  odam_id    INTEGER NOT NULL REFERENCES odam(id),
  nom        TEXT    NOT NULL,
  izoh       TEXT,
  sana       TEXT    NOT NULL,
  streak_id  INTEGER REFERENCES streak(id),
  nishon     INTEGER NOT NULL DEFAULT 0,
  ochirilgan INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_yutuq_odam ON yutuq(odam_id);

-- ═══════════════════════════════════════════════════════════════ viewlar

-- Har odamning uchta soni. Bu — dasturning yuragi.
--
--   naqd   (Real balans)     = qo'lidagi haqiqiy pul
--   sof    (Sof pozitsiya)   = + menga qarzdor,  - men qarzdorman
--   adolat (Adolatli balans) = naqd + sof
--
-- Matematik kafolat:  SUM(sof) = 0   va   SUM(naqd) = SUM(kirim) - SUM(rasxod)
DROP VIEW IF EXISTS v_balans;
CREATE VIEW v_balans AS
WITH
k  AS (SELECT odam_id    id, SUM(summa) s FROM kirim  WHERE ochirilgan=0 GROUP BY odam_id),
sh AS (SELECT kim_toladi id, SUM(summa) s FROM rasxod WHERE ochirilgan=0 AND umumiymi=0 GROUP BY kim_toladi),
ut AS (SELECT kim_toladi id, SUM(summa) s FROM rasxod WHERE ochirilgan=0 AND umumiymi=1 GROUP BY kim_toladi),
-- Haqiqiy UMUMIY rasxoddagi ulushi (hammaga bo'lingan)
uu AS (SELECT u.odam_id  id, SUM(u.summa) s FROM ulush u
       JOIN rasxod r ON r.id=u.rasxod_id
       WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NULL
       GROUP BY u.odam_id),
-- Boshqa odam UNING UCHUN olib bergan narsalari. Bu kirim emas —
-- pul uning qo'liga tegmagan, shuning uchun `naqd` ga ta'sir qilmaydi,
-- faqat qarz bo'lib yoziladi.
ub AS (SELECT u.odam_id  id, SUM(u.summa) s FROM ulush u
       JOIN rasxod r ON r.id=u.rasxod_id
       WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NOT NULL
       GROUP BY u.odam_id),
qb AS (SELECT kim_berdi  id, SUM(summa) s FROM qarz        WHERE ochirilgan=0 GROUP BY kim_berdi),
qo AS (SELECT kimga      id, SUM(summa) s FROM qarz        WHERE ochirilgan=0 GROUP BY kimga),
ht AS (SELECT kim_toladi id, SUM(summa) s FROM hisob_kitob WHERE ochirilgan=0 GROUP BY kim_toladi),
ho AS (SELECT kimga      id, SUM(summa) s FROM hisob_kitob WHERE ochirilgan=0 GROUP BY kimga)
-- DIQQAT: bu view faol bo'lmagan odamni ham qaytaradi. Agar `faol=1` filtri
-- shu yerda bo'lsa, odam nofaol qilinganda uning qarzi hisobdan tushib
-- qoladi va SUM(sof) noldan chiqib ketadi — ya'ni audit yolg'on gapiradi.
-- Filtr `ledger.balanslar()` da, audit esa HAMMA odamni ko'radi.
SELECT
  o.id, o.nom, o.rang, o.tartib, o.faol,
  COALESCE(k.s,0)  AS kirim,
  COALESCE(sh.s,0) AS shaxsiy,
  COALESCE(ut.s,0) AS umumiy_tolagan,
  COALESCE(uu.s,0) AS umumiy_ulush,
  COALESCE(ub.s,0) AS uchun_ulush,
  COALESCE(qb.s,0) AS qarz_bergan,
  COALESCE(qo.s,0) AS qarz_olgan,
  COALESCE(ht.s,0) AS hk_tolagan,
  COALESCE(ho.s,0) AS hk_olgan,
  COALESCE(k.s,0) - COALESCE(sh.s,0) - COALESCE(ut.s,0)
    - COALESCE(qb.s,0) + COALESCE(qo.s,0)
    - COALESCE(ht.s,0) + COALESCE(ho.s,0)               AS naqd,
  (COALESCE(ut.s,0) - COALESCE(uu.s,0) - COALESCE(ub.s,0))
    + COALESCE(qb.s,0) - COALESCE(qo.s,0)
    + COALESCE(ht.s,0) - COALESCE(ho.s,0)               AS sof,
  COALESCE(k.s,0) - COALESCE(sh.s,0)
    - COALESCE(uu.s,0) - COALESCE(ub.s,0)               AS adolat
FROM odam o
LEFT JOIN k  ON k.id=o.id   LEFT JOIN sh ON sh.id=o.id
LEFT JOIN ut ON ut.id=o.id  LEFT JOIN uu ON uu.id=o.id
LEFT JOIN ub ON ub.id=o.id
LEFT JOIN qb ON qb.id=o.id  LEFT JOIN qo ON qo.id=o.id
LEFT JOIN ht ON ht.id=o.id  LEFT JOIN ho ON ho.id=o.id;

-- Juftlik bo'yicha xom qarz (netlanmagan)
DROP VIEW IF EXISTS v_juft_qarz;
CREATE VIEW v_juft_qarz AS
  SELECT u.odam_id AS qarzdor, r.kim_toladi AS kreditor, SUM(u.summa) AS summa
  FROM ulush u JOIN rasxod r ON r.id=u.rasxod_id
  WHERE r.ochirilgan=0 AND r.umumiymi=1 AND u.odam_id <> r.kim_toladi
  GROUP BY u.odam_id, r.kim_toladi
UNION ALL
  SELECT kimga, kim_berdi, SUM(summa) FROM qarz
  WHERE ochirilgan=0 GROUP BY kimga, kim_berdi
UNION ALL
  -- To'lov qarzni KAMAYTIRADI: to'lovchi qarzdor, oluvchi kreditor, minus bilan.
  SELECT kim_toladi, kimga, -SUM(summa) FROM hisob_kitob
  WHERE ochirilgan=0 GROUP BY kim_toladi, kimga;

-- To'lanmagan bloklar: har bir ulush alohida qator.
-- To'lovchining o'z ulushi bu yerga TUSHMAYDI — u pulni o'zi chiqargan.
DROP VIEW IF EXISTS v_ochiq_ulush;
CREATE VIEW v_ochiq_ulush AS
SELECT u.id            AS ulush_id,
       r.id            AS rasxod_id,
       r.sana,
       r.nom,
       r.summa         AS rasxod_summa,
       r.kim_uchun,
       u.summa,
       u.tolandi,
       u.tolangan_sana,
       u.odam_id       AS qarzdor_id,
       q.nom           AS qarzdor,
       r.kim_toladi    AS kreditor_id,
       k.nom           AS kreditor,
       t.nom           AS turi_nom,
       t.belgi         AS turi_belgi
FROM ulush u
JOIN rasxod r ON r.id = u.rasxod_id
JOIN odam   q ON q.id = u.odam_id
JOIN odam   k ON k.id = r.kim_toladi
LEFT JOIN turi t ON t.id = r.turi_id
WHERE r.ochirilgan = 0 AND r.umumiymi = 1 AND u.odam_id <> r.kim_toladi;

-- Yaxlitlash adolati: kimga qancha ortiqcha so'm tushgan
DROP VIEW IF EXISTS v_yaxlitlash;
CREATE VIEW v_yaxlitlash AS
SELECT o.id, o.nom, COALESCE(SUM(u.yaxlitlash),0) AS ortiqcha
FROM odam o
LEFT JOIN ulush  u ON u.odam_id=o.id
LEFT JOIN rasxod r ON r.id=u.rasxod_id AND r.ochirilgan=0
WHERE o.faol=1 GROUP BY o.id;

-- Kunlik yig'indi (shaxsiy varaqdagi "Qoldiq" ustuni uchun)
DROP VIEW IF EXISTS v_kunlik;
CREATE VIEW v_kunlik AS
SELECT r.sana, r.kim_toladi AS odam_id,
       SUM(CASE WHEN r.umumiymi=0 THEN r.summa ELSE 0 END) AS shaxsiy,
       SUM(CASE WHEN r.umumiymi=1 THEN r.summa ELSE 0 END) AS umumiy_tolagan
FROM rasxod r WHERE r.ochirilgan=0
GROUP BY r.sana, r.kim_toladi;
