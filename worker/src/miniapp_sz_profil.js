// Telegram Mini App — Sozlamalar: «Profil», «Uy a’zolari», «Bildirishnomalar»,
// «Ilova sozlamalari» (app/sz_profil.js) API'si.
//
//   GET  /app/api/profil            — to'rttala bo'lim uchun hammasi bitta javobda
//   POST /app/api/profil/nom        {nom} — O'Z ismini o'zgartirish
//                                   (`entries.odam_nomi_ozgartir`, bitta undo)
//   POST /app/api/profil/telegram   — O'Z `odam.telegram` ini Telegram'dagi haqiqiy
//                                   username bilan bog'lash (initData'dan, tanadan EMAS;
//                                   desktop `sahifa_qosh._tg_nom_saqla` bilan bir xil yozuv)
//
// Ruxsat (initData) va ochgan odam (`odam`) — miniapp.js da; `user` — imzosi
// tekshirilgan Telegram foydalanuvchisi.
//
// NIMA O'ZGARTIRILADI, NIMA YO'Q (sinxron egaligi, ../../src/sinx.py):
//   * `odam` qatorlari `apply()` → `ozgarishlar` (toq id) orqali desktopga pull
//     bo'ladi — ism va Telegram nomi shuning uchun XAVFSIZ tahrirlanadi.
//   * `sozlama` jadvalidagi kalitlarning deyarli hammasi DESKTOPNIKI
//     (`sinx.desktop_kalitimi`): desktop har push'da o'z nusxasini yuboradi va
//     server qiymatini bosib ketadi. Shuning uchun tg_yoqilgan, tg_kunlik_vaqt,
//     tg_kechiktirish, uborka_kuni/vaqt, dars_*, asosiy_odam — bu yerda FAQAT
//     O'QILADI («Desktop dasturida o'zgartiriladi»). Token va guruh id hech
//     qachon javobga chiqmaydi.
//   * Odam qo'shish/olib tashlash yo'q — balans va ulushlarga ta'sir qiladi.
//   * Rang: desktop `odam.rang` ni ko'rsatmaydi, rangni id'dan hisoblaydi
//     (`ui/eski/theme.odam_rangi`) — Mini App ham aynan shuni ko'rsatadi; desktopda
//     rang tahrirlash funksiyasi yo'q, demak bu yerda ham yo'q.

import * as xabar from "./xabar.js";
import * as plan from "./plan.js";
import * as vz from "./vazifa.js";
import * as dars from "./dars.js";
import * as vaqt from "./vaqt.js";

/** Worker nashri — Ilova sozlamalarida ko'rinadi (deploy'da yangilanadi). */
export const VERSIYA = "2026.10.02";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const xato = (m, status = 400) => json({ ok: false, xato: m }, status);

// ─────────────────────────────────────────────── desktop bilan bir xil manba

// ui/eski/theme.py:131 (iliq) va :166 (oq) — `ODAM_RANG`. Mini App yorug' fonda,
// shuning uchun «tungi» palitra (quyuq fon uchun ochroq ranglar) olinmaydi.
export const ODAM_RANG = {
  iliq: ["#4A40BE", "#0D7490", "#B0421F", "#9C2C74", "#1D6F3F", "#8A5A12"],
  oq: ["#3E36CC", "#0B7285", "#B23C18", "#9E2470", "#146B3C", "#835310"],
};

// theme.py:273 `odam_rangi` + :287 `_indeks` (butun son kaliti)
export function odam_rangi(odam_id, rejim = "iliq") {
  const p = ODAM_RANG[rejim] || ODAM_RANG.iliq;
  const n = p.length;
  return p[odam_id > 0 ? (((odam_id - 1) % n) + n) % n : 0];
}

// entries.py:495
export async function odam_nomi_ozgartir(db, odam_id, yangi) {
  yangi = String(yangi ?? "").trim();
  if (!yangi) throw new Error("Ism bo'sh bo'lmasin");
  if (await db.q1("SELECT 1 FROM odam WHERE nom=? AND id<>?", yangi, odam_id)) {
    throw new Error(`${yangi} allaqachon bor`);
  }
  const a = db.amal(`Ism o'zgartirildi: ${yangi}`);
  await a.apply("odam", "UPDATE", { nom: yangi }, odam_id);
  await a.commit();
}

// ui/eski/sahifa_qosh.py:1003 `_tg_nom_saqla` — bir xil yozuv va tavsif.
export async function telegram_nomi_qoy(db, odam_id, matn) {
  matn = String(matn ?? "").trim().replace(/^@+/, "") || null;
  const a = db.amal("Telegram nomi o'zgardi");
  await a.apply("odam", "UPDATE", { telegram: matn }, odam_id);
  await a.commit();
}

// xabar.py:192
export async function dm_yoqmaganlar(db) {
  return db.q("SELECT id, nom FROM odam WHERE faol=1 AND telegram IS NOT NULL" +
    " AND telegram<>'' AND tg_chat IS NULL ORDER BY tartib, id");
}

// vazifa.py:312
export async function uborka_kuni(db) {
  let k;
  try { k = vz._int(await db.sozlama(vz.UBORKA_KUNI_KALIT, "6")); } catch { return 6; }
  return k >= 0 && k <= 6 ? k : 6;
}

// vazifa.py:328
export async function uborka_vaqti(db) {
  return db.sozlama(vz.UBORKA_VAQT_KALIT, "10:00");
}

// ─────────────────────────────────────────────────────────────── javob

export const HAFTA_KUNLARI = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];

function dmHolat(o) {
  if (o.tg_chat != null && o.tg_chat !== "") return "yoqilgan";
  return o.telegram ? "start_kerak" : "nom_yoq";
}

async function guruhNomi(db, guruh) {
  if (!guruh) return null;
  try {
    const j = JSON.parse((await db.sozlama("tg_korilgan_guruhlar", "[]")) || "[]");
    const g = Array.isArray(j) ? j.find((x) => x && String(x.id) === String(guruh)) : null;
    return g && g.nom ? String(g.nom) : null;
  } catch { return null; }
}

export async function malumot(db, odam, user = null) {
  const rejim = (await db.sozlama("rejim", "iliq")) === "oq" ? "oq" : "iliq";
  const asosiy = await plan.asosiy_odam(db);
  const qatorlar = await db.q("SELECT id, nom, telegram, tg_chat, faol FROM odam ORDER BY faol DESC, tartib, id");
  const azolar = qatorlar.map((o) => ({
    id: o.id,
    nom: o.nom,
    rang: odam_rangi(o.id, rejim),
    telegram: o.telegram || null,
    dm: dmHolat(o),
    faol: !!o.faol,
    asosiy: o.id === asosiy,
    men: o.id === odam.id,
  }));

  const s = await xabar.sozlamalar(db);
  const yoqmagan = await dm_yoqmaganlar(db);
  const d = await dars.sozlamalar(db);
  const darsOdam = d.odam_id ? await db.q1("SELECT nom FROM odam WHERE id=?", d.odam_id) : null;
  const uk = await uborka_kuni(db);
  const desktop = await db.q1("SELECT MAX(vaqt) v, COUNT(*) n FROM ozgarishlar WHERE id%2=0");
  const server = await db.q1("SELECT MAX(vaqt) v, COUNT(*) n FROM ozgarishlar WHERE id%2=1");

  return {
    ok: true,
    men_id: odam.id,
    tg_username: user?.username ? String(user.username) : null,
    azolar,
    bildirishnoma: {
      sozlangan: !!(s.yoqilgan && s.token && s.guruh),
      yoqilgan: s.yoqilgan,
      token_bor: !!s.token,
      guruh_bor: !!s.guruh,
      guruh_nomi: await guruhNomi(db, s.guruh),
      kunlik_vaqt: s.kunlik_vaqt,
      kechiktirish: await xabar.kechiktirish_variantlari(db),
      dm_yoqmaganlar: yoqmagan.map((r) => r.nom),
    },
    ilova: {
      versiya: VERSIYA,
      hozir: vaqt.hozirStr(),
      desktop_oxirgi: desktop?.v || null,
      desktop_soni: desktop?.n || 0,
      server_oxirgi: server?.v || null,
      uborka: {
        kun: uk,
        kun_nomi: HAFTA_KUNLARI[uk],
        vaqt: await uborka_vaqti(db),
        ishlar: (await vz.uborka_turlari(db)).map((t) => t.nom),
      },
      dars: {
        yoq: d.yoq,
        sinf: d.sinf || null,
        odam: darsOdam ? darsOdam.nom : null,
        tekshirildi: d.tekshirildi || null,
      },
    },
  };
}

/** /app/api/profil* — null qaytarsa marshrut bu modulniki emas. */
export async function ishla(req, url, yol, db, odam, user = null) {
  if (yol !== "/app/api/profil" && !yol.startsWith("/app/api/profil/")) return null;
  try {
    if (yol === "/app/api/profil") {
      if (req.method !== "GET") return xato("Topilmadi", 404);
      return json(await malumot(db, odam, user));
    }
    if (req.method !== "POST") return xato("Topilmadi", 404);
    if (yol === "/app/api/profil/nom") {
      let b;
      try { b = await req.json(); } catch { return xato("JSON noto'g'ri"); }
      const nom = String(b?.nom ?? "").trim();
      if (nom.length > 40) return xato("Ism juda uzun (40 belgigacha)");
      await odam_nomi_ozgartir(db, odam.id, nom);
      return json({ ok: true, nom });
    }
    if (yol === "/app/api/profil/telegram") {
      const un = user?.username ? String(user.username) : "";
      if (!un) return xato("Telegram'da foydalanuvchi nomi (username) yo'q");
      const toza = un.replace(/^@+/, "");
      const r = await db.q1("SELECT telegram FROM odam WHERE id=?", odam.id);
      if (r && r.telegram === toza) return json({ ok: true, telegram: toza });
      // Ikki a'zoda bir xil nom bo'lsa bot kimga yozishini bilmay qoladi.
      const band = await db.q1("SELECT nom FROM odam WHERE id<>? AND faol=1 AND telegram IS NOT NULL" +
        " AND lower(telegram)=lower(?)", odam.id, toza);
      if (band) return xato(`@${toza} allaqachon ${band.nom} uchun yozilgan`);
      await telegram_nomi_qoy(db, odam.id, toza);
      return json({ ok: true, telegram: un.replace(/^@+/, "") });
    }
    return null;
  } catch (e) {
    return xato(String(e?.message || e));
  }
}
