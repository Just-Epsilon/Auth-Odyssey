#!/bin/bash
set -e

response=$(curl -s -X POST "http://127.0.0.1:8080/realms/agent-lab/protocol/openid-connect/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d grant_type=password \
  -d client_id=entry-cli \
  -d username=alice \
  -d password=alice \
  -d scope=openid)

if echo "$response" | jq -e .access_token > /dev/null 2>&1; then
    echo "$response" | jq -r .access_token > .run/t0.jwt
    # Send success message to stderr (not stdout)
    echo "T0 saved to .run/t0.jwt" >&2
else
    echo "ERROR: Failed to obtain T0. Response:" >&2
    echo "$response" >&2
    exit 1
fi
