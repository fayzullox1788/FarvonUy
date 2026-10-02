// Desktop ⇄ D1 sinxroni — HTTP uchlari. Mijoz: `../src/sinx.py` (desktop).
//
//   POST /sinx/push  {ozgarishlar:[…], sozlama:{k:v}, davr:[…], rasmlar:[{nom,data}]}
//                    → {ok:true, qabul:[id…], rad:[{id,sabab}…]}
//   POST /sinx/pull  {dan} → {ok, ozgarishlar:[…], oxirgi, kop, sozlama:{…}, rasmlar:[nom…]}
//   GET  /sinx/rasm?nom=… → rasm baytlari
//
// Hammasi `Authorization: Bearer <SINX_KALIT>` bilan.
//
// Jurnal QAYTA O'YNALADI: har `ozgarishlar` qatori `keyin` holatini o'z
// jadvaliga yozadi (yoki keyin=NULL bo'lsa qatorni o'chiradi), keyin qatorning
// o'zi `INSERT OR IGNORE` bilan jurnalga tushadi. Jurnalda BOR qator qayta
// qo'llanmaydi — javob yo'qolib, mijoz qayta yuborsa, botning keyingi
// o'zgarishi eski holat bilan bosib ketilmasin. Shuning uchun push idempotent:
// yarmida yiqilsa ham qayta yuborish xavfsiz.
//
// Jadval/ustun nomlari SQL'ga faqat haqiqiy sxemadan (sqlite_master,
// PRAGMA table_info) tekshirilgandan keyin qo'yiladi — mijoz yuborgan nom
// to'g'ridan-to'g'ri SQL'ga tushmaydi.

const BATCH = 50;          // D1 batch() dagi ifodalar soni
const PARAM = 90;          // bitta ifodadagi ? lar (D1 chegarasi 100)
const PULL_LIMIT = 500;

// Server egasi bo'lgan sozlamalar — desktop ularni bosib keta olmaydi.
const SERVER_KALITLAR = new Set(["tg_offset", "dars_tekshirildi", "tg_korilgan_guruhlar", "tg_rasxod_dan"]);
const SERVER_PREFIKSLAR = ["tg_rx:", "sinx_"];
// Desktop pull qiladigan server sozlamalari.
const PULL_SOZLAMA = ["tg_korilgan_guruhlar", "tg_rasxod_dan"];

export const RASM_NOM = /^\d+-[0-9a-f]{16}\.(jpg|jpeg|png|webp|bmp|gif)$/;
const RASM_TUR = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp",
  bmp: "image/bmp", gif: "image/gif" };

// Jurnal orqali yozib bo'lmaydigan jadvallar.
const JURNALSIZ = new Set(["ozgarishlar", "rasm", "sozlama", "meta", "davr", "yuborilgan"]);

export function serverKalitimi(k) {
  return SERVER_KALITLAR.has(k) || SERVER_PREFIKSLAR.some((p) => k.startsWith(p));
}

// ── yordamchilar ─────────────────────────────────────────────────────

const _jadvallar = new WeakMap(); // d1 -> Set(jadval)

async function jadvallar(db) {
  let s = _jadvallar.get(db.d1);
  if (!s) {
    const r = await db.q("SELECT name FROM sqlite_master WHERE type='table'");
    s = new Set(r.map((x) => x.name).filter((n) =>
      !n.startsWith("sqlite_") && !n.startsWith("_cf_") && !n.startsWith("d1_")));
    _jadvallar.set(db.d1, s);
  }
  return s;
}

/** Konstant vaqtli solishtirish (uzunlik farqi ham sizdirilmaydi). */
export function tengmi(a, b) {
  const x = new TextEncoder().encode(String(a));
  const y = new TextEncoder().encode(String(b));
  let f = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) f |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return f === 0;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function ruxsatmi(req, env) {
  const kalit = env.SINX_KALIT;
  if (!kalit) return false;
  const h = req.headers.get("authorization") || "";
  const m = /^Bearer\s+(.+)$/i.exec(h.trim());
  return !!m && tengmi(m[1], kalit);
}

function base64Dan(s) {
  const bin = atob(String(s).replace(/\s+/g, ""));
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}

// JSON qiymatini SQLite parametri qilish.
function qiymat(v) {
  if (v === undefined) return null;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (v !== null && typeof v === "object") return JSON.stringify(v);
  return v;
}

const butunmi = (x) => Number.isSafeInteger(x);

// ── push ─────────────────────────────────────────────────────────────

/** Bitta jurnal qatori → [ifodalar] yoki sabab matni (rad). */
async function qatorIfodalari(db, r, ozUstun, bor) {
  const d1 = db.d1;
  if (!r || typeof r !== "object") return "qator obyekt emas";
  if (!butunmi(r.id)) return "id butun son emas";
  const jadval = r.jadval;
  if (typeof jadval !== "string" || !bor.has(jadval) || JURNALSIZ.has(jadval)) return `jadval yo'q: ${jadval}`;
  const ustunlar = await db.ustunlar(jadval);
  if (!ustunlar.includes("id")) return `jadvalda id yo'q: ${jadval}`;
  const qid = r.qator_id;
  if (!butunmi(qid)) return "qator_id butun son emas";

  const st = [];
  if (r.keyin != null) {
    let k;
    try { k = typeof r.keyin === "string" ? JSON.parse(r.keyin) : r.keyin; } catch { return "keyin JSON emas"; }
    if (!k || typeof k !== "object" || Array.isArray(k)) return "keyin obyekt emas";
    const data = { ...k, id: qid };
    const u = ustunlar.filter((c) => Object.hasOwn(data, c));
    const qolgan = u.filter((c) => c !== "id");
    const yangila = qolgan.length
      ? `DO UPDATE SET ${qolgan.map((c) => `${c}=excluded.${c}`).join(",")}`
      : "DO NOTHING";
    st.push(d1.prepare(
      `INSERT INTO ${jadval}(${u.join(",")}) VALUES(${u.map(() => "?").join(",")}) ON CONFLICT(id) ${yangila}`)
      .bind(...u.map((c) => qiymat(data[c]))));
  } else {
    st.push(d1.prepare(`DELETE FROM ${jadval} WHERE id=?`).bind(qid));
  }
  const ou = ozUstun.filter((c) => Object.hasOwn(r, c));
  st.push(d1.prepare(
    `INSERT OR IGNORE INTO ozgarishlar(${ou.join(",")}) VALUES(${ou.map(() => "?").join(",")})`)
    .bind(...ou.map((c) => qiymat(r[c]))));
  return st;
}

const DEFER = "PRAGMA defer_foreign_keys = true";

async function batchlar(db, ifodalar) {
  for (let i = 0; i < ifodalar.length; i += BATCH - 1) {
    await db.d1.batch([db.d1.prepare(DEFER), ...ifodalar.slice(i, i + BATCH - 1)]);
  }
}

async function push(db, body) {
  const bor = await jadvallar(db);
  const qabul = [];
  const rad = [];

  // 1) jurnal
  const qatorlar = Array.isArray(body.ozgarishlar) ? [...body.ozgarishlar] : [];
  qatorlar.sort((a, b) => (a?.id ?? 0) - (b?.id ?? 0));
  const idlar = qatorlar.map((r) => r?.id).filter(butunmi);
  const allaqachon = new Set();
  for (let i = 0; i < idlar.length; i += PARAM) {
    const qism = idlar.slice(i, i + PARAM);
    const r = await db.q(`SELECT id FROM ozgarishlar WHERE id IN (${qism.map(() => "?").join(",")})`, ...qism);
    for (const x of r) allaqachon.add(x.id);
  }
  const ozUstun = (await db.ustunlar("ozgarishlar")).filter((c) => c !== "sinx");
  const reja = []; // [{id, st:[…]}]
  for (const r of qatorlar) {
    if (butunmi(r?.id) && allaqachon.has(r.id)) { qabul.push(r.id); continue; }
    const st = await qatorIfodalari(db, r, ozUstun, bor);
    if (typeof st === "string") { rad.push({ id: r?.id ?? null, sabab: st }); continue; }
    reja.push({ id: r.id, st });
  }
  // Qatorlar juft-juft (yozuv + jurnal) — bitta batch'da qoladi.
  const juft = Math.floor((BATCH - 1) / 2);
  for (let i = 0; i < reja.length; i += juft) {
    const qism = reja.slice(i, i + juft);
    try {
      await db.d1.batch([db.d1.prepare(DEFER), ...qism.flatMap((x) => x.st)]);
      qabul.push(...qism.map((x) => x.id));
    } catch {
      // Bitta yomon qator (mas. UNIQUE to'qnashuvi) qolganini to'smasin.
      for (const x of qism) {
        try {
          await db.d1.batch([db.d1.prepare(DEFER), ...x.st]);
          qabul.push(x.id);
        } catch (e) {
          rad.push({ id: x.id, sabab: String(e?.message || e) });
        }
      }
    }
  }

  // 2) sozlama
  const st = [];
  const soz = body.sozlama && typeof body.sozlama === "object" ? body.sozlama : {};
  for (const [k, v] of Object.entries(soz)) {
    if (serverKalitimi(k) || v === null || v === undefined) continue;
    st.push(db.d1.prepare(
      "INSERT INTO sozlama(kalit,qiymat) VALUES(?,?) ON CONFLICT(kalit) DO UPDATE SET qiymat=excluded.qiymat")
      .bind(k, typeof v === "string" ? v : String(qiymat(v))));
  }

  // 3) davr (oy bo'yicha)
  if (Array.isArray(body.davr) && body.davr.length && bor.has("davr")) {
    const du = await db.ustunlar("davr");
    for (const r of body.davr) {
      if (!r || typeof r.oy !== "string") continue;
      const u = du.filter((c) => Object.hasOwn(r, c));
      const q = u.filter((c) => c !== "oy");
      st.push(db.d1.prepare(
        `INSERT INTO davr(${u.join(",")}) VALUES(${u.map(() => "?").join(",")}) ON CONFLICT(oy) ` +
        (q.length ? `DO UPDATE SET ${q.map((c) => `${c}=excluded.${c}`).join(",")}` : "DO NOTHING"))
        .bind(...u.map((c) => qiymat(r[c]))));
    }
  }

  if (st.length) await batchlar(db, st);

  // 4) rasmlar — har biri ALOHIDA so'rov (bitta rasm ~1 MB gacha; batch'ga
  // yig'ilsa D1 so'rov hajmi chegarasiga uriladi).
  for (const r of Array.isArray(body.rasmlar) ? body.rasmlar : []) {
    if (!r || typeof r.nom !== "string" || !RASM_NOM.test(r.nom) || typeof r.data !== "string") continue;
    let b;
    try { b = base64Dan(r.data); } catch { continue; }
    await db.d1.prepare("INSERT OR IGNORE INTO rasm(nom,data) VALUES(?,?)").bind(r.nom, b).run();
  }

  return { ok: true, qabul, rad };
}

// ── pull ─────────────────────────────────────────────────────────────

async function pull(db, body) {
  const dan = Number.isFinite(Number(body?.dan)) ? Math.trunc(Number(body.dan)) : 0;
  const r = await db.q(
    `SELECT * FROM ozgarishlar WHERE id>? AND id%2=1 ORDER BY id LIMIT ${PULL_LIMIT + 1}`, dan);
  const kop = r.length > PULL_LIMIT;
  const qatorlar = kop ? r.slice(0, PULL_LIMIT) : r;
  for (const q of qatorlar) delete q.sinx;
  const sozlama = {};
  for (const k of PULL_SOZLAMA) sozlama[k] = await db.sozlama(k, null);
  const rasmlar = (await db.q("SELECT nom FROM rasm ORDER BY nom")).map((x) => x.nom);
  return {
    ok: true, ozgarishlar: qatorlar,
    oxirgi: qatorlar.length ? qatorlar[qatorlar.length - 1].id : dan,
    kop, sozlama, rasmlar,
  };
}

// ── rasm ─────────────────────────────────────────────────────────────

function baytlar(v) {
  if (v == null) return null;
  if (v instanceof Uint8Array) return v;
  if (v instanceof ArrayBuffer) return new Uint8Array(v);
  if (Array.isArray(v)) return Uint8Array.from(v); // D1 BLOB'ni son massivi qilib beradi
  if (typeof v === "string") return new TextEncoder().encode(v);
  return null;
}

async function rasm(db, url) {
  const nom = url.searchParams.get("nom") || "";
  if (!RASM_NOM.test(nom)) return new Response("topilmadi", { status: 404 });
  const r = await db.q1("SELECT data FROM rasm WHERE nom=?", nom);
  const b = baytlar(r?.data);
  if (!b) return new Response("topilmadi", { status: 404 });
  const ext = nom.split(".").pop();
  return new Response(b, { headers: { "content-type": RASM_TUR[ext] || "application/octet-stream",
    "cache-control": "private, max-age=86400" } });
}

// ── marshrut ─────────────────────────────────────────────────────────

/** `/sinx/*` so'rovi. Boshqa yo'l bo'lsa null. */
export async function ishla(req, env, db) {
  const url = new URL(req.url);
  if (!url.pathname.startsWith("/sinx/")) return null;
  if (!ruxsatmi(req, env)) return json({ ok: false, xato: "ruxsat yo'q" }, 401);
  const yol = url.pathname;
  if (yol === "/sinx/rasm" && req.method === "GET") return rasm(db, url);
  if ((yol === "/sinx/push" || yol === "/sinx/pull") && req.method === "POST") {
    let body;
    try { body = await req.json(); } catch { return json({ ok: false, xato: "JSON emas" }, 400); }
    if (!body || typeof body !== "object") return json({ ok: false, xato: "JSON obyekt emas" }, 400);
    return json(yol === "/sinx/push" ? await push(db, body) : await pull(db, body));
  }
  return json({ ok: false, xato: "topilmadi" }, 404);
}
