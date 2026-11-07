"""The memory: workspaces of documents and notes, versions, changesets, audit.

Every write belongs to a changeset (one session = one change). Versions are append-only;
a rollback writes new versions that restore what was there before, in a changeset of its own.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import (JSON, BigInteger, Boolean, Column, DateTime, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, and_, func, insert, or_, select, update)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from .redact import redact
from .settings import AGENTS_DEFAULT, CORE_DEFAULT, Workspace

log = logging.getLogger("agentbrain.store")

NOTE_KINDS = ("finding", "decision", "handover", "runbook-gap", "event")
KINDS = ("document", *NOTE_KINDS)
INSTRUCTION_FILES = ("CORE.md", "AGENTS.md")
NOTE_MAX = 4_000
DOC_MAX = 200_000
ID = BigInteger().with_variant(Integer, "sqlite")

metadata = MetaData()

workspaces = Table(
    "workspaces", metadata,
    Column("name", String(200), primary_key=True),
    Column("title", String(200), nullable=False),
    Column("readers", JSON, nullable=False),
    Column("writers", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

changesets = Table(
    "changesets", metadata,
    Column("id", String(40), primary_key=True),
    Column("key", String(400), nullable=False, index=True),  # user|client|session: finds the open one
    Column("user_id", String(200), nullable=False),
    Column("client", String(200), nullable=False),
    Column("task", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("rolled_back_at", DateTime(timezone=True)),
    Column("rolled_back_by", String(200)),
    Column("rollback_of", String(40)),
)

documents = Table(
    "documents", metadata,
    Column("id", ID, primary_key=True, autoincrement=True),
    Column("path", String(500), nullable=False, unique=True),
    Column("workspace", String(200), nullable=False, index=True),
    Column("kind", String(20), nullable=False),
    Column("summary", String(300), nullable=False),
    Column("body", Text, nullable=False),
    Column("links", JSON, nullable=False),
    Column("author", String(200), nullable=False),
    Column("client", String(200), nullable=False),
    Column("version", Integer, nullable=False),
    Column("changeset_id", String(40), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Column("reads", Integer, nullable=False, default=0),
    Column("delivered_at", DateTime(timezone=True)),  # a handover shown to its receiver
)

versions = Table(
    "versions", metadata,
    Column("id", ID, primary_key=True, autoincrement=True),
    Column("document_id", ID, nullable=False, index=True),
    Column("path", String(500), nullable=False),
    Column("version", Integer, nullable=False),
    Column("kind", String(20), nullable=False),
    Column("summary", String(300), nullable=False),
    Column("body", Text, nullable=False),
    Column("links", JSON, nullable=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Column("author", String(200), nullable=False),
    Column("client", String(200), nullable=False),
    Column("changeset_id", String(40), nullable=False, index=True),
    Column("op", String(20), nullable=False),  # write | rollback
    Column("at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("document_id", "version"),
)

audit = Table(
    "audit", metadata,
    Column("id", ID, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("user_id", String(200)),
    Column("client", String(200)),
    Column("via", String(20), nullable=False),  # mcp | platform | console
    Column("tool", String(60), nullable=False),
    Column("args", JSON, nullable=False),
    Column("status", String(16), nullable=False),  # ok | error | refused
    Column("error", Text),
    Column("changeset_id", String(40)),
    Column("duration_ms", Integer, nullable=False),
)


class BrainError(Exception):
    """A refusal or a bad request, said so that the caller can fix it."""


@dataclass(frozen=True)
class Caller:
    user: str
    groups: frozenset[str] = frozenset()
    client: str = "unknown"
    via: str = "mcp"
    admin: bool = False
    session: str | None = None  # transport session (Mcp-Session-Id), when the client keeps one

    def principals(self) -> set[str]:
        return {"*", f"user:{self.user}", *self.groups}


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def engine_from_url(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)


def slug(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:limit].rstrip("-")) or "note"


PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$")


def clean_path(path: str) -> str:
    path = path.strip().strip("/")
    if not PATH.match(path) or ".." in path:
        raise BrainError(f"bad path {path!r}: use letters, digits, '.', '_', '-' and '/' between parts")
    return path


def outline(body: str) -> list[str]:
    return [line.strip() for line in body.splitlines() if re.match(r"^#{1,4} ", line)]


def section_of(body: str, section: str) -> str:
    """The text under a heading (matched without #s, case-insensitive) down to the next heading of its level."""
    lines = body.splitlines()
    want = section.strip().lstrip("#").strip().lower()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,4}) (.*)$", line)
        if m and m[2].strip().lower() == want:
            level = len(m[1])
            end = next((j for j in range(i + 1, len(lines))
                        if (n := re.match(r"^(#{1,4}) ", lines[j])) and len(n[1]) <= level), len(lines))
            return "\n".join(lines[i:end])
    raise BrainError(f"no section {section!r}; the outline is: {outline(body)}")


@dataclass
class Store:
    engine: AsyncEngine
    seed: tuple[Workspace, ...] = ()
    _ws_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ---- setup -------------------------------------------------------------

    async def init(self, attempts: int = 10, delay_s: float = 3.0) -> None:
        for attempt in range(1, attempts + 1):
            try:
                async with self.engine.begin() as conn:
                    await conn.run_sync(metadata.create_all)
                break
            except (DBAPIError, OSError) as exc:
                if attempt == attempts:
                    raise
                log.warning("database init failed (%s), retry %d/%d", exc.__class__.__name__, attempt, attempts)
                await asyncio.sleep(delay_s)
        system = Caller("agentbrain", client="agentbrain", via="platform", admin=True)
        await self.ensure_workspace("", "Root", ("*",), ())
        for w in self.seed:
            await self.ensure_workspace(w.name, w.title, w.readers, w.writers)
        if not await self._doc("CORE.md"):
            await self._put(system, "CORE.md", "document", "What this memory is and how to work in it", CORE_DEFAULT, [],
                            await self.changeset(system, "seed"), instructions_ok=True)
        for w in self.seed:
            path = f"{w.name}/AGENTS.md"
            if not await self._doc(path):
                await self._put(system, path, "document", f"Rules for {w.name}", AGENTS_DEFAULT, [],
                                await self.changeset(system, "seed"), instructions_ok=True)

    async def ensure_workspace(self, name: str, title: str, readers: tuple[str, ...], writers: tuple[str, ...]) -> None:
        async with self.engine.begin() as conn:
            row = (await conn.execute(select(workspaces).where(workspaces.c.name == name))).first()
            if row is None:
                await conn.execute(insert(workspaces).values(name=name, title=title, readers=list(readers),
                                                             writers=list(writers), created_at=now()))
            elif (list(row.readers), list(row.writers), row.title) != (list(readers), list(writers), title):
                await conn.execute(update(workspaces).where(workspaces.c.name == name)
                                   .values(title=title, readers=list(readers), writers=list(writers)))
        self._ws_cache.clear()

    async def personal(self, caller: Caller) -> str:
        name = f"user/{caller.user}"
        if name not in await self._workspaces():
            await self.ensure_workspace(name, f"{caller.user}'s own", (f"user:{caller.user}",), (f"user:{caller.user}",))
        return name

    # ---- rights ------------------------------------------------------------

    async def _workspaces(self) -> dict[str, dict[str, Any]]:
        if not self._ws_cache:
            async with self.engine.connect() as conn:
                rows = (await conn.execute(select(workspaces))).mappings().all()
            self._ws_cache.update({r["name"]: dict(r) for r in rows})
        return self._ws_cache

    async def workspace_of(self, path: str) -> str:
        """The longest workspace name that is a prefix of the path ("" is the root)."""
        names = await self._workspaces()
        best = ""
        for name in names:
            if name and (path == name or path.startswith(name + "/")) and len(name) > len(best):
                best = name
        return best

    async def can(self, caller: Caller, workspace: str, what: str) -> bool:
        if caller.admin:
            return True
        ws = (await self._workspaces()).get(workspace)
        if ws is None:
            return False
        allowed = set(ws["readers"] if what == "read" else ws["writers"])
        if what == "read":
            allowed |= set(ws["writers"])
        return bool(allowed & caller.principals())

    async def readable(self, caller: Caller) -> list[dict[str, Any]]:
        await self.personal(caller)
        out = []
        for name, ws in sorted((await self._workspaces()).items()):
            if await self.can(caller, name, "read"):
                out.append({"workspace": name or "/", "title": ws["title"], "write": await self.can(caller, name, "write")})
        return out

    async def _require(self, caller: Caller, path: str, what: str) -> str:
        ws = await self.workspace_of(path)
        if not await self.can(caller, ws, what):
            raise BrainError(f"{caller.user} may not {what} in workspace {ws or '/'!r}")
        return ws

    # ---- changesets --------------------------------------------------------

    async def changeset(self, caller: Caller, task: str = "", session: str | None = None) -> str:
        """The caller's open changeset for this session, or a new one. Without a session id: one per user, client and day."""
        if session:
            async with self.engine.connect() as conn:
                row = (await conn.execute(select(changesets).where(changesets.c.id == session))).first()
            if row is None or row.user_id != caller.user:
                raise BrainError(f"no session {session!r} of {caller.user}; call brain_start for a new one")
            return row.id
        key = f"{caller.user}|{caller.client}|{caller.session or now().date().isoformat()}"
        async with self.engine.begin() as conn:
            # A transport session (a platform's run, an MCP session) is one changeset however often it starts.
            if not task or caller.session:
                row = (await conn.execute(select(changesets.c.id).where(changesets.c.key == key,
                                                                        changesets.c.rolled_back_at.is_(None))
                                          .order_by(changesets.c.started_at.desc()).limit(1))).first()
                if row:
                    return row.id
            cid = f"cs-{now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
            await conn.execute(insert(changesets).values(id=cid, key=key, user_id=caller.user, client=caller.client,
                                                         task=task or "(no task given)", started_at=now()))
        return cid

    # ---- reading -----------------------------------------------------------

    async def _doc(self, path: str, conn: AsyncConnection | None = None) -> dict[str, Any] | None:
        q = select(documents).where(documents.c.path == path)
        if conn is not None:
            row = (await conn.execute(q)).mappings().first()
        else:
            async with self.engine.connect() as c:
                row = (await c.execute(q)).mappings().first()
        return dict(row) if row else None

    async def tree(self, caller: Caller, prefix: str = "", limit: int = 200) -> list[dict[str, Any]]:
        prefix = prefix.strip().strip("/")
        q = select(documents.c.path, documents.c.kind, documents.c.summary, documents.c.author,
                   documents.c.updated_at, documents.c.version, documents.c.workspace).where(documents.c.deleted.is_(False))
        if prefix:
            q = q.where(or_(documents.c.path == prefix, documents.c.path.startswith(prefix + "/")))
        async with self.engine.connect() as conn:
            rows = (await conn.execute(q.order_by(documents.c.path))).mappings().all()
        out = []
        for r in rows:
            if await self.can(caller, r["workspace"], "read"):
                out.append({"path": r["path"], "kind": r["kind"], "summary": r["summary"], "author": r["author"],
                            "updated": r["updated_at"].isoformat(timespec="minutes"), "version": r["version"]})
            if len(out) >= limit:
                break
        return out

    async def read(self, caller: Caller, path: str, section: str | None = None, version: int | None = None) -> dict[str, Any]:
        path = clean_path(path)
        await self._require(caller, path, "read")
        doc = await self._doc(path)
        if doc is None or (doc["deleted"] and version is None):
            raise BrainError(f"nothing at {path!r}; brain_tree shows what there is")
        body, summary, at_version, author, client = doc["body"], doc["summary"], doc["version"], doc["author"], doc["client"]
        if version is not None:
            async with self.engine.connect() as conn:
                v = (await conn.execute(select(versions).where(versions.c.document_id == doc["id"],
                                                               versions.c.version == version))).mappings().first()
            if v is None:
                raise BrainError(f"{path} has versions 1..{doc['version']}")
            body, summary, at_version, author, client = v["body"], v["summary"], v["version"], v["author"], v["client"]
        async with self.engine.begin() as conn:
            await conn.execute(update(documents).where(documents.c.id == doc["id"]).values(reads=documents.c.reads + 1))
        text = section_of(body, section) if section else body
        out: dict[str, Any] = {"path": path, "kind": doc["kind"], "summary": summary, "version": at_version,
                               "latest_version": doc["version"], "author": author, "client": client, "links": doc["links"],
                               "updated": doc["updated_at"].isoformat(timespec="minutes"), "body": text}
        if len(body) > 6000 and not section:
            out["outline"] = outline(body)
        return out

    async def graph(self, caller: Caller) -> dict[str, Any]:
        """Every readable note and document with its links: the console draws the graph and the backlinks from it."""
        q = select(documents.c.path, documents.c.kind, documents.c.summary, documents.c.author, documents.c.client,
                   documents.c.links, documents.c.updated_at, documents.c.created_at, documents.c.workspace,
                   documents.c.changeset_id, documents.c.reads).where(documents.c.deleted.is_(False))
        async with self.engine.connect() as conn:
            rows = (await conn.execute(q)).mappings().all()
        out = []
        for r in rows:
            if await self.can(caller, r["workspace"], "read"):
                out.append({"path": r["path"], "kind": r["kind"], "summary": r["summary"], "author": r["author"],
                            "client": r["client"], "links": r["links"], "workspace": r["workspace"] or "/",
                            "session": r["changeset_id"], "reads": r["reads"],
                            "created": r["created_at"].isoformat(timespec="seconds"),
                            "updated": r["updated_at"].isoformat(timespec="seconds")})
        return {"nodes": out}

    async def history(self, caller: Caller, path: str) -> list[dict[str, Any]]:
        path = clean_path(path)
        await self._require(caller, path, "read")
        async with self.engine.connect() as conn:
            rows = (await conn.execute(
                select(versions.c.version, versions.c.summary, versions.c.author, versions.c.client, versions.c.op,
                       versions.c.changeset_id, versions.c.at, versions.c.deleted)
                .where(versions.c.path == path).order_by(versions.c.version.desc()))).mappings().all()
        return [{**r, "at": r["at"].isoformat(timespec="seconds")} for r in rows]

    async def search(self, caller: Caller, query: str, prefix: str = "", kind: str | None = None,
                     limit: int = 10) -> list[dict[str, Any]]:
        words = [w for w in re.findall(r"[\w.-]+", query.lower()) if len(w) > 1][:12]
        if not words:
            raise BrainError("give a few words to search for")
        base = select(documents).where(documents.c.deleted.is_(False))
        if prefix.strip("/"):
            p = prefix.strip("/")
            base = base.where(or_(documents.c.path == p, documents.c.path.startswith(p + "/")))
        if kind:
            base = base.where(documents.c.kind == kind)
        text = func.lower(documents.c.path + " " + documents.c.summary + " " + documents.c.body)
        if self.engine.dialect.name == "postgresql":
            tsv = func.to_tsvector("simple", documents.c.path + " " + documents.c.summary + " " + documents.c.body)
            tsq = func.to_tsquery("simple", " | ".join(re.sub(r"[^\w]", "", w) or "x" for w in words))
            rank = func.ts_rank(tsv, tsq) + sum((text.contains(w)).cast(Integer) * 0.05 for w in words)
            q = base.add_columns(rank.label("score")).where(or_(tsv.op("@@")(tsq), *[text.contains(w) for w in words]))
        else:
            score = sum(text.contains(w).cast(Integer) for w in words)
            q = base.add_columns(score.label("score")).where(or_(*[text.contains(w) for w in words]))
        q = q.order_by(func.coalesce(q.selected_columns.score, 0).desc(), documents.c.updated_at.desc()).limit(limit * 3)
        async with self.engine.connect() as conn:
            rows = (await conn.execute(q)).mappings().all()
        out = []
        for r in rows:
            if not await self.can(caller, r["workspace"], "read"):
                continue
            out.append({"path": r["path"], "kind": r["kind"], "summary": r["summary"], "author": r["author"],
                        "client": r["client"], "updated": r["updated_at"].isoformat(timespec="minutes"), "links": r["links"],
                        "snippet": snippet(r["body"], words)})
            if len(out) >= limit:
                break
        return out

    # ---- writing -----------------------------------------------------------

    async def write(self, caller: Caller, path: str, kind: str, summary: str, body: str, links: list[str] | None = None,
                    base_version: int | None = None, session: str | None = None) -> dict[str, Any]:
        if kind not in KINDS:
            raise BrainError(f"kind must be one of {', '.join(KINDS)}")
        path = clean_path(path)
        if path == f"user/{caller.user}" or path.startswith(f"user/{caller.user}/"):
            await self.personal(caller)
        if kind in NOTE_KINDS and not path.endswith(".md"):
            folder = path if path.endswith("/notes") or "/notes/" in path else f"{path}/notes"
            stem = f"{folder}/{now():%Y-%m-%d}-{slug(summary)}"
            path, n = f"{stem}.md", 2
            while (d := await self._doc(path)) is not None and not d["deleted"]:
                path, n = f"{stem}-{n}.md", n + 1
        await self._require(caller, path, "write")
        cid = await self.changeset(caller, session=session)
        return await self._put(caller, path, kind, summary, body, links or [], cid, base_version=base_version)

    async def handover(self, caller: Caller, to: str, summary: str, body: str, links: list[str] | None = None,
                       session: str | None = None) -> dict[str, Any]:
        receiver = Caller(to)
        ws = await self.personal(receiver)
        cid = await self.changeset(caller, session=session)
        path = f"{ws}/handovers/{now():%Y-%m-%d}-{slug(summary)}-from-{slug(caller.user, 30)}.md"
        # A handover is the one write into someone else's own workspace: append-only, signed with the sender.
        return await self._put(caller, path, "handover", summary, body, links or [], cid, rights_checked=True)

    async def event(self, caller: Caller, workspace: str, summary: str, body: str, links: list[str]) -> dict[str, Any]:
        ws = clean_path(workspace) if workspace.strip("/") else await self.personal(caller)
        if (await self.workspace_of(ws + "/x")) != ws:
            raise BrainError(f"no workspace {ws!r}")
        cid = await self.changeset(caller)
        path = f"{ws}/events/{now():%Y-%m-%d-%H%M%S}-{slug(summary)}.md"
        return await self._put(caller, path, "event", summary, body, links, cid, rights_checked=True)

    async def _put(self, caller: Caller, path: str, kind: str, summary: str, body: str, links: list[str], cid: str,
                   base_version: int | None = None, instructions_ok: bool = False,
                   rights_checked: bool = False) -> dict[str, Any]:
        name = path.rsplit("/", 1)[-1]
        if name in INSTRUCTION_FILES and not instructions_ok:
            raise BrainError(f"{name} instructs every agent here, so it changes only with a person's approval: "
                             "propose the change to the person (or as a runbook-gap note) instead")
        summary = " ".join(summary.split())
        if not summary:
            raise BrainError("summary is required: one line that says what this is")
        if len(summary) > 300:
            raise BrainError("summary is one line, at most 300 characters")
        limit = NOTE_MAX if kind in NOTE_KINDS else DOC_MAX
        if len(body) > limit:
            raise BrainError(f"a {kind} is at most {limit} characters; split it, or link the long text")
        _, found = redact(body + "\n" + summary + "\n" + " ".join(links))
        if found:
            raise BrainError(f"refused: {found} secret-looking value(s) in the text. Never store secrets here; "
                             "say where the secret lives (e.g. its Vault path) instead")
        ws = await self.workspace_of(path)
        at = now()
        async with self.engine.begin() as conn:
            doc = await self._doc(path, conn)
            if doc and not doc["deleted"]:
                if doc["kind"] in NOTE_KINDS or kind in NOTE_KINDS:
                    raise BrainError(f"{path} exists, and notes are not edited: write a new note that links it")
                if base_version is None:
                    raise BrainError(f"{path} exists at version {doc['version']} (by {doc['author']}): read it, "
                                     "then write again with base_version set to the version you read")
                if base_version != doc["version"]:
                    raise BrainError(f"conflict: {path} changed since version {base_version}; it is now version "
                                     f"{doc['version']} by {doc['author']}. Read it, merge both, write with "
                                     f"base_version={doc['version']}")
            version = (doc["version"] + 1) if doc else 1
            values = dict(path=path, workspace=ws, kind=kind, summary=summary, body=body, links=links,
                          author=caller.user, client=caller.client, version=version, changeset_id=cid,
                          updated_at=at, deleted=False)
            if doc:
                await conn.execute(update(documents).where(documents.c.id == doc["id"]).values(**values))
                doc_id = doc["id"]
            else:
                res = await conn.execute(insert(documents).values(**values, created_at=at, reads=0))
                doc_id = res.inserted_primary_key[0]
            await conn.execute(insert(versions).values(
                document_id=doc_id, path=path, version=version, kind=kind, summary=summary, body=body, links=links,
                deleted=False, author=caller.user, client=caller.client, changeset_id=cid, op="write", at=at))
        return {"path": path, "version": version, "session": cid, "workspace": ws or "/"}

    async def set_instructions(self, caller: Caller, path: str, body: str, base_version: int | None) -> dict[str, Any]:
        """CORE.md / AGENTS.md through the console: a person with the admin group, i.e. the approval itself."""
        if not caller.admin:
            raise BrainError("instruction files change only by an admin of agentBrain")
        path = clean_path(path)
        if path.rsplit("/", 1)[-1] not in INSTRUCTION_FILES:
            raise BrainError("only CORE.md and AGENTS.md files are instruction files")
        cid = await self.changeset(caller, f"edit {path}")
        doc = await self._doc(path)
        return await self._put(caller, path, "document", doc["summary"] if doc else f"Rules for {path.rsplit('/', 1)[0]}",
                               body, [], cid, base_version=base_version, instructions_ok=True)

    # ---- sessions and rollback --------------------------------------------

    async def start(self, caller: Caller, task: str, workspace: str | None = None) -> dict[str, Any]:
        mine = await self.personal(caller)
        ws = clean_path(workspace) if workspace and workspace.strip("/") else ""
        if ws and not await self.can(caller, await self.workspace_of(ws + "/x"), "read"):
            raise BrainError(f"{caller.user} may not read {ws!r}; brain_start without a workspace lists what you can")
        cid = await self.changeset(caller, task or "(no task given)")
        core = await self._doc("CORE.md")
        rules = []
        parts = ws.split("/") if ws else []
        for i in range(1, len(parts) + 1):
            d = await self._doc("/".join(parts[:i]) + "/AGENTS.md")
            if d and not d["deleted"]:
                rules.append({"path": d["path"], "body": d["body"]})
        handovers = await self._deliver_handovers(mine)
        related = []
        if task.strip():
            try:
                related = await self.search(caller, task, limit=5)
            except BrainError:
                pass
        tree = await self.tree(caller, ws, limit=60)
        return {
            "session": cid,
            "you": caller.user,
            "core": core["body"] if core else "",
            "rules": rules,
            "workspaces": await self.readable(caller),
            "your_workspace": mine,
            "handovers_for_you": handovers,
            "related": related,
            "tree": [t for t in tree if t["kind"] == "document"][:40]
                    + [t for t in sorted(tree, key=lambda t: t["updated"], reverse=True) if t["kind"] != "document"][:20],
            "next": "Pass session to brain_write and brain_handover. Read only what you need (brain_read, by section).",
        }

    async def _deliver_handovers(self, mine: str) -> list[dict[str, Any]]:
        async with self.engine.begin() as conn:
            rows = (await conn.execute(select(documents).where(
                documents.c.workspace == mine, documents.c.kind == "handover", documents.c.deleted.is_(False),
                documents.c.delivered_at.is_(None)).order_by(documents.c.created_at))).mappings().all()
            if rows:
                await conn.execute(update(documents).where(documents.c.id.in_([r["id"] for r in rows]))
                                   .values(delivered_at=now()))
        return [{"path": r["path"], "from": r["author"], "summary": r["summary"], "body": r["body"],
                 "links": r["links"]} for r in rows]

    async def changesets_list(self, caller: Caller, limit: int = 50) -> list[dict[str, Any]]:
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(changesets).order_by(changesets.c.started_at.desc()).limit(limit * 3))).mappings().all()
            counts = dict((await conn.execute(select(versions.c.changeset_id, func.count()).where(
                versions.c.changeset_id.in_([r["id"] for r in rows])).group_by(versions.c.changeset_id))).all())
        out = []
        for r in rows:
            n = counts.get(r["id"], 0)
            if not n and r["user_id"] != caller.user:
                continue
            out.append({**r, "started_at": r["started_at"].isoformat(timespec="seconds"),
                        "rolled_back_at": r["rolled_back_at"].isoformat(timespec="seconds") if r["rolled_back_at"] else None,
                        "changes": n})
            if len(out) >= limit:
                break
        return out

    async def changeset_detail(self, caller: Caller, cid: str) -> dict[str, Any]:
        async with self.engine.connect() as conn:
            cs = (await conn.execute(select(changesets).where(changesets.c.id == cid))).mappings().first()
            if cs is None:
                raise BrainError(f"no changeset {cid}")
            rows = (await conn.execute(select(versions.c.path, versions.c.version, versions.c.kind, versions.c.summary,
                                              versions.c.op, versions.c.deleted, versions.c.at)
                                       .where(versions.c.changeset_id == cid).order_by(versions.c.id))).mappings().all()
        visible = []
        for r in rows:
            if await self.can(caller, await self.workspace_of(r["path"]), "read"):
                visible.append({**r, "at": r["at"].isoformat(timespec="seconds")})
        return {**cs, "started_at": cs["started_at"].isoformat(timespec="seconds"),
                "rolled_back_at": cs["rolled_back_at"].isoformat(timespec="seconds") if cs["rolled_back_at"] else None,
                "versions": visible, "hidden": len(rows) - len(visible)}

    async def rollback(self, caller: Caller, cid: str) -> dict[str, Any]:
        """Undo a whole changeset: each document it touched goes back to its latest version outside rolled-back changesets."""
        async with self.engine.connect() as conn:
            cs = (await conn.execute(select(changesets).where(changesets.c.id == cid))).mappings().first()
        if cs is None:
            raise BrainError(f"no changeset {cid}")
        if cs["rolled_back_at"] is not None:
            raise BrainError(f"{cid} was rolled back already, by {cs['rolled_back_by']}")
        if cs["user_id"] != caller.user and not caller.admin:
            raise BrainError("only its author or an admin rolls a changeset back")
        rb = await self.changeset(caller, f"rollback of {cid}")
        restored: list[dict[str, Any]] = []
        async with self.engine.begin() as conn:
            await conn.execute(update(changesets).where(changesets.c.id == cid)
                               .values(rolled_back_at=now(), rolled_back_by=caller.user))
            await conn.execute(update(changesets).where(changesets.c.id == rb).values(rollback_of=cid))
            dead = {r[0] for r in (await conn.execute(select(changesets.c.id).where(changesets.c.rolled_back_at.is_not(None)))).all()}
            doc_ids = [r[0] for r in (await conn.execute(select(versions.c.document_id).where(versions.c.changeset_id == cid).distinct())).all()]
            for doc_id in doc_ids:
                doc = (await conn.execute(select(documents).where(documents.c.id == doc_id))).mappings().first()
                keep = (await conn.execute(select(versions).where(versions.c.document_id == doc_id,
                                                                  versions.c.changeset_id.not_in(dead))
                                           .order_by(versions.c.version.desc()).limit(1))).mappings().first()
                if keep is not None and keep["version"] == doc["version"]:
                    continue  # a later changeset already replaced what this one wrote
                version, at = doc["version"] + 1, now()
                if keep is None:
                    vals = dict(summary=doc["summary"], body=doc["body"], links=doc["links"], deleted=True, kind=doc["kind"])
                else:
                    vals = dict(summary=keep["summary"], body=keep["body"], links=keep["links"], deleted=bool(keep["deleted"]),
                                kind=keep["kind"])
                await conn.execute(update(documents).where(documents.c.id == doc_id).values(
                    **vals, version=version, author=caller.user, client=caller.client, changeset_id=rb, updated_at=at))
                await conn.execute(insert(versions).values(document_id=doc_id, path=doc["path"], version=version, **vals,
                                                           author=caller.user, client=caller.client, changeset_id=rb,
                                                           op="rollback", at=at))
                restored.append({"path": doc["path"], "version": version,
                                 "now": "removed" if vals["deleted"] else f"as of version {keep['version']}"})  # type: ignore[index]
        return {"rolled_back": cid, "changeset": rb, "documents": restored}

    # ---- audit -------------------------------------------------------------

    async def record(self, caller: Caller | None, tool: str, args: dict[str, Any], status: str, error: str | None,
                     changeset_id: str | None, duration_ms: int, via: str = "mcp") -> None:
        # A refused write is refused because of what it holds: the audit keeps the attempt, never the secret.
        masked = {k: redact(v)[0] if isinstance(v, str) else v for k, v in args.items()}
        short = {k: (v[:500] + "…" if isinstance(v, str) and len(v) > 500 else v) for k, v in masked.items()}
        async with self.engine.begin() as conn:
            await conn.execute(insert(audit).values(
                at=now(), user_id=caller.user if caller else None, client=caller.client if caller else None,
                via=caller.via if caller else via, tool=tool, args=short, status=status, error=error,
                changeset_id=changeset_id, duration_ms=duration_ms))

    async def audit_list(self, limit: int = 200, user: str | None = None) -> list[dict[str, Any]]:
        q = select(audit).order_by(audit.c.id.desc()).limit(limit)
        if user:
            q = q.where(audit.c.user_id == user)
        async with self.engine.connect() as conn:
            rows = (await conn.execute(q)).mappings().all()
        return [{**r, "at": r["at"].isoformat(timespec="seconds")} for r in rows]

    async def stats(self) -> dict[str, Any]:
        async with self.engine.connect() as conn:
            by_kind = dict((await conn.execute(select(documents.c.kind, func.count()).where(documents.c.deleted.is_(False))
                                               .group_by(documents.c.kind))).all())
            unread = (await conn.execute(select(func.count()).where(and_(documents.c.reads == 0, documents.c.deleted.is_(False),
                                                                         documents.c.kind != "document")))).scalar()
            sessions = (await conn.execute(select(func.count()).select_from(changesets))).scalar()
            clients = dict((await conn.execute(select(audit.c.client, func.count()).group_by(audit.c.client))).all())
        return {"by_kind": by_kind, "unread_notes": unread, "sessions": sessions, "calls_by_client": clients}


def snippet(body: str, words: list[str], width: int = 220) -> str:
    low = body.lower()
    pos = min((p for w in words if (p := low.find(w)) >= 0), default=0)
    start = max(0, pos - width // 3)
    text = " ".join(body[start:start + width].split())
    return ("…" if start else "") + text + ("…" if start + width < len(body) else "")
