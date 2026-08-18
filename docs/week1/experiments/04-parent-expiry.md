# PoC 4: Parent Expiration

## Hypothesis
A child token (T2) may remain usable after the parent token (T0) expires because each token has its own independent expiration.

## Baseline configuration
- T0 lifespan: 60 seconds (reduced from default for testing)
- T1 lifespan: default (5 minutes)
- T2 lifespan: default (5 minutes)
- Delegation chain: alice → orchestrator → subagent → tool-api

## Controlled mutation
We shorten T0's lifespan to 60 seconds, issue T2, wait for T0 to expire, then test T2.

## Execution
1. Set T0 lifespan to 60 seconds
2. Issue T0, exchange to T1, exchange to T2
3. Record T0 and T2 expiration times
4. Test T2 immediately (baseline)
5. Wait 2 minutes (until T0 expires)
6. Test T2 again

## Token/claim evidence

| Token | Issued at | Expires at | Status |
|-------|-----------|------------|--------|
| T0    | 20:00:00  | 20:01:00   | Expired |
| T2    | 20:00:30  | 20:05:30   | Valid (if still working) |

## Authorization result

### Before T0 expiry:
T2 → `/effect` → 200 OK (ALLOW)

### After T0 expiry:
T2 → `/effect` → [200 OK / 401 UNAUTHORIZED]

**Actual result:** [Fill in based on your test]

## Audit evidence
- GRANT event: recorded (T0)
- RESOURCE_REQUEST event: [recorded if T2 worked]

## Conclusion
**Hypothesis [confirmed/rejected].**

- If T2 still works: Child tokens outlive parent tokens. Keycloak does not enforce transitive expiration. This means authority can persist even after the original grant expires.
- If T2 fails: Child tokens expire with parent. Keycloak enforces transitive expiration, providing stronger security.

## Security implication
- If child tokens outlive parents: Need to implement explicit revocation or shorter token lifetimes for child tokens. Or rely on parent expiration as a session boundary.
- If child tokens expire with parents: Stronger security, but may impact long-running delegated operations.

