# Breaking the Audience Chain

## Goal
Demonstrate that token exchange requires the exchanging client to be an authorized audience of the subject token.

## Baseline (Working)
- Configuration: `aud-orchestrator` attached to `entry-cli`.
- T0 claims: `aud` includes `orchestrator`.
- Exchange `T0 → T1` as `orchestrator` with `audience=subagent` → **Success** (HTTP 200, T1 issued).

## Broken Configuration
- Removed `aud-orchestrator` from `entry-cli` default scopes.
- New T0 claims: `aud` **does not** contain `orchestrator`.

## Request (Broken)
```bash
curl -X POST $TOKEN_URL \
  -u orchestrator:secret \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token=$T0 \
  -d audience=subagent
