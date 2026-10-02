// Telegram Mini App — «Sozlamalar → Reja (budget)»: oylik reja boshqaruvi.
// Desktop «Analitika → Reja va fakt» paneli (sahifa_reja_fakt.py) bilan BITTA
// mantiq — hamma hisob va yozuv `plan.js` (Python `core/plan.py` egizagi) da.
//
//   GET  /app/api/reja?oy=YYYY-MM&doira=umumiy|shaxsiy
//        → reja va fakt (`plan.reja_va_fakt`, kategoriya qatorlari bilan),
//          o'tgan oyda reja bormi (ko'chirish uchun)
//   GET  /app/api/reja/limitlar?oy=        → «Umumiy reja va limitlar» oynasi
//   POST /app/api/reja/limitlar            {oy, umumiy, limitlar: {turi_id: summa}}
//        → `plan.reja_saqla` (FAQAT limit — reja yozuvlariga tegmaydi)
//   POST /app/api/reja/limit/ochir         {oy, turi_id} → shu oy limiti 0
//   GET  /app/api/reja/kategoriya?oy=&turi_id=&doira=
//        → toifa ichi: kunlar (`plan.kategoriya_kunlari`) va reja ro'yxatlari
//   GET  /app/api/reja/forma               → kategoriya daraxti va mahsulotlar
//   GET  /app/api/reja/yozuv/<id>          → bitta yozuv (tahrirlash uchun)
//   POST /app/api/reja/yozuv               {sana, turi_id, nom, summa, mahsulotlar, doira}
//   POST /app/api/reja/yozuv/<id>          (xuddi shu — tahrirlash)
//   POST /app/api/reja/yozuv/<id>/ochir
//   POST /app/api/reja/yozuv/<id>/nusxa    → keyingi kunga (`plan.reja_yozuv_nusxa`)
//   POST /app/api/reja/kochir              {oy} → o'tgan oy rejasini shu oyga
//
// Doira: «umumiy» — uyniki (`odam_id=None`), «shaxsiy» — OCHGAN odamning o'zi.
// Boshqa odamning shaxsiy rejasini ko'rish/tahrirlash yo'q (403).
// Ko'chirish faqat shu oyda HECH QANDAY reja bo'lmasa (aks holda yozuvlar
// ikki marta tushardi). «Aslida to'landi» (`reja_bajar`) — bu yerda YO'Q:
// u haqiqiy rasxod yozadi, Mini App'da hali port qilinmagan.

import * as plan from "./plan.js";
import * as mh from "./mahsulot.js";
import * as vaqt from "./vaqt.js";
import { reja_va_fakt } from "./miniapp_hisobot.js";
import { belgi_fayli } from "./miniapp_rasxod.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

const OY = /^\d{4}-(0[1-9]|1[0-2])$/;
/** Butun son (pul) — bo'sh → 0, aks holda NaN. */
const pul = (x) => {
  if (x == null || x === "") return 0;
  const n = Number(String(x).replace(/[\s  ]/g, ""));
  return Number.isInteger(n) ? n : NaN;
};
const idOl = (x) => {
  const n = Number(x);
  return Number.isInteger(n) && n > 0 ? n : null;
};

/** Doira matni → plan odam_id (null — umumiy). */
function doiraOl(s, odam) {
  if (s == null || s === "" || s === "umumiy") return { ok: true, odam_id: null };
  if (s === "shaxsiy") return { ok: true, odam_id: odam.id };
  return { ok: false };
}

/**
 * Shu oyning O'Z rejasi bormi: reja yozuvi, umumiy summa yoki shu oy uchun
 * limit. «Har oy» ('*') limiti hisobga olinmaydi — u har oyda bor va
 * ko'chirishni abadiy to'sib qo'yardi; yozuvlar esa ikki marta tushmasin.
 */
async function ozReja(db, oy) {
  if (await plan.oylik_reja(db, oy) != null) return true;
  if ((await plan.reja_yozuvlari(db, oy)).length) return true;
  return Boolean(await db.skalyar("SELECT COUNT(*) FROM budjet b JOIN turi t ON t.id=b.turi_id" +
    " WHERE t.ota_id IS NULL AND b.oy=? AND b.summa>0", [oy], 0));
}

/** Kategoriya qatoriga Mini App ikonkasi. */
const belgili = (q) => ({ ...q, belgi_fayl: belgi_fayli(q.rasm) });

export async function asosiy(db, oy, odam_id) {
  const rf = await reja_va_fakt(db, oy, odam_id);
  const otgan = plan.oy_sur(oy, -1);
  return {
    rf: { ...rf, qatorlar: rf.qatorlar.map(belgili), diqqat: rf.diqqat ? belgili(rf.diqqat) : null },
    otgan: { oy: otgan, bor: await plan.reja_bormi(db, otgan) },
    bu_oy_bor: await plan.reja_bormi(db, oy),
    kochir_mumkin: !(await ozReja(db, oy)) && await plan.reja_bormi(db, otgan),
  };
}

export async function limitlar(db, oy) {
  const otgan = plan.oy_sur(oy, -1);
  const yozuvlar = await plan.yozuv_reja(db, oy);
  return {
    umumiy: await plan.oylik_reja(db, oy),
    kategoriyalar: (await plan.reja_kategoriyalari(db, oy)).map(belgili),
    yozuv_jami: [...yozuvlar.values()].reduce((s, v) => s + v, 0),
    otgan: {
      oy: otgan, bor: await plan.reja_bormi(db, otgan),
      umumiy: await plan.oylik_reja(db, otgan),
      limitlar: Object.fromEntries(await plan.limit_reja(db, otgan)),
    },
  };
}

/** Yozuv — Mini App ko'rinishi (mahsulotlari bilan). */
function yozuvKor(y) {
  return {
    id: y.id, sana: y.sana, nom: y.nom, summa: y.summa, turi_id: y.turi_id,
    turi_nom: y.turi_nom ?? null, umumiymi: y.umumiymi ? 1 : 0, odam_id: y.odam_id, odam_nom: y.odam_nom ?? null,
    mahsulotlar: (y.mahsulotlar || []).map((m) => ({ item_id: m.item_id, nom: m.nom, miqdor: m.miqdor, summa: m.summa })),
  };
}

export async function kategoriya(db, oy, turi_id, odam_id) {
  const t = await db.q1("SELECT id, nom, rasm FROM turi WHERE id=? AND ota_id IS NULL", turi_id);
  if (!t) return null;
  const kk = await plan.kategoriya_kunlari(db, oy, turi_id, odam_id);
  return {
    turi: { id: t.id, nom: t.nom, belgi_fayl: belgi_fayli(t.rasm) },
    reja: kk.reja, fakt: kk.fakt, qolgan: kk.qolgan, limit: kk.limit,
    kunlar: kk.kunlar.map((k) => ({ ...k, holat: plan.kun_holati(k.reja, k.fakt) })),
    yozuvlar: (await plan.kategoriya_reja_yozuvlari(db, oy, turi_id, odam_id)).map(yozuvKor),
  };
}

export async function forma(db) {
  const tugun = (t) => ({ id: t.id, nom: t.nom, belgi_fayl: belgi_fayli(t.rasm) });
  const kategoriyalar = (await mh.daraxt(db)).map((t) => {
    const ichki = [];
    const yur = (bolalar, chuq) => {
      for (const b of bolalar) { ichki.push({ ...tugun(b), chuq }); yur(b.bolalar, chuq + 1); }
    };
    yur(t.bolalar, 0);
    return { ...tugun(t), ichki };
  });
  const mahsulotlar = (await db.q("SELECT id, nom, narx, turi_id FROM item" +
    " WHERE faol=1 AND ochirilgan=0 AND turi_id IS NOT NULL ORDER BY nom COLLATE NOCASE"))
    .map((m) => ({ id: m.id, nom: m.nom, narx: Math.trunc(Number(m.narx || 0)), turi_id: m.turi_id }));
  return { kategoriyalar, mahsulotlar };
}

/** Oylik rejaning yozuvi va ochgan odam unga tega oladimi. */
async function yozuvOl(db, id, odam) {
  const y = await db.q1("SELECT q.id, q.umumiymi, q.odam_id FROM reja_qator q" +
    " JOIN reja r ON r.id=q.reja_id WHERE q.id=? AND q.ochirilgan=0 AND r.tur='oylik'", id);
  if (!y) return [null, xato("Reja yozuvi topilmadi", 404)];
  if (!y.umumiymi && y.odam_id !== odam.id) return [null, xato("Bu reja sizniki emas", 403)];
  return [y, null];
}

/** Tanadan yozuv maydonlari — `plan.reja_yozuv_saqla` tekshiradi. */
function yozuvTana(b, odam) {
  const summa = pul(b.summa);
  if (Number.isNaN(summa)) throw new Error("Summa butun son bo'lsin.");
  if (b.doira !== "umumiy" && b.doira !== "shaxsiy") throw new Error("Reja umumiy yoki shaxsiy bo'lsin.");
  const sana = String(b.sana ?? "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sana)) throw new Error("Sana noto'g'ri.");
  const t = b.turi_id == null || b.turi_id === "" ? null : idOl(b.turi_id);
  if (b.turi_id != null && b.turi_id !== "" && t == null) throw new Error("Kategoriya tanlanmagan.");
  if (b.mahsulotlar != null && !Array.isArray(b.mahsulotlar)) throw new Error("Mahsulotlar ro'yxati noto'g'ri.");
  const mahsulotlar = (b.mahsulotlar || []).map((m, i) => {
    const s = pul(m && m.summa), q = pul(m && m.miqdor);
    if (Number.isNaN(s) || Number.isNaN(q)) throw new Error(`${i + 1}-mahsulot summasi yoki miqdori noto'g'ri.`);
    const iid = m && m.item_id != null && m.item_id !== "" ? idOl(m.item_id) : null;
    return { item_id: iid, nom: String((m && m.nom) ?? ""), miqdor: q || 1, summa: s };
  });
  return {
    sana, nom: String(b.nom ?? ""), turi_id: t, summa, mahsulotlar,
    umumiymi: b.doira === "umumiy", odam_id: b.doira === "shaxsiy" ? odam.id : null,
  };
}

/** /app/api/reja* — null qaytarsa marshrut topilmadi. */
export async function ishla(req, url, yol, db, odam) {
  const p = url.searchParams;
  try {
    if (req.method === "GET") {
      const oy = p.get("oy") || vaqt.bugun().slice(0, 7);
      if (!OY.test(oy)) return xato("Oy noto'g'ri");
      const d = doiraOl(p.get("doira"), odam);
      if (!d.ok) return xato("Doira noto'g'ri");
      const asos = { ok: true, bugun: vaqt.bugun(), oy, doira: d.odam_id == null ? "umumiy" : "shaxsiy",
        odam: { id: odam.id, nom: odam.nom } };
      if (yol === "/app/api/reja") return json({ ...asos, ...(await asosiy(db, oy, d.odam_id)) });
      if (yol === "/app/api/reja/limitlar") return json({ ...asos, ...(await limitlar(db, oy)) });
      if (yol === "/app/api/reja/forma") return json({ ...asos, ...(await forma(db)) });
      if (yol === "/app/api/reja/kategoriya") {
        const tid = idOl(p.get("turi_id"));
        if (tid == null) return xato("Kategoriya noto'g'ri");
        const r = await kategoriya(db, oy, tid, d.odam_id);
        return r ? json({ ...asos, ...r }) : xato("Kategoriya topilmadi", 404);
      }
      const m = yol.match(/^\/app\/api\/reja\/yozuv\/(\d+)$/);
      if (m) {
        const [, rad] = await yozuvOl(db, Number(m[1]), odam);
        if (rad) return rad;
        const y = await plan.reja_yozuv_toliq(db, Number(m[1]));
        const ildiz = y.turi_id == null ? null : await db.skalyar(
          "WITH RECURSIVE o(id, ota) AS (SELECT id, ota_id FROM turi WHERE id=?" +
          " UNION ALL SELECT t.id, t.ota_id FROM turi t JOIN o ON t.id=o.ota)" +
          " SELECT id FROM o WHERE ota IS NULL", [y.turi_id], null);
        return json({ ...asos, yozuv: { ...yozuvKor(y), ildiz } });
      }
      return null;
    }

    if (req.method !== "POST") return null;
    let b;
    try { b = await req.json(); } catch { return xato("JSON noto'g'ri"); }
    if (!b || typeof b !== "object" || Array.isArray(b)) return xato("JSON noto'g'ri");

    if (yol === "/app/api/reja/limitlar") {
      const oy = String(b.oy ?? "");
      if (!OY.test(oy)) return xato("Oy noto'g'ri");
      const umumiy = pul(b.umumiy);
      if (Number.isNaN(umumiy) || umumiy < 0) return xato("Umumiy reja butun musbat son bo'lsin.");
      const ruxsat = new Set((await plan.reja_kategoriyalari(db, oy)).map((k) => k.turi_id));
      const turlar = new Map();
      for (const [k, v] of Object.entries(b.limitlar && typeof b.limitlar === "object" ? b.limitlar : {})) {
        const tid = idOl(k), s = pul(v);
        if (tid == null || !ruxsat.has(tid)) return xato("Kategoriya topilmadi");
        if (Number.isNaN(s) || s < 0) return xato("Limit butun musbat son bo'lsin.");
        turlar.set(tid, s);
      }
      await plan.reja_saqla(db, oy, umumiy || null, turlar);
      return json({ ok: true });
    }

    if (yol === "/app/api/reja/limit/ochir") {
      const oy = String(b.oy ?? ""), tid = idOl(b.turi_id);
      if (!OY.test(oy)) return xato("Oy noto'g'ri");
      if (tid == null || !(await plan.limit_reja(db, oy)).get(tid)) return xato("Bu kategoriyada limit yo'q.");
      await plan.budjet_qoy(db, tid, oy, 0);
      return json({ ok: true });
    }

    if (yol === "/app/api/reja/kochir") {
      const oy = String(b.oy ?? "");
      if (!OY.test(oy)) return xato("Oy noto'g'ri");
      if (await ozReja(db, oy)) return xato("Bu oyda reja allaqachon bor.");
      if (!await plan.reja_kochir(db, plan.oy_sur(oy, -1), oy)) return xato("O'tgan oy uchun reja yo'q.");
      return json({ ok: true });
    }

    if (yol === "/app/api/reja/yozuv") {
      const t = yozuvTana(b, odam);
      const id = await plan.reja_yozuv_saqla(db, t.sana, t.nom, t.turi_id, t.summa, t.mahsulotlar, null,
        { umumiymi: t.umumiymi, odam_id: t.odam_id });
      return json({ ok: true, id });
    }

    const m = yol.match(/^\/app\/api\/reja\/yozuv\/(\d+)(?:\/(ochir|nusxa))?$/);
    if (m) {
      const id = Number(m[1]);
      const [, rad] = await yozuvOl(db, id, odam);
      if (rad) return rad;
      if (m[2] === "ochir") { await plan.reja_yozuv_ochir(db, id); return json({ ok: true }); }
      if (m[2] === "nusxa") return json({ ok: true, id: await plan.reja_yozuv_nusxa(db, id) });
      const t = yozuvTana(b, odam);
      await plan.reja_yozuv_saqla(db, t.sana, t.nom, t.turi_id, t.summa, t.mahsulotlar, id,
        { umumiymi: t.umumiymi, odam_id: t.odam_id });
      return json({ ok: true, id });
    }
    return null;
  } catch (e) {
    return xato(String(e?.message || e));
  }
}
