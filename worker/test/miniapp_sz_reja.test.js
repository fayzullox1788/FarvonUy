// Mini App «Sozlamalar → Reja (budget)» (miniapp_sz_reja.js + plan.js portlari):
// bir xil amallar ketma-ketligi Python `core/plan.py` da va Worker API'da —
// jadval qatorlari, `ozgarishlar` jurnali (guruhlari bilan) va «Reja va fakt»
// raqamlari AYNAN teng bo'lishi kerak. Ruxsat va xato javoblari alohida.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { yangiBaza, py } from "./fixture.js";
import * as ma from "../src/miniapp.js";
import * as plan from "../src/plan.js";
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
from core import entries as en, xabar as xb, plan, mahsulot as mh
F = en.odam_qosh(db, "Fayzulloxon")
O = en.odam_qosh(db, "Otabek")
B = en.odam_qosh(db, "Behruz")
db.apply("odam", "UPDATE", {"tg_chat": 111}, F)
db.apply("odam", "UPDATE", {"tg_chat": 222}, O)
db.apply("odam", "UPDATE", {"tg_chat": 333}, B)
xb.sozlama_qoy(db, token="123456:SINOV-token", guruh="-1", yoqilgan=True, kunlik_vaqt="08:00")
bz = db.skalyar("SELECT id FROM turi WHERE nom='Bozorlik'")
trn = db.skalyar("SELECT id FROM turi WHERE nom='Transport'")
db.apply("turi", "UPDATE", {"rasm": "food_03.png"}, bz)
mv = mh.kategoriya_qosh(db, "Mevalar", bz, rasm=[b for b in mh.bosh_belgilar(db) if b != "food_03.png"][0])
non = plan.item_qosh(db, "Non", 5000, bz)
en.kirim_qosh(db, "2026-10-01", F, 5_000_000, "Oylik")
en.rasxod_qosh(db, "2026-10-04", "Non, sut", 120_000, F, turi_id=bz)
en.rasxod_qosh(db, "2026-10-05", "Olma", 90_000, O, turi_id=mv)
en.rasxod_qosh(db, "2026-10-05", "Taksi", 15_000, F, umumiymi=False, turi_id=trn)
en.rasxod_qosh(db, "2026-10-06", "Kitob", 70_000, O, turi_id=bz, kim_uchun=F)
en.rasxod_qosh(db, "2026-09-15", "Bozor", 600_000, F, turi_id=bz)
plan.budjet_qoy(db, trn, "*", 100_000)
plan.reja_saqla(db, "2026-09", 2_000_000, {bz: 300_000})
plan.reja_yozuv_saqla(db, "2026-09-30", "Sentabr bozor", mv, 100_000, [{"item_id": non, "miqdor": 1, "summa": 100_000}])
plan.reja_yozuv_saqla(db, "2026-09-10", "Darslik", bz, 40_000, umumiymi=False, odam_id=B)
`;

// Amallar: [tur, maydonlar]. `ref: n` — n-amal qaytargan yozuv id'si.
// Kategoriya va mahsulot — nomi bilan (id'lar ikki tomonda bir xil, lekin aniqroq).
const AMALLAR = [
  ["yozuv", { sana: "2026-10-05", turi: "Mevalar", nom: "Haftalik bozorlik", summa: 25000, doira: "umumiy",
    mahsulotlar: [{ item: "Non", miqdor: 2, summa: 10000 }, { nom: "Yangi olma", miqdor: 3, summa: 10000 },
      { nom: "YANGI olma", miqdor: 1, summa: 5000 }] }],
  ["yozuv", { sana: "2026-10-31", turi: "Bozorlik", nom: "Kitob", summa: 50000, doira: "shaxsiy" }],
  ["yozuv", { sana: "2026-10-07", turi: "Bozorlik", nom: "Xato", summa: 30000, doira: "umumiy",
    mahsulotlar: [{ item: "Non", miqdor: 1, summa: 5000 }] }],
  ["yozuv", { sana: "2026-10-07", turi: "Bozorlik", nom: "  ", summa: 30000, doira: "umumiy" }],
  ["yozuv", { sana: "2026-10-07", turi: null, nom: "X", summa: 30000, doira: "umumiy" }],
  ["yozuv", { sana: "2026-10-07", turi: "Bozorlik", nom: "X", summa: 0, doira: "umumiy" }],
  ["yozuv", { sana: "2026-10-07", turi: "Bozorlik", nom: "X", summa: 9000, doira: "umumiy",
    mahsulotlar: [{ nom: "Tuxum", miqdor: -1, summa: 9000 }] }],
  ["tahrir", { ref: 0, sana: "2026-10-06", turi: "Mevalar", nom: "Haftalik bozorlik", summa: 20000, doira: "umumiy",
    mahsulotlar: [{ item: "Non", miqdor: 2, summa: 10000 }, { nom: "Yangi olma", miqdor: 2, summa: 10000 }] }],
  ["tahrir", { ref: 0, sana: "2026-10-06", turi: "Mevalar", nom: "Haftalik bozorlik (2)", summa: 20000, doira: "umumiy",
    mahsulotlar: [{ item: "Non", miqdor: 2, summa: 10000 }, { item: "Yangi olma", miqdor: 2, summa: 10000 }] }],
  ["nusxa", { ref: 1 }],
  ["nusxa", { ref: 0 }],
  ["limitlar", { oy: "2026-10", umumiy: 3_000_000, limitlar: { Bozorlik: 400_000, Transport: 0 } }],
  ["limitlar", { oy: "2026-10", umumiy: 0, limitlar: { Bozorlik: 400_000, Transport: 150_000 } }],
  ["limit_ochir", { oy: "2026-10", turi: "Bozorlik" }],
  ["ochir", { ref: 10 }],
  ["kochir", { oy: "2026-11" }],
  ["kochir_plan", { dan: "2026-09", ga: "2026-12" }],
  ["tahrir", { ref: 1, sana: "2026-10-30", turi: "Bozorlik", nom: "Kitob", summa: 50000, doira: "umumiy" }],
];

const PY_AMALLAR = String.raw`
import json
from core import plan
AM = json.load(open(r"__FAYL__", encoding="utf-8"))
F = db.skalyar("SELECT id FROM odam WHERE tg_chat=111")
turi = lambda n: None if n is None else db.skalyar("SELECT id FROM turi WHERE nom=?", n)
item = lambda n: db.skalyar("SELECT id FROM item WHERE nom=? AND ochirilgan=0 ORDER BY id", n)
def mahs(a):
    return [{"item_id": item(m["item"]) if "item" in m else None, "nom": m.get("nom", ""),
             "miqdor": m["miqdor"], "summa": m["summa"]} for m in a.get("mahsulotlar", [])]
natija = []
for tur, a in AM:
    try:
        if tur in ("yozuv", "tahrir"):
            qid = natija[a["ref"]] if tur == "tahrir" else None
            r = plan.reja_yozuv_saqla(db, a["sana"], a["nom"], turi(a["turi"]), a["summa"], mahs(a), qid,
                                      umumiymi=a["doira"] == "umumiy",
                                      odam_id=F if a["doira"] == "shaxsiy" else None)
        elif tur == "nusxa":
            r = plan.reja_yozuv_nusxa(db, natija[a["ref"]])
        elif tur == "ochir":
            plan.reja_yozuv_ochir(db, natija[a["ref"]]); r = "ok"
        elif tur == "limitlar":
            plan.reja_saqla(db, a["oy"], a["umumiy"] or None, {turi(k): v for k, v in a["limitlar"].items()}); r = "ok"
        elif tur == "limit_ochir":
            plan.budjet_qoy(db, turi(a["turi"]), a["oy"], 0); r = "ok"
        elif tur == "kochir":
            r = "ok" if plan.reja_kochir(db, plan.oy_sur(a["oy"], -1), a["oy"]) else "yo'q"
        elif tur == "kochir_plan":
            r = "ok" if plan.reja_kochir(db, a["dan"], a["ga"]) else "yo'q"
        natija.append(r)
    except ValueError as e:
        natija.append("XATO " + str(e))
holat = {}
for oy in ("2026-09", "2026-10", "2026-11", "2026-12"):
    h = {"bormi": plan.reja_bormi(db, oy), "rf": {}, "kunlar": {}, "limit": plan.reja_kategoriyalari(db, oy)}
    for d, oid in (("umumiy", None), ("shaxsiy", F)):
        h["rf"][d] = plan.reja_va_fakt(db, oy, oid)
        h["kunlar"][d] = {str(t): plan.kategoriya_kunlari(db, oy, t, oid) for t in (turi("Bozorlik"), turi("Transport"))}
    holat[oy] = h
print(json.dumps({"natija": natija, "holat": holat}, ensure_ascii=False, default=str))
`;

const BOSH_SQL = "SELECT (SELECT COALESCE(MAX(id),0) FROM ozgarishlar) oz";
const JADVALLAR = ["reja", "reja_qator", "reja_mahsulot", "budjet", "item"];
const FK = { reja_id: "reja", qator_id: "reja_qator", item_id: "item" };

/** Bazadagi yangi qatorlar va jurnal — id'larsiz (Python juft, Worker toq id beradi). */
function holatOl(fayl, chegara) {
  const d = new DatabaseSync(fayl);
  try {
    const xarita = {};
    const jadval = {};
    for (const t of JADVALLAR) {
      const qatorlar = d.prepare(`SELECT * FROM ${t} ORDER BY id`).all().map((r) => ({ ...r }));
      xarita[t] = new Map();
      let k = 0;
      for (const r of qatorlar) if (r.id > chegara[t]) xarita[t].set(r.id, `${t}#${k++}`);
      jadval[t] = qatorlar;
    }
    const nomla = (t, id) => (id == null ? null : xarita[t]?.get(id) ?? id);
    const tekis = (t, r) => {
      if (r == null) return null;
      const o = { ...r };
      delete o.yaratilgan;
      o.id = nomla(t, o.id);
      for (const [u, jt] of Object.entries(FK)) if (u in o) o[u] = nomla(jt, o[u]);
      if (typeof o.miqdor === "number") o.miqdor = Number(o.miqdor);
      return o;
    };
    const natija = {};
    for (const t of JADVALLAR) natija[t] = jadval[t].map((r) => tekis(t, r));
    const jurnal = d.prepare("SELECT guruh_id, tavsif, jadval, qator_id, amal, oldin, keyin FROM ozgarishlar" +
      " WHERE id>? ORDER BY id").all(chegara.oz).map((r) => ({ ...r }));
    const guruhlar = [...new Set(jurnal.map((r) => r.guruh_id))];
    const qoshilgan = new Set();
    natija.jurnal = jurnal.map((r) => {
      const kalit = `${r.guruh_id}|${r.jadval}|${r.qator_id}`;
      // Shu amalda INSERT qilingan qatorning keyingi UPDATE'i: Python «oldin» ni
      // amal ichidagi holatdan oladi, Worker navbatli — bazadagi (yo'q) holatdan.
      const ichki = r.amal !== "INSERT" && qoshilgan.has(kalit);
      if (r.amal === "INSERT") qoshilgan.add(kalit);
      return {
        guruh: guruhlar.indexOf(r.guruh_id), tavsif: r.tavsif, jadval: r.jadval, amal: r.amal,
        qator: nomla(r.jadval, r.qator_id),
        oldin: ichki ? "(amal ichida)" : tekis(r.jadval, r.oldin && JSON.parse(r.oldin)),
        keyin: tekis(r.jadval, r.keyin && JSON.parse(r.keyin)),
      };
    });
    return natija;
  } finally { d.close(); }
}

function chegaraOl(fayl) {
  const d = new DatabaseSync(fayl);
  try {
    const c = { oz: d.prepare(BOSH_SQL).get().oz };
    for (const t of JADVALLAR) c[t] = d.prepare(`SELECT COALESCE(MAX(id),0) m FROM ${t}`).get().m;
    return c;
  } finally { d.close(); }
}

function qur() {
  const b = yangiBaza(SEED);
  soatniQoy(new Date("2026-10-04T07:00:00Z"));
  b.sor = (yol, { user = { id: 111 }, tana } = {}) => ma.ishla(new Request(`https://w.example${yol}`, {
    method: tana ? "POST" : "GET",
    headers: { authorization: "tma " + imzola(user), ...(tana ? { "content-type": "application/json" } : {}) },
    body: tana ? JSON.stringify(tana) : undefined,
  }), {}, b.db);
  b.json = async (yol, o) => { const r = await b.sor(yol, o); return [r.status, await r.json()]; };
  b.turi = async (n) => (n == null ? null : (await b.db.q1("SELECT id FROM turi WHERE nom=?", n)).id);
  b.item = async (n) => (await b.db.q1("SELECT id FROM item WHERE nom=? AND ochirilgan=0 ORDER BY id", n)).id;
  return b;
}

async function jsAmallar(b) {
  const natija = [];
  for (const [tur, a] of AMALLAR) {
    let r;
    if (tur === "yozuv" || tur === "tahrir") {
      const mahsulotlar = [];
      for (const m of a.mahsulotlar || []) {
        mahsulotlar.push({ item_id: m.item ? await b.item(m.item) : null, nom: m.nom || "", miqdor: m.miqdor, summa: m.summa });
      }
      const tana = { sana: a.sana, nom: a.nom, turi_id: await b.turi(a.turi), summa: a.summa, doira: a.doira, mahsulotlar };
      r = await b.json(tur === "tahrir" ? `/app/api/reja/yozuv/${natija[a.ref]}` : "/app/api/reja/yozuv", { tana });
      natija.push(r[1].ok ? r[1].id : "XATO " + r[1].xato);
    } else if (tur === "nusxa") {
      r = await b.json(`/app/api/reja/yozuv/${natija[a.ref]}/nusxa`, { tana: {} });
      natija.push(r[1].ok ? r[1].id : "XATO " + r[1].xato);
    } else if (tur === "ochir") {
      r = await b.json(`/app/api/reja/yozuv/${natija[a.ref]}/ochir`, { tana: {} });
      natija.push(r[1].ok ? "ok" : "XATO " + r[1].xato);
    } else if (tur === "limitlar") {
      const limitlar = {};
      for (const [k, v] of Object.entries(a.limitlar)) limitlar[await b.turi(k)] = v;
      r = await b.json("/app/api/reja/limitlar", { tana: { oy: a.oy, umumiy: a.umumiy, limitlar } });
      natija.push(r[1].ok ? "ok" : "XATO " + r[1].xato);
    } else if (tur === "limit_ochir") {
      r = await b.json("/app/api/reja/limit/ochir", { tana: { oy: a.oy, turi_id: await b.turi(a.turi) } });
      natija.push(r[1].ok ? "ok" : "XATO " + r[1].xato);
    } else if (tur === "kochir") {
      r = await b.json("/app/api/reja/kochir", { tana: { oy: a.oy } });
      natija.push(r[1].ok ? "ok" : "XATO " + r[1].xato);
    } else if (tur === "kochir_plan") {
      natija.push((await plan.reja_kochir(b.db, a.dan, a.ga)) ? "ok" : "yo'q");
      continue;
    }
    assert.equal(r[0], r[1].ok ? 200 : 400, `${tur} ${JSON.stringify(a)} → ${JSON.stringify(r[1])}`);
  }
  return natija;
}

let _p = null;
/** Python haqiqati: alohida nusxa bazada amallar → natija, jadvallar, holat. */
function python() {
  if (_p) return _p;
  const b = yangiBaza(SEED);
  const papka = mkdtempSync(join(tmpdir(), "fuy-reja-"));
  copyFileSync(join(b.papka, "t.db"), join(papka, "t.db"));
  const chegara = chegaraOl(join(papka, "t.db"));
  const fayl = join(papka, "amallar.json");
  writeFileSync(fayl, JSON.stringify(AMALLAR));
  const chiq = py(papka, PY_AMALLAR.replace("__FAYL__", fayl)).trim().split(/\r?\n/);
  const j = JSON.parse(chiq[chiq.length - 1]);
  _p = { ...j, chegara, baza: holatOl(join(papka, "t.db"), chegara) };
  return _p;
}

test("amallar ketma-ketligi: natija, jadvallar va jurnal Python bilan AYNAN teng", async () => {
  const p = python();
  const b = qur();
  const chegara = chegaraOl(join(b.papka, "t.db"));
  assert.deepEqual(chegara, p.chegara, "ikki baza bir xil holatdan boshlansin");
  const natija = await jsAmallar(b);
  const idsiz = (x) => (typeof x === "number" ? "id" : x);
  assert.deepEqual(natija.map(idsiz), p.natija.map(idsiz));
  // Xato matnlari desktopniki — ssenariy haqiqatan ularni yuradi.
  assert.ok(p.natija.some((x) => String(x).includes("yig'indisiga teng emas")));
  assert.ok(p.natija.some((x) => String(x).includes("Sabab yozilmagan")));
  assert.ok(p.natija.some((x) => String(x).includes("Kategoriya tanlanmagan")));
  assert.ok(p.natija.some((x) => String(x) === "XATO Summa kiritilmagan."));
  assert.ok(p.natija.some((x) => String(x).includes("miqdori musbat")));
  const j = holatOl(join(b.papka, "t.db"), chegara);
  for (const t of JADVALLAR) assert.deepEqual(j[t], p.baza[t], `jadval ${t}`);
  assert.deepEqual(j.jurnal, p.baza.jurnal);
  // Har foydalanuvchi amali — bitta undo guruhi (kochir_plan ham bitta).
  const yozgan = p.natija.filter((x) => !String(x).startsWith("XATO")).length;
  assert.equal(new Set(j.jurnal.map((r) => r.guruh)).size, yozgan);
  // «YANGI olma» bitta amaldagi «Yangi olma» katalog mahsulotiga bog'landi (bitta item).
  assert.equal(j.item.filter((r) => /^yangi olma$/i.test(r.nom)).length, 1);
});

test("«Reja va fakt», toifa kunlari va limit oynasi — Python bilan parity", async () => {
  const p = python();
  const b = qur();
  await jsAmallar(b);
  const kalitsiz = (x, ...k) => JSON.parse(JSON.stringify(x, (key, v) => (k.includes(key) ? undefined : v)));
  for (const [oy, h] of Object.entries(p.holat)) {
    assert.equal(await plan.reja_bormi(b.db, oy), h.bormi, `bormi ${oy}`);
    const [, lim] = await b.json(`/app/api/reja/limitlar?oy=${oy}`);
    assert.deepEqual(kalitsiz(lim.kategoriyalar, "belgi_fayl"), h.limit, `limit ${oy}`);
    for (const d of ["umumiy", "shaxsiy"]) {
      const [s, r] = await b.json(`/app/api/reja?oy=${oy}&doira=${d}`);
      assert.equal(s, 200);
      const kut = { ...h.rf[d], odam_id: d === "umumiy" ? null : r.odam.id };
      assert.deepEqual(kalitsiz(r.rf, "belgi_fayl"), kut, `rf ${oy} ${d}`);
      for (const [tid, kk] of Object.entries(h.kunlar[d])) {
        const [, k] = await b.json(`/app/api/reja/kategoriya?oy=${oy}&turi_id=${tid}&doira=${d}`);
        assert.deepEqual({ reja: k.reja, fakt: k.fakt, qolgan: k.qolgan, limit: k.limit,
          kunlar: kalitsiz(k.kunlar, "holat") }, kk, `kunlar ${oy} ${d} ${tid}`);
        assert.equal(k.yozuvlar.reduce((s, y) => s + y.summa, 0) + k.limit, k.reja);
      }
    }
  }
  // Ssenariy ko'chirishni haqiqatan yurgan: noyabrda 31 → 30-kunga qisilgan yozuv bor.
  const nov = await plan.reja_yozuvlari(b.db, "2026-11");
  assert.ok(nov.some((y) => y.sana === "2026-11-30"));
});

test("ruxsat va xatolar: begona shaxsiy 403, oy/doira 400, ko'chirish takrori rad", async () => {
  const b = qur();
  const bz = await b.turi("Bozorlik");
  const [, y] = await b.json("/app/api/reja/yozuv", { tana: { sana: "2026-10-10", turi_id: bz, nom: "Shaxsiy", summa: 1000, doira: "shaxsiy" } });
  assert.ok(y.ok);
  // Otabek Fayzulloxonning shaxsiy rejasiga tega olmaydi; umumiy rejaga — tega oladi.
  for (const yol of [`/app/api/reja/yozuv/${y.id}`, `/app/api/reja/yozuv/${y.id}/ochir`, `/app/api/reja/yozuv/${y.id}/nusxa`]) {
    const r = await b.sor(yol, { user: { id: 222 }, tana: { sana: "2026-10-10", turi_id: bz, nom: "x", summa: 1, doira: "umumiy" } });
    assert.equal(r.status, 403, yol);
  }
  assert.equal((await b.sor(`/app/api/reja/yozuv/${y.id}`, { user: { id: 222 } })).status, 403);
  const [, u] = await b.json("/app/api/reja/yozuv", { tana: { sana: "2026-10-10", turi_id: bz, nom: "Umumiy", summa: 2000, doira: "umumiy" } });
  const [s2, t] = await b.json(`/app/api/reja/yozuv/${u.id}`, { user: { id: 222 } });
  assert.equal(s2, 200);
  assert.deepEqual([t.yozuv.nom, t.yozuv.ildiz, t.yozuv.umumiymi], ["Umumiy", bz, 1]);
  // Shaxsiy doira — har kim faqat o'zini ko'radi.
  const [, sh] = await b.json("/app/api/reja?oy=2026-10&doira=shaxsiy", { user: { id: 222 } });
  assert.equal(sh.rf.reja, 0);
  const [, shF] = await b.json("/app/api/reja?oy=2026-10&doira=shaxsiy");
  assert.equal(shF.rf.reja, 1000);

  assert.equal((await b.sor("/app/api/reja?oy=2026-13")).status, 400);
  assert.equal((await b.sor("/app/api/reja?doira=boshqa")).status, 400);
  assert.equal((await b.sor("/app/api/reja/kategoriya?oy=2026-10")).status, 400);
  assert.equal((await b.sor("/app/api/reja/kategoriya?oy=2026-10&turi_id=99999")).status, 404);
  assert.equal((await b.sor("/app/api/reja/yozuv/99999")).status, 404);
  assert.equal((await b.sor("/app/api/reja/boshqa")).status, 404);
  const [s3, k] = await b.json("/app/api/reja/kochir", { tana: { oy: "2026-10" } });
  assert.deepEqual([s3, k.xato], [400, "Bu oyda reja allaqachon bor."]);
  // Avgustda faqat «har oy» ('*') limiti — o'z rejasi yo'q, ko'chirish ochiq.
  const [, av] = await b.json("/app/api/reja?oy=2026-08");
  assert.deepEqual([av.bu_oy_bor, av.kochir_mumkin], [true, true]);
  const [, ok] = await b.json("/app/api/reja?oy=2026-10");
  assert.equal(ok.kochir_mumkin, false);
  await b.db.exec("DELETE FROM budjet WHERE oy='*'");
  const [s4, k2] = await b.json("/app/api/reja/kochir", { tana: { oy: "2026-08" } });
  assert.deepEqual([s4, k2.xato], [400, "O'tgan oy uchun reja yo'q."]);
  const [s5, l] = await b.json("/app/api/reja/limitlar", { tana: { oy: "2026-10", umumiy: "1.5", limitlar: {} } });
  assert.equal(s5, 400, JSON.stringify(l));
  const [s6] = await b.json("/app/api/reja/limitlar", { tana: { oy: "2026-10", umumiy: 0, limitlar: { 99999: 5 } } });
  assert.equal(s6, 400);
  const [s7, l7] = await b.json("/app/api/reja/limit/ochir", { tana: { oy: "2026-10", turi_id: bz } });
  assert.deepEqual([s7, l7.xato], [400, "Bu kategoriyada limit yo'q."]);
  const [s8, f] = await b.json("/app/api/reja/forma");
  assert.equal(s8, 200);
  const bzK = f.kategoriyalar.find((x) => x.id === bz);
  assert.deepEqual([bzK.belgi_fayl, bzK.ichki.map((x) => x.nom)], ["food_03.svg", ["Mevalar"]]);
  assert.ok(f.mahsulotlar.some((m) => m.nom === "Non" && m.narx === 5000 && m.turi_id === bz));
  // Imzosiz — 401 (miniapp.js umumiy ruxsati).
  const r401 = await ma.ishla(new Request("https://w.example/app/api/reja", { headers: { authorization: "tma hash=x" } }), {}, b.db);
  assert.equal(r401.status, 401);
});
