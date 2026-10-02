// vazifa.js ↔ core/vazifa.py PARITY testlari.
import { test } from "node:test";
import assert from "node:assert/strict";
import { usta, nusxa, jsDb, pyIshla, muzlat, qatorlar, jurnal, jurnalNorm, maxOz } from "./_parity.js";
import * as vz from "../src/vazifa.js";

const BUGUN = "2026-10-04"; // yakshanba

const SEED = String.raw`
muzlat("2026-10-04 06:00:00")
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
kitob = vz.tur_qosh(db, "Kitob o'qish", 30, shaxsiy=True)
for i in range(1, 7):
    d = (_dt.date(2026, 10, 4) - _dt.timedelta(days=i)).isoformat()
    v = vz.biriktir(db, kitob, F, d, "21:00")
    vz.bajar(db, v)
kit_bugun = vz.biriktir(db, kitob, F, "2026-10-04", "21:00")
st = vz.streak_qosh(db, F, kitob, 7, "2026-09-28")
dori = vz.tur_qosh(db, "Dori ichish", 5, shaxsiy=True)
st2 = vz.streak_qosh(db, O, dori, 14, "2026-10-01")
dori_v = vz.biriktir(db, dori, O, "2026-10-04", "08:00")
peshin = vz.qosh(db, "Peshin namozi", A, "2026-10-04", "12:30", 20)
shom = vz.qosh(db, "Shom namozi", A, "2026-10-03", "18:00", 20)
vz.qazo_qil(db, shom)
kelajak = vz.qosh(db, "Xufton namozi", A, "2026-10-06", "20:00", 20)
musor = vz.qosh(db, "Musorlarni tashlash", O, "2026-10-04", "09:00", 30)
ovq = vz.navbat_turi(db)
vz.navbat_biriktir(db, ovq["id"], F, "2026-10-04", "19:00", 3)
vz.uborka_biriktir(db, "2026-10-04", O, 1)
chiq({"F": F, "O": O, "A": A, "kitob": kitob, "kit_bugun": kit_bugun,
      "dori": dori, "dori_v": dori_v, "peshin": peshin, "shom": shom,
      "kelajak": kelajak, "musor": musor, "ovq": ovq["id"], "st": st, "st2": st2})
`;

const U = usta(SEED);
const ID = U.id;

const VAZIFA_SQL = "SELECT nom, odam_id, sana, vaqt, davomiylik, holat, bajarilgan, izoh, kechiktirildi," +
  " manba, ochirilgan, menyu FROM vazifa ORDER BY sana, nom, odam_id, COALESCE(vaqt,''), manba";
const YUTUQ_SQL = "SELECT odam_id, nom, izoh, sana, streak_id, nishon, ochirilgan FROM yutuq ORDER BY odam_id, streak_id, nishon";

/** Bir xil amalni ikkala tomonda bajarib, natija/qatorlar/jurnalni solishtiradi. */
async function ikkala(pyKod, jsFn, { sql = [VAZIFA_SQL, YUTUQ_SQL] } = {}) {
  const pp = nusxa(U.papka), jp = nusxa(U.papka);
  const oz = maxOz(pp);
  const pr = pyIshla(pp, pyKod);
  const db = jsDb(jp);
  const jr = await jsFn(db);
  for (const s of sql) assert.deepEqual(qatorlar(jp, s), qatorlar(pp, s), s);
  assert.deepEqual(jurnalNorm(jurnal(jp, oz)), jurnalNorm(jurnal(pp, oz)), "ozgarishlar");
  return { pr, jr, pp, jp, db };
}

const json = (x) => JSON.parse(JSON.stringify(x));

test("o'qish funksiyalari Python bilan bir xil", async () => {
  const p = nusxa(U.papka);
  muzlat("2026-10-04 10:00:00");
  const pr = pyIshla(p, String.raw`
muzlat("2026-10-04 10:00:00")
D = lambda rs: [dict(r) for r in rs]
chiq({
 "kun": D(vz.kun(db, "2026-10-04")),
 "kunF": D(vz.kun(db, "2026-10-04", ${ID.F})),
 "oraliq": D(vz.oraliq(db, "2026-10-03", "2026-10-06", None, True)),
 "oraliqO": D(vz.oraliq(db, "2026-10-01", "2026-10-06", ${ID.O}, False)),
 "bitta": dict(vz.bitta(db, ${ID.musor})),
 "yoq": vz.bitta(db, 999999),
 "shaxsiy_turlari": D(vz.shaxsiy_turlari(db)),
 "shaxsiy_nomlari": sorted(vz.shaxsiy_nomlari(db)),
 "tur_bitta": dict(vz.tur_bitta(db, ${ID.kitob})),
 "tur_ergash": dict(vz.tur_ergash(db, ${ID.ovq})),
 "tur_ergash_yoq": vz.tur_ergash(db, ${ID.kitob}),
 "navbat_turi": dict(vz.navbat_turi(db)),
 "uborka_turlari": D(vz.uborka_turlari(db)),
 "qadamlar": D(vz.qadamlar(db, vz.uborka_turlari(db)[0]["id"])),
 "qadam_nomlari": vz.qadam_nomlari(db, vz.uborka_turlari(db)[1]["id"]),
 "yutuqlar": D(vz.yutuqlar(db)),
 "streaklar": D(vz.streaklar(db)),
 "holat": [vz.streak_holati(db, s) for s in vz.streaklar(db)],
 "holat_ertaga": [vz.streak_holati(db, s, "2026-10-05") for s in vz.streaklar(db, ${ID.F})],
 "kunlari": vz.streak_kunlari(db, ${ID.F}, ${ID.kitob}),
 "bormi": vz.yutuq_bormi(db, ${ID.F}, ${ID.st}, 7),
 "qazo_ishlari": D(vz.qazo_ishlari(db, ${ID.shom})),
 "qazo_ochiq": D(vz.qazo_ishlari(db, ${ID.shom}, True)),
 "yopiq": [vz.yopiqmi(r) for r in vz.kun(db, "2026-10-04")],
 "kech": [vz.kechiktirilganmi(r) for r in vz.kun(db, "2026-10-04")],
})`);
  const db = jsDb(p);
  const ub = await vz.uborka_turlari(db);
  const st = await vz.streaklar(db);
  const kun = await vz.kun(db, BUGUN);
  const jr = {
    kun, kunF: await vz.kun(db, BUGUN, ID.F),
    oraliq: await vz.oraliq(db, "2026-10-03", "2026-10-06", null, true),
    oraliqO: await vz.oraliq(db, "2026-10-01", "2026-10-06", ID.O, false),
    bitta: await vz.bitta(db, ID.musor), yoq: await vz.bitta(db, 999999),
    shaxsiy_turlari: await vz.shaxsiy_turlari(db),
    shaxsiy_nomlari: [...await vz.shaxsiy_nomlari(db)].sort(),
    tur_bitta: await vz.tur_bitta(db, ID.kitob),
    tur_ergash: await vz.tur_ergash(db, ID.ovq), tur_ergash_yoq: await vz.tur_ergash(db, ID.kitob),
    navbat_turi: await vz.navbat_turi(db), uborka_turlari: ub,
    qadamlar: await vz.qadamlar(db, ub[0].id), qadam_nomlari: await vz.qadam_nomlari(db, ub[1].id),
    yutuqlar: await vz.yutuqlar(db), streaklar: st,
    holat: await Promise.all(st.map((s) => vz.streak_holati(db, s))),
    holat_ertaga: await Promise.all((await vz.streaklar(db, ID.F)).map((s) => vz.streak_holati(db, s, "2026-10-05"))),
    kunlari: await vz.streak_kunlari(db, ID.F, ID.kitob),
    bormi: await vz.yutuq_bormi(db, ID.F, ID.st, 7),
    qazo_ishlari: await vz.qazo_ishlari(db, ID.shom), qazo_ochiq: await vz.qazo_ishlari(db, ID.shom, true),
    yopiq: kun.map(vz.yopiqmi), kech: kun.map((r) => vz.kechiktirilganmi(r)),
  };
  assert.deepEqual(json(jr), pr);
});

test("namozmi / qazo_ishimi / qazo_nomi", () => {
  const nomlar = ["Bomdod namozi", "Peshin", "ASR", "Xufton o'qish", "Namoz", "nomoz", "namaz",
    "Kitob o'qish", "Shomil bilan", "Asrlar", "Ovqat qilish", "", "o'qish namozni"];
  const p = nusxa(U.papka);
  const pr = pyIshla(p, `chiq([[vz.namozmi({"nom": n, "manba": None}), vz.namozmi({"nom": n, "manba": "qazo:1"}),` +
    ` vz.qazo_nomi(n)] for n in ${JSON.stringify(nomlar)}])`);
  const jr = nomlar.map((n) => [vz.namozmi({ nom: n, manba: null }), vz.namozmi({ nom: n, manba: "qazo:1" }), vz.qazo_nomi(n)]);
  assert.deepEqual(jr, pr);
  assert.equal(vz.qazo_ishimi(null), false);
  assert.equal(vz.qazo_ishimi({ manba: "qazo:5" }), true);
});

test("bajar: streak nishoniga yetganda yutuq SHU amalda beriladi", async () => {
  const { pr, jr, jp } = await ikkala(
    `muzlat("2026-10-04 21:15:00")\nvz.bajar(db, ${ID.kit_bugun})\nchiq(vz.streak_kunlari(db, ${ID.F}, ${ID.kitob}))`,
    async (db) => { muzlat("2026-10-04 21:15:00"); await vz.bajar(db, ID.kit_bugun); return vz.streak_kunlari(db, ID.F, ID.kitob); });
  assert.equal(jr, pr);
  assert.equal(jr, 7);
  const y = qatorlar(jp, YUTUQ_SQL);
  assert.equal(y.length, 1);
  assert.equal(y[0].izoh, "Kitob o'qish — 7 kun ketma-ket");
  // vazifa UPDATE va yutuq INSERT — bitta guruh (bitta undo)
  const g = jurnalNorm(jurnal(jp, maxOz(U.papka)));
  assert.equal(g.length, 1);
  assert.deepEqual(g[0].map((x) => x[0]), ["vazifa", "yutuq"]);
});

test("bajar: ikkinchi marta yutuq berilmaydi; qayta ochish", async () => {
  await ikkala(
    `muzlat("2026-10-04 21:15:00")\nvz.bajar(db, ${ID.kit_bugun})\nvz.bajar(db, ${ID.kit_bugun}, False)\nvz.bajar(db, ${ID.kit_bugun})`,
    async (db) => {
      muzlat("2026-10-04 21:15:00");
      await vz.bajar(db, ID.kit_bugun); await vz.bajar(db, ID.kit_bugun, false); await vz.bajar(db, ID.kit_bugun);
    });
});

test("bajar: oddiy vazifa (yutuqsiz), kechiktirish tozalanadi", async () => {
  await ikkala(
    `muzlat("2026-10-04 09:20:00")\nvz.kechiktir(db, ${ID.musor}, 30)\nvz.bajar(db, ${ID.musor})`,
    async (db) => { muzlat("2026-10-04 09:20:00"); await vz.kechiktir(db, ID.musor, 30); await vz.bajar(db, ID.musor); });
});

test("bajar: qazo bo'lgan namoz o'qildi — ochiq qazo ishi o'chadi", async () => {
  await ikkala(
    `muzlat("2026-10-04 07:00:00")\nvz.bajar(db, ${ID.shom})`,
    async (db) => { muzlat("2026-10-04 07:00:00"); await vz.bajar(db, ID.shom); });
});

test("bajar: topilmagan vazifa — xato", async () => {
  const db = jsDb(nusxa(U.papka));
  await assert.rejects(() => vz.bajar(db, 999999), /Vazifa topilmadi/);
});

test("qazo_qil: namoz QAZO, qazo ishi bugunga (yoki kelajakdagi kuniga)", async () => {
  const { pr, jr } = await ikkala(
    `muzlat("2026-10-04 13:00:00")\na = vz.qazo_qil(db, ${ID.peshin})\nb = vz.qazo_qil(db, ${ID.kelajak})\nchiq(vz.bitta(db, b)["sana"])`,
    async (db) => {
      muzlat("2026-10-04 13:00:00");
      await vz.qazo_qil(db, ID.peshin);
      const b = await vz.qazo_qil(db, ID.kelajak);
      return (await vz.bitta(db, b)).sana;
    });
  assert.equal(jr, pr);
  assert.equal(jr, "2026-10-06");
});

test("qazo_qil: xato holatlari bir xil", async () => {
  const p = nusxa(U.papka);
  const pr = pyIshla(p, String.raw`
r = []
for vid in (${ID.musor}, ${ID.shom}, 999999):
    try:
        vz.qazo_qil(db, vid)
        r.append(None)
    except ValueError as e:
        r.append(str(e))
chiq(r)`);
  const db = jsDb(nusxa(U.papka));
  const jr = [];
  for (const vid of [ID.musor, ID.shom, 999999]) {
    try { await vz.qazo_qil(db, vid); jr.push(null); } catch (e) { jr.push(e.message); }
  }
  assert.deepEqual(jr, pr);
});

test("kechiktir + kechiktirilganmi + menyu_qoy", async () => {
  const { pr, jr } = await ikkala(String.raw`
h = muzlat("2026-10-04 09:40:00")
m = vz.kechiktir(db, ${ID.musor}, 30)
v = vz.bitta(db, ${ID.musor})
a = [vz.kechiktirilganmi(v, _dt.datetime(2026,10,4,10,9,59)), vz.kechiktirilganmi(v, _dt.datetime(2026,10,4,10,10,0))]
o = vz.navbat_turi(db)
oid = db.q1("SELECT id FROM vazifa WHERE nom=? AND sana='2026-10-04'", o["nom"])["id"]
vz.menyu_qoy(db, oid, "  Mastava ")
vz.menyu_qoy(db, oid, "   ")
vz.menyu_qoy(db, oid, "Osh")
e = []
for d in (0, -5, "x"):
    try:
        vz.kechiktir(db, ${ID.musor}, d)
    except ValueError as ex:
        e.append(type(ex).__name__)
chiq([m, a, e])`, async (db) => {
    muzlat("2026-10-04 09:40:00");
    const m = await vz.kechiktir(db, ID.musor, 30);
    const v = await vz.bitta(db, ID.musor);
    const vaqt = await import("../src/vaqt.js");
    const a = [vz.kechiktirilganmi(v, vaqt.vaqtDan("2026-10-04 10:09:59")), vz.kechiktirilganmi(v, vaqt.vaqtDan("2026-10-04 10:10:00"))];
    const o = await vz.navbat_turi(db);
    const oid = (await db.q1("SELECT id FROM vazifa WHERE nom=? AND sana='2026-10-04'", o.nom)).id;
    await vz.menyu_qoy(db, oid, "  Mastava ");
    await vz.menyu_qoy(db, oid, "   ");
    await vz.menyu_qoy(db, oid, "Osh");
    const e = [];
    for (const d of [0, -5, "x"]) { try { await vz.kechiktir(db, ID.musor, d); } catch { e.push("ValueError"); } }
    return [m, a, e];
  });
  assert.deepEqual(jr, pr);
  assert.equal(jr[0], "2026-10-04 10:10:00");
});

test("yutuqlarni_tekshir mustaqil (o'z amalida)", async () => {
  // Bazada bajarilgan 7 kun bo'lsa bajar'siz ham yutuq beriladi.
  await ikkala(
    `muzlat("2026-10-04 22:00:00")\ndb.con.execute("UPDATE vazifa SET holat='bajarildi' WHERE id=?", (${ID.kit_bugun},))\nchiq([dict(x) for x in vz.yutuqlarni_tekshir(db)])`,
    async (db) => {
      muzlat("2026-10-04 22:00:00");
      await db.exec("UPDATE vazifa SET holat='bajarildi' WHERE id=?", ID.kit_bugun);
      return vz.yutuqlarni_tekshir(db);
    });
});

// ─────────────────────────────────────────────── takror_toldir

const TAKROR_SEED = String.raw`
muzlat("2026-10-04 06:00:00")
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
def qoida(**d):
    d.setdefault("davomiylik", 20)
    return db.apply("vazifa_takror", "INSERT", d)
t1 = qoida(nom="Bomdod namozi", odam_id=A, vaqt="05:30", naqsh="kunlik", oraliq=1, boshlanish="2026-09-01")
t2 = qoida(nom="Sport", odam_id=O, vaqt="16:00", naqsh="kunlar", kunlar="0,2,6", oraliq=1, boshlanish="2026-10-01", izoh="Zal")
t3 = qoida(nom="Gullarga suv", odam_id=F, vaqt=None, naqsh="oraliq", oraliq=3, boshlanish="2026-09-29")
t4 = qoida(nom="Dori", odam_id=F, vaqt="08:00", naqsh="kunlik", oraliq=1, boshlanish="2026-10-02", tugash="2026-10-10")
t5 = qoida(nom="Nofaol", odam_id=F, vaqt="08:00", naqsh="kunlik", oraliq=1, boshlanish="2026-10-01", faol=0)
t6 = qoida(nom="Ochirilgan", odam_id=F, vaqt="08:00", naqsh="kunlik", oraliq=1, boshlanish="2026-10-01", ochirilgan=1)
t7 = qoida(nom="Kelajak", odam_id=O, vaqt="07:00", naqsh="oraliq", oraliq=7, boshlanish="2026-10-20")
t8 = qoida(nom="Tugagan", odam_id=O, vaqt="07:00", naqsh="kunlik", oraliq=1, boshlanish="2026-09-01", tugash="2026-09-30")
# Avval qo'lda yozilgan bitta kun (to'ldirish uni takrorlamasin)
db.apply("vazifa", "INSERT", {"nom": "Bomdod namozi", "odam_id": A, "sana": "2026-10-05", "vaqt": "05:30",
         "davomiylik": 20, "holat": "bajarildi", "manba": vz.takror_kaliti(t1, "2026-10-05")})
chiq({"t1": t1, "t2": t2, "t3": t3})
`;
const T = usta(TAKROR_SEED);

test("takror_toldir: 3 naqsh, tugash, nofaol/o'chirilgan, kelajak", async () => {
  const pp = nusxa(T.papka), jp = nusxa(T.papka);
  const oz = maxOz(pp);
  const pr = pyIshla(pp, `muzlat("2026-10-04 06:00:00")\nchiq(vz.takror_toldir(db))`);
  muzlat("2026-10-04 06:00:00");
  const db = jsDb(jp);
  const jr = await vz.takror_toldir(db);
  assert.equal(jr, pr);
  assert.ok(jr > 40);
  assert.deepEqual(qatorlar(jp, VAZIFA_SQL), qatorlar(pp, VAZIFA_SQL));
  assert.deepEqual(jurnalNorm(jurnal(jp, oz)), jurnalNorm(jurnal(pp, oz)));
  // takror_sanalari ham bir xil
  const sanalar = pyIshla(nusxa(T.papka),
    `chiq([[d.isoformat() for d in vz.takror_sanalari(t, "2026-10-04", "2026-11-03")] for t in vz.takrorlar(db)])`);
  assert.deepEqual((await vz.takrorlar(db)).map((t) => vz.takror_sanalari(t, "2026-10-04", "2026-11-03")), sanalar);
});

test("takror_toldir: idempotent, o'chirilgan kun tirilmaydi, ufq siljiydi", async () => {
  const pp = nusxa(T.papka), jp = nusxa(T.papka);
  const pr = pyIshla(pp, String.raw`
muzlat("2026-10-04 06:00:00")
n1 = vz.takror_toldir(db)
oz = db.skalyar("SELECT MAX(id) FROM ozgarishlar")
n2 = vz.takror_toldir(db)
oz2 = db.skalyar("SELECT MAX(id) FROM ozgarishlar")
vid = db.q1("SELECT id FROM vazifa WHERE manba=?", vz.takror_kaliti(${T.id.t1}, "2026-10-07"))["id"]
vz.ochir(db, vid)
n3 = vz.takror_toldir(db)
n4 = vz.takror_toldir(db, "2026-10-06")
n5 = vz.takror_toldir(db, "2026-10-06", 0)
chiq([n1, n2, oz == oz2, n3, n4, n5])`);
  muzlat("2026-10-04 06:00:00");
  const db = jsDb(jp);
  const n1 = await vz.takror_toldir(db);
  const oz = await db.skalyar("SELECT MAX(id) FROM ozgarishlar");
  const n2 = await vz.takror_toldir(db);
  const oz2 = await db.skalyar("SELECT MAX(id) FROM ozgarishlar");
  const vid = (await db.q1("SELECT id FROM vazifa WHERE manba=?", vz.takror_kaliti(T.id.t1, "2026-10-07"))).id;
  await db.apply("vazifa", "DELETE", {}, vid, "Vazifa o'chirildi: Bomdod namozi");
  const n3 = await vz.takror_toldir(db);
  const n4 = await vz.takror_toldir(db, "2026-10-06");
  const n5 = await vz.takror_toldir(db, "2026-10-06", 0);
  assert.deepEqual([n1, n2, oz === oz2, n3, n4, n5], pr);
  assert.equal(n2, 0); assert.equal(n3, 0);
  assert.deepEqual(qatorlar(jp, VAZIFA_SQL), qatorlar(pp, VAZIFA_SQL));
});

test("takror_toldir: surilgan kun (sana kalitdan farq qiladi) — Python bilan bir xil", async () => {
  // Kalit sanasi 10-06, lekin qator 11-20 ga surilgan: Python uni oraliqdan
  // tashqarida ko'rmaydi va yana yozadi. JS ham aynan shunday qilishi kerak.
  const pp = nusxa(T.papka), jp = nusxa(T.papka);
  const kod = `UPDATE vazifa SET sana='2026-11-20' WHERE manba='takror:${T.id.t1}:2026-10-05'`;
  const pr = pyIshla(pp, `muzlat("2026-10-04 06:00:00")\ndb.con.execute("${kod}")\nchiq(vz.takror_toldir(db))`);
  muzlat("2026-10-04 06:00:00");
  const db = jsDb(jp);
  await db.exec(kod);
  assert.equal(await vz.takror_toldir(db), pr);
  assert.deepEqual(qatorlar(jp, VAZIFA_SQL), qatorlar(pp, VAZIFA_SQL));
});
