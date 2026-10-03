"""Small Meta Graph API OAuth client for Facebook Pages and linked Instagram accounts."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import base64
import mimetypes
import secrets


class MetaError(RuntimeError):
    pass


class MetaClient:
    graph = "https://graph.facebook.com/v26.0"
    dialog = "https://www.facebook.com/v26.0/dialog/oauth"

    def __init__(self, app_id, app_secret, config_id=None, opener=urlopen):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config_id = config_id
        self.opener = opener

    def authorization_url(self, redirect_uri, state):
        parameters = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
        }
        if self.config_id:
            parameters.update(config_id=self.config_id, override_default_response_type="true")
        else:
            parameters["scope"] = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
            parameters["auth_type"] = "rerequest"
        query = urlencode(parameters)
        return f"{self.dialog}?{query}"

    def _get(self, path, parameters):
        url = f"{self.graph}{path}?{urlencode(parameters)}"
        try:
            with self.opener(Request(url, headers={"Accept": "application/json"}), timeout=20) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise MetaError(f"Meta returned {error.code}: {detail[:500]}") from error

    def _post(self, path, parameters, files=None):
        if files:
            boundary = f"----polysocial-{secrets.token_hex(12)}"
            chunks = []
            for name, value in parameters.items():
                chunks.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode(),))
            for name, filename, content_type, content in files:
                chunks.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(), content, b"\r\n"))
            chunks.append(f"--{boundary}--\r\n".encode())
            data = b"".join(chunks)
            content_type = f"multipart/form-data; boundary={boundary}"
        else:
            data = urlencode(parameters).encode()
            content_type = "application/x-www-form-urlencoded"
        request = Request(f"{self.graph}{path}", data=data, method="POST", headers={"Accept": "application/json", "Content-Type": content_type})
        try:
            with self.opener(request, timeout=60) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise MetaError(f"Meta returned {error.code}: {detail[:500]}") from error

    def exchange_code(self, code, redirect_uri):
        result = self._get("/oauth/access_token", {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        if not result.get("access_token"):
            raise MetaError("Meta did not return an access token")
        return result["access_token"]

    def pages(self, user_token):
        result = self._get("/me/accounts", {
            "fields": "id,name,access_token,instagram_business_account{id,username}",
            "access_token": user_token,
            "limit": 100,
        })
        return result.get("data", [])

    def publish_facebook(self, page_id, token, text, media):
        videos = [item for item in media if item.get("type") == "video/mp4"]
        if videos:
            video = videos[0]
            result = self._post(f"/{page_id}/videos", {"description": text, "access_token": token}, [
                ("source", video.get("name", "polysocial.mp4"), "video/mp4", base64.b64decode(video["data"]))
            ])
            return result["id"]
        images = [item for item in media if item.get("type", "").startswith("image/")]
        if not images:
            result = self._post(f"/{page_id}/feed", {"message": text, "access_token": token})
            return result["id"]
        photo_ids = []
        for index, image in enumerate(images):
            content_type = image.get("type", "image/jpeg")
            extension = mimetypes.guess_extension(content_type) or ".jpg"
            result = self._post(f"/{page_id}/photos", {"published": "false", "access_token": token}, [
                ("source", f"polysocial-{index}{extension}", content_type, base64.b64decode(image["data"]))
            ])
            photo_ids.append(result["id"])
        parameters = {"message": text, "access_token": token}
        for index, photo_id in enumerate(photo_ids):
            parameters[f"attached_media[{index}]"] = json.dumps({"media_fbid": photo_id})
        result = self._post(f"/{page_id}/feed", parameters)
        return result["id"]

    def publish_instagram(self, user_id, token, text, media_urls, video=False):
        if not media_urls:
            raise MetaError("Instagram requires an image or video")
        if video:
            container = self._post(f"/{user_id}/media", {"media_type": "REELS", "video_url": media_urls[0], "caption": text, "access_token": token})
            self._wait_for_container(container["id"], token)
        elif len(media_urls) == 1:
            container = self._post(f"/{user_id}/media", {"image_url": media_urls[0], "caption": text, "access_token": token})
        else:
            children = []
            for url in media_urls[:10]:
                child = self._post(f"/{user_id}/media", {"image_url": url, "is_carousel_item": "true", "access_token": token})
                children.append(child["id"])
            container = self._post(f"/{user_id}/media", {"media_type": "CAROUSEL", "children": ",".join(children), "caption": text, "access_token": token})
        published = self._post(f"/{user_id}/media_publish", {"creation_id": container["id"], "access_token": token})
        try:
            details = self._get(f"/{published['id']}", {"fields": "permalink", "access_token": token})
            permalink = details.get("permalink")
        except MetaError:
            # The post is already live; failure to decorate its history entry
            # must never cause a duplicate retry.
            permalink = None
        return published["id"], permalink

    def _wait_for_container(self, container_id, token):
        import time
        for attempt in range(13):
            result = self._get(f"/{container_id}", {"fields": "status_code,status", "access_token": token})
            status = result.get("status_code") or result.get("status")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise MetaError(f"Instagram could not process video: {status}")
            if attempt < 12:
                time.sleep(5)
        raise MetaError("Instagram video was still processing after 60 seconds; verify Instagram before retrying")
