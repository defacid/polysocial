import unittest
import io
import json
from urllib.parse import parse_qs, urlsplit

from polysocial.meta import MetaClient


class MetaTests(unittest.TestCase):
    def test_authorization_requests_page_and_instagram_permissions(self):
        url = MetaClient("123", "secret").authorization_url("https://example.test/callback", "state-value")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["state"], ["state-value"])
        scopes = set(query["scope"][0].split(","))
        self.assertEqual(scopes, {"pages_show_list", "pages_read_engagement", "pages_manage_posts", "instagram_basic", "instagram_content_publish"})

    def test_business_login_uses_configuration_instead_of_scopes(self):
        url = MetaClient("123", "secret", "456").authorization_url("https://example.test/callback", "state-value")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["config_id"], ["456"])
        self.assertEqual(query["override_default_response_type"], ["true"])
        self.assertNotIn("scope", query)

    def test_facebook_text_post_uses_page_feed(self):
        calls = []
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def opener(request, timeout=0):
            calls.append(request)
            return Response(json.dumps({"id": "page_post_id"}).encode())
        result = MetaClient("", "", opener=opener).publish_facebook("page", "token", "hello", [])
        self.assertEqual(result, "page_post_id")
        self.assertTrue(calls[0].full_url.endswith("/page/feed"))
        self.assertEqual(parse_qs(calls[0].data.decode())["message"], ["hello"])

    def test_facebook_image_is_uploaded_without_public_url(self):
        calls = []
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def opener(request, timeout=0):
            calls.append(request)
            payload = {"id": "photo_id"} if request.full_url.endswith("/photos") else {"id": "page_post_id"}
            return Response(json.dumps(payload).encode())
        media = [{"type": "image/png", "data": "aGVsbG8="}]
        result = MetaClient("", "", opener=opener).publish_facebook("page", "token", "caption", media)
        self.assertEqual(result, "page_post_id")
        self.assertIn(b'name="source"', calls[0].data)
        self.assertIn(b"hello", calls[0].data)
        self.assertIn(b"photo_id", calls[1].data)


if __name__ == "__main__":
    unittest.main()
