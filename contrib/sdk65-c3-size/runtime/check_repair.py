#!/usr/bin/env python3
"""Targeted v2 flow and parser checks. Radio, CPU, heap and TLS boundaries are deliberate host mocks."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
HERE=Path(__file__).resolve().parent

def block(text, marker):
    start=text.index(marker)
    left=text.index('{',start)
    depth=1
    at=left+1
    while depth:
        depth += (text[at]=='{')-(text[at]=='}')
        at+=1
    return text[start:at]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cp',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    commands=[]
    def run(command):
        begin=time.monotonic();result=subprocess.run(command,capture_output=True,text=True)
        commands.append({'command':command,'seconds':round(time.monotonic()-begin,3),'exit':result.returncode,'stdout':result.stdout.strip()})
        if result.returncode: raise RuntimeError(result.stderr or result.stdout)
    with tempfile.TemporaryDirectory(prefix='g10-v2-flow-') as temporary:
        directory=Path(temporary)
        main=(a.cp/'src/main.cpp').read_text()
        dispatcher=block(main,'if (logSerial.available() > 0)')
        (directory/'dispatch.inc').write_text('void dispatch() {\n'+dispatcher+'\n}\n')
        reader=(a.cp/'src/activities/reader/EpubReaderActivity.cpp').read_text()
        reader_start=reader.index('void EpubReaderActivity::loop()')
        guarded=reader[reader.index('#if defined(CROSSPOINT_TLS_MEMORY_PROBE)',reader_start):]
        guarded=guarded[:guarded.index('#endif')+len('#endif')]
        (directory/'reader.inc').write_text('void readyReader() {\n'+guarded+'\n}\n')
        for flags,variant in [(['-DCROSSPOINT_TLS_MEMORY_PROBE=1'],'probe'),([],'flag-off')]:
            run(['c++','-std=c++20','-fsanitize=address,undefined',*flags,'-I',str(HERE/'host/flow_stubs'),
                 '-I',str(HERE/'host/stubs'),'-I',str(directory),'-I',str(a.cp/'src'),
                 str(HERE/'host/Flow.cpp'),'-o',str(directory/variant)])
            scenarios=['normal','wrong-command','foreign-radio','prep-timeout','mode-failure','clock-failure',
                       'foreign-monitor','monitor-stop-failure'] if flags else ['flag-off']
            for scenario in scenarios: run([str(directory/variant),scenario])
        run(['c++','-std=c++20','-fsanitize=address,undefined','-I',str(HERE/'host/stubs'),'-I',str(a.cp/'src/util'),
             str(HERE/'host/Contracts.cpp'),'-o',str(directory/'contracts')])
        run([str(directory/'contracts')])
        run(['python3',str(HERE/'test_parser.py')])
    a.output.write_text(json.dumps({'status':'PASS','commands':commands,'flow':'Actual main serial dispatcher and ready-reader guarded caller extracted from candidate; production probe compiled unchanged',
      'boundary':'Radio/CPU/heap/TLS mocked; no physical claims','tls52':'REUSED unchanged SDK/runtime connect; bind source hashes','device':'NOT_MEASURED'},indent=2)+'\n')
    print('PASS: 9 actual dispatch/ready-reader flow cases, production probe ASan/UBSan, config/window contracts and parser')
if __name__=='__main__':main()
