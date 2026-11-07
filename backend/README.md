# VendorFlow API

FastAPI backend for vendor onboarding (ZAMP case study, PS-2).

```bash
uv sync                                   # or: pip install -e .
uvicorn src.main:app --reload             # http://localhost:8000/docs
python -m pytest                          # in-memory (mongomock), no NVIDIA calls
```

## AI Decision Engine

Takes a submitted application (form fields + every uploaded document) and returns
**Approve**, **Needs Review** (pending) or **Reject**, with the reasons and a drafted
message telling the vendor what to fix.

### Pipeline (each stage is recorded live in `ai_decision_runs`)

| # | Stage | What it does |
|---|-------|--------------|
| 1 | Intake | Loads the form and document list |
| 2 | Completeness | Mandatory documents/fields for the entity type (PAN, bank proof, GST cert if registered, CoI if corporate) |
| 3 | Document parsing | NVIDIA **Nemotron Parse** text extraction per page (cached between runs) |
| 4 | Identity extraction | Canonical fields per document: name, PAN, GSTIN, CIN, mobiles, emails, address/PIN, account holder, account no., IFSC. Nemotron reasoning + deterministic regex. Printed identifiers win over LLM guesses, and LLM values that don't appear in the text are dropped. |
| 5 | Form integrity | The form contradicting itself: GSTIN's embedded PAN ≠ PAN, PAN 4th char vs entity type (personal PAN for a company), CIN class/year vs entity type/incorporation date, GST state code vs address, bank holder vs legal name |
| 6 | Cross-document | Form vs every document **and** document vs document for company name (fuzzy, legal-suffix aware), PAN, GSTIN, CIN, mobile, address (PIN code + similarity), account no., IFSC, account holder |
| 7 | Duplicate screening | Bank account / GSTIN / mobile already used by a *different* vendor (only the later applicant is blocked) |
| 8 | AI reviewer | Nemotron reads the evidence pack and may raise extra concerns. **Escalate-only:** it can move approve → review, but can't clear a rule finding or reject on its own. |
| 9 | Decision | any critical → **reject** · any major → **review** · else **approve** (and name, PAN and bank account must each be backed by a document) |

A one-character difference in a PAN/GSTIN/account number is treated as a likely typo (review);
larger differences are critical (reject). Account numbers are masked in all stored output.

### Triggers

* Automatically on vendor **submit** and **resubmit** (background task)
* Manually from the admin portal → application → **AI Decision** tab

### API

```
POST /api/admin/applications/{id}/ai-decision/run?wait=false&force_reparse=false
GET  /api/admin/applications/{id}/ai-decision            latest run
GET  /api/admin/applications/{id}/ai-decision/runs       history
GET  /api/admin/ai-decision/runs/{run_id}                poll for live stage progress
GET  /api/admin/ai-decision/runs                         recent runs (all applications)
POST /api/admin/applications/{id}/ai-decision/send-to-vendor   send drafted request as a clarification
```

Without `NVIDIA_API_KEY` (or with `NVIDIA_MOCK_MODE=true`) the engine runs on embedded PDF
text + deterministic rules only. The run records which mode was used.

### Demo scenarios

```bash
python -m src.scripts.seed_demo_scenarios --run          # seed VND-DEMO-0001..0007 into MongoDB and run the engine
python -m src.scripts.seed_demo_scenarios --export demo  # write the scenario PDFs + form.json to ./demo
```

| Ref | Scenario | Expected |
|-----|----------|----------|
| 0001 | Clean submission, formatting variants normalised | approve |
| 0002 | PAN card shows a different PAN than the form & GSTIN | reject |
| 0003 | Payout account is the director's personal account | review |
| 0004 | Director's personal ("P") PAN used for a Pvt Ltd company | review |
| 0005 | Bank account already belongs to vendor 0001 | reject |
| 0006 | GST certificate shows another address (PIN) and mobile | review |
| 0007 | GST certificate missing, bank proof an unreadable photo | review |
