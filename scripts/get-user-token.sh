#!/usr/bin/env bash

set -e

KC="http://127.0.0.1:8080"
REALM="agent-lab"
CLIENT_ID="entry-cli"
USERNAME="alice"
PASSWORD="alice"

mkdir -p .run

curl -s \
  -X POST \
  "$KC/realms/$REALM/protocol/openid-connect/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "scope=openid" |
jq -r '.access_token' > ~/Documents/a-a/week1/agent-auth-lab/.run/t0.jwt

echo "T0 saved to .run/t0.jwt"
