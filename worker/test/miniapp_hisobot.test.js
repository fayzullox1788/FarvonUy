// «Hisobotlar» API (miniapp_hisobot.js): ruxsat, desktop bilan parity
// (`reja_va_fakt`, `turi_boyicha`/`doira_bolaklari`/`kategoriya_jadvali`,
// `kategoriya_rasxodlari`) — umumiy doira va har odam uchun, to'liq oy va
// oy o'rtasidagi oraliqda; bo'laklar yig'indisi = jami, ro'yxat = bo'lak.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { yangiBaza } from "./fixture.js";
import { pyJson } from "./moliya_yordam.js";
import * as ma from "../src/miniapp.js";
import * as h from "../src/miniapp_hisobot.js";
import * as ledger from "../src/ledger.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";
function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Umumiy, shaxsiy, kim_uchun, bir nechta mahsulotli, ichki kategoriyali
// rasxodlar; umumiy summa, limit, umumiy va shaxsiy reja yozuvlari.
const SEED = String.raw`
import json
from core import entries as en, xabar as xb, mahsulot as mh, plan, rasxod_kirit as rk
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
B = en.odam_qosh(db, "Behruz")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
trn = db.skalyar("SELECT id FROM turi WHERE nom='Transport'")
db.apply("turi", "UPDATE", {"rasm": "food_03.png"}, bz)
bosh = mh.bosh_belgilar(db)
meva = mh.kategoriya_qosh(db, "Meva-sabzavot", ota_id=bz, rasm=bosh[0])
gosht = mh.kategoriya_qosh(db, "Go'sht", ota_id=bz, rasm=bosh[1])
olma = mh.kategoriya_qosh(db, "Olmalar", ota_id=meva, rasm=bosh[2])
boshqa = [r["id"] for r in db.q("SELECT id FROM turi WHERE ota_id IS NULL AND id NOT IN (?,?)", bz, trn)]
en.kirim_qosh(db, "2026-09-01", F, 9_000_000, "Oylik")
def vq(i, v):
    db.apply("rasxod", "UPDATE", {"yaratilgan": v}, i)
vq(en.rasxod_qosh(db, "2026-09-02", "Bozor", 300_000, F, turi_id=bz), "2026-09-02 09:00:00")
vq(en.rasxod_qosh(db, "2026-09-03", "Meva", 100_000, O, turi_id=meva), "2026-09-03 14:30:00")
vq(en.rasxod_qosh(db, "2026-09-06", "Olma", 40_000, F, turi_id=olma), "2026-09-06 12:15:00")
vq(en.rasxod_qosh(db, "2026-09-07", "Go'sht", 150_000, F, turi_id=gosht), "2026-09-07 10:20:00")
vq(en.rasxod_qosh(db, "2026-09-10", "Behruzga meva", 80_000, F, turi_id=meva, kim_uchun=B), "2026-09-10 18:20:00")
vq(en.rasxod_qosh(db, "2026-09-12", "Taksi", 25_000, O, umumiymi=False, turi_id=trn), "2026-09-12 08:00:00")
vq(en.rasxod_qosh(db, "2026-09-14", "Benzin", 50_000, O, umumiymi=False, turi_id=trn), "2026-09-14 17:10:00")
vq(en.rasxod_qosh(db, "2026-09-15", "Avtobus", 12_000, F, turi_id=trn), "2026-09-15 07:40:00")
vq(en.rasxod_qosh(db, "2026-09-16", "Kitob", 70_000, B, umumiymi=False, turi_id=meva), "2026-09-16 19:00:00")
vq(en.rasxod_qosh(db, "2026-09-20", "Kategoriyasiz", 9_000, F), "2026-09-20 11:00:00")
for i, t in enumerate(boshqa[:7]):
    vq(en.rasxod_qosh(db, "2026-09-%02d" % (4 + i), "Mayda %d" % i, 5_000 * (i + 1), F, turi_id=t), "2026-09-04 1%d:00:00" % i)
q = rk.Qoralama(sana="2026-09-14", kim_toladi=F, turi_id=meva, nom="Bozorlik ro'yxati", summa=75_000,
    mahsulotlar=[{"item_id": None, "nom": "Olma", "miqdor": 2, "summa": 25_000},
                 {"item_id": None, "nom": "Banan", "miqdor": 1, "summa": 18_000},
                 {"item_id": None, "nom": "Pomidor", "miqdor": 1, "summa": 32_000}])
vq(rk.saqla(db, q), "2026-09-14 14:30:00")
q = rk.Qoralama(sana="2026-09-15", kim_toladi=O, turi_id=meva, nom="Otabekka", summa=30_000, tur=rk.SHAXSIY,
    mahsulotlar=[{"item_id": None, "nom": "Uzum", "miqdor": 1, "summa": 10_000},
                 {"item_id": None, "nom": "Nok", "miqdor": 1, "summa": 20_000}])
vq(rk.saqla(db, q), "2026-09-15 16:00:00")
vq(en.rasxod_qosh(db, "2026-10-02", "Oktabr bozori", 200_000, F, turi_id=bz), "2026-10-02 09:00:00")
plan.budjet_qoy(db, bz, "2026-09", 900_000)
plan.budjet_qoy(db, trn, "*", 100_000)
plan.reja_yozuv_saqla(db, "2026-09-05", "Meva rejasi", meva, 300_000)
plan.reja_yozuv_saqla(db, "2026-09-05", "Behruz mevasi", meva, 120_000, umumiymi=False, odam_id=B)
plan.reja_yozuv_saqla(db, "2026-09-05", "Otabek taksi", trn, 60_000, umumiymi=False, odam_id=O)
plan.reja_saqla(db, "2026-10", 3_000_000, {})
`;

const ORALIQLAR = [["2026-09-01", "2026-09-30"], ["2026-09-05", "2026-09-18"], ["2026-09-01", "2026-10-31"]];

const KUTILGAN = String.raw`
import json
from core import ledger, plan
odamlar = [None] + [r["id"] for r in db.q("SELECT id FROM odam ORDER BY id")]
oraliqlar = ${JSON.stringify(ORALIQLAR)}
turi = {r["id"]: r["ota_id"] for r in db.q("SELECT id, ota_id FROM turi")}
def avlod(t, x):
    while x is not None:
        if x == t: return True
        x = turi.get(x)
    return False
rasxod_turi = {r["id"]: r["turi_id"] for r in db.q("SELECT id, turi_id FROM rasxod")}
natija = {}
for o in odamlar:
    qism = "shaxsiy" if o else "umumiy"
    k = {"rf": {oy: plan.reja_va_fakt(db, oy, o) for oy in ("2026-09", "2026-10")}, "oraliq": []}
    for boshi, oxiri in oraliqlar:
        tb = ledger.turi_boyicha(db, boshi, oxiri, o, qism)
        kr = {("null" if t["turi_id"] is None else str(t["turi_id"])): ledger.kategoriya_rasxodlari(db, [t["turi_id"]], boshi, oxiri, o, qism) for t in tb}
        ichki = {}
        for t in turi:
            if turi[t] is None: continue
            hammasi = [r for rs in kr.values() for r in rs]
            ichki[str(t)] = sum(r["summa"] for r in hammasi if avlod(t, rasxod_turi[r["id"]]))
        k["oraliq"].append({"tb": tb, "db": ledger.doira_bolaklari(db, boshi, oxiri, odam_id=o, qism=qism),
                            "kj": ledger.kategoriya_jadvali(db, boshi, oxiri, o, qism), "kr": kr, "ichki": ichki})
    natija["null" if o is None else str(o)] = k
print(json.dumps(natija))
`;

let _asos = null;
function asos() {
  if (!_asos) {
    const b = yangiBaza(SEED);
    _asos = { ...b, kut: pyJson(b.papka, KUTILGAN) };
  }
  soatniQoy(new Date("2026-09-20T07:00:00Z")); // Toshkent 12:00
  return _asos;
}
const ids = async (db) => [null, ...(await db.q("SELECT id FROM odam ORDER BY id")).map((r) => r.id)];
const sor = (b, yol, { user = { id: 111, username: "fsultonoov" }, init } = {}) =>
  ma.ishla(new Request(`https://w.example${yol}`, { headers: { authorization: "tma " + (init ?? imzola(user)) } }), {}, b.db);
const ol = async (b, yol) => { const r = await sor(b, yol); const j = await r.json(); assert.equal(r.status, 200, JSON.stringify(j)); return j; };

test("ruxsat: imzosiz 401, begona 403, noto'g'ri parametr 400", async () => {
  const b = asos();
  assert.equal((await sor(b, "/app/api/hisobot", { init: "hash=abc" })).status, 401);
  assert.equal((await sor(b, "/app/api/hisobot", { user: { id: 999, username: "begona" } })).status, 403);
  assert.equal((await sor(b, "/app/api/hisobot?dan=2026-09-10&gacha=2026-09-01")).status, 400);
  assert.equal((await sor(b, "/app/api/hisobot?dan=yomon")).status, 400);
  assert.equal((await sor(b, "/app/api/hisobot?doira=abc")).status, 400);
  assert.equal((await sor(b, "/app/api/hisobot?doira=999")).status, 404);
  assert.equal((await sor(b, "/app/api/hisobot/kategoriya?idlar=x")).status, 400);
  assert.equal((await sor(b, "/app/api/hisobot/kategoriya?idlar=99999")).status, 404);
  assert.equal((await sor(b, "/app/api/hisobot/boshqa")).status, 404);
});

test("birlamchi oraliq: oyning 1-kunidan bugungacha, umumiy doira, ochgan odam", async () => {
  const b = asos();
  const j = await ol(b, "/app/api/hisobot");
  assert.equal(j.dan, "2026-09-01");
  assert.equal(j.gacha, "2026-09-20");
  assert.equal(j.doira, "umumiy");
  assert.equal(j.odam.nom, "Fayzulloxon");
  assert.deepEqual(j.odamlar.map((o) => o.nom), ["Fayzulloxon", "Otabek", "Behruz"]);
});

test("parity: reja_va_fakt (to'liq, kategoriya qatorlari bilan) — umumiy va har odam", async () => {
  const b = asos();
  for (const o of await ids(b.db)) {
    for (const oy of ["2026-09", "2026-10"]) {
      assert.deepEqual(await h.reja_va_fakt(b.db, oy, o), b.kut[String(o)].rf[oy], `${o} ${oy}`);
    }
  }
});

test("parity: turi_boyicha, doira_bolaklari, kategoriya_jadvali, kategoriya_rasxodlari", async () => {
  const b = asos();
  for (const o of await ids(b.db)) {
    const qism = o ? "shaxsiy" : "umumiy";
    for (const [i, [dan, gacha]] of ORALIQLAR.entries()) {
      const k = b.kut[String(o)].oraliq[i];
      const izoh = `${o} ${dan}..${gacha}`;
      assert.deepEqual(await ledger.turi_boyicha(b.db, dan, gacha, o, qism), k.tb, izoh);
      assert.deepEqual(await h.doira_bolaklari(b.db, dan, gacha, 6, o, qism), k.db, izoh);
      assert.deepEqual(await h.kategoriya_jadvali(b.db, dan, gacha, o, qism), k.kj, izoh);
      for (const t of k.tb) {
        assert.deepEqual(await h.kategoriya_rasxodlari(b.db, [t.turi_id], dan, gacha, o, qism), k.kr[String(t.turi_id)], izoh);
      }
    }
  }
});

test("seed qamrovi: umumiyda Qolganlari va Kategoriyasiz, shaxsiyda kim_uchun va mahsulotlar", async () => {
  const b = asos();
  const k = b.kut["null"].oraliq[0];
  assert.ok(k.db.some((x) => x.tur === "qolgan"));
  assert.ok(k.db.some((x) => x.tur === "kategoriyasiz"));
  const bId = (await b.db.q1("SELECT id FROM odam WHERE nom='Behruz'")).id;
  const bk = b.kut[String(bId)].oraliq[0];
  assert.ok(Object.values(bk.kr).flat().some((r) => r.kim_uchun === bId));
});

test("API: xulosa = bo'laklar yig'indisi = Python; jadval rejasi = reja_va_fakt; kategoriya va ro'yxat yig'indilari", async () => {
  const b = asos();
  const odamlar = await ids(b.db);
  const turlar = await b.db.q("SELECT id, ota_id FROM turi");
  const ichkilar = turlar.filter((t) => t.ota_id != null);
  for (const o of odamlar) {
    const doira = o == null ? "umumiy" : String(o);
    for (const [i, [dan, gacha]] of ORALIQLAR.entries()) {
      const k = b.kut[String(o)].oraliq[i];
      const izoh = `${doira} ${dan}..${gacha}`;
      const q = `dan=${dan}&gacha=${gacha}&doira=${doira}`;
      const j = await ol(b, `/app/api/hisobot?${q}`);
      const pyJami = k.tb.reduce((s, t) => s + t.summa, 0);
      assert.equal(j.xulosa.fakt, pyJami, izoh);
      assert.equal(j.bolaklar.reduce((s, x) => s + x.summa, 0), pyJami, izoh);
      if (j.bolaklar.length) assert.equal(j.bolaklar.reduce((s, x) => s + x.ulush, 0), 1000, izoh);

      // Reja: bitta oy ichida — o'sha oy; to'liq oylar — yig'indi.
      const rf = b.kut[String(o)].rf;
      const oylik = (oy) => (rf[oy].reja_bor ? rf[oy].reja : 0);
      const kutReja = i < 2 ? (rf["2026-09"].reja_bor ? rf["2026-09"].reja : null)
        : (rf["2026-09"].reja_bor || rf["2026-10"].reja_bor ? oylik("2026-09") + oylik("2026-10") : null);
      assert.equal(j.xulosa.reja, kutReja || null, izoh);
      if (i === 0) {
        for (const row of j.jadval.filter((r) => r.turi_id)) {
          const pq = rf["2026-09"].qatorlar.find((x) => x.turi_id === row.turi_id);
          assert.equal(row.reja, pq && pq.reja ? pq.reja : null, `${izoh} reja ${row.nom}`);
        }
      }

      for (const bl of j.bolaklar) {
        const d = await ol(b, `/app/api/hisobot/kategoriya?idlar=${bl.idlar.join(",")}&${q}`);
        assert.equal(d.xulosa.fakt, bl.summa, `${izoh} kat ${bl.nom}`);
        if (d.ichki.length) assert.equal(d.ichki.reduce((s, x) => s + x.summa, 0), bl.summa, `${izoh} ichki ${bl.nom}`);
        const r = await ol(b, `/app/api/hisobot/rasxodlar?idlar=${bl.idlar.join(",")}&${q}`);
        const qatorlar = r.kunlar.flatMap((x) => x.qatorlar);
        assert.equal(qatorlar.reduce((s, x) => s + x.summa, 0), bl.summa, `${izoh} ro'yxat ${bl.nom}`);
        for (const kun of r.kunlar) assert.equal(kun.jami, kun.qatorlar.reduce((s, x) => s + x.summa, 0));
        for (const x of qatorlar) if (x.mahsulotlar.length) assert.equal(x.mahsulotlar.reduce((s, m) => s + m.summa, 0), x.summa);
        assert.deepEqual(d.songgi.map((x) => x.id), qatorlar.slice(0, 3).map((x) => x.id));
        if (bl.tur === "turi") {
          const py = bl.idlar.flatMap((t) => k.kr[String(t)] || []);
          assert.deepEqual(qatorlar.map((x) => [x.id, x.summa]), py.map((x) => [x.id, x.summa]), izoh);
        }
        // Ichki kategoriya sahifasi — o'z (va avlodlari) rasxodi
        for (const ic of d.ichki.filter((x) => x.turi_id)) {
          const s = await ol(b, `/app/api/hisobot/rasxodlar?turi_id=${ic.turi_id}${ic.ozi ? "&ozi=1" : ""}&${q}`);
          assert.equal(s.xulosa.fakt, ic.summa, `${izoh} ichki ro'yxat ${ic.nom}`);
        }
      }
      for (const t of ichkilar) {
        const s = await ol(b, `/app/api/hisobot/rasxodlar?turi_id=${t.id}&${q}`);
        assert.equal(s.xulosa.fakt, k.ichki[String(t.id)], `${izoh} ichki ${t.id}`);
      }
    }
  }
});

test("davr rejasi: bitta oy — o'sha oy, to'liq oylar — yig'indi, qisman ko'p oy — yo'q", async () => {
  assert.deepEqual(h.davr_oylari("2026-09-05", "2026-09-18"), ["2026-09"]);
  assert.deepEqual(h.davr_oylari("2026-09-01", "2026-10-31"), ["2026-09", "2026-10"]);
  assert.equal(h.davr_oylari("2026-09-05", "2026-10-03"), null);
  assert.equal(h.davr_oylari("2026-01-01", "2026-10-02"), null);
  assert.deepEqual(h.davr_oylari("2025-12-01", "2026-01-31"), ["2025-12", "2026-01"]);
  const b = asos();
  const j = await ol(b, "/app/api/hisobot?dan=2026-09-05&gacha=2026-10-03");
  assert.equal(j.xulosa.reja, null);
  assert.ok(j.jadval.every((r) => r.reja === null));
});

test("mahsulotli rasxod: qatorlari alohida, nomi va yo'li; tafsilot", async () => {
  const b = asos();
  const meva = (await b.db.q1("SELECT id FROM turi WHERE nom='Meva-sabzavot'")).id;
  const r = await ol(b, `/app/api/hisobot/rasxodlar?turi_id=${meva}&dan=2026-09-14&gacha=2026-09-14`);
  assert.equal(r.kunlar.length, 1);
  const x = r.kunlar[0].qatorlar[0];
  assert.deepEqual(x.mahsulotlar.map((m) => m.nom), ["Olma", "Banan", "Pomidor"]);
  assert.equal(x.vaqt, "14:30");
  assert.equal(x.yol, "Bozorlik → Meva-sabzavot");
  assert.equal(x.tafsilot.doira, "Umumiy");
  assert.equal(x.tafsilot.joy, "Naqd");
  assert.equal(x.tafsilot.ulushlar.reduce((s, u) => s + u.summa, 0), 75_000);
  assert.equal(r.xulosa.reja, 300_000);
  assert.equal(r.kunlar[0].jami, 75_000);
});
