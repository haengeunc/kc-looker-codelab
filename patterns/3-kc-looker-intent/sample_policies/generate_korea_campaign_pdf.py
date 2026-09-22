#!/usr/bin/env python3
"""Generates the 2026 APAC Regional Growth & South Korea Outerwear Campaign Policy PDF."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1a73e8"),
        spaceAfter=4,
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#5f6368"),
        spaceAfter=8,
    )
    
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#202124"),
        spaceBefore=10,
        spaceAfter=4,
    )
    
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#3c4043"),
        spaceAfter=5,
    )
    
    table_text_style = ParagraphStyle(
        "TableText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#202124"),
    )
    
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a73e8"),
    )

    story = []
    
    # 1. Header Banner & Metadata
    story.append(Paragraph("2026 APAC Regional Growth Strategy & Commercial Campaign Policy", title_style))
    story.append(Paragraph("<b>South Korea 6-Month Promotional Campaign: Outerwear & Coats Acceleration Initiative</b>", subtitle_style))
    story.append(Paragraph(
        "<b>Document ID:</b> POL-MKT-2026-KR04 &nbsp;|&nbsp; "
        "<b>Classification:</b> Confidential - Commercial Strategy & Governance &nbsp;|&nbsp; "
        "<b>Effective:</b> July 1, 2026 – December 31, 2026 (6 Months)",
        body_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a73e8"), spaceAfter=10))
    
    # 2. Executive Summary & Strategic Rationale
    story.append(Paragraph("1. Executive Summary & Market Opportunity", h2_style))
    story.append(Paragraph(
        "This commercial policy governs the execution of the <b>H2 2026 South Korea Outerwear & Coats Promotional Campaign</b>. "
        "Certified Looker baseline analytics (<code>thelook_prod.order_items</code>) identify South Korea as the #1 regional opportunity in APAC: "
        "Outerwear & Coats represents South Korea's highest revenue category (<b>$73,350.75</b> historical baseline) with a premium Average Sale Price of <b>$150.00</b>. "
        "However, order volume (475 orders) lags behind high-velocity categories such as Jeans (649 orders). "
        "To capture market share ahead of the critical winter retail season, the executive committee has authorized a structured 6-month promotional campaign "
        "combining targeted discount structures with strict margin floor guardrails.",
        body_style
    ))
    
    # 3. Promotional Discount & Voucher Structure
    story.append(Paragraph("2. Promotional Discount & Commercial Terms (The Campaign Rules)", h2_style))
    story.append(Paragraph(
        "Effective <b>July 1, 2026 through December 31, 2026</b>, all retail customer transactions originating from <code>users.country = 'South Korea'</code> "
        "are eligible for the following tiered promotional incentives on qualified Outerwear & Coats SKUs:",
        body_style
    ))
    
    promo_table_data = [
        [
            Paragraph("Promotion Tier", table_header_style),
            Paragraph("Eligibility & Criteria", table_header_style),
            Paragraph("Discount & Incentive", table_header_style),
            Paragraph("Promo Code / Terms", table_header_style),
        ],
        [
            Paragraph("<b>Tier 1: Category Growth</b>", table_text_style),
            Paragraph("Order includes at least 1 item in <code>products.category = 'Outerwear & Coats'</code>. Minimum cart subtotal: <b>$120.00</b>.", table_text_style),
            Paragraph("<b>15% Off</b> qualifying Outerwear items. Maximum discount capped at $45.00.", table_text_style),
            Paragraph("<code>KOREA_WINTER_15</code><br/>One use per verified customer account.", table_text_style),
        ],
        [
            Paragraph("<b>Tier 2: Basket Accelerator</b>", table_text_style),
            Paragraph("Total basket exceeds <b>$200.00</b> across any apparel combination including Outerwear.", table_text_style),
            Paragraph("<b>Additional $20 Instant Credit</b> + Free Expedited Shipping across South Korea.", table_text_style),
            Paragraph("Automatic checkout trigger; stackable with Tier 1.", table_text_style),
        ],
        [
            Paragraph("<b>VIP Loyalty Tier</b>", table_text_style),
            Paragraph("Customers with prior lifetime spend &gt; $500 in South Korea (per <code>user_order_facts</code>).", table_text_style),
            Paragraph("<b>20% Promotional Discount</b> on Outerwear & Sweaters + complimentary garment bag.", table_text_style),
            Paragraph("Direct invitation code issued via regional customer portal.", table_text_style),
        ],
    ]
    t_promo = Table(promo_table_data, colWidths=[100, 175, 145, 110])
    t_promo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_promo)
    story.append(Spacer(1, 6))

    # 4. Financial Guardrails & Minimum Margin Protection
    story.append(Paragraph("3. Financial Guardrails & Unit Economic Protection", h2_style))
    story.append(Paragraph(
        "• <b>Gross Margin Floor (Mandatory):</b> Under corporate treasury rules, no combination of promotional discounts may depress the "
        "<b>Gross Margin below 42.0%</b> (LookML: <code>order_items.total_gross_margin / order_items.total_sale_price</code>).<br/>"
        "• <b>High-Cost Product Exclusion:</b> For premium designer coats where wholesale landed cost exceeds 58% of MSRP, the promotional discount "
        "is hard-capped at <b>8.0%</b> to protect baseline unit profitability.<br/>"
        "• <b>Accounting Standard Compliance:</b> All campaign discounts are recognized as a contra-revenue item under <b>ASC 606</b> and "
        "must reconcile against the certified Looker <code>order_items.total_sale_price</code> measure.",
        body_style
    ))

    # 5. Regional Extended Return & Refund Window
    story.append(Paragraph("4. Regional Extended Return & Refund Policy (South Korea)", h2_style))
    story.append(Paragraph(
        "• <b>60-Day Extended Return Window:</b> To reduce online purchasing friction for high-ticket outerwear, South Korean customers receive an extended "
        "<b>60-day return window</b> (compared to the global standard 30-day window) for all unworn Outerwear & Coats items.<br/>"
        "• <b>Express Regional Refund SLA:</b> Returns collected via our Seoul and Gyeonggi logistics hub are inspected and refunded within "
        "<b>48 business hours</b> of carrier handover.<br/>"
        "• <b>Impact on Net Revenue:</b> Returned items are automatically updated to status <code>'Returned'</code> and deducted from certified Net Revenue in Looker.",
        body_style
    ))

    # 6. Target Campaign KPIs & Performance Milestones
    story.append(Paragraph("5. Target 6-Month Campaign Milestones & Performance Quotas", h2_style))
    
    kpi_table_data = [
        [
            Paragraph("Performance Metric", table_header_style),
            Paragraph("Pre-Campaign Baseline (Looker)", table_header_style),
            Paragraph("6-Month Target Quota (H2 2026)", table_header_style),
            Paragraph("Strategic Business Target", table_header_style),
        ],
        [
            Paragraph("<b>South Korea Outerwear Revenue</b>", table_text_style),
            Paragraph("$73,350.75", table_text_style),
            Paragraph("<b>$125,000.00</b>", table_text_style),
            Paragraph("+70.4% Revenue Growth in Korea", table_text_style),
        ],
        [
            Paragraph("<b>Completed Outerwear Orders</b>", table_text_style),
            Paragraph("475 completed orders", table_text_style),
            Paragraph("<b>800+ completed orders</b>", table_text_style),
            Paragraph("+68.4% Unit Volume Expansion", table_text_style),
        ],
        [
            Paragraph("<b>Average Sale Price (ASP)</b>", table_text_style),
            Paragraph("$150.00", table_text_style),
            Paragraph("<b>Maintain &ge; $142.00</b>", table_text_style),
            Paragraph("Protect premium brand positioning", table_text_style),
        ],
        [
            Paragraph("<b>Maximum Refund Rate</b>", table_text_style),
            Paragraph("7.8% of gross orders", table_text_style),
            Paragraph("<b>&le; 9.5% threshold</b>", table_text_style),
            Paragraph("Sustained quality guarantee", table_text_style),
        ],
    ]
    t_kpi = Table(kpi_table_data, colWidths=[130, 120, 130, 150])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 6))

    # 7. Knowledge Catalog Governance & Data Privacy Compliance
    story.append(Paragraph("6. Knowledge Catalog Governance & Privacy Guardrails (GDPR / PIPA)", h2_style))
    story.append(Paragraph(
        "• <b>Catalog Registration:</b> This policy is formally indexed in Google Cloud Knowledge Catalog (Dataplex) under entry group "
        "<code>governance-policies</code> (Entry: <code>south-korea-outerwear-campaign-policy</code>).<br/>"
        "• <b>PII Protection (South Korea Personal Information Protection Act - PIPA):</b> Direct customer identifiers "
        "(<code>users.email</code>, <code>users.phone</code>, Korean resident registration numbers, home delivery addresses) are tagged as "
        "<b>RESTRICTED_PII</b>. Commercial agents analyzing campaign performance must aggregate metrics strictly by geographic dimensions "
        "(<code>users.country = 'South Korea'</code>, <code>users.state</code>, <code>users.city</code>) and are prohibited from surfacing individual customer PII.<br/>"
        "• <b>Authoritative Semantic Layer:</b> All campaign reporting must be generated via Looker's certified Explore (<code>thelook_prod.order_items</code>). "
        "Unapproved direct SQL queries bypassing Looker are non-compliant with corporate audit standards.",
        body_style
    ))

    doc.build(story)
    print(f"Successfully generated South Korea Campaign Policy PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(
        os.path.dirname(__file__),
        "South_Korea_Outerwear_Promotional_Campaign_Policy.pdf"
    )
    generate_pdf(out_file)
