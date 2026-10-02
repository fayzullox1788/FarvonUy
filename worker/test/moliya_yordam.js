// Moliya / bot parity testlari uchun umumiy yordamchilar
// (moliya.test.js, tg_menyu.test.js, tg_rasxod.test.js).
import { copyFileSync, cpSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { yangiBaza, py } from "./fixture.js";
import { soatniQoy } from "../src/vaqt.js";
import { transportQoy } from "../src/tg.js";

/**
 * Bitta Python ekish → ikki NUSXA: JS shu bazada (`db`), Python esa
 * `pyPapka` dagi nusxada ishlaydi. Ikkalasi bir xil holatdan boshlaydi.
 */
export function ikkiBaza(pyKod = "") {
  const b = yangiBaza(pyKod);
  const pyPapka = mkdtempSync(join(tmpdir(), "fuy-py-"));
  copyFileSync(join(b.papka, "t.db"), join(pyPapka, "t.db"));
  // Python mahsulot rasmlari fayl sifatida (config.MAHSULOT_RASM) — ular ham.
  const rasm = join(b.papka, "mahsulot_rasm");
  if (existsSync(rasm)) cpSync(rasm, join(pyPapka, "mahsulot_rasm"), { recursive: true });
  return { ...b, pyPapka };
}

/** Python ishga tushiradi, oxirgi chiqish qatorini JSON qilib qaytaradi. */
export function pyJson(papka, kod) {
  const chiqish = py(papka, kod).trim().split(/\r?\n/);
  return JSON.parse(chiqish[chiqish.length - 1]);
}

/** Python modullarida soatni muzlatuvchi kirish kodi. `SOAT[0]` — joriy vaqt. */
export const PY_SOAT = (boshi) => `
import json, datetime as _dt
from pathlib import Path
SOAT = [_dt.datetime.fromisoformat(${JSON.stringify(boshi)})]
class _FD(_dt.date):
    @classmethod
    def today(cls):
        s = SOAT[0]
        return cls(s.year, s.month, s.day)
class _FDT(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        s = SOAT[0]
        return cls(s.year, s.month, s.day, s.hour, s.minute, s.second, s.microsecond)
from core import tg_rasxod as tr, tg_menyu as tm, vazifa as vz, xabar as xb
for _m in (tr, tm, vz):
    if hasattr(_m, "date"): _m.date = _FD
    if hasattr(_m, "datetime"): _m.datetime = _FDT
`;

/** JS soatini Toshkent devor soati bo'yicha muzlatadi ("YYYY-MM-DD HH:MM:SS"). */
export function jsSoat(devor) {
  const [s, v = "00:00:00"] = devor.replace("T", " ").split(" ");
  const [y, m, d] = s.split("-").map(Number);
  const [h, mi, se = 0] = v.split(":").map(Number);
  soatniQoy(new Date(Date.UTC(y, m - 1, d, h - 5, mi, se)));
}

/**
 * Telegram yozib oluvchisi — Python `PY_TG` bilan AYNAN bir xil xatti-harakat:
 * sendMessage → message_id (101, 102, …); editMessageText matn va klaviatura
 * o'zgarmagan bo'lsa «message is not modified» xatosi (haqiqiy Telegramdek).
 */
export function jsTg(boshMid = 100) {
  const yozuv = [];
  const oxirgi = new Map();
  let mid = boshMid;
  const kalit = (m) => JSON.stringify([m.text ?? null, m.reply_markup ?? null]);
  transportQoy(async (metod, m) => {
    yozuv.push([metod, { ...m }]);
    if (metod === "editMessageText") {
      const k = m.message_id ?? null;
      if (oxirgi.get(k) === kalit(m)) throw new Error("Bad Request: message is not modified");
      oxirgi.set(k, kalit(m));
      return {};
    }
    if (metod === "sendMessage") {
      mid += 1;
      oxirgi.set(mid, kalit(m));
      return { message_id: mid };
    }
    return {};
  });
  return { yozuv, midQoy: (n) => { mid = n; } };
}

export const PY_TG = `
_tq = []
_mid = [100]
_oxirgi = {}
def _kalit(m):
    return (m.get("text"), m.get("reply_markup"))
def _sorov(token, metod, **m):
    m.pop("_vaqt", None)
    m = {k: v for k, v in m.items() if v is not None}
    _tq.append([metod, dict(m)])
    if metod == "editMessageText":
        k = m.get("message_id")
        if _oxirgi.get(k) == _kalit(m):
            raise RuntimeError("Bad Request: message is not modified")
        _oxirgi[k] = _kalit(m)
        return {}
    if metod == "sendMessage":
        _mid[0] += 1
        _oxirgi[_mid[0]] = _kalit(m)
        return {"message_id": _mid[0]}
    return {}
def _rasm(token, chat, yol, izoh=""):
    _tq.append(["sendPhoto", {"chat_id": chat, "caption": izoh or None,
                              "parse_mode": "HTML", "fayl": Path(yol).name}])
xb._sorov = _sorov
xb._rasm_yubor = _rasm
`;

/** Telegram chaqiruvlarini solishtirish uchun: reply_markup parse, None/null tashlanadi. */
export function tgNorm(royxat) {
  return royxat.map(([metod, m]) => {
    const x = {};
    for (const [k, v] of Object.entries(m)) {
      if (v == null) continue;
      x[k] = k === "reply_markup" ? JSON.parse(v) : v;
    }
    return [metod, x];
  });
}

/** Rasxod id lari Python'da juft, JS'da toq — matndagi id larni almashtiradi. */
export function idsiz(x) {
  return JSON.parse(JSON.stringify(x)
    .replace(/rx:del:\d+/g, "rx:del:N")
    .replace(/#\d+/g, "#N"));
}

/** Seed'dan keyingi rasxod/ulush qatorlari — mazmuni bo'yicha (id siz). */
export const RASXOD_SQL = "SELECT id, sana, nom, summa, turi_id, item_id, kim_toladi, umumiymi," +
  " bolish_usul, kim_uchun, izoh, karta_id, reja_id, takror_id, ochirilgan FROM rasxod" +
  " WHERE id > ? ORDER BY id";
export const ULUSH_SQL = "SELECT odam_id, summa, yaxlitlash FROM ulush WHERE rasxod_id=? ORDER BY id";

export const PY_RASXODLAR = (chegara) => `
def _rasxodlar():
    natija = []
    for r in db.q(${JSON.stringify(RASXOD_SQL)}, ${chegara}):
        d = dict(r)
        d["ulush"] = [dict(u) for u in db.q(${JSON.stringify(ULUSH_SQL)}, d["id"])]
        del d["id"]
        natija.append(d)
    return natija
`;

export async function jsRasxodlar(db, chegara) {
  const natija = [];
  for (const r of await db.q(RASXOD_SQL, chegara)) {
    r.ulush = await db.q(ULUSH_SQL, r.id);
    delete r.id;
    natija.push(r);
  }
  return natija;
}
