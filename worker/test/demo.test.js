// Demo rejim: bot suhbati (menyu, rasxod) soxta bazadan, shaxsiy eslatmalar ushlanadi.
import { test } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { yangiBaza, py } from "./fixture.js";
import { D1Shim } from "./d1shim.js";
import { Db } from "../src/db.js";
import * as tg from "../src/tg.js";
import * as xb from "../src/xabar.js";
import * as demo from "../src/demo.js";
import * as tgm from "../src/tg_menyu.js";
import { soatniQoy } from "../src/vaqt.js";

const SEED = String.raw`
from core import entries, xabar as xb, vazifa as vz
F = entries.odam_qosh(db, "Fayzulloxon")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
entries.kirim_qosh(db, "2026-10-01", F, 7_777_000, "Haqiqiy oylik")
xb.sozlama_qoy(db, token="T", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
kitob = vz.tur_qosh(db, "Kitob o'qish", 30, shaxsiy=True)
vz.biriktir(db, kitob, F, "2026-10-04", "17:00")
`;

function qur() {
  const b = yangiBaza(SEED);
  py(b.papka, "import demo, config\ndemo.qur(config.DEMO_PAPKA / 'd.db')");
  b.demoDb = new Db(new D1Shim(join(b.papka, "demo", "d.db")));
  return b;
}
const fid = async (b) => (await b.db.q1("SELECT id FROM odam WHERE nom=?", "Fayzulloxon")).id;
const yuborilgan = [];
tg.transportQoy(async (metod, m) => { yuborilgan.push({ metod, ...m }); return { message_id: 1 }; });
const xat = (text) => ({ update_id: 1, message: { message_id: 5, chat: { id: 111, type: "private" },
  from: { id: 111, username: "fsultonoov" }, text } });

test("bot: /demo yoqadi, menyu javoblari soxta, haqiqiy raqam chiqmaydi; /demo o'chiradi", async () => {
  const b = qur();
  yuborilgan.length = 0;
  await xb.bittasini_ishla(b.db, "T", xat(tgm.PULIM), { demoDb: b.demoDb });
  assert.match(yuborilgan.at(-1).text, /777/);

  await xb.bittasini_ishla(b.db, "T", xat("/demo"), { demoDb: b.demoDb });
  assert.equal(await demo.yoqiqmi(b.db, await fid(b)), true);
  assert.match(yuborilgan.at(-1).text, /YOQILDI/);

  for (const t of [tgm.PULIM, tgm.AYLANMA, tgm.TASHQI, tgm.SHAXSIY, tgm.UY_ISH, "salom"]) {
    yuborilgan.length = 0;
    await xb.bittasini_ishla(b.db, "T", xat(t), { demoDb: b.demoDb });
    const hamma = yuborilgan.map((y) => y.text || "").join("\n");
    assert.ok(!/777|Fayzulloxon|Kitob/.test(hamma), `${t}: ${hamma}`);
  }
  yuborilgan.length = 0;
  await xb.bittasini_ishla(b.db, "T", xat(tgm.PULIM), { demoDb: b.demoDb });
  assert.match(yuborilgan.at(-1).text, /Sardor/);

  // Demo baza ulanmagan — haqiqiy emas, ogohlantirish.
  yuborilgan.length = 0;
  await xb.bittasini_ishla(b.db, "T", xat(tgm.PULIM), {});
  assert.match(yuborilgan.at(-1).text, /ulanmagan/);

  await xb.bittasini_ishla(b.db, "T", xat("/demo off"), { demoDb: b.demoDb });
  assert.equal(await demo.yoqiqmi(b.db, await fid(b)), false);
  yuborilgan.length = 0;
  await xb.bittasini_ishla(b.db, "T", xat(tgm.PULIM), { demoDb: b.demoDb });
  assert.match(yuborilgan.at(-1).text, /Fayzulloxon/);
});

test("eslatma: demo paytida shaxsiy xabar ushlanadi, o'chgach yuboriladi", async () => {
  const b = qur();
  soatniQoy(new Date("2026-10-04T12:05:00Z")); // Toshkent 17:05
  await demo.qoy(b.db, await fid(b), true);
  yuborilgan.length = 0;
  const birinchi = await xb.yubor_kutilayotgan(b.db);
  assert.ok(!yuborilgan.some((y) => String(y.chat_id) === "111"), JSON.stringify(yuborilgan));
  await demo.qoy(b.db, await fid(b), false);
  yuborilgan.length = 0;
  await xb.yubor_kutilayotgan(b.db);
  assert.ok(yuborilgan.some((y) => String(y.chat_id) === "111" && /Kitob/.test(y.text)), JSON.stringify(yuborilgan));
  assert.ok(Array.isArray(birinchi));
});
