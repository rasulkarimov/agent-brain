"""One-time setup of agentBrain next to AgentGate: Keycloak clients, the database, Secret agentbrain.

Idempotent. Nothing secret is printed: the Keycloak admin password comes from the macOS Keychain,
generated values and the client secret go straight into Secret agentbrain (one Secret for the app).

    python3 deploy/setup.py keycloak   # clients agentbrain (console) and agentbrain-mcp (MCP clients, PKCE)
    python3 deploy/setup.py db         # role and database agentbrain in AgentGate's CNPG cluster
    python3 deploy/setup.py keys       # platform key for AgentGate's gateway, oauth2-proxy cookie secret

Env: KC_URL, KC_REALM, KC_ADMIN_REALM, KEYCHAIN_SERVICE, APP_URL, NAMESPACE, DB_CLUSTER.
"""
import base64
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

KC = os.environ.get("KC_URL", "https://dataplatform-keycloak.presight.ai/auth")
REALM = os.environ.get("KC_REALM", "dataplatform")
ADMIN_REALM = os.environ.get("KC_ADMIN_REALM", "master")
SERVICE = os.environ.get("KEYCHAIN_SERVICE", "dataplatform-keycloak-admin")
APP = os.environ.get("APP_URL", "https://agentbrain.intdev.presight.ai")
NAMESPACE = os.environ.get("NAMESPACE", "agentgate")
DB_CLUSTER = os.environ.get("DB_CLUSTER", "agentgate-db")
SECRET = "agentbrain"
AUDIENCE = "agentbrain"


def kubectl(*args, input=None):
    return subprocess.run(["kubectl", "-n", NAMESPACE, *args], input=input, capture_output=True, text=True, check=True).stdout


def secret_keys():
    try:
        data = json.loads(kubectl("get", "secret", SECRET, "-o", "json")).get("data") or {}
    except subprocess.CalledProcessError:
        return {}
    return {k: base64.b64decode(v).decode() for k, v in data.items()}


def put_secret(values, only_missing=False):
    """Merge keys into Secret agentbrain without printing them."""
    current = secret_keys()
    merged = {**current, **{k: v for k, v in values.items() if not (only_missing and k in current)}}
    manifest = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": SECRET, "namespace": NAMESPACE},
                "type": "Opaque", "stringData": merged}
    kubectl("apply", "-f", "-", input=json.dumps(manifest))
    print(f"secret {NAMESPACE}/{SECRET}: keys {', '.join(sorted(merged))}")


# ---- Keycloak ---------------------------------------------------------------

def keychain():
    out = subprocess.run(["security", "find-generic-password", "-s", SERVICE], capture_output=True, text=True, check=True).stdout
    user = next(line.split("=", 1)[1].strip().strip('"') for line in out.splitlines() if '"acct"' in line)
    password = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-w"],
                              capture_output=True, text=True, check=True).stdout.rstrip("\n")
    return user, password


def kc_token(user, password):
    form = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli", "username": user, "password": password})
    req = urllib.request.Request(f"{KC}/realms/{ADMIN_REALM}/protocol/openid-connect/token", form.encode())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["access_token"]


def call(tok, method, path, body=None):
    req = urllib.request.Request(f"{KC}/admin/realms/{REALM}{path}", method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


MAPPERS = [
    {"name": "groups", "protocol": "openid-connect", "protocolMapper": "oidc-group-membership-mapper",
     "config": {"claim.name": "groups", "full.path": "false", "id.token.claim": "true",
                "access.token.claim": "true", "userinfo.token.claim": "true"}},
    # agentBrain takes only tokens meant for it; oauth2-proxy checks the same audience for the console.
    {"name": "audience-agentbrain", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
     "config": {"included.client.audience": AUDIENCE, "id.token.claim": "true", "access.token.claim": "true"}},
]

CLIENTS = [
    # The console, through oauth2-proxy.
    {"clientId": "agentbrain", "name": "agentBrain console", "enabled": True, "protocol": "openid-connect",
     "publicClient": False, "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
     "implicitFlowEnabled": False, "serviceAccountsEnabled": False,
     "redirectUris": [f"{APP}/oauth2/callback"], "webOrigins": [APP], "rootUrl": APP,
     "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": f"{APP}/*"}},
    # MCP clients on engineers' laptops (Claude Code, Codex): authorization code with PKCE, loopback redirect.
    {"clientId": "agentbrain-mcp", "name": "agentBrain MCP clients", "enabled": True, "protocol": "openid-connect",
     "publicClient": True, "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
     "implicitFlowEnabled": False, "serviceAccountsEnabled": False,
     "redirectUris": ["http://localhost:*", "http://127.0.0.1:*"], "webOrigins": [],
     "attributes": {"pkce.code.challenge.method": "S256"}},
]


def keycloak():
    tok = kc_token(*keychain())
    realm = call(tok, "GET", "")
    print(f"keycloak: realm {realm['realm']}, access tokens live {realm.get('accessTokenLifespan')} s")
    for client in CLIENTS:
        cid_name = client["clientId"]
        found = call(tok, "GET", f"/clients?clientId={urllib.parse.quote(cid_name)}")
        if found:
            cid = found[0]["id"]
            call(tok, "PUT", f"/clients/{cid}", {**found[0], **client})
            print(f"client {cid_name}: updated")
        else:
            call(tok, "POST", "/clients", client)
            cid = call(tok, "GET", f"/clients?clientId={urllib.parse.quote(cid_name)}")[0]["id"]
            print(f"client {cid_name}: created")
        have = {m["name"]: m for m in call(tok, "GET", f"/clients/{cid}/protocol-mappers/models")}
        for m in MAPPERS:
            if m["name"] in have:
                call(tok, "PUT", f"/clients/{cid}/protocol-mappers/models/{have[m['name']]['id']}", {**have[m["name"]], **m})
            else:
                call(tok, "POST", f"/clients/{cid}/protocol-mappers/models", m)
        print(f"client {cid_name}: mappers {', '.join(m['name'] for m in MAPPERS)}")
        if not client["publicClient"]:
            secret = call(tok, "GET", f"/clients/{cid}/client-secret")["value"]
            put_secret({"OAUTH2_PROXY_CLIENT_ID": cid_name, "OAUTH2_PROXY_CLIENT_SECRET": secret})


# ---- database and keys ------------------------------------------------------

def db():
    primary = json.loads(kubectl("get", "cluster.postgresql.cnpg.io", DB_CLUSTER, "-o", "json"))["status"]["currentPrimary"]
    current = secret_keys()
    password = (current.get("DB_PASSWORD") or secrets.token_urlsafe(24))
    sql = f"""
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agentbrain') THEN CREATE ROLE agentbrain LOGIN; END IF;
END $$;
ALTER ROLE agentbrain WITH LOGIN PASSWORD '{password}';
SELECT 'CREATE DATABASE agentbrain OWNER agentbrain' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agentbrain')\\gexec
"""
    kubectl("exec", "-i", primary, "-c", "postgres", "--", "psql", "-q", "-U", "postgres", "-v", "ON_ERROR_STOP=1", input=sql)
    print(f"database agentbrain on {primary}: ready")
    put_secret({"DB_PASSWORD": password,
                "DATABASE_URL": f"postgresql+asyncpg://agentbrain:{password}@{DB_CLUSTER}-rw:5432/agentbrain"})


def keys():
    put_secret({"BRAIN_PLATFORM_KEY_AGENTGATE": secrets.token_urlsafe(32),
                "OAUTH2_PROXY_COOKIE_SECRET": secrets.token_hex(16)}, only_missing=True)


if __name__ == "__main__":
    steps = {"keycloak": keycloak, "db": db, "keys": keys}
    try:
        for name in sys.argv[1:] or list(steps):
            steps[name]()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{e.code} {e.reason} on {e.url}: {e.read()[:300].decode(errors='replace')}")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"{' '.join(e.cmd[:6])}…: {e.stderr[:300]}")
