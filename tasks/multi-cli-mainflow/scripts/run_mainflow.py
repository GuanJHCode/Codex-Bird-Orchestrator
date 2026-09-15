#!/usr/bin/env python3
"""Opt-in real CLI read/collect/ACK/accept trial; uses the current login environment.

Only task-owned requests are generated. Runtime state is retained for audit and
recovery. No login, lock replacement, or existing installation changes occur.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--provider", action="append", choices=["claude-code", "antigravity-cli", "grok-build", "codex-cli"], required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix="multi-cli-flow-", dir="/tmp")).resolve()
    state, workspace = root / "state", root / "workspace"
    workspace.mkdir()
    # The task-specific file proves a real tool read, rather than prompt echo.
    marker = "READ_OK_" + os.urandom(12).hex()
    (workspace / "INPUT.txt").write_text(marker + "\n")
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    binary = str(args.binary.resolve())
    plugin_root = Path(binary).parent.parent
    wrapper = plugin_root / "scripts/invoke.sh"
    if not wrapper.is_file():
        parser.error("--binary must belong to an installed plugin version")
    command_env = dict(os.environ, PLUGIN_ROOT=str(plugin_root))
    transcript = {"runtime_root": str(root), "providers": {}, "completed": False}
    command_log = []
    submitted = None

    def call(command, *options, request=None, timeout=15):
        path = None
        argv = [str(wrapper), command]
        if command not in ("provider-probe", "provider-lock"):
            argv += ["--state-dir", str(state)]
        if request is not None:
            path = root / "request.json"
            path.write_text(json.dumps(request))
            argv += ["--request", str(path)]
        argv += [str(x) for x in options]
        try:
            result = subprocess.run(argv, env=command_env, capture_output=True, timeout=timeout)
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
        body = json.loads(result.stdout if result.returncode == 0 else result.stderr)
        command_log.append({"command": command, "exit": result.returncode, "status": body.get("status", "")})
        if result.returncode:
            raise RuntimeError(f"{command}: {body}")
        return body

    server_log = (root / "server.log").open("wb")
    server = subprocess.Popen([binary, "serve", "--state-dir", str(state)], stdout=server_log, stderr=server_log)
    try:
        call("ensure-running")
        birth = subprocess.check_output(["/bin/ps", "-o", "lstart=", "-p", str(os.getpid())], text=True).strip()
        owner = call("owner-bind", request={"controller_thread": "multi-cli-mainflow", "origin_pid": os.getpid(), "origin_birth": birth})
        tasks = []
        names = {"claude-code": "claude", "antigravity-cli": "agy", "grok-build": "grok", "codex-cli": "codex"}
        models = {"claude-code": "haiku", "antigravity-cli": "gemini-3.8-flash-low", "grok-build": "grok-4.5", "codex-cli": "gpt-5.6-luna"}
        for provider in args.provider:
            path = Path(shutil.which(names[provider])).resolve()
            probe = call("provider-probe", request={"provider": provider, "binary_path": str(path)})
            transcript["providers"][provider] = {"lock": probe["lock"], "profile_supported": probe["profile_supported"], "reason": probe["reason"]}
            if not probe["profile_supported"]:
                raise RuntimeError(f"{provider}: {probe['reason']}")
            prompt = "Read INPUT.txt in the current directory using a file-reading tool. Return exactly its contents. Do not edit files, run other tasks, delegate, or use network tools."
            if provider == "antigravity-cli":
                prompt = f"Use view_file to read {workspace}/INPUT.txt and return its contents. Do not use terminal/run_command, edit files, delegate, or use network tools."
            tasks.append({"id": provider, "max_attempts": 1, "max_active_ms": 120000, "completion_policy": "owner_review", "adapter": {
                "provider": provider, "provider_lock": probe["lock"], "directory": str(workspace),
                "profile": {"version": 1, "role": "reviewer", "permission": "read-only", "model": models[provider], "timeout_ms": 120000},
                "prompt": prompt,
            }})
        owner.pop("version", None)
        owner.update(run_id="multi-cli-mainflow", plan_revision=1, delivery_mode="collect", tasks=tasks)
        submitted = call("submit", request=owner)
        control = submitted["control_file"]
        pending = set(args.provider)
        deadline = time.monotonic() + 150
        while pending and time.monotonic() < deadline:
            for task in list(pending):
                snapshot = call("status", "--task-id", task, "--control-file", control)
                item = transcript["providers"][task]
                if item.get("status") != snapshot["status"]:
                    print(task, snapshot["status"], flush=True)
                item["status"] = snapshot["status"]
                item["snapshot"] = snapshot
                if snapshot["status"] not in ("result_ready", "failed", "interrupted", "unknown", "blocked_dependency"):
                    continue
                collection = call("collect", "--task-id", task, "--control-file", control)
                item["collection"] = collection
                if snapshot["status"] != "result_ready":
                    pending.remove(task)
                    continue
                events = [e for e in collection["events"] if e["kind"] == "result"]
                if len(events) != 1:
                    raise RuntimeError(f"{task}: expected exactly one result")
                event = events[0]
                artifact = event["artifact"]
                data = Path(artifact["path"]).read_bytes()
                # Provider prose/Markdown may surround the answer. Require the
                # exact unpredictable file token, with no alternate token, and
                # independently verify the immutable artifact and input file.
                if (hashlib.sha256(data).hexdigest() != artifact["sha256"]
                        or len(data) != artifact["size"]
                        or set(re.findall(r"READ_OK_[0-9a-f]+", data.decode())) != {marker}
                        or (workspace / "INPUT.txt").read_text() != marker + "\n"):
                    raise RuntimeError(f"{task}: incorrect result artifact")
                item["read_verified"] = True
                ack = {"version": 1, "task_id": task, "control_file": control, "delivery_id": collection["delivery_id"], "collection_proof_sha256": collection["collection_proof_sha256"], "decisions": [
                    {"event_id": e["event_id"], "event_revision": e["event_revision"], "event_hash": e["payload_hash"], "action_slot": e["action_slot"], "decision": "handled", "command_id": "ack-" + e["event_id"]}
                    for e in collection["events"] if e.get("action_slot") and e["kind"] != "progress"
                ]}
                call("ack", request=ack)
                call("ack", request=ack)
                after_ack = call("status", "--task-id", task, "--control-file", control)
                if after_ack["status"] != "result_ready":
                    raise RuntimeError("delivery ACK changed business acceptance")
                review = ["--task-id", task, "--control-file", control, "--work-revision", event["work_revision"], "--event-id", event["event_id"], "--event-revision", event["event_revision"], "--event-hash", event["payload_hash"], "--action-slot", event["action_slot"], "--decision", "accept", "--command-id", "accept-" + event["event_id"]]
                call("accept", *review)
                call("accept", *review)
                item["status"] = call("status", "--task-id", task, "--control-file", control)["status"]
                item["ack_idempotent"] = item["accept_idempotent"] = True
                print(task, item["status"], "read/ACK/accept verified", flush=True)
                pending.remove(task)
            if pending:
                time.sleep(0.5)
        transcript["summary"] = call("summary", "--task-id", args.provider[0], "--control-file", control)
        transcript["completed"] = all(x.get("status") == "completed" for x in transcript["providers"].values())
        if not transcript["completed"]:
            transcript["error"] = "mainflow_incomplete: " + ", ".join(f"{p}={v.get('status', 'not_started')}" for p, v in transcript["providers"].items() if v.get("status") != "completed")
    except Exception as exc:
        transcript["error"] = str(exc)
        print(type(exc).__name__, str(exc), flush=True)
    finally:
        if submitted:
            for task in args.provider:
                if transcript["providers"].get(task, {}).get("status") != "completed":
                    try:
                        call("stop", "--task-id", task, "--control-file", submitted["control_file"])
                    except Exception:
                        pass
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            transcript["coordinator_stop_unknown"] = True
        server_log.close()
        transcript["commands"] = command_log
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(transcript, indent=2) + "\n")
        print("Evidence:", args.evidence, "Runtime:", root, flush=True)
    return 0 if transcript["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
