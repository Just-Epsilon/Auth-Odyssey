# PoC 2: Audience Narrowing

## Hypothesis
The audience (`aud`) claim narrows from `orchestrator` → `subagent` → `tool-api` during each token exchange. A token with audience `orchestrator` cannot be used for `subagent`, and a token with audience `subagent` cannot be used for `tool-api`. The resource server correctly enforces that the audience must equal `tool-api`.

## Baseline configuration
- **Keycloak realm:** `agent-lab`
- **Audience mappings:**
  - `entry-cli` → has audience `orchestrator` (via client scope)
  - `orchestrator` → has audience `subagent` (via client scope)
  - `subagent` → has audience `tool-api` (via client scope)
- **Resource server:** `tool-api` (FastAPI) requires `aud = tool-api` for all requests to `/effect`
- **JWT verification:** `verify_tool_token()` enforces `audience = tool-api`

## Controlled mutation
We do not mutate anything in this experiment. Instead, we compare three different tokens (T0, T1, T2) that are produced by the normal delegation chain. Each token has a different audience, and we observe whether the resource server accepts or rejects each one.

## Execution

### 1. Generate fresh tokens
```bash
cd ~/Documents/a-a/week1/agent-auth-lab
source .venv/bin/activate

./scripts/get-user-token.sh
export ORCHESTRATOR_SECRET="YOUR_ORCHESTRATOR_SECRET"
./scripts/exchange-orchestrator.sh
export SUBAGENT_SECRET="YOUR_SUBAGENT_SECRET"
./scripts/ex_subagent.sh
