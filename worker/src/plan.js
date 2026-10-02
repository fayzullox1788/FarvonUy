// Reja — botga va Mini App'ga kerak bo'lgan qism (Python `core/plan.py`).
import * as money from "./money.js";
import * as ledger from "./ledger.js";
import * as vaqt from "./vaqt.js";
import * as rk from "./rasxod_kirit.js";
import * as entries from "./entries.js";

// plan.py:1019
/** Shu kategoriya (va ichki kategoriyalari) mahsulotlari — narxi bilan. */
export async function turi_itemlari(db, turi_id) {
  if (turi_id == null) {
    return db.q("SELECT * FROM item WHERE faol=1 AND ochirilgan=0" +
      " AND turi_id IS NULL ORDER BY nom");
  }
  return db.q(
    "WITH RECURSIVE a(id) AS (SELECT ?" +
    " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)" +
    " SELECT i.*, t.nom turi_nom, (i.turi_id<>?) ichkida FROM item i" +
    " JOIN turi t ON t.id=i.turi_id" +
    " WHERE i.faol=1 AND i.ochirilgan=0 AND i.turi_id IN (SELECT id FROM a)" +
    " ORDER BY ichkida, t.tartib, i.nom COLLATE NOCASE", turi_id, turi_id);
}

// ── Rejaga band pul — «Shaxsiy» varag'idagi Real balans uchun ──────────
// Faqat KO'RSATISH: `v_balans`, audit va qarzga tegmaydi.

// plan.py:50
function _kun(kun) { return kun == null ? vaqt.bugun() : String(kun).slice(0, 10); }

// plan.py:247
/** '2026-09-25' → '2026-09'. */
export function oy_kaliti(kun = null) { return _kun(kun).slice(0, 7); }

// plan.py:43
export function oy_oxiri(kun = null) {
  const [y, m] = _kun(kun).split("-").map(Number);
  const d = new Date(Date.UTC(y, m, 0)); // keyingi oyning 0-kuni = shu oyning oxiri
  return `${y}-${String(m).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

// plan.py:93
export async function reja_ol(db, boshi, tur = "haftalik") {
  return db.q1("SELECT * FROM reja WHERE tur=? AND boshi=?", tur, boshi);
}

// plan.py:257
/** Umumiy oylik reja yoki null (qo'yilmagan). */
export async function oylik_reja(db, oy) {
  const r = await reja_ol(db, oy + "-01", "oylik");
  return r && r.budjet ? r.budjet : null;
}

// plan.py:264
/** Map<turi_id, limit> — `budjet` jadvali, faqat asosiylar, faqat > 0; oyniki '*' ni bosadi. */
export async function limit_reja(db, oy) {
  const natija = new Map();
  for (const r of await db.q("SELECT b.turi_id, b.summa FROM budjet b" +
    " JOIN turi t ON t.id=b.turi_id" +
    " WHERE t.ota_id IS NULL AND b.oy IN (?, '*')" +
    " ORDER BY b.oy='*' DESC", oy)) {
    natija.set(r.turi_id, r.summa);
  }
  return new Map([...natija].filter(([, v]) => v > 0));
}

// plan.py:286
function _doira_sharti(odam_id) {
  if (odam_id == null) return [" AND q.umumiymi=1", []];
  return [" AND q.umumiymi=0 AND q.odam_id=?", [odam_id]];
}

// plan.py:293
/** Map<asosiy turi_id, summa> — reja yozuvlari (ichkisi otasiga). */
export async function yozuv_reja(db, oy, odam_id = null) {
  const [shart, args] = _doira_sharti(odam_id);
  const qatorlar = await db.q(
    "WITH RECURSIVE y(id, ildiz) AS (" +
    "  SELECT id, id FROM turi WHERE ota_id IS NULL" +
    "  UNION ALL SELECT t.id, y.ildiz FROM turi t JOIN y ON t.ota_id=y.id)" +
    " SELECT y.ildiz, SUM(q.summa) jami FROM reja_qator q" +
    " JOIN reja r ON r.id=q.reja_id JOIN y ON y.id=q.turi_id" +
    " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0" + shart +
    " GROUP BY y.ildiz", oy + "-01", ...args);
  return new Map(qatorlar.filter((r) => r.jami).map((r) => [r.ildiz, r.jami]));
}

// plan.py:308
/** Map<turi_id, reja> — umumiy: limit + umumiy yozuvlar; shaxsiy: o'sha odamning yozuvlari. */
export async function turi_reja(db, oy, odam_id = null) {
  const natija = odam_id == null ? new Map(await limit_reja(db, oy)) : new Map();
  for (const [tid, summa] of await yozuv_reja(db, oy, odam_id)) {
    natija.set(tid, (natija.get(tid) || 0) + summa);
  }
  return new Map([...natija].filter(([, v]) => v > 0));
}

// plan.py:776
/**
 * `reja_va_fakt` ning JAMI qismi: {oy, boshi, oxiri, odam_id, reja_bor,
 * umumiy_qoyilgan, reja, fakt, qolgan, turi_reja_jami}. Kategoriya
 * qatorlari (`qatorlar`, `foiz`, `holat`, `diqqat`) hali port qilinmagan —
 * `band_pul` ga kerak emas.
 */
export async function reja_va_fakt(db, oy, odam_id = null) {
  const boshi = oy + "-01", oxiri = oy_oxiri(oy + "-01");
  const rejalar = await turi_reja(db, oy, odam_id);
  const fakt = await ledger.turi_boyicha(db, boshi, oxiri, odam_id, odam_id ? "shaxsiy" : "umumiy");
  const umumiy = odam_id == null ? await oylik_reja(db, oy) : null;
  const turi_jami = [...rejalar.values()].reduce((s, v) => s + v, 0);
  const reja = umumiy != null ? umumiy : turi_jami;
  const jami_fakt = fakt.reduce((s, t) => s + Number(t.summa), 0);
  return { oy, boshi, oxiri, odam_id,
    reja_bor: Boolean(umumiy) || rejalar.size > 0,
    umumiy_qoyilgan: umumiy != null,
    reja, fakt: jami_fakt, qolgan: reja - jami_fakt, turi_reja_jami: turi_jami };
}

// plan.py:849
/** Map<odam_id, band summa> — joriy oy rejasidan. Reja yo'q bo'lsa bo'sh. */
export async function band_pul(db, kun = null) {
  const oy = oy_kaliti(kun);
  const idlar = (await db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id")).map((r) => r.id);
  const natija = new Map();
  const rf = await reja_va_fakt(db, oy);
  const qolgan = rf.reja_bor ? Math.max(0, rf.qolgan) : 0;
  if (qolgan && idlar.length) {
    for (const u of money.bol_teng(qolgan, idlar)) natija.set(u.odam_id, u.summa);
  }
  for (const oid of idlar) {
    const rs = await reja_va_fakt(db, oy, oid);
    if (rs.reja_bor && rs.qolgan > 0) natija.set(oid, (natija.get(oid) || 0) + rs.qolgan);
  }
  return new Map([...natija].filter(([, v]) => v));
}

// plan.py:871
/** «Qo'ldagi pul» kimniki: `sozlama.asosiy_odam`, yo'q bo'lsa birinchi faol odam. */
export async function asosiy_odam(db) {
  const r = await db.q1("SELECT qiymat FROM sozlama WHERE kalit='asosiy_odam'");
  if (r && r.qiymat && await db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", Math.trunc(Number(r.qiymat)))) {
    return Math.trunc(Number(r.qiymat));
  }
  return db.skalyar("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id", [], null);
}

// plan.py:882
/**
 * Rejaga band pul HAQIQATDA kimning qo'lidan ayiriladi:
 * Map<odam_id, {band, ayirildi, qarz, qoplaydi}>. Hech kimdan naqddan
 * (manfiy bo'lsa 0) ortiq ayirilmaydi; yetmagani asosiy odam qoplaydi.
 */
export async function band_hisob(db, kun = null) {
  const band = await band_pul(db, kun);
  if (!band.size) return new Map();
  const asosiy = await asosiy_odam(db);
  const naqd = new Map((await db.q("SELECT id, naqd FROM v_balans"))
    .map((r) => [r.id, Math.max(0, Math.trunc(Number(r.naqd)))]));
  const natija = new Map();
  let boshqalar_qarzi = 0;
  for (const [oid, b] of band) {
    if (oid === asosiy) continue;
    const ayir = Math.min(b, naqd.get(oid) || 0);
    natija.set(oid, { band: b, ayirildi: ayir, qarz: b - ayir, qoplaydi: 0 });
    boshqalar_qarzi += b - ayir;
  }
  if (asosiy != null) {
    const ozi = band.get(asosiy) || 0;
    const kerak = ozi + boshqalar_qarzi;
    const ayir = Math.min(kerak, naqd.get(asosiy) || 0);
    const qoplaydi = Math.min(boshqalar_qarzi, Math.max(0, ayir - ozi));
    natija.set(asosiy, { band: ozi, ayirildi: ayir, qarz: kerak - ayir, qoplaydi });
  }
  return natija;
}

// plan.py:967
/** Map<odam_id, qo'lidagi puldan ayiriladigani> — ko'rsatish uchun. */
export async function band_ayirma(db, kun = null) {
  return new Map([...await band_hisob(db, kun)].filter(([, v]) => v.ayirildi)
    .map(([k, v]) => [k, v.ayirildi]));
}

// ════════════════════════════════════════════════════════════════════════
// Reja boshqaruvi — Mini App «Sozlamalar → Reja (budget)» uchun
// (plan.py: reja_yarat, budjet_qoy, reja_saqla, reja_bormi, reja_kochir,
// reja yozuvlari). Yozuvlar BITTA undo — `a` (Amal) berilsa unga qo'shiladi.
//
// Navbatli yozuv (PORT.md): Python amal ichida o'z yozuvini o'qiydi —
// `reja_kochir` da yaratilgan oylik `reja` qatori keyingi yozuvlarga,
// yangi katalog mahsuloti keyingi qatorga ko'rinadi. JS'da buni `kesh`
// ({reja: Map<tur|boshi, id>, item: Map<kalit, id>}) amal bo'ylab tashiydi.

export const YAQIN_FOIZ = 80; // plan.py:244
export const HAMMASI = "hammasi"; // plan.py:343

function _kesh(kesh) {
  return kesh || { reja: new Map(), item: new Map() };
}

// plan.py:62
export async function itemlar(db, faqat_faol = true) {
  const shart = " WHERE i.ochirilgan=0" + (faqat_faol ? " AND i.faol=1" : "");
  return db.q(
    "SELECT i.*, t.nom turi_nom, t.belgi turi_belgi FROM item i" +
    ` LEFT JOIN turi t ON t.id=i.turi_id${shart}` +
    " ORDER BY t.tartib, i.nom");
}

// plan.py:70
export async function item_qosh(db, nom, narx, turi_id = null, birlik = null, cikl_kun = null, { a = null } = {}) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Mahsulot nomi bo'sh");
  const ozi = a == null;
  if (ozi) a = db.amal(`Katalog: ${nom} qo'shildi`);
  const id = await a.apply("item", "INSERT", {
    nom, narx: Math.trunc(Number(narx)), turi_id: turi_id ?? null,
    birlik: birlik || null, cikl_kun: cikl_kun ?? null });
  if (ozi) await a.commit();
  return id;
}

// plan.py:1047
export async function item_topib_qosh(db, nom, narx, turi_id, { a = null } = {}) {
  nom = String(nom ?? "").trim();
  const bor = await db.q1("SELECT id FROM item WHERE faol=1 AND ochirilgan=0 AND nom=? AND" +
    " (turi_id IS ? OR turi_id=?)", nom, turi_id ?? null, turi_id ?? null);
  if (bor) return bor.id;
  return item_qosh(db, nom, narx, turi_id, null, null, { a });
}

// plan.py:252
/** '2026-09' + 1 → '2026-10'. */
export function oy_sur(oy, qadam) {
  const y = Number(oy.slice(0, 4)), m = Number(oy.slice(5, 7)) - 1 + qadam;
  return `${String(y + Math.floor(m / 12)).padStart(4, "0")}-${String(((m % 12) + 12) % 12 + 1).padStart(2, "0")}`;
}

/** 'YYYY-MM-DD' + n kun (UTC hisobida, vaqt mintaqasiz). */
function _kun_qosh(sana, n) {
  const d = new Date(Date.parse(sana.slice(0, 10) + "T00:00:00Z") + n * 86400000);
  return d.toISOString().slice(0, 10);
}

// plan.py:28
export function hafta_oxiri(kun = null) {
  const s = _kun(kun);
  const hk = (new Date(Date.parse(s + "T00:00:00Z")).getUTCDay() + 6) % 7; // Du=0
  return _kun_qosh(s, 6 - hk);
}

// plan.py:97
/**
 * Reja yaratadi (bor bo'lsa id'sini qaytaradi). `katalogdan` — sikli bor
 * mahsulotlar narx snapshoti bilan. `kesh` — shu amalda yaratilganlar.
 */
export async function reja_yarat(db, boshi, tur = "haftalik", katalogdan = true, { a = null, kesh = null } = {}) {
  kesh = _kesh(kesh);
  const k = `${tur}|${boshi}`;
  if (kesh.reja.has(k)) return kesh.reja.get(k);
  const bor = await reja_ol(db, boshi, tur);
  if (bor) return bor.id;
  const oxiri = tur === "haftalik" ? hafta_oxiri(boshi) : oy_oxiri(boshi);
  const kunlar = tur === "haftalik" ? 7 : 30;
  const ozi = a == null;
  if (ozi) a = db.amal(`Reja yaratildi: ${boshi}`);
  const rid = await a.apply("reja", "INSERT", { tur, boshi, oxiri });
  kesh.reja.set(k, rid);
  if (katalogdan) {
    for (const it of await itemlar(db)) {
      const cikl = it.cikl_kun;
      if (!cikl) continue;
      const marta = Math.max(1, _pyRound(kunlar / cikl));
      await a.apply("reja_qator", "INSERT", {
        reja_id: rid, item_id: it.id, nom: it.nom, turi_id: it.turi_id,
        summa: Math.trunc(Number(it.narx)) * marta, miqdor: marta });
    }
  }
  if (ozi) await a.commit();
  return rid;
}

/** Python `round()` — bankir yaxlitlashi (x.5 → juftga). */
function _pyRound(x) {
  const f = Math.floor(x), d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// plan.py:223
export async function budjet_qoy(db, turi_id, oy, summa, { a = null } = {}) {
  const bor = await db.q1("SELECT id FROM budjet WHERE turi_id=? AND oy=?", turi_id, oy);
  const ozi = a == null;
  if (ozi) a = db.amal("Budjet o'zgartirildi");
  if (bor) await a.apply("budjet", "UPDATE", { summa: Math.trunc(Number(summa)) }, bor.id);
  else await a.apply("budjet", "INSERT", { turi_id, oy, summa: Math.trunc(Number(summa)) });
  if (ozi) await a.commit();
}

// plan.py:320
/**
 * Oy rejasini BITTA undo qadamida saqlaydi. `umumiy` null/0 — umumiy reja
 * olib tashlanadi (`budjet` NULL). `turlar` — Map<turi_id, summa> (yoki
 * {id: summa}); faqat o'zgarganlari yoziladi, 0 — shu oyda limit yo'q.
 * FAQAT limit (`budjet`) — reja yozuvlariga tegmaydi.
 */
export async function reja_saqla(db, oy, umumiy, turlar, { a = null, kesh = null } = {}) {
  kesh = _kesh(kesh);
  const juft = turlar instanceof Map ? [...turlar]
    : Object.entries(turlar || {}).map(([k, v]) => [Math.trunc(Number(k)), v]);
  const eski = await limit_reja(db, oy);
  const ozi = a == null;
  if (ozi) a = db.amal(`Oylik reja: ${oy}`);
  const r = await reja_ol(db, oy + "-01", "oylik");
  const yangi = umumiy && umumiy > 0 ? Math.trunc(Number(umumiy)) : null;
  if (r == null && yangi != null) {
    const rid = await reja_yarat(db, oy + "-01", "oylik", false, { a, kesh });
    await a.apply("reja", "UPDATE", { budjet: yangi }, rid);
  } else if (r != null && r.budjet !== yangi) {
    await a.apply("reja", "UPDATE", { budjet: yangi }, r.id);
  }
  for (const [tid, s] of juft) {
    const summa = Math.max(0, Math.trunc(Number(s || 0)));
    if (summa !== (eski.get(tid) || 0)) await budjet_qoy(db, tid, oy, summa, { a });
  }
  if (ozi) await a.commit();
}

// plan.py:346
/** Shu oyda reja bormi: HAMMASI — har qanday doira; null — umumiy; <id> — o'sha odamniki. */
export async function reja_bormi(db, oy, odam_id = HAMMASI) {
  if (odam_id === HAMMASI) {
    return (await reja_bormi(db, oy, null)) || Boolean(await db.skalyar(
      "SELECT COUNT(*) FROM reja_qator q JOIN reja r ON r.id=q.reja_id" +
      " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0" +
      " AND q.umumiymi=0", [oy + "-01"]));
  }
  if (odam_id == null && (await oylik_reja(db, oy)) != null) return true;
  return (await turi_reja(db, oy, odam_id)).size > 0;
}

// plan.py:359
/** Limit oynasi: har asosiy kategoriya — limiti (`reja`), umumiy fakti va yozuvlari. */
export async function reja_kategoriyalari(db, oy) {
  const rejalar = await limit_reja(db, oy);
  const yozuvlar = await yozuv_reja(db, oy);
  const fakt = new Map((await ledger.turi_boyicha(db, oy + "-01", oy_oxiri(oy + "-01"), null, "umumiy"))
    .map((t) => [t.turi_id, t.summa]));
  const natija = [];
  for (const t of await db.q("SELECT id, nom, belgi, rasm, faol FROM turi" +
    " WHERE ota_id IS NULL ORDER BY tartib, id")) {
    const r = rejalar.get(t.id) || 0, f = fakt.get(t.id) || 0;
    if (t.faol || r || f) {
      natija.push({ turi_id: t.id, nom: t.nom, belgi: t.belgi, rasm: t.rasm,
        reja: r, fakt: f, yozuv: yozuvlar.get(t.id) || 0 });
    }
  }
  return natija;
}

// plan.py:380
/** `dan` oy rejasini `ga` oyga ko'chiradi (bitta undo). `dan` da reja yo'q — false. */
export async function reja_kochir(db, dan, ga) {
  if (!await reja_bormi(db, dan)) return false;
  const a = db.amal(`Reja ko'chirildi: ${dan} → ${ga}`);
  const kesh = _kesh(null);
  await reja_saqla(db, ga, await oylik_reja(db, dan), await limit_reja(db, dan), { a, kesh });
  const oxirgi = Number(oy_oxiri(ga + "-01").slice(8, 10));
  for (const y of await reja_yozuvlari(db, dan)) {
    const kun = Math.min(Number((y.sana || dan + "-01").slice(8, 10)), oxirgi);
    await reja_yozuv_saqla(db, `${ga}-${String(kun).padStart(2, "0")}`, y.nom, y.turi_id, y.summa,
      await reja_yozuv_mahsulotlari(db, y.id), null,
      { majburiy: false, umumiymi: Boolean(y.umumiymi), odam_id: y.odam_id, a, kesh });
  }
  await a.commit();
  return true;
}

// ── rasxod_kirit.py dagi mahsulot qatorlari yordamchilari (reja ham ishlatadi) ──

/** SQLite `COLLATE NOCASE` — faqat ASCII harflar. */
const _nocase = (s) => String(s).replace(/[A-Z]/g, (c) => c.toLowerCase());

// rasxod_kirit.py:120
/** Katalogda yo'q mahsulot shu kategoriyaga qo'shiladi va qator unga bog'lanadi (amal ICHIDA). */
export async function _rk_yangi_mahsulotlarni_qosh(db, qatorlar, turi_id, { a, kesh = null }) {
  kesh = _kesh(kesh);
  for (const x of qatorlar) {
    if (x.item_id) continue;
    const kalit = `${turi_id ?? ""}|${_nocase(x.nom)}`;
    if (kesh.item.has(kalit)) { x.item_id = kesh.item.get(kalit); continue; }
    const mavjud = await db.q1(
      "SELECT id FROM item WHERE ochirilgan=0 AND turi_id IS ?" +
      " AND nom=? COLLATE NOCASE", turi_id ?? null, x.nom);
    if (mavjud) { x.item_id = mavjud.id; continue; }
    const miqdor = Math.max(1, Math.trunc(Number(x.miqdor)));
    const narx = Math.min(...money.bol_teng(Math.trunc(Number(x.summa)),
      Array.from({ length: miqdor }, (_, i) => i)).map((u) => u.summa));
    x.item_id = await item_topib_qosh(db, x.nom, narx, turi_id, { a });
    kesh.item.set(kalit, x.item_id);
  }
}

// rasxod_kirit.py:158
/** Yozuvning mahsulot qatorlarini yangilaydi (amal ICHIDA); o'zgarmagan bo'lsa yozmaydi. */
export async function _rk_qatorlarni_yoz(db, jadval, ota_ustun, ota_id, qatorlar, { a }) {
  if (!["rasxod_mahsulot", "reja_mahsulot"].includes(jadval)) throw new Error(jadval);
  const eski = await db.q(`SELECT id, item_id, nom, miqdor, summa FROM ${jadval}` +
    ` WHERE ${ota_ustun}=? AND ochirilgan=0 ORDER BY tartib, id`, ota_id);
  const kalit = (x) => JSON.stringify([x.item_id ?? null, x.nom,
    Math.trunc(Number(x.miqdor)), Math.trunc(Number(x.summa))]);
  if (JSON.stringify(eski.map(kalit)) === JSON.stringify(qatorlar.map(kalit))) return;
  const tolangan = new Map();
  if (jadval === "reja_mahsulot") {
    for (const x of await db.q("SELECT item_id, nom, tolangan FROM reja_mahsulot" +
      " WHERE qator_id=? AND ochirilgan=0 AND tolangan IS NOT NULL", ota_id)) {
      const k = JSON.stringify([x.item_id ?? null, x.nom]);
      if (!tolangan.has(k)) tolangan.set(k, x.tolangan);
    }
  }
  for (const x of eski) await a.apply(jadval, "DELETE", {}, x.id);
  let i = 0;
  for (const x of qatorlar) {
    const maydon = { [ota_ustun]: ota_id, item_id: x.item_id ?? null, nom: x.nom,
      miqdor: Math.trunc(Number(x.miqdor)), summa: Math.trunc(Number(x.summa)), tartib: i++ };
    const k = JSON.stringify([x.item_id ?? null, x.nom]);
    if (tolangan.has(k)) { maydon.tolangan = tolangan.get(k); tolangan.delete(k); }
    await a.apply(jadval, "INSERT", maydon);
  }
}

// rasxod_kirit.py:193
export async function _rk_qatorlarni_ol(db, jadval, ota_ustun, ota_id) {
  if (!["rasxod_mahsulot", "reja_mahsulot"].includes(jadval)) throw new Error(jadval);
  return db.q(`SELECT item_id, nom, miqdor, summa FROM ${jadval}` +
    ` WHERE ${ota_ustun}=? AND ochirilgan=0 ORDER BY tartib, id`, ota_id);
}

// ── Reja yozuvlari (rasxod kabi) ──────────────────────────────────────

// plan.py:406
/**
 * Yangi reja yozuvi yoki mavjudini tahrirlash — bitta undo. Qoida rasxodniki:
 * sabab va faol kategoriya majburiy, mahsulotlar bo'lsa summa — yig'indisi.
 * Shaxsiy (`umumiymi=false`) — `odam_id` majburiy.
 */
export async function reja_yozuv_saqla(db, sana, nom, turi_id, summa, mahsulotlar = null, qator_id = null,
  { majburiy = true, umumiymi = true, odam_id = null, a = null, kesh = null } = {}) {
  if (umumiymi) {
    odam_id = null;
  } else if (odam_id == null || (majburiy && !await db.q1(
    "SELECT 1 FROM odam WHERE id=? AND faol=1", odam_id))) {
    throw new Error("Shaxsiy reja kimniki ekanini tanlang.");
  }
  sana = _kun(sana);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sana) || _kun_qosh(sana, 0) !== sana) throw new Error("Sana noto'g'ri.");
  nom = String(nom ?? "").trim();
  const qatorlar = await rk.mahsulot_qatorlari(db, mahsulotlar);
  summa = Math.trunc(Number(summa || 0));
  if (qatorlar.length && rk.qatorlar_jami(qatorlar) !== summa) {
    throw new Error("Summa mahsulotlar yig'indisiga teng emas " +
      `(${money.fmt_som(rk.qatorlar_jami(qatorlar))}).`);
  }
  if (summa <= 0) throw new Error("Summa kiritilmagan.");
  if (majburiy) await entries.rasxod_majburiy(db, nom, turi_id);
  const oy = oy_kaliti(sana);
  const maydonlar = { nom, turi_id: turi_id ?? null, summa, sana, miqdor: 1,
    umumiymi: umumiymi ? 1 : 0, odam_id: odam_id ?? null };
  kesh = _kesh(kesh);
  const ozi = a == null;
  if (ozi) a = db.amal(`Reja: ${nom || "—"} ${money.fmt(summa)}`);
  await _rk_yangi_mahsulotlarni_qosh(db, qatorlar, turi_id ?? null, { a, kesh });
  maydonlar.item_id = qatorlar.length === 1 ? qatorlar[0].item_id : null;
  maydonlar.reja_id = await reja_yarat(db, oy + "-01", "oylik", false, { a, kesh });
  if (qator_id == null) qator_id = await a.apply("reja_qator", "INSERT", maydonlar);
  else await a.apply("reja_qator", "UPDATE", maydonlar, qator_id);
  await _rk_qatorlarni_yoz(db, "reja_mahsulot", "qator_id", qator_id, qatorlar, { a });
  if (ozi) await a.commit();
  return qator_id;
}

// plan.py:456
/** Nusxa — keyingi kunga (oydan chiqmaydi), mahsulotlari bilan; «aslida to'landi» ko'chmaydi. */
export async function reja_yozuv_nusxa(db, qator_id, sana = null) {
  const y = await db.q1("SELECT * FROM reja_qator WHERE id=? AND ochirilgan=0", qator_id);
  if (!y) throw new Error("Reja ro'yxati topilmadi.");
  if (sana == null) {
    const asl = _kun(y.sana || null);
    const keyingi = _kun_qosh(asl, 1);
    sana = keyingi.slice(0, 7) === asl.slice(0, 7) ? keyingi : asl;
  }
  return reja_yozuv_saqla(db, sana, y.nom, y.turi_id, y.summa,
    await reja_yozuv_mahsulotlari(db, qator_id), null,
    { majburiy: false, umumiymi: Boolean(y.umumiymi), odam_id: y.odam_id });
}

// plan.py:475
export async function reja_yozuv_ochir(db, qator_id) {
  const r = await db.q1("SELECT nom FROM reja_qator WHERE id=?", qator_id);
  const a = db.amal(`Reja o'chirildi: ${(r ? r.nom : "") || "—"}`);
  await a.apply("reja_qator", "DELETE", {}, qator_id);
  await a.commit();
}

// plan.py:481
/** Oyning reja yozuvlari. `odam_id`: HAMMASI | null (umumiy) | <id> (shaxsiy). */
export async function reja_yozuvlari(db, oy, odam_id = HAMMASI) {
  const [shart, args] = odam_id === HAMMASI ? ["", []] : _doira_sharti(odam_id);
  return db.q(
    "SELECT q.*, t.nom turi_nom, t.belgi turi_belgi, t.rasm turi_rasm," +
    " o.nom odam_nom," +
    " (SELECT COUNT(*) FROM reja_mahsulot m WHERE m.qator_id=q.id" +
    "  AND m.ochirilgan=0) mahsulot_soni" +
    " FROM reja_qator q JOIN reja r ON r.id=q.reja_id" +
    " LEFT JOIN turi t ON t.id=q.turi_id" +
    " LEFT JOIN odam o ON o.id=q.odam_id" +
    " WHERE r.tur='oylik' AND r.boshi=? AND q.ochirilgan=0" + shart +
    " ORDER BY COALESCE(q.sana, r.boshi), q.id", oy + "-01", ...args);
}

// plan.py:514
async function _toliq(db, y) {
  const x = { ...y };
  x.mahsulotlar = await db.q(
    "SELECT id, item_id, nom, miqdor, summa, tolangan" +
    " FROM reja_mahsulot WHERE qator_id=? AND ochirilgan=0" +
    " ORDER BY tartib, id", y.id);
  const r = y.rasxod_id ? await db.q1("SELECT id, sana, kim_toladi, summa FROM rasxod" +
    " WHERE id=? AND ochirilgan=0", y.rasxod_id) : null;
  x.rasxod = r || null;
  return x;
}

// plan.py:497
/** Toifa ICHI: asosiy kategoriyaning (ichkilari bilan) reja yozuvlari, to'liq. */
export async function kategoriya_reja_yozuvlari(db, oy, turi_id, odam_id = null) {
  const idlar = new Set((await db.q(
    "WITH RECURSIVE a(id) AS (SELECT ?" +
    " UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)" +
    " SELECT id FROM a", turi_id ?? null)).map((r) => r.id));
  const natija = [];
  for (const y of await reja_yozuvlari(db, oy, odam_id)) {
    if (!idlar.has(y.turi_id)) continue;
    natija.push(await _toliq(db, y));
  }
  return natija;
}

// plan.py:575
/** Map<sana, summa> — asosiy kategoriyaning rasxodi `reja_va_fakt` doirasida
 *  (`ledger.kategoriya_rasxodlari` qatorlari kun bo'yicha). */
async function _kun_fakt(db, turi_id, boshi, oxiri, odam_id) {
  const [manba, args] = ledger._manba(boshi, oxiri, odam_id, odam_id ? "shaxsiy" : "umumiy");
  const shart = turi_id == null ? "ild.ildiz IS NULL" : "ild.ildiz IN (?)";
  const kunlar = new Map();
  for (const r of await db.q(ledger._ILDIZ + ", m AS (" + manba + ")" +
    " SELECT r.sana, m.summa FROM m JOIN rasxod r ON r.id=m.id" +
    " LEFT JOIN ild ON ild.id=m.turi_id WHERE " + shart +
    " ORDER BY r.sana DESC, r.id DESC", ...args, ...(turi_id == null ? [] : [turi_id]))) {
    const s = String(r.sana).slice(0, 10);
    kunlar.set(s, (kunlar.get(s) || 0) + r.summa);
  }
  return kunlar;
}

// plan.py:587
/**
 * Toifa ichi, KUN bo'yicha: {reja, fakt, qolgan, limit, kunlar: [{sana, reja,
 * fakt, royxatlar, qolgan}]}. `reja`/`fakt` — `reja_va_fakt` qatori bilan teng.
 */
export async function kategoriya_kunlari(db, oy, turi_id, odam_id = null) {
  const boshi = oy + "-01", oxiri = oy_oxiri(boshi);
  const kunlar = new Map();
  const _k = (sana) => {
    if (!kunlar.has(sana)) kunlar.set(sana, { sana, reja: 0, fakt: 0, royxatlar: [] });
    return kunlar.get(sana);
  };
  for (const y of await kategoriya_reja_yozuvlari(db, oy, turi_id, odam_id)) {
    const k = _k(String(y.sana || boshi).slice(0, 10));
    k.reja += y.summa;
    k.royxatlar.push(y.nom || "—");
  }
  for (const [sana, summa] of await _kun_fakt(db, turi_id, boshi, oxiri, odam_id)) _k(sana).fakt += summa;
  const qatorlar = [...kunlar.values()].sort((x, y) => (x.sana < y.sana ? -1 : x.sana > y.sana ? 1 : 0));
  for (const k of qatorlar) k.qolgan = k.reja - k.fakt;
  const limit = odam_id == null && turi_id != null ? ((await limit_reja(db, oy)).get(turi_id) || 0) : 0;
  const reja = qatorlar.reduce((s, k) => s + k.reja, 0) + limit;
  const fakt = qatorlar.reduce((s, k) => s + k.fakt, 0);
  return { reja, fakt, qolgan: reja - fakt, limit, kunlar: qatorlar };
}

// plan.py:654
/** Kun/kategoriya qatoridagi «Holat»: reja − fakt. */
export function kun_holati(reja, fakt) {
  if (!fakt) return reja ? "sarflanmagan" : "—";
  if (!reja) return "rejasiz";
  const farq = reja - fakt;
  return !farq ? "rejadagidek" : farq > 0 ? `${money.fmt(farq)} qoldi` : `${money.fmt(-farq)} oshdi`;
}

// plan.py:676
export async function reja_yozuv_toliq(db, qator_id) {
  const y = await db.q1("SELECT q.*, t.nom turi_nom, o.nom odam_nom FROM reja_qator q" +
    " LEFT JOIN turi t ON t.id=q.turi_id" +
    " LEFT JOIN odam o ON o.id=q.odam_id" +
    " WHERE q.id=? AND q.ochirilgan=0", qator_id);
  return y ? _toliq(db, y) : null;
}

// plan.py:760
export async function reja_yozuv_mahsulotlari(db, qator_id) {
  return _rk_qatorlarni_ol(db, "reja_mahsulot", "qator_id", qator_id);
}
