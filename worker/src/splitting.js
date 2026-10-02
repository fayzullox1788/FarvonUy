// Kim qatnashadi va ulush qanday bo'linadi — Python `core/splitting.py` egizagi.
import * as money from "./money.js";

// splitting.py:13
/** Shu sanada uyda bo'lgan faol odamlar (hech kim qolmasa — hamma). */
export async function qatnashchilar(db, sana) {
  const hamma = (await db.q("SELECT id FROM odam WHERE faol=1 ORDER BY tartib,id")).map((r) => r.id);
  const yoq = new Set((await db.q(
    "SELECT DISTINCT odam_id FROM yoq_kun" +
    " WHERE ochirilgan=0 AND boshi<=? AND oxiri>=?", sana, sana)).map((r) => r.odam_id));
  const qolgan = hamma.filter((i) => !yoq.has(i));
  return qolgan.length ? qolgan : hamma;
}

// splitting.py:34
/** Map<odam_id, shu paytgacha olgan ortiqcha so'm>. */
export async function yaxlitlash_tarixi(db) {
  return new Map((await db.q("SELECT id, ortiqcha FROM v_yaxlitlash")).map((r) => [r.id, r.ortiqcha]));
}

// splitting.py:39
/** Rasxod ulushlari. parametrlar: Map<odam_id, qiymat> | null. */
export async function hisobla(db, summa, sana, usul = money.USUL_TENG, parametrlar = null) {
  if (parametrlar != null && !(parametrlar instanceof Map)) {
    parametrlar = new Map(Object.entries(parametrlar).map(([k, v]) => [Number(k), v]));
  }
  let p;
  if (parametrlar && parametrlar.size) {
    p = new Map(parametrlar);
  } else {
    p = new Map((await qatnashchilar(db, sana)).map((i) => [i, 1.0]));
  }
  if (!p.size) throw new Error("bo'linadigan odam yo'q");
  return money.bol(summa, usul, p, await yaxlitlash_tarixi(db));
}
