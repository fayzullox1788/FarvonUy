#!/usr/bin/env bash
# Mini App'ni yoqish: D1 ustuni → deploy → botda «Vazifalar» menyu tugmasi.
# Qayta ishga tushirish xavfsiz (ustun bor bo'lsa o'tkazib yuboriladi).
#   bash tools/miniapp_yoq.sh
set -euo pipefail
ILDIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ILDIZ/worker"
KALIT_FAYL="$LOCALAPPDATA/FarvonUy/bulut.json"
URL=$(py -3.14 -c "import json; print(json.load(open(r'$KALIT_FAYL'))['url'])")

echo "== 1/3 D1: vazifa.toifa ustuni"
BOR=$(npx wrangler d1 execute farvonuy --remote --json \
  --command "SELECT count(*) n FROM pragma_table_info('vazifa') WHERE name='toifa'" \
  | py -3.14 -c "import json,sys; print(json.load(sys.stdin)[0]['results'][0]['n'])")
if [ "$BOR" = "0" ]; then
  npx wrangler d1 execute farvonuy --remote --command "ALTER TABLE vazifa ADD COLUMN toifa TEXT" | tail -2
else
  echo "ustun bor"
fi

echo "== 2/3 Deploy"
npx wrangler deploy 2>&1 | tail -6
sleep 3
echo "sahifa: $(curl -s -o /dev/null -w '%{http_code}' "$URL/app")"

echo "== 3/3 Bot menyu tugmasi"
TOKEN=$(py -3.14 -c "import sqlite3,os; c=sqlite3.connect('file:'+os.environ['LOCALAPPDATA']+'/FarvonUy/farvonuy.db?mode=ro',uri=True); print(c.execute(\"SELECT qiymat FROM sozlama WHERE kalit='tg_token'\").fetchone()[0])")
TUGMA=$(py -3.14 -c "import json; print(json.dumps({'type':'web_app','text':'Vazifalar','web_app':{'url':'$URL/app'}}))")
curl -s "https://api.telegram.org/bot$TOKEN/setChatMenuButton" --data-urlencode "menu_button=$TUGMA"; echo
echo "TAYYOR: botning shaxsiy chatida pastdagi «Vazifalar» tugmasini bosing."
