import os
import json
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.models import (
    Invoice, PurchaseOrder, DeliveryReceipt,
    TrustPassport, CrossDocVerification, DuplicateCheckResult,
    RiskAssessment, AuditBlock
)
from backend.crypto_utils import hash_bytes, hash_string, generate_normalized_key, format_inr
from backend.extractor import extract_invoice_data_from_pdf
from backend.verification import verify_cross_documents, check_duplicate_financing
from backend.risk_engine import evaluate_trust_risk
from backend.audit_chain import AuditLedger
from backend.sample_data import (
    get_initial_invoices, get_initial_purchase_orders, get_initial_delivery_receipts
)

app = FastAPI(
    title="InvoiceTrust — Intelligent Invoice Financing Verification",
    description="Synesis 26 Fintech MVP with Hybrid Audit Architecture & Explainable Risk Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent in-memory storage (can also be saved to JSON)
invoices_db: Dict[str, Invoice] = {}
po_db: Dict[str, PurchaseOrder] = {}
delivery_db: Dict[str, DeliveryReceipt] = {}
audit_ledger = AuditLedger()

def seed_demo_database():
    """Initializes sample data and records initial cryptographic audit blocks."""
    global invoices_db, po_db, delivery_db, audit_ledger
    invoices_db = {inv.id: inv for inv in get_initial_invoices()}
    po_db = get_initial_purchase_orders()
    delivery_db = get_initial_delivery_receipts()
    audit_ledger = AuditLedger()

    # Pre-record verifiable audit events for existing invoices
    for inv in invoices_db.values():
        audit_ledger.append_event(
            event_type="INVOICE_SUBMITTED",
            entity_id=inv.id,
            payload={
                "invoice_number": inv.invoice_number,
                "supplier": inv.supplier_name,
                "buyer": inv.buyer_name,
                "amount": inv.amount,
                "currency": inv.currency,
                "doc_hash": inv.doc_hash,
                "summary": f"Commercial invoice #{inv.invoice_number} submitted by {inv.supplier_name} for {format_inr(inv.amount)}"
            },
            action_by="Supplier Portal"
        )
        if inv.status in ["VERIFIED", "FINANCED", "FLAGGED_MISMATCH"]:
            audit_ledger.append_event(
                event_type="VERIFICATION_COMPLETED",
                entity_id=inv.id,
                payload={
                    "status": inv.status,
                    "po_reference": inv.po_reference,
                    "summary": f"Initial verification completed: Status marked as {inv.status}"
                },
                action_by="Automated Risk Engine"
            )

seed_demo_database()

# Static directories
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
sample_docs_dir = os.path.join(os.path.dirname(__file__), "sample_docs")

# ----------------- API ROUTES -----------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "InvoiceTrust Engine",
        "audit_chain_blocks": len(audit_ledger.get_all_blocks()),
        "invoices_registered": len(invoices_db)
    }

@app.get("/api/invoices", response_model=List[Invoice])
def list_invoices():
    """Returns all registered invoices."""
    return list(invoices_db.values())

@app.get("/api/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: str):
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoices_db[invoice_id]

class InvoiceSubmissionPayload(BaseModel):
    invoice_number: str
    supplier_name: str
    buyer_name: str
    invoice_date: str
    due_date: str
    amount: float
    currency: str = "INR"
    po_reference: Optional[str] = None
    delivery_reference: Optional[str] = None
    doc_hash: Optional[str] = None
    doc_filename: Optional[str] = None
    buyer_credit_status: Optional[str] = "GOOD"

@app.post("/api/invoices/upload-pdf")
async def upload_invoice_pdf(file: UploadFile = File(...)):
    """Uploads a PDF invoice, parses fields via pypdf, and returns extracted metadata."""
    contents = await file.read()
    result = extract_invoice_data_from_pdf(contents, file.filename)
    return result

@app.post("/api/invoices", response_model=Invoice)
def submit_invoice(payload: InvoiceSubmissionPayload):
    """Submits or confirms an invoice, computes hashes, and appends an audit event."""
    import re
    clean_num = re.sub(r'[^A-Za-z0-9]+', '-', payload.invoice_number.strip()).upper().strip('-')
    if not clean_num.startswith("INV-") and clean_num != "INV":
        clean_num = f"INV-{clean_num}"

    new_id = clean_num
    if new_id in invoices_db:
        # If ID exists, append unique suffix
        new_id = f"{clean_num}-{len(invoices_db) + 1}"

    # Compute normalized composite key
    _, norm_key = generate_normalized_key(
        payload.supplier_name, payload.buyer_name, payload.invoice_number, payload.amount, payload.currency
    )

    doc_hash = payload.doc_hash or hash_string(f"{payload.invoice_number}:{payload.supplier_name}:{payload.amount}")

    inv = Invoice(
        id=new_id,
        invoice_number=payload.invoice_number.strip(),
        supplier_name=payload.supplier_name.strip(),
        buyer_name=payload.buyer_name.strip(),
        invoice_date=payload.invoice_date.strip(),
        due_date=payload.due_date.strip(),
        amount=float(payload.amount),
        currency=payload.currency.strip().upper(),
        po_reference=payload.po_reference.strip() if payload.po_reference else None,
        delivery_reference=payload.delivery_reference.strip() if payload.delivery_reference else None,
        status="PENDING",
        doc_hash=doc_hash,
        doc_filename=payload.doc_filename,
        normalized_key=norm_key,
        buyer_credit_status=payload.buyer_credit_status or "GOOD"
    )

    invoices_db[inv.id] = inv

    # Append to cryptographic audit chain
    audit_ledger.append_event(
        event_type="INVOICE_SUBMITTED",
        entity_id=inv.id,
        payload={
            "invoice_number": inv.invoice_number,
            "supplier": inv.supplier_name,
            "buyer": inv.buyer_name,
            "amount": inv.amount,
            "currency": inv.currency,
            "doc_hash": inv.doc_hash,
            "normalized_key": inv.normalized_key,
            "summary": f"Invoice #{inv.invoice_number} submitted with doc hash {inv.doc_hash[:16]}..."
        },
        action_by="Lender Submission Desk"
    )

    return inv

@app.get("/api/passport/{invoice_id}", response_model=TrustPassport)
def get_trust_passport(invoice_id: str):
    """
    Builds the full Trust Passport:
    - 3-Way Cross-Document matching
    - Multi-tiered Duplicate Financing detection
    - Explainable deterministic Risk Assessment
    - Chronological audit blocks & cryptographic integrity status
    """
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = invoices_db[invoice_id]

    # Resolve matching Purchase Order
    po = None
    if invoice.po_reference and invoice.po_reference in po_db:
        po = po_db[invoice.po_reference]
    else:
        # Search by supplier/buyer/PO number if not exact key
        for p in po_db.values():
            if invoice.po_reference and p.po_number.upper() == invoice.po_reference.upper():
                po = p
                break

    # Resolve matching Delivery Receipt
    delivery = None
    if invoice.delivery_reference and invoice.delivery_reference in delivery_db:
        delivery = delivery_db[invoice.delivery_reference]
    elif invoice.po_reference:
        for d in delivery_db.values():
            if d.po_reference == invoice.po_reference:
                delivery = d
                break

    # 1. Cross-Document 3-Way Verification
    cross_verif = verify_cross_documents(invoice, po, delivery)

    # 2. Duplicate Financing Detection
    duplicate_result = check_duplicate_financing(invoice, list(invoices_db.values()))

    # 3. Deterministic Explainable Risk Assessment
    risk_assessment = evaluate_trust_risk(invoice, cross_verif, duplicate_result)

    # 4. Audit Chain inspection
    audit_events = audit_ledger.get_events_for_entity(invoice.id)
    chain_valid, _, _ = audit_ledger.verify_integrity()

    # Auto-align status if invoice is still PENDING
    if invoice.status == "PENDING":
        if duplicate_result.is_duplicate:
            invoice.status = "FLAGGED_DUPLICATE"
        elif cross_verif.status == "MISMATCH":
            invoice.status = "FLAGGED_MISMATCH"
        elif cross_verif.status == "INSUFFICIENT_EVIDENCE" or not cross_verif.delivery_found:
            invoice.status = "NEEDS_DOCUMENTS"
        elif risk_assessment.trust_score >= 80 and cross_verif.status == "MATCHED":
            invoice.status = "VERIFIED"

    return TrustPassport(
        invoice=invoice,
        purchase_order=po,
        delivery_receipt=delivery,
        cross_verification=cross_verif,
        duplicate_check=duplicate_result,
        risk_assessment=risk_assessment,
        audit_events=audit_events,
        chain_valid=chain_valid
    )

class ReviewActionPayload(BaseModel):
    new_status: str  # VERIFIED, NEEDS_DOCUMENTS, FLAGGED_MISMATCH, FLAGGED_DUPLICATE, FINANCED, REJECTED
    reviewer_notes: str
    reviewer_name: str = "Chief Credit Officer"

@app.post("/api/invoices/{invoice_id}/review")
def review_invoice(invoice_id: str, payload: ReviewActionPayload):
    """Applies human underwriter decision and records an immutable audit event."""
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = invoices_db[invoice_id]
    old_status = invoice.status
    invoice.status = payload.new_status

    # Record audit event
    block = audit_ledger.append_event(
        event_type="STATUS_CHANGED",
        entity_id=invoice.id,
        payload={
            "old_status": old_status,
            "new_status": payload.new_status,
            "reviewer_notes": payload.reviewer_notes,
            "summary": f"Invoice {invoice.id} status changed from {old_status} -> {payload.new_status}. Note: {payload.reviewer_notes}"
        },
        action_by=payload.reviewer_name
    )

    return {
        "success": True,
        "invoice_id": invoice.id,
        "old_status": old_status,
        "new_status": payload.new_status,
        "audit_block_index": block.index,
        "block_hash": block.current_hash
    }

# ----------------- AUDIT CHAIN ROUTES -----------------

@app.get("/api/audit/blocks")
def get_audit_blocks():
    """Returns chronological ledger entries."""
    return audit_ledger.get_all_blocks()

@app.post("/api/audit/verify")
def verify_audit_ledger():
    """Validates full sequential hash-chain cryptographic integrity."""
    valid, broken_idx, reason = audit_ledger.verify_integrity()
    return {
        "valid": valid,
        "broken_block_index": broken_idx,
        "total_blocks": len(audit_ledger.get_all_blocks()),
        "reason": reason
    }

class TamperPayload(BaseModel):
    block_index: int = 1
    malicious_text: str = "MALICIOUS TAMPERING: Bank wire coordinates rerouted to unauthorized account."

@app.post("/api/audit/tamper")
def tamper_audit_ledger(payload: TamperPayload):
    """
    Demonstrates Scenario E: Maliciously modifies a historical ledger entry
    so judges can witness the cryptographic hash mismatch immediately.
    """
    success, msg = audit_ledger.simulate_tampering(payload.block_index, payload.malicious_text)
    return {"success": success, "message": msg}

@app.post("/api/audit/restore")
def restore_audit_ledger():
    """Restores the hash-chain ledger to authentic state after a tampering demo."""
    restored = audit_ledger.restore_tampering()
    return {"restored": restored, "message": "Audit ledger restored to pristine cryptographic state."}

# ----------------- DEMO SCENARIOS -----------------

@app.post("/api/reset-demo")
def reset_demo():
    """Resets all data back to original state."""
    seed_demo_database()
    return {"message": "Demo data reset to clean initial state."}

@app.post("/api/load-scenario/{scenario_key}")
def load_scenario(scenario_key: str):
    """
    Returns pre-configured target invoice and context for Scenarios A, B, C, D, E.
    """
    s = scenario_key.upper()
    if s == "A":
        return {
            "scenario": "A",
            "title": "Consistent 3-Way Matched Invoice",
            "target_invoice_id": "INV-2024-101",
            "description": "Consistent invoice with matching PO (#PO-OMNI-7821) and confirmed Goods Received Note (#GRN-9901) for ₹4,50,000.00. High trust score, recommended for financing."
        }
    elif s == "B":
        return {
            "scenario": "B",
            "title": "PO Amount Mismatch Conflict",
            "target_invoice_id": "INV-2024-202",
            "description": "Commercial conflict: Invoice requests ₹12,85,000.00 but PO authorizes only ₹9,80,000.00 (+31.1% variance). Flagged for reviewer reconciliation."
        }
    elif s == "C":
        return {
            "scenario": "C",
            "title": "Duplicate Financing Attempt",
            "target_invoice_id": "INV-2024-303",
            "description": "Same invoice and collateral (₹7,50,000.00) already registered/financed under INV-2024-303. Caught via normalized composite key and binary hash collision."
        }
    elif s == "D":
        return {
            "scenario": "D",
            "title": "Missing Delivery Evidence (GRN Missing)",
            "target_invoice_id": "INV-2024-404",
            "description": "Titan Steel ₹21,00,000.00 invoice with PO, but lacking Proof of Delivery / Goods Received Note. Workflow recommends 'Request Documents'."
        }
    elif s == "E":
        return {
            "scenario": "E",
            "title": "Audit Hash-Chain Tamper Detection",
            "target_invoice_id": "INV-2024-505",
            "description": "Demonstrates cryptographic tamper detection for Solace Solar invoice (₹6,24,000.00). An unauthorized modification in block history is instantly caught by recomputing SHA-256 block hashes."
        }
    else:
        raise HTTPException(status_code=400, detail="Unknown scenario. Use A, B, C, D, or E.")

# ----------------- STATIC FILES & FRONTEND -----------------

@app.get("/sample_docs/{filename}")
def serve_sample_doc(filename: str):
    path = os.path.join(sample_docs_dir, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="File not found")

# Serve frontend directory
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
