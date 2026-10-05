// Mini App Sozlamalar → «Hamyon» (miniapp_sz_tolov.js + hamyon.js):
// o'qish va yozish Python `core/hamyon.py` bilan PARITY (natija, qatorlar, jurnal),
// egalik (faqat o'z kartasi — 403), xato matnlari.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { ikkiBaza, pyJson } from "./moliya_yordam.js";
import { qatorlar, jurnal, jurnalNorm, maxOz } from "./_parity.js";
import * as ma from "../src/miniapp.js";
import * as hm from "../src/hamyon.js";
import * as api from "../src/miniapp_sz_tolov.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";
const BUGUN = "2026-10-04";

function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

// Fayzulloxon (111): Uzcard (kirim + rasxod), Humo (boshlang'ich 300 000 + rasxod),
// naqd kirim; Otabek (222): o'z kartasi va o'tkazmasi; Abbosxon — kartasiz.
const SEED = String.raw`
from core import entries, xabar as xb, hamyon
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"telegram": "Otabek_33", "tg_chat": 222}, O)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
k1 = hamyon.karta_qosh(db, F, "Uzcard", 0, "2026-10-01")
k2 = hamyon.karta_qosh(db, F, "Humo", 300_000, "2026-10-01")
k3 = hamyon.karta_qosh(db, O, "Otabek karta", 0, "2026-10-01")
entries.kirim_qosh(db, "2026-10-01", F, 1_000_000, "Oylik", karta_id=k1)
entries.kirim_qosh(db, "2026-10-02", F, 200_000)
entries.kirim_qosh(db, "2026-10-02", F, 50_000, karta_id=k1)
entries.kirim_qosh(db, "2026-10-01", O, 400_000)
entries.kirim_qosh(db, "2026-10-01", A, 30_000)
entries.rasxod_qosh(db, "2026-10-02", "Non", 30_000, F, turi_id=bz, karta_id=k2)
entries.rasxod_qosh(db, "2026-10-03", "Benzin", 45_000, F, umumiymi=False, turi_id=bz, karta_id=k1)
entries.rasxod_qosh(db, "2026-10-03", "Go'sht", 90_000, O, turi_id=bz)
hamyon.otkazma(db, "2026-10-02", O, None, k3, 100_000, "kartaga soldim")
hamyon.otkazma(db, "2026-10-03", F, k1, k2, 70_000)
`;

function qur() {
  const b = ikkiBaza(SEED);
  soatniQoy(new Date("2026-10-04T07:00:00Z")); // Toshkent 12:00
  b.sor = (yol, { user = { id: 111 }, post = false, tana, init } = {}) =>
    ma.ishla(new Request(`https://w.example/app/api/tolov${yol}`, {
      method: post || tana ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)), "content-type": "application/json" },
      body: tana === undefined ? (post ? "{}" : undefined) : (typeof tana === "string" ? tana : JSON.stringify(tana)),
    }), {}, b.db);
  b.kid = async (nom) => (await b.db.q1("SELECT id FROM karta WHERE nom=? AND ochirilgan=0", nom))?.id;
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];

test("ruxsat: imzosiz 401, begona 403, noma'lum yo'l 404, buzuq JSON 400", async () => {
  const b = qur();
  assert.equal((await b.sor("", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("", { user: { id: 999 } })).status, 403);
  assert.equal((await b.sor("/boshqa")).status, 404);
  assert.equal((await b.sor("/karta/abc")).status, 404);
  assert.equal((await b.sor("/karta", { tana: "{buzuq" })).status, 400);
  const [s, j] = await jsonOl(await b.sor("/karta", { tana: "{buzuq" }));
  assert.equal(s, 400);
  assert.equal(j.ok, false);
});

test("o'qish: hamyon va har karta tarixi Python bilan parity (har odam)", async () => {
  const b = qur();
  const kut = pyJson(b.pyPapka, String.raw`
import json
from core import hamyon
r = {}
for o in db.q("SELECT id, tg_chat FROM odam WHERE tg_chat IS NOT NULL ORDER BY id"):
    h = hamyon.hamyon(db, o["id"])
    r[str(o["tg_chat"])] = {"h": h, "t": {str(k["id"]): hamyon.harakatlar(db, k["id"]) for k in h["kartalar"]}}
print(json.dumps(r, ensure_ascii=False))
`);
  for (const [tg, k] of Object.entries(kut)) {
    const [s, j] = await jsonOl(await b.sor("", { user: { id: Number(tg) } }));
    assert.equal(s, 200);
    assert.deepEqual(j.hamyon, k.h, `hamyon ${tg}`);
    assert.equal(j.bugun, BUGUN);
    assert.equal(j.hamyon.naqd + j.hamyon.karta, j.hamyon.jami);
    for (const [kid, tarix] of Object.entries(k.t)) {
      const [s2, j2] = await jsonOl(await b.sor(`/karta/${kid}`, { user: { id: Number(tg) } }));
      assert.equal(s2, 200);
      assert.deepEqual(j2.karta.harakatlar, tarix, `tarix ${kid}`);
      assert.equal(j2.karta.qoldiq, k.h.kartalar.find((x) => x.id === Number(kid)).qoldiq);
    }
  }
  // Ssenariy hamma turdagi qatorni yuradi: kirim (sababsiz ham), rasxod, ikki yo'nalishli o'tkazma.
  const uz = kut["111"].t[String(await b.kid("Uzcard"))];
  assert.deepEqual(new Set(uz.map((x) => x.tur)), new Set(["kirim", "rasxod", "otkazma"]));
  assert.ok(uz.some((x) => x.nima === "Kirim: —"));
  // Funksiyalar ham to'g'ridan-to'g'ri (API'siz) bir xil.
  const fid = (await b.db.q1("SELECT id FROM odam WHERE tg_chat=111")).id;
  assert.deepEqual(await hm.hamyon(b.db, fid), kut["111"].h);
});

test("umumiy pul: faqat asosiy odamga, Python bilan parity, naqd + kartalar = jami", async () => {
  const b = qur();
  const kut = pyJson(b.pyPapka, String.raw`
import json
from core import hamyon, plan
print(json.dumps({"u": hamyon.umumiy(db), "asosiy": db.skalyar("SELECT tg_chat FROM odam WHERE id=?", plan.asosiy_odam(db))}, ensure_ascii=False))
`);
  const [s, j] = await jsonOl(await b.sor("", { user: { id: Number(kut.asosiy) } }));
  assert.equal(s, 200);
  assert.deepEqual(j.umumiy, kut.u);
  assert.equal(j.umumiy.naqd + j.umumiy.karta, j.umumiy.jami);
  for (const tg of [111, 222].filter((x) => x !== Number(kut.asosiy))) {
    const [s2, j2] = await jsonOl(await b.sor("", { user: { id: tg } }));
    assert.equal(s2, 200);
    assert.equal(j2.umumiy, undefined, `boshqa odam (${tg}) umumiyni ko'rmaydi`);
  }
});

test("egalik: boshqa odamning kartasi va o'tkazmasi — 403, yo'q/o'chirilgan — 404", async () => {
  const b = qur();
  const begona = await b.kid("Otabek karta");
  const oz = await b.kid("Humo");
  const otkO = (await b.db.q1("SELECT id FROM karta_otkazma WHERE izoh='kartaga soldim'")).id;
  const oldin = maxOz(b.papka);
  for (const [yol, tana] of [
    [`/karta/${begona}`, undefined],
    [`/karta/${begona}/nom`, { nom: "Meniki" }],
    [`/karta/${begona}/togirla`, { qoldiq: 1 }],
    [`/karta/${begona}/ochir`, {}],
    ["/otkazma", { dan: begona, ga: null, summa: 1000 }],
    ["/otkazma", { dan: oz, ga: begona, summa: 1000 }],
    [`/otkazma/${otkO}/ochir`, {}],
  ]) {
    const [s, j] = await jsonOl(await b.sor(yol, { tana }));
    assert.equal(s, 403, yol);
    assert.equal(j.ok, false);
  }
  // Otabekning o'zi uchun o'sha karta ochiladi
  assert.equal((await b.sor(`/karta/${begona}`, { user: { id: 222 } })).status, 200);
  assert.equal((await b.sor("/karta/99999")).status, 404);
  assert.equal((await b.sor("/otkazma/99999/ochir", { post: true })).status, 404);
  // Hech narsa yozilmadi
  assert.equal(maxOz(b.papka), oldin);
  // O'chirilgan karta — 404
  assert.equal((await b.sor(`/karta/${oz}/ochir`, { post: true })).status, 200);
  assert.equal((await b.sor(`/karta/${oz}`)).status, 404);
  assert.equal((await b.sor(`/karta/${oz}/nom`, { tana: { nom: "X" } })).status, 404);
});

test("summa kiritish: butun so'm, bo'shliqli matn ham; kasr/harf — 400", () => {
  assert.equal(api.summaOl("1 250 000"), 1_250_000);
  assert.equal(api.summaOl(5000), 5000);
  assert.equal(api.summaOl(undefined), 0);
  assert.throws(() => api.summaOl("12.5"));
  assert.throws(() => api.summaOl(12.5));
  assert.throws(() => api.summaOl("abc"));
});

// Bir xil ssenariy: Python `core/hamyon.py` (nusxada) va Mini App API (JS) — natija,
// karta/o'tkazma qatorlari va jurnal (undo guruhlari, tavsiflar) bir xil bo'lsin.
const PY_SSENARIY = String.raw`
import json
from core import hamyon as h
F = db.skalyar("SELECT id FROM odam WHERE tg_chat=111")
S = "2026-10-04"
def kid(n):
    return db.skalyar("SELECT id FROM karta WHERE nom=? AND ochirilgan=0", n)
nat, saq = [], {}
def q(fn, kalit=None):
    try:
        r = fn()
        if kalit: saq[kalit] = r
        nat.append(["ok", r is not None])
    except ValueError as e:
        nat.append(["xato", str(e)])
jami0 = h.hamyon(db, F)["jami"]
q(lambda: h.karta_qosh(db, F, "Visa", 250_000, S))
q(lambda: h.karta_qosh(db, F, "humo", 0, S))
q(lambda: h.karta_qosh(db, F, "   ", 5, S))
q(lambda: h.karta_qosh(db, F, "Yangi", -5, S))
q(lambda: h.karta_qosh(db, F, "Bo'sh", 0, S))
q(lambda: h.otkazma(db, S, F, kid("Humo"), None, 100_000, "bankomat"), "o1")
q(lambda: h.otkazma(db, S, F, kid("Visa"), kid("Humo"), 50_000, None))
q(lambda: h.otkazma(db, S, F, None, kid("Bo'sh"), 1_234_567, None))
q(lambda: h.otkazma(db, S, F, None, None, 10, None))
q(lambda: h.otkazma(db, S, F, None, kid("Humo"), 0, None))
q(lambda: h.qoldiq_togirla(db, kid("Humo"), 400_000, S))
q(lambda: h.qoldiq_togirla(db, kid("Visa"), 120_000, S))
q(lambda: h.qoldiq_togirla(db, kid("Visa"), 120_000, S))
q(lambda: h.qoldiq_togirla(db, kid("Visa"), -1, S))
q(lambda: h.karta_nomla(db, kid("Uzcard"), "Uzcard Plus"))
q(lambda: h.karta_nomla(db, kid("Uzcard Plus"), "visa"))
q(lambda: h.karta_nomla(db, kid("Uzcard Plus"), "  "))
q(lambda: h.karta_ochir(db, kid("Visa")))
q(lambda: h.otkazma_ochir(db, saq["o1"]))
hm = h.hamyon(db, F)
tarix = {k["nom"]: [{a: b for a, b in x.items() if a != "id"} for x in h.harakatlar(db, k["id"])]
         for k in hm["kartalar"]}
print(json.dumps({"nat": nat, "jami0": jami0,
                  "h": {**hm, "kartalar": [{"nom": k["nom"], "qoldiq": k["qoldiq"]} for k in hm["kartalar"]]},
                  "tarix": tarix}, ensure_ascii=False))
`;

const KARTA_SQL = "SELECT odam_id, nom, tartib, ochirilgan FROM karta ORDER BY id";
const OTK_SQL = `SELECT o.sana, o.odam_id, o.summa, o.izoh, o.ochirilgan,
    (SELECT nom FROM karta WHERE id=o.dan_karta_id) dan, (SELECT nom FROM karta WHERE id=o.ga_karta_id) ga
  FROM karta_otkazma o ORDER BY o.id`;

test("yozish: karta qo'shish, o'tkazma, to'g'irlash, nom, o'chirish — Python bilan parity", async () => {
  const b = qur();
  const pyOz = maxOz(b.pyPapka), jsOz = maxOz(b.papka);
  const kut = pyJson(b.pyPapka, PY_SSENARIY);

  const nat = [];
  const saq = {};
  const q = async (yol, tana, kalit = null, natijaBor = (j) => j.id != null) => {
    const [s, j] = await jsonOl(await b.sor(yol, { tana }));
    if (s === 200) { if (kalit) saq[kalit] = j.id; nat.push(["ok", natijaBor(j)]); }
    else { assert.equal(s, 400, `${yol}: ${j.xato}`); nat.push(["xato", j.xato]); }
  };
  const yoq = () => false;
  const k = (nom) => b.kid(nom);
  const [, bosh] = await jsonOl(await b.sor(""));
  await q("/karta", { nom: "Visa", qoldiq: 250_000 });
  await q("/karta", { nom: "humo", qoldiq: 0 });
  await q("/karta", { nom: "   ", qoldiq: 5 });
  await q("/karta", { nom: "Yangi", qoldiq: -5 });
  await q("/karta", { nom: "Bo'sh" });
  await q("/otkazma", { dan: await k("Humo"), ga: null, summa: 100_000, izoh: "bankomat" }, "o1");
  await q("/otkazma", { dan: await k("Visa"), ga: await k("Humo"), summa: "50 000" });
  await q("/otkazma", { dan: "naqd", ga: await k("Bo'sh"), summa: 1_234_567, izoh: "  " });
  await q("/otkazma", { dan: null, ga: null, summa: 10 });
  await q("/otkazma", { dan: null, ga: await k("Humo"), summa: 0 });
  await q(`/karta/${await k("Humo")}/togirla`, { qoldiq: 400_000 }, null, (j) => j.ozgardi);
  await q(`/karta/${await k("Visa")}/togirla`, { qoldiq: 120_000 }, null, (j) => j.ozgardi);
  await q(`/karta/${await k("Visa")}/togirla`, { qoldiq: 120_000 }, null, (j) => j.ozgardi);
  await q(`/karta/${await k("Visa")}/togirla`, { qoldiq: -1 }, null, (j) => j.ozgardi);
  await q(`/karta/${await k("Uzcard")}/nom`, { nom: "Uzcard Plus" }, null, yoq);
  await q(`/karta/${await k("Uzcard Plus")}/nom`, { nom: "visa" }, null, yoq);
  await q(`/karta/${await k("Uzcard Plus")}/nom`, { nom: "  " }, null, yoq);
  await q(`/karta/${await k("Visa")}/ochir`, {}, null, yoq);
  await q(`/otkazma/${saq.o1}/ochir`, {}, null, yoq);

  assert.deepEqual(nat, kut.nat);
  // Natija ko'rinishi
  const [, j] = await jsonOl(await b.sor(""));
  assert.deepEqual({ ...j.hamyon, kartalar: j.hamyon.kartalar.map(({ nom, qoldiq }) => ({ nom, qoldiq })) }, kut.h);
  for (const x of j.hamyon.kartalar) {
    const [, d] = await jsonOl(await b.sor(`/karta/${x.id}`));
    assert.deepEqual(d.karta.harakatlar.map(({ id, ...r }) => r), kut.tarix[x.nom], x.nom);
  }
  // Pul hech qayoqqa ketmadi: o'tkazma/to'g'irlash/o'chirish jamini o'zgartirmaydi.
  assert.equal(bosh.hamyon.jami, kut.jami0);
  assert.equal(j.hamyon.jami, kut.jami0);
  // Qatorlar va jurnal (har amal — bitta undo guruhi, tavsiflari bir xil)
  assert.deepEqual(qatorlar(b.papka, KARTA_SQL, []), qatorlar(b.pyPapka, KARTA_SQL, []));
  assert.deepEqual(qatorlar(b.papka, OTK_SQL, []), qatorlar(b.pyPapka, OTK_SQL, []));
  const jsJ = jurnalNorm(jurnal(b.papka, jsOz)), pyJ = jurnalNorm(jurnal(b.pyPapka, pyOz));
  assert.deepEqual(jsJ, pyJ);
  assert.equal(jsJ.length, 10); // 2 karta, 3 o'tkazma, 2 to'g'irlash, nom, o'chirish, o'tkazma o'chirish
  assert.deepEqual(jsJ[0], [["karta", "INSERT", "Karta qo'shildi: Visa (Fayzulloxon)"],
    ["karta_otkazma", "INSERT", "Karta qo'shildi: Visa (Fayzulloxon)"]]);
  // Hech narsa haqiqatan o'chmadi
  assert.equal(qatorlar(b.papka, "SELECT COUNT(*) n FROM karta WHERE nom='Visa'", [])[0].n, 1);
});

test("karta o'chirilsa qoldig'i naqdga qaytadi, jami o'zgarmaydi; tafsilotsiz javob", async () => {
  const b = qur();
  const [, oldin] = await jsonOl(await b.sor(""));
  const humo = oldin.hamyon.kartalar.find((x) => x.nom === "Humo");
  const [s, j] = await jsonOl(await b.sor(`/karta/${humo.id}/ochir`, { post: true }));
  assert.equal(s, 200);
  assert.equal(j.karta, undefined);
  assert.equal(j.hamyon.jami, oldin.hamyon.jami);
  assert.equal(j.hamyon.naqd, oldin.hamyon.naqd + humo.qoldiq);
  assert.ok(!j.hamyon.kartalar.some((x) => x.id === humo.id));
});
