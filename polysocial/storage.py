"""SQLite persistence and migrations for posts and per-platform deliveries."""

from datetime import datetime
from pathlib import Path
import json
import sqlite3


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Storage:
    def __init__(self, database: Path):
        self.database = database

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def migrate(self):
        self.database.parent.mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS connections (
                platform TEXT PRIMARY KEY, display_name TEXT NOT NULL,
                status TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
                post_id TEXT NOT NULL, platform TEXT NOT NULL, status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at TEXT,
                remote_id TEXT, remote_url TEXT, error TEXT, receipt TEXT,
                updated_at TEXT NOT NULL, PRIMARY KEY(post_id, platform),
                FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)""")
            db.execute("UPDATE deliveries SET status='not_implemented',updated_at=? WHERE status='waiting_for_crosspost'", (now(),))
            posts = db.execute("SELECT payload FROM posts").fetchall()
            for row in posts:
                post = json.loads(row["payload"])
                for platform, selection in post.get("destinations", {}).items():
                    if selection == "none":
                        continue
                    # Preserve legacy rows as-is, but every supported destination is
                    # now eligible for delivery when a missing row is repaired.
                    status = "queued"
                    db.execute("INSERT OR IGNORE INTO deliveries(post_id,platform,status,updated_at) VALUES(?,?,?,?)", (post["id"], platform, status, now()))

    def list_posts(self):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM posts").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_post(self, post_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM posts WHERE id=?", (post_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def put_post(self, post):
        selected = {key for key, value in post["destinations"].items() if value != "none"}
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO posts VALUES (?,?)", (post["id"], json.dumps(post)))
            for platform in selected:
                status = "queued"
                db.execute("""INSERT INTO deliveries(post_id,platform,status,updated_at)
                    VALUES(?,?,?,?) ON CONFLICT(post_id,platform) DO UPDATE SET
                    status=CASE WHEN deliveries.status='delivered' THEN deliveries.status ELSE excluded.status END,
                    updated_at=excluded.updated_at""", (post["id"], platform, status, now()))
            if selected:
                placeholders = ",".join("?" for _ in selected)
                db.execute(f"DELETE FROM deliveries WHERE post_id=? AND platform NOT IN ({placeholders})", (post["id"], *selected))
            else:
                db.execute("DELETE FROM deliveries WHERE post_id=?", (post["id"],))

    def delete_post(self, post_id):
        with self.connect() as db:
            db.execute("DELETE FROM posts WHERE id=?", (post_id,))

    def due_bluesky(self):
        return self.due_deliveries("bluesky")

    def due_deliveries(self, platform):
        local_now = datetime.now().astimezone()
        with self.connect() as db:
            rows = db.execute("""SELECT p.payload,d.status,d.next_attempt_at FROM posts p JOIN deliveries d ON d.post_id=p.id
                WHERE d.platform=? AND d.status IN ('queued','retry') ORDER BY d.updated_at LIMIT 10""", (platform,)).fetchall()
        due = []
        for row in rows:
            post = json.loads(row["payload"])
            scheduled = post.get("scheduledFor")
            retry_at = row["next_attempt_at"]
            if retry_at and datetime.fromisoformat(retry_at).astimezone() > local_now:
                continue
            if not scheduled or datetime.fromisoformat(scheduled).astimezone() <= local_now:
                due.append(post)
        return due

    def delivery(self, post_id, platform, status, **values):
        allowed = {"remote_id", "remote_url", "error", "receipt", "next_attempt_at", "attempts"}
        fields = {key: value for key, value in values.items() if key in allowed}
        fields.update(status=status, updated_at=now())
        assignments = ",".join(f"{key}=?" for key in fields)
        with self.connect() as db:
            db.execute(f"UPDATE deliveries SET {assignments} WHERE post_id=? AND platform=?", (*fields.values(), post_id, platform))

    def list_deliveries(self, post_id=None):
        with self.connect() as db:
            if post_id:
                rows = db.execute("SELECT * FROM deliveries WHERE post_id=? ORDER BY platform", (post_id,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM deliveries ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def set_connection(self, platform, display_name, status="connected"):
        with self.connect() as db:
            db.execute("""INSERT INTO connections(platform,display_name,status,updated_at) VALUES(?,?,?,?)
                ON CONFLICT(platform) DO UPDATE SET display_name=excluded.display_name,status=excluded.status,updated_at=excluded.updated_at""", (platform, display_name, status, now()))

    def delete_connection(self, platform):
        with self.connect() as db:
            db.execute("DELETE FROM connections WHERE platform=?", (platform,))

    def connections(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM connections ORDER BY platform")]

    def requeue_platform(self, platform):
        with self.connect() as db:
            db.execute("""UPDATE deliveries SET status='queued',attempts=0,next_attempt_at=NULL,error=NULL,updated_at=?
                WHERE platform=? AND status IN ('retry','failed')""", (now(), platform))

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_setting(self, key, value):
        with self.connect() as db:
            db.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
