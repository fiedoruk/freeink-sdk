#!/usr/bin/env python3
"""Validate complete paired probe logs without interpreting synthetic heap as C3 evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

GOOD = {'tls12', 'tls13'}
CASES = GOOD | {'wronghost', 'unknownca', 'malformedca', 'stall', 'abort', 'drop'}
CONTEXTS = {'early_boot', 'reader_ui'}
EXPECTED = {(case, repeat) for case in GOOD for repeat in range(1, 11)} | {(case, 1) for case in CASES-GOOD}

def load_logs(paths):
    records, metadata = [], []
    ends = 0
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if line.startswith('G10_ERROR'):
                raise ValueError('Probe reported an error')
            if line.startswith('G10_META '):
                metadata.append(json.loads(line[9:]))
            elif line.startswith('G10 '):
                records.append(json.loads(line[4:]))
            elif line == 'G10_END':
                ends += 1
    if ends != 2:
        raise ValueError('Expected exactly two completed context runs')
    return records, metadata

def validate(records, metadata, server, identity, fixture):
    if len(metadata) != 2 or {m.get('context') for m in metadata} != CONTEXTS:
        raise ValueError('Missing or duplicate context metadata')
    seen = {context: set() for context in CONTEXTS}
    requests = Counter()
    for endpoint in server.values():
        requests.update(endpoint['protected_requests'])
    expected_requests = Counter()
    for row in records:
        context, case, repeat = row['context'], row['case'], row['repeat']
        if context not in CONTEXTS or case not in CASES or (case, repeat) not in EXPECTED:
            raise ValueError('Unknown context/case/repetition')
        if (case, repeat) in seen[context]:
            raise ValueError('Duplicate case')
        seen[context].add((case, repeat))
        if row['schema'] != 1 or row['monitor_start'] != 0 or row['monitor_stop'] != 0 or row['monitor_stop_called'] is not True:
            raise ValueError('Allocator window was not owned and stopped successfully')
        for field in ['window_min', 'lifetime_before', 'lifetime_after', 'sampled_free', 'sampled_largest',
                      'attempts', 'connect_calls', 'timeouts', 'connect_ms', 'total_ms', 'written', 'received', 'cpu_mhz']:
            value = row[field]
            if type(value) is not int or value < 0 or value > 4294967295:
                raise ValueError('Invalid numeric measurement: '+field)
        for field in ['before', 'connect', 'response', 'stop']:
            pair = row[field]
            if len(pair) != 2 or any(type(v) is not int or v < 0 or v > 4294967295 for v in pair) or pair[1] > pair[0]:
                raise ValueError('Invalid heap sample')
        success = case in GOOD
        if row['connected'] is not success or row['response_ok'] is not success or row['aborted'] is not (case == 'abort'):
            raise ValueError('Unexpected transport result')
        if success:
            if row['written'] == 0 or row['received'] == 0 or row['tls'] != ('TLSv1.2' if case == 'tls12' else 'TLSv1.3'):
                raise ValueError('Missing verified response or wrong TLS version')
            expected_requests[f'GET /G10_PROTECTED/{case}/{repeat} HTTP/1.1'] += 1
        elif row['written'] != 0 or row['received'] != 0:
            raise ValueError('Protected request sent after failed connect')
        if row['attempts'] != (1 if success or case == 'abort' else 2):
            raise ValueError('Unexpected retry count')
        if case == 'stall' and (row['timeouts'] != 2 or row['connect_ms'] < 4000):
            raise ValueError('Stall did not exercise both timeout windows')
        if case == 'abort' and (row['connect_calls'] == 0 or row['connect_ms'] < 100 or row['connect_ms'] >= 2000):
            raise ValueError('Abort was not observed in a pending handshake')
        if case == 'malformedca' and row['connect_calls'] != 0:
            raise ValueError('Malformed CA reached handshake')
        if row['total_ms'] < row['connect_ms']:
            raise ValueError('Impossible elapsed time')
    if any(cases != EXPECTED for cases in seen.values()):
        raise ValueError('Incomplete case matrix')
    if requests != expected_requests:
        raise ValueError('Server markers differ from successful requests; inspect bad-verification leakage or missing receipt')
    for meta in metadata:
        if meta['chip'] != 'ESP32-C3' or meta['psram'] != 0 or meta['epoch'] != fixture['epoch']:
            raise ValueError('This paired record does not identify the intended C3 fixture context')
    if any(m.get('cpu_mhz') != 160 for m in metadata) or any(r.get('cpu_mhz') != 160 for r in records):
        raise ValueError('C3 context and case CPU checkpoints must all report normal 160 MHz')
    if metadata[0]['revision'] != metadata[1]['revision'] or metadata[0]['flash'] != metadata[1]['flash']:
        raise ValueError('Hardware identity changed between contexts')
    if identity.get('physicalC3') != 'IDENTIFIED':
        raise ValueError('Physical C3 identification has not been declared')
    workload = identity.get('readerWorkload', {})
    if not isinstance(workload, dict):
        raise ValueError('Missing reader workload')
    digest = workload.get('epubSha256', '')
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest):
        raise ValueError('Missing EPUB hash')
    for field in ('font', 'orientation', 'page', 'concurrentWorkers'):
        value = workload.get(field)
        if not isinstance(value, str) or not value.strip() or value.strip().upper() in ('UNKNOWN', 'NOT_MEASURED', 'NOT_IDENTIFIED'):
            raise ValueError('Missing reader workload: '+field)
    if type(workload.get('fontSize')) is not int or workload['fontSize'] <= 0:
        raise ValueError('Missing positive reader font size')
    source = identity.get('source', {})
    for key in ('cpRef', 'sdkRef', 'firmwareSha256'):
        text = source.get(key, '')
        expected_length = 64 if key == 'firmwareSha256' else 40
        if not isinstance(text, str) or len(text) != expected_length or any(ch not in '0123456789abcdef' for ch in text):
            raise ValueError('Missing exact source/firmware identity')
    device = identity.get('device', {})
    if device.get('chip') != 'ESP32-C3' or not device.get('model') or device.get('revision') != metadata[0]['revision']:
        raise ValueError('Missing identified physical C3 model/revision')
    if identity.get('rootSha256') != fixture['root_sha256']:
        raise ValueError('Trust fixture identity differs')
    drift = {}
    for context in sorted(CONTEXTS):
        drift[context] = {}
        for case in sorted(GOOD):
            sequence = sorted([r for r in records if r['context'] == context and r['case'] == case], key=lambda r:r['repeat'])
            drift[context][case] = {'free_end_minus_first': sequence[-1]['stop'][0]-sequence[0]['stop'][0],
                                    'largest_end_minus_first': sequence[-1]['stop'][1]-sequence[0]['stop'][1],
                                    'raw_after_stop': [r['stop'] for r in sequence]}
    return {'status': 'DATA_VALIDATED', 'records': records, 'metadata': metadata, 'identity': identity,
            'fixture': fixture, 'cleanup_drift': drift, 'release': 'NOT_QUALIFIED', 'energy': 'NOT_MEASURED',
            'ota': 'NOT_MEASURED', 'limits': ['Allocator window includes TCP/CA/TLS and concurrent system activity',
            'Regional lows need not occur at one time', 'Largest-block minima are sampled around wolfSSL_connect',
            'Stop samples include the live diagnostic client object', 'Instrumented firmware is not zero-overhead production firmware']}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs=2, type=Path)
    p.add_argument('--server', type=Path, required=True)
    p.add_argument('--identity', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows, meta = load_logs(a.logs)
    result = validate(rows, meta, json.loads(a.server.read_text()), json.loads(a.identity.read_text()), json.loads(a.fixture.read_text()))
    result['input_log_sha256'] = [hashlib.sha256(path.read_bytes()).hexdigest() for path in a.logs]
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print('DATA_VALIDATED; review raw cleanup drift and measurement limits before drawing a memory conclusion')
