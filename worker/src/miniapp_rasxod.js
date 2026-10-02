// Telegram Mini App — «Yangi rasxod» oynasining API'si.
//
//   GET  /app/api/rasxod/forma  — oynaga kerak hamma narsa: odamlar (real
//                                 balansi va kartalari bilan), bugun uyda
//                                 bo'lganlar (umumiy bo'linadiganlar),
//                                 kategoriya daraxti (ikonka fayli bilan)
//   POST /app/api/rasxod        — {kimning, tur: umumiy|shaxsiy, kim_toladi,
//                                  karta_id, turi_id, summa, sabab} → {ok, id}
//
// Ruxsat (Telegram initData) va ochgan odam (`odam`) — miniapp.js da.
// Yozuv FAQAT `rasxod_kirit.js` orqali (Qoralama → tekshir → saqla) —
// desktop `RasxodDialog` va bot bilan BITTA mantiq.
//
// Real balans — desktopdagi «Shaxsiy» varag'idagi son bilan AYNAN bir xil:
// `v_balans.naqd − plan.band_ayirma()[odam]` (sahifa_qosh.py:127).

import * as rk from "./rasxod_kirit.js";
import * as plan from "./plan.js";
import * as hamyon from "./hamyon.js";
import * as mh from "./mahsulot.js";
import * as splitting from "./splitting.js";
import * as vaqt from "./vaqt.js";

/** `turi.rasm` (`food_03.png`) → Mini App'dagi SVG fayli (`food_03.svg`). */
export function belgi_fayli(rasm) {
  if (!rasm) return null;
  const m = /^([A-Za-z0-9_-]+)\.(png|svg)$/.exec(String(rasm).trim());
  return m ? `${m[1]}.svg` : null;
}

/** {odam_id: real balans} — «Shaxsiy» varag'idagi «Real balans». */
export async function real_balanslar(db) {
  const band = await plan.band_ayirma(db);
  const natija = new Map();
  for (const r of await db.q("SELECT id, naqd FROM v_balans")) {
    natija.set(r.id, Math.trunc(Number(r.naqd)) - (band.get(r.id) || 0));
  }
  return natija;
}

/** Kategoriya daraxti — `widgets.KategoriyaTanla` dagidek: ildizlar va
 *  har birining ichkilari (har chuqurlikda, tekis, `chuq` bilan). */
async function kategoriyalar(db) {
  const tugun = (t, chuq = 0) => ({ id: t.id, nom: t.nom, belgi: belgi_fayli(t.rasm), chuq });
  return (await mh.daraxt(db)).map((t) => {
    const ichki = [];
    const yur = (bolalar, chuq) => {
      for (const b of bolalar) { ichki.push(tugun(b, chuq)); yur(b.bolalar, chuq + 1); }
    };
    yur(t.bolalar, 0);
    return { ...tugun(t), ichki };
  });
}

export async function forma(db, odam) {
  const bugun = vaqt.bugun();
  const odamlar = await db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id");
  const balans = await real_balanslar(db);
  const royxat = [];
  for (const o of odamlar) {
    royxat.push({
      id: o.id, nom: o.nom, real_balans: balans.get(o.id) ?? 0,
      kartalar: (await hamyon.tanlov(db, o.id)).slice(1).map(([id, nom]) => ({ id, nom })),
    });
  }
  return {
    ok: true, men: odam.id, bugun,
    odamlar: royxat,
    // Umumiy rasxod kimlarga bo'linadi — `rk.qatnashchilar` (parametrlar=null).
    qatnashchilar: await splitting.qatnashchilar(db, bugun),
    kategoriyalar: await kategoriyalar(db),
  };
}

const butun = (x) => (x == null || x === "" ? null : Number.isInteger(Number(x)) ? Number(x) : NaN);

/** So'rov tanasidan Qoralama — desktop `RasxodDialog.qoralama()` qoidasi. */
export async function qoralama(db, b) {
  const kim_toladi = butun(b.kim_toladi);
  const kimning = butun(b.kimning);
  let tur;
  if (b.tur === "umumiy") tur = rk.UMUMIY;
  else if (b.tur === "shaxsiy") {
    if (kimning == null || Number.isNaN(kimning) ||
        !await db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", kimning)) {
      throw new Error("Kimning rasxodi ekanini tanlang.");
    }
    // Boshqa odam to'lasa — «uning uchun olingan» (CLAUDE.md «kim_uchun»).
    tur = kim_toladi === kimning ? rk.SHAXSIY : rk.UCHUN;
  } else throw new Error("Rasxod turi noma'lum.");
  const summa = Number(String(b.summa ?? "").replace(/[\s ]/g, ""));
  return new rk.Qoralama({
    sana: vaqt.bugun(),
    kim_toladi: Number.isNaN(kim_toladi) ? null : kim_toladi,
    karta_id: Number.isNaN(butun(b.karta_id)) ? -1 : butun(b.karta_id),
    turi_id: Number.isNaN(butun(b.turi_id)) ? null : butun(b.turi_id),
    nom: String(b.sabab ?? "").trim(),
    summa: Number.isInteger(summa) ? summa : 0,
    tur,
    kim_uchun: tur === rk.UCHUN ? kimning : null,
    parametrlar: null,           // umumiy — bugun uydagilarga teng
    manba: "miniapp",
  });
}

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

/** /app/api/rasxod* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, db, odam, yol) {
  try {
    if (req.method === "GET" && yol === "/app/api/rasxod/forma") return json(await forma(db, odam));
    if (req.method === "POST" && yol === "/app/api/rasxod") {
      let b;
      try { b = await req.json(); } catch { return json({ ok: false, xato: "JSON noto'g'ri" }, 400); }
      if (!b || typeof b !== "object") return json({ ok: false, xato: "JSON noto'g'ri" }, 400);
      const q = await qoralama(db, b);
      const id = await rk.saqla(db, q);
      return json({ ok: true, id });
    }
  } catch (e) {
    return json({ ok: false, xato: String(e?.message || e) }, 400);
  }
  return null;
}
