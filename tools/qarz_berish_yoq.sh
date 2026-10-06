#!/usr/bin/env bash
# Tashqariga qarz berish (2026-10-06): D1 ga `tashqi_berilgan` + `tashqi_qaytim`
# jadvallari va yangi `v_balans` (berilgan qarz naqd'dan chiqadi) → deploy
# (Mini App'dagi 24 soatlik vaqt tanlagichi ham shu deploy bilan chiqadi).
# Desktop sinxronidan OLDIN ishga tushiring. Qayta ishga tushirish xavfsiz.
#   bash tools/qarz_berish_yoq.sh
set -euo pipefail
ILDIZ="$(cd "$(dirname "$0")/.." && pwd)"
ILDIZ_W="$(cd "$ILDIZ" && pwd -W)"
cd "$ILDIZ/worker"
export PYTHONIOENCODING=utf-8

echo "== 1/3 SQL tayyorlash (src/schema.sql dan)"
py -3.14 - > /tmp/qarz_berish.sql <<PY
import re
s = open(r"$ILDIZ_W/src/schema.sql", encoding="utf-8").read()
out = []
for jad in ("tashqi_berilgan", "tashqi_qaytim"):
    m = re.search(r"CREATE TABLE IF NOT EXISTS %s \(.*?\n\);" % jad, s, re.S)
    out.append(m.group(0))
out.append("CREATE INDEX IF NOT EXISTS ix_tashqi_qaytim ON tashqi_qaytim(berilgan_id);")
m = re.search(r"DROP VIEW IF EXISTS v_balans;.*?;\n(?=\n)", s, re.S)
v = m.group(0)
# SQL izohlari D1 bitta-ifoda bo'lishida xalaqit bermasin.
v = "\n".join(l for l in v.splitlines() if not l.strip().startswith("--"))
out.append(v)
print("\n".join(out))
PY
grep -c "tashqi_haq" /tmp/qarz_berish.sql >/dev/null

echo "== 2/3 D1: jadvallar + v_balans"
npx wrangler d1 execute farvonuy --remote --file /tmp/qarz_berish.sql | tail -3

echo "== 3/3 Deploy"
npx wrangler deploy 2>&1 | tail -6
echo "TAYYOR"
