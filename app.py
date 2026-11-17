"""Run with: python -m streamlit run app.py"""
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from ai import generate_advisory
from tracker import (Advisory, Record, Store, canonical, csv_export, export_bundle,
                     fingerprint, import_records, official_host)

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="COP31 Outcomes Tracker", page_icon="🌍", layout="wide")
store = Store(os.getenv("TRACKER_DB_PATH", str(ROOT / "local_data/tracker.sqlite3")))
for record in import_records((ROOT / "data/synthetic_records.json").read_bytes()):
    # Seed once. Do not overwrite edited demonstration records on reruns.
    try:
        store.get(record.id)
    except ValueError:
        store.save(record)

st.title("COP31 Final Outcomes & Commitments Tracker V1.0")
st.caption("COP31 AI Solutions Lab | Day 12 — November 20, 2026 | Independent educational project")
st.info("Prepared on November 17, 2026. Scheduled events are not outcomes. No final COP31 outcomes are preloaded.")
workspace = st.sidebar.radio("Workspace", ["Synthetic demonstration", "Real evidence workspace"])
synthetic = workspace == "Synthetic demonstration"
st.sidebar.warning("FICTITIOUS records — no actual COP31 decisions." if synthetic else "User-entered evidence. URLs and claims require independent checking.")
module = st.sidebar.radio("Module", ["1. Final Outcomes Overview", "2. Commitments & Evidence Tracker",
                                     "3. AI & Human Review", "4. Export & Methodology"])
records = store.records(synthetic)


def table_rows():
    return [{"ID": r.id, "Title": r.title, "Stage (recorded)": r.stage,
             "Implementation": r.implementation, "Human review": store.review_status(r),
             "Synthetic": r.synthetic} for r in records]


if module.startswith("1."):
    st.header("Final Outcomes Overview")
    if records:
        cols = st.columns(4)
        cols[0].metric("Records", len(records))
        cols[1].metric("Recorded as adopted", sum(r.stage == "Adopted" for r in records))
        cols[2].metric("Implementation material supplied", sum(r.implementation == "Evidence supplied" for r in records))
        cols[3].metric("Accepted human reviews", sum(store.review_status(r) == "Accepted" for r in records))
        st.dataframe(pd.DataFrame(table_rows()), hide_index=True, width="stretch")
        st.bar_chart(pd.Series([r.stage for r in records]).value_counts(), color="#27d9be")
    else:
        st.info("No real evidence records yet. Add a source-supported record in Module 2.")
    st.caption("Counts describe recorded labels. Neither source validity nor real-world delivery is automatically verified.")
    st.subheader("Official context — checked November 17, 2026")
    context = json.loads((ROOT / "data/official_context.json").read_text(encoding="utf-8"))
    for item in context["items"]:
        with st.expander(item["category"] + " | " + item["title"]):
            st.write(item["summary"])
            st.write("Event date: " + item["event_date"])
            st.markdown(f"[Source]({item['url']})")
            st.caption(item["verification_note"])
    st.warning("Pending: final negotiated texts, formal adoption and subsequent implementation evidence. This snapshot does not assert that no other procedural decisions have occurred.")

elif module.startswith("2."):
    st.header("Commitments & Evidence Tracker")
    choices = ["Create new record"] + [r.id for r in records]
    choice = st.selectbox("Record", choices)
    current = store.get(choice) if choice != choices[0] else None
    values = current.model_dump(mode="json") if current else {
        "id": "", "title": "", "responsible_party": "", "topic": "Climate finance",
        "stage": "Proposed", "implementation": "Not assessed", "source_url": "",
        "source_date": date.today().isoformat(), "accessed_on": date.today().isoformat(),
        "excerpt": "", "document_id": "", "locator": "", "implementation_url": "",
        "implementation_excerpt": "", "notes": ""}
    st.caption("Adopted needs a document identifier and page/paragraph. Implementation material is recorded separately. These checks do not authenticate evidence.")
    with st.form("record_editor_" + choice):
        fields = {}
        for name, label in [("id", "Record ID"), ("title", "Title"), ("responsible_party", "Responsible party"), ("topic", "Topic")]:
            fields[name] = st.text_input(label, values[name], disabled=bool(current and name == "id"))
        stages = ["Proposed", "Announced", "Adopted"]
        fields["stage"] = st.selectbox("Recorded stage", stages, index=stages.index(values["stage"]))
        statuses = ["Not assessed", "No evidence supplied", "Evidence supplied"]
        fields["implementation"] = st.selectbox("Implementation evidence", statuses, index=statuses.index(values["implementation"]))
        fields["source_url"] = st.text_input("Source URL (HTTPS)", values["source_url"])
        fields["source_date"] = st.date_input("Source date", date.fromisoformat(values["source_date"]))
        fields["accessed_on"] = st.date_input("Accessed on", date.fromisoformat(values["accessed_on"]))
        fields["excerpt"] = st.text_area("Relevant excerpt (source text, not AI output)", values["excerpt"])
        fields["document_id"] = st.text_input("Document identifier", values["document_id"])
        fields["locator"] = st.text_input("Page / paragraph / section", values["locator"])
        fields["implementation_url"] = st.text_input("Implementation evidence URL", values["implementation_url"])
        fields["implementation_excerpt"] = st.text_area("Implementation evidence excerpt", values["implementation_excerpt"])
        fields["notes"] = st.text_area("Limitations / notes", values["notes"])
        if st.form_submit_button("Save record"):
            try:
                candidate = Record(**fields, synthetic=synthetic)
                if current is None:
                    try:
                        store.get(candidate.id)
                    except ValueError:
                        pass
                    else:
                        raise ValueError("ID already exists. Select the existing record to edit it.")
                store.save(candidate)
                st.success("Record saved. Changed evidence needs a new human review.")
            except (ValueError, ValidationError) as exc:
                st.error(str(exc))
    st.subheader("Import JSON records")
    st.caption("Use the array format in data/synthetic_records.json. Imports add new IDs only; edit existing records above.")
    upload = st.file_uploader("JSON array, maximum 2 MB", type="json")
    if upload and st.button("Validate and import"):
        try:
            imported = import_records(upload.getvalue())
            if any(r.synthetic != synthetic for r in imported):
                raise ValueError("Imported records must match the selected workspace.")
            existing_ids = {r.id for r in store.records(True) + store.records(False)}
            if any(r.id in existing_ids for r in imported):
                raise ValueError("An imported ID already exists. No records were imported.")
            # Validation of the entire batch happens before the first write.
            for record in imported:
                store.save(record)
            st.success(f"Imported {len(imported)} records.")
        except (ValueError, ValidationError) as exc:
            st.error(str(exc))

elif module.startswith("3."):
    st.header("AI & Human Review")
    if not records:
        st.info("Add a record in Module 2 first.")
    else:
        selected = st.selectbox("Record to review", [r.id for r in records])
        record = store.get(selected)
        payload = record.model_dump(mode="json")
        digest = fingerprint(payload)
        st.json(payload)
        st.caption("Official host label: " + str(official_host(record.source_url)) + ". Host matching does not verify the document or claim.")
        st.write("Current record review: " + store.review_status(record))
        with st.form("human_review_" + digest):
            reviewer = st.text_input("Reviewer role or pseudonym", key="record_reviewer")
            decision = st.selectbox("Evidence review decision", ["Needs more evidence", "Accepted", "Rejected"])
            rationale = st.text_area("Evidence review rationale")
            checked = st.checkbox("I checked the source, excerpt, dates and recorded classifications.")
            if st.form_submit_button("Save evidence review"):
                try:
                    if not checked:
                        raise ValueError("Confirm source checking before recording a review.")
                    store.review_record(record.id, digest, reviewer, decision, rationale)
                    st.success("Evidence review recorded for this version.")
                except ValueError as exc:
                    st.error(str(exc))
        st.subheader("Optional AI advisory")
        st.warning("UNVERIFIED AI ADVISORY — HUMAN REVIEW REQUIRED")
        consent = st.checkbox("Send this selected record and its excerpts to Google's Gemini API.")
        if st.button("Generate advisory", disabled=not consent):
            try:
                with st.spinner("Generating advisory…"):
                    advisory = generate_advisory(record)
                st.session_state["advisory"] = {"record_digest": digest, "payload": advisory.model_dump()}
            except Exception:
                st.error("Advisory unavailable. Check the local API key, model availability and network. No record was changed.")
        saved = st.session_state.get("advisory")
        if saved and saved["record_digest"] == digest:
            advisory = Advisory.model_validate(saved["payload"])
            st.json(advisory.model_dump())
            with st.form("advisory_review_" + digest):
                ar = st.text_input("AI reviewer role or pseudonym")
                ad = st.selectbox("AI review decision", ["Needs more evidence", "Accepted", "Rejected"])
                an = st.text_area("AI review rationale")
                if st.form_submit_button("Save AI review"):
                    try:
                        store.review_advisory(record, advisory, ar, ad, an)
                        st.success("AI review saved. Evidence classification was not changed.")
                    except ValueError as exc:
                        st.error(str(exc))
        elif saved:
            st.info("The earlier advisory belongs to another record or version. Generate a new advisory to review this one.")
        with st.expander("Record history"):
            st.json(store.history(record.id))

else:
    st.header("Export & Methodology")
    bundle = export_bundle(store, synthetic)
    raw = canonical(bundle)
    st.download_button("Download JSON with history", raw, "tracker_export.json", "application/json")
    st.download_button("Download CSV", csv_export(bundle["records"]), "tracker_records.csv", "text/csv")
    st.code(fingerprint(bundle), language="text")
    st.caption("SHA-256 of the exact canonical JSON download. CSV has its own byte representation. Hashes do not establish authenticity or truth.")
    st.markdown((ROOT / "METHODOLOGY.md").read_text(encoding="utf-8"))

st.divider()
st.caption("Evidence first. Engineering second. Measurable impact as the goal.")
