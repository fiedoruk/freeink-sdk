"""Read actual SecureHttpClient default and opt-in cross-origin redirect behavior."""
from pathlib import Path
import json
import socket
import subprocess
import threading

EXE = Path(__file__).resolve().parents[1] / "build/secure_http_redirect"

class Server:
    def __init__(self, response):
        self.response = response
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.data = bytearray()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
    def run(self):
        while not self.stop.is_set():
            try: peer, _ = self.listener.accept()
            except socket.timeout: continue
            with peer:
                peer.settimeout(1)
                try:
                    while len(self.data) < 4096 and b"\r\n\r\n" not in self.data:
                        chunk = peer.recv(4096 - len(self.data))
                        if not chunk: break
                        self.data.extend(chunk)
                    peer.sendall(self.response)
                except OSError: pass
            break
    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *_):
        self.stop.set(); self.thread.join(timeout=2); self.listener.close()

results = []
for follow in (0, 1):
    with Server(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK") as target:
        location = f"http://second.test:{target.port}/final"
        response = (f"HTTP/1.1 302 Found\r\nLocation: {location}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").encode()
        with Server(response) as first:
            proc = subprocess.run([str(EXE), f"http://first.test:{first.port}/start", str(follow)],
                                  capture_output=True, text=True, timeout=8)
    first_token = b"TEST-ONLY-TOKEN" in first.data
    second_token = b"TEST-ONLY-TOKEN" in target.data
    expected_status = 302 if not follow else 200
    passed = proc.returncode == 0 and f"status={expected_status}" in proc.stdout \
             and first_token and second_token == bool(follow)
    results.append({"follow_hops": follow, "pass": passed, "first_token": first_token,
                    "second_origin_token": second_token, "status": proc.stdout.strip(),
                    "stderr_tail": proc.stderr[-350:]})
output = Path(__file__).resolve().parents[1] / "redirect-results.json"
output.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
if not all(r["pass"] for r in results): raise SystemExit(1)
