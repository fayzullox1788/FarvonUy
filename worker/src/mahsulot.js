// Mahsulotlar va kategoriya daraxti — Python `core/mahsulot.py` ning botga kerak qismi.
//
// Rasm: Python faylni `config.MAHSULOT_RASM` ga yozadi; Worker'da disk yo'q,
// shuning uchun bayt D1 dagi `rasm(nom TEXT PRIMARY KEY, data BLOB)` jadvalida.
// Nom qoidasi bir xil (`{item_id}-{sha1[:16]}{ext}`) — `item.rasm` ikki
// tomonda ham bir xil kalitni ko'rsatadi.
import * as money from "./money.js";

export const RASM_TURLARI = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"];
export const RASM_MAX_BAYT = 25 * 1024 * 1024;

// mahsulot.py:33
/** Faol kategoriyalar daraxti: [{id, nom, belgi, rasm, ota_id, bolalar: [...]}]. */
export async function daraxt(db) {
  const qatorlar = (await db.q(
    "SELECT id, nom, belgi, rasm, ota_id FROM turi WHERE faol=1 ORDER BY tartib, id"))
    .map((r) => ({ ...r, bolalar: [] }));
  const boyicha = new Map(qatorlar.map((r) => [r.id, r]));
  const ildizlar = [];
  for (const r of qatorlar) {
    const ota = r.ota_id != null ? boyicha.get(r.ota_id) : undefined;
    (ota ? ota.bolalar : ildizlar).push(r);
  }
  return ildizlar;
}

// mahsulot.py:68
/** «Bozorlik › Mevalar» — ko'rsatish uchun. */
export async function yol_nomi(db, turi_id) {
  if (turi_id == null) return "";
  const qismlar = [];
  const korilgan = new Set();
  let joriy = turi_id;
  while (joriy != null && !korilgan.has(joriy)) {
    korilgan.add(joriy);
    const r = await db.q1("SELECT nom, ota_id FROM turi WHERE id=?", joriy);
    if (!r) break;
    qismlar.push(r.nom);
    joriy = r.ota_id;
  }
  return qismlar.reverse().join(" › ");
}

/** Python `f"{x:g}"` (6 muhim raqam, keraksiz nollarsiz). */
export function _g(x) {
  x = Number(x);
  if (!Number.isFinite(x)) return String(x).toLowerCase().replace("infinity", "inf");
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  const exp = Math.floor(Math.log10(Math.abs(Number(x.toPrecision(6)))));
  if (exp < -4 || exp >= 6) {
    let [m, e] = x.toExponential(5).split("e");
    if (m.includes(".")) m = m.replace(/0+$/, "").replace(/\.$/, "");
    const n = Number(e);
    return `${m}e${n < 0 ? "-" : "+"}${String(Math.abs(n)).padStart(2, "0")}`;
  }
  let s = x.toFixed(Math.max(0, 5 - exp));
  if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
  return s;
}

// mahsulot.py:289
/** «2 kg · 1,5 l · 12 000 so'm» — kartada va rasxod oynasida. */
export function tavsif(r) {
  const qism = [];
  const son = (x) => (x != null ? _g(x).replace(".", ",") : null);
  if (r.miqdor != null) qism.push(`${son(r.miqdor)} ${r.olchov || ""}`.trim());
  else if (r.olchov) qism.push(r.olchov);
  else if (r.birlik) qism.push(r.birlik);
  if (r.ogirlik != null) qism.push(`${son(r.ogirlik)} kg`);
  if (r.litr != null) qism.push(`${son(r.litr)} l`);
  if (r.narx) qism.push(money.fmt_som(r.narx));
  return qism.join(" · ");
}

// ═══════════════════════════════════════════════════════════ rasm

/** sha1 hex (Web Crypto — Worker'da ham, Node'da ham). */
async function _sha1hex(baytlar) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-1", baytlar));
  return [...h].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// mahsulot.py:325 (_rasm_yoz) + :352 (rasm_baytdan)
/** Telegramdan kelgan rasm: baytlar D1 `rasm` ga, nomi `item.rasm` ga. */
export async function rasm_baytdan(db, item_id, baytlar, kengaytma = ".jpg", { a = null } = {}) {
  kengaytma = String(kengaytma).toLowerCase();
  if (!RASM_TURLARI.includes(kengaytma)) {
    throw new Error(`Bu turdagi rasm qo'llab-quvvatlanmaydi: ${kengaytma}`);
  }
  baytlar = baytlar instanceof Uint8Array ? baytlar : new Uint8Array(baytlar);
  if (baytlar.length > RASM_MAX_BAYT) throw new Error("Rasm juda katta (25 MB dan oshmasin)");
  if (!baytlar.length) throw new Error("Rasm fayli bo'sh");
  const r = await db.q1("SELECT nom FROM item WHERE id=? AND ochirilgan=0", item_id);
  if (!r) throw new Error("Mahsulot topilmadi");
  // Nom — mazmun xeshi: bir xil rasm ikki marta yuklansa nusxa ko'paymaydi.
  const fayl = `${item_id}-${(await _sha1hex(baytlar)).slice(0, 16)}${kengaytma}`;
  // Fayl tizimidagi nusxa kabi — audit qilinmaydi (undo bog'lanishni qaytaradi).
  await db.exec("INSERT OR IGNORE INTO rasm(nom, data) VALUES(?, ?)", fayl, baytlar);
  const ozim = a == null;
  if (ozim) a = db.amal(`Mahsulot rasmi: ${r.nom}`);
  await a.apply("item", "UPDATE", { rasm: fayl }, item_id);
  if (ozim) await a.commit();
  return fayl;
}

// mahsulot.py:310 (rasm_yoli) — fayl o'rniga baytlar
/** `item.rasm` nomi bo'yicha baytlar; yo'q bo'lsa null. */
export async function rasm_baytlari(db, nom) {
  if (!nom) return null;
  const r = await db.q1("SELECT data FROM rasm WHERE nom=?", nom);
  if (!r || r.data == null) return null;
  const d = r.data;
  if (d instanceof Uint8Array) return d;
  if (d instanceof ArrayBuffer) return new Uint8Array(d);
  if (Array.isArray(d)) return new Uint8Array(d); // D1 BLOB'ni ba'zan massiv qaytaradi
  return new Uint8Array(d);
}

// mahsulot.py:369
/** Aniq nom (katta-kichik harf farqsiz) — Telegram izohidan qidirish. */
export async function nom_boyicha(db, matn) {
  const q = _casefold(String(matn ?? "").trim());
  if (!q) return [];
  return (await db.q("SELECT id, nom FROM item WHERE ochirilgan=0 ORDER BY faol DESC, id"))
    .filter((r) => _casefold(String(r.nom ?? "").trim()) === q);
}

// mahsulot.py:379
export async function oxshashlar(db, matn, n = 5) {
  const q = _casefold(String(matn ?? "").trim());
  if (!q) return [];
  return (await db.q("SELECT nom FROM item WHERE ochirilgan=0 ORDER BY nom"))
    .filter((r) => _casefold(r.nom).includes(q) || q.includes(_casefold(r.nom)))
    .map((r) => r.nom)
    .slice(0, n);
}

/** str.casefold() taqribi (PORT.md). */
export function _casefold(s) {
  return String(s).toLowerCase().replaceAll("ß", "ss");
}
