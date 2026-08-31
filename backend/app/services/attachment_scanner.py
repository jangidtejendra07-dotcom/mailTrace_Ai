"""
Section 5 — Attachment Risk Scanner.

Inspects filename, extension, MIME type and file-signature (magic bytes)
where feasible. Flags executables, macro-enabled Office files, double
extensions, and type mismatches.
"""

DANGEROUS_EXTENSIONS = {
    "exe", "scr", "bat", "cmd", "com", "pif", "vbs", "vbe", "js", "jse",
    "wsf", "wsh", "msi", "msp", "jar", "ps1", "reg", "hta", "cpl", "dll",
}

MACRO_EXTENSIONS = {"docm", "xlsm", "pptm", "dotm", "xltm", "potm"}

RISKY_ARCHIVE_EXTENSIONS = {"zip", "7z", "rar", "iso", "img"}

# Common file signatures (magic bytes, hex) to detect type mismatches
MAGIC_SIGNATURES = {
    "4d5a": "PE executable (Windows .exe/.dll)",
    "504b0304": "ZIP/Office Open XML container",
    "25504446": "PDF document",
    "d0cf11e0": "Legacy MS Office (OLE2) document",
    "7f454c46": "ELF executable (Linux)",
}

BENIGN_MAGIC_FOR_EXT = {
    "pdf": {"25504446"},
    "docx": {"504b0304"},
    "xlsx": {"504b0304"},
    "pptx": {"504b0304"},
    "doc": {"d0cf11e0"},
    "xls": {"d0cf11e0"},
    "zip": {"504b0304"},
}


def _extensions(filename: str) -> list[str]:
    # split all dot-separated segments to detect double extensions e.g. invoice.pdf.exe
    return filename.lower().split(".")[1:] if "." in filename else []


def _magic_hex(magic_bytes_hex: str) -> str:
    return (magic_bytes_hex or "").lower()


def scan_attachment(att: dict) -> dict:
    filename = att.get("filename") or "unknown"
    exts = _extensions(filename)
    final_ext = exts[-1] if exts else ""
    magic_hex = _magic_hex(att.get("magic_bytes", ""))

    findings = []
    severity = "LOW"
    score = 0

    detected_type = next(
        (label for sig, label in MAGIC_SIGNATURES.items() if magic_hex.startswith(sig)),
        None,
    )

    double_extension = len(exts) >= 2 and exts[-2] in {
        "pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "txt", "csv"
    } and final_ext in DANGEROUS_EXTENSIONS

    if double_extension:
        findings.append(
            f"Double extension detected ({'.'.join(exts[-2:])}) — disguised executable pattern"
        )
        severity, score = "CRITICAL", 100

    elif final_ext in DANGEROUS_EXTENSIONS:
        findings.append(f"Dangerous executable extension: .{final_ext}")
        severity, score = "CRITICAL", 95

    elif final_ext in MACRO_EXTENSIONS:
        findings.append(f"Macro-enabled Office document: .{final_ext} (may contain malicious macros)")
        severity, score = "HIGH", 70

    elif final_ext in RISKY_ARCHIVE_EXTENSIONS:
        findings.append(f"Archive/disk-image attachment (.{final_ext}) — contents not inspected, treat as elevated risk")
        severity, score = "MEDIUM", 45

    # Type mismatch: magic bytes say PE/executable but extension claims something benign
    if detected_type and "executable" in detected_type.lower() and final_ext not in DANGEROUS_EXTENSIONS:
        findings.append(
            f"CRITICAL TYPE MISMATCH: file extension '.{final_ext}' but binary signature indicates {detected_type}"
        )
        severity, score = "CRITICAL", 100

    expected_magics = BENIGN_MAGIC_FOR_EXT.get(final_ext)
    if expected_magics and magic_hex and not any(magic_hex.startswith(m) for m in expected_magics):
        findings.append(
            f"File signature does not match expected format for .{final_ext} extension"
        )
        if severity != "CRITICAL":
            severity, score = "HIGH", max(score, 75)

    if not findings:
        findings.append("No known risk indicators found for this attachment")
        severity, score = "LOW", 5

    return {
        "filename": filename,
        "extension": final_ext,
        "content_type": att.get("content_type"),
        "size_bytes": att.get("size_bytes"),
        "sha256": att.get("sha256"),
        "detected_file_type": detected_type,
        "double_extension": double_extension,
        "severity": severity,
        "score": score,
        "findings": findings,
    }


def scan_attachments(attachments: list[dict]) -> dict:
    if not attachments:
        return {"score": 0, "severity": "LOW", "items": [], "summary": "No attachments present"}

    results = [scan_attachment(a) for a in attachments]
    max_score = max(r["score"] for r in results)
    worst = max(results, key=lambda r: r["score"])

    return {
        "score": max_score,
        "severity": worst["severity"],
        "items": results,
        "summary": f"{len(results)} attachment(s) scanned; highest severity: {worst['severity']} ({worst['filename']})",
    }
