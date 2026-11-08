"""
AI Decision Engine tests.

Runs the full pipeline (GridFS upload → Nemotron Parse fallback on embedded PDF
text → identity extraction → consistency checks → decision) in-memory against
the demo scenarios, plus focused unit tests for normalisers and checks.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

import src.database.mongodb as mongo_module
from src.main import app
from src.scripts.demo_scenarios import build_scenarios, seed_scenario
from src.services.application_decision_service import STAGES, ApplicationDecisionService
from src.services.decision_engine.consistency_checker import ApplicationConsistencyChecker, DocumentEvidence
from src.services.decision_engine.identity_extractor import RuleBasedIdentityExtractor, reconcile_extractions
from src.services.decision_engine.normalizers import (
    address_similarity,
    name_similarity,
    normalize_phone,
)

SCENARIOS = {s["key"]: s for s in build_scenarios()}


@pytest.fixture(scope="module")
def seeded() -> dict[str, str]:
    """Seed every scenario once, in submission order, and return key → vendor_id."""
    db = mongo_module.db
    ids: dict[str, str] = {}
    for s in build_scenarios():
        ids[s["key"]] = seed_scenario(db, s)
    return ids


def _run(vendor_id: str) -> dict:
    svc = ApplicationDecisionService(mongo_module.db)
    return asyncio.run(svc.run_now(vendor_id, trigger="test"))


def _codes(run: dict) -> set[str]:
    return {f["code"] for f in run["findings"]}


# ---------------------------------------------------------------------------
# End-to-end scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", list(SCENARIOS))
def test_scenario_outcome(seeded, key):
    run = _run(seeded[key])
    assert run["status"] == "completed", run.get("error")
    decision = run["decision"]
    assert decision["outcome"] == SCENARIOS[key]["mock_expected"], (
        key, decision["headline"], [(f["severity"], f["code"], f["detail"]) for f in decision["reasons"]]
    )
    # Every stage executed and was recorded.
    assert [s["key"] for s in run["stages"]] == [k for k, _ in STAGES]
    assert all(s["status"] not in ("pending", "running") for s in run["stages"])
    # Non-approvals always explain themselves and tell the vendor what to do (except pure-fraud wording).
    if decision["outcome"] != "approve":
        assert decision["reasons"]
        assert decision["vendor_message"]


def test_happy_path_cross_references_every_attribute(seeded):
    run = _run(seeded["happy_path"])
    matrix = {r["attribute"]: r for r in run["evidence_matrix"]}
    for attr in ("company_name", "pan_number", "gstin", "cin", "mobile", "address", "account_number", "ifsc_code", "account_holder_name"):
        assert matrix[attr]["status"] == "verified", (attr, matrix[attr])
    assert run["decision"]["counts"]["critical"] == 0 and run["decision"]["counts"]["major"] == 0
    # Account numbers are masked in stored output.
    assert "50200012345678" not in str(run["evidence_matrix"])


def test_pan_mismatch_is_critical(seeded):
    codes = _codes(_run(seeded["pan_card_mismatch"]))
    assert "PAN_NUMBER_MISMATCH" in codes
    assert "DOCUMENTS_PAN_CONFLICT" in codes


def test_third_party_bank_flags_holder(seeded):
    run = _run(seeded["third_party_bank"])
    assert "BANK_HOLDER_NAME_MISMATCH" in _codes(run)
    assert "BANK_PROOF_HOLDER_MISMATCH" not in _codes(run)  # cheque agrees with what was declared


def test_personal_pan_for_company(seeded):
    assert "PAN_ENTITY_TYPE_MISMATCH" in _codes(_run(seeded["personal_pan"]))


def test_duplicate_bank_only_blocks_later_applicant(seeded):
    later = _run(seeded["duplicate_bank"])
    assert "DUPLICATE_BANK_ACCOUNT" in _codes(later)
    original = _run(seeded["happy_path"])
    assert "DUPLICATE_BANK_ACCOUNT" not in _codes(original)
    assert original["decision"]["outcome"] == "approve"


def test_moved_office_flags_address_and_mobile(seeded):
    codes = _codes(_run(seeded["moved_office"]))
    assert {"ADDRESS_PINCODE_MISMATCH", "MOBILE_MISMATCH"} <= codes


def test_incomplete_flags_missing_and_unreadable(seeded):
    codes = _codes(_run(seeded["incomplete"]))
    assert {"MISSING_DOC_GST_CERTIFICATE", "DOC_UNREADABLE"} <= codes


def test_vendor_mirror_and_history(seeded):
    vid = seeded["happy_path"]
    _run(vid)
    vendor = mongo_module.db["vendors"].find_one({"reference_number": "VND-DEMO-0001"})
    assert vendor["ai_decision"]["outcome"] == "approve"
    runs = ApplicationDecisionService(mongo_module.db).list_runs(vid)
    assert len(runs) >= 1 and runs[0]["decision"]["outcome"] == "approve"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_api_run_and_send_to_vendor(seeded):
    client = TestClient(app)
    vid = seeded["moved_office"]
    res = client.post(f"/api/admin/applications/{vid}/ai-decision/run", params={"wait": True})
    assert res.status_code == 202, res.text
    body = res.json()
    assert body["decision"]["outcome"] == "review"

    latest = client.get(f"/api/admin/applications/{vid}/ai-decision").json()["run"]
    assert latest["id"] == body["id"]
    assert client.get(f"/api/admin/ai-decision/runs/{body['id']}").status_code == 200
    assert client.get("/api/admin/ai-decision/runs").json()["items"]

    sent = client.post(f"/api/admin/applications/{vid}/ai-decision/send-to-vendor", json={})
    assert sent.status_code == 200, sent.text
    assert "MIDC" in sent.json()["clarification_message"] or "address" in sent.json()["clarification_message"].lower()
    vendor = client.get(f"/api/admin/applications/{vid}").json()["vendor"]
    assert vendor["status"] == "clarification_required"


def test_api_background_run_creates_queued_run(seeded):
    client = TestClient(app)
    res = client.post(f"/api/admin/applications/{seeded['personal_pan']}/ai-decision/run")
    assert res.status_code == 202
    run_id = res.json()["id"]
    # TestClient executes background tasks before returning.
    run = client.get(f"/api/admin/ai-decision/runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["decision"]["outcome"] == "review"


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_name_normalisation():
    assert name_similarity("Acme Technologies Pvt. Ltd.", "ACME TECHNOLOGIES PRIVATE LIMITED") >= 0.95
    assert name_similarity("M/s Acme Technologies Private Limited", "Acme Technologies Pvt Ltd") >= 0.95
    assert name_similarity("Acme Technologies Pvt Ltd", "Brightwave Solutions Pvt Ltd") < 0.5


def test_phone_and_address_normalisation():
    assert normalize_phone("+91 98450-12345") == "9845012345"
    assert normalize_phone("098450 12345") == "9845012345"
    assert address_similarity("12, M.G. Road, Indiranagar, Bangalore", "12 MG Road Indiranagar Bengaluru") > 0.8


def test_rule_extractor_reads_markdown_tables():
    text = (
        "| Field | Value |\n|---|---|\n| **Legal Name** | Acme Technologies Pvt Ltd |\n"
        "| GSTIN | 29AAACA1234F1Z5 |\n| Mobile | +91 98450 12345 |\n"
        "| Address of Principal Place of Business | 12 MG Road, Bengaluru 560038 |"
    )
    f = RuleBasedIdentityExtractor.extract(text, "gst_certificate")
    assert f["gstin"] == "29AAACA1234F1Z5"
    assert f["pan_number"] == "AAACA1234F" and f["pan_printed"] is False
    assert f["entity_name"] == "Acme Technologies Pvt Ltd"
    assert f["mobile_numbers"] == ["9845012345"]
    assert f["pincode"] == "560038"
    assert f["state"] == "Karnataka"


def test_llm_output_cannot_override_printed_identifiers():
    text = "PAN: AAACA1234F\nName: Acme Technologies Private Limited"
    rules = RuleBasedIdentityExtractor.extract(text, "pan_card")
    llm = {"pan_number": "ZZZZZ9999Z", "entity_name": "Acme Technologies Private Limited", "mobile_numbers": ["9000000000"]}
    merged, method = reconcile_extractions(rules, llm, text)
    assert merged["pan_number"] == "AAACA1234F"  # printed value wins
    assert merged["mobile_numbers"] == []  # hallucinated number not present in text is dropped
    assert method == "nemotron+rules"


def test_gstin_pan_mismatch_in_form_is_critical():
    vendor = SCENARIOS["happy_path"]["form"] | {}
    vendor = {**vendor, "tax_details": {**vendor["tax_details"], "gstin": "29AABCB5678K1Z2"}}
    checker = ApplicationConsistencyChecker(vendor, [])
    findings = checker.run_stage("form_integrity")
    assert any(f.code == "GSTIN_PAN_MISMATCH" and f.severity == "critical" for f in findings)


def test_one_character_pan_typo_is_review_not_reject():
    vendor = SCENARIOS["happy_path"]["form"]
    doc = DocumentEvidence("d1", "pan_card", "pan.pdf", {"pan_number": "AAACA1234E", "entity_name": vendor["company_info"]["legal_company_name"], "pan_printed": True})
    checker = ApplicationConsistencyChecker(vendor, [doc])
    findings = checker.run_stage("cross_document")
    pan = [f for f in findings if f.code == "PAN_NUMBER_MISMATCH"]
    assert pan and pan[0].severity == "major"


# ---------------------------------------------------------------------------
# Vendor-portal test-case pre-fill
# ---------------------------------------------------------------------------

def test_prefill_scenario_creates_fresh_draft_and_is_repeatable():
    client = TestClient(app)
    cases = client.get("/api/demo/scenarios").json()
    assert {c["key"] for c in cases} == set(SCENARIOS)
    assert next(c for c in cases if c["key"] == "duplicate_bank")["requires_first"]

    first = client.post("/api/demo/scenarios/moved_office/prefill")
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["form"]["tax_details"]["pan_number"] == "AAICO6655R"
    assert len(body["documents"]) == 4

    # Selecting the same case again replaces the earlier copy instead of tripping the duplicate-PAN guard.
    second = client.post("/api/demo/scenarios/moved_office/prefill").json()
    assert second["removed_previous"] >= 1
    assert client.get(f"/api/vendors/{body['vendor_id']}").status_code == 404

    # The draft submits and the engine reaches the expected decision.
    vid = second["vendor_id"]
    assert client.post(f"/api/vendors/{vid}/submit").status_code == 200
    run = client.get(f"/api/admin/applications/{vid}/ai-decision").json()["run"]
    assert run["decision"]["outcome"] == "review"
