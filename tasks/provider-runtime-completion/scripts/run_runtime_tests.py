"""Run historical runtime suites separately to preserve their import scopes."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
suites = [
    "tasks/g0-tui-proxy/tests",
    "tasks/g0-completion/tests",
    "tasks/g0-auth-preserving-activation/tests",
    "tasks/g0-proxy-continuation/cold-start/tests",
    "tasks/g0-global-delivery-validation/tests",
]
failed = False
for suite in suites:
    print(f"SUITE {suite}", flush=True)
    result = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", suite, "-q"], cwd=root)
    failed = failed or result.returncode != 0
raise SystemExit(int(failed))
