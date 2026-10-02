// tg_rasxod.js ↔ core/tg_rasxod.py parity: butun suhbat (har qadamda Telegram
// chaqiruvlari, qaytgan qiymat, sozlamadagi holat) va natijadagi rasxod/ulush
// qatorlari. Python va JS bir xil ekilgan bazaning ikki nusxasida ishlaydi.
import { test } from "node:test";
import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { ikkiBaza, pyJson, PY_SOAT, PY_TG, jsSoat, jsTg, tgNorm, idsiz,
  PY_RASXODLAR, jsRasxodlar } from "./moliya_yordam.js";
import * as tr from "../src/tg_rasxod.js";
import * as tm from "../src/tg_menyu.js";
import * as rk from "../src/rasxod_kirit.js";

const CHAT = 555;
const BOSH_SOAT = "2026-09-25 10:00:00";

const EKISH = `
from core import entries, mahsulot as mh
F = entries.odam_qosh(db, "Fayzulloxon")
O = entries.odam_qosh(db, "Otabek")
A = entries.odam_qosh(db, "Abbosxon")
db.apply("odam", "UPDATE", {"telegram": "fsultonoov"}, F)
db.apply("odam", "UPDATE", {"telegram": "otabek"}, O)
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
trn = db.skalyar("SELECT id FROM turi WHERE nom='Transport'")
mv = mh.kategoriya_qosh(db, "Mevalar", bz, rasm=mh.bosh_belgilar(db)[0])
ol = mh.saqla(db, nom="Olma", turi_id=mv, narx=18_000, miqdor=1.5, olchov="kg",
              izoh="Qizil <olma> & shirin")
mh.saqla(db, nom="Nok", turi_id=bz, narx=0)
mh.saqla(db, nom="Banan", turi_id=mv, narx=25_000)
mh.rasm_baytdan(db, ol, b"\\x89PNG\\r\\n\\x1a\\nsoxta-rasm", ".png")
db.apply("yoq_kun", "INSERT", {"odam_id": A, "boshi": "2026-09-24", "oxiri": "2026-09-24"})
entries.kirim_qosh(db, "2026-09-01", F, 1_000_000)
entries.rasxod_qosh(db, "2026-09-01", "Non", 10_000, F)
entries.rasxod_qosh(db, "2026-09-02", "Sut", 20_000, O, umumiymi=True, parametrlar={F: 1.0, O: 1.0})
`;

/** Python: qadamlarni bajaradi, har qadam natijasini yozadi. */
const PY_YURGIZ = (qadamlar, chegara) => `
${PY_SOAT(BOSH_SOAT)}
${PY_TG}
${PY_RASXODLAR(chegara[0])}
CHAT = ${CHAT}
QADAMLAR = json.loads(r'''${JSON.stringify(qadamlar)}''')
natija = []
oxirgi_rid = None
for s in QADAMLAR:
    _tq.clear()
    t = s["t"]
    r = None
    if t == "boshla":
        r = tr.boshlash(db, "T", CHAT, s["kim"], bugun=s.get("bugun"))
    elif t == "tugma":
        data = s["data"].replace("OXIRGI", str(oxirgi_rid))
        h = tr.holat_ol(db, CHAT)
        cb = {"id": "c", "data": data, "from": {"username": "x"},
              "message": {"message_id": s.get("mid") or (h or {}).get("xabar"),
                          "chat": {"id": CHAT, "type": "private"}}}
        r = tr.tugma_bosildi(db, "T", cb, s["kim"])
    elif t == "matn":
        r = tr.matn_keldi(db, "T", {"chat": {"id": CHAT, "type": "private"},
                                    "text": s["text"]}, s["kim"])
    elif t == "menyu":
        r = tm.matn_keldi(db, "T", {"chat": {"id": CHAT, "type": "private"},
                                    "text": s["text"]}, s["kim"])
    elif t == "soat":
        SOAT[0] = _dt.datetime.fromisoformat(s["soat"])
    if isinstance(r, str) and "saqlandi #" in r:
        oxirgi_rid = int(r.split("#")[1])
    xom = db.sozlama(f"tg_rx:{CHAT}", "")
    hol = json.loads(xom) if xom else None
    natija.append({"r": r, "tg": _tq[:], "holat": hol, "xom": xom, "mid": _mid[0],
                   "ptartib": list((hol["q"]["parametrlar"] or {}).keys())
                              if hol and hol["q"]["parametrlar"] is not None else None})
oz = [[x["tavsif"], x["jadval"], x["amal"]] for x in db.q(
    "SELECT tavsif, jadval, amal FROM ozgarishlar WHERE id > ? ORDER BY id", ${chegara[1]})]
print(json.dumps({"qadamlar": natija, "rasxod": _rasxodlar(), "oz": oz}, ensure_ascii=False))
`;

async function jsYurgiz(db, qadamlar, tgYoz, chegara) {
  const natija = [];
  let oxirgi = null;
  for (const s of qadamlar) {
    tgYoz.yozuv.length = 0;
    let r = null;
    if (s.t === "boshla") {
      r = (await tr.boshlash(db, "T", CHAT, s.kim, s.bugun ?? null)) ?? null;
    } else if (s.t === "tugma") {
      const data = s.data.replace("OXIRGI", String(oxirgi));
      const h = await tr.holat_ol(db, CHAT);
      const cb = { id: "c", data, from: { username: "x" },
        message: { message_id: s.mid || (h || {}).xabar || null, chat: { id: CHAT, type: "private" } } };
      r = await tr.tugma_bosildi(db, "T", cb, s.kim);
    } else if (s.t === "matn") {
      r = await tr.matn_keldi(db, "T", { chat: { id: CHAT, type: "private" }, text: s.text }, s.kim);
    } else if (s.t === "menyu") {
      r = await tm.matn_keldi(db, "T", { chat: { id: CHAT, type: "private" }, text: s.text }, s.kim);
    } else if (s.t === "soat") {
      jsSoat(s.soat);
    }
    if (typeof r === "string" && r.includes("saqlandi #")) oxirgi = Number(r.split("#")[1]);
    const xom = await db.sozlama(`tg_rx:${CHAT}`, "");
    const hol = xom ? JSON.parse(xom) : null;
    natija.push({ r, tg: [...tgYoz.yozuv], holat: hol, xom,
      ptartib: hol && hol.q.parametrlar != null ? rk.parametrlar_tartibi(xom).map(([k]) => String(k)) : null });
  }
  const oz = (await db.q("SELECT tavsif, jadval, amal FROM ozgarishlar WHERE id > ? ORDER BY id", chegara[1]))
    .map((x) => [x.tavsif, x.jadval, x.amal]);
  return { qadamlar: natija, rasxod: await jsRasxodlar(db, chegara[0]), oz };
}

async function tayyorla() {
  const b = ikkiBaza(EKISH);
  const { db, d1 } = b;
  await d1.exec("CREATE TABLE IF NOT EXISTS rasm(nom TEXT PRIMARY KEY, data BLOB)");
  const id = async (sql) => db.skalyar(sql, [], null);
  const ids = {
    F: await id("SELECT id FROM odam WHERE nom='Fayzulloxon'"),
    O: await id("SELECT id FROM odam WHERE nom='Otabek'"),
    A: await id("SELECT id FROM odam WHERE nom='Abbosxon'"),
    bz: await id("SELECT id FROM turi WHERE nom='Bozorlik'"),
    trn: await id("SELECT id FROM turi WHERE nom='Transport'"),
    mv: await id("SELECT id FROM turi WHERE nom='Mevalar'"),
    ol: await id("SELECT id FROM item WHERE nom='Olma'"),
    ban: await id("SELECT id FROM item WHERE nom='Banan'"),
  };
  // Python rasmni faylga yozgan — JS nusxasida xuddi shu nom bilan D1 `rasm` ga.
  const rasm = await id(`SELECT rasm FROM item WHERE id=${ids.ol}`);
  await db.exec("INSERT INTO rasm(nom, data) VALUES(?, ?)", rasm,
    new TextEncoder().encode("\x89PNG\r\n\x1a\nsoxta-rasm"));
  const chegara = [await id("SELECT MAX(id) FROM rasxod"), await id("SELECT MAX(id) FROM ozgarishlar")];
  return { ...b, ids, chegara };
}

function solishtir(py, js) {
  assert.equal(js.qadamlar.length, py.qadamlar.length);
  for (let i = 0; i < py.qadamlar.length; i++) {
    const p = py.qadamlar[i], j = js.qadamlar[i];
    const ctx = `qadam ${i}: ${JSON.stringify(p.r)}`;
    assert.deepEqual(idsiz(j.r), idsiz(p.r), ctx);
    assert.deepEqual(idsiz(tgNorm(j.tg)), idsiz(tgNorm(p.tg)), ctx + " — Telegram chaqiruvlari");
    assert.deepEqual(idsiz(j.holat), idsiz(p.holat), ctx + " — holat");
    assert.deepEqual(j.ptartib, p.ptartib, ctx + " — parametrlar tartibi");
  }
  assert.deepEqual(js.rasxod, py.rasxod, "rasxod/ulush qatorlari");
  assert.deepEqual(js.oz, py.oz, "ozgarishlar (tavsif, jadval, amal)");
}

async function parity(qadamlar) {
  const t = await tayyorla();
  const q = qadamlar(t.ids);
  jsSoat(BOSH_SOAT);
  const tgYoz = jsTg();
  const py = pyJson(t.pyPapka, PY_YURGIZ(q, t.chegara));
  const js = await jsYurgiz(t.db, q, tgYoz, t.chegara);
  if (process.env.FUY_DUMP) writeFileSync(process.env.FUY_DUMP, JSON.stringify(py, null, 1));
  solishtir(py, js);
  return { py, js, t };
}

test("1. umumiy: ichki kategoriya, mahsulot+rasm, odam olib tashlash/qaytarish, kecha (qolda), saqlash, rx:del", async () => {
  const { py, js } = await parity(({ F, O, A, bz, mv, ol }) => [
    { t: "boshla", kim: F },
    { t: "tugma", data: `rx:ko`, kim: F },            // ildizda «orqaga» — o'zgarmagan ekran (not modified)
    { t: "tugma", data: `rx:k:${bz}`, kim: F },       // ichki kategoriyasi bor — ichiga
    { t: "tugma", data: `rx:ko`, kim: F },            // orqaga — ildiz
    { t: "tugma", data: `rx:k:${bz}`, kim: F },
    { t: "tugma", data: `rx:k:${mv}`, kim: F },       // → mahsulot
    { t: "tugma", data: `rx:mo`, kim: F },            // orqaga — Bozorlik ichi
    { t: "tugma", data: `rx:kt:${bz}`, kim: F },      // «Bozorlik o'zi» → mahsulotlar (ichkida bilan)
    { t: "tugma", data: `rx:mo`, kim: F },
    { t: "tugma", data: `rx:k:${mv}`, kim: F },
    { t: "tugma", data: `rx:m:${ol}`, kim: F },       // rasm + nom/narx
    { t: "tugma", data: "rx:n", kim: F },
    { t: "matn", text: "18 001", kim: F },            // summa matn bilan (toq — qoldiq)
    { t: "matn", text: "salom", kim: F },             // tugma kutilayotganda matn — qayta chizish
    { t: "tugma", data: `rx:p:${O}`, kim: F },
    { t: "tugma", data: "rx:t:u", kim: F },
    { t: "tugma", data: `rx:q:${A}`, kim: F },        // Abbosxon olib tashlandi
    { t: "tugma", data: `rx:q:${F}`, kim: F },
    { t: "tugma", data: `rx:q:${F}`, kim: F },        // qaytdi — tartib o'zgaradi (O, F)
    { t: "tugma", data: "rx:qd", kim: F },
    { t: "tugma", data: "rx:d:1", kim: F },           // kecha — qolda: tanlov saqlanadi
    { t: "tugma", data: "rx:to", kim: F },
    { t: "tugma", data: "rx:qd", kim: F },
    { t: "tugma", data: "rx:ok", kim: F },
    { t: "tugma", data: "rx:t:u", kim: F, mid: 1 },   // suhbat tugagan — eski
    { t: "tugma", data: "rx:del:OXIRGI", kim: F, mid: 999 },
    { t: "tugma", data: "rx:del:OXIRGI", kim: F, mid: 999 },
  ]);
  const saqlangan = py.qadamlar.find((x) => String(x.r).startsWith("rx: saqlandi"));
  assert.ok(saqlangan, "Python saqladi");
  assert.equal(js.rasxod.length, 1);
  assert.equal(js.rasxod[0].ochirilgan, 1, "rx:del — o'chdi");
  assert.equal(js.rasxod[0].sana, "2026-09-24");
  assert.ok(py.qadamlar.some((x) => x.tg.some(([m]) => m === "sendPhoto")), "rasm yuborildi");
});

test("2. kecha — uydagilar qayta olinadi (qolda emas); summa xatosi; umumiy", async () => {
  const { js } = await parity(({ O, trn }) => [
    { t: "boshla", kim: O },
    { t: "tugma", data: `rx:k:${trn}`, kim: O },      // mahsulotsiz → sabab
    { t: "tugma", data: "rx:n", kim: O },             // nom bo'sh — noma'lum
    { t: "matn", text: "Taksi", kim: O },
    { t: "matn", text: "abc", kim: O },
    { t: "matn", text: "12,5", kim: O },
    { t: "matn", text: "0", kim: O },
    { t: "matn", text: "25.000 so'm", kim: O },
    { t: "tugma", data: `rx:p:${O}`, kim: O },
    { t: "tugma", data: "rx:t:u", kim: O },
    { t: "tugma", data: "rx:qd", kim: O },
    { t: "tugma", data: "rx:d:1", kim: O },           // kecha Abbosxon yo'q → F, O
    { t: "tugma", data: "rx:d:0", kim: O },           // bugun — yana uchala
    { t: "tugma", data: "rx:d:1", kim: O },
    { t: "tugma", data: "rx:ok", kim: O },
  ]);
  assert.equal(js.rasxod[0].ulush.length, 2);
});

test("3. shaxsiy va boshqa uchun; /rasxod va «➕ Rasxod» matni; menyudan boshlash", async () => {
  await parity(({ F, O, A, trn }) => [
    { t: "matn", text: "/rasxod", kim: A },
    { t: "tugma", data: `rx:k:${trn}`, kim: A },
    { t: "matn", text: "Avtobus", kim: A },
    { t: "matn", text: "5000", kim: A },
    { t: "tugma", data: "rx:s", kim: A },             // summa allaqachon bor — davom
    { t: "tugma", data: `rx:p:${A}`, kim: A },
    { t: "tugma", data: "rx:t:s", kim: A },
    { t: "tugma", data: "rx:to", kim: A },            // shaxsiy → «tur» ga
    { t: "tugma", data: "rx:t:s", kim: A },
    { t: "tugma", data: "rx:ok", kim: A },
    { t: "matn", text: "➕ RASXOD", kim: O },
    { t: "tugma", data: `rx:k:${trn}`, kim: O },
    { t: "matn", text: "Taksi <tez> & arzon", kim: O },
    { t: "matn", text: "7 000", kim: O },
    { t: "tugma", data: `rx:p:${O}`, kim: O },
    { t: "tugma", data: "rx:t:b", kim: O },
    { t: "tugma", data: `rx:u:${F}`, kim: O },
    { t: "tugma", data: "rx:to", kim: O },            // → «uchun»
    { t: "tugma", data: `rx:u:${F}`, kim: O },
    { t: "tugma", data: "rx:ok", kim: O },
    { t: "menyu", text: "➕ rasxod yozish", kim: F },  // tg_menyu orqali
    { t: "tugma", data: `rx:k:${trn}`, kim: F },
    { t: "matn", text: "Metro", kim: F },
    { t: "matn", text: "1700", kim: F },
    { t: "tugma", data: `rx:p:${O}`, kim: F },        // boshqa to'lovchi
    { t: "tugma", data: "rx:t:b", kim: F },
    { t: "tugma", data: `rx:u:${F}`, kim: F },
    { t: "tugma", data: "rx:to", kim: F },
    { t: "tugma", data: "rx:xyz", kim: F },           // noma'lum amal
    { t: "tugma", data: `rx:u:${A}`, kim: F },
    { t: "tugma", data: "rx:ok", kim: F },
  ]);
});

test("4. tekshiruv xatosi (hech kim tanlanmagan), xatodan keyin qadam, /bekor, rx:x, eskirgan suhbat", async () => {
  await parity(({ F, O, A, trn, ban, mv }) => [
    { t: "boshla", kim: F },
    { t: "tugma", data: `rx:k:${trn}`, kim: F },
    { t: "matn", text: "Avtobus", kim: F },
    { t: "matn", text: "5000", kim: F },
    { t: "tugma", data: `rx:p:${F}`, kim: F },
    { t: "tugma", data: "rx:t:u", kim: F },
    { t: "tugma", data: `rx:q:${F}`, kim: F },
    { t: "tugma", data: `rx:q:${O}`, kim: F },
    { t: "tugma", data: `rx:q:${A}`, kim: F },
    { t: "tugma", data: "rx:qd", kim: F },
    { t: "tugma", data: "rx:ok", kim: F },            // xato — saqlanmaydi
    { t: "tugma", data: "rx:ok", kim: F },            // yana — ekran o'zgarmagan (not modified)
    { t: "tugma", data: "rx:d:1", kim: F },           // xato tozalanadi
    { t: "matn", text: "/bekor", kim: F },
    { t: "matn", text: "Taksi", kim: F },             // suhbat yo'q — None
    { t: "boshla", kim: F },
    { t: "tugma", data: "rx:x", kim: F },
    { t: "boshla", kim: O },
    { t: "tugma", data: `rx:k:${mv}`, kim: O },
    { t: "tugma", data: `rx:m:0`, kim: O },           // mahsulotsiz
    { t: "matn", text: "Meva", kim: O },
    { t: "soat", soat: "2026-09-25 15:59:00" },       // 5:59 — hali tirik
    { t: "tugma", data: "rx:s", kim: O },             // summa yo'q — noma'lum
    { t: "soat", soat: "2026-09-25 23:00:00" },       // 6 soatdan oshdi
    { t: "tugma", data: "rx:s", kim: O },             // eski
    { t: "matn", text: "5000", kim: O },              // holat yo'q — None
    { t: "boshla", kim: O },
    { t: "tugma", data: `rx:k:${mv}`, kim: O },
    { t: "tugma", data: `rx:m:${ban}`, kim: O },      // rasmsiz mahsulot
    { t: "tugma", data: "rx:n", kim: O },
    { t: "tugma", data: "rx:s", kim: O },
    { t: "tugma", data: `rx:p:${O}`, kim: O },
    { t: "tugma", data: "rx:t:u", kim: O },           // bugun (23-sentabr emas) — sana 25
    { t: "tugma", data: "rx:qd", kim: O },
    { t: "tugma", data: "rx:ok", kim: O },
  ]);
});

test("5. Python yozgan suhbat holatini JS davom ettiradi (o'tish payti)", async () => {
  const t = await tayyorla();
  const { F, O, A, bz, mv, ol } = t.ids;
  const q = [
    { t: "boshla", kim: F },
    { t: "tugma", data: `rx:k:${bz}`, kim: F },
    { t: "tugma", data: `rx:k:${mv}`, kim: F },
    { t: "tugma", data: `rx:m:${ol}`, kim: F },
    { t: "tugma", data: "rx:n", kim: F },
    { t: "tugma", data: "rx:s", kim: F },
    { t: "tugma", data: `rx:p:${F}`, kim: F },
    { t: "tugma", data: "rx:t:u", kim: F },
    { t: "tugma", data: `rx:q:${F}`, kim: F },
    { t: "tugma", data: `rx:q:${F}`, kim: F },        // tartib: O, A, F
    // ↓ shu yerdan JS davom etadi
    { t: "tugma", data: `rx:q:${A}`, kim: F },
    { t: "tugma", data: "rx:qd", kim: F },
    { t: "tugma", data: "rx:d:1", kim: F },
    { t: "tugma", data: "rx:ok", kim: F },
  ];
  const N = 10;
  jsSoat(BOSH_SOAT);
  const py = pyJson(t.pyPapka, PY_YURGIZ(q, t.chegara));
  // Python'ning N-qadamdan keyingi holati va message_id hisoblagichi JS bazasiga.
  await t.db.sozlama_qoy(`tg_rx:${CHAT}`, py.qadamlar[N - 1].xom);
  assert.deepEqual(py.qadamlar[N - 1].ptartib, [String(O), String(A), String(F)]);
  const tgYoz = jsTg(py.qadamlar[N - 1].mid);
  const js = await jsYurgiz(t.db, q.slice(N), tgYoz, t.chegara);
  solishtir({ ...py, qadamlar: py.qadamlar.slice(N) }, js);
});

test("_summa_oqi: Python bilan bir xil", async () => {
  const t = await tayyorla();
  const misollar = ["25000", "25 000", "25 000", "25.000", "25,000", "7000 so'm", "7000som",
    "7000 SO'M", "-5", "besh", "0", "007", "12.5", "1 2 3", "  42  ", "so'm", "", "3e5", "+5"];
  const py = pyJson(t.pyPapka, `
import json
from core import tg_rasxod as tr
print(json.dumps([tr._summa_oqi(x) for x in json.loads(r'''${JSON.stringify(misollar)}''')]))`);
  assert.deepEqual(misollar.map(tr._summa_oqi), py);
});
