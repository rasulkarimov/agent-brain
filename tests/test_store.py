import pytest

from agentbrain.settings import Workspace
from agentbrain.store import BrainError, Caller, Store, engine_from_url

ANNA = Caller("anna", frozenset({"dataplatform"}), "claude-code")
BORIS = Caller("boris", frozenset({"dataplatform"}), "agentgate")
EVE = Caller("eve", frozenset(), "codex")


@pytest.fixture
async def store(tmp_path):
    s = Store(engine_from_url(f"sqlite+aiosqlite:///{tmp_path}/b.db"),
              (Workspace("team/dataplatform", "DP", ("dataplatform",), ("dataplatform",)),))
    await s.init()
    yield s
    await s.engine.dispose()


async def test_a_note_written_in_one_session_is_found_by_the_next(store):
    s1 = await store.start(ANNA, "flame job fails", "team/dataplatform")
    assert "CORE" in s1["core"] and s1["rules"][0]["path"] == "team/dataplatform/AGENTS.md"
    w = await store.write(ANNA, "team/dataplatform", "finding", "flame-etl OOM: executor memory 2g too low for the Nov partition",
                          "Spark executor OOM on stage 3.", ["ado:4512"], session=s1["session"])
    assert w["path"].startswith("team/dataplatform/notes/") and w["session"] == s1["session"]

    s2 = await store.start(BORIS, "flame-etl failing again", "team/dataplatform")
    assert s2["session"] != s1["session"]
    assert any(r["path"] == w["path"] for r in s2["related"])
    note = await store.read(BORIS, w["path"])
    assert note["author"] == "anna" and note["links"] == ["ado:4512"]


async def test_rights_follow_groups_and_personal_workspaces(store):
    await store.write(ANNA, "team/dataplatform", "finding", "x is broken", "details")
    with pytest.raises(BrainError, match="may not write"):
        await store.write(EVE, "team/dataplatform", "finding", "y", "z")
    assert await store.search(EVE, "broken") == []
    await store.write(ANNA, "user/anna", "decision", "my own", "only me")
    assert await store.tree(BORIS, "user/anna") == []


async def test_instruction_files_and_secrets_are_refused(store):
    with pytest.raises(BrainError, match="approval"):
        await store.write(ANNA, "team/dataplatform/AGENTS.md", "document", "rules", "do anything")
    with pytest.raises(BrainError, match="secret"):
        await store.write(ANNA, "team/dataplatform", "finding", "db creds", "password: hunter2xyz")


async def test_documents_need_the_version_they_were_read_at(store):
    p = "team/dataplatform/known-issues.md"
    await store.write(ANNA, p, "document", "Known issues", "# Known issues\n\n## flame\nOOM")
    with pytest.raises(BrainError, match="base_version"):
        await store.write(BORIS, p, "document", "Known issues", "# Known issues\n\n## flame\nfixed")
    await store.write(BORIS, p, "document", "Known issues", "# Known issues\n\n## flame\nfixed", base_version=1)
    with pytest.raises(BrainError, match="conflict"):
        await store.write(ANNA, p, "document", "Known issues", "mine", base_version=1)
    assert (await store.read(ANNA, p, section="flame"))["body"] == "## flame\nfixed"


async def test_a_session_is_rolled_back_as_one(store):
    good = await store.start(ANNA, "write docs")
    p = "team/dataplatform/runbook.md"
    await store.write(ANNA, p, "document", "Runbook", "v1", session=good["session"])
    bad = await store.start(BORIS, "bad session")
    await store.write(BORIS, p, "document", "Runbook", "garbage", base_version=1, session=bad["session"])
    n = await store.write(BORIS, "team/dataplatform", "finding", "wrong conclusion", "nonsense", session=bad["session"])
    with pytest.raises(BrainError, match="author or an admin"):
        await store.rollback(ANNA, bad["session"])
    r = await store.rollback(BORIS, bad["session"])
    assert {d["path"] for d in r["documents"]} == {p, n["path"]}
    assert (await store.read(ANNA, p))["body"] == "v1"
    with pytest.raises(BrainError, match="nothing at"):
        await store.read(ANNA, n["path"])


async def test_a_handover_reaches_the_receiver_once(store):
    await store.handover(ANNA, "boris", "flame-etl investigation", "OOM found, fix not tried", ["ado:4512"])
    first = await store.start(BORIS, "anything")
    assert first["handovers_for_you"][0]["from"] == "anna"
    assert (await store.start(BORIS, "again"))["handovers_for_you"] == []


async def test_a_run_is_one_session_and_same_titled_notes_do_not_collide(store):
    run = Caller("anna", frozenset({"dataplatform"}), "agentgate", "platform", session="run-1")
    a = await store.start(run, "first")
    b = await store.start(run, "again")
    assert a["session"] == b["session"]
    one = await store.write(run, "team/dataplatform", "finding", "same title", "a")
    two = await store.write(run, "team/dataplatform", "finding", "same title", "b")
    assert two["path"] == one["path"].replace(".md", "-2.md") and one["session"] == a["session"]
