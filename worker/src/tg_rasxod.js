// Telegram bot orqali rasxod kiritish — Python `core/tg_rasxod.py` egizagi.
//
// Bu fayl FAQAT suhbat: qaysi savol, qaysi tugma. Rasxodning o'zi —
// `rasxod_kirit.js` dagi `Qoralama` va `saqla()` (dasturdagi oyna bilan bitta
// qoida). Tekshiruv, narx/nom to'ldirish, ulush hisoblash bu yerda YOZILMAYDI.
//
// Suhbat holati `sozlama.tg_rx:<chat>` da (JSON, Python yozgani bilan bir xil
// shakl — o'tish paytida Python yozgan holatni JS davom ettira oladi).
// Telegram chaqiruvlari `tg.js` orqali (Python `_xb()._sorov` o'rniga).
import * as money from "./money.js";
import * as tg from "./tg.js";
import * as vaqt from "./vaqt.js";
import * as mh from "./mahsulot.js";
import * as plan from "./plan.js";
import * as rk from "./rasxod_kirit.js";
import * as entries from "./entries.js";

export const BOSHLASH_TUGMA = "➕ Rasxod";
export const BUYRUQLAR = new Set(["/rasxod", "rasxod", _casefold(BOSHLASH_TUGMA)]);
export const BEKOR_BUYRUQ = new Set(["/bekor", "bekor"]);
export const ESKIRISH_SOAT = 6;   // shundan eski yarim qolgan suhbat hisobga olinmaydi
export const QATORDA = 2;         // tugmalar bir qatorda nechta

function _casefold(s) { return String(s).toLowerCase().replaceAll("ß", "ss").replaceAll("ς", "σ"); }

/** Python `int(s)` — butun son bo'lmasa xato (jim NaN emas). */
function _int(s) {
  if (typeof s === "number") return Math.trunc(s);
  const t = String(s).trim().replaceAll("_", "");
  if (!/^[-+]?\d+$/.test(t)) throw new Error(`invalid literal for int() with base 10: '${s}'`);
  return Number(t);
}

/** Python kod nuqtasi bo'yicha kesish `s[:n]`. */
function _kes(s, n) { return Array.from(String(s)).slice(0, n).join(""); }

// ═══════════════════════════════════════════════════════════ holat

// tg_rasxod.py:46
export function _kalit(chat_id) { return `tg_rx:${chat_id}`; }

/** Python `datetime.fromisoformat` (asosiy shakllar) → Date (devor soati); xato — null. */
function _isodan(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2})(?::?(\d{2})(?::?(\d{2})(?:[.,](\d{1,6}))?)?)?)?$/.exec(String(s));
  if (!m) return null;
  const ms = m[7] ? Math.floor(Number(m[7].padEnd(6, "0")) / 1000) : 0;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0), ms));
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Python `datetime.now().isoformat()` (devor soati). */
function _iso(d) {
  const s = vaqt.vaqtStr(d).replace(" ", "T");
  const ms = d.getUTCMilliseconds();
  return ms ? `${s}.${String(ms * 1000).padStart(6, "0")}` : s;
}

// tg_rasxod.py:50
export async function holat_ol(db, chat_id) {
  const matn = await db.sozlama(_kalit(chat_id), "");
  if (!matn) return null;
  let h, t;
  try {
    h = JSON.parse(matn);
    t = _isodan(h.vaqt);
    if (t == null) throw new Error("vaqt");
  } catch {
    return null;
  }
  if (vaqt.hozir().getTime() - t.getTime() > ESKIRISH_SOAT * 3600 * 1000) return null;
  const q = { ...h.q };
  // JSON.parse butun son kalitlarni saralaydi — asl tartibni matndan olamiz.
  if (q.parametrlar != null) q.parametrlar = new Map(rk.parametrlar_tartibi(matn) ?? Object.entries(q.parametrlar));
  h.q = rk.Qoralama.lugatdan(q);
  return h;
}

// tg_rasxod.py:64
export async function _holat_saqla(db, chat_id, h) {
  const d = { ...h, q: null, vaqt: _iso(vaqt.hozir()) };
  const matn = "{" + Object.keys(d).map((k) =>
    `${JSON.stringify(k)}:${k === "q" ? h.q.lugat_json() : JSON.stringify(d[k] === undefined ? null : d[k])}`)
    .join(",") + "}";
  await db.sozlama_qoy(_kalit(chat_id), matn);
}

// tg_rasxod.py:69
export async function _holat_tozala(db, chat_id) {
  await db.sozlama_qoy(_kalit(chat_id), "");
}

// ═══════════════════════════════════════════════════════════ ko'rinish

// tg_rasxod.py:75 — html.escape(str(x), quote=False); None → "None" (Python str)
export function _e(x) { return tg.e(x == null ? "None" : x); }

// tg_rasxod.py:80
async function _odamlar(db) {
  return db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id");
}

// tg_rasxod.py:84
async function _nom(db, odam_id) {
  return db.skalyar("SELECT nom FROM odam WHERE id=?", [odam_id], "?");
}

// tg_rasxod.py:88
function _qatorlab(tugmalar, n = QATORDA) {
  const r = [];
  for (let i = 0; i < tugmalar.length; i += n) r.push(tugmalar.slice(i, i + n));
  return r;
}

// tg_rasxod.py:92
/** Hozircha tanlanganlar — har ekranning tepasida. */
async function _xulosa(db, q) {
  const s = [];
  if (q.turi_id) s.push(`🗂 ${_e(await mh.yol_nomi(db, q.turi_id))}`);
  if (q.item_id) {
    const it = await db.q1("SELECT nom FROM item WHERE id=?", q.item_id);
    s.push(`📦 ${_e(it ? it.nom : "?")}`);
  }
  if (q.nom) s.push(`✏️ ${_e(q.nom)}`);
  if (q.summa) s.push(`💰 ${_e(money.fmt_som(q.summa))}`);
  return s;
}

// tg_rasxod.py:107
async function _ulush_matn(db, q) {
  let u;
  try {
    u = await rk.ulushlar(db, q);
  } catch (e) {
    if (e instanceof TypeError || e instanceof ReferenceError) throw e;
    return "";
  }
  const s = [];
  for (const x of u) s.push(`   • ${_e(await _nom(db, x.odam_id))}: ${_e(money.fmt(x.summa))}`);
  return s.join("\n");
}

// tg_rasxod.py:116
async function _tur_matn(db, q) {
  if (q.tur === rk.SHAXSIY) return "Shaxsiy";
  if (q.tur === rk.UCHUN) return `${_e(await _nom(db, q.kim_uchun))} uchun`;
  return "Umumiy";
}

// tg_rasxod.py:124
/** [matn, tugmalar] — joriy qadam uchun. Tugma: [yozuv, callback_data]. */
export async function ekran(db, h) {
  const q = h.q, qadam = h.qadam;
  const bosh = ["<b>➕ Yangi rasxod</b>", ...await _xulosa(db, q)];
  const bekor = [["✖ Bekor", "rx:x"]];
  let tug = [];

  if (qadam === "kat") {
    const ota = h.ota ?? null;
    let tugunlar = await mh.daraxt(db);
    let savol;
    if (ota !== null) {
      const tugun = _tugun_top(tugunlar, ota);
      tugunlar = tugun ? tugun.bolalar : [];
      savol = `«${_e(await mh.yol_nomi(db, ota))}» ichidan tanlang:`;
    } else {
      savol = "Kategoriyani tanlang:";
    }
    const k = [];
    for (const t of tugunlar) {
      const belgi = t.bolalar.length ? "📂 " : "";
      k.push([`${belgi}${t.belgi} ${t.nom}`.trim(), `rx:k:${t.id}`]);
    }
    tug = _qatorlab(k);
    if (ota !== null) {
      const yol = (await mh.yol_nomi(db, ota)).split(" › ");
      tug.unshift([[`✔ «${yol[yol.length - 1]}» o'zi`, `rx:kt:${ota}`]]);
      tug.push([["‹ Orqaga", "rx:ko"], ...bekor]);
    } else {
      tug.push(bekor);
    }
    return [[...bosh, "", savol].join("\n"), tug];
  }

  if (qadam === "mah") {
    const k = [];
    for (const it of await plan.turi_itemlari(db, q.turi_id)) {
      let yoz = it.nom;
      if ("ichkida" in it && it.ichkida) yoz = `${it.turi_nom} › ${yoz}`;
      if (it.narx) yoz += ` · ${money.fmt(it.narx)}`;
      k.push([yoz, `rx:m:${it.id}`]);
    }
    tug = [..._qatorlab(k, 1), [["Mahsulotsiz ›", "rx:m:0"]], [["‹ Orqaga", "rx:mo"], ...bekor]];
    return [[...bosh, "", "Mahsulotni tanlang:"].join("\n"), tug];
  }

  if (qadam === "nom") {
    if (q.nom) tug.push([[`✔ «${_kes(q.nom, 40)}»`, "rx:n"]]);
    tug.push(bekor);
    return [[...bosh, "", "✏️ Sabab — nima uchun? <i>Yozib yuboring.</i>"].join("\n"), tug];
  }

  if (qadam === "summa") {
    if (q.summa) tug.push([[`✔ ${money.fmt(q.summa)}`, "rx:s"]]);
    tug.push(bekor);
    return [[...bosh, "", "💰 Summa (so'm)? <i>Yozib yuboring, masalan 25000.</i>"].join("\n"), tug];
  }

  if (qadam === "kim") {
    const k = (await _odamlar(db)).map((o) =>
      [(o.id === q.kim_toladi ? "✔ " : "") + o.nom, `rx:p:${o.id}`]);
    tug = [..._qatorlab(k), bekor];
    return [[...bosh, "", "👤 Kim to'ladi?"].join("\n"), tug];
  }

  if (qadam === "tur") {
    tug = [[["Umumiy", "rx:t:u"], ["Shaxsiy", "rx:t:s"]], [["Boshqa uchun", "rx:t:b"]], bekor];
    return [[...bosh, `👤 ${_e(await _nom(db, q.kim_toladi))} to'ladi`, "", "Qanday rasxod?"].join("\n"), tug];
  }

  if (qadam === "uchun") {
    const k = (await _odamlar(db)).filter((o) => o.id !== q.kim_toladi)
      .map((o) => [o.nom, `rx:u:${o.id}`]);
    tug = [..._qatorlab(k), bekor];
    return [[...bosh, "", "Kim uchun olindi? <i>(u qarzdor bo'ladi, kirim emas)</i>"].join("\n"), tug];
  }

  if (qadam === "bol") {
    const tanlangan = new Set(await rk.qatnashchilar(db, q));
    const k = (await _odamlar(db)).map((o) =>
      [(tanlangan.has(o.id) ? "✅ " : "⬜ ") + o.nom, `rx:q:${o.id}`]);
    tug = [..._qatorlab(k), [["Davom ›", "rx:qd"]], bekor];
    return [[...bosh, "", "Kimlarga teng bo'linadi?", await _ulush_matn(db, q)].join("\n"), tug];
  }

  if (qadam === "tasdiq") {
    const bugun = h.bugun;
    const kecha = vaqt.kunQosh(bugun, -1);
    const satr = [...bosh, `👤 ${_e(await _nom(db, q.kim_toladi))} to'ladi · ${await _tur_matn(db, q)}`];
    if (q.tur === rk.UMUMIY) satr.push(await _ulush_matn(db, q));
    satr.push(`📅 ${vaqt.sanaNuqta(q.sana)}`);
    if (h.xato) satr.push("", `⚠️ ${_e(h.xato)}`);
    tug = [[[(q.sana === bugun ? "✔ " : "") + "Bugun", "rx:d:0"],
      [(q.sana === kecha ? "✔ " : "") + "Kecha", "rx:d:1"]],
    [["💾 Saqlash", "rx:ok"]],
    [["‹ Orqaga", "rx:to"], ...bekor]];
    return [satr.join("\n"), tug];
  }

  return ["Noma'lum qadam.", [bekor]];
}

// tg_rasxod.py:232
function _tugun_top(tugunlar, tid) {
  for (const t of tugunlar) {
    if (t.id === tid) return t;
    const topildi = _tugun_top(t.bolalar, tid);
    if (topildi) return topildi;
  }
  return null;
}

// ═══════════════════════════════════════════════════════════ yuborish

// tg_rasxod.py:249
/**
 * Joriy ekranni ko'rsatadi: eski xabarni tahrirlaydi yoki yangisini yuboradi.
 * `yangi=true` — foydalanuvchi matn yozgan: eski xabar o'chirilib, yangisi pastda.
 */
export async function _chiz(db, token, chat_id, h, yangi = false) {
  const [matn, tug] = await ekran(db, h);
  if (h.xabar && !yangi) {
    try {
      await tg.sorov(token, "editMessageText", {
        chat_id, message_id: h.xabar, text: matn, parse_mode: "HTML",
        reply_markup: tg.klaviaturaJson(tug),
      });
      return;
    } catch (e) {
      if (String(e?.message ?? e).includes("not modified")) return;
    }
  }
  if (h.xabar) {
    try {
      await tg.sorov(token, "deleteMessage", { chat_id, message_id: h.xabar });
    } catch { /* o'chmasa ham davom etamiz */ }
  }
  const r = (await tg.sorov(token, "sendMessage", {
    chat_id, text: matn, parse_mode: "HTML", reply_markup: tg.klaviaturaJson(tug),
  })) || {};
  h.xabar = r.message_id ?? null;
}

// ═══════════════════════════════════════════════════════════ qadamlar

// tg_rasxod.py:281
async function _keyingi_kat_dan(db, h) {
  h.qadam = (await plan.turi_itemlari(db, h.q.turi_id)).length ? "mah" : "nom";
}

// tg_rasxod.py:286
async function _ota(db, tid) {
  return db.skalyar("SELECT ota_id FROM turi WHERE id=?", [tid], null);
}

// tg_rasxod.py:290
export async function boshlash(db, token, chat_id, odam_id, bugun = null) {
  bugun = bugun || vaqt.bugun();
  const h = {
    odam: odam_id, qadam: "kat", ota: null, xabar: null, bugun,
    q: new rk.Qoralama({ sana: bugun, kim_toladi: odam_id, manba: "telegram" }),
  };
  await _chiz(db, token, chat_id, h, true);
  await _holat_saqla(db, chat_id, h);
}

// tg_rasxod.py:299
/** «25000», «25 000», «25.000» → 25000. Kasr va harf — rad (null). */
export function _summa_oqi(matn) {
  let t = String(matn).trim().replaceAll(" ", "").replaceAll(" ", "").replaceAll(".", "");
  t = t.replaceAll(",", "").toLowerCase();
  if (t.endsWith("so'm")) t = t.slice(0, -4);
  if (t.endsWith("som")) t = t.slice(0, -3);
  return /^[0-9]+$/.test(t) && Number(t) > 0 ? Number(t) : null;
}

// tg_rasxod.py:306
/** Shaxsiy chatdagi matn. Rasxodga tegishli bo'lsa — ishlaydi. */
export async function matn_keldi(db, token, msg, odam_id) {
  const chat_id = msg.chat.id;
  const matn = String(msg.text || "").trim();
  if (!matn) return null;
  const kichik = _casefold(matn);

  // /start va menyu — `tg_menyu.js` da (u bu funksiyadan OLDIN chaqiriladi).
  if (BUYRUQLAR.has(kichik)) {
    await boshlash(db, token, chat_id, odam_id);
    return "rx: boshlandi";
  }

  const h = await holat_ol(db, chat_id);
  if (h == null) return null;
  if (BEKOR_BUYRUQ.has(kichik)) {
    await _holat_tozala(db, chat_id);
    await tg.sorov(token, "sendMessage", { chat_id, text: "✖ Bekor qilindi." });
    return "rx: bekor";
  }

  const q = h.q;
  if (h.qadam === "nom") {
    q.nom = _kes(matn, 200);
    h.qadam = "summa";
  } else if (h.qadam === "summa") {
    const s = _summa_oqi(matn);
    if (s == null) {
      await tg.sorov(token, "sendMessage", { chat_id, text: "Summani raqam bilan yozing, masalan: 25000" });
      return "rx: summa xato";
    }
    q.summa = s;
    h.qadam = "kim";
  }
  // Aks holda tugma kutilayotganda matn yozildi — savolni pastga qayta chiqaramiz.
  await _chiz(db, token, chat_id, h, true);
  await _holat_saqla(db, chat_id, h);
  return `rx: ${h.qadam}`;
}

// tg_rasxod.py:346
/** «rx:» bilan boshlanadigan tugma. Boshqasi — null (xabar.js ishlaydi). */
export async function tugma_bosildi(db, token, cb, odam_id) {
  const data = cb.data || "";
  if (!data.startsWith("rx:")) return null;
  const msg = cb.message || {};
  const chat_id = (msg.chat || {}).id ?? null;
  const qism = data.split(":").slice(1);
  const amal = qism[0], arg = qism.length > 1 ? qism[1] : null;

  const javob = async (matn = null) => {
    try {
      await tg.sorov(token, "answerCallbackQuery", {
        callback_query_id: cb.id ?? null, ...(matn ? { text: matn } : {}),
      });
    } catch { /* javob yetmasa ham */ }
  };

  // Saqlangan rasxodni bekor qilish — suhbat tugagandan keyin ham ishlaydi.
  if (amal === "del" && arg && /^\d+$/.test(arg)) {
    const r = await db.q1("SELECT nom FROM rasxod WHERE id=? AND ochirilgan=0", Number(arg));
    if (!r) {
      await javob("Allaqachon bekor qilingan");
      return "rx: del (yo'q)";
    }
    await entries.rasxod_ochir(db, Number(arg));
    await tg.sorov(token, "editMessageText", {
      chat_id, message_id: msg.message_id ?? null,
      text: `↶ Bekor qilindi: ${_e(r.nom)}`, parse_mode: "HTML",
    });
    await javob("Bekor qilindi");
    return `rx: del #${arg}`;
  }

  const h = await holat_ol(db, chat_id);
  if (h == null || (msg.message_id ?? null) !== (h.xabar ?? null)) {
    await javob("Bu eski xabar — «➕ Rasxod» ni qayta bosing");
    return "rx: eski";
  }
  const q = h.q;

  if (amal === "x") {
    await _holat_tozala(db, chat_id);
    await tg.sorov(token, "editMessageText", { chat_id, message_id: h.xabar, text: "✖ Bekor qilindi." });
    await javob();
    return "rx: bekor";
  }

  if (amal === "k" && arg) {
    const tid = _int(arg);
    if (await db.skalyar("SELECT COUNT(*) FROM turi WHERE ota_id=? AND faol=1", [tid])) {
      h.ota = tid;                       // ichiga kiramiz
    } else {
      q.turi_id = tid;
      await _keyingi_kat_dan(db, h);
    }
  } else if (amal === "kt" && arg) {
    q.turi_id = _int(arg);
    await _keyingi_kat_dan(db, h);
  } else if (amal === "ko") {
    h.ota = (h.ota ?? null) !== null ? await _ota(db, h.ota) : null;
  } else if (amal === "mo") {
    // Orqaga — tanlangan kategoriyaning qo'shnilari ko'rinsin.
    h.ota = q.turi_id ? await _ota(db, q.turi_id) : null;
    q.turi_id = null; q.item_id = null;
    h.qadam = "kat";
  } else if (amal === "m" && arg !== null) {
    await rk.mahsulot_tanla(db, q, _int(arg));   // nom va narx — umumiy qoida
    h.qadam = "nom";
    if (q.item_id) {
      await _rasmini_yubor(db, token, chat_id, q.item_id);
      await _chiz(db, token, chat_id, h, true);
      await _holat_saqla(db, chat_id, h);
      await javob();
      return "rx: nom";
    }
  } else if (amal === "n" && q.nom) {
    h.qadam = "summa";
  } else if (amal === "s" && q.summa) {
    h.qadam = "kim";
  } else if (amal === "p" && arg) {
    q.kim_toladi = _int(arg);
    if (q.kim_uchun === q.kim_toladi) q.kim_uchun = null;
    h.qadam = "tur";
  } else if (amal === "t" && ["u", "s", "b"].includes(arg)) {
    q.tur = { u: rk.UMUMIY, s: rk.SHAXSIY, b: rk.UCHUN }[arg];
    if (q.tur === rk.UMUMIY) {
      if (q.parametrlar == null) {
        q.parametrlar = new Map((await rk.qatnashchilar(db, q)).map((i) => [i, 1.0]));
      }
      h.qadam = "bol";
    } else if (q.tur === rk.UCHUN) {
      h.qadam = "uchun";
    } else {
      h.qadam = "tasdiq";
    }
  } else if (amal === "u" && arg) {
    q.kim_uchun = _int(arg);
    h.qadam = "tasdiq";
  } else if (amal === "q" && arg) {
    const oid = _int(arg);
    const p = new Map(q.parametrlar || []);
    if (p.has(oid)) p.delete(oid);
    else p.set(oid, 1.0);
    q.parametrlar = p;
    h.qolda = true;             // sana almashsa ham tanlov saqlansin
  } else if (amal === "qd") {
    h.qadam = "tasdiq";
  } else if (amal === "d" && ["0", "1"].includes(arg)) {
    q.sana = vaqt.kunQosh(h.bugun, -_int(arg));
    // Uyda kim borligi sanaga bog'liq — qayta olinadi, lekin faqat
    // foydalanuvchi kimlarni o'zi tanlamagan bo'lsa.
    if (q.tur === rk.UMUMIY && q.parametrlar != null && !h.qolda) {
      q.parametrlar = new Map((await rk.qatnashchilar(db, new rk.Qoralama({ sana: q.sana })))
        .map((i) => [i, 1.0]));
    }
  } else if (amal === "to") {
    h.qadam = { [rk.UMUMIY]: "bol", [rk.UCHUN]: "uchun" }[q.tur] ?? "tur";
  } else if (amal === "ok") {
    return _saqla(db, token, chat_id, h, javob);
  } else {
    await javob();
    return "rx: noma'lum";
  }

  delete h.xato;
  await _chiz(db, token, chat_id, h);
  await _holat_saqla(db, chat_id, h);
  await javob();
  return `rx: ${h.qadam}`;
}

// tg_rasxod.py:460
async function _saqla(db, token, chat_id, h, javob) {
  const q = h.q;
  let rid;
  try {
    rid = await rk.saqla(db, q);                 // dasturdagi oyna bilan bitta
  } catch (e) {
    const xato = String(e?.message ?? e);
    h.xato = xato;
    await _chiz(db, token, chat_id, h);
    await _holat_saqla(db, chat_id, h);
    await javob("Saqlanmadi");
    return `rx: xato (${xato})`;
  }
  await _holat_tozala(db, chat_id);
  const matn = ["<b>✔ Rasxod saqlandi</b>", ...await _xulosa(db, q),
    `👤 ${_e(await _nom(db, q.kim_toladi))} to'ladi · ${await _tur_matn(db, q)}`,
    `📅 ${vaqt.sanaNuqta(q.sana)}`,
    "", "<i>Dasturda darhol ko'rinadi.</i>"].join("\n");
  await tg.sorov(token, "editMessageText", {
    chat_id, message_id: h.xabar, text: matn, parse_mode: "HTML",
    reply_markup: tg.klaviaturaJson([[["↶ Bekor qilish", `rx:del:${rid}`]]]),
  });
  await javob("Saqlandi");
  return `rx: saqlandi #${rid}`;
}

// tg_rasxod.py:490
/** Mahsulot tanlanganda — uning rasmi va saqlangan ma'lumotlari. */
async function _rasmini_yubor(db, token, chat_id, item_id) {
  const it = await db.q1("SELECT * FROM item WHERE id=?", item_id);
  const baytlar = it ? await mh.rasm_baytlari(db, it.rasm) : null;
  if (!baytlar) return;
  const izoh = [`<b>${_e(it.nom)}</b>`, _e(await mh.yol_nomi(db, it.turi_id)),
    _e(mh.tavsif(it)), _e(it.izoh || "")].filter((x) => x).join("\n");
  try {
    await tg.rasmYubor(token, chat_id, baytlar, it.rasm, izoh);
  } catch { /* rasm yetmasa ham rasxod davom etadi */ }
}
