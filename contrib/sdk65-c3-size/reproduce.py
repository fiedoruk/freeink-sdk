#!/usr/bin/env python3
"""Reconstruct a pinned C3 size comparison; firmware builds are opt-in."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
parser.add_argument("--build", action="store_true")
parser.add_argument("--pio", default="pio")
args = parser.parse_args()
out = args.destination.resolve()
out.mkdir()
lock = json.loads((HERE / "source-lock.json").read_text())
for name, expected in lock["patches"].items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected
cp = out / "crosspoint"
sdk = cp / "freeink-sdk"

def run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True)

for name, repo in (("cp", cp), ("sdk", sdk)):
    repo.mkdir(exist_ok=True)
    run(["git", "init", "-q"], repo)
    run(["git", "fetch", "--quiet", "--depth=1", lock[name]["url"], lock[name]["commit"]], repo)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], repo)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip() == lock[name]["commit"]
run(["git", "apply", "--check", str(HERE / "subdir-guards.patch")], cp)
run(["git", "apply", str(HERE / "subdir-guards.patch")], cp)
assert hashlib.sha256((cp / "src/activities/plugins/PluginCatalogActivity.cpp").read_bytes()).hexdigest() == lock["cpResultSha256"]
client = sdk / "libs/network/SecureNet/src/SecureClient.cpp"
assert hashlib.sha256(client.read_bytes()).hexdigest() == lock["sdkBeforeSha256"]

def build(label):
    target = out / label
    target.mkdir()
    start = time.monotonic()
    build_env = dict(os.environ, PLATFORMIO_RUN_JOBS="2")
    with (target / "build.log").open("w") as log:
        subprocess.run(["nice", "-n", "10", args.pio, "run", "-e", lock["target"], "-j2"],
                       cwd=cp, env=build_env, stdout=log, stderr=subprocess.STDOUT, check=True)
    log = (target / "build.log").read_text(errors="replace")
    sizes = {}
    for field in ("RAM", "Flash"):
        matches = re.findall(r"^" + field + r":.*\(used (\d+) bytes from (\d+) bytes\)", log, re.M)
        if not matches:
            raise RuntimeError("Missing size output: " + field)
        sizes[field] = int(matches[-1][0])
    for name in ("firmware.bin", "firmware.elf"):
        shutil.copyfile(cp / ".pio/build" / lock["target"] / name, target / name)
    return {"sizes": sizes, "wallSeconds": round(time.monotonic() - start, 3)}

results = {}
if args.build:
    results["baseline"] = build("baseline")
run(["git", "apply", "--check", str(HERE / "sdk65-compatible.patch")], sdk)
run(["git", "apply", str(HERE / "sdk65-compatible.patch")], sdk)
assert hashlib.sha256(client.read_bytes()).hexdigest() == lock["sdkAfterSha256"]
run(["git", "diff", "--check"], cp)
run(["git", "diff", "--check"], sdk)
if args.build:
    results["verified"] = build("verified")
    results["deltaBytes"] = {key: results["verified"]["sizes"][key] - results["baseline"]["sizes"][key]
                             for key in ("RAM", "Flash")}
receipt = {"sourceReconstruction": "PASS", "build": "PASS" if args.build else "NOT_RUN",
           "results": results, "target": lock["target"], "device": "NOT_MEASURED"}
(out / "reproduction.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
