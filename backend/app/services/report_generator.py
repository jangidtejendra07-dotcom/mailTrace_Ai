"""
Section 11 — Cybercrime Reporting.

Generates a ready-to-review PDF evidence/report package for a case.
This intentionally does NOT auto-file a police complaint — it produces
a report package that a human reviewer can submit via the National
Cyber Crime Reporting Portal's "Report Suspect" facility.

Feature 4 (Legal-Grade Automation) additionally adds
generate_legal_report_pdf(), which renders a jurisdiction-specific HTML
template (US/EU) through Jinja2, converts it to PDF, appends the case's
chain-of-custody trail, and applies a digital signature so the resulting
PDF is tamper-evident.
"""
import io
import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa
from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

from app.config import settings
from app.services import cert_generator

logger = logging.getLogger("mailtrace.report_generator")


def _kv_table(data: list[tuple[str, str]]) -> Table:
    table = Table(data, colWidths=[5 * cm, 11 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def generate_case_report_pdf(case: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], textColor=colors.HexColor("#0f172a"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#0f172a"), spaceBefore=14)
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#475569"))

    elements = []
    elements.append(Paragraph("MailTrace AI — Forensic Case Report", title_style))
    elements.append(Paragraph(
        "Automated email threat detection &amp; forensic intelligence report package. "
        "This document is generated for human analyst review prior to any external reporting.",
        small,
    ))
    elements.append(Spacer(1, 12))

    decision_color = {
        "BLOCK": "#dc2626", "QUARANTINE": "#d97706", "ALLOW": "#16a34a"
    }.get(case.get("decision", ""), "#1e293b")

    elements.append(_kv_table([
        ["Case ID", case.get("case_id", "")],
        ["Classification", case.get("classification", "")],
        ["Decision", f'<font color="{decision_color}"><b>{case.get("decision", "")}</b></font>'],
        ["Final Risk Score", f'{case.get("final_risk_score", "")} / 100'],
        ["Subject", case.get("subject", "") or "(none)"],
        ["From", case.get("from_address", "")],
        ["Evidence SHA-256", case.get("evidence_hash", "")],
        ["Generated At", case.get("generated_at", "")],
    ]))

    elements.append(Paragraph("Risk Reasoning", h2))
    for reason in case.get("explanation", []):
        elements.append(Paragraph(f"• {reason}", body))

    elements.append(Paragraph("Header / Authentication Forensics", h2))
    forensics = case.get("forensics_result", {})
    elements.append(_kv_table([
        ["SPF", forensics.get("spf", "")],
        ["DKIM", forensics.get("dkim", "")],
        ["DMARC", forensics.get("dmarc", "")],
        ["From Domain", forensics.get("from_domain", "")],
        ["Reply-To Domain", forensics.get("reply_to_domain") or "-"],
        ["Reply-To Mismatch", str(forensics.get("reply_to_mismatch", ""))],
        ["Candidate Source IP", forensics.get("candidate_source_ip") or "Unknown"],
    ]))
    for a in forensics.get("anomalies", []):
        elements.append(Paragraph(f"• {a}", body))

    geo = case.get("geolocation", {})
    if geo:
        elements.append(Paragraph("IP Geolocation Intelligence (probable, not exact)", h2))
        elements.append(_kv_table([
            ["IP Address", geo.get("ip") or "-"],
            ["Probable Origin", geo.get("probable_origin") or "Unknown"],
            ["ASN", geo.get("asn") or "-"],
            ["ISP / Org", geo.get("isp") or "-"],
            ["Hosting/Proxy Indicator", str(geo.get("is_hosting_or_proxy"))],
            ["Confidence", geo.get("confidence") or "-"],
        ]))

    url_result = case.get("url_result", {})
    if url_result.get("items"):
        elements.append(Paragraph("URL Intelligence", h2))
        for u in url_result["items"]:
            elements.append(Paragraph(f"<b>{u['original_url']}</b> — score {u['score']}/100", body))
            for f in u["suspicious_features"]:
                elements.append(Paragraph(f"&nbsp;&nbsp;• {f}", small))

    attachment_result = case.get("attachment_result", {})
    if attachment_result.get("items"):
        elements.append(Paragraph("Attachment Analysis", h2))
        for a in attachment_result["items"]:
            elements.append(Paragraph(
                f"<b>{a['filename']}</b> — severity {a['severity']} (score {a['score']}/100)", body
            ))
            for f in a["findings"]:
                elements.append(Paragraph(f"&nbsp;&nbsp;• {f}", small))
            elements.append(Paragraph(f"&nbsp;&nbsp;SHA-256: {a['sha256']}", small))

    elements.append(PageBreak())
    elements.append(Paragraph("Reporting Guidance", h2))
    elements.append(Paragraph(
        "This report package is intended to support a human-reviewed submission to the "
        "National Cyber Crime Reporting Portal's 'Report Suspect' facility (which accepts "
        "identifiers such as email IDs and website URLs, along with supporting evidence). "
        "MailTrace AI does not file complaints automatically.",
        body,
    ))
    elements.append(Paragraph(
        f"Evidence integrity hash (SHA-256): {case.get('evidence_hash', '')}", small
    ))

    doc.build(elements)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Feature 4 — Legal-Grade Automation
# ---------------------------------------------------------------------------

# app/templates/ (sibling of app/services/ where this file lives)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

_JURISDICTION_TEMPLATES = {
    "us": "legal_report_us.html",
    "eu": "legal_report_eu.html",
}


def _sign_pdf_bytes(pdf_bytes: bytes) -> bytes:
    """
    Applies a chain-of-custody digital signature to an already-rendered
    PDF. On any signing failure, logs a warning and returns the original
    unsigned PDF rather than blocking report delivery — an unsigned legal
    report is still useful to a human reviewer; a hard 500 error is not.
    """
    try:
        cert_generator.ensure_certs_exist()

        signer = signers.SimpleSigner.load(
            key_file=settings.CUSTODY_KEY_PATH,
            cert_file=settings.CUSTODY_CERT_PATH,
            key_passphrase=None,
        )

        writer = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
        output_buf = io.BytesIO()
        signers.sign_pdf(
            writer,
            signers.PdfSignatureMetadata(field_name="MailTraceEvidenceSignature"),
            signer=signer,
            output=output_buf,
        )
        return output_buf.getvalue()

    except Exception as exc:
        logger.warning("Could not digitally sign legal report PDF: %s", exc)
        return pdf_bytes


def generate_legal_report_pdf(case: dict, jurisdiction: str, custody_log: list[dict]) -> bytes:
    """
    Renders a jurisdiction-specific legal report and digitally signs it.

    Args:
        case: same shape as generate_case_report_pdf's `case` dict.
        jurisdiction: "us" or "eu" (case-insensitive).
        custody_log: list of {action, evidence_hash, timestamp, user_id}
            dicts, typically from chain_of_custody.get_custody_log(db, case_id).

    Raises:
        ValueError: if jurisdiction isn't one of the known templates.
        RuntimeError: if the HTML-to-PDF conversion itself fails.
    """
    template_name = _JURISDICTION_TEMPLATES.get(jurisdiction.lower())
    if not template_name:
        raise ValueError(
            f"Unknown jurisdiction '{jurisdiction}'. Expected one of: {list(_JURISDICTION_TEMPLATES)}"
        )

    template = _jinja_env.get_template(template_name)
    html = template.render(case=case, custody_log=custody_log)

    pdf_buf = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=pdf_buf)
    if result.err:
        raise RuntimeError(f"Failed to render legal report PDF for jurisdiction '{jurisdiction}'")

    unsigned_pdf = pdf_buf.getvalue()
    return _sign_pdf_bytes(unsigned_pdf)