import time
import unittest
from urllib.parse import parse_qs, urlsplit

from polysocial.media_urls import signed_url, valid_signature


class MediaUrlTests(unittest.TestCase):
    def test_signed_url_round_trip(self):
        url = signed_url("https://social.example", "test-secret", "PS-TEST", 2, lifetime=60)
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/media/PS-TEST/2")
        self.assertTrue(valid_signature("test-secret", "PS-TEST", 2, query["expires"][0], query["signature"][0]))

    def test_tampering_and_expiry_are_rejected(self):
        expires = int(time.time()) - 1
        self.assertFalse(valid_signature("test-secret", "PS-TEST", 0, expires, "invalid"))


if __name__ == "__main__":
    unittest.main()
