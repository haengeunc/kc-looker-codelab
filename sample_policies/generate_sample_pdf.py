#!/usr/bin/env python3
"""Generates a sample Corporate Revenue Recognition and Refund Policy PDF."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1a73e8"),
        spaceAfter=10,
    )
    
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#202124"),
        spaceBefore=12,
        spaceAfter=6,
    )
    
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#3c4043"),
        spaceAfter=6,
    )
    
    alert_style = ParagraphStyle(
        "AlertBox",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#b06000"),
    )

    story = []
    
    # Title & Metadata
    story.append(Paragraph("Enterprise Policy & Governance Standard", title_style))
    story.append(Paragraph("<b>Document ID:</b> POL-FIN-2026-V3 &nbsp;|&nbsp; <b>Classification:</b> Confidential - Internal Operations &nbsp;|&nbsp; <b>Effective:</b> Fiscal Year 2025-2026", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a73e8"), spaceAfter=14))
    
    # Section 1
    story.append(Paragraph("1. Corporate Revenue Recognition Standard (ASC 606 / GAAP)", h2_style))
    story.append(Paragraph(
        "This policy defines the authoritative standards for calculating financial metrics across all corporate reporting systems, "
        "Business Intelligence dashboards (Looker), and AI agent workflows.",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Gross Revenue:</b> Total value of all merchandise ordered prior to cancellations or returns (LookML formula: <code>SUM(order_items.sale_price)</code>).<br/>"
        "• <b>Net Revenue (Certified Gold):</b> Revenue is recognized <i>only upon fulfillment completion</i>. Cancelled, returned, or in-transit orders are excluded. "
        "Strict LookML definition: <code>SUM(CASE WHEN order_items.status = 'Complete' THEN order_items.sale_price ELSE 0 END)</code>.<br/>"
        "• <b>Fiscal Calendar:</b> The corporate fiscal year begins <b>February 1</b> (<code>fiscal_month_offset: 1</code>). "
        "Fiscal Quarter 1 covers February through April, Q2 covers May through July, Q3 covers August through October, and Q4 covers November through January.",
        body_style
    ))
    
    # Section 2
    story.append(Paragraph("2. Customer Return, Refund & Cancellation Policy", h2_style))
    story.append(Paragraph(
        "• <b>Standard Return Window:</b> Retail customers may request refunds within 30 days of shipment delivery for unworn apparel and unopened merchandise.<br/>"
        "• <b>Refund Processing:</b> Upon receipt and inspection at distribution facilities, refunds are remitted to the original payment method within 3 to 5 business days.<br/>"
        "• <b>Restocking Fees:</b> A 15% restocking deduction applies to open-box consumer electronics and clearance items.<br/>"
        "• <b>Impact on Net Revenue:</b> Returned items are marked with status <code>Returned</code> in the order management database and are automatically excluded from the Gold Net Revenue metric.",
        body_style
    ))
    
    # Section 3
    story.append(Paragraph("3. Customer Data Privacy & PII Protection Guidelines (GDPR / CCPA)", h2_style))
    story.append(Paragraph(
        "In compliance with global data privacy mandates, all customer-level direct identifiers are tagged in Google Cloud Knowledge Catalog (Dataplex) "
        "with <b>PII = True</b> and access classification <b>RESTRICTED</b>.",
        body_style
    ))
    
    # Table of PII fields
    table_data = [
        ["Field Name", "Classification", "Looker View", "Policy Restriction"],
        ["users.email", "PII - Direct Identifier", "users", "Strictly Prohibited in AI responses. Masking required."],
        ["users.phone", "PII - Direct Identifier", "users", "Strictly Prohibited in AI responses. Masking required."],
        ["users.street_address", "PII - Geolocation", "users", "Prohibited. Use aggregated State or Country only."],
        ["users.country / state", "Non-PII (Aggregated)", "users", "Approved for geographic revenue segmentation."],
    ]
    t = Table(table_data, colWidths=[110, 120, 90, 200])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    
    # Section 4
    story.append(Paragraph("4. Looker Semantic Layer Certification Requirements", h2_style))
    story.append(Paragraph(
        "To prevent non-deterministic calculations and SQL hallucinations: "
        "<b>All AI assistants, analytics tools, and downstream consumers must query the Looker Semantic Layer via Looker MCP or the Looker Query API.</b> "
        "Raw SQL queries bypassing Looker's governed Explores (<code>customer_orders</code>) are non-compliant with corporate audit standards.",
        body_style
    ))
    
    doc.build(story)
    print(f"Policy PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "Corporate_Revenue_and_Refund_Policy.pdf")
    generate_pdf(out)
