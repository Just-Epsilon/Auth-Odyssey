# scripts/security_jwt.py

import jwt
from jwt import PyJWKClient

ISSUER = "http://127.0.0.1:8080/realms/agent-lab"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"
AUDIENCE = "tool-api"

jwks_client = PyJWKClient(JWKS_URL)


def verify_tool_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={
            "require": ["exp", "iat", "iss", "sub"],
        },
    )

    return claims
