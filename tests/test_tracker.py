import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ai import generate_advisory
from tracker import (Advisory, Record, Store, canonical, csv_export, export_bundle,
                     fingerprint, import_records, official_host)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def record():
    return Record(id="TEST-1", title="Fictitious climate proposal", responsible_party="Demo council",
                  topic="Adaptation", stage="Proposed", source_url="https://example.org/demo",
                  source_date=date(2026, 11, 16), accessed_on=date(2026, 11, 17),
                  excerpt="FICTITIOUS: a draft adaptation proposal for a classroom exercise.")


@pytest.fixture
def db(tmp_path):
    return Store(tmp_path / "records.sqlite3")


def test_adopted_requires_specific_reference(record):
    with pytest.raises(ValidationError):
        Record.model_validate({**record.model_dump(), "stage": "Adopted"})


def test_implementation_requires_separate_evidence(record):
    with pytest.raises(ValidationError):
        Record.model_validate({**record.model_dump(), "implementation": "Evidence supplied"})


def test_announced_is_not_implemented(record, db):
    value = Record.model_validate({**record.model_dump(), "stage": "Announced"})
    db.save(value)
    assert db.get(value.id).implementation == "Not assessed"
    assert db.review_status(value) == "Pending"


def test_implementation_can_exist_without_formal_adoption(record):
    value = Record.model_validate({**record.model_dump(), "implementation": "Evidence supplied",
                                  "implementation_url": "https://example.org/progress",
                                  "implementation_excerpt": "FICTITIOUS: initial pilot work was recorded."})
    assert value.stage == "Proposed"


@pytest.mark.parametrize("url", ["http://example.org", "javascript:alert(1)", "https://user:secret@example.org"])
def test_reject_bad_source_urls(record, url):
    with pytest.raises(ValidationError):
        Record.model_validate({**record.model_dump(), "source_url": url})


def test_future_date_rejected(record):
    with pytest.raises(ValidationError):
        Record.model_validate({**record.model_dump(), "source_date": date.today() + timedelta(days=1)})


@pytest.mark.parametrize("url,expected", [("https://unfccc.int/doc", True), ("https://www.unfccc.int/doc", True),
                                         ("https://unfccc.int.evil.org/doc", False), ("https://fakecop31.tr", False)])
def test_official_host_is_exact_domain(url, expected):
    assert official_host(url) == expected


def test_review_invalidated_on_evidence_change(record, db):
    digest = db.save(record)
    db.review_record(record.id, digest, "Reviewer", "Accepted", "Checked the demonstration excerpt.")
    assert db.review_status(record) == "Accepted"
    changed = Record.model_validate({**record.model_dump(), "excerpt": "FICTITIOUS: materially revised draft proposal."})
    db.save(changed)
    assert db.review_status(changed) == "Pending"
    with pytest.raises(ValueError, match="changed"):
        db.review_record(record.id, digest, "Reviewer", "Accepted", "This review is now stale.")
    assert len(db.history(record.id)) == 3


def test_latest_review_wins(record, db):
    digest = db.save(record)
    for decision in ("Accepted", "Rejected"):
        db.review_record(record.id, digest, "Reviewer", decision, "Checked this precise version.")
    assert db.review_status(record) == "Rejected"


def test_idempotent_save_preserves_history(record, db):
    db.save(record)
    db.save(record)
    assert len(db.history(record.id)) == 1


def test_workspace_isolation(record, db):
    db.save(record)
    real = Record.model_validate({**record.model_dump(), "id": "REAL-1", "synthetic": False})
    db.save(real)
    assert [x["id"] for x in export_bundle(db, False)["records"]] == ["REAL-1"]
    assert all(x["record_id"] == "REAL-1" for x in export_bundle(db, False)["history"])
    with pytest.raises(ValueError, match="cross"):
        db.save(Record.model_validate({**record.model_dump(), "synthetic": False}))


def test_import_validation_is_complete(record):
    raw = json.dumps([record.model_dump(mode="json")] * 2).encode()
    with pytest.raises(ValueError, match="Duplicate"):
        import_records(raw)
    with pytest.raises(ValueError):
        import_records(b"{}")


def test_export_hash_is_reproducible(record, db):
    db.save(record)
    first = export_bundle(db, True)
    assert fingerprint(first) == fingerprint(export_bundle(db, True))
    import hashlib
    assert hashlib.sha256(canonical(first)).hexdigest() == fingerprint(first)
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})


def test_csv_formula_safety():
    text = csv_export([{"Title": " =WEBSERVICE(\"example\")"}]).decode("utf-8-sig")
    assert "' =WEBSERVICE" in text


def test_ai_requires_key(record, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generate_advisory(record)


def test_structured_ai_contract_and_independent_review(record, db):
    value = {"summary": "This supplied excerpt describes a draft only.", "evidence_gaps": ["No adopted text."],
             "verification_questions": ["Where is the primary document?"], "limitations": ["No browsing performed."]}
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(value))
    advisory = generate_advisory(record, client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    assert json.loads(calls[0]["contents"])["id"] == record.id
    db.save(record)
    db.review_advisory(record, advisory, "Reviewer", "Accepted", "Checked the advisory against the excerpt.")
    assert db.review_status(record) == "Pending"
    assert db.get(record.id).stage == "Proposed"


def test_invalid_ai_output_is_rejected(record):
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text='{"summary":"false"}')))
    with pytest.raises(ValidationError):
        generate_advisory(record, client=client)


def test_seed_data_is_synthetic():
    records = import_records((ROOT / "data/synthetic_records.json").read_bytes())
    assert len(records) == 4 and all(r.synthetic for r in records)
    assert all("FICTITIOUS" in r.excerpt for r in records)


def test_context_is_not_a_commitment_dataset():
    context = json.loads((ROOT / "data/official_context.json").read_text())
    assert context["checked_on"] == "2026-11-17"
    assert {x["category"] for x in context["items"]} == {"Verified as of November 17", "Scheduled for November 20"}
