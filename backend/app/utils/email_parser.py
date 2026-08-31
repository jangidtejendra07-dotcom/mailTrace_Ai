"""
Parses raw .eml bytes into a structured dict: headers, plaintext body,
HTML body, URLs found in the body, and attachment metadata (without
writing attachments to disk except transient hashing).
"""
import re
import hashlib
from email import message_from_bytes
from email.policy import default as default_policy
from email.utils import getaddresses, parseaddr

URL_REGEX = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)


def parse_eml(raw_bytes: bytes) -> dict:
    msg = message_from_bytes(raw_bytes, policy=default_policy)

    headers = {}
    for key in msg.keys():
        # collapse multiple same-name headers (e.g. Received) into a list
        values = msg.get_all(key) or []
        headers[key] = values if len(values) > 1 else values[0]

    subject = msg.get("Subject", "") or ""
    from_header = msg.get("From", "") or ""
    reply_to = msg.get("Reply-To", "") or ""
    return_path = msg.get("Return-Path", "") or ""
    message_id = msg.get("Message-ID", "") or ""
    received = msg.get_all("Received", []) or []
    auth_results = msg.get("Authentication-Results", "") or ""
    dkim_sig = msg.get("DKIM-Signature", "") or ""
    to_header = msg.get("To", "") or ""

    plain_body, html_body = "", ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition") or "")
            content_type = part.get_content_type()
            filename = part.get_filename()

            if filename:
                payload = part.get_payload(decode=True) or b""
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest() if payload else None,
                    "magic_bytes": payload[:8].hex() if payload else "",
                })
                continue

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    plain_body += part.get_content()
                except Exception:
                    pass
            elif content_type == "text/html" and "attachment" not in content_disposition:
                try:
                    html_body += part.get_content()
                except Exception:
                    pass
    else:
        content_type = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            content = ""
        if content_type == "text/html":
            html_body = content
        else:
            plain_body = content

    body_for_urls = plain_body + " " + re.sub(r"<[^>]+>", " ", html_body)
    urls = sorted(set(URL_REGEX.findall(body_for_urls)))

    from_name, from_addr = parseaddr(from_header)
    reply_name, reply_addr = parseaddr(reply_to)

    return {
        "headers": headers,
        "subject": subject,
        "from_header": from_header,
        "from_address": from_addr.lower(),
        "from_name": from_name,
        "reply_to_header": reply_to,
        "reply_to_address": reply_addr.lower() if reply_addr else "",
        "to_header": to_header,
        "return_path": return_path,
        "message_id": message_id,
        "received_headers": received if isinstance(received, list) else [received],
        "authentication_results": auth_results,
        "dkim_signature_present": bool(dkim_sig),
        "plain_body": plain_body.strip(),
        "html_body": html_body.strip(),
        "urls": urls,
        "attachments": attachments,
        "raw_size_bytes": len(raw_bytes),
    }
