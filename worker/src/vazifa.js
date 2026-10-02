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
      yaratilgan: yar,
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
