import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from backend.models import Invoice, PurchaseOrder, DeliveryReceipt
from backend.crypto_utils import (
    hash_bytes, hash_string, generate_normalized_key, verify_chain_integrity, format_inr
)
from backend.extractor import extract_invoice_data_from_pdf
from backend.verification import verify_cross_documents, check_duplicate_financing
from backend.risk_engine import evaluate_trust_risk
from backend.audit_chain import AuditLedger
from backend.sample_data import (
    get_initial_invoices, get_initial_purchase_orders, get_initial_delivery_receipts
)

def test_all():
    print(">>> 1. Testing Indian Currency (INR) Normalization & Formatter...")
    formatted_val = format_inr(1285000.0)
    assert formatted_val == "₹12,85,000.00", f"Expected ₹12,85,000.00, got {formatted_val}"
    assert format_inr(1500.0) == "₹1,500.00"
    assert format_inr(25000.0) == "₹25,000.00"
    assert format_inr(125000.0) == "₹1,25,000.00"
    assert format_inr(1250000.0) == "₹12,50,000.00"
    print(f"   [PASS] format_inr verified: 1285000 -> {formatted_val}")

    comp, key_hash = generate_normalized_key("Apex Global Technologies Pvt Ltd", "OmniRetail India Ltd", "INV-2024-101", 450000.0, "INR")
    comp2, key_hash2 = generate_normalized_key("apex global technologies pvt ltd", "omniretail india ltd", "inv2024101", 450000.0, "INR")
    assert key_hash == key_hash2, f"Normalized keys should match: {key_hash} != {key_hash2}"
    print(f"   [PASS] Normalization matches: '{comp}' -> {key_hash[:16]}...")

    print("\n>>> 2. Testing PDF Extraction in INR (pypdf)...")
    with open("sample_docs/Invoice_Apex_101.pdf", "rb") as f:
        pdf_res = extract_invoice_data_from_pdf(f.read(), "Invoice_Apex_101.pdf")
    assert pdf_res["success"] is True
    assert pdf_res["extracted_fields"]["invoice_number"] == "INV-2024-101"
    assert pdf_res["extracted_fields"]["amount"] == 450000.0
    assert pdf_res["extracted_fields"]["currency"] == "INR"
    assert pdf_res["extracted_fields"]["po_reference"] == "PO-OMNI-7821"
    print(f"   [PASS] Extracted invoice {pdf_res['extracted_fields']['invoice_number']} for {format_inr(pdf_res['extracted_fields']['amount'])} ({pdf_res['extracted_fields']['currency']})")

    print("\n>>> 3. Testing Scenario A (Consistent 3-Way Match in INR: Apex Tech)...")
    invoices = get_initial_invoices()
    pos = get_initial_purchase_orders()
    grns = get_initial_delivery_receipts()

    inv_A = invoices[0]
    po_A = pos[inv_A.po_reference]
    grn_A = grns[inv_A.delivery_reference]

    v_A = verify_cross_documents(inv_A, po_A, grn_A)
    dup_A = check_duplicate_financing(inv_A, invoices)
    risk_A = evaluate_trust_risk(inv_A, v_A, dup_A)

    assert v_A.status == "MATCHED", f"Expected MATCHED, got {v_A.status}"
    assert v_A.amount_match is True
    assert inv_A.amount == 450000.0
    assert inv_A.currency == "INR"
    assert dup_A.is_duplicate is False
    assert risk_A.trust_score >= 80, f"Expected trust score >= 80, got {risk_A.trust_score}"
    assert risk_A.recommendation == "FINANCE_APPROVED"
    print(f"   [PASS] Scenario A: Amount = {format_inr(inv_A.amount)}, Trust Score = {risk_A.trust_score}, Recommendation = {risk_A.recommendation}")

    print("\n>>> 4. Testing Scenario B (PO Amount Conflict in INR: Nexus Supplies)...")
    inv_B = invoices[1]  # Rs 12,85,000.00
    po_B = pos[inv_B.po_reference]  # Rs 9,80,000.00
    grn_B = grns[inv_B.delivery_reference]

    v_B = verify_cross_documents(inv_B, po_B, grn_B)
    dup_B = check_duplicate_financing(inv_B, invoices)
    risk_B = evaluate_trust_risk(inv_B, v_B, dup_B)

    assert v_B.status == "MISMATCH", f"Expected MISMATCH, got {v_B.status}"
    assert v_B.amount_match is False
    assert v_B.amount_difference == 305000.0  # +Rs 3,05,000.00
    assert risk_B.trust_score <= 65, f"Expected lower trust score, got {risk_B.trust_score}"
    assert risk_B.recommendation == "HUMAN_REVIEW_REQUIRED"
    print(f"   [PASS] Scenario B: Conflict flagged (+{format_inr(v_B.amount_difference)}), Score = {risk_B.trust_score}, Recommendation = {risk_B.recommendation}")

    print("\n>>> 5. Testing Scenario C (Duplicate Financing Collision in INR)...")
    # Duplicate attempt for Vanguard Semiconductor in INR
    candidate_dup = Invoice(
        id="INV-2024-303-REPRESENT",
        invoice_number="INV 2024 303",  # different punctuation
        supplier_name="Vanguard Semiconductor India, Pvt Ltd",  # slight suffix variance
        buyer_name="Starlight Electronics Ltd",
        invoice_date="2026-08-30",
        due_date="2026-10-30",
        amount=750000.0,
        currency="INR"
    )
    dup_C = check_duplicate_financing(candidate_dup, invoices)
    assert dup_C.is_duplicate is True, "Duplicate should be caught by normalized key!"
    print(f"   [PASS] Scenario C: Duplicate Caught! Match Type: {dup_C.match_type}")
    print(f"          Details: {dup_C.details}")

    print("\n>>> 6. Testing Scenario D (Missing Delivery Evidence in INR: Titan Steel)...")
    inv_D = invoices[3]
    po_D = pos[inv_D.po_reference]
    v_D = verify_cross_documents(inv_D, po_D, None)  # No GRN
    dup_D = check_duplicate_financing(inv_D, invoices)
    risk_D = evaluate_trust_risk(inv_D, v_D, dup_D)

    assert v_D.delivery_found is False
    assert risk_D.recommendation == "REQUEST_DOCUMENTS"
    print(f"   [PASS] Scenario D: Missing GRN detected for {format_inr(inv_D.amount)}. Recommendation = {risk_D.recommendation}")

    print("\n>>> 7. Testing Scenario E (Cryptographic Hash-Chain & Tamper Detection)...")
    ledger = AuditLedger()
    b1 = ledger.append_event("INVOICE_SUBMITTED", "INV-101", {"amount": 450000.0, "currency": "INR", "supplier": "Apex"})
    b2 = ledger.append_event("VERIFICATION_COMPLETED", "INV-101", {"result": "MATCHED"})
    b3 = ledger.append_event("STATUS_CHANGED", "INV-101", {"new_status": "FINANCED"})

    # Check initial chain
    is_valid, broken_idx, msg = ledger.verify_integrity()
    assert is_valid is True, "Clean ledger must be valid"
    print(f"   [PASS] Initial 4-Block Ledger Integrity: 100% VALID.")

    # Tamper with Block #1
    ledger.simulate_tampering(1, "MALICIOUS TAMPER: Hijacked wire routing number")
    is_valid_tampered, broken_tampered_idx, tampered_msg = ledger.verify_integrity()
    assert is_valid_tampered is False, "Tampered ledger must fail!"
    assert broken_tampered_idx == 1, f"Expected broken block 1, got {broken_tampered_idx}"
    print(f"   [PASS] Tamper Detection Caught! Broken Block #{broken_tampered_idx}")
    print(f"          Reason: {tampered_msg}")

    # Restore ledger
    ledger.restore_tampering()
    is_valid_restored, _, _ = ledger.verify_integrity()
    assert is_valid_restored is True, "Restored ledger must be valid again"
    print(f"   [PASS] Ledger restored to pristine cryptographic state.")

    print("\n=======================================================")
    print("ALL CORE ENGINES & SCENARIOS A-E PASSED WITH 100% SUCCESS (INR)!")
    print("=======================================================")

if __name__ == "__main__":
    test_all()
