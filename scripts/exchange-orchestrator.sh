#!/usr/bin/env bash
set -euo pipefail

KC="http://127.0.0.1:8080"
REALM="agent-lab"
EXCHANGER_CLIENT="orchestrator"
TARGET_AUDIENCE="subagent"
T0_FILE=".run/t0.jwt"
T1_FILE=".run/t1.jwt"

: "${ORCHESTRATOR_SECRET:?Set ORCHESTRATOR_SECRET first}"

if [[ ! -s "$T0_FILE" ]]; then
    echo "ERROR: $T0_FILE does not exist or is empty." >&2
    exit 1
fi

T0="$(cat "$T0_FILE")"

echo "Exchanging T0 as $EXCHANGER_CLIENT..." >&2

RESPONSE="$(
    curl -sS \
        -u "$EXCHANGER_CLIENT:$ORCHESTRATOR_SECRET" \
        -X POST \
        "$KC/realms/$REALM/protocol/openid-connect/token" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode \
            'grant_type=urn:ietf:params:oauth:grant-type:token-exchange' \
        --data-urlencode \
            "subject_token=$T0" \
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

T1="$(jq -er '.access_token' <<< "$RESPONSE")"
mkdir -p .run
printf '%s' "$T1" > "$T1_FILE"
chmod 600 "$T1_FILE"

# ✅ Success messages to stderr
echo "T0 -> T1 exchange successful." >&2
echo "T1 saved to $T1_FILE" >&2
