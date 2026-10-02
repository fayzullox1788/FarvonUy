// Balanslar va juftlik qarzlari — Python `core/ledger.py` ning botga kerak qismi.

// ledger.py:30
export async function balans(db, odam_id) {
  return db.q1("SELECT * FROM v_balans WHERE id=?", odam_id);
}

// ledger.py:51
/** Tashqi qarzlar: olingan, qaytarilgan va qoldig'i bilan. */
export async function tashqi_qarzlar(db, faqat_ochiq = false) {
  let qatorlar = await db.q(
    "SELECT q.*, o.nom odam_nom," +
    "  (SELECT GROUP_CONCAT(x.nom || ':' || u.summa, ', ') FROM tashqi_ulush u" +
    "   JOIN odam x ON x.id=u.odam_id WHERE u.qarz_id=q.id AND u.tolov_id IS NULL" +
    "   AND u.ochirilgan=0) ulushlar," +
    "  COALESCE((SELECT SUM(t.summa) FROM tashqi_tolov t" +
    "            WHERE t.tashqi_qarz_id=q.id AND t.ochirilgan=0),0) qaytgan" +
    " FROM tashqi_qarz q JOIN odam o ON o.id=q.odam_id" +
    " WHERE q.ochirilgan=0 ORDER BY q.sana DESC, q.id DESC");
  for (const r of qatorlar) r.qoldiq = r.summa - r.qaytgan;
  if (faqat_ochiq) qatorlar = qatorlar.filter((r) => r.qoldiq > 0);
  return qatorlar;
}

// ledger.py:99
export class Juft {
  constructor(qarzdor_id, kreditor_id, qarzdor_nom, kreditor_nom, summa) {
    Object.assign(this, { qarzdor_id, kreditor_id, qarzdor_nom, kreditor_nom, summa });
  }
}

// ledger.py:107
/** Netlangan juftlik qarzlari: A→B va B→A birlashtirilgan. */
export async function juft_qarzlar(db) {
  const nomlar = new Map((await db.q("SELECT id, nom FROM odam")).map((r) => [r.id, r.nom]));
  const xom = new Map(); // "a,b" -> summa (qo'shilish tartibi — Python dict kabi)
  for (const r of await db.q("SELECT qarzdor, kreditor, summa FROM v_juft_qarz")) {
    const k = `${r.qarzdor},${r.kreditor}`;
    xom.set(k, (xom.get(k) || 0) + Math.trunc(Number(r.summa || 0)));
  }
  const net = new Map();
  for (const [k, s] of xom) {
    const [a, b] = k.split(",").map(Number);
    if (a === b) continue;
    const [x, y] = a < b ? [a, b] : [b, a];
    const kalit = `${x},${y}`;
    net.set(kalit, (net.get(kalit) || 0) + (x === a ? s : -s));
  }
  const natija = [];
  for (const [k, s] of net) {
    if (s === 0) continue;
    const [a, b] = k.split(",").map(Number);
    const [qarzdor, kreditor, summa] = s > 0 ? [a, b, s] : [b, a, -s];
    natija.push(new Juft(qarzdor, kreditor, nomlar.get(qarzdor) ?? "?",
      nomlar.get(kreditor) ?? "?", summa));
  }
  natija.sort((p, q) => q.summa - p.summa); // barqaror — Python sort kabi
  return natija;
}

// ── Kategoriya bo'yicha rasxod (rejaga band pul hisobi uchun) ───────────

// ledger.py:420
export const _ILDIZ = "WITH RECURSIVE ild(id, ildiz) AS (" +
  " SELECT id, id FROM turi WHERE ota_id IS NULL" +
  " UNION ALL SELECT t.id, ild.ildiz FROM turi t" +
  " JOIN ild ON t.ota_id=ild.id) ";

// ledger.py:432
export const ODAM_QISMLARI = ["hammasi", "shaxsiy", "umumiy"];
const _ODAM_SHAXSIY = [
  "SELECT r.id, r.turi_id, r.summa, 'shaxsiy' qism FROM rasxod r" +
  " WHERE r.ochirilgan=0 AND r.umumiymi=0 AND r.kim_toladi=?" +
  " AND r.sana BETWEEN ? AND ?",
  "SELECT r.id, r.turi_id, u.summa, 'shaxsiy' qism FROM ulush u" +
  " JOIN rasxod r ON r.id=u.rasxod_id" +
  " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NOT NULL" +
  " AND u.odam_id=? AND u.summa<>0 AND r.sana BETWEEN ? AND ?"];
const _ODAM_UMUMIY = [
  "SELECT r.id, r.turi_id, u.summa, 'umumiy' qism FROM ulush u" +
  " JOIN rasxod r ON r.id=u.rasxod_id" +
  " WHERE r.ochirilgan=0 AND r.umumiymi=1 AND r.kim_uchun IS NULL" +
  " AND u.odam_id=? AND u.summa<>0 AND r.sana BETWEEN ? AND ?"];

// ledger.py:450
export function _odam_manba(qism, odam_id, boshi, oxiri) {
  if (!ODAM_QISMLARI.includes(qism)) throw new Error(`noma'lum qism: '${qism}'`);
  const bolaklar = { shaxsiy: _ODAM_SHAXSIY, umumiy: _ODAM_UMUMIY,
    hammasi: [..._ODAM_SHAXSIY, ..._ODAM_UMUMIY] }[qism];
  return [bolaklar.join(" UNION ALL "), bolaklar.flatMap(() => [odam_id, boshi, oxiri])];
}

// ledger.py:460
/** (id, turi_id, summa, qism) qatorlari manbasi — [sql, args]. */
export function _manba(boshi, oxiri, odam_id, qism) {
  if (odam_id == null) {
    const shart = { hammasi: "",
      umumiy: " AND umumiymi=1 AND kim_uchun IS NULL",
      shaxsiy: " AND (umumiymi=0 OR kim_uchun IS NOT NULL)" };
    if (!(qism in shart)) throw new Error(`noma'lum qism: '${qism}'`);
    return ["SELECT id, turi_id, summa," +
      " CASE WHEN umumiymi=0 OR kim_uchun IS NOT NULL" +
      " THEN 'shaxsiy' ELSE 'umumiy' END qism" +
      " FROM rasxod WHERE ochirilgan=0 AND sana BETWEEN ? AND ?" + shart[qism], [boshi, oxiri]];
  }
  return _odam_manba(qism, odam_id, boshi, oxiri);
}

// ledger.py:481
/** Kategoriya (asosiy) bo'yicha rasxod; `odam_id` berilsa — o'sha odamniki. */
export async function turi_boyicha(db, boshi, oxiri, odam_id = null, qism = "hammasi") {
  const [manba, args] = _manba(boshi, oxiri, odam_id, qism);
  return db.q(
    _ILDIZ +
    ", m AS (" + manba + ") " +
    "SELECT ild.ildiz turi_id, COALESCE(t.nom,'Kategoriyasiz') nom," +
    "       COALESCE(t.belgi,'') belgi, t.rasm rasm," +
    "       SUM(m.summa) summa, COUNT(*) soni" +
    " FROM m LEFT JOIN ild ON ild.id=m.turi_id" +
    " LEFT JOIN turi t ON t.id=ild.ildiz" +
    " GROUP BY ild.ildiz ORDER BY summa DESC", ...args);
}
