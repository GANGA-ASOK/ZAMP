"""
Seed the AI Decision Engine demo scenarios.

Usage:
    python -m src.scripts.seed_demo_scenarios                 # seed vendors + documents into MongoDB
    python -m src.scripts.seed_demo_scenarios --run           # ...and run the AI Decision Engine on each
    python -m src.scripts.seed_demo_scenarios --export demo   # only write the scenario PDFs to ./demo
                                                              # (for uploading through the vendor portal)

Seeded vendors use reference numbers VND-DEMO-0001 … VND-DEMO-0007 and are
replaced on every run, so the script is safe to re-run before a demo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib

from dotenv import load_dotenv

load_dotenv()

import src.database.mongodb as mongo_module  # noqa: E402
from src.scripts.demo_scenarios import build_scenarios, make_blank_scan, make_pdf, seed_scenario  # noqa: E402


def _form_sheet(s: dict) -> str:
    """Human-readable values to type into the vendor onboarding form."""
    f = s["form"]
    ci, ct, tx, bk = f["company_info"], f["contact_info"], f["tax_details"], f["banking_details"]
    a, p = ci["registered_address"], ct["primary"]
    rows = [
        ("STEP 1 - COMPANY INFORMATION", None),
        ("Legal company name", ci["legal_company_name"]), ("Trade name", ci["trade_name"]),
        ("Business entity type", ci["business_entity_type"]), ("Country", ci["country"]),
        ("Registration number (CIN)", ci["registration_number"] or "(not applicable)"),
        ("Incorporation date", ci["incorporation_date"]), ("Industry", ci["industry"]),
        ("Registered address", a["street"]), ("City", a["city"]), ("State", a["state"]), ("Pincode", a["pincode"]),
        ("Operational address", "Same as registered"),
        ("STEP 2 - CONTACT INFORMATION", None),
        ("Primary first name", p["first_name"]), ("Primary last name", p["last_name"]),
        ("Designation", p["designation"]), ("Email", p["email"]), ("Mobile", p["phone"]),
        ("Department", p["department"]),
        ("Authorized signatory", ct["signatory"]["full_name"]), ("Signatory designation", ct["signatory"]["designation"]),
        ("Signatory email", ct["signatory"]["email"]),
        ("STEP 3 - TAX & BANKING", None),
        ("PAN", tx["pan_number"]), ("GST status", tx["gst_status"]), ("GSTIN", tx["gstin"]), ("GST state", tx["gst_state"]),
        ("Account holder name", bk["account_holder_name"]), ("Bank name", bk["bank_name"]),
        ("Account number", bk["account_number"]), ("IFSC", bk["ifsc_code"]),
        ("Account type", bk["account_type"]), ("Branch", bk["bank_branch"]),
        ("STEP 4 - DOCUMENTS TO UPLOAD", None),
    ] + [(cat.replace("_", " ").title(), name) for cat, name, _ in s["documents"]]
    lines = [f"{s['title']}  (expected AI decision: {s['expected'].upper()})", ""]
    for label, value in rows:
        lines.append(f"\n{label}" if value is None else f"  {label:<28} {value}")
    return "\n".join(lines) + "\n"


def export(directory: str) -> None:
    root = pathlib.Path(directory)
    for s in build_scenarios():
        folder = root / s["key"]
        folder.mkdir(parents=True, exist_ok=True)
        for category, filename, text in s["documents"]:
            (folder / filename).write_bytes(make_blank_scan() if text is None else make_pdf(text))
        form = {k: v for k, v in s["form"].items() if k not in ("created_at", "updated_at", "submitted_at")}
        (folder / "form.json").write_text(json.dumps(form, indent=2), encoding="utf-8")
        (folder / "README.txt").write_text(f"{s['title']}\nExpected: {s['expected']}\n\n{s['story']}\n", encoding="utf-8")
        (folder / "form_fields.txt").write_text(_form_sheet(s), encoding="utf-8")
        print(f"  {folder}  ({len(s['documents'])} file(s), expected: {s['expected']})")


async def seed(run: bool) -> None:
    await mongo_module.connect_to_mongodb()
    try:
        db = mongo_module.db
        from src.services.application_decision_service import ApplicationDecisionService

        svc = ApplicationDecisionService(db)
        svc.ensure_indexes()
        for s in build_scenarios():
            old = db["vendors"].find_one({"reference_number": s["form"]["reference_number"]})
            if old:
                old_id = str(old["_id"])
                for col in ("verification_results", "ai_decision_runs", "ai_insights"):
                    db[col].delete_many({"vendor_id": old_id})
                for f in db["document_files.files"].find({"metadata.vendor_id": old_id}, {"_id": 1}):
                    db["document_files.chunks"].delete_many({"files_id": f["_id"]})
                    db["document_files.files"].delete_one({"_id": f["_id"]})
            vid = seed_scenario(db, s)
            line = f"  {s['form']['reference_number']}  {s['title']:<70} expected={s['expected']:<8}"
            if run:
                result = await svc.run_now(vid, trigger="demo-seed")
                d = result.get("decision") or {}
                line += f" got={d.get('outcome', result.get('status'))} risk={d.get('risk_score')}"
            print(line)
    finally:
        await mongo_module.close_mongodb_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="store_true", help="Run the AI Decision Engine after seeding.")
    parser.add_argument("--export", metavar="DIR", help="Write scenario files to DIR instead of seeding the database.")
    args = parser.parse_args()
    if args.export:
        export(args.export)
    else:
        asyncio.run(seed(args.run))


if __name__ == "__main__":
    main()
