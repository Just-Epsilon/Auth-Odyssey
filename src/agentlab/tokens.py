from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

import jwt
import typer
from rich.console import Console
from rich.table import Table


app = typer.Typer(
    help="Inspect tokens used in the authorization lab.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main():
    """
    Token utilities.
    """
    pass


def read_token(token_file: Path) -> str:
    """Read a bearer token from disk."""

    if not token_file.exists():
        raise ValueError(f"Token file does not exist: {token_file}")

    token = token_file.read_text().strip()

    if not token:
        raise ValueError(f"Token file is empty: {token_file}")

    return token


def decode_unverified(token: str) -> dict:
    """
    Decode JWT claims WITHOUT cryptographically verifying the token.

    This is intentional for Day 2 claim inspection.
    Real verification is added to tool-api later.
    """

    return jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
        },
    )


def sha256_token(token: str) -> str:
    """
    Return a stable identifier for a token without storing
    the bearer credential itself.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def format_timestamp(value):
    if value is None:
        return "-"

    try:
        timestamp = int(value)

        readable = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).isoformat()

        return f"{timestamp}  ({readable})"

    except (TypeError, ValueError):
        return str(value)


def format_claim(value):
    if value is None:
        return "-"

    if isinstance(value, (list, dict)):
        return json.dumps(value)

    return str(value)


@app.command("inspect")
def inspect_token(
    token_file: Path = typer.Argument(
        ...,
        help="File containing the JWT access token.",
    ),
):
    """
    Inspect important authorization claims.
    """

    try:
        token = read_token(token_file)
        claims = decode_unverified(token)

    except (ValueError, jwt.PyJWTError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    table = Table(
        title="JWT Claims — UNVERIFIED"
    )

    table.add_column("Claim")
    table.add_column("Value")

    claims_to_show = [
        "iss",
        "sub",
        "azp",
        "aud",
        "scope",
        "iat",
        "exp",
        "sid",
        "session_state",
    ]

    for name in claims_to_show:
        value = claims.get(name)

        if name in {"iat", "exp"}:
            value = format_timestamp(value)
        else:
            value = format_claim(value)

        table.add_row(name, value)

    table.add_row(
        "sha256",
        sha256_token(token),
    )

    console.print(table)


@app.command("hash")
def hash_token(
    token_file: Path = typer.Argument(...),
):
    """
    Print SHA-256 of a token.
    """

    try:
        token = read_token(token_file)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(sha256_token(token))


if __name__ == "__main__":
    app()
