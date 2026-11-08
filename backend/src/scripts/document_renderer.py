"""
Realistic renderers for the synthetic KYC test documents.

Each renderer reproduces the public layout of the real document so the demo
looks like what a procurement team actually receives:

    PanCard          — new-format PAN card / e-PAN (Income Tax Department)
    GstCertificate   — Form GST REG-06 registration certificate
    IncCertificate   — Form INC-11 certificate of incorporation (MCA, CRC Manesar)
    CancelledCheque  — CTS-2010 cheque leaf with MICR band, crossed "CANCELLED"

Every page carries a real, selectable text layer (as genuine e-PANs, GST and MCA
certificates do), drawn in reading order so the deterministic extractors keep
working in mock/test mode.  No emblems or logos are reproduced, and every page is
watermarked SPECIMEN: these are synthetic test fixtures, not usable documents.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

import pymupdf as fitz

A4 = (595, 842)

INK = (0.12, 0.12, 0.14)
GREY = (0.42, 0.42, 0.45)
RULE = (0.70, 0.70, 0.72)

SPECIMEN_NOTE = "SPECIMEN - synthetic test document generated for VendorFlow. Not issued by any authority."


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _text(page, x, y, s, size=9, font="helv", color=INK):
    page.insert_text((x, y), s, fontsize=size, fontname=font, color=color)


def _centered(page, y, s, size=10, font="helv", color=INK, x0=0, x1=None):
    x1 = page.rect.width if x1 is None else x1
    w = fitz.get_text_length(s, fontname=font, fontsize=size)
    _text(page, x0 + (x1 - x0 - w) / 2, y, s, size, font, color)


def _wrap(s: str, width: float, size: float, font: str) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if fitz.get_text_length(trial, fontname=font, fontsize=size) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def _paragraph(page, x, y, s, width, size=10, font="tiro", leading=1.45, color=INK) -> float:
    """Draw wrapped text; returns the y after the last line."""
    for line in _wrap(s, width, size, font):
        _text(page, x, y, line, size, font, color)
        y += size * leading
    return y


def _seed(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:8], 16))


def _qr(page, x, y, size, seed: str):
    """A QR-like block (decorative; encodes nothing)."""
    rnd, n = _seed(seed), 25
    cell = size / n
    page.draw_rect(fitz.Rect(x - 3, y - 3, x + size + 3, y + size + 3), color=None, fill=(1, 1, 1))
    shape = page.new_shape()
    for i in range(n):
        for j in range(n):
            finder = any(i in r and j in c for r, c in [(range(0, 7), range(0, 7)), (range(0, 7), range(18, 25)), (range(18, 25), range(0, 7))])
            if finder:
                on =(i in (0, 6, 18, 24) or j in (0, 6, 18, 24)) or (2 <= i % 18 <= 4 and 2 <= j % 18 <= 4)
            else:
                on = rnd.random() < 0.48
            if on:
                shape.draw_rect(fitz.Rect(x + j * cell, y + i * cell, x + (j + 1) * cell, y + (i + 1) * cell))
    shape.finish(color=None, fill=INK)
    shape.commit()


def _signature(page, x, y, w, seed: str, color=(0.10, 0.18, 0.45)):
    """A handwritten-looking squiggle."""
    rnd = _seed(seed, "sig")
    pts = [fitz.Point(x + w * k / 14, y + rnd.uniform(-7, 5)) for k in range(15)]
    shape = page.new_shape()
    for a, b, c in zip(pts[::2], pts[1::2], pts[2::2]):
        shape.draw_bezier(a, b + (0, rnd.uniform(-9, 9)), b, c)
    shape.finish(color=color, width=1.1, closePath=False)
    shape.commit()


def _guilloche(page, rect, color, step=5.0, seed="g"):
    """Fine wavy security-print background, like cheque / card pantographs."""
    import math

    rnd = _seed(seed, "wave")
    phase = rnd.uniform(0, 6)
    shape = page.new_shape()
    y = rect.y0
    while y < rect.y1:
        pts = [fitz.Point(rect.x0 + t, y + 2.2 * math.sin(t / 9 + phase + y / 17)) for t in range(0, int(rect.width) + 1, 3)]
        shape.draw_polyline(pts)
        y += step
    shape.finish(color=color, width=0.35, closePath=False)
    shape.commit()


def _watermark(page, text="SPECIMEN", size=64, opacity=0.10):
    """Diagonal watermark across the page (drawn last so it sits on top)."""
    r = page.rect
    w = fitz.get_text_length(text, fontname="hebo", fontsize=size)
    centre = fitz.Point(r.width / 2, r.height / 2)
    start = fitz.Point(centre.x - w / 2, centre.y + size / 3)
    page.insert_text(start, text, fontsize=size, fontname="hebo", color=(0.75, 0.1, 0.1),
                     fill_opacity=opacity, stroke_opacity=opacity,
                     morph=(centre, fitz.Matrix(28 if r.width > r.height else 40)))


def _footer(page, y=None):
    _centered(page, y or page.rect.height - 18, SPECIMEN_NOTE, size=6.5, color=(0.6, 0.15, 0.15))


def _doc_bytes(doc) -> bytes:
    data = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return data


# ---------------------------------------------------------------------------
# PAN card (new-format card, as on an e-PAN)
# ---------------------------------------------------------------------------

@dataclass
class PanCard:
    name: str
    pan: str
    date: str                      # incorporation date (entities) or DOB (individuals)
    father_name: str | None = None  # individuals only

    @property
    def individual(self) -> bool:
        return len(self.pan) == 10 and self.pan[3] == "P"

    def render(self) -> bytes:
        doc = fitz.open()
        page = doc.new_page(width=A4[0], height=A4[1])
        card = fitz.Rect(92, 70, 92 + 411, 70 + 259)  # 85.6 x 54 mm card, scaled ~1.7x

        # Card body: pale cyan with a darker header band and pantograph print.
        page.draw_rect(card + (3, 3, 3, 3), color=None, fill=(0.85, 0.85, 0.87), radius=0.05)
        page.draw_rect(card, color=(0.55, 0.65, 0.72), fill=(0.86, 0.94, 0.97), width=0.6, radius=0.05)
        _guilloche(page, fitz.Rect(card.x0 + 6, card.y0 + 52, card.x1 - 6, card.y1 - 8), (0.70, 0.84, 0.90), seed=self.pan)
        band = fitz.Rect(card.x0, card.y0, card.x1, card.y0 + 46)
        page.draw_rect(band, color=None, fill=(0.62, 0.82, 0.90), radius=0.12)
        page.draw_rect(fitz.Rect(band.x0, band.y0 + 20, band.x1, band.y1), color=None, fill=(0.62, 0.82, 0.90))
        # Generic round seal (not the national emblem).
        page.draw_circle(fitz.Point(card.x0 + (card.width / 2), card.y0 + 23), 15, color=(0.25, 0.4, 0.5), width=0.8)
        page.draw_circle(fitz.Point(card.x0 + (card.width / 2), card.y0 + 23), 10, color=(0.25, 0.4, 0.5), width=0.5)

        x, y = card.x0 + 16, card.y0
        _text(page, x, y + 20, "INCOME TAX DEPARTMENT", 11, "hebo")
        gw = fitz.get_text_length("GOVT. OF INDIA", fontname="hebo", fontsize=11)
        _text(page, card.x1 - 16 - gw, y + 20, "GOVT. OF INDIA", 11, "hebo")
        _centered(page, y + 66, "Permanent Account Number Card", 9.5, "helv", x0=card.x0, x1=card.x1 - 80)
        _centered(page, y + 86, self.pan, 15, "cobo", x0=card.x0, x1=card.x1 - 80)

        # Photo (individuals) and QR code on the right.
        _qr(page, card.x1 - 88, card.y0 + 58, 70, self.pan)
        ty = y + 116
        if self.individual:
            photo = fitz.Rect(card.x0 + 16, ty - 8, card.x0 + 84, ty + 78)
            page.draw_rect(photo, color=(0.5, 0.5, 0.5), fill=(0.80, 0.83, 0.86), width=0.5)
            page.draw_circle(fitz.Point(photo.x0 + 34, photo.y0 + 30), 15, color=None, fill=(0.62, 0.66, 0.70))
            import math
            cx, top, rx = photo.x0 + 34, photo.y0 + 50, 24
            shoulders = [fitz.Point(cx - rx * math.cos(t), top + 26 - 26 * math.sin(t)) for t in [k * math.pi / 16 for k in range(17)]]
            page.draw_polyline(shoulders + [fitz.Point(cx + rx, photo.y1), fitz.Point(cx - rx, photo.y1)],
                               color=None, fill=(0.62, 0.66, 0.70), closePath=True)
            x = photo.x1 + 14

        _text(page, x, ty, "Name", 7, "helv", GREY)
        _text(page, x, ty + 13, self.name, 10.5, "hebo")
        ty += 32
        if self.individual:
            _text(page, x, ty, "Father's Name", 7, "helv", GREY)
            _text(page, x, ty + 13, self.father_name or "-", 10.5, "hebo")
            ty += 32
            _text(page, x, ty, "Date of Birth", 7, "helv", GREY)
        else:
            _text(page, x, ty, "Date of Incorporation/Formation", 7, "helv", GREY)
        _text(page, x, ty + 13, self.date, 10.5, "hebo")

        # Faint background seal and a hologram sticker (bottom left), as on issued cards.
        seal = fitz.Point(card.x0 + card.width * 0.45, card.y0 + 165)
        for rad in (52, 44, 30):
            page.draw_circle(seal, rad, color=(0.72, 0.85, 0.91), width=0.8)
        holo = fitz.Rect(card.x0 + 16, card.y1 - 44, card.x0 + 52, card.y1 - 12)
        for i, c in enumerate([(0.85, 0.80, 0.95), (0.80, 0.92, 0.95), (0.92, 0.95, 0.80), (0.96, 0.86, 0.80)]):
            page.draw_rect(fitz.Rect(holo.x0, holo.y0 + i * 8, holo.x1, holo.y0 + (i + 1) * 8), color=None, fill=c)
        page.draw_rect(holo, color=(0.6, 0.65, 0.7), width=0.4)

        # Signature (individuals sign; entity cards carry none).
        if self.individual:
            _signature(page, card.x1 - 150, card.y1 - 28, 110, self.name)
            _text(page, card.x1 - 140, card.y1 - 12, "Signature", 7, "helv", GREY)

        _text(page, card.x0, card.y1 + 22, "This is a computer-generated PAN card layout. Quoting of PAN is mandatory "
              "for transactions specified under the Income Tax Act, 1961.", 6.5, "helv", GREY)
        _watermark(page, size=56, opacity=0.12)
        _footer(page)
        return _doc_bytes(doc)


# ---------------------------------------------------------------------------
# GST registration certificate — Form GST REG-06
# ---------------------------------------------------------------------------

@dataclass
class GstCertificate:
    gstin: str
    legal_name: str
    trade_name: str
    address: str
    constitution: str = "Private Limited Company"
    liability_date: str = "01/07/2017"
    mobile: str | None = None

    def render(self) -> bytes:
        doc = fitz.open()
        page = doc.new_page(width=A4[0], height=A4[1])
        L, R = 50, A4[0] - 50

        page.draw_rect(fitz.Rect(36, 36, A4[0] - 36, A4[1] - 36), color=RULE, width=0.6)
        _centered(page, 70, "Government of India", 12, "hebo")
        _centered(page, 88, "Form GST REG-06", 11, "hebo")
        _centered(page, 102, "[See Rule 10(1)]", 8.5, "helv", GREY)
        _centered(page, 124, "Registration Certificate", 14, "hebo")
        _qr(page, R - 64, 52, 58, self.gstin)

        _text(page, L, 156, f"Registration Number : {self.gstin}", 10.5, "hebo")

        issued = self.liability_date
        rows: list[tuple[str, list[str]]] = [
            ("1. Legal Name", [self.legal_name.upper()]),
            ("2. Trade Name, if any", [self.trade_name.upper()]),
            ("3. Constitution of Business", [self.constitution]),
            ("4. Address of Principal Place of Business", _wrap(self.address, 255, 9, "helv")),
            ("5. Date of Liability", [self.liability_date]),
            ("6. Period of Validity", ["From: " + self.liability_date, "To: Not Applicable"]),
            ("7. Type of Registration", ["Regular"]),
            ("8. Particulars of Approving Authority", ["Goods and Services Tax Network", "Designation: Approving Authority",
                                                      "Jurisdictional Office: State Tax Office"]),
            ("9. Date of issue of Certificate", [issued]),
        ]
        if self.mobile:
            rows.insert(4, ("Mobile Number of Principal Place", [self.mobile]))

        y, col = 172, L + 230
        for label, values in rows:
            h = 10 + 13 * len(values)
            page.draw_rect(fitz.Rect(L, y, R, y + h), color=RULE, width=0.5)
            page.draw_line(fitz.Point(col - 8, y), fitz.Point(col - 8, y + h), color=RULE, width=0.5)
            _text(page, L + 6, y + 15, label, 8.6, "hebo")
            for k, v in enumerate(values):
                _text(page, col, y + 15 + 13 * k, v, 9, "helv")
            y += h

        # Digital signature stamp.
        y += 26
        stamp = fitz.Rect(R - 230, y, R, y + 52)
        page.draw_rect(stamp, color=(0.15, 0.55, 0.25), width=0.8)
        _text(page, stamp.x0 + 8, y + 15, "Signature Not Verified", 8, "hebo", (0.15, 0.45, 0.2))
        _text(page, stamp.x0 + 8, y + 28, "Digitally signed by Goods and Services Tax Network", 7, "helv", GREY)
        _text(page, stamp.x0 + 8, y + 40, f"Date: {issued} 11:42:07 IST", 7, "helv", GREY)

        y += 90
        _paragraph(page, L, y, "Note: The registration certificate is required to be prominently displayed at all "
                   "places of business in the State. This is a system generated digitally signed Registration Certificate "
                   "issued based on the approval of application granted on " + issued + " by the jurisdictional authority.",
                   R - L, size=7.5, font="helv", color=GREY)

        _watermark(page)
        _footer(page, A4[1] - 44)
        return _doc_bytes(doc)


# ---------------------------------------------------------------------------
# Certificate of incorporation — Form INC-11
# ---------------------------------------------------------------------------

@dataclass
class IncCertificate:
    company: str
    cin: str
    date_words: str      # e.g. "14th day of June 2018"
    address: str

    def render(self) -> bytes:
        doc = fitz.open()
        page = doc.new_page(width=A4[0], height=A4[1])
        L, R = 64, A4[0] - 64

        # Ornamental double border.
        page.draw_rect(fitz.Rect(28, 28, A4[0] - 28, A4[1] - 28), color=(0.45, 0.35, 0.15), width=2.2)
        page.draw_rect(fitz.Rect(34, 34, A4[0] - 34, A4[1] - 34), color=(0.45, 0.35, 0.15), width=0.6)
        page.draw_circle(fitz.Point(A4[0] / 2, 82), 20, color=(0.45, 0.35, 0.15), width=0.8)
        page.draw_circle(fitz.Point(A4[0] / 2, 82), 14, color=(0.45, 0.35, 0.15), width=0.5)

        _centered(page, 126, "GOVERNMENT OF INDIA", 12, "tibo")
        _centered(page, 143, "MINISTRY OF CORPORATE AFFAIRS", 12, "tibo")
        _centered(page, 160, "Central Registration Centre", 10.5, "tiro")
        _centered(page, 196, "Certificate of Incorporation", 20, "tibo")
        y = _paragraph(page, L + 20, 216, "[Pursuant to sub-section (2) of section 7 and sub-section (1) of section 8 of the "
                       "Companies Act, 2013 (18 of 2013) and rule 18 of the Companies (Incorporation) Rules, 2014]",
                       R - L - 40, size=8.5, font="tiit", color=GREY)

        y = _paragraph(page, L, y + 22, f"I hereby certify that {self.company} is incorporated on this {self.date_words} "
                       "under the Companies Act, 2013 (18 of 2013) and that the company is limited by shares.",
                       R - L, size=11)
        y = _paragraph(page, L, y + 10, f"The Corporate Identity Number of the company is {self.cin}.", R - L, size=11)
        y = _paragraph(page, L, y + 10, f"Given under my hand at Manesar this {self.date_words}.", R - L, size=11)

        # Digital signature block.
        y += 30
        stamp = fitz.Rect(R - 220, y, R, y + 56)
        page.draw_rect(stamp, color=(0.15, 0.55, 0.25), width=0.8)
        _text(page, stamp.x0 + 8, y + 15, "Digital Signature Certificate", 8, "hebo", (0.15, 0.45, 0.2))
        _text(page, stamp.x0 + 8, y + 28, "DS MINISTRY OF CORPORATE AFFAIRS", 7, "helv", GREY)
        _text(page, stamp.x0 + 8, y + 40, "For and on behalf of the Jurisdictional", 7, "helv", GREY)
        _text(page, stamp.x0 + 8, y + 50, "Registrar of Companies", 7, "helv", GREY)
        y += 74
        _text(page, R - 220, y, "Registrar of Companies", 10, "tibo")
        _text(page, R - 220, y + 14, "Central Registration Centre", 10, "tiro")

        y += 46
        _text(page, L, y, "Registered Office:", 9.5, "tibo")
        y = _paragraph(page, L, y + 14, f"{self.company}, {self.address}", R - L, size=9.5)

        y += 18
        _paragraph(page, L, y, "Note: This certificate only evidences incorporation of the company on the basis of "
                   "documents and declarations of the applicant(s). This certificate is neither a license nor permission "
                   "to conduct business or solicit deposits or funds from public. Permission of business will be subject "
                   "to obtaining other licenses, permissions or registrations from the concerned authorities. The status "
                   "of the company can be verified on the Ministry of Corporate Affairs portal.",
                   R - L, size=7.5, font="tiro", color=GREY)

        _watermark(page)
        _footer(page, A4[1] - 42)
        return _doc_bytes(doc)


# ---------------------------------------------------------------------------
# Cancelled cheque — CTS-2010 leaf
# ---------------------------------------------------------------------------

_BANK_TINTS = [(0.84, 0.90, 0.97), (0.88, 0.95, 0.88), (0.97, 0.92, 0.84), (0.93, 0.88, 0.96), (0.96, 0.88, 0.88)]
_BANK_INK = [(0.08, 0.20, 0.45), (0.10, 0.38, 0.20), (0.50, 0.28, 0.05), (0.32, 0.16, 0.48), (0.50, 0.10, 0.12)]


@dataclass
class CancelledCheque:
    bank: str
    holder: str
    account: str
    ifsc: str
    branch: str
    company_account: bool = True

    def render(self) -> bytes:
        rnd = _seed(self.account, self.ifsc)
        k = int(hashlib.sha1(self.bank.encode()).hexdigest(), 16) % len(_BANK_TINTS)
        tint, ink = _BANK_TINTS[k], _BANK_INK[k]

        doc = fitz.open()
        page = doc.new_page(width=573, height=261)  # 202 x 92 mm
        r = page.rect
        page.draw_rect(r, color=None, fill=tint)
        _guilloche(page, fitz.Rect(0, 52, r.width, r.height - 40), tuple(c - 0.035 for c in tint), step=8, seed=self.account)
        _text(page, r.width / 2 - 26, 14, "CTS-2010", 7, "hebo", ink)

        # Bank and branch (top left).
        page.draw_rect(fitz.Rect(16, 12, 42, 38), color=None, fill=ink, radius=0.2)
        _text(page, 22, 31, self.bank[:1].upper(), 16, "hebo", (1, 1, 1))
        _text(page, 50, 26, self.bank.upper(), 13, "hebo", ink)
        _text(page, 50, 38, f"{self.branch.upper()} BRANCH", 6.8, "helv", ink)
        _text(page, 50, 47, f"IFSC: {self.ifsc}", 7.2, "hebo", ink)

        # Date boxes (top right).
        _text(page, r.width - 210, 24, "VALID FOR 3 MONTHS ONLY FROM THE DATE OF ISSUE", 5.6, "helv", ink)
        for i, ch in enumerate("DDMMYYYY"):
            box = fitz.Rect(r.width - 150 + i * 16, 30, r.width - 136 + i * 16, 46)
            page.draw_rect(box, color=ink, width=0.5)
            _text(page, box.x0 + 4, box.y1 - 4, ch, 6, "helv", (0.6, 0.6, 0.65))

        # Pay / Rupees lines.
        _text(page, 18, 76, "Pay", 9, "helv", ink)
        page.draw_line(fitz.Point(40, 78), fitz.Point(r.width - 70, 78), color=ink, width=0.5)
        _text(page, r.width - 66, 76, "OR BEARER", 7, "helv", ink)
        _text(page, 18, 100, "Rupees", 9, "helv", ink)
        page.draw_line(fitz.Point(58, 102), fitz.Point(r.width - 150, 102), color=ink, width=0.5)
        page.draw_line(fitz.Point(18, 124), fitz.Point(r.width - 150, 124), color=ink, width=0.5)
        amt = fitz.Rect(r.width - 140, 92, r.width - 16, 116)
        page.draw_rect(amt, color=ink, width=0.7, fill=(1, 1, 1))
        _text(page, amt.x0 + 5, amt.y1 - 7, "Rs.", 9, "hebo", ink)

        # Account number.
        _text(page, 18, 148, f"A/c No. {self.account}", 10.5, "cobo", INK)
        _text(page, 18, 160, "CURRENT ACCOUNT" if self.company_account else "SAVINGS ACCOUNT", 6.5, "helv", ink)

        # Signature block (bottom right): account name printed above the signature.
        sx = r.width - 210
        name_x = sx + 24 if self.company_account else sx
        size = 8.5
        while size > 6 and fitz.get_text_length(self.holder, fontname="hebo", fontsize=size) > r.width - 16 - name_x:
            size -= 0.25  # shrink long names to fit rather than truncating them
        if self.company_account:
            _text(page, sx, 150, "For", size, "hebo", INK)
        _text(page, name_x, 150, self.holder, size, "hebo", INK)
        page.draw_line(fitz.Point(sx, 192), fitz.Point(r.width - 16, 192), color=ink, width=0.5)
        _text(page, sx + 40, 202, "Authorised Signatories" if self.company_account else "Please sign above", 7, "helv", ink)

        # MICR band: cheque no., MICR (city-bank-branch), short a/c, transaction code.
        cheque_no = f"{rnd.randint(1, 999999):06d}"
        micr = f"{rnd.randint(110, 999)}{rnd.randint(100, 999)}{rnd.randint(1, 999):03d}"
        txn = "29" if self.company_account else "10"
        page.draw_rect(fitz.Rect(0, r.height - 40, r.width, r.height), color=None, fill=(1, 1, 1))
        _text(page, 60, r.height - 16, f'"{cheque_no}"  {micr}:  {self.account[-6:]}"  {txn}', 13, "cour", INK)

        # Crossed and cancelled.
        page.draw_line(fitz.Point(120, r.height - 44), fitz.Point(290, 56), color=(0.75, 0.05, 0.05), width=1.6)
        page.draw_line(fitz.Point(150, r.height - 44), fitz.Point(320, 56), color=(0.75, 0.05, 0.05), width=1.6)
        cw = fitz.get_text_length("CANCELLED", fontname="hebo", fontsize=26)
        mid = fitz.Point(220, 135)
        page.insert_text(fitz.Point(mid.x - cw / 2, mid.y + 9), "CANCELLED", fontsize=26, fontname="hebo",
                         color=(0.75, 0.05, 0.05), fill_opacity=0.85, morph=(mid, fitz.Matrix(48)))

        # Horizontal stamp in a blank area: a diagonal watermark over a cheque confuses OCR.
        stamp = fitz.Rect(18, 176, 106, 192)
        page.draw_rect(stamp, color=(0.75, 0.1, 0.1), width=0.8)
        _text(page, stamp.x0 + 9, stamp.y1 - 4.5, "SPECIMEN", 10, "hebo", (0.75, 0.1, 0.1))
        _centered(page, r.height - 3, SPECIMEN_NOTE, size=5, color=(0.6, 0.15, 0.15))

        # Scale the leaf up 1.5x (vector, text layer kept) so it rasterises like a
        # ~300 DPI scan rather than a thumbnail; small cheque print OCRs poorly otherwise.
        big = fitz.open()
        out = big.new_page(width=r.width * 1.5, height=r.height * 1.5)
        out.show_pdf_page(out.rect, doc, 0)
        doc.close()
        return _doc_bytes(big)


def render(spec) -> bytes:
    """Render a document spec (or legacy plain text) to PDF bytes."""
    return spec.render()
