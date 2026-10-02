// /sinx/* — push (jurnalni qayta o'ynash), pull (sahifalash), rasm, ruxsat.
import { test } from "node:test";
import assert from "node:assert/strict";
import { yangiBaza } from "./fixture.js";
import { ilova } from "../src/ilova.js";

const KALIT = "maxfiy-kalit-123";
const stub = { xabar: {}, vazifa: {}, dars: {} };

function baza(pyKod = `from core import entries\nentries.odam_qosh(db, "Ali")`) {
  const b = yangiBaza(pyKod);
  b.d1.db.exec("CREATE TABLE IF NOT EXISTS rasm(nom TEXT PRIMARY KEY, data BLOB)");
  b.env = { DB: b.d1, SINX_KALIT: KALIT };
  b.app = ilova(stub);
  b.sor = async (yol, body, { kalit = KALIT, method = "POST" } = {}) => {
    const headers = { "content-type": "application/json" };
    if (kalit !== null) headers.authorization = `Bearer ${kalit}`;
    const r = await b.app.fetch(new Request(`https://w.example${yol}`, {
      method, headers, body: method === "GET" ? undefined : JSON.stringify(body),
    }), b.env, {});
    return r;
  };
  b.push = async (body) => { const r = await b.sor("/sinx/push", body); assert.equal(r.status, 200); return r.json(); };
  b.pull = async (dan) => { const r = await b.sor("/sinx/pull", { dan }); assert.equal(r.status, 200); return r.json(); };
  return b;
}

const oz = (id, jadval, qator_id, amal, keyin, oldin = null, extra = {}) => ({
  id, vaqt: "2026-10-02 10:00:00", guruh_id: `g${id}`, tavsif: "desktop", jadval, qator_id, amal,
  oldin: oldin == null ? null : JSON.stringify(oldin),
  keyin: keyin == null ? null : JSON.stringify(keyin), qaytarilgan: 0, bekor: 0, ...extra,
});

test("push: upsert / soft-delete / hard-delete / idempotent / bad table / sozlama / davr / rasm", async () => {
  const b = baza();
  const { db } = b;
  const nOz = await db.skalyar("SELECT COUNT(*) FROM ozgarishlar");
  const menyu = (id, nom, ochirilgan = 0) => ({ id, nom, tartib: 9, ochirilgan });
  const png = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0, 1, 2, 255]);
  const body = {
    ozgarishlar: [
      // tartibsiz yuborilsa ham id bo'yicha qo'llanadi
      oz(1002, "menyu", 1000, "UPDATE", menyu(1000, "Lag'mon \"2\"\n✓")),
      oz(1000, "menyu", 1000, "INSERT", { ...menyu(1000, "Lag'mon"), "yo'q_ustun": 1, "x) ; DROP TABLE odam; --": 2 }),
      oz(1004, "menyu", 1000, "DELETE", menyu(1000, "Lag'mon \"2\"\n✓", 1)),
      oz(1006, "menyu", 1002, "INSERT", menyu(1002, "Somsa")),
      oz(1008, "menyu", 1002, "DELETE", null, menyu(1002, "Somsa")),     // keyin=null → haqiqiy o'chirish
      oz(1010, "odam; DROP TABLE odam", 1, "UPDATE", { nom: "x" }),
      oz(1012, "sqlite_master", 1, "UPDATE", { nom: "x" }),
      oz(1014, "ozgarishlar", 1, "UPDATE", { tavsif: "x" }),
      { ...oz(1016, "menyu", 1004, "INSERT", menyu(1004, "Manti")), sinx: 1 }, // desktop ustuni e'tiborsiz
    ],
    sozlama: { tg_guruh: "-100123", rejim: "qorong'i", tg_offset: "999", "tg_rx:5": "{}", sinx_dan: "7",
      dars_tekshirildi: "x", tg_korilgan_guruhlar: "[]", tg_rasxod_dan: "2000-01-01 00:00:00", nol: null },
    davr: [{ oy: "2026-08", holat: "yopilgan", yopilgan_vaqt: "2026-09-01 09:00:00", izoh: null }],
    rasmlar: [{ nom: "12-0123456789abcdef.png", data: png.toString("base64") },
      { nom: "../evil.png", data: png.toString("base64") }],
  };
  await db.sozlama_qoy("tg_offset", "5");
  const j = await b.push(body);
  assert.equal(j.ok, true);
  assert.deepEqual(j.qabul.sort((x, y) => x - y), [1000, 1002, 1004, 1006, 1008, 1016]);
  assert.deepEqual(j.rad.map((x) => x.id).sort((x, y) => x - y), [1010, 1012, 1014]);

  const m = await db.q1("SELECT * FROM menyu WHERE id=1000");
  assert.deepEqual(m, { id: 1000, nom: "Lag'mon \"2\"\n✓", tartib: 9, ochirilgan: 1 });
  assert.equal(await db.q1("SELECT * FROM menyu WHERE id=1002"), null);
  assert.equal((await db.q1("SELECT nom FROM menyu WHERE id=1004")).nom, "Manti");
  assert.ok(await db.q1("SELECT 1 FROM odam"));                         // jadval joyida
  const ozRows = await db.q("SELECT * FROM ozgarishlar WHERE id>=1000 ORDER BY id");
  assert.deepEqual(ozRows.map((r) => r.id), [1000, 1002, 1004, 1006, 1008, 1016]);
  assert.equal(ozRows[0].guruh_id, "g1000");
  assert.equal(ozRows[0].vaqt, "2026-10-02 10:00:00");
  assert.equal(ozRows[4].keyin, null);

  assert.equal(await db.sozlama("tg_guruh"), "-100123");
  assert.equal(await db.sozlama("rejim"), "qorong'i");
  assert.equal(await db.sozlama("tg_offset"), "5");
  for (const k of ["tg_rx:5", "sinx_dan", "dars_tekshirildi", "tg_korilgan_guruhlar", "tg_rasxod_dan", "nol"]) {
    assert.equal(await db.sozlama(k), null, k);
  }
  assert.deepEqual(await db.q1("SELECT * FROM davr"),
    { oy: "2026-08", holat: "yopilgan", yopilgan_vaqt: "2026-09-01 09:00:00", izoh: null });
  assert.deepEqual(await db.q("SELECT nom FROM rasm"), [{ nom: "12-0123456789abcdef.png" }]);

  // Bot keyin menyu 1000 ni o'zgartirdi; desktop javobni yo'qotib QAYTA yuboradi.
  await db.apply("menyu", "UPDATE", { nom: "Bot nomi" }, 1000);
  const j2 = await b.push({ ...body, davr: [{ oy: "2026-08", holat: "ochiq" }] });
  assert.deepEqual(j2.qabul.sort((x, y) => x - y), [1000, 1002, 1004, 1006, 1008, 1016]);
  assert.equal((await db.q1("SELECT nom FROM menyu WHERE id=1000")).nom, "Bot nomi"); // qayta qo'llanmadi
  assert.equal(await db.skalyar("SELECT COUNT(*) FROM ozgarishlar"), nOz + 6 + 1);
  assert.equal((await db.q1("SELECT holat FROM davr WHERE oy='2026-08'")).holat, "ochiq");
  assert.equal(await db.skalyar("SELECT COUNT(*) FROM rasm"), 1);
});

test("push: UNIQUE to'qnashuvi faqat o'sha qatorni rad etadi, qolgani o'tadi", async () => {
  const b = baza();
  const nom = (await b.db.q1("SELECT nom FROM menyu ORDER BY id LIMIT 1")).nom;
  const j = await b.push({ ozgarishlar: [
    oz(2000, "menyu", 2000, "INSERT", { id: 2000, nom, tartib: 0, ochirilgan: 0 }), // nom UNIQUE
    oz(2002, "menyu", 2002, "INSERT", { id: 2002, nom: "Yangi taom", tartib: 0, ochirilgan: 0 }),
  ] });
  assert.deepEqual(j.qabul, [2002]);
  assert.equal(j.rad.length, 1);
  assert.equal(j.rad[0].id, 2000);
  assert.equal(await b.db.q1("SELECT 1 FROM ozgarishlar WHERE id=2000"), null);
  assert.ok(await b.db.q1("SELECT 1 FROM menyu WHERE id=2002"));
});

test("push: tashqi kalit — bola ota'dan oldin kelsa ham bitta batch ichida o'tadi", async () => {
  const b = baza();
  const odam = (await b.db.q1("SELECT id FROM odam")).id;
  const j = await b.push({ ozgarishlar: [
    oz(3000, "vazifa", 3002, "INSERT", { id: 3002, nom: "Tozalash", odam_id: odam + 100, sana: "2026-10-02",
      davomiylik: 60, holat: "ochiq", ochirilgan: 0, yaratilgan: "2026-10-02 10:00:00" }),
    oz(3002, "odam", odam + 100, "INSERT", { id: odam + 100, nom: "Mehmon", rang: "#000", tartib: 5, faol: 1 }),
  ] });
  assert.deepEqual(j.qabul, [3000, 3002]);
  assert.equal((await b.db.q1("SELECT nom FROM vazifa WHERE id=3002")).nom, "Tozalash");
});

test("pull: faqat toq id, 500 talik sahifalar, sozlama va rasm nomlari", async () => {
  const b = baza();
  const { d1, db } = b;
  const ins = d1.db.prepare("INSERT INTO ozgarishlar(id,guruh_id,tavsif,jadval,qator_id,amal,keyin) VALUES(?,?,?,?,?,?,?)");
  d1.db.exec("BEGIN");
  for (let id = 10001; id <= 11300; id++) ins.run(id, "g", "t", "menyu", 1, "UPDATE", "{}");
  d1.db.exec("COMMIT");
  await db.sozlama_qoy("tg_korilgan_guruhlar", '[{"id":"-1","nom":"Uy","turi":"group"}]');
  await db.exec("INSERT INTO rasm(nom,data) VALUES('2-00000000000000ff.jpg', X'FFD8')");

  const toq = await db.skalyar("SELECT COUNT(*) FROM ozgarishlar WHERE id>10000 AND id%2=1");
  let dan = 10000, jami = [], sahifa = 0, oxirgi;
  do {
    oxirgi = await b.pull(dan);
    assert.ok(oxirgi.ozgarishlar.length <= 500);
    assert.ok(oxirgi.ozgarishlar.every((r) => r.id % 2 === 1 && r.id > dan));
    jami.push(...oxirgi.ozgarishlar.map((r) => r.id));
    if (oxirgi.ozgarishlar.length) assert.equal(oxirgi.oxirgi, oxirgi.ozgarishlar.at(-1).id);
    dan = oxirgi.oxirgi;
    sahifa++;
  } while (oxirgi.kop);
  assert.equal(jami.length, toq);
  assert.equal(sahifa, 2);
  assert.deepEqual(jami, [...jami].sort((x, y) => x - y));
  assert.deepEqual(oxirgi.sozlama, { tg_korilgan_guruhlar: '[{"id":"-1","nom":"Uy","turi":"group"}]', tg_rasxod_dan: null });
  assert.deepEqual(oxirgi.rasmlar, ["2-00000000000000ff.jpg"]);
  const bosh = await b.pull(dan);
  assert.deepEqual([bosh.ozgarishlar.length, bosh.oxirgi, bosh.kop], [0, dan, false]);
  const r0 = (await b.pull(10000)).ozgarishlar[0];
  assert.ok(!("sinx" in r0));
  assert.deepEqual(Object.keys(r0).sort(),
    ["amal", "bekor", "guruh_id", "id", "jadval", "keyin", "oldin", "qator_id", "qaytarilgan", "tavsif", "vaqt"]);
});

test("rasm GET: baytlar va content-type; yo'q yoki yomon nom → 404", async () => {
  const b = baza();
  const bayt = Buffer.from([0xff, 0xd8, 0, 7, 0xff, 0xd9]);
  await b.push({ rasmlar: [{ nom: "7-0123456789abcdef.jpg", data: bayt.toString("base64") }] });
  const r = await b.sor("/sinx/rasm?nom=7-0123456789abcdef.jpg", null, { method: "GET" });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("content-type"), "image/jpeg");
  assert.deepEqual(Buffer.from(await r.arrayBuffer()), bayt);
  assert.equal((await b.sor("/sinx/rasm?nom=8-0123456789abcdef.jpg", null, { method: "GET" })).status, 404);
  assert.equal((await b.sor("/sinx/rasm?nom=../x.jpg", null, { method: "GET" })).status, 404);
});

test("ruxsat: kalitsiz / noto'g'ri / sozlanmagan → 401; noto'g'ri JSON → 400", async () => {
  const b = baza();
  assert.equal((await b.sor("/sinx/pull", { dan: 0 }, { kalit: null })).status, 401);
  assert.equal((await b.sor("/sinx/pull", { dan: 0 }, { kalit: "maxfiy-kalit-12" })).status, 401);
  assert.equal((await b.sor("/sinx/push", {}, { kalit: KALIT + "x" })).status, 401);
  assert.equal((await b.sor("/sinx/rasm?nom=1-0123456789abcdef.png", null, { kalit: null, method: "GET" })).status, 401);
  b.env.SINX_KALIT = "";
  assert.equal((await b.sor("/sinx/pull", { dan: 0 }, { kalit: "" })).status, 401);
  b.env.SINX_KALIT = KALIT;
  const r = await b.app.fetch(new Request("https://w.example/sinx/push", {
    method: "POST", headers: { authorization: `Bearer ${KALIT}` }, body: "{buzuq" }), b.env, {});
  assert.equal(r.status, 400);
  assert.equal((await b.sor("/sinx/boshqa", {})).status, 404);
});
