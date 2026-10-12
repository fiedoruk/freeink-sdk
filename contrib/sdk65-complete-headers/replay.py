"""Reproduce the narrow header-completion fix on SDK65's public head."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
BASE="6d33e9fd8c6fd1c53c40c0ef1ccaa4535606610a"
p=argparse.ArgumentParser(description=__doc__);p.add_argument("destination",type=Path);a=p.parse_args()
root=a.destination.resolve();root.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent;manifest=json.loads((here/"manifest.json").read_text())
for name,h in manifest["files"].items():assert hashlib.sha256((here/name).read_bytes()).hexdigest()==h
started=time.monotonic();receipt={"status":"RUNNING","base":BASE}
with (root/"replay.log").open("w") as log:
 def run(command,cwd,expected=0):
  log.write("$ "+" ".join(command)+"\n");log.flush()
  result=subprocess.run(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
  assert result.returncode==expected,(command,result.returncode,expected)
 try:
  sdk=root/"sdk";sdk.mkdir()
  for command in [["git","init","-q"],["git","fetch","--depth=1","https://github.com/Free-Ink/freeink-sdk.git",BASE],["git","checkout","--detach","FETCH_HEAD"]]:run(command,sdk)
  def compile(name):
   exe=root/name
   run(["c++","-std=c++17","-Wall","-Wextra","-Werror","-fsanitize=address,undefined","-fno-omit-frame-pointer","-I"+str(here/"tests/stubs"),"-I"+str(sdk/"libs/network/SecureNet/include"),str(here/"tests/test_http_headers.cpp"),"-o",str(exe)],root)
   return str(exe)
  run([compile("before"),"negative"],root,42)
  run(["git","apply","--check",str(here/"complete-headers.patch")],sdk)
  run(["git","apply",str(here/"complete-headers.patch")],sdk)
  run([compile("after")],root)
  receipt.update(status="PASS",negativeExit=42,positiveExit=0,firmwareBuild=False,device=False)
 finally:
  receipt["seconds"]=round(time.monotonic()-started,3)
  (root/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt))
