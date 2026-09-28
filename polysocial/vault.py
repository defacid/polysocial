"""Encrypted local credential storage with legacy Windows DPAPI migration."""

from pathlib import Path
import json
import shutil
import subprocess

from cryptography.fernet import Fernet, InvalidToken


class VaultError(RuntimeError):
    pass


class CredentialVault:
    def __init__(self, directory: Path):
        self.directory = directory
        self.powershell = shutil.which("powershell.exe")

    @property
    def available(self):
        return True

    def _path(self, name):
        if not name.replace("-", "").isalnum():
            raise VaultError("Invalid credential name")
        return self.directory / f"{name}.vault"

    def _legacy_path(self, name):
        return self.directory / f"{name}.dpapi"

    def _fernet(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        key_path = self.directory / ".vault-key"
        if not key_path.exists():
            key_path.write_bytes(Fernet.generate_key())
            key_path.chmod(0o600)
        return Fernet(key_path.read_bytes())

    def _get_legacy(self, name):
        path = self._legacy_path(name)
        if not path.exists():
            return None
        if not self.powershell:
            raise VaultError("Legacy Windows credential protection is unavailable")
        script = "$e=[Console]::In.ReadToEnd();$s=ConvertTo-SecureString $e;$b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s);try{[Runtime.InteropServices.Marshal]::PtrToStringBSTR($b)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)}"
        result = subprocess.run([self.powershell, "-NoProfile", "-NonInteractive", "-Command", script], input=path.read_text(encoding="utf-8"), text=True, capture_output=True, timeout=15)
        if result.returncode:
            raise VaultError("Could not unlock the legacy Windows credential")
        return json.loads(result.stdout)

    def set(self, name, value):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(name)
        path.write_bytes(self._fernet().encrypt(json.dumps(value, separators=(",", ":")).encode("utf-8")))
        path.chmod(0o600)

    def get(self, name):
        path = self._path(name)
        if not path.exists():
            return self._get_legacy(name)
        try:
            return json.loads(self._fernet().decrypt(path.read_bytes()))
        except (InvalidToken, ValueError, json.JSONDecodeError) as error:
            raise VaultError("Could not unlock the local credential vault") from error

    def migrate_legacy(self):
        migrated = []
        for path in self.directory.glob("*.dpapi"):
            name = path.stem
            if not self._path(name).exists():
                self.set(name, self._get_legacy(name))
                migrated.append(name)
        return migrated

    def delete(self, name):
        self._path(name).unlink(missing_ok=True)
        self._legacy_path(name).unlink(missing_ok=True)
