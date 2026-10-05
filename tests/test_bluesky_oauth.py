import base64
import json
import unittest

from polysocial import bluesky_oauth


class BlueskyOAuthTests(unittest.TestCase):
    def test_only_public_https_endpoints_are_accepted(self):
        self.assertTrue(bluesky_oauth._safe_https("https://bsky.social/xrpc"))
        self.assertFalse(bluesky_oauth._safe_https("http://bsky.social/xrpc"))
        self.assertFalse(bluesky_oauth._safe_https("https://127.0.0.1/xrpc"))
        self.assertFalse(bluesky_oauth._safe_https("https://localhost/xrpc"))
        self.assertFalse(bluesky_oauth._safe_https("https://bsky.social@evil.example/xrpc"))

    def test_dpop_proof_exposes_only_a_public_jwk(self):
        proof = bluesky_oauth._dpop(bluesky_oauth._private_key(), "POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord", "token")
        header = json.loads(base64.urlsafe_b64decode(proof.split(".")[0] + "=="))
        self.assertEqual("dpop+jwt", header["typ"])
        self.assertEqual("EC", header["jwk"]["kty"])
        self.assertNotIn("d", header["jwk"])

    def test_invalid_handle_is_rejected_before_network_access(self):
        with self.assertRaises(bluesky_oauth.BlueskyOAuthError):
            bluesky_oauth._resolve("not a handle")


if __name__ == "__main__":
    unittest.main()
