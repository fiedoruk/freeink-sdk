"""Build the pinned Arduino-wolfSSL 5.7.2 C sources for a POSIX host test.

This host variant keeps the relevant TLS/verification flags from platformio.ini.
It omits ESP-specific hardware acceleration and does not model device heap.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--wolf-root", type=Path, required=True, help="Arduino-wolfSSL 5.7.2 package root")
args = parser.parse_args()
WOLF = args.wolf_root.resolve()
SRC = WOLF / "src"
package = json.loads((WOLF / "library.json").read_text())
if package.get("version") != "5.7.2":
    raise SystemExit("expected Arduino-wolfSSL 5.7.2")
OUT = ROOT / "build"
OUT.mkdir(exist_ok=True)
FLAGS = ["-std=c99", "-O0", "-w", "-DWOLFSSL_USER_SETTINGS", "-DWOLFSSL_OPTIONS_H",
         "-DWOLFSSL_CLIENT_EXAMPLE", "-DWOLFSSL_TLS13", "-DWOLFSSL_HAVE_SP_ECC",
         "-DWOLFSSL_SP_SMALL", "-DHAVE_CURVE25519", "-DHAVE_SNI", "-I", str(SRC)]
sources = sorted((SRC / "src").glob("*.c")) + sorted((SRC / "wolfcrypt/src").glob("*.c"))
started = time.monotonic()

def compile_one(path):
    obj = OUT / (path.parent.parent.name + "-" + path.stem + ".o")
    result = subprocess.run(["nice", "-n", "10", "cc", *FLAGS, "-c", str(path), "-o", str(obj)],
                            text=True, capture_output=True)
    return path.name, obj, result

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(compile_one, sources))
errors = [(name, result.stderr[-3500:]) for name, _, result in results if result.returncode]
if errors:
    for name, err in errors[:8]:
        print(name, err, file=sys.stderr)
    print(f"FAILED {len(errors)}/{len(sources)} files", file=sys.stderr)
    sys.exit(1)
archive = OUT / "libwolfssl-host.a"
subprocess.run(["ar", "rcs", str(archive), *(str(obj) for _, obj, _ in results)], check=True)
meta = {"library": "Arduino-wolfSSL 5.7.2", "sources": len(sources),
        "flags": FLAGS, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "elapsed_s": round(time.monotonic() - started, 3),
        "user_settings_sha256": hashlib.sha256((SRC / "user_settings.h").read_bytes()).hexdigest()}
(ROOT / "wolfssl-host-build.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta))
