#!/usr/bin/env bash
set -euo pipefail

KC="http://127.0.0.1:8080"
REALM="agent-lab"
EXCHANGER_CLIENT="subagent"
TARGET_AUDIENCE="tool-api"
T0_FILE=".run/t0.jwt"
T1_FILE=".run/t1.jwt"
T2_FILE=".run/t2.jwt"

: "${SUBAGENT_SECRET:?Set SUBAGENT_SECRET first}"

if [[ ! -s "$T0_FILE" ]]; then
    echo "ERROR: $T0_FILE does not exist or is empty." >&2
    exit 1
fi
if [[ ! -s "$T1_FILE" ]]; then
    echo "ERROR: $T1_FILE does not exist or is empty." >&2
    exit 1
fi

T1="$(cat "$T1_FILE")"

echo "Exchanging T1 as $EXCHANGER_CLIENT..." >&2

RESPONSE="$(
    curl -sS \
        -u "$EXCHANGER_CLIENT:$SUBAGENT_SECRET" \
        -X POST \
        "$KC/realms/$REALM/protocol/openid-connect/token" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode \
            'grant_type=urn:ietf:params:oauth:grant-type:token-exchange' \
        --data-urlencode \
            "subject_token=$T1" \
        --data-urlencode \
            'subject_token_type=urn:ietf:params:oauth:token-type:access_token' \
        --data-urlencode \
            'requested_token_type=urn:ietf:params:oauth:token-type:access_token' \
        --data-urlencode \
            "audience=$TARGET_AUDIENCE"
)"

if jq -e '.error' >/dev/null 2>&1 <<< "$RESPONSE"; then
    echo "Token exchange FAILED:" >&2
    echo "$RESPONSE" | jq . >&2
    exit 1
fi

T2="$(jq -er '.access_token' <<< "$RESPONSE")"
printf '%s' "$T2" > "$T2_FILE"
chmod 600 "$T2_FILE"

# ✅ Success messages to stderr
echo "T0 -> T1 > T2 exchange successful." >&2
echo "T2 saved to $T2_FILE" >&2
