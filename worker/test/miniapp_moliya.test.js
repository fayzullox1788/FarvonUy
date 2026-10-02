// Mini App «Moliya» API (miniapp_moliya.js): kartalar va «Reja va fakt» — Python
// bilan PARITY, bugungi yozuvlar qoidasi, o'z rasxodini o'chirish.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { yangiBaza, py } from "./fixture.js";
import * as ma from "../src/miniapp.js";
import * as mo from "../src/miniapp_moliya.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";

function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Python'da «bugun» = 2026-10-04 (plan.date muzlatiladi — band_pul joriy oyni oladi).
const PY_SOAT = String.raw`
import json, datetime as _dt
from core import plan
class _FD(_dt.date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 4)
plan.date = _FD
`;

const SEED = PY_SOAT + String.raw`
from core import entries as en, xabar as xb
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
B = en.odam_qosh(db, "Behruz")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"telegram": "Otabek_33", "tg_chat": 222}, O)
db.apply("odam", "UPDATE", {"tg_chat": 333}, B)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
trn = db.skalyar("SELECT id FROM turi WHERE nom='Transport'")
db.apply("turi", "UPDATE", {"rasm": "food_03.png"}, bz)
en.kirim_qosh(db, "2026-10-01", F, 5_000_000, "Oylik")
en.kirim_qosh(db, "2026-10-01", O, 300_000, "Oylik")
en.kirim_qosh(db, "2026-10-01", B, 100_000, "Stipendiya")
en.kirim_qosh(db, "2026-09-01", F, 1_000_000, "Oylik")
def vaqt(jadval, i, v):
    db.apply(jadval, "UPDATE", {"yaratilgan": "2026-10-04 " + v}, i)
vaqt("rasxod", en.rasxod_qosh(db, "2026-10-04", "Non, sut", 120_000, F, turi_id=bz), "14:30:00")
vaqt("rasxod", en.rasxod_qosh(db, "2026-10-04", "Taksi", 15_000, O, umumiymi=False, turi_id=trn), "08:10:00")
vaqt("rasxod", en.rasxod_qosh(db, "2026-10-04", "Go'sht", 90_000, O, turi_id=bz), "12:00:00")
en.rasxod_qosh(db, "2026-10-03", "Olma", 80_000, F, turi_id=bz, kim_uchun=B)
en.rasxod_qosh(db, "2026-09-15", "Bozor", 600_000, F, turi_id=bz)
en.rasxod_qosh(db, "2026-09-20", "Benzin", 50_000, O, umumiymi=False, turi_id=trn)
plan.reja_saqla(db, "2026-10", 3_000_000, {})
plan.reja_saqla(db, "2026-09", 500_000, {})
plan.reja_yozuv_saqla(db, "2026-10-04", "Uy ijarasi", bz, 650_000)
plan.reja_yozuv_saqla(db, "2026-10-04", "Kitoblar", bz, 400_000, umumiymi=False, odam_id=B)
plan.reja_yozuv_saqla(db, "2026-10-05", "Ertangi", bz, 70_000)
vaqt("qarz", en.qarz_qosh(db, "2026-10-04", O, F, 200_000, "kartaga"), "09:20:00")
vaqt("hisob_kitob", en.hisob_kitob_qosh(db, "2026-10-04", B, F, 10_000), "11:00:00")
tq = en.tashqi_qarz_qosh(db, "2026-10-04", F, "Aziz aka", 500_000)
vaqt("tashqi_qarz", tq, "07:00:00")
uq = en.tashqi_qarz_qosh(db, "2026-10-04", O, "Bank", 300_000, umumiy=True, qatnashchilar=[F, O, B])
vaqt("tashqi_qarz", uq, "06:00:00")
vaqt("tashqi_tolov", en.tashqi_tolov_qosh(db, tq, "2026-10-04", 100_000), "16:00:00")
`;

// Python haqiqati — har odam uchun kartalar, uch oy uchun reja va fakt, bugungi rejalar.
const KUTILGAN = PY_SOAT + String.raw`
from core import ledger
odamlar = [r["id"] for r in db.q("SELECT id FROM odam ORDER BY id")]
bh = plan.band_hisob(db)
k = {}
for oid in odamlar:
    h = bh.get(oid, {"band": 0, "qoplaydi": 0})
    k[oid] = {"balans": ledger.balans(db, oid)["naqd"], "band": h["band"] + h["qoplaydi"],
              "qarzim": plan.odam_qarzlari(db, oid)["jami"],
              "reja_kun": [y["id"] for y in plan.kun_reja_yozuvlari(db, "2026-10-04")
                           if y["umumiymi"] or y["odam_id"] == oid]}
rf = {}
for oy in ("2026-10", "2026-09", "2026-08"):
    r = plan.reja_va_fakt(db, oy)
    rf[oy] = {"oy": oy, "reja_bor": r["reja_bor"], "reja": r["reja"] if r["reja_bor"] else None,
              "fakt": r["fakt"], "foiz": r["foiz"] if r["reja_bor"] else None}
print(json.dumps({"k": k, "rf": rf, "band_qarz": {o: v["qarz"] for o, v in bh.items()}}))
`;

let _asos = null;
function asos() {
  if (!_asos) {
    const b = yangiBaza(SEED);
    const chiq = py(b.papka, KUTILGAN).trim().split(/\r?\n/);
    _asos = { papka: b.papka, kut: JSON.parse(chiq[chiq.length - 1]) };
  }
  return _asos;
}

function qur() {
  const { kut } = asos();
  const b = yangiBaza(SEED);
  soatniQoy(new Date("2026-10-04T12:20:00Z")); // Toshkent 17:20
  b.kut = kut;
  b.sor = (yol, { user = { id: 111 }, post = false, init } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: post ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)) },
    }), {}, b.db);
  b.id = async (sql, ...a) => (await b.db.q1(sql, ...a)).id;
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];

test("ruxsat: imzosiz 401, begona 403, noto'g'ri oy 400, POST/GET aralash 404", async () => {
  const b = qur();
  assert.equal((await b.sor("/app/api/moliya", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("/app/api/moliya", { user: { id: 999 } })).status, 403);
  assert.equal((await b.sor("/app/api/moliya?oy=2026-13")).status, 400);
  assert.equal((await b.sor("/app/api/moliya", { post: true })).status, 404);
  assert.equal((await b.sor("/app/api/moliya/rasxod/1/ochir")).status, 404);
  assert.equal((await b.sor("/app/api/moliya/boshqa")).status, 404);
});

test("kartalar: har odam uchun Python bilan parity (balans, band, Qarzim)", async () => {
  const b = qur();
  // Ssenariy haqiqatan hamma tarmoqni yuradi: kimdadir band qarzi bor, asosiy qoplaydi.
  assert.ok(Object.values(b.kut.band_qarz).some((v) => v > 0), "band qarzi bo'lsin");
  for (const [oid, k] of Object.entries(b.kut.k)) {
    const tg = (await b.db.q1("SELECT tg_chat FROM odam WHERE id=?", Number(oid))).tg_chat;
    const [s, j] = await jsonOl(await b.sor("/app/api/moliya", { user: { id: Number(tg) } }));
    assert.equal(s, 200);
    assert.deepEqual(j.kartalar, { balans: k.balans, band: k.band, qarzim: k.qarzim }, `odam ${oid}`);
    assert.deepEqual(j.yozuvlar.filter((y) => y.tur === "reja").map((y) => y.id).sort(),
      [...k.reja_kun].sort(), `reja ${oid}`);
  }
});

test("oy xarajati: «Reja va fakt» parity — bu oy, o'tgan oy, rejasiz oy", async () => {
  const b = qur();
  for (const oy of ["2026-10", "2026-09", "2026-08"]) {
    const [s, j] = await jsonOl(await b.sor(`/app/api/moliya?oy=${oy}`));
    assert.equal(s, 200);
    assert.deepEqual(j.xarajat, b.kut.rf[oy], oy);
  }
  const [, j] = await jsonOl(await b.sor("/app/api/moliya"));
  assert.equal(j.xarajat.oy, "2026-10");
  assert.equal(j.joriy_oy, "2026-10");
  assert.equal(j.otgan_oy, "2026-09");
  assert.equal(j.bugun, "2026-10-04");
  assert.equal(b.kut.rf["2026-08"].reja_bor, false);
  assert.equal(mo.foiz(2_130_000, 3_000_000), 71);
  assert.equal(mo.foiz(1, 0), null);
  assert.equal(mo.oy_sur("2026-01", -1), "2025-12");
});

test("bugun: Fayzulloxonga tegadigan yozuvlar, tartib, belgi va summa", async () => {
  const b = qur();
  const [, j] = await jsonOl(await b.sor("/app/api/moliya"));
  const qisqa = j.yozuvlar.map((y) => [y.nom, y.belgi, y.vaqt, y.ishora + y.summa, y.rang]);
  const reja = qisqa.find((x) => x[1] === "Reja");
  assert.match(reja[2] ?? "", /^\d\d:\d\d$/); // jurnaldagi INSERT vaqti
  assert.deepEqual(qisqa.filter((x) => x[1] !== "Reja"), [
    ["Aziz akaga qarz qaytarildi", "Qarz", "16:00", "-100000", "navy"],
    ["Bozorlik", "Xarajat", "14:30", "-120000", "qizil"],
    ["Bozorlik", "Xarajat", "12:00", "-90000", "qizil"],
    ["Behruzdan qarz qaytdi", "Qarz", "11:00", "+10000", "yashil"],
    ["Otabekdan qarz", "Qarz", "09:20", "+200000", "yashil"],
    ["Aziz akadan qarz", "Qarz", "07:00", "+500000", "yashil"],
    ["Bankdan qarz", "Qarz", "06:00", "+100000", "yashil"], // umumiy — faqat UNING ulushi
  ]);
  assert.deepEqual(reja.slice(0, 1).concat(reja.slice(3)), ["Uy ijarasi (reja)", "-650000", "navy"]);
  // Otabekning shaxsiy taksisi va Behruzning shaxsiy rejasi Fayzulloxonda YO'Q.
  assert.ok(!j.yozuvlar.some((y) => y.tafsilot.sabab === "Taksi" || y.nom.startsWith("Kitoblar")));
  const ozi = j.yozuvlar.find((y) => y.vaqt === "14:30");
  assert.equal(ozi.ozimi, true);
  assert.equal(ozi.rasm, "food_03");
  assert.deepEqual(ozi.tafsilot.ulushlar, [
    { nom: "Fayzulloxon", summa: 40000 }, { nom: "Otabek", summa: 40000 }, { nom: "Behruz", summa: 40000 }]);
  assert.equal(ozi.tafsilot.joy, "Naqd");
  assert.equal(ozi.tafsilot.doira, "Umumiy");
  assert.equal(j.yozuvlar.find((y) => y.vaqt === "12:00").ozimi, false);

  // Otabek: o'z taksisi (shaxsiy), Fayzulloxonga bergan qarzi (navy, minus).
  const [, o] = await jsonOl(await b.sor("/app/api/moliya", { user: { id: 222 } }));
  const on = o.yozuvlar.map((y) => [y.nom, y.ishora + y.summa]);
  assert.ok(on.some(([nm, s]) => nm === "Transport" && s === "-15000"));
  assert.ok(on.some(([nm, s]) => nm === "Fayzulloxonga qarz" && s === "-200000"));
  assert.ok(!on.some(([nm]) => nm.startsWith("Aziz aka")));
  // Behruz: o'z shaxsiy rejasi ko'rinadi, «uning uchun» olingan olma kechagi — yo'q.
  const [, bj] = await jsonOl(await b.sor("/app/api/moliya", { user: { id: 333 } }));
  assert.ok(bj.yozuvlar.some((y) => y.nom === "Kitoblar (reja)"));
  assert.ok(bj.yozuvlar.some((y) => y.nom === "Fayzulloxonga qarz to‘landi" && y.ishora === "-"));
});

test("o'chirish: faqat to'lagan odam, yumshoq, bitta jurnal guruhi (toq id)", async () => {
  const b = qur();
  const ozi = await b.id("SELECT id FROM rasxod WHERE nom='Non, sut'");
  const boshqa = await b.id("SELECT id FROM rasxod WHERE nom=?", "Go'sht");
  assert.equal((await b.sor(`/app/api/moliya/rasxod/${ozi}/ochir`, { post: true, user: { id: 222 } })).status, 403);
  assert.equal((await b.sor(`/app/api/moliya/rasxod/${boshqa}/ochir`, { post: true })).status, 403);
  assert.equal((await b.sor("/app/api/moliya/rasxod/99999/ochir", { post: true })).status, 404);

  const [s, j] = await jsonOl(await b.sor(`/app/api/moliya/rasxod/${ozi}/ochir`, { post: true }));
  assert.equal(s, 200);
  assert.equal(j.ok, true);
  const r = await b.db.q1("SELECT ochirilgan FROM rasxod WHERE id=?", ozi);
  assert.equal(r.ochirilgan, 1); // qator joyida
  const jurnal = await b.db.q("SELECT id, guruh_id, amal, tavsif FROM ozgarishlar WHERE jadval='rasxod' AND qator_id=? AND amal='DELETE'", ozi);
  assert.equal(jurnal.length, 1);
  assert.equal(jurnal[0].id % 2, 1);
  assert.match(jurnal[0].tavsif, /Rasxod o'chirildi: Non, sut/);
  assert.equal((await b.sor(`/app/api/moliya/rasxod/${ozi}/ochir`, { post: true })).status, 404);

  const [, keyin] = await jsonOl(await b.sor("/app/api/moliya"));
  assert.ok(!keyin.yozuvlar.some((y) => y.tur === "rasxod" && y.id === ozi));
});

test("ga(): o'zbekcha qo'shimcha", () => {
  assert.equal(mo.ga("Otabek"), "Otabekka");
  assert.equal(mo.ga("Aziz aka"), "Aziz akaga");
  assert.equal(mo.ga("Farruq"), "Farruqqa");
  assert.equal(mo.rasm_kaliti("food_03.png"), "food_03");
  assert.equal(mo.rasm_kaliti("../x.png"), null);
});
