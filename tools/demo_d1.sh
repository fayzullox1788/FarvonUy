#!/usr/bin/env bash
# Mini App demo rejimi uchun ALOHIDA D1 baza (farvonuy_demo): yaratadi
# (bo'lmasa), soxta ma'lumot bilan QAYTA to'ldiradi va deploy qiladi.
# Haqiqiy `farvonuy` bazasiga tegmaydi. Qayta ishga tushirish xavfsiz —
# sanalar bugunga yangilanadi.
#   bash tools/demo_d1.sh
set -euo pipefail
ILDIZ="$(cd "$(dirname "$0")/.." && pwd)"
# Windows Python /c/... yo'lni tushunmaydi — satr ichidagi yo'llar uchun C:/... ko'rinishi.
ILDIZ_W="$(cd "$ILDIZ" && pwd -W)"
cd "$ILDIZ/worker"
export PYTHONIOENCODING=utf-8

echo "== 1/4 Soxta baza (src/demo.py) va SQL eksport"
DEMO_DB=$(py -3.14 -c "import sys; sys.path.insert(0, r'$ILDIZ_W/src'); import demo, config; print(demo.qur(config.DEMO_PAPKA / 'd1.db'))")
rm -rf d1_demo
py -3.14 "$ILDIZ/tools/d1_eksport.py" --db "$DEMO_DB" --chiqish d1_demo | tail -2
# Eski jadvallarni tashlash (qayta to'ldirish uchun). Tartib MUHIM: ichida
# qatori bor ota jadval bolalaridan OLDIN tashlansa, D1 butun importni FK xatosi
# bilan orqaga qaytaradi. Shuning uchun viewlar, keyin jadvallar BOLALARIDAN
# boshlab (bog'lanishlar d1_demo/schema.sql dan).
py -3.14 - > d1_demo/drop.sql <<'PY'
import sqlite3
c = sqlite3.connect(":memory:")
c.executescript(open("d1_demo/schema.sql", encoding="utf-8").read())
print("PRAGMA defer_foreign_keys = true;")
for (v,) in c.execute("SELECT name FROM sqlite_master WHERE type='view'"):
    print(f'DROP VIEW IF EXISTS "{v}";')
jad = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
ota = {t: {r[2] for r in c.execute(f'PRAGMA foreign_key_list("{t}")')} for t in jad}
qoldi = set(jad)
while qoldi:
    bola = sorted(t for t in qoldi if not any(t in ota[x] and x != t for x in qoldi)) or sorted(qoldi)
    for t in bola:
        print(f'DROP TABLE IF EXISTS "{t}";')
    qoldi -= set(bola)
PY

echo "== 2/4 D1 baza: farvonuy_demo"
if ! grep -q '^binding = "DEMO_DB"' wrangler.toml; then
  ID=$(npx wrangler d1 list --json | py -3.14 -c "import json,sys; print(next((d['uuid'] for d in json.load(sys.stdin) if d['name']=='farvonuy_demo'), ''))")
  if [ -z "$ID" ]; then
    ID=$(npx wrangler d1 create farvonuy_demo 2>&1 | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
  fi
  [ -n "$ID" ] || { echo "D1 id topilmadi"; exit 1; }
  py -3.14 - "$ID" <<'PY'
import re, sys
from pathlib import Path
p = Path("wrangler.toml"); s = p.read_text(encoding="utf-8")
s = s.replace('# [[d1_databases]]\n# binding = "DEMO_DB"', '[[d1_databases]]\nbinding = "DEMO_DB"')
s = s.replace('# database_name = "farvonuy_demo"', 'database_name = "farvonuy_demo"')
s = s.replace('# database_id = ""', f'database_id = "{sys.argv[1]}"')
p.write_text(s, encoding="utf-8")
PY
  echo "wrangler.toml ga ulandi: $ID"
fi

echo "== 3/4 To'ldirish (eski demo ma'lumot o'chadi)"
npx wrangler d1 execute farvonuy_demo --remote --yes --file d1_demo/drop.sql | tail -1
npx wrangler d1 execute farvonuy_demo --remote --yes --file d1_demo/schema.sql | tail -1
for f in d1_demo/data*.sql; do
  npx wrangler d1 execute farvonuy_demo --remote --yes --file "$f" | tail -1
done

echo "== 4/4 Deploy"
npx wrangler deploy 2>&1 | tail -6
echo "TAYYOR — Mini App → Sozlamalar → «Demo rejim»"
