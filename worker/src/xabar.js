// Telegram xabarlari — Python `src/core/xabar.py` ning bot qismi.
//
// Uy guruhiga ketadigan hamma xabar `kutilayotgan()` dan chiqadi:
// KUNLIK (sarlavha + odam boshiga bo'lak), SHAXSIY, ESLATMA, DARS
// (oldindan ogohlantirish), RASXOD e'loni va YUTUQ tabrigi.
//
// `yuborilgan` va `sozlama` yozuvlari db.apply() dan O'TMAYDI (texnik iz).
//
// UNUMDORLIK: `kutilayotgan` har daqiqada ishlaydi (Cloudflare bepul reja —
// 10 ms CPU). Python har odam/vazifa uchun alohida so'raydi; bu yerda
// hamma kerakli narsa bir martalik `_kontekst()` ga yig'iladi (vazifa turlari,
// odamlar, uborka qadamlari, menyu) va matn quruvchilar faqat shu xotiradan
// o'qiydi. Har eksport qilingan funksiya Python imzosini saqlaydi va oxirida
// ixtiyoriy `ctx` oladi — berilmasa o'zi quradi (natija bir xil).
import * as vaqt from "./vaqt.js";
import * as money from "./money.js";
import * as tg from "./tg.js";
import * as vz from "./vazifa.js";
import * as mn from "./menyu.js";
import * as dars from "./dars.js";
import * as tgm from "./tg_menyu.js";
import * as tgr from "./tg_rasxod.js";
import * as mh from "./mahsulot.js";

export const RASM_MAX = 1280;

// ── sozlama kalitlari
export const K_TOKEN = "tg_token";
export const K_GURUH = "tg_guruh";
export const K_YOQILGAN = "tg_yoqilgan";
export const K_KUNLIK_VAQT = "tg_kunlik_vaqt";
export const K_RASXOD_DAN = "tg_rasxod_dan";
export const K_OFFSET = "tg_offset";
export const K_KECHIKTIRISH = "tg_kechiktirish";

// ── tugma matnlari
export const ALBATTA_TUGMA = "Albatta! ✅";
export const DARS_ALBATTA_TUGMA = "Qatnashdim ✅";
export const YOQ_TUGMA = "Hali yo'q ⏳";
export const QAZO_TUGMA = "Qazo bo'ldi 🕌";
export const MENYU_TUGMA = "Menyuyimizda nimalar bor 🍲";
export const MENYU_SOROV = "Bugun nima pishirasiz? 🍲";

const _ROL_BLOK = {
  oshpaz: [
    "👨‍🍳 {tag}, bugun oshxona sizniki 😄  ({vaqt})",
    "Bugungi missiya: hammamizni och qoldirmaslik 🍳",
  ],
  yuvuvchi: [
    "🍽 {tag}, bugun rakovina sizni kutyapti 😄  ({vaqt})",
    "Missiya: idishlarni ertalabgacha qoldirmaslik 🫡",
  ],
};

const _ROL_ESLATMA = {
  oshpaz: "bugungi oshxona missiyasi nima bo'ldi?",
  yuvuvchi: "rakovina bilan ishlar hal bo'ldimi?",
};

const _BOSH_IBORA = [
  "Yangi kun, yangi vazifalar! 💪",
  "Bugun ham ajoyib kun bo'lsin! ☀️",
  "Kun boshlandi — ishga tushamiz 🚀",
  "Hammaga xayrli kun! 🌤",
  "Bugungi reja tayyor 📋",
  "Kun yaxshi o'tsin! ✨",
  "Ishlarni tartib bilan bajaramiz 🗓",
];

// Eslatma oynalarining bir martalik so'rovlari — 30 kundan eski rasxod/yutuq
// e'lon qilinmaydi (Python'da chegara yo'q edi: `eski_izlarni_tozala` 60 kunlik
// `yuborilgan` kalitlarini o'chirgach, ular QAYTA e'lon qilinardi).
export const ELON_KUN = 30;

const { darsmi, OGOH_DAQIQA, KECHIKISH_DAQIQA } = dars;

// ═══════════════════════════════════════════════════════════ yordamchi

// xabar.py:111
function _tanla(royxat, urugh) {
  return royxat[Math.trunc(Number(urugh)) % royxat.length];
}

// xabar.py:116
export function _teg(nom, telegram) {
  if (telegram) return `<b>@${telegram}</b>`;
  return `<b>${nom}</b>`;
}

/** html.escape(x) — quote=True (Python birlamchisi). */
function _escq(x) {
  return tg.e(x).replaceAll('"', "&quot;").replaceAll("'", "&#x27;");
}

// xabar.py:128
export function _ish_belgi(v) {
  const nom = String(v.nom || "").toLowerCase();
  if (nom.includes("musor")) return "🗑";
  if (nom.includes("dasturxon")) return "🍽";
  if (nom.includes("plita") || nom.includes("gaz")) return "🔥";
  return "📌";
}

/**
 * Bir martalik o'qish: vazifa turlari (rollar, shaxsiy, uborka qadamlari),
 * odamlar, menyu. Kunlik vazifalar sana bo'yicha keshlanadi.
 */
export async function _kontekst(db) {
  const [turlar, nt, qadam, odamlar, menyu] = await Promise.all([
    db.q("SELECT * FROM vazifa_turi WHERE ochirilgan=0 ORDER BY tartib, id"),
    vz.navbat_turi(db),
    db.q("SELECT q.turi_id, q.nom FROM ish_qadam q JOIN vazifa_turi t ON t.id=q.turi_id" +
      " WHERE q.ochirilgan=0 AND t.ochirilgan=0 AND t.haftalik=1 ORDER BY q.turi_id, q.tartib, q.id"),
    db.q("SELECT * FROM odam ORDER BY tartib, id"),
    db.q1("SELECT 1 x FROM menyu WHERE ochirilgan=0 LIMIT 1"),
  ]);
  const turId = new Map(turlar.map((t) => [t.id, t]));
  // vz.tur_ergash(nt.id): ergash o'chirilgan bo'lsa — null.
  const erg = nt && nt.ergash_turi_id ? turId.get(nt.ergash_turi_id) ?? null : null;
  const qadamMap = new Map();
  for (const q of qadam) {
    if (!qadamMap.has(q.turi_id)) qadamMap.set(q.turi_id, []);
    qadamMap.get(q.turi_id).push(q.nom);
  }
  return {
    nt, erg,
    uborka: new Map(turlar.filter((t) => t.haftalik === 1).map((t) => [t.nom, t.id])),
    shaxsiy: new Set(turlar.filter((t) => t.shaxsiy === 1).map((t) => t.nom)),
    qadam: qadamMap,
    odam: new Map(odamlar.map((o) => [o.id, o])),
    faol: odamlar.filter((o) => o.faol === 1).map((o) => o.id),
    menyuBor: menyu != null,
    kunlar: new Map(),
  };
}

const _k = async (db, ctx) => ctx ?? _kontekst(db);

/** vz.kun(db, sana, odam_id) — sana bo'yicha keshdan. */
async function _kun(db, ctx, sana, odam_id = null) {
  const iso = vz._sana(sana);
  if (!ctx.kunlar.has(iso)) ctx.kunlar.set(iso, await vz.kun(db, iso));
  const r = ctx.kunlar.get(iso);
  return odam_id ? r.filter((v) => v.odam_id === odam_id) : r;
}

// xabar.py:123
function _odam_nom_telegram(ctx, odam_id) {
  const r = ctx.odam.get(odam_id);
  return r ? [r.nom, r.telegram] : ["?", null];
}

// xabar.py:139
export async function _rol(db, v, ctx = null) {
  ctx = await _k(db, ctx);
  if (ctx.nt && v.nom === ctx.nt.nom) return "oshpaz";
  if (ctx.nt && ctx.erg && v.nom === ctx.erg.nom) return "yuvuvchi";
  if (ctx.uborka.has(v.nom)) return "uborka";
  return null;
}

// xabar.py:153
const _menyu_qiymati = (v) => ("menyu" in v ? v.menyu : null);

// ═══════════════════════════════════════════════════════════ sozlamalar

async function _sozlamalar_xom(db, kalitlar) {
  const r = await db.q(
    `SELECT kalit, qiymat FROM sozlama WHERE kalit IN (${kalitlar.map(() => "?").join(",")})`, ...kalitlar);
  return new Map(r.map((x) => [x.kalit, x.qiymat]));
}

function _sozlama_obyekt(m) {
  return {
    token: m.get(K_TOKEN) ?? "",
    guruh: m.get(K_GURUH) ?? "",
    yoqilgan: (m.get(K_YOQILGAN) ?? "0") === "1",
    kunlik_vaqt: m.get(K_KUNLIK_VAQT) ?? "08:00",
  };
}

// xabar.py:159
export async function sozlamalar(db) {
  return _sozlama_obyekt(await _sozlamalar_xom(db, [K_TOKEN, K_GURUH, K_YOQILGAN, K_KUNLIK_VAQT]));
}

// xabar.py:187
export async function sozlangami(db) {
  const s = await sozlamalar(db);
  return !!(s.yoqilgan && s.token && s.guruh);
}

// xabar.py:199
export async function odam_chati(db, odam_id) {
  const r = await db.q1("SELECT tg_chat FROM odam WHERE id=?", odam_id);
  return r ? r.tg_chat : null;
}

// xabar.py:204
export async function kechiktirish_variantlari(db) {
  const xom = await db.sozlama(K_KECHIKTIRISH, "");
  if (xom) {
    try {
      const q = xom.split(",").filter((x) => x.trim()).map((x) => vz._int(x.trim()));
      if (q.length && q.every((v) => v > 0)) return q.slice(0, 4);
    } catch { /* noto'g'ri qiymat — birlamchi */ }
  }
  return [...vz.KECHIKTIRISH];
}

// ═══════════════════════════════════════════════════════════ /start → chat

// xabar.py:231
export async function _chatni_eslab_qol(db, update) {
  const msg = update.message || {};
  const chat = msg.chat || {};
  if (chat.type !== "private") return null;
  const username = (msg.from || {}).username;
  if (!username) return null;
  const r = await db.q1(
    "SELECT id, nom, tg_chat FROM odam" +
    " WHERE faol=1 AND telegram IS NOT NULL AND LOWER(telegram)=LOWER(?)", username);
  if (!r || r.tg_chat != null) return null;
  await db.apply("odam", "UPDATE", { tg_chat: chat.id }, r.id, `Telegram chat bog'landi: ${r.nom}`);
  return r.id;
}

// ═══════════════════════════════════════════════════ telefondan mahsulot rasmi

// xabar.py:264
export async function _uy_azosi(db, msg) {
  const username = (msg.from || {}).username;
  if (!username) return null;
  return db.q1("SELECT id, nom FROM odam WHERE faol=1 AND telegram IS NOT NULL" +
    " AND LOWER(telegram)=LOWER(?)", username);
}

// xabar.py:272
export function _rasm_fayl_id(msg) {
  const ol = msg.photo || [];
  if (ol.length) {
    const mos = ol.filter((p) => Math.max(p.width || 0, p.height || 0) <= RASM_MAX);
    return (mos.length ? mos[mos.length - 1] : ol[0]).file_id;
  }
  const h = msg.document || {};
  if (String(h.mime_type ?? "").startsWith("image/")) return h.file_id ?? null;
  return null;
}

/** PurePosixPath(yol).suffix */
function _suffix(yol) {
  const nom = String(yol).split("/").pop();
  const i = nom.lastIndexOf(".");
  return i > 0 && i < nom.length - 1 ? nom.slice(i) : "";
}

// xabar.py:295
export async function _rasmni_ishla(db, msg, token) {
  const chat = msg.chat || {};
  if (chat.type !== "private") return null;
  const fayl_id = _rasm_fayl_id(msg);
  if (!fayl_id || !(await _uy_azosi(db, msg))) return null;

  const javob = async (matn) => {
    try { await tg.xabarYubor(token, chat.id, matn); } catch { /* rasm saqlangani muhimroq */ }
  };

  const izoh = String(msg.caption || "").trim();
  if (!izoh) {
    await javob("Rasm izohiga mahsulot nomini yozing — masalan: <b>Olma</b>");
    return "rasm: izohsiz";
  }
  const topilgan = await mh.nom_boyicha(db, izoh);
  if (!topilgan || !topilgan.length) {
    const ox = await mh.oxshashlar(db, izoh, 5);
    const qosh = ox && ox.length ? "\nBalki: " + ox.map(_escq).join(", ") : "";
    await javob(`«${_escq(izoh)}» nomli mahsulot topilmadi. Nomni dasturdagidek aniq yozing.${qosh}`);
    return `rasm: topilmadi (${izoh})`;
  }
  const m = topilgan[0];
  try {
    const f = (await tg.sorov(token, "getFile", { file_id: fayl_id })) || {};
    const yol = f.file_path || "";
    const bayt = await tg.faylYolYukla(token, yol);
    await mh.rasm_baytdan(db, m.id, bayt, _suffix(yol) || ".jpg");
  } catch (e) {
    await javob(`Rasmni saqlab bo'lmadi: ${_escq(e.message ?? e)}`);
    return `rasm: xato (${e.message ?? e})`;
  }
  await javob(`✔ «${_escq(m.nom)}» ga rasm biriktirildi.`);
  return `rasm: ${m.nom}`;
}

// ═══════════════════════════════════════════════════════════ kunlik xabar

// xabar.py:342
export async function oshpaz_vazifasi(db, sana, ctx = null) {
  ctx = await _k(db, ctx);
  if (!ctx.nt) return null;
  return (await _kun(db, ctx, sana)).find((v) => v.nom === ctx.nt.nom) ?? null;
}

// xabar.py:352
export async function kunlik_klaviatura(db, sana, ctx = null) {
  ctx = await _k(db, ctx);
  if (!ctx.menyuBor) return null;
  const v = await oshpaz_vazifasi(db, sana, ctx);
  if (!v) return null;
  return [[[MENYU_TUGMA, `menyu:${v.id}`]]];
}

// xabar.py:361
export async function _taom_klaviatura(db, vazifa_id) {
  const t = (await mn.royxat(db)).map((x) => [x.nom, `taom:${vazifa_id}:${x.id}`]);
  const r = [];
  for (let i = 0; i < t.length; i += 2) r.push(t.slice(i, i + 2));
  return r;
}

// xabar.py:367
function _holat_belgi(v, ochiq) {
  if (v.holat === vz.BAJARILDI) return "✅";
  if (v.holat === vz.QAZO) return "🕌 qazo —";
  return ochiq;
}

// xabar.py:375
export async function _bitta_blok(db, v, tag, ctx = null) {
  ctx = await _k(db, ctx);
  const rol = await _rol(db, v, ctx);
  if (rol === "oshpaz" || rol === "yuvuvchi") {
    if (v.holat === vz.BAJARILDI) return `${tag} — Rahmat! ✅`;
    const [b1, b2] = _ROL_BLOK[rol];
    const q = [b1.replace("{tag}", () => tag).replace("{vaqt}", () => v.vaqt || ""), b2];
    const menyu = _menyu_qiymati(v);
    if (rol === "oshpaz" && menyu) q.push(`🍲 Bugun: ${menyu}`);
    return q.join("\n");
  }
  if (rol === "uborka") {
    if (v.holat === vz.BAJARILDI) return `🧹 ${tag} ${v.nom} — Rahmat! ✅`;
    const turi = ctx.uborka.get(v.nom);
    const qadamlar = turi != null ? ctx.qadam.get(turi) ?? [] : [];
    const q = [`🧹 ${tag}, bugun general uborka: ${v.nom} (${v.vaqt || ""})`];
    for (const x of qadamlar) q.push(`   • ${x}`);
    return q.join("\n");
  }
  const belgi = _holat_belgi(v, _ish_belgi(v));
  return `${tag}, bugun sizda 👇\n${belgi} ${v.vaqt || ""}  ${v.nom}`.trim();
}

// xabar.py:409
export async function kunlik_odam_matn(db, sana, odam_id, ctx = null) {
  ctx = await _k(db, ctx);
  const tasks = (await _kun(db, ctx, sana, odam_id)).filter((t) => !ctx.shaxsiy.has(t.nom));
  if (!tasks.length) return null;
  const [nom, tgn] = _odam_nom_telegram(ctx, odam_id);
  const teng = _teg(nom, tgn);
  const qisqa = `<b>${nom}</b>`;
  const b = [];
  for (let i = 0; i < tasks.length; i++) b.push(await _bitta_blok(db, tasks[i], i === 0 ? teng : qisqa, ctx));
  return b.join("\n\n");
}

// xabar.py:424
export async function kunlik_bloklar(db, sana, ctx = null) {
  ctx = await _k(db, ctx);
  const natija = [];
  const oshpaz = await oshpaz_vazifasi(db, sana, ctx);
  const oshpaz_odam = oshpaz ? oshpaz.odam_id : null;
  for (const oid of ctx.faol) {
    const tasks = (await _kun(db, ctx, sana, oid)).filter((t) => !ctx.shaxsiy.has(t.nom));
    if (!tasks.length) continue;
    const matn = await kunlik_odam_matn(db, sana, oid, ctx);
    if (!matn) continue;
    natija.push({
      odam_id: oid, matn,
      klaviatura: oid === oshpaz_odam ? await kunlik_klaviatura(db, sana, ctx) : null,
    });
  }
  return natija;
}

// xabar.py:447
export async function kunlik_bosh_matn(db, sana, ctx = null) {
  ctx = await _k(db, ctx);
  const d = vz._sana(sana);
  const sarlavha = `📅 ${vz.KUNLAR[vaqt.weekday(d)]}, ${vaqt.sanaNuqta(d)}`;
  if (!(await kunlik_bloklar(db, d, ctx)).length) {
    return `${sarlavha}\n\nBugun umumiy vazifa yo'q — hammaga bo'sh kun 🎉`;
  }
  return `${sarlavha}\n\n${_tanla(_BOSH_IBORA, vaqt.toordinal(d))}`;
}

// ═══════════════════════════════════════════════════════════ eslatma

// xabar.py:468
export async function dars_ogoh_matn(db, v, ctx = null) {
  ctx = await _k(db, ctx);
  const [nom, tgn] = _odam_nom_telegram(ctx, v.odam_id);
  const q = [`⏰ ${_teg(nom, tgn)}, bugun soat ${v.vaqt} da darsingiz bor:`, `📚 ${v.nom}`];
  if (v.izoh) q.push(`📍 ${v.izoh}`);
  return q.join("\n");
}

// xabar.py:482
export async function eslatma_matn(db, v, ctx = null) {
  ctx = await _k(db, ctx);
  const [nom, tgn] = _odam_nom_telegram(ctx, v.odam_id);
  const tag = _teg(nom, tgn);
  if (darsmi(v)) {
    return [
      `${tag}, ${v.nom} darsi tugadi.`,
      "Davomat: darsda bo'ldingizmi?",
      `«${DARS_ALBATTA_TUGMA}» yoki «${YOQ_TUGMA}» tugmasini bosing.`,
    ].join("\n");
  }
  const rol = await _rol(db, v, ctx);
  const q = [rol === "uborka" ? `${tag}, general uborka — ${v.nom} bajarildimi?` : `${tag}, ${v.nom} bajarildimi?`];
  if (rol === "oshpaz") {
    q.push(_ROL_ESLATMA.oshpaz);
    const menyu = _menyu_qiymati(v);
    if (menyu) q.push(`🍲 Bugun: ${menyu}`);
  } else if (rol === "yuvuvchi") {
    q.push(_ROL_ESLATMA.yuvuvchi);
  }
  q.push(`«${ALBATTA_TUGMA}» yoki «${YOQ_TUGMA}» tugmasini bosing.`);
  return q.join("\n");
}

// ═══════════════════════════════════════════════════════════ shaxsiy

// xabar.py:512
export async function shaxsiy_matn(db, sana, odam_id, ctx = null) {
  ctx = await _k(db, ctx);
  const tasks = (await _kun(db, ctx, sana, odam_id)).filter((t) => ctx.shaxsiy.has(t.nom));
  if (!tasks.length) return null;
  const q = ["🔒 Shaxsiy ro'yxatingiz:"];
  for (const t of tasks) {
    q.push(`${_holat_belgi(t, "⏳")} ${t.vaqt || ""}  ${t.nom}`.trim());
    if (t.izoh) q.push(`      ${t.izoh}`);
  }
  return q.join("\n");
}

// xabar.py:531
export async function shaxsiy_bloklar(db, sana, ctx = null) {
  ctx = await _k(db, ctx);
  const natija = [];
  for (const oid of ctx.faol) {
    const chat = ctx.odam.get(oid)?.tg_chat ?? null;
    if (chat == null) continue;
    const matn = await shaxsiy_matn(db, sana, oid, ctx);
    if (!matn) continue;
    natija.push({ odam_id: oid, matn, chat });
  }
  return natija;
}

// xabar.py:544
export async function shaxsiy_klaviatura(db, sana, odam_id, ctx = null) {
  ctx = await _k(db, ctx);
  const ochiq = (await _kun(db, ctx, sana, odam_id)).filter((t) => ctx.shaxsiy.has(t.nom) && !vz.yopiqmi(t));
  if (!ochiq.length) return null;
  return ochiq.map((t) => {
    let yozuv = darsmi(t) ? DARS_ALBATTA_TUGMA : ALBATTA_TUGMA;
    if (t.vaqt) yozuv = `${yozuv} · ${t.vaqt}`;
    return [[yozuv, `bajar:${t.id}`]];
  });
}

// ═══════════════════════════════════════════════════════════ rasxod

// xabar.py:565
export async function rasxod_matn(db, rasxod_id) {
  const r = await db.q1("SELECT * FROM rasxod WHERE id=? AND ochirilgan=0", rasxod_id);
  if (!r) return null;
  const tolovchi = (await db.q1("SELECT nom FROM odam WHERE id=?", r.kim_toladi)).nom;
  const q = [r.kim_uchun ? "🧾 Boshqa uchun olingan" : "🛒 Yangi umumiy rasxod"];
  if (r.nom) q.push(r.nom);
  q.push(`To'ladi: ${tolovchi} — ${money.fmt_som(r.summa)}`);
  q.push("");
  q.push("Kim qancha ko'taradi:");
  for (const u of await db.q(
    "SELECT u.summa, o.nom, o.telegram FROM ulush u" +
    " JOIN odam o ON o.id=u.odam_id WHERE u.rasxod_id=?" +
    " ORDER BY o.tartib", rasxod_id)) {
    q.push(`${_teg(u.nom, u.telegram)} — ${money.fmt(u.summa)}`);
  }
  return q.join("\n");
}

// ═══════════════════════════════════════════════════════════ yutuq

// xabar.py:588
export async function yutuq_matn(db, y, ctx = null) {
  ctx = await _k(db, ctx);
  const r = ctx.odam.get(y.odam_id);
  const tag = _teg("odam" in y ? y.odam : "", r ? r.telegram : null);
  return `🏅 ${tag} — ${y.nom}!\n${y.izoh}`;
}

// ═══════════════════════════════════════════════════════════ kutilayotgan

/**
 * xabar.py:597 — hozir yuborilishi kerak bo'lgan HAMMA xabar.
 * `hozir` — devor soati Date (vaqt.hozir()).
 */
export async function kutilayotgan(db, hozir = null) {
  hozir = hozir || vaqt.hozir();
  const bugun = vaqt.sanaStr(hozir);
  const endi = vaqt.daqiqaDan(hozir);
  const chegara30 = vaqt.vaqtStr(vaqt.daqiqaQosh(hozir, -ELON_KUN * 1440));

  const [sm, ctx] = await Promise.all([
    _sozlamalar_xom(db, [K_TOKEN, K_GURUH, K_YOQILGAN, K_KUNLIK_VAQT, K_RASXOD_DAN]),
    _kontekst(db),
  ]);
  const s = _sozlama_obyekt(sm);
  const tg_rasxod_dan = sm.get(K_RASXOD_DAN) ?? "";
  const rasxodChegara = tg_rasxod_dan > chegara30 ? tg_rasxod_dan : chegara30;
  const [kunV, rasxodlar, yutuqlar] = await Promise.all([
    _kun(db, ctx, bugun),
    tg_rasxod_dan
      ? db.q("SELECT id FROM rasxod WHERE ochirilgan=0 AND umumiymi=1" +
        " AND yaratilgan>=? ORDER BY yaratilgan, id", rasxodChegara)
      : [],
    db.q("SELECT y.*, o.nom odam FROM yutuq y JOIN odam o ON o.id = y.odam_id" +
      " WHERE y.ochirilgan=0 AND y.sana>=? ORDER BY y.sana DESC, y.id DESC", vaqt.kunQosh(bugun, -ELON_KUN)),
  ]);

  // `yuborilgan` dan faqat shu daqiqada tekshiriladigan kalitlar (PK bo'yicha).
  const nomzod = [`kunlik:${bugun}`];
  for (const oid of ctx.faol) nomzod.push(`kunlik:${bugun}:odam:${oid}`, `shaxsiy:${bugun}:odam:${oid}`);
  for (const v of kunV) {
    nomzod.push(`vazifa:${v.id}` + (v.kechiktirildi ? `:${v.kechiktirildi}` : ""), `dars_ogoh:${v.id}`);
  }
  for (const r of rasxodlar) nomzod.push(`rasxod:${r.id}`);
  for (const y of yutuqlar) nomzod.push(`yutuq:${y.id}`);
  const yuborilgan = new Set((await db.q(
    "SELECT kalit FROM yuborilgan WHERE kalit IN (SELECT value FROM json_each(?))",
    JSON.stringify(nomzod))).map((r) => r.kalit));

  const natija = [];
  const kv = vaqt.daqiqa(s.kunlik_vaqt);
  if (kv != null && endi >= kv) {
    const bosh = `kunlik:${bugun}`;
    if (!yuborilgan.has(bosh)) {
      natija.push({ turi: "kunlik", kalit: bosh, matn: await kunlik_bosh_matn(db, bugun, ctx), chat: null, klaviatura: null });
    }
    for (const b of await kunlik_bloklar(db, bugun, ctx)) {
      const kalit = `kunlik:${bugun}:odam:${b.odam_id}`;
      if (yuborilgan.has(kalit)) continue;
      const tasks = (await _kun(db, ctx, bugun, b.odam_id)).filter((t) => !ctx.shaxsiy.has(t.nom));
      if (tasks.every((t) => vz.yopiqmi(t))) continue;
      natija.push({ turi: "kunlik", kalit, matn: b.matn, chat: null, klaviatura: b.klaviatura });
    }
    for (const b of await shaxsiy_bloklar(db, bugun, ctx)) {
      const kalit = `shaxsiy:${bugun}:odam:${b.odam_id}`;
      if (yuborilgan.has(kalit)) continue;
      natija.push({
        turi: "shaxsiy", kalit, matn: b.matn, chat: b.chat,
        klaviatura: await shaxsiy_klaviatura(db, bugun, b.odam_id, ctx),
      });
    }
  }

  // ── eslatma: faqat BUGUNGI, vaqti tugagan va bajarilmagan vazifalar
  for (const v of kunV) {
    if (vz.yopiqmi(v)) continue;
    if (vz.kechiktirilganmi(v, hozir)) continue;
    if (v.vaqt == null) continue;
    let tugadi = vz._daqiqa(v.vaqt) + v.davomiylik;
    if (darsmi(v)) tugadi += KECHIKISH_DAQIQA;
    if (endi < tugadi) continue;
    const kech = "kechiktirildi" in v ? v.kechiktirildi : null;
    const kalit = `vazifa:${v.id}` + (kech ? `:${kech}` : "");
    if (yuborilgan.has(kalit)) continue;
    let chat = null;
    if (ctx.shaxsiy.has(v.nom)) {
      chat = ctx.odam.get(v.odam_id)?.tg_chat ?? null;
      if (chat == null) continue;
    }
    natija.push({
      turi: "eslatma", kalit, matn: await eslatma_matn(db, v, ctx), chat, vazifa_id: v.id,
      klaviatura: [[[darsmi(v) ? DARS_ALBATTA_TUGMA : ALBATTA_TUGMA, `bajar:${v.id}`],
        [YOQ_TUGMA, `haliyoq:${v.id}`]]]
        .concat(vz.namozmi(v) ? [[[QAZO_TUGMA, `qazo:${v.id}`]]] : []),
    });
  }

  // ── dars ogohlantirishi: boshlanishidan OGOH_DAQIQA oldin (YAGONA oldindan xabar)
  for (const v of kunV) {
    if (!darsmi(v) || vz.yopiqmi(v)) continue;
    if (v.vaqt == null) continue;
    const bosh = vz._daqiqa(v.vaqt);
    if (!(bosh - OGOH_DAQIQA <= endi && endi < bosh)) continue;
    const kalit = `dars_ogoh:${v.id}`;
    if (yuborilgan.has(kalit)) continue;
    const chat = ctx.odam.get(v.odam_id)?.tg_chat ?? null;
    if (chat == null) continue;
    natija.push({ turi: "dars", kalit, matn: await dars_ogoh_matn(db, v, ctx), chat, klaviatura: null });
  }

  // ── umumiy rasxod e'loni (oxirgi ELON_KUN kun ichida yaratilganlari)
  for (const r of rasxodlar) {
    const kalit = `rasxod:${r.id}`;
    if (yuborilgan.has(kalit)) continue;
    const matn = await rasxod_matn(db, r.id);
    if (!matn) continue;
    natija.push({ turi: "rasxod", kalit, matn, chat: null, klaviatura: null });
  }

  // ── yutuq tabrigi (oxirgi ELON_KUN kun)
  for (const y of yutuqlar) {
    const kalit = `yutuq:${y.id}`;
    if (yuborilgan.has(kalit)) continue;
    natija.push({ turi: "yutuq", kalit, matn: await yutuq_matn(db, y, ctx), chat: null, klaviatura: null });
  }
  return natija;
}

// xabar.py:726 — `yuborilgan` ga xom yozuv (texnik iz, undo'ga tushmaydi).
export async function belgila(db, kalit, xabar_id = null) {
  await db.exec(
    "INSERT INTO yuborilgan(kalit, xabar_id, vaqt) VALUES(?,?,?)" +
    " ON CONFLICT(kalit) DO UPDATE SET xabar_id=excluded.xabar_id",
    kalit, xabar_id ?? null, vaqt.hozirStr());
}

// xabar.py:734
export async function eski_izlarni_tozala(db) {
  await db.exec("DELETE FROM yuborilgan WHERE vaqt < ?",
    vaqt.vaqtStr(vaqt.daqiqaQosh(vaqt.hozir(), -60 * 1440)));
}

// xabar.py:876
export async function yubor_kutilayotgan(db, hozir = null) {
  const s = await sozlamalar(db);
  if (!(s.yoqilgan && s.token && s.guruh)) return [];
  const natija = [];
  for (const x of await kutilayotgan(db, hozir)) {
    const chat = x.chat != null ? x.chat : s.guruh;
    let javob;
    try {
      javob = await tg.xabarYubor(s.token, chat, x.matn, x.klaviatura && x.klaviatura.length ? x.klaviatura : null);
    } catch {
      continue; // bitta xato qolganini to'xtatmaydi
    }
    await belgila(db, x.kalit, (javob || {}).message_id ?? null);
    natija.push(x);
  }
  return natija;
}

// ═══════════════════════════════════════════════════════════ tugmalar

// xabar.py:899
export async function _egasimi(db, odam_id, username) {
  const r = await db.q1("SELECT telegram FROM odam WHERE id=?", odam_id);
  if (!r || !r.telegram) return true;
  return !!username && r.telegram.toLowerCase() === String(username).toLowerCase();
}

// xabar.py:907
export async function tugmani_ishla(db, sorov, token, guruh = null) {
  const data = sorov.data || "";
  const q = data.split(":");
  const amal = q[0];
  const username = (sorov.from || {}).username || "";
  const xabar = sorov.message || {};
  const chat_id = (xabar.chat || {}).id;
  const message_id = xabar.message_id;
  const tahrir = (m) => tg.sorov(token, "editMessageText", { chat_id, message_id, ...m });

  if (amal === "menyu" && q.length === 2) {
    const vid = vz._int(q[1]);
    const v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    await tahrir({
      text: `${MENYU_SOROV}\n(taomni tanlang)`, parse_mode: "HTML",
      reply_markup: tg.klaviaturaJson(await _taom_klaviatura(db, vid)),
    });
  } else if (amal === "taom" && q.length === 3) {
    const vid = vz._int(q[1]), mid = vz._int(q[2]);
    let v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    const taom = await mn.bitta(db, mid);
    if (!taom) return;
    await vz.menyu_qoy(db, vid, taom.nom);
    v = await vz.bitta(db, vid);
    const ctx = await _kontekst(db);
    const [nom, tgn] = _odam_nom_telegram(ctx, v.odam_id);
    const kb = (await kunlik_klaviatura(db, v.sana, ctx)) || [];
    await tahrir({
      text: await _bitta_blok(db, v, _teg(nom, tgn), ctx), parse_mode: "HTML",
      reply_markup: tg.klaviaturaJson(kb),
    });
  } else if (amal === "bajar" && q.length === 2) {
    const vid = vz._int(q[1]);
    let v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    await vz.bajar(db, vid, true);
    v = await vz.bitta(db, vid);
    const ctx = await _kontekst(db);
    const [nom, tgn] = _odam_nom_telegram(ctx, v.odam_id);
    await tahrir({ text: await _bitta_blok(db, v, _teg(nom, tgn), ctx), parse_mode: "HTML" });
  } else if (amal === "qazo" && q.length === 2) {
    const vid = vz._int(q[1]);
    const v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    if (!vz.namozmi(v) || v.holat !== vz.OCHIQ) return;
    await vz.qazo_qil(db, vid);
    await tahrir({
      text: `🕌 ${v.nom} qazo bo'ldi. «${vz.qazo_nomi(v.nom)}» ro'yxatingizga qo'shildi.`,
      parse_mode: "HTML",
    });
  } else if (amal === "haliyoq" && q.length === 2) {
    const vid = vz._int(q[1]);
    const v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    await tahrir({
      text: "Qachon eslataman? ⏳", parse_mode: "HTML",
      reply_markup: tg.klaviaturaJson(await kechiktirish_klaviatura(db, vid)),
    });
  } else if (amal === "kech" && q.length === 3) {
    const vid = vz._int(q[1]), daqiqa = vz._int(q[2]);
    const v = await vz.bitta(db, vid);
    if (!v || !(await _egasimi(db, v.odam_id, username))) return;
    await vz.kechiktir(db, vid, daqiqa);
    await tahrir({ text: `Xop, ${daqiqa} daqiqadan keyin qayta so'rayman ⏳` });
  }
}

// xabar.py:985
export async function kechiktirish_klaviatura(db, vazifa_id) {
  const t = (await kechiktirish_variantlari(db)).map((d) =>
    [d % 60 === 0 ? `${Math.floor(d / 60)} soatdan keyin` : `${d} daqiqadan keyin`, `kech:${vazifa_id}:${d}`]);
  const r = [];
  for (let i = 0; i < t.length; i += 2) r.push(t.slice(i, i + 2));
  return r;
}

// xabar.py:1000
export async function _shaxsiy_azo(db, msg) {
  if ((msg.chat || {}).type !== "private") return null;
  return _uy_azosi(db, msg);
}

/** Tugma aylanib qolmasin — Telegram'ga "qabul qilindi" (xatosi yutiladi). */
async function _javob_ber(token, cb) {
  if (!cb || cb.id == null) return;
  try { await tg.sorov(token, "answerCallbackQuery", { callback_query_id: cb.id }); } catch { /* muhim emas */ }
}

/**
 * xabar.py:1035 — bitta Telegram update (webhook). Natija — log qatorlari.
 * getUpdates/offset YO'Q: webhook har update'ni bir marta beradi.
 */
export async function _bittasini_ishla(db, token, u) {
  const natija = [];
  if ("callback_query" in u) {
    const cb = u.callback_query;
    if (String(cb.data ?? "").startsWith("rx:")) {
      const msg = { ...(cb.message || {}), from: cb.from };
      const azo = await _shaxsiy_azo(db, msg);
      if (azo) {
        natija.push((await tgr.tugma_bosildi(db, token, cb, azo.id)) || "rx: ?");
      } else {
        await _javob_ber(token, cb); // begona — hech kim javob bermasdi
      }
    } else {
      // Python'da bu tugmalarga answerCallbackQuery yuborilmasdi (tugma
      // aylanib turardi) — endi har doim, xato bo'lsa ham, javob beriladi.
      try {
        await tugmani_ishla(db, cb, token, null);
      } finally {
        await _javob_ber(token, cb);
      }
      natija.push(`tugma: ${cb.data ?? "None"}`);
    }
  } else if ("message" in u) {
    const msg = u.message;
    const oid = await _chatni_eslab_qol(db, u);
    if (oid) natija.push(`chat bog'landi: odam#${oid}`);
    const azo = await _shaxsiy_azo(db, msg);
    if (azo && msg.text) {
      // Avval menyu (Moliya / Vazifalar): suhbat o'rtasida menyu tugmasi
      // bosilsa u «sabab» bo'lib yozilib qolmasin.
      const r = (await tgm.matn_keldi(db, token, msg, azo.id))
        || (await tgr.matn_keldi(db, token, msg, azo.id))
        || (await tgm.tushunmadim(db, token, msg.chat.id));
      natija.push(r);
    }
    const r = await _rasmni_ishla(db, msg, token);
    if (r) natija.push(r);
  }
  return natija;
}

export { _bittasini_ishla as bittasini_ishla };
