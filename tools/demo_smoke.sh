#!/bin/sh
# demo smoke test: bin/rvt-view FILE --no-browser on a free port, wait until the model is complete, curl the main page, meta, materials and /sheets/. usage: tools/demo_smoke.sh FILE.rvt [PORT]
F="$1"; P="${2:-8893}"; D="$(dirname "$(readlink -f "$0")")/.."
"$D/bin/rvt-view" "$F" --no-browser --port "$P" > /tmp/rvt-demo-smoke-$P.log 2>&1 &
PID=$!; ok=1
for i in $(seq 1 600); do curl -sf "http://127.0.0.1:$P/api/models" > /dev/null && break; sleep 1; done
MID=$(curl -s "http://127.0.0.1:$P/api/models" | python3 -c "import json,sys,os; d=json.load(sys.stdin); m=[x for x in d if x['name'] == os.path.basename(sys.argv[1])]; print(m[0]['id'] if m else '')" "$F")
[ -n "$MID" ] || { echo "model for $(basename "$F") not listed by /api/models"; kill $PID 2>/dev/null; echo DEMO-SMOKE FAIL; exit 1; }
for i in $(seq 1 900); do ph=$(curl -s "http://127.0.0.1:$P/m/$MID/meta.json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('phase'))" 2>/dev/null); [ "$ph" = done ] && break; sleep 2; done
echo "model $MID phase=$ph"; [ "$ph" = done ] || ok=0
curl -sf "http://127.0.0.1:$P/" | grep -q "<canvas\|app.js" && echo "main page OK" || { echo "main page FAIL"; ok=0; }
curl -sf "http://127.0.0.1:$P/m/$MID/materials.json" > /dev/null && echo "materials OK" || echo "materials missing (old cache?)"
curl -sf "http://127.0.0.1:$P/sheets/" > /dev/null && echo "sheets page OK" || { echo "sheets page FAIL"; ok=0; }
curl -sf "http://127.0.0.1:$P/sheets/api/$MID/doc.json" > /dev/null && echo "sheets doc OK" || echo "sheets doc not ready/failed"
kill $PID 2>/dev/null; sleep 1; pkill -P $PID 2>/dev/null
[ $ok = 1 ] && echo DEMO-SMOKE OK || { echo DEMO-SMOKE FAIL; exit 1; }
