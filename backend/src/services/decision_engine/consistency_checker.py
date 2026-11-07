"""
Consistency checks for a vendor application.

Produces two artefacts:

* ``findings`` — a flat list of explainable check results, each with a
  severity (critical / major / warning / info / pass), the values compared,
  the source document, and a vendor-facing action when something is needed.
* ``evidence_matrix`` — one row per identity attribute (company name, PAN,
  GSTIN, CIN, mobile, address, bank account, IFSC, account holder) showing the
  form value next to the value found in every document, so a reviewer can see
  the cross-reference at a glance.

Check families
--------------
1. Completeness        — mandatory documents / fields for the declared entity.
2. Document quality    — unreadable files, or a file that doesn't carry the
                         identifier its category implies (wrong document).
3. Form integrity      — the form contradicting itself: GSTIN's embedded PAN
                         vs PAN, PAN 4th char vs entity type, CIN vs entity
                         type / incorporation year, GSTIN state vs address,
                         bank account holder vs legal name.
4. Cross-document      — every document vs the form *and* documents vs each
                         other, for name, PAN, GSTIN, CIN, mobile, address,
                         bank account, IFSC.
5. Duplicate screening — bank account / GSTIN / mobile already used by a
                         different vendor.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.services.decision_engine.identity_extractor import CIN_RE, IFSC_RE, LLPIN_RE, PAN_RE, GSTIN_RE
from src.services.decision_engine.normalizers import (
    address_similarity,
    core_name,
    edit_distance,
    extract_pincode,
    format_address,
    is_valid_indian_mobile,
    legal_form_of,
    mask_account,
    name_similarity,
    normalize_address,
    normalize_id,
    normalize_phone,
    normalize_state,
    state_from_gstin,
)

SEVERITY_ORDER = {"critical": 4, "major": 3, "warning": 2, "info": 1, "pass": 0}

CATEGORY_LABELS: dict[str, str] = {
    "pan_card": "PAN Card",
    "gst_certificate": "GST Certificate",
    "certificate_of_incorporation": "Certificate of Incorporation",
    "bank_proof": "Bank Proof",
    "tan_certificate": "TAN Certificate",
    "msme_certificate": "MSME / Udyam Certificate",
    "other": "Supporting Document",
}

CORPORATE_TYPES = {
    "Private Limited Company": "PTC",
    "Public Limited Company": "PLC",
    "One Person Company (OPC)": "OPC",
}

# PAN 4th character → holder type
PAN_HOLDER_TYPES = {
    "C": "Company", "P": "Individual / Proprietor", "H": "Hindu Undivided Family",
    "F": "Firm / LLP", "A": "Association of Persons", "T": "Trust",
    "B": "Body of Individuals", "L": "Local Authority", "J": "Artificial Juridical Person",
    "G": "Government",
}

EXPECTED_PAN_TYPE: dict[str, set[str]] = {
    "Private Limited Company": {"C"},
    "Public Limited Company": {"C"},
    "One Person Company (OPC)": {"C"},
    "Limited Liability Partnership (LLP)": {"F"},
    "Partnership": {"F"},
    "Sole Proprietorship": {"P"},
}


@dataclass
class Finding:
    code: str
    category: str
    field: str
    severity: str
    title: str
    detail: str
    form_value: str | None = None
    document_value: str | None = None
    document_id: str | None = None
    document_name: str | None = None
    vendor_action: str | None = None
    source: str = "rules"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentEvidence:
    document_id: str
    category: str
    file_name: str
    fields: dict[str, Any]
    readable: bool = True
    extraction_method: str = "rules"
    error: str | None = None

    @property
    def label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.replace("_", " ").title())


@dataclass
class MatrixCell:
    document_id: str
    document_label: str
    value: str | None
    status: str  # match | minor | mismatch | not_found
    note: str = ""


@dataclass
class MatrixRow:
    attribute: str
    label: str
    form_value: str | None
    cells: list[MatrixCell] = field(default_factory=list)
    status: str = "unverified"  # verified | minor | conflict | unverified | missing | not_applicable

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribute": self.attribute,
            "label": self.label,
            "form_value": self.form_value,
            "status": self.status,
            "cells": [asdict(c) for c in self.cells],
        }


def _s(value: Any) -> str:
    return str(value).strip() if value is not None else ""


class ApplicationConsistencyChecker:
    """Runs every deterministic check for one application."""

    def __init__(
        self,
        vendor: dict[str, Any],
        documents: list[DocumentEvidence],
        other_vendors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.vendor = vendor
        self.documents = documents
        self.other_vendors = other_vendors or []
        self.findings: list[Finding] = []
        self.matrix: dict[str, MatrixRow] = {}

        ci = vendor.get("company_info") or {}
        ct = vendor.get("contact_info") or {}
        tx = vendor.get("tax_details") or {}
        bk = vendor.get("banking_details") or {}

        self.legal_name = _s(ci.get("legal_company_name") or ci.get("legal_name"))
        self.trade_name = _s(ci.get("trade_name"))
        self.entity_type = _s(ci.get("business_entity_type"))
        self.cin = normalize_id(ci.get("registration_number"))
        self.incorporation_date = _s(ci.get("incorporation_date"))
        self.reg_address = ci.get("registered_address") or {}
        self.op_address = None if ci.get("is_operational_same_as_registered", True) else (ci.get("operational_address") or None)

        self.pan = normalize_id(tx.get("pan_number"))
        self.gstin = normalize_id(tx.get("gstin"))
        self.gst_status = _s(tx.get("gst_status")) or "Registered"
        self.gst_state = _s(tx.get("gst_state"))
        self.tan = normalize_id(tx.get("tan_number"))

        self.account_holder = _s(bk.get("account_holder_name"))
        self.account_number = normalize_id(bk.get("account_number"))
        self.ifsc = normalize_id(bk.get("ifsc_code"))

        primary = ct.get("primary") or {}
        secondary = ct.get("secondary") or {}
        signatory = ct.get("signatory") or {}
        self.person_names = [
            n for n in (
                f"{_s(primary.get('first_name'))} {_s(primary.get('last_name'))}".strip(),
                _s(signatory.get("full_name")) or f"{_s(signatory.get('first_name'))} {_s(signatory.get('last_name'))}".strip(),
                _s(secondary.get("full_name")) or f"{_s(secondary.get('first_name'))} {_s(secondary.get('last_name'))}".strip(),
            ) if n
        ]
        self.primary_phone = normalize_phone(primary.get("phone"))
        self.form_phones = [p for p in {self.primary_phone, normalize_phone(secondary.get("phone")), normalize_phone(signatory.get("phone"))} if p]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        self._check_completeness()
        self._check_document_quality()
        self._check_form_integrity()
        self._check_cross_document()
        self._check_duplicates()
        findings = sorted(self.findings, key=lambda f: -SEVERITY_ORDER.get(f.severity, 0))
        return [f.to_dict() for f in findings], [r.to_dict() for r in self.matrix.values()]

    def run_stage(self, stage: str) -> list[Finding]:
        """Run a single check family (used by the orchestrator for stage-level logging)."""
        before = len(self.findings)
        {
            "completeness": self._check_completeness,
            "document_quality": self._check_document_quality,
            "form_integrity": self._check_form_integrity,
            "cross_document": self._check_cross_document,
            "duplicates": self._check_duplicates,
        }[stage]()
        return self.findings[before:]

    def results(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        findings = sorted(self.findings, key=lambda f: -SEVERITY_ORDER.get(f.severity, 0))
        return [f.to_dict() for f in findings], [r.to_dict() for r in self.matrix.values()]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add(self, **kwargs: Any) -> Finding:
        f = Finding(**kwargs)
        self.findings.append(f)
        return f

    def _docs(self, *categories: str) -> list[DocumentEvidence]:
        if not categories:
            return [d for d in self.documents if d.readable]
        return [d for d in self.documents if d.category in categories and d.readable]

    def _row(self, attribute: str, label: str, form_value: str | None) -> MatrixRow:
        if attribute not in self.matrix:
            self.matrix[attribute] = MatrixRow(attribute=attribute, label=label, form_value=form_value or None)
        return self.matrix[attribute]

    @staticmethod
    def _finalise_row(row: MatrixRow) -> None:
        statuses = [c.status for c in row.cells if c.status != "not_found"]
        if not row.form_value and not statuses:
            row.status = "not_applicable"
        elif not row.form_value:
            row.status = "missing"
        elif "mismatch" in statuses:
            row.status = "conflict"
        elif "minor" in statuses:
            row.status = "minor"
        elif "match" in statuses:
            row.status = "verified"
        else:
            row.status = "unverified"

    @property
    def _is_corporate(self) -> bool:
        return self.entity_type in CORPORATE_TYPES or self.entity_type == "Limited Liability Partnership (LLP)"

    @property
    def _is_proprietorship(self) -> bool:
        return self.entity_type == "Sole Proprietorship"

    # ------------------------------------------------------------------
    # 1. Completeness
    # ------------------------------------------------------------------

    def _check_completeness(self) -> None:
        uploaded = {d.category for d in self.documents}
        required: list[tuple[str, str]] = [
            ("pan_card", "PAN verification is mandatory for every vendor."),
            ("bank_proof", "A cancelled cheque or bank statement is required to confirm ownership of the payout account."),
        ]
        if self.gst_status.lower() == "registered":
            required.append(("gst_certificate", "GST status is declared as 'Registered', so the GST registration certificate (REG-06) is required."))
        if self._is_corporate:
            required.append(("certificate_of_incorporation", f"Entity type '{self.entity_type}' requires the Certificate of Incorporation."))

        for cat, reason in required:
            if cat not in uploaded:
                label = CATEGORY_LABELS[cat]
                self._add(
                    code=f"MISSING_DOC_{cat.upper()}",
                    category="completeness",
                    field=cat,
                    severity="major",
                    title=f"{label} not uploaded",
                    detail=reason,
                    vendor_action=f"Upload your {label}.",
                )

        if self.tan and "tan_certificate" not in uploaded:
            self._add(
                code="MISSING_DOC_TAN_CERTIFICATE", category="completeness", field="tan_certificate",
                severity="warning", title="TAN certificate not uploaded",
                detail="A TAN was entered on the form but no TAN certificate was provided to substantiate it.",
                form_value=self.tan,
            )

        required_fields = [
            (self.legal_name, "company_info.legal_company_name", "Legal company name"),
            (self.pan, "tax_details.pan_number", "PAN"),
            (self.account_number, "banking_details.account_number", "Bank account number"),
            (self.ifsc, "banking_details.ifsc_code", "IFSC code"),
            (self.primary_phone, "contact_info.primary.phone", "Primary contact mobile number"),
        ]
        if self.gst_status.lower() == "registered":
            required_fields.append((self.gstin, "tax_details.gstin", "GSTIN"))
        if self._is_corporate:
            required_fields.append((self.cin, "company_info.registration_number", "CIN / LLPIN"))
        for value, path, label in required_fields:
            if not value:
                self._add(
                    code="MISSING_FIELD", category="completeness", field=path, severity="major",
                    title=f"{label} missing from the form",
                    detail=f"{label} is required but was left empty.",
                    vendor_action=f"Provide your {label} in the application form.",
                )

    # ------------------------------------------------------------------
    # 2. Document quality
    # ------------------------------------------------------------------

    def _check_document_quality(self) -> None:
        key_identifier = {
            "pan_card": ("pan_number", "a PAN"),
            "gst_certificate": ("gstin", "a GSTIN"),
            "certificate_of_incorporation": ("cin", "a CIN / LLPIN"),
            "bank_proof": ("account_number", "a bank account number"),
            "tan_certificate": ("tan_number", "a TAN"),
            "msme_certificate": ("udyam_number", "a Udyam registration number"),
        }
        for d in self.documents:
            if not d.readable:
                self._add(
                    code="DOC_UNREADABLE", category="document_quality", field=d.category, severity="major",
                    title=f"{d.label} could not be read",
                    detail=f"Text extraction failed for '{d.file_name}'"
                    + (f": {d.error}" if d.error else ". The file may be blurred, password-protected or a blank scan."),
                    document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"Re-upload a clear, complete copy of your {d.label} (PDF or high-resolution image).",
                )
                continue
            if d.category not in key_identifier:
                continue
            key, desc = key_identifier[d.category]
            value = d.fields.get(key)
            if d.category == "pan_card" and value and d.fields.get("pan_printed") is False:
                value = None  # PAN only derivable from a GSTIN → not a PAN card
            if not value:
                self._add(
                    code="DOC_KEY_IDENTIFIER_NOT_FOUND", category="document_quality", field=d.category,
                    severity="major",
                    title=f"No {desc[2:] if desc.startswith('a ') else desc} found on the {d.label}",
                    detail=f"'{d.file_name}' was uploaded as {d.label} but {desc} could not be located on it. "
                    "It may be the wrong document, an incomplete page, or a poor-quality scan.",
                    document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"Check that the file uploaded as {d.label} is the correct document and re-upload it.",
                )

    # ------------------------------------------------------------------
    # 3. Form integrity (the form contradicting itself)
    # ------------------------------------------------------------------

    def _check_form_integrity(self) -> None:
        # PAN format + holder type vs entity type
        if self.pan:
            if not PAN_RE.fullmatch(self.pan):
                self._add(
                    code="PAN_FORMAT_INVALID", category="tax", field="pan_number", severity="major",
                    title="PAN format is invalid", form_value=self.pan,
                    detail="A PAN must be 5 letters, 4 digits and 1 letter (e.g. AAACA1234F).",
                    vendor_action="Correct the PAN entered in the form.",
                )
            else:
                holder = self.pan[3]
                expected = EXPECTED_PAN_TYPE.get(self.entity_type)
                if expected and holder not in expected:
                    self._add(
                        code="PAN_ENTITY_TYPE_MISMATCH", category="tax", field="pan_number", severity="major",
                        title="PAN holder type does not match the declared entity type",
                        detail=f"The 4th character of PAN {self.pan} is '{holder}' "
                        f"({PAN_HOLDER_TYPES.get(holder, 'unknown')}), but the business is declared as "
                        f"'{self.entity_type}', which requires a PAN with '{'/'.join(sorted(expected))}'. "
                        "This usually means a personal PAN was supplied for a company, or vice-versa.",
                        form_value=self.pan,
                        vendor_action=f"Provide the PAN issued to the {self.entity_type.lower()} itself (not a director's or proprietor's personal PAN).",
                    )
                elif holder != "P" and self.legal_name:
                    initial = (core_name(self.legal_name) or self.legal_name.lower())[:1].upper()
                    if initial and initial.isalpha() and self.pan[4] != initial:
                        self._add(
                            code="PAN_NAME_INITIAL_MISMATCH", category="tax", field="pan_number", severity="warning",
                            title="PAN 5th character does not match the company name",
                            detail=f"For non-individual PANs the 5th character is normally the first letter of the entity's name. "
                            f"PAN {self.pan} has '{self.pan[4]}' but '{self.legal_name}' starts with '{initial}'.",
                            form_value=self.pan,
                        )

        # GSTIN ↔ PAN, GSTIN state ↔ address
        if self.gstin:
            if not GSTIN_RE.fullmatch(self.gstin):
                self._add(
                    code="GSTIN_FORMAT_INVALID", category="tax", field="gstin", severity="major",
                    title="GSTIN format is invalid", form_value=self.gstin,
                    detail="A GSTIN is 15 characters: 2-digit state code + PAN + entity number + 'Z' + check character.",
                    vendor_action="Correct the GSTIN entered in the form.",
                )
            else:
                embedded = self.gstin[2:12]
                if self.pan and embedded != self.pan:
                    self._add(
                        code="GSTIN_PAN_MISMATCH", category="tax", field="gstin", severity="critical",
                        title="GSTIN belongs to a different PAN",
                        detail=f"Every GSTIN embeds the holder's PAN. GSTIN {self.gstin} embeds {embedded}, "
                        f"but the PAN on the form is {self.pan}. The GST registration does not belong to this entity.",
                        form_value=self.pan, document_value=embedded,
                        vendor_action="The GSTIN and PAN you entered belong to different entities. Provide the GSTIN registered against your own PAN.",
                    )
                gst_state = state_from_gstin(self.gstin)
                declared_states = {normalize_state(self.gst_state), normalize_state(self.reg_address.get("state"))}
                if self.op_address:
                    declared_states.add(normalize_state(self.op_address.get("state")))
                declared_states.discard("")
                if gst_state and declared_states and normalize_state(gst_state) not in declared_states:
                    self._add(
                        code="GSTIN_STATE_MISMATCH", category="address", field="gstin", severity="major",
                        title="GST state code does not match the business address",
                        detail=f"GSTIN {self.gstin} is registered in {gst_state} (state code {self.gstin[:2]}), "
                        f"but the declared address / GST state is {', '.join(sorted(s.title() for s in declared_states))}.",
                        form_value=self.reg_address.get("state") or self.gst_state, document_value=gst_state,
                        vendor_action="Confirm which state your GST registration is in, or provide the GSTIN for the state of your registered address.",
                    )

        # CIN ↔ entity type / incorporation year
        if self.cin and self._is_corporate:
            if self.entity_type == "Limited Liability Partnership (LLP)":
                if CIN_RE.fullmatch(self.cin):
                    self._add(
                        code="CIN_ENTITY_TYPE_MISMATCH", category="identity", field="registration_number", severity="major",
                        title="Company CIN supplied for an LLP",
                        detail=f"{self.cin} is a company CIN, but the entity is declared as an LLP (which has an LLPIN like AAA-1234).",
                        form_value=self.cin,
                        vendor_action="Confirm your entity type and provide the matching registration number (LLPIN for an LLP).",
                    )
            elif CIN_RE.fullmatch(self.cin):
                expected_code = CORPORATE_TYPES.get(self.entity_type)
                actual_code = self.cin[12:15]
                if expected_code and actual_code != expected_code and not (expected_code == "PTC" and actual_code == "FTC"):
                    self._add(
                        code="CIN_ENTITY_TYPE_MISMATCH", category="identity", field="registration_number", severity="major",
                        title="CIN company class does not match the declared entity type",
                        detail=f"CIN {self.cin} carries class code '{actual_code}', but '{self.entity_type}' should carry '{expected_code}'.",
                        form_value=self.cin,
                        vendor_action="Confirm your entity type and CIN.",
                    )
                year = self.cin[8:12]
                if self.incorporation_date and year.isdigit() and year not in self.incorporation_date:
                    self._add(
                        code="CIN_YEAR_MISMATCH", category="identity", field="incorporation_date", severity="major",
                        title="Incorporation year conflicts with the CIN",
                        detail=f"CIN {self.cin} encodes incorporation year {year}, but the form states {self.incorporation_date}.",
                        form_value=self.incorporation_date, document_value=year,
                        vendor_action="Check the date of incorporation and CIN entered in the form.",
                    )
            else:
                self._add(
                    code="CIN_FORMAT_INVALID", category="identity", field="registration_number", severity="major",
                    title="CIN format is invalid", form_value=self.cin,
                    detail="A CIN is 21 characters, e.g. U72200KA2018PTC123456.",
                    vendor_action="Correct the CIN entered in the form.",
                )

        # Bank account holder vs legal name (form-internal)
        if self.account_holder and self.legal_name:
            sim = max(name_similarity(self.account_holder, self.legal_name), name_similarity(self.account_holder, self.trade_name))
            person_sim = max((name_similarity(self.account_holder, p) for p in self.person_names), default=0.0)
            if sim >= 0.88:
                pass
            elif self._is_proprietorship and person_sim >= 0.85:
                self._add(
                    code="BANK_HOLDER_IS_PROPRIETOR", category="banking", field="account_holder_name", severity="info",
                    title="Bank account held in the proprietor's name",
                    detail=f"Account holder '{self.account_holder}' matches the proprietor/contact name — acceptable for a sole proprietorship.",
                    form_value=self.account_holder,
                )
            else:
                sev = "warning" if sim >= 0.75 else "major"
                self._add(
                    code="BANK_HOLDER_NAME_MISMATCH", category="banking", field="account_holder_name", severity=sev,
                    title="Bank account holder differs from the legal company name",
                    detail=f"Payouts would go to an account held by '{self.account_holder}', while the vendor's legal name is "
                    f"'{self.legal_name}' (similarity {sim:.0%}). A third-party payout account is a common payment-diversion pattern.",
                    form_value=self.legal_name, document_value=self.account_holder,
                    vendor_action="Provide a bank account held in the vendor's legal name, or explain the relationship with the account holder.",
                )

        # Contact + bank format
        if self.primary_phone and not is_valid_indian_mobile(self.primary_phone):
            self._add(
                code="MOBILE_FORMAT_INVALID", category="contact", field="contact_info.primary.phone", severity="major",
                title="Primary mobile number is not a valid Indian mobile",
                detail=f"'{self.primary_phone}' should be a 10-digit number starting with 6-9.",
                form_value=self.primary_phone,
                vendor_action="Provide a valid 10-digit mobile number for the primary contact.",
            )
        if self.ifsc and not IFSC_RE.fullmatch(self.ifsc):
            self._add(
                code="IFSC_FORMAT_INVALID", category="banking", field="ifsc_code", severity="major",
                title="IFSC format is invalid", form_value=self.ifsc,
                detail="An IFSC is 11 characters: 4-letter bank code, '0', then 6 branch characters.",
                vendor_action="Correct the IFSC code.",
            )

    # ------------------------------------------------------------------
    # 4. Cross-document consistency
    # ------------------------------------------------------------------

    def _check_cross_document(self) -> None:
        self._compare_names()
        self._compare_identifier("pan_number", "PAN", self.pan, ("pan_card", "gst_certificate", "tan_certificate", "certificate_of_incorporation", "msme_certificate", "other"), critical=True)
        self._compare_identifier("gstin", "GSTIN", self.gstin, ("gst_certificate", "other", "msme_certificate"), critical=True)
        self._compare_identifier("cin", "CIN / LLPIN", self.cin, ("certificate_of_incorporation", "other"), critical=False)
        self._compare_identifier("account_number", "Bank account number", self.account_number, ("bank_proof",), critical=True, masked=True)
        self._compare_ifsc()
        self._compare_account_holder()
        self._compare_mobiles()
        self._compare_addresses()
        self._compare_documents_with_each_other()
        for row in self.matrix.values():
            self._finalise_row(row)

    def _compare_names(self) -> None:
        row = self._row("company_name", "Company / entity name", self.legal_name)
        for d in self._docs():
            if d.category == "bank_proof":
                continue  # handled by account-holder comparison
            doc_name = d.fields.get("entity_name")
            if not doc_name:
                row.cells.append(MatrixCell(d.document_id, d.label, None, "not_found"))
                continue
            if not self.legal_name:
                row.cells.append(MatrixCell(d.document_id, d.label, doc_name, "not_found", "no form value"))
                continue

            sim = max(name_similarity(doc_name, self.legal_name), name_similarity(doc_name, self.trade_name) - 0.05)
            # Proprietorship / individual PAN cards carry the person's name.
            person_sim = max((name_similarity(doc_name, p) for p in self.person_names), default=0.0)
            if (self._is_proprietorship or d.category == "pan_card" and self.pan[3:4] == "P") and person_sim > sim:
                sim = person_sim

            form_lf, doc_lf = legal_form_of(self.legal_name), legal_form_of(doc_name)
            legal_form_conflict = (
                core_name(doc_name) == core_name(self.legal_name)
                and form_lf and doc_lf and form_lf != doc_lf
                and {form_lf, doc_lf} != {"private_limited", "limited"}
            )

            if legal_form_conflict:
                row.cells.append(MatrixCell(d.document_id, d.label, doc_name, "mismatch", "legal form differs"))
                self._add(
                    code="NAME_LEGAL_FORM_MISMATCH", category="identity", field="company_name", severity="major",
                    title=f"Legal form on {d.label} differs from the form",
                    detail=f"'{doc_name}' on the {d.label} vs '{self.legal_name}' on the form — same business name but a different legal form "
                    "(e.g. LLP vs Private Limited). These are legally different entities.",
                    form_value=self.legal_name, document_value=doc_name, document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"Confirm the exact registered name and entity type; the {d.label} shows '{doc_name}'.",
                )
            elif sim >= 0.9:
                row.cells.append(MatrixCell(d.document_id, d.label, doc_name, "match", f"{sim:.0%}"))
            elif sim >= 0.75:
                row.cells.append(MatrixCell(d.document_id, d.label, doc_name, "minor", f"{sim:.0%}"))
                self._add(
                    code="NAME_MINOR_VARIATION", category="identity", field="company_name", severity="warning",
                    title=f"Company name on {d.label} differs slightly",
                    detail=f"'{doc_name}' vs form '{self.legal_name}' ({sim:.0%} similar) — likely a spelling or abbreviation variant.",
                    form_value=self.legal_name, document_value=doc_name, document_id=d.document_id, document_name=d.file_name,
                )
            else:
                sev = "major" if sim >= 0.5 else "critical"
                row.cells.append(MatrixCell(d.document_id, d.label, doc_name, "mismatch", f"{sim:.0%}"))
                self._add(
                    code="NAME_MISMATCH", category="identity", field="company_name", severity=sev,
                    title=f"Company name on {d.label} does not match the application",
                    detail=f"The {d.label} is issued to '{doc_name}', but the application is for '{self.legal_name}' "
                    f"({sim:.0%} similar)." + (" The document appears to belong to a different entity." if sev == "critical" else ""),
                    form_value=self.legal_name, document_value=doc_name, document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"The {d.label} you uploaded is in the name of '{doc_name}'. Upload the {d.label} issued to '{self.legal_name}', or correct the company name in the form.",
                )

    def _compare_identifier(
        self,
        key: str,
        label: str,
        form_value: str,
        categories: tuple[str, ...],
        critical: bool,
        masked: bool = False,
    ) -> None:
        show = (lambda v: mask_account(v)) if masked else (lambda v: v)
        row = self._row(key, label, show(form_value) if form_value else None)
        for d in self._docs(*categories):
            doc_val = normalize_id(d.fields.get(key))
            if key == "pan_number" and d.category != "pan_card" and not d.fields.get("pan_printed", True):
                note = "derived from GSTIN"
            else:
                note = ""
            if not doc_val:
                if d.category in categories[:1]:
                    row.cells.append(MatrixCell(d.document_id, d.label, None, "not_found"))
                continue
            if not form_value:
                row.cells.append(MatrixCell(d.document_id, d.label, show(doc_val), "not_found", "no form value"))
                continue
            if doc_val == form_value:
                row.cells.append(MatrixCell(d.document_id, d.label, show(doc_val), "match", note))
                continue

            dist = edit_distance(doc_val, form_value)
            row.cells.append(MatrixCell(d.document_id, d.label, show(doc_val), "mismatch", note or f"{dist} char(s) differ"))
            if note == "derived from GSTIN":
                continue  # the GSTIN comparison already explains this conflict
            if key == "gstin" and doc_val[2:12] == form_value[2:12]:
                sev, extra = "major", " Both GSTINs belong to the same PAN, so this may be a registration in another state."
            elif dist <= 1 and len(form_value) >= 9:
                sev, extra = "major", " Only one character differs, so this is probably a typing error — but it must be corrected before payments are set up."
            else:
                sev, extra = ("critical" if critical else "major"), ""
            self._add(
                code=f"{key.upper()}_MISMATCH", category="banking" if key == "account_number" else "tax" if key in ("pan_number", "gstin") else "identity",
                field=key, severity=sev,
                title=f"{label} on {d.label} does not match the form",
                detail=f"The {d.label} shows {label} {show(doc_val)}, but the form has {show(form_value)}.{extra}",
                form_value=show(form_value), document_value=show(doc_val), document_id=d.document_id, document_name=d.file_name,
                vendor_action=f"The {label} on your {d.label} ({show(doc_val)}) does not match the {label} in your application ({show(form_value)}). Correct the form or upload the right document.",
            )

    def _compare_ifsc(self) -> None:
        row = self._row("ifsc_code", "IFSC code", self.ifsc or None)
        for d in self._docs("bank_proof"):
            doc_val = normalize_id(d.fields.get("ifsc_code"))
            if not doc_val:
                row.cells.append(MatrixCell(d.document_id, d.label, None, "not_found"))
                continue
            if not self.ifsc or doc_val == self.ifsc:
                row.cells.append(MatrixCell(d.document_id, d.label, doc_val, "match" if self.ifsc else "not_found"))
                continue
            same_bank = doc_val[:4] == self.ifsc[:4]
            row.cells.append(MatrixCell(d.document_id, d.label, doc_val, "mismatch", "same bank, other branch" if same_bank else "different bank"))
            self._add(
                code="IFSC_MISMATCH", category="banking", field="ifsc_code", severity="major",
                title="IFSC on bank proof does not match the form",
                detail=f"Bank proof shows IFSC {doc_val}, form has {self.ifsc}"
                + (" (same bank, different branch)." if same_bank else " (a different bank)."),
                form_value=self.ifsc, document_value=doc_val, document_id=d.document_id, document_name=d.file_name,
                vendor_action=f"Your bank proof shows IFSC {doc_val} but the form has {self.ifsc}. Correct the IFSC or upload proof for the right account.",
            )

    def _compare_account_holder(self) -> None:
        row = self._row("account_holder_name", "Bank account holder", self.account_holder or None)
        for d in self._docs("bank_proof"):
            holder = d.fields.get("account_holder_name") or d.fields.get("entity_name")
            if not holder:
                row.cells.append(MatrixCell(d.document_id, d.label, None, "not_found"))
                continue
            # Cell: does the bank proof agree with the holder declared on the form?
            declared = self.account_holder or self.legal_name
            sim_declared = name_similarity(holder, declared)
            # Severity: does the bank proof belong to the vendor at all?
            sim_vendor = max(
                [name_similarity(holder, self.legal_name), name_similarity(holder, self.trade_name)]
                + ([name_similarity(holder, p) for p in self.person_names] if self._is_proprietorship else [])
            )
            if sim_declared >= 0.88:
                row.cells.append(MatrixCell(d.document_id, d.label, holder, "match", f"{sim_declared:.0%}"))
                continue  # any holder ≠ legal-name issue is reported by the form-integrity check
            if sim_declared >= 0.75:
                row.cells.append(MatrixCell(d.document_id, d.label, holder, "minor", f"{sim_declared:.0%}"))
                continue
            row.cells.append(MatrixCell(d.document_id, d.label, holder, "mismatch", f"{sim_declared:.0%}"))
            hidden = sim_vendor < 0.5
            self._add(
                code="BANK_PROOF_HOLDER_MISMATCH", category="banking", field="account_holder_name",
                severity="critical" if hidden else "major",
                title="Bank proof is in a different name",
                detail=f"The bank proof is for an account held by '{holder}', but the form declares the holder as '{declared}'"
                + (f" and the vendor is '{self.legal_name}'. The payout account does not appear to belong to the vendor — a payment-diversion risk."
                   if hidden else f" ({sim_declared:.0%} similar)."),
                form_value=declared, document_value=holder, document_id=d.document_id, document_name=d.file_name,
                vendor_action=f"The bank proof is in the name of '{holder}'. Upload a cancelled cheque or statement for the account held by '{self.legal_name or declared}'.",
            )

    def _compare_mobiles(self) -> None:
        row = self._row("mobile", "Mobile number", ", ".join(self.form_phones) or None)
        any_doc_phone = False
        for d in self._docs():
            nums = d.fields.get("mobile_numbers") or []
            if not nums:
                continue
            any_doc_phone = True
            shown = ", ".join(nums)
            if not self.form_phones:
                row.cells.append(MatrixCell(d.document_id, d.label, shown, "not_found", "no form value"))
            elif set(nums) & set(self.form_phones):
                row.cells.append(MatrixCell(d.document_id, d.label, shown, "match"))
            else:
                row.cells.append(MatrixCell(d.document_id, d.label, shown, "mismatch"))
                self._add(
                    code="MOBILE_MISMATCH", category="contact", field="mobile", severity="major",
                    title=f"Mobile number on {d.label} does not match the form",
                    detail=f"The {d.label} lists {shown}, none of which match the contact number(s) on the form "
                    f"({', '.join(self.form_phones)}). The registered contact for this entity may belong to someone else.",
                    form_value=", ".join(self.form_phones), document_value=shown,
                    document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"The mobile number registered on your {d.label} ({shown}) differs from the one in your application. Confirm the correct contact number or explain the difference.",
                )
        if not any_doc_phone and self.form_phones:
            self._add(
                code="MOBILE_UNVERIFIED", category="contact", field="mobile", severity="info",
                title="Mobile number could not be cross-checked",
                detail="None of the uploaded documents print a mobile number, so the contact number is verified only for format.",
                form_value=", ".join(self.form_phones),
            )

    def _compare_addresses(self) -> None:
        reg_line = format_address(self.reg_address)
        op_line = format_address(self.op_address) if self.op_address else ""
        row = self._row("address", "Registered address", reg_line or None)
        form_pins = {p for p in (_s(self.reg_address.get("pincode")).replace(" ", ""), _s((self.op_address or {}).get("pincode")).replace(" ", "")) if p}
        form_cities = {normalize_address(c) for c in (self.reg_address.get("city"), (self.op_address or {}).get("city")) if c}

        for d in self._docs():
            addr = d.fields.get("address")
            if not addr:
                if d.category in ("gst_certificate", "certificate_of_incorporation"):
                    row.cells.append(MatrixCell(d.document_id, d.label, None, "not_found"))
                continue
            if not reg_line:
                row.cells.append(MatrixCell(d.document_id, d.label, addr, "not_found", "no form value"))
                continue
            doc_pin = extract_pincode(addr)
            sim = max(address_similarity(addr, reg_line), address_similarity(addr, op_line) if op_line else 0.0)
            norm_doc = normalize_address(addr)
            city_hit = any(c and c in norm_doc for c in form_cities)

            if doc_pin and form_pins and doc_pin not in form_pins:
                row.cells.append(MatrixCell(d.document_id, d.label, addr, "mismatch", f"PIN {doc_pin}"))
                self._add(
                    code="ADDRESS_PINCODE_MISMATCH", category="address", field="address", severity="major",
                    title=f"Address on {d.label} is in a different PIN code",
                    detail=f"The {d.label} address '{addr}' has PIN {doc_pin}, but the form's address PIN is {', '.join(sorted(form_pins))}.",
                    form_value=reg_line, document_value=addr, document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"The address on your {d.label} (PIN {doc_pin}) differs from the address in your application. Update the address or upload a document showing the current address.",
                )
            elif (doc_pin and doc_pin in form_pins and (sim >= 0.45 or city_hit)) or sim >= 0.7:
                row.cells.append(MatrixCell(d.document_id, d.label, addr, "match", f"{sim:.0%}"))
            elif (doc_pin and doc_pin in form_pins) or city_hit or sim >= 0.5:
                row.cells.append(MatrixCell(d.document_id, d.label, addr, "minor", f"{sim:.0%}"))
                self._add(
                    code="ADDRESS_MINOR_VARIATION", category="address", field="address", severity="warning",
                    title=f"Address on {d.label} differs in detail",
                    detail=f"'{addr}' vs form '{reg_line}' — same locality but the street details differ ({sim:.0%} similar).",
                    form_value=reg_line, document_value=addr, document_id=d.document_id, document_name=d.file_name,
                )
            else:
                row.cells.append(MatrixCell(d.document_id, d.label, addr, "mismatch", f"{sim:.0%}"))
                self._add(
                    code="ADDRESS_MISMATCH", category="address", field="address", severity="major",
                    title=f"Address on {d.label} does not match the form",
                    detail=f"The {d.label} shows '{addr}', which does not correspond to the form's address '{reg_line}'.",
                    form_value=reg_line, document_value=addr, document_id=d.document_id, document_name=d.file_name,
                    vendor_action=f"The address on your {d.label} does not match your application. Update the address or upload a document showing the current address.",
                )

    def _compare_documents_with_each_other(self) -> None:
        """Documents must also agree with each other — independent of the form."""
        pans: dict[str, list[DocumentEvidence]] = {}
        for d in self._docs():
            p = normalize_id(d.fields.get("pan_number"))
            if p and PAN_RE.fullmatch(p):
                pans.setdefault(p, []).append(d)
        if len(pans) > 1:
            desc = "; ".join(f"{', '.join(x.label for x in ds)}: {p}" for p, ds in pans.items())
            self._add(
                code="DOCUMENTS_PAN_CONFLICT", category="fraud", field="pan_number", severity="critical",
                title="Uploaded documents carry different PANs",
                detail=f"The documents do not agree on the entity's PAN ({desc}). Documents from more than one legal entity have been combined in this application.",
                vendor_action="The documents you uploaded belong to different PAN holders. Upload documents that all belong to the applying entity.",
            )

        named = [(d, d.fields.get("entity_name")) for d in self._docs() if d.category != "bank_proof" and d.fields.get("entity_name")]
        for i in range(len(named)):
            for j in range(i + 1, len(named)):
                (d1, n1), (d2, n2) = named[i], named[j]
                if self.pan[3:4] == "P" and "pan_card" in (d1.category, d2.category):
                    continue  # personal PAN vs business name — legitimately different
                sim = name_similarity(n1, n2)
                if sim < 0.6:
                    self._add(
                        code="DOCUMENTS_NAME_CONFLICT", category="identity", field="company_name", severity="major",
                        title=f"{d1.label} and {d2.label} name different entities",
                        detail=f"'{n1}' ({d1.label}) vs '{n2}' ({d2.label}) — {sim:.0%} similar.",
                        vendor_action=f"Your {d1.label} and {d2.label} are issued to different names. Upload documents issued to the same legal entity.",
                    )

    # ------------------------------------------------------------------
    # 5. Duplicate screening against other vendors
    # ------------------------------------------------------------------

    def _other_has_precedence(self, other: dict[str, Any]) -> bool:
        """The other vendor 'owns' a shared identifier if approved or submitted first."""
        if other.get("status") == "approved":
            return True
        mine, theirs = self.vendor.get("submitted_at"), other.get("submitted_at")
        if not theirs:
            return False
        if not mine:
            return True
        strip = lambda d: d.replace(tzinfo=None) if hasattr(d, "replace") and getattr(d, "tzinfo", None) else d  # noqa: E731
        try:
            return strip(theirs) <= strip(mine)
        except TypeError:
            return True

    def _check_duplicates(self) -> None:
        for other in self.other_vendors:
            o_tax = other.get("tax_details") or {}
            o_bank = other.get("banking_details") or {}
            o_ct = other.get("contact_info") or {}
            o_pan = normalize_id(o_tax.get("pan_number"))
            o_name = (other.get("company_info") or {}).get("legal_company_name") or "another vendor"
            o_ref = other.get("reference_number") or str(other.get("_id", ""))
            o_status = other.get("status", "")
            same_entity = bool(o_pan and o_pan == self.pan)
            precedence = self._other_has_precedence(other)

            if self.account_number and normalize_id(o_bank.get("account_number")) == self.account_number and not same_entity:
                if precedence:
                    self._add(
                        code="DUPLICATE_BANK_ACCOUNT", category="fraud", field="account_number", severity="critical",
                        title="Bank account already registered to another vendor",
                        detail=f"Account {mask_account(self.account_number)} is also the payout account of '{o_name}' ({o_ref}, status: {o_status}), "
                        "which has a different PAN. One account receiving payments for two unrelated vendors is a classic shell-vendor pattern.",
                        form_value=mask_account(self.account_number),
                        vendor_action="The bank account provided is already registered to a different business. Provide a bank account held by your entity.",
                    )
                else:
                    self._add(
                        code="BANK_ACCOUNT_REUSED_BY_LATER_APPLICATION", category="fraud", field="account_number", severity="warning",
                        title="A newer application reuses this bank account",
                        detail=f"'{o_name}' ({o_ref}), submitted after this application and with a different PAN, lists the same payout account. "
                        "That application is the one flagged; this vendor's ownership is supported by its own bank proof.",
                        form_value=mask_account(self.account_number),
                    )
            if self.gstin and normalize_id(o_tax.get("gstin")) == self.gstin and not same_entity and precedence:
                self._add(
                    code="DUPLICATE_GSTIN", category="fraud", field="gstin", severity="critical",
                    title="GSTIN already registered to another vendor",
                    detail=f"GSTIN {self.gstin} is already used by '{o_name}' ({o_ref}).",
                    form_value=self.gstin,
                    vendor_action="The GSTIN provided is already registered to a different vendor. Provide your own GSTIN.",
                )
            if self.pan and same_entity:
                self._add(
                    code="DUPLICATE_PAN", category="fraud", field="pan_number", severity="major",
                    title="Another application exists for this PAN",
                    detail=f"PAN {self.pan} is also on application {o_ref} ('{o_name}', status: {o_status}). This may be a duplicate onboarding.",
                    form_value=self.pan,
                )
            o_phones = {normalize_phone(p.get("phone")) for p in (o_ct.get("primary") or {}, o_ct.get("secondary") or {}) if isinstance(p, dict)}
            o_phones.discard("")
            shared = set(self.form_phones) & o_phones
            if shared and not same_entity:
                self._add(
                    code="DUPLICATE_MOBILE", category="fraud", field="mobile", severity="major",
                    title="Contact mobile shared with another vendor",
                    detail=f"Mobile {', '.join(sorted(shared))} is also the contact number of '{o_name}' ({o_ref}), a different legal entity.",
                    form_value=", ".join(sorted(shared)),
                    vendor_action="Your contact mobile number is registered to another vendor. Provide a contact number belonging to your organisation.",
                )
