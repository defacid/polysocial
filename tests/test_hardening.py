import base64
import json
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path

from polysocial.backup import create_backup, restore_backup, verify_backup
from polysocial.storage import Storage
from polysocial.validation import validate_post


def post(post_id="PS-TEST", media=None, destinations=None):
    return {
        "id": post_id,
        "text": "hello",
        "createdAt": "2026-01-01T12:00:00+00:00",
        "scheduledFor": "2026-12-01T12:00:00+00:00",
        "media": media or [],
        "destinations": destinations or {"threads": "connected"},
    }


class ValidationTests(unittest.TestCase):
    def test_rejects_video_and_invalid_base64(self):
        errors = validate_post(post(media=[{"type": "video/mp4", "data": "%%%"}]))
        self.assertTrue(any("JPEG" in error for error in errors))

    def test_instagram_requires_image(self):
        errors = validate_post(post(destinations={"instagram": "connected"}))
        self.assertIn("Instagram requires at least one image", errors)

    def test_bluesky_enforces_image_count(self):
        image = {"type": "image/jpeg", "data": base64.b64encode(b"x").decode(), "alt": "test"}
        errors = validate_post(post(media=[image] * 5, destinations={"bluesky": "connected"}))
        self.assertTrue(any("at most 4" in error for error in errors))


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temporary.name) / "posts.sqlite3")
        self.storage.migrate()
        self.storage.put_post(post())

    def tearDown(self):
        self.temporary.cleanup()

    def test_interrupted_publish_is_not_automatically_retried(self):
        self.storage.delivery("PS-TEST", "threads", "publishing")
        self.storage.migrate()
        delivery = self.storage.list_deliveries("PS-TEST")[0]
        self.assertEqual("failed", delivery["status"])
        self.assertIn("verify", delivery["error"])

    def test_retry_targets_one_delivery(self):
        self.storage.delivery("PS-TEST", "threads", "failed", attempts=5, error="bad")
        self.assertTrue(self.storage.retry_delivery("PS-TEST", "threads"))
        delivery = self.storage.list_deliveries("PS-TEST")[0]
        self.assertEqual("queued", delivery["status"])
        self.assertEqual(0, delivery["attempts"])

    def test_attempt_history_survives_delivery_updates(self):
        attempt_id = self.storage.start_attempt("PS-TEST", "threads", 1)
        self.storage.finish_attempt(attempt_id, "retry", "ambiguous", error="Timed out")
        attempts = self.storage.list_attempts("PS-TEST", "threads")
        self.assertEqual(1, len(attempts))
        self.assertEqual("ambiguous", attempts[0]["stage"])
        self.assertEqual("Timed out", attempts[0]["error"])

    def test_running_attempt_becomes_interrupted_on_migration(self):
        self.storage.start_attempt("PS-TEST", "threads", 1)
        self.storage.delivery("PS-TEST", "threads", "publishing")
        self.storage.migrate()
        self.assertEqual("interrupted", self.storage.list_attempts("PS-TEST", "threads")[0]["status"])

    def test_cancel_and_publish_now(self):
        self.assertTrue(self.storage.cancel_delivery("PS-TEST", "threads"))
        self.assertEqual("cancelled", self.storage.list_deliveries("PS-TEST")[0]["status"])
        self.assertTrue(self.storage.publish_now("PS-TEST"))
        self.assertIsNone(self.storage.get_post("PS-TEST")["scheduledFor"])
        self.assertEqual("queued", self.storage.list_deliveries("PS-TEST")[0]["status"])

    def test_media_is_stored_outside_sqlite_and_hydrated(self):
        image = {"name": "one.jpg", "type": "image/jpeg", "data": base64.b64encode(b"image-bytes").decode(), "alt": "Example"}
        self.storage.put_post(post("PS-MEDIA", media=[image], destinations={"bluesky": "connected"}))
        with self.storage.connect() as database:
            payload = json.loads(database.execute("SELECT payload FROM posts WHERE id='PS-MEDIA'").fetchone()[0])
        self.assertNotIn("data", payload["media"][0])
        self.assertTrue((Path(self.temporary.name) / payload["media"][0]["file"]).is_file())
        self.assertEqual(0o700, (Path(self.temporary.name) / "media" / "PS-MEDIA").stat().st_mode & 0o777)
        self.assertEqual(image["data"], self.storage.get_post("PS-MEDIA")["media"][0]["data"])


class BackupTests(unittest.TestCase):
    def test_backup_verify_and_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            data.mkdir()
            storage = Storage(data / "posts.sqlite3")
            storage.migrate()
            storage.put_post(post())
            image = {"name": "one.jpg", "type": "image/jpeg", "data": base64.b64encode(b"image-bytes").decode(), "alt": "Example"}
            storage.put_post(post("PS-MEDIA", media=[image], destinations={"bluesky": "connected"}))
            archive = create_backup(data, root / "backup.tar.gz")
            self.assertFalse(verify_backup(archive)["includesCredentials"])
            storage.delete_post("PS-TEST")
            restore_backup(archive, data)
            self.assertEqual("PS-TEST", storage.list_posts()[0]["id"])
            self.assertEqual(image["data"], storage.get_post("PS-MEDIA")["media"][0]["data"])

    def test_backup_rejects_unsafe_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unsafe.tar.gz"
            source = Path(temporary) / "payload"
            source.write_text("bad")
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(source, arcname="../payload")
            with self.assertRaises(ValueError):
                verify_backup(archive_path)


if __name__ == "__main__":
    unittest.main()
