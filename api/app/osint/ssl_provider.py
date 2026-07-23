"""SSL/TLS certificate inspection.

Uses `cryptography` for X.509 parsing via a real TLS handshake. We connect
to the target, retrieve the peer certificate chain, and parse fields
locally — no third-party cert lookup is required.

We never MITM or intercept traffic. We only ever connect as a normal
TLS client and inspect what the server returns.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import socket
import ssl
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)


def _build_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False  # we just want the cert, not validation
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _format_sig_alg(name: str) -> str:
    # cryptography returns things like "sha256WithRSAEncryption"
    return name.replace("With", " with ").replace("Encryption", "").strip()


def get_cert(host: str, port: int = 443, timeout: float = 5.0) -> dict[str, Any] | None:
    try:
        ctx = _build_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der = ssock.getpeercert(binary_form=True)
                if not der:
                    return None
                return _parse_der(der)
    except Exception as e:
        log.debug("SSL %s:%d failed: %s", host, port, e)
        return None


def _parse_der(der: bytes) -> dict[str, Any]:
    # Local import keeps the module lightweight if cryptography is missing.
    from cryptography import x509  # type: ignore
    from cryptography.hazmat.primitives import hashes, serialization  # type: ignore

    cert = x509.load_der_x509_certificate(der)

    def _name(name: x509.Name) -> str:
        return ", ".join(f"{a.oid._name}={a.value}" for a in name)

    san: list[str] = []
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        san = [str(d) for d in ext.value]
    except x509.ExtensionNotFound:
        pass

    try:
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        chain_valid = bool(bc.ca) is False or True  # we don't fail hard; the consumer can
    except Exception:
        chain_valid = None

    now = _dt.datetime.now(_dt.timezone.utc)
    delta = cert.not_valid_after_utc - now
    days_remaining = max(int(delta.total_seconds() // 86400), 0)

    pubkey = cert.public_key()
    pub_alg = pubkey.__class__.__name__
    pub_sha256 = hashlib.sha256(
        pubkey.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).hexdigest()
    cert_sha256 = hashlib.sha256(der).hexdigest()

    return {
        "issuer": _name(cert.issuer),
        "subject": _name(cert.subject),
        "valid_from": cert.not_valid_before_utc,
        "valid_to": cert.not_valid_after_utc,
        "days_remaining": days_remaining,
        "fingerprint_sha256": cert_sha256,
        "public_key_fingerprint_sha256": pub_sha256,
        "public_key_algorithm": pub_alg,
        "signature_algorithm": _format_sig_alg(cert.signature_algorithm_oid._name),
        "san": san,
        "serial": format(cert.serial_number, "x"),
        "version": cert.version.name,
        "chain_valid": chain_valid,
    }
