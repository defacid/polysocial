import tempfile
import unittest
from pathlib import Path

from polysocial.bluesky import BlueskyClient, link_facets, split_text
from polysocial.storage import Storage
from polysocial.vault import CredentialVault, VaultError


class FakeBluesky(BlueskyClient):
    def __init__(self):
        super().__init__("defacid.com", "secret")
        self.calls = []

    def _request(self, method, nsid, payload=None, content_type="application/json"):
        self.calls.append((nsid, payload))
        if nsid.endswith("createSession"):
            return {"did": "did:plc:test", "accessJwt": "token", "refreshJwt": "refresh"}
        if nsid.endswith("refreshSession"):
            return {"did": "did:plc:test", "accessJwt": "new-token", "refreshJwt": "new-refresh"}
        if nsid.endswith("uploadBlob"):
            return {"blob": {"$type": "blob", "ref": {"$link": "cid"}, "mimeType": content_type, "size": len(payload)}}
        number = sum(call[0].endswith("createRecord") for call in self.calls)
        return {"uri": f"at://did:plc:test/app.bsky.feed.post/{number}", "cid": f"cid-{number}"}


class BlueskyTests(unittest.TestCase):
    def test_split_is_bounded_and_preserves_text(self):
        text = ("A sentence with words. " * 40).strip()
        parts = split_text(text)
        self.assertTrue(all(0 < len(part) <= 300 for part in parts))
        self.assertEqual(" ".join(parts), text)

    def test_links_use_utf8_byte_offsets(self):
        facets = link_facets("Hi 🦋 https://example.com/test.")
        self.assertEqual(facets[0]["index"], {"byteStart": 8, "byteEnd": 32})

    def test_publish_builds_reply_chain(self):
        client = FakeBluesky()
        refs = client.publish("One. " * 120, [])
        records = [payload["record"] for nsid, payload in client.calls if nsid.endswith("createRecord")]
        self.assertGreater(len(records), 1)
        self.assertNotIn("reply", records[0])
        self.assertEqual(records[1]["reply"]["root"], refs[0])
        self.assertEqual(records[1]["reply"]["parent"], refs[0])

    def test_login_includes_email_factor_token(self):
        client = FakeBluesky()
        client.login("123456")
        self.assertEqual(client.calls[0][1]["authFactorToken"], "123456")

    def test_refresh_rotates_session_tokens(self):
        client = FakeBluesky()
        client.resume("old-refresh")
        self.assertEqual(client.did, "did:plc:test")
        self.assertEqual(client.access_token, "new-token")
        self.assertEqual(client.refresh_token, "new-refresh")

    def test_storage_creates_platform_deliveries(self):
        with tempfile.TemporaryDirectory() as folder:
            storage = Storage(Path(folder) / "test.sqlite3")
            storage.migrate()
            storage.put_post({"id": "PS-TEST", "text": "hello", "destinations": {"bluesky": "defacid", "facebook": "none"}, "scheduledFor": "", "createdAt": "2026-01-01T00:00:00", "media": []})
            rows = storage.list_deliveries("PS-TEST")
            self.assertEqual([(row["platform"], row["status"]) for row in rows], [("bluesky", "queued")])

    def test_encrypted_vault_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            vault = CredentialVault(Path(folder))
            value = {"handle": "test.invalid", "password": "not-a-real-secret"}
            vault.set("bluesky", value)
            self.assertEqual(vault.get("bluesky"), value)
            self.assertNotIn(b"not-a-real-secret", (Path(folder) / "bluesky.vault").read_bytes())
            vault.delete("bluesky")
            self.assertIsNone(vault.get("bluesky"))


if __name__ == "__main__":
    unittest.main()
