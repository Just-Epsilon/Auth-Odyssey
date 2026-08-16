#!/usr/bin/env python3
"""
Log the full authorization timeline:
- GRANT (T0)
- TOKEN_EXCHANGE (T0 → T1)
- TOKEN_EXCHANGE (T1 → T2)
"""
import sqlite3
import json
import jwt
import hashlib
import uuid
from datetime import datetime
import os

# Configuration
DB_PATH = "audit.db"
RUN_ID = "run-001"  # change this for each run

TOKEN_FILES = {
    "t0": ".run/t0.jwt",
    "t1": ".run/t1.jwt",
    "t2": ".run/t2.jwt",
}

def sha256_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def decode_token(path):
    with open(path) as f:
        token = f.read().strip()  # remove whitespace
    decoded = jwt.decode(token, options={"verify_signature": False})
    return token, decoded

# Read tokens
t0_raw, t0_dec = decode_token(TOKEN_FILES["t0"])
t1_raw, t1_dec = decode_token(TOKEN_FILES["t1"])
t2_raw, t2_dec = decode_token(TOKEN_FILES["t2"])

# Compute hashes
h0 = sha256_token(t0_raw)
h1 = sha256_token(t1_raw)
h2 = sha256_token(t2_raw)

# Connect to database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Helper to insert an event
def insert_event(
    event_type,
    human_subject,
    token_subject,
    acting_client,
    logical_agent,
    agent_instance,
    parent_token_hash,
    token_hash,
    issuer,
    authorized_party,
    audience,
    scope,
    issued_at,
    expires_at,
    requested_audience=None,
    requested_scope=None,
    result="SUCCESS",
    claims_json=None,
    notes=None
):
    event_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO events (
            event_id, run_id, timestamp, event_type,
            human_subject, token_subject,
            acting_client, logical_agent, agent_instance,
            parent_token_hash, token_hash,
            issuer, authorized_party, audience, scope,
            issued_at, expires_at,
            requested_audience, requested_scope,
            result, claims_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id, RUN_ID, timestamp, event_type,
        human_subject, token_subject,
        acting_client, logical_agent, agent_instance,
        parent_token_hash, token_hash,
        issuer, authorized_party, audience, scope,
        issued_at, expires_at,
        requested_audience, requested_scope,
        result, json.dumps(claims_json) if claims_json else None, notes
    ))

# 1. GRANT – Alice gets T0 via entry-cli
insert_event(
    event_type="GRANT",
    human_subject="alice",
    token_subject=t0_dec.get("sub"),
    acting_client="entry-cli",
    logical_agent=None,
    agent_instance=None,
    parent_token_hash=None,   # no parent
    token_hash=h0,
    issuer=t0_dec.get("iss"),
    authorized_party=t0_dec.get("azp"),
    audience=", ".join(t0_dec.get("aud", [])),
    scope=t0_dec.get("scope"),
    issued_at=t0_dec.get("iat"),   # Unix timestamp
    expires_at=t0_dec.get("exp"),  # Unix timestamp
    requested_audience=None,
    requested_scope=None,
    claims_json=t0_dec,
    notes="Initial grant for alice"
)

# 2. TOKEN_EXCHANGE – T0 → T1 (orchestrator)
insert_event(
    event_type="TOKEN_EXCHANGE",
    human_subject="alice",
    token_subject=t1_dec.get("sub"),
    acting_client="orchestrator",
    logical_agent="orchestrator-agent",
    agent_instance="orch-01",
    parent_token_hash=h0,         # T1's parent is T0
    token_hash=h1,
    issuer=t1_dec.get("iss"),
    authorized_party=t1_dec.get("azp"),
    audience=", ".join(t1_dec.get("aud", [])),
    scope=t1_dec.get("scope"),
    issued_at=t1_dec.get("iat"),
    expires_at=t1_dec.get("exp"),
    requested_audience="subagent",   # what we asked for
    requested_scope=None,
    claims_json=t1_dec,
    notes="Orchestrator delegates to subagent"
)

# 3. TOKEN_EXCHANGE – T1 → T2 (subagent)
insert_event(
    event_type="TOKEN_EXCHANGE",
    human_subject="alice",
    token_subject=t2_dec.get("sub"),
    acting_client="subagent",
    logical_agent="research-subagent",
    agent_instance="sub-01",
    parent_token_hash=h1,         # T2's parent is T1
    token_hash=h2,
    issuer=t2_dec.get("iss"),
    authorized_party=t2_dec.get("azp"),
    audience=", ".join(t2_dec.get("aud", [])),
    scope=t2_dec.get("scope"),
    issued_at=t2_dec.get("iat"),
    expires_at=t2_dec.get("exp"),
    requested_audience="tool-api",   # what we asked for
    requested_scope=None,
    claims_json=t2_dec,
    notes="Subagent delegates to tool-api"
)

conn.commit()
conn.close()

print(f"✅ Timeline logged for RUN_ID={RUN_ID}")
print(f"   T0 hash: {h0[:16]}...")
print(f"   T1 hash: {h1[:16]}... (parent: {h0[:16]}...)")
print(f"   T2 hash: {h2[:16]}... (parent: {h1[:16]}...)")
print("\nRun this to view the chain:")
print("sqlite3 audit.db \"SELECT event_type, acting_client, substr(token_hash,1,16) as token, substr(parent_token_hash,1,16) as parent FROM events WHERE run_id='run-001' ORDER BY event_id;\"")
