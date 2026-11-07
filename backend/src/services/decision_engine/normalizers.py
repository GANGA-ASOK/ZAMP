"""
Canonicalisation and fuzzy-matching helpers used by the decision engine.

Every comparison in the engine goes through these functions so that harmless
formatting differences ("Pvt. Ltd." vs "Private Limited", "+91 98450 12345"
vs "9845012345") never produce false mismatches, while real differences do.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Company / person names
# ---------------------------------------------------------------------------

_ABBREVIATIONS: list[tuple[str, str]] = [
    (r"\bpvt\b", "private"),
    (r"\bprivate\s+ltd\b", "private limited"),
    (r"\bltd\b", "limited"),
    (r"\bcorp\b", "corporation"),
    (r"\binc\b", "incorporated"),
    (r"\bco\b", "company"),
    (r"\bllp\b", "limited liability partnership"),
    (r"\bopc\b", "one person company"),
    (r"\bintl\b", "international"),
    (r"\btech\b", "technologies"),
    (r"\btechnology\b", "technologies"),
    (r"\bsvcs\b", "services"),
]

# Tokens that describe the legal form, not the identity of the business.
LEGAL_FORM_TOKENS: frozenset[str] = frozenset(
    {
        "private", "limited", "public", "company", "corporation", "incorporated",
        "liability", "partnership", "one", "person", "llp", "firm",
    }
)

_PREFIX_NOISE = re.compile(r"^(m\s*/\s*s\.?|messrs\.?|the)\s+", re.IGNORECASE)


def normalize_name(name: str | None) -> str:
    """Lower-case, strip punctuation/prefixes and expand legal abbreviations."""
    if not name:
        return ""
    s = str(name).lower().strip()
    s = _PREFIX_NOISE.sub("", s)
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = " ".join(s.split())
    for pattern, repl in _ABBREVIATIONS:
        s = re.sub(pattern, repl, s)
    return " ".join(s.split())


def core_name(name: str | None) -> str:
    """Business name with legal-form words removed ("acme technologies")."""
    tokens = [t for t in normalize_name(name).split() if t not in LEGAL_FORM_TOKENS]
    return " ".join(tokens)


def legal_form_of(name: str | None) -> str:
    """Return a coarse legal form detected from a name suffix."""
    n = normalize_name(name)
    if "limited liability partnership" in n:
        return "llp"
    if "one person company" in n:
        return "opc"
    if "private limited" in n:
        return "private_limited"
    if n.endswith("limited") or " limited " in f" {n} ":
        return "limited"
    return ""


def name_similarity(a: str | None, b: str | None) -> float:
    """
    Similarity in [0, 1] between two business / person names.

    Combines a sequence ratio on the normalised strings with a token-set
    overlap on the core names so word re-ordering and legal suffix variations
    are tolerated.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    ca, cb = core_name(a), core_name(b)
    if ca and cb and ca == cb:
        return 0.97  # same business, different legal-form wording

    # Compare the distinctive part of the names: shared legal-form words
    # ("private limited") must not make two unrelated businesses look similar.
    xa, xb = (ca, cb) if ca and cb else (na, nb)
    seq = SequenceMatcher(None, xa, xb).ratio()
    ta, tb = set(xa.split()), set(xb.split())
    jaccard = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    sorted_seq = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return round(max(seq, (jaccard + sorted_seq) / 2), 3)


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

def normalize_id(value: str | None) -> str:
    """Upper-case and strip whitespace / separators from an identifier."""
    if not value:
        return ""
    return re.sub(r"[\s\-./]", "", str(value)).upper()


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (small strings only — identifiers)."""
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def mask_account(value: str | None) -> str | None:
    """Mask a bank account number, keeping the last four digits."""
    if not value:
        return value
    digits = normalize_id(value)
    if len(digits) <= 4:
        return digits
    return "X" * (len(digits) - 4) + digits[-4:]


# ---------------------------------------------------------------------------
# Phone numbers
# ---------------------------------------------------------------------------

INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(value: str | None) -> str:
    """Reduce a phone number to its national significant number (10 digits for India)."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def is_valid_indian_mobile(value: str | None) -> bool:
    return bool(INDIAN_MOBILE.match(normalize_phone(value)))


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

PINCODE = re.compile(r"(?<!\d)([1-9]\d{2}\s?\d{3})(?!\d)")

_ADDRESS_ABBREVIATIONS: list[tuple[str, str]] = [
    (r"\brd\b", "road"),
    (r"\bst\b", "street"),
    (r"\bmg\b", "mahatma gandhi"),
    (r"\bblr\b", "bengaluru"),
    (r"\bbangalore\b", "bengaluru"),
    (r"\bbombay\b", "mumbai"),
    (r"\bmadras\b", "chennai"),
    (r"\bgurgaon\b", "gurugram"),
    (r"\bflr\b", "floor"),
    (r"\bnr\b", "near"),
    (r"\bopp\b", "opposite"),
    (r"\bno\b", "number"),
]


def normalize_address(value: str | None) -> str:
    if not value:
        return ""
    s = str(value).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = " ".join(s.split())
    for pattern, repl in _ADDRESS_ABBREVIATIONS:
        s = re.sub(pattern, repl, s)
    return " ".join(s.split())


def extract_pincode(value: str | None) -> str:
    if not value:
        return ""
    m = PINCODE.search(str(value))
    return m.group(1).replace(" ", "") if m else ""


def address_similarity(a: str | None, b: str | None) -> float:
    """Token-overlap similarity between two free-text addresses (pincode excluded)."""
    na = re.sub(r"\b\d{6}\b", "", normalize_address(a))
    nb = re.sub(r"\b\d{6}\b", "", normalize_address(b))
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb) / min(len(ta), len(tb))
    seq = SequenceMatcher(None, na, nb).ratio()
    return round(max(seq, overlap * 0.95), 3)


def format_address(addr: dict | str | None) -> str:
    """Render the form's structured address sub-document as one line."""
    if not addr:
        return ""
    if isinstance(addr, str):
        return addr
    parts = [addr.get("street"), addr.get("city"), addr.get("state"), addr.get("pincode")]
    return ", ".join(str(p).strip() for p in parts if p and str(p).strip())


# ---------------------------------------------------------------------------
# GST state codes (first two digits of a GSTIN)
# ---------------------------------------------------------------------------

GST_STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra", "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory",
}


def normalize_state(value: str | None) -> str:
    if not value:
        return ""
    s = re.sub(r"[^a-z\s]", " ", str(value).lower())
    s = " ".join(s.replace(" and ", " ").split())
    aliases = {"orissa": "odisha", "pondicherry": "puducherry", "nct of delhi": "delhi", "new delhi": "delhi"}
    return aliases.get(s, s)


def state_from_gstin(gstin: str | None) -> str:
    g = normalize_id(gstin)
    return GST_STATE_CODES.get(g[:2], "") if len(g) >= 2 else ""
