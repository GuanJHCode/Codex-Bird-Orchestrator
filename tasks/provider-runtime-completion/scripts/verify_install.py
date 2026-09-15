"""Build-free package/install/doctor smoke test using a supplied Go binary."""
from pathlib import Path
import json
import os
import subprocess
import sys

repo = Path(__file__).resolve().parents[3]
binary = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
root.mkdir(mode=0o700)
python = Path(sys.executable).resolve()
package = root / "package"
version = "0.2.0-runtime-check"
subprocess.run(["sh", str(repo / "tasks/g1-g4-delivery/scripts/package-plugin.sh"),
                "--binary", str(binary), "--python", str(python),
                "--version", version, "--out", str(package)], check=True)


def request(name, value):
    path = root / f"{name}.json"
    with path.open("x") as stream:
        json.dump(value, stream)
    path.chmod(0o600)
    return path


install_request = request("install", {"source_root": str(package / "plugin"),
    "binary_path": str(binary), "destination_root": str(root / "installed"),
    "data_root": str(root / "state"), "version": version})
installed = json.loads(subprocess.check_output([str(binary), "install", "--request", str(install_request)]))["result"]
installed_binary = Path(installed["version_root"]) / "bin/codex-orchestrator"
doctor_request = request("doctor", {"destination_root": str(root / "installed")})
health = json.loads(subprocess.check_output([str(installed_binary), "doctor", "--request", str(doctor_request)]))["result"]
if not health["healthy"]:
    raise SystemExit("installed doctor rejected package")
print(json.dumps({"installed": True, "doctor_healthy": True, "version": version,
                  "binary": str(installed_binary), "native_runtime_files": len(list((Path(installed["version_root"]) / "runtime/g0").glob("*.py")))}))
