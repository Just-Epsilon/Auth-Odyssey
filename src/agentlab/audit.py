import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agentlab.config import AUDIT_DB
from agentlab.tokens import (
    decode_unverified,
    read_token,
    sha256_token,
)


app = typer.Typer(
    help="Authorization audit database utilities.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main():
    """
    Audit utilities.
    """
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,

    human_subject TEXT,
    token_subject TEXT,

    acting_client TEXT,
    logical_agent TEXT,
    agent_instance TEXT,

    parent_event_id TEXT,
    parent_token_hash TEXT,
    token_hash TEXT,

    issuer TEXT,
    authorized_party TEXT,
    audience TEXT,
    scope TEXT,

    issued_at INTEGER,
    expires_at INTEGER,

    requested_audience TEXT,
    requested_scope TEXT,

    result TEXT,
    claims_json TEXT,
    notes TEXT
);
"""


def connect():
    """
    Open the audit database and ensure its schema exists.
    """

    AUDIT_DB.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(AUDIT_DB)

    connection.row_factory = sqlite3.Row

    connection.execute(SCHEMA)
    connection.commit()

    return connection


def normalize_claim(value):
    """
    Convert JWT values such as audience arrays into strings
    suitable for SQLite.
    """

    if value is None:
        return None

    if isinstance(value, (list, dict)):
        return json.dumps(value)

    return str(value)


def create_run_id():
    """
    Create a readable run identifier.
    """

    now = datetime.now(timezone.utc)

    return now.strftime(
        "run-%Y%m%d-%H%M%S"
    )


@app.command("init-db")
def init_db():
    """
    Initialize the SQLite audit database.
    """

    connection = connect()
    connection.close()

    console.print(
        f"[green]Audit database ready:[/green] {AUDIT_DB}"
    )


@app.command("record-grant")
def record_grant(
    token_file: Path = typer.Argument(
        ...,
        help="T0 JWT file.",
    ),
    human_subject: str = typer.Option(
        "alice",
        "--human",
        help="Human principal represented by this grant.",
    ),
    run_id: str = typer.Option(
        None,
        "--run-id",
        help="Experiment run identifier.",
    ),
):
    """
    Record the initial T0 grant.
    """

    try:
        token = read_token(token_file)
        claims = decode_unverified(token)

    except Exception as exc:
        console.print(
            f"[red]Unable to inspect token:[/red] {exc}"
        )
        raise typer.Exit(code=1)

    if run_id is None:
        run_id = create_run_id()

    event_id = str(uuid.uuid4())

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    token_hash = sha256_token(token)

    connection = connect()

    connection.execute(
        """
        INSERT INTO events (
            event_id,
            run_id,
            timestamp,
            event_type,

            human_subject,
            token_subject,

            acting_client,
            logical_agent,
            agent_instance,

            parent_event_id,
            parent_token_hash,
            token_hash,

            issuer,
            authorized_party,
            audience,
            scope,

            issued_at,
            expires_at,

            requested_audience,
            requested_scope,

            result,
            claims_json,
            notes
        )
        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?
        )
        """,
        (
            event_id,
            run_id,
            timestamp,
            "GRANT",

            human_subject,
            claims.get("sub"),

            claims.get("azp"),
            None,
            None,

            None,
            None,
            token_hash,

            claims.get("iss"),
            claims.get("azp"),
            normalize_claim(
                claims.get("aud")
            ),
            normalize_claim(
                claims.get("scope")
            ),

            claims.get("iat"),
            claims.get("exp"),

            None,
            None,

            "SUCCESS",
            json.dumps(
                claims,
                sort_keys=True,
            ),
            "Initial human-subject access token T0",
        ),
    )

    connection.commit()
    connection.close()

    console.print(
        "[green]GRANT recorded.[/green]"
    )

    console.print(
        f"run_id:      {run_id}"
    )

    console.print(
        f"event_id:    {event_id}"
    )

    console.print(
        f"token_hash:  {token_hash}"
    )


@app.command("list")
def list_events():
    """
    Display authorization events.
    """

    connection = connect()

    rows = connection.execute(
        """
        SELECT
            timestamp,
            run_id,
            event_type,
            human_subject,
            token_subject,
            acting_client,
            audience,
            result,
            token_hash
        FROM events
        ORDER BY timestamp
        """
    ).fetchall()

    connection.close()

    if not rows:
        console.print(
            "[yellow]No audit events yet.[/yellow]"
        )
        return

    table = Table(
        title="Authorization Audit Events"
    )

    table.add_column("Event")
    table.add_column("Run")
    table.add_column("Human")
    table.add_column("Token subject")
    table.add_column("Client")
    table.add_column("Audience")
    table.add_column("Result")
    table.add_column("Token hash")

    for row in rows:
        table.add_row(
            row["event_type"],
            row["run_id"],
            row["human_subject"] or "-",
            row["token_subject"] or "-",
            row["acting_client"] or "-",
            row["audience"] or "-",
            row["result"] or "-",
            (
                row["token_hash"][:12] + "..."
                if row["token_hash"]
                else "-"
            ),
        )

    console.print(table)


if __name__ == "__main__":
    app()
