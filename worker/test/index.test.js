// Worker marshruti (ilova.js) — soxta xabar/vazifa/dars modullari bilan,
// boshqa agentlarning fayllariga bog'lanmasdan.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { yangiBaza } from "./fixture.js";
import { ilova, K_GURUHLAR } from "../src/ilova.js";
import { soatniQoy } from "../src/vaqt.js";

const MAXFIY = "tg-maxfiy_42";

function qur(m = {}) {
  const b = yangiBaza();
  b.chaqiruv = [];
  const yoz = (nom, natija) => async (...a) => { b.chaqiruv.push([nom, a.slice(1)]); return typeof natija === "function" ? natija(...a) : natija; };
  b.m = {
    xabar: {
      bittasini_ishla: yoz("bittasini_ishla"),
      yubor_kutilayotgan: yoz("yubor_kutilayotgan", []),
      eski_izlarni_tozala: yoz("eski_izlarni_tozala"),
      ...m.xabar,
    },
    vazifa: { takror_toldir: yoz("takror_toldir", 0), ...m.vazifa },
    dars: { yangila: yoz("dars.yangila", null), ...m.dars },
  };
  b.app = ilova(b.m);
  b.env = { DB: b.d1, TG_MAXFIY: MAXFIY, SINX_KALIT: "k" };
  b.tg = (update, { yol = MAXFIY, sarlavha = MAXFIY } = {}) => b.app.fetch(new Request(`https://w.example/tg/${yol}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(sarlavha ? { "x-telegram-bot-api-secret-token": sarlavha } : {}) },
    body: typeof update === "string" ? update : JSON.stringify(update),
  }), b.env, {});
  return b;
}

const guruhXabar = (id, title, type = "supergroup") => ({ update_id: 1, message: { message_id: 1, chat: { id, title, type }, text: "salom" } });

test("GET / → ok; noma'lum yo'l → 404", async () => {
  const b = qur();
  const r = await b.app.fetch(new Request("https://w.example/"), b.env, {});
  assert.equal(r.status, 200);
  assert.equal(await r.text(), "ok");
  assert.equal((await b.app.fetch(new Request("https://w.example/boshqa"), b.env, {})).status, 404);
});

test("tg webhook: maxfiy yo'l + sarlavha tekshiriladi, token bilan xabar.bittasini_ishla", async () => {
  const b = qur();
  await b.db.sozlama_qoy("tg_token", "123:ABC");
  const u = { update_id: 5, message: { chat: { id: 77, type: "private" }, text: "/start" } };
  assert.equal((await b.tg(u, { yol: "boshqa" })).status, 404);
  assert.equal((await b.tg(u, { sarlavha: "" })).status, 404);
  assert.equal((await b.tg(u, { sarlavha: "noto'g'ri" })).status, 404);
  assert.equal(b.chaqiruv.length, 0);
  const r = await b.tg(u);
  assert.equal(r.status, 200);
  assert.deepEqual(b.chaqiruv, [["bittasini_ishla", ["123:ABC", u, { demoDb: null }]]]);
  // Maxfiy sozlanmagan bo'lsa yo'l yopiq.
  b.env.TG_MAXFIY = "";
  assert.equal((await b.tg(u, { yol: "", sarlavha: "" })).status, 404);
});

test("tg webhook: handler yiqilsa yoki JSON buzuq bo'lsa ham 200", async () => {
  const b = qur({ xabar: { bittasini_ishla: async () => { throw new Error("portlash"); } } });
  await b.db.sozlama_qoy("tg_token", "t");
  const xato = console.error;
  console.error = () => {};
  try {
    assert.equal((await b.tg({ update_id: 1 })).status, 200);
    assert.equal((await b.tg("{buzuq")).status, 200);
  } finally { console.error = xato; }
});

test("guruhlar sozlama.tg_korilgan_guruhlar ga yoziladi: takrorsiz, yangisi boshida, 10 ta", async () => {
  const b = qur();
  await b.tg(guruhXabar(-1001, "Uy"));
  await b.tg({ update_id: 2, callback_query: { id: "q", data: "bajar:1", message: { chat: { id: -1001, title: "Uy", type: "supergroup" } } } });
  await b.tg({ update_id: 3, message: { chat: { id: 55, type: "private" } } });
  assert.deepEqual(JSON.parse(await b.db.sozlama(K_GURUHLAR)), [{ id: "-1001", nom: "Uy", turi: "supergroup" }]);
  await b.tg({ update_id: 4, my_chat_member: { chat: { id: -5, title: "Ikkinchi", type: "group" } } });
  await b.tg(guruhXabar(-1001, "Uy (yangi nom)"));
  let r = JSON.parse(await b.db.sozlama(K_GURUHLAR));
  assert.deepEqual(r.map((x) => [x.id, x.nom]), [["-1001", "Uy (yangi nom)"], ["-5", "Ikkinchi"]]);
  for (let i = 0; i < 12; i++) await b.tg(guruhXabar(-200 - i, `G${i}`, "group"));
  r = JSON.parse(await b.db.sozlama(K_GURUHLAR));
  assert.equal(r.length, 10);
  assert.equal(r[0].id, "-211");
  // Token yo'q — bittasini_ishla chaqirilmaydi, lekin guruh baribir yoziladi.
  assert.equal(b.chaqiruv.filter((c) => c[0] === "bittasini_ishla").length, 0);
});

test("/sinx/* sinx.js ga uzatiladi (ruxsat bilan)", async () => {
  const b = qur();
  const r = await b.app.fetch(new Request("https://w.example/sinx/pull", { method: "POST", body: "{}" }), b.env, {});
  assert.equal(r.status, 401);
});

test("scheduled: har daqiqa yuboradi; %10 da takror + dars; bir qadam yiqilsa boshqasi ishlaydi", async () => {
  const xato = console.error;
  console.error = () => {};
  try {
    // 10:11 Toshkent — faqat yuborish, hech narsa ketmadi → tozalash yo'q.
    let b = qur();
    soatniQoy(new Date(Date.UTC(2026, 9, 2, 5, 11, 0)));
    await b.app.scheduled({}, b.env, {});
    assert.deepEqual(b.chaqiruv.map((c) => c[0]), ["yubor_kutilayotgan"]);
    assert.equal(b.chaqiruv[0][1][0].getUTCHours(), 10); // Toshkent devor soati

    // 10:20 — yuborildi → tozalash; takror + dars.
    b = qur({ xabar: { yubor_kutilayotgan: async () => { b.chaqiruv.push(["yubor_kutilayotgan"]); return [{}]; } } });
    soatniQoy(new Date(Date.UTC(2026, 9, 2, 5, 20, 0)));
    await b.app.scheduled({}, b.env, {});
    assert.deepEqual(b.chaqiruv.map((c) => c[0]), ["yubor_kutilayotgan", "eski_izlarni_tozala", "takror_toldir", "dars.yangila"]);

    // Hammasi yiqilsa ham har biri chaqiriladi.
    const tushdi = [];
    const yiq = (n) => async () => { tushdi.push(n); throw new Error(n); };
    b = qur({ xabar: { yubor_kutilayotgan: yiq("yubor") }, vazifa: { takror_toldir: yiq("takror") }, dars: { yangila: yiq("dars") } });
    soatniQoy(new Date(Date.UTC(2026, 9, 2, 5, 30, 0)));
    await b.app.scheduled({}, b.env, {});
    assert.deepEqual(tushdi, ["yubor", "takror", "dars"]);
  } finally {
    soatniQoy(null);
    console.error = xato;
  }
});

const BOR = ["xabar.js", "vazifa.js"].every((f) => existsSync(resolve(import.meta.dirname, "../src", f)));
test("index.js haqiqiy modullar bilan yuklanadi", { skip: !BOR && "xabar.js/vazifa.js hali yo'q" }, async () => {
  const m = await import("../src/index.js");
  assert.equal(typeof m.default.fetch, "function");
  assert.equal(typeof m.default.scheduled, "function");
});
