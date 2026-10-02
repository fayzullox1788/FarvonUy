// Vaqt — HAR DOIM Toshkent (UTC+5, yozgi vaqt yo'q). Worker UTC'da ishlaydi,
// Python esa `datetime.now()` (mahalliy) ishlatadi — farq shu yerda yopiladi.
//
// Formatlar Python bilan bir xil:
//   sana  "YYYY-MM-DD"
//   vaqt  "YYYY-MM-DD HH:MM:SS"  — orasida BO'SH JOY (ISO 'T' emas!). Matn
//         solishtiruvida ' ' < 'T', shuning uchun 'T' jimgina xato beradi.
//
// Testlar soatni muzlatadi: `soatniQoy(new Date(...))`.

const OFFSET_MS = 5 * 3600 * 1000;
let _muzlatilgan = null;

export function soatniQoy(d) { _muzlatilgan = d; }

/** Hozirgi UTC lahza (Date). */
export function hozirUtc() { return _muzlatilgan ? new Date(_muzlatilgan) : new Date(); }

/** Toshkentdagi devor soati — UTC maydonlari Toshkent qiymatlarini saqlaydi. */
export function hozir() { return new Date(hozirUtc().getTime() + OFFSET_MS); }

const p2 = (n) => String(n).padStart(2, "0");

/** Date (devor soati, UTC maydonlari) → "YYYY-MM-DD". */
export function sanaStr(d) {
  return `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}`;
}
/** → "YYYY-MM-DD HH:MM:SS" */
export function vaqtStr(d) {
  return `${sanaStr(d)} ${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}`;
}
export function bugun() { return sanaStr(hozir()); }
export function hozirStr() { return vaqtStr(hozir()); }

/** "YYYY-MM-DD" → Date (UTC yarim tun, devor soati sifatida). */
export function sanaDan(s) {
  const [y, m, d] = String(s).slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}
/** "YYYY-MM-DD HH:MM[:SS]" → Date (devor soati). */
export function vaqtDan(s) {
  const t = String(s).replace("T", " ");
  const [sana, soat = "00:00:00"] = t.split(" ");
  const [h, mi, se = 0] = soat.split(":").map(Number);
  const d = sanaDan(sana);
  d.setUTCHours(h, mi, se);
  return d;
}

export function kunQosh(s, n) {
  const d = sanaDan(s);
  d.setUTCDate(d.getUTCDate() + n);
  return sanaStr(d);
}
export function daqiqaQosh(d, n) { return new Date(d.getTime() + n * 60000); }

/** Python `date.weekday()`: Dushanba=0 … Yakshanba=6. */
export function weekday(s) { return (sanaDan(s).getUTCDay() + 6) % 7; }

/** Python `date.toordinal()`: 0001-01-01 = 1. */
export function toordinal(s) {
  // date(1970,1,1).toordinal() == 719163
  return Math.round(sanaDan(s).getTime() / 86400000) + 719163;
}

/** Ikki sana orasidagi kun farqi (b - a). */
export function kunFarqi(a, b) {
  return Math.round((sanaDan(b).getTime() - sanaDan(a).getTime()) / 86400000);
}

/** "HH:MM" → yarim tundan beri daqiqa; bo'sh/noto'g'ri → null (xabar._daqiqa). */
export function daqiqa(v) {
  if (!v) return null;
  const m = /^(\d{1,2}):(\d{2})/.exec(String(v));
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}
/** Date (devor soati) → yarim tundan beri daqiqa. */
export function daqiqaDan(d) { return d.getUTCHours() * 60 + d.getUTCMinutes(); }

/** "dd.mm.yyyy" */
export function sanaNuqta(s) {
  const [y, m, d] = String(s).slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}
