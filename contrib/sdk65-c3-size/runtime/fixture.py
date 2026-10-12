#!/usr/bin/env python3
"""Synthetic TLS endpoints. Bind locally by default; use --bind for an authorized bench."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import socket
import ssl
import threading
import time
from certificates import issue, pem_cert, pem_key

class Endpoint:
    def __init__(self, directory, name, cert, key, version=None, bind='127.0.0.1', log=None):
        self.name, self.mode, self.log = name, version, log
        self.requests, self.accepts, self.versions = [], 0, []
        self.lock = threading.Lock()
        self.shutdown = threading.Event()
        self.workers = []
        self.listener = socket.socket()
        self.listener.bind((bind, 0))
        self.port = self.listener.getsockname()[1]
        self.listener.listen(8)
        self.listener.settimeout(.1)
        self.context = None
        if version is not None:
            cp, kp = directory / (name + '.pem'), directory / (name + '.key')
            cp.write_bytes(pem_cert(cert)); kp.write_bytes(pem_key(key)); kp.chmod(0o600)
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.context.minimum_version = version
            self.context.maximum_version = version
            self.context.load_cert_chain(str(cp), str(kp))
        self.thread = threading.Thread(target=self.accept, daemon=True)

    def accept(self):
        while not self.shutdown.is_set():
            try:
                peer, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.accepts += 1
            worker = threading.Thread(target=self.handle, args=(peer,), daemon=True)
            self.workers.append(worker); worker.start()

    def handle(self, raw):
        try:
            raw.settimeout(5)
            if self.name == 'drop':
                return
            if self.name == 'stall':
                self.shutdown.wait(5)
                return
            with self.context.wrap_socket(raw, server_side=True) as peer:
                self.versions.append(peer.version())
                data = bytearray()
                while len(data) < 512 and b'\r\n\r\n' not in data:
                    chunk = peer.recv(512 - len(data))
                    if not chunk:
                        break
                    data.extend(chunk)
                if b'G10_PROTECTED' in data:
                    first = bytes(data).split(b'\r\n', 1)[0].decode('ascii', errors='strict')
                    with self.lock:
                        self.requests.append(first)
                        if self.log:
                            with self.log.open('a') as out:
                                out.write(json.dumps({'endpoint': self.name, 'request': first, 'tls': peer.version()}) + '\n')
                    peer.sendall(b'HTTP/1.1 200 Fixture\r\nContent-Length: 6\r\nConnection: close\r\n\r\nG10_OK')
        except (OSError, ssl.SSLError, UnicodeError):
            pass
        finally:
            raw.close()

    def __enter__(self):
        self.thread.start(); return self
    def __exit__(self, *_):
        self.shutdown.set(); self.listener.close(); self.thread.join(2)
        for worker in self.workers:
            worker.join(6)
        if self.thread.is_alive() or any(w.is_alive() for w in self.workers):
            raise RuntimeError('Fixture did not stop')

class Fixture:
    def __init__(self, directory, host='127.0.0.1', bind='127.0.0.1'):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)
        self.directory.chmod(0o700)
        root_key, root = issue('G10 test CA', ca=True)
        _, unknown = issue('G10 unknown CA', ca=True)
        key, cert = issue('G10 leaf', root_key, root, san=host)
        wrong_key, wrong = issue('G10 wrong host', root_key, root, san='wrong.invalid')
        self.root, self.unknown = pem_cert(root), pem_cert(unknown)
        (self.directory / 'root.pem').write_bytes(self.root)
        (self.directory / 'unknown.pem').write_bytes(self.unknown)
        self.endpoints = {
            'tls12': Endpoint(self.directory, 'tls12', cert, key, ssl.TLSVersion.TLSv1_2, bind),
            'tls13': Endpoint(self.directory, 'tls13', cert, key, ssl.TLSVersion.TLSv1_3, bind),
            'wronghost': Endpoint(self.directory, 'wronghost', wrong, wrong_key, ssl.TLSVersion.TLSv1_2, bind),
            'stall': Endpoint(self.directory, 'stall', None, None, bind=bind),
            'drop': Endpoint(self.directory, 'drop', None, None, bind=bind)}
        self.stack = ExitStack()
        self.host = host
        self.epoch = int(time.time())
        self.info = {'cert_algorithm': 'ECDSA P-256/SHA256', 'chain_length': 1,
                     'root_sha256': __import__('hashlib').sha256(self.root).hexdigest(),
                     'leaf_sha256': __import__('hashlib').sha256(pem_cert(cert)).hexdigest(),
                     'supported_versions': ['TLSv1.2', 'TLSv1.3'], 'epoch': self.epoch}
        (self.directory / 'fixture.json').write_text(json.dumps(self.info, indent=2) + '\n')

    def __enter__(self):
        for endpoint in self.endpoints.values():
            self.stack.enter_context(endpoint)
        return self
    def __exit__(self, *exception):
        return self.stack.__exit__(*exception)
    def config(self, context='early_boot'):
        lines = [f'context={context}', f'host={self.host}', 'ssid=REPLACE_LOCALLY', 'password=REPLACE_LOCALLY', f'epoch={self.epoch}']
        lines += [f'{name}={endpoint.port}' for name, endpoint in self.endpoints.items()]
        return '\n'.join(lines) + '\n'
    def snapshot(self):
        return {name: {'accepts': e.accepts, 'protected_requests': list(e.requests), 'versions': e.versions}
                for name, e in self.endpoints.items()}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--bind', default='127.0.0.1')
    p.add_argument('--context', choices=['early_boot', 'reader_ui'], default='early_boot')
    a = p.parse_args()
    with Fixture(a.directory, a.host, a.bind) as fixture:
        (a.directory / 'probe.conf').write_text(fixture.config(a.context))
        for e in fixture.endpoints.values():
            e.log = a.directory / 'requests.jsonl'
        print('Fixture ready. Copy root.pem, unknown.pem and your edited probe.conf to /.crosspoint/g10/.')
        print('Press Ctrl-C to stop and write the server receipt.')
        try:
            while True:
                time.sleep(.25)
        except KeyboardInterrupt:
            pass
        finally:
            (a.directory / 'server-results.json').write_text(json.dumps(fixture.snapshot(), indent=2) + '\n')
