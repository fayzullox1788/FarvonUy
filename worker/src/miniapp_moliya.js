// Telegram Mini App — «Moliya» sahifasining API'si.
//
//   GET  /app/api/moliya?oy=YYYY-MM         — kartalar, oy xarajati (reja va fakt),
//                                             bugungi yozuvlar (ochgan odamniki)
//   POST /app/api/moliya/rasxod/<id>/ochir  — O'Z rasxodini o'chirish (yumshoq,
//                                             bitta undo — `entries.rasxod_ochir`,
//                                             botdagi `rx:del` bilan bitta yo'l)
//
// Ruxsat (Telegram initData) va ochgan odam (`odam`) — miniapp.js da.
//
// Moliya — FAQAT ochgan odamning o'z hisoboti (foydalanuvchi: «moliyada faqat
// o'zimni hisoboti bo'lsin»). Desktop manbalari bilan parity: test/miniapp_moliya.test.js.
// Kartalar:
//   Joriy balans  = qarz va rejalardan KEYIN qolgan pul:
//                   `v_balans.naqd − band_hisob()[odam].ayirildi − Qarzim`
//                   (Qarzim — pastdagi karta). Manfiy bo'lishi mumkin.
//   Rejaga band   = «Shaxsiy» varag'idagi «Rejaga band» kartasi:
//                   `plan.band_hisob()[odam].band + .qoplaydi` (sahifa_qosh.py:139).
//                   Har doim JORIY oy (band — joriy oy rejasining sarflanmagani).
//   Qarzim        = `plan.odam_qarzlari(odam).jami` — ichki + tashqi + rejadan qarz.
//   Oy xarajati   = ochgan odamning shu oydagi rasxodi — Analitika odam filtri
//                   «Shaxsiy + umumiy ulushi» (`ledger.turi_boyicha(odam, 'hammasi')`
//                   = `_odam_manba`: o'z shaxsiysi + uning uchun olingani + umumiy
//                   rasxoddagi ULUSHI, butun summasi EMAS).
//                   Reja = shaxsiy rejasi (`reja_va_fakt(oy, odam).reja`) + umumiy rejaning
//                   TENG ulushi (`money.bol_teng` faol odamlarga — `band_pul` bilan bir
//                   xil bo'lish). Ikkalasi ham yo'q → `reja_bor=false`. Foiz `money.foiz`
//                   (100 dan oshadi), reja ≤ 0 → null.
//
// «Bugun» — Toshkent bugungi kuni (`vaqt.bugun()`), ochgan odamga TEGADIGAN yozuvlar:
//   rasxod       sana=bugun, o'chirilmagan; summa — UNING ULUSHI (`_odam_manba` qoidasi):
//                umumiy → ulushi, «uning uchun» → ulushi (butuni), shaxsiysi → butuni.
//                Ulushi 0 bo'lsa (faqat boshqaga to'lagan) — chiqmaydi. Nomi — kategoriya
//                (yo'q bo'lsa sabab); tafsilotda butun chek, ulushlar, «Sizning ulushingiz».
//   reja         `plan.kun_reja_yozuvlari(bugun)` dan umumiy + O'ZINING shaxsiysi. Umumiysi —
//                TENG ulushi (`bol_teng` faol odamlarga), shaxsiysi — butun; 0 → chiqmaydi.
//   qarz         uy ichidagi qarz (`qarz`), u bergan yoki olgan.
//   hisob-kitob  qarz to'lovi (`hisob_kitob`), u to'lagan yoki unga to'langan.
//   tashqi qarz  `tashqi_qarz` — shaxsiysi (u olgan) butun summa, umumiysi — UNING
//                ulushi (`tashqi_ulush`, tolov_id NULL), 0 bo'lsa chiqmaydi.
//   tashqi to'lov `tashqi_tolov` — shaxsiy qarzniki butun summa, umumiyniki — uning ulushi.
// Ikonka (`rasm` — belgilar/<kalit>.svg, `emoji`) — desktop kategoriya ikonkasi:
//   kategoriya va otalari zanjirida birinchi `turi.rasm`; yo'q bo'lsa birinchi `turi.belgi`
//   (eski kategoriyalar emojisi, mas. «Sneklar» 🍿); u ham yo'q bo'lsa neytral `BOSH_RASM[tur]`.
//   Qarzda kategoriya yo'q — `BOSH_RASM.qarz` (finance_03, pul).
// Vaqt — `yaratilgan` (reja_qator'da ustun yo'q — jurnaldagi INSERT vaqti).
// Tartib — vaqt bo'yicha yangisi tepada, vaqtsizlari oxirida.

import * as plan from "./plan.js";
import * as ledger from "./ledger.js";
import * as entries from "./entries.js";
import * as vaqt from "./vaqt.js";
import * as money from "./money.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);
const n = (x) => Math.trunc(Number(x || 0));

// money.py:38
/** `qism` `butun` ning necha foizi — butun son, yarmi yuqoriga; butun ≤ 0 → null. */
export function foiz(qism, butun) {
  if (!butun || butun <= 0) return null;
  return Math.floor((n(qism) * 200 + n(butun)) / (2 * n(butun)));
}

// plan.py:252
/** '2026-09' + 1 → '2026-10'. */
export function oy_sur(oy, qadam) {
  const y = Number(oy.slice(0, 4)), m = Number(oy.slice(5, 7)) - 1 + qadam;
  return `${String(y + Math.floor(m / 12)).padStart(4, "0")}-${String(((m % 12) + 12) % 12 + 1).padStart(2, "0")}`;
}

// ledger.py:134
/** Bitta odamning qarzlari — «Qarzim». */
export async function ledger_odam_qarzlari(db, odam_id) {
  const juftlar = await ledger.juft_qarzlar(db);
  const ichki = juftlar.filter((j) => j.qarzdor_id === odam_id);
  const menga = juftlar.filter((j) => j.kreditor_id === odam_id);
  const tashqi = [];
  for (const t of await ledger.tashqi_qarzlar(db, true)) {
    t.jami_qoldiq = t.qoldiq;
    if (t.umumiy) {
      t.qoldiq = await db.skalyar(
        "SELECT SUM(CASE WHEN u.tolov_id IS NULL THEN u.summa" +
        "            ELSE -u.summa END) FROM tashqi_ulush u" +
        " LEFT JOIN tashqi_tolov p ON p.id=u.tolov_id" +
        " WHERE u.qarz_id=? AND u.odam_id=? AND u.ochirilgan=0" +
        "   AND (u.tolov_id IS NULL OR p.ochirilgan=0)", [t.id, odam_id], 0);
      if (t.qoldiq > 0) tashqi.push(t);
    } else if (t.odam_id === odam_id) {
      tashqi.push(t);
    }
  }
  const ichki_jami = ichki.reduce((s, j) => s + j.summa, 0);
  const tashqi_jami = tashqi.reduce((s, t) => s + n(t.qoldiq), 0);
  return { ichki, menga, tashqi, ichki_jami, tashqi_jami,
    menga_jami: menga.reduce((s, j) => s + j.summa, 0),
    jami: ichki_jami + tashqi_jami };
}

// plan.py:920
/** `ledger.odam_qarzlari` + rejaga band puldan hisobida yo'q qismi. */
export async function odam_qarzlari(db, odam_id) {
  const q = await ledger_odam_qarzlari(db, odam_id);
  const bh = await plan.band_hisob(db);
  const r = bh.get(odam_id)?.qarz || 0;
  q.reja_jami = r;
  q.jami += r;
  return q;
}

/** Uchta karta — desktop qoidasi (yuqoridagi izohga qarang). */
export async function kartalar(db, odam_id) {
  const naqd = n(await db.skalyar("SELECT naqd FROM v_balans WHERE id=?", [odam_id], 0));
  const bh = (await plan.band_hisob(db)).get(odam_id);
  const band = bh ? bh.band + bh.qoplaydi : 0;
  const qarzim = (await odam_qarzlari(db, odam_id)).jami;
  const balans = naqd - (bh ? bh.ayirildi : 0) - qarzim;
  return { balans, band, qarzim };
}

const faol_idlar = async (db) =>
  (await db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib, id")).map((r) => r.id);

/** `summa` dan `odam_id` ga tegadigan TENG ulush (faol odamlarga — `band_pul` kabi). */
export function teng_ulush(summa, idlar, odam_id) {
  if (!summa || !idlar.includes(odam_id)) return 0;
  return money.bol_teng(summa, idlar).find((u) => u.odam_id === odam_id)?.summa || 0;
}

/** Oy xarajati kartasi — ochgan odamniki (qoida fayl boshida). */
export async function oy_xarajati(db, oy, odam_id) {
  const boshi = oy + "-01", oxiri = plan.oy_oxiri(boshi);
  const fakt = (await ledger.turi_boyicha(db, boshi, oxiri, odam_id, "hammasi"))
    .reduce((s, t) => s + n(t.summa), 0);
  const umumiy = await plan.reja_va_fakt(db, oy);
  const shaxsiy = await plan.reja_va_fakt(db, oy, odam_id);
  const reja_bor = umumiy.reja_bor || shaxsiy.reja_bor;
  const reja = (shaxsiy.reja_bor ? n(shaxsiy.reja) : 0) +
    (umumiy.reja_bor ? teng_ulush(n(umumiy.reja), await faol_idlar(db), odam_id) : 0);
  return { oy, reja_bor, reja: reja_bor ? reja : null, fakt,
    foiz: reja_bor ? foiz(fakt, reja) : null };
}

// ── Ikonka ───────────────────────────────────────────────────────────

/** Kategoriya ikonkasi topilmasa — neytral (desktop belgilar to'plamidan). */
export const BOSH_RASM = { rasxod: "others_04", reja: "others_11", qarz: "finance_03" };

/** (turi_id, tur) → {rasm, emoji} hal qiluvchi (qoida fayl boshida). */
export async function ikonka_hal(db) {
  const turi = new Map((await db.q("SELECT id, ota_id, rasm, belgi FROM turi")).map((t) => [t.id, t]));
  return (turi_id, tur) => {
    const zanjir = [];
    for (let id = turi_id; id != null && turi.has(id) && zanjir.length < 32; id = turi.get(id).ota_id) {
      zanjir.push(turi.get(id));
    }
    for (const t of zanjir) {
      const r = rasm_kaliti(t.rasm);
      if (r) return { rasm: r, emoji: null };
    }
    for (const t of zanjir) {
      const b = String(t.belgi || "").trim();
      if (b) return { rasm: null, emoji: b };
    }
    return { rasm: BOSH_RASM[tur] || null, emoji: null };
  };
}

// ── «Bugun» ──────────────────────────────────────────────────────────

/** O'zbekcha jo'nalish qo'shimchasi: Otabek → Otabekka, Aziz aka → Aziz akaga. */
export function ga(nom) {
  const s = String(nom || "").trim();
  const oxir = s.slice(-1).toLowerCase();
  return s + (oxir === "k" ? "ka" : oxir === "q" ? "qa" : "ga");
}
const dan = (nom) => `${String(nom || "").trim()}dan`;
const soat = (v) => (v && v.length >= 16 ? v.slice(11, 16) : null);

/** `turi.rasm` (`food_03.png`) → `food_03` (Mini App `belgilar/food_03.svg`). */
export function rasm_kaliti(rasm) {
  const m = /^([A-Za-z0-9_-]+)\.(png|svg)$/.exec(String(rasm || "").trim());
  return m ? m[1] : null;
}

/** Ochgan odamning bugungi yozuvlari — qoida fayl boshida. */
export async function bugungi_yozuvlar(db, odam_id, sana = vaqt.bugun()) {
  const q = [];

  const rasxodlar = await db.q(
    "SELECT r.*, t.nom turi_nom, k.nom karta_nom," +
    " o.nom toladi_nom, ou.nom uchun_nom FROM rasxod r" +
    " JOIN odam o ON o.id=r.kim_toladi" +
    " LEFT JOIN odam ou ON ou.id=r.kim_uchun" +
    " LEFT JOIN turi t ON t.id=r.turi_id" +
    " LEFT JOIN karta k ON k.id=r.karta_id" +
    " WHERE r.ochirilgan=0 AND r.sana=? AND (r.kim_toladi=? OR EXISTS(" +
    "  SELECT 1 FROM ulush u WHERE u.rasxod_id=r.id AND u.odam_id=? AND u.summa<>0))",
    sana, odam_id, odam_id);
  const ikonka = await ikonka_hal(db);
  for (const r of rasxodlar) {
    const ulushlar = r.umumiymi ? await db.q(
      "SELECT u.odam_id, o.nom, u.summa FROM ulush u JOIN odam o ON o.id=u.odam_id" +
      " WHERE u.rasxod_id=? AND u.summa<>0 ORDER BY o.tartib, o.id", r.id) : [];
    const ozi = ulushlar.find((u) => u.odam_id === odam_id);
    const ulushim = r.umumiymi ? (ozi ? n(ozi.summa) : 0) : n(r.summa);
    if (!ulushim) continue; // faqat boshqa odam uchun to'lagan — uning hisobotiga kirmaydi
    q.push({
      tur: "rasxod", id: r.id, nom: r.turi_nom || r.nom || "Rasxod", belgi: "Xarajat",
      ishora: "-", rang: "qizil", summa: ulushim, ...ikonka(r.turi_id, "rasxod"),
      yaratilgan: r.yaratilgan, ozimi: r.kim_toladi === odam_id,
      tafsilot: {
        sabab: r.nom || "", kategoriya: r.turi_nom || null, sana: r.sana,
        kim_toladi: r.toladi_nom,
        doira: r.kim_uchun != null ? `${r.uchun_nom} uchun` : r.umumiymi ? "Umumiy" : "Shaxsiy",
        joy: r.karta_nom || "Naqd",
        ulushlar: ulushlar.map((u) => ({ nom: u.nom, summa: n(u.summa) })),
        jami: n(r.summa), mening_ulushim: ulushim,
      },
    });
  }

  // plan.kun_reja_yozuvlari(sana) — faqat umumiy va o'zining shaxsiysi.
  const rejalar = await db.q(
    "SELECT q.*, t.nom turi_nom, o.nom odam_nom," +
    " (SELECT MIN(z.vaqt) FROM ozgarishlar z WHERE z.jadval='reja_qator'" +
    "  AND z.qator_id=q.id AND z.amal='INSERT') yaratilgan" +
    " FROM reja_qator q JOIN reja r ON r.id=q.reja_id" +
    " LEFT JOIN turi t ON t.id=q.turi_id LEFT JOIN odam o ON o.id=q.odam_id" +
    " WHERE r.tur='oylik' AND q.ochirilgan=0 AND q.sana=?" +
    " AND (q.umumiymi=1 OR q.odam_id=?) ORDER BY q.umumiymi DESC, q.id", sana, odam_id);
  const idlar = rejalar.some((y) => y.umumiymi) ? await faol_idlar(db) : [];
  for (const y of rejalar) {
    const ulushim = y.umumiymi ? teng_ulush(n(y.summa), idlar, odam_id) : n(y.summa);
    if (!ulushim) continue;
    q.push({
      tur: "reja", id: y.id, nom: `${y.nom || y.turi_nom || "Reja"} (reja)`, belgi: "Reja",
      ishora: "-", rang: "navy", summa: ulushim, ...ikonka(y.turi_id, "reja"),
      yaratilgan: y.yaratilgan, ozimi: false,
      tafsilot: { sabab: y.nom || "", kategoriya: y.turi_nom || null, sana: y.sana,
        doira: y.umumiymi ? "Umumiy reja" : `${y.odam_nom} — shaxsiy reja`,
        jami: n(y.summa), mening_ulushim: ulushim,
        tolangan: y.tolangan == null ? null : n(y.tolangan) },
    });
  }

  const qarz = (o) => q.push({ belgi: "Qarz", rasm: BOSH_RASM.qarz, emoji: null, ozimi: false, ...o });

  for (const r of await db.q(
    "SELECT q.*, a.nom berdi_nom, b.nom olgan_nom FROM qarz q" +
    " JOIN odam a ON a.id=q.kim_berdi JOIN odam b ON b.id=q.kimga" +
    " WHERE q.ochirilgan=0 AND q.sana=? AND (q.kim_berdi=? OR q.kimga=?)", sana, odam_id, odam_id)) {
    const oldim = r.kimga === odam_id;
    qarz({ tur: "qarz", id: r.id, summa: n(r.summa), yaratilgan: r.yaratilgan,
      nom: oldim ? `${dan(r.berdi_nom)} qarz` : `${ga(r.olgan_nom)} qarz`,
      ishora: oldim ? "+" : "-", rang: oldim ? "yashil" : "navy",
      tafsilot: { sabab: r.sabab || "", sana: r.sana, kim_berdi: r.berdi_nom, kimga: r.olgan_nom } });
  }

  for (const r of await db.q(
    "SELECT h.*, a.nom toladi_nom, b.nom olgan_nom FROM hisob_kitob h" +
    " JOIN odam a ON a.id=h.kim_toladi JOIN odam b ON b.id=h.kimga" +
    " WHERE h.ochirilgan=0 AND h.sana=? AND (h.kim_toladi=? OR h.kimga=?)", sana, odam_id, odam_id)) {
    const oldim = r.kimga === odam_id;
    qarz({ tur: "hisob_kitob", id: r.id, summa: n(r.summa), yaratilgan: r.yaratilgan,
      nom: oldim ? `${dan(r.toladi_nom)} qarz qaytdi` : `${ga(r.olgan_nom)} qarz to‘landi`,
      ishora: oldim ? "+" : "-", rang: oldim ? "yashil" : "navy",
      tafsilot: { sabab: r.izoh || "", sana: r.sana, kim_toladi: r.toladi_nom, kimga: r.olgan_nom } });
  }

  for (const r of await db.q(
    "SELECT q.*, o.nom olgan_nom," +
    " (SELECT SUM(u.summa) FROM tashqi_ulush u WHERE u.qarz_id=q.id AND u.tolov_id IS NULL" +
    "  AND u.odam_id=? AND u.ochirilgan=0) ulushim" +
    " FROM tashqi_qarz q JOIN odam o ON o.id=q.odam_id" +
    " WHERE q.ochirilgan=0 AND q.sana=? AND (q.odam_id=? OR q.umumiy=1)", odam_id, sana, odam_id)) {
    const summa = r.umumiy ? n(r.ulushim) : n(r.summa);
    if (!summa) continue;
    qarz({ tur: "tashqi_qarz", id: r.id, summa, yaratilgan: r.yaratilgan,
      nom: `${dan(r.kimdan)} qarz`, ishora: "+", rang: "yashil",
      tafsilot: { sabab: r.sabab || "", sana: r.sana, kimdan: r.kimdan, kim_oldi: r.olgan_nom,
        doira: r.umumiy ? "Umumiy qarz" : "Shaxsiy qarz", jami: n(r.summa) } });
  }

  for (const r of await db.q(
    "SELECT t.*, q.kimdan, q.umumiy, q.odam_id qarz_odam, q.summa qarz_summa," +
    " (SELECT SUM(u.summa) FROM tashqi_ulush u WHERE u.tolov_id=t.id" +
    "  AND u.odam_id=? AND u.ochirilgan=0) ulushim" +
    " FROM tashqi_tolov t JOIN tashqi_qarz q ON q.id=t.tashqi_qarz_id" +
    " WHERE t.ochirilgan=0 AND q.ochirilgan=0 AND t.sana=? AND (q.odam_id=? OR q.umumiy=1)",
    odam_id, sana, odam_id)) {
    const summa = r.umumiy ? n(r.ulushim) : n(r.summa);
    if (!summa) continue;
    qarz({ tur: "tashqi_tolov", id: r.id, summa, yaratilgan: r.yaratilgan,
      nom: `${ga(r.kimdan)} qarz qaytarildi`, ishora: "-", rang: "navy",
      tafsilot: { sabab: r.izoh || "", sana: r.sana, kimga: r.kimdan,
        doira: r.umumiy ? "Umumiy qarz" : "Shaxsiy qarz", jami: n(r.summa) } });
  }

  // Yangisi tepada; vaqtsizlari oxirida; teng bo'lsa — keyin yozilgani (id) tepada.
  q.sort((a, b) => {
    if (!a.yaratilgan !== !b.yaratilgan) return a.yaratilgan ? -1 : 1;
    if (a.yaratilgan !== b.yaratilgan) return a.yaratilgan < b.yaratilgan ? 1 : -1;
    return b.id - a.id;
  });
  for (const x of q) {
    x.vaqt = soat(x.yaratilgan);
    x.kalit = `${x.tur}:${x.id}`;
    x.tafsilot.vaqt = x.vaqt;
    delete x.yaratilgan;
  }
  return q;
}

/** GET javobi. */
export async function moliya(db, odam, oy) {
  const bugun = vaqt.bugun();
  const joriy = bugun.slice(0, 7);
  const [k, x, yozuvlar] = [await kartalar(db, odam.id), await oy_xarajati(db, oy || joriy, odam.id),
    await bugungi_yozuvlar(db, odam.id, bugun)];
  return { ok: true, odam: odam.nom, bugun, joriy_oy: joriy, otgan_oy: oy_sur(joriy, -1),
    kartalar: k, xarajat: x, yozuvlar };
}

/** /app/api/moliya* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam) {
  if (yol === "/app/api/moliya") {
    if (req.method !== "GET") return xato("Topilmadi", 404);
    const oy = url.searchParams.get("oy");
    if (oy && !/^\d{4}-(0[1-9]|1[0-2])$/.test(oy)) return xato("Oy noto'g'ri");
    return json(await moliya(db, odam, oy));
  }
  const m = yol.match(/^\/app\/api\/moliya\/rasxod\/(\d+)\/ochir$/);
  if (!m) return yol.startsWith("/app/api/moliya/") ? xato("Topilmadi", 404) : null;
  if (req.method !== "POST") return xato("Topilmadi", 404);
  const r = await db.q1("SELECT id, kim_toladi, ochirilgan FROM rasxod WHERE id=?", Number(m[1]));
  if (!r || r.ochirilgan) return xato("Rasxod topilmadi", 404);
  if (r.kim_toladi !== odam.id) return xato("Bu rasxodni faqat to‘lagan odam o‘chira oladi", 403);
  try {
    await entries.rasxod_ochir(db, r.id);
  } catch (e) {
    return xato(String(e?.message || e));
  }
  return json({ ok: true });
}
