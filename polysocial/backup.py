"""Create, verify, and restore Polysocial backup archives."""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sqlite3
import tarfile
import tempfile


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(data_dir, output, include_credentials=False):
    data_dir, output = Path(data_dir).resolve(), Path(output).resolve()
    database = data_dir / "posts.sqlite3"
    if not database.exists():
        raise FileNotFoundError(f"Database not found: {database}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        database_copy = staging / "posts.sqlite3"
        with sqlite3.connect(database) as source, sqlite3.connect(database_copy) as target:
            source.backup(target)
        files = [database_copy]
        media = data_dir / "media"
        if media.exists():
            shutil.copytree(media, staging / "media")
            files.extend(path for path in (staging / "media").rglob("*") if path.is_file())
        if include_credentials:
            credentials = data_dir / "credentials"
            if credentials.exists():
                shutil.copytree(credentials, staging / "credentials")
                files.extend(path for path in (staging / "credentials").rglob("*") if path.is_file())
        manifest = {
            "format": 1,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "includesCredentials": include_credentials,
            "files": {str(path.relative_to(staging)): _sha256(path) for path in files},
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with tarfile.open(output, "w:gz") as archive:
            for path in staging.rglob("*"):
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(staging))
    output.chmod(0o600)
    return output


def verify_backup(archive_path):
    with tempfile.TemporaryDirectory() as temporary, tarfile.open(archive_path, "r:gz") as archive:
        _safe_extract(archive, Path(temporary))
        root = Path(temporary)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["files"].items():
            path = root / name
            if not path.is_file() or _sha256(path) != expected:
                raise ValueError(f"Backup verification failed: {name}")
        with sqlite3.connect(root / "posts.sqlite3") as database:
            result = database.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise ValueError(f"Database integrity check failed: {result}")
        return manifest


def _safe_extract(archive, destination):
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if destination not in target.parents and target != destination:
            raise ValueError("Backup contains an unsafe path")
        if member.issym() or member.islnk():
            raise ValueError("Backup contains an unsupported link")
    archive.extractall(destination)


def restore_backup(archive_path, data_dir):
    manifest = verify_backup(archive_path)
    data_dir = Path(data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary, tarfile.open(archive_path, "r:gz") as archive:
        root = Path(temporary)
        _safe_extract(archive, root)
        database = data_dir / "posts.sqlite3"
        if database.exists():
            safety = data_dir / f"posts.sqlite3.before-restore-{datetime.now():%Y%m%d-%H%M%S}"
            shutil.copy2(database, safety)
            safety.chmod(0o600)
        temporary_db = data_dir / ".posts.sqlite3.restore"
        shutil.copy2(root / "posts.sqlite3", temporary_db)
        temporary_db.chmod(0o600)
        for suffix in ("-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        temporary_db.replace(database)
        if (root / "media").exists():
            restored_media = data_dir / ".media.restore"
            shutil.rmtree(restored_media, ignore_errors=True)
            shutil.copytree(root / "media", restored_media)
            shutil.rmtree(data_dir / "media", ignore_errors=True)
            restored_media.replace(data_dir / "media")
        else:
            shutil.rmtree(data_dir / "media", ignore_errors=True)
        if manifest.get("includesCredentials") and (root / "credentials").exists():
            credentials = data_dir / "credentials"
            credentials.mkdir(mode=0o700, exist_ok=True)
            for source in (root / "credentials").iterdir():
                if source.is_file():
                    shutil.copy2(source, credentials / source.name)
                    (credentials / source.name).chmod(0o600)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(Path.home() / ".local/share/polysocial"))
    parser.add_argument("--output")
    parser.add_argument("--include-credentials", action="store_true")
    parser.add_argument("--verify")
    parser.add_argument("--restore")
    args = parser.parse_args()
    if args.verify:
        manifest = verify_backup(args.verify)
        print(f"Backup is valid ({manifest['createdAt']})")
        return
    if args.restore:
        manifest = restore_backup(args.restore, args.data_dir)
        print(f"Backup restored ({manifest['createdAt']}); restart Polysocial")
        return
    output = args.output or f"polysocial-backup-{datetime.now():%Y%m%d-%H%M%S}.tar.gz"
    print(create_backup(args.data_dir, output, args.include_credentials))


if __name__ == "__main__":
    main()
