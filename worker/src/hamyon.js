// Hamyon — JS egizagi (Python `core/hamyon.py`): bot uchun tanlov/tekshiruv va
// Mini App «To'lov usullari» uchun o'qish/yozish (pastda).
import * as _vaqt from "./vaqt.js";
import * as _money from "./money.js";

// hamyon.py:90
/** Karta shu odamniki va o'chirilmagan bo'lishi SHART (null — naqd). */
export async function tekshir_karta(db, karta_id, odam_id) {
  if (karta_id == null) return;
  if (!await db.q1("SELECT 1 FROM karta WHERE id=? AND odam_id IS ? AND ochirilgan=0",
    karta_id, odam_id ?? null)) {
    throw new Error("Bu karta to'lovchiniki emas yoki o'chirilgan — " +
      "«Qayerdan» ni qayta tanlang.");
  }
}

// hamyon.py:28
export const NAQD_NOM = "Naqd";

// hamyon.py:73
/** Rasxod/kirim oynasidagi «qayerdan» ro'yxati: [[null, "Naqd"], [karta_id, nom], …]. */
export async function tanlov(db, odam_id) {
  const natija = [[null, NAQD_NOM]];
  if (odam_id != null) {
    for (const r of await db.q("SELECT id, nom FROM karta WHERE odam_id=? AND ochirilgan=0" +
      " ORDER BY tartib, id", odam_id)) natija.push([r.id, r.nom]);
  }
  return natija;
}

// ─────────────────────────────────────────── Hamyon: o'qish va yozish
// (Mini App «To'lov usullari» — desktop «Hamyon» varag'i bilan bir xil yo'l.)
// Python date.today() → vaqt.bugun(); f"{x:,}" → money.fmt.

// hamyon.py:33
/** Map{karta_id: qoldiq} — faqat o'chirilmagan kartalar. */
export async function _qoldiqlar(db, odam_id = null) {
  let shart = "", args = [];
  if (odam_id != null) { shart = " AND k.odam_id=?"; args = [odam_id]; }
  const rows = await db.q(`
        SELECT k.id,
          COALESCE((SELECT SUM(summa) FROM kirim x
                    WHERE x.karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0)
        - COALESCE((SELECT SUM(summa) FROM rasxod x
                    WHERE x.karta_id=k.id AND x.kim_toladi=k.odam_id
                      AND x.ochirilgan=0), 0)
        + COALESCE((SELECT SUM(summa) FROM karta_otkazma x
                    WHERE x.ga_karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0)
        - COALESCE((SELECT SUM(summa) FROM karta_otkazma x
                    WHERE x.dan_karta_id=k.id AND x.odam_id=k.odam_id
                      AND x.ochirilgan=0), 0) AS qoldiq
        FROM karta k WHERE k.ochirilgan=0${shart}`, ...args);
  return new Map(rows.map((r) => [r.id, Math.trunc(Number(r.qoldiq))]));
}

// hamyon.py:55
/** [{id, nom, qoldiq}] — tartib bo'yicha. */
export async function kartalar(db, odam_id) {
  const q = await _qoldiqlar(db, odam_id);
  return (await db.q("SELECT id, nom FROM karta WHERE odam_id=?" +
    " AND ochirilgan=0 ORDER BY tartib, id", odam_id))
    .map((r) => ({ id: r.id, nom: r.nom, qoldiq: q.get(r.id) ?? 0 }));
}

// hamyon.py:63
/** {jami, naqd, karta, kartalar} — jami = v_balans.naqd. */
export async function hamyon(db, odam_id) {
  const jami = Math.trunc(Number(await db.skalyar("SELECT naqd FROM v_balans WHERE id=?", [odam_id], 0)));
  const k = await kartalar(db, odam_id);
  const kjami = k.reduce((s, x) => s + x.qoldiq, 0);
  return { jami, naqd: jami - kjami, karta: kjami, kartalar: k };
}

// hamyon.py:83
export async function joy_nomi(db, karta_id) {
  if (karta_id == null) return NAQD_NOM;
  return db.skalyar("SELECT nom FROM karta WHERE id=?", [karta_id], "?");
}

// hamyon.py:100
/** Kartaning tarixi, yangisi tepada: [{tur, id, sana, nima, summa(±)}]. */
export async function harakatlar(db, karta_id) {
  const k = await db.q1("SELECT odam_id FROM karta WHERE id=?", karta_id);
  if (!k) return [];
  const oid = k.odam_id;
  const natija = [];
  for (const r of await db.q("SELECT id, sana, summa, sabab FROM kirim WHERE karta_id=?" +
    " AND odam_id=? AND ochirilgan=0", karta_id, oid)) {
    natija.push({ tur: "kirim", id: r.id, sana: r.sana, nima: `Kirim: ${r.sabab || "—"}`, summa: r.summa });
  }
  for (const r of await db.q("SELECT id, sana, summa, nom FROM rasxod WHERE karta_id=?" +
    " AND kim_toladi=? AND ochirilgan=0", karta_id, oid)) {
    natija.push({ tur: "rasxod", id: r.id, sana: r.sana, nima: r.nom || "Rasxod", summa: -r.summa });
  }
  for (const r of await db.q("SELECT * FROM karta_otkazma WHERE odam_id=? AND ochirilgan=0" +
    " AND (dan_karta_id=? OR ga_karta_id=?)", oid, karta_id, karta_id)) {
    const kelgan = r.ga_karta_id === karta_id;
    const boshqa = await joy_nomi(db, kelgan ? r.dan_karta_id : r.ga_karta_id);
    let nima = kelgan ? `${boshqa} → shu karta` : `Shu karta → ${boshqa}`;
    if (r.izoh) nima += ` (${r.izoh})`;
    natija.push({ tur: "otkazma", id: r.id, sana: r.sana, nima, summa: kelgan ? r.summa : -r.summa });
  }
  // Python: sort(key=(sana, tur, id), reverse=True)
  const kal = (x) => [x.sana, x.tur, x.id];
  natija.sort((a, b) => {
    const p = kal(a), q = kal(b);
    for (let i = 0; i < 3; i++) if (p[i] !== q[i]) return p[i] < q[i] ? 1 : -1;
    return 0;
  });
  return natija;
}

// hamyon.py:133
export async function _odam_bormi(db, odam_id) {
  const r = await db.q1("SELECT nom FROM odam WHERE id=? AND faol=1", odam_id ?? null);
  if (!r) throw new Error("Odam tanlanmagan.");
  return r.nom;
}

/** Python int(x or 0) — pul har doim butun son. */
function _butun(x) {
  const n = Number(x || 0);
  if (!Number.isFinite(n)) throw new Error("Summa noto'g'ri.");
  return Math.trunc(n);
}

// hamyon.py:140
/** Yangi karta; `qoldiq` naqddan kartaga o'tkazma bo'lib yoziladi. Bitta undo. */
export async function karta_qosh(db, odam_id, nom, qoldiq = 0, sana = null) {
  nom = String(nom || "").trim();
  if (!nom) throw new Error("Karta nomini yozing (masalan: Humo, Uzcard).");
  qoldiq = _butun(qoldiq);
  if (qoldiq < 0) throw new Error("Qoldiq manfiy bo'lmaydi.");
  const kim = await _odam_bormi(db, odam_id);
  if (await db.q1("SELECT 1 FROM karta WHERE odam_id=? AND ochirilgan=0" +
    " AND nom=? COLLATE NOCASE", odam_id, nom)) {
    throw new Error(`${kim}da «${nom}» degan karta bor.`);
  }
  const tartib = await db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM karta" +
    " WHERE odam_id=?", [odam_id]);
  const a = db.amal(`Karta qo'shildi: ${nom} (${kim})`);
  const kid = await a.apply("karta", "INSERT", { odam_id, nom, tartib });
  if (qoldiq) {
    await a.apply("karta_otkazma", "INSERT", {
      sana: sana || _vaqt.bugun(), odam_id,
      dan_karta_id: null, ga_karta_id: kid, summa: qoldiq,
      izoh: "Boshlang'ich qoldiq",
    });
  }
  await a.commit();
  return kid;
}

// hamyon.py:166
export async function karta_nomla(db, karta_id, nom) {
  nom = String(nom || "").trim();
  if (!nom) throw new Error("Karta nomini yozing.");
  const k = await db.q1("SELECT odam_id, nom FROM karta WHERE id=?", karta_id);
  if (!k) throw new Error("Karta topilmadi.");
  if (nom === k.nom) return;
  if (await db.q1("SELECT 1 FROM karta WHERE odam_id=? AND ochirilgan=0 AND id<>?" +
    " AND nom=? COLLATE NOCASE", k.odam_id, karta_id, nom)) {
    throw new Error(`«${nom}» degan karta bor.`);
  }
  const a = db.amal(`Karta nomi: ${k.nom} → ${nom}`);
  await a.apply("karta", "UPDATE", { nom }, karta_id);
  await a.commit();
}

// hamyon.py:182
/** O'chiriladi; qoldig'i naqdga qaytadi (yozuvlari joyida qoladi). */
export async function karta_ochir(db, karta_id) {
  const k = await db.q1("SELECT nom FROM karta WHERE id=? AND ochirilgan=0", karta_id);
  if (!k) throw new Error("Karta topilmadi.");
  const a = db.amal(`Karta o'chirildi: ${k.nom}`);
  await a.apply("karta", "DELETE", {}, karta_id);
  await a.commit();
}

// hamyon.py:191
/** Naqd ↔ karta yoki karta → karta (bitta odamning ichida). */
export async function otkazma(db, sana, odam_id, dan, ga, summa, izoh = null) {
  summa = _butun(summa);
  if (summa <= 0) throw new Error("Summa kiritilmagan.");
  dan = dan ?? null; ga = ga ?? null;
  if (dan === ga) throw new Error("Qayerdan va qayerga bir xil.");
  const kim = await _odam_bormi(db, odam_id);
  await tekshir_karta(db, dan, odam_id);
  await tekshir_karta(db, ga, odam_id);
  const a = db.amal(`O'tkazma (${kim}): ${await joy_nomi(db, dan)} → ` +
    `${await joy_nomi(db, ga)} ${_money.fmt(summa)}`);
  const id = await a.apply("karta_otkazma", "INSERT", {
    sana, odam_id, dan_karta_id: dan, ga_karta_id: ga, summa, izoh: izoh || null,
  });
  await a.commit();
  return id;
}

// hamyon.py:207
export async function otkazma_ochir(db, otkazma_id) {
  const a = db.amal("O'tkazma o'chirildi");
  await a.apply("karta_otkazma", "DELETE", {}, otkazma_id);
  await a.commit();
}

// hamyon.py:212
/** Bankdagi haqiqiy qoldiqqa tenglaydi: farq naqd bilan o'tkazma. Farq yo'q — null. */
export async function qoldiq_togirla(db, karta_id, haqiqiy, sana) {
  haqiqiy = _butun(haqiqiy);
  if (haqiqiy < 0) throw new Error("Qoldiq manfiy bo'lmaydi.");
  const k = await db.q1("SELECT odam_id FROM karta WHERE id=? AND ochirilgan=0", karta_id);
  if (!k) throw new Error("Karta topilmadi.");
  const farq = haqiqiy - ((await _qoldiqlar(db, k.odam_id)).get(karta_id) ?? 0);
  if (farq === 0) return null;
  if (farq > 0) return otkazma(db, sana, k.odam_id, null, karta_id, farq, "Qoldiq to'g'irlandi");
  return otkazma(db, sana, k.odam_id, karta_id, null, -farq, "Qoldiq to'g'irlandi");
}
