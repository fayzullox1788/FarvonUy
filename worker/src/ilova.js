// Worker mantig'i — `index.js` uni haqiqiy modullar bilan quradi, testlar
// esa soxta `xabar`/`vazifa`/`dars` bilan (boshqa agentlarning fayllariga
// bog'lanmasdan marshrut va ruxsatni tekshirish uchun).
//
//   fetch:     POST /tg/<TG_MAXFIY>  — Telegram webhook (har doim 200)
//              /sinx/*               — desktop sinxroni (sinx.js)
//              /app, /app/api/*      — Telegram Mini App (miniapp.js, app/)
//              GET /                 — "ok"
//   scheduled: har daqiqa — kutilayotgan xabarlar;
//              Toshkent daqiqasi %10==0 — takroriy vazifa + dars jadvali.

import { Db } from "./db.js";
import * as vaqt from "./vaqt.js";
import * as sinx from "./sinx.js";
import * as miniapp from "./miniapp.js";
import { tengmi } from "./sinx.js";

export const K_GURUHLAR = "tg_korilgan_guruhlar";
const GURUH_MAX = 10;
const GURUH_TURLARI = new Set(["group", "supergroup", "channel"]);

/** Update ichidagi chat (xabar.guruhlarni_top bilan bir xil manbalar + tugma/a'zolik). */
export function updateChati(u) {
  if (!u || typeof u !== "object") return null;
  const m = u.message || u.edited_message || u.channel_post || u.edited_channel_post ||
    u.my_chat_member || u.chat_member || u.chat_join_request || u.callback_query?.message;
  return m?.chat || null;
}

/**
 * Bot ko'rgan guruhlarni `sozlama.tg_korilgan_guruhlar` ga yozadi (JSON ro'yxat,
 * `xabar.guruhlarni_top()` formatida: {id: matn, nom, turi}). Yangisi boshida,
 * ko'pi bilan 10 ta. O'zgarmasa yozilmaydi.
 */
export async function guruhniEslab(db, u) {
  const chat = updateChati(u);
  if (!chat || !GURUH_TURLARI.has(chat.type) || chat.id == null) return false;
  const id = String(chat.id);
  const nom = chat.title || id;
  let royxat = [];
  try {
    const j = JSON.parse((await db.sozlama(K_GURUHLAR, "[]")) || "[]");
    if (Array.isArray(j)) royxat = j.filter((x) => x && typeof x === "object");
  } catch { /* buzilgan qiymat — yangidan */ }
  const bor = royxat.find((x) => String(x.id) === id);
  if (bor && bor.nom === nom && bor.turi === chat.type) return false;
  royxat = [{ id, nom, turi: chat.type }, ...royxat.filter((x) => String(x.id) !== id)].slice(0, GURUH_MAX);
  await db.sozlama_qoy(K_GURUHLAR, JSON.stringify(royxat));
  return true;
}

const matn = (t, status = 200) => new Response(t, { status, headers: { "content-type": "text/plain; charset=utf-8" } });

/** @param {{xabar:any, vazifa:any, dars:any}} m */
export function ilova(m) {
  async function telegram(req, env, db) {
    // Har doim 200: Telegram 200 bo'lmagan javobni cheksiz qayta yuboradi.
    let u;
    try { u = await req.json(); } catch { return matn("ok"); }
    try { await guruhniEslab(db, u); } catch (e) { console.error("guruh yozilmadi:", e); }
    try {
      const token = await db.sozlama("tg_token");
      if (token) await m.xabar.bittasini_ishla(db, token, u);
    } catch (e) {
      console.error("update ishlanmadi:", e?.stack || e);
    }
    return matn("ok");
  }

  async function fetch(req, env, ctx) {
    const url = new URL(req.url);
    const db = new Db(env.DB);
    if (url.pathname.startsWith("/tg/")) {
      const maxfiy = env.TG_MAXFIY;
      const yol = decodeURIComponent(url.pathname.slice(4));
      const sarlavha = req.headers.get("x-telegram-bot-api-secret-token") || "";
      if (req.method !== "POST" || !maxfiy || !tengmi(yol, maxfiy) || !tengmi(sarlavha, maxfiy)) {
        return matn("topilmadi", 404);
      }
      return telegram(req, env, db);
    }
    if (url.pathname === "/app" || url.pathname === "/app/") {
      if (!env.ASSETS) return matn("topilmadi", 404);
      const r = await env.ASSETS.fetch(new Request(new URL("/index.html", url), req));
      const h = new Headers(r.headers);
      h.set("cache-control", "no-cache");
      return new Response(r.body, { status: r.status, headers: h });
    }
    if (url.pathname.startsWith("/app/api/")) {
      try {
        return (await miniapp.ishla(req, env, db)) || matn("topilmadi", 404);
      } catch (e) {
        console.error("miniapp xato:", e?.stack || e);
        return new Response(JSON.stringify({ ok: false, xato: "Server xatosi" }),
          { status: 500, headers: { "content-type": "application/json; charset=utf-8" } });
      }
    }
    if (url.pathname.startsWith("/sinx/")) {
      try {
        return await sinx.ishla(req, env, db);
      } catch (e) {
        console.error("sinx xato:", e?.stack || e);
        return new Response(JSON.stringify({ ok: false, xato: String(e?.message || e) }),
          { status: 500, headers: { "content-type": "application/json; charset=utf-8" } });
      }
    }
    if (url.pathname === "/" && (req.method === "GET" || req.method === "HEAD")) return matn("ok");
    return matn("topilmadi", 404);
  }

  async function scheduled(event, env, ctx) {
    const db = new Db(env.DB);
    const natija = {};
    try {
      const yuborildi = await m.xabar.yubor_kutilayotgan(db, vaqt.hozir());
      natija.yuborildi = yuborildi?.length ?? 0;
      if (natija.yuborildi) {
        try { await m.xabar.eski_izlarni_tozala(db); } catch (e) { console.error("tozalash:", e?.stack || e); }
      }
    } catch (e) { console.error("yubor_kutilayotgan:", e?.stack || e); }

    if (vaqt.daqiqaDan(vaqt.hozir()) % 10 === 0) {
      try { natija.takror = await m.vazifa.takror_toldir(db); } catch (e) { console.error("takror_toldir:", e?.stack || e); }
      try { natija.dars = await m.dars.yangila(db, vaqt.hozir()); } catch (e) { console.error("dars:", e?.stack || e); }
    }
    return natija;
  }

  return { fetch, scheduled };
}
