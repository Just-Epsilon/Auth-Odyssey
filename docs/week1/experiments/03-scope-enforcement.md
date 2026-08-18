# Experiment 03 — Scope Expansion vs Downscoping

## Security question

Can a delegated token obtain a scope that was absent
from its parent token?

## Security invariant

Scopes(child) ⊆ Scopes(parent)

## Hypothesis

Without explicit downscope enforcement, subagent can
request tool-write even though T1 contains only tool-read.

With downscope-assertion-grant-enforcer enabled,
the same request will be rejected.

## Configuration

Parent:
T1

Requester:
subagent

Audience:
tool-api

Parent scopes:
tool-read

Optional child scope:
tool-write


## Run A — Enforcement disabled

T1.scope:
[...]

Requested:
scope=tool-write

Exchange:
SUCCESS / actual result

T2.scope:
[...]

Resource result:
ALLOW / DENY

Conclusion:
...


## Run B — Enforcement enabled

T1.scope:
[...]

Requested:
scope=tool-write

Exchange:
actual HTTP status

Error:
[...]

T2 issued:
YES / NO

Conclusion:
...


## Security implication

...


## Final conclusion

Invariant without enforcement:
SATISFIED / VIOLATED

Invariant with enforcement:
SATISFIED / VIOLATED
