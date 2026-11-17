# COP31 Final Outcomes & Commitments Tracker V1.0

**COP31 AI Solutions Lab | Day 12 — November 20, 2026**  
Prepared and checked on **November 17, 2026**. English interface and documentation.

An independent educational Python application for distinguishing recorded proposals, announcements, adopted decisions and separately supplied implementation material. It combines explicit evidence fields, optional Gemini explanations and version-specific human reviews.

**No final COP31 outcomes are preloaded.** Four demonstration records are entirely fictitious. Their example.org URLs and document identifiers are placeholders, not actual conference evidence. The real evidence workspace starts empty.

## Four modules

1. **Final Outcomes Overview:** recorded stages, implementation material and human review counts. A separate official-context snapshot distinguishes facts checked on November 17, scheduled November 20 activities and pending outcomes.
2. **Commitments & Evidence Tracker:** add/edit records; validated JSON import; sources, dates, excerpts, document identifiers and page/paragraph locators. Adoption and implementation are separate fields, not an automatic progression.
3. **AI & Human Review:** manual evidence review and optional structured Gemini advisory. Reviews bind to a SHA-256 fingerprint of the complete record. Changed content needs another review. Reviewing AI does not accept an evidence record.
4. **Export & Methodology:** CSV, canonical JSON with local history, SHA-256 and methodological limits. Synthetic and real exports remain separate.

## Windows / PyCharm setup

Use Python **3.11 or 3.12**. From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

If PowerShell prevents activation, call `.venv\Scripts\python.exe` directly in place of `python`.
Open the local URL displayed by Streamlit. If port 8501 is occupied, add `--server.port 8502`.
No GPU is required. The core tracker works offline after dependencies have been installed.

## Optional Gemini

```powershell
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in your local `.env`; never commit the file. The default model is `gemini-2.5-flash`; change `GEMINI_MODEL` if your account requires another available model.

Only clicking **Generate advisory** after selecting the consent checkbox transmits the selected record to Google's API. No remote URL retrieval is implemented. API access requires internet, model access and potentially paid quota. Provider errors are shown without echoing credentials. AI output is schema-validated, not fact-verified, and cannot change record classifications.

## Validation

See [VALIDATION.md](VALIDATION.md). Local validation: **26 tests passed** on Python 3.12, including two Streamlit AppTest flows. Tests cover record constraints, independent implementation evidence, review invalidation, host matching, data isolation, history, JSON import, stable hashes, CSV formula protection and mocked AI responses. Tests do not call the live Gemini API.

The repository includes a GitHub Actions workflow for Python 3.11 and 3.12; its remote execution status must be checked in the Actions tab. A configured workflow alone does not mean CI has passed.

## Data and audit

- Default store: `local_data/tracker.sqlite3`, excluded from Git. Override with `TRACKER_DB_PATH` for local testing.
- Input examples: `data/synthetic_records.json` (a JSON array). The exported JSON envelope is a report, not an import file; extract original record fields before reimporting.
- Records use source and access dates; future or reversed dates are rejected.
- Missing evidence is explicit. A supplied implementation excerpt is not independently verified delivery.
- SQLite preserves record snapshots and review events. It is not tamper-proof; someone with file access can alter it.
- To reset local data, stop the app and delete `local_data/tracker.sqlite3`. Restarting reseeds demonstration records only.
- One local user is assumed. There is no authentication or shared deployment control.

## Official context snapshot

`data/official_context.json` is a dated set of source summaries, separate from commitment records. It covers the conference dates and venue, the published November 17–18 high-level segment notice, the planned November 20 closing plenaries and the Presidency's scheduled Final Negotiations / Connect To Funds programme. Summaries are paraphrases. The planning note is preliminary; direct Presidency page requests timed out, so the schedule was checked against indexed official pages. Recheck live schedules before using them on November 20.

No assumption is made that every item on the agenda will yield an adopted decision. Final texts, formal adoption and subsequent implementation must be documented separately once supporting evidence is available.

## Limits

Read [METHODOLOGY.md](METHODOLOGY.md). Labels are user-entered claims, not legal certification. An official-domain URL is only a host label. A human acceptance is a recorded review, not independent authentication. A hash detects byte changes, not truth. No disbursement, emissions reduction or real-world impact is verified.

Not affiliated with or endorsed by COP31, UNFCCC or Google. No license is granted beyond applicable law; a reuse license has not yet been selected.

**Evidence first. Engineering second. Measurable impact as the goal.**
