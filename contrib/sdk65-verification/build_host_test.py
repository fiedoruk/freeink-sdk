"""Compile production SecureClient against the pinned real wolfSSL host archive."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--sdk-root", type=Path, required=True)
parser.add_argument("--wolf-root", type=Path, required=True)
args = parser.parse_args()
SDK = args.sdk_root.resolve()
WOLF = args.wolf_root.resolve() / "src"
SRC_REL = "libs/network/SecureNet/src/SecureClient.cpp"
SRC = SDK / SRC_REL
OUT = ROOT / "build"
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SDK, text=True).strip()
if head != "425d200a8ea447326b4b9696e4e47dc84ad9d7f6":
    raise SystemExit(f"SDK HEAD changed: {head}; re-review the patch and test before use")
FLAGS = ["-std=c++20", "-O0", "-w", "-DFREEINK_NET_WOLFSSL=1", "-DWOLFSSL_USER_SETTINGS",
         "-DWOLFSSL_OPTIONS_H", "-DWOLFSSL_CLIENT_EXAMPLE", "-DWOLFSSL_TLS13",
         "-DWOLFSSL_HAVE_SP_ECC", "-DWOLFSSL_SP_SMALL", "-DHAVE_CURVE25519", "-DHAVE_SNI",
         "-I", str(ROOT / "test/stubs"), "-I", str(SDK / "libs/network/SecureNet/include"),
         "-I", str(WOLF)]
raw = subprocess.run(["git", "show", f"HEAD:{SRC_REL}"], cwd=SDK, check=True, capture_output=True).stdout
raw_src = OUT / "raw-SecureClient.cpp"
raw_src.write_bytes(raw)
for label, source in (("compatible", SRC), ("raw", raw_src)):
    target = OUT / ("secure_client_real_tls" if label == "compatible" else "secure_client_raw_tls")
    subprocess.run(["nice", "-n", "10", "c++", *FLAGS, str(source),
                    str(ROOT / "test/secure_client_real_tls.cpp"), str(OUT / "libwolfssl-host.a"),
                    "-o", str(target)], check=True)
    print(f"{label} executable sha256={hashlib.sha256(target.read_bytes()).hexdigest()}")
subprocess.run(["nice", "-n", "10", "c++", *FLAGS, str(SRC), str(ROOT / "test/secure_http_redirect.cpp"),
                str(OUT / "libwolfssl-host.a"), "-o", str(OUT / "secure_http_redirect")], check=True)
meta = {"sdk_head": head,
        "compatible_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(), "compile_flags": FLAGS}
(ROOT / "host-test-build.json").write_text(json.dumps(meta, indent=2) + "\n")
