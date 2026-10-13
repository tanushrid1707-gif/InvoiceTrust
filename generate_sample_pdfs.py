import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def create_sample_invoice_pdf(filename: str, invoice_no: str, supplier: str, buyer: str, date: str, due_date: str, amount: float, po_ref: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Format amount in Indian notation
    # e.g., 450000.0 -> 4,50,000.00
    parts = f"{amount:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]
    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        pairs = []
        while len(remaining) > 2:
            pairs.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            pairs.insert(0, remaining)
        formatted_int = ",".join(pairs) + "," + last_three
    amt_str = f"INR {formatted_int}.{dec_part}"
    amt_symbol_str = f"Rs. {formatted_int}.{dec_part}"

    # Header Banner
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, height - 90, width, 90, fill=True, stroke=False)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 55, "TAX INVOICE")
    
    c.setFont("Helvetica", 11)
    c.drawString(400, height - 45, f"Invoice #: {invoice_no}")
    c.drawString(400, height - 65, f"Date: {date}")

    # Supplier & Buyer Boxes
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 130, "SUPPLIER / ISSUER:")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 150, f"From: {supplier}")
    c.drawString(50, height - 165, "GSTIN: 27AABCU9603R1ZM")
    c.drawString(50, height - 180, "Bandra Kurla Complex, Mumbai, MH - 400051")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 130, "CUSTOMER / BILL TO:")
    c.setFont("Helvetica", 11)
    c.drawString(320, height - 150, f"Bill To: {buyer}")
    c.drawString(320, height - 165, f"Purchase Order Ref: {po_ref}")
    c.drawString(320, height - 180, f"Payment Due Date: {due_date}")

    # Line item table header
    c.setFillColor(colors.HexColor("#0d9488"))
    c.rect(50, height - 240, width - 100, 25, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 225, "ITEM DESCRIPTION")
    c.drawString(320, height - 225, "QTY")
    c.drawString(390, height - 225, "UNIT PRICE")
    c.drawString(480, height - 225, "TOTAL (INR)")

    # Line items
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 260, "Enterprise Technology & Fulfillment Services")
    c.drawString(320, height - 260, "1")
    c.drawString(390, height - 260, amt_str)
    c.drawString(480, height - 260, amt_str)

    # Divider line
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(50, height - 280, width - 50, height - 280)

    # Totals box
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, height - 320, "Total Amount Due (INR):")
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(480, height - 320, amt_symbol_str)

    # Payment Instructions
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, height - 370, "Payment terms: Net 60 days. RTGS / NEFT transfer to authorized corporate treasury account.")
    c.drawString(50, height - 385, "Certified digital representation for Synesis 26 Invoice Financing verification (INR Currency).")

    c.save()
    print(f"Generated sample PDF: {filename} ({amt_str})")

if __name__ == "__main__":
    create_sample_invoice_pdf(
        "sample_docs/Invoice_Apex_101.pdf",
        invoice_no="INV-2024-101",
        supplier="Apex Global Technologies Pvt Ltd",
        buyer="OmniRetail India Ltd",
        date="2026-09-15",
        due_date="2026-11-15",
        amount=450000.00,
        po_ref="PO-OMNI-7821"
    )
    create_sample_invoice_pdf(
        "sample_docs/Invoice_Nexus_202.pdf",
        invoice_no="INV-2024-202",
        supplier="Nexus Industrial Supplies Pvt Ltd",
        buyer="Metro Logistics India Ltd",
        date="2026-09-20",
        due_date="2026-11-20",
        amount=1285000.00,
        po_ref="PO-METRO-4040"
    )
    create_sample_invoice_pdf(
        "sample_docs/Invoice_Duplicate_Attempt_303.pdf",
        invoice_no="INV-2024-303",
        supplier="Vanguard Semiconductor India Pvt Ltd",
        buyer="Starlight Electronics Ltd",
        date="2026-08-30",
        due_date="2026-10-30",
        amount=750000.00,
        po_ref="PO-STAR-9920"
    )
