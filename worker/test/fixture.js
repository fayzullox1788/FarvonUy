// Test bazasi: Python `db.Db()` bilan yaratiladi (sxema + migratsiya + ekish
// aynan desktopdagidek), keyin JS uni node:sqlite orqali ochadi.
// `pyKod` — shu bazada qo'shimcha Python (ma'lumot ekish) ishlatish uchun.
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { D1Shim } from "./d1shim.js";
import { Db } from "../src/db.js";

export const SRC = resolve(import.meta.dirname, "../../src");

/** Python'ni FARVONUY_DATA=papka bilan ishga tushiradi; `db` o'zgaruvchisi tayyor. */
export function py(papka, kod) {
  const skript = join(papka, "_f.py");
  writeFileSync(skript, `import sys\nsys.path.insert(0, r"${SRC}")\nimport db as dbm\n` +
    `db = dbm.Db(r"${join(papka, "t.db")}", zaxirasiz=True)\n${kod}\ndb.yop()\n`);
  return execFileSync("py", ["-3.14", "-X", "utf8", skript], {
    env: { ...process.env, FARVONUY_DATA: papka, PYTHONIOENCODING: "utf-8" }, encoding: "utf8",
  });
}

/** Yangi test bazasi. pyKod — ixtiyoriy ekish. → {db, d1, papka} */
export function yangiBaza(pyKod = "") {
  const papka = mkdtempSync(join(tmpdir(), "fuy-"));
  py(papka, pyKod);
  const d1 = new D1Shim(join(papka, "t.db"));
  return { db: new Db(d1), d1, papka };
}
