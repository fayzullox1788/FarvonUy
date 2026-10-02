// Mini App «Yangi rasxod» API (miniapp_rasxod.js): ruxsat, forma, real balans
// (desktop «Shaxsiy» varag'i bilan parity), saqlash (Python `rasxod_kirit` bilan
// parity: rasxod + ulush qatorlari), tekshiruv xatolari.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { ikkiBaza, pyJson, PY_RASXODLAR, jsRasxodlar } from "./moliya_yordam.js";
import * as ma from "../src/miniapp.js";
import * as plan from "../src/plan.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";
const BUGUN = "2026-10-04";

/** Telegram qanday imzolasa — node:crypto bilan (miniapp.test.js dagi kabi). */
function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Uch odam, kartalar, oktabr rejasi (umumiy 300 000 + Otabekning shaxsiy
// rejasi), Abbosxonning puli band ulushiga yetmaydi — asosiy odam qoplaydi.
const SEED = String.raw`
from core import entries, xabar as xb, mahsulot as mh, hamyon, plan
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"telegram": "Otabek_33"}, O)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
trn = db.skalyar("SELECT id FROM turi WHERE nom='Transport'")
mv = mh.kategoriya_qosh(db, "Mevalar", bz, rasm=mh.bosh_belgilar(db)[0])
k1 = hamyon.karta_qosh(db, F, "Uzcard", 0, "2026-10-01")
k2 = hamyon.karta_qosh(db, F, "Humo", 0, "2026-10-01")
k3 = hamyon.karta_qosh(db, O, "Otabek karta", 0, "2026-10-01")
entries.kirim_qosh(db, "2026-10-01", F, 1_000_000, karta_id=k1)
entries.kirim_qosh(db, "2026-10-01", O, 400_000)
entries.kirim_qosh(db, "2026-10-01", A, 30_000)
entries.rasxod_qosh(db, "2026-10-02", "Non", 30_000, F, turi_id=bz)
entries.rasxod_qosh(db, "2026-10-02", "Taksi", 15_000, O, umumiymi=False, turi_id=trn)
plan.reja_saqla(db, "2026-10", 300_000, {})
plan.reja_yozuv_saqla(db, "2026-10-03", "Kitob", trn, 50_000, umumiymi=False, odam_id=O)
`;

// Python'da bugungi sana — plan modulida muzlatiladi.
const PY_BUGUN = `
import json, datetime as _dt
class _FD(_dt.date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 4)
from core import plan, ledger, rasxod_kirit as rk
plan.date = _FD
`;

function qur() {
  const b = ikkiBaza(SEED);
  soatniQoy(new Date("2026-10-04T07:00:00Z")); // Toshkent 12:00
  b.sor = (yol, { user = { id: 111, username: "fsultonoov" }, tana, init } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: tana ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)), ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    }), {}, b.db);
  b.idlar = pyJson(b.papka, `import json
print(json.dumps({
  "F": db.skalyar("SELECT id FROM odam WHERE nom='Fayzulloxon'"),
  "O": db.skalyar("SELECT id FROM odam WHERE nom='Otabek'"),
  "A": db.skalyar("SELECT id FROM odam WHERE nom='Abbosxon'"),
  "bz": db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'"),
  "mv": db.skalyar("SELECT id FROM turi WHERE nom='Mevalar'"),
  "trn": db.skalyar("SELECT id FROM turi WHERE nom='Transport'"),
  "k1": db.skalyar("SELECT id FROM karta WHERE nom='Uzcard'"),
  "k2": db.skalyar("SELECT id FROM karta WHERE nom='Humo'"),
  "k3": db.skalyar("SELECT id FROM karta WHERE nom='Otabek karta'"),
  "rasm": db.skalyar("SELECT rasm FROM turi WHERE nom='Mevalar'"),
  "chegara": db.skalyar("SELECT MAX(id) FROM rasxod"),
}))`);
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];

test("rasxod API ruxsati: imzosiz 401, begona 403", async () => {
  const b = qur();
  assert.equal((await b.sor("/app/api/rasxod/forma", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("/app/api/rasxod/forma", { user: { id: 999, username: "begona" } })).status, 403);
  assert.equal((await b.sor("/app/api/rasxod", { init: "hash=abc", tana: { summa: 1 } })).status, 401);
  assert.equal((await b.sor("/app/api/rasxod/yoq")).status, 404);
});

test("forma: odamlar, ochgan odam, kartalar, qatnashchilar, kategoriya daraxti", async () => {
  const b = qur();
  const { F, O, A, bz, mv, k1, k2, k3, rasm } = b.idlar;
  const [s, j] = await jsonOl(await b.sor("/app/api/rasxod/forma", { user: { id: 222, username: "otabek_33" } }));
  assert.equal(s, 200);
  assert.equal(j.men, O);
  assert.equal(j.bugun, BUGUN);
  assert.deepEqual(j.odamlar.map((o) => [o.id, o.nom]), [[F, "Fayzulloxon"], [O, "Otabek"], [A, "Abbosxon"]]);
  assert.deepEqual(j.odamlar.map((o) => o.kartalar), [
    [{ id: k1, nom: "Uzcard" }, { id: k2, nom: "Humo" }], [{ id: k3, nom: "Otabek karta" }], []]);
  assert.deepEqual(j.qatnashchilar, [F, O, A]);
  // Faqat faol asosiy kategoriyalar (Python daraxt tartibida), ichkilari bilan
  const py = pyJson(b.papka, `import json
from core import mahsulot as mh
print(json.dumps([[t["id"], t["nom"], t["rasm"], [c["id"] for c in t["bolalar"]]] for t in mh.daraxt(db)]))`);
  assert.deepEqual(j.kategoriyalar.map((k) => [k.id, k.nom, k.ichki.map((c) => c.id)]),
    py.map(([id, nom, , bolalar]) => [id, nom, bolalar]));
  const bozor = j.kategoriyalar.find((k) => k.id === bz);
  assert.deepEqual(bozor.ichki, [{ id: mv, nom: "Mevalar", belgi: rasm.replace(/\.png$/, ".svg"), chuq: 0 }]);
  for (const k of j.kategoriyalar) {
    const asl = py.find((x) => x[0] === k.id)[2];
    assert.equal(k.belgi, asl ? asl.replace(/\.png$/, ".svg") : null);
  }
});

test("real balans: desktop «Shaxsiy» varag'i bilan aynan bir xil (band_hisob parity)", async () => {
  const b = qur();
  const py = pyJson(b.pyPapka, `${PY_BUGUN}
bh = plan.band_hisob(db)
print(json.dumps({
  "real": {str(r["id"]): ledger.balans(db, r["id"])["naqd"] - bh.get(r["id"], {}).get("ayirildi", 0)
           for r in db.q("SELECT id FROM odam WHERE faol=1")},
  "band_pul": {str(k): v for k, v in plan.band_pul(db).items()},
  "band_hisob": {str(k): v for k, v in bh.items()},
  "band_ayirma": {str(k): v for k, v in plan.band_ayirma(db).items()},
}))`);
  const js = {
    band_pul: Object.fromEntries([...await plan.band_pul(b.db)].map(([k, v]) => [String(k), v])),
    band_hisob: Object.fromEntries([...await plan.band_hisob(b.db)].map(([k, v]) => [String(k), v])),
    band_ayirma: Object.fromEntries([...await plan.band_ayirma(b.db)].map(([k, v]) => [String(k), v])),
  };
  assert.deepEqual(js.band_pul, py.band_pul);
  assert.deepEqual(js.band_hisob, py.band_hisob);
  assert.deepEqual(js.band_ayirma, py.band_ayirma);
  // Sinov ma'nosi: reja bor, Abbosxonga yetmaydi, asosiy odam qoplaydi
  const { F, A } = b.idlar;
  assert.ok(py.band_hisob[A].qarz > 0 && py.band_hisob[A].ayirildi < py.band_hisob[A].band);
  assert.ok(py.band_hisob[F].qoplaydi > 0);

  const [, j] = await jsonOl(await b.sor("/app/api/rasxod/forma"));
  assert.deepEqual(Object.fromEntries(j.odamlar.map((o) => [String(o.id), o.real_balans])), py.real);
});

test("band_pul: reja yo'q bo'lsa bo'sh, reja oshib ketsa umumiy band 0 (Python bilan)", async () => {
  const b = qur();
  // Katta umumiy rasxod — umumiy reja oshib ketadi
  const kod = `
from core import entries
entries.rasxod_qosh(db, "2026-10-03", "Katta", 500_000, ${b.idlar.F}, turi_id=${b.idlar.bz})
`;
  pyJson(b.pyPapka, kod + "print(1)");
  pyJson(b.papka, kod + "print(1)");
  const py = pyJson(b.pyPapka, `${PY_BUGUN}
print(json.dumps({str(k): v for k, v in plan.band_pul(db).items()}))`);
  assert.deepEqual(Object.fromEntries([...await plan.band_pul(b.db)].map(([k, v]) => [String(k), v])), py);
  // Boshqa oyda reja yo'q
  const py2 = pyJson(b.pyPapka, `${PY_BUGUN}
print(json.dumps({str(k): v for k, v in plan.band_pul(db, "2026-11-15").items()}))`);
  assert.deepEqual(py2, {});
  assert.equal((await plan.band_pul(b.db, "2026-11-15")).size, 0);
});

/** Bir xil kirish: JS — API orqali, Python — rk.saqla(Qoralama) bilan; qatorlar teng bo'lsin. */
async function solishtir(b, tana, pyQoralama) {
  const [s, j] = await jsonOl(await b.sor("/app/api/rasxod", { tana }));
  assert.equal(s, 200, JSON.stringify(j));
  assert.equal(j.ok, true);
  assert.ok(Number.isInteger(j.id) && j.id % 2 === 1); // Worker — toq id
  const py = pyJson(b.pyPapka, `${PY_BUGUN}
${PY_RASXODLAR(b.idlar.chegara)}
rk.saqla(db, rk.Qoralama(sana="${BUGUN}", ${pyQoralama}))
print(json.dumps(_rasxodlar()))`);
  const js = await jsRasxodlar(b.db, b.idlar.chegara);
  assert.deepEqual(js, py);
  return js;
}

test("saqlash: umumiy — bugun uydagilarga teng, karta bilan (Python rasxod_kirit bilan bir xil)", async () => {
  const b = qur();
  const { F, O, mv, k2 } = b.idlar;
  const js = await solishtir(b,
    { kimning: O, tur: "umumiy", kim_toladi: F, karta_id: k2, turi_id: mv, summa: 145_000, sabab: "Bozor" },
    `kim_toladi=${F}, karta_id=${k2}, turi_id=${mv}, nom="Bozor", summa=145000, tur=rk.UMUMIY`);
  assert.equal(js.length, 1);
  assert.equal(js[0].umumiymi, 1);
  assert.equal(js[0].karta_id, k2);
  assert.equal(js[0].sana, BUGUN);
  assert.equal(js[0].ulush.length, 3);
  assert.equal(js[0].ulush.reduce((s, u) => s + u.summa, 0), 145_000);
});

test("saqlash: shaxsiy — o'zi to'lagan (naqd)", async () => {
  const b = qur();
  const { O, trn } = b.idlar;
  const js = await solishtir(b,
    { kimning: O, tur: "shaxsiy", kim_toladi: O, karta_id: null, turi_id: trn, summa: "12 000", sabab: "Avtobus" },
    `kim_toladi=${O}, karta_id=None, turi_id=${trn}, nom="Avtobus", summa=12000, tur=rk.SHAXSIY`);
  assert.equal(js[0].umumiymi, 0);
  assert.equal(js[0].kim_uchun, null);
  assert.equal(js[0].karta_id, null);
  assert.deepEqual(js[0].ulush, []);
});

test("saqlash: shaxsiy, boshqa to'lagan — «uning uchun» (kim_uchun), to'lovchining kartasi", async () => {
  const b = qur();
  const { F, A, bz, k1 } = b.idlar;
  const js = await solishtir(b,
    { kimning: A, tur: "shaxsiy", kim_toladi: F, karta_id: k1, turi_id: bz, summa: 80_000, sabab: "Poyabzal" },
    `kim_toladi=${F}, karta_id=${k1}, turi_id=${bz}, nom="Poyabzal", summa=80000, tur=rk.UCHUN, kim_uchun=${A}`);
  assert.equal(js[0].kim_uchun, A);
  assert.equal(js[0].kim_toladi, F);
  assert.equal(js[0].umumiymi, 1);
  assert.equal(js[0].bolish_usul, "aniq");
  assert.deepEqual(js[0].ulush.map((u) => [u.odam_id, u.summa]), [[A, 80_000]]);
});

test("tekshiruv: o'zbekcha xato 400, hech narsa yozilmaydi", async () => {
  const b = qur();
  const { F, O, A, bz, k3 } = b.idlar;
  const asos = { kimning: F, tur: "umumiy", kim_toladi: F, karta_id: null, turi_id: bz, summa: 10_000, sabab: "Non" };
  const holatlar = [
    [{ summa: 0 }, "Summa kiritilmagan."],
    [{ summa: "abc" }, "Summa kiritilmagan."],
    [{ sabab: "  " }, "Sabab yozilmagan — rasxod nima uchun?"],
    [{ turi_id: null }, "Kategoriya tanlanmagan."],
    [{ turi_id: 999_999 }, "Bu kategoriya endi yo'q — boshqasini tanlang."],
    [{ kim_toladi: null }, "Kim to'laganini tanlang."],
    [{ karta_id: k3 }, "Bu karta to'lovchiniki emas yoki o'chirilgan — «Qayerdan» ni qayta tanlang."],
    [{ tur: "boshqa" }, "Rasxod turi noma'lum."],
    [{ tur: "shaxsiy", kimning: null }, "Kimning rasxodi ekanini tanlang."],
    [{ tur: "shaxsiy", kimning: 999 }, "Kimning rasxodi ekanini tanlang."],
  ];
  for (const [ozgar, xato] of holatlar) {
    const [s, j] = await jsonOl(await b.sor("/app/api/rasxod", { tana: { ...asos, ...ozgar } }));
    assert.equal(s, 400, JSON.stringify(ozgar));
    assert.deepEqual(j, { ok: false, xato }, JSON.stringify(ozgar));
  }
  assert.deepEqual(await jsRasxodlar(b.db, b.idlar.chegara), []);
  void O; void A;
});

test("ilova: /app/<fayl> ASSETS dan (rasxod.js, belgilar), api va yo'l chiqishi emas", async () => {
  const { ilova } = await import("../src/ilova.js");
  const b = qur();
  const app = ilova({ xabar: {}, vazifa: {}, dars: {} });
  const sorovlar = [];
  const env = { DB: b.d1, ASSETS: { fetch: async (r) => { sorovlar.push(new URL(r.url).pathname); return new Response("x", { status: 200 }); } } };
  const ol = (yol) => app.fetch(new Request(`https://w.example${yol}`), env, {});
  let r = await ol("/app/rasxod.js");
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("cache-control"), "no-cache");
  assert.equal((await ol("/app/belgilar/food_13.svg")).status, 200);
  assert.deepEqual(sorovlar, ["/rasxod.js", "/belgilar/food_13.svg"]);
  assert.equal((await ol("/app/index.html")).status, 404);
  r = await ol("/app/api/rasxod/forma");     // API — ruxsatsiz 401, ASSETS ga ketmaydi
  assert.equal(r.status, 401);
  assert.equal(sorovlar.length, 2);
});
