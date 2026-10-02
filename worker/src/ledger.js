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
