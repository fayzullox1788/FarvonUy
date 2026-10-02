// Telegram Mini App — «Sozlamalar → Mahsulotlar» (mahsulot katalogi) API'si.
//
//   GET  /app/api/mahsulot                 — katalog: {mahsulotlar, daraxt, olchovlar}
//                                            (?turi=&q=&faollar=1 — `mh.mahsulotlar` filtrlari)
//   GET  /app/api/mahsulot/<id>/rasm       — mahsulot rasmi (D1 `rasm` jadvalidan baytlar)
//   POST /app/api/mahsulot                 — yangi {nom, turi_id, narx, miqdor, olchov,
//                                            ogirlik, litr, izoh, faol}       (`mh.saqla`)
//   POST /app/api/mahsulot/<id>            — tahrir (o'sha maydonlar)          (`mh.saqla`)
//   POST /app/api/mahsulot/<id>/ochir      — yumshoq o'chirish, ochirilgan=1   (`mh.ochir`)
//
// Qoidalar desktopniki (core/mahsulot.py, sahifa_mahsulot.MahsulotDialog): `faol=0` —
// rasxodda tanlanmaydi, katalogda ko'rinadi; `ochirilgan=1` — o'chirilgan (eski rasxodlar
// joyida qoladi). Har yozuv — bitta undo guruhi. Yozuvdan keyin javobda yangi katalog
// qaytadi. Rasm: <img> sarlavha yubora olmaydi — klient shu yo'lni `Authorization` bilan
// fetch qilib blob URL yasaydi; demak rasmni faqat initData'si tekshirilgan uy a'zosi oladi.
// Rasm yuklash bu yerda YO'Q (bot qabul qiladi). Xato — 400 {ok:false, xato}.

import * as mh from "./mahsulot.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

const RASM_TURI = {
  ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
  ".bmp": "image/bmp", ".gif": "image/gif",
};

/** Klientga bitta mahsulot qatori (desktop kartasidagi ma'lumot). */
export function qator(r) {
  return {
    id: r.id, nom: r.nom, turi_id: r.turi_id ?? null, kategoriya: r.kategoriya ?? "",
    narx: r.narx || 0, miqdor: r.miqdor ?? null, olchov: r.olchov ?? null,
    ogirlik: r.ogirlik ?? null, litr: r.litr ?? null, izoh: r.izoh ?? null,
    faol: r.faol ? 1 : 0, rasm: r.rasm || null,
    tavsif: mh.tavsif(r),
    olcham: mh.tavsif({ ...r, narx: 0 }), // narxsiz qismi: «2 kg · 1,5 l»
  };
}

/** Katalog: mahsulotlar (mh.mahsulotlar tartibida) + kategoriya daraxti (tanlagich uchun). */
export async function katalog(db, { turi_id = null, qidiruv = "", faollar = false } = {}) {
  const [qatorlar, ildiz] = await Promise.all([
    mh.mahsulotlar(db, turi_id, qidiruv, faollar),
    mh.daraxt(db),
  ]);
  const tugun = (t) => ({ id: t.id, nom: t.nom, rasm: t.rasm || null, ota_id: t.ota_id ?? null,
    bolalar: t.bolalar.map(tugun) });
  return { mahsulotlar: qatorlar.map(qator), daraxt: ildiz.map(tugun), olchovlar: mh.OLCHOVLAR };
}

const MAYDONLAR = ["narx", "miqdor", "ogirlik", "litr", "olchov", "izoh"];

/** /app/api/mahsulot* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam) {
  if (!(yol === "/app/api/mahsulot" || yol.startsWith("/app/api/mahsulot/"))) return null;
  try {
    if (req.method === "GET") {
      if (yol === "/app/api/mahsulot") {
        const t = url.searchParams.get("turi") || "";
        return json({ ok: true, ...(await katalog(db, {
          turi_id: /^\d+$/.test(t) ? Number(t) : null,
          qidiruv: url.searchParams.get("q") || "",
          faollar: url.searchParams.get("faollar") === "1",
        })) });
      }
      const m = yol.match(/^\/app\/api\/mahsulot\/(\d+)\/rasm$/);
      if (!m) return xato("Topilmadi", 404);
      const r = await db.q1("SELECT rasm FROM item WHERE id=? AND ochirilgan=0", Number(m[1]));
      const baytlar = r?.rasm ? await mh.rasm_baytlari(db, r.rasm) : null;
      if (!baytlar) return xato("Rasm topilmadi", 404);
      const ext = r.rasm.slice(r.rasm.lastIndexOf(".")).toLowerCase();
      return new Response(baytlar, { headers: {
        "content-type": RASM_TURI[ext] || "application/octet-stream",
        "cache-control": "private, max-age=600",
        "x-content-type-options": "nosniff",
      } });
    }
    if (req.method !== "POST") return xato("Topilmadi", 404);
    let b;
    try { b = await req.json(); } catch { b = {}; }
    if (!b || typeof b !== "object") b = {};

    const turi = (x) => {
      if (x == null || x === "") return null;
      const n = Number(x);
      if (!Number.isInteger(n)) throw new Error("Bu kategoriya endi yo'q — boshqasini tanlang");
      return n;
    };

    if (yol === "/app/api/mahsulot") {
      const id = await mh.saqla(db, null, {
        nom: b.nom == null ? "" : String(b.nom), turi_id: turi(b.turi_id),
        ...Object.fromEntries(MAYDONLAR.map((k) => [k, b[k] ?? null])),
        faol: "faol" in b ? !!b.faol : true,
      });
      return json({ ok: true, id, ...(await katalog(db)) });
    }

    const m = yol.match(/^\/app\/api\/mahsulot\/(\d+)(\/ochir)?$/);
    if (!m) return xato("Topilmadi", 404);
    const id = Number(m[1]);
    const r = await db.q1("SELECT * FROM item WHERE id=? AND ochirilgan=0", id);
    if (!r) return xato("Mahsulot topilmadi", 404);
    if (m[2]) {
      await mh.ochir(db, id);
    } else {
      // Desktop dialogi hamma maydonni yuboradi; yuborilmagani joriy qiymatida qoladi
      // (`saqla` bo'shini NULL qiladi — yarim so'rov ma'lumotni o'chirib yubormasin).
      const ol = (k) => (k in b ? b[k] : r[k]);
      await mh.saqla(db, id, {
        nom: String(ol("nom") ?? ""), turi_id: "turi_id" in b ? turi(b.turi_id) : r.turi_id,
        ...Object.fromEntries(MAYDONLAR.map((k) => [k, ol(k) ?? null])),
        faol: !!ol("faol"),
      });
    }
    return json({ ok: true, id, ...(await katalog(db)) });
  } catch (e) {
    return xato(String(e?.message || e));
  }
}
