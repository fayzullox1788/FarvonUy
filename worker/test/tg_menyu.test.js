// tg_menyu.js ↔ core/tg_menyu.py parity: pul matnlari (umumiy tashqi qarz bilan),
// vazifa matnlari, `_norm` variantlari, `javob` va `matn_keldi` Telegram chaqiruvlari.
import { test } from "node:test";
import assert from "node:assert/strict";
import { ikkiBaza, pyJson, PY_SOAT, PY_TG, jsSoat, jsTg, tgNorm } from "./moliya_yordam.js";
import * as tm from "../src/tg_menyu.js";

const BOSH_SOAT = "2026-09-25 10:00:00";
const CHAT = 777;

const EKISH = `
import money
from datetime import date
from core import entries, vazifa as vz
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon <A&B>")
entries.kirim_qosh(db, "2026-09-01", F, 1_000_000)
entries.kirim_qosh(db, "2026-09-02", O, 300_000)
entries.rasxod_qosh(db, "2026-09-03", "Bozorlik", 100_001, F)
entries.rasxod_qosh(db, "2026-09-04", "Gaz", 60_000, O, parametrlar={O: 1.0, A: 1.0})
entries.rasxod_qosh(db, "2026-09-05", "Poyabzal", 250_000, O, kim_uchun=F)
entries.rasxod_qosh(db, "2026-09-06", "Kitob", 40_000, A, umumiymi=False)
entries.qarz_qosh(db, "2026-09-07", A, F, 15_000)
entries.hisob_kitob_qosh(db, "2026-09-08", F, O, 20_000)
# shaxsiy tashqi qarz (qisman qaytarilgan) + yopilgani
q1 = entries.tashqi_qarz_qosh(db, "2026-09-10", F, "Aziz aka", 500_000, "telefon")
entries.tashqi_tolov_qosh(db, q1, "2026-09-12", 200_000)
q2 = entries.tashqi_qarz_qosh(db, "2026-09-11", O, "Bank", 50_000)
entries.tashqi_tolov_qosh(db, q2, "2026-09-13", 50_000)
# umumiy tashqi qarz (Fayzulloxon olgan, uchalasiga) — qisman qaytarilgan
q3 = entries.tashqi_qarz_qosh(db, "2026-09-15", F, "Shoxrux aka", 90_001, "ijara",
                              umumiy=True, qatnashchilar=[F, O, A])
entries.tashqi_tolov_qosh(db, q3, "2026-09-16", 30_000)
# umumiy, faqat O va F — Abbosxonda ulush yo'q
q4 = entries.tashqi_qarz_qosh(db, "2026-09-17", O, "Do'kon", 40_000, umumiy=True,
                              qatnashchilar=[O, F])
# vazifalar — bugun (2026-09-25)
kun = date(2026, 9, 25)
vz.tur_qosh(db, "Kitob o'qish", shaxsiy=True)
vz.tur_qosh(db, "Algoritmlar", shaxsiy=True)
vz.qosh(db, "Idish yuvish", F, kun, "20:00")
v2 = vz.qosh(db, "Kitob o'qish", F, kun, "21:00", izoh="20 bet <tez>")
dv = vz.qosh(db, "Algoritmlar", F, kun, "09:00", izoh="Karimov · B-204")
db.apply("vazifa", "UPDATE", {"manba": "dars:2026-09-25:1"}, dv)
vz.bajar(db, v2)
v3 = vz.qosh(db, "Idish yuvish", O, kun, "20:00")
v4 = vz.qosh(db, "Kitob o'qish", O, kun)
db.apply("vazifa", "UPDATE", {"holat": "qazo"}, v3)
vz.bajar(db, v4)
vz.qosh(db, "Idish yuvish", A, date(2026, 9, 26), "20:00")
`;

const KIRISHLAR = [
  "/start", "/menu", "/menyu", "menyu", "START", "  Bosh   menyu ", "‹ Asosiy menyu", "asosiy",
  "💰 Moliya", "moliya", "MOLIYA", "Moliya!!!", "📋 Vazifalar", "vazifalar",
  "💵 Qancha pulim bor", "qancha pulim bor?", "QANCHA PULIM BOR", "🔄 Aylanma qarz", "aylanma  qarz",
  "🌐 Tashqaridan qarz", "tashqaridan qarz", "🏠 Uy ishlari", "uy ishlari", "🔒 Shaxsiy ishlar",
  "🎓 Universitet", "universitet", "Darslar", "darslarim", "🎓 Bugun qanday darslarim bor",
  "🏠 Bugun uyda qanday vazifalarim bor", "🔒 Bugun shaxsiy qanday ishlarim bor",
  "otabekdan qarz", "qancha qarzim bor", "salom", "", "   ", "🙂", "➕ Rasxod yozish",
  "Qo‘shimcha", "qoʻlingiz", "Qo`l", "qo´l", "qoʼl", "STRASSE straße", "ΟΔΟΣ", "١٢٣ abc", "Ⅻ",
  "tab\tva nbsp", "é", "İstanbul",
];

const PY_HAMMA = (ids) => `
${PY_SOAT(BOSH_SOAT)}
${PY_TG}
from datetime import date
IDS = json.loads(r'''${JSON.stringify(ids)}''')
K = json.loads(r'''${JSON.stringify(KIRISHLAR)}''')
odam = {}
for oid in IDS + [999]:
    odam[str(oid)] = {
        "pulim": tm.pulim(db, oid), "tashqi": tm.tashqi(db, oid),
        "uy": tm.uy_vazifalari(db, oid), "dars": tm.darslar(db, oid),
        "shaxsiy": tm.shaxsiy_ishlar(db, oid),
        "uy26": tm.uy_vazifalari(db, oid, date(2026, 9, 26)),
        "bugungi": {q: [v["nom"] for v in tm.bugungi(db, oid, q)] for q in ("uy", "dars", "shaxsiy")},
        "javob": [tm.javob(db, k, oid) for k in K],
    }
tgr = []
for k in K:
    _tq.clear()
    r = tm.matn_keldi(db, "T", {"chat": {"id": ${CHAT}, "type": "private"}, "text": k}, IDS[0])
    tgr.append([r, _tq[:]])
_tq.clear()
tush = [tm.tushunmadim(db, "T", ${CHAT}), _tq[:]]
print(json.dumps({"aylanma": tm.aylanma(db), "odam": odam, "norm": [tm._norm(k) for k in K],
                  "tg": tgr, "tush": tush}, ensure_ascii=False))
`;

test("tg_menyu: hamma matnlar, _norm, javob, matn_keldi — Python bilan bir xil", async () => {
  const { db, pyPapka } = ikkiBaza(EKISH);
  const ids = (await db.q("SELECT id FROM odam ORDER BY tartib, id")).map((r) => r.id);
  const py = pyJson(pyPapka, PY_HAMMA(ids));
  jsSoat(BOSH_SOAT);

  assert.deepEqual(KIRISHLAR.map(tm._norm), py.norm, "_norm");
  assert.equal(await tm.aylanma(db), py.aylanma, "aylanma");
  for (const oid of [...ids, 999]) {
    const p = py.odam[String(oid)];
    assert.equal(await tm.pulim(db, oid), p.pulim, `pulim ${oid}`);
    assert.equal(await tm.tashqi(db, oid), p.tashqi, `tashqi ${oid}`);
    assert.equal(await tm.uy_vazifalari(db, oid), p.uy, `uy ${oid}`);
    assert.equal(await tm.darslar(db, oid), p.dars, `dars ${oid}`);
    assert.equal(await tm.shaxsiy_ishlar(db, oid), p.shaxsiy, `shaxsiy ${oid}`);
    assert.equal(await tm.uy_vazifalari(db, oid, "2026-09-26"), p.uy26, `uy26 ${oid}`);
    for (const q of ["uy", "dars", "shaxsiy"]) {
      assert.deepEqual((await tm.bugungi(db, oid, q)).map((v) => v.nom), p.bugungi[q], `bugungi ${q} ${oid}`);
    }
    for (let i = 0; i < KIRISHLAR.length; i++) {
      assert.deepEqual(await tm.javob(db, KIRISHLAR[i], oid), p.javob[i], `javob «${KIRISHLAR[i]}» ${oid}`);
    }
  }

  // Telegram: menyu tugmalari (reply keyboard) va tushunmadim
  const tg = jsTg();
  for (let i = 0; i < KIRISHLAR.length; i++) {
    tg.yozuv.length = 0;
    const r = await tm.matn_keldi(db, "T", { chat: { id: CHAT, type: "private" }, text: KIRISHLAR[i] }, ids[0]);
    const [pr, ptg] = py.tg[i];
    assert.equal(r, pr, `matn_keldi «${KIRISHLAR[i]}»`);
    // «➕ Rasxod yozish» suhbat boshlaydi — holatdagi vaqt va klaviatura tg_rasxod testida.
    assert.deepEqual(tgNorm(tg.yozuv), tgNorm(ptg), `matn_keldi TG «${KIRISHLAR[i]}»`);
  }
  tg.yozuv.length = 0;
  assert.equal(await tm.tushunmadim(db, "T", CHAT), py.tush[0]);
  assert.deepEqual(tgNorm(tg.yozuv), tgNorm(py.tush[1]));

  // Sinov ma'lumoti haqiqatan ham turli holatlarni qamrasin.
  const pF = py.odam[String(ids[0])];
  assert.match(pF.pulim, /qarzdor/);
  assert.match(pF.pulim, /tashqaridan/);
  assert.match(py.odam[String(ids[2])].tashqi, /Sizning ulushingiz/);
  assert.match(pF.shaxsiy, /✅/);
  assert.match(py.odam[String(ids[1])].uy, /🕌/);
  assert.match(py.aylanma, /→/);
});
