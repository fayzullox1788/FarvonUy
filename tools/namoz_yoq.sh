#!/usr/bin/env bash
# Namoz toifasi + vaqtni keyingi kunlarga o'zgartirish: D1 ustuni → deploy.
# Qayta ishga tushirish xavfsiz (ustun bor bo'lsa o'tkazib yuboriladi).
#   bash tools/namoz_yoq.sh
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)/worker"

echo "== 1/2 D1: vazifa_takror.toifa ustuni"
BOR=$(npx wrangler d1 execute farvonuy --remote --json \
  --command "SELECT count(*) n FROM pragma_table_info('vazifa_takror') WHERE name='toifa'" \
  | py -3.14 -c "import json,sys; print(json.load(sys.stdin)[0]['results'][0]['n'])")
if [ "$BOR" = "0" ]; then
  npx wrangler d1 execute farvonuy --remote --command "ALTER TABLE vazifa_takror ADD COLUMN toifa TEXT" | tail -2
else
  echo "ustun bor"
fi

echo "== 2/2 Deploy"
npx wrangler deploy 2>&1 | tail -6
echo "TAYYOR"
