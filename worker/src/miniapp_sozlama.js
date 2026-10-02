// Telegram Mini App — «Sozlamalar → Kategoriyalar» API'si.
//
//   GET  /app/api/kategoriya                  — faol kategoriyalar daraxti + bo'sh ikonkalar
//   GET  /app/api/kategoriya/belgilar?ota=&ozi= — tanlasa bo'ladigan ikonkalar, guruhlar, taklif
//   POST /app/api/kategoriya                  — {nom, ota_id?, rasm?}  (`mh.kategoriya_qosh`)
//   POST /app/api/kategoriya/<id>             — {nom?, rasm?}          (`mh.kategoriya_tahrirla`)
//   POST /app/api/kategoriya/<id>/ochir       — yumshoq (`mh.kategoriya_ochir`, faol=0)
//
// Har yozuvdan keyin javobda yangi `daraxt` va `bosh` qaytadi (qayta so'rov shart emas).
// Qoidalar desktopniki (core/mahsulot.py): ichki kategoriyaga bo'sh ikonka majburiy,
// bitta ikonka — bitta faol kategoriya, ichida faol ichki kategoriya yoki mahsulot
// bo'lsa o'chmaydi (hech qachon zanjir bo'lib o'chmaydi), o'chirilgan nom qayta
// qo'shilsa eski qator tiriladi. Uyning har a'zosi boshqara oladi (desktop kabi).
// Xato — 400 {ok:false, xato: core funksiyasining o'zbekcha matni}.

import * as mh from "./mahsulot.js";
import * as kat from "./kategoriya.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

/** Daraxt (mh.daraxt tartibida) + har tugunda to'g'ridan-to'g'ri mahsulotlar soni. */
export async function royxat(db) {
  const [ildiz, soni, bosh] = await Promise.all([
    mh.daraxt(db),
    db.q("SELECT turi_id, COUNT(*) n FROM item WHERE ochirilgan=0 AND turi_id IS NOT NULL GROUP BY turi_id"),
    mh.bosh_belgilar(db),
  ]);
  const m = new Map(soni.map((r) => [r.turi_id, r.n]));
  const tugun = (t) => ({
    id: t.id, nom: t.nom, rasm: t.rasm || null, ota_id: t.ota_id ?? null,
    mahsulot: m.get(t.id) || 0, bolalar: t.bolalar.map(tugun),
  });
  return { daraxt: ildiz.map(tugun), bosh };
}

// Taklif: ichki kategoriya uchun — otasining ikonka guruhidan, keyin qo'shni
// guruhlardan; katta kategoriya uchun — har guruhdan bittadan (navbat bilan).
// Faqat UI tartibi; tanlash qoidasi — `bosh`. Klient (app/sozlama.js) ham shuni qiladi.
export const GURUH_TARTIB = ["food", "life", "transportation", "shopping", "health", "education",
  "entertainment", "personal", "finance", "sports", "travel", "office", "others"];
export const QOSHNI = {
  food: ["shopping", "life", "health"],
  life: ["shopping", "personal", "food"],
  transportation: ["travel", "finance", "life"],
  shopping: ["life", "food", "personal"],
  health: ["personal", "sports", "food"],
  education: ["office", "others", "entertainment"],
  entertainment: ["sports", "travel", "personal"],
  personal: ["life", "health", "shopping"],
  finance: ["office", "shopping", "others"],
  sports: ["health", "entertainment", "travel"],
  travel: ["transportation", "entertainment", "sports"],
  office: ["education", "finance", "others"],
  others: ["life", "office", "personal"],
};

export function taklif(bosh, otaRasm = null, n = null) {
  const guruhlar = new Map(GURUH_TARTIB.map((g) => [g, []]));
  for (const f of bosh) {
    const g = kat.guruh(f);
    if (!guruhlar.has(g)) guruhlar.set(g, []);
    guruhlar.get(g).push(f);
  }
  if (otaRasm) {
    const g = kat.guruh(otaRasm);
    const tartib = [...new Set([g, ...(QOSHNI[g] || []), ...guruhlar.keys()])];
    return tartib.flatMap((x) => guruhlar.get(x) || []).slice(0, n ?? 10);
  }
  const navbat = [...guruhlar.values()], natija = [];
  for (let i = 0; navbat.some((q) => q.length > i); i++) {
    for (const q of navbat) if (q[i]) natija.push(q[i]);
  }
  return natija.slice(0, n ?? 16);
}

/** /app/api/kategoriya* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam) {
  if (!(yol === "/app/api/kategoriya" || yol.startsWith("/app/api/kategoriya/"))) return null;
  try {
    if (req.method === "GET") {
      if (yol === "/app/api/kategoriya") return json({ ok: true, ...(await royxat(db)) });
      if (yol === "/app/api/kategoriya/belgilar") {
        const son = (k) => (/^\d+$/.test(url.searchParams.get(k) || "") ? Number(url.searchParams.get(k)) : null);
        const ota = son("ota"), ozi = son("ozi");
        let bosh = await mh.bosh_belgilar(db);
        if (ozi != null) {
          // Tahrirlashda o'z ikonkasi ham tanlasa bo'ladi.
          const r = await db.q1("SELECT rasm FROM turi WHERE id=? AND faol=1", ozi);
          if (r?.rasm && !bosh.includes(r.rasm)) bosh = [...bosh, r.rasm].sort();
        }
        const otaRasm = ota != null ? (await db.q1("SELECT rasm FROM turi WHERE id=?", ota))?.rasm : null;
        const guruhlar = [...new Set(kat.belgilar().map(kat.guruh))]
          .map((g) => ({ kalit: g, nom: kat.guruh_nomi(g) }));
        return json({ ok: true, belgilar: bosh, guruhlar, taklif: taklif(bosh, otaRasm, ota != null ? 10 : 16) });
      }
      return xato("Topilmadi", 404);
    }
    if (req.method !== "POST") return xato("Topilmadi", 404);
    let b;
    try { b = await req.json(); } catch { b = {}; }
    if (!b || typeof b !== "object") b = {};
    const matn = (x) => (x == null ? x : String(x));

    if (yol === "/app/api/kategoriya") {
      const ota = b.ota_id == null || b.ota_id === "" ? null : Number(b.ota_id);
      if (ota != null && !Number.isInteger(ota)) return xato("Asosiy kategoriya topilmadi");
      const id = await mh.kategoriya_qosh(db, matn(b.nom), ota, matn(b.rasm) || null);
      return json({ ok: true, id, ...(await royxat(db)) });
    }
    const m = yol.match(/^\/app\/api\/kategoriya\/(\d+)(\/ochir)?$/);
    if (!m) return xato("Topilmadi", 404);
    const id = Number(m[1]);
    if (!(await db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", id))) return xato("Kategoriya topilmadi", 404);
    if (m[2]) {
      await mh.kategoriya_ochir(db, id);
    } else {
      const ozg = {};
      if ("nom" in b) ozg.nom = matn(b.nom);
      if ("rasm" in b) ozg.rasm = matn(b.rasm) || null;
      await mh.kategoriya_tahrirla(db, id, ozg);
    }
    return json({ ok: true, id, ...(await royxat(db)) });
  } catch (e) {
    return xato(String(e?.message || e));
  }
}
