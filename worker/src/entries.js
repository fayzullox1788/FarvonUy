// Yozuvlar — Python `core/entries.py` ning botga kerak qismi (rasxod).
//
// Ichma-ich amal: Python'da ichki `with db.amal()` tashqisiga qo'shiladi
// (tavsif — tashqiniki). JS'da ixtiyoriy `a` (Amal) beriladi: berilsa
// yozuvlar o'sha amalga navbatlanadi va commit QILINMAYDI.
import * as money from "./money.js";
import * as hamyon from "./hamyon.js";
import * as splitting from "./splitting.js";

// entries.py:52
/** Qo'lda yoziladigan har rasxodda sabab VA kategoriya bo'lishi shart. */
export async function rasxod_majburiy(db, nom, turi_id) {
  if (!String(nom ?? "").trim()) throw new Error("Sabab yozilmagan — rasxod nima uchun?");
  if (turi_id == null) throw new Error("Kategoriya tanlanmagan.");
  if (!await db.q1("SELECT 1 FROM turi WHERE id=? AND faol=1", turi_id)) {
    throw new Error("Bu kategoriya endi yo'q — boshqasini tanlang.");
  }
}

// entries.py:67
/**
 * Rasxod + (umumiy bo'lsa) ulushlar — bitta Amal (bitta undo).
 * parametrlar: Map<odam_id, qiymat> | null.
 */
export async function rasxod_qosh(db, sana, nom, summa, kim_toladi, {
  umumiymi = true, turi_id = null, usul = money.USUL_TENG, parametrlar = null,
  izoh = null, item_id = null, reja_id = null, takror_id = null,
  kim_uchun = null, karta_id = null, a = null,
} = {}) {
  summa = Math.trunc(Number(summa));
  if (summa <= 0) throw new Error("Rasxod summasi musbat bo'lishi kerak");
  await hamyon.tekshir_karta(db, karta_id, kim_toladi);

  if (kim_uchun != null) {
    // 100% bitta odamga — bo'lish shart emas, qoldiq ham yo'q.
    umumiymi = true;
    usul = money.USUL_ANIQ;
    parametrlar = new Map([[kim_uchun, summa]]);
  }

  let ulushlar = [];
  if (umumiymi) ulushlar = await splitting.hisobla(db, summa, sana, usul, parametrlar);

  const kim = await _odam_nom(db, kim_toladi);
  let tur;
  if (kim_uchun != null) tur = `${await _odam_nom(db, kim_uchun)} uchun`;
  else tur = umumiymi ? "Umumiy" : "Shaxsiy";

  const ozim = a == null;
  if (ozim) a = db.amal(`${tur} rasxod: ${nom || "—"} ${money.fmt(summa)} (${kim})`);
  const rid = await a.apply("rasxod", "INSERT", {
    sana, nom: nom || "", turi_id, summa,
    kim_toladi, umumiymi: umumiymi ? 1 : 0,
    bolish_usul: usul, item_id, reja_id,
    takror_id, kim_uchun,
    izoh: izoh || null, karta_id,
  });
  for (const u of ulushlar) {
    await a.apply("ulush", "INSERT", {
      rasxod_id: rid, odam_id: u.odam_id, summa: u.summa, yaxlitlash: u.yaxlitlash,
    });
  }
  if (ozim) await a.commit();
  return rid;
}

// entries.py:183
export async function rasxod_ochir(db, rasxod_id, { a = null } = {}) {
  const r = await db.q1("SELECT nom, summa FROM rasxod WHERE id=?", rasxod_id);
  const nom = (r ? r.nom : "") || "—";
  const ozim = a == null;
  if (ozim) a = db.amal(`Rasxod o'chirildi: ${nom}`);
  await a.apply("rasxod", "DELETE", {}, rasxod_id);
  if (ozim) await a.commit();
}

// entries.py:454
export async function _odam_nom(db, odam_id) {
  const r = await db.q1("SELECT nom FROM odam WHERE id=?", odam_id);
  return r ? r.nom : "?";
}
