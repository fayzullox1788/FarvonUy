// Telegram Mini App — «Vazifalar» sahifasining API'si.
//
//   GET  /app                       — sahifa (worker/app/index.html, ASSETS)
//   GET  /app/api/vazifalar?sana=   — ochgan odamning shu kungi vazifalari
//   POST /app/api/vazifa            — yangi vazifa {nom, sana, vaqt, davomiylik, toifa, takror?}
//                                     takror=true → «har kuni» qoidasi (takror_qosh)
//   POST /app/api/vazifa/<id>       — {amal: bajarildi|ochiq|kechiktir|bekor|vaqt, daqiqa?,
//                                      vaqt?, hammasi?} — vaqt+hammasi: qoidaga, keyingi kunlarga ham
//   GET  /app/api/namozlar          — o'z namoz qoidalari [{id, nom, vaqt}]
//   POST /app/api/namozlar          — {vaqtlar: {<takror id>: "HH:MM"}} → bugundan keyingi barcha kunlar
//
// Kim ekanini Telegram aytadi: har so'rovda `Authorization: tma <initData>`,
// imzosi bot tokeni bilan tekshiriladi (core.telegram.org/bots/webapps
// «Validating data received via the Mini App»). Odam `odam.tg_chat`
// (shaxsiy chat id = foydalanuvchi id) yoki `odam.telegram` (username)
// bo'yicha topiladi — botdagi `_egasimi` bilan bir xil manba. Faqat O'Z
// vazifalari: boshqa odamning vazifasiga tegish 403.

import { Db } from "./db.js";
import * as demo from "./demo.js";
import * as vz from "./vazifa.js";
import * as vaqt from "./vaqt.js";
import * as rasxodApi from "./miniapp_rasxod.js";
import * as moliyaApi from "./miniapp_moliya.js";
import * as hisobotApi from "./miniapp_hisobot.js";
import * as sozlamaApi from "./miniapp_sozlama.js";
import * as profilApi from "./miniapp_sz_profil.js";
import * as szMahsulotApi from "./miniapp_sz_mahsulot.js";
import * as tolovApi from "./miniapp_sz_tolov.js";
import * as rejaApi from "./miniapp_sz_reja.js";
import * as szVazifaApi from "./miniapp_sz_vazifa.js";

export const TOIFALAR = ["namoz", "shaxsiy", "uy", "darslar", "boshqa"];
const IMZO_MUDDATI = 24 * 3600; // soniya

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

const kodla = new TextEncoder();
async function hmac(kalit, matn) {
  const k = await crypto.subtle.importKey("raw", typeof kalit === "string" ? kodla.encode(kalit) : kalit,
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", k, kodla.encode(matn)));
}
const hex = (b) => [...b].map((x) => x.toString(16).padStart(2, "0")).join("");

/** initData imzosi to'g'ri bo'lsa Telegram foydalanuvchisi, aks holda null. */
export async function initDataTekshir(initData, token, hozirSoniya = Math.floor(Date.now() / 1000)) {
  if (!initData || !token) return null;
  const p = new URLSearchParams(initData);
  const hash = p.get("hash");
  if (!hash) return null;
  p.delete("hash");
  const qator = [...p.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = await hmac("WebAppData", token);
  const togri = hex(await hmac(sir, qator));
  if (togri.length !== hash.length) return null;
  let farq = 0;
  for (let i = 0; i < togri.length; i++) farq |= togri.charCodeAt(i) ^ hash.charCodeAt(i);
  if (farq) return null;
  const vaqtS = Number(p.get("auth_date"));
  if (!vaqtS || hozirSoniya - vaqtS > IMZO_MUDDATI) return null;
  try { return JSON.parse(p.get("user") || "null"); } catch { return null; }
}

export async function odamTop(db, user) {
  if (!user?.id) return null;
  let r = await db.q1("SELECT id, nom FROM odam WHERE faol=1 AND tg_chat=?", String(user.id));
  if (!r && user.id) r = await db.q1("SELECT id, nom FROM odam WHERE faol=1 AND tg_chat=?", user.id);
  if (!r && user.username) {
    r = await db.q1("SELECT id, nom FROM odam WHERE faol=1 AND telegram IS NOT NULL AND lower(telegram)=lower(?)",
      String(user.username).replace(/^@/, ""));
  }
  return r || null;
}

/** Vazifaning kategoriyasi: qo'lda tanlangan `toifa`, bo'lmasa qoidadan. */
export function toifaAniqla(v, shaxsiy, uyTurlari) {
  // Namoz har doim «Namoz» — qo'lda boshqa kategoriya tanlangan bo'lsa ham.
  if (vz.namozmi(v) || vz.qazo_ishimi(v)) return "namoz";
  if (v.toifa && TOIFALAR.includes(v.toifa)) return v.toifa;
  if (String(v.manba || "").startsWith("dars:")) return "darslar";
  if (shaxsiy.has(v.nom)) return "shaxsiy";
  if (uyTurlari.has(v.nom)) return "uy";
  return "boshqa";
}

async function vazifalar(db, odam, sana) {
  const [qatorlar, shaxsiy, turlar, qoidalar] = await Promise.all([
    vz.kun(db, sana, odam.id),
    vz.shaxsiy_nomlari(db),
    db.q("SELECT nom FROM vazifa_turi WHERE ochirilgan=0 AND COALESCE(shaxsiy,0)=0"),
    vz.takrorlar(db),
  ]);
  const qoida = new Map(qoidalar.map((t) => [t.id, t]));
  const takrorOl = (v) => {
    if (!vz.takrorlimi(v)) return null;
    const t = qoida.get(Number(String(v.manba).split(":")[1]));
    return t ? { id: t.id, vaqt: t.vaqt, tavsif: vz.takror_tavsif(t) } : null;
  };
  const uy = new Set(turlar.map((r) => r.nom));
  const h = vaqt.hozir();
  return {
    ok: true,
    odam: odam.nom,
    sana,
    bugun: vaqt.sanaStr(h),
    hozir: vaqt.vaqtStr(h).slice(-8, -3), // "HH:MM"
    vazifalar: qatorlar.map((v) => ({
      id: v.id,
      nom: v.nom,
      vaqt: v.vaqt,
      davomiylik: v.davomiylik,
      holat: v.holat,
      izoh: v.izoh,
      kechiktirildi: v.kechiktirildi,
      toifa: toifaAniqla(v, shaxsiy, uy),
      takror: takrorOl(v),
    })),
  };
}

/** /app/api/* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, env, db) {
  const url = new URL(req.url);
  const yol = url.pathname.replace(/\/+$/, "");
  if (!yol.startsWith("/app/api/")) return null;

  const token = await db.sozlama("tg_token");
  const sarlavha = req.headers.get("authorization") || "";
  const initData = sarlavha.startsWith("tma ") ? sarlavha.slice(4) : "";
  const user = await initDataTekshir(initData, token);
  if (!user) return xato("Telegram orqali oching", 401);
  let odam = await odamTop(db, user);
  if (!odam) return xato("Siz uy a'zolari ro'yxatida yo'qsiz. Avval botga /start yozing.", 403);
  // Demo rejim holati — HAQIQIY bazada (`demo.js`); bot /demo yoki shu yerdan.
  if (yol === "/app/api/demo") {
    if (req.method === "POST") {
      let b = {};
      try { b = await req.json(); } catch { /* bo'sh — almashtirish */ }
      const yoq = typeof b.yoq === "boolean" ? b.yoq : !(await demo.yoqiqmi(db, odam.id));
      await demo.qoy(db, odam.id, yoq);
      return json({ ok: true, yoqiq: yoq, ulangan: !!env?.DEMO_DB });
    }
    return json({ ok: true, yoqiq: await demo.yoqiqmi(db, odam.id), ulangan: !!env?.DEMO_DB });
  }
  // Demo yoqilgan bo'lsa: HAQIQIY uy a'zosi tekshirilgach, qolgan hamma
  // narsa alohida demo D1 dan — o'qish ham, yozish ham. Kirgan odam demo
  // bazaning asosiy odami bo'lib ko'rinadi.
  if (await demo.yoqiqmi(db, odam.id)) {
    if (!env?.DEMO_DB) return xato("Demo baza hali ulanmagan (tools/demo_d1.sh)", 503);
    db = new Db(env.DEMO_DB);
    odam = await demo.demoOdam(db);
    if (!odam) return xato("Demo baza bo'sh", 503);
  }
  if (yol === "/app/api/rasxod" || yol.startsWith("/app/api/rasxod/")) {
    return (await rasxodApi.ishla(req, db, odam, yol)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/moliya" || yol.startsWith("/app/api/moliya/")) {
    return (await moliyaApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/hisobot" || yol.startsWith("/app/api/hisobot/")) {
    return (await hisobotApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/kategoriya" || yol.startsWith("/app/api/kategoriya/")) {
    return (await sozlamaApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/profil" || yol.startsWith("/app/api/profil/")) {
    return (await profilApi.ishla(req, url, yol, db, odam, user)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/mahsulot" || yol.startsWith("/app/api/mahsulot/")) {
    return (await szMahsulotApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/tolov" || yol.startsWith("/app/api/tolov/")) {
    return (await tolovApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === "/app/api/reja" || yol.startsWith("/app/api/reja/")) {
    return (await rejaApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }
  if (yol === szVazifaApi.YOL || yol.startsWith(szVazifaApi.YOL + "/")) {
    return (await szVazifaApi.ishla(req, url, yol, db, odam)) || xato("Topilmadi", 404);
  }

  try {
    if (req.method === "GET" && yol === "/app/api/vazifalar") {
      const sana = url.searchParams.get("sana") || vaqt.bugun();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(sana)) return xato("Sana noto'g'ri");
      return json(await vazifalar(db, odam, sana));
    }
    if (req.method === "GET" && yol === "/app/api/namozlar") {
      const r = await vz.namoz_takrorlari(db, odam.id);
      return json({ ok: true, namozlar: r.map((t) => ({ id: t.id, nom: t.nom, vaqt: t.vaqt })) });
    }

    if (req.method !== "POST") return xato("Topilmadi", 404);
    let b;
    try { b = await req.json(); } catch { return xato("JSON noto'g'ri"); }

    if (yol === "/app/api/namozlar") {
      // Faqat O'Z qoidalari; vaqt bugundan keyingi barcha kunlarga yoziladi.
      const ozi = new Map((await vz.namoz_takrorlari(db, odam.id)).map((t) => [t.id, t]));
      let n = 0;
      for (const [k, vq] of Object.entries(b.vaqtlar || {})) {
        const t = ozi.get(Number(k));
        if (!t) return xato("Bu namoz sizniki emas", 403);
        if ((vq || null) === t.vaqt) continue;
        n += await vz.takror_vaqt_qoy(db, t.id, vq || null);
      }
      return json({ ok: true, soni: n });
    }

    if (yol === "/app/api/vazifa") {
      const toifa = TOIFALAR.includes(b.toifa) ? b.toifa : null;
      if (b.takror) {
        const takror_id = await vz.takror_qosh(db, b.nom, odam.id, {
          vaqt: b.vaqt || null, davomiylik: b.davomiylik || 30, boshlanish: b.sana || vaqt.bugun(), toifa,
        });
        return json({ ok: true, takror_id });
      }
      const id = await vz.qosh(db, b.nom, odam.id, b.sana || vaqt.bugun(), b.vaqt || null,
        b.davomiylik || 30, null, toifa);
      return json({ ok: true, id });
    }

    const m = yol.match(/^\/app\/api\/vazifa\/(\d+)$/);
    if (!m) return xato("Topilmadi", 404);
    const v = await vz.bitta(db, Number(m[1]));
    if (!v) return xato("Vazifa topilmadi", 404);
    if (v.odam_id !== odam.id) return xato("Bu vazifa sizniki emas", 403);

    switch (b.amal) {
      case "bajarildi": await vz.bajar(db, v.id, true); break;
      case "ochiq": await vz.bajar(db, v.id, false); break;
      case "kechiktir": await vz.kechiktir(db, v.id, b.daqiqa || 10); break;
      case "bekor": await vz.ochir(db, v.id); break;
      case "vaqt": {
        // hammasi: «Asr endi 16:30» — qoidaga va shu kundan keyingi barcha kunlarga.
        const t = b.hammasi ? await vz.takror_egasi(db, v) : null;
        if (t) await vz.takror_vaqt_qoy(db, t.id, b.vaqt || null, v.sana);
        else await vz.tahrir(db, v.id, { vaqt: b.vaqt || null });
        break;
      }
      default: return xato("Noma'lum amal");
    }
    return json({ ok: true });
  } catch (e) {
    // core funksiyalari foydalanuvchiga tushunarli matn bilan yiqiladi
    return xato(String(e?.message || e));
  }
}
