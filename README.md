# InvoiceTrust — Intelligent Invoice Financing Verification
### Synesis 26 Fintech Track: Hybrid Audit Architecture & Decision-Support MVP

**InvoiceTrust** is a production-grade hackathon prototype designed for trade finance lenders, factors, and supply chain financiers. It solves the multi-billion dollar problem of fraudulent invoice financing, double-pledging (duplicate collateral), and phantom receivables through **3-Way Cross-Document Verification**, **Multi-Tiered Duplicate Detection**, **Explainable Deterministic Risk Scoring**, and a **Cryptographic Hybrid Audit Ledger**.

---

## 🏛️ System Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │          InvoiceTrust Presentation Layer               │
                  │  (Navy/Teal Fintech SPA • Tailwind CSS • Modern JS)    │
                  └───────────────────────────┬────────────────────────────┘
                                              │ REST API / JSON
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Application Core                                     │
├───────────────────────────────┬─────────────────────────────┬────────────────────────────┤
│   Document Extraction         │     Verification Engine     │    Cryptographic Engine    │
│   • pypdf native text layer   │     • 3-Way Cross Match     │    • SHA-256 Hasher        │
│   • Regex heuristic parser    │     • Multi-tier De-dup     │    • Normalized Key Gen    │
│   • Manual entry fallback     │     • Explainable Risk Rule │    • Hash-Chain Ledger     │
└───────────────┬───────────────┴──────────────┬──────────────┴──────────────┬─────────────┘
                │                              │                             │
                ▼                              ▼                             ▼
┌───────────────────────────────┐ ┌───────────────────────────┐ ┌──────────────────────────┐
│   Private Document Store      │ │   Lender Registry (Off-   │ │  Sequential Hash-Chain   │
│   (Off-Chain Confidentiality) │ │   Chain Factoring DB)     │ │  (Tamper-Evident Ledger) │
└───────────────────────────────┘ └───────────────────────────┘ └──────────────────────────┘
```

### Key Architectural Tenets
1. **Off-Chain Privacy First**: Trade secrets, invoices, and sensitive banking coordinates remain strictly off-chain in private storage. Only immutable cryptographic digests (SHA-256) are anchored to the audit ledger.
2. **Deterministic, Transparent Risk Scoring**: No black-box hallucinations. All risk factors are itemized with documented positive/negative point impacts.
3. **No Paid Dependencies**: Zero external cloud APIs, paid OCR tools, or complex blockchain nodes required. Runs self-contained in Python 3.12 with zero configuration.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12 (already installed on this machine)

### Option 1: One-Click Startup (Windows)
Double-click `run.bat` in the project root folder.

### Option 2: Command Line (PowerShell)
```powershell
python main.py
```

Open your browser to:
**(https://discuss-comfort-novels-ears.trycloudflare.com/)**

---

## 🎯 Demo Scenarios (Step-by-Step for Judges)

Use the top **Demo Scenarios Bar** in the application for 1-click test demonstration:

| Scenario | Title | Description | Expected Outcome |
|---|---|---|---|
| **A** | **Consistent 3-Way Match** | Apex Global (₹4,50,000.00) matches PO `#PO-OMNI-7821` and Confirmed GRN `#GRN-9901`. | **Trust Score: 95/100 (LOW RISK)**<br>Recommendation: `FINANCE_APPROVED` under policy limit. |
| **B** | **Amount Mismatch Conflict** | Nexus Supplies requests **₹12,85,000.00**, but PO authorizes only **₹9,80,000.00** (+31.1% variance). | **Trust Score: 65/100 (MODERATE RISK)**<br>Flagged: Material commercial discrepancy; requires underwriter review. |
| **C** | **Duplicate Financing Attempt** | Vanguard Semiconductor (₹7,50,000.00) re-presented. Normalized composite key catches claim collision. | **Trust Score: 30/100 (HIGH RISK)**<br>Flagged: `NORMALIZED_KEY_COLLISION`. Recommendation: `REJECT_FINANCING`. |
| **D** | **Missing Delivery Evidence** | Titan Steel invoice (₹21,00,000.00) has an approved PO, but Goods Received Note (GRN) is missing. | **Recommendation: `REQUEST_DOCUMENTS`**<br>Holds advance disbursement until delivery is verified. |
| **E** | **Ledger Tamper Detection** | Modifies historical Block #1 payload (₹4,50,000.00 invoice). Live integrity check recalculates SHA-256 chain. | **Alert: TAMPER DETECTED at Block #1**<br>Cryptographic proof that past records cannot be quietly modified. |

---

## 🔍 Deep-Dive: Core Technical Components

### 1. 3-Way Cross-Document Verification (`backend/verification.py`)
- Reconciles 3 key trade instruments:
  1. **Invoice**: Commercial payment request.
  2. **Purchase Order (PO)**: Buyer's commercial authorization and commitment.
  3. **Goods Received Note (GRN) / Delivery Receipt**: Proof of physical acceptance.
- Detects amount variance, entity naming differences, and missing delivery performance.
- **Fintech Principle**: A mismatch alone is **not definitive proof of fraud** (could be freight surcharges, partial shipments, or credit notes). It alerts the lender to hold funding until resolved.

### 2. Multi-Tiered Duplicate Financing Detection (`backend/crypto_utils.py`)
- **Tier 1 (Exact Binary Hash)**: Computes SHA-256 of the raw document file bytes. Catches direct PDF re-uploads.
- **Tier 2 (Normalized Composite Key)**:
  $$\text{Key} = \text{SHA256}(\text{Norm}(\text{Supplier}) \,\|\, \text{Norm}(\text{Buyer}) \,\|\, \text{Norm}(\text{Inv\#}) \,\|\, \text{Amount} \,\|\, \text{Currency})$$
  - Strips non-alphanumeric punctuation (`INV-2024-303` becomes `INV2024303`).
  - Cleans corporate entity suffixes (`Inc.`, `LLC`, `Ltd.`, `Corp`).
  - Standardizes rounding and currency format.
  - Catches fraudsters attempting to double-pledge invoices by simply altering formatting.
- **Tier 3 (Potential Collateral Collision)**: Flags identical supplier-buyer-amount billing in active windows.

### 3. Explainable Risk Engine & Trust Passport (`backend/risk_engine.py`)
- Calculates an objective score from 0 to 100 based on deterministic credit rules:
  - Base baseline: `85` points
  - Binary doc hash anchored: `+5` pts
  - De-duplication clear: `+5` pts
  - PO amount matches exactly: `+5` pts
  - Goods Received confirmed: `+5` pts
  - Material amount discrepancy (>5%): `-35` pts
  - Missing PO: `-30` pts
  - Missing delivery proof: `-20` pts
  - Duplicate claim flag: `-50` pts
  - Buyer overdue receivables history: `-20` pts
- Displays an itemized audit ledger of every factor for complete regulatory compliance.

### 4. Hybrid Audit Architecture & Hash-Chain (`backend/audit_chain.py`)
- Each block contains:
  ```json
  {
    "index": 1,
    "timestamp": "2026-10-13T10:45:00Z",
    "event_type": "INVOICE_SUBMITTED",
    "entity_id": "INV-2024-101",
    "payload_hash": "a1b2c3...",
    "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "current_hash": "SHA256(index:timestamp:event_type:entity_id:payload_hash:prev_hash)",
    "anchor_block_height": 1000001
  }
  ```
- **Integrity Verification**: Traverses blocks from index 0 to $N$, re-computing the cryptographic hash and comparing `prev_hash` to predecessor `current_hash`.
- In Scenario E, tampering with any historical block breaks the cryptographic chain at $O(N)$ speed and isolates the exact compromised block.

---



## 📂 File Map
- `main.py`: FastAPI server, REST endpoints, static mounting, database seeding.
- `backend/models.py`: Pydantic data schemas.
- `backend/crypto_utils.py`: SHA-256 hashing, string normalization, chain verification.
- `backend/extractor.py`: PDF reader with `pypdf` and regex fallback parser.
- `backend/verification.py`: 3-way cross-document matching and duplicate detection.
- `backend/risk_engine.py`: Deterministic Trust Score calculations and factor breakdowns.
- `backend/audit_chain.py`: Hybrid audit ledger, hash chaining, and tamper simulation.
- `backend/sample_data.py`: Pre-seeded realistic synthetic datasets for Scenarios A-E.
- `frontend/index.html`: Responsive single-page application with Navy/Teal design.
- `frontend/app.js`: Client UI controller, API calls, dynamic chart dials, and scenario loader.
- `frontend/styles.css`: Custom fintech styling and hash-chain visuals.
- `test_system.py`: Automated test suite testing all core engines and Scenarios A-E.
- `generate_sample_pdfs.py`: Script generating real test PDF files in `sample_docs/`.
- `run.bat`: One-click startup batch script for Windows.

