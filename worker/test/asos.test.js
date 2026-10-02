import { test } from "node:test";
import assert from "node:assert/strict";
import { yangiBaza } from "./fixture.js";
import * as money from "../src/money.js";
import * as vaqt from "../src/vaqt.js";

test("money.bol yig'indisi aniq va Python bilan bir xil", () => {
  const u = money.bol_teng(1559000, [1, 2, 3]);
  assert.deepEqual(u.map((x) => x.summa), [519667, 519667, 519666]);
  assert.equal(money.fmt(1559000), "1\u00a0559\u00a0000");
});

test("vaqt: weekday/toordinal", () => {
  assert.equal(vaqt.weekday("2026-10-05"), 0); // dushanba
  assert.equal(vaqt.toordinal("2026-10-02"), 739891);
});

test("Amal: toq id, jurnal, atomik batch", async () => {
  const { db } = yangiBaza(`from core import entries\nentries.odam_qosh(db, "Ali")\nentries.odam_qosh(db, "Vali")`);
  const a = db.amal("sinov");
  const id1 = await a.apply("menyu", "INSERT", { nom: "Osh" });
  const id2 = await a.apply("menyu", "INSERT", { nom: "Sho'rva" });
  assert.equal(id1 % 2, 1); assert.equal(id2, id1 + 2);
  await a.commit();
  const oz = await db.q("SELECT * FROM ozgarishlar WHERE jadval='menyu' AND guruh_id=?", a.guruh);
  assert.equal(oz.length, 2);
  assert.equal(JSON.parse(oz[0].keyin).nom, "Osh");
  assert.ok(oz.every((r) => r.id % 2 === 1));
  await db.apply("menyu", "DELETE", {}, id1);
  assert.equal((await db.q1("SELECT ochirilgan FROM menyu WHERE id=?", id1)).ochirilgan, 1);
});
