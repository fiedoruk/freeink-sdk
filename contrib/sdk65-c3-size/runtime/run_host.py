#!/usr/bin/env python3
"""Check production probe contracts and the actual SecureClient against real host TLS."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from fixture import Fixture
HERE = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cp', type=Path, required=True)
    p.add_argument('--wolf-root', type=Path, required=True)
    p.add_argument('--wolf-archive', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    started = time.monotonic()
    commands, results = [], []
    def run(command, **kwargs):
        begin = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, **kwargs)
        commands.append({'command': command, 'wall_seconds': round(time.monotonic()-begin, 3), 'exit': result.returncode})
        if result.returncode:
            raise RuntimeError(result.stderr[-3000:] or result.stdout[-3000:])
        return result
    with tempfile.TemporaryDirectory(prefix='g10-host-') as temporary:
        temp = Path(temporary)
        stub = HERE / 'host/stubs'
        run(['c++', '-std=c++20', '-fsanitize=address,undefined', '-I', str(stub), '-I', str(a.cp/'src/util'),
             str(HERE/'host/Contracts.cpp'), '-o', str(temp/'contracts')])
        run([str(temp/'contracts')])
        for flags in ([], ['-DCROSSPOINT_TLS_MEMORY_PROBE=1']):
            run(['c++', '-std=c++20', '-fsyntax-only', *flags, '-I', str(stub),
                 '-I', str(a.cp/'freeink-sdk/libs/network/SecureNet/include'),
                 str(a.cp/'src/util/TlsMemoryProbe.cpp')])
        flags = ['-std=c++20', '-O0', '-DFREEINK_NET_WOLFSSL=1', '-DWOLFSSL_USER_SETTINGS', '-DWOLFSSL_OPTIONS_H',
                 '-DWOLFSSL_CLIENT_EXAMPLE', '-DWOLFSSL_TLS13', '-DWOLFSSL_HAVE_SP_ECC', '-DWOLFSSL_SP_SMALL',
                 '-DHAVE_CURVE25519', '-DHAVE_SNI']
        for variant in ('probe', 'flag-off'):
            command = ['nice', '-n', '10', 'c++', *flags]
            if variant == 'probe':
                command += ['-DCROSSPOINT_TLS_MEMORY_PROBE=1']
            command += ['-I', str(stub), '-I', str(a.cp/'freeink-sdk/libs/network/SecureNet/include'),
                        '-I', str(a.wolf_root/'src'), str(a.cp/'freeink-sdk/libs/network/SecureNet/src/SecureClient.cpp'),
                        str(HERE/'host/NativeTls.cpp'), str(a.wolf_archive), '-o', str(temp/variant)]
            run(command)
        with Fixture(temp/'fixture') as fixture:
            root, unknown, malformed = temp/'root.pem', temp/'unknown.pem', temp/'malformed.pem'
            root.write_bytes(fixture.root); unknown.write_bytes(fixture.unknown); malformed.write_text('not a PEM certificate')
            matrix = [('tls12', 'tls12', root, 10), ('tls13', 'tls13', root, 10), ('wronghost', 'wronghost', root, 1),
                      ('unknownca', 'tls12', unknown, 1), ('malformedca', 'tls12', malformed, 1),
                      ('stall', 'stall', root, 1), ('abort', 'stall', root, 1), ('drop', 'drop', root, 1)]
            for variant in ('probe', 'flag-off'):
                for name, endpoint, ca, repetitions in matrix:
                    for repetition in range(1, repetitions+1):
                        server = fixture.endpoints[endpoint]
                        before = len(server.requests)
                        result = run([str(temp/variant), '127.0.0.1', str(server.port), str(ca),
                                      'abort' if name == 'abort' else 'none', name], timeout=6)
                        observed = json.loads(result.stdout)
                        success = name in ('tls12', 'tls13')
                        marker = len(server.requests) - before
                        passed = (observed['connected'] == success and observed['response_ok'] == success
                                  and marker == int(success) and observed['aborted'] == (name == 'abort'))
                        if variant == 'probe':
                            expected_attempts = 1 if success or name == 'abort' else 2
                            passed = passed and observed['attempts'] == expected_attempts
                            if name == 'stall':
                                passed = passed and observed['timeouts'] == 2 and observed['elapsed_ms'] >= 400
                            if name == 'malformedca':
                                passed = passed and observed['connect_calls'] == 0
                        item = {'variant': variant, 'case': name, 'repeat': repetition, 'pass': passed,
                                'protected_request_count': marker, 'observed': observed}
                        results.append(item)
                        if not passed:
                            raise RuntimeError(str(item))
            server_result = fixture.snapshot()
    result = {'status': 'PASS', 'cases': results, 'commands': commands,
              'wall_seconds': round(time.monotonic()-started, 3), 'heap': 'MOCK_CONTRACT_ONLY',
              'tls': 'actual pinned SecureClient/wolfSSL; POSIX transport, Python OpenSSL server',
              'device': 'NOT_MEASURED', 'archive_sha256': hashlib.sha256(a.wolf_archive.read_bytes()).hexdigest(),
              'server': server_result}
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(f'PASS: {len(results)} real TLS cases; production config and monitor contracts ASan/UBSan')
if __name__ == '__main__': main()
