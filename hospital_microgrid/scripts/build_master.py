import sys
from pathlib import Path

# Ensure the scripts directory is in sys.path so we can import peer scripts
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from generate_master import generate_master

if __name__ == "__main__":
    generate_master()
