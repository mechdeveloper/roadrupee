#!/usr/bin/env bash
# Smoke test a running RoadRupee: scripts/smoke.sh <base-url>
#   scripts/smoke.sh http://localhost:3000
#   scripts/smoke.sh https://roadrupee-frontend.graygrass-b61bee71.centralindia.azurecontainerapps.io
# Read-only GETs. Exits 0 when every check passes, 1 otherwise.
set -u

BASE="${1:-}"
if [ -z "$BASE" ]; then
  echo "usage: $0 <base-url>" >&2
  exit 2
fi
BASE="${BASE%/}"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
FAILS=0
if [ -t 1 ]; then GREEN=$'\033[32m'; RED=$'\033[31m'; OFF=$'\033[0m'; else GREEN=""; RED=""; OFF=""; fi

# check <label> <path> <description of what the body must satisfy> <test command run on $TMP>
check() {
  local label="$1" path="$2" what="$3" test_cmd="$4" code
  code="$(curl -sS -L --max-time 30 --retry 2 --retry-delay 3 -o "$TMP" -w '%{http_code}' "$BASE$path" 2>/dev/null)" || code="000"
  if [ "$code" = "200" ] && eval "$test_cmd"; then
    printf '%s PASS%s  %-22s %s\n' "$GREEN" "$OFF" "$label" "$path"
  else
    printf '%s FAIL%s  %-22s %s  (HTTP %s; wanted: %s)\n' "$RED" "$OFF" "$label" "$path" "$code" "$what"
    FAILS=$((FAILS + 1))
  fi
}

echo "Smoke test: $BASE"
check "home"            "/"                      "HTML containing RoadRupee"                 'grep -q "RoadRupee" "$TMP"'
check "ward page"       "/ward/k-e"              "HTML containing RoadRupee"                 'grep -q "RoadRupee" "$TMP"'
check "trace page"      "/trace"                 "HTML containing RoadRupee"                 'grep -q "RoadRupee" "$TMP"'
check "api health"      "/api/health"            '{"status":"ok",...}'                        'grep -q "\"status\":\"ok\"" "$TMP"'
check "flags.csv"       "/api/flags.csv"         "audit-tier CSV, work_order_id first, ~391 rows"  'head -1 "$TMP" | grep -q "^work_order_id," && [ "$(wc -l < "$TMP")" -gt 300 ] && [ "$(wc -l < "$TMP")" -lt 600 ]'
check "next-rupee city" "/api/plan/city?limit=3" "3 items with a risk_score"                 '[ "$(grep -o "\"risk_score\"" "$TMP" | wc -l)" -ge 3 ]'

echo
if [ "$FAILS" -eq 0 ]; then
  echo "${GREEN}All checks passed.${OFF}"
  exit 0
fi
echo "${RED}$FAILS check(s) failed.${OFF}"
exit 1
