import sqlite3
import uuid
from datetime import datetime, timezone
from agentlab.config import AUDIT_DB

def persist_effect(claims: dict, event_id: str, operation: str, order_id: str, run_id: str = "unknown") -> dict:
    """
    Create a durable synthetic effect linked to an audit event.
    
    Args:
        claims: Decoded JWT claims (sub, azp, etc.)
        event_id: The ID of the RESOURCE_REQUEST audit event
        operation: The operation to perform (e.g., "mark_test_order_reviewed")
        order_id: The order ID to apply the operation to
        run_id: The run ID for the experiment
    
    Returns:
        dict: effect_id, operation, order_id, timestamp
    """
    effect_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(AUDIT_DB) as conn:
        # Create the effects table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS effects (
                effect_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                run_id TEXT,
                order_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                subject TEXT NOT NULL,
                authorized_party TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # Insert the effect
        conn.execute(
            """
            INSERT INTO effects (
                effect_id,
                event_id,
                run_id,
                order_id,
                operation,
                subject,
                authorized_party,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                effect_id,
                event_id,
                run_id,
                order_id,
                operation,
                claims["sub"],
                claims.get("azp"),
                timestamp,
            ),
        )

    return {
        "effect_id": effect_id,
        "operation": operation,
        "order_id": order_id,
        "timestamp": timestamp,
    }
