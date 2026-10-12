#!/usr/bin/env python3
"""Synthetic parser fault cases. These deliberately invented bytes are not runtime measurements."""
import copy
from pathlib import Path
import tempfile
from parse_results import validate, load_logs

rows=[]
server={'fixture':{'protected_requests':[]}}
for context in ['early_boot','reader_ui']:
    cases=[(name, repetition) for name in ['tls12','tls13'] for repetition in range(1,11)]
    cases += [(name,1) for name in ['wronghost','unknownca','malformedca','stall','abort','drop']]
    for name, repetition in cases:
        good=name in ['tls12','tls13']
        rows.append({'schema':1,'context':context,'case':name,'repeat':repetition,
          'cpu_mhz':160,'monitor_start':0,'monitor_stop':0,'monitor_stop_called':True,'window_min':50000,
          'lifetime_before':40000,'lifetime_after':40000,'before':[80000,40000],
          'connect':[60000,30000],'response':[60000,30000],'stop':[80000,40000],
          'sampled_free':55000,'sampled_largest':25000,'attempts':1 if good or name=='abort' else 2,
          'connect_calls':0 if name=='malformedca' else 3,'timeouts':2 if name=='stall' else 0,
          'last_error':0,'tls':('TLSv1.2' if name=='tls12' else 'TLSv1.3') if good else 'none',
          'connect_ms':4000 if name=='stall' else 100,'total_ms':4500,
          'connected':good,'aborted':name=='abort','written':90 if good else 0,'received':78 if good else 0,'response_ok':good})
        if good: server['fixture']['protected_requests'].append(f'GET /G10_PROTECTED/{name}/{repetition} HTTP/1.1')
meta=[{'context':context,'chip':'ESP32-C3','revision':1,'psram':0,'flash':16000000,'epoch':1800000000,'cpu_mhz':160}
      for context in ['early_boot','reader_ui']]
identity={'source':{'cpRef':'a'*40,'sdkRef':'b'*40,'firmwareSha256':'c'*64},
          'device':{'model':'X4','chip':'ESP32-C3','revision':1},'rootSha256':'d'*64,'physicalC3':'IDENTIFIED', 'readerWorkload':{'epubSha256':'e'*64,'font':'Noto Serif','fontSize':14,'orientation':'portrait','page':'2/6','concurrentWorkers':'none observed'}}
fixture={'epoch':1800000000,'root_sha256':'d'*64}
assert validate(rows,meta,server,identity,fixture)['status']=='DATA_VALIDATED'
count=1
for mutate in [lambda r,m,s,i,f:r.pop(), lambda r,m,s,i,f:r.append(r[0]),
               lambda r,m,s,i,f:r[0].update(monitor_start=-1),lambda r,m,s,i,f:r[0].update(monitor_stop=42),
               lambda r,m,s,i,f:r[0].update(monitor_stop_called=False),lambda r,m,s,i,f:r[20].update(written=1),
               lambda r,m,s,i,f:r[0].update(response_ok=False),lambda r,m,s,i,f:r[0].update(sampled_free=-1),
               lambda r,m,s,i,f:r[0].update(tls='TLSv1.3'),lambda r,m,s,i,f:r[24].update(aborted=False),
               lambda r,m,s,i,f:r[24].update(connect_calls=0),lambda r,m,s,i,f:r[23].update(timeouts=1),
               lambda r,m,s,i,f:m[0].update(chip='ESP32-S3'),lambda r,m,s,i,f:m[1].update(revision=2),
               lambda r,m,s,i,f:i['source'].update(firmwareSha256=''),lambda r,m,s,i,f:i.update(rootSha256='wrong'),
               lambda r,m,s,i,f:i.update(physicalC3='NOT_IDENTIFIED'),
               lambda r,m,s,i,f:i.update(readerWorkload={}),
               lambda r,m,s,i,f:i['readerWorkload'].update(epubSha256=None),
               lambda r,m,s,i,f:i['readerWorkload'].update(font=None),
               lambda r,m,s,i,f:i['readerWorkload'].update(fontSize=None),
               lambda r,m,s,i,f:i['readerWorkload'].update(orientation=''),
               lambda r,m,s,i,f:i['readerWorkload'].update(page='UNKNOWN'),
               lambda r,m,s,i,f:i['readerWorkload'].update(concurrentWorkers=None),
               lambda r,m,s,i,f:m[0].update(cpu_mhz=10),
               lambda r,m,s,i,f:r[0].update(cpu_mhz=10),
               lambda r,m,s,i,f:s['fixture']['protected_requests'].append('GET /G10_PROTECTED/wronghost/1 HTTP/1.1')]:
    data=copy.deepcopy([rows,meta,server,identity,fixture]);mutate(*data)
    try: validate(*data)
    except ValueError: count+=1
    else: raise AssertionError('negative parser case unexpectedly accepted')
with tempfile.TemporaryDirectory() as directory:
    a=Path(directory)/'a';b=Path(directory)/'b'
    a.write_text('G10_ERROR monitor_failed\n');b.write_text('G10_END\n')
    try: load_logs([a,b])
    except ValueError: count+=1
    else: raise AssertionError('error log accepted')
print(f'PASS: {count} synthetic parser cases; no device evidence')
