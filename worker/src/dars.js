// EduPage dars jadvali → bitta odamning shaxsiy kalendari.
// Python `src/core/dars.py` ning aniq egizagi (sababi va qoidalari o'sha
// faylda va CLAUDE.md «Dars jadvali» bo'limida).
//
// Farqlar faqat platformada:
//   · sana — "YYYY-MM-DD" matn (Python `date`);
//   · tarmoq — fetch (Python urllib), testlar `sorovQoy()` bilan almashtiradi;
//   · yozuv — `db.amal()` navbati: `_turni_taminla` bir amal ichida bir nechta
//     yangi tur qo'shsa, `tartib` ni JS o'zi sanaydi (navbatdagi yozuv
//     commit'gacha bazada ko'rinmaydi).

import * as vaqt from "./vaqt.js";

export const HOST = "ttpu.edupage.org";
export const GSH = "00000000";
export const KUTISH = 20; // soniya

export const K_YOQ = "dars_yoq";
export const K_HOST = "dars_host";
export const K_SINF = "dars_sinf";
export const K_ODAM = "dars_odam";
export const K_TT = "dars_tt";
export const K_TEKSHIRILDI = "dars_tekshirildi";

export const ORALIQ_DAQIQA = 60;     // dars.py:41
export const OGOH_DAQIQA = 5 * 60;   // dars.py:49
export const KECHIKISH_DAQIQA = 10;  // dars.py:50

// vazifa.py:13 — vazifa.js ga bog'lanmaslik uchun shu yerda.
const OCHIQ = "ochiq";

/** dars.py:53 */
export function darsmi(v) {
  const m = v && typeof v === "object" && "manba" in v ? v.manba : null;
  return !!(m && String(m).startsWith("dars:"));
}

/** dars.py:65 — Python `ValueError`. */
export class DarsXato extends Error {}

// Python `str(x)` (None → "None").
function pyStr(x) {
  if (x === null) return "None";
  if (x === true) return "True";
  if (x === false) return "False";
  return String(x);
}
// Python `d.get(k, birlamchi)` — kalit bor-yo'qligi bo'yicha.
function get(o, k, b = undefined) {
  return o != null && typeof o === "object" && Object.hasOwn(o, k) ? o[k] : b;
}
// Python `int(x)` matn uchun.
function pyInt(x) {
  const s = String(x).trim();
  if (!/^[+-]?\d+$/.test(s)) throw new DarsXato(`invalid literal for int(): '${x}'`);
  return Number.parseInt(s, 10);
}
// Python `str.strip()`
const strip = (s) => s.replace(/^\s+|\s+$/gu, "");

// ──────────────────────────────────────────────────────────── sozlama

/** dars.py:72 */
export async function sozlamalar(db) {
  return {
    yoq: (await db.sozlama(K_YOQ, "")) === "1",
    host: (await db.sozlama(K_HOST, HOST)) || HOST,
    sinf: await db.sozlama(K_SINF, ""),
    odam_id: pyInt((await db.sozlama(K_ODAM, "0")) || 0),
    tt: await db.sozlama(K_TT, ""),
    tekshirildi: await db.sozlama(K_TEKSHIRILDI, ""),
  };
}

/** dars.py:83 */
export async function sozlama_qoy(db, { yoq = null, host = null, sinf = null, odam_id = null } = {}) {
  if (yoq !== null) await db.sozlama_qoy(K_YOQ, yoq ? "1" : "");
  if (host !== null) await db.sozlama_qoy(K_HOST, strip(strip(host).replace(/^\/+|\/+$/g, "")) || HOST);
  if (sinf !== null) await db.sozlama_qoy(K_SINF, strip(sinf));
  if (odam_id !== null) await db.sozlama_qoy(K_ODAM, String(Math.trunc(Number(odam_id))));
}

/** dars.py:96 */
export async function sozlangami(db) {
  const s = await sozlamalar(db);
  return !!(s.yoq && s.sinf && s.odam_id);
}

// ────────────────────────────────────────────────────────────── tarmoq

let _sorovchi = null;
/** Testlar uchun: `fn(url, yuk) → javob obyekti`. null — haqiqiy fetch. */
export function sorovQoy(fn) { _sorovchi = fn; }

/** dars.py:103 */
export async function _sorov(url, yuk) {
  if (_sorovchi) return _sorovchi(url, yuk);
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": "FarvonUy/1.0" },
    body: JSON.stringify(yuk),
    signal: AbortSignal.timeout(KUTISH * 1000),
  });
  if (!r.ok) throw new DarsXato(`HTTP Error ${r.status}`);
  return JSON.parse(await r.text());
}

/** dars.py:113 */
export async function joriy_jadval(host = HOST) {
  const url = `https://${host}/timetable/server/ttviewer.js?__func=getTTViewerData`;
  const yil = Number(vaqt.bugun().slice(0, 4));
  for (const y of [yil, yil - 1]) {
    const j = await _sorov(url, { __args: [null, String(y)], __gsh: GSH });
    const royxat = get(get(j?.r || {}, "regular", {}) || {}, "timetables") || [];
    if (royxat.length) return royxat[royxat.length - 1];
  }
  return null;
}

/** dars.py:128 */
export async function jadval_malumot(host, tt_num) {
  const url = `https://${host}/timetable/server/regulartt.js?__func=regularttGetData`;
  return _sorov(url, { __args: [null, String(tt_num)], __gsh: GSH });
}

// ─────────────────────────────────────────────────────────────── o'qish

/** dars.py:135 — Map(jadval id → Map(qator id → qator)), qo'shilish tartibida. */
export function _jadvallar(malumot) {
  const ichki = get(malumot?.r || {}, "dbiAccessorRes") || {};
  const T = new Map();
  for (const t of get(ichki, "tables", [])) {
    const m = new Map();
    for (const r of get(t, "data_rows", [])) m.set(r.id, r);
    T.set(t.id, m);
  }
  return T;
}

/** dars.py:142 */
export function _nomlash(s) {
  return pyStr(s).split(/\s+/u).filter(Boolean).map((w) => {
    const h = Array.from(w);
    return (h[0] ?? "").toUpperCase() + h.slice(1).join("").toLowerCase();
  }).join(" ");
}

/** dars.py:151 */
export function _daqiqa(v) {
  const [s, d] = pyStr(v).split(":").slice(0, 2);
  return pyInt(s) * 60 + pyInt(d);
}

/** dars.py:156 — dushanba, "YYYY-MM-DD". */
export function hafta_boshi(datefrom) {
  const s = pyStr(datefrom).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) throw new DarsXato(`Invalid isoformat string: '${s}'`);
  return vaqt.kunQosh(s, (7 - vaqt.weekday(s)) % 7);
}

const bosh = new Map();

/** dars.py:166 */
export function darslar(malumot, sinf, boshi) {
  const T = _jadvallar(malumot);
  const sinflar = T.get("classes") || bosh;
  const sinfK = strip(sinf).toLowerCase();
  const kerakli = new Set();
  for (const [k, v] of sinflar) if (strip(pyStr(get(v, "name", ""))).toLowerCase() === sinfK) kerakli.add(k);
  if (!kerakli.size) throw new DarsXato(`«${sinf}» jadvalda topilmadi`);

  const kunlar = [...(T.get("days") || bosh).keys()].sort((a, b) => pyInt(a) - pyInt(b));
  const paralar = T.get("periods") || bosh;
  const darslar_j = T.get("lessons") || bosh;
  const fanlar = T.get("subjects") || bosh;
  const ustozlar = T.get("teachers") || bosh;
  const xonalar = T.get("classrooms") || bosh;

  const natija = [];
  for (const c of (T.get("cards") || bosh).values()) {
    const L = darslar_j.get(get(c, "lessonid"));
    if (!L || !(get(L, "classids") || []).some((x) => kerakli.has(x))) continue;
    const p = paralar.get(pyStr(get(c, "period", null)));
    if (!p || !get(p, "starttime")) continue;
    const boshlanish = _daqiqa(p.starttime);
    const davomiylik = get(p, "endtime") ? _daqiqa(p.endtime) - boshlanish : 80;
    if (davomiylik <= 0) continue;
    const fan = fanlar.get(get(L, "subjectid"));
    const nom = strip(pyStr(get(fan === undefined ? {} : fan, "name", "")));
    if (!nom) continue;
    const ustoz = (get(L, "teacherids") || []).filter((t) => ustozlar.has(t))
      .map((t) => _nomlash(ustozlar.get(t).name)).join(", ");
    const xona = (get(c, "classroomids") || []).filter((x) => xonalar.has(x))
      .map((x) => pyStr(xonalar.get(x).name)).join(", ");
    const kunMaska = Array.from(pyStr(get(c, "days", "")));
    kunMaska.forEach((belgi, j) => {
      if (belgi !== "1" || j >= kunlar.length) return;
      const sana = vaqt.kunQosh(boshi, j);
      natija.push({
        manba: `dars:${sana}:${pyStr(c.period)}`,
        nom,
        sana,
        vaqt: p.starttime,
        davomiylik,
        izoh: [ustoz, xona].filter(Boolean).join(" · ") || null,
      });
    });
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  natija.sort((a, b) => cmp(a.sana, b.sana) || cmp(a.vaqt, b.vaqt) || cmp(a.nom, b.nom));
  return natija;
}

// ─────────────────────────────────────────────────────────── sinxronlash

/**
 * dars.py:229. `a` — tashqi amal; `holat.tartib` — shu amalda berilgan
 * oxirgi tartib (navbatdagi INSERT bazada ko'rinmagani uchun JS sanaydi).
 */
export async function _turni_taminla(db, nom, davomiylik, { a = null, holat = {} } = {}) {
  const ichki = a ?? db.amal();
  const t = await db.q1("SELECT id, shaxsiy, ochirilgan FROM vazifa_turi WHERE nom=?", nom);
  if (t == null) {
    if (holat.tartib == null) {
      holat.tartib = await db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM vazifa_turi");
    } else {
      holat.tartib += 1;
    }
    await ichki.apply("vazifa_turi", "INSERT", {
      nom, davomiylik, tartib: holat.tartib, shaxsiy: 1 });
  } else if (t.ochirilgan || !t.shaxsiy) {
    await ichki.apply("vazifa_turi", "UPDATE", { ochirilgan: 0, shaxsiy: 1 }, t.id);
  }
  if (!a) await ichki.commit();
}

/** dars.py:247 — oraliqdagi dars vazifalarini jadvalga tenglashtiradi. */
export async function sinxronla(db, qatorlar, odam_id, dan, gacha, { a = null } = {}) {
  if (!qatorlar || !qatorlar.length) throw new DarsXato("Bo'sh jadval — kalendar o'chirilmadi");

  const kerak = new Map();
  for (const r of qatorlar) kerak.set(r.manba, r);
  const bor = new Map();
  for (const r of await db.q(
    "SELECT * FROM vazifa WHERE ochirilgan=0 AND manba LIKE 'dars:%'" +
    " AND sana BETWEEN ? AND ?", dan, gacha)) bor.set(r.manba, r);

  let qoshildi = 0, yangilandi = 0, ochirildi = 0;
  const amal = a ?? db.amal("Dars jadvali yangilandi");
  const holat = {};
  const nomlar = [...new Set(qatorlar.map((r) => r.nom))].sort((x, y) => (x < y ? -1 : x > y ? 1 : 0));
  for (const nom of nomlar) {
    const d = Math.max(...qatorlar.filter((r) => r.nom === nom).map((r) => r.davomiylik));
    await _turni_taminla(db, nom, d, { a: amal, holat });
  }

  for (const [kalit, r] of kerak) {
    const yangi = { nom: r.nom, sana: r.sana, vaqt: r.vaqt, davomiylik: r.davomiylik,
      izoh: r.izoh, odam_id };
    const eski = bor.get(kalit);
    if (eski == null) {
      await amal.apply("vazifa", "INSERT", { ...yangi, holat: OCHIQ, manba: kalit });
      qoshildi += 1;
      continue;
    }
    const farq = {};
    for (const [k, v] of Object.entries(yangi)) if (eski[k] !== v) farq[k] = v;
    if (Object.keys(farq).length) {
      await amal.apply("vazifa", "UPDATE", farq, eski.id);
      yangilandi += 1;
    }
  }

  for (const [kalit, eski] of bor) {
    if (!kerak.has(kalit)) {
      await amal.apply("vazifa", "DELETE", {}, eski.id);
      ochirildi += 1;
    }
  }
  if (!a) await amal.commit();

  return { qoshildi, yangilandi, ochirildi, jami: kerak.size };
}

// ───────────────────────────────────────────────────────────── yangilash

const SQLITE_VAQT = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

/** dars.py:294 — tarmoqqa chiqish vaqti keldimi (soatiga bir marta). */
export async function kerakmi(db, hozir = null) {
  if (!(await sozlangami(db))) return false;
  const oxirgi = await db.sozlama(K_TEKSHIRILDI, "");
  if (!oxirgi) return true;
  if (!SQLITE_VAQT.test(oxirgi)) return true;
  const o = vaqt.vaqtDan(oxirgi);
  if (Number.isNaN(o.getTime())) return true;
  const h = hozir || vaqt.hozir();
  return h.getTime() - o.getTime() >= ORALIQ_DAQIQA * 60000;
}

/** dars.py:308 — tarmoqdan o'qib, kalendarni tenglashtiradi. `hozir` — Toshkent devor soati (vaqt.hozir()). */
export async function yangila(db, hozir = null, majburiy = false) {
  if (!(await sozlangami(db))) return null;
  if (!majburiy && !(await kerakmi(db, hozir))) return null;
  const s = await sozlamalar(db);
  hozir = hozir || vaqt.hozir();
  // Chegara urinishdan OLDIN yoziladi.
  await db.sozlama_qoy(K_TEKSHIRILDI, vaqt.vaqtStr(hozir));

  const jadval = await joriy_jadval(s.host);
  if (!jadval) throw new DarsXato("E'lon qilingan jadval yo'q");
  const boshi = hafta_boshi(get(jadval, "datefrom") || vaqt.bugun());
  const malumot = await jadval_malumot(s.host, jadval.tt_num);
  const qatorlar = darslar(malumot, s.sinf, boshi);
  const natija = await sinxronla(db, qatorlar, s.odam_id, boshi, vaqt.kunQosh(boshi, 6));
  await db.sozlama_qoy(K_TT, pyStr(jadval.tt_num));
  natija.hafta = get(jadval, "text") || boshi;
  return natija;
}
