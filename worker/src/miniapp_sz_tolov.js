// Telegram Mini App — Sozlamalar → «Hamyon» (desktop «Hamyon»).
//
//   GET  /app/api/tolov                        — ochgan odamning hamyoni: jami, naqd, kartalar
//                                                (+ asosiy odamga `umumiy`: hammaning naqdi va kartalari birga)
//   GET  /app/api/tolov/karta/<id>             — + bitta karta: qoldig'i va tarixi
//   POST /app/api/tolov/karta                  — yangi karta {nom, qoldiq}
//   POST /app/api/tolov/otkazma                — {dan, ga, summa, izoh} (null = naqd)
//   POST /app/api/tolov/karta/<id>/togirla     — {qoldiq}: bankdagi haqiqiy qoldiq
//   POST /app/api/tolov/karta/<id>/nom         — {nom}
//   POST /app/api/tolov/karta/<id>/ochir       — o'chirish (qoldig'i naqdga qaytadi)
//   POST /app/api/tolov/otkazma/<id>/ochir     — tarixdagi o'tkazmani o'chirish
//
// Ruxsat (Telegram initData) va ochgan odam (`odam`) — miniapp.js da.
// Hisob va yozuv — FAQAT hamyon.js (Python core/hamyon.py egizagi, parity:
// test/miniapp_sz_tolov.test.js); bu fayl faqat egalikni tekshiradi va javob yig'adi:
//   · hamma narsa O'Z puli: boshqa odamning kartasi/o'tkazmasi — 403;
//   · jami = v_balans.naqd, naqd = jami − kartalar (naqd saqlanmaydi);
//   · yangi karta qoldig'i va «Qoldiqni to'g'irlash» — naqd bilan o'tkazma
//     (jami o'zgarmaydi); o'chirilgan karta puli naqdga qaytadi;
//   · sana — Toshkent bugungi kuni (desktop oynalaridagi birlamchi).
// Har yozuv bitta undo guruhi (hamyon.js ichida `db.amal`).

import * as hm from "./hamyon.js";
import * as vaqt from "./vaqt.js";
import * as plan from "./plan.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

class Rad extends Error {
  constructor(m, status) { super(m); this.status = status; }
}

/** Summa: butun so'm (son yoki "1 250 000" matni), aks holda xato. */
export function summaOl(x, { bosh = 0 } = {}) {
  if (x == null || x === "") return bosh;
  const s = typeof x === "string" ? x.replace(/[\s  ]/g, "") : x;
  const n = typeof s === "string" ? (/^-?\d+$/.test(s) ? Number(s) : NaN) : Number(s);
  if (!Number.isSafeInteger(n)) throw new Rad("Summa noto'g'ri — butun so'mda yozing.", 400);
  return n;
}

/** Karta shu odamniki va o'chirilmagan bo'lsin — aks holda 404/403. */
async function oz_kartasi(db, odam, kid) {
  const k = await db.q1("SELECT id, odam_id, nom FROM karta WHERE id=? AND ochirilgan=0", kid);
  if (!k) throw new Rad("Karta topilmadi.", 404);
  if (k.odam_id !== odam.id) throw new Rad("Bu karta sizniki emas.", 403);
  return k;
}

/** Ekranga hamma narsa: hamyon (+ ochiq karta tafsiloti). */
export async function holat(db, odam, kid = null) {
  const h = await hm.hamyon(db, odam.id);
  const natija = { ok: true, odam: odam.nom, bugun: vaqt.bugun(), hamyon: h };
  // Uch kishining puli asosiy odamning qo'lida turadi — unga hammaning naqdi va
  // kartalari birga (faqat ikki raqam); boshqalar faqat o'z pulini ko'radi.
  if (await plan.asosiy_odam(db) === odam.id) natija.umumiy = await hm.umumiy(db);
  if (kid != null) {
    const k = h.kartalar.find((x) => x.id === kid);
    if (k) natija.karta = { ...k, harakatlar: await hm.harakatlar(db, kid) };
  }
  return natija;
}

/** /app/api/tolov* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam) {
  if (yol !== "/app/api/tolov" && !yol.startsWith("/app/api/tolov/")) return null;
  const q = yol.slice("/app/api/tolov".length); // "", "/karta/5", "/karta/5/nom", …
  try {
    if (req.method === "GET") {
      if (q === "") return json(await holat(db, odam));
      const m = q.match(/^\/karta\/(\d+)$/);
      if (!m) return null;
      const k = await oz_kartasi(db, odam, Number(m[1]));
      return json(await holat(db, odam, k.id));
    }
    if (req.method !== "POST") return null;

    let m;
    const tana = async () => {
      try { return (await req.json()) || {}; } catch { throw new Rad("JSON noto'g'ri", 400); }
    };

    if (q === "/karta") {
      const b = await tana();
      const kid = await hm.karta_qosh(db, odam.id, b.nom, summaOl(b.qoldiq), vaqt.bugun());
      return json({ ...(await holat(db, odam, kid)), id: kid });
    }

    if (q === "/otkazma") {
      const b = await tana();
      const joy = (x) => (x == null || x === "" || x === "naqd" ? null : Number(x));
      const dan = joy(b.dan), ga = joy(b.ga);
      for (const k of [dan, ga]) {
        if (k == null) continue;
        if (!Number.isSafeInteger(k)) throw new Rad("Karta noto'g'ri.", 400);
        await oz_kartasi(db, odam, k);
      }
      const izoh = String(b.izoh ?? "").trim().slice(0, 200) || null;
      const id = await hm.otkazma(db, vaqt.bugun(), odam.id, dan, ga, summaOl(b.summa), izoh);
      const kid = Number(b.karta) || null; // ochiq karta sahifasi bo'lsa — tafsiloti bilan
      return json({ ...(await holat(db, odam, kid)), id });
    }

    if ((m = q.match(/^\/otkazma\/(\d+)\/ochir$/))) {
      const o = await db.q1("SELECT id, odam_id FROM karta_otkazma WHERE id=? AND ochirilgan=0", Number(m[1]));
      if (!o) throw new Rad("O'tkazma topilmadi.", 404);
      if (o.odam_id !== odam.id) throw new Rad("Bu o'tkazma sizniki emas.", 403);
      await hm.otkazma_ochir(db, o.id);
      const b = await req.json().catch(() => ({}));
      return json(await holat(db, odam, Number(b?.karta) || null));
    }

    if ((m = q.match(/^\/karta\/(\d+)\/(togirla|nom|ochir)$/))) {
      const k = await oz_kartasi(db, odam, Number(m[1]));
      const amal = m[2];
      if (amal === "ochir") {
        await hm.karta_ochir(db, k.id);
        return json(await holat(db, odam));
      }
      const b = await tana();
      if (amal === "nom") {
        await hm.karta_nomla(db, k.id, b.nom);
        return json(await holat(db, odam, k.id));
      }
      if (b.qoldiq == null || b.qoldiq === "") throw new Rad("Kartadagi qoldiqni yozing.", 400);
      const id = await hm.qoldiq_togirla(db, k.id, summaOl(b.qoldiq), vaqt.bugun());
      return json({ ...(await holat(db, odam, k.id)), id, ozgardi: id != null });
    }
    return null;
  } catch (e) {
    // core funksiyalari foydalanuvchiga tushunarli o'zbekcha matn bilan yiqiladi
    return xato(String(e?.message || e), e instanceof Rad ? e.status : 400);
  }
}
