#!/usr/bin/env bash
# Darsning xonasi va o'qituvchisi (2026-10-12): D1 ga `vazifa.xona` va
# `vazifa.oqituvchi` ustunlari (farvonuy + farvonuy_demo) → deploy.
# Desktop sinxronidan OLDIN ishga tushiring. Qayta ishga tushirish xavfsiz
# (ustun bor bo'lsa o'tkazib yuboriladi).
#   bash tools/dars_xona_yoq.sh
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)/worker"
export PYTHONIOENCODING=utf-8

ustun_qosh() {  # $1 = baza, $2 = ustun
  local BOR
  BOR=$(npx wrangler d1 execute "$1" --remote --json \
    --command "SELECT (SELECT count(*)>0 FROM pragma_table_info('vazifa')) j, (SELECT count(*) FROM pragma_table_info('vazifa') WHERE name='$2') n" \
    | py -3.14 -c "import json,sys; r=json.load(sys.stdin)[0]['results'][0]; print(f\"{r['j']}{r['n']}\")")
  case "$BOR" in
    10) npx wrangler d1 execute "$1" --remote --command "ALTER TABLE vazifa ADD COLUMN $2 TEXT" | tail -2 ;;
    11) echo "$1: vazifa.$2 bor" ;;
    *)  echo "$1: vazifa jadvali yo'q — o'tkazildi" ;;
  esac
}

echo "== 1/3 D1 farvonuy: vazifa.xona, vazifa.oqituvchi"
ustun_qosh farvonuy xona
ustun_qosh farvonuy oqituvchi

echo "== 2/3 D1 farvonuy_demo: vazifa.xona, vazifa.oqituvchi"
ustun_qosh farvonuy_demo xona
ustun_qosh farvonuy_demo oqituvchi

echo "== 3/3 Deploy"
npx wrangler deploy 2>&1 | tail -6
echo "TAYYOR"
