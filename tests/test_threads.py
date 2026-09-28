import unittest
import io
import json
from urllib.parse import parse_qs, urlsplit

from polysocial.threads import ThreadsClient


class ThreadsTests(unittest.TestCase):
    def test_authorization_is_separate_and_requests_publish(self):
        url = ThreadsClient("123", "secret").authorization_url("https://example.test/threads", "state-value")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(urlsplit(url).netloc, "threads.net")
        self.assertEqual(query["client_id"], ["123"])
        self.assertEqual(query["redirect_uri"], ["https://example.test/threads"])
        self.assertEqual(set(query["scope"][0].split(",")), {"threads_basic", "threads_content_publish"})
        self.assertEqual(query["state"], ["state-value"])

    def test_long_text_publishes_as_reply_chain(self):
        calls = []
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def opener(request, timeout=0):
            calls.append(request)
            if request.method == "GET":
                return Response(b'{"permalink":"https://www.threads.net/@test/post/one"}')
            number = len([call for call in calls if call.method == "POST"])
            return Response(json.dumps({"id": f"id-{number}"}).encode())
        ids, permalink = ThreadsClient("123", "secret", opener=opener).publish("user", "token", "Words. " * 160)
        creates = [parse_qs(call.data.decode()) for call in calls if call.full_url.endswith("/threads")]
        self.assertGreater(len(creates), 1)
        self.assertNotIn("reply_to_id", creates[0])
        self.assertEqual(creates[1]["reply_to_id"], [ids[0]])
        self.assertEqual(permalink, "https://www.threads.net/@test/post/one")


if __name__ == "__main__":
    unittest.main()
