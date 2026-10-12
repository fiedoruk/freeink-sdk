#!/usr/bin/env python3
"""Reconstruct the diagnostic candidate from public pinned refs. Does not compile or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    lock = json.loads((HERE/'source-lock.json').read_text())
    for name, expected in lock['files'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Packet hash mismatch: '+name)
    destination = args.destination.resolve()
    destination.mkdir()
    cp, sdk = destination/'crosspoint', destination/'crosspoint/freeink-sdk'
    commands = []
    def run(command, cwd):
        begin = time.monotonic()
        subprocess.run(command, cwd=cwd, check=True)
        commands.append({'command':command,'seconds':round(time.monotonic()-begin,3)})
    for name, repo in [('cp',cp),('sdk',sdk)]:
        repo.mkdir(exist_ok=True)
        run(['git','init','-q'],repo)
        run(['git','fetch','--quiet','--depth=1',lock[name]['url'],lock[name]['commit']],repo)
        run(['git','checkout','--quiet','--detach','FETCH_HEAD'],repo)
        head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
        if head != lock[name]['commit']:
            raise RuntimeError('Source ref differs: '+name)
        patch=HERE/('cp-runtime.patch' if name=='cp' else 'sdk-runtime.patch')
        run(['git','apply','--check',str(patch)],repo)
        run(['git','apply',str(patch)],repo)
        run(['git','diff','--check'],repo)
    shutil.copyfile(HERE/'platformio.local.ini',cp/'platformio.local.ini')
    for name, expected in lock['result_files'].items():
        if hashlib.sha256((cp/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Result hash mismatch: '+name)
    receipt={'source':'PASS','build':'NOT_RUN','device':'NOT_MEASURED','commands':commands,
             'cp':lock['cp']['commit'],'sdk':lock['sdk']['commit'],'target':'default'}
    (destination/'reconstruction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS: source reconstruction only; no firmware build or device operation')
if __name__ == '__main__': main()
