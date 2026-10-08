#!/usr/bin/env python3
"""Reconstruct the public SDK supplement and check its capability without firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination', type=Path, help='new directory; existing destinations are refused')
parser.add_argument('--wolf-root', type=Path, required=True, help='Arduino-wolfSSL 5.7.2 sources')
parser.add_argument('--wolf-archive', type=Path, help='optional compatible host archive; otherwise build the published helper')
args = parser.parse_args()
lock = json.loads((HERE/'sources.json').read_text())
assert sha(HERE/'sdk-peer-capability.patch') == lock['patchSha256']
wolf = args.wolf_root.resolve()
assert json.loads((wolf/'library.json').read_text())['version'] == '5.7.2'
assert sha(wolf/'src/user_settings.h') == lock['wolfUserSettingsSha256']
dest = args.destination.resolve()
dest.mkdir()
started = time.monotonic()
sdk = dest/'sdk'
sdk.mkdir()
run(['git','init','-q'],sdk)
run(['git','fetch','--quiet','--depth=1',lock['repository'],lock['publicSupportCommit']],sdk)
run(['git','checkout','--quiet','--detach','FETCH_HEAD'],sdk)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=sdk,text=True).strip() == lock['publicSupportCommit']
for name, digest in lock['rawFiles'].items():
    assert sha(sdk/name) == digest, name
support = sdk/'contrib/sdk65-verification'
assert sha(support/'sdk65-compatible.patch') == lock['publishedVerificationPatchSha256']
run(['git','apply','--check',str(support/'sdk65-compatible.patch')],sdk)
run(['git','apply',str(support/'sdk65-compatible.patch')],sdk)
run(['git','apply','--check',str(HERE/'sdk-peer-capability.patch')],sdk)
run(['git','apply',str(HERE/'sdk-peer-capability.patch')],sdk)
for name, digest in lock['resultFiles'].items():
    assert sha(sdk/name) == digest, name
run(['git','diff','--check'],sdk)
archive = args.wolf_archive.resolve() if args.wolf_archive else support/'build/libwolfssl-host.a'
if not args.wolf_archive:
    run([sys.executable,str(support/'build_wolfssl.py'),'--wolf-root',str(wolf)],sdk)
assert archive.is_file()
flags = ['-std=c++20','-O0','-DFREEINK_NET_WOLFSSL=1','-DWOLFSSL_USER_SETTINGS',
         '-DWOLFSSL_OPTIONS_H','-DWOLFSSL_CLIENT_EXAMPLE','-DWOLFSSL_TLS13',
         '-DWOLFSSL_HAVE_SP_ECC','-DWOLFSSL_SP_SMALL','-DHAVE_CURVE25519','-DHAVE_SNI']
rows = []
with tempfile.TemporaryDirectory(prefix='sdk-capability-') as tmp:
    temp=Path(tmp)
    probe=temp/'probe.cpp'
    probe.write_text('''#include <SecureHttpClient.h>
#include <iostream>
template<class T> constexpr bool declared() { return requires { T::peerVerificationAvailable(); }; }
template<class T> bool available() {
  if constexpr (declared<T>()) return T::peerVerificationAvailable();
  return false;
}
int main() {
  std::cout << std::boolalpha << "{\\"clientDeclared\\":" << declared<freeink::SecureClient>()
    << ",\\"httpDeclared\\":" << declared<freeink::SecureHttpClient>()
    << ",\\"clientAvailable\\":" << available<freeink::SecureClient>()
    << ",\\"httpAvailable\\":" << available<freeink::SecureHttpClient>() << "}\\n";
}
''')
    raw=temp/'raw';raw.mkdir()
    for name in lock['rawFiles']:
        (raw/Path(name).name).write_bytes(subprocess.check_output(['git','show','HEAD:'+name],cwd=sdk))
    for mode in ['older-sdk','backend-disabled','verified-backend']:
        include=raw if mode=='older-sdk' else sdk/'libs/network/SecureNet/include'
        source=raw/'SecureClient.cpp' if mode=='older-sdk' else sdk/'libs/network/SecureNet/src/SecureClient.cpp'
        options=['-std=c++20','-O0'] if mode=='backend-disabled' else flags
        command=['nice','-n','10','c++',*options,'-I',str(support/'test/stubs'),'-I',str(include),'-I',str(wolf/'src'),str(source),str(probe)]
        if mode!='backend-disabled':command += [str(archive)]
        exe=temp/mode
        run([*command,'-o',str(exe)],sdk)
        result=json.loads(subprocess.check_output([str(exe)],text=True))
        expected={'clientDeclared':mode!='older-sdk','httpDeclared':mode!='older-sdk',
                  'clientAvailable':mode=='verified-backend','httpAvailable':mode=='verified-backend'}
        assert result==expected,(mode,result)
        rows.append({'mode':mode,'result':result,'status':'PASS'})
receipt={'status':'PASS','checks':rows,'publicSupportCommit':lock['publicSupportCommit'],
         'sourceHashesMatchG1':True,'seconds':round(time.monotonic()-started,3),
         'firmwareBuilds':0,'tlsHandshakesRun':0,'device':'NOT_TESTED'}
(dest/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
