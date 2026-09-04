"""
Feature 4 — Self-signed certificate generator for chain-of-custody PDF
signing.

This is NOT a real legal signing certificate — it exists so legal report
PDFs carry a cryptographic signature proving the file wasn't altered
after MailTrace generated it (tamper-evidence, not legal notarization).
For a real deployment, replace with a CA-issued PEM certificate and point
CUSTODY_CERT_PATH / CUSTODY_KEY_PATH at it instead — no code change needed.

ensure_certs_exist() is safe to call on every startup and before every
signing operation: it's a no-op once the files are already on disk. This
matters because Render's filesystem is ephemeral between deploys, so the
cert regenerates automatically instead of needing a manual setup step.
"""
import datetime
import logging
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import settings

logger = logging.getLogger("mailtrace.cert_generator")


def ensure_certs_exist() -> None:
    cert_path = settings.CUSTODY_CERT_PATH
    key_path = settings.CUSTODY_KEY_PATH

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return

    cert_dir = os.path.dirname(cert_path) or "."
    os.makedirs(cert_dir, exist_ok=True)

    logger.info("Generating self-signed chain-of-custody certificate at %s", cert_path)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MailTrace AI (SIH 26106)"),
        x509.NameAttribute(NameOID.COMMON_NAME, "MailTrace AI Evidence Signing"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info("Chain-of-custody certificate generated successfully.")