// Mini App API (miniapp.js): Telegram imzosi, kim ochgani, faqat o'z vazifasi.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { yangiBaza } from "./fixture.js";
import * as ma from "../src/miniapp.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";

/** Telegram qanday imzolasa — node:crypto bilan, miniapp.js dan mustaqil. */
function imzola(user, { token = TOKEN, auth = Math.floor(Date.now() / 1000) } = {}) {
  const p = new URLSearchParams({ auth_date: String(auth), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(token).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

const SEED = String.raw`
from core import entries, xabar as xb, vazifa as vz
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"telegram": "Otabek_33"}, O)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
kitob = vz.tur_qosh(db, "Kitob o'qish", 30, shaxsiy=True)
vz.biriktir(db, kitob, F, "2026-10-04", "21:00")
vz.qosh(db, "Do'kon hisoboti", F, "2026-10-04", "17:00", 30)
vz.qosh(db, "Peshin namozi", F, "2026-10-04", "12:30", 20)
db.apply("vazifa", "INSERT", {"nom": "Matematika", "odam_id": F, "sana": "2026-10-04", "vaqt": "14:00",
    "davomiylik": 80, "holat": "ochiq", "manba": "dars:2026-10-04:1"})
vz.qosh(db, "Otabekning ishi", O, "2026-10-04", "10:00", 30)
`;

function qur() {
  const b = yangiBaza(SEED);
  soatniQoy(new Date("2026-10-04T12:20:00Z")); // Toshkent 17:20
  b.sor = (yol, { user = { id: 111, username: "fsultonoov" }, tana, init } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: tana ? "POST" : "GET",
      headers: { authorization: "tma " + (init ?? imzola(user)), ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    }), {}, b.db);
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];

test("initDataTekshir: to'g'ri imzo, buzilgan, boshqa token, eskirgan", async () => {
  const u = { id: 7, username: "x" };
  assert.deepEqual(await ma.initDataTekshir(imzola(u), TOKEN), u);
  const buzuq = imzola(u).replace("username%22%3A%22x", "username%22%3A%22y");
  assert.equal(await ma.initDataTekshir(buzuq, TOKEN), null);
  assert.equal(await ma.initDataTekshir(imzola(u, { token: "boshqa:token" }), TOKEN), null);
  assert.equal(await ma.initDataTekshir(imzola(u, { auth: 1000 }), TOKEN), null);
  assert.equal(await ma.initDataTekshir("", TOKEN), null);
  assert.equal(await ma.initDataTekshir(imzola(u), ""), null);
});

test("ruxsat: imzosiz 401, begona 403, username bo'yicha topiladi", async () => {
  const b = qur();
  assert.equal((await b.sor("/app/api/vazifalar", { init: "hash=abc" })).status, 401);
  assert.equal((await b.sor("/app/api/vazifalar", { user: { id: 999, username: "begona" } })).status, 403);
  const [s, j] = await jsonOl(await b.sor("/app/api/vazifalar?sana=2026-10-04", { user: { id: 222, username: "otabek_33" } }));
  assert.equal(s, 200);
  assert.equal(j.odam, "Otabek");
  assert.deepEqual(j.vazifalar.map((v) => v.nom), ["Otabekning ishi"]);
});

test("vazifalar: faqat o'ziniki, kategoriya qoidasi, Toshkent soati", async () => {
  const b = qur();
  const [s, j] = await jsonOl(await b.sor("/app/api/vazifalar"));
  assert.equal(s, 200);
  assert.equal(j.bugun, "2026-10-04");
  assert.equal(j.hozir, "17:20");
  const t = Object.fromEntries(j.vazifalar.map((v) => [v.nom, v.toifa]));
  assert.deepEqual(t, {
    "Peshin namozi": "namoz", "Matematika": "darslar", "Do'kon hisoboti": "boshqa", "Kitob o'qish": "shaxsiy",
  });
  assert.equal((await b.sor("/app/api/vazifalar?sana=yomon")).status, 400);
});

test("amallar: bajarildi / ochiq / kechiktir / bekor; boshqaning vazifasi 403", async () => {
  const b = qur();
  const id = (nom) => b.db.q1("SELECT id FROM vazifa WHERE nom=?", nom).then((r) => r.id);
  const dokon = await id("Do'kon hisoboti");

  let [s] = await jsonOl(await b.sor(`/app/api/vazifa/${dokon}`, { tana: { amal: "bajarildi" } }));
  assert.equal(s, 200);
  assert.equal((await b.db.q1("SELECT holat FROM vazifa WHERE id=?", dokon)).holat, "bajarildi");
  await b.sor(`/app/api/vazifa/${dokon}`, { tana: { amal: "ochiq" } });
  assert.equal((await b.db.q1("SELECT holat FROM vazifa WHERE id=?", dokon)).holat, "ochiq");

  await b.sor(`/app/api/vazifa/${dokon}`, { tana: { amal: "kechiktir", daqiqa: 30 } });
  assert.equal((await b.db.q1("SELECT kechiktirildi FROM vazifa WHERE id=?", dokon)).kechiktirildi, "2026-10-04 17:50:00");

  await b.sor(`/app/api/vazifa/${dokon}`, { tana: { amal: "bekor" } });
  assert.equal((await b.db.q1("SELECT ochirilgan FROM vazifa WHERE id=?", dokon)).ochirilgan, 1);

  const begona = await id("Otabekning ishi");
  [s] = await jsonOl(await b.sor(`/app/api/vazifa/${begona}`, { tana: { amal: "bajarildi" } }));
  assert.equal(s, 403);
  assert.equal((await b.db.q1("SELECT holat FROM vazifa WHERE id=?", begona)).holat, "ochiq");
  assert.equal((await b.sor(`/app/api/vazifa/${dokon}`, { tana: { amal: "nimadir" } })).status, 404); // o'chirilgan
  // Har amal jurnalga tushadi (desktop sinxroni shundan oladi) — toq id
  const j = await b.db.q("SELECT id FROM ozgarishlar WHERE jadval='vazifa' AND qator_id=?", dokon);
  assert.equal(j.filter((r) => r.id % 2 === 1).length, 4);
});

test("yangi vazifa: toifa saqlanadi, xato matni qaytadi", async () => {
  const b = qur();
  const [s, j] = await jsonOl(await b.sor("/app/api/vazifa",
    { tana: { nom: "  Kir yuvish ", sana: "2026-10-04", vaqt: "18:30", davomiylik: 60, toifa: "uy" } }));
  assert.equal(s, 200);
  const v = await b.db.q1("SELECT * FROM vazifa WHERE id=?", j.id);
  assert.equal(v.nom, "Kir yuvish");
  assert.equal(v.odam_id, (await b.db.q1("SELECT id FROM odam WHERE tg_chat=111")).id);
  assert.equal(v.vaqt, "18:30");
  assert.equal(v.toifa, "uy");
  const [, r] = await jsonOl(await b.sor("/app/api/vazifalar"));
  assert.equal(r.vazifalar.find((x) => x.id === j.id).toifa, "uy");

  const [s2, x] = await jsonOl(await b.sor("/app/api/vazifa", { tana: { nom: "  ", sana: "2026-10-04" } }));
  assert.equal(s2, 400);
  assert.match(x.xato, /bo'sh/);
  assert.equal((await b.sor("/app/api/vazifa", { tana: { nom: "a", vaqt: "25:00" } })).status, 400);
});

test("/app sahifani ASSETS dan beradi; /app/api ilova orqali", async () => {
  const { ilova } = await import("../src/ilova.js");
  const b = qur();
  const app = ilova({ xabar: {}, vazifa: {}, dars: {} });
  let soralgan = null;
  const env = { DB: b.d1, ASSETS: { fetch: async (r) => { soralgan = new URL(r.url).pathname; return new Response("<html>ok</html>", { headers: { "content-type": "text/html" } }); } } };
  const r = await app.fetch(new Request("https://w.example/app"), env, {});
  assert.equal(r.status, 200);
  assert.equal(soralgan, "/index.html");
  assert.equal(await r.text(), "<html>ok</html>");
  assert.equal((await app.fetch(new Request("https://w.example/app/api/vazifalar"), env, {})).status, 401);
  assert.equal((await app.fetch(new Request("https://w.example/app"), { DB: b.d1 }, {})).status, 404);
});

test("namozlar: vaqtini o'zgartirish keyingi barcha kunlarga, faqat o'ziniki", async () => {
  const b = qur();
  // Otabekning namozi ham bor — Fayzulloxon unga tega olmaydi.
  const [, q1] = await jsonOl(await b.sor("/app/api/vazifa", {
    tana: { nom: "Asr namozi", sana: "2026-10-04", vaqt: "17:00", davomiylik: 5, toifa: "namoz", takror: true } }));
  assert.ok(q1.takror_id);
  const [, q2] = await jsonOl(await b.sor("/app/api/vazifa", { user: { id: 222, username: "otabek_33" },
    tana: { nom: "Asr namozi", sana: "2026-10-04", vaqt: "17:10", davomiylik: 5, takror: true } }));
  const [, n] = await jsonOl(await b.sor("/app/api/namozlar"));
  assert.deepEqual(n.namozlar.map((x) => [x.nom, x.vaqt]), [["Asr namozi", "17:00"]]);
  assert.equal((await b.sor("/app/api/namozlar", { tana: { vaqtlar: { [q2.takror_id]: "16:00" } } })).status, 403);

  const [s, j] = await jsonOl(await b.sor("/app/api/namozlar", { tana: { vaqtlar: { [q1.takror_id]: "16:30" } } }));
  assert.equal(s, 200, JSON.stringify(j));
  for (const sana of ["2026-10-04", "2026-10-10", "2026-11-03"]) {
    const [, k] = await jsonOl(await b.sor(`/app/api/vazifalar?sana=${sana}`));
    const asr = k.vazifalar.find((v) => v.nom === "Asr namozi");
    assert.equal(asr.vaqt, "16:30", sana);
    assert.equal(asr.toifa, "namoz");
    assert.equal(asr.takror.vaqt, "16:30");
  }

  // Vazifaning o'zidan: «keyingi kunlarga ham» — o'sha kundan boshlab
  const [, k5] = await jsonOl(await b.sor("/app/api/vazifalar?sana=2026-10-05"));
  const id5 = k5.vazifalar.find((v) => v.nom === "Asr namozi").id;
  await b.sor(`/app/api/vazifa/${id5}`, { tana: { amal: "vaqt", vaqt: "16:15", hammasi: true } });
  const vq = async (sana) => (await jsonOl(await b.sor(`/app/api/vazifalar?sana=${sana}`)))[1]
    .vazifalar.find((v) => v.nom === "Asr namozi").vaqt;
  assert.equal(await vq("2026-10-04"), "16:30");
  assert.equal(await vq("2026-10-05"), "16:15");
  assert.equal(await vq("2026-10-20"), "16:15");
  // faqat shu kun
  await b.sor(`/app/api/vazifa/${id5}`, { tana: { amal: "vaqt", vaqt: "15:00" } });
  assert.equal(await vq("2026-10-05"), "15:00");
  assert.equal(await vq("2026-10-06"), "16:15");
});

test("demo rejim: holat serverda, yoqilsa hamma narsa DEMO_DB dan, haqiqiysiga tegilmaydi", async () => {
  const { D1Shim } = await import("./d1shim.js");
  const { Db } = await import("../src/db.js");
  const { py } = await import("./fixture.js");
  const { join } = await import("node:path");
  const demo = await import("../src/demo.js");
  const b = qur();
  py(b.papka, "import demo, config\ndemo.qur(config.DEMO_PAPKA / 'd.db')");
  const demoD1 = new D1Shim(join(b.papka, "demo", "d.db"));
  const F = { id: 111, username: "fsultonoov" };
  const sor = (yol, env, { user = F, tana } = {}) => ma.ishla(new Request("https://w.example" + yol, {
    method: tana ? "POST" : "GET",
    headers: { authorization: "tma " + imzola(user), ...(tana ? { "content-type": "application/json" } : {}) },
    body: tana ? JSON.stringify(tana) : undefined,
  }), env, b.db);
  const env = { DEMO_DB: demoD1 };

  // Birlamchi o'chiq — haqiqiy odam.
  assert.deepEqual((await (await sor("/app/api/demo", env)).json()), { ok: true, yoqiq: false, ulangan: true });
  assert.equal((await (await sor("/app/api/vazifalar", env)).json()).odam, "Fayzulloxon");
  // Mini App'dan yoqish.
  assert.equal((await (await sor("/app/api/demo", env, { tana: { yoq: true } })).json()).yoqiq, true);
  const [s, j] = await jsonOl(await sor("/app/api/vazifalar", env));
  assert.equal(s, 200);
  assert.equal(j.odam, "Sardor");
  assert.ok(!j.vazifalar.some((v) => /Do'kon|Kitob|namoz/i.test(v.nom)));
  // Boshqa odamga ta'sir qilmaydi.
  assert.equal((await (await sor("/app/api/vazifalar", env, { user: { id: 222, username: "otabek_33" } })).json()).odam, "Otabek");
  // Demo baza ulanmagan bo'lsa — tushunarli xato, haqiqiy ma'lumot EMAS.
  assert.equal((await sor("/app/api/vazifalar", {})).status, 503);
  // Demo'da yozilgan vazifa haqiqiy bazaga tushmaydi.
  const oldin = (await b.db.q1("SELECT count(*) n FROM vazifa")).n;
  assert.equal((await sor("/app/api/vazifa", env, { tana: { nom: "Demo ish", sana: "2026-10-04", vaqt: "09:00" } })).status, 200);
  assert.equal((await b.db.q1("SELECT count(*) n FROM vazifa")).n, oldin);
  assert.ok(await new Db(demoD1).q1("SELECT 1 FROM vazifa WHERE nom='Demo ish'"));
  // Demo yoqiq paytida ham o'chirish mumkin.
  assert.equal((await (await sor("/app/api/demo", env, { tana: {} })).json()).yoqiq, false);
  assert.equal((await (await sor("/app/api/vazifalar", env)).json()).odam, "Fayzulloxon");

  // Bot buyrug'i: /demo — almashtiradi, on/off — aniq; boshqa matn — null.
  assert.equal(await demo.buyruq(b.db, 1, "/demo"), true);
  assert.equal(await demo.yoqiqmi(b.db, 1), true);
  assert.equal(await demo.buyruq(b.db, 1, "/demo"), false);
  assert.equal(await demo.buyruq(b.db, 1, "/demo on"), true);
  assert.equal(await demo.buyruq(b.db, 1, "/demo@farvonuy_bot off"), false);
  assert.equal(await demo.buyruq(b.db, 1, "demo emas"), null);
});
