"""
setup.py — Hospital Microgrid Full Pipeline Setup
==================================================
Run this script ONCE before launching the dashboard for the first time.
It will generate all datasets and train the AI model in the correct order.

Usage:
    python setup.py
"""

import subprocess
import sys
import os
import time

# ── Colour helpers (work on Windows 10+ and Linux/Mac) ───────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"

def _supports_colour():
    """Return True if the terminal supports ANSI colour codes."""
    if sys.platform == "win32":
        # Enable ANSI on Windows 10+ via the virtual terminal
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOUR = _supports_colour()

def c(text, *codes):
    if USE_COLOUR:
        return "".join(codes) + text + RESET
    return text


# ── Pipeline definition ───────────────────────────────────────────────────────
# All scripts live inside hospital_microgrid/scripts/ relative to this file.
PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital_microgrid")

PIPELINE = [
    {
        "step":    1,
        "label":   "Generate weather data",
        "script":  os.path.join("scripts", "generate_weather.py"),
        "detail":  "Fetches/generates historical weather for Casablanca "
                   "(temperature, irradiance, wind speed).",
    },
    {
        "step":    2,
        "label":   "Generate energy supply data",
        "script":  os.path.join("scripts", "generate_supply.py"),
        "detail":  "Calculates solar PV and wind turbine generation curves "
                   "from the weather data.",
    },
    {
        "step":    3,
        "label":   "Generate energy demand data",
        "script":  os.path.join("scripts", "generate_demand.py"),
        "detail":  "Simulates hospital load profiles across all priority levels "
                   "(P1 critical → P5 deferrable).",
    },
    {
        "step":    4,
        "label":   "Generate battery state data",
        "script":  os.path.join("scripts", "generate_batteries.py"),
        "detail":  "Simulates battery charge/discharge cycles and state-of-charge "
                   "over the full time horizon.",
    },
    {
        "step":    5,
        "label":   "Build master dataset",
        "script":  os.path.join("scripts", "build_master.py"),
        "detail":  "Merges all data sources into data/master_dataset.csv "
                   "and computes derived features.",
    },
    {
        "step":    6,
        "label":   "Train AI prediction model",
        "script":  os.path.join("scripts", "run_training.py"),
        "detail":  "Trains the LSTM/dense neural network on the master dataset. "
                   "This step may take several minutes — please be patient.",
    },
]

TOTAL_STEPS = len(PIPELINE)


# ── Helpers ───────────────────────────────────────────────────────────────────
def banner():
    width = 60
    print()
    print(c("=" * width, BOLD, CYAN))
    print(c("  SMART HOSPITAL MICROGRID — FIRST-TIME SETUP", BOLD, CYAN))
    print(c("=" * width, BOLD, CYAN))
    print(c(f"  Running {TOTAL_STEPS} pipeline steps. Do not close this window.", DIM))
    print(c("=" * width, BOLD, CYAN))
    print()


def step_header(step_info):
    n     = step_info["step"]
    label = step_info["label"]
    detail = step_info["detail"]
    print(c(f"[{n}/{TOTAL_STEPS}] {label}", BOLD, YELLOW))
    print(c(f"      {detail}", DIM))
    print(c(f"      Script: {step_info['script']}", DIM))


def run_step(step_info):
    """Run a single pipeline step. Returns True on success, False on failure."""
    script = step_info["script"]

    # Scripts live inside hospital_microgrid/ — resolved from PROJECT_DIR
    full_path = os.path.join(PROJECT_DIR, script)

    if not os.path.isfile(full_path):
        print(c(f"\n  ✗ Script not found: {full_path}", RED, BOLD))
        print(c(  "    Make sure hospital_microgrid/ is present next to setup.py.", RED))
        return False

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, full_path],
            # Run with cwd = hospital_microgrid/ so relative paths inside
            # each script (e.g. data/, models/) resolve correctly.
            cwd=PROJECT_DIR,
            check=False,          # We handle non-zero exit codes ourselves
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            print(c(f"\n  ✗ Step failed with exit code {result.returncode} "
                    f"(after {elapsed:.1f}s)", RED, BOLD))
            return False

        print(c(f"  ✓ Done  ({elapsed:.1f}s)", GREEN, BOLD))
        return True

    except KeyboardInterrupt:
        print(c("\n\n  ⚠  Setup interrupted by user (Ctrl+C).", YELLOW, BOLD))
        sys.exit(1)
    except Exception as exc:
        print(c(f"\n  ✗ Unexpected error: {exc}", RED, BOLD))
        return False


def success_banner():
    width = 60
    print()
    print(c("=" * width, BOLD, GREEN))
    print(c("  ✓  SETUP COMPLETE!", BOLD, GREEN))
    print(c("=" * width, BOLD, GREEN))
    print()
    print(c("  All datasets have been generated and the AI model", GREEN))
    print(c("  has been trained. You can now launch the system:", GREEN))
    print()
    print(c("  Option A — One click (Windows):", BOLD))
    print(c("    Double-click  launch.bat", CYAN))
    print()
    print(c("  Option B — Manual (3 terminals, from hospital_microgrid/):", BOLD))
    print(c("    Terminal 1:  npx hardhat node", CYAN))
    print(c("    Terminal 2:  npx hardhat run scripts/deploy.js --network localhost", CYAN))
    print(c("    Terminal 3:  python -m streamlit run dashboard/app.py", CYAN))
    print()
    print(c("=" * width, BOLD, GREEN))
    print()


def failure_banner(failed_step):
    width = 60
    print()
    print(c("=" * width, BOLD, RED))
    print(c("  ✗  SETUP FAILED", BOLD, RED))
    print(c("=" * width, BOLD, RED))
    print()
    print(c(f"  Step {failed_step['step']}/{TOTAL_STEPS} failed: "
            f"{failed_step['label']}", RED))
    print()
    print(c("  Please check the error output above, fix the issue,", RED))
    print(c("  and re-run:  python setup.py", RED))
    print()
    print(c("=" * width, BOLD, RED))
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    banner()

    for step_info in PIPELINE:
        step_header(step_info)
        ok = run_step(step_info)
        print()           # blank line between steps

        if not ok:
            failure_banner(step_info)
            sys.exit(1)

    success_banner()
    sys.exit(0)


if __name__ == "__main__":
    main()
