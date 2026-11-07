"""The console: browse the memory, review sessions, roll one back, edit instruction files, read the audit.

Served on its own port behind oauth2-proxy (NetworkPolicy lets only it in), so the user headers are trusted.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from .auth import console_caller
from .settings import Settings
from .store import BrainError, Caller, Store

STATIC = Path(__file__).parent / "static"


def create_console(settings: Settings, store: Store) -> Starlette:
    async def handle(request: Request, tool: str, fn: Any, audit: bool = False) -> JSONResponse:
        started, caller = time.monotonic(), None
        try:
            caller = console_caller(settings, request)
            result = await fn(caller)
            if audit:
                await store.record(caller, tool, dict(request.query_params), "ok", None,
                                   result.get("changeset") if isinstance(result, dict) else None,
                                   int((time.monotonic() - started) * 1000))
            return JSONResponse(result)
        except BrainError as exc:
            if audit and caller:
                await store.record(caller, tool, dict(request.query_params), "refused", str(exc), None,
                                   int((time.monotonic() - started) * 1000))
            return JSONResponse({"error": str(exc)}, status_code=403 if "may not" in str(exc) or "only" in str(exc) else 400)

    async def index(_: Request) -> FileResponse:
        return FileResponse(STATIC / "index.html")

    async def me(request: Request) -> JSONResponse:
        async def fn(c: Caller) -> dict[str, Any]:
            return {"user": c.user, "admin": c.admin, "groups": sorted(c.groups), "workspaces": await store.readable(c),
                    "stats": await store.stats(), "run_url": settings.run_url}
        return await handle(request, "me", fn)

    async def tree(request: Request) -> JSONResponse:
        return await handle(request, "tree", lambda c: store.tree(c, request.query_params.get("path", ""), 1000))

    async def doc(request: Request) -> JSONResponse:
        q = request.query_params
        version = int(q["version"]) if q.get("version") else None

        async def fn(c: Caller) -> dict[str, Any]:
            d = await store.read(c, q["path"], None, version)
            d["history"] = await store.history(c, q["path"])
            return d
        return await handle(request, "read", fn)

    async def graph(request: Request) -> JSONResponse:
        return await handle(request, "graph", lambda c: store.graph(c))

    async def search(request: Request) -> JSONResponse:
        return await handle(request, "search", lambda c: store.search(c, request.query_params.get("q", ""), limit=30))

    async def sessions(request: Request) -> JSONResponse:
        return await handle(request, "sessions", lambda c: store.changesets_list(c, 100))

    async def session(request: Request) -> JSONResponse:
        return await handle(request, "session", lambda c: store.changeset_detail(c, request.path_params["cid"]))

    async def rollback(request: Request) -> JSONResponse:
        return await handle(request, "rollback", lambda c: store.rollback(c, request.path_params["cid"]), audit=True)

    async def instructions(request: Request) -> JSONResponse:
        body = await request.json()

        async def fn(c: Caller) -> dict[str, Any]:
            return await store.set_instructions(c, body["path"], body["body"], body.get("base_version"))
        return await handle(request, "set_instructions", fn, audit=True)

    async def audit(request: Request) -> JSONResponse:
        async def fn(c: Caller) -> list[dict[str, Any]]:
            return await store.audit_list(300, None if c.admin else c.user)
        return await handle(request, "audit", fn)

    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return Starlette(routes=[
        Route("/", index), Route("/healthz", healthz),
        Route("/api/me", me), Route("/api/tree", tree), Route("/api/doc", doc), Route("/api/search", search), Route("/api/graph", graph),
        Route("/api/sessions", sessions), Route("/api/sessions/{cid}", session),
        Route("/api/sessions/{cid}/rollback", rollback, methods=["POST"]),
        Route("/api/instructions", instructions, methods=["PUT"]), Route("/api/audit", audit),
    ])
