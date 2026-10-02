#!/usr/bin/env bash
# Botni Cloudflare'ga o'tkazish (bir martalik). Ishga tushirishdan oldin:
#   * xabarchi to'xtatilgan (FarvonUy_Telegram rejasi o'chiq),
#   * desktop dasturi yopiq,
#   * eksport tayyor:  py -3.14 tools/d1_eksport.py --chiqish <EKSPORT> --rasmlar
# Ishlatish:  bash tools/otish.sh <EKSPORT papka>
# Orqaga qaytish:  deleteWebhook + FarvonUy_Telegram rejasini yoqish.
set -euo pipefail

EKS="${1:?eksport papkasi kerak}"
ILDIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ILDIZ/worker"
KALIT_FAYL="$LOCALAPPDATA/FarvonUy/bulut.json"

echo "== 1/5 D1 bo'shmi"
JADVAL=$(npx wrangler d1 execute farvonuy --remote --json \
  --command "SELECT count(*) n FROM sqlite_master WHERE type='table' AND name IN ('odam','rasxod')" \
  | py -3.14 -c "import json,sys; print(json.load(sys.stdin)[0]['results'][0]['n'])")
if [ "$JADVAL" != "0" ]; then echo "D1 bo'sh emas — to'xtadim."; exit 1; fi

echo "== 2/5 Sxema va ma'lumot yuklanyapti"
npx wrangler d1 execute farvonuy --remote --yes --file "$EKS/schema.sql" | tail -2
npx wrangler d1 execute farvonuy --remote --yes --file "$EKS/data.sql" | tail -2
if [ -s "$EKS/rasm.sql" ] && [ "$(wc -c < "$EKS/rasm.sql")" -gt 5 ]; then
  npx wrangler d1 execute farvonuy --remote --yes --file "$EKS/rasm.sql" | tail -2
fi

echo "== 3/5 Maxfiy kalitlar"
if [ ! -f "$KALIT_FAYL" ]; then
  py -3.14 -c "import json,secrets; json.dump({'sinx_kalit':secrets.token_urlsafe(32),'tg_maxfiy':secrets.token_hex(24)}, open(r'$KALIT_FAYL','w'))"
fi
SINX=$(py -3.14 -c "import json; print(json.load(open(r'$KALIT_FAYL'))['sinx_kalit'])")
MAXFIY=$(py -3.14 -c "import json; print(json.load(open(r'$KALIT_FAYL'))['tg_maxfiy'])")

echo "== 4/5 Deploy"
DEPLOY=$(npx wrangler deploy 2>&1); echo "$DEPLOY" | tail -8
URL=$(echo "$DEPLOY" | grep -oE 'https://[a-z0-9.-]+\.workers\.dev' | head -1)
[ -n "$URL" ] || { echo "workers.dev manzili topilmadi"; exit 1; }
printf '%s' "$SINX"   | npx wrangler secret put SINX_KALIT | tail -1
printf '%s' "$MAXFIY" | npx wrangler secret put TG_MAXFIY  | tail -1
py -3.14 -c "import json; d=json.load(open(r'$KALIT_FAYL')); d['url']='$URL'; json.dump(d, open(r'$KALIT_FAYL','w'))"
sleep 5
echo "server: $(curl -s "$URL/")"

echo "== 5/5 Telegram -> server (webhook)"
TOKEN=$(py -3.14 -c "import sqlite3,os; c=sqlite3.connect('file:'+os.environ['LOCALAPPDATA']+'/FarvonUy/farvonuy.db?mode=ro',uri=True); print(c.execute(\"SELECT qiymat FROM sozlama WHERE kalit='tg_token'\").fetchone()[0])")
curl -s "https://api.telegram.org/bot$TOKEN/setWebhook" \
  --data-urlencode "url=$URL/tg/$MAXFIY" \
  --data-urlencode "secret_token=$MAXFIY" \
  --data-urlencode 'allowed_updates=["message","callback_query"]'; echo
curl -s "https://api.telegram.org/bot$TOKEN/getWebhookInfo" \
  | py -3.14 -c "import json,sys; r=json.load(sys.stdin)['result']; r['url']=r.get('url','')[:40]+'…'; print(r)"
echo "TAYYOR: $URL"
