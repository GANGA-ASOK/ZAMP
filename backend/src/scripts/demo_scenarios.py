"""
Demo / test scenarios for the AI Decision Engine.

Each scenario is a realistic vendor submission (form data + document texts)
designed to exercise one behaviour of the engine.  The same definitions drive
the automated tests (tests/test_ai_decision_engine.py) and the demo seeding
script (src/scripts/seed_demo_scenarios.py).

    1. happy_path          → approve   everything consistent
    2. pan_card_mismatch   → reject    PAN card carries a different PAN than the form/GSTIN
    3. third_party_bank    → review    payouts to a director's personal account
    4. personal_pan        → review    individual PAN used for a private limited company
    5. duplicate_bank      → reject    bank account already belongs to another vendor
    6. moved_office        → review    GST certificate shows another address and mobile
    7. incomplete          → review    GST certificate missing, bank proof is an unreadable scan
"""

from __future__ import annotations

import copy
import io
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# File builders
# ---------------------------------------------------------------------------


def make_pdf(text: str) -> bytes:
    """A one-page PDF with selectable text (like a digitally issued certificate)."""
    import pymupdf as fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 72
    for line in text.strip().splitlines():
        page.insert_text((56, y), line.strip(), fontsize=11)
        y += 18
    data = doc.tobytes()
    doc.close()
    return data


def make_blank_scan() -> bytes:
    """A near-blank JPEG — simulates a photo of a document with no legible text."""
    from PIL import Image

    img = Image.new("RGB", (800, 500), color=(236, 236, 230))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Form builder
# ---------------------------------------------------------------------------


def _vendor(
    *,
    ref: str,
    legal_name: str,
    trade_name: str,
    entity: str,
    cin: str,
    inc_date: str,
    street: str,
    city: str,
    state: str,
    pincode: str,
    first: str,
    last: str,
    phone: str,
    email: str,
    pan: str,
    gstin: str,
    gst_status: str = "Registered",
    holder: str,
    bank: str,
    account: str,
    ifsc: str,
    branch: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "reference_number": ref,
        "status": "submitted",
        "user_id": None,
        "company_info": {
            "legal_company_name": legal_name,
            "trade_name": trade_name,
            "business_entity_type": entity,
            "country": "India",
            "registration_number": cin,
            "incorporation_date": inc_date,
            "industry": "Information Technology",
            "website": "",
            "registered_address": {"street": street, "city": city, "state": state, "pincode": pincode, "country": "India"},
            "is_operational_same_as_registered": True,
            "operational_address": None,
        },
        "contact_info": {
            "primary": {"first_name": first, "last_name": last, "full_name": "", "designation": "Director",
                        "email": email, "phone": phone, "department": "Management"},
            "secondary": None,
            "signatory": {"first_name": "", "last_name": "", "full_name": f"{first} {last}", "designation": "Director",
                          "email": email, "phone": "", "department": ""},
            "confirm_authorized": True,
        },
        "tax_details": {"pan_number": pan, "gst_status": gst_status, "gstin": gstin, "gst_state": state, "tan_number": ""},
        "banking_details": {"account_holder_name": holder, "bank_name": bank, "account_number": account,
                            "ifsc_code": ifsc, "account_type": "Current Account", "bank_branch": branch,
                            "confirm_bank_ownership": True},
        "documents": [],
        "declarations": {"confirm_accurate": True, "authorize_verification": True, "agree_terms": True},
        "review_notes": "",
        "rejection_reason": "",
        "clarification_requests": [],
        "created_at": now,
        "updated_at": now,
        "submitted_at": now,
    }


# ---------------------------------------------------------------------------
# Document text templates
# ---------------------------------------------------------------------------


def pan_card(name: str, pan: str, date: str) -> str:
    return f"""
INCOME TAX DEPARTMENT
GOVT. OF INDIA
Permanent Account Number Card
PAN: {pan}
Name: {name}
Date of Incorporation/Formation: {date}
"""


def gst_certificate(gstin: str, legal: str, trade: str, address: str, mobile: str | None = None,
                    liability_date: str = "01/07/2017") -> str:
    mob = f"\nMobile: {mobile}" if mobile else ""
    return f"""
Government of India
Form GST REG-06
Registration Certificate
Registration Number (GSTIN): {gstin}
Legal Name: {legal}
Trade Name: {trade}
Constitution of Business: Private Limited Company
Address of Principal Place of Business: {address}{mob}
Date of Liability: {liability_date}
Type of Registration: Regular
"""


def incorporation_certificate(name: str, cin: str, date_words: str, address: str) -> str:
    return f"""
GOVERNMENT OF INDIA
MINISTRY OF CORPORATE AFFAIRS
Certificate of Incorporation
I hereby certify that {name} is incorporated
on this {date_words} under the Companies Act, 2013.
Corporate Identity Number: {cin}
Registered Office: {address}
Registrar of Companies
"""


def bank_proof(bank: str, holder: str, account: str, ifsc: str, branch: str) -> str:
    return f"""
{bank.upper()}
CANCELLED CHEQUE
Account Holder Name: {holder}
A/C No: {account}
IFSC: {ifsc}
Branch: {branch}
"""


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

ACME = dict(
    ref="VND-DEMO-0001", legal_name="Acme Technologies Private Limited", trade_name="Acme Tech",
    entity="Private Limited Company", cin="U72200KA2018PTC123456", inc_date="2018-06-14",
    street="12 MG Road, Indiranagar", city="Bengaluru", state="Karnataka", pincode="560038",
    first="Priya", last="Nair", phone="9845012345", email="priya@acmetech.in",
    pan="AAACA1234F", gstin="29AAACA1234F1Z5", holder="Acme Technologies Pvt Ltd",
    bank="HDFC Bank", account="50200012345678", ifsc="HDFC0001234", branch="Indiranagar, Bengaluru",
)


def _dates(iso: str) -> tuple[str, str, str]:
    """ISO incorporation date → (dd/mm/yyyy, '14th day of June 2018', GST date of liability)."""
    d = datetime.strptime(iso, "%Y-%m-%d")
    suffix = "th" if 11 <= d.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    gst_start = datetime(2017, 7, 1)  # GST came into force on 1 July 2017
    gst_registered = max(d + timedelta(days=24), gst_start)  # companies register for GST a few weeks after incorporation
    return d.strftime("%d/%m/%Y"), f"{d.day}{suffix} day of {d.strftime('%B %Y')}", gst_registered.strftime("%d/%m/%Y")


def _happy_docs(v: dict[str, Any], *, mobile: str | None = None, gst_address: str | None = None) -> list[tuple[str, str, Any]]:
    addr = f"{v['street']}, {v['city']}, {v['state']} - {v['pincode']}"
    numeric, words, liability = _dates(v["inc_date"])
    return [
        ("pan_card", "pan_card.pdf", pan_card(v["legal_name"].upper(), v["pan"], numeric)),
        ("gst_certificate", "gst_reg06.pdf",
         gst_certificate(v["gstin"], v["legal_name"], v["trade_name"], gst_address or addr, mobile, liability)),
        ("certificate_of_incorporation", "certificate_of_incorporation.pdf",
         incorporation_certificate(v["legal_name"].upper(), v["cin"], words, f"{v['street']}, {v['city']} {v['pincode']}")),
        ("bank_proof", "cancelled_cheque.pdf", bank_proof(v["bank"], v["holder"].upper(), v["account"], v["ifsc"], v["branch"])),
    ]


def _scenario(key: str, title: str, expected: str, story: str, form: dict[str, Any], docs: list) -> dict[str, Any]:
    return {"key": key, "title": title, "expected": expected, "story": story, "form": form, "documents": docs}


def build_scenarios() -> list[dict[str, Any]]:
    s: list[dict[str, Any]] = []

    # 1. Happy path ---------------------------------------------------------
    v = dict(ACME)
    s.append(_scenario(
        "happy_path", "Acme Technologies — clean submission", "approve",
        "Every identifier on the form matches the PAN card, GST certificate, CoI and cancelled cheque. "
        "'Pvt Ltd' vs 'Private Limited' and '+91 98450 12345' vs '9845012345' are normalised, not flagged.",
        _vendor(**v), _happy_docs(v, mobile="+91 98450 12345"),
    ))

    # 2. PAN card belongs to a different PAN --------------------------------
    v = dict(ACME, ref="VND-DEMO-0002", legal_name="Brightwave Solutions Private Limited", trade_name="Brightwave",
             cin="U74999MH2019PTC234567", inc_date="2019-03-02", street="401 Link Road, Andheri West", city="Mumbai",
             state="Maharashtra", pincode="400053", first="Arjun", last="Kapoor", phone="9820098200",
             email="arjun@brightwave.co.in", pan="AABCB5678K", gstin="27AABCB5678K1Z2",
             holder="Brightwave Solutions Private Limited", bank="Axis Bank", account="912010045678123",
             ifsc="UTIB0000123", branch="Andheri West, Mumbai")
    docs = _happy_docs(v)
    docs[0] = ("pan_card", "pan_card.pdf", pan_card("BRIGHTWAVE SOLUTIONS PRIVATE LIMITED", "AABCB9012Q", "02/03/2019"))
    s.append(_scenario(
        "pan_card_mismatch", "Brightwave Solutions — PAN card doesn't match", "reject",
        "The form PAN and the GSTIN agree (AABCB5678K), but the uploaded PAN card shows AABCB9012Q. "
        "The name looks right, so this only surfaces when the identifiers are cross-referenced.",
        _vendor(**v), docs,
    ))

    # 3. Third-party bank account ------------------------------------------
    v = dict(ACME, ref="VND-DEMO-0003", legal_name="Greenleaf Organics Private Limited", trade_name="Greenleaf",
             cin="U01100TN2020PTC345678", inc_date="2020-01-20", street="22 Anna Salai, T Nagar", city="Chennai",
             state="Tamil Nadu", pincode="600017", first="Rahul", last="Mehta", phone="9884012345",
             email="rahul@greenleaforganics.in", pan="AAFCG4521L", gstin="33AAFCG4521L1Z8",
             holder="Rahul Mehta", bank="State Bank of India", account="30987654321", ifsc="SBIN0001234",
             branch="T Nagar, Chennai")
    s.append(_scenario(
        "third_party_bank", "Greenleaf Organics — payouts to a director's personal account", "review",
        "Company documents are all consistent, but the payout account is held by the director personally. "
        "The cheque matches what was declared, so it is not hidden — it needs a human decision, not an auto-reject.",
        _vendor(**v), _happy_docs(v),
    ))

    # 4. Individual PAN used for a company ---------------------------------
    v = dict(ACME, ref="VND-DEMO-0004", legal_name="Mehta Engineering Works Private Limited", trade_name="Mehta Engineering",
             cin="U29100GJ2017PTC456789", inc_date="2017-08-09", street="14 Ashram Road, Navrangpura",
             city="Ahmedabad", state="Gujarat", pincode="380009", first="Rajesh", last="Mehta", phone="9925012345",
             email="rajesh@mehtaengg.com", pan="AAPPM7788K", gstin="24AAPPM7788K1Z3",
             holder="Mehta Engineering Works Private Limited", bank="ICICI Bank", account="123405006789",
             ifsc="ICIC0000456", branch="Navrangpura, Ahmedabad")
    docs = _happy_docs(v)
    docs[0] = ("pan_card", "pan_card.pdf", pan_card("RAJESH MEHTA", v["pan"], "11/02/1979"))
    s.append(_scenario(
        "personal_pan", "Mehta Engineering — director's personal PAN used for the company", "review",
        "Everything matches across documents, but the PAN's 4th character is 'P' (individual). A private limited "
        "company must have its own 'C' PAN — the tax ID format is wrong for the entity type.",
        _vendor(**v), docs,
    ))

    # 5. Bank account already used by another vendor -----------------------
    v = dict(ACME, ref="VND-DEMO-0005", legal_name="Nimbus Traders Private Limited", trade_name="Nimbus",
             cin="U51909KA2021PTC567890", inc_date="2021-11-03", street="7 Residency Road", city="Bengaluru",
             state="Karnataka", pincode="560025", first="Vikram", last="Rao", phone="9900112233",
             email="vikram@nimbustraders.in", pan="AAHCN3344P", gstin="29AAHCN3344P1Z6",
             holder="Nimbus Traders Private Limited", account=ACME["account"], ifsc=ACME["ifsc"])
    s.append(_scenario(
        "duplicate_bank", "Nimbus Traders — bank account belongs to another vendor", "reject",
        "On its own this submission looks perfect. But the payout account is already Acme Technologies' account "
        "(different PAN) — one account collecting for two unrelated vendors is a shell-vendor pattern.",
        _vendor(**v), _happy_docs(v),
    ))

    # 6. Moved office: address & mobile on GST certificate differ ----------
    v = dict(ACME, ref="VND-DEMO-0006", legal_name="Orbit Logistics Private Limited", trade_name="Orbit Logistics",
             cin="U63090MH2016PTC678901", inc_date="2016-05-27", street="Office 5, Viman Nagar Road", city="Pune",
             state="Maharashtra", pincode="411014", first="Sneha", last="Kulkarni", phone="9822012345",
             email="sneha@orbitlogistics.in", pan="AAICO6655R", gstin="27AAICO6655R1Z4",
             holder="Orbit Logistics Private Limited", bank="Kotak Mahindra Bank", account="7712345678",
             ifsc="KKBK0001777", branch="Viman Nagar, Pune")
    s.append(_scenario(
        "moved_office", "Orbit Logistics — GST certificate shows another address & mobile", "review",
        "IDs all match, but the GST certificate lists the principal place of business in MIDC Bhosari (PIN 411026) "
        "with a different mobile number. Likely an office move not updated on GST — the vendor must clarify.",
        _vendor(**v),
        _happy_docs(v, mobile="9765432100", gst_address="Plot 45, MIDC Bhosari, Pune, Maharashtra - 411026"),
    ))

    # 7. Incomplete: GST missing + unreadable bank proof -------------------
    v = dict(ACME, ref="VND-DEMO-0007", legal_name="Sunrise Foods", trade_name="Sunrise Foods",
             entity="Partnership", cin="", inc_date="2015-04-01", street="B-12 Okhla Industrial Area Phase 2",
             city="New Delhi", state="Delhi", pincode="110020", first="Amit", last="Gupta", phone="9811012345",
             email="amit@sunrisefoods.in", pan="AAKFS2233M", gstin="07AAKFS2233M1Z9", holder="Sunrise Foods",
             bank="Punjab National Bank", account="0123000100456789", ifsc="PUNB0012300", branch="Okhla, New Delhi")
    s.append(_scenario(
        "incomplete", "Sunrise Foods — GST certificate missing, unreadable bank proof", "review",
        "The firm declares itself GST-registered but did not upload the GST certificate, and the cancelled cheque is "
        "a blank photo with no legible text, so the payout account cannot be verified.",
        _vendor(**v),
        [
            ("pan_card", "pan_card.pdf", pan_card("SUNRISE FOODS", v["pan"], "01/04/2015")),
            ("bank_proof", "cheque_photo.jpg", None),  # None → blank scan image
        ],
    ))
    return s


def seed_scenario(db, scenario: dict[str, Any]) -> str:
    """Insert one scenario's vendor + documents into ``db``. Returns the vendor id."""
    from src.services.document_service import DocumentService

    form = copy.deepcopy(scenario["form"])
    now = datetime.now(timezone.utc)
    form.update(created_at=now, updated_at=now, submitted_at=now)  # seeding order = submission order
    db["vendors"].delete_many({"reference_number": form["reference_number"]})
    vendor_id = str(db["vendors"].insert_one(form).inserted_id)
    docs = DocumentService(db)
    for category, filename, text in scenario["documents"]:
        data = make_blank_scan() if text is None else make_pdf(text)
        docs.upload_document(vendor_id=vendor_id, file_bytes=data, filename=filename, category=category)
    return vendor_id
