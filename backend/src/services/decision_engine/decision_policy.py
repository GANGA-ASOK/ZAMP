"""
Decision policy: findings → approve / review / reject.

The policy is deliberately simple and auditable:

    any CRITICAL finding   → REJECT   (identity / payout conflict that cannot
                                        be explained by a typo: PAN or bank
                                        account belongs to someone else,
                                        documents from different entities,
                                        account shared with another vendor)
    any MAJOR finding      → REVIEW   (pending — something is missing, unreadable
                                        or inconsistent and needs the vendor or
                                        a reviewer to resolve it)
    otherwise              → APPROVE  (all mandatory evidence present and
                                        consistent; warnings are listed but do
                                        not block)

The Nemotron reviewer may *escalate* (approve → review) by raising a major
concern, but it can never clear a rules finding or produce a rejection on its
own — the LLM reads untrusted document text, so it is not allowed to make the
outcome more favourable or to reject without deterministic evidence.
"""

from __future__ import annotations

from typing import Any

from src.services.decision_engine.consistency_checker import SEVERITY_ORDER

OUTCOME_LABELS = {
    "approve": "Approve",
    "review": "Needs Review",
    "reject": "Reject",
}

SEVERITY_WEIGHTS = {"critical": 40, "major": 15, "warning": 4, "info": 0, "pass": 0}

# Attributes whose document-backed verification is required for auto-approval.
CORE_ATTRIBUTES = ("company_name", "pan_number", "account_number")


def decide(
    findings: list[dict[str, Any]],
    evidence_matrix: list[dict[str, Any]],
    vendor_name: str,
) -> dict[str, Any]:
    by_sev: dict[str, list[dict[str, Any]]] = {k: [] for k in SEVERITY_ORDER}
    for f in findings:
        by_sev.setdefault(f.get("severity", "info"), []).append(f)

    critical, major, warning = by_sev["critical"], by_sev["major"], by_sev["warning"]

    # Coverage — how much of the identity was actually corroborated by documents.
    rows = {r["attribute"]: r for r in evidence_matrix}
    checked_rows = [r for r in evidence_matrix if r.get("form_value")]
    verified_rows = [r for r in checked_rows if r.get("status") in ("verified", "minor")]
    coverage = len(verified_rows) / len(checked_rows) if checked_rows else 0.0
    core_unverified = [
        a for a in CORE_ATTRIBUTES
        if rows.get(a) and rows[a].get("form_value") and rows[a].get("status") not in ("verified", "minor")
    ]

    if critical:
        outcome = "reject"
    elif major:
        outcome = "review"
    elif core_unverified:
        outcome = "review"
        labels = ", ".join(rows[a]["label"] for a in core_unverified)
        major.append({
            "code": "CORE_IDENTITY_UNVERIFIED",
            "category": "completeness",
            "field": ",".join(core_unverified),
            "severity": "major",
            "title": "Core identity not corroborated by documents",
            "detail": f"No uploaded document confirmed: {labels}. Auto-approval requires document evidence for name, PAN and bank account.",
            "vendor_action": None,
            "source": "policy",
        })
        findings.append(major[-1])
    else:
        outcome = "approve"

    risk_score = min(100, sum(SEVERITY_WEIGHTS.get(f.get("severity", "info"), 0) for f in findings))

    if outcome == "approve":
        confidence = 0.75 + 0.22 * coverage - 0.03 * len(warning)
    elif outcome == "reject":
        confidence = 0.85 + 0.04 * (len(critical) - 1)
    else:
        confidence = 0.7 + 0.05 * min(len(major), 4)
    confidence = round(max(0.5, min(0.99, confidence)) * 100, 1)

    headline = _headline(outcome, critical, major, warning, coverage)
    reasons = sorted(
        (f for f in findings if f.get("severity") in ("critical", "major", "warning")),
        key=lambda f: -SEVERITY_ORDER.get(f.get("severity", "info"), 0),
    )
    passed = [f for f in findings if f.get("severity") in ("pass", "info")]

    return {
        "outcome": outcome,
        "label": OUTCOME_LABELS[outcome],
        "confidence": confidence,
        "risk_score": risk_score,
        "coverage": round(coverage * 100, 1),
        "headline": headline,
        "reasons": reasons,
        "observations": passed,
        "counts": {k: len(v) for k, v in by_sev.items()},
        "required_actions": _required_actions(findings),
        "vendor_message": _vendor_message(outcome, findings, vendor_name),
    }


def _headline(outcome: str, critical: list, major: list, warning: list, coverage: float) -> str:
    if outcome == "reject":
        top = critical[0]["title"]
        more = f" and {len(critical) - 1} other critical issue(s)" if len(critical) > 1 else ""
        return f"Reject — {top}{more}."
    if outcome == "review":
        top = major[0]["title"]
        more = f" (+{len(major) - 1} more)" if len(major) > 1 else ""
        return f"Needs review — {top}{more}."
    tail = f" {len(warning)} warning(s) noted for the reviewer." if warning else ""
    return f"Approve — company name, PAN, bank account and contact details are consistent across the form and documents ({coverage:.0%} of attributes corroborated).{tail}"


def _required_actions(findings: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    actions: list[str] = []
    for f in sorted(findings, key=lambda x: -SEVERITY_ORDER.get(x.get("severity", "info"), 0)):
        act = f.get("vendor_action")
        if act and f.get("severity") in ("critical", "major") and act not in seen:
            seen.add(act)
            actions.append(act)
    return actions


def _vendor_message(outcome: str, findings: list[dict[str, Any]], vendor_name: str) -> str | None:
    actions = _required_actions(findings)
    if outcome == "approve" or not actions:
        return None
    items = "\n".join(f"{i}. {a}" for i, a in enumerate(actions, 1))
    if outcome == "reject":
        return (
            f"Dear {vendor_name or 'Vendor'},\n\nWe were unable to verify your onboarding application because the "
            f"information provided is inconsistent with the supporting documents:\n\n{items}\n\n"
            "If you believe this is an error, please contact the procurement team with the corrected documents."
        )
    return (
        f"Dear {vendor_name or 'Vendor'},\n\nThank you for your application. Before we can complete verification, "
        f"we need the following from you:\n\n{items}\n\nPlease update your application and resubmit."
    )


def merge_ai_findings(
    rule_findings: list[dict[str, Any]],
    ai_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add LLM concerns, capped at MAJOR severity and de-duplicated against rule findings."""
    flagged_topics = {
        topic
        for f in rule_findings if f.get("severity") in ("critical", "major", "warning")
        for topic in _topics(f"{f.get('field', '')} {f.get('title', '')}")
    }
    merged = list(rule_findings)
    for f in ai_findings:
        sev = f.get("severity", "warning")
        if sev not in ("major", "warning", "info"):
            sev = "major" if sev == "critical" else "warning"
        # Skip concerns about something the rules already flagged (the LLM re-wording a rule finding).
        if _topics(f"{f.get('field', '')} {f.get('title', '')}") & flagged_topics:
            continue
        merged.append({
            "code": "AI_REVIEW_CONCERN",
            "category": "ai_review",
            "field": f.get("field") or "general",
            "severity": sev,
            "title": str(f.get("title") or "AI reviewer concern")[:160],
            "detail": str(f.get("detail") or "")[:800],
            "form_value": None,
            "document_value": None,
            "document_id": None,
            "document_name": f.get("document_name"),
            "vendor_action": f.get("vendor_action") if sev == "major" else None,
            "source": "nemotron",
        })
    return merged


_TOPIC_WORDS = {
    "address": ("address", "pincode", "pin code", "location"),
    "mobile": ("mobile", "phone", "contact number"),
    "pan": ("pan",),
    "gstin": ("gstin", "gst number"),
    "cin": ("cin", "llpin", "registration number"),
    "bank": ("bank", "account", "ifsc", "cheque", "holder"),
    "name": ("name", "entity"),
}


def _topics(text: str) -> set[str]:
    """Coarse subject of a finding, used to spot an AI concern that repeats a rule finding."""
    import re

    words = " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "
    return {t for t, keys in _TOPIC_WORDS.items() if any(f" {k} " in words for k in keys)}
