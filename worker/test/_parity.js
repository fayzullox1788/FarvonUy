// Parity testlari uchun umumiy yordamchilar (vazifa.test.js, xabar.test.js).
//
// Naqsh: Python bilan ekilgan "usta" baza → har ssenariy uchun IKKI nusxa
// (Python o'z faylida, JS o'z faylida) → bir xil amal → natija/qatorlar
// solishtiriladi.
import { copyFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { py } from "./fixture.js";
import { D1Shim } from "./d1shim.js";
import { Db } from "../src/db.js";
import * as vaqt from "../src/vaqt.js";
import * as tg from "../src/tg.js";

/** Python boshi: soat muzlatish, Telegram yozib oluvchi, natija chiqarish. */
export const PY_BOSH = String.raw`
import json, datetime as _dt
from core import vazifa as vz, xabar as xb, menyu as mn, entries
CALLS = []
def _rec(token, metod, **m):
    CALLS.append([metod, {k: v for k, v in m.items() if v is not None}])
    if metod == "getFile":
        return {"file_path": "photos/file_1.jpg"}
    return {"message_id": 777}
xb._sorov = _rec
xb._fayl_yukla = lambda token, yol: b"RASM-BAYT"
def muzlat(s):
    t = _dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    class FD(_dt.date):
        @classmethod
        def today(cls):
            return cls(t.year, t.month, t.day)
    class FDT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(t.year, t.month, t.day, t.hour, t.minute, t.second)
    for m in (vz, xb):
        m.date = FD
        m.datetime = FDT
    return FDT.now()
def chiq(x):
    print("@@" + json.dumps(x, ensure_ascii=False, default=str))
`;

/** Usta baza — Python ekish kodi bilan. → {papka, id: <ekish `chiq()` qiymati>} */
export function usta(pyKod) {
  const papka = mkdtempSync(join(tmpdir(), "fuy-u-"));
  const id = pyIshla(papka, pyKod);
  return { papka, id };
}

/** Usta bazaning yangi nusxasi (alohida papkada). */
export function nusxa(papka) {
  const p = mkdtempSync(join(tmpdir(), "fuy-n-"));
  copyFileSync(join(papka, "t.db"), join(p, "t.db"));
  return p;
}

/** Nusxa ustida JS Db. */
export function jsDb(papka) {
  const d1 = new D1Shim(join(papka, "t.db"));
  return new Db(d1);
}

/** Python'ni ishlatadi, `chiq(...)` qilgan oxirgi qiymatni qaytaradi. */
export function pyIshla(papka, kod) {
  const out = py(papka, PY_BOSH + kod);
  const q = out.split(/\r?\n/).filter((x) => x.startsWith("@@"));
  if (!q.length) return undefined;
  return JSON.parse(q[q.length - 1].slice(2));
}

/** JS soatini Toshkent devor soatiga muzlatadi ("YYYY-MM-DD HH:MM:SS"). */
export function muzlat(s) {
  vaqt.soatniQoy(new Date(vaqt.vaqtDan(s).getTime() - 5 * 3600 * 1000));
  return vaqt.hozir();
}

/** Telegram yozib oluvchi (Python `_rec` egizagi). */
export function yozuvchi() {
  const calls = [];
  tg.transportQoy(async (metod, m) => {
    if (metod === "__yukla") return new TextEncoder().encode("RASM-BAYT");
    calls.push([metod, { ...m }]);
    if (metod === "getFile") return { file_path: "photos/file_1.jpg" };
    return { message_id: 777 };
  });
  return calls;
}

/** Chaqiruvlarni solishtirishga tayyorlaydi: reply_markup JSON parse. */
export function norm(calls) {
  return calls.map(([m, f]) => {
    const g = { ...f };
    if (typeof g.reply_markup === "string") g.reply_markup = JSON.parse(g.reply_markup);
    return [m, g];
  });
}

/** Bazadan qatorlar (fayldan to'g'ridan-to'g'ri, ustunlarni olib tashlab). */
export function qatorlar(papka, sql, olib = ["id", "yaratilgan"], ...args) {
  const d = new DatabaseSync(join(papka, "t.db"));
  try {
    return d.prepare(sql).all(...args).map((r) => {
      const o = { ...r };
      for (const k of olib) delete o[k];
      return o;
    });
  } finally { d.close(); }
}

/** Ma'lum id dan keyingi ozgarishlar: (jadval, amal, tavsif) ketma-ketligi. */
export function jurnal(papka, dan) {
  return qatorlar(papka,
    "SELECT jadval, amal, tavsif, guruh_id FROM ozgarishlar WHERE id>? ORDER BY id", [], dan)
    .map((r) => r);
}

/** Jurnalni guruhlarga bo'lib solishtiriladigan ko'rinishga keltiradi. */
export function jurnalNorm(r) {
  const guruhlar = new Map();
  for (const x of r) {
    if (!guruhlar.has(x.guruh_id)) guruhlar.set(x.guruh_id, []);
    guruhlar.get(x.guruh_id).push([x.jadval, x.amal, x.tavsif]);
  }
  return [...guruhlar.values()];
}

export function maxOz(papka) {
  return qatorlar(papka, "SELECT COALESCE(MAX(id),0) m FROM ozgarishlar", [])[0].m;
}
