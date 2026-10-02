// Telegram botning menyusi: «Moliya» va «Vazifalar» — Python `core/tg_menyu.py` egizagi.
//
// Bu fayl HECH NARSA hisoblamaydi. Pul — `ledger` (`v_balans`, juftlik
// qarzlari, tashqi qarz), vazifalar — `vazifa`, rasxod yozish — `tg_rasxod`
// → `rasxod_kirit`. Ko'rsatiladigan hamma narsa SO'RAGAN odamniki (`odam_id`).
import * as money from "./money.js";
import * as tg from "./tg.js";
import * as vaqt from "./vaqt.js";
import * as ledger from "./ledger.js";
import { kun, shaxsiy_nomlari } from "./vazifa.js";
import * as tg_rasxod from "./tg_rasxod.js";

export const MOLIYA = "💰 Moliya";
export const VAZIFALAR = "📋 Vazifalar";
export const ASOSIY = "‹ Asosiy menyu";

export const PULIM = "💵 Qancha pulim bor";
export const AYLANMA = "🔄 Aylanma qarz";
export const TASHQI = "🌐 Tashqaridan qarz";
export const RASXOD = "➕ Rasxod yozish";

export const UY_ISH = "🏠 Uy ishlari";          // uyning umumiy ishidan menga biriktirilgani
export const SHAXSIY = "🔒 Shaxsiy ishlar";
export const DARS = "🎓 Universitet";           // bugungi darslar (EduPage jadvali)
// Eski tugma matnlari — chatda eski klaviatura qolgan bo'lsa ham ishlasin.
export const _ESKI = new Map([
  ["🏠 Bugun uyda qanday vazifalarim bor", UY_ISH],
  ["🎓 Bugun qanday darslarim bor", DARS],
  ["🔒 Bugun shaxsiy qanday ishlarim bor", SHAXSIY],
]);

export const BOSHLASH = new Set(["/start", "/menu", "/menyu", "menyu"]);

// vazifa.py:14,17,693 — holatlar (vazifa.js ga bog'lanmaslik uchun shu yerda).
const BAJARILDI = "bajarildi";
const QAZO = "qazo";
const _yopiqmi = (v) => v.holat === BAJARILDI || v.holat === QAZO;

// tg_menyu.py:47
function _e(x) { return tg.e(x == null ? "None" : x); }

// tg_menyu.py:51
function _som(x) { return _e(money.fmt_som(x)); }

// tg_menyu.py:60
export function _klaviatura(qatorlar) {
  return JSON.stringify({
    keyboard: qatorlar.map((q) => q.map((t) => ({ text: t }))),
    resize_keyboard: true, is_persistent: true,
  });
}

// ═══════════════════════════════════════════════════════════ menyular

// tg_menyu.py:68
export function asosiy_menyu() { return [[MOLIYA, VAZIFALAR]]; }
export function moliya_menyu() { return [[PULIM, AYLANMA], [TASHQI], [RASXOD], [ASOSIY]]; }
export function vazifa_menyu() { return [[UY_ISH, SHAXSIY], [DARS], [ASOSIY]]; }

// ═══════════════════════════════════════════════════════════ moliya

// tg_menyu.py:82
export async function pulim(db, odam_id) {
  const b = await ledger.balans(db, odam_id);
  if (!b) return "Ma'lumot topilmadi.";
  const s = [`<b>💵 ${_e(b.nom)}, sizning pulingiz</b>`, "",
    `Qo'lingizdagi pul: <b>${_som(b.naqd)}</b>`];
  if (b.sof > 0) s.push(`Sizga qarzdorlar: +${_som(b.sof)}`);
  else if (b.sof < 0) s.push(`Siz qarzdorsiz: −${_som(-b.sof)}`);
  s.push(`Hisob-kitobdan keyin qoladi: <b>${_som(b.adolat)}</b>`);
  if (b.tashqi_qoldiq) {
    s.push("", `⚠️ Shundan ${_som(b.tashqi_qoldiq)} — tashqaridan ` +
      "olingan qarz, qaytarilishi kerak.");
  }
  return s.join("\n");
}

// tg_menyu.py:100
export async function aylanma(db) {
  const juftlar = await ledger.juft_qarzlar(db);
  if (!juftlar.length) return "<b>🔄 Aylanma qarz</b>\n\n✔ Hech kim hech kimga qarzdor emas.";
  const s = ["<b>🔄 Aylanma qarz — kim kimga qarzdor</b>", ""];
  for (const j of juftlar) s.push(`• ${_e(j.qarzdor_nom)} → ${_e(j.kreditor_nom)}: <b>${_som(j.summa)}</b>`);
  return s.join("\n");
}

// tg_menyu.py:110
/** Umumiy qarzdan shu odamning HALI qaytarilmagan ulushi. */
export async function _ulush_qoldiq(db, qarz_id, odam_id) {
  return db.skalyar(
    "SELECT COALESCE(SUM(CASE WHEN u.tolov_id IS NULL THEN u.summa" +
    "                         ELSE -u.summa END),0)" +
    " FROM tashqi_ulush u LEFT JOIN tashqi_tolov t ON t.id=u.tolov_id" +
    " WHERE u.qarz_id=? AND u.odam_id=? AND u.ochirilgan=0" +
    "   AND (u.tolov_id IS NULL OR t.ochirilgan=0)", [qarz_id, odam_id]);
}

// tg_menyu.py:121
/** O'zi olgan qarzlar + UMUMIY qarzlardagi o'z ulushi. */
export async function tashqi(db, odam_id) {
  const qarzlar = [];
  for (const r of await ledger.tashqi_qarzlar(db, true)) {
    const ulush = r.umumiy ? await _ulush_qoldiq(db, r.id, odam_id) : null;
    if (r.odam_id === odam_id || ulush) qarzlar.push([r, ulush]);
  }
  if (!qarzlar.length) return "<b>🌐 Tashqaridan qarz</b>\n\n✔ Tashqaridan olingan qarzingiz yo'q.";
  const s = ["<b>🌐 Tashqaridan olingan qarzlar</b>", ""];
  let jami = 0;
  for (const [r, ulush] of qarzlar) {
    const sana = vaqt.sanaNuqta(r.sana);
    s.push(`• <b>${_e(r.kimdan)}</b> — ${_som(r.qoldiq)}` + (r.umumiy ? "  · umumiy" : ""));
    let tafsil = `   ${sana}, ${_e(r.odam_nom)} olgan ${_som(r.summa)}`;
    if (r.qaytgan) tafsil += `, qaytarilgan ${_som(r.qaytgan)}`;
    s.push(tafsil);
    if (r.umumiy) {
      s.push(`   Sizning ulushingiz: <b>${_som(ulush || 0)}</b>`);
      jami += ulush || 0;
    } else {
      jami += r.qoldiq;
    }
    if (r.sabab) s.push(`   ${_e(r.sabab)}`);
  }
  s.push("", `Sizga tushadigani: <b>${_som(jami)}</b>`);
  return s.join("\n");
}

// ═══════════════════════════════════════════════════════════ vazifalar
//
// Uch xil ish ALOHIDA: dars (`manba` = «dars:…»), shaxsiy ish
// (`vazifa_turi.shaxsiy=1`) va uy vazifasi (qolgani). Dars turi ham
// `shaxsiy=1` — shuning uchun darsni avval `manba` bo'yicha ajratamiz.

// tg_menyu.py:165
export function _darsmi(v) { return String(v.manba || "").startsWith("dars:"); }

// tg_menyu.py:169
/** bugun — "YYYY-MM-DD" (Python `date`). */
export async function bugungi(db, odam_id, qism, bugun = null) {
  bugun = bugun || vaqt.bugun();
  const yopiq = await shaxsiy_nomlari(db);
  const bor = yopiq instanceof Set ? (x) => yopiq.has(x) : (x) => [...yopiq].includes(x);
  const natija = [];
  for (const v of await kun(db, bugun, odam_id)) {
    let tur;
    if (_darsmi(v)) tur = "dars";
    else if (bor(v.nom)) tur = "shaxsiy";
    else tur = "uy";
    if (tur === qism) natija.push(v);
  }
  return natija;
}

// tg_menyu.py:186
export function _vazifa_matn(royxat, sarlavha, bosh) {
  if (!royxat.length) return `<b>${sarlavha}</b>\n\n${bosh}`;
  const s = [`<b>${sarlavha}</b>`, ""];
  for (const v of royxat) {
    const belgi = v.holat === BAJARILDI ? "✅" : v.holat === QAZO ? "🕌" : "⏳";
    const vq = v.vaqt ? `${v.vaqt}  ` : "";
    s.push(`${belgi} ${_e(vq)}${_e(v.nom)}`);
    if (v.izoh) s.push(`      ${_e(v.izoh)}`);
  }
  const ochiq = royxat.filter((v) => !_yopiqmi(v)).length;
  s.push("", ochiq ? `${royxat.length} ta, ${ochiq} tasi hali bajarilmagan.`
    : `${royxat.length} ta — hammasi bajarilgan ✔`);
  return s.join("\n");
}

// tg_menyu.py:204
export async function uy_vazifalari(db, odam_id, bugun = null) {
  return _vazifa_matn(await bugungi(db, odam_id, "uy", bugun),
    "🏠 Uy ishlari — bugun sizga biriktirilgan",
    "✔ Bugun sizga uy ishi biriktirilmagan.");
}

export async function darslar(db, odam_id, bugun = null) {
  return _vazifa_matn(await bugungi(db, odam_id, "dars", bugun),
    "🎓 Universitet — bugungi darslar", "✔ Bugun dars yo'q.");
}

export async function shaxsiy_ishlar(db, odam_id, bugun = null) {
  return _vazifa_matn(await bugungi(db, odam_id, "shaxsiy", bugun),
    "🔒 Shaxsiy ishlar — bugun", "✔ Bugun shaxsiy ishingiz yo'q.");
}

// ═══════════════════════════════════════════════════════════ kirish

const _APOSTROFLAR = "ʻʼ’‘`´";

// tg_menyu.py:224
/** Tugma matni ham, qo'lda yozilgani ham bir xil ko'rinishga. */
export function _norm(matn) {
  let t = String(matn || "").toLowerCase().replaceAll("ß", "ss").replaceAll("ς", "σ");
  for (const b of _APOSTROFLAR) t = t.replaceAll(b, "'");
  let x = "";
  for (const c of t) x += (/[\p{L}\p{N}]/u.test(c) || c === "'" || c === " ") ? c : " ";
  return x.split(" ").filter(Boolean).join(" ");
}

// Menyu so'zlari — `_norm` qilingan ko'rinishda.
const _MOLIYA_JAVOBLARI = new Map([
  [_norm(PULIM), pulim], [_norm(TASHQI), tashqi],
  [_norm(UY_ISH), uy_vazifalari], [_norm(DARS), darslar],
  [_norm(SHAXSIY), shaxsiy_ishlar],
  ...[..._ESKI].map(([eski, yangi]) => [_norm(eski),
    new Map([[UY_ISH, uy_vazifalari], [DARS, darslar], [SHAXSIY, shaxsiy_ishlar]]).get(yangi)]),
  ["universitet", darslar], ["darslar", darslar], ["darslarim", darslar],
]);
const _BOSHLASH = new Set([...[...BOSHLASH].map(_norm), _norm(ASOSIY), "start", "menu",
  "asosiy", "bosh menyu"]);

// tg_menyu.py:254
/** Menyu matni → [javob, yangi menyu yoki null]. Menyu emas → null. */
export async function javob(db, matn, odam_id) {
  const n = _norm(matn);
  if (!n) return null;
  if (_BOSHLASH.has(n)) return ["Bo'limni tanlang:", asosiy_menyu()];
  if (n === _norm(MOLIYA)) return ["💰 Moliya — nimani ko'ramiz?", moliya_menyu()];
  if (n === _norm(VAZIFALAR)) return ["📋 Vazifalar — bugungi kun:", vazifa_menyu()];
  if (n === _norm(AYLANMA)) return [await aylanma(db), null];
  if (_MOLIYA_JAVOBLARI.has(n)) return [await _MOLIYA_JAVOBLARI.get(n)(db, odam_id), null];
  return null;
}

// tg_menyu.py:274
/** Hech narsa mos kelmadi — jim qolmaymiz, menyuni qayta beramiz. */
export async function tushunmadim(db, token, chat_id) {
  await tg.sorov(token, "sendMessage", {
    chat_id, text: "Tushunmadim 🙂 Pastdagi menyudan tanlang:",
    reply_markup: _klaviatura(asosiy_menyu()),
  });
  return "menyu: tushunmadim";
}

// tg_menyu.py:282
/** Shaxsiy chatdagi matn menyu tugmasi bo'lsa — javob beradi. */
export async function matn_keldi(db, token, msg, odam_id) {
  const t = String(msg.text || "").trim();
  const chat_id = msg.chat.id;
  if (_norm(t) === _norm(RASXOD)) {
    // Rasxod — dasturdagi oyna bilan bitta mantiq (tg_rasxod → rasxod_kirit).
    await tg_rasxod.boshlash(db, token, chat_id, odam_id);
    return "menyu: rasxod";
  }
  const j = await javob(db, t, odam_id);
  if (j == null) return null;
  const [matn, menyu] = j;
  const maydon = { chat_id, text: matn, parse_mode: "HTML" };
  if (menyu != null) maydon.reply_markup = _klaviatura(menyu);
  await tg.sorov(token, "sendMessage", maydon);
  return `menyu: ${t}`;
}
