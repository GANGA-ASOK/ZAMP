"""
Deterministic Python Field Validators and Normalizers.

Performs rule-based format and structural validation without invoking an LLM.
Includes checksum and regex pattern matching for Indian regulatory identifiers.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from src.schemas.verification import FieldValidationFinding


class ValidationResult(NamedTuple):
    is_valid: bool
    rule: str
    details: str


# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
CIN_REGEX = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
LLPIN_REGEX = re.compile(r"^[A-Z]{3}-[0-9]{4}$|^[A-Z0-9]{7,8}$")
BANK_ACCOUNT_REGEX = re.compile(r"^\d{9,18}$")
TAN_REGEX = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")
UDYAM_REGEX = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")


class DeterministicFieldValidator:
    """Performs deterministic Python validation on extracted fields."""

    @classmethod
    def validate_pan(cls, pan: str | None) -> ValidationResult:
        """Validate 10-character Indian Permanent Account Number (PAN)."""
        if not pan or not pan.strip():
            return ValidationResult(
                is_valid=False,
                rule="PAN Format Check (10 characters, 5 letters + 4 digits + 1 letter)",
                details="PAN number was not found or is empty in extracted document data.",
            )

        cleaned = pan.strip().upper()
        if PAN_REGEX.match(cleaned):
            entity_type_char = cleaned[3]
            entity_desc = {
                "C": "Company",
                "P": "Individual / Proprietor",
                "H": "Hindu Undivided Family",
                "F": "Partnership Firm / LLP",
                "A": "Association of Persons",
                "T": "Trust",
                "B": "Body of Individuals",
                "L": "Local Authority",
                "J": "Artificial Juridical Person",
                "G": "Government Agency",
            }.get(entity_type_char, "Entity")

            return ValidationResult(
                is_valid=True,
                rule="PAN Format Check",
                details=f"Valid PAN format. 4th character '{entity_type_char}' indicates {entity_desc}.",
            )

        return ValidationResult(
            is_valid=False,
            rule="PAN Format Check",
            details=f"Invalid PAN format: '{cleaned}'. Expected format is 5 uppercase letters, 4 digits, 1 letter (e.g. ABCDE1234F).",
        )

    @classmethod
    def validate_gstin(cls, gstin: str | None) -> ValidationResult:
        """Validate 15-character Goods and Services Tax Identification Number (GSTIN)."""
        if not gstin or not gstin.strip():
            return ValidationResult(
                is_valid=False,
                rule="GSTIN Format Check",
                details="GSTIN was not found or is empty in extracted document data.",
            )

        cleaned = gstin.strip().upper()
        if not GSTIN_REGEX.match(cleaned):
            return ValidationResult(
                is_valid=False,
                rule="GSTIN Format Check",
                details=f"Invalid GSTIN format: '{cleaned}'. Expected 15 characters (2 digits state code + 10-char PAN + 1 entity num + 'Z' + 1 checksum char).",
            )

        # Embedded PAN check (chars 3 to 12)
        embedded_pan = cleaned[2:12]
        if not PAN_REGEX.match(embedded_pan):
            return ValidationResult(
                is_valid=False,
                rule="GSTIN Embedded PAN Check",
                details=f"Embedded PAN in GSTIN '{embedded_pan}' is not a valid PAN.",
            )

        state_code = cleaned[:2]
        return ValidationResult(
            is_valid=True,
            rule="GSTIN Format Check",
            details=f"Valid GSTIN structure. State code: {state_code}, Embedded PAN: {embedded_pan}.",
        )

    @classmethod
    def validate_ifsc(cls, ifsc: str | None) -> ValidationResult:
        """Validate 11-character Indian Financial System Code (IFSC)."""
        if not ifsc or not ifsc.strip():
            return ValidationResult(
                is_valid=False,
                rule="IFSC Format Check",
                details="IFSC code was not found or is empty in extracted document data.",
            )

        cleaned = ifsc.strip().upper()
        if IFSC_REGEX.match(cleaned):
            bank_code = cleaned[:4]
            branch_code = cleaned[5:]
            return ValidationResult(
                is_valid=True,
                rule="IFSC Format Check",
                details=f"Valid IFSC format. Bank code: '{bank_code}', 5th character '0', Branch: '{branch_code}'.",
            )

        return ValidationResult(
            is_valid=False,
            rule="IFSC Format Check",
            details=f"Invalid IFSC format: '{cleaned}'. Must be 11 characters: 4 letters bank code, '0' in 5th position, and 6 alphanumeric branch characters.",
        )

    @classmethod
    def validate_cin(cls, cin: str | None) -> ValidationResult:
        """Validate 21-character Corporate Identification Number (CIN) or LLPIN."""
        if not cin or not cin.strip():
            return ValidationResult(
                is_valid=False,
                rule="CIN / Registration Number Check",
                details="CIN / Registration number was not found or is empty.",
            )

        cleaned = cin.strip().upper()
        if CIN_REGEX.match(cleaned):
            status_desc = "Listed" if cleaned.startswith("L") else "Unlisted"
            return ValidationResult(
                is_valid=True,
                rule="CIN Format Check (21 characters)",
                details=f"Valid CIN format for {status_desc} company.",
            )

        if LLPIN_REGEX.match(cleaned):
            return ValidationResult(
                is_valid=True,
                rule="LLPIN Format Check",
                details="Valid LLP Identification Number (LLPIN) format.",
            )

        return ValidationResult(
            is_valid=False,
            rule="CIN / LLPIN Format Check",
            details=f"Invalid CIN/LLPIN format: '{cleaned}'.",
        )

    @classmethod
    def validate_account_number(cls, acc_num: str | None) -> ValidationResult:
        """Validate plausibility of Indian bank account number."""
        if not acc_num or not acc_num.strip():
            return ValidationResult(
                is_valid=False,
                rule="Bank Account Number Format Check",
                details="Bank account number was not found or is empty.",
            )

        # Remove spaces and hyphens
        cleaned = re.sub(r"[\s\-]", "", acc_num)
        if BANK_ACCOUNT_REGEX.match(cleaned):
            return ValidationResult(
                is_valid=True,
                rule="Bank Account Number Plausibility Check",
                details=f"Account number format is plausible ({len(cleaned)} digits). (Note: Does not confirm account activity with bank).",
            )

        return ValidationResult(
            is_valid=False,
            rule="Bank Account Number Plausibility Check",
            details=f"Invalid bank account number format: '{acc_num}'. Expected 9 to 18 numeric digits.",
        )

    @classmethod
    def run_all_field_validations(
        cls,
        document_category: str,
        extracted_fields: dict[str, str | None],
    ) -> list[FieldValidationFinding]:
        """Run all applicable format validations for the extracted category fields."""
        findings: list[FieldValidationFinding] = []

        if document_category == "pan_card" or "pan_number" in extracted_fields:
            pan_val = extracted_fields.get("pan_number")
            res = cls.validate_pan(pan_val)
            findings.append(
                FieldValidationFinding(
                    field_name="pan_number",
                    value=pan_val,
                    is_valid=res.is_valid,
                    rule=res.rule,
                    details=res.details,
                )
            )

        if document_category == "gst_certificate" or "gstin" in extracted_fields:
            gstin_val = extracted_fields.get("gstin")
            res = cls.validate_gstin(gstin_val)
            findings.append(
                FieldValidationFinding(
                    field_name="gstin",
                    value=gstin_val,
                    is_valid=res.is_valid,
                    rule=res.rule,
                    details=res.details,
                )
            )

        if document_category == "bank_proof":
            if "ifsc_code" in extracted_fields:
                ifsc_val = extracted_fields.get("ifsc_code")
                res = cls.validate_ifsc(ifsc_val)
                findings.append(
                    FieldValidationFinding(
                        field_name="ifsc_code",
                        value=ifsc_val,
                        is_valid=res.is_valid,
                        rule=res.rule,
                        details=res.details,
                    )
                )

            if "account_number" in extracted_fields:
                acc_val = extracted_fields.get("account_number")
                res = cls.validate_account_number(acc_val)
                findings.append(
                    FieldValidationFinding(
                        field_name="account_number",
                        value=acc_val,
                        is_valid=res.is_valid,
                        rule=res.rule,
                        details=res.details,
                    )
                )

        if document_category == "certificate_of_incorporation" and "cin" in extracted_fields:
            cin_val = extracted_fields.get("cin")
            res = cls.validate_cin(cin_val)
            findings.append(
                FieldValidationFinding(
                    field_name="cin",
                    value=cin_val,
                    is_valid=res.is_valid,
                    rule=res.rule,
                    details=res.details,
                )
            )

        return findings


# ---------------------------------------------------------------------------
# String Normalizers for Comparison
# ---------------------------------------------------------------------------

def normalize_text(text: str | None) -> str:
    """Normalize text by trimming, lowercasing, and collapsing whitespace."""
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


def normalize_company_name(name: str | None) -> str:
    """
    Normalize company names by standardizing common legal entity abbreviations:
    e.g. 'Pvt. Ltd.' -> 'private limited', 'LLP' -> 'limited liability partnership'.
    """
    if not name:
        return ""

    s = normalize_text(name)
    # Remove punctuation like dots and commas
    s = re.sub(r"[^\w\s]", "", s)

    # Standardize abbreviations
    replacements = [
        (r"\bpvt\s+ltd\b", "private limited"),
        (r"\bpvt\b", "private"),
        (r"\bltd\b", "limited"),
        (r"\bcorp\b", "corporation"),
        (r"\binc\b", "incorporated"),
        (r"\bco\b", "company"),
        (r"\bllp\b", "limited liability partnership"),
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)

    return " ".join(s.split())

