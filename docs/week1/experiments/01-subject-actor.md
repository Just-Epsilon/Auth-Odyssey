# PoC 1: Subject vs. Actor Attribution

## Hypothesis
The audit trail can distinguish the human subject (Alice) from the delegated component (subagent) that actually invoked the tool.

## Baseline configuration
- Keycloak realm: agent-lab
- Delegation chain: alice → orchestrator → subagent → tool-api
- Audit schema includes both `token_subject` and `acting_client`

## Controlled mutation
We intentionally query the audit database using **only** the `token_subject` column, ignoring `acting_client`.

## Execution
1. Run the full delegation chain with T0 → T1 → T2.
2. Call `/effect` with T2.
3. Query the `events` table for the `RESOURCE_REQUEST` event.

## Token/claim evidence
- T0: `sub = alice`, `azp = entry-cli`
- T1: `sub = alice`, `azp = orchestrator`
- T2: `sub = alice`, `azp = subagent`

## Authorization result
T2 → `/effect` → 200 OK (ALLOW)

## Audit evidence (full)
| event_type          | token_subject | acting_client |
|---------------------|---------------|---------------|
| GRANT               | alice         | entry-cli     |
| RESOURCE_REQUEST    | alice         | subagent      |

## Audit evidence (broken — only subject)
| event_type          | token_subject |
|---------------------|---------------|
| RESOURCE_REQUEST    | alice         |

## Conclusion
**Hypothesis confirmed.** The full audit trail distinguishes Alice (the subject) from the subagent (the acting client). A broken audit system that logs only `token_subject` would incorrectly attribute the action to Alice alone, losing the delegation chain.

## Security implication
To reconstruct authorization history, audit logs must record **both** the subject (`sub`) and the immediate authorized party (`azp` or `acting_client`). Otherwise, you cannot prove which delegated component performed the action.
