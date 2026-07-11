"""Central database connection configuration for all test/benchmark scripts.

Connection parameters are read from environment variables, optionally
loaded from a `.env` file in the project root (not committed to git).
Copy `.env.example` to `.env` and adjust the values for your environment.
"""

import os
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DB_CONFIG = {
    "host": os.environ.get("FIREBIRD_HOST", "localhost"),
    "database": os.environ.get("FIREBIRD_DATABASE", "database.fdb"),
    "port": int(os.environ.get("FIREBIRD_PORT", "3050")),
    "user": os.environ.get("FIREBIRD_USER", "SYSDBA"),
    "password": os.environ.get("FIREBIRD_PASSWORD", "masterkey"),
}
