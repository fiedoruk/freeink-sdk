"""Loopback TLS fixture against the actual SDK SecureClient and pinned wolfSSL."""
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

NOW = datetime.now(timezone.utc)

def issue(cn, issuer_key=None, issuer_cert=None, san=None, start=None, end=None, ca=False):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    start = start or NOW - timedelta(days=2)
    end = end or NOW + timedelta(days=2)
    builder = (x509.CertificateBuilder().subject_name(name)
               .issuer_name(issuer_cert.subject if issuer_cert else name)
               .public_key(key.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(start).not_valid_after(end)
               .add_extension(x509.BasicConstraints(ca=ca, path_length=1 if ca else None), critical=True))
    if ca:
        builder = builder.add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
    if san:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
    if not ca:
        builder = builder.add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    cert = builder.sign(issuer_key or key, hashes.SHA256())
    return key, cert

def pem_cert(cert): return cert.public_bytes(serialization.Encoding.PEM)
def pem_key(key):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                             serialization.NoEncryption())

