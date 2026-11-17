# Methodology and limits

- **Proposed:** a proposal or draft recorded by a user. It may never be adopted.
- **Announced:** an attributable public announcement recorded by a user. It does not establish delivery.
- **Adopted:** a recorded formal decision. A document identifier and precise locator are required. Their presence does not prove authenticity.
- **Implementation evidence:** a separate dimension. A link and excerpt can be supplied independently of proposal, announcement or adoption. Supplied material is not automatically verified execution or measured impact.
- **Human review:** Accepted, Rejected or Needs more evidence applies to a specific content fingerprint. A changed record needs another review. The latest decision on the same fingerprint is displayed. Returning to exactly the same content reuses that content's review history. Reviewing AI text does not accept the evidence record.
- **Two workspaces:** demonstration records and real user-entered evidence remain separate in displays and exports. Demonstration records are fictitious, including their document identifiers and reserved example.org URLs. The real workspace starts empty.
- **Official context:** a dated reference snapshot, separate from commitment records. Verified facts as of November 17, scheduled November 20 activities, and pending final outcomes have different labels. A published schedule does not establish that a session happened or produced a result.
- **Evidence collection:** enter short source excerpts, document identifiers, locators, source/access dates and limitations manually. JSON imports are validated before writing. The app does not crawl URLs, download PDFs, authenticate source documents or resolve URL redirects.
- **AI:** Gemini is optional and sees only the selected record after explicit user action. It has no browsing tool. Structured validation checks output shape, not factual correctness or grounding. External source text can contain prompt injection; human checking remains necessary. No autonomous status changes occur.
- **Audit:** SQLite records versions and review events with UTC timestamps. The app exposes no event editing UI. The database is local and can be edited externally: this is not a tamper-proof or cryptographically signed ledger.
- **Exports:** JSON contains records and their complete local history for the selected workspace. SHA-256 fingerprints the exact canonical UTF-8 JSON download, without volatile export timestamps. CSV text starting with spreadsheet formula characters is prefixed with an apostrophe. A hash detects byte changes; it cannot certify source truth.
- **Privacy and scope:** use public evidence and reviewer roles or pseudonyms. Do not enter secrets or personal data. The app is intended for one local user, with no login or multiuser deployment controls. No financial disbursements, emissions reductions or operational impact are validated.

Independent educational project; no affiliation with or endorsement by COP31, UNFCCC or Google.
