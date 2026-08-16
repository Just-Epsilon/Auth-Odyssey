#!/usr/bin/env bash

set -euo pipefail

KC="http://127.0.0.1:8080"
REALM="agent-lab"

EXCHANGER_CLIENT="subagent"
TARGET_AUDIENCE="tool-api"

T0_FILE=".run/t0.jwt"
T1_FILE=".run/t1.jwt"
T2_FILE=".run/t2.jwt"

# Fail immediately if the secret wasn't supplied.
: "${SUBAGENT_SECRET:?Set SUBAGENT_SECRET first}"

# Make sure T0 exists.
if [[ ! -s "$T0_FILE" ]]; then
    echo "ERROR: $T0_FILE does not exist or is empty."
    echo "Generate T0 first."
    exit 1
fi

# Make sure T1 exists.
if [[ ! -s "$T1_FILE" ]]; then
    echo "ERROR: $T1_FILE does not exist or is empty."
    echo "Generate T1 first."
    exit 1
fi


T0="$(cat "$T0_FILE")"
T1="$(cat "$T1_FILE")"


echo "Exchanging T1 as $EXCHANGER_CLIENT..."


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


# Detect Keycloak/OAuth errors.
if jq -e '.error' >/dev/null 2>&1 <<< "$RESPONSE"; then
    echo "Token exchange FAILED:"
    echo "$RESPONSE" | jq .
    exit 1
fi


# Extract T2.
T2="$(jq -er '.access_token' <<< "$RESPONSE")"

printf '%s' "$T2" > "$T2_FILE"

chmod 600 "$T2_FILE"

echo "T0 -> T1 > T2 exchange successful."
echo "T2 saved to $T2_FILE"









