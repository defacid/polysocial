"""Serve the local Polysocial UI, queue, API, and delivery worker."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit
import argparse
import json
import re
import os
import secrets
import base64

from polysocial.bluesky import BlueskyClient, BlueskyError
from polysocial.meta import MetaClient, MetaError
from polysocial.threads import ThreadsClient, ThreadsError
from polysocial.storage import Storage
from polysocial.vault import CredentialVault, VaultError
from polysocial.worker import DeliveryWorker
from polysocial.media_urls import valid_signature


DATA_DIR = Path(os.environ.get("POLYSOCIAL_DATA_DIR", Path.home() / ".local" / "share" / "polysocial")).expanduser().resolve()
DATABASE = DATA_DIR / "posts.sqlite3"
POST_ID = re.compile(r"^PS-[A-Z0-9-]{1,40}$")
STORAGE = Storage(DATABASE)
VAULT = CredentialVault(DATA_DIR / "credentials")
PUBLIC_ORIGIN = os.environ.get("POLYSOCIAL_PUBLIC_ORIGIN", "").rstrip("/")
PUBLIC_FILES = {
    "/", "/index.html", "/app.js", "/overrides.js", "/styles.css",
    "/polysocial-brand.svg", "/defacid-logo-black.png",
}


def is_public_asset(path):
    return path in PUBLIC_FILES or path.startswith("/assets/fontawesome/")


def initialize_database():
    STORAGE.migrate()
    with STORAGE.connect() as connection:
        if connection.execute("SELECT value FROM meta WHERE key = 'seeded'").fetchone():
            return
        connection.execute("INSERT INTO meta VALUES ('seeded', 'true')")


class PreviewHandler(SimpleHTTPRequestHandler):
    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def public_origin(self):
        if PUBLIC_ORIGIN:
            return PUBLIC_ORIGIN
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "127.0.0.1:5500")
        scheme = self.headers.get("X-Forwarded-Proto") or ("https" if host.endswith("getbb.app") else "http")
        return f"{scheme}://{host}"

    def api_response(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def api_path(self):
        return urlsplit(self.path).path

    def read_json(self, maximum=1024 * 1024):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= maximum:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = self.api_path()
        if path.startswith("/api/media/"):
            try:
                parts = path.split("/")
                post_id, index = parts[3], int(parts[4])
                query = parse_qs(urlsplit(self.path).query)
                key = STORAGE.setting("media_signing_key", "")
                expires = query.get("expires", [""])[0]
                supplied = query.get("signature", [""])[0]
                post = STORAGE.get_post(post_id)
                if not key or not post or not valid_signature(key, post_id, index, expires, supplied):
                    raise ValueError
                media = post["media"][index]
                content = base64.b64decode(media["data"], validate=True)
                self.send_response(200)
                self.send_header("Content-Type", media.get("type", "application/octet-stream"))
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "private, max-age=300")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(content)
            except (ValueError, IndexError, KeyError, TypeError):
                self.api_response(404, {"error": "Media not found"})
            return
        if path == "/api/oauth/meta/start":
            try:
                config = VAULT.get("meta-app")
                if not config:
                    raise VaultError("Save the Meta App ID and App Secret first")
                state = secrets.token_urlsafe(32)
                redirect_uri = f"{self.public_origin()}/api/oauth/meta/callback"
                VAULT.set("meta-oauth", {"state": state, "redirectUri": redirect_uri})
                self.redirect(MetaClient(config["appId"], config["appSecret"], config.get("configId")).authorization_url(redirect_uri, state))
            except (VaultError, KeyError) as error:
                self.redirect(f"/?meta_error={quote(str(error))}")
        elif path == "/api/oauth/meta/callback":
            query = parse_qs(urlsplit(self.path).query)
            try:
                oauth = VAULT.get("meta-oauth")
                config = VAULT.get("meta-app")
                if not oauth or not config or query.get("state", [""])[0] != oauth["state"]:
                    raise MetaError("Meta connection state was invalid or expired")
                if query.get("error"):
                    raise MetaError(query.get("error_description", query["error"])[0])
                code = query.get("code", [""])[0]
                if not code:
                    raise MetaError("Meta did not return an authorization code")
                client = MetaClient(config["appId"], config["appSecret"], config.get("configId"))
                user_token = client.exchange_code(code, oauth["redirectUri"])
                pages = client.pages(user_token)
                VAULT.set("meta-pending", {"pages": pages})
                VAULT.delete("meta-oauth")
                self.redirect("/?meta=select")
            except (MetaError, VaultError, KeyError) as error:
                self.redirect(f"/?meta_error={quote(str(error))}")
        elif path == "/api/connections/meta/pending":
            pending = VAULT.get("meta-pending") or {"pages": []}
            pages = [{"id": page.get("id"), "name": page.get("name"), "instagram": page.get("instagram_business_account")} for page in pending["pages"]]
            self.api_response(200, {"pages": pages})
        elif path == "/api/oauth/threads/start":
            try:
                config = VAULT.get("threads-app")
                if not config:
                    raise VaultError("Save the Threads App ID and App Secret first")
                state = secrets.token_urlsafe(32)
                redirect_uri = f"{self.public_origin()}/api/oauth/threads/callback"
                VAULT.set("threads-oauth", {"state": state, "redirectUri": redirect_uri})
                self.redirect(ThreadsClient(config["appId"], config["appSecret"]).authorization_url(redirect_uri, state))
            except (VaultError, KeyError) as error:
                self.redirect(f"/?threads_error={quote(str(error))}")
        elif path == "/api/oauth/threads/callback":
            query = parse_qs(urlsplit(self.path).query)
            try:
                oauth = VAULT.get("threads-oauth")
                config = VAULT.get("threads-app")
                if not oauth or not config or query.get("state", [""])[0] != oauth["state"]:
                    raise ThreadsError("Threads connection state was invalid or expired")
                if query.get("error"):
                    raise ThreadsError(query.get("error_description", query["error"])[0])
                code = query.get("code", [""])[0]
                if not code:
                    raise ThreadsError("Threads did not return an authorization code")
                client = ThreadsClient(config["appId"], config["appSecret"])
                token, expires_in = client.long_lived_token(client.exchange_code(code, oauth["redirectUri"]))
                profile = client.profile(token)
                username = profile.get("username") or profile.get("id")
                VAULT.set("threads", {"userId": profile.get("id"), "username": profile.get("username"), "accessToken": token, "expiresIn": expires_in, "appId": config["appId"], "appSecret": config["appSecret"]})
                STORAGE.set_connection("threads", f"@{username}")
                VAULT.delete("threads-oauth")
                self.redirect("/?threads=connected")
            except (ThreadsError, VaultError, KeyError) as error:
                self.redirect(f"/?threads_error={quote(str(error))}")
        elif path == "/api/posts":
            self.api_response(200, STORAGE.list_posts())
        elif path == "/api/status":
            connections = {row["platform"]: row for row in STORAGE.connections()}
            bluesky = connections.get("bluesky")
            self.api_response(200, {"service": "ready", "deliveryEnabled": STORAGE.setting("delivery_enabled", False), "vaultAvailable": VAULT.available, "bluesky": {"configured": bool(bluesky), "handle": bluesky["display_name"] if bluesky else None}})
        elif path == "/api/connections":
            self.api_response(200, {"vaultAvailable": VAULT.available, "deliveryEnabled": STORAGE.setting("delivery_enabled", False), "connections": STORAGE.connections()})
        elif path == "/api/config":
            meta = VAULT.get("meta-app") or {}
            threads = VAULT.get("threads-app") or {}
            self.api_response(200, {
                "publicOrigin": self.public_origin(),
                "metaAppId": meta.get("appId", ""),
                "metaConfigId": meta.get("configId", ""),
                "threadsAppId": threads.get("appId", ""),
            })
        elif path == "/api/deliveries":
            self.api_response(200, STORAGE.list_deliveries())
        elif path.startswith("/api/deliveries/"):
            self.api_response(200, STORAGE.list_deliveries(path.rsplit("/", 1)[-1]))
        elif path.startswith("/api/posts/"):
            post_id = path.rsplit("/", 1)[-1]
            post = STORAGE.get_post(post_id)
            self.api_response(200, post) if post else self.api_response(404, {"error": "Post not found"})
        elif path.startswith("/api/"):
            self.api_response(404, {"error": "Not found"})
        else:
            super().do_GET()

    def do_PUT(self):
        path = self.api_path()
        if path == "/api/connections/meta/config":
            try:
                body = self.read_json(32 * 1024)
                app_id = str(body.get("appId", "")).strip()
                app_secret = str(body.get("appSecret", "")).strip()
                config_id = str(body.get("configId", "")).strip()
                if not app_id.isdigit() or len(app_secret) < 8 or (config_id and not config_id.isdigit()):
                    raise ValueError("A numeric Meta App ID and App Secret are required; Configuration ID must be numeric when supplied")
                config = {"appId": app_id, "appSecret": app_secret}
                if config_id:
                    config["configId"] = config_id
                VAULT.set("meta-app", config)
                self.api_response(200, {"authorizationUrl": "/api/oauth/meta/start"})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/connections/meta/token":
            try:
                body = self.read_json(128 * 1024)
                app_id = str(body.get("appId", "")).strip()
                app_secret = str(body.get("appSecret", "")).strip()
                supplied_token = str(body.get("accessToken", "")).strip()
                if not app_id.isdigit() or len(app_secret) < 8 or len(supplied_token) < 20:
                    raise ValueError("Meta App ID, App Secret, and access token are required")
                client = MetaClient(app_id, app_secret)
                pages = client.pages(supplied_token)
                if not pages:
                    raise MetaError("Meta returned no managed Pages for this token")
                VAULT.set("meta-app", {"appId": app_id, "appSecret": app_secret})
                VAULT.set("meta-pending", {"pages": pages})
                self.api_response(200, {"pages": len(pages)})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except MetaError as error:
                self.api_response(401, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/connections/threads/config":
            try:
                body = self.read_json(32 * 1024)
                app_id = str(body.get("appId", "")).strip()
                app_secret = str(body.get("appSecret", "")).strip()
                if not app_id.isdigit() or len(app_secret) < 8:
                    raise ValueError("A numeric Threads App ID and Threads App Secret are required")
                VAULT.set("threads-app", {"appId": app_id, "appSecret": app_secret})
                self.api_response(200, {"authorizationUrl": "/api/oauth/threads/start"})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/connections/threads/token":
            try:
                body = self.read_json(128 * 1024)
                app_id = str(body.get("appId", "")).strip()
                app_secret = str(body.get("appSecret", "")).strip()
                supplied_token = str(body.get("accessToken", "")).strip()
                if not app_id.isdigit() or len(app_secret) < 8 or len(supplied_token) < 20:
                    raise ValueError("Threads App ID, App Secret, and access token are required")
                client = ThreadsClient(app_id, app_secret)
                try:
                    token, expires_in = client.long_lived_token(supplied_token)
                except ThreadsError:
                    token, expires_in = supplied_token, None
                profile = client.profile(token)
                if not profile.get("id"):
                    raise ThreadsError("Threads could not validate this access token")
                username = profile.get("username") or profile["id"]
                VAULT.set("threads-app", {"appId": app_id, "appSecret": app_secret})
                VAULT.set("threads", {"userId": profile["id"], "username": profile.get("username"), "accessToken": token, "expiresIn": expires_in, "appId": app_id, "appSecret": app_secret})
                STORAGE.set_connection("threads", f"@{username}")
                self.api_response(200, {"displayName": f"@{username}"})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except ThreadsError as error:
                self.api_response(401, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/connections/meta/select":
            try:
                body = self.read_json(4096)
                page_id = str(body.get("pageId", ""))
                pending = VAULT.get("meta-pending") or {"pages": []}
                page = next((item for item in pending["pages"] if str(item.get("id")) == page_id), None)
                if not page or not page.get("access_token"):
                    raise ValueError("Select an authorized Facebook Page")
                VAULT.set("facebook", {"pageId": page["id"], "pageName": page["name"], "accessToken": page["access_token"]})
                STORAGE.set_connection("facebook", page["name"])
                instagram = page.get("instagram_business_account")
                if instagram:
                    VAULT.set("instagram", {"userId": instagram["id"], "username": instagram.get("username"), "accessToken": page["access_token"]})
                    STORAGE.set_connection("instagram", f"@{instagram.get('username')}" if instagram.get("username") else instagram["id"])
                VAULT.delete("meta-pending")
                self.api_response(200, {"facebook": page["name"], "instagram": instagram})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/connections/bluesky":
            try:
                body = self.read_json(32 * 1024)
                handle = str(body.get("handle", "")).strip().lstrip("@")
                password = str(body.get("password", "")).strip()
                auth_factor_token = str(body.get("authFactorToken", "")).strip()
                service = str(body.get("service", "https://bsky.social")).strip().rstrip("/")
                if not handle or not password or not service.startswith("https://"):
                    raise ValueError("Handle, app password, and an HTTPS service are required")
                client = BlueskyClient(handle, password, service)
                client.login(auth_factor_token or None)
                VAULT.set("bluesky", {"handle": handle, "refreshToken": client.refresh_token, "service": service})
                STORAGE.set_connection("bluesky", f"@{handle}")
                STORAGE.requeue_platform("bluesky")
                self.api_response(200, {"platform": "bluesky", "displayName": f"@{handle}", "status": "connected"})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            except BlueskyError as error:
                self.api_response(401, {"error": str(error)})
            except VaultError as error:
                self.api_response(503, {"error": str(error)})
            return
        if path == "/api/settings/delivery":
            try:
                body = self.read_json(4096)
                if not isinstance(body.get("enabled"), bool):
                    raise ValueError("enabled must be a boolean")
                STORAGE.set_setting("delivery_enabled", body["enabled"])
                self.api_response(200, {"enabled": body["enabled"]})
            except (ValueError, json.JSONDecodeError) as error:
                self.api_response(400, {"error": str(error)})
            return
        if not path.startswith("/api/posts/"):
            self.api_response(404, {"error": "Not found"})
            return
        post_id = path.rsplit("/", 1)[-1]
        if not POST_ID.fullmatch(post_id):
            self.api_response(400, {"error": "Invalid post ID"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 50 * 1024 * 1024:
                self.api_response(413, {"error": "Post is too large"})
                return
            post = json.loads(self.rfile.read(length))
            if post.get("id") != post_id or not isinstance(post.get("text"), str) or not isinstance(post.get("destinations"), dict) or not isinstance(post.get("media"), list):
                raise ValueError("Invalid post")
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.api_response(400, {"error": "Invalid post"})
            return
        STORAGE.put_post(post)
        self.api_response(200, {"id": post_id})

    def do_DELETE(self):
        path = self.api_path()
        if path == "/api/connections/bluesky":
            VAULT.delete("bluesky")
            STORAGE.delete_connection("bluesky")
            STORAGE.set_setting("delivery_enabled", False)
            self.api_response(204)
            return
        if path == "/api/connections/threads":
            VAULT.delete("threads")
            VAULT.delete("threads-app")
            STORAGE.delete_connection("threads")
            self.api_response(204)
            return
        if path == "/api/connections/meta":
            for name in ("facebook", "instagram", "meta-app", "meta-oauth", "meta-pending"):
                VAULT.delete(name)
            STORAGE.delete_connection("facebook")
            STORAGE.delete_connection("instagram")
            self.api_response(204)
            return
        if not path.startswith("/api/posts/"):
            self.api_response(404, {"error": "Not found"})
            return
        post_id = path.rsplit("/", 1)[-1]
        if not POST_ID.fullmatch(post_id):
            self.api_response(400, {"error": "Invalid post ID"})
            return
        STORAGE.delete_post(post_id)
        self.api_response(204)

    def send_head(self):
        path = unquote(self.api_path())
        if not is_public_asset(path):
            self.send_error(404)
            return None
        # Replace previously cached prototype files even when a browser
        # revalidates them with an old Last-Modified timestamp.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        if "If-None-Match" in self.headers:
            del self.headers["If-None-Match"]
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5500)
    args = parser.parse_args()
    initialize_database()
    worker = DeliveryWorker(STORAGE, VAULT)
    worker.start()
    handler = partial(PreviewHandler, directory=str(Path(__file__).resolve().parent))
    with ThreadingHTTPServer(("0.0.0.0", args.port), handler) as server:
        print(f"Polysocial local service: http://127.0.0.1:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
