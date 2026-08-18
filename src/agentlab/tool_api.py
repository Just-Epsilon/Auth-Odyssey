from typing import Annotated
import os
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import jwt

from agentlab.security_jwt import verify_tool_token
from agentlab.audit import create_resource_request_event
from agentlab.effects import persist_effect

app = FastAPI(title="agent-auth-lab tool-api")

bearer = HTTPBearer()

# Define the request body schema
class EffectRequest(BaseModel):
    operation: str
    order_id: str


def require_tool_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer),
    ],
) -> dict:
    token = credentials.credentials

    try:
        return verify_tool_token(token)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
        )

    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token not intended for tool-api",
        )

    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid issuer",
        )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/effect")
def create_effect(
    claims: Annotated[dict, Depends(require_tool_token)],
    request: EffectRequest,
):
    """
    Protected endpoint that:
    1. Verifies the token (via require_tool_token)
    2. Creates a RESOURCE_REQUEST audit event
    3. Creates a durable effect linked to that event
    4. Returns the result
    """
    # Get run_id from environment or generate one
    run_id = os.getenv("RUN_ID", f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}")
    
    # Step 1: Create the RESOURCE_REQUEST audit event
    event_id = create_resource_request_event(claims, run_id)
    
    # Step 2: Create the durable effect linked to the event
    effect = persist_effect(
        claims=claims,
        event_id=event_id,
        operation=request.operation,
        order_id=request.order_id,
        run_id=run_id
    )

    # Step 3: Return response
    return {
        "result": "ALLOW",
        "message": f"Effect applied to order '{request.order_id}'",
        "effect": effect,
        "subject": claims.get("sub"),
        "authorized_party": claims.get("azp")
    }
