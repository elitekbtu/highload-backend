from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERTS = ROOT / "certs"
CERTS.mkdir(exist_ok=True)


private_key = ec.generate_private_key(ec.SECP256R1())

subject = issuer = x509.Name(
    [
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ]
)

# Certificate
certificate = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(IPv4Address("127.0.0.1")),
            ]
        ),
        critical=False,
    )
    .sign(private_key, hashes.SHA256())
)

p12_data = pkcs12.serialize_key_and_certificates(
    name=b"practice",
    key=private_key,
    cert=certificate,
    cas=None,
    encryption_algorithm=serialization.BestAvailableEncryption(b"changeit"),
)

(CERTS / "keystore.p12").write_bytes(p12_data)
print(f"Wrote {CERTS / 'keystore.p12'}")

# pem key and cert

(CERTS / "key.pem").write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
(CERTS / "cert.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
print(f"Wrote {CERTS / 'cert.pem'} and {CERTS / 'key.pem'}")
