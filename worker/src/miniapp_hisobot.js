// Telegram Mini App — «Hisobotlar» sahifasi (doira → kategoriya → ichki → rasxodlar).
//
//   GET /app/api/hisobot?dan=&gacha=&doira=umumiy|<odam_id>
//        → xulosa (fakt, reja, foiz), doira bo'laklari, kategoriyalar jadvali
//   GET /app/api/hisobot/kategoriya?idlar=<id>[,<id>…]&dan=&gacha=&doira=
//        → bitta asosiy kategoriya (yoki «Qolganlari» guruhi) xulosasi,
//          ichki kategoriyalari va so'nggi 3 rasxod. `0` — «Kategoriyasiz».
//   GET /app/api/hisobot/rasxodlar?idlar=…|turi_id=<id>[&ozi=1]&dan=&gacha=&doira=
//        → rasxodlar kun bo'yicha guruhlangan (har kun jami bilan)
//
// Faqat O'QIYDI. Ruxsat (Telegram initData) va ochgan odam — miniapp.js da.
//
// DOIRA — desktop «Reja va fakt» (`plan.reja_va_fakt`) bilan AYNAN bir xil:
//   umumiy  → `ledger._manba(odam_id=None, qism='umumiy')`: umumiy rasxodlarning
//             BUTUN summasi («boshqa uchun» olingani kirmaydi); reja — umumiy
//             oylik summa (qo'yilgan bo'lsa), aks holda umumiy yozuvlar + limitlar.
//   <odam>  → `_manba(odam_id, 'shaxsiy')`: o'z shaxsiy rasxodi + boshqa odam
//             UNING UCHUN olgani (`kim_uchun`); reja — o'sha odamning shaxsiy
//             reja yozuvlari.
// Ichki kategoriya hamma joyda otasiga qo'shiladi (`turi.ota_id`, `_ILDIZ`).
// Ro'yxatlar doira bilan BITTA manbadan: qatorlar yig'indisi bo'lakka teng.
//
// DAVR REJASI (desktopda oraliq uchun reja yo'q — reja oylik): oraliq bitta
// oy ichida bo'lsa — o'sha oyning rejasi (1–14 sentabr → sentabr rejasi,
// desktop «Reja va fakt» kartasi bilan bir xil); bir necha oyni qamrasa —
// faqat oraliq to'liq oylardan iborat bo'lsa (1-kundan oxirgi kungacha)
// o'sha oylar rejalari yig'indisi, aks holda reja yo'q (null → «—»).
// Ichki kategoriya rejasi — shu ichki kategoriya (va avlodlari) ga yozilgan
// reja yozuvlari (limit faqat asosiy kategoriyada bo'ladi).

import * as money from "./money.js";
import * as ledger from "./ledger.js";
import * as plan from "./plan.js";
import * as vaqt from "./vaqt.js";
import { belgi_fayli } from "./miniapp_rasxod.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);
const n = (x) => Math.trunc(Number(x || 0));
const BOLAK = 90; // D1: bitta so'rovda ko'pi bilan 100 parametr

// money.py:38
/** `qism` `butun` ning necha foizi — butun son, yarmi yuqoriga; butun ≤ 0 → null. */
export function foiz(qism, butun) {
  if (!butun || butun <= 0) return null;
  return Math.floor((n(qism) * 200 + n(butun)) / (2 * n(butun)));
}

// plan.py:765
/** oshdi | yaqin | yaxshi | rejasiz */
export function _holat(reja, fakt) {
  if (!reja || reja <= 0) return "rejasiz";
  if (fakt > reja) return "oshdi";
  if (foiz(fakt, reja) >= plan_YAQIN_FOIZ) return "yaqin";
  return "yaxshi";
}
const plan_YAQIN_FOIZ = 80; // plan.py:244 YAQIN_FOIZ

// ledger.py:557
export const DOIRA_QADAM = 6;

// ledger.py:560
/** Doira bo'laklari: kategoriyalar katta → kichik, keyin «Qolganlari», «Kategoriyasiz». */
export async function doira_bolaklari(db, boshi, oxiri, korsat = DOIRA_QADAM, odam_id = null, qism = "hammasi") {
  const turlar = (await ledger.turi_boyicha(db, boshi, oxiri, odam_id, qism))
    .sort((a, b) => (b.summa - a.summa) || (a.nom < b.nom ? -1 : a.nom > b.nom ? 1 : 0));
  let nomli = turlar.filter((t) => t.turi_id != null)
    .map((t) => ({ ...t, tur: "turi", ichida: [], idlar: [t.turi_id] }));
  const nomsiz = turlar.filter((t) => t.turi_id == null)
    .map((t) => ({ ...t, tur: "kategoriyasiz", ichida: [], idlar: [null] }));
  korsat = Math.max(1, korsat);
  if (nomli.length > korsat) {
    const kichik = nomli.slice(korsat);
    nomli = [...nomli.slice(0, korsat), {
      turi_id: null, nom: "Qolganlari", belgi: "", rasm: null,
      summa: kichik.reduce((s, t) => s + t.summa, 0),
      soni: kichik.reduce((s, t) => s + t.soni, 0),
      tur: "qolgan",
      ichida: kichik.map((t) => `${t.belgi} ${t.nom}`.trim()),
      idlar: kichik.map((t) => t.turi_id),
    }];
  }
  const bolaklar = [...nomli, ...nomsiz];
  if (bolaklar.length) {
    for (const u of money.bol_tortli(1000, new Map(bolaklar.map((b, i) => [i, b.summa])))) {
      bolaklar[u.odam_id].ulush = u.summa;
    }
  }
  return bolaklar;
}

// ledger.py:605
/** HAMMA asosiy kategoriya (rasxodi 0 bo'lgan faollari ham), «Kategoriyasiz» oxirida. */
export async function kategoriya_jadvali(db, boshi, oxiri, odam_id = null, qism = "hammasi") {
  const fakt = new Map((await ledger.turi_boyicha(db, boshi, oxiri, odam_id, qism)).map((t) => [t.turi_id, t]));
  const natija = [];
  for (const r of await db.q("SELECT id, nom, belgi, rasm, faol FROM turi WHERE ota_id IS NULL ORDER BY tartib, id")) {
    const f = fakt.get(r.id);
    if (!r.faol && !f) continue;
    natija.push({ turi_id: r.id, nom: r.nom, belgi: r.belgi, rasm: r.rasm,
      summa: f ? f.summa : 0, soni: f ? f.soni : 0, ulush: 0 });
  }
  natija.sort((a, b) => b.summa - a.summa); // barqaror
  if (fakt.has(null)) {
    const f = fakt.get(null);
    natija.push({ turi_id: null, nom: "Kategoriyasiz", belgi: "", rasm: null,
      summa: f.summa, soni: f.soni, ulush: 0 });
  }
  const bor = new Map(natija.map((x, i) => [i, x.summa]).filter(([, s]) => s > 0));
  if (bor.size) for (const u of money.bol_tortli(1000, bor)) natija[u.odam_id].ulush = u.summa;
  return natija;
}

const _QATOR_SELECT =
  "SELECT r.id, r.sana, r.nom, r.izoh, m.qism, m.summa," +
  "       r.summa jami, r.umumiymi, r.kim_uchun," +
  "       COALESCE(t.nom, '') kategoriya," +
  "       COALESCE(o.nom, '?') kim_toladi," +
  "       ou.nom kim_uchun_nom" +
  " FROM m JOIN rasxod r ON r.id=m.id" +
  " LEFT JOIN ild ON ild.id=m.turi_id" +
  " LEFT JOIN turi t ON t.id=r.turi_id" +
  " LEFT JOIN odam o ON o.id=r.kim_toladi" +
  " LEFT JOIN odam ou ON ou.id=r.kim_uchun";

// ledger.py:497
/** Bo'lak ichi — har bir rasxod; yig'indisi `turi_boyicha` dagi songa AYNAN teng. */
export async function kategoriya_rasxodlari(db, turi_idlar, boshi, oxiri, odam_id = null, qism = "hammasi") {
  const [manba, args] = ledger._manba(boshi, oxiri, odam_id, qism);
  const idlar = turi_idlar.filter((i) => i != null);
  const shart = [];
  if (idlar.length) shart.push(`ild.ildiz IN (${idlar.map(() => "?").join(",")})`);
  if (turi_idlar.includes(null)) shart.push("ild.ildiz IS NULL");
  if (!shart.length) return [];
  return db.q(ledger._ILDIZ + ", m AS (" + manba + ") " + _QATOR_SELECT +
    " WHERE " + shart.join(" OR ") + " ORDER BY r.sana DESC, r.id DESC", ...args, ...idlar);
}

/**
 * Ichki kategoriya ichi — `kategoriya_rasxodlari` bilan bir xil qatorlar, lekin
 * filtr ildiz emas: `turi_id` va uning avlodlari (`ozi` — faqat `turi_id` ning o'zi).
 */
export async function ichki_rasxodlari(db, turi_id, ozi, boshi, oxiri, odam_id = null, qism = "hammasi") {
  const [manba, args] = ledger._manba(boshi, oxiri, odam_id, qism);
  const ost = ozi ? "SELECT ? id" :
    "WITH RECURSIVE o(id) AS (SELECT ? UNION ALL SELECT t.id FROM turi t JOIN o ON t.ota_id=o.id) SELECT id FROM o";
  return db.q(ledger._ILDIZ + ", m AS (" + manba + "), ost AS (" + ost + ") " + _QATOR_SELECT +
    " WHERE m.turi_id IN (SELECT id FROM ost) ORDER BY r.sana DESC, r.id DESC", ...args, turi_id);
}

/** Map<bevosita bola id | turi_id (o'zi), {summa, soni}> — asosiy kategoriya ichi bo'laklari. */
async function bolalar_boyicha(db, turi_id, boshi, oxiri, odam_id, qism) {
  const [manba, args] = ledger._manba(boshi, oxiri, odam_id, qism);
  const qator = await db.q(
    "WITH RECURSIVE b(id, bosh) AS (SELECT id, id FROM turi WHERE ota_id=?" +
    " UNION ALL SELECT t.id, b.bosh FROM turi t JOIN b ON t.ota_id=b.id), m AS (" + manba + ")" +
    " SELECT COALESCE(b.bosh, ?) k, SUM(m.summa) summa, COUNT(*) soni FROM m" +
    " LEFT JOIN b ON b.id=m.turi_id WHERE m.turi_id=? OR b.id IS NOT NULL GROUP BY k",
    turi_id, ...args, turi_id, turi_id);
  return new Map(qator.map((r) => [r.k, { summa: n(r.summa), soni: n(r.soni) }]));
}

// ── Reja ──────────────────────────────────────────────────────────────

// plan.py:776 — to'liq (kategoriya qatorlari bilan)
/** Bitta oy: reja, fakt va kategoriyalar — bitta DOIRADA (desktop bilan aynan). */
export async function reja_va_fakt(db, oy, odam_id = null) {
  const boshi = oy + "-01", oxiri = plan.oy_oxiri(boshi);
  const rejalar = await plan.turi_reja(db, oy, odam_id);
  const fakt = new Map((await ledger.turi_boyicha(db, boshi, oxiri, odam_id, odam_id ? "shaxsiy" : "umumiy"))
    .map((t) => [t.turi_id, n(t.summa)]));
  let qatorlar = [];
  for (const t of await db.q("SELECT id, nom, belgi, rasm, faol FROM turi WHERE ota_id IS NULL ORDER BY tartib, id")) {
    const r = rejalar.get(t.id) || 0, f = fakt.get(t.id) || 0;
    if (!r && !f) continue;
    qatorlar.push({ turi_id: t.id, nom: t.nom, belgi: t.belgi, rasm: t.rasm, reja: r, fakt: f });
  }
  const kalit = (q) => [q.reja ? 0 : 1, q.reja ? 0 : -q.fakt];
  qatorlar = qatorlar.map((q, i) => [q, i]).sort(([a, i], [b, j]) => {
    const [a1, a2] = kalit(a), [b1, b2] = kalit(b);
    return (a1 - b1) || (a2 - b2) || (i - j);
  }).map(([q]) => q);
  if (fakt.get(null)) {
    qatorlar.push({ turi_id: null, nom: "Kategoriyasiz", belgi: "", rasm: null, reja: 0, fakt: fakt.get(null) });
  }
  for (const q of qatorlar) {
    q.qolgan = q.reja - q.fakt;
    q.foiz = foiz(q.fakt, q.reja);
    q.holat = _holat(q.reja, q.fakt);
  }
  const umumiy = odam_id == null ? await plan.oylik_reja(db, oy) : null;
  const turi_jami = [...rejalar.values()].reduce((s, v) => s + v, 0);
  const reja = umumiy != null ? umumiy : turi_jami;
  const jami_fakt = [...fakt.values()].reduce((s, v) => s + v, 0);
  const oshgan = qatorlar.filter((q) => q.holat === "oshdi");
  const yaqin = qatorlar.filter((q) => q.holat === "yaqin");
  const diqqat = oshgan.length ? oshgan.reduce((a, q) => (q.qolgan < a.qolgan ? q : a))
    : yaqin.length ? yaqin.reduce((a, q) => (q.foiz > a.foiz ? q : a)) : null;
  return { oy, boshi, oxiri, odam_id,
    reja_bor: Boolean(umumiy) || rejalar.size > 0,
    umumiy_qoyilgan: umumiy != null,
    reja, fakt: jami_fakt, qolgan: reja - jami_fakt,
    foiz: foiz(jami_fakt, reja), holat: _holat(reja, jami_fakt),
    turi_reja_jami: turi_jami, qatorlar, diqqat };
}

/** Oraliq qaysi oylarni qamraydi va reja ma'nolimi (qoida fayl boshida). → oylar[] | null */
export function davr_oylari(dan, gacha) {
  const oylar = [];
  for (let oy = dan.slice(0, 7); oy <= gacha.slice(0, 7); oy = oy_sur(oy, 1)) oylar.push(oy);
  if (oylar.length === 1) return oylar;
  const toliq = dan.slice(8) === "01" && gacha === plan.oy_oxiri(gacha);
  return toliq ? oylar : null;
}

// plan.py:252
export function oy_sur(oy, qadam) {
  const y = Number(oy.slice(0, 4)), m = Number(oy.slice(5, 7)) - 1 + qadam;
  return `${String(y + Math.floor(m / 12)).padStart(4, "0")}-${String(((m % 12) + 12) % 12 + 1).padStart(2, "0")}`;
}

/** Davr rejasi: {jami: number|null, turi: Map<asosiy turi_id, reja>} (null — reja ma'nosiz/yo'q). */
export async function davr_rejasi(db, dan, gacha, odam_id) {
  const oylar = davr_oylari(dan, gacha);
  if (!oylar) return { jami: null, turi: new Map(), oylar: null };
  let jami = 0, bor = false;
  const turi = new Map();
  for (const oy of oylar) {
    const tr = await plan.turi_reja(db, oy, odam_id);
    const umumiy = odam_id == null ? await plan.oylik_reja(db, oy) : null;
    const tj = [...tr.values()].reduce((s, v) => s + v, 0);
    if (umumiy || tr.size) { bor = true; jami += umumiy != null ? umumiy : tj; }
    for (const [k, v] of tr) turi.set(k, (turi.get(k) || 0) + v);
  }
  return { jami: bor ? jami : null, turi, oylar };
}

/** Ichki kategoriya (va avlodlari; `ozi` — faqat o'zi) ga yozilgan reja yozuvlari, davr oylarida. */
async function ichki_reja(db, oylar, turi_id, ozi, odam_id) {
  if (!oylar) return null;
  const shart = odam_id == null ? " AND q.umumiymi=1" : " AND q.umumiymi=0 AND q.odam_id=?";
  const ost = ozi ? "SELECT ? id" :
    "WITH RECURSIVE o(id) AS (SELECT ? UNION ALL SELECT t.id FROM turi t JOIN o ON t.ota_id=o.id) SELECT id FROM o";
  const s = await db.skalyar(
    "SELECT COALESCE(SUM(q.summa),0) FROM reja_qator q JOIN reja r ON r.id=q.reja_id" +
    ` WHERE r.tur='oylik' AND r.boshi IN (${oylar.map(() => "?").join(",")}) AND q.ochirilgan=0` + shart +
    ` AND q.turi_id IN (${ost})`,
    [...oylar.map((o) => o + "-01"), ...(odam_id == null ? [] : [odam_id]), turi_id], 0);
  return n(s) || null;
}

const xulosa = (fakt, reja) => ({
  fakt, reja: reja || null, foiz: reja ? foiz(fakt, reja) : null, holat: _holat(reja || 0, fakt),
});

// ── Javoblar ──────────────────────────────────────────────────────────

/** "umumiy" | "<odam_id>" → {odam_id, qism} */
export function doira_ajrat(doira) {
  if (!doira || doira === "umumiy") return { odam_id: null, qism: "umumiy" };
  const id = Number(doira);
  if (!Number.isInteger(id) || id <= 0) return null;
  return { odam_id: id, qism: "shaxsiy" };
}

/** Bosh sahifa: xulosa, doira, jadval. */
export async function hisobot(db, dan, gacha, odam_id) {
  const qism = odam_id == null ? "umumiy" : "shaxsiy";
  const [bolaklar, jadval, rj] = [
    await doira_bolaklari(db, dan, gacha, DOIRA_QADAM, odam_id, qism),
    await kategoriya_jadvali(db, dan, gacha, odam_id, qism),
    await davr_rejasi(db, dan, gacha, odam_id)];
  const fakt = bolaklar.reduce((s, b) => s + n(b.summa), 0);
  return {
    xulosa: xulosa(fakt, rj.jami),
    bolaklar: bolaklar.map((b) => ({
      tur: b.tur, nom: b.nom, belgi: belgi_fayli(b.rasm), summa: n(b.summa), ulush: b.ulush,
      idlar: b.idlar.map((i) => (i == null ? 0 : i)),
    })),
    jadval: jadval
      .map((j) => ({ turi_id: j.turi_id == null ? 0 : j.turi_id, nom: j.nom, belgi: belgi_fayli(j.rasm),
        summa: n(j.summa), ulush: j.ulush, reja: rj.oylar ? (rj.turi.get(j.turi_id) || null) : null }))
      .filter((j) => j.summa > 0 || j.reja),
  };
}

async function turi_ol(db, id) {
  return db.q1("SELECT t.id, t.nom, t.rasm, t.ota_id, o.nom ota_nom, o.rasm ota_rasm FROM turi t" +
    " LEFT JOIN turi o ON o.id=t.ota_id WHERE t.id=?", id);
}

/** Kategoriya (yoki guruh) sahifasi: xulosa, ichki kategoriyalar, so'nggi 3 rasxod. */
export async function kategoriya(db, idlar, dan, gacha, odam_id) {
  const qism = odam_id == null ? "umumiy" : "shaxsiy";
  const rj = await davr_rejasi(db, dan, gacha, odam_id);
  const fakt_map = new Map((await ledger.turi_boyicha(db, dan, gacha, odam_id, qism)).map((t) => [t.turi_id, t]));
  const fakt = idlar.reduce((s, i) => s + n(fakt_map.get(i)?.summa), 0);
  const rejaOl = (i) => (i == null ? 0 : rj.turi.get(i) || 0);
  const reja = rj.oylar ? idlar.reduce((s, i) => s + rejaOl(i), 0) : null;
  let nom, belgi = null, ichki = [];

  if (idlar.length === 1 && idlar[0] != null) {
    const t = await turi_ol(db, idlar[0]);
    if (!t || t.ota_id != null) return null;
    nom = t.nom; belgi = belgi_fayli(t.rasm);
    const bolalar = await db.q("SELECT id, nom, rasm, faol FROM turi WHERE ota_id=? ORDER BY tartib, id", t.id);
    const bm = await bolalar_boyicha(db, t.id, dan, gacha, odam_id, qism);
    for (const b of bolalar) {
      const f = bm.get(b.id)?.summa || 0;
      const r = await ichki_reja(db, rj.oylar, b.id, false, odam_id);
      if (!f && !r) continue;
      ichki.push({ turi_id: b.id, ozi: false, nom: b.nom, belgi: belgi_fayli(b.rasm) || belgi, summa: f, reja: r });
    }
    ichki.sort((a, b) => b.summa - a.summa);
    const oz = bm.get(t.id)?.summa || 0;
    if (oz) {
      const band = bolalar.some((b) => b.nom.toLowerCase() === "boshqa");
      ichki.push({ turi_id: t.id, ozi: true, nom: band ? "— ichki kategoriyasiz —" : "Boshqa", belgi: null,
        summa: oz, reja: await ichki_reja(db, rj.oylar, t.id, true, odam_id) });
    }
  } else {
    // «Qolganlari» guruhi yoki «Kategoriyasiz» — ichida asosiy kategoriyalar
    nom = idlar.length === 1 ? "Kategoriyasiz" : "Qolganlari";
    if (idlar.length > 1) {
      for (const i of idlar) {
        const t = i == null ? null : await turi_ol(db, i);
        const f = n(fakt_map.get(i)?.summa);
        ichki.push({ idlar: [i == null ? 0 : i], nom: t ? t.nom : "Kategoriyasiz", belgi: t ? belgi_fayli(t.rasm) : null,
          summa: f, reja: rj.oylar ? rejaOl(i) || null : null });
      }
      ichki.sort((a, b) => b.summa - a.summa);
    }
  }
  const bor = new Map(ichki.map((x, i) => [i, x.summa]).filter(([, s]) => s > 0));
  for (const x of ichki) x.ulush = 0;
  if (bor.size) for (const u of money.bol_tortli(1000, bor)) ichki[u.odam_id].ulush = u.summa;

  const qatorlar = await kategoriya_rasxodlari(db, idlar, dan, gacha, odam_id, qism);
  return {
    nom, belgi, xulosa: xulosa(fakt, reja), ichki,
    soni: qatorlar.length,
    songgi: await boyit(db, qatorlar.slice(0, 3)),
  };
}

/** Rasxodlar ro'yxati — kun bo'yicha guruhlangan. */
export async function rasxodlar(db, { idlar = null, turi_id = null, ozi = false }, dan, gacha, odam_id) {
  const qism = odam_id == null ? "umumiy" : "shaxsiy";
  const rj = await davr_rejasi(db, dan, gacha, odam_id);
  let nom, belgi = null, qatorlar, reja;
  if (idlar) {
    qatorlar = await kategoriya_rasxodlari(db, idlar, dan, gacha, odam_id, qism);
    if (idlar.length === 1 && idlar[0] != null) {
      const t = await turi_ol(db, idlar[0]);
      if (!t) return null;
      nom = t.nom; belgi = belgi_fayli(t.rasm);
    } else nom = idlar.length === 1 ? "Kategoriyasiz" : "Qolganlari";
    reja = rj.oylar ? idlar.reduce((s, i) => s + (i == null ? 0 : rj.turi.get(i) || 0), 0) : null;
  } else {
    const t = await turi_ol(db, turi_id);
    if (!t) return null;
    qatorlar = await ichki_rasxodlari(db, turi_id, ozi, dan, gacha, odam_id, qism);
    nom = ozi ? `${t.nom} — boshqa` : t.nom;
    belgi = belgi_fayli(t.rasm) || belgi_fayli(t.ota_rasm);
    reja = t.ota_id == null && !ozi ? (rj.oylar ? rj.turi.get(t.id) || 0 : null)
      : await ichki_reja(db, rj.oylar, turi_id, ozi, odam_id);
  }
  const boyitilgan = await boyit(db, qatorlar);
  const kunlar = [];
  for (const q of boyitilgan) {
    let k = kunlar[kunlar.length - 1];
    if (!k || k.sana !== q.sana) kunlar.push(k = { sana: q.sana, jami: 0, qatorlar: [] });
    k.jami += q.summa;
    k.qatorlar.push(q);
  }
  const fakt = boyitilgan.reduce((s, q) => s + q.summa, 0);
  return { nom, belgi, xulosa: xulosa(fakt, reja), kunlar };
}

const parchala = (a) => { const r = []; for (let i = 0; i < a.length; i += BOLAK) r.push(a.slice(i, i + BOLAK)); return r; };

/** Rasxod qatorlariga vaqt, ikonka, kategoriya yo'li, mahsulotlar va tafsilot qo'shadi. */
async function boyit(db, qatorlar) {
  if (!qatorlar.length) return [];
  const idlar = qatorlar.map((q) => q.id);
  const qosh = new Map(), mahs = new Map(), ulush = new Map();
  for (const p of parchala(idlar)) {
    const ph = p.map(() => "?").join(",");
    for (const r of await db.q(
      "SELECT r.id, r.yaratilgan, r.turi_id, r.item_id, i.nom item_nom, k.nom karta_nom," +
      " t.nom t_nom, t.rasm t_rasm, ota.nom ota_nom, ota.rasm ota_rasm FROM rasxod r" +
      " LEFT JOIN turi t ON t.id=r.turi_id LEFT JOIN turi ota ON ota.id=t.ota_id" +
      " LEFT JOIN item i ON i.id=r.item_id LEFT JOIN karta k ON k.id=r.karta_id" +
      ` WHERE r.id IN (${ph})`, ...p)) qosh.set(r.id, r);
    for (const r of await db.q(
      "SELECT rasxod_id, nom, miqdor, summa FROM rasxod_mahsulot WHERE ochirilgan=0" +
      ` AND rasxod_id IN (${ph}) ORDER BY rasxod_id, tartib, id`, ...p)) {
      if (!mahs.has(r.rasxod_id)) mahs.set(r.rasxod_id, []);
      mahs.get(r.rasxod_id).push({ nom: r.nom, miqdor: n(r.miqdor), summa: n(r.summa) });
    }
    for (const r of await db.q(
      "SELECT u.rasxod_id, o.nom, u.summa FROM ulush u JOIN odam o ON o.id=u.odam_id" +
      ` WHERE u.summa<>0 AND u.rasxod_id IN (${ph}) ORDER BY u.rasxod_id, o.tartib, o.id`, ...p)) {
      if (!ulush.has(r.rasxod_id)) ulush.set(r.rasxod_id, []);
      ulush.get(r.rasxod_id).push({ nom: r.nom, summa: n(r.summa) });
    }
  }
  return qatorlar.map((q) => {
    const x = qosh.get(q.id) || {};
    const yol = x.ota_nom ? `${x.ota_nom} → ${x.t_nom}` : (x.t_nom || "Kategoriyasiz");
    const m = mahs.get(q.id) || [];
    return {
      id: q.id, sana: q.sana, vaqt: String(x.yaratilgan || "").slice(11, 16),
      nom: q.nom || (m.length === 1 ? m[0].nom : "") || x.item_nom || x.t_nom || "Rasxod",
      summa: n(q.summa), jami: n(q.jami),
      kategoriya: x.t_nom || "Kategoriyasiz", ichki: x.ota_nom ? x.t_nom : null, yol,
      belgi: belgi_fayli(x.t_rasm) || belgi_fayli(x.ota_rasm),
      // Mahsulot qatorlari faqat rasxod butunicha shu doirada bo'lsa (summa = jami)
      // alohida qator bo'ladi — aks holda kun jami rasxodlar yig'indisidan farq qilardi.
      mahsulotlar: m.length > 1 && n(q.summa) === n(q.jami) ? m : [],
      tafsilot: {
        izoh: q.izoh || "", kim_toladi: q.kim_toladi,
        doira: q.kim_uchun != null ? `${q.kim_uchun_nom} uchun` : q.umumiymi ? "Umumiy" : "Shaxsiy",
        joy: x.karta_nom || "Naqd",
        ulushlar: q.umumiymi && q.kim_uchun == null ? (ulush.get(q.id) || []) : [],
        mahsulotlar: m,
      },
    };
  });
}

// ── Marshrut ──────────────────────────────────────────────────────────

const SANA = /^\d{4}-\d{2}-\d{2}$/;

/** /app/api/hisobot* — null qaytarsa marshrut topilmadi. */
export async function ishla(req, url, yol, db, odam) {
  if (req.method !== "GET") return null;
  const p = url.searchParams;
  const bugun = vaqt.bugun();
  const dan = p.get("dan") || bugun.slice(0, 8) + "01";
  const gacha = p.get("gacha") || bugun;
  if (!SANA.test(dan) || !SANA.test(gacha) || dan > gacha) return xato("Sana noto'g'ri");
  if (vaqt.kunFarqi(dan, gacha) > 3700 || vaqt.kunFarqi(gacha, dan) > 3700) return xato("Oraliq juda katta");
  const d = doira_ajrat(p.get("doira"));
  if (!d) return xato("Doira noto'g'ri");
  const odamlar = await db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id");
  if (d.odam_id != null && !(await db.q1("SELECT id FROM odam WHERE id=?", d.odam_id))) return xato("Odam topilmadi", 404);
  const asos = { ok: true, bugun, dan, gacha, doira: d.odam_id == null ? "umumiy" : String(d.odam_id) };
  const idlarOl = () => {
    const s = p.get("idlar");
    if (!s || !/^\d+(,\d+)*$/.test(s)) return null;
    return [...new Set(s.split(",").map(Number))].map((i) => (i === 0 ? null : i));
  };

  if (yol === "/app/api/hisobot") {
    return json({ ...asos, odam: { id: odam.id, nom: odam.nom }, odamlar, ...(await hisobot(db, dan, gacha, d.odam_id)) });
  }
  if (yol === "/app/api/hisobot/kategoriya") {
    const idlar = idlarOl();
    if (!idlar) return xato("Kategoriya noto'g'ri");
    const r = await kategoriya(db, idlar, dan, gacha, d.odam_id);
    return r ? json({ ...asos, ...r }) : xato("Kategoriya topilmadi", 404);
  }
  if (yol === "/app/api/hisobot/rasxodlar") {
    const idlar = idlarOl();
    const tid = Number(p.get("turi_id"));
    if (!idlar && !(Number.isInteger(tid) && tid > 0)) return xato("Kategoriya noto'g'ri");
    const r = await rasxodlar(db, idlar ? { idlar } : { turi_id: tid, ozi: p.get("ozi") === "1" }, dan, gacha, d.odam_id);
    return r ? json({ ...asos, ...r }) : xato("Kategoriya topilmadi", 404);
  }
  return null;
}
