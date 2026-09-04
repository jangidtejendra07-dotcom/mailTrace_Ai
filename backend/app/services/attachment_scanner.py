import zipfile
import io
import math

DANGEROUS_EXTENSIONS = {
    "exe", "scr", "bat", "cmd", "com", "pif", "vbs", "vbe", "js", "jse",
    "wsf", "wsh", "msi", "msp", "jar", "ps1", "reg", "hta", "cpl", "dll",
}

MACRO_EXTENSIONS = {"docm", "xlsm", "pptm", "dotm", "xltm", "potm"}
RISKY_ARCHIVE_EXTENSIONS = {"zip", "7z", "rar", "iso", "img"}

# Suspicious keywords to look for inside text/script/macro files
SUSPICIOUS_KEYWORDS = [
    "powershell", "wscript.shell", "cmd.exe", "invoke-expression", 
    "iex", "downloadstring", "base64", "eval(", "shellexecute"
]

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
    return filename.lower().split(".")[1:] if "." in filename else []


def _calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy to detect packed or encrypted payloads."""
    if not data:
        return 0.0
    entropy = 0
    length = len(data)
    frequencies = {byte: data.count(byte) for byte in set(data)}
    for count in frequencies.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    return entropy


def _inspect_archive_contents(file_bytes: bytes) -> list[str]:
    """Extracts and inspects files inside a ZIP archive for dangerous payloads."""
    archive_findings = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            namelist = zf.namelist()
            archive_findings.append(f"Archive contains {len(namelist)} inner file(s)")
            for inner_name in namelist:
                inner_ext = _extensions(inner_name)[-1] if _extensions(inner_name) else ""
                if inner_ext in DANGEROUS_EXTENSIONS:
                    archive_findings.append(f"MALICIOUS INNER FILE DETECTED: '{inner_name}' inside archive!")
                # Read inner content sample to check for malicious keywords
                try:
                    with zf.open(inner_name) as inner_file:
                        sample_data = inner_file.read(2048).decode("utf-8", errors="ignore").lower()
                        for kw in SUSPICIOUS_KEYWORDS:
                            if kw in sample_data:
                                archive_findings.append(f"Suspicious keyword '{kw}' found inside archived file '{inner_name}'")
                except Exception:
                    pass
    except Exception:
        archive_findings.append("Could not parse or inspect archive contents (possibly encrypted or corrupt)")
    return archive_findings


def scan_attachment(att: dict) -> dict:
    filename = att.get("filename") or "unknown"
    exts = _extensions(filename)
    final_ext = exts[-1] if exts else ""
    magic_hex = (att.get("magic_bytes", "")).lower()
    file_bytes = att.get("file_bytes", b"")  # Raw bytes if passed from backend

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

    # 1. Structural Checks
    if double_extension:
        findings.append(f"Double extension detected ({'.'.join(exts[-2:])}) — disguised executable pattern")
        severity, score = "CRITICAL", 100

    elif final_ext in DANGEROUS_EXTENSIONS:
        findings.append(f"Dangerous executable extension: .{final_ext}")
        severity, score = "CRITICAL", 95

    elif final_ext in MACRO_EXTENSIONS:
        findings.append(f"Macro-enabled Office document: .{final_ext} (may contain malicious macros)")
        severity, score = "HIGH", 70

    elif final_ext in RISKY_ARCHIVE_EXTENSIONS:
        findings.append(f"Archive/disk-image attachment (.{final_ext})")
        severity, score = "MEDIUM", 45
        # ADVANCED: Deep inspection of archive inner files
        if file_bytes:
            archive_results = _inspect_archive_contents(file_bytes)
            findings.extend(archive_results)
            if any("MALICIOUS INNER FILE" in f or "Suspicious keyword" in f for f in archive_results):
                severity, score = "CRITICAL", 100

    # 2. Deep Content & Keyword Analysis for Scripts / Text files
    if file_bytes and final_ext in {"js", "vbs", "ps1", "bat", "txt"}:
        text_content = file_bytes.decode("utf-8", errors="ignore").lower()
        for kw in SUSPICIOUS_KEYWORDS:
            if kw in text_content:
                findings.append(f"Suspicious payload keyword '{kw}' found inside script content")
                severity, score = "CRITICAL", 90

    # 3. Entropy Check for packed payloads
    if file_bytes:
        entropy = _calculate_entropy(file_bytes)
        if entropy > 7.2 and final_ext not in RISKY_ARCHIVE_EXTENSIONS:
            findings.append(f"High file entropy ({entropy:.2f}) detected — file may be packed, encrypted, or obfuscated malware")
            if score < 75:
                severity, score = "HIGH", 75

    # Type mismatch check
    if detected_type and "executable" in detected_type.lower() and final_ext not in DANGEROUS_EXTENSIONS:
        findings.append(f"CRITICAL TYPE MISMATCH: extension '.{final_ext}' but binary signature indicates {detected_type}")
        severity, score = "CRITICAL", 100

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