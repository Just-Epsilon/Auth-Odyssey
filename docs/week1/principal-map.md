# Week 1 Principal Map

| Security concept | Concrete Week 1 object |
|---|---|
| Human principal | Alice |
| Human/token subject | Alice's Keycloak `sub` |
| Entry application | `entry-cli` |
| Logical primary agent | `orchestrator-agent` |
| OAuth identity for primary agent | `orchestrator` |
| Primary agent instance | `orch-01` |
| Logical child agent | `research-subagent` |
| OAuth identity for child agent | `subagent` |
| Child agent instance | `sub-01` |
| Protected resource | `tool-api` |
| Workload | Local Python process/container |
| Workload identity | Not enforced in Week 1 |

## Authorization flow

Alice
  ↓
entry-cli
  ↓
T0
  ↓
orchestrator-agent
  instance: orch-01
  ↓
T1
  ↓
research-subagent
  instance: sub-01
  ↓
T2
  ↓
tool-api
