"""Streamlit's headless AppTest checks navigation and the actual form flows."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def launch(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACKER_DB_PATH", str(tmp_path / "ui.sqlite3"))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    return app


def test_all_modules_and_empty_real_workspace(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    for module in app.sidebar.radio[1].options:
        app.sidebar.radio[1].set_value(module).run()
        assert not app.exception
    app.sidebar.radio[0].set_value("Real evidence workspace").run()
    assert not app.exception
    app.sidebar.radio[1].set_value("1. Final Outcomes Overview").run()
    assert any("No real evidence" in x.value for x in app.info)


def test_edit_record_then_review_real_form(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    app.sidebar.radio[1].set_value("2. Commitments & Evidence Tracker").run()
    app.selectbox[0].set_value("DEMO-1").run()
    next(x for x in app.text_area if x.label == "Limitations / notes").set_value("UI regression test: revised evidence note.")
    next(b for b in app.button if b.label == "Save record").click().run()
    assert not app.exception and any("Record saved" in s.value for s in app.success)
    app.sidebar.radio[1].set_value("3. AI & Human Review").run()
    next(x for x in app.text_input if x.label == "Reviewer role or pseudonym").set_value("Test reviewer")
    next(x for x in app.selectbox if x.label == "Evidence review decision").set_value("Accepted")
    next(x for x in app.text_area if x.label == "Evidence review rationale").set_value("Checked the current synthetic source and dates.")
    app.checkbox[0].check()
    next(b for b in app.button if b.label == "Save evidence review").click().run()
    assert not app.exception and any("Evidence review recorded" in s.value for s in app.success)
