"""Evidence records, review gates and reproducible exports. No remote fetching."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Stage = Literal["Proposed", "Announced", "Adopted"]
Implementation = Literal["Not assessed", "No evidence supplied", "Evidence supplied"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=5, max_length=250)
    synthetic: bool = True
    responsible_party: str = Field(min_length=2, max_length=250)
    topic: str = Field(min_length=2, max_length=100)
    stage: Stage
    implementation: Implementation = "Not assessed"
    source_url: str = Field(max_length=2000)
    source_date: date
    accessed_on: date
    excerpt: str = Field(min_length=10, max_length=20000)
    document_id: str = Field(default="", max_length=200)
    locator: str = Field(default="", max_length=300)
    implementation_url: str = Field(default="", max_length=2000)
    implementation_excerpt: str = Field(default="", max_length=10000)
    notes: str = Field(default="", max_length=2000)

    @field_validator("source_url", "implementation_url")
    @classmethod
    def valid_url(cls, value):
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use an HTTPS source URL without embedded credentials.")
        return value

    @model_validator(mode="after")
    def evidence_requirements(self):
        if not self.source_url:
            raise ValueError("A source URL is required.")
        if self.accessed_on > date.today() or self.source_date > self.accessed_on:
            raise ValueError("Source and access dates cannot be in the future or reversed.")
        if self.stage == "Adopted" and (not self.document_id or not self.locator):
            raise ValueError("Adopted requires a document identifier and page/paragraph locator.")
        if self.implementation == "Evidence supplied":
            if not self.implementation_url or len(self.implementation_excerpt) < 10:
                raise ValueError("Implementation evidence needs its own URL and excerpt.")
        elif self.implementation_url or self.implementation_excerpt:
            raise ValueError("Select Evidence supplied when adding implementation material.")
        return self


class Advisory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    summary: str = Field(min_length=10, max_length=4000)
    evidence_gaps: list[str] = Field(max_length=15)
    verification_questions: list[str] = Field(max_length=15)
    limitations: list[str] = Field(min_length=1, max_length=15)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def official_host(url: str) -> bool:
    """Host label only; neither authenticates a document nor verifies its claims."""
    host = urlsplit(url).hostname or ""
    return any(host == domain or host.endswith("." + domain) for domain in ("unfccc.int", "cop31.tr"))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, time TEXT NOT NULL, record_id TEXT NOT NULL,
                    action TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.path)

    def records(self, synthetic: bool) -> list[Record]:
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM records ORDER BY id").fetchall()
        records = [Record.model_validate_json(row[0]) for row in rows]
        return [r for r in records if r.synthetic == synthetic]

    def get(self, record_id) -> Record:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM records WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown record.")
        return Record.model_validate_json(row[0])

    def save(self, record: Record):
        record = Record.model_validate(record.model_dump())
        payload = record.model_dump(mode="json")
        digest = fingerprint(payload)
        with self.connect() as db:
            existing = db.execute("SELECT digest, payload FROM records WHERE id=?", (record.id,)).fetchone()
            if existing and json.loads(existing[1])["synthetic"] != record.synthetic:
                raise ValueError("Record identity cannot cross between demo and real workspaces.")
            if existing and existing[0] == digest:
                return digest
            db.execute("INSERT INTO records VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,digest=excluded.digest",
                       (record.id, json.dumps(payload, ensure_ascii=False), digest))
            self._event(db, record.id, "record_saved", digest, payload)
        return digest

    @staticmethod
    def _event(db, record_id, action, digest, payload):
        db.execute("INSERT INTO events(time,record_id,action,digest,payload) VALUES(?,?,?,?,?)",
                   (utc_now(), record_id, action, digest, json.dumps(payload, ensure_ascii=False)))

    def history(self, record_id=None):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            query = "SELECT * FROM events"
            args = ()
            if record_id:
                query += " WHERE record_id=?"
                args = (record_id,)
            rows = db.execute(query + " ORDER BY seq", args).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def review_record(self, record_id, expected_digest, reviewer, decision, rationale):
        if decision not in ("Accepted", "Rejected", "Needs more evidence"):
            raise ValueError("Unknown review decision.")
        if not reviewer.strip() or len(rationale.strip()) < 10:
            raise ValueError("A reviewer and a meaningful rationale are required.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest FROM records WHERE id=?", (record_id,)).fetchone()
            if not row or row[0] != expected_digest:
                raise ValueError("The record changed. Review the current version.")
            self._event(db, record_id, "record_review", expected_digest,
                        {"reviewer": reviewer.strip(), "decision": decision, "rationale": rationale.strip()})

    def review_status(self, record: Record):
        digest = fingerprint(record.model_dump(mode="json"))
        reviews = [e for e in self.history(record.id) if e["action"] == "record_review" and e["digest"] == digest]
        return reviews[-1]["payload"]["decision"] if reviews else "Pending"

    def review_advisory(self, record: Record, advisory: Advisory, reviewer, decision, rationale):
        if decision not in ("Accepted", "Rejected", "Needs more evidence"):
            raise ValueError("Unknown review decision.")
        if not reviewer.strip() or len(rationale.strip()) < 10:
            raise ValueError("A reviewer and rationale are required.")
        digest = fingerprint(record.model_dump(mode="json"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest FROM records WHERE id=?", (record.id,)).fetchone()
            if not row or row[0] != digest:
                raise ValueError("The record changed. Generate a new advisory.")
            self._event(db, record.id, "advisory_review", digest,
                        {"reviewer": reviewer.strip(), "decision": decision, "rationale": rationale.strip(),
                         "advisory": advisory.model_dump(), "advisory_sha256": fingerprint(advisory.model_dump())})


def import_records(raw: bytes) -> list[Record]:
    if len(raw) > 2_000_000:
        raise ValueError("JSON import must be smaller than 2 MB.")
    values = json.loads(raw)
    if not isinstance(values, list) or not 1 <= len(values) <= 200:
        raise ValueError("Import an array containing 1–200 records.")
    records = [Record.model_validate(v) for v in values]
    if len({r.id for r in records}) != len(records):
        raise ValueError("Duplicate record identifiers.")
    return records


def csv_export(rows):
    if not rows:
        return b""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        # Prevent spreadsheet formulas when opening user-supplied text in Excel.
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
                         for k, v in row.items()})
    return buffer.getvalue().encode("utf-8-sig")


def export_bundle(store: Store, synthetic: bool):
    records = store.records(synthetic)
    ids = {r.id for r in records}
    return {"schema_version": "1.0", "workspace": "synthetic" if synthetic else "real",
            "limitations": "User-recorded classifications; human review is not independent verification. Hashes detect byte changes, not truth.",
            "records": [dict(r.model_dump(mode="json"), review_status=store.review_status(r)) for r in records],
            "history": [e for e in store.history() if e["record_id"] in ids]}
