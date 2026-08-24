import os
import re
import uuid
from pathlib import Path


UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")


def environment_id_path():
    return Path(os.getenv("PMQMS_ENVIRONMENT_ID_FILE", "/etc/odoo/environment_id"))


def read_environment_id(path=None):
    identity_path = Path(path) if path else environment_id_path()
    try:
        value = identity_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not UUID_PATTERN.fullmatch(value):
        raise ValueError("Perfect Match environment identity is not a valid UUID.")
    return str(uuid.UUID(value))


def ensure_environment_id(path=None):
    identity_path = Path(path) if path else environment_id_path()
    current = read_environment_id(identity_path)
    if current:
        return current
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    value = str(uuid.uuid4())
    identity_path.write_text(value + "\n", encoding="utf-8")
    try:
        identity_path.chmod(0o600)
    except OSError:
        pass
    return value


def short_environment_id(value):
    return value.replace("-", "")[:8].upper() if value else "Not configured"
