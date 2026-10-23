"""Only successful validated probability payloads are durable cache entries."""
import json
from pathlib import Path
import sqlite3
from .config import digest


class ScoreCache:
    def __init__(self, path, identity):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS scores (key TEXT PRIMARY KEY, probabilities TEXT NOT NULL)")
        self.identity = identity
        self.hits = self.calls = self.failures = 0

    def key(self, text):
        return digest({"text": text, "identity": self.identity})

    def get(self, text):
        found = self.conn.execute("SELECT probabilities FROM scores WHERE key=?", (self.key(text),)).fetchone()
        if found:
            self.hits += 1
            return json.loads(found[0])
        return None

    def put(self, text, value):
        self.conn.execute("INSERT OR REPLACE INTO scores VALUES (?,?)", (self.key(text), json.dumps(value, allow_nan=False)))

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
