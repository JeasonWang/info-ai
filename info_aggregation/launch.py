"""Windows UTF-8 launcher for info_aggregation.

Usage: python launch.py [log_dir]
  log_dir: directory for stdout/stderr log files (default: ./logs)

This script forces UTF-8 on all text streams and redirects
stdout/stderr to files, bypassing cmd.exe encoding issues.
"""
import io
import os
import sys

# --- Force UTF-8 on stdio ---
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

# --- Redirect stdout/stderr to log files when running as a background service ---
# If LOG_DIR is set via env (from start-local.ps1), redirect to files there.
log_dir = os.environ.get("LOG_DIR", "")
redirect_to_files = log_dir and not sys.stdout.isatty()

if redirect_to_files:
    os.makedirs(log_dir, exist_ok=True)
    sys.stdout = open(os.path.join(log_dir, "info_aggregation_stdout.log"), "a", encoding="utf-8", errors="replace", buffering=1)
    sys.stderr = open(os.path.join(log_dir, "info_aggregation_stderr.log"), "a", encoding="utf-8", errors="replace", buffering=1)

# --- Run the real application ---
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

with open(os.path.join(script_dir, "main.py"), encoding="utf-8") as f:
    code = compile(f.read(), "main.py", "exec")
    exec(code)