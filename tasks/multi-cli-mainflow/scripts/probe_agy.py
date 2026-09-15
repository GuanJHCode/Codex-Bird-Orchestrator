#!/usr/bin/env python3
"""Bounded AGY startup diagnostic under the reviewer write boundary."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
import sys

os.umask(0o077)
root = Path(tempfile.mkdtemp(prefix="multi-cli-agy-probe-", dir="/tmp")).resolve()
workspace, scratch = root / "work", root / "scratch"
if "--long-scratch" in sys.argv:
    scratch = root / "host-spool" / ("host-launch-" + "a"*32) / ("attempt-" + "b"*24) / ("segment-" + "c"*24) / "scratch"
workspace.mkdir()
scratch.mkdir(parents=True)
prompt = "Reply with exactly AGY_START_OK. Do not use tools."
if "--read-file" in sys.argv:
    (workspace / "INPUT.txt").write_text("READ_OK_" + os.urandom(12).hex() + "\n")
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    prompt = "Read INPUT.txt in the current directory using a file-reading tool. Return exactly its contents. Do not edit files, run other tasks, delegate, or use network tools."
if "--view-file" in sys.argv:
    prompt = f"Use view_file to read {workspace}/INPUT.txt and return its contents. Do not use terminal/run_command, edit files, delegate, or use network tools."
rules = '(version 1) (allow default) (deny file-write*) (allow file-write* (literal "/dev/null")) (allow file-write* (subpath ' + json.dumps(str(scratch)) + '))'
log_args = [] if "--default-log" in sys.argv else ["--log-file", str(scratch/"cli.log")]
proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", rules, str(Path.home()/".local/bin/agy"), "--input-format", "stream-json", "--output-format", "stream-json", "--mode", "plan", "--model", "gemini-3.8-flash-low", *log_args], cwd=workspace, env=dict(os.environ, TMPDIR=str(scratch), AGY_CLI_DISABLE_AUTO_UPDATE="true"), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
proc.stdin.write(json.dumps({"event": "user", "message": {"content": prompt}}).encode()+b"\n")
proc.stdin.close()
sel = selectors.DefaultSelector()
sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
sel.register(proc.stderr, selectors.EVENT_READ, "stderr")
buffers = {"stdout": bytearray(), "stderr": bytearray()}
deadline = time.monotonic()+30
while sel.get_map() and time.monotonic() < deadline:
    for key, _ in sel.select(0.5):
        data=os.read(key.fileobj.fileno(),65536)
        if not data:
            sel.unregister(key.fileobj)
            continue
        if len(buffers[key.data]) < 1024*1024:
            buffers[key.data].extend(data)
if proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL)
        proc.wait(timeout=3)
print("root",root,"exit",proc.returncode)
for channel,data in buffers.items():
    print(channel, "bytes",len(data))
    for line in data.decode(errors="replace").splitlines():
        try:
            obj=json.loads(line)
        except ValueError:
            # Only startup failure diagnostics, never full transcript/config.
            if any(word in line.lower() for word in ("permission denied","operation not permitted","failed to","error:")):
                print(channel,line[:500])
            continue
        step = obj.get("step_update", {})
        print(channel, {"event":obj.get("event"),"keys":list(obj),"tools": obj.get("init",{}).get("tools"),"step": {k:v for k,v in step.items() if k in ("step_type","state","tool_name","text_delta")},"tool_error": step.get("tool_info",{}).get("error"),"result": {k:v for k,v in obj.get("result",{}).items() if k in ("status","response","error")}})
print("scratch_files",[str(p.relative_to(scratch)) for p in scratch.rglob('*') if p.is_file()][:20])
