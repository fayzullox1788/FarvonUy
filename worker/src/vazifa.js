// Uy vazifalari — Python `src/core/vazifa.py` ning bot ishlatadigan qismi.
//
// Pulga tegmaydi. Yozuv faqat `db.apply()`/`Amal` orqali, o'chirish —
// `ochirilgan=1`, bir amal = bitta guruh (= bitta D1 batch).
//
// Sanalar JS'da "YYYY-MM-DD" MATN sifatida yuradi (Python `date` o'rniga);
// `takror_sanalari` ham matn ro'yxati qaytaradi.
import * as vaqt from "./vaqt.js";

export const OCHIQ = "ochiq";
export const BAJARILDI = "bajarildi";
export const QAZO = "qazo";

export const KUNLAR = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba",
  "Juma", "Shanba", "Yakshanba"];
export const KUN_QISQA = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

export const UBORKA_KUNI_KALIT = "uborka_kuni";
export const UBORKA_VAQT_KALIT = "uborka_vaqt";

// ─────────────────────────────────────────────────────────── yordamchi

// vazifa.py:37
export function _sana(x) {
  return String(x).slice(0, 10);
}

// vazifa.py:43
export function _daqiqa(v) {
  if (!v) return null;
  const [s, d] = String(v).split(":");
  return Number.parseInt(s, 10) * 60 + Number.parseInt(d, 10);
}

// vazifa.py:51
export function _vaqt_matn(d) {
  return `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(d % 60).padStart(2, "0")}`;
}

/** "dd.mm" / "dd.mm.yyyy" (strftime) */
const _dm = (iso) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;
const _dmy = (iso) => `${_dm(iso)}.${iso.slice(0, 4)}`;

// ───────────────────────────────────────────────────────── vazifa turi

// vazifa.py:101
export async function tur_bitta(db, tur_id) {
  return db.q1("SELECT * FROM vazifa_turi WHERE id=? AND ochirilgan=0", tur_id);
}

// vazifa.py:139
export async function tur_ergash(db, tur_id) {
  const t = await tur_bitta(db, tur_id);
  if (!t || !t.ergash_turi_id) return null;
  return tur_bitta(db, t.ergash_turi_id);
}

// vazifa.py:210
export async function shaxsiy_turlari(db) {
  return db.q("SELECT * FROM vazifa_turi WHERE shaxsiy=1 AND ochirilgan=0 ORDER BY tartib, id");
}

// vazifa.py:215 — Set
export async function shaxsiy_nomlari(db) {
  return new Set((await shaxsiy_turlari(db)).map((t) => t.nom));
}

// vazifa.py:241
export async function qadamlar(db, turi_id) {
  return db.q("SELECT * FROM ish_qadam WHERE turi_id=? AND ochirilgan=0 ORDER BY tartib, id", turi_id);
}

// vazifa.py:246
export async function qadam_nomlari(db, turi_id) {
  return (await qadamlar(db, turi_id)).map((r) => r.nom);
}

// vazifa.py:296
export async function uborka_turlari(db) {
  return db.q("SELECT * FROM vazifa_turi WHERE haftalik=1 AND ochirilgan=0 ORDER BY tartib, id");
}

// vazifa.py:502
export async function navbat_turi(db) {
  return db.q1("SELECT * FROM vazifa_turi WHERE navbat=1 AND ochirilgan=0 ORDER BY tartib LIMIT 1");
}

// ─────────────────────────────────────────────────────────────── o'qish

// vazifa.py:871
export async function bitta(db, vazifa_id) {
  return db.q1("SELECT * FROM vazifa WHERE id=? AND ochirilgan=0", vazifa_id);
}

// vazifa.py:883
export async function oraliq(db, dan, gacha, odam_id = null, shaxsiysiz = false) {
  const p = [_sana(dan), _sana(gacha)];
  let qosh = "";
  if (odam_id) { qosh = " AND v.odam_id=?"; p.push(odam_id); }
  let qatorlar = await db.q(
    "SELECT v.*, o.nom odam, o.rang odam_rang" +
    " FROM vazifa v JOIN odam o ON o.id=v.odam_id" +
    " WHERE v.ochirilgan=0 AND v.sana BETWEEN ? AND ?" + qosh +
    " ORDER BY v.sana, COALESCE(v.vaqt,'99:99'), v.id", ...p);
  if (shaxsiysiz) {
    const yopiq = await shaxsiy_nomlari(db);
    qatorlar = qatorlar.filter((r) => !yopiq.has(r.nom));
  }
  return qatorlar;
}

// vazifa.py:910
export async function kun(db, sana, odam_id = null, shaxsiysiz = false) {
  return oraliq(db, sana, sana, odam_id, shaxsiysiz);
}

// ─────────────────────────────────────────────────────────────── yozish

// vazifa.py:55
export async function _odam_nom(db, odam_id) {
  const r = await db.q1("SELECT nom FROM odam WHERE id=?", odam_id);
  if (!r) throw new Error(`Odam topilmadi: ${odam_id}`);
  return r.nom;
}

// vazifa.py:62
export async function _tekshir(db, nom, odam_id, sana, vaqt_, davomiylik) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Vazifa nomi bo'sh bo'lishi mumkin emas");
  const r = await db.q1("SELECT faol FROM odam WHERE id=?", odam_id);
  if (!r) throw new Error(`Odam topilmadi: ${odam_id}`);
  if (!r.faol) throw new Error("Ro'yxatdan olingan odamga vazifa biriktirilmaydi");
  const iso = _sana(sana);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) throw new Error(`Sana noto'g'ri: ${sana}`);
  if (vaqt_) {
    const d = _daqiqa(vaqt_);
    if (d == null || Number.isNaN(d) || !(d >= 0 && d < 24 * 60)) throw new Error(`Vaqt noto'g'ri: ${vaqt_}`);
    vaqt_ = _vaqt_matn(d);
  } else {
    vaqt_ = null;
  }
  davomiylik = _int(davomiylik);
  if (davomiylik <= 0) throw new Error("Davomiylik musbat bo'lishi kerak");
  return [nom, iso, vaqt_, davomiylik];
}

// vazifa.py:628 (+ Mini App: ixtiyoriy `toifa`)
export async function qosh(db, nom, odam_id, sana, vaqt_ = null, davomiylik = 60, izoh = null, toifa = null) {
  let iso;
  [nom, iso, vaqt_, davomiylik] = await _tekshir(db, nom, odam_id, sana, vaqt_, davomiylik);
  const kim = await _odam_nom(db, odam_id);
  const data = {
    nom, odam_id, sana: iso, vaqt: vaqt_, davomiylik, holat: OCHIQ,
    izoh: String(izoh ?? "").trim() || null,
  };
  if (toifa) data.toifa = toifa;
  const a = db.amal(`Vazifa: ${nom} — ${kim}, ${iso}`);
  const id = await a.apply("vazifa", "INSERT", data);
  await a.commit();
  return id;
}

// vazifa.py:815
export async function ochir(db, vazifa_id) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  await db.apply("vazifa", "DELETE", {}, vazifa_id, `Vazifa o'chirildi: ${v.nom}`);
}

// vazifa.py:668
export async function bajar(db, vazifa_id, bajarildi = true, { a = null } = {}) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  const holat = bajarildi ? BAJARILDI : OCHIQ;
  const oz = !a;
  a ??= db.amal(`Vazifa ${bajarildi ? "bajarildi" : "qayta ochildi"}: ${v.nom}`);
  const h = vaqt.hozir();
  await a.apply("vazifa", "UPDATE", {
    holat,
    // datetime.now().isoformat(timespec="minutes") → "YYYY-MM-DDTHH:MM"
    bajarilgan: bajarildi ? `${vaqt.sanaStr(h)}T${vaqt.vaqtStr(h).slice(11, 16)}` : null,
    kechiktirildi: null,
  }, vazifa_id);
  // Yutuq SHU AMAL ICHIDA. Navbatli yozuv commit'gacha ko'rinmaydi —
  // shuning uchun bajarilayotgan vazifa streakka qo'lda qo'shiladi.
  if (bajarildi) await yutuqlarni_tekshir(db, null, { a, bajarilgan: v });
  if (v.holat === QAZO) {
    for (const q of await qazo_ishlari(db, vazifa_id, true)) {
      await a.apply("vazifa", "DELETE", {}, q.id);
    }
  }
  if (oz) await a.commit();
}

// vazifa.py:693
export function yopiqmi(v) {
  return v.holat === BAJARILDI || v.holat === QAZO;
}

// ─────────────────────────────────────────────────────────────── qazo

export const NAMOZ_SOZLAR = ["namoz", "nomoz", "namaz", "bomdod", "peshin", "asr", "shom", "xufton"];
export const QAZO_QOSHIMCHA = "qazosini o'qish";
export const QAZO_BELGI = "qazo";

// vazifa.py:713
export function qazo_ishimi(v) {
  return v ? String(v.manba ?? "").startsWith(`${QAZO_BELGI}:`) : false;
}

// vazifa.py:717
export function namozmi(v) {
  if (!v || qazo_ishimi(v)) return false;
  // Qo'lda «Namoz» toifasi tanlangan bo'lsa — nomi nima bo'lishidan qat'i nazar.
  if (v.toifa === "namoz") return true;
  const sozlar = String(v.nom || "").toLowerCase().replaceAll("'", " ").split(/\s+/).filter(Boolean);
  return sozlar.some((s) => NAMOZ_SOZLAR.some((n) => s.startsWith(n)));
}

// vazifa.py:725
export function qazo_nomi(nom) {
  return `${nom} — ${QAZO_QOSHIMCHA}`;
}

// vazifa.py:729
export async function qazo_ishlari(db, vazifa_id, faqat_ochiq = false) {
  const shart = faqat_ochiq ? " AND holat=?" : "";
  const p = [`${QAZO_BELGI}:${Math.trunc(Number(vazifa_id))}`, ...(faqat_ochiq ? [OCHIQ] : [])];
  return db.q("SELECT * FROM vazifa WHERE ochirilgan=0 AND manba=?" + shart, ...p);
}

// vazifa.py:736
export async function qazo_qil(db, vazifa_id, bugun = null, { a = null } = {}) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  if (!namozmi(v)) throw new Error(`«${v.nom}» namoz emas`);
  if (v.holat !== OCHIQ) throw new Error("Faqat hali o'qilmagan namoz qazo bo'ladi");
  const asl = _sana(v.sana);
  const b = _sana(bugun || vaqt.bugun());
  const kunS = asl > b ? asl : b;
  const oz = !a;
  a ??= db.amal(`Qazo: ${v.nom} (${_dm(asl)})`);
  await a.apply("vazifa", "UPDATE", { holat: QAZO, bajarilgan: null, kechiktirildi: null }, vazifa_id);
  const id = await a.apply("vazifa", "INSERT", {
    nom: qazo_nomi(v.nom), odam_id: v.odam_id, sana: kunS, vaqt: null,
    davomiylik: v.davomiylik, holat: OCHIQ,
    izoh: `${_dmy(asl)} kungi ${v.nom}`,
    manba: `${QAZO_BELGI}:${Math.trunc(Number(vazifa_id))}`,
    yaratilgan: vaqt.hozirStr(), // D1'da DEFAULT localtime = UTC bo'lardi
  });
  if (oz) await a.commit();
  return id;
}

// ─────────────────────────────────────────────────────── kechiktirish

export const KECHIKTIRISH = [10, 30, 60];

/** Python int(): butun son matni bo'lmasa yiqiladi. */
export function _int(x) {
  if (typeof x === "number" && Number.isInteger(x)) return x;
  const s = String(x);
  if (!/^\s*[+-]?\d+\s*$/.test(s)) throw new Error(`invalid literal for int(): '${s}'`);
  return Number.parseInt(s, 10);
}

// vazifa.py:777 — hozir: devor soati Date (vaqt.hozir())
export async function kechiktir(db, vazifa_id, daqiqa, hozir = null) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  daqiqa = _int(daqiqa);
  if (daqiqa <= 0) throw new Error("Kechiktirish musbat bo'lishi kerak");
  const matn = vaqt.vaqtStr(vaqt.daqiqaQosh(hozir || vaqt.hozir(), daqiqa));
  await db.apply("vazifa", "UPDATE", { kechiktirildi: matn }, vazifa_id,
    `«${v.nom}» ${daqiqa} daqiqaga kechiktirildi`);
  return matn;
}

// vazifa.py:793
export function kechiktirilganmi(v, hozir = null) {
  const q = "kechiktirildi" in v ? v.kechiktirildi : null;
  if (!q) return false;
  return vaqt.vaqtStr(hozir || vaqt.hozir()) < q;
}

// vazifa.py:801
export async function menyu_qoy(db, vazifa_id, taom) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  taom = String(taom ?? "").trim() || null;
  await db.apply("vazifa", "UPDATE", { menyu: taom }, vazifa_id, `Menyu: ${taom || "—"} (${v.nom})`);
}

// ═════════════════════════════ takroriy vazifa

export const TAKROR_UFQ = 30;
export const TAKROR_BELGI = "takror";
export const NAQSH_KUNLIK = "kunlik";
export const NAQSH_KUNLAR = "kunlar";
export const NAQSH_ORALIQ = "oraliq";
export const NAQSHLAR = { [NAQSH_KUNLIK]: "Har kuni", [NAQSH_KUNLAR]: "Tanlangan kunlar", [NAQSH_ORALIQ]: "Har N kunda" };

// vazifa.py:962
export function takror_kaliti(takror_id, sana) {
  return `${TAKROR_BELGI}:${Math.trunc(Number(takror_id))}:${_sana(sana)}`;
}

// vazifa.py:976
export function takror_kunlari(t) {
  return String(t.kunlar ?? "").split(",").filter((x) => x !== "").map((x) => _int(x));
}

// vazifa.py:1013
export async function takrorlar(db, faqat_faol = false) {
  const shart = faqat_faol ? " AND tk.faol=1" : "";
  return db.q(
    "SELECT tk.*, o.nom odam FROM vazifa_takror tk" +
    " JOIN odam o ON o.id = tk.odam_id" +
    ` WHERE tk.ochirilgan=0${shart}` +
    " ORDER BY tk.nom, tk.id");
}

// vazifa.py:1040 — ISO matnlar ro'yxati
export function takror_sanalari(t, dan, gacha) {
  const b = _sana(t.boshlanish);
  let d0 = _sana(dan); if (b > d0) d0 = b;
  let d1 = _sana(gacha);
  if (t.tugash && _sana(t.tugash) < d1) d1 = _sana(t.tugash);
  const naqsh = t.naqsh;
  const kunlar = new Set(naqsh === NAQSH_KUNLAR ? takror_kunlari(t) : []);
  const or = Math.max(1, Math.trunc(Number(t.oraliq || 1)));
  const natija = [];
  for (let k = d0; k <= d1; k = vaqt.kunQosh(k, 1)) {
    let mos;
    if (naqsh === NAQSH_KUNLAR) mos = kunlar.has(vaqt.weekday(k));
    else if (naqsh === NAQSH_ORALIQ) mos = ((vaqt.kunFarqi(b, k) % or) + or) % or === 0;
    else mos = true;
    if (mos) natija.push(k);
  }
  return natija;
}

// vazifa.py:1068
export async function takror_toldir(db, bugun = null, ufq = TAKROR_UFQ, { a = null } = {}) {
  const d0 = _sana(bugun || vaqt.bugun());
  const d1 = vaqt.kunQosh(d0, Math.max(0, _int(ufq)));
  const qoidalar = [];
  for (const t of await takrorlar(db, true)) {
    const s = takror_sanalari(t, d0, d1);
    if (s.length) qoidalar.push([t, s]);
  }
  if (!qoidalar.length) return 0;
  // Python har qoida uchun alohida so'raydi (manba LIKE 'takror:<id>:%'
  // AND sana BETWEEN birinchi..oxirgi). Bu yerda BITTA so'rov (d0..d1 —
  // hamma oraliqlarni qamraydi), keyin aynan o'sha shart JS'da: N+1 yo'q.
  // `ochirilgan` FILTRLANMAYDI — o'chirilgan kun qayta tirilmaydi.
  const mavjud = await db.q(
    "SELECT manba, sana FROM vazifa WHERE manba LIKE 'takror:%' AND sana BETWEEN ? AND ?", d0, d1);
  const yoziladi = [];
  for (const [t, sanalar] of qoidalar) {
    const pre = `${TAKROR_BELGI}:${t.id}:`;
    const birinchi = sanalar[0], oxirgi = sanalar[sanalar.length - 1];
    const bor = new Set(mavjud
      .filter((r) => r.manba.toLowerCase().startsWith(pre) && r.sana >= birinchi && r.sana <= oxirgi)
      .map((r) => r.manba));
    for (const k of sanalar) {
      const kalit = takror_kaliti(t.id, k);
      if (!bor.has(kalit)) yoziladi.push([t, k, kalit]);
    }
  }
  if (!yoziladi.length) return 0;
  const oz = !a;
  a ??= db.amal(`Takroriy vazifalar: ${yoziladi.length} ta kun qo'shildi`);
  const yar = vaqt.hozirStr();
  for (const [t, k, kalit] of yoziladi) {
    await a.apply("vazifa", "INSERT", {
      nom: t.nom, odam_id: t.odam_id, sana: k, vaqt: t.vaqt,
      davomiylik: t.davomiylik, holat: OCHIQ, izoh: t.izoh, manba: kalit,
      toifa: t.toifa ?? null, yaratilgan: yar,
    });
  }
  if (oz) await a.commit();
  return yoziladi.length;
}

// ═══════════════════════════════════════════════════════════ streak

export const NISHONLAR = [7, 14, 21, 28];
export const YUTUQ_IRODA = "Po'lat iroda";

// vazifa.py:1221
export async function streaklar(db, odam_id = null) {
  const p = [];
  let shart = "";
  if (odam_id) { shart = " AND s.odam_id=?"; p.push(odam_id); }
  return db.q(
    "SELECT s.*, o.nom odam, t.nom ish" +
    " FROM streak s" +
    " JOIN odam o ON o.id = s.odam_id" +
    " JOIN vazifa_turi t ON t.id = s.turi_id" +
    " WHERE s.ochirilgan=0" + shart +
    " ORDER BY o.tartib, o.id, t.tartib, t.id", ...p);
}

/**
 * vazifa.py:1278
 * `bajarilgan` — hali commit qilinmagan, shu amalda bajarilayotgan vazifa
 * qatori (navbatli yozuv): u ham bajarilgan deb sanaladi.
 */
export async function streak_kunlari(db, odam_id, turi_id, bugun = null, { bajarilgan = null } = {}) {
  const t = await tur_bitta(db, turi_id);
  if (!t) return 0;
  const kunlar = new Set((await db.q(
    "SELECT DISTINCT sana FROM vazifa WHERE ochirilgan=0 AND holat=? AND odam_id=? AND nom=?",
    BAJARILDI, odam_id, t.nom)).map((r) => r.sana));
  if (bajarilgan && bajarilgan.odam_id === odam_id && bajarilgan.nom === t.nom) kunlar.add(bajarilgan.sana);
  if (!kunlar.size) return 0;
  let k = _sana(bugun || vaqt.bugun());
  if (!kunlar.has(k)) k = vaqt.kunQosh(k, -1);
  let n = 0;
  while (kunlar.has(k)) { n += 1; k = vaqt.kunQosh(k, -1); }
  return n;
}

// vazifa.py:1303
export async function streak_holati(db, s, bugun = null, opts = {}) {
  const kunN = await streak_kunlari(db, s.odam_id, s.turi_id, bugun, opts);
  const nishon = Math.trunc(Number(s.nishon));
  return {
    id: s.id, odam_id: s.odam_id, turi_id: s.turi_id,
    odam: "odam" in s ? s.odam : "", ish: "ish" in s ? s.ish : "",
    kun: kunN, nishon, qoldi: Math.max(0, nishon - kunN),
    bajarildi: kunN >= nishon,
    ulush: nishon ? Math.min(1.0, kunN / nishon) : 0.0,
  };
}

// vazifa.py:1320
export async function yutuqlar(db, odam_id = null) {
  const p = [];
  let shart = "";
  if (odam_id) { shart = " AND y.odam_id=?"; p.push(odam_id); }
  return db.q(
    "SELECT y.*, o.nom odam FROM yutuq y" +
    " JOIN odam o ON o.id = y.odam_id" +
    " WHERE y.ochirilgan=0" + shart +
    " ORDER BY y.sana DESC, y.id DESC", ...p);
}

// vazifa.py:1333
export async function yutuq_bormi(db, odam_id, streak_id, nishon) {
  return (await db.q1(
    "SELECT 1 FROM yutuq WHERE ochirilgan=0 AND odam_id=? AND streak_id=? AND nishon=?",
    odam_id, streak_id, nishon)) != null;
}

// vazifa.py:1339 — `a` berilsa yutuqlar o'sha amalga qo'shiladi.
export async function yutuqlarni_tekshir(db, bugun = null, { a = null, bajarilgan = null } = {}) {
  const yangi = [];
  const sana = _sana(bugun || vaqt.bugun());
  for (const s of await streaklar(db)) {
    const h = await streak_holati(db, s, bugun, { bajarilgan });
    if (!h.bajarildi) continue;
    if (await yutuq_bormi(db, s.odam_id, s.id, h.nishon)) continue;
    const izoh = `${h.ish} — ${h.nishon} kun ketma-ket`;
    const data = { odam_id: s.odam_id, nom: YUTUQ_IRODA, izoh, sana, streak_id: s.id, nishon: h.nishon };
    const yid = a ? await a.apply("yutuq", "INSERT", data)
      : await db.apply("yutuq", "INSERT", data, null, `Yutuq: ${h.odam} — ${YUTUQ_IRODA}`);
    yangi.push({ id: yid, odam_id: s.odam_id, odam: h.odam, nom: YUTUQ_IRODA, izoh, nishon: h.nishon, ish: h.ish });
  }
  return yangi;
}

// ═══════════════════════════════════════ Sozlamalar → «Vazifalar» uchun portlar
// (miniapp_sz_vazifa.js). Hammasi Python bilan parity: test/miniapp_sz_vazifa.test.js.

// ───────────────────────────────────────────────────────── vazifa turi

// vazifa.py:92
export async function turlar(db) {
  return db.q("SELECT * FROM vazifa_turi WHERE ochirilgan=0 ORDER BY tartib, id");
}

// vazifa.py:97
export async function tur_nomlari(db) {
  return (await turlar(db)).map((r) => r.nom);
}

// vazifa.py:106
export async function tur_qosh(db, nom, davomiylik = 60, shaxsiy = false) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Vazifa turi nomi bo'sh bo'lishi mumkin emas");
  davomiylik = _int(davomiylik);
  if (davomiylik <= 0) throw new Error("Davomiylik musbat bo'lishi kerak");
  shaxsiy = shaxsiy ? 1 : 0;
  // `nom` UNIQUE: o'chirilgani bor bo'lsa qayta INSERT yiqiladi — tiriltiramiz.
  const eski = await db.q1("SELECT id, ochirilgan FROM vazifa_turi WHERE nom=?", nom);
  if (eski && eski.ochirilgan) {
    await db.apply("vazifa_turi", "UPDATE", { ochirilgan: 0, davomiylik, shaxsiy }, eski.id,
      `Vazifa turi qaytarildi: ${nom}`);
    return eski.id;
  }
  if (eski) throw new Error(`«${nom}» ro'yxatda bor`);
  const tartib = await db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM vazifa_turi", [], 1);
  return db.apply("vazifa_turi", "INSERT", { nom, davomiylik, tartib, shaxsiy }, null, `Vazifa turi: ${nom}`);
}

// vazifa.py:167
export async function tur_davomiylik_qoy(db, tur_id, davomiylik) {
  const t = await tur_bitta(db, tur_id);
  if (!t) throw new Error("Vazifa turi topilmadi");
  davomiylik = _int(davomiylik);
  if (davomiylik <= 0) throw new Error("Davomiylik musbat bo'lishi kerak");
  await db.apply("vazifa_turi", "UPDATE", { davomiylik }, tur_id,
    `«${t.nom}» davomiyligi: ${davomiylik} daqiqa`);
}

// vazifa.py:189
export async function tur_ochir(db, tur_id) {
  const t = await tur_bitta(db, tur_id);
  if (!t) throw new Error("Vazifa turi topilmadi");
  await db.apply("vazifa_turi", "DELETE", {}, tur_id, `Vazifa turi o'chirildi: ${t.nom}`);
}

// vazifa.py:220
export async function tur_shaxsiy_qoy(db, tur_id, shaxsiy) {
  const t = await tur_bitta(db, tur_id);
  if (!t) throw new Error("Vazifa turi topilmadi");
  const holat = shaxsiy ? "shaxsiy" : "umumiy";
  await db.apply("vazifa_turi", "UPDATE", { shaxsiy: shaxsiy ? 1 : 0 }, tur_id, `«${t.nom}» ${holat} bo'ldi`);
}

// vazifa.py:250
export async function qadam_qosh(db, turi_id, nom) {
  nom = String(nom ?? "").trim();
  if (!nom) throw new Error("Qadam nomi bo'sh bo'lishi mumkin emas");
  const t = await tur_bitta(db, turi_id);
  if (!t) throw new Error("Vazifa turi topilmadi");
  if ((await qadamlar(db, turi_id)).some((x) => x.nom.toLowerCase() === nom.toLowerCase())) {
    throw new Error(`«${nom}» bu ishda allaqachon bor`);
  }
  const tartib = await db.skalyar("SELECT COALESCE(MAX(tartib),0)+1 FROM ish_qadam WHERE turi_id=?", [turi_id], 1);
  return db.apply("ish_qadam", "INSERT", { turi_id, nom, tartib }, null, `«${t.nom}» ga qadam: ${nom}`);
}

// vazifa.py:267
export async function qadam_ochir(db, qadam_id) {
  const r = await db.q1("SELECT * FROM ish_qadam WHERE id=? AND ochirilgan=0", qadam_id);
  if (!r) throw new Error("Qadam topilmadi");
  await db.apply("ish_qadam", "DELETE", {}, qadam_id, `Qadam o'chirildi: ${r.nom}`);
}

// ────────────────────────────────────────────────────────────── navbat

// vazifa.py:428
export async function navbat_odamlari(db) {
  return db.q("SELECT id, nom FROM odam WHERE faol=1 ORDER BY tartib, id");
}

// vazifa.py:432 — sanalar ISO matn
export async function navbat_rejasi(db, tur_id, odam_id, sana, vaqt_ = null, kunlar = 7) {
  const t = await tur_bitta(db, tur_id);
  if (!t) throw new Error("Vazifa turi topilmadi");
  if (!t.navbat) throw new Error(`«${t.nom}» navbatli ish emas`);
  const odamlar = await navbat_odamlari(db);
  if (odamlar.length < 2) throw new Error("Navbat uchun kamida ikkita faol odam kerak");
  const idlar = odamlar.map((r) => r.id);
  const nomlar = new Map(odamlar.map((r) => [r.id, r.nom]));
  if (!idlar.includes(odam_id)) throw new Error("Tanlangan odam navbatda yo'q");
  kunlar = _int(kunlar);
  if (kunlar <= 0) throw new Error("Kunlar soni musbat bo'lishi kerak");
  const ergash = await tur_ergash(db, tur_id);
  const boshi = idlar.indexOf(odam_id);
  const n = idlar.length;
  const d0 = _sana(sana);
  const reja = [];
  for (let i = 0; i < kunlar; i++) {
    const kun = vaqt.kunQosh(d0, i);
    const oshpaz = idlar[(boshi + i) % n];
    reja.push({ sana: kun, vaqt: vaqt_, nom: t.nom, odam_id: oshpaz, odam: nomlar.get(oshpaz), davomiylik: t.davomiylik });
    if (ergash == null) continue;
    let y_vaqt = null;
    // Idish ovqatdan keyin: yarim tunni oshib ketmasin.
    if (vaqt_) y_vaqt = _vaqt_matn(Math.min(23 * 60 + 30, _daqiqa(vaqt_) + t.davomiylik));
    reja.push({ sana: kun, vaqt: y_vaqt, nom: ergash.nom, odam_id: oshpaz, odam: nomlar.get(oshpaz), davomiylik: ergash.davomiylik });
  }
  return reja;
}

/** `qosh()` ning amal ichidagi egizagi (Python'da ichki `amal` tashqisiga qo'shiladi). */
async function _qosh_amalda(db, a, nom, odam_id, sana, vaqt_ = null, davomiylik = 60, izoh = null) {
  let iso;
  [nom, iso, vaqt_, davomiylik] = await _tekshir(db, nom, odam_id, sana, vaqt_, davomiylik);
  await _odam_nom(db, odam_id);
  return a.apply("vazifa", "INSERT", {
    nom, odam_id, sana: iso, vaqt: vaqt_, davomiylik, holat: OCHIQ, izoh: String(izoh ?? "").trim() || null,
  });
}

// vazifa.py:476
export async function navbat_biriktir(db, tur_id, odam_id, sana, vaqt_ = null, kunlar = 7) {
  const reja = await navbat_rejasi(db, tur_id, odam_id, sana, vaqt_, kunlar);
  const a = db.amal(`Ovqat navbati: ${kunlar} kun, ${reja.length} ta vazifa`);
  for (const x of reja) await _qosh_amalda(db, a, x.nom, x.odam_id, x.sana, x.vaqt, x.davomiylik);
  await a.commit();
  return reja.length;
}

// vazifa.py:508
export async function yuvuvchi_id(db, oshpaz_id) {
  const idlar = (await navbat_odamlari(db)).map((r) => r.id);
  return idlar.includes(oshpaz_id) ? oshpaz_id : null;
}

// vazifa.py:516
export async function navbatlimi(db, vazifa_id) {
  const v = await bitta(db, vazifa_id);
  const t = await navbat_turi(db);
  return Boolean(v && t && v.nom === t.nom);
}

// vazifa.py:522
export async function _ergash_vazifa(db, oshpaz_vazifa) {
  const t = await navbat_turi(db);
  if (!t || oshpaz_vazifa.nom !== t.nom) return null;
  const ergash = await tur_ergash(db, t.id);
  if (!ergash) return null;
  return db.q1(
    "SELECT * FROM vazifa WHERE ochirilgan=0 AND nom=? AND sana=?" +
    " ORDER BY COALESCE(vaqt,'99:99'), id LIMIT 1", ergash.nom, oshpaz_vazifa.sana);
}

// vazifa.py:536 — JS: `v` amaldagi (navbatda turgan) holat bilan beriladi,
// `yangilangan` — shu amalda allaqachon tuzatilgan ergash qatorlari (id → odam_id).
async function _yuvuvchini_tugrila(db, a, v, yangilangan) {
  if (!v) return 0;
  const ergash = await _ergash_vazifa(db, v);
  if (!ergash) return 0;
  const hozirgi = yangilangan.has(ergash.id) ? yangilangan.get(ergash.id) : ergash.odam_id;
  const kerak = await yuvuvchi_id(db, v.odam_id);
  if (kerak == null || kerak === hozirgi) return 0;
  await a.apply("vazifa", "UPDATE", { odam_id: kerak }, ergash.id);
  yangilangan.set(ergash.id, kerak);
  return 1;
}

// vazifa.py:551
export async function keyingi_navbat(db, vazifa_id, odam_id) {
  const v = await bitta(db, vazifa_id);
  if (!v) return null;
  return db.q1(
    "SELECT * FROM vazifa WHERE ochirilgan=0 AND nom=? AND odam_id=?" +
    " AND (sana>? OR (sana=? AND id>?))" +
    " ORDER BY sana, COALESCE(vaqt,'99:99'), id LIMIT 1",
    v.nom, odam_id, v.sana, v.sana, v.id);
}

// vazifa.py:563
export async function almashtirish_rejasi(db, vazifa_id, yangi_odam_id) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  yangi_odam_id = _int(yangi_odam_id);
  if (yangi_odam_id === v.odam_id) throw new Error("Bu vazifa allaqachon o'shanikida");
  if (!(await db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", yangi_odam_id))) {
    throw new Error("Odam topilmadi yoki ro'yxatdan olingan");
  }
  const juft = await keyingi_navbat(db, vazifa_id, yangi_odam_id);
  if (!juft) {
    const nom = await _odam_nom(db, yangi_odam_id);
    throw new Error(`${nom}ning bundan keyin «${v.nom}» navbati yo'q — almashtirib bo'lmaydi.\n` +
      "«Faqat shu kunni berish» dan foydalaning.");
  }
  return { vazifa: v, juft, eski_odam: v.odam_id, yangi_odam: yangi_odam_id };
}

// vazifa.py:583
export async function almashtir(db, vazifa_id, yangi_odam_id) {
  const r = await almashtirish_rejasi(db, vazifa_id, yangi_odam_id);
  const { vazifa: v, juft } = r;
  const eski_nom = await _odam_nom(db, r.eski_odam);
  const yangi_nom = await _odam_nom(db, r.yangi_odam);
  const a = db.amal(`Navbat almashdi: ${eski_nom} ↔ ${yangi_nom} (${v.sana} / ${juft.sana})`);
  await a.apply("vazifa", "UPDATE", { odam_id: r.yangi_odam }, v.id);
  await a.apply("vazifa", "UPDATE", { odam_id: r.eski_odam }, juft.id);
  const yang = new Map();
  const tuzatildi = await _yuvuvchini_tugrila(db, a, { ...v, odam_id: r.yangi_odam }, yang) +
    await _yuvuvchini_tugrila(db, a, { ...juft, odam_id: r.eski_odam }, yang);
  await a.commit();
  return { vazifa_id: v.id, juft_id: juft.id, juft_sana: juft.sana, yuvuvchi_tuzatildi: tuzatildi, eski_nom, yangi_nom };
}

// vazifa.py:604
export async function bersin(db, vazifa_id, yangi_odam_id) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  yangi_odam_id = _int(yangi_odam_id);
  if (yangi_odam_id === v.odam_id) throw new Error("Bu vazifa allaqachon o'shanikida");
  if (!(await db.q1("SELECT 1 FROM odam WHERE id=? AND faol=1", yangi_odam_id))) {
    throw new Error("Odam topilmadi yoki ro'yxatdan olingan");
  }
  const eski_nom = await _odam_nom(db, v.odam_id);
  const yangi_nom = await _odam_nom(db, yangi_odam_id);
  const a = db.amal(`«${v.nom}» ${eski_nom} → ${yangi_nom} (${v.sana})`);
  await a.apply("vazifa", "UPDATE", { odam_id: yangi_odam_id }, v.id);
  const tuzatildi = await _yuvuvchini_tugrila(db, a, { ...v, odam_id: yangi_odam_id }, new Map());
  await a.commit();
  return { vazifa_id: v.id, yuvuvchi_tuzatildi: tuzatildi, eski_nom, yangi_nom };
}

// ─────────────────────────────────────────────────────────────── tahrir

const TAHRIR_MAYDON = ["nom", "odam_id", "sana", "vaqt", "davomiylik", "izoh"];

// vazifa.py:640 — Python **maydonlar → obyekt {nom, odam_id, sana, vaqt, davomiylik, izoh} (bori)
export async function tahrir(db, vazifa_id, maydonlar = {}) {
  const v = await bitta(db, vazifa_id);
  if (!v) throw new Error("Vazifa topilmadi");
  const yangi = {};
  for (const k of TAHRIR_MAYDON) if (k in maydonlar) yangi[k] = maydonlar[k];
  if (!Object.keys(yangi).length) return;
  const b = { ...v, ...yangi };
  const [nom, iso, vaqt_, davomiylik] = await _tekshir(db, b.nom, b.odam_id, b.sana, b.vaqt, b.davomiylik);
  if ("nom" in yangi) yangi.nom = nom;
  if ("sana" in yangi) yangi.sana = iso;
  if ("vaqt" in yangi) yangi.vaqt = vaqt_;
  if ("davomiylik" in yangi) yangi.davomiylik = davomiylik;
  if ("izoh" in yangi) yangi.izoh = String(yangi.izoh ?? "").trim() || null;
  await db.apply("vazifa", "UPDATE", yangi, vazifa_id, `Vazifa tahrirlandi: ${b.nom}`);
}

// ───────────────────────────────────────────────────── takroriy vazifa

// vazifa.py:966
export function _kunlar_matn(kunlar) {
  if (typeof kunlar === "string") kunlar = kunlar.replaceAll(" ", "").split(",").filter((x) => x);
  const toza = [...new Set((kunlar || []).map((x) => _int(x)))].sort((p, q) => p - q);
  if (toza.some((k) => !(k >= 0 && k <= 6))) throw new Error("Hafta kuni 0 (dushanba) va 6 (yakshanba) orasida");
  return toza.join(",");
}

// vazifa.py:981
export async function _takrorni_tekshir(db, nom, odam_id, vaqt_, davomiylik, naqsh, kunlar, oraliq, boshlanish, tugash) {
  let iso;
  [nom, iso, vaqt_, davomiylik] = await _tekshir(db, nom, odam_id, boshlanish, vaqt_, davomiylik);
  if (!Object.hasOwn(NAQSHLAR, naqsh)) throw new Error(`Noma'lum takror naqshi: ${naqsh}`);
  let kunlar_m = "";
  // `oraliq || 1` EMAS: 0 jimgina 1 ga aylanardi.
  oraliq = oraliq == null ? 1 : _int(oraliq);
  if (naqsh === NAQSH_KUNLAR) {
    kunlar_m = _kunlar_matn(kunlar);
    if (!kunlar_m) throw new Error("Kamida bitta hafta kuni tanlanishi kerak");
    oraliq = 1;
  } else if (naqsh === NAQSH_ORALIQ) {
    if (!(oraliq >= 1 && oraliq <= 90)) throw new Error("Oraliq 1 va 90 kun orasida bo'lishi kerak");
  } else {
    oraliq = 1;
  }
  let tugash_iso = null;
  if (tugash) {
    tugash_iso = _sana(tugash);
    if (tugash_iso < iso) throw new Error("Tugash sanasi boshlanishdan oldin bo'lmaydi");
  }
  return { nom, odam_id, vaqt: vaqt_, davomiylik, naqsh, kunlar: kunlar_m || null, oraliq, boshlanish: iso, tugash: tugash_iso };
}

// vazifa.py:1022
export async function takror_bitta(db, takror_id) {
  return db.q1("SELECT * FROM vazifa_takror WHERE id=? AND ochirilgan=0", takror_id);
}

// vazifa.py:1027
export function takror_tavsif(t) {
  let qachon;
  if (t.naqsh === NAQSH_KUNLAR) qachon = takror_kunlari(t).map((k) => KUN_QISQA[k]).join(", ") || "—";
  else if (t.naqsh === NAQSH_ORALIQ) qachon = t.oraliq === 1 ? "Har kuni" : `Har ${t.oraliq} kunda`;
  else qachon = NAQSHLAR[NAQSH_KUNLIK];
  return `${qachon} ${t.vaqt || "vaqtsiz"}`;
}

// vazifa.py:1110 — kwargs → obyekt. Qoida va undan chiqqan kunlar BITTA amal.
export async function takror_qosh(db, nom, odam_id, {
  vaqt: vaqt_ = null, davomiylik = 60, naqsh = NAQSH_KUNLIK, kunlar = null, oraliq = 1,
  izoh = null, boshlanish = null, tugash = null, bugun = null, toifa = null,
} = {}) {
  const d = await _takrorni_tekshir(db, nom, odam_id, vaqt_, davomiylik, naqsh, kunlar, oraliq,
    boshlanish || bugun || vaqt.bugun(), tugash);
  d.izoh = String(izoh ?? "").trim() || null;
  if (toifa) d.toifa = toifa;
  const a = db.amal(`Takroriy vazifa: ${d.nom}`);
  const yar = vaqt.hozirStr();
  const tid = await a.apply("vazifa_takror", "INSERT", { ...d, yaratilgan: yar });
  // Navbatli yozuv: yangi qoida commit'gacha bazada ko'rinmaydi — uning kunlari
  // shu yerda (takror_toldir bilan AYNAN bir xil shart), qolgan qoidalar o'zida.
  const d0 = _sana(bugun || vaqt.bugun());
  const sanalar = takror_sanalari({ ...d, id: tid }, d0, vaqt.kunQosh(d0, TAKROR_UFQ));
  if (sanalar.length) {
    const bor = new Set((await db.q(
      "SELECT manba FROM vazifa WHERE manba LIKE ? AND sana BETWEEN ? AND ?",
      `${TAKROR_BELGI}:${tid}:%`, sanalar[0], sanalar[sanalar.length - 1])).map((r) => r.manba));
    for (const k of sanalar) {
      const kalit = takror_kaliti(tid, k);
      if (bor.has(kalit)) continue;
      await a.apply("vazifa", "INSERT", {
        nom: d.nom, odam_id: d.odam_id, sana: k, vaqt: d.vaqt, davomiylik: d.davomiylik,
        holat: OCHIQ, izoh: d.izoh, manba: kalit, toifa: d.toifa ?? null, yaratilgan: yar,
      });
    }
  }
  await takror_toldir(db, bugun, TAKROR_UFQ, { a });
  await a.commit();
  return tid;
}

// vazifa.py:1129
async function _takror_kelajagini_ochir(db, a, takror_id, bugun = null) {
  const d0 = _sana(bugun || vaqt.bugun());
  const qatorlar = await db.q(
    "SELECT id FROM vazifa WHERE ochirilgan=0 AND holat=? AND sana>=? AND manba LIKE ?",
    OCHIQ, d0, `${TAKROR_BELGI}:${Math.trunc(Number(takror_id))}:%`);
  for (const r of qatorlar) await a.apply("vazifa", "DELETE", {}, r.id);
  return qatorlar.length;
}

// vazifa.py — takror_vaqt_qoy: qoida + `dan` kunidan keyingi BARCHA ochiq kunlar,
// joyida (o'chirib-yozish emas: to'ldirish o'chirilgan kalitni tiriltirmaydi).
export async function takror_vaqt_qoy(db, takror_id, vaqt_, dan = null) {
  const t = await takror_bitta(db, takror_id);
  if (!t) throw new Error("Takroriy vazifa topilmadi");
  [, , vaqt_] = await _tekshir(db, t.nom, t.odam_id, vaqt.bugun(), vaqt_, t.davomiylik);
  const d0 = _sana(dan || vaqt.bugun());
  const qatorlar = await db.q(
    "SELECT id, vaqt FROM vazifa WHERE ochirilgan=0 AND holat=? AND sana>=? AND manba LIKE ?",
    OCHIQ, d0, `${TAKROR_BELGI}:${Math.trunc(Number(takror_id))}:%`);
  if (t.vaqt === vaqt_ && qatorlar.every((r) => r.vaqt === vaqt_)) return 0;
  const a = db.amal(`${t.nom}: vaqti ${vaqt_ || "vaqtsiz"} (${d0} dan)`);
  if (t.vaqt !== vaqt_) await a.apply("vazifa_takror", "UPDATE", { vaqt: vaqt_ }, t.id);
  let n = 0;
  for (const r of qatorlar) {
    if (r.vaqt === vaqt_) continue;
    await a.apply("vazifa", "UPDATE", { vaqt: vaqt_ }, r.id);
    n++;
  }
  await a.commit();
  return n;
}

// vazifa.py — namoz_takrorlari: namoz qoidalari, vaqt bo'yicha.
export async function namoz_takrorlari(db, odam_id = null) {
  const r = (await takrorlar(db)).filter((t) => namozmi(t) && (odam_id == null || t.odam_id === odam_id));
  const k = (t) => (t.vaqt ? _daqiqa(t.vaqt) : 1e9);
  return r.sort((x, y) => k(x) - k(y) || x.id - y.id);
}

// vazifa.py:1170
export async function takror_ochir(db, takror_id, bugun = null) {
  const t = await takror_bitta(db, takror_id);
  if (!t) throw new Error("Takroriy vazifa topilmadi");
  const a = db.amal(`Takroriy vazifa to'xtatildi: ${t.nom}`);
  await a.apply("vazifa_takror", "DELETE", {}, takror_id);
  const n = await _takror_kelajagini_ochir(db, a, takror_id, bugun);
  await a.commit();
  return n;
}

// vazifa.py:1180
export function takrorlimi(v) {
  if (!v) return false;
  return String(v.manba ?? "").startsWith(`${TAKROR_BELGI}:`);
}

// vazifa.py:1191
export async function takror_egasi(db, v) {
  if (!takrorlimi(v)) return null;
  const q = String(v.manba).split(":")[1];
  if (q == null || !/^\s*[+-]?\d+\s*$/.test(q)) return null;
  return takror_bitta(db, _int(q));
}
