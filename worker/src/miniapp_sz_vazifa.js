// Telegram Mini App — «Sozlamalar → Vazifalar»: vazifalarni boshqarish.
// Desktop `VazifaDialog` / `VazifaTafsilot` / `VazifaTurlariSahifa`
// (src/ui/eski/sahifa_vazifalar.py) bilan BITTA mantiq — hamma yozuv `vazifa.js`
// (Python `core/vazifa.py` egizagi) orqali. Uyning har a'zosi boshqaradi (desktopdagidek).
//
//   GET  /app/api/vazifa-boshqaruv?dan=YYYY-MM-DD&kun=8
//        → odamlar, ish turlari (qadamlari bilan), dan..dan+kun-1 kunlarning HAMMA
//          vazifalari (har biriga `ruxsat` — qaysi maydon o'zgaradi va nega)
//   POST …/vazifa                {nom, odam_id, sana, vaqt, davomiylik, izoh,
//                                 takror?: {naqsh, kunlar, oraliq}, navbat?: {tur_id, kunlar}}
//        → qosh | takror_qosh | navbat_biriktir (VazifaDialog._saqla kabi)
//   POST …/vazifa/<id>           {nom?, odam_id?, sana?, vaqt?, davomiylik?, izoh?, hammasi?} → tahrir
//                                hammasi + vaqt (takror): qoida va shu kundan keyingi barcha kunlar
//   POST …/vazifa/<id>/ochir     → shu kun (ochir)
//   POST …/vazifa/<id>/takror-ochir → qoidani bugundan to'xtatish (takror_ochir)
//   GET  …/vazifa/<id>/navbat?odam=  → almashuv oldindan (almashtirish_rejasi)
//   POST …/vazifa/<id>/navbat    {odam_id, usul: almashtir|bersin}
//   POST …/vazifa/<id>/shaxsiy   {shaxsiy} → turining bayrog'i (tur yo'q bo'lsa tur_qosh)
//   POST …/tur                   {nom, davomiylik, shaxsiy} → tur_qosh
//   POST …/tur/<id>              {davomiylik?, shaxsiy?} → tur_davomiylik_qoy / tur_shaxsiy_qoy
//   POST …/tur/<id>/ochir        → tur_ochir
//   POST …/tur/<id>/qadam        {nom} → qadam_qosh
//   POST …/qadam/<id>/ochir      → qadam_ochir
//
// Qator turlari va ruxsat (desktop qoidalari):
//   dars   (`manba LIKE 'dars:%'`) — FAQAT o'qish: EduPage sinxroni nom/sana/vaqt/
//          davomiylik/izoh/odamni har soatda qaytadan yozadi, o'chirilgani qayta tiriladi.
//   navbat (ovqat) — kim faqat `almashtir`/`bersin` bilan (yuvuvchi o'zi tuzatiladi);
//          nom va sana o'zgarmaydi (navbat va idish shu ikkisi bilan bog'langan).
//   ergash (idish) — kimi oshpazga ergashadi (o'zgarmaydi), nom/sana ham; vaqt/izoh mumkin.
//   takror — bitta kun `tahrir` (qoidaga tegmaydi); o'chirish: shu kun yoki qoida.

import * as vz from "./vazifa.js";
import * as vaqt from "./vaqt.js";
import { toifaAniqla } from "./miniapp.js";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

export const YOL = "/app/api/vazifa-boshqaruv";
const SANA = /^\d{4}-\d{2}-\d{2}$/;
const idOl = (x) => {
  const n = Number(x);
  return Number.isInteger(n) && n > 0 ? n : null;
};

/** Qatorning turi: dars | navbat | ergash | takror | oddiy. */
export function qatorTuri(v, navbatNom, ergashNom) {
  if (String(v.manba || "").startsWith("dars:")) return "dars";
  if (navbatNom && v.nom === navbatNom) return "navbat";
  if (ergashNom && v.nom === ergashNom) return "ergash";
  if (vz.takrorlimi(v)) return "takror";
  return "oddiy";
}

const HAMMASI = { nom: true, sana: true, kim: true, vaqt: true, davomiylik: true, izoh: true };

/** Qaysi maydon o'zgaradi, qanday o'chiriladi va nega — server ham shu bilan tekshiradi. */
export function ruxsat(tur, takrorTirik) {
  switch (tur) {
    case "dars":
      return { maydon: { nom: false, sana: false, kim: false, vaqt: false, davomiylik: false, izoh: false },
        ochir: false, navbat: false, shaxsiy: false,
        izoh: "Dars jadvalidan (EduPage) keladi — sinxron har soatda qaytadan yozadi, shuning uchun bu yerda o‘zgartirilmaydi." };
    case "navbat":
      return { maydon: { ...HAMMASI, nom: false, sana: false, kim: false }, ochir: true, navbat: true, shaxsiy: true,
        izoh: "Ovqat navbati: kimligi «Almashtirish» yoki «Faqat shu kunni berish» bilan o‘zgaradi — idish yuvuvchi ham o‘zi to‘g‘rilanadi." };
    case "ergash":
      return { maydon: { ...HAMMASI, nom: false, sana: false, kim: false }, ochir: true, navbat: false, shaxsiy: true,
        izoh: "Idishni ovqat qilgan odamning o‘zi yuvadi — kimligi ovqat navbati bilan birga o‘zgaradi." };
    case "takror":
      return { maydon: { ...HAMMASI }, ochir: true, navbat: false, shaxsiy: true, takror: takrorTirik,
        izoh: takrorTirik ? "Takroriy vazifaning bitta kuni — o‘zgartirish faqat shu kunga tegadi, qoidaga emas."
          : "Takror qoidasi to‘xtatilgan — bu kun alohida qolgan." };
    default:
      return { maydon: { ...HAMMASI }, ochir: true, navbat: false, shaxsiy: true, izoh: "" };
  }
}

/** Kontekst: navbat/ergash nomlari, shaxsiy va «uy» turlari, dars fanlari. */
async function kontekst(db) {
  const [nt, turlar, darsNomlar] = await Promise.all([
    vz.navbat_turi(db),
    vz.turlar(db),
    db.q("SELECT DISTINCT nom FROM vazifa WHERE ochirilgan=0 AND manba LIKE 'dars:%'"),
  ]);
  const erg = nt ? await vz.tur_ergash(db, nt.id) : null;
  return {
    nt, erg, turlar,
    navbatNom: nt?.nom ?? null,
    ergashNom: erg?.nom ?? null,
    turNom: new Map(turlar.map((t) => [t.nom, t])),
    shaxsiy: new Set(turlar.filter((t) => t.shaxsiy).map((t) => t.nom)),
    uy: new Set(turlar.filter((t) => !t.shaxsiy).map((t) => t.nom)),
    dars: new Set(darsNomlar.map((r) => r.nom)),
  };
}

async function qatorKorinish(db, v, k, takrorKesh) {
  const tur = qatorTuri(v, k.navbatNom, k.ergashNom);
  let takror = null;
  if (tur === "takror") {
    const tid = Number(String(v.manba).split(":")[1]);
    if (!takrorKesh.has(tid)) takrorKesh.set(tid, await vz.takror_egasi(db, v));
    const t = takrorKesh.get(tid);
    if (t) takror = { id: t.id, tavsif: vz.takror_tavsif(t) };
  }
  const tt = k.turNom.get(v.nom);
  return {
    id: v.id, nom: v.nom, odam_id: v.odam_id, sana: v.sana, vaqt: v.vaqt, davomiylik: v.davomiylik,
    izoh: v.izoh, holat: v.holat, menyu: v.menyu ?? null,
    toifa: toifaAniqla(v, k.shaxsiy, k.uy),
    tur, tur_id: tt ? tt.id : null, shaxsiy: k.shaxsiy.has(v.nom),
    takror, ruxsat: ruxsat(tur, Boolean(takror)),
  };
}

export async function holat(db, odam, dan, kun = 8) {
  const gacha = vaqt.kunQosh(dan, kun - 1);
  const [k, odamlar, qatorlar, qadamlar] = await Promise.all([
    kontekst(db),
    db.q("SELECT id, nom, rang FROM odam WHERE faol=1 ORDER BY tartib, id"),
    vz.oraliq(db, dan, gacha),
    db.q("SELECT q.id, q.turi_id, q.nom FROM ish_qadam q JOIN vazifa_turi t ON t.id=q.turi_id" +
      " WHERE q.ochirilgan=0 AND t.ochirilgan=0 ORDER BY q.turi_id, q.tartib, q.id"),
  ]);
  const kesh = new Map();
  const vazifalar = [];
  for (const v of qatorlar) vazifalar.push(await qatorKorinish(db, v, k, kesh));
  return {
    ok: true, men: odam.id, bugun: vaqt.bugun(), dan, gacha,
    odamlar,
    turlar: k.turlar.map((t) => ({
      id: t.id, nom: t.nom, davomiylik: t.davomiylik, shaxsiy: Boolean(t.shaxsiy),
      navbat: Boolean(t.navbat), haftalik: Boolean(t.haftalik),
      ergash: Boolean(k.erg && k.erg.id === t.id), dars: k.dars.has(t.nom),
      qadamlar: qadamlar.filter((q) => q.turi_id === t.id).map((q) => ({ id: q.id, nom: q.nom })),
    })),
    navbat: k.nt ? { tur_id: k.nt.id, nom: k.nt.nom, ergash: k.erg?.nom ?? null } : null,
    vazifalar,
  };
}

const MAYDON_KALIT = { nom: "nom", sana: "sana", odam_id: "kim", vaqt: "vaqt", davomiylik: "davomiylik", izoh: "izoh" };
const MAYDON_NOM = { nom: "nomi", sana: "kuni", kim: "kim bajarishi", vaqt: "vaqti", davomiylik: "davomiyligi", izoh: "izohi" };

async function vazifaVaRuxsat(db, id) {
  const v = await vz.bitta(db, id);
  if (!v) return { v: null };
  const k = await kontekst(db);
  const tur = qatorTuri(v, k.navbatNom, k.ergashNom);
  const tirik = tur === "takror" ? Boolean(await vz.takror_egasi(db, v)) : false;
  return { v, k, tur, r: ruxsat(tur, tirik) };
}

/** /app/api/vazifa-boshqaruv* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam) {
  if (yol !== YOL && !yol.startsWith(YOL + "/")) return null;
  const qism = yol.slice(YOL.length).split("/").filter(Boolean);
  try {
    if (req.method === "GET") {
      if (!qism.length) {
        const dan = url.searchParams.get("dan") || vaqt.bugun();
        if (!SANA.test(dan)) return xato("Sana noto'g'ri");
        const kun = Math.min(31, Math.max(1, Number(url.searchParams.get("kun")) || 8));
        return json(await holat(db, odam, dan, kun));
      }
      if (qism[0] === "vazifa" && qism[2] === "navbat" && qism.length === 3) {
        const id = idOl(qism[1]); const kim = idOl(url.searchParams.get("odam"));
        if (!id || !kim) return xato("Noto'g'ri so'rov");
        const { v, r } = await vazifaVaRuxsat(db, id);
        if (!v) return xato("Vazifa topilmadi", 404);
        if (!r.navbat) return xato("Bu vazifa navbatli emas");
        try {
          const p = await vz.almashtirish_rejasi(db, id, kim);
          return json({ ok: true, mumkin: true, sana: p.vazifa.sana, juft_sana: p.juft.sana,
            eski: await vz._odam_nom(db, p.eski_odam), yangi: await vz._odam_nom(db, p.yangi_odam) });
        } catch (e) {
          return json({ ok: true, mumkin: false, sabab: String(e?.message || e) });
        }
      }
      return xato("Topilmadi", 404);
    }

    if (req.method !== "POST") return xato("Topilmadi", 404);
    let b;
    try { b = await req.json(); } catch { return xato("JSON noto'g'ri"); }
    if (!b || typeof b !== "object") return xato("JSON noto'g'ri");

    // ── yangi vazifa (VazifaDialog._saqla) ──
    if (qism.length === 1 && qism[0] === "vazifa") {
      const odam_id = idOl(b.odam_id);
      if (!odam_id) return xato("Kim bajarishini tanlang");
      const sana = String(b.sana || "");
      if (!SANA.test(sana)) return xato("Sana noto'g'ri");
      const vq = b.vaqt || null;
      if (b.navbat) {
        const tid = idOl(b.navbat.tur_id);
        const t = tid ? await vz.tur_bitta(db, tid) : null;
        if (!t || !t.navbat) return xato("Navbatli ish turi topilmadi");
        const n = await vz.navbat_biriktir(db, tid, odam_id, sana, vq, b.navbat.kunlar ?? 7);
        return json({ ok: true, soni: n });
      }
      if (b.takror) {
        const id = await vz.takror_qosh(db, b.nom, odam_id, {
          vaqt: vq, davomiylik: b.davomiylik ?? 60, naqsh: b.takror.naqsh,
          kunlar: b.takror.kunlar ?? null, oraliq: b.takror.oraliq ?? 1, izoh: b.izoh ?? null, boshlanish: sana,
        });
        return json({ ok: true, takror_id: id });
      }
      const id = await vz.qosh(db, b.nom, odam_id, sana, vq, b.davomiylik ?? 60, b.izoh ?? null);
      return json({ ok: true, id });
    }

    // ── bitta vazifa ──
    if (qism[0] === "vazifa" && qism.length >= 2) {
      const id = idOl(qism[1]);
      if (!id) return xato("Topilmadi", 404);
      const { v, k, r } = await vazifaVaRuxsat(db, id);
      if (!v) return xato("Vazifa topilmadi", 404);
      const amal = qism[2] || "";

      if (!amal) {
        const m = {};
        for (const [kalit, rk] of Object.entries(MAYDON_KALIT)) {
          if (!(kalit in b)) continue;
          if (!r.maydon[rk]) return xato(`Bu vazifaning ${MAYDON_NOM[rk]} bu yerda o'zgartirilmaydi. ${r.izoh}`.trim());
          m[kalit] = b[kalit];
        }
        if ("odam_id" in m) {
          m.odam_id = idOl(m.odam_id);
          if (!m.odam_id) return xato("Kim bajarishini tanlang");
        }
        if ("sana" in m && !SANA.test(String(m.sana || ""))) return xato("Sana noto'g'ri");
        if ("vaqt" in m) m.vaqt = m.vaqt || null;
        const t = "vaqt" in m && b.hammasi ? await vz.takror_egasi(db, v) : null;
        if (t) {
          await vz.takror_vaqt_qoy(db, t.id, m.vaqt, v.sana);
          delete m.vaqt;
        }
        if (Object.keys(m).length) await vz.tahrir(db, id, m);
        return json({ ok: true });
      }
      if (amal === "ochir" && qism.length === 3) {
        if (!r.ochir) return xato(r.izoh || "Bu vazifani o'chirib bo'lmaydi");
        await vz.ochir(db, id);
        return json({ ok: true });
      }
      if (amal === "takror-ochir" && qism.length === 3) {
        const t = await vz.takror_egasi(db, v);
        if (!t) return xato("Takroriy vazifa topilmadi");
        const n = await vz.takror_ochir(db, t.id);
        return json({ ok: true, soni: n });
      }
      if (amal === "navbat" && qism.length === 3) {
        if (!r.navbat) return xato("Bu vazifa navbatli emas");
        const kim = idOl(b.odam_id);
        if (!kim) return xato("Kimga berilishini tanlang");
        if (b.usul === "almashtir") return json({ ok: true, ...(await vz.almashtir(db, id, kim)) });
        if (b.usul === "bersin") return json({ ok: true, ...(await vz.bersin(db, id, kim)) });
        return xato("Noma'lum amal");
      }
      if (amal === "shaxsiy" && qism.length === 3) {
        if (!r.shaxsiy) return xato(r.izoh || "Bu vazifaning turi o'zgartirilmaydi");
        const kerak = Boolean(b.shaxsiy);
        const t = k.turNom.get(v.nom);
        if (t) {
          if (k.dars.has(t.nom) && !kerak) return xato("Dars fani shaxsiy bo'lib qolishi kerak — aks holda dars guruhga chiqib ketadi");
          if (Boolean(t.shaxsiy) !== kerak) await vz.tur_shaxsiy_qoy(db, t.id, kerak);
        } else if (kerak) {
          // Bayroq TURDA turadi — bunday nomli tur yo'q bo'lsa, shaxsiy tur yaratiladi
          // (desktop «+ Yangi vazifa turi» → «Shaxsiy» bilan aynan bir xil).
          await vz.tur_qosh(db, v.nom, v.davomiylik, true);
        }
        return json({ ok: true });
      }
      return xato("Topilmadi", 404);
    }

    // ── ish turlari ──
    if (qism[0] === "tur") {
      if (qism.length === 1) {
        const id = await vz.tur_qosh(db, b.nom, b.davomiylik ?? 60, Boolean(b.shaxsiy));
        return json({ ok: true, id });
      }
      const tid = idOl(qism[1]);
      const t = tid ? await vz.tur_bitta(db, tid) : null;
      if (!t) return xato("Vazifa turi topilmadi", 404);
      const darsmi = Boolean(await db.q1(
        "SELECT 1 FROM vazifa WHERE ochirilgan=0 AND manba LIKE 'dars:%' AND nom=? LIMIT 1", t.nom));
      if (qism.length === 2) {
        // Desktop XabarDialog._saqla: o'zgargani alohida chaqiruv bilan.
        if ("shaxsiy" in b && darsmi && !b.shaxsiy) {
          return xato("Dars fani shaxsiy bo'lib qolishi kerak — aks holda dars guruhga chiqib ketadi");
        }
        if ("davomiylik" in b && b.davomiylik !== t.davomiylik) await vz.tur_davomiylik_qoy(db, tid, b.davomiylik);
        if ("shaxsiy" in b && Boolean(b.shaxsiy) !== Boolean(t.shaxsiy)) await vz.tur_shaxsiy_qoy(db, tid, Boolean(b.shaxsiy));
        return json({ ok: true });
      }
      if (qism[2] === "ochir" && qism.length === 3) {
        if (darsmi) return xato("Dars fani — jadval sinxroni uni baribir qaytadan tiklaydi");
        await vz.tur_ochir(db, tid);
        return json({ ok: true });
      }
      if (qism[2] === "qadam" && qism.length === 3) {
        const id = await vz.qadam_qosh(db, tid, b.nom);
        return json({ ok: true, id });
      }
      return xato("Topilmadi", 404);
    }
    if (qism[0] === "qadam" && qism[2] === "ochir" && qism.length === 3) {
      const qid = idOl(qism[1]);
      if (!qid) return xato("Qadam topilmadi", 404);
      await vz.qadam_ochir(db, qid);
      return json({ ok: true });
    }
    return xato("Topilmadi", 404);
  } catch (e) {
    // core funksiyalari foydalanuvchiga tushunarli o'zbekcha matn bilan yiqiladi
    return xato(String(e?.message || e));
  }
}
