// Reja — botga va Mini App'ga kerak bo'lgan qism (Python `core/plan.py`).
import * as money from "./money.js";
import * as ledger from "./ledger.js";
import * as vaqt from "./vaqt.js";

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
