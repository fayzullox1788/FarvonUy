// Telegram Bot API — Python `xabar._sorov`/`_xabar_yubor`/`_rasm_yubor` egizagi.
//
// Testlar transportni almashtiradi: `transportQoy(async (metod, maydonlar) => natija)`
// — Python testlaridagi soxta `xb._sorov` yozib oluvchisi bilan bir xil g'oya.
// Har chaqiruv (metod, maydonlar) ko'rinishida yoziladi; parity testi aynan
// shu ro'yxatni Python ro'yxati bilan solishtiradi.

export class TgXato extends Error {}

let _transport = null;
export function transportQoy(fn) { _transport = fn; }

/** POST JSON. `ok=false` bo'lsa TgXato (description bilan). */
export async function sorov(token, metod, maydonlar = {}) {
  // undefined/null maydonlar yuborilmaydi (Python ham None'ni tashlab ketadi).
  const m = {};
  for (const [k, v] of Object.entries(maydonlar)) if (v !== undefined && v !== null) m[k] = v;
  if (_transport) return _transport(metod, m);
  const r = await fetch(`https://api.telegram.org/bot${token}/${metod}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(m),
  });
  const j = await r.json();
  if (!j.ok) throw new TgXato(j.description || `Telegram xato (${r.status})`);
  return j.result;
}

/** Inline klaviatura: [[ [matn, data], ... ], ...] → reply_markup JSON matni. */
export function klaviaturaJson(rows) {
  return JSON.stringify({
    inline_keyboard: rows.map((q) => q.map(([text, callback_data]) => ({ text, callback_data }))),
  });
}

export async function xabarYubor(token, chatId, matn, klaviatura = null) {
  return sorov(token, "sendMessage", {
    chat_id: chatId, text: matn, parse_mode: "HTML",
    reply_markup: klaviatura ? klaviaturaJson(klaviatura) : null,
  });
}

/** "message is not modified" xato emas — yutiladi (Python `_tahrirla_jim`). */
export async function tahrirlaJim(token, maydonlar) {
  try {
    return await sorov(token, "editMessageText", maydonlar);
  } catch (e) {
    if (String(e.message).includes("message is not modified")) return null;
    throw e;
  }
}

/** Rasm baytlari bilan sendPhoto (multipart). */
export async function rasmYubor(token, chatId, baytlar, fayl = "rasm.jpg", izoh = "") {
  if (_transport) return _transport("sendPhoto", { chat_id: chatId, caption: izoh || null, parse_mode: "HTML", fayl });
  const fd = new FormData();
  fd.append("chat_id", String(chatId));
  if (izoh) { fd.append("caption", izoh); fd.append("parse_mode", "HTML"); }
  fd.append("photo", new Blob([baytlar]), fayl);
  const r = await fetch(`https://api.telegram.org/bot${token}/sendPhoto`, { method: "POST", body: fd });
  const j = await r.json();
  if (!j.ok) throw new TgXato(j.description || "sendPhoto xato");
  return j.result;
}

/** getFile + yuklab olish → Uint8Array. */
export async function faylYukla(token, fileId) {
  if (_transport) return _transport("__fayl", { file_id: fileId });
  const f = await sorov(token, "getFile", { file_id: fileId });
  const r = await fetch(`https://api.telegram.org/file/bot${token}/${f.file_path}`);
  if (!r.ok) throw new TgXato(`fayl yuklanmadi (${r.status})`);
  return new Uint8Array(await r.arrayBuffer());
}

/** file_path bo'yicha yuklab olish (Python `xabar._fayl_yukla(token, yol)`).
 *  `getFile` alohida chaqiriladi — fayl kengaytmasi `file_path` dan olinadi. */
export async function faylYolYukla(token, yol) {
  if (_transport) return _transport("__yukla", { yol });
  const r = await fetch(`https://api.telegram.org/file/bot${token}/${yol}`);
  if (!r.ok) throw new TgXato(`Rasmni yuklab bo'lmadi (${r.status})`);
  return new Uint8Array(await r.arrayBuffer());
}

/** html.escape(x, quote=False) */
export function e(x) {
  return String(x ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
