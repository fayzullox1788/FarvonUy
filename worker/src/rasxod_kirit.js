// Rasxod kiritish — dastur va bot uchun BITTA mantiq (Python `core/rasxod_kirit.py`).
//
// `parametrlar`: null — «tanlanmagan, uydagilar»; bo'sh Map — «hech kim
// tanlanmagan» (saqlanmaydi). Ikkalasini aralashtirmang.
import * as money from "./money.js";
import * as entries from "./entries.js";
import * as hamyon from "./hamyon.js";
import * as splitting from "./splitting.js";

export const UMUMIY = "umumiy", SHAXSIY = "shaxsiy", UCHUN = "uchun";

// Maydonlar tartibi — Python dataclass tartibi (asdict / JSON).
const MAYDONLAR = ["sana", "kim_toladi", "turi_id", "item_id", "nom", "summa", "tur",
  "kim_uchun", "usul", "parametrlar", "izoh", "manba", "mahsulotlar", "karta_id"];

// rasxod_kirit.py:22
export class Qoralama {
  constructor({
    sana, kim_toladi = null, turi_id = null, item_id = null, nom = "", summa = 0,
    tur = UMUMIY, kim_uchun = null, usul = money.USUL_TENG, parametrlar = null,
    izoh = null, manba = "dastur", mahsulotlar = [], karta_id = null,
  } = {}) {
    if (sana === undefined) throw new TypeError("Qoralama: 'sana' majburiy");
    Object.assign(this, { sana, kim_toladi, turi_id, item_id, nom, summa, tur, kim_uchun,
      usul, parametrlar, izoh, manba, mahsulotlar, karta_id });
  }

  // rasxod_kirit.py:47
  /** JSON uchun lug'at (Python `lugat()` bilan bir xil shakl). */
  lugat() {
    const d = {};
    for (const k of MAYDONLAR) d[k] = this[k];
    d.mahsulotlar = (this.mahsulotlar || []).map((x) => ({ ...x }));
    if (this.parametrlar != null) {                 // JSON kaliti — matn
      d.parametrlar = Object.fromEntries([...this.parametrlar].map(([k, v]) => [String(k), v]));
    }
    return d;
  }

  /**
   * `lugat()` ning JSON matni, `parametrlar` kalitlari QO'SHILISH TARTIBIDA.
   * (JS obyekti "3","1" kalitlarini saralab yuboradi; Python dict esa tartibni
   * saqlaydi — tartib ulush qatorlari va ro'yxat ko'rinishiga ta'sir qiladi.)
   */
  lugat_json() {
    const d = this.lugat();
    return "{" + MAYDONLAR.map((k) => {
      let v;
      if (k === "parametrlar" && this.parametrlar != null) {
        v = "{" + [...this.parametrlar].map(([i, x]) => `${JSON.stringify(String(i))}:${JSON.stringify(x)}`).join(",") + "}";
      } else {
        v = JSON.stringify(d[k] === undefined ? null : d[k]);
      }
      return `${JSON.stringify(k)}:${v}`;
    }).join(",") + "}";
  }

  // rasxod_kirit.py:54
  /** d.parametrlar — Map yoki {"id": qiymat} obyekt (yoki null). */
  static lugatdan(d) {
    d = { ...d };
    for (const k of Object.keys(d)) {
      if (!MAYDONLAR.includes(k)) throw new TypeError(`Qoralama: noma'lum maydon '${k}'`);
    }
    if (d.parametrlar != null) {
      const juft = d.parametrlar instanceof Map ? [...d.parametrlar] : Object.entries(d.parametrlar);
      d.parametrlar = new Map(juft.map(([k, v]) => [Math.trunc(Number(k)), Number(v)]));
    }
    return new Qoralama(d);
  }
}

/**
 * JSON matnidagi `"parametrlar": {...}` juftlarini ASL tartibda o'qiydi
 * (JSON.parse butun son kalitlarni saralab yuboradi). Topilmasa — null.
 * Qiymatlar doim son (Python `float`), kalitlar — odam id.
 */
export function parametrlar_tartibi(matn) {
  const m = /"parametrlar"\s*:\s*\{([^{}]*)\}/.exec(String(matn));
  if (!m) return null;
  const juft = [];
  for (const x of m[1].matchAll(/"(-?\d+)"\s*:\s*(-?[0-9][0-9.eE+-]*)/g)) {
    juft.push([Number(x[1]), Number(x[2])]);
  }
  return juft;
}

// rasxod_kirit.py:63
/** Mahsulot tanlanganda nom va narx O'ZI to'ldiriladi — agar bo'sh bo'lsa. */
export async function mahsulot_tanla(db, q, item_id) {
  q.item_id = item_id || null;
  if (!q.item_id) return;
  const it = await db.q1("SELECT nom, narx FROM item WHERE id=?", q.item_id);
  if (!it) { q.item_id = null; return; }
  if (!String(q.nom ?? "").trim()) q.nom = it.nom;
  if (it.narx && !q.summa) q.summa = Math.trunc(Number(it.narx));
}

// rasxod_kirit.py:93
/** Tekshiradi va tozalaydi: bo'sh qatorlar tashlanadi, nom mahsulotdan. */
export async function mahsulot_qatorlari(db, qatorlar) {
  const natija = [];
  let i = 0;
  for (const x of qatorlar || []) {
    i += 1;
    const iid = x.item_id || null;
    const summa = Math.trunc(Number(x.summa || 0));
    let nom = String(x.nom || "").trim();
    if (!iid && !summa && !nom) continue;
    if (iid) {
      const it = await db.q1("SELECT nom FROM item WHERE id=?", iid);
      if (!it) throw new Error(`${i}-mahsulot topilmadi.`);
      nom = nom || it.nom;
    }
    if (!nom) throw new Error(`${i}-qatorda mahsulot tanlanmagan.`);
    if (summa <= 0) throw new Error(`«${nom}» summasi kiritilmagan.`);
    const miqdor = Math.trunc(Number(x.miqdor || 1));
    if (miqdor <= 0) throw new Error(`«${nom}» miqdori musbat bo'lishi kerak.`);
    natija.push({ item_id: iid, nom, miqdor, summa });
  }
  return natija;
}

// rasxod_kirit.py:146
export function qatorlar_jami(qatorlar) {
  return qatorlar.reduce((s, x) => s + Math.trunc(Number(x.summa)), 0);
}

// rasxod_kirit.py:214
/** Umumiy rasxod kimlarga bo'linadi (tanlanmagan bo'lsa — uydagilar). */
export async function qatnashchilar(db, q) {
  if (q.parametrlar != null) return [...q.parametrlar].filter(([, v]) => v).map(([i]) => i);
  return splitting.qatnashchilar(db, q.sana);
}

// rasxod_kirit.py:224
/** Saqlashdan OLDIN ko'rsatish uchun — `rasxod_qosh` bilan aynan bir xil. */
export async function ulushlar(db, q) {
  if (q.tur !== UMUMIY || q.summa <= 0 || (q.parametrlar != null && q.parametrlar.size === 0)) return [];
  return splitting.hisobla(db, Math.trunc(Number(q.summa)), q.sana, q.usul, q.parametrlar);
}

// rasxod_kirit.py:233
/** Dasturdagi oyna ham, bot ham aynan shu xabarlar bilan to'xtaydi. */
export async function tekshir(db, q) {
  q.mahsulotlar = await mahsulot_qatorlari(db, q.mahsulotlar);
  const summa = Math.trunc(Number(q.summa || 0));
  if (q.mahsulotlar.length && qatorlar_jami(q.mahsulotlar) !== summa) {
    throw new Error("Summa mahsulotlar yig'indisiga teng emas " +
      `(${money.fmt_som(qatorlar_jami(q.mahsulotlar))}).`);
  }
  if (summa <= 0) throw new Error("Summa kiritilmagan.");
  await entries.rasxod_majburiy(db, q.nom, q.turi_id);
  if (q.kim_toladi == null || !await db.q1(
    "SELECT 1 FROM odam WHERE id=? AND faol=1", q.kim_toladi)) {
    throw new Error("Kim to'laganini tanlang.");
  }
  await hamyon.tekshir_karta(db, q.karta_id, q.kim_toladi);
  if (![UMUMIY, SHAXSIY, UCHUN].includes(q.tur)) throw new Error("Rasxod turi noma'lum.");
  if (q.tur === UCHUN) {
    if (q.kim_uchun == null) throw new Error("Kim uchun olinganini tanlang.");
    if (q.kim_uchun === q.kim_toladi) {
      throw new Error("To'lovchi va «kim uchun» bir odam bo'lsa — bu oddiy " +
        "shaxsiy rasxod. «Shaxsiy» ni tanlang.");
    }
  }
  if (q.tur === UMUMIY && q.parametrlar != null && ![...q.parametrlar.values()].some((v) => v)) {
    throw new Error("Kamida bitta odam tanlangan bo'lishi kerak.");
  }
}

// rasxod_kirit.py:261
/**
 * Tekshiradi va YANGI rasxod yozadi (`entries.rasxod_qosh` — bitta undo).
 * Bir nechta mahsulotli yo'l (`q.mahsulotlar`) faqat dasturdagi oynada —
 * bot uni hech qachon to'ldirmaydi; Worker'da u port qilinmagan.
 */
export async function saqla(db, q, katalog_narxi = false) {
  await tekshir(db, q);
  if (q.mahsulotlar.length) {
    throw new Error("Bir nechta mahsulotli rasxod faqat dasturda yoziladi.");
  }
  const umumiy = q.tur === UMUMIY;
  const it = katalog_narxi && q.item_id
    ? await db.q1("SELECT narx FROM item WHERE id=?", q.item_id) : null;
  const summa = Math.trunc(Number(q.summa));
  if (!it || it.narx === summa) return _yoz(db, q, umumiy);
  const a = db.amal(`Rasxod: ${q.nom.trim()} ${money.fmt(summa)} (narx yangilandi)`);
  const rid = await _yoz(db, q, umumiy, { a });
  await a.apply("item", "UPDATE", { narx: summa }, q.item_id);
  await a.commit();
  return rid;
}

// rasxod_kirit.py:300
export async function _yoz(db, q, umumiy, { a = null } = {}) {
  return entries.rasxod_qosh(db, q.sana, q.nom.trim(), Math.trunc(Number(q.summa)), q.kim_toladi, {
    umumiymi: umumiy, turi_id: q.turi_id, usul: q.usul,
    parametrlar: umumiy ? q.parametrlar : null,
    izoh: q.izoh, item_id: q.item_id,
    kim_uchun: q.tur === UCHUN ? q.kim_uchun : null,
    karta_id: q.karta_id, a,
  });
}
