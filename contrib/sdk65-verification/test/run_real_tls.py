"""Loopback TLS fixture against the actual SDK SecureClient and pinned wolfSSL."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import socket
import ssl
import subprocess
import tempfile
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

HERE = Path(__file__).resolve().parent
EXE = HERE.parent / "build/secure_client_real_tls"
NOW = datetime.now(timezone.utc)
parser = argparse.ArgumentParser()
parser.add_argument("--exe", type=Path, default=EXE)
parser.add_argument("--negative-control", action="store_true")
args = parser.parse_args()

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

class LoopbackTLS:
    def __init__(self, cert_path, key_path, tls13=False):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(3)
        self.listener.settimeout(0.15)
        self.port = self.listener.getsockname()[1]
        self.data = bytearray()
        self.handshakes = 0
        self.versions = []
        self.stop = threading.Event()
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.minimum_version = ssl.TLSVersion.TLSv1_3 if tls13 else ssl.TLSVersion.TLSv1_2
        self.ctx.maximum_version = self.ctx.minimum_version
        self.ctx.load_cert_chain(str(cert_path), str(key_path))
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            try: raw, _ = self.listener.accept()
            except socket.timeout: continue
            try:
                raw.settimeout(2)
                with self.ctx.wrap_socket(raw, server_side=True) as peer:
                    self.handshakes += 1
                    self.versions.append(peer.version())
                    try:
                        peer.settimeout(0.3)
                        while len(self.data) < 4096 and b"\r\n\r\n" not in self.data:
                            data = peer.recv(4096 - len(self.data))
                            if not data: break
                            self.data.extend(data)
                        if self.data: peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                    except (OSError, ssl.SSLError): pass
            except (OSError, ssl.SSLError):
                raw.close()

    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=3)
        self.listener.close()

class StallServer:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(0.15)
        self.port = self.listener.getsockname()[1]
        self.stop = threading.Event()
        self.data = bytearray()
        self.thread = threading.Thread(target=self.run, daemon=True)
    def run(self):
        try:
            peer, _ = self.listener.accept()
            peer.settimeout(0.1)
            with peer:
                while not self.stop.is_set():
                    try: self.data.extend(peer.recv(4096))
                    except socket.timeout: pass
        except (OSError, socket.timeout): pass
    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *_):
        self.stop.set(); self.thread.join(timeout=2); self.listener.close()

def write(path, data): path.write_bytes(data); return path

def main():
    root_key, root = issue("Test root", ca=True)
    other_key, other = issue("Other root", ca=True)
    intermediate_key, intermediate = issue("Test intermediate", root_key, root, ca=True)
    cases = [
        ("valid_ca_san", "good.test", root, root_key, "good.test", None, None, None, True),
        ("valid_tls13", "good.test", root, root_key, "good.test", None, None, None, True),
        ("wrong_hostname_same_ca", "good.test", root, root_key, "wrong.test", None, None, None, False),
        ("wrong_hostname_tls13", "good.test", root, root_key, "wrong.test", None, None, None, False),
        ("unknown_ca", "good.test", root, root_key, "good.test", None, None, other, False),
        ("malformed_ca", "good.test", root, root_key, "good.test", None, None, b"not PEM\n", False),
        ("expired", "good.test", root, root_key, "good.test", NOW-timedelta(days=10), NOW-timedelta(days=2), None, False),
        ("not_yet_valid", "good.test", root, root_key, "good.test", NOW+timedelta(days=2), NOW+timedelta(days=10), None, False),
        ("full_intermediate_chain", "good.test", intermediate, intermediate_key, "good.test", None, None, None, True),
        ("incomplete_chain", "good.test", intermediate, intermediate_key, "good.test", None, None, None, False),
        ("legacy_insecure", "good.test", root, root_key, "wrong.test", None, None, None, True),
    ]
    if args.negative_control:
        cases = [row for row in cases if row[0] == "wrong_hostname_same_ca"]
    results = []
    with tempfile.TemporaryDirectory(prefix="w06-real-tls-") as tmp:
        work = Path(tmp)
        for name, host, issuer, issuer_key, san, start, end, ca_override, expected in cases:
            leaf_key, leaf = issue("leaf", issuer_key, issuer, san, start, end)
            chain = pem_cert(leaf)
            if name == "full_intermediate_chain": chain += pem_cert(intermediate)
            cert_path = write(work / f"{name}.pem", chain)
            key_path = write(work / f"{name}.key", pem_key(leaf_key))
            ca_path = write(work / f"{name}.ca", ca_override if isinstance(ca_override, bytes)
                            else pem_cert(ca_override or root))
            with LoopbackTLS(cert_path, key_path, tls13=name.endswith("tls13")) as server:
                mode = "legacy" if name == "legacy_insecure" else "verified"
                proc = subprocess.run([str(args.exe), host, str(server.port), str(ca_path), mode],
                                      text=True, capture_output=True, timeout=12)
            has_token = b"TEST-ONLY-TOKEN" in server.data
            connected = "connected=1" in proc.stdout
            expected_here = True if args.negative_control else expected
            passed = proc.returncode == 0 and connected == expected_here and has_token == expected_here \
                     and "after_stop=0" in proc.stdout
            results.append({"case": name, "pass": passed, "connected": connected,
                            "server_handshakes": server.handshakes, "tls_versions": server.versions,
                            "protected_request_seen": has_token,
                            "stdout": proc.stdout.strip(), "stderr_tail": proc.stderr[-350:]})
        if not args.negative_control:
            leaf_key, leaf = issue("leaf", root_key, root, "wrong.test")
            cert_path = write(work / "switch.pem", pem_cert(leaf))
            key_path = write(work / "switch.key", pem_key(leaf_key))
            ca_path = write(work / "switch.ca", pem_cert(root))
            with LoopbackTLS(cert_path, key_path) as server:
                proc = subprocess.run([str(args.exe), "good.test", str(server.port), str(ca_path), "mode-switch"],
                                      text=True, capture_output=True, timeout=12)
            # Observation of an existing API trap, not an expected secure result:
            # SecureClient::setCACert does not reset the previous _insecure flag.
            observed = proc.returncode == 0 and "first=1 connected=1" in proc.stdout \
                       and b"TEST-ONLY-TOKEN" in server.data
            results.append({"case": "same_object_legacy_to_ca_observation", "pass": observed,
                            "connected": True, "protected_request_seen": b"TEST-ONLY-TOKEN" in server.data,
                            "expected_security": "should refuse wrong SAN after switching to CA",
                            "observed_risk": "setCACert retained previous setInsecure mode",
                            "stdout": proc.stdout.strip(), "stderr_tail": proc.stderr[-350:]})
            ca_path = write(work / "abort.ca", pem_cert(root))
            with StallServer() as server:
                proc = subprocess.run([str(args.exe), "good.test", str(server.port), str(ca_path), "abort"],
                                      text=True, capture_output=True, timeout=12)
            passed = proc.returncode == 0 and "connected=0" in proc.stdout and "aborted=1" in proc.stdout \
                     and "abort_polls=3" in proc.stdout and "after_stop=0" in proc.stdout \
                     and b"TEST-ONLY-TOKEN" not in server.data
            results.append({"case": "abort_during_handshake", "pass": passed,
                            "connected": False, "protected_request_seen": False,
                            "stdout": proc.stdout.strip(), "stderr_tail": proc.stderr[-350:]})
    print(json.dumps(results, indent=2))
    result_path = HERE.parent / ("negative-control-results.json" if args.negative_control else "real-tls-results.json")
    result_path.write_text(json.dumps(results, indent=2) + "\n")
    if not all(r["pass"] for r in results): raise SystemExit(1)

if __name__ == "__main__": main()
