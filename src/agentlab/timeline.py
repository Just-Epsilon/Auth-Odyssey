
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from agentlab.config import AUDIT_DB

app = typer.Typer(
    name="timeline",
    help="Display authorization timeline from audit database",
    no_args_is_help=True,
)
console = Console()


def get_events(run_id: str) -> List[sqlite3.Row]:
    """
    Fetch all events for a given run_id, ordered by timestamp.
    """
    if not AUDIT_DB.exists():
        console.print(f"[red]Audit database not found: {AUDIT_DB}[/red]")
        return []

    conn = sqlite3.connect(AUDIT_DB)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(
        """
        SELECT 
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
        FROM events
        WHERE run_id = ?
        ORDER BY timestamp ASC
        """,
        (run_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_run_ids() -> List[str]:
    """
    Get all unique run_ids from the audit database.
    """
    if not AUDIT_DB.exists():
        return []

    conn = sqlite3.connect(AUDIT_DB)
    cursor = conn.execute(
        """
        SELECT DISTINCT run_id, COUNT(*) as count, MIN(timestamp) as first
        FROM events
        GROUP BY run_id
        ORDER BY first DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def format_timestamp(ts: Optional[str]) -> str:
    """
    Format ISO timestamp for display.
    """
    if not ts:
        return "-"
    try:
        # Handle various timestamp formats
        if 'T' in ts:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except:
        return ts[:16] if len(ts) > 16 else ts


def format_short_hash(hash_value: Optional[str]) -> str:
    """
    Shorten a token hash for display.
    """
    if not hash_value:
        return "-"
    return hash_value[:12] + "..." if len(hash_value) > 12 else hash_value


def format_short_subject(subject: Optional[str]) -> str:
    """
    Shorten a subject ID for display.
    """
    if not subject:
        return "-"
    return subject[:16] + "..." if len(subject) > 16 else subject


def render_event(event: sqlite3.Row, index: int) -> None:
    """
    Render a single event to the console.
    """
    event_type = event["event_type"]
    timestamp = format_timestamp(event["timestamp"])
    
    # Event header
    console.print(f"\n[bold cyan]t{index}[/bold cyan]  [bold yellow]{event_type}[/bold yellow]  [dim]{timestamp}[/dim]")
    
    # Render based on event type
    if event_type == "GRANT":
        console.print(f"    [dim]human:[/dim]       {event['human_subject'] or '-'}")
        console.print(f"    [dim]client:[/dim]      {event['acting_client'] or '-'}")
        console.print(f"    [dim]token:[/dim]       {format_short_hash(event['token_hash'])}")
        console.print(f"    [dim]subject:[/dim]     {format_short_subject(event['token_subject'])}")
        console.print(f"    [dim]audience:[/dim]    {event['audience'] or '-'}")
        if event["scope"]:
            console.print(f"    [dim]scope:[/dim]      {event['scope']}")
        console.print(f"    [dim]result:[/dim]      [green]{event['result'] or '-'}[/green]")
        
    elif event_type == "TOKEN_EXCHANGE":
        console.print(f"    [dim]actor:[/dim]       {event['acting_client'] or '-'}")
        console.print(f"    [dim]instance:[/dim]    {event['agent_instance'] or '-'}")
        console.print(f"    [dim]subject:[/dim]     {format_short_subject(event['token_subject'])}")
        if event["parent_token_hash"]:
            console.print(f"    [dim]parent:[/dim]     {format_short_hash(event['parent_token_hash'])}")
        console.print(f"    [dim]token:[/dim]       {format_short_hash(event['token_hash'])}")
        console.print(f"    [dim]audience:[/dim]    {event['audience'] or '-'}")
        if event["scope"]:
            console.print(f"    [dim]scope:[/dim]      {event['scope']}")
        console.print(f"    [dim]result:[/dim]      [green]{event['result'] or '-'}[/green]")
        if event["notes"]:
            console.print(f"    [dim]note:[/dim]       {event['notes']}")
        
    elif event_type == "RESOURCE_REQUEST":
        console.print(f"    [dim]resource:[/dim]    {event['audience'] or '-'}")
        console.print(f"    [dim]token:[/dim]       {format_short_hash(event['token_hash'])}")
        console.print(f"    [dim]actor:[/dim]       {event['acting_client'] or '-'}")
        console.print(f"    [dim]subject:[/dim]     {format_short_subject(event['token_subject'])}")
        result = event['result']
        if result == "ALLOW":
            console.print(f"    [dim]result:[/dim]      [green]{result}[/green]")
        else:
            console.print(f"    [dim]result:[/dim]      [red]{result}[/red]")
        
    elif event_type == "RESOURCE_REJECTION":
        console.print(f"    [dim]resource:[/dim]    {event['audience'] or '-'}")
        console.print(f"    [dim]token:[/dim]       {format_short_hash(event['token_hash'])}")
        console.print(f"    [dim]reason:[/dim]      {event['result'] or 'denied'}")
        if event["notes"]:
            console.print(f"    [dim]detail:[/dim]     {event['notes']}")
        
    elif event_type == "DURABLE_EFFECT":
        console.print(f"    [dim]operation:[/dim]   {event['notes'] or 'effect created'}")
        console.print(f"    [dim]subject:[/dim]     {format_short_subject(event['token_subject'])}")
        console.print(f"    [dim]actor:[/dim]       {event['acting_client'] or '-'}")
        
    elif event_type == "TOKEN_EXPIRED":
        console.print(f"    [dim]token:[/dim]       {format_short_hash(event['token_hash'])}")
        if event["expires_at"]:
            console.print(f"    [dim]expired at:[/dim]  {format_timestamp(event['expires_at'])}")
        console.print(f"    [dim]result:[/dim]      [red]EXPIRED[/red]")
        
    else:
        # Generic render for unknown event types
        for key in ["human_subject", "token_subject", "acting_client", "audience", "result"]:
            if event[key]:
                console.print(f"    [dim]{key}:[/dim]       {event[key]}")


def check_invariants(events: List[sqlite3.Row]) -> List[str]:
    """
    Check for broken relationships in the timeline.
    """
    warnings = []
    
    # Collect all token hashes from this run
    token_hashes = set()
    for event in events:
        if event["token_hash"]:
            token_hashes.add(event["token_hash"])
    
    # Check parent references exist
    for event in events:
        parent_hash = event["parent_token_hash"]
        if parent_hash and parent_hash not in token_hashes:
            warnings.append(
                f"⚠️  Parent token {format_short_hash(parent_hash)} not found in this run"
            )
    
    # Check DURABLE_EFFECT has a prior RESOURCE_REQUEST
    resource_requests = [e for e in events if e["event_type"] == "RESOURCE_REQUEST"]
    effects = [e for e in events if e["event_type"] == "DURABLE_EFFECT"]
    
    if effects and not resource_requests:
        warnings.append(
            "⚠️  DURABLE_EFFECT exists without prior RESOURCE_REQUEST"
        )
    
    return warnings


def render_token_lineage(events: List[sqlite3.Row]) -> None:
    """
    Display the token lineage as a visual chain.
    """
    # Build parent-child relationships
    lineage = {}
    for event in events:
        child_hash = event["token_hash"]
        parent_hash = event["parent_token_hash"]
        if child_hash and parent_hash:
            lineage[parent_hash] = child_hash
    
    if not lineage:
        return
    
    console.print("\n[bold]Token lineage:[/bold]")
    
    # Find the root (no parent) or use the first token
    all_parents = set(lineage.keys())
    all_children = set(lineage.values())
    roots = all_parents - all_children
    
    if roots:
        start_hash = list(roots)[0]
    elif lineage:
        start_hash = list(lineage.keys())[0]
    else:
        return
    
    # Walk the chain
    current = start_hash
    step = 0
    while current:
        console.print(f"    [dim]t{step}:[/dim] {format_short_hash(current)}")
        if current in lineage:
            current = lineage[current]
            step += 1
        else:
            break
    
    console.print()


@app.command("show")
def show_timeline(
    run_id: str = typer.Argument(..., help="Run ID to display"),
    show_invariants: bool = typer.Option(True, "--invariants/--no-invariants", help="Check invariants"),
):
    """
    Display the authorization timeline for a specific run.
    """
    events = get_events(run_id)
    
    if not events:
        console.print(f"[red]No events found for run_id: {run_id}[/red]")
        console.print("\nUse 'timeline list' to see available runs.")
        return
    
    console.print(f"\n[bold cyan]📋 Authorization Timeline — {run_id}[/bold cyan]")
    console.print(f"[dim]Events: {len(events)}[/dim]")
    
    # Render each event
    for i, event in enumerate(events):
        render_event(event, i)
    
    # Show token lineage
    render_token_lineage(events)
    
    # Check invariants
    if show_invariants:
        warnings = check_invariants(events)
        if warnings:
            console.print("\n[bold yellow]⚠️  Invariant warnings:[/bold yellow]")
            for warning in warnings:
                console.print(f"    {warning}")
        else:
            console.print("\n[green]✅ No invariant warnings.[/green]")


@app.command("list")
def list_runs(
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum runs to show"),
):
    """
    List all available run_ids in the audit database.
    """
    runs = get_all_run_ids()
    
    if not runs:
        console.print("[yellow]No runs found in audit database.[/yellow]")
        console.print("\nRecord a GRANT first:")
        console.print("  python -m agentlab.audit record-grant .run/t0.jwt")
        return
    
    table = Table(title="Available Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Events", style="green")
    table.add_column("First Event", style="dim")
    
    for run_id, count, first in runs[:limit]:
        table.add_row(
            run_id,
            str(count),
            first[:16] if first else "-"
        )
    
    console.print(table)
    
    if len(runs) > limit:
        console.print(f"[dim]... and {len(runs) - limit} more[/dim]")


@app.command("stats")
def show_stats(
    run_id: Optional[str] = typer.Argument(None, help="Run ID (optional, shows all runs)"),
):
    """
    Show statistics about a run or all runs.
    """
    if run_id:
        events = get_events(run_id)
        if not events:
            console.print(f"[red]No events found for run_id: {run_id}[/red]")
            return
        
        event_types = {}
        for event in events:
            et = event["event_type"]
            event_types[et] = event_types.get(et, 0) + 1
        
        console.print(f"[bold]Statistics for: {run_id}[/bold]")
        console.print(f"Total events: {len(events)}")
        console.print("\n[bold]Event types:[/bold]")
        for et, count in sorted(event_types.items()):
            console.print(f"    {et}: {count}")
    else:
        runs = get_all_run_ids()
        console.print(f"[bold]Total runs: {len(runs)}[/bold]")
        console.print(f"Total events: {sum(r[1] for r in runs)}")


if __name__ == "__main__":
    app()

