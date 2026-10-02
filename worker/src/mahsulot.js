// Mahsulotlar va kategoriya daraxti — Python `core/mahsulot.py` ning botga kerak qismi.
//
// Rasm: Python faylni `config.MAHSULOT_RASM` ga yozadi; Worker'da disk yo'q,
// shuning uchun bayt D1 dagi `rasm(nom TEXT PRIMARY KEY, data BLOB)` jadvalida.
// Nom qoidasi bir xil (`{item_id}-{sha1[:16]}{ext}`) — `item.rasm` ikki
// tomonda ham bir xil kalitni ko'rsatadi.
import * as money from "./money.js";
import * as kat from "./kategoriya.js";

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

// ═══════════════════════════════════════════════════ kategoriya daraxti (yozish)
// Mini App «Sozlamalar → Kategoriyalar» uchun. Qoidalar desktopniki bilan bir xil
// (sahifa_mahsulot.py «Kategoriyalar» varag'i, IchkiKategoriyaDialog).

// mahsulot.py:61
/** Kategoriyaning o'zi + hamma ichki kategoriyalari (har chuqurlikda). */
export async function avlodlar(db, turi_id) {
  return (await db.q(
    "WITH RECURSIVE a(id) AS (SELECT ? UNION SELECT t.id FROM turi t JOIN a ON t.ota_id=a.id)" +
    " SELECT id FROM a", turi_id)).map((r) => r.id);
}

// mahsulot.py:84
/** Hali hech bir FAOL kategoriyada ishlatilmagan ikonkalar (bitta ikonka — bitta kategoriya). */
export async function bosh_belgilar(db) {
  const band = await kat.nomlanganlar(db);
  return kat.belgilar().filter((f) => !band.has(f));
}

// mahsulot.py:97
export async function _rasm_tekshir(db, rasm, ozi = null) {
  if (!kat.belgilar().includes(rasm)) throw new Error("Bunday rasm yo'q — ro'yxatdan tanlang.");
  const egasi = await db.q1("SELECT nom FROM turi WHERE faol=1 AND rasm=? AND id<>?",
    rasm, ozi == null ? -1 : ozi);
  if (egasi) throw new Error(`Bu rasm «${egasi.nom}» kategoriyasida band — boshqasini tanlang.`);
}

// mahsulot.py:108
/** Yangi kategoriya. ICHKI (`ota_id` berilgan) uchun bo'sh ikonka MAJBURIY.
 *  Shu nomli o'chirilgan (faol=0) qator bo'lsa — o'sha tiriladi. → turi.id */
export async function kategoriya_qosh(db, nom, ota_id = null, rasm = null) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Kategoriya nomi bo'sh bo'lmasin");
  if (ota_id != null && !(await db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", ota_id))) {
    throw new Error("Asosiy kategoriya topilmadi");
  }
  if (ota_id != null && !rasm) throw new Error("Ichki kategoriya uchun rasm tanlang.");
  const band = await db.q1("SELECT id, faol FROM turi WHERE nom=?", nom);
  if (band && band.faol) throw new Error(`«${nom}» nomli kategoriya allaqachon bor`);
  if (rasm) await _rasm_tekshir(db, rasm, band ? band.id : null);
  if (band) {
    // Oldin o'chirilgan — o'sha qatorni tiriltiramiz, eski rasxodlari qaytadi.
    const yangi = { faol: 1, ota_id };
    if (rasm) yangi.rasm = rasm;
    const a = db.amal(`Kategoriya qaytdi: ${nom}`);
    await a.apply("turi", "UPDATE", yangi, band.id);
    await a.commit();
    return band.id;
  }
  const n = await db.skalyar("SELECT COALESCE(MAX(tartib),-1)+1 FROM turi");
  const tavsif = ota_id ? `Ichki kategoriya: ${await yol_nomi(db, ota_id)} › ${nom}` : `Kategoriya: ${nom}`;
  const a = db.amal(tavsif);
  const id = await a.apply("turi", "INSERT", {
    nom, belgi: "", tartib: n, ota_id, rasm: rasm || null });
  await a.commit();
  return id;
}

// mahsulot.py:142
export async function kategoriya_nomla(db, turi_id, nom) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Kategoriya nomi bo'sh bo'lmasin");
  if (await db.q1("SELECT id FROM turi WHERE nom=? AND id<>?", nom, turi_id)) {
    throw new Error(`«${nom}» nomli kategoriya allaqachon bor`);
  }
  const a = db.amal(`Kategoriya nomi: ${nom}`);
  await a.apply("turi", "UPDATE", { nom }, turi_id);
  await a.commit();
}

/** Mini App «Tahrirlash»: nom (`kategoriya_nomla` qoidasi) va ikonka
 *  (`_rasm_tekshir(ozi=turi_id)` — o'z ikonkasi band hisoblanmaydi) — BITTA undo.
 *  Desktopda ikonka almashtirish funksiyasi yo'q; qoidalar o'sha ikkisidan.
 *  O'zgarmagan maydon yozilmaydi; hech narsa o'zgarmasa — yozuv yo'q. */
export async function kategoriya_tahrirla(db, turi_id, { nom, rasm } = {}) {
  const t = await db.q1("SELECT nom, rasm, ota_id FROM turi WHERE id=? AND faol=1", turi_id);
  if (!t) throw new Error("Kategoriya topilmadi");
  const yangi = {};
  if (nom !== undefined) {
    nom = String(nom ?? "").trim();
    if (!nom) throw new Error("Kategoriya nomi bo'sh bo'lmasin");
    if (nom !== t.nom) {
      if (await db.q1("SELECT id FROM turi WHERE nom=? AND id<>?", nom, turi_id)) {
        throw new Error(`«${nom}» nomli kategoriya allaqachon bor`);
      }
      yangi.nom = nom;
    }
  }
  if (rasm !== undefined && (rasm || null) !== (t.rasm || null)) {
    if (!rasm) {
      if (t.ota_id != null) throw new Error("Ichki kategoriya uchun rasm tanlang.");
    } else {
      await _rasm_tekshir(db, rasm, turi_id);
    }
    yangi.rasm = rasm || null;
  }
  if (!Object.keys(yangi).length) return false;
  const a = db.amal(yangi.nom ? `Kategoriya nomi: ${yangi.nom}` : `Kategoriya rasmi: ${t.nom}`);
  await a.apply("turi", "UPDATE", yangi, turi_id);
  await a.commit();
  return true;
}

// mahsulot.py:197
/** `faol=0`. Ichida faol ichki kategoriya yoki mahsulot bo'lsa — rad. */
export async function kategoriya_ochir(db, turi_id) {
  const t = await db.q1("SELECT nom FROM turi WHERE id=?", turi_id);
  if (!t) throw new Error("Kategoriya topilmadi");
  let n = await db.skalyar("SELECT COUNT(*) FROM turi WHERE ota_id=? AND faol=1", [turi_id]);
  if (n) throw new Error(`«${t.nom}» ichida ${n} ta ichki kategoriya bor — avval ularni o'chiring.`);
  n = await db.skalyar("SELECT COUNT(*) FROM item WHERE turi_id=? AND ochirilgan=0", [turi_id]);
  if (n) {
    throw new Error(`«${t.nom}» ichida ${n} ta mahsulot bor — avval ` +
      "ularni boshqa kategoriyaga o'tkazing yoki o'chiring.");
  }
  const a = db.amal(`Kategoriya o'chirildi: ${t.nom}`);
  await a.apply("turi", "UPDATE", { faol: 0 }, turi_id);
  await a.commit();
}
