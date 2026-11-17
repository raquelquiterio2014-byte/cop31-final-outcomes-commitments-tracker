# Validation record — November 17, 2026

## Executed locally

- Python 3.12 isolated environment; dependencies installed from `requirements.txt`.
- `python -m pytest -q`: **26 passed**.
- Two tests use Streamlit AppTest: navigation across all four modules and the empty real workspace; editing a demonstration record and submitting the human evidence review form.
- Core tests check adoption reference requirements, implementation evidence requirements, date and URL constraints, exact official-host matching, fingerprint-bound reviews, history retention, workspace isolation, JSON imports, deterministic JSON hashes and spreadsheet formula protection.
- Mocked AI tests check structured output validation, missing-key behavior and the independence of advisory review from evidence acceptance.

## Limits of these checks

- No live Gemini API call was made. Model availability, account quota and provider behavior remain unverified.
- AppTest runs the application without a browser. It does not establish the appearance on the user's Windows display.
- Tests cannot certify the authenticity or truth of user-supplied sources.
- GitHub Actions status is external to local testing and must be inspected separately after publication.

## Manual checks on the user's computer

1. Open all four modules and switch between Synthetic demonstration and Real evidence workspace.
2. Confirm the real workspace initially contains no commitment records.
3. Edit a demonstration record, review it, then change its excerpt and confirm the current review becomes Pending.
4. Download JSON and CSV; keep synthetic and real data separate.
5. If using Gemini, configure `.env` locally, consent to transmitting one selected record, generate an advisory and review it against the source.
