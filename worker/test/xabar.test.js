// xabar.js ↔ core/xabar.py PARITY testlari.
import { test } from "node:test";
import assert from "node:assert/strict";
import { usta, nusxa, jsDb, pyIshla, muzlat, yozuvchi, norm, qatorlar, jurnal, jurnalNorm, maxOz } from "./_parity.js";
import * as xb from "../src/xabar.js";
import * as vz from "../src/vazifa.js";
import * as vaqt from "../src/vaqt.js";

const SEED = String.raw`
muzlat("2026-10-04 06:00:00")
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
for oid, t in ((F, "fsultonoov"), (O, "otabek_33"), (A, "NothingTrue1")):
    db.apply("odam", "UPDATE", {"telegram": t}, oid)
db.apply("odam", "UPDATE", {"tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"tg_chat": 333}, A)
xb.sozlama_qoy(db, token="sinov", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
ovq = vz.navbat_turi(db)
vz.navbat_biriktir(db, ovq["id"], F, "2026-10-03", "19:00", 4)
vz.uborka_biriktir(db, "2026-10-04", O, 1)
musor = vz.qosh(db, "Musorlarni tashlash", O, "2026-10-04", "09:00", 30)
vz.kechiktir(db, musor, 30, _dt.datetime(2026, 10, 4, 10, 0, 0))
dast = vz.qosh(db, "Dasturxon yozish, narsalarni qo'yish", A, "2026-10-04", "13:00", 15)
gaz = vz.qosh(db, "Gaz plitasini ovqatdan keyin yog'laridan artib tozalash", A, "2026-10-04", "20:30", 15)
vz.bajar(db, gaz)
boshqa = vz.qosh(db, "Kitob <javon> & stol", F, "2026-10-04", None, 30, "izohli")
kitob = vz.tur_qosh(db, "Kitob o'qish", 30, shaxsiy=True)
for i in range(1, 7):
    d = (_dt.date(2026, 10, 4) - _dt.timedelta(days=i)).isoformat()
    vz.bajar(db, vz.biriktir(db, kitob, F, d, "21:00"))
kit_bugun = vz.biriktir(db, kitob, F, "2026-10-04", "21:00")
st = vz.streak_qosh(db, F, kitob, 7, "2026-09-28")
kitob_o = vz.biriktir(db, kitob, O, "2026-10-04", "07:00")
mat = vz.tur_qosh(db, "Matematika", 80, shaxsiy=True)
dars_v = db.apply("vazifa", "INSERT", {"nom": "Matematika", "odam_id": A, "sana": "2026-10-04", "vaqt": "14:00",
    "davomiylik": 80, "holat": "ochiq", "izoh": "Karimov · 101", "manba": "dars:2026-10-04:1"})
vz.takror_qosh(db, "Bomdod namozi", A, "05:30", 20, bugun="2026-10-04")
peshin = vz.qosh(db, "Peshin namozi", A, "2026-10-04", "12:30", 20)
shom = vz.qosh(db, "Shom namozi", A, "2026-10-04", "05:00", 10)
vz.qazo_qil(db, shom)
oshpaz = db.q1("SELECT id FROM vazifa WHERE nom=? AND sana='2026-10-04'", ovq["nom"])["id"]
idish = db.q1("SELECT id FROM vazifa WHERE nom<>? AND sana='2026-10-04' AND vaqt='20:00'", ovq["nom"])["id"]
vz.menyu_qoy(db, oshpaz, "Chuchvara")
r1 = entries.rasxod_qosh(db, "2026-10-04", "Bozorlik", 110000, F)
r2 = entries.rasxod_qosh(db, "2026-10-04", "Poyabzal", 300000, F, kim_uchun=O)
r3 = entries.rasxod_qosh(db, "2026-10-04", "O'zimniki", 5000, O, umumiymi=False)
r4 = entries.rasxod_qosh(db, "2026-08-01", "Eski", 90000, F)
db.con.execute("UPDATE rasxod SET yaratilgan='2026-10-04 07:00:00' WHERE id IN (?,?,?)", (r1, r2, r3))
db.con.execute("UPDATE rasxod SET yaratilgan='2020-01-01 00:00:00' WHERE id=?", (r4,))
db.apply("yutuq", "INSERT", {"odam_id": O, "nom": vz.YUTUQ_IRODA, "izoh": "Sport — 7 kun ketma-ket",
    "sana": "2026-10-01", "nishon": 7})
olma = db.apply("item", "INSERT", {"nom": "Olma", "narx": 1000})
db.apply("item", "INSERT", {"nom": "Olma qizil", "narx": 1200})
db.apply("item", "INSERT", {"nom": "Nok 'Duchess'", "narx": 1500})
chiq({"F": F, "O": O, "A": A, "musor": musor, "dast": dast, "gaz": gaz, "kit_bugun": kit_bugun,
      "kitob_o": kitob_o, "dars": dars_v, "peshin": peshin, "shom": shom, "oshpaz": oshpaz,
      "idish": idish, "olma": olma, "boshqa": boshqa, "r1": r1})
`;
const U = usta(SEED);
const ID = U.id;

const js = (x) => JSON.parse(JSON.stringify(x));
const pyDt = (s) => `_dt.datetime.strptime("${s}", "%Y-%m-%d %H:%M:%S")`;

/** Python va JS kutilayotgan()ni bir xil vaqtda solishtiradi. */
async function kutPar(papkaPy, db, s, oldin = "") {
  const pr = pyIshla(papkaPy, `${oldin}\nmuzlat("${s}")\nchiq(xb.kutilayotgan(db, ${pyDt(s)}))`);
  muzlat(s);
  const jr = js(await xb.kutilayotgan(db, vaqt.vaqtDan(s)));
  assert.deepEqual(jr, pr, `kutilayotgan @ ${s}`);
  return jr;
}

test("kutilayotgan: kun davomida har xil vaqtlarda — Python bilan bir xil", async () => {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const db = jsDb(jp);
  const turlar = {};
  for (const s of ["2026-10-04 07:00:00", "2026-10-04 07:59:00", "2026-10-04 08:00:00", "2026-10-04 09:35:00",
    "2026-10-04 10:31:00", "2026-10-04 12:00:00", "2026-10-04 13:59:00", "2026-10-04 15:29:00",
    "2026-10-04 15:30:00", "2026-10-04 20:05:00", "2026-10-04 23:59:00", "2026-10-05 08:30:00",
    "2026-10-03 21:00:00"]) {
    const r = await kutPar(pp, db, s);
    turlar[s] = [...new Set(r.map((x) => x.turi))].sort();
  }
  // Ssenariy haqiqatan hamma turni qamraganini tekshiramiz
  const hammasi = new Set(Object.values(turlar).flat());
  for (const t of ["kunlik", "shaxsiy", "eslatma", "dars", "rasxod", "yutuq"]) assert.ok(hammasi.has(t), t);
  assert.ok(!turlar["2026-10-04 07:59:00"].includes("kunlik"));
  assert.ok(turlar["2026-10-04 12:00:00"].includes("dars"));
});

test("kutilayotgan: kechiktirish kaliti, belgilangandan keyin qolgani", async () => {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const db = jsDb(jp);
  const r = await kutPar(pp, db, "2026-10-04 10:31:00");
  const m = r.find((x) => x.vazifa_id === ID.musor);
  assert.equal(m.kalit, `vazifa:${ID.musor}:2026-10-04 10:30:00`);
  // Bir qismini belgilaymiz (ikkala tomonda), qolgani bir xil chiqsin
  const kal = r.filter((_, i) => i % 2 === 0).map((x) => x.kalit);
  const pyBel = kal.map((k) => `xb.belgila(db, ${JSON.stringify(k)}, 5)`).join("\n");
  for (const k of kal) await xb.belgila(db, k, 5);
  await kutPar(pp, db, "2026-10-04 20:05:00", pyBel);
});

test("yubor_kutilayotgan: Telegram chaqiruvlari va yuborilgan izlari bir xil", async () => {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const db = jsDb(jp);
  const pr = pyIshla(pp, `muzlat("2026-10-04 20:05:00")\nn = xb.yubor_kutilayotgan(db, ${pyDt("2026-10-04 20:05:00")})\nchiq([CALLS, n])`);
  const calls = yozuvchi();
  muzlat("2026-10-04 20:05:00");
  const n = js(await xb.yubor_kutilayotgan(db, vaqt.vaqtDan("2026-10-04 20:05:00")));
  assert.deepEqual(norm(calls), norm(pr[0]));
  assert.deepEqual(n, pr[1]);
  const sql = "SELECT kalit, xabar_id FROM yuborilgan ORDER BY kalit";
  assert.deepEqual(qatorlar(jp, sql, []), qatorlar(pp, sql, []));
  assert.ok(calls.length > 5);
  // JS `vaqt` ustunini Toshkent vaqti bilan yozadi (D1'da localtime = UTC)
  assert.deepEqual([...new Set(qatorlar(jp, "SELECT vaqt FROM yuborilgan", []).map((r) => r.vaqt))], ["2026-10-04 20:05:00"]);
  // ikkinchi marta — hech narsa
  const c2 = yozuvchi();
  assert.deepEqual(await xb.yubor_kutilayotgan(db, vaqt.vaqtDan("2026-10-04 20:05:00")), []);
  assert.equal(c2.length, 0);
});

test("yubor_kutilayotgan: o'chirilgan bot hech narsa yubormaydi", async () => {
  const db = jsDb(nusxa(U.papka));
  await db.sozlama_qoy(xb.K_YOQILGAN, "0");
  const c = yozuvchi();
  assert.deepEqual(await xb.yubor_kutilayotgan(db, vaqt.vaqtDan("2026-10-04 20:05:00")), []);
  assert.equal(c.length, 0);
  assert.equal(await xb.sozlangami(db), false);
});

test("matn quruvchilar Python bilan bir xil", async () => {
  const p = nusxa(U.papka);
  const pr = pyIshla(p, String.raw`
muzlat("2026-10-04 12:00:00")
kun = vz.kun(db, "2026-10-04")
chiq({
 "bosh": [xb.kunlik_bosh_matn(db, d) for d in ("2026-10-03", "2026-10-04", "2026-10-05", "2026-10-07", "2026-11-30")],
 "bloklar": xb.kunlik_bloklar(db, "2026-10-04"),
 "odam": [xb.kunlik_odam_matn(db, "2026-10-04", o) for o in (${ID.F}, ${ID.O}, ${ID.A})],
 "blok": [xb._bitta_blok(db, v, xb._teg("Ism", None)) for v in kun],
 "rol": [xb._rol(db, v) for v in kun],
 "belgi": [xb._ish_belgi(v) for v in kun],
 "eslatma": [xb.eslatma_matn(db, v) for v in kun],
 "dars": xb.dars_ogoh_matn(db, vz.bitta(db, ${ID.dars})),
 "shaxsiy": [xb.shaxsiy_matn(db, "2026-10-04", o) for o in (${ID.F}, ${ID.O}, ${ID.A})],
 "shaxsiy_bloklar": xb.shaxsiy_bloklar(db, "2026-10-04"),
 "shaxsiy_klav": [xb.shaxsiy_klaviatura(db, "2026-10-04", o) for o in (${ID.F}, ${ID.O}, ${ID.A})],
 "kunlik_klav": [xb.kunlik_klaviatura(db, d) for d in ("2026-10-04", "2026-10-09")],
 "taom_klav": xb._taom_klaviatura(db, ${ID.oshpaz}),
 "rasxod": [xb.rasxod_matn(db, r[0]) for r in db.q("SELECT id FROM rasxod ORDER BY id")] + [xb.rasxod_matn(db, 99999)],
 "yutuq": [xb.yutuq_matn(db, y) for y in vz.yutuqlar(db)],
 "kech_klav": xb.kechiktirish_klaviatura(db, 5),
 "kech_var": xb.kechiktirish_variantlari(db),
 "teg": [xb._teg("Ali", None), xb._teg("Ali", "ali_1")],
 "soz": xb.sozlamalar(db), "sozlangami": xb.sozlangami(db),
 "chat": [xb.odam_chati(db, o) for o in (${ID.F}, ${ID.O}, 9999)],
})`);
  const db = jsDb(p);
  muzlat("2026-10-04 12:00:00");
  const kun = await vz.kun(db, "2026-10-04");
  const m = async (arr, f) => { const r = []; for (const x of arr) r.push(await f(x)); return r; };
  const jr = {
    bosh: await m(["2026-10-03", "2026-10-04", "2026-10-05", "2026-10-07", "2026-11-30"], (d) => xb.kunlik_bosh_matn(db, d)),
    bloklar: await xb.kunlik_bloklar(db, "2026-10-04"),
    odam: await m([ID.F, ID.O, ID.A], (o) => xb.kunlik_odam_matn(db, "2026-10-04", o)),
    blok: await m(kun, (v) => xb._bitta_blok(db, v, xb._teg("Ism", null))),
    rol: await m(kun, (v) => xb._rol(db, v)),
    belgi: kun.map(xb._ish_belgi),
    eslatma: await m(kun, (v) => xb.eslatma_matn(db, v)),
    dars: await xb.dars_ogoh_matn(db, await vz.bitta(db, ID.dars)),
    shaxsiy: await m([ID.F, ID.O, ID.A], (o) => xb.shaxsiy_matn(db, "2026-10-04", o)),
    shaxsiy_bloklar: await xb.shaxsiy_bloklar(db, "2026-10-04"),
    shaxsiy_klav: await m([ID.F, ID.O, ID.A], (o) => xb.shaxsiy_klaviatura(db, "2026-10-04", o)),
    kunlik_klav: await m(["2026-10-04", "2026-10-09"], (d) => xb.kunlik_klaviatura(db, d)),
    taom_klav: await xb._taom_klaviatura(db, ID.oshpaz),
    rasxod: [...await m((await db.q("SELECT id FROM rasxod ORDER BY id")).map((r) => r.id), (id) => xb.rasxod_matn(db, id)),
      await xb.rasxod_matn(db, 99999)],
    yutuq: await m(await vz.yutuqlar(db), (y) => xb.yutuq_matn(db, y)),
    kech_klav: await xb.kechiktirish_klaviatura(db, 5),
    kech_var: await xb.kechiktirish_variantlari(db),
    teg: [xb._teg("Ali", null), xb._teg("Ali", "ali_1")],
    soz: await xb.sozlamalar(db), sozlangami: await xb.sozlangami(db),
    chat: await m([ID.F, ID.O, 9999], (o) => xb.odam_chati(db, o)),
  };
  assert.deepEqual(js(jr), pr);
});

test("kechiktirish_variantlari: sozlama qiymatlari", async () => {
  for (const q of ["15,45,120", " 5 , 90 ", "1,2,3,4,5,6", "0,10", "abc", "1.5,2", ",,", "-3"]) {
    const p = nusxa(U.papka);
    const pr = pyIshla(p, `db.sozlama_qoy(xb.K_KECHIKTIRISH, ${JSON.stringify(q)})\nchiq([xb.kechiktirish_variantlari(db), xb.kechiktirish_klaviatura(db, 7)])`);
    const db = jsDb(p);
    assert.deepEqual(js([await xb.kechiktirish_variantlari(db), await xb.kechiktirish_klaviatura(db, 7)]), pr, q);
  }
});

// ═════════════════════════════════════════════════ tugmalar

const VZ_SQL = "SELECT nom, odam_id, sana, vaqt, davomiylik, holat, bajarilgan, izoh, kechiktirildi, manba," +
  " ochirilgan, menyu FROM vazifa ORDER BY sana, nom, odam_id, COALESCE(vaqt,''), manba";
const YT_SQL = "SELECT odam_id, nom, izoh, sana, streak_id, nishon, ochirilgan FROM yutuq ORDER BY odam_id, sana, nishon";

const bosish = (data, kim = "fsultonoov", chat = -1) =>
  ({ id: "cb1", data, from: { username: kim }, message: { message_id: 777, chat: { id: chat } } });

/** Bitta tugmani ikkala tomonda bosadi; chaqiruvlar, qatorlar va jurnal teng. */
async function tugmaPar(data, kim, s = "2026-10-04 21:15:00", oldin = "") {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const oz = maxOz(pp);
  const cb = bosish(data, kim);
  const pr = pyIshla(pp, `${oldin}\nmuzlat("${s}")\nxb.tugmani_ishla(db, ${JSON.stringify(cb)}, "sinov", "-1")\nchiq(CALLS)`);
  const db = jsDb(jp);
  if (oldin.includes("K_KECHIKTIRISH")) await db.sozlama_qoy(xb.K_KECHIKTIRISH, "15,45,120");
  const calls = yozuvchi();
  muzlat(s);
  await xb.tugmani_ishla(db, cb, "sinov", "-1");
  assert.deepEqual(norm(calls), norm(pr), `${data} chaqiruvlar`);
  assert.deepEqual(qatorlar(jp, VZ_SQL), qatorlar(pp, VZ_SQL), `${data} vazifa`);
  assert.deepEqual(qatorlar(jp, YT_SQL), qatorlar(pp, YT_SQL), `${data} yutuq`);
  assert.deepEqual(jurnalNorm(jurnal(jp, oz)), jurnalNorm(jurnal(pp, oz)), `${data} jurnal`);
  return { calls, pp, jp, db };
}

test("tugma menyu: — taomlar ro'yxati", async () => {
  // 10-04 oshpazi navbat bo'yicha Otabek
  const { calls } = await tugmaPar(`menyu:${ID.oshpaz}`, "otabek_33");
  assert.equal(calls.length, 1);
  const b = await tugmaPar(`menyu:${ID.oshpaz}`, "fsultonoov"); // begona — hech narsa
  assert.equal(b.calls.length, 0);
});

test("tugma taom: — vazifa.menyu yoziladi, xabar tahrirlanadi", async () => {
  const mid = qatorlar(U.papka, "SELECT id FROM menyu WHERE nom='Mastava'", [])[0];
  const id = (await jsDb(nusxa(U.papka)).q1("SELECT id FROM menyu WHERE nom='Mastava'")).id;
  assert.ok(mid);
  await tugmaPar(`taom:${ID.oshpaz}:${id}`, "OTABEK_33");
  await tugmaPar(`taom:${ID.oshpaz}:${id}`, "NothingTrue1");
  await tugmaPar(`taom:${ID.oshpaz}:99999`, "otabek_33");
});

test("tugma bajar: — streak 7 kun → yutuq, keyin e'lon ham bir xil", async () => {
  const { calls, pp, db } = await tugmaPar(`bajar:${ID.kit_bugun}`, "fsultonoov");
  assert.equal(calls[0][0], "editMessageText");
  const y = await db.q("SELECT * FROM yutuq WHERE streak_id IS NOT NULL");
  assert.equal(y.length, 1);
  // Yangi yutuq id'lari tomonlarda farq qiladi (juft/toq) — matn bo'yicha solishtiramiz
  const pr = pyIshla(pp, `chiq([[x["turi"], x["matn"]] for x in xb.kutilayotgan(db, ${pyDt("2026-10-04 21:40:00")})])`);
  const jr = (await xb.kutilayotgan(db, vaqt.vaqtDan("2026-10-04 21:40:00"))).map((x) => [x.turi, x.matn]);
  assert.deepEqual(jr, pr);
  assert.ok(jr.some(([t, m]) => t === "yutuq" && m.includes("Kitob o'qish — 7 kun ketma-ket")));
});

test("tugma bajar: — oddiy, idish, qazo bo'lgan namoz, begona, yo'q vazifa", async () => {
  await tugmaPar(`bajar:${ID.idish}`, "fsultonoov");
  await tugmaPar(`bajar:${ID.musor}`, "otabek_33");
  await tugmaPar(`bajar:${ID.shom}`, "nothingtrue1");
  await tugmaPar(`bajar:${ID.dars}`, "NothingTrue1");
  await tugmaPar(`bajar:${ID.musor}`, "fsultonoov");
  await tugmaPar("bajar:999999", "fsultonoov");
  await tugmaPar(`bajar:${ID.musor}:1`, "otabek_33"); // noto'g'ri shakl — e'tiborsiz
});

test("tugma qazo: — namoz qazo, qazo ishi yoziladi", async () => {
  await tugmaPar(`qazo:${ID.peshin}`, "NothingTrue1", "2026-10-04 13:00:00");
  await tugmaPar(`qazo:${ID.musor}`, "otabek_33"); // namoz emas
  await tugmaPar(`qazo:${ID.shom}`, "NothingTrue1"); // allaqachon qazo
  await tugmaPar(`qazo:${ID.peshin}`, "otabek_33"); // begona
});

test("tugma haliyoq: / kech: — kechiktirish", async () => {
  await tugmaPar(`haliyoq:${ID.musor}`, "otabek_33");
  await tugmaPar(`haliyoq:${ID.musor}`, "otabek_33", "2026-10-04 09:40:00", `db.sozlama_qoy(xb.K_KECHIKTIRISH, "15,45,120")`);
  const { jp } = await tugmaPar(`kech:${ID.musor}:30`, "otabek_33", "2026-10-04 09:40:00");
  assert.equal(qatorlar(jp, "SELECT kechiktirildi FROM vazifa WHERE id=?", [], ID.musor)[0].kechiktirildi, "2026-10-04 10:10:00");
  await tugmaPar(`kech:${ID.musor}:120`, "fsultonoov");
});

test("tugma: noto'g'ri raqam — ikkala tomon ham yiqiladi", async () => {
  const db = jsDb(nusxa(U.papka));
  yozuvchi();
  await assert.rejects(() => xb.tugmani_ishla(db, bosish("bajar:abc"), "sinov", "-1"));
  const pr = pyIshla(nusxa(U.papka), String.raw`
try:
    xb.tugmani_ishla(db, {"data": "bajar:abc", "from": {}, "message": {}}, "sinov", "-1")
    chiq("ok")
except ValueError:
    chiq("ValueError")`);
  assert.equal(pr, "ValueError");
});

// ═════════════════════════════════════════════════ dispatcher

/** Update'ni ikkala tomonda ishlaydi. Python: `_bittasini_ishla(db, u, s, tg_rasxod)`. */
async function updPar(u, { s = "2026-10-04 21:15:00", javobBor = false } = {}) {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const pr = pyIshla(pp, String.raw`
from core import tg_rasxod
muzlat("${s}")
r = xb._bittasini_ishla(db, json.loads(${JSON.stringify(JSON.stringify(u))}), xb.sozlamalar(db), tg_rasxod)
chiq([r, CALLS])`);
  const db = jsDb(jp);
  await db.exec("CREATE TABLE IF NOT EXISTS rasm(nom TEXT PRIMARY KEY, data BLOB)");
  const calls = yozuvchi();
  muzlat(s);
  const r = await xb.bittasini_ishla(db, "sinov", u);
  let jc = norm(calls);
  if (javobBor) {
    // Tuzatish: tugma bosilganda answerCallbackQuery — Python'da yo'q edi.
    const oxir = jc[jc.length - 1];
    assert.deepEqual(oxir, ["answerCallbackQuery", { callback_query_id: u.callback_query.id }]);
    jc = jc.slice(0, -1);
  }
  assert.deepEqual(r, pr[0]);
  assert.deepEqual(jc, norm(pr[1]));
  for (const sql of [VZ_SQL, YT_SQL, "SELECT id, nom, telegram, tg_chat FROM odam ORDER BY id",
    "SELECT id, nom, rasm FROM item ORDER BY id"]) {
    assert.deepEqual(qatorlar(jp, sql, []), qatorlar(pp, sql, []), sql);
  }
  return { r, calls, db, jp };
}

test("dispatcher: guruhdagi tugma → tugmani_ishla + answerCallbackQuery", async () => {
  await updPar({ update_id: 1, callback_query: bosish(`bajar:${ID.kit_bugun}`) }, { javobBor: true });
  await updPar({ update_id: 2, callback_query: bosish(`menyu:${ID.oshpaz}`, "otabek_33") }, { javobBor: true });
  // xato bersa ham javob beriladi
  const db = jsDb(nusxa(U.papka));
  const c = yozuvchi();
  await assert.rejects(() => xb.bittasini_ishla(db, "sinov", { update_id: 3, callback_query: { id: "z9", data: "kech:x:y", from: {}, message: {} } }));
  assert.deepEqual(c, [["answerCallbackQuery", { callback_query_id: "z9" }]]);
});

test("dispatcher: begonaning rx: tugmasi — faqat javob", async () => {
  const db = jsDb(nusxa(U.papka));
  const c = yozuvchi();
  const r = await xb.bittasini_ishla(db, "sinov",
    { update_id: 4, callback_query: { id: "q1", data: "rx:k:1", from: { username: "begona" }, message: { message_id: 5, chat: { id: 42, type: "private" } } } });
  assert.deepEqual(r, []);
  assert.deepEqual(c, [["answerCallbackQuery", { callback_query_id: "q1" }]]);
});

test("dispatcher: /start — chat bog'lanadi (shaxsiy, uy a'zosi)", async () => {
  const { r } = await updPar({ update_id: 5, message: { message_id: 9, text: "/start", chat: { id: 222, type: "private" }, from: { username: "Otabek_33" } } });
  assert.equal(r[0], `chat bog'landi: odam#${ID.O}`);
});

test("dispatcher: guruh xabari va begona — hech narsa", async () => {
  const a = await updPar({ update_id: 6, message: { message_id: 9, text: "salom", chat: { id: -1, type: "group" }, from: { username: "otabek_33" } } });
  assert.deepEqual(a.r, []); assert.equal(a.calls.length, 0);
  const b = await updPar({ update_id: 7, message: { message_id: 9, text: "salom", chat: { id: 77, type: "private" }, from: { username: "begona" } } });
  assert.deepEqual(b.r, []); assert.equal(b.calls.length, 0);
  await updPar({ update_id: 8, edited_message: { text: "x" } });
});

const rasm = (caption, kim = "fsultonoov", extra = {}) => ({
  update_id: 10, message: {
    message_id: 11, chat: { id: 111, type: "private" }, from: { username: kim },
    photo: [{ file_id: "kichik", width: 90, height: 90 }, { file_id: "orta", width: 800, height: 1280 },
      { file_id: "katta", width: 2560, height: 1920 }],
    ...(caption != null ? { caption } : {}), ...extra,
  },
});

test("dispatcher: rasm — izohsiz / topilmadi / o'xshashlar / saqlandi / begona", async () => {
  assert.deepEqual((await updPar(rasm(null))).r, ["rasm: izohsiz"]);
  const t = await updPar(rasm("Olm"));
  assert.deepEqual(t.r, ["rasm: topilmadi (Olm)"]);
  await updPar(rasm("Nok \"<x>\" 'y'"));
  await updPar(rasm("Nok 'Duchess' zo'r"));
  const ok = await updPar(rasm("  olma "));
  assert.deepEqual(ok.r, ["rasm: Olma"]);
  assert.equal(ok.calls[0][1].file_id, "orta");
  const f = qatorlar(ok.jp, "SELECT rasm FROM item WHERE id=?", [], ID.olma)[0].rasm;
  assert.match(f, new RegExp(`^${ID.olma}-[0-9a-f]{16}\\.jpg$`));
  assert.equal(qatorlar(ok.jp, "SELECT COUNT(*) n FROM rasm WHERE nom=?", [], f)[0].n, 1);
  assert.deepEqual((await updPar(rasm("Olma", "begona"))).r, []);
  // hujjat sifatida yuborilgan rasm
  const doc = await updPar({ update_id: 12, message: { message_id: 13, chat: { id: 111, type: "private" },
    from: { username: "fsultonoov" }, caption: "Olma", document: { file_id: "doc1", mime_type: "image/png" } } });
  assert.deepEqual(doc.r, ["rasm: Olma"]);
});

test("_rasm_fayl_id", () => {
  assert.equal(xb._rasm_fayl_id({ photo: [{ file_id: "a", width: 2000, height: 2000 }] }), "a");
  assert.equal(xb._rasm_fayl_id({ document: { file_id: "d", mime_type: "application/pdf" } }), null);
  assert.equal(xb._rasm_fayl_id({}), null);
});

test("_chatni_eslab_qol: Python bilan bir xil", async () => {
  const holatlar = [
    { message: { chat: { id: 501, type: "private" }, from: { username: "OTABEK_33" } } },
    { message: { chat: { id: 502, type: "private" }, from: { username: "fsultonoov" } } }, // allaqachon bog'langan
    { message: { chat: { id: 503, type: "group" }, from: { username: "otabek_33" } } },
    { message: { chat: { id: 504, type: "private" }, from: {} } },
    { message: { chat: { id: 505, type: "private" }, from: { username: "begona" } } },
    { callback_query: {} },
  ];
  for (const u of holatlar) {
    const pp = nusxa(U.papka), jp = nusxa(U.papka);
    const oz = maxOz(pp);
    const pr = pyIshla(pp, `chiq(xb._chatni_eslab_qol(db, json.loads(${JSON.stringify(JSON.stringify(u))})))`);
    const db = jsDb(jp);
    assert.equal(await xb._chatni_eslab_qol(db, u), pr);
    const sql = "SELECT id, tg_chat FROM odam ORDER BY id";
    assert.deepEqual(qatorlar(jp, sql, []), qatorlar(pp, sql, []));
    assert.deepEqual(jurnalNorm(jurnal(jp, oz)), jurnalNorm(jurnal(pp, oz)));
  }
});

// ═════════════════════════════════════════════════ tuzatilgan xatolar (faqat JS)

test("TUZATISH: 30 kundan eski rasxod/yutuq qayta e'lon qilinmaydi", async () => {
  const db = jsDb(nusxa(U.papka));
  // tg_rasxod_dan juda eski — Python bu rasxodni (va yutuqni) e'lon qilardi
  await db.sozlama_qoy(xb.K_RASXOD_DAN, "2020-01-01 00:00:00");
  await db.exec("UPDATE rasxod SET yaratilgan='2026-08-20 10:00:00' WHERE id=?", ID.r1);
  await db.apply("yutuq", "INSERT", { odam_id: ID.A, nom: vz.YUTUQ_IRODA, izoh: "Eski", sana: "2026-08-01", nishon: 7 });
  const r = await xb.kutilayotgan(db, vaqt.vaqtDan("2026-10-04 12:00:00"));
  const rasxodlar = r.filter((x) => x.turi === "rasxod").map((x) => x.kalit);
  assert.ok(!rasxodlar.includes(`rasxod:${ID.r1}`));
  assert.ok(rasxodlar.length >= 1); // 2026-10-04 dagilari bor
  assert.ok(!r.some((x) => x.turi === "yutuq" && x.matn.includes("Eski")));
  assert.ok(r.some((x) => x.turi === "yutuq" && x.matn.includes("Sport")));
});

test("eski_izlarni_tozala: 60 kundan eski izlar o'chadi (Toshkent vaqti)", async () => {
  const db = jsDb(nusxa(U.papka));
  await db.exec("INSERT INTO yuborilgan(kalit, vaqt) VALUES('eski','2026-08-05 11:59:00'),('yangi','2026-08-05 12:01:00')");
  muzlat("2026-10-04 12:00:00");
  await xb.eski_izlarni_tozala(db);
  assert.deepEqual((await db.q("SELECT kalit FROM yuborilgan WHERE kalit IN ('eski','yangi')")).map((r) => r.kalit), ["yangi"]);
});
