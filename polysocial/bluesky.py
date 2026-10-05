"""Minimal AT Protocol publisher used by the local delivery worker."""

from datetime import datetime, timezone
import base64
import json
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .bluesky_oauth import resource_request


URL = re.compile(r"https?://[^\s]+")


class BlueskyError(RuntimeError):
    pass


def split_text(text, limit=300):
    """Split text on useful boundaries while never exceeding *limit*."""
    remaining = text.strip()
    if not remaining:
        return [""]
    parts = []
    while len(remaining) > limit:
        window = remaining[: limit + 1]
        candidates = []
        for pattern, weight in ((r"\n\n", 3), (r"(?<=[.!?])\s+", 2), (r"\s+", 1)):
            candidates.extend((match.end(), weight) for match in re.finditer(pattern, window))
        cut = max(candidates, key=lambda item: (item[1], item[0]))[0] if candidates else limit
        part = remaining[:cut].strip()
        if not part:
            part, cut = remaining[:limit], limit
        parts.append(part)
        remaining = remaining[cut:].strip()
    if remaining or not parts:
        parts.append(remaining)
    return parts


def link_facets(text):
    facets = []
    for match in URL.finditer(text):
        before = text[: match.start()].encode("utf-8")
        value = match.group(0).rstrip(".,;:!?)")
        facets.append({
            "index": {"byteStart": len(before), "byteEnd": len(before) + len(value.encode("utf-8"))},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": value}],
        })
    return facets


class BlueskyClient:
    def __init__(self, handle, password=None, service="https://bsky.social", oauth=None):
        self.handle = handle.lstrip("@")
        self.password = password
        self.service = service.rstrip("/")
        self.did = None
        self.access_token = None
        self.refresh_token = None
        self.oauth = oauth

    def _request(self, method, nsid, payload=None, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else (json.dumps(payload).encode() if payload is not None else None)
        if self.oauth:
            result = resource_request(self.oauth, method, f"{self.service}/xrpc/{nsid}", body, {"Content-Type": content_type})
            self.access_token = self.oauth["accessToken"]
            return result
        headers = {"Content-Type": content_type, "Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        request = Request(f"{self.service}/xrpc/{nsid}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise BlueskyError(f"Bluesky returned {error.code}: {detail[:500]}") from error
        except OSError as error:
            raise BlueskyError(f"Could not reach Bluesky: {error}") from error

    def login(self, auth_factor_token=None):
        payload = {"identifier": self.handle, "password": self.password}
        if auth_factor_token:
            payload["authFactorToken"] = auth_factor_token
        session = self._request("POST", "com.atproto.server.createSession", payload)
        self.did = session["did"]
        self.access_token = session["accessJwt"]
        self.refresh_token = session["refreshJwt"]
        return session

    def resume(self, refresh_token):
        self.access_token = refresh_token
        session = self._request("POST", "com.atproto.server.refreshSession")
        self.did = session["did"]
        self.access_token = session["accessJwt"]
        self.refresh_token = session["refreshJwt"]
        return session

    def upload_image(self, media):
        blob = self._request("POST", "com.atproto.repo.uploadBlob", base64.b64decode(media["data"]), media["type"])
        return {"alt": media.get("alt", ""), "image": blob["blob"]}

    def _video_request(self, method, nsid, payload=None):
        body = payload if isinstance(payload, bytes) else (json.dumps(payload).encode() if payload is not None else None)
        if self.oauth:
            headers = {"atproto-proxy": "did:web:video.bsky.app"}
            if isinstance(payload, bytes):
                headers["Content-Type"] = "video/mp4"
            return resource_request(self.oauth, method, f"https://video.bsky.app/xrpc/{nsid}", body, headers)
        headers = {"Accept": "application/json", "atproto-proxy": "did:web:video.bsky.app"}
        if isinstance(payload, bytes):
            headers["Content-Type"] = "video/mp4"
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        request = Request(f"https://video.bsky.app/xrpc/{nsid}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=90) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise BlueskyError(f"Bluesky video returned {error.code}: {detail[:500]}") from error
        except OSError as error:
            raise BlueskyError(f"Could not reach Bluesky video service: {error}") from error

    def upload_video(self, media):
        result = self._video_request("POST", "app.bsky.video.uploadVideo", base64.b64decode(media["data"]))
        job = result["jobStatus"]
        for attempt in range(25):
            if job.get("state") == "JOB_STATE_COMPLETED" and job.get("blob"):
                return {"$type": "app.bsky.embed.video", "video": job["blob"], "alt": media.get("alt", "")}
            if job.get("state") == "JOB_STATE_FAILED":
                raise BlueskyError(f"Bluesky could not process video: {job.get('message') or job.get('error') or job.get('failureCode') or 'unknown error'}")
            if attempt < 24:
                time.sleep(5)
                job = self._video_request("GET", f"app.bsky.video.getJobStatus?jobId={job['jobId']}")["jobStatus"]
        raise BlueskyError("Bluesky video was still processing after two minutes; verify Bluesky before retrying")

    def publish(self, text, media):
        if not self.access_token:
            self.login()
        video = next((item for item in media if item.get("type") == "video/mp4"), None)
        images = [self.upload_image(item) for item in media[:4] if item.get("type", "").startswith("image/")]
        refs, root, parent = [], None, None
        for index, part in enumerate(split_text(text)):
            record = {"$type": "app.bsky.feed.post", "text": part, "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
            facets = link_facets(part)
            if facets:
                record["facets"] = facets
            if index == 0 and images:
                record["embed"] = {"$type": "app.bsky.embed.images", "images": images}
            elif index == 0 and video:
                record["embed"] = self.upload_video(video)
            if parent:
                record["reply"] = {"root": root, "parent": parent}
            result = self._request("POST", "com.atproto.repo.createRecord", {"repo": self.did, "collection": "app.bsky.feed.post", "record": record})
            ref = {"uri": result["uri"], "cid": result["cid"]}
            root = root or ref
            parent = ref
            refs.append(ref)
        return refs
