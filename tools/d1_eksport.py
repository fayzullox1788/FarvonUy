"""Desktop SQLite bazasini Cloudflare D1 ga ko'chirish uchun SQL fayllar.

    py -3.14 tools/d1_eksport.py                 # jonli baza (faqat o'qish)
    py -3.14 tools/d1_eksport.py --db boshqa.db --chiqish papka --rasmlar

Natija (`worker/d1/`):
    schema.sql      — jadvallar, indekslar, viewlar (D1 uchun moslangan)
    data.sql        — barcha qatorlar (katta bo'lsa data-01.sql, data-02.sql …)
    rasm.sql        — `--rasmlar` bilan: mahsulot rasmlari `rasm` jadvaliga

Yuklash (BO'SH D1 bazaga, tartib bilan):
    npx wrangler d1 execute farvonuy --remote --file d1/schema.sql
    npx wrangler d1 execute farvonuy --remote --file d1/data.sql
    npx wrangler d1 execute farvonuy --remote --file d1/rasm.sql

Jonli baza `?mode=ro` bilan ochiladi — bu skript unga HECH NARSA yozmaydi.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
DATA_PAPKA = Path(os.environ.get("LOCALAPPDATA", "")) / "FarvonUy"
JONLI_DB = DATA_PAPKA / "farvonuy.db"
RASM_PAPKA = DATA_PAPKA / "mahsulot_rasm"

# D1: bitta SQL ifoda 100 KB dan oshmasin. Zaxira bilan.
IFODA_CHEGARA = 90_000
# Bitta fayl (D1 --file importi bir necha MB ni yaxshi ko'taradi).
FAYL_CHEGARA = 3_000_000
RASM_CHEGARA = 900 * 1024
RASM_NOM = re.compile(r"^\d+-[0-9a-f]{16}\.(jpg|jpeg|png|webp|bmp|gif)$")

# Faqat desktopda turadigan ustunlar (D1 ga ko'chmaydi).
DESKTOP_USTUNLAR = {"ozgarishlar": {"sinx"}}

# Botning har daqiqalik so'rovlari uchun qo'shimcha indekslar.
QOSHIMCHA_INDEKSLAR = [
    ("ix_rasxod_yaratilgan", "rasxod", "yaratilgan"),
    ("ix_vazifa_sana", "vazifa", "sana"),
    ("ix_vazifa_manba", "vazifa", "manba"),
]

LOCALTIME = re.compile(r"datetime\(\s*'now'\s*,\s*'localtime'\s*\)", re.I)


# ─────────────────────────────────────────────────────────── SQL matn

def _izohsiz(sql: str) -> str:
    """`--` va `/* */` izohlarini olib tashlaydi (satr literali ichidagisiga tegmaydi).

    wrangler faylni ifodalarga o'zi bo'ladi; izohdagi apostrof («yo'q»)
    uni chalg'itmasligi uchun izohlar umuman qoldirilmaydi.
    """
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c in "'\"`[":
            yop = "]" if c == "[" else c
            j = i + 1
            while j < n:
                if sql[j] == yop:
                    if yop != "]" and j + 1 < n and sql[j + 1] == yop:
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i:j + 1])
            i = j + 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    matn = "".join(out)
    # Bo'sh qatorlar va qator oxiridagi bo'shliqlar.
    return "\n".join(q.rstrip() for q in matn.splitlines() if q.strip())


def _yuqori_vergul(body: str) -> list[str]:
    """Qavs ichidagi ro'yxatni yuqori darajadagi vergullar bo'yicha bo'ladi."""
    qism, chuqur, bosh, i = [], 0, 0, 0
    while i < len(body):
        c = body[i]
        if c == "'":
            j = i + 1
            while j < len(body):
                if body[j] == "'" and not (j + 1 < len(body) and body[j + 1] == "'"):
                    break
                j += 2 if body[j] == "'" else 1
            i = j
        elif c == "(":
            chuqur += 1
        elif c == ")":
            chuqur -= 1
        elif c == "," and chuqur == 0:
            qism.append(body[bosh:i])
            bosh = i + 1
        i += 1
    qism.append(body[bosh:])
    return qism


def _ustun_olib_tashla(sql: str, ustunlar: set[str]) -> str:
    ochiq = sql.index("(")
    yopiq = sql.rindex(")")
    qismlar = _yuqori_vergul(sql[ochiq + 1:yopiq])
    qol = []
    for q in qismlar:
        birinchi = q.strip().split(None, 1)[0].strip('"`[]') if q.strip() else ""
        if birinchi.lower() in {u.lower() for u in ustunlar}:
            continue
        qol.append(q.rstrip())
    return sql[:ochiq + 1] + ",".join(qol) + "\n" + sql[yopiq:]


def _moslash(sql: str) -> str:
    sql = _izohsiz(sql)
    sql = LOCALTIME.sub("datetime('now','+5 hours')", sql)
    return sql


def _ifnotexists(sql: str, tur: str) -> str:
    """`CREATE TABLE x` → `CREATE TABLE IF NOT EXISTS x` (qayta ishga tushirsa ham xavfsiz)."""
    return re.sub(rf"^\s*CREATE\s+(UNIQUE\s+)?{tur}\s+(?!IF\s+NOT\s+EXISTS)",
                  lambda m: f"CREATE {m.group(1) or ''}{tur} IF NOT EXISTS ",
                  sql, count=1, flags=re.I)


def _q(nom: str) -> str:
    return '"' + nom.replace('"', '""') + '"'


def literal(v) -> str:
    """Python qiymati → SQLite literali."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v:
            return "NULL"
        if v in (float("inf"), float("-inf")):
            return "9e999" if v > 0 else "-9e999"
        r = repr(v)
        # 1.0 → "1.0" — REAL bo'lib qolishi uchun nuqta saqlanadi.
        return r
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "X'" + bytes(v).hex().upper() + "'"
    s = str(v)
    if "\x00" in s:
        # NUL baytli matn — literalda ifodalab bo'lmaydi, BLOB orqali.
        return "CAST(X'" + s.encode("utf-8").hex().upper() + "' AS TEXT)"
    return "'" + s.replace("'", "''") + "'"


# ─────────────────────────────────────────────────────────── tartib

def _fk_tartib(con: sqlite3.Connection, jadvallar: list[str]) -> list[str]:
    """Jadvallarni tashqi kalitlar bo'yicha tartiblaydi (ota avval)."""
    ota: dict[str, set[str]] = {}
    for t in jadvallar:
        ota[t] = {r[2] for r in con.execute(f"PRAGMA foreign_key_list({_q(t)})")
                  if r[2] != t and r[2] in jadvallar}
    natija, korilgan = [], set()

    def tashri(t, yol=()):
        if t in korilgan or t in yol:
            return
        for o in sorted(ota[t]):
            tashri(o, yol + (t,))
        korilgan.add(t)
        natija.append(t)

    for t in jadvallar:
        tashri(t)
    return natija


def _view_tartib(viewlar: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """View boshqa view'ga tayansa — u avval yaratiladi."""
    nomlar = {n for n, _ in viewlar}
    sqllar = dict(viewlar)
    kerak = {n: {m for m in nomlar if m != n and re.search(rf"\b{re.escape(m)}\b", sqllar[n])}
             for n in nomlar}
    natija, korilgan = [], set()

    def tashri(n, yol=()):
        if n in korilgan or n in yol:
            return
        for m in sorted(kerak[n]):
            tashri(m, yol + (n,))
        korilgan.add(n)
        natija.append((n, sqllar[n]))

    for n, _ in viewlar:
        tashri(n)
    return natija


# ─────────────────────────────────────────────────────────── eksport

def ochish(yol: Path) -> sqlite3.Connection:
    con = sqlite3.connect(yol.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def _ustunlar(con, jadval) -> list[str]:
    tashla = DESKTOP_USTUNLAR.get(jadval, set())
    return [r[1] for r in con.execute(f"PRAGMA table_info({_q(jadval)})") if r[1] not in tashla]


def schema_sql(con: sqlite3.Connection) -> tuple[str, list[str]]:
    obyektlar = con.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall()
    jadvallar = [n for t, n, _, _ in obyektlar if t == "table"]
    tartib = _fk_tartib(con, jadvallar)
    sql_of = {n: s for t, n, _, s in obyektlar}

    qator = ["-- Farovon Hayot → Cloudflare D1 sxemasi (tools/d1_eksport.py yaratgan).",
             "-- Toshkent vaqti: datetime('now','+5 hours') — yozgi vaqt yo'q.", ""]
    for t in tartib:
        s = sql_of[t]
        if t in DESKTOP_USTUNLAR:
            s = _ustun_olib_tashla(s, DESKTOP_USTUNLAR[t])
        qator.append(_ifnotexists(_moslash(s), "TABLE") + ";")
        qator.append("")
    qator.append("CREATE TABLE IF NOT EXISTS rasm(nom TEXT PRIMARY KEY, data BLOB);")
    qator.append("")

    indekslar = [(n, tb, s) for t, n, tb, s in obyektlar if t == "index"]
    bor_ustun = set()
    for n, tb, s in indekslar:
        qator.append(_ifnotexists(_moslash(s), "INDEX") + ";")
        cols = [r[2] for r in con.execute(f"PRAGMA index_info({_q(n)})")]
        if cols:
            bor_ustun.add((tb, cols[0]))
    bor_nom = {n for n, _, _ in indekslar}
    for n, tb, ustun in QOSHIMCHA_INDEKSLAR:
        if tb in jadvallar and ustun in _ustunlar(con, tb) and n not in bor_nom \
                and (tb, ustun) not in bor_ustun:
            qator.append(f"CREATE INDEX IF NOT EXISTS {n} ON {tb}({ustun});")
    qator.append("")

    viewlar = [(n, s) for t, n, _, s in obyektlar if t == "view"]
    for n, s in _view_tartib(viewlar):
        qator.append(f"DROP VIEW IF EXISTS {_q(n)};")
        qator.append(_moslash(s) + ";")
        qator.append("")

    for t, n, _, s in obyektlar:
        if t == "trigger":
            qator.append(_moslash(s) + ";")
    return "\n".join(qator) + "\n", tartib


def data_ifodalar(con: sqlite3.Connection, tartib: list[str]):
    """Har jadval uchun ko'p qatorli INSERT'lar (har biri < IFODA_CHEGARA)."""
    for t in tartib:
        if t == "sqlite_sequence":
            continue
        ustunlar = _ustunlar(con, t)
        bosh = f"INSERT INTO {_q(t)}({','.join(_q(u) for u in ustunlar)}) VALUES\n"
        tanla = ",".join(_q(u) for u in ustunlar)
        pk = [r[1] for r in con.execute(f"PRAGMA table_info({_q(t)})") if r[5]]
        tart = ",".join(_q(p) for p in pk) if pk else "rowid"
        qatorlar: list[str] = []
        hajm = len(bosh)
        for r in con.execute(f"SELECT {tanla} FROM {_q(t)} ORDER BY {tart}"):
            q = "(" + ",".join(literal(v) for v in r) + ")"
            if len(q) + len(bosh) + 2 > IFODA_CHEGARA:
                raise SystemExit(f"{t}: bitta qator {len(q)} bayt — D1 chegarasidan katta")
            if qatorlar and hajm + len(q) + 2 > IFODA_CHEGARA:
                yield t, bosh + ",\n".join(qatorlar) + ";"
                qatorlar, hajm = [], len(bosh)
            qatorlar.append(q)
            hajm += len(q) + 2
        if qatorlar:
            yield t, bosh + ",\n".join(qatorlar) + ";"


def rasm_ifodalar(con: sqlite3.Connection, papka: Path):
    """`item.rasm` dagi fayllar → `rasm` jadvali. Katta fayl bo'laklarga bo'linadi."""
    try:
        nomlar = sorted({r[0] for r in con.execute(
            "SELECT DISTINCT rasm FROM item WHERE rasm IS NOT NULL AND rasm<>''")})
    except sqlite3.OperationalError:
        nomlar = []
    # Hex — har bayt 2 belgi; ifoda ~90 KB dan oshmasin.
    bolak = (IFODA_CHEGARA - 300) // 2
    for nom in nomlar:
        if not RASM_NOM.match(nom):
            print(f"  ! rasm nomi andozaga mos emas, o'tkazildi: {nom}", file=sys.stderr)
            continue
        f = papka / nom
        if not f.is_file():
            print(f"  ! rasm fayli yo'q: {f}", file=sys.stderr)
            continue
        b = f.read_bytes()
        if len(b) > RASM_CHEGARA:
            print(f"  ! {nom}: {len(b) // 1024} KB > 900 KB, o'tkazildi", file=sys.stderr)
            continue
        n = literal(nom)
        yield (f"INSERT OR IGNORE INTO rasm(nom,data) VALUES({n},X'{b[:bolak].hex().upper()}');")
        for i in range(bolak, len(b), bolak):
            # Blob || blob matn qaytaradi; CAST AS BLOB baytlarni o'zgartirmaydi.
            yield (f"UPDATE rasm SET data=CAST(data || X'{b[i:i + bolak].hex().upper()}' AS BLOB) "
                   f"WHERE nom={n} AND length(data)={i};")


def _fayllarga(ifodalar: list[str], prefiks: str, papka: Path, sarlavha: str) -> list[Path]:
    """Ifodalarni FAYL_CHEGARA dan oshmaydigan fayllarga bo'ladi."""
    guruhlar: list[list[str]] = [[]]
    hajm = 0
    for s in ifodalar:
        b = len(s.encode("utf-8")) + 1
        if guruhlar[-1] and hajm + b > FAYL_CHEGARA:
            guruhlar.append([])
            hajm = 0
        guruhlar[-1].append(s)
        hajm += b
    for eski in papka.glob(f"{prefiks}*.sql"):
        if re.fullmatch(rf"{prefiks}(-\d+)?\.sql", eski.name):
            eski.unlink()
    yollar = []
    for i, g in enumerate(guruhlar, 1):
        nom = f"{prefiks}.sql" if len(guruhlar) == 1 else f"{prefiks}-{i:02d}.sql"
        yol = papka / nom
        yol.write_text(sarlavha + "\n".join(g) + "\n", encoding="utf-8", newline="\n")
        yollar.append(yol)
    return yollar


def eksport(db: Path, chiqish: Path, rasmlar: bool = False, rasm_papka: Path = RASM_PAPKA) -> dict:
    con = ochish(db)
    chiqish.mkdir(parents=True, exist_ok=True)
    schema, tartib = schema_sql(con)
    (chiqish / "schema.sql").write_text(schema, encoding="utf-8", newline="\n")

    sanoq: dict[str, int] = {}
    ifodalar = []
    for t, s in data_ifodalar(con, tartib):
        ifodalar.append(s)
    for t in tartib:
        if t != "sqlite_sequence":
            sanoq[t] = con.execute(f"SELECT COUNT(*) FROM {_q(t)}").fetchone()[0]
    # D1 tashqi kalitlarni majburiy tekshiradi; o'z-o'ziga ishora qiluvchi
    # qatorlar (turi.ota_id) uchun tekshiruv tranzaksiya oxiriga suriladi.
    sarlavha = "PRAGMA defer_foreign_keys = true;\n"
    data_fayllar = _fayllarga(ifodalar, "data", chiqish, sarlavha)

    rasm_fayllar = []
    if rasmlar:
        r = list(rasm_ifodalar(con, rasm_papka))
        rasm_fayllar = _fayllarga(r, "rasm", chiqish, "")

    oxirgi = 0
    try:
        oxirgi = con.execute("SELECT COALESCE(MAX(id),0) FROM ozgarishlar").fetchone()[0]
    except sqlite3.OperationalError:
        pass
    con.close()
    return {"schema": chiqish / "schema.sql", "data": data_fayllar, "rasm": rasm_fayllar,
            "sanoq": sanoq, "ozgarishlar_max": oxirgi}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--db", type=Path, default=JONLI_DB, help="SQLite baza (faqat o'qiladi)")
    p.add_argument("--chiqish", type=Path, default=ILDIZ / "worker" / "d1")
    p.add_argument("--rasmlar", action="store_true", help="mahsulot rasmlarini ham (rasm.sql)")
    p.add_argument("--rasm-papka", type=Path, default=RASM_PAPKA)
    a = p.parse_args(argv)
    if not a.db.is_file():
        print(f"Baza topilmadi: {a.db}", file=sys.stderr)
        return 1
    n = eksport(a.db, a.chiqish, a.rasmlar, a.rasm_papka)
    print(f"schema: {n['schema']}")
    for f in n["data"] + n["rasm"]:
        print(f"fayl:   {f}  ({f.stat().st_size // 1024} KB)")
    print(f"jadvallar: {len(n['sanoq'])}, qatorlar: {sum(n['sanoq'].values())}")
    print(f"ozgarishlar MAX(id) = {n['ozgarishlar_max']}  "
          f"(desktop sinxron kursori shundan boshlansin)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
