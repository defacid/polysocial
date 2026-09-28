"""Threads OAuth client and token lifecycle."""

import json
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .bluesky import split_text


class ThreadsError(RuntimeError):
    pass


class ThreadsClient:
    authorize_endpoint = "https://threads.net/oauth/authorize"
    graph = "https://graph.threads.net"

    def __init__(self, app_id, app_secret, opener=urlopen):
        self.app_id = app_id
        self.app_secret = app_secret
        self.opener = opener

    def authorization_url(self, redirect_uri, state):
        return f"{self.authorize_endpoint}?{urlencode({'client_id': self.app_id, 'redirect_uri': redirect_uri, 'scope': 'threads_basic,threads_content_publish', 'response_type': 'code', 'state': state})}"

    def _request(self, url, parameters=None, method="GET"):
        data = urlencode(parameters).encode() if parameters is not None else None
        request = Request(url, data=data, method=method, headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with self.opener(request, timeout=20) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise ThreadsError(f"Threads returned {error.code}: {detail[:500]}") from error

    def exchange_code(self, code, redirect_uri):
        result = self._request(f"{self.graph}/oauth/access_token", {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }, "POST")
        if not result.get("access_token"):
            raise ThreadsError("Threads did not return an access token")
        return result["access_token"]

    def long_lived_token(self, short_token):
        query = urlencode({"grant_type": "th_exchange_token", "client_secret": self.app_secret, "access_token": short_token})
        result = self._request(f"{self.graph}/access_token?{query}")
        return result.get("access_token", short_token), result.get("expires_in")

    def profile(self, token):
        query = urlencode({"fields": "id,username", "access_token": token})
        return self._request(f"{self.graph}/me?{query}")

    def publish(self, user_id, token, text, media_urls=None):
        parts = split_text(text, 500)
        media_urls = media_urls or []
        published_ids = []
        parent = None
        for index, part in enumerate(parts):
            parameters = {"media_type": "TEXT", "text": part, "access_token": token}
            if index == 0 and len(media_urls) == 1:
                parameters.update(media_type="IMAGE", image_url=media_urls[0])
            elif index == 0 and len(media_urls) > 1:
                children = []
                for url in media_urls[:10]:
                    child = self._request(f"{self.graph}/v1.0/{user_id}/threads", {"media_type": "IMAGE", "image_url": url, "is_carousel_item": "true", "access_token": token}, "POST")
                    children.append(child["id"])
                parameters.update(media_type="CAROUSEL", children=",".join(children))
            if parent:
                parameters["reply_to_id"] = parent
            container = self._request(f"{self.graph}/v1.0/{user_id}/threads", parameters, "POST")
            if index == 0 and media_urls:
                self._wait_for_container(container["id"], token)
            published = self._request(f"{self.graph}/v1.0/{user_id}/threads_publish", {"creation_id": container["id"], "access_token": token}, "POST")
            parent = published["id"]
            published_ids.append(parent)
        query = urlencode({"fields": "permalink", "access_token": token})
        try:
            details = self._request(f"{self.graph}/v1.0/{published_ids[0]}?{query}")
            permalink = details.get("permalink")
        except ThreadsError:
            permalink = None
        return published_ids, permalink

    def _wait_for_container(self, container_id, token):
        query = urlencode({"fields": "status,error_message", "access_token": token})
        for attempt in range(7):
            result = self._request(f"{self.graph}/v1.0/{container_id}?{query}")
            status = result.get("status")
            if status in ("FINISHED", "PUBLISHED"):
                return
            if status in ("ERROR", "EXPIRED"):
                raise ThreadsError(f"Threads could not process media: {result.get('error_message') or status}")
            if attempt < 6:
                time.sleep(5)
        raise ThreadsError("Threads media was still processing after 30 seconds; it will be retried")
