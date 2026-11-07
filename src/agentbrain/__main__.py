"""Run agentBrain: MCP and the platform API on one port, the console on another."""
from __future__ import annotations

import asyncio
import logging

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings

from .console import create_console
from .server import create_server
from .settings import Settings
from .store import Store, engine_from_url

log = logging.getLogger("agentbrain")


async def serve(settings: Settings) -> None:
    engine = engine_from_url(settings.database_url)
    store = Store(engine, settings.workspaces)
    await store.init()
    log.info("auth: %s%s; platforms: %s", settings.auth_mode, f" ({settings.issuer}, audience {settings.audience})"
             if settings.auth_mode == "keycloak" else "", ", ".join(settings.platform_keys) or "none")
    if settings.auth_mode == "dev" and settings.host not in ("127.0.0.1", "localhost"):
        log.warning("dev mode on %s: anyone who reaches it is anyone they say they are", settings.host)

    security = None
    if settings.allowed_hosts:
        security = TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                             allowed_hosts=["127.0.0.1:*", "localhost:*", *settings.allowed_hosts],
                                             allowed_origins=[])
    mcp_app = create_server(settings, store).streamable_http_app(stateless_http=True, transport_security=security,
                                                                 host=settings.host)
    console = create_console(settings, store)
    servers = [uvicorn.Server(uvicorn.Config(mcp_app, host=settings.host, port=settings.port, log_level="info")),
               uvicorn.Server(uvicorn.Config(console, host=settings.host, port=settings.console_port, log_level="info"))]
    try:
        await asyncio.gather(*(s.serve() for s in servers))
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(serve(Settings.from_env()))


if __name__ == "__main__":
    main()
