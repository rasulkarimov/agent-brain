"""Who is calling.

- MCP clients (Claude Code, Codex, Copilot) sign in to Keycloak themselves (OAuth with PKCE) and send the
  access token; it is checked here against the realm's keys, issuer and audience. No token is passed on.
- Platforms (AgentGate's gateway) hold a shared key and act on behalf of the user they verified themselves;
  the call is recorded as that user through that platform.
- The console sits behind oauth2-proxy, which sets the user and groups headers; only it reaches that port.
- dev mode (laptop): the user name comes from a header, every one is an admin.
"""
from __future__ import annotations

import asyncio
import hmac
import time
from dataclasses import dataclass
from typing import Any

import jwt
from mcp.server.auth.provider import AccessToken
from starlette.requests import Request

from .settings import Settings
from .store import BrainError, Caller

DEV_USER_HEADER = "x-brain-dev-user"
PLATFORM_USER_HEADER = "x-brain-user"
PLATFORM_GROUPS_HEADER = "x-brain-groups"


def groups_of(claims: dict[str, Any]) -> frozenset[str]:
    return frozenset(str(g).strip().lstrip("/") for g in claims.get("groups") or [] if str(g).strip())


@dataclass
class KeycloakVerifier:
    """MCP TokenVerifier: a Keycloak access token issued for this audience, signature checked against the realm's JWKS."""
    settings: Settings
    _jwks: jwt.PyJWKClient | None = None

    def __post_init__(self) -> None:
        if self.settings.issuer:
            self._jwks = jwt.PyJWKClient(f"{self.settings.issuer}/protocol/openid-connect/certs", cache_keys=True,
                                         lifespan=3600, timeout=10)

    def _decode(self, token: str) -> dict[str, Any]:
        assert self._jwks is not None
        key = self._jwks.get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["RS256", "ES256", "PS256"], audience=self.settings.audience,
                          issuer=self.settings.issuer, options={"require": ["exp", "iss", "sub"]})

    async def verify_token(self, token: str) -> AccessToken | None:
        if self._jwks is None:
            return None
        try:
            claims = await asyncio.to_thread(self._decode, token)
        except (jwt.PyJWTError, OSError):
            return None
        return AccessToken(token=token, client_id=str(claims.get("azp") or "unknown"),
                           scopes=str(claims.get("scope", "")).split(), expires_at=int(claims["exp"]),
                           subject=str(claims["sub"]), claims=claims)


@dataclass
class DevVerifier:
    """dev mode: the bearer token is the user name. Never on a shared host."""

    async def verify_token(self, token: str) -> AccessToken | None:
        return AccessToken(token=token, client_id="dev", scopes=[], expires_at=int(time.time()) + 3600,
                           subject=token, claims={"preferred_username": token, "groups": []})


def client_name(headers: Any, fallback: str) -> str:
    ua = (headers.get("user-agent") or "").split(" ")[0].split("/")[0] if headers else ""
    return f"{fallback}/{ua}" if ua and ua.lower() not in fallback.lower() else fallback


def caller_from_token(settings: Settings, token: AccessToken | None, headers: Any) -> Caller:
    if token is None or not token.claims:
        raise BrainError("not signed in")
    c = token.claims
    user = str(c.get("preferred_username") or c.get("sub"))
    groups = groups_of(c)
    return Caller(user, groups, client_name(headers, token.client_id), "mcp", settings.admin_group in groups,
                  (headers.get("mcp-session-id") if headers else None))


def platform_caller(settings: Settings, request: Request) -> Caller:
    auth = request.headers.get("authorization", "")
    key = auth.removeprefix("Bearer ").strip()
    name = next((n for n, k in settings.platform_keys.items() if key and hmac.compare_digest(k, key)), None)
    if name is None:
        raise BrainError("unknown platform key")
    user = request.headers.get(PLATFORM_USER_HEADER, "").strip()
    if not user:
        raise BrainError(f"a platform acts on behalf of a user: send {PLATFORM_USER_HEADER}")
    groups = frozenset(g.strip() for g in request.headers.get(PLATFORM_GROUPS_HEADER, "").split(",") if g.strip())
    session = request.headers.get("x-brain-session") or None
    return Caller(user, groups, name, "platform", False, session)


def console_caller(settings: Settings, request: Request) -> Caller:
    if settings.auth_mode == "dev":
        name = (request.headers.get(DEV_USER_HEADER) or request.query_params.get("dev_user") or "").strip()
        if not name:
            raise BrainError(f"dev mode: send the {DEV_USER_HEADER} header")
        return Caller(name, frozenset(), "console", "console", True)
    name = request.headers.get(settings.user_header, "").strip()
    if not name:
        raise BrainError("not signed in")
    groups = frozenset(g.strip().lstrip("/") for g in request.headers.get(settings.groups_header, "").split(",") if g.strip())
    return Caller(name, groups, "console", "console", settings.admin_group in groups)
