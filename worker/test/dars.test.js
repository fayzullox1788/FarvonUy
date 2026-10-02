// dars.js ↔ core/dars.py parity. Tarmoqqa chiqmaydi: soxta EduPage javobi
// (tekshir.py `_tt()` bilan bir xil), Python'da `dars._sorov` almashtiriladi.
import { test } from "node:test";
import assert from "node:assert/strict";
import { yangiBaza, py } from "./fixture.js";
import * as dars from "../src/dars.js";
import { soatniQoy } from "../src/vaqt.js";

function tt(kartalar, { qoshimchaDars = false } = {}) {
  const jad = (nom, qatorlar) => ({ id: nom, data_rows: qatorlar });
  const lessons = [
    { id: "l1", subjectid: "s1", teacherids: ["t1"], classids: ["c1"] },
    { id: "l2", subjectid: "s2", teacherids: ["t1"], classids: ["c2"] }, // boshqa guruh
  ];
  if (qoshimchaDars) lessons.push({ id: "l3", subjectid: "s3", teacherids: ["t1", "t9"], classids: ["c1", "c2"] },
    { id: "l4", subjectid: "s4", classids: ["c1"] });
  return { r: { dbiAccessorRes: { tables: [
    jad("days", ["Mo", "Tu", "We", "Th", "Fr", "Sa"].map((n, i) => ({ id: String(i), name: n }))),
    jad("periods", [
      { id: "4", period: "4", starttime: "14:20", endtime: "15:40" },
      { id: "5", period: "5", starttime: "15:50", endtime: "17:10" },
      { id: "6", period: "6", starttime: "17:20" },                  // endtime yo'q → 80
      { id: "7", period: "7", starttime: "18:00", endtime: "18:00" }, // 0 → tashlanadi
    ]),
    jad("classes", [{ id: "c1", name: " se-25 " }, { id: "c2", name: "SE-24" }]),
    jad("subjects", [{ id: "s1", name: "Databases (lec)" }, { id: "s2", name: "OOP (lec)" },
      { id: "s3", name: "Calculus  " }, { id: "s4", name: "Physics" }]),
    jad("teachers", [{ id: "t1", name: "ABDUMANNOPOVA MA'MURA" }]),
    jad("classrooms", [{ id: "r1", name: "GREEN HALL" }, { id: "r2", name: "404AB" }]),
    jad("lessons", lessons),
    jad("cards", kartalar),
  ] } } };
}

const BOSHI = "2026-09-07";
const GACHA = "2026-09-13";
const MON5 = { id: "k1", lessonid: "l1", period: "5", days: "100000", classroomids: ["r1"] };
const WED4 = { id: "k2", lessonid: "l1", period: "4", days: "001000", classroomids: ["r1"] };
const BOSHQA = { id: "k3", lessonid: "l2", period: "4", days: "010000", classroomids: ["r2"] };
const CAL = { id: "k4", lessonid: "l3", period: "6", days: "1000011", classroomids: ["r2", "r1", "rx"] };
const NOL = { id: "k5", lessonid: "l3", period: "7", days: "010000", classroomids: [] };
const MON5B = { ...MON5, classroomids: ["r2"] };
const PHY = { id: "k6", lessonid: "l4", period: "4", days: "000100" };

const PY_DARSLAR = (malumot, sinf = "SE-25") => `
import json
from datetime import date
from core import dars
m = json.loads(r'''${JSON.stringify(malumot)}''')
d = dars.darslar(m, ${JSON.stringify(sinf)}, date.fromisoformat("${BOSHI}"))
print(json.dumps([dict(r, sana=r["sana"].isoformat()) for r in d], ensure_ascii=False))
`;

test("darslar: Python bilan bir xil (izoh, davomiylik, tartib, boshqa guruh)", () => {
  const { papka } = yangiBaza();
  for (const kartalar of [[MON5, WED4, BOSHQA], [MON5B], [CAL, NOL, MON5, WED4, PHY]]) {
    const m = tt(kartalar, { qoshimchaDars: true });
    const pyN = JSON.parse(py(papka, PY_DARSLAR(m)));
    assert.deepEqual(dars.darslar(m, "SE-25", BOSHI), pyN);
  }
  const d = dars.darslar(tt([MON5, WED4, BOSHQA]), "SE-25", BOSHI);
  assert.equal(d.length, 2);
  assert.equal(d[0].manba, "dars:2026-09-07:5");
  assert.equal(d[0].izoh, "Abdumannopova Ma'mura · GREEN HALL");
  assert.equal(d[1].sana, "2026-09-09");
  assert.throws(() => dars.darslar(tt([MON5]), "YO'Q-99", BOSHI), dars.DarsXato);
});

test("hafta_boshi, _nomlash, darsmi", () => {
  assert.equal(dars.hafta_boshi("2026-09-06"), BOSHI);
  assert.equal(dars.hafta_boshi("2026-09-07"), BOSHI);
  assert.equal(dars.hafta_boshi("2026-09-08T00:00:00"), "2026-09-14");
  assert.equal(dars._nomlash("ABDUMANNOPOVA  MA'MURA"), "Abdumannopova Ma'mura");
  assert.ok(dars.darsmi({ manba: "dars:2026-09-07:5" }));
  assert.ok(!dars.darsmi({ manba: "takror:1:2026-09-07" }));
  assert.ok(!dars.darsmi({ nom: "x" }));
  assert.equal(dars.OGOH_DAQIQA, 300);
  assert.equal(dars.KECHIKISH_DAQIQA, 10);
  assert.equal(dars.ORALIQ_DAQIQA, 60);
});

// Bir xil boshlang'ich holatli ikki baza: biri Python, biri JS uchun.
const EKISH = `
from core import entries
oid = entries.odam_qosh(db, "Fayzulloxon")
# Mavjud, lekin o'chirilgan va shaxsiy bo'lmagan tur — tiriltirilishi kerak.
tid = db.apply("vazifa_turi", "INSERT", {"nom": "Databases (lec)", "shaxsiy": 0, "tartib": 50})
db.apply("vazifa_turi", "DELETE", None, tid)
# Qo'lda yozilgan vazifa — tegilmasligi kerak.
db.apply("vazifa", "INSERT", {"nom": "Kitob o'qish", "odam_id": oid, "sana": "${BOSHI}", "vaqt": "21:00", "davomiylik": 30})
`;

const PY_SINX = (qatorlar, oid) => `
import json
from datetime import date
from core import dars
q = json.loads(r'''${JSON.stringify(qatorlar)}''')
for r in q: r["sana"] = date.fromisoformat(r["sana"])
n = dars.sinxronla(db, q, ${oid}, date.fromisoformat("${BOSHI}"), date.fromisoformat("${GACHA}"))
print(json.dumps(n))
`;

async function holat(db) {
  const v = await db.q("SELECT nom,odam_id,sana,vaqt,davomiylik,holat,bajarilgan,izoh,manba,ochirilgan " +
    "FROM vazifa ORDER BY sana, vaqt, nom, manba");
  const t = await db.q("SELECT nom,davomiylik,tartib,navbat,haftalik,shaxsiy,ochirilgan FROM vazifa_turi ORDER BY nom");
  return { v, t };
}

test("sinxronla: Python bilan bir xil natija va qatorlar (3 bosqich)", async () => {
  const P = yangiBaza(EKISH);
  const J = yangiBaza(EKISH);
  const bosqichlar = [
    tt([MON5, WED4, CAL, PHY], { qoshimchaDars: true }),   // qo'shish + 2 yangi tur + tiriltirish
    tt([MON5, WED4, CAL, PHY], { qoshimchaDars: true }),   // o'zgarishsiz → 0/0/0
    tt([MON5B, CAL], { qoshimchaDars: true }),        // xona o'zgardi, chorshanba o'chdi
  ];
  for (const [i, m] of bosqichlar.entries()) {
    const q = dars.darslar(m, "SE-25", BOSHI);
    if (i === 2) {
      // Bajarilgan dars sinxrondan keyin ham bajarilgan qoladi (ikkala bazada bir xil).
      for (const b of [P, J]) {
        const r = await b.db.q1("SELECT id FROM vazifa WHERE manba='dars:2026-09-07:5'");
        await b.db.exec("UPDATE vazifa SET holat='bajarildi', bajarilgan='2026-09-07 17:00:00' WHERE id=?", r.id);
      }
    }
    const oid = (await J.db.q1("SELECT id FROM odam")).id;
    assert.equal((await P.db.q1("SELECT id FROM odam")).id, oid);
    const pyN = JSON.parse(py(P.papka, PY_SINX(q, oid)));
    const jsN = await dars.sinxronla(J.db, q, oid, BOSHI, GACHA);
    assert.deepEqual(jsN, pyN, `bosqich ${i}`);
    assert.deepEqual(await holat(J.db), await holat(P.db), `bosqich ${i} qatorlar`);
  }
  const s = await holat(J.db);
  assert.equal(s.v.find((r) => r.manba === "dars:2026-09-07:5").holat, "bajarildi");
  assert.ok(s.v.some((r) => r.nom === "Kitob o'qish" && r.ochirilgan === 0));
  // JS yozuvlari toq id bilan, jurnal bitta guruhda.
  const g = await J.db.q("SELECT DISTINCT guruh_id, tavsif FROM ozgarishlar WHERE id%2=1 AND jadval IN ('vazifa','vazifa_turi')");
  assert.ok(g.length >= 2 && g.every((x) => x.tavsif === "Dars jadvali yangilandi"));
  await assert.rejects(dars.sinxronla(J.db, [], 1, BOSHI, GACHA), dars.DarsXato);
});

const SOZ = `
from core import dars
dars.sozlama_qoy(db, yoq=True, sinf="SE-25", odam_id=oid)
`;

test("yangila: soxta tarmoq bilan Python bilan bir xil; soatiga bir marta", async () => {
  const P = yangiBaza(EKISH + SOZ);
  const J = yangiBaza(EKISH + SOZ);
  const viewer = { r: { regular: { timetables: [
    { tt_num: "40", text: "Eski", datefrom: "2026-08-30" },
    { tt_num: "41", text: "1-hafta", datefrom: "2026-09-06" },
  ] } } };
  const malumot = tt([MON5, WED4, CAL], { qoshimchaDars: true });
  const pyKod = `
import json
from datetime import datetime
from core import dars
V = json.loads(r'''${JSON.stringify(viewer)}''')
M = json.loads(r'''${JSON.stringify(malumot)}''')
chaqiruv = []
def soxta(url, yuk):
    chaqiruv.append([url, yuk])
    return V if "ttviewer" in url else M
dars._sorov = soxta
h = datetime(2026, 9, 8, 10, 0, 0)
n = dars.yangila(db, h)
print(json.dumps({"n": n, "ch": chaqiruv, "tt": db.sozlama("dars_tt"), "tek": db.sozlama("dars_tekshirildi"),
  "kerak1": dars.kerakmi(db, datetime(2026, 9, 8, 10, 59, 0)), "kerak2": dars.kerakmi(db, datetime(2026, 9, 8, 11, 0, 0))}))
`;
  const pyN = JSON.parse(py(P.papka, pyKod));

  const chaqiruv = [];
  dars.sorovQoy(async (url, yuk) => { chaqiruv.push([url, yuk]); return url.includes("ttviewer") ? viewer : malumot; });
  soatniQoy(new Date(Date.UTC(2026, 8, 8, 5, 0, 0))); // 10:00 Toshkent
  try {
    const h = new Date(Date.UTC(2026, 8, 8, 10, 0, 0)); // devor soati
    const n = await dars.yangila(J.db, h);
    assert.deepEqual(n, pyN.n);
    assert.deepEqual(chaqiruv, pyN.ch);
    assert.equal(await J.db.sozlama("dars_tt"), pyN.tt);
    assert.equal(await J.db.sozlama("dars_tekshirildi"), pyN.tek);
    assert.equal(await dars.kerakmi(J.db, new Date(Date.UTC(2026, 8, 8, 10, 59, 0))), pyN.kerak1);
    assert.equal(await dars.kerakmi(J.db, new Date(Date.UTC(2026, 8, 8, 11, 0, 0))), pyN.kerak2);
    assert.deepEqual(await holat(J.db), await holat(P.db));
    // Soat ichida qayta chaqirilsa tarmoqqa chiqmaydi.
    chaqiruv.length = 0;
    assert.equal(await dars.yangila(J.db, new Date(Date.UTC(2026, 8, 8, 10, 30, 0))), null);
    assert.equal(chaqiruv.length, 0);
    // Tarmoq yiqilsa ham chegara yozilgan bo'ladi.
    dars.sorovQoy(async () => { throw new Error("tarmoq yo'q"); });
    await assert.rejects(dars.yangila(J.db, new Date(Date.UTC(2026, 8, 8, 12, 0, 0))));
    assert.equal(await J.db.sozlama("dars_tekshirildi"), "2026-09-08 12:00:00");
  } finally {
    dars.sorovQoy(null);
    soatniQoy(null);
  }
});

test("sozlanmagan bo'lsa yangila hech narsa qilmaydi", async () => {
  const { db } = yangiBaza();
  dars.sorovQoy(async () => { throw new Error("chaqirilmasligi kerak"); });
  try {
    assert.equal(await dars.sozlangami(db), false);
    assert.equal(await dars.yangila(db), null);
    assert.equal(await dars.kerakmi(db), false);
  } finally { dars.sorovQoy(null); }
});
