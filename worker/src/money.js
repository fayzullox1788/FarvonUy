// Pul — Python `src/money.py` ning egizagi. Pul HAR DOIM butun son (so'm).
// Bo'lish faqat `bol()` orqali; yig'indi aniq `jami` ga teng.

export const VERGUL = " "; // ajratmaydigan probel — 1 559 000

export function fmt(summa, belgi = false) {
  if (summa == null) return "—";
  const s = Math.round(Number(summa));
  const ishora = s < 0 ? "-" : (belgi && s > 0 ? "+" : "");
  return ishora + String(Math.abs(s)).replace(/\B(?=(\d{3})+(?!\d))/g, VERGUL);
}

export function fmt_som(summa, belgi = false) {
  if (summa == null) return "—";
  return `${fmt(summa, belgi)} so'm`;
}

export const USUL_TENG = "teng";
export const USUL_FOIZ = "foiz";
export const USUL_OGIRLIK = "ogirlik";
export const USUL_ANIQ = "aniq";

/** @returns {{odam_id:number, summa:number, yaxlitlash:number}[]} */
export function bol_tortli(jami, ogirliklar, qarzTarixi = null) {
  // ogirliklar: Map<number, number> yoki {id: w} (kalitlar raqamga aylantiriladi,
  // tartib — Python dict kabi qo'shilish tartibi).
  const juft = ogirliklar instanceof Map ? [...ogirliklar] : Object.entries(ogirliklar).map(([k, v]) => [Number(k), v]);
  const w = new Map(juft);
  const ids = juft.filter(([, v]) => v > 0).map(([k]) => k);
  if (!ids.length) throw new Error("bo'linadigan odam yo'q");
  if (jami === 0) return ids.map((i) => ({ odam_id: i, summa: 0, yaxlitlash: 0 }));

  const manfiy = jami < 0;
  const j = Math.abs(jami);
  const W = ids.reduce((s, i) => s + w.get(i), 0);
  const xom = new Map(ids.map((i) => [i, (j * w.get(i)) / W]));
  const asos = new Map(ids.map((i) => [i, Math.floor(xom.get(i))]));
  const qoldiq = j - ids.reduce((s, i) => s + asos.get(i), 0);
  const tarix = qarzTarixi || {};
  const tg = (i) => (tarix instanceof Map ? tarix.get(i) : tarix[i]) || 0;
  const navbat = [...ids].sort((a, b) =>
    -(xom.get(a) - asos.get(a)) - -(xom.get(b) - asos.get(b)) || tg(a) - tg(b) || a - b);
  const extra = new Map(ids.map((i) => [i, 0]));
  for (const i of navbat.slice(0, qoldiq)) { asos.set(i, asos.get(i) + 1); extra.set(i, 1); }
  const ishora = manfiy ? -1 : 1;
  const natija = ids.map((i) => ({ odam_id: i, summa: ishora * asos.get(i), yaxlitlash: extra.get(i) }));
  if (natija.reduce((s, u) => s + u.summa, 0) !== jami) throw new Error("bo'lish yig'indisi buzildi");
  return natija;
}

export function bol_teng(jami, odamlar, qarzTarixi = null) {
  return bol_tortli(jami, new Map(odamlar.map((i) => [Number(i), 1.0])), qarzTarixi);
}

export function bol_aniq(jami, summalar) {
  const juft = summalar instanceof Map ? [...summalar] : Object.entries(summalar).map(([k, v]) => [Number(k), v]);
  const s = juft.reduce((a, [, v]) => a + v, 0);
  if (s !== jami) {
    throw new Error(`aniq ulushlar yig'indisi ${fmt(s)} — rasxod ${fmt(jami)} ga teng emas ` +
      `(farq ${fmt(jami - s, true)})`);
  }
  return juft.map(([i, v]) => ({ odam_id: i, summa: v, yaxlitlash: 0 }));
}

export function bol(jami, usul, parametrlar, qarzTarixi = null) {
  const juft = parametrlar instanceof Map ? [...parametrlar] : Object.entries(parametrlar).map(([k, v]) => [Number(k), v]);
  if (usul === USUL_TENG) return bol_teng(jami, juft.map(([k]) => k), qarzTarixi);
  if (usul === USUL_FOIZ || usul === USUL_OGIRLIK) return bol_tortli(jami, new Map(juft), qarzTarixi);
  if (usul === USUL_ANIQ) return bol_aniq(jami, new Map(juft.map(([k, v]) => [k, Math.trunc(v)])));
  throw new Error(`noma'lum bo'lish usuli: '${usul}'`);
}
