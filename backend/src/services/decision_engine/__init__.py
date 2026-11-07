"""
Application-level AI Decision Engine.

Cross-checks the identity attributes of a vendor application (company name,
PAN, GSTIN, CIN, mobile numbers, addresses, bank details) across the submitted
form fields and *every* uploaded document, then produces an explainable
recommendation: ``approve``, ``review`` (pending) or ``reject``.

Modules
-------
normalizers           — canonicalisation + fuzzy similarity helpers
identity_extractor    — canonical identity fields from parsed document text
                        (Nemotron reasoning with deterministic regex fallback)
consistency_checker   — form-integrity, cross-document and duplicate checks
decision_policy       — severity-based rules that turn findings into a decision
"""
