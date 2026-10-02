// Mini App Sozlamalar → Profil / Uy a'zolari / Bildirishnomalar / Ilova
// (miniapp_sz_profil.js): Python bilan PARITY (rang, ism o'zgartirish, Telegram
// nomi, dm_yoqmaganlar, kechiktirish, uborka, dars, asosiy odam) va ruxsat.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { yangiBaza } from "./fixture.js";
import { ikkiBaza, pyJson } from "./moliya_yordam.js";
import * as ma from "../src/miniapp.js";
import * as pr from "../src/miniapp_sz_profil.js";
import { soatniQoy } from "../src/vaqt.js";

const TOKEN = "123456:SINOV-token";

function imzola(user) {
  const p = new URLSearchParams({ auth_date: String(Math.floor(Date.now() / 1000)), query_id: "AAE1", user: JSON.stringify(user) });
  const qator = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
  const sir = createHmac("sha256", "WebAppData").update(TOKEN).digest();
  p.set("hash", createHmac("sha256", sir).update(qator).digest("hex"));
  return p.toString();
}

const SEED = String.raw`
import json
from core import entries as en, xabar as xb, vazifa as vz, dars
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
B = en.odam_qosh(db, "Behruz")
Q = en.odam_qosh(db, "Qadimgi")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov", "tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"telegram": "Otabek_33"}, O)
db.apply("odam", "UPDATE", {"tg_chat": 333}, B)
en.odam_ochir(db, Q)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-100500", yoqilgan=True, kunlik_vaqt="07:30")
db.sozlama_qoy("tg_kechiktirish", "15,45,90")
db.sozlama_qoy("tg_korilgan_guruhlar", json.dumps([{"id": "-100500", "nom": "Farovon oila", "turi": "supergroup"}]))
db.sozlama_qoy("asosiy_odam", str(O))
vz.uborka_kuni_qoy(db, 5)
vz.uborka_vaqti_qoy(db, "09:30")
dars.sozlama_qoy(db, yoq=True, sinf="11-A", odam_id=B)
`;

function qur() {
  const b = ikkiBaza(SEED);
  soatniQoy(new Date("2026-10-02T09:00:00Z"));
  b.sor = (yol, { user = { id: 111, username: "fsultonoov" }, post = false, tana } = {}) =>
    ma.ishla(new Request(`https://w.example${yol}`, {
      method: post ? "POST" : "GET",
      headers: { authorization: "tma " + imzola(user), ...(tana ? { "content-type": "application/json" } : {}) },
      body: tana ? JSON.stringify(tana) : undefined,
    }), {}, b.db);
  b.id = async (nom) => (await b.db.q1("SELECT id FROM odam WHERE nom=?", nom)).id;
  return b;
}
const jsonOl = async (r) => [r.status, await r.json()];

test("ruxsat: begona 403, noma'lum yo'l 404, POST/GET aralash 404", async () => {
  const b = qur();
  assert.equal((await b.sor("/app/api/profil", { user: { id: 999 } })).status, 403);
  assert.equal((await b.sor("/app/api/profil", { post: true, tana: {} })).status, 404);
  assert.equal((await b.sor("/app/api/profil/nom")).status, 404);
  assert.equal((await b.sor("/app/api/profil/boshqa", { post: true, tana: {} })).status, 404);
});

test("odam_rangi: desktop theme.odam_rangi bilan parity (iliq va oq)", async () => {
  const b = qur();
  const kut = pyJson(b.pyPapka, String.raw`
import json
from ui.eski import theme as t
r = {}
for rj in ("iliq", "oq"):
    t.rejim_qoy(rj)
    r[rj] = [t.odam_rangi(i) for i in range(0, 15)]
print(json.dumps(r))`);
  for (const rj of ["iliq", "oq"]) {
    assert.deepEqual([...Array(15).keys()].map((i) => pr.odam_rangi(i, rj)), kut[rj]);
  }
});

test("GET: a'zolar, bildirishnoma, ilova — Python bilan parity", async () => {
  const b = qur();
  const [s, j] = await jsonOl(await b.sor("/app/api/profil"));
  assert.equal(s, 200);
  const kut = pyJson(b.pyPapka, String.raw`
import json
from core import xabar as xb, vazifa as vz, plan, dars
import json
from ui.eski import theme as t
t.rejim_qoy("iliq")
print(json.dumps({
  "asosiy": plan.asosiy_odam(db),
  "rang": {r["id"]: t.odam_rangi(r["id"]) for r in db.q("SELECT id FROM odam")},
  "yoqmagan": [r["nom"] for r in xb.dm_yoqmaganlar(db)],
  "kech": xb.kechiktirish_variantlari(db),
  "soz": {k: v for k, v in xb.sozlamalar(db).items() if k != "token"},
  "ukun": vz.uborka_kuni(db), "uvaqt": vz.uborka_vaqti(db),
  "uishlar": [x["nom"] for x in vz.uborka_turlari(db)],
  "dars": dars.sozlamalar(db),
}))`);
  const F = await b.id("Fayzulloxon"), O = await b.id("Otabek"), B = await b.id("Behruz"), Q = await b.id("Qadimgi");
  assert.equal(j.men_id, F);
  assert.equal(j.tg_username, "fsultonoov");
  assert.deepEqual(j.azolar.map((a) => a.id), [F, O, B, Q]); // faollar tartib bo'yicha, nofaol oxirida
  for (const a of j.azolar) assert.equal(a.rang, kut.rang[a.id]);
  assert.deepEqual(j.azolar.map((a) => [a.dm, a.faol, a.asosiy, a.men]), [
    ["yoqilgan", true, false, true], ["start_kerak", true, true, false],
    ["yoqilgan", true, false, false], ["nom_yoq", false, false, false]]);
  assert.equal(kut.asosiy, O);

  const bn = j.bildirishnoma;
  assert.deepEqual(bn.dm_yoqmaganlar, kut.yoqmagan);
  assert.deepEqual(bn.kechiktirish, kut.kech);
  assert.equal(bn.yoqilgan, kut.soz.yoqilgan);
  assert.equal(bn.kunlik_vaqt, kut.soz.kunlik_vaqt);
  assert.equal(bn.guruh_nomi, "Farovon oila");
  assert.equal(bn.sozlangan, true);
  // Maxfiy qiymatlar javobga chiqmaydi.
  const matn = JSON.stringify(j);
  assert.ok(!matn.includes(TOKEN) && !matn.includes("-100500"));

  const il = j.ilova;
  assert.equal(il.versiya, pr.VERSIYA);
  assert.equal(il.uborka.kun, kut.ukun);
  assert.equal(il.uborka.kun_nomi, "Shanba");
  assert.equal(il.uborka.vaqt, kut.uvaqt);
  assert.deepEqual(il.uborka.ishlar, kut.uishlar);
  assert.equal(il.dars.yoq, kut.dars.yoq);
  assert.equal(il.dars.sinf, kut.dars.sinf);
  assert.equal(il.dars.odam, "Behruz");
  assert.ok(il.desktop_soni > 0 && il.desktop_oxirgi); // ekish = desktop (juft id)
  assert.equal(il.server_oxirgi, null);
  assert.equal(il.hozir, "2026-10-02 14:00:00");
});

test("uborka_kuni: buzilgan/chegaradan tashqari qiymat — Python bilan bir xil", async () => {
  for (const q of ["abc", "9", "-1", " 3 ", "", "4"]) {
    const b = ikkiBaza(`db.sozlama_qoy("uborka_kuni", ${JSON.stringify(q)})`);
    const kut = pyJson(b.pyPapka, `import json\nfrom core import vazifa as vz\nprint(json.dumps(vz.uborka_kuni(db)))`);
    assert.equal(await pr.uborka_kuni(b.db), kut, `qiymat ${JSON.stringify(q)}`);
  }
});

test("ism o'zgartirish: entries.odam_nomi_ozgartir bilan parity (xato matni, yozuv, tavsif)", async () => {
  const b = qur();
  const F = await b.id("Fayzulloxon");
  const pyXato = (nom) => pyJson(b.pyPapka, String.raw`
import json
from core import entries as en
try:
    en.odam_nomi_ozgartir(db, ${F}, ${JSON.stringify(nom)}); print(json.dumps(None))
except ValueError as e:
    print(json.dumps(str(e)))`);
  for (const nom of ["   ", "Otabek", "Qadimgi"]) {
    const [s, j] = await jsonOl(await b.sor("/app/api/profil/nom", { post: true, tana: { nom } }));
    assert.equal(s, 400);
    assert.equal(j.xato, pyXato(nom));
  }
  assert.equal((await b.sor("/app/api/profil/nom", { post: true, tana: { nom: "x".repeat(41) } })).status, 400);

  const [s, j] = await jsonOl(await b.sor("/app/api/profil/nom", { post: true, tana: { nom: "  Fayzulla  " } }));
  assert.equal(s, 200);
  assert.equal(j.nom, "Fayzulla");
  assert.equal(pyXato("  Fayzulla  "), null); // Python nusxasi ham shu holatga
  const js = await b.db.q1("SELECT nom FROM odam WHERE id=?", F);
  const pyR = pyJson(b.pyPapka, `import json\nprint(json.dumps(db.q1("SELECT nom FROM odam WHERE id=?", ${F})["nom"]))`);
  assert.equal(js.nom, pyR);
  const jr = await b.db.q("SELECT id, tavsif FROM ozgarishlar WHERE jadval='odam' AND id%2=1");
  assert.equal(jr.length, 1);
  const pyT = pyJson(b.pyPapka, `import json\nprint(json.dumps(db.q1("SELECT tavsif FROM ozgarishlar WHERE jadval='odam' ORDER BY id DESC")["tavsif"]))`);
  assert.equal(jr[0].tavsif, pyT);
  // O'zgargan ism bilan ham tanib oladi (tg_chat bo'yicha).
  const [, g] = await jsonOl(await b.sor("/app/api/profil"));
  assert.equal(g.azolar.find((a) => a.men).nom, "Fayzulla");
});

test("Telegram nomi: faqat initData'dagi username, desktop yozuvi bilan bir xil", async () => {
  const b = qur();
  const B = await b.id("Behruz");
  // username yo'q
  assert.equal((await b.sor("/app/api/profil/telegram", { post: true, user: { id: 333 } })).status, 400);
  // boshqa a'zoniki — rad
  const [s0, j0] = await jsonOl(await b.sor("/app/api/profil/telegram", { post: true, user: { id: 333, username: "OTABEK_33" } }));
  assert.equal(s0, 400);
  assert.match(j0.xato, /Otabek uchun/);
  // tana e'tiborga olinmaydi
  const [s, j] = await jsonOl(await b.sor("/app/api/profil/telegram", { post: true, user: { id: 333, username: "behruz_o" }, tana: { telegram: "boshqa" } }));
  assert.equal(s, 200);
  assert.equal(j.telegram, "behruz_o");
  assert.equal((await b.db.q1("SELECT telegram FROM odam WHERE id=?", B)).telegram, "behruz_o");
  const jr = await b.db.q("SELECT tavsif, keyin FROM ozgarishlar WHERE jadval='odam' AND id%2=1");
  assert.equal(jr.length, 1);
  assert.equal(jr[0].tavsif, "Telegram nomi o'zgardi");
  // Takror — yangi jurnal qatori yo'q.
  await b.sor("/app/api/profil/telegram", { post: true, user: { id: 333, username: "behruz_o" } });
  assert.equal((await b.db.q("SELECT 1 FROM ozgarishlar WHERE jadval='odam' AND id%2=1")).length, 1);
  // Python desktop yozuvi bilan bir xil natija.
  const pyR = pyJson(b.pyPapka, String.raw`
import json
with db.amal("Telegram nomi o'zgardi"):
    db.apply("odam", "UPDATE", {"telegram": "behruz_o"}, ${B})
r = db.q1("SELECT tavsif, keyin FROM ozgarishlar WHERE jadval='odam' ORDER BY id DESC")
print(json.dumps({"tavsif": r["tavsif"], "keyin": json.loads(r["keyin"])}))`);
  assert.equal(jr[0].tavsif, pyR.tavsif);
  assert.deepEqual(JSON.parse(jr[0].keyin), pyR.keyin);
});

test("sozlanmagan bot: bo'sh qiymatlar, xatosiz", async () => {
  const b = yangiBaza(String.raw`
from core import entries as en
F = en.odam_qosh(db, "Yolg'iz")
db.apply("odam", "UPDATE", {"tg_chat": 5}, F)
db.sozlama_qoy("tg_token", "123456:SINOV-token")
db.sozlama_qoy("uborka_kuni", "xato")`);
  const r = await ma.ishla(new Request("https://w.example/app/api/profil", {
    headers: { authorization: "tma " + imzola({ id: 5 }) } }), {}, b.db);
  const j = await r.json();
  assert.equal(r.status, 200);
  assert.equal(j.tg_username, null);
  assert.equal(j.bildirishnoma.sozlangan, false);
  assert.equal(j.bildirishnoma.guruh_nomi, null);
  assert.deepEqual(j.bildirishnoma.kechiktirish, [10, 30, 60]);
  assert.equal(j.ilova.uborka.kun, 6);
  assert.equal(j.ilova.dars.yoq, false);
  assert.equal(j.azolar[0].asosiy, true);
});
