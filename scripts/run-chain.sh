#!/bin/bash
set -e

# ============================================================================
# run-chain.sh — Complete authorization chain from Alice to durable effect
#
# Output: RUN_ID (only) on stdout, all diagnostics on stderr
# ============================================================================

# Generate a unique run ID
RUN_ID=$(date +"run-%Y%m%d-%H%M%S")
export RUN_ID

# Redirect all diagnostic output to stderr
# (stdout is reserved for the final RUN_ID)

echo "============================================================" >&2
echo "  run-chain.sh started at $(date)" >&2
echo "  RUN_ID: $RUN_ID" >&2
echo "============================================================" >&2

# --------------------------------------------------------------------------
# 1. Obtain T0 (human subject token)
# --------------------------------------------------------------------------
echo "  [1/7] Obtaining T0 (Alice's token)..." >&2
./scripts/get-user-token.sh
if [ ! -f .run/t0.jwt ]; then
    echo "ERROR: Failed to obtain T0" >&2
    exit 1
fi
echo "  ✓ T0 obtained" >&2

# --------------------------------------------------------------------------
# 2. Record GRANT event
# --------------------------------------------------------------------------
echo "  [2/7] Recording GRANT event..." >&2
PYTHONPATH=src python -m agentlab.audit record-grant .run/t0.jwt \
    --human alice \
    --run-id "$RUN_ID" >&2
echo "  ✓ GRANT recorded" >&2

# --------------------------------------------------------------------------
# 3. Exchange T0 → T1 (orchestrator)
# --------------------------------------------------------------------------
echo "  [3/7] Exchanging T0 → T1 (orchestrator)..." >&2
if [ -z "$ORCHESTRATOR_SECRET" ]; then
    echo "ERROR: ORCHESTRATOR_SECRET environment variable not set" >&2
    exit 1
fi
./scripts/exchange-orchestrator.sh >&2
if [ ! -f .run/t1.jwt ]; then
    echo "ERROR: Failed to obtain T1" >&2
    exit 1
fi
echo "  ✓ T1 obtained" >&2

# --------------------------------------------------------------------------
# 4. Record TOKEN_EXCHANGE T0 → T1
# --------------------------------------------------------------------------
echo "  [4/7] Recording TOKEN_EXCHANGE (orchestrator)..." >&2
PYTHONPATH=src python -m agentlab.audit record-exchange \
    .run/t0.jwt .run/t1.jwt \
    --actor orchestrator \
    --run-id "$RUN_ID" >&2
echo "  ✓ TOKEN_EXCHANGE T0→T1 recorded" >&2

# --------------------------------------------------------------------------
# 5. Exchange T1 → T2 (subagent)
# --------------------------------------------------------------------------
echo "  [5/7] Exchanging T1 → T2 (subagent)..." >&2
if [ -z "$SUBAGENT_SECRET" ]; then
    echo "ERROR: SUBAGENT_SECRET environment variable not set" >&2
    exit 1
fi
./scripts/ex_subagent.sh >&2
if [ ! -f .run/t2.jwt ]; then
    echo "ERROR: Failed to obtain T2" >&2
    exit 1
fi
echo "  ✓ T2 obtained" >&2

# --------------------------------------------------------------------------
# 6. Record TOKEN_EXCHANGE T1 → T2
# --------------------------------------------------------------------------
echo "  [6/7] Recording TOKEN_EXCHANGE (subagent)..." >&2
PYTHONPATH=src python -m agentlab.audit record-exchange \
    .run/t1.jwt .run/t2.jwt \
    --actor subagent \
    --run-id "$RUN_ID" >&2
echo "  ✓ TOKEN_EXCHANGE T1→T2 recorded" >&2

# --------------------------------------------------------------------------
# 7. Call the protected resource (/effect) with T2
#    This automatically records:
#      - RESOURCE_REQUEST (audit.py)
#      - DURABLE_EFFECT (effects.py)
# --------------------------------------------------------------------------
echo "  [7/7] Calling /effect with T2..." >&2
T2=$(cat .run/t2.jwt)
response=$(curl -s -X POST http://127.0.0.1:8000/effect \
    -H "Authorization: Bearer $T2" \
    -H "Content-Type: application/json" \
    -d '{"operation":"mark_test_order_reviewed","order_id":"ORDER-001"}')

# Check if the call succeeded
if echo "$response" | grep -q '"result":"ALLOW"'; then
    echo "  ✓ /effect call succeeded" >&2
else
    echo "ERROR: /effect call failed with response: $response" >&2
    exit 1
fi

# --------------------------------------------------------------------------
# 8. Print the RUN_ID (stdout only)
# --------------------------------------------------------------------------
echo "============================================================" >&2
echo "  ✅ run-chain.sh completed successfully at $(date)" >&2
echo "  RUN_ID: $RUN_ID" >&2
echo "  Use: python -m agentlab.timeline show $RUN_ID" >&2
echo "============================================================" >&2

# This is the ONLY output to stdout
echo "$RUN_ID"

