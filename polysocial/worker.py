"""Restart-safe local delivery loop."""

from datetime import datetime, timedelta, timezone
import json
import os
import threading
import time

from .bluesky import BlueskyClient
from .media_urls import signed_url
from .meta import MetaClient
from .threads import ThreadsClient


class DeliveryWorker(threading.Thread):
    daemon = True

    def __init__(self, storage, vault, interval=5):
        super().__init__(name="polysocial-delivery-worker")
        self.storage = storage
        self.vault = vault
        self.interval = interval
        self.stopping = threading.Event()

    @property
    def configured(self):
        return any(self.vault.get(name) for name in ("bluesky", "facebook", "instagram", "threads"))

    @property
    def enabled(self):
        return bool(self.storage.setting("delivery_enabled", False))

    def run(self):
        while not self.stopping.wait(self.interval):
            if not self.configured or not self.enabled:
                continue
            for platform in ("bluesky", "facebook", "instagram", "threads"):
                credentials = self.vault.get(platform)
                if not credentials:
                    continue
                for post in self.storage.due_deliveries(platform):
                    self.publish(post, platform, credentials)

    def publish(self, post, platform, credentials):
        deliveries = self.storage.list_deliveries(post["id"])
        current = next(row for row in deliveries if row["platform"] == platform)
        attempts = current["attempts"] + 1
        self.storage.delivery(post["id"], platform, "publishing", attempts=attempts, error=None)
        try:
            remote_id, remote_url, receipt = self._publish(post, platform, credentials)
            self.storage.delivery(post["id"], platform, "delivered", remote_id=remote_id, remote_url=remote_url, receipt=json.dumps(receipt), error=None, next_attempt_at=None)
        except Exception as error:
            status = "retry" if attempts < 5 else "failed"
            retry_at = (datetime.now().astimezone() + timedelta(seconds=30 * (2 ** (attempts - 1)))).isoformat(timespec="seconds") if status == "retry" else None
            self.storage.delivery(post["id"], platform, status, attempts=attempts, error=str(error)[:1000], next_attempt_at=retry_at)

    def _publish(self, post, platform, credentials):
        text = post.get("text", "")
        media = post.get("media", [])
        if platform == "bluesky":
            if not credentials.get("refreshToken"):
                raise RuntimeError("Bluesky connection must be renewed before publishing")
            client = BlueskyClient(credentials["handle"], service=credentials.get("service", "https://bsky.social"))
            client.resume(credentials["refreshToken"])
            credentials["refreshToken"] = client.refresh_token
            self.vault.set("bluesky", credentials)
            refs = client.publish(text, media)
            first = refs[0]
            handle = credentials["handle"].lstrip("@")
            rkey = first["uri"].rsplit("/", 1)[-1]
            return first["uri"], f"https://bsky.app/profile/{handle}/post/{rkey}", refs
        if platform == "facebook":
            client = MetaClient("", "")
            post_id = client.publish_facebook(credentials["pageId"], credentials["accessToken"], text, media)
            return post_id, f"https://www.facebook.com/{post_id}", {"id": post_id}

        image_urls = self._media_urls(post)
        if platform == "instagram":
            client = MetaClient("", "")
            media_id, permalink = client.publish_instagram(credentials["userId"], credentials["accessToken"], text, image_urls)
            return media_id, permalink, {"id": media_id}
        if platform == "threads":
            client = ThreadsClient(credentials.get("appId", ""), credentials.get("appSecret", ""))
            expires_at = credentials.get("expiresAt")
            if expires_at and datetime.fromisoformat(expires_at) - datetime.now(timezone.utc) <= timedelta(days=7):
                token, expires_in = client.refresh_token(credentials["accessToken"])
                credentials["accessToken"] = token
                credentials["expiresIn"] = expires_in
                credentials["expiresAt"] = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat() if expires_in else None
                credentials["lastCheckedAt"] = datetime.now(timezone.utc).isoformat()
                self.vault.set("threads", credentials)
            ids, permalink = client.publish(credentials["userId"], credentials["accessToken"], text, image_urls)
            return ids[0], permalink, ids
        raise RuntimeError(f"Unsupported destination: {platform}")

    def _media_urls(self, post):
        images = [item for item in post.get("media", []) if item.get("type", "").startswith("image/")]
        if not images:
            return []
        origin = os.environ.get("POLYSOCIAL_PUBLIC_ORIGIN", "").rstrip("/")
        if not origin:
            raise RuntimeError("A public Polysocial origin is required for Meta media publishing")
        secret = self.storage.setting("media_signing_key")
        if not secret:
            import secrets
            secret = secrets.token_urlsafe(32)
            self.storage.set_setting("media_signing_key", secret)
        return [signed_url(origin, secret, post["id"], index) for index, item in enumerate(post.get("media", [])) if item.get("type", "").startswith("image/")]
