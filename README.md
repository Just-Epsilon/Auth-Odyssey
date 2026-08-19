# Auth-Odyssey
Who delegated to whom? A lab for tracing authorization chains


A reproducible research lab that demonstrates **multi-hop OAuth token delegation** using Keycloak and RFC 8693 Token Exchange.

The lab tracks authorization state evolution and provides a full audit trail to answer:

> **Who authorized the action, which component performed it, which tokens supported each step, and what durable effect resulted?**

---

## Table of Contents

* [Inspiration](#inspiration)
* [Research Question](#research-question)
* [Architecture](#architecture)
* [Principal Model](#principal-model)
* [Prerequisites](#prerequisites)
* [Setup](#setup)

  * [1. Start Keycloak](#1-start-keycloak)
  * [2. Configure Realm and Clients](#2-configure-realm-and-clients)
  * [3. Set Environment Variables](#3-set-environment-variables)
  * [4. Start the FastAPI Server](#4-start-the-fastapi-server)
* [Running the Authorization Chain](#running-the-authorization-chain)
* [Viewing the Timeline](#viewing-the-timeline)
* [Results](#results)
* [Limitations](#limitations)

---

## Inspiration

I was reading **RFC 8693 (OAuth 2.0 Token Exchange)** and became fascinated by the idea of delegating authority across multiple hops.

RFC 8693 describes how a client can exchange one security token for another, potentially changing the audience, scope, or other authorization properties.

I wanted to see this in action and understand:

* Can I actually build a multi-hop delegation chain?
* What does the authorization state look like at each step?
* Can I prove, from audit logs alone, who authorized what and who actually performed the action?
* How does token lineage evolve across multiple delegation hops?
* What information is lost if we only look at individual JWT claims?

This lab is a **hands-on experiment** designed to answer those questions.

It implements:

```text
Human
  ↓
OAuth Client
  ↓
Orchestrator Agent
  ↓
Subagent
  ↓
Resource Server
```

with each delegation hop represented through OAuth 2.0 Token Exchange and recorded in an audit trail.

The goal is not to build production software, but to **understand delegated authorization by building it**.

---

## Research Question

> In a system with delegated authority, can we reconstruct **who authorized an action**, **which delegated component performed it**, and **why it was allowed**, using only an audit log?

The lab uses **OAuth 2.0 Token Exchange (RFC 8693)** to delegate authority from a human subject (`alice`) through a chain of agents:

```text
Alice
  ↓
entry-cli
  ↓
orchestrator
  ↓
subagent
  ↓
tool-api
```

A SQLite audit trail captures:

* Token issuance
* Token exchanges
* Parent/child token relationships
* Resource requests
* Authorization decisions
* Durable effects
* Claim snapshots
* Token hashes

The resulting event history can be reconstructed into a chronological authorization timeline.

---

## Architecture

```text
                         ┌─────────────────┐
                         │   Alice (human) │
                         └────────┬────────┘
                                  │
                                  │ Authentication
                                  ▼
                         ┌─────────────────┐
                         │    entry-cli    │
                         │   OAuth Client  │
                         └────────┬────────┘
                                  │
                                  │ T0
                                  │ sub=alice
                                  │ aud=orchestrator
                                  ▼
                         ┌─────────────────┐
                         │  orchestrator   │
                         │  Logical Agent  │
                         └────────┬────────┘
                                  │
                                  │ RFC 8693
                                  │ T0 → T1
                                  ▼
                         ┌─────────────────┐
                         │       T1        │
                         │ sub=alice       │
                         │ azp=orchestrator│
                         │ aud=subagent    │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    subagent     │
                         │  Logical Agent  │
                         └────────┬────────┘
                                  │
                                  │ RFC 8693
                                  │ T1 → T2
                                  ▼
                         ┌─────────────────┐
                         │       T2        │
                         │ sub=alice       │
                         │ azp=subagent   │
                         │ aud=tool-api   │
                         └────────┬────────┘
                                  │
                                  │ Authorization
                                  ▼
                         ┌─────────────────┐
                         │    tool-api     │
                         │ Resource Server │
                         └────────┬────────┘
                                  │
                                  │ Authorized operation
                                  ▼
                         ┌─────────────────┐
                         │ Durable Effect  │
                         │ mark_test_order │
                         │ _reviewed       │
                         └─────────────────┘
```

### Token lineage

```text
T0
 │
 │ RFC 8693
 ▼
T1
 │
 │ RFC 8693
 ▼
T2
 │
 ▼
tool-api
```

All authorization events are recorded in a SQLite database.

The database stores token hashes rather than raw access tokens and maintains parent/child relationships between tokens.

---

## Principal Model

One of the goals of this lab is to explicitly distinguish different kinds of identity.

| Concept               | Representation in Lab             |
| --------------------- | --------------------------------- |
| Human principal       | Keycloak user `alice`             |
| Entry application     | OAuth client `entry-cli`          |
| Logical primary agent | `orchestrator`                    |
| Agent instance        | `orch-01`                         |
| Logical child agent   | `subagent`                        |
| Child instance        | `sub-01`                          |
| Resource server       | `tool-api`                        |
| Workload              | Python process running `tool-api` |

The distinction is important.

A **human** is not an OAuth client.

An **OAuth client** is not necessarily the same thing as a logical agent.

A **logical agent** is not necessarily the same thing as a runtime instance.

A **workload** is not automatically given a strong cryptographic identity simply because it is running a particular process.

This lab intentionally keeps these concepts separate so their relationships can be examined through the audit trail.

---

## Prerequisites

Install the following before starting:

* Docker
* Docker Compose
* Python 3.10+
* `jq`
* `git`

Verify the installation:

```bash
docker --version
docker compose version
python3 --version
jq --version
git --version
```

---

# Setup

## 1. Start Keycloak

Start the environment:

```bash
docker compose up -d
```

Keycloak should become available at:

```text
http://127.0.0.1:8080
```

The development environment uses:

```text
Username: admin
Password: admin
```

> These credentials are suitable only for the local development lab. Do not use them in production.

Check the containers:

```bash
docker compose ps
```

Check Keycloak logs if necessary:

```bash
docker compose logs -f keycloak
```

---

## 2. Configure Realm and Clients

The lab uses a Keycloak realm named:

```text
agent-lab
```

The main objects are:

```text
User:
    alice

Clients:
    entry-cli
    orchestrator
    subagent
    tool-api
```

### Option A — Import the Realm

If a Keycloak realm export is available, place:

```text
agent-lab-realm.json
```

inside:

```text
infra/keycloak/
```

Then configure Keycloak to import the realm on startup.

For example:

```yaml
command:
  - start-dev
  - --import-realm
```

Restart the environment:

```bash
docker compose down
docker compose up -d
```

---

### Option B — Configure Manually

Create the realm:

```text
agent-lab
```

Create the user:

```text
alice
```

Create the following clients:

```text
entry-cli
orchestrator
subagent
tool-api
```

#### `entry-cli`

Configure:

```text
Client authentication: OFF
Direct Access Grants: ON
```

#### `orchestrator`

Configure:

```text
Client authentication: ON
Standard Token Exchange: ON
```

#### `subagent`

Configure:

```text
Client authentication: ON
Standard Token Exchange: ON
```

#### `tool-api`

Configure:

```text
Client authentication: ON
Token Exchange: OFF
```

The resource server does not need to perform another exchange.

---

### Audience Client Scopes

Create client scopes for audience narrowing:

```text
aud-orchestrator
aud-subagent
aud-tool
```

Attach them to the appropriate clients.

The intended authorization path is:

```text
entry-cli
    ↓
orchestrator
    ↓
subagent
    ↓
tool-api
```

The important property is that the audience becomes progressively narrower.

---

## 3. Set Environment Variables

The `orchestrator` and `subagent` clients use client authentication.

Obtain their client secrets from:

```text
Keycloak Admin Console
    → Clients
        → orchestrator
        → Credentials
```

and:

```text
Keycloak Admin Console
    → Clients
        → subagent
        → Credentials
```

Export them:

```bash
export ORCHESTRATOR_SECRET="your-orchestrator-secret"
export SUBAGENT_SECRET="your-subagent-secret"
```

You can verify that they exist:

```bash
echo "$ORCHESTRATOR_SECRET"
echo "$SUBAGENT_SECRET"
```

Do **not** commit secrets to Git.

If using a `.env` file, add it to `.gitignore`:

```gitignore
.env
```

---

## 4. Start the FastAPI Server

Create or activate the Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the resource server:

```bash
uvicorn agentlab.tool_api:app \
  --app-dir src \
  --reload \
  --host 127.0.0.1 \
  --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

The protected endpoint is:

```text
POST /effect
```

The endpoint verifies the access token before allowing the durable effect.

---

# Running the Authorization Chain

Once Keycloak and the FastAPI resource server are running, execute:

```bash
RUN_ID=$(./scripts/run-chain.sh)
```

The script performs the complete authorization chain.

### Step 1 — Obtain T0

Authenticate as Alice and obtain the initial token:

```text
T0
```

Conceptually:

```text
sub = alice
aud = orchestrator
```

The token issuance is recorded as a `GRANT` event.

---

### Step 2 — Exchange T0 for T1

The orchestrator exchanges T0 using RFC 8693:

```text
T0 → T1
```

The resulting token is intended for the subagent:

```text
sub = alice
azp = orchestrator
aud = subagent
```

The exchange is recorded as:

```text
TOKEN_EXCHANGE
```

---

### Step 3 — Exchange T1 for T2

The subagent exchanges T1:

```text
T1 → T2
```

The resulting token is intended for the resource server:

```text
sub = alice
azp = subagent
aud = tool-api
```

Another:

```text
TOKEN_EXCHANGE
```

event is recorded.

---

### Step 4 — Call the Resource Server

The script sends T2 to:

```http
POST /effect
```

The resource server:

1. Verifies the JWT signature.
2. Validates the issuer.
3. Validates the audience.
4. Checks authorization requirements.
5. Records the resource request.
6. Creates the synthetic durable effect.
7. Records the durable effect.

The final operation is:

```text
mark_test_order_reviewed
```

on:

```text
ORDER-001
```

---

### Expected Authorization Behavior

The intended result is:

| Token | Resource   | Expected |
| ----- | ---------- | -------- |
| T0    | `tool-api` | DENY     |
| T1    | `tool-api` | DENY     |
| T2    | `tool-api` | ALLOW    |

This demonstrates audience narrowing.

A token intended for an earlier component should not automatically authorize access to a later resource.

---

# Viewing the Timeline

The timeline tool reconstructs the authorization history from SQLite.

Run:

```bash
PYTHONPATH=src python -m agentlab.timeline show "$RUN_ID"
```

Example:

```text
📋 Authorization Timeline — run-20260819-210034
Events: 5

t0  GRANT  17:30:35
    human:       alice
    client:      entry-cli
    token:       8d8ad90dc0ca...
    subject:     cea48ae5-...
    audience:    ["orchestrator", "account"]
    result:      SUCCESS

t1  TOKEN_EXCHANGE  17:30:35
    actor:       orchestrator
    parent:      8d8ad90dc0ca...
    token:       d90f2734dece...
    audience:    subagent

t2  TOKEN_EXCHANGE  17:30:35
    actor:       subagent
    parent:      d90f2734dece...
    token:       dee751bfa277...
    audience:    tool-api

t3  RESOURCE_REQUEST  17:30:35
    resource:    tool-api
    token:       dee751bfa277...
    actor:       subagent
    result:      ALLOW

t4  DURABLE_EFFECT  17:30:35
    operation:   mark_test_order_reviewed
    object:      ORDER-001

Token lineage:
    t0: 8d8ad90dc0ca...
       ↓
    t1: d90f2734dece...
       ↓
    t2: dee751bfa277...

✅ No invariant warnings.
```

---

## List Runs

List previous authorization runs:

```bash
PYTHONPATH=src python -m agentlab.timeline list
```

---

## Show Statistics

Display aggregate statistics:

```bash
PYTHONPATH=src python -m agentlab.timeline stats
```

---

# Audit Model

The audit trail is designed around the idea that authorization is not a single event.

Instead, authorization evolves over time:

```text
Human authorization
        ↓
Token issuance
        ↓
Delegation
        ↓
Delegation
        ↓
Resource request
        ↓
Durable effect
```

Each token is represented by a cryptographic hash rather than storing the raw access token.

Conceptually:

```text
T0
 │
 │ parent_token_hash
 ▼
T1
 │
 │ parent_token_hash
 ▼
T2
 │
 ▼
Resource request
 │
 ▼
Durable effect
```

This makes it possible to reconstruct token lineage without placing raw bearer credentials into the audit database.

---

# Results

The lab successfully demonstrates:

* Delegation from Alice to `orchestrator` to `subagent` to `tool-api`.
* Multi-hop RFC 8693 token exchange.
* Token lineage tracking.
* Parent/child token relationships.
* Audience narrowing across delegation hops.
* Resource-server audience enforcement.
* Rejection of T0 and T1 at the resource server.
* Acceptance of T2 at the resource server.
* Durable synthetic effects.
* SQLite-based authorization auditing.
* Timeline reconstruction of the authorization chain.
* Controlled experiments around attribution, audience, scope, and token lifetime.

The resulting authorization history can be represented as:

```text
Alice
  │
  │ authorizes
  ▼
T0
  │
  │ exchanged by orchestrator
  ▼
T1
  │
  │ exchanged by subagent
  ▼
T2
  │
  │ presented to tool-api
  ▼
Resource Request
  │
  │ authorized
  ▼
Durable Effect
```

The key result is that authorization can be analyzed as a **timeline of state transitions**, rather than as a property of a single JWT.

---

# Limitations

This is an educational and research laboratory, not a production authorization system.

## Development Configuration

Keycloak runs in development mode and uses local credentials.

This configuration should not be deployed to production.

---

# Research Questions for Future Versions

The lab can eventually investigate deeper questions such as:

### Identity

> Can we cryptographically distinguish the human, logical agent, agent instance, and workload?

### Delegation

> Can every delegated authorization decision be traced back to its originating authority?

### Attribution

> Can we distinguish the person who authorized an action from the component that actually performed it?

### Audience

> Can a delegated token be prevented from crossing trust boundaries outside its intended audience?

### Scope

> Can delegation ever increase authority, or must authority always remain equal to or narrower than the parent?

### Time

> What happens when a parent token expires while a child token remains valid?

### Revocation

> Can previously delegated authority be reliably revoked?

### Auditability

> Can an auditor reconstruct the complete authorization history from durable records without access to the original tokens?

### AI Agents

> Does the same authorization model remain correct when agents can dynamically create subagents, delegate tasks, and perform actions asynchronously?

---

# Repository Structure

A typical repository layout is:

```text
agent-auth-lab/
├── README.md
├── compose.yaml
├── requirements.txt
│
├── data/
│   └── audit.db
│
├── docs/
│   └── week1/
│       ├── principal-map.md
│       └── experiments/
│           ├── subject-vs-actor.md
│           ├── audience-narrowing.md
│           ├── scope-expansion.md
│           └── parent-expiration.md
│
├── infra/
│   └── keycloak/
│       └── agent-lab-realm.json
│
├── scripts/
│   └── run-chain.sh
│
└── src/
    └── agentlab/
        ├── audit.py
        ├── timeline.py
        ├── tokens.py
        └── tool_api.py
```

The exact structure may vary as the lab evolves.

---

# Security Notes

This repository is intended for local experimentation.

Do not use the development configuration in a production environment.

In particular:

* Do not expose Keycloak's development admin credentials.
* Do not commit client secrets.
* Do not commit `.env` files containing credentials.
* Do not store raw bearer tokens in the audit database.
* Do not expose the local FastAPI server to an untrusted network.
* Do not treat the synthetic durable effect as a real business operation.

Recommended `.gitignore` entries:

```gitignore
.env
.venv/
__pycache__/
*.pyc
.run/
```

Depending on the repository policy, the local SQLite database may also be excluded:

```gitignore
*.db
```

