import json
import urllib.request
import urllib.error
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def get_json(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "E2E-Checker"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "E2E-Checker"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def run_tests():
    passed = []
    failed = []

    print("=====================================================================")
    print("INVOICETRUST — COMPREHENSIVE END-TO-END QUALITY AUDIT")
    print("=====================================================================")

    # -------------------------------------------------------------------------
    # TEST 1 — INR consistency
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: INR Consistency & Underlying Monetary Values ---")
    try:
        # Check backend format_inr
        from backend.crypto_utils import format_inr
        assert format_inr(1500.0) == "₹1,500.00"
        assert format_inr(25000.0) == "₹25,000.00"
        assert format_inr(125000.0) == "₹1,25,000.00"
        assert format_inr(1250000.0) == "₹12,50,000.00"
        assert format_inr(450000.0) == "₹4,50,000.00"
        assert format_inr(1285000.0) == "₹12,85,000.00"
        print("  [✓] Indian numbering format_inr helper verified with all required amounts.")

        # Check frontend index HTML content
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as resp:
            html = resp.read().decode("utf-8")
        assert "₹52,09,000" in html, "Dashboard KPI total should show ₹52,09,000"
        assert "₹12,00,000" in html, "Dashboard KPI verified should show ₹12,00,000"
        assert 'value="INR" selected' in html, "Form should default to INR selected"
        assert "₹12.85L vs ₹9.80L" in html, "Scenario B pill should show INR amounts"
        print("  [✓] Frontend template verified: ₹ symbols and Indian number grouping present.")

        # Check API invoices data
        status, invoices = get_json("/api/invoices")
        assert status == 200 and len(invoices) >= 5
        for inv in invoices:
            assert inv["currency"] == "INR", f"Invoice {inv['id']} has currency {inv['currency']}"
            assert inv["amount"] > 0, f"Invoice {inv['id']} amount must be positive"
        print(f"  [✓] Registered invoices ({len(invoices)} claims) verified: 100% INR currency and valid amounts.")
        passed.append("TEST 1: INR Consistency & Monetary Integrity")
    except Exception as e:
        print(f"  [✗] TEST 1 FAILED: {e}")
        failed.append(f"TEST 1: INR Consistency ({e})")

    # -------------------------------------------------------------------------
    # TEST 2 — Invoice verification (Matched vs Mismatched)
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Invoice Verification (Matched vs Mismatched 3-Way Reconciliation) ---")
    try:
        # Case 2A: Matched Invoice (INV-2024-101)
        status, pA = get_json("/api/passport/INV-2024-101")
        assert status == 200
        crossA = pA["cross_verification"]
        assert crossA["amount_match"] is True, "INV-2024-101 amount should match PO"
        assert crossA["status"] == "MATCHED", f"Expected MATCHED, got {crossA['status']}"
        assert pA["risk_assessment"]["trust_score"] >= 80
        assert pA["risk_assessment"]["recommendation"] == "FINANCE_APPROVED"
        assert any("Invoice amount perfectly matches" in f["message"] for f in crossA["flags"])
        print(f"  [✓] 2A Matched Invoice: Score={pA['risk_assessment']['trust_score']}, Status={crossA['status']}, Flag explanation verified.")

        # Case 2B: Mismatched Invoice (INV-2024-202)
        status, pB = get_json("/api/passport/INV-2024-202")
        assert status == 200
        crossB = pB["cross_verification"]
        assert crossB["amount_match"] is False, "INV-2024-202 amount should NOT match PO"
        assert crossB["status"] == "MISMATCH", f"Expected MISMATCH, got {crossB['status']}"
        assert crossB["amount_difference"] == 305000.0, f"Expected 305000.0 diff, got {crossB['amount_difference']}"
        assert pB["risk_assessment"]["recommendation"] == "HUMAN_REVIEW_REQUIRED"
        mismatch_flag = next((f for f in crossB["flags"] if f["field"] == "amount"), None)
        assert mismatch_flag is not None and "Amount mismatch detected!" in mismatch_flag["message"]
        print(f"  [✓] 2B Mismatched Invoice: Variance=+₹3,05,000.00 (+31.1%), Flag explanation verified, Review escalated.")

        # Check legal / decision-support disclaimer
        assert "Advisory decision-support only" in pA["risk_assessment"]["legal_disclaimer"]
        print("  [✓] Legal / decision-support disclaimer confirmed in risk response.")
        passed.append("TEST 2: Cross-Document Verification (Matched vs Mismatched)")
    except Exception as e:
        print(f"  [✗] TEST 2 FAILED: {e}")
        failed.append(f"TEST 2: Invoice Verification ({e})")

    # -------------------------------------------------------------------------
    # TEST 3 — Duplicate detection
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Duplicate Financing Detection (Double-Pledging Intercept) ---")
    try:
        # First submission
        dup_inv_1 = {
            "invoice_number": "INV-DUP-TEST-900",
            "supplier_name": "Godrej Tech Industries Pvt Ltd",
            "buyer_name": "Tata Consumer Logistics",
            "invoice_date": "2026-09-01",
            "due_date": "2026-11-01",
            "amount": 840000.0,
            "currency": "INR",
            "po_reference": "PO-TATA-8800",
            "delivery_reference": "GRN-8800"
        }
        status1, created1 = post_json("/api/invoices", dup_inv_1)
        assert status1 == 200, f"First submission failed: {status1}"
        inv_id_1 = created1["id"]
        print(f"  [✓] Initial invoice submitted successfully: ID={inv_id_1}")

        # Second submission (Same invoice re-presented with slight formatting difference)
        dup_inv_2 = {
            "invoice_number": "INV DUP TEST 900",  # spaces instead of hyphens
            "supplier_name": "Godrej Tech Industries Pvt Ltd",
            "buyer_name": "Tata Consumer Logistics",
            "invoice_date": "2026-09-01",
            "due_date": "2026-11-01",
            "amount": 840000.0,
            "currency": "INR",
            "po_reference": "PO-TATA-8800",
            "delivery_reference": "GRN-8800"
        }
        status2, created2 = post_json("/api/invoices", dup_inv_2)
        assert status2 == 200, f"Second submission failed: {status2}"
        inv_id_2 = created2["id"]
        print(f"  [✓] Duplicate invoice re-submitted: ID={inv_id_2}")

        # Check passport of second submission
        status_pass, pass2 = get_json(f"/api/passport/{inv_id_2}")
        assert status_pass == 200
        dup_res = pass2["duplicate_check"]
        assert dup_res["is_duplicate"] is True, "Second submission MUST be flagged as duplicate!"
        assert dup_res["match_type"] in ["NORMALIZED_KEY_COLLISION", "EXACT_INVOICE_NUMBER"]
        assert pass2["risk_assessment"]["recommendation"] == "REJECT_FINANCING"
        print(f"  [✓] Duplicate intercepted: Match Type={dup_res['match_type']}, Details='{dup_res['details'][:65]}...'")
        print(f"  [✓] Financing decision blocked: Recommendation={pass2['risk_assessment']['recommendation']}, Score={pass2['risk_assessment']['trust_score']}")
        passed.append("TEST 3: Duplicate Financing Detection")
    except Exception as e:
        print(f"  [✗] TEST 3 FAILED: {e}")
        failed.append(f"TEST 3: Duplicate Detection ({e})")

    # -------------------------------------------------------------------------
    # TEST 4 — Audit integrity & tamper detection
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Hybrid Audit Architecture (Hash-Chain Integrity & Tamper Detection) ---")
    try:
        # Check initial blocks
        status, blocks = get_json("/api/audit/blocks")
        assert status == 200 and len(blocks) >= 2
        print(f"  [✓] Sequential audit ledger has {len(blocks)} recorded blocks.")

        # Check initial verification
        status, verify1 = post_json("/api/audit/verify", {})
        assert status == 200 and verify1["valid"] is True, f"Initial chain should be valid: {verify1}"
        print("  [✓] Initial hash-chain verified: 100% cryptographically valid.")

        # Tamper simulation: alter block #1
        status, tamper_res = post_json("/api/audit/tamper", {
            "block_index": 1,
            "malicious_text": "MALICIOUS TAMPER: Diverting NEFT wire to unauthorized account #1234."
        })
        assert status == 200 and tamper_res["success"] is True

        # Re-verify tampered chain: must fail
        status, verify2 = post_json("/api/audit/verify", {})
        assert status == 200 and verify2["valid"] is False, "Tampered chain MUST fail verification!"
        assert verify2["broken_block_index"] == 1
        print(f"  [✓] Tamper detection verified: Compromised Block #{verify2['broken_block_index']} caught immediately.")

        # Restore ledger to pristine state
        status, restore_res = post_json("/api/audit/restore", {})
        assert status == 200 and restore_res["restored"] is True
        status, verify3 = post_json("/api/audit/verify", {})
        assert status == 200 and verify3["valid"] is True, "Restored chain must be valid"
        print("  [✓] Ledger restored to pristine state: Verification passed.")

        # System characterization check: Verify it is labelled as local hash chain
        first_block = blocks[0]
        assert "is_anchored_mock" in first_block and first_block["is_anchored_mock"] is True
        print("  [✓] Audit architecture architecture verified: clearly identified as development hash-chain ledger with mock L1 commitments.")
        passed.append("TEST 4: Hybrid Audit Architecture & Tamper Detection")
    except Exception as e:
        print(f"  [✗] TEST 4 FAILED: {e}")
        failed.append(f"TEST 4: Audit Integrity ({e})")

    # -------------------------------------------------------------------------
    # TEST 5 — Application reliability & Main Workflow
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Application Reliability & Main End-to-End Workflow ---")
    try:
        # 5A: PDF extraction test
        import os
        from backend.extractor import extract_invoice_data_from_pdf
        pdf_path = "sample_docs/Invoice_Apex_101.pdf"
        assert os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        extracted = extract_invoice_data_from_pdf(pdf_bytes, "Invoice_Apex_101.pdf")
        assert extracted["success"] is True
        assert extracted["extracted_fields"]["invoice_number"] == "INV-2024-101"
        assert extracted["extracted_fields"]["amount"] == 450000.0
        assert extracted["extracted_fields"]["currency"] == "INR"
        print(f"  [✓] PDF Extractor parsed {extracted['filename']} successfully (Amount: ₹4,50,000.00).")

        # 5B: Underwriter review workflow: Update status
        review_payload = {
            "new_status": "NEEDS_DOCUMENTS",
            "reviewer_notes": "Holding disbursement pending verification of revised GSTIN e-way bill.",
            "reviewer_name": "Chief Risk Officer"
        }
        status, rev_res = post_json("/api/invoices/INV-2024-101/review", review_payload)
        assert status == 200 and rev_res["new_status"] == "NEEDS_DOCUMENTS"
        # Confirm audit event was recorded for review action
        status, updated_blocks = get_json("/api/audit/blocks")
        latest_block = updated_blocks[-1]
        assert latest_block["event_type"] == "STATUS_CHANGED"
        assert latest_block["entity_id"] == "INV-2024-101"
        assert latest_block["action_by"] == "Chief Risk Officer"
        print(f"  [✓] Underwriter review status update recorded to hash-chain: Block #{latest_block['index']}.")

        # Re-approve invoice back to VERIFIED
        post_json("/api/invoices/INV-2024-101/review", {
            "new_status": "VERIFIED",
            "reviewer_notes": "GSTIN verified. Cleared for financing.",
            "reviewer_name": "Chief Risk Officer"
        })

        # 5C: Error handling: 404 on missing invoice
        try:
            get_json("/api/passport/NON-EXISTENT-ID")
            assert False, "Should have returned 404"
        except urllib.error.HTTPError as err:
            assert err.code == 404
            print("  [✓] Error handling verified: Non-existent invoice returns HTTP 404.")

        # 5D: Error handling: 400 on invalid scenario
        try:
            post_json("/api/load-scenario/INVALID_SCENARIO", {})
            assert False, "Should have returned 400"
        except urllib.error.HTTPError as err:
            assert err.code == 400
            print("  [✓] Error handling verified: Invalid scenario key returns HTTP 400.")

        passed.append("TEST 5: Application Reliability & End-to-End Workflow")
    except Exception as e:
        print(f"  [✗] TEST 5 FAILED: {e}")
        failed.append(f"TEST 5: Application Reliability ({e})")

    # Reset demo database to clean state after test runs
    post_json("/api/reset-demo", {})

    print("\n=====================================================================")
    print(f"FINAL AUDIT SUMMARY: {len(passed)} PASSED, {len(failed)} FAILED")
    print("=====================================================================")
    for p in passed:
        print(f"  [PASS] {p}")
    for f in failed:
        print(f"  [FAIL] {f}")

    return len(failed) == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
