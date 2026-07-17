#!/bin/bash
# Send the Bernard-LM newsletter via Resend.
#
# Test send (to your own inbox):
#   RESEND_API_KEY=re_xxx ./scripts/send-newsletter.sh test
#
# Real broadcast (to the whole audience — creates a Resend broadcast draft
# and sends it):
#   RESEND_API_KEY=re_xxx ./scripts/send-newsletter.sh broadcast
set -euo pipefail

HTML_FILE="$(dirname "$0")/../_newsletters/2026-07-17-bernard-lm.html"
SUBJECT="I trained a GPT on 15 years of my life"
FROM="Bernard Huang <bernard@zonted.com>"
TEST_TO="psyduckler@gmail.com"
AUDIENCE_ID="3282e3a7-f68b-45fb-99fa-4f203f203892"   # "General" audience (same as subscribe.js fallback)

[ -z "${RESEND_API_KEY:-}" ] && { echo "RESEND_API_KEY not set"; exit 1; }
MODE="${1:-test}"

# JSON-encode the HTML body via python (handles quotes/newlines safely)
HTML_JSON=$(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "$HTML_FILE")

if [ "$MODE" = "test" ]; then
  # Test sends go through /emails; strip the broadcast-only unsubscribe var
  HTML_JSON=$(python3 -c "
import json,sys
h = json.loads(sys.argv[1])
h = h.replace('{{{RESEND_UNSUBSCRIBE_URL}}}', 'https://zonted.com/#subscribe')
print(json.dumps(h))" "$HTML_JSON")
  curl -sS https://api.resend.com/emails \
    -H "Authorization: Bearer $RESEND_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"from\": \"$FROM\", \"to\": [\"$TEST_TO\"], \"subject\": \"[TEST] $SUBJECT\", \"html\": $HTML_JSON}"
  echo; echo "Test sent to $TEST_TO"
elif [ "$MODE" = "broadcast" ]; then
  ID=$(curl -sS https://api.resend.com/broadcasts \
    -H "Authorization: Bearer $RESEND_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"audience_id\": \"$AUDIENCE_ID\", \"from\": \"$FROM\", \"subject\": \"$SUBJECT\", \"html\": $HTML_JSON}" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
  echo "Broadcast created: $ID"
  curl -sS -X POST "https://api.resend.com/broadcasts/$ID/send" \
    -H "Authorization: Bearer $RESEND_API_KEY"
  echo; echo "Broadcast $ID sent to audience $AUDIENCE_ID"
else
  echo "usage: send-newsletter.sh [test|broadcast]"; exit 1
fi
